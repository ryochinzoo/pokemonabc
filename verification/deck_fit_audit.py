#!/usr/bin/env python3
"""操縦者のハードコード定数が「そのデッキ」と噛み合っているかの構造監査 (2026-08-13)。

**なぜ**: D76 副産物2(`docs/memo/decisions.md:1927`)は
「**デッキを替える判断のたびに、過去の修理が転移するかを再点検する必要がある**」で終わっている。
実害は測定済みで、`preserve_deck = my_deck_count <= 5` が tarountula 専用の較正値だったため
**7/18 に直した自山切れが、デッキを替えたら 71.4% で復活した**。
しかしその「再点検」をする道具が無かった。これがその計器。

**何をするか**: `main.py` を AST で走査して**モジュール定数の整数リテラルを悉皆列挙**し、
それぞれが「カードID」か「ワザID」かを**使用箇所から推論**したうえで、
同梱の `deck.csv` にその札が実在するかを突き合わせる。判定語彙:

    APPLIES    そのデッキに実在する = 生きている
    DEAD       不在 = その分岐は到達しない(そのデッキでは死んでいる)
    MISFIRING  門は開くが狙いが外れている。意図した対象は不在なのに、
               共条件を満たす**別の札**があるので、挙動は変わるが狙いどおりではない
    INERT      門は開くが本体が発火しない(自陣に前提が無い)
    DERIVED    deck.csv とカードDBのテキストから実行時に導出している = **加点**。欠陥ではない
    OPPONENT   相手アーキタイプ表など。「自デッキに無い」は正常
    UNREF      宣言されているのに一度も読まれていない
    PROVISIONAL 名前空間は推論できたが射程(自分/相手)の注釈が無い。暫定
    UNCLASS    整数がID位置にあるが名前空間を決められない ← **これが番犬**

**対戦は1戦も走らせない。エンジンも import しない。** 全33dirで0.3秒、読み取り専用。

**判定の限界(必ず併記)**:
- `MISFIRING` は「**狙いが外れている**」の証拠であって「**有害**」の証拠ではない。
  効果量は `bench.py` / `cew.py` でしか出ない。この道具は効果量を一切測っていない。
- 経路依存の到達可能性は見ていない。env のアブレーション旗(`V4_NO_*` 等)で切られている分岐、
  手前の `return` に食われている分岐、探索層の上書きは判別できない。
- 名前空間の推論はトークンの発見的規則。推論根拠の行を必ず併記するので**人が1件で falsify できる**。
- 偽陰性: 動的アクセス(`getattr`・文字列から作るID・算術で作るID)は見えない。

**層の宣言**: 層Sではない(標本分布を持たず、悉皆・決定的・同一コミットで同じ数が出る)。
**層0 構造監査**として扱う。census 部分は引用可。`CALIB-RISK` の助言部分は引用不可
(較正定数の因果は決定トレース未実施の推論 — `review-fable5-2026-08-11-verdict.md:64`)。

**前提検査**: ATTACK名前空間の判定を引用する前に `attackid_crosscheck.py` を1回走らせる
(ワザIDの通番導出をエンジンに突き合わせて悉皆で証明する。対戦0戦・約1秒)。

使い方:
    cd src/input/datasets/decks/starmie-aggro
    python3 ../../../../../verification/deck_fit_audit.py
    python3 ../../../../../verification/deck_fit_audit.py --strict     # 未分類で exit 1

    python3 verification/deck_fit_audit.py --all        # 全デッキdirの行列(記事の図)
    python3 verification/deck_fit_audit.py --selftest   # 既知の真値4件を検査
    python3 verification/deck_fit_audit.py --pilot verification/reference/x.py --deck ...
"""
import argparse
import ast
import csv
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "data", "EN_Card_Data.csv")
DECKS_ROOT = os.path.normpath(
    os.path.join(HERE, "..", "src", "input", "datasets", "decks"))

# 導出の健全性ピン。合わなければ即 exit(黙って劣化させない)。
PIN_ATTACKS = 1556
PIN_CARDS = 1267
PIN_PAIRS = {            # attackId -> (owner cardId, CSV上のワザ名)
    1072: (743, "Powerful Hand"),
    1486: (1030, "Water Gun"),
    1487: (1031, "Jetting Blow"),
    1488: (1031, "Nebula Beam"),
}

CARD, ATTACK = "CARD", "ATTACK"
SELF, OPPONENT, NONE_SCOPE = "SELF", "OPPONENT", "NONE"

# 使用箇所の相手側トークン → 名前空間。属性チェーンの末尾か変数名で引く。
CARD_TOKENS = {"id", "cardid", "card_id", "cid", "ecid", "contextcard",
               "effect_card_id", "context_card_id", "tid", "toolid", "pid"}
ATTACK_TOKENS = {"attackid", "attack_id", "aid", "attacks", "atkid"}
# **第3の名前空間**: エンジンの IntEnum の値。カードIDでもワザIDでもないので
# 「デッキに実在するか」を問うのが無意味(`_WATER_ENERGY_TYPE = 3` は EnergyType.WATER で、
# カード3番の Basic {W} Energy とは別物 — 偶然どちらも水なので取り違えても気付きにくい)。
# 定数名で個別注釈するのではなく、`c.energyType == X` という**使用箇所の形**で判別する。
ENUM_TOKENS = {"energytype", "cardtype", "weakness", "resistance",
               "specialconditiontype", "selecttype", "optiontype", "areatype"}
ENUM = "ENUM"


class Ann:
    """定数の**意味だけ**を注釈する。発見はASTがやるので、ここが古くなっても取り逃さない。

    未注釈の定数は PROVISIONAL / UNCLASS に出て --strict が落ちるので、
    **定数を足した diff が、そのまま番犬に引っかかる。**
    """

    def __init__(self, ns=None, scope=SELF, target=None, cocond=None,
                 cocond_self=None, kind=None, note=None):
        self.ns = ns
        self.scope = scope
        self.target = target          # 意図した対象カードID(MISFIRING判定用)
        self.cocond = cocond          # 門の残り条件(閉じた述語集合の名前)
        self.cocond_self = cocond_self
        self.kind = kind              # OPPONENT_DECK_TABLE / NAME_PREFIX / XREF
        self.note = note


# 定数名キー(dirキーではない)。`_IGNITION_ID` は30dirに出るが、注釈は1つで足りる。
ANNOTATIONS = {
    "_SCALING_DAMAGE":          Ann(ns=ATTACK, scope=SELF),
    "_PLACEMENT_ATTACKS":       Ann(ns=ATTACK, scope=SELF),
    "_EFFECT_IGNORING_ATTACKS": Ann(ns=ATTACK, scope=SELF),
    "_TRFIX_SCALING":           Ann(ns=ATTACK, scope=SELF),
    "_IGNITION_ID":             Ann(ns=CARD, scope=SELF, target=1031,
                                    cocond="evolution_in_deck",
                                    note="進化体+バトル場+have<2 で最優先(main.py:404)"),
    "_EX_WALL_IDS":             Ann(ns=CARD, scope=OPPONENT,
                                    cocond_self="ex_or_mega_in_deck",
                                    note="_ex_wall_ids() がテキスト抽出。literalは except 経路のみ"),
    "_META_DECKS":              Ann(kind="OPPONENT_DECK_TABLE", scope=OPPONENT),
    "_CLASS_MATCHUP_VETO":      Ann(kind="XREF", scope=OPPONENT),
    "_FILLER_ID":               Ann(ns=CARD, scope=NONE_SCOPE, note="パディング用の実在カード"),
    "_TR_PREFIX":               Ann(kind="NAME_PREFIX", scope=SELF),
    # カードIDでもワザIDでもない: EnergyType の enum 値(WATER=3)。
    # 「3枚積んでいるか」を問うのが無意味なので、ID位置から外す。
    "_WATER_ENERGY_TYPE":       Ann(kind="ENUM_VALUE", scope=NONE_SCOPE,
                                    note="EnergyType.WATER の enum 値。カードIDではない"),
    "_BEACH_ID":                Ann(ns=CARD, scope=SELF),
    "_WALLY_ID":                Ann(ns=CARD, scope=SELF, cocond="evolution_in_deck"),
    "_CINDERACE_ID":            Ann(ns=CARD, scope=SELF),
    "_MEGA_STARMIE_ID":         Ann(ns=CARD, scope=SELF),
    "_JETTING_BLOW_ID":         Ann(ns=ATTACK, scope=SELF),
    "_NEBULA_BEAM_ID":          Ann(ns=ATTACK, scope=SELF),
    "_BENCH_SPLASH":            Ann(ns=ATTACK, scope=SELF),
    "_BIG_DRAW_IDS":            Ann(ns=CARD, scope=SELF),
    "_E3_RAD_ID":               Ann(ns=CARD, scope=SELF),
    "_E3_DRAW_EVOS":            Ann(ns=CARD, scope=SELF),
    "_E3_ALAKAZAM":             Ann(ns=CARD, scope=SELF),
}

# `--all` の行列に出す追跡対象(記事の図の列)
TRACKED = ["_IGNITION_ID", "_SCALING_DAMAGE", "_PLACEMENT_ATTACKS",
           "_EFFECT_IGNORING_ATTACKS"]

# `--strict` の番犬から外す dir と、その理由。**黙って外さず必ず表示する。**
# 我々が保守していないコードは注釈を足せないので、残渣を我々の責任として数えない。
# 逆に言えば、ここに無い dir の UNCLASS/PROVISIONAL は全部こちらの宿題。
STRICT_EXEMPT = {
    "mega-starmie-ex-deck": "D35 りょーちんのdir(読むだけ)。定数はクラス属性形式で"
                            "別系統、ID literal 105本。注釈を足す権限が無い",
}

# 較正定数(判定ではなく助言。因果を主張しない)
CALIB_PATTERNS = [
    (r"preserve_deck\s*=\s*.*?<=\s*(\d+)", "preserve_deck 閾値", "deckswap-tarountula"),
    (r"_PRESERVE_DECK_N\s*=\s*(\d+)", "_PRESERVE_DECK_N", "starmie-mastercontrol"),
    (r"_E3_PRESERVE_THR\s*=\s*(\d+)", "_E3_PRESERVE_THR", "alakazam-e3"),
]


# --------------------------------------------------------------------------
# カードDB
# --------------------------------------------------------------------------
def _cost_count(cost: str) -> int:
    cost = (cost or "").strip()
    if not cost or cost == "n/a":
        return 0
    return len(re.findall(r"\{\w\}", cost)) + cost.count("●")


class CardDB:
    """`EN_Card_Data.csv` から カード表 と ワザID→所有カード を導出する。

    行指向で読むと壊れる(効果テキストに改行が入る)。必ず csv.DictReader。
    ワザIDの通番導出は `attackid_crosscheck.py` がエンジンで悉皆証明済み。
    """

    def __init__(self, path=CSV_PATH):
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.cards = {}
        self.attack_owner = {}
        self.attack_name = {}
        aid = 0
        for r in rows:
            cid = int(r["Card ID"])
            c = self.cards.setdefault(cid, {
                "id": cid, "name": (r.get("Card Name") or "").strip(),
                "stage": (r.get("Stage (Pokémon)/Type (Energy and Trainer)") or "").strip(),
                "rule": (r.get("Rule") or "").strip(),
                "type": (r.get("Type") or "").strip(),
                "max_cost": 0, "effects": [], "atk_effects": [], "moves": [],
            })
            eff = (r.get("Effect Explanation") or "").strip()
            if eff:
                c["effects"].append(eff)
            mv = (r.get("Move Name") or "").strip()
            cost = (r.get("Cost") or "").strip()
            if not mv or mv == "n/a" or mv.startswith("[Ability]") or cost == "n/a":
                continue
            aid += 1
            self.attack_owner[aid] = cid
            self.attack_name[aid] = mv
            c["max_cost"] = max(c["max_cost"], _cost_count(cost))
            c["moves"].append((aid, mv))
            # ワザ行の効果テキストだけを別に持つ。較正助言の proxy が
            # 「特性の文言」や「相手が引く」を拾って嘘をつかないようにするため。
            if eff:
                c["atk_effects"].append(eff)
        self.n_attacks = aid

    def check_pins(self):
        bad = []
        if self.n_attacks != PIN_ATTACKS:
            bad.append(f"ワザ総数 {self.n_attacks} != {PIN_ATTACKS}")
        if len(self.cards) != PIN_CARDS:
            bad.append(f"カード総数 {len(self.cards)} != {PIN_CARDS}")
        for a, (cid, nm) in PIN_PAIRS.items():
            got = (self.attack_owner.get(a), self.attack_name.get(a))
            if got != (cid, nm):
                bad.append(f"ワザ{a} = {got} 期待 {(cid, nm)}")
        return bad

    # CSV の実際の語彙は 'Basic Pokémon' / 'Stage 1 Pokémon' / 'Stage 2 Pokémon' /
    # 'Item' / 'Supporter' / 'Pokémon Tool' / 'Stadium' / 'Special Energy' / 'Basic Energy'。
    # **'Basic Energy' が 'Basic' で始まる**ので、ポケモン判定は接尾の 'Pokémon' で見る
    # (かつ 'Pokémon Tool' を除く)。初版は `st in ('Basic', …)` で書いていて
    # 'Basic Pokémon' を1体もポケモンと認めていなかった。
    def is_pokemon(self, cid):
        st = self.cards.get(cid, {}).get("stage", "")
        return st.endswith("Pokémon") and st != "Pokémon Tool"

    def is_evolution(self, cid):
        st = self.cards.get(cid, {}).get("stage", "")
        return st.startswith("Stage") and st.endswith("Pokémon")

    def is_ex_or_mega(self, cid):
        return "ex" in self.cards.get(cid, {}).get("rule", "").lower()

    def name(self, cid):
        return self.cards.get(cid, {}).get("name", f"?{cid}")


def read_deck(path):
    """末尾カンマ許容(D55 / りょーちん形式)。probe_metadecks.read_ids と同じ流儀。"""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",").strip()
            if line:
                out.append(int(line))
    return out


# --------------------------------------------------------------------------
# AST: 発見 と 名前空間推論
# --------------------------------------------------------------------------
def _ints_in(node, refs=None):
    """ID位置の整数だけを返す。dictの値・算術の項は payload なので除く。

    `refs` を渡すと、既に発見済みのスカラー定数への**名前参照**も解決する
    (`{_JETTING_BLOW_ID: 50}` のキーを拾うため)。
    """
    def lit(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int) \
                and not isinstance(n.value, bool):
            return n.value
        if refs and isinstance(n, ast.Name) and n.id in refs:
            return refs[n.id]
        return None

    if (v := lit(node)) is not None and isinstance(node, ast.Constant):
        return [v], "scalar"
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        vals = [v for e in node.elts if (v := lit(e)) is not None]
        return vals, "seq"
    if isinstance(node, ast.Dict):
        # 値がリスト/タプル = デッキ表(キーはアーキタイプ名なので、IDは値の側)
        if node.values and all(isinstance(v, (ast.List, ast.Tuple)) for v in node.values):
            vals = sorted({e.value for v in node.values for e in v.elts
                           if isinstance(e, ast.Constant) and isinstance(e.value, int)})
            return vals, "decktable:%d" % len(node.values)
        keys = [v for k in node.keys if (v := lit(k)) is not None]
        return keys, "dictkey"
    return [], None


def _tail_token(node):
    """比較の相手側から、属性チェーンの末尾 or 変数名を取り出す。"""
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    if isinstance(node, ast.Name):
        return node.id.lower()
    if isinstance(node, ast.Subscript):
        return _tail_token(node.value)
    if isinstance(node, ast.Call):
        return _tail_token(node.func)
    return None


class Analyzer(ast.NodeVisitor):
    """定数の発見・参照数・使用箇所からの名前空間推論・派生ヘルパの検出。"""

    def __init__(self, src):
        self.tree = ast.parse(src)
        self.src_lines = src.split("\n")
        self.consts = {}       # name -> {"ids", "line", "shape"}
        self.none_globals = set()
        self.loads = {}        # name -> count
        self.evidence = {}     # name -> (ns, line, snippet)
        self.alias = {}        # 変数名 -> トークン(provenance)
        self._collect_top_level()
        self._collect_alias()
        self._collect_loads()
        self._infer()

    # -- 発見 ------------------------------------------------------------
    def _collect_top_level(self):
        """2周する。1周目でスカラー定数を集め、2周目でそれへの**名前参照**を解決する。

        1周だけだと `_BENCH_SPLASH = {_JETTING_BLOW_ID: 50}` のようにキーがリテラルでなく
        Name 参照の表を取り逃す(正規表現なら値の 50 しか見えない、という同じ穴)。
        """
        assigns = []
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                targets = [t for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets, value = [node.target], node.value
            else:
                continue
            if value is None:
                continue
            assigns.append((targets, value, node.lineno))

        scalars = {}
        for targets, value, lineno in assigns:
            for t in targets:
                if isinstance(value, ast.Constant) and value.value is None:
                    self.none_globals.add(t.id)
                    continue
                ids, shape = _ints_in(value)
                if ids:
                    self.consts[t.id] = {"ids": ids, "line": lineno, "shape": shape}
                    if shape == "scalar":
                        scalars[t.id] = ids[0]

        for targets, value, lineno in assigns:
            for t in targets:
                if t.id in self.consts or t.id in self.none_globals:
                    continue
                ids, shape = _ints_in(value, scalars)
                if ids:
                    self.consts[t.id] = {"ids": ids, "line": lineno,
                                         "shape": (shape or "seq") + ":byref"}

    def mutable_cells(self):
        """`_x[0] = …` で書き換えられる名前 = 可変セルであって定数表ではない。

        `_turn_seen = [9999]` は「ターン後退で新ゲームを検出する」ための1要素リストで、
        中身は毎ターン上書きされる。IDの表ではないので判定の対象外にする。
        名前を個別に列挙するのではなく、**添字への代入がある**という形で判別する。
        """
        out = set()
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                tgts = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in tgts:
                    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                        out.add(t.value.id)
        return out

    # -- alias provenance ------------------------------------------------
    def _collect_alias(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                tok = _tail_token(node.value)
                if tok in CARD_TOKENS or tok in ATTACK_TOKENS:
                    self.alias[node.targets[0].id.lower()] = tok
            elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                tok = _tail_token(node.iter)
                if tok in CARD_TOKENS or tok in ATTACK_TOKENS:
                    self.alias[node.target.id.lower()] = tok
            # `x = a if c else b` / IfExp の両枝も拾う
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name) \
                    and isinstance(node.value, ast.IfExp):
                for br in (node.value.body, node.value.orelse):
                    tok = _tail_token(br)
                    if tok in CARD_TOKENS or tok in ATTACK_TOKENS:
                        self.alias[node.targets[0].id.lower()] = tok

    # -- 参照数 ----------------------------------------------------------
    def _collect_loads(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                self.loads[node.id] = self.loads.get(node.id, 0) + 1

    # -- 名前空間推論 ----------------------------------------------------
    def _resolve(self, node):
        tok = _tail_token(node)
        if tok is None:
            return None
        tok = self.alias.get(tok, tok)
        if tok in ATTACK_TOKENS:
            return ATTACK
        if tok in CARD_TOKENS:
            return CARD
        if tok in ENUM_TOKENS:
            return ENUM
        return None

    def _record(self, name, ns, line):
        if name in self.consts and name not in self.evidence and ns:
            snip = self.src_lines[line - 1].strip() if 0 < line <= len(self.src_lines) else ""
            self.evidence[name] = (ns, line, snip[:90])

    def _infer(self):
        for node in ast.walk(self.tree):
            # `x in CONST` / `CONST == x` / `x == CONST`
            if isinstance(node, ast.Compare):
                left = node.left
                for op, right in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.In, ast.NotIn)):
                        nm = right.id if isinstance(right, ast.Name) else None
                        if nm:
                            self._record(nm, self._resolve(left), node.lineno)
                    elif isinstance(op, (ast.Eq, ast.NotEq)):
                        for a, b in ((left, right), (right, left)):
                            if isinstance(a, ast.Name) and a.id in self.consts:
                                self._record(a.id, self._resolve(b), node.lineno)
            # `CONST.get(x)` / `CONST[x]`
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("get", "__contains__") \
                    and isinstance(node.func.value, ast.Name) and node.args:
                self._record(node.func.value.id, self._resolve(node.args[0]), node.lineno)
            elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                self._record(node.value.id, self._resolve(node.slice), node.lineno)

    # -- 順序比較/算術に出る = IDではなくチューニング定数 -------------------
    def scalar_only(self, name):
        """順序比較・算術・スライス境界・range() に出る名前は、IDではなくチューニング定数。"""
        if name not in self.consts or self.consts[name]["shape"] != "scalar":
            return False

        def mentions(n):
            return any(isinstance(x, ast.Name) and x.id == name for x in ast.walk(n))

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Compare):
                if mentions(node) and any(
                        isinstance(o, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for o in node.ops):
                    return True
            elif isinstance(node, ast.BinOp) and mentions(node):
                return True
            elif isinstance(node, ast.Slice) and mentions(node):
                return True
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id in ("range", "round", "min", "max", "sorted") \
                    and any(mentions(a) for a in node.args):
                return True
        return False

    # -- 派生ヘルパ(=良い形)の検出 ----------------------------------------
    def derived_helpers(self):
        """`global _X`(_X はモジュールで None)+ デッキ/DBのテキストを条件で絞る関数。

        素朴に「_card_db() を触る関数」にすると1dirで11〜20件出て使えない。
        「memo化 + カードDBを読む + 文字列リテラルで絞り込む」まで要求すると
        `_ex_wall_ids` / `_deck_energy_types` / `_unreachable_evolution` / `_tool_kinds`
        だけが残る。デッキを読むだけの `_my_deck60` は**除く**(それは単なるデッキ読み込みで、
        「デッキに応じて挙動を変えている」わけではない)。
        """
        out = {}
        for fn in ast.walk(self.tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            globs = [g for n in ast.walk(fn) if isinstance(n, ast.Global) for g in n.names]
            memo = [g for g in globs if g in self.none_globals]
            if not memo:
                continue
            body = ast.dump(fn)
            has_str_filter = any(
                isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 2
                for n in ast.walk(fn))
            reads_deck = ("_my_deck60" in body or "read_deck_csv" in body
                          or "_deck_csv" in body)
            reads_db = "_card_db" in body or "all_card_data" in body
            has_cond = any(isinstance(n, (ast.If, ast.IfExp, ast.comprehension))
                           for n in ast.walk(fn))
            if reads_db and has_cond and has_str_filter:
                lits = sorted({n.value for n in ast.walk(fn)
                               if isinstance(n, ast.Constant)
                               and isinstance(n.value, int)
                               and not isinstance(n.value, bool) and n.value > 20})
                in_handler = set()
                for h in ast.walk(fn):
                    if isinstance(h, ast.ExceptHandler):
                        in_handler |= {n.value for n in ast.walk(h)
                                       if isinstance(n, ast.Constant)
                                       and isinstance(n.value, int)}
                out[fn.name] = {"memo": memo, "line": fn.lineno,
                                "literals": lits,
                                "fallback_only": bool(lits) and set(lits) <= in_handler}
        return out


# --------------------------------------------------------------------------
# 判定
# --------------------------------------------------------------------------
def cocond_holds(which, deck_counts, db, exclude=()):
    """閉じた述語集合。デッキに対する宣言的な条件だけを持つ(Turing完全にしない)。"""
    ids = [c for c in deck_counts if c not in exclude]
    if which == "evolution_in_deck":
        return [c for c in ids if db.is_evolution(c)]
    if which == "ex_or_mega_in_deck":
        return [c for c in ids if db.is_ex_or_mega(c)]
    if which == "water_pokemon_in_deck":
        return [c for c in ids if db.is_pokemon(c)
                and "{W}" in db.cards.get(c, {}).get("type", "")]
    return []


def audit(pilot_path, deck_path, db):
    src = open(pilot_path, encoding="utf-8").read()
    an = Analyzer(src)
    deck = read_deck(deck_path)
    counts = {}
    for c in deck:
        counts[c] = counts.get(c, 0) + 1

    derived = an.derived_helpers()
    derived_globals = {g for d in derived.values() for g in d["memo"]}
    cells = an.mutable_cells()

    entries = []
    for name, info in sorted(an.consts.items(), key=lambda kv: kv[1]["line"]):
        ann = ANNOTATIONS.get(name)
        e = {"name": name, "line": info["line"], "ids": info["ids"],
             "shape": info["shape"], "refs": an.loads.get(name, 0),
             "resolved": [], "note": (ann.note if ann else None)}

        if e["refs"] == 0:
            e["verdict"] = "UNREF"
            entries.append(e)
            continue
        if name in cells and not (ann and ann.ns):
            e["verdict"] = "SCALAR"
            e["ns"] = None
            e["detail"] = "添字代入で書き換わる可変セル。IDの表ではない"
            entries.append(e)
            continue
        if (ann and ann.kind == "OPPONENT_DECK_TABLE") \
                or info["shape"].startswith("decktable"):
            e["verdict"] = "OPPONENT"
            e["ns"] = None
            n_arch = info["shape"].split(":")[1] if ":" in info["shape"] else "?"
            e["detail"] = f"相手アーキタイプ表 {n_arch}型 / 異なるID {len(info['ids'])}種"
            selfhit = [i for i in info["ids"] if i in counts]
            e["self_hit"] = selfhit
            entries.append(e)
            continue
        if ann and ann.kind == "ENUM_VALUE":
            e["verdict"] = "NONE"
            e["ns"] = None
            e["detail"] = "enum値(カードID/ワザIDではない)"
            entries.append(e)
            continue
        if ann and ann.kind in ("XREF", "NAME_PREFIX"):
            e["verdict"] = "OPPONENT" if ann.scope == OPPONENT else "PROVISIONAL"
            e["ns"] = None
            entries.append(e)
            continue
        if an.scalar_only(name) and not (ann and ann.ns):
            e["verdict"] = "SCALAR"
            e["ns"] = None
            entries.append(e)
            continue

        ns = (ann.ns if ann and ann.ns else None) or (
            an.evidence[name][0] if name in an.evidence else None)
        e["ns"] = ns
        if name in an.evidence:
            e["evidence"] = {"line": an.evidence[name][1], "src": an.evidence[name][2]}
        if ns is None:
            e["verdict"] = "UNCLASS"
            entries.append(e)
            continue
        # 使用箇所から enum 値と分かった場合(`c.energyType == X`)。
        # 定数名の注釈ではなく形で判別しているので、新しい enum 定数にも自動で効く。
        if ns == ENUM:
            e["verdict"] = "NONE"
            e["detail"] = "エンジンのenum値。カードID/ワザIDではないので在否を問わない"
            entries.append(e)
            continue

        scope = ann.scope if ann else SELF
        e["scope"] = scope
        # ID を「デッキに実在するか」で数える。ATTACK は所有カードに解決してから数える。
        total = 0
        for i in info["ids"]:
            if ns == ATTACK:
                cid = db.attack_owner.get(i)
                n = counts.get(cid, 0) if cid else 0
                e["resolved"].append({"id": i, "card": cid, "n": n,
                                      "label": f"{i}→{cid} {db.name(cid)}"
                                               f"「{db.attack_name.get(i,'?')}」"
                                      if cid else f"{i}(ワザとして未解決)"})
            else:
                n = counts.get(i, 0)
                e["resolved"].append({"id": i, "card": i, "n": n,
                                      "label": f"{i} {db.name(i)}"})
            total += n
        e["hits"] = total

        if scope == NONE_SCOPE:
            e["verdict"] = "NONE"
        elif scope == OPPONENT:
            e["verdict"] = "OPPONENT"
            e["self_hit"] = [r["id"] for r in e["resolved"] if r["n"]]
        # ★ 意図した対象の検査は APPLIES より**先**に来なければならない。
        # MISFIRING はまさに「門(total>0)は開くが対象が不在」の状態なので、
        # total>0 で先に APPLIES に落とすと MISFIRING は永久に発火しない
        # (初版でこれを踏み、deckswap-honchkrow が APPLIES に見えていた)。
        elif ann and ann.target is not None:
            gate = [r for r in e["resolved"] if r["n"]]
            tgt_n = counts.get(ann.target, 0)
            e["target"] = {"id": ann.target, "name": db.name(ann.target), "n": tgt_n}
            if gate and tgt_n == 0:
                subs = cocond_holds(ann.cocond, counts, db, exclude=(ann.target,))
                e["substitutes"] = [
                    {"id": s, "name": db.name(s), "n": counts[s],
                     "stage": db.cards[s]["stage"], "max_cost": db.cards[s]["max_cost"]}
                    for s in sorted(set(subs), key=lambda x: -counts[x])]
                e["verdict"] = "MISFIRING" if subs else "INERT"
            else:
                # 門が開いていて対象も居る = 狙いどおり / 門が閉じている = 到達しない
                e["verdict"] = "APPLIES" if gate else "DEAD"
        else:
            e["verdict"] = "APPLIES" if total > 0 else "DEAD"
        if not (ann and ann.ns) and e["verdict"] in ("APPLIES", "DEAD"):
            e["verdict"] = "PROVISIONAL"
            e["provisional_as"] = "APPLIES" if total else "DEAD"
        entries.append(e)

    # 派生ヘルパ(=良い形)を加点として出す
    for fn, d in sorted(derived.items(), key=lambda kv: kv[1]["line"]):
        ann = None
        for g in d["memo"]:
            ann = ANNOTATIONS.get(g) or ann
        e = {"name": fn + "()", "line": d["line"], "ids": d["literals"],
             "shape": "derived", "refs": an.loads.get(fn, 0), "ns": None,
             "verdict": "DERIVED", "fallback_only": d["fallback_only"],
             "resolved": [], "note": (ann.note if ann else None)}
        if ann and ann.cocond_self:
            ok = cocond_holds(ann.cocond_self, counts, db)
            e["self_cocond"] = {"which": ann.cocond_self, "met": bool(ok), "n": len(ok)}
            if not ok:
                e["verdict"] = "DERIVED"
                e["inert_note"] = f"自側共条件 {ann.cocond_self} = False → この分岐は発火しない"
        entries.append(e)

    # 較正定数(助言のみ)
    calib = []
    for pat, label, origin in CALIB_PATTERNS:
        for m in re.finditer(pat, src):
            line = src[:m.start()].count("\n") + 1
            calib.append({"label": label, "value": int(m.group(1)),
                          "line": line, "calibrated_on": origin})
    # D76 の機構に合わせた2つの代理量。**共起の記述であって因果の主張ではない。**
    # 素朴に /draw|search your deck/ を効果テキスト全部に当てると、
    # 「相手が引く」や特性の文言まで拾って 60枚中33枚が該当し、何も言っていない数になる
    # (初版で実際にそうなった)。自分が引く/掘る文言に絞る。
    _BURN = re.compile(r"\bsearch your deck\b|\bdraw \d+ cards?\b|\bdraw a card\b", re.I)
    burn = sum(n for c, n in counts.items()
               if any(_BURN.search(t) and "opponent draws" not in t.lower()
                      for t in db.cards.get(c, {}).get("effects", [])))
    # D76 の機構そのもの: **ワザの打点が手札枚数に比例する**(例: Alakazam「Powerful Hand」=
    # 'for each card in your hand')。だから操縦者は打点のために引き続け、山札温存が効かない。
    # 特性やトレーナーの文言ではなく、**ワザ行の効果テキスト**だけを見る。
    _HANDSCALE = re.compile(r"for each card in your hand", re.I)
    hand_scale = sorted(c for c in counts
                        if any(_HANDSCALE.search(t)
                               for t in db.cards.get(c, {}).get("atk_effects", [])))
    proxies = {"deck_burn": burn, "hand_scaling_attack": bool(hand_scale),
               "hand_scaling_cards": hand_scale}

    return {"entries": entries, "calib": calib, "proxies": proxies,
            "deck_size": len(deck), "n_derived": len(derived)}


# --------------------------------------------------------------------------
# 出力
# --------------------------------------------------------------------------
ORDER = ["MISFIRING", "INERT", "DEAD", "APPLIES", "DERIVED", "OPPONENT",
         "NONE", "SCALAR", "UNREF", "PROVISIONAL", "UNCLASS"]


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()[:8]


def report(res, pilot, deck, db, quiet=False):
    counts = {}
    for e in res["entries"]:
        counts[e["verdict"]] = counts.get(e["verdict"], 0) + 1
    if quiet:
        return counts

    nlines = len(open(pilot, encoding="utf-8").read().split("\n"))
    print(f"deck_fit_audit — pilot={pilot} ({nlines}行, md5 {md5(pilot)})  "
          f"deck={deck} ({res['deck_size']}枚, md5 {md5(deck)})")
    print(f"carddb={os.path.relpath(CSV_PATH, os.getcwd()) if os.path.isabs(CSV_PATH) else CSV_PATH}"
          f"  cards={len(db.cards)}  attacks={db.n_attacks} (ピン一致)")
    print("※層0 構造監査(対戦0戦・悉皆・決定的)。勝率も効果量も一切測っていない。\n")

    hdr = f"{'定数':<26} {'行':>5} {'名前空間':<9} {'解決先':<44} {'枚':>4}  判定"
    print(hdr)
    print("-" * 104)
    for e in sorted(res["entries"], key=lambda x: (ORDER.index(e0) if (e0 := x["verdict"]) in ORDER else 99, x["line"])):
        lab = e["resolved"][0]["label"] if e["resolved"] else (
            e.get("detail") or ("派生: テキスト/デッキから導出" if e["verdict"] == "DERIVED" else "—"))
        n = e.get("hits", "")
        print(f"{e['name']:<26} {e['line']:>5} {(e.get('ns') or '—'):<9} "
              f"{lab[:44]:<44} {('x'+str(n)) if n != '' else '—':>4}  {e['verdict']}")
        for r in e["resolved"][1:]:
            print(f"{'':<26} {'':>5} {'':<9} {r['label'][:44]:<44} {'x'+str(r['n']):>4}")
        if e.get("target"):
            t = e["target"]
            print(f"     └ 意図した対象 {t['id']} {t['name']} … x{t['n']}"
                  f"{'(不在)' if not t['n'] else ''}")
        for s in e.get("substitutes", [])[:4]:
            print(f"     └ 共条件を満たす別札: {s['id']} {s['name']} "
                  f"({s['stage']}, 最大ワザコスト{s['max_cost']}) x{s['n']}")
        if e.get("substitutes"):
            print("       → 狙いはここに流れる(挙動は変わるが狙いどおりではない)")
        if e.get("self_hit"):
            print(f"     └ 自デッキ命中: {', '.join(f'{i} {db.name(i)}' for i in e['self_hit'][:6])}")
        if e.get("inert_note"):
            print(f"     └ {e['inert_note']}")
        if e.get("fallback_only"):
            print(f"     └ literal {e['ids']} は except 経路のみ = 通常経路にハードコード無し")
        if e.get("evidence") and e["verdict"] in ("PROVISIONAL", "UNCLASS"):
            print(f"     └ 推論根拠 {pilot}:{e['evidence']['line']} `{e['evidence']['src']}`")
        if e.get("provisional_as"):
            print(f"     └ 射程の注釈が無い。自陣前提なら {e['provisional_as']}")
    print()

    dv = [e for e in res["entries"] if e["verdict"] == "DERIVED"]
    print(f"派生(ハードコード無しの良い形) {len(dv)}件: "
          f"{', '.join(e['name'] for e in dv) if dv else 'なし'}")
    if res["calib"]:
        print("較正定数(助言のみ・因果の主張ではない):")
        for c in res["calib"]:
            print(f"  {pilot}:{c['line']} {c['label']} = {c['value']}   較正元 {c['calibrated_on']}")
            print(f"     proxy deck_burn={res['proxies']['deck_burn']} / "
                  f"hand_scaling_attack={res['proxies']['hand_scaling_attack']}")
    print()
    print("  ".join(f"{k}={counts.get(k,0)}" for k in ORDER if counts.get(k)))
    print()
    print("注意: 判定はASTの使用箇所推論であり意味的正しさを保証しない。")
    print("      MISFIRING は『狙いが外れている』の証拠であって『有害』の証拠ではない")
    print("      (効果量は bench.py / cew.py でしか出ない)。envの旗・到達不能分岐は見ていない。")
    print("      ATTACK判定を引用する前に attackid_crosscheck.py を1回走らせること。")
    for k in ORDER:
        print(f"{k}={counts.get(k, 0)}")
    verdict = ("UNCLASSIFIED" if counts.get("UNCLASS") else
               "MISFIRE" if counts.get("MISFIRING") else
               "DEAD_CRUST" if counts.get("DEAD") else "OK")
    print(f"VERDICT={verdict}")
    print("DECK_FIT_JSON=" + json.dumps({
        "pilot": pilot, "pilot_md5": md5(pilot), "deck_md5": md5(deck),
        "cards": len(db.cards), "attacks": db.n_attacks,
        "counts": counts, "verdict": verdict,
        "entries": [{k: v for k, v in e.items() if k != "shape"} for e in res["entries"]],
        "calib": res["calib"], "proxies": res["proxies"],
    }, ensure_ascii=False))
    return counts


# --------------------------------------------------------------------------
# --all / --selftest
# --------------------------------------------------------------------------
def deck_dirs():
    out = []
    if not os.path.isdir(DECKS_ROOT):
        return out
    for d in sorted(os.listdir(DECKS_ROOT)):
        p = os.path.join(DECKS_ROOT, d)
        if os.path.isfile(os.path.join(p, "main.py")) \
                and os.path.isfile(os.path.join(p, "deck.csv")):
            out.append((d, p))
    return out


def run_all(db):
    dirs = deck_dirs()
    rows, agg = [], {}
    pilots, decks = set(), set()
    for name, p in dirs:
        pilot = os.path.join(p, "main.py")
        deck = os.path.join(p, "deck.csv")
        pilots.add(md5(pilot))
        decks.add(md5(deck))
        res = audit(pilot, deck, db)
        by = {e["name"]: e["verdict"] for e in res["entries"]}
        c = {}
        for e in res["entries"]:
            c[e["verdict"]] = c.get(e["verdict"], 0) + 1
        for k, v in c.items():
            agg[k] = agg.get(k, 0) + v
        rows.append((name, by, c, md5(pilot)))

    print(f"deck_fit_audit --all : {len(dirs)}dir / {len(pilots)}種のpilot / "
          f"{len(decks)}種のdeck  (対戦0戦)")
    print("※層0 構造監査。勝率も効果量も測っていない。\n")
    w = 31
    print(f"{'dir':<{w}} " + " ".join(f"{t.replace('_',''):<10}" for t in TRACKED)
          + f" {'APP':>4}{'DEAD':>5}{'MIS':>4}{'DERI':>5}{'UNREF':>6}{'UNCL':>5}")
    print("-" * (w + 1 + 11 * len(TRACKED) + 29))
    cells = {}
    for name, by, c, _ in rows:
        line = f"{name[:w]:<{w}} "
        for t in TRACKED:
            v = by.get(t, "—")
            cells[v] = cells.get(v, 0) + 1
            line += f"{v[:10]:<10} "
        line += (f"{c.get('APPLIES',0):>4}{c.get('DEAD',0):>5}{c.get('MISFIRING',0):>4}"
                 f"{c.get('DERIVED',0):>5}{c.get('UNREF',0):>6}{c.get('UNCLASS',0):>5}")
        print(line)
    print("-" * (w + 1 + 11 * len(TRACKED) + 29))
    tracked_cells = sum(v for k, v in cells.items() if k != "—")
    app = cells.get("APPLIES", 0)
    dead = cells.get("DEAD", 0) + cells.get("INERT", 0)
    mis = cells.get("MISFIRING", 0)
    print(f"追跡定数 {len(TRACKED)}本 × {len(dirs)}dir = {len(TRACKED)*len(dirs)}セル "
          f"(宣言あり {tracked_cells}): APPLIES={app}  DEAD/INERT={dead}  MISFIRING={mis}")
    if tracked_cells:
        print(f"→ ハードコード表のセルの {100*dead/tracked_cells:.0f}% は、そのデッキでは到達しない。")
    print()
    print("  ".join(f"{k}={agg.get(k,0)}" for k in ORDER if agg.get(k)))

    # 未分類がどこに溜まっているかを明示する。「全体で17件」だけ出すと、
    # 自陣のdirが汚れているように読めてしまう(実際は他人のコード1本に集中している)。
    residue = sorted(((n, c.get("UNCLASS", 0) + c.get("PROVISIONAL", 0))
                      for n, _, c, _ in rows if c.get("UNCLASS") or c.get("PROVISIONAL")),
                     key=lambda x: -x[1])
    ours = [(n, v) for n, v in residue if n != "mega-starmie-ex-deck"]
    if residue:
        print(f"未分類(UNCLASS+PROVISIONAL) {sum(v for _, v in residue)}件の所在: "
              + ", ".join(f"{n} {v}" for n, v in residue[:6]))
        if not ours:
            print("  → 全て mega-starmie-ex-deck (D35: りょーちんのdir、読むだけ) に集中。"
                  "**我々の全dirは完全に分類済み** = --strict を提出前ゲートに使える。")
    print("DECK_FIT_MATRIX_JSON=" + json.dumps({
        "dirs": len(dirs), "pilots": len(pilots), "decks": len(decks),
        "tracked": TRACKED, "tracked_cells": tracked_cells,
        "APPLIES": app, "DEAD_INERT": dead, "MISFIRING": mis,
        "agg": agg, "residue": dict(residue),
        "per_dir": {n: c for n, _, c, _ in rows},
    }, ensure_ascii=False))
    agg["_per_dir"] = {n: c for n, _, c, _ in rows}
    return agg


SELFTEST = [
    # (dir, 定数, 期待判定, 期待の枚数)
    ("deckswap-honchkrow", "_IGNITION_ID", "MISFIRING", 4),
    ("deckswap-crustle", "_IGNITION_ID", "DEAD", 0),
    ("deckswap-garchomp", "_IGNITION_ID", "DEAD", 0),
    ("deckswap-grimmsnarl", "_IGNITION_ID", "DEAD", 0),
    ("deckswap-tarountula", "_IGNITION_ID", "DEAD", 0),
    ("deckswap-tarountula-sweep", "_IGNITION_ID", "DEAD", 0),
    ("dragapult-calib", "_IGNITION_ID", "DEAD", 0),
    ("lucario-calib", "_IGNITION_ID", "DEAD", 0),
    ("starmie-aggro", "_IGNITION_ID", "APPLIES", 4),
    # ワザ1488(Nebula Beam)は 1031 Mega Starmie ex が所有。同dirは 1031 を4枚積む
    # (`grep -cx '1031,\?' deck.csv` = 4 で独立確認)。ワザIDが所有カードに解決できている証拠。
    ("starmie-aggro", "_EFFECT_IGNORING_ATTACKS", "APPLIES", 4),
]
# 初回走行で必ず出るはずの UNREF(出なければ解析器が壊れている)
SELFTEST_UNREF = [
    ("starmie-aqua", "_MEGA_STARMIE_ID"),
    ("starmie-aqua", "_NEBULA_BEAM_ID"),
    ("starmie-mastercontrol", "_MEGA_STARMIE_ID"),
]


def run_selftest(db):
    bad = []
    cache = {}

    def get(d):
        if d not in cache:
            p = os.path.join(DECKS_ROOT, d)
            cache[d] = audit(os.path.join(p, "main.py"),
                             os.path.join(p, "deck.csv"), db)
        return cache[d]

    print("deck_fit_audit --selftest — 既知の真値")
    for d, const, want, want_n in SELFTEST:
        res = get(d)
        e = next((x for x in res["entries"] if x["name"] == const), None)
        got = e["verdict"] if e else "MISSING"
        gotn = e.get("hits") if e else None
        ok = got == want and (want_n is None or gotn == want_n)
        print(f"  [{'OK ' if ok else 'NG '}] {d:<28} {const:<26} "
              f"判定={got:<10} 枚数={gotn} (期待 {want}/{want_n})")
        if not ok:
            bad.append((d, const, want, want_n, got, gotn))
    print("  -- 未参照定数(コードが実装していない意図を記述している状態) --")
    for d, const in SELFTEST_UNREF:
        res = get(d)
        e = next((x for x in res["entries"] if x["name"] == const), None)
        got = e["verdict"] if e else "MISSING"
        ok = got == "UNREF"
        print(f"  [{'OK ' if ok else 'NG '}] {d:<28} {const:<26} 判定={got} (期待 UNREF)")
        if not ok:
            bad.append((d, const, "UNREF", None, got, None))

    # クローン不変検査: 同一md5のpilotはコード由来フィールドが一致するはず
    groups = {}
    for name, p in deck_dirs():
        groups.setdefault(md5(os.path.join(p, "main.py")), []).append((name, p))
    clone_bad = []
    for h, members in groups.items():
        if len(members) < 2:
            continue
        sigs = {}
        for name, p in members:
            res = audit(os.path.join(p, "main.py"), os.path.join(p, "deck.csv"), db)
            sig = json.dumps([[e["name"], e["line"], e.get("ns"), e.get("scope")]
                              for e in res["entries"]], ensure_ascii=False)
            sigs.setdefault(sig, []).append(name)
        status = "OK " if len(sigs) == 1 else "NG "
        print(f"  [{status}] クローン不変 md5 {h}: {len(members)}dir → "
              f"コード由来フィールドの型 {len(sigs)}種")
        if len(sigs) != 1:
            clone_bad.append(h)
    bad += [("clone", h, "1種", None, "複数", None) for h in clone_bad]

    print()
    print(f"SELFTEST_CASES={len(SELFTEST)+len(SELFTEST_UNREF)}")
    print(f"SELFTEST_FAIL={len(bad)}")
    print(f"VERDICT={'PASS' if not bad else 'FAIL'}")
    return len(bad)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default="main.py")
    ap.add_argument("--deck", default="deck.csv")
    ap.add_argument("--all", action="store_true", help="全デッキdirの行列")
    ap.add_argument("--selftest", action="store_true", help="既知の真値を検査")
    ap.add_argument("--strict", action="store_true",
                    help="UNCLASS / PROVISIONAL があれば exit 1(定数追加の番犬)")
    args = ap.parse_args()

    db = CardDB()
    pins = db.check_pins()
    if pins:
        sys.exit("ワザID通番の導出が無効化された — " + " / ".join(pins) +
                 "\n  ATTACK判定を信用する前に verification/attackid_crosscheck.py を"
                 "エンジンに対して走らせること。")

    if args.selftest:
        sys.exit(1 if run_selftest(db) else 0)
    if args.all:
        agg = run_all(db)
        if args.strict:
            # 我々が保守していない dir は番犬の対象外にする。ただし**黙って外さない**
            # (playbook: 覆域を絞ったら必ず log する。黙った切り捨ては「全部見た」と読まれる)。
            skipped = {d: c for d, c in agg.get("_per_dir", {}).items()
                       if d in STRICT_EXEMPT and (c.get("UNCLASS") or c.get("PROVISIONAL"))}
            for d, c in sorted(skipped.items()):
                print(f"--strict 対象外: {d} "
                      f"(UNCLASS={c.get('UNCLASS',0)} PROVISIONAL={c.get('PROVISIONAL',0)}) "
                      f"— {STRICT_EXEMPT[d]}")
            residue = sum(c.get("UNCLASS", 0) + c.get("PROVISIONAL", 0)
                          for d, c in agg.get("_per_dir", {}).items()
                          if d not in STRICT_EXEMPT)
            print(f"STRICT_RESIDUE={residue}  STRICT_EXEMPT_DIRS={len(skipped)}")
            sys.exit(1 if residue else 0)
        return

    for p in (args.pilot, args.deck):
        if not os.path.exists(p):
            sys.exit(f"見つからない: {p}(デッキディレクトリから実行するか --pilot/--deck を渡す)")
    res = audit(args.pilot, args.deck, db)
    counts = report(res, args.pilot, args.deck, db)
    if args.strict and (counts.get("UNCLASS") or counts.get("PROVISIONAL")):
        sys.exit(1)


if __name__ == "__main__":
    main()

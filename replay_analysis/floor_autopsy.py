#!/usr/bin/env python3
"""床の対面(メガルカリオ/ブリジュラス)の機構検死 — 層S。

**層S(スクリーニング/機構診断)。出力は標的選定にのみ使う。**
効果量の判定・ゲート充足の宣言・記事本文には使わない(README.md:57 / D51-訂正)。

背景(2026-08-08 の族外4面):
  フーディン 94.0% / イワパレス 97.5% / **メガルカリオ 19.0%** / **ブリジュラス 12.5%**
  床の2セルが合成重みの36%を占め、ここだけに MDE(2.67pt)を超える伸びしろが残っている。

検証する仮説 H1:
  エネ貼りの価値付け `_best_attack_damage_of_card` は**カード単体の値しか見ず、相手の弱点を
  通さない**。対メガルカリオでは ミュウツーex の実効打点は 320〜560(弱点×2)なのに、
  貼り先キーには 160 としか映らない。結果、ミュウツーがオンラインにならないまま負ける。

  ★エンジンで確認済み: Mega Lucario ex(678) weakness=5, Mewtwo ex(431) energyType=5
    → 弱点が乗る。Erasure Ball 160→320、ベンチのエネ1枚トラッシュで 220→440。
      Mega Lucario は HP340(ヒーローマント込み440)なので **一撃KO圏**。

  対照的に Archaludon ex(190) は weakness=2(炎)・抵抗【草】。我々に弱点は無く、
  むしろ主砲ロケットラッシュ(草)が −30 される。**こちらは構造的かもしれない** — 分けて測る。

kill基準(計画 §4.4、先に固定):
  敗戦のうち「ミュウツーが3エネに到達しなかった試合」が **≥70%** → 律速は上流=修理可能
  ミュウツーが **≥70%** の試合でオンラインなのに負けている       → 構造的。介入しない
  中間・機構が立たない                                          → 介入しない

使い方:
  python3 replay_analysis/floor_autopsy.py <epsDir> <自デッキcsv> [対面名...]
  例:
    python3 replay_analysis/floor_autopsy.py replay_analysis/eps55308422 \\
        src/input/datasets/decks/deckswap-tarountula-pilotfix/deck.csv Lucario Archaludon

チーム内対戦とバリデーション自己対戦は、両席のデッキ重なりで自動除外する
(probe_autopsy.py と違い ListEpisodes を叩かない = 完全ローカル・playbook §8 に抵触しない)。
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# probe_autopsy.py の RULES を継承(先勝ち)。
RULES = [
    ("Lucario", ["Mega Lucario ex"]),
    ("Archaludon", ["Archaludon ex"]),
    ("Abomasnow", ["Mega Abomasnow ex"]),
    ("Wall(Crustle/GreatTusk)", ["Crustle"]),
    ("StarmieMirror", ["Mega Starmie ex"]),
    ("Alakazam", ["Alakazam"]),
    ("Grimmsnarl", ["Marnie's Grimmsnarl ex"]),
    ("Dragapult", ["Dragapult ex"]),
    ("TR Mewtwo", ["Team Rocket's Mewtwo ex"]),
    ("Kangaskhan", ["Mega Kangaskhan ex"]),
    ("Garchomp", ["Cynthia's Garchomp ex", "Garchomp ex"]),
]

MEWTWO = 431
ERASURE_BALL = 608
# エネの型コード(リプレイの players[].active/bench[].energies は「払える単位」の列)。
# 2026-08-09 実測: 1=草, 5=超, 7=悪, 11=ロケット団エネ(1枚で 2 単位ぶん列に入る)。
PSYCHIC_CAPABLE = {5, 11}          # イレイザーボールの {P}{P} を払えるのはこの2つだけ
ERASURE_COST_UNITS, ERASURE_PSYCHIC = 3, 2   # cost=[5,5,0] → 総3単位・うち超2単位


def erasure_payable(energies) -> bool:
    """イレイザーボール(608)が実際に撃てるエネが乗っているか。

    単位数だけを数えると**基本草エネ3枚でも「3エネ到達」と誤判定する**。
    実測(2026-08-09)では ミュウツーに草が乗っている状態が最頻(853観測)だったので、
    型を見ないと機構の判定を誤る。
    """
    e = list(energies or [])
    return len(e) >= ERASURE_COST_UNITS and sum(1 for x in e if x in PSYCHIC_CAPABLE) >= ERASURE_PSYCHIC
# 攻撃ID → 表示名(エンジンの _card_db から採取。mechanism_autopsy.py と同じく ATTACK ログ type=15)
ATK_NAMES = {
    560: "ロケットラッシュ(ワナイダー)", 608: "★イレイザーボール(ミュウツーex)",
    609: "ロケットミラー(ソーナンス)", 610: "とびだしヘッド(ソーナンス)",
    652: "たぶらかす(ヤミカラス)", 653: "いちゃもん(ヤミカラス)",
    559: "たね殴り(タマンチュラ)", 583: "ダークフロスト(フリーザー)",
    982: "はどうづき(メガルカリオ 130)", 983: "メガブレイブ(メガルカリオ 270)",
    253: "メタルディフェンダー(ブリジュラス 220)",
    153: "ジェットヘッド(ドラパルト)", 154: "ファントムダイブ(ドラパルト 200)",
}
ATTACK, MOVE_CARD = 15, 6
AREA_ACTIVE, AREA_BENCH, AREA_DISCARD = 4, 5, 3


def load_names():
    """cardId -> (名前, ポケモンか)。probe_autopsy.load_names と同じ。"""
    out = {}
    with open(REPO / "verification/data/EN_Card_Data.csv") as f:
        for r in csv.DictReader(f):
            st = r["Stage (Pokémon)/Type (Energy and Trainer)"] or ""
            out[int(r["Card ID"])] = (r["Card Name"], "Pokémon" in st)
    return out


def classify(opp_deck, names):
    lineup = {}
    for cid, n in opp_deck.items():
        nm, isp = names.get(cid, ("?", False))
        if isp:
            lineup[nm] = lineup.get(nm, 0) + n
    lab = next((lab for lab, keys in RULES if any(k in lineup for k in keys)), None)
    if lab is None:
        top = sorted(lineup.items(), key=lambda kv: -kv[1])
        lab = "Other:" + (top[0][0] if top else "?")
    return lab


def walk_logs(steps):
    """両ビューを (playerIndex, log) の列にする。

    ログは差分で出る(累積ではない)ので `logs == prev` の重複除去が必須
    — mechanism_autopsy.py:61 と同じ型。片方のビューには終局イベントが
    現れないことがあるため、両ビューを走査して serial で重複排除する。
    """
    seen, out = set(), []
    for step in steps:
        for view in step:
            o = view.get("observation") or {}
            for L in (o.get("logs") or []):
                key = (L.get("serial"), L.get("type"), L.get("cardId"),
                       L.get("playerIndex"), L.get("fromArea"), L.get("toArea"),
                       L.get("attackId"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(L)
    return out


def analyse_game(d, ours, names):
    """1試合 → 機構の指標。自席が同定できない/自己対戦なら None。"""
    decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
    if len(decks) < 2:
        return None
    ov = [sum((ours & x).values()) for x in decks]
    if min(ov) >= 40:            # 両席とも我々のデッキ = バリデーション自己対戦
        return None
    if max(ov) < 40:             # 自席が同定できない
        return None
    mine = 0 if ov[0] >= ov[1] else 1
    label = classify(decks[1 - mine], names)

    r = {"label": label, "reward": (d.get("rewards") or [None, None])[mine],
         "our_atk": Counter(), "opp_atk": Counter(),
         "mewtwo_max_e": 0, "mewtwo_e3_turn": None, "mewtwo_seen": False,
         "mewtwo_pay_turn": None, "mewtwo_grass_only": 0,
         "mewtwo_active_turns": set(), "mewtwo_e3_active_turns": set(),
         "tr_max": 0, "our_ko_active": 0, "our_ko_bench": 0, "turns": 0}

    for L in walk_logs(d["steps"]):
        t = L.get("type")
        if t == ATTACK:
            (r["our_atk"] if L.get("playerIndex") == mine else r["opp_atk"])[L.get("attackId")] += 1
        elif t == MOVE_CARD and L.get("playerIndex") == mine and L.get("toArea") == AREA_DISCARD:
            cid = L.get("cardId")
            if names.get(cid, ("", False))[1]:      # ポケモンだけ数える
                if L.get("fromArea") == AREA_ACTIVE:
                    r["our_ko_active"] += 1
                elif L.get("fromArea") == AREA_BENCH:
                    r["our_ko_bench"] += 1

    # 盤面の走査: 自席視点の current だけを見る
    for step in d["steps"]:
        for view in step:
            cur = (view.get("observation") or {}).get("current")
            if not cur or cur.get("yourIndex") != mine:
                continue
            me = cur["players"][mine] or {}
            # ベンチには空スロットの None が入りうる(2026-08-09: 47戦中32戦がこれで落ちていた)
            act = [p for p in (me.get("active") or []) if p]
            bench = [p for p in (me.get("bench") or []) if p]
            turn = cur.get("turn") or 0
            r["turns"] = max(r["turns"], turn)
            tr = sum(1 for p in act + bench
                     if names.get(p.get("id"), ("", False))[0].startswith("Team Rocket's"))
            r["tr_max"] = max(r["tr_max"], tr)
            for p in act + bench:
                if p.get("id") != MEWTWO:
                    continue
                r["mewtwo_seen"] = True
                en = list(p.get("energies") or [])
                r["mewtwo_max_e"] = max(r["mewtwo_max_e"], len(en))
                if len(en) >= 3 and r["mewtwo_e3_turn"] is None:
                    r["mewtwo_e3_turn"] = turn
                if erasure_payable(en) and r["mewtwo_pay_turn"] is None:
                    r["mewtwo_pay_turn"] = turn
                # 型が合わないエネ(草だけ)が乗っている観測 = 貼り先評価の誤り候補
                if en and not any(x in PSYCHIC_CAPABLE for x in en):
                    r["mewtwo_grass_only"] += 1
            for p in act:
                if p.get("id") == MEWTWO:
                    r["mewtwo_active_turns"].add(turn)
                    if erasure_payable(p.get("energies")):
                        r["mewtwo_e3_active_turns"].add(turn)
    return r


def main(eps_dir, deck_csv, targets):
    names = load_names()
    ours = Counter(int(l) for l in open(deck_csv) if l.strip())
    games = []
    for f in sorted(Path(eps_dir).glob("ep*.json")):
        try:
            g = analyse_game(json.loads(f.read_text()), ours, names)
        except Exception as e:                       # 壊れたリプレイは飛ばして続行
            print(f"  ! skip {f.name}: {type(e).__name__} {e}", file=sys.stderr)
            continue
        if g:
            g["ep"] = f.stem
            games.append(g)

    print("### 層S(スクリーニング/機構診断) — 引用禁止。標的選定にのみ使う。")
    print(f"# floor autopsy  eps={eps_dir}  deck={deck_csv}")
    print(f"解析できた試合 {len(games)} (自己対戦/同定不能は除外)")
    census = Counter(g["label"] for g in games)
    print("対面分布:", ", ".join(f"{k} {v}" for k, v in census.most_common()))

    for tgt in targets:
        sub = [g for g in games if g["label"] == tgt]
        if not sub:
            print(f"\n=== {tgt}: 該当なし ===")
            continue
        w = sum(1 for g in sub if g["reward"] == 1)
        losses = [g for g in sub if g["reward"] != 1]
        print(f"\n=== {tgt}  {w}-{len(sub)-w}  (n={len(sub)}) ===")
        print(f"{'ep':<12}{'結果':>4}{'手数':>5}{'自攻':>5}{'相攻':>5}"
              f"{'Mew最大E':>9}{'払える手':>9}{'Mew場':>6}{'撃てる場':>9}"
              f"{'草のみ':>7}{'TR最大':>7}{'被KO':>6}")
        for g in sorted(sub, key=lambda x: x["ep"]):
            n_our = sum(g["our_atk"].values())
            n_opp = sum(g["opp_atk"].values())
            pay = g["mewtwo_pay_turn"]
            ko = f"{g['our_ko_active']}/{g['our_ko_bench']}"
            print(f"{g['ep']:<12}{'W' if g['reward'] == 1 else 'L':>4}{g['turns']:>5}"
                  f"{n_our:>5}{n_opp:>5}{g['mewtwo_max_e']:>9}"
                  f"{(pay if pay is not None else '-'):>9}{len(g['mewtwo_active_turns']):>6}"
                  f"{len(g['mewtwo_e3_active_turns']):>9}{g['mewtwo_grass_only']:>7}"
                  f"{g['tr_max']:>7}{ko:>6}")

        # ★kill基準の判定材料
        n_l = len(losses)
        never_pay = sum(1 for g in losses if g["mewtwo_pay_turn"] is None)
        never_seen = sum(1 for g in losses if not g["mewtwo_seen"])
        eb = sum(g["our_atk"].get(ERASURE_BALL, 0) for g in sub)
        pay_all = sum(1 for g in sub if g["mewtwo_pay_turn"] is not None)
        grass = sum(g["mewtwo_grass_only"] for g in sub)
        print(f"\n  自攻撃/戦 {sum(sum(g['our_atk'].values()) for g in sub)/len(sub):.2f}"
              f"   相手攻撃/戦 {sum(sum(g['opp_atk'].values()) for g in sub)/len(sub):.2f}")
        print(f"  イレイザーボール(608) 総使用 {eb} 回 = {eb/len(sub):.2f}回/戦")
        print(f"  全 {len(sub)} 戦中、ミュウツーが**実際に撃てるエネ**を積めた試合 = {pay_all} "
              f"({100*pay_all/len(sub):.0f}%)   型違いエネのみ(草だけ)の観測 {grass}")
        if n_l:
            print(f"  ★敗戦 {n_l} 件のうち 撃てるエネに未到達 = {never_pay} "
                  f"({100*never_pay/n_l:.0f}%)  / 場に一度も出なかった = {never_seen} "
                  f"({100*never_seen/n_l:.0f}%)")
            verdict = ("律速は上流=修理可能" if never_pay / n_l >= 0.70 else
                       "構造的の疑い" if never_pay / n_l <= 0.30 else "中間=介入しない")
            print(f"  → kill基準の読み: {verdict}")
        print("  自分の攻撃内訳: " + ", ".join(
            f"{ATK_NAMES.get(k, k)} {v}" for k, v in
            sorted(sum((g["our_atk"] for g in sub), Counter()).most_common())))
        print("  相手の攻撃内訳: " + ", ".join(
            f"{ATK_NAMES.get(k, k)} {v}" for k, v in
            sum((g["opp_atk"] for g in sub), Counter()).most_common()))
        ko_a = sum(g["our_ko_active"] for g in sub)
        ko_b = sum(g["our_ko_bench"] for g in sub)
        print(f"  我々の被KO: バトル場 {ko_a} / ベンチ {ko_b}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2],
         sys.argv[3:] if len(sys.argv) > 3 else ["Lucario", "Archaludon"])

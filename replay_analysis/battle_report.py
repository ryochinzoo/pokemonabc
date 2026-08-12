#!/usr/bin/env python3
"""1試合のリプレイを「講評できる形」の Markdown にする。

**既存の trace_replay.py との違い**: あちらは「何が起きたか」を並べる。
こちらは各決定点で **「そのとき何が選べたか」** を復元して、選んだ手と並べる。

    手番12 / 我々 / 手札7枚 / 相手アクティブ Mega Lucario ex HP 90/280
      選べた手 9個:
        1. PLAY Team Rocket's Ariana
        2. ATTACH Basic {G} Energy → Team Rocket's Spidops
        ...
        9. ATTACK Rocket Rush (attackId 560)
      **選んだ = 2番**

これが無いと「なぜこれを出したのか」「他にこれがあったのに」という講評が
そもそも成立しない。盤面・手札・状態異常・「今ターンもうエネを付けたか」まで
リプレイに全部入っている(2026-08-10確認)ので、足りないのは**描き出し方**だけだった。

**LLMは読みの計算をしない**。この資料でできるのは「見落としの指摘」と「仮説出し」まで。
「Xを出していれば勝てた」は**仮説**であって、検証はローカルのエンジンで行うこと。

**選んだ手の対応規則（2026-08-11 に確定。134譜4,593決定で 99.9%）**

    選択肢   steps[N].observation.select.option
    その答え steps[N+1].action                    ← **1step 遅れて記録される**
    結果ログ steps[N+1].observation.logs

`steps[N].action` を使うと 29% しか当たらない。**行動と、その結果のログは、
どちらも次のstepに一緒に記録される**(提示は N、応答は N+1)。
kaggle-coach スキルが言う「リプレイの selected の off-by-one」の正体がこれ。

導き方: エンジンのログ(PLAY=10 / ATTACH=11 は cardId を持つ)を正解として、
「そのカードを出せる選択肢」が一意に定まる決定だけを集め、action の取得位置を
2次元で総当たりした。N+1 だけが 100% になった。

`option.index` = 手札の位置は**正しい**(型整合 7,510件で破綻0)。
2026-08-10 に「index が誤り」と判断したのは、検証side(手札から消えたカードとの照合)が
壊れていたため。**推測で検証してはいけない典型例**として data.md に残してある。

    python3 replay_analysis/battle_report.py <replay.json> [--out out.md] [--seat 0]
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CARDS = REPO / "verification/data/EN_Card_Data.csv"
API = REPO / "src/input/datasets/decks/deckswap-tarountula-pilotfix/cg/api.py"

AREA = {1: "山札", 2: "手札", 3: "トラッシュ", 4: "バトル場", 5: "ベンチ", 6: "サイド",
        7: "スタジアム", 8: "エネルギー", 9: "どうぐ", 10: "進化前", 11: "プレイヤー",
        12: "確認中"}


def _enum_from_api(name):
    """api.py から実際の列挙を読む。

    CLAUDE.md の「列挙は競技中に増えうる。網羅を仮定するな」に対応して、
    ここにハードコードせず**原本から読む**。読めなければ空 = 未知は数値で出す。
    """
    try:
        s = API.read_text()
        i = s.index(f"class {name}(IntEnum):")
    except (OSError, ValueError):
        return {}
    out = {}
    for ln in s[i:i + 3000].split("\n")[1:]:
        m = re.match(r"\s+([A-Z_]+)\s*=\s*(\d+)", ln)
        if m:
            out[int(m.group(2))] = m.group(1)
        elif ln.strip().startswith("class "):
            break
    return out


OPT = _enum_from_api("OptionType")
SELT = _enum_from_api("SelectType")
CTX = _enum_from_api("SelectContext")


def load_names():
    out = {}
    with open(CARDS) as f:
        for r in csv.DictReader(f):
            out[int(r["Card ID"])] = r["Card Name"]
    return out


NAMES = load_names()


def cname(cid):
    return NAMES.get(cid, f"(ID {cid})") if cid is not None else None


def _at(me, area, idx):
    """場所+添字を実際のカード名に解決する。

    ここが要。選択肢は `{"index": 4, "type": PLAY}` のように**添字しか持たない**ので、
    盤面に照合しないと「PLAY」としか書けず、講評の材料にならない。
    PLAY(type 7)は area を持たないが**暗黙で手札**。
    """
    if idx is None:
        return None
    pool = {2: me.get("hand"), 4: me.get("active"), 5: me.get("bench"),
            3: me.get("discard"), 6: me.get("prize")}.get(area)
    if not isinstance(pool, list) or not (0 <= idx < len(pool)):
        return None
    c = pool[idx]
    return cname(c.get("id")) if isinstance(c, dict) else None


def describe(op, me=None):
    """1つの選択肢を人が読める1行にする。盤面を渡すと添字をカード名に解決する。"""
    t = op.get("type")
    tn = OPT.get(t, f"TYPE{t}")
    me = me or {}
    bits = []
    if op.get("cardId") is not None:
        bits.append(cname(op["cardId"]))
    # PLAY は area を省略する＝暗黙で手札。それ以外は area に従う。
    nm = _at(me, op.get("area", 2 if t == 7 else None), op.get("index"))
    if nm:
        bits.append(nm)
    elif op.get("area") is not None:
        bits.append(f"[{AREA.get(op['area'], op['area'])}:{op.get('index')}]")
    if op.get("attackId") is not None:
        bits.append(f"わざ#{op['attackId']}")
    if op.get("inPlayArea") is not None:
        tgt = _at(me, op["inPlayArea"], op.get("inPlayIndex"))
        loc = AREA.get(op["inPlayArea"], op["inPlayArea"])
        bits.append(f"→ {loc}の{tgt}" if tgt else f"→ {loc}:{op.get('inPlayIndex')}")
    if op.get("number") is not None:
        bits.append(f"数={op['number']}")
    return f"{tn} " + " ".join(b for b in bits if b) if bits else tn


def poke(p):
    """バトル場のポケモンを1行に。

    バトル場が空(相手の視点では見えない/気絶直後)だと `active` が `[None]` や
    `[]` になる。リストの中身が None のケースがあるので両方弾く。
    """
    if not p:
        return "—"
    c = p[0] if isinstance(p, list) else p
    if not isinstance(c, dict):
        return "—"
    nm = cname(c.get("id"))
    en = len(c.get("energies") or [])
    tl = len(c.get("tools") or [])
    return (f"{nm} HP{c.get('hp')}/{c.get('maxHp')}"
            + (f" エネ{en}" if en else "") + (f" どうぐ{tl}" if tl else ""))


def build(path, seat=None):
    d = json.loads(Path(path).read_text())
    info = d.get("info") or {}
    ep = info.get("EpisodeId", "?")
    rewards = d.get("rewards") or []
    steps = d["steps"]

    L = []
    A = L.append
    A(f"# 対戦ログ（講評用） — エピソード {ep}")
    A("")
    A(f"- 結果: rewards={rewards}（席0視点で 1=勝ち / -1=負け）")
    A("- 各決定点に **その瞬間に合法だった手の一覧** と **実際に選んだ手** を並べてある。")
    A("- 「なぜこれを選んだのか」「他にこれがあったのに」を検討するための資料。")
    A("")
    A("**この資料の限界**: ここに載っているのは*選べた手*であって*最善手*ではない。")
    A("最善手の判定には読み（探索）が要る。指摘は仮説として扱い、")
    A("採否はローカルのエンジンでの実測で決めること。")
    A("")

    ndec = 0
    for si, st in enumerate(steps):
        for ai, a in enumerate(st):
            if seat is not None and ai != seat:
                continue
            # **`status == "ACTIVE"` でしか判定できない**(2026-08-10に踏んだ):
            # 手番でない側にも observation が入っており、しかも
            # `select.option` が1個ある&`yourIndex` は自分の席番号のまま。
            # つまり「見た目は決定点」だが実体は前の観測の残骸で、`action` は `[]`。
            # yourIndex で絞ると**決定数が倍**になり、「選んだ手」も全部空になる。
            if a.get("status") != "ACTIVE":
                continue
            o = a.get("observation") or {}
            sel = o.get("select")
            # 応答は次のstepに記録される(このファイル冒頭の対応規則)。
            act = (steps[si + 1][ai].get("action") if si + 1 < len(steps) else None)
            if not sel or not sel.get("option"):
                continue
            cur = o.get("current") or {}
            ndec += 1
            me = (cur.get("players") or [{}, {}])[ai] if cur.get("players") else {}
            foe = (cur.get("players") or [{}, {}])[1 - ai] if cur.get("players") else {}
            stn = SELT.get(sel.get("type"), sel.get("type"))
            ctxn = CTX.get(sel.get("context"), sel.get("context"))

            A(f"## 決定 {ndec}（手番 {cur.get('turn')} / 席{ai} / step {si}）")
            A("")
            A(f"- 場面: **{stn}**" + (f" / {ctxn}" if ctxn is not None else "")
              + f"（{sel.get('minCount')}〜{sel.get('maxCount')}個選ぶ）")
            A(f"- 自分: {poke(me.get('active'))}　ベンチ{len(me.get('bench') or [])}体"
              f"　手札{me.get('handCount')}枚　山{me.get('deckCount')}枚"
              f"　サイド{len(me.get('prize') or [])}枚")
            A(f"- 相手: {poke(foe.get('active'))}　ベンチ{len(foe.get('bench') or [])}体"
              f"　手札{foe.get('handCount')}枚　サイド{len(foe.get('prize') or [])}枚")
            flags = [lab for k, lab in (("energyAttached", "エネ付与済"),
                                        ("supporterPlayed", "サポート使用済"),
                                        ("retreated", "にげる済"),
                                        ("stadiumPlayed", "スタジアム出し済"))
                     if cur.get(k)]
            if flags:
                A(f"- このターン既に: {', '.join(flags)}")
            cond = [lab for k, lab in (("asleep", "ねむり"), ("confused", "こんらん"),
                                       ("paralyzed", "まひ"), ("poisoned", "どく"),
                                       ("burned", "やけど")) if me.get(k)]
            if cond:
                A(f"- 自分の状態異常: {', '.join(cond)}")
            hand = me.get("hand") or []
            if hand:
                A(f"- 手札: {', '.join(cname(c.get('id')) for c in hand)}")
            A("")
            opts = sel["option"]
            A(f"**選べた手 {len(opts)}個:**")
            A("")
            chosen = set(act if isinstance(act, list) else [])
            for i, op in enumerate(opts):
                mark = " ← **選んだ**" if i in chosen else ""
                A(f"{i}. {describe(op, me)}{mark}")
            A("")
    A(f"\n---\n\n合計 {ndec} 決定。")
    return "\n".join(L), ndec


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    seat = None
    if "--seat" in sys.argv:
        seat = int(sys.argv[sys.argv.index("--seat") + 1])
    text, n = build(args[0], seat)
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else str(Path(args[0]).with_suffix(".report.md")))
    Path(out).write_text(text)
    print(f"生成: {out}  ({len(text)/1024:.0f} KB / {n} 決定)")

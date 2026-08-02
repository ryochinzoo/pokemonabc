#!/usr/bin/env python3
"""完封試合の解剖(測定専用): サイド0で負けた試合/相手を0に抑えた試合の立ち上がり比較。

問い: 敗北30戦のうち我々のサイド取得0の7戦は「押し負け」か「立ち上がり不成立」か。
マリガン・初手たね・Mega着地ターン・試合長を、完封勝ち10戦および他39戦と比較する。

使い方:
  cd src/input/datasets/decks/starmie-aggro && \
  python3 ../../../../../replay_analysis/shutout_anatomy.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/input/datasets/decks/starmie-aggro"))
sys.path.insert(0, str(ROOT / "replay_analysis"))
from cg.api import CardType, all_card_data  # noqa: E402
import prize_race  # noqa: E402

CARDS = {c.cardId: c for c in all_card_data()}
OUR = "Yser"
CTX_SETUP_ACTIVE, CTX_DRAW_COUNT = 1, 38


def anatomy(rep, me):
    steps = rep["steps"]
    last_turn = 0
    my_setup_selects = 0
    opp_drawcount_nopt = None   # 相手のDrawCount選択肢数-1 = 我々のマリガン数
    my_drawcount_nopt = None    # 我々のDrawCount選択肢数-1 = 相手のマリガン数
    kept_hand_basics = None
    kept_hand = None
    mega_turn = None
    opp_names = Counter()
    for step in steps:
        for pi, e in enumerate(step):
            obsd = e.get("observation") or {}
            cur = obsd.get("current")
            if e.get("status") == "ACTIVE" and cur:
                t = cur.get("turn") or 0
                last_turn = max(last_turn, t)
                ps = cur.get("players") or []
                if len(ps) == 2:
                    # 我々のMega着地ターン
                    if mega_turn is None:
                        for zone in ("active", "bench"):
                            for pk in ps[me].get(zone) or []:
                                c = CARDS.get((pk or {}).get("id"))
                                if c is not None and getattr(c, "megaEx", False):
                                    mega_turn = t
                    # 相手の場のポケモン名
                    for zone in ("active", "bench"):
                        for pk in ps[1 - me].get(zone) or []:
                            c = CARDS.get((pk or {}).get("id"))
                            if c is not None:
                                opp_names[c.name] += 1
            sel = obsd.get("select")
            if not sel or not sel.get("option") or e.get("status") != "ACTIVE":
                continue
            ctx = sel.get("context")
            if pi == me and ctx == CTX_SETUP_ACTIVE:
                my_setup_selects += 1
                try:
                    hand = [c.get("id") for c in
                            (obsd["current"]["players"][me].get("hand") or [])]
                    kept_hand = hand
                    kept_hand_basics = sum(
                        1 for cid in hand
                        if (c := CARDS.get(cid)) is not None
                        and c.cardType == CardType.POKEMON and getattr(c, "basic", False))
                except Exception:
                    pass
            if ctx == CTX_DRAW_COUNT:
                nopt = len(sel["option"]) - 1
                if pi == me:
                    my_drawcount_nopt = nopt   # 相手がマリガンした数
                else:
                    opp_drawcount_nopt = nopt  # 我々がマリガンした数
    return dict(turns=last_turn,
                my_mulligans=max(0, my_setup_selects - 1),
                my_mull_x=opp_drawcount_nopt,
                opp_mulligans=my_drawcount_nopt,
                basics=kept_hand_basics, hand=kept_hand,
                mega_turn=mega_turn,
                opp=", ".join(k for k, _ in opp_names.most_common(3)))


def main():
    rows = []
    for d in ["eps55058443", "eps55060473"]:
        for f in sorted((ROOT / "replay_analysis" / d).glob("*.json")):
            try:
                rep = json.loads(f.read_text())
            except Exception:
                continue
            nm = (rep.get("info") or {}).get("TeamNames") or []
            if OUR not in nm:
                continue
            me = nm.index(OUR)
            g = prize_race.analyze(rep, me)
            if not g or g.get("unknown"):
                continue
            a = anatomy(rep, me)
            a.update(ep=f.stem, win=g["win"], us=g["us"], them=g["them"])
            rows.append(a)

    sh_loss = [r for r in rows if not r["win"] and r["us"] == 0]
    sh_win = [r for r in rows if r["win"] and r["them"] == 0]
    rest = [r for r in rows if r not in sh_loss and r not in sh_win]

    def table(rs, title):
        print(f"\n## {title} (n={len(rs)})\n")
        print("| ep | W/L | ターン数 | 我々mull | 相手mull | 初手たね | Mega着地T | 相手の場(上位) |")
        print("|---|---|---:|---:|---:|---:|---|---|")
        for r in rs:
            mg = r["mega_turn"] if r["mega_turn"] is not None else "**着地せず**"
            mull = r["my_mull_x"] if r["my_mull_x"] is not None else r["my_mulligans"]
            print(f"| {r['ep']} | {'W' if r['win'] else 'L'} | {r['turns']} | "
                  f"{mull} | {r['opp_mulligans'] or 0} | {r['basics']} | {mg} | {r['opp']} |")

    def avg(rs, k):
        vs = [r[k] for r in rs if r[k] is not None]
        return sum(vs) / len(vs) if vs else float("nan")

    table(sh_loss, "完封負け(我々サイド0)")
    table(sh_win, "完封勝ち(相手サイド0)")
    print(f"\n## 平均比較\n")
    print("| 群 | n | ターン数 | 初手たね | Mega着地T | 着地せず |")
    print("|---|---:|---:|---:|---:|---:|")
    for name, rs in (("完封負け", sh_loss), ("完封勝ち", sh_win), ("その他39戦", rest)):
        nomega = sum(1 for r in rs if r["mega_turn"] is None)
        print(f"| {name} | {len(rs)} | {avg(rs,'turns'):.1f} | {avg(rs,'basics'):.1f} | "
              f"{avg(rs,'mega_turn'):.1f} | {nomega} |")


if __name__ == "__main__":
    main()

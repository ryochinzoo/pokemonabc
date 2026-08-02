#!/usr/bin/env python3
"""シフト補正の意味論検証(測定専用) + 未特定2件(120→0)の解剖。

検証: シフト対応(select[s]↔action[s+1])の範囲検査は済んでいるが、意味論
(選んだ手が本当にその後実行されたか)は未検証。actionとは独立な情報源である
ログ列(D59でクリーン判定)と突き合わせる:
  (i)  MAINで攻撃(attackId=A)を選んだ → 以後最初の自分ATTACK(15)ログのattackIdがA
  (ii) MAINでPLAY(手札cardId=C)を選んだ → 以後最初の自分PLAY(10)ログのcardIdがC

使い方:
  cd src/input/datasets/decks/starmie-aggro && \
  python3 ../../../../../replay_analysis/semantic_check.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/input/datasets/decks/starmie-aggro"))
sys.path.insert(0, str(ROOT / "replay_analysis"))
from cg.api import AreaType, OptionType, to_observation_class  # noqa: E402
import main as champ  # noqa: E402
import damage_pairing_diff as dpd  # noqa: E402

CARDS, _ = champ._card_db()
LOG_PLAY, LOG_ATTACK = 10, 15
OUR = "Yser"


def check_game(rep, me):
    steps = rep["steps"]
    stream = []          # 自分のACTIVE観測で届いたログ(順序つき)
    decisions = []       # (kind, value, stream位置)
    for si, step in enumerate(steps):
        if me >= len(step):
            continue
        e = step[me]
        if e.get("status") != "ACTIVE":
            continue
        obsd = e.get("observation") or {}
        for lg in obsd.get("logs") or []:
            stream.append(lg)
        sel = obsd.get("select")
        if not sel or not sel.get("option") or sel.get("type") != 0:
            continue
        act = (steps[si + 1][me].get("action")
               if si + 1 < len(steps) and me < len(steps[si + 1]) else None)
        if not act:
            continue
        try:
            obs = to_observation_class(obsd)
        except Exception:
            continue
        if obs.select is None or obs.current is None:
            continue
        st = obs.current
        my = st.yourIndex if st.yourIndex is not None else me
        for oi in act:
            if not isinstance(oi, int) or not (0 <= oi < len(obs.select.option)):
                continue
            o = obs.select.option[oi]
            if getattr(o, "attackId", None) is not None and o.type == OptionType.ATTACK:
                decisions.append(("attack", o.attackId, len(stream)))
            elif o.type == OptionType.PLAY:
                # PLAYオプションは area を持たない(main.py:344-347 と同じ直読み)
                try:
                    cid = st.players[my].hand[o.index].id
                except Exception:
                    cid = None
                if cid is not None:
                    decisions.append(("play", cid, len(stream)))
    res = Counter()
    bad = []
    for kind, val, pos in decisions:
        want_type = LOG_ATTACK if kind == "attack" else LOG_PLAY
        key = "attackId" if kind == "attack" else "cardId"
        nxt = next((lg for lg in stream[pos:]
                    if lg.get("type") == want_type and lg.get("playerIndex") == me),
                   None)
        if nxt is None:
            res[f"{kind}:後続ログ無し"] += 1
        elif nxt.get(key) == val:
            res[f"{kind}:一致"] += 1
        else:
            res[f"{kind}:不一致"] += 1
            bad.append((kind, val, nxt.get(key)))
    return res, bad


def main():
    total = Counter()
    badex = []
    weird_rows = []
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
            res, bad = check_game(rep, me)
            total.update(res)
            badex += bad[:2]
            # 未特定2件(pred=120, actual=0)の行を回収
            for r in dpd.collect(rep, me, shift=True):
                if r["pred"] == 120 and r.get("actual") == 0:
                    r["ep"] = f.stem
                    weird_rows.append(r)

    print("# シフト補正の意味論検証(ログ列との独立突き合わせ)\n")
    for k, v in sorted(total.items()):
        print(f"  {k}: {v}")
    if badex:
        print(f"  不一致の例: {badex[:6]}")

    print("\n# 未特定2件(予測120→実測0)の解剖\n")
    for r in weird_rows:
        foe = CARDS.get(r["foe_id"])
        print(f"- {r['ep']} turn={r['turn']} 防御側={foe.name if foe else r['foe_id']} "
              f"HP={r.get('foe_hp')}")
        if foe is not None:
            for sk in foe.skills or []:
                print(f"    skill: {(sk.text or '')[:120]}")
        print(f"    tools: {[CARDS.get(t).name if CARDS.get(t) else t for t in r.get('foe_tools', ())]}")
        print(f"    stadium: {[CARDS.get(s).name if CARDS.get(s) else s for s in r['stadium']]}")


if __name__ == "__main__":
    main()

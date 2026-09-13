#!/usr/bin/env python3
"""最終エージェントの技使用率(記事のデッキ図用): ATTACK 選択(select.type=6)で選ばれた attackId を数える.
使い方: python3 replay_analysis/attack_usage.py <epsDir> <deck.csv>
規約: 選択肢=steps[N].observation.select.option / 答え=steps[N+1].action / 手番=status=="ACTIVE" / 自席=deck重なり最大。
"""
import csv, json, sys
from collections import Counter
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
eps, deck_csv = Path(sys.argv[1]), Path(sys.argv[2])
ours = Counter(int(x) for x in deck_csv.read_text().split())
names = {}
with open(REPO / "verification/data/EN_Card_Data.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try: names[int(r["Card ID"])] = r["Card Name"]
        except Exception: pass
use, dmg_by = Counter(), Counter()
games = 0
for fp in sorted(eps.glob("ep*.json")):
    d = json.loads(fp.read_text()); steps = d.get("steps") or []
    if len(steps) < 2: continue
    decks = [Counter(a.get("action") or []) for a in steps[1]]
    ov = [sum((ours & x).values()) for x in decks]
    mine = 0 if ov[0] >= ov[1] else 1
    games += 1
    for si in range(len(steps) - 1):
        ag = steps[si][mine] or {}
        if ag.get("status") != "ACTIVE": continue
        sel = (ag.get("observation") or {}).get("select")
        if not sel or sel.get("type") not in (0, 6): continue   # 攻撃は MAIN の OptionType.ATTACK(13) として出る
        act = (steps[si + 1][mine] or {}).get("action")
        opts = sel.get("option") or []
        if not act or act[0] >= len(opts): continue
        o = opts[act[0]]
        if sel.get("type") == 0 and o.get("type") != 13: continue
        use[(o.get("attackId"), None)] += 1
tot = sum(use.values())
print(f"games={games} attacks={tot}")
for (aid, cid), n in use.most_common(8):
    print(f"  attackId {aid:>5}  {n:5d}  {100*n/tot:5.1f}%")

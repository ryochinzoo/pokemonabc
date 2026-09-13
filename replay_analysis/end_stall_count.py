#!/usr/bin/env python3
"""層S: 「選択=END なのに 選択肢に ATTACK が存在」した MAIN 決定を機械で数える.

対応規則(CLAUDE.md 罠#1): 選択肢は steps[N] の observation.select.option、
その答えは steps[N+1] の action。手番側の判別は status == "ACTIVE" のみ(罠#2)。
OPT: 13=ATTACK, 14=END, 8=ATTACH。SELTYPE: 0=MAIN。
"""
import csv, json
from collections import Counter
from pathlib import Path

REPO = Path("/Users/yujiinoue/Documents/products/pokemonabc")
names = {}
with open(REPO/"verification/data/EN_Card_Data.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        try: names[int(row["Card ID"])] = row["Card Name"]
        except: continue
import sys
# 2026-09-02 引数化: argv[1]=epsDir, argv[2]=deck.csv(既定は 55468574 / starmie-aqua = 8/15 の対照実測を再現)
EPS = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO/"replay_analysis/eps55468574"
DECK = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO/"src/input/datasets/decks/starmie-aqua/deck.csv"
ours = Counter(int(x) for x in DECK.read_text().split())

tot = Counter()
hits = []
for fp in sorted(EPS.glob("ep*.json")):
    d = json.loads(fp.read_text())
    steps = d["steps"]
    decks = [Counter(a.get("action") or []) for a in steps[1]]
    ov = [sum((ours & x).values()) for x in decks]
    mine = 0 if ov[0] >= ov[1] else 1
    opp_names = {names.get(c, "?") for c in decks[1-mine]}
    is_grim = any("Grimmsnarl" in n for n in opp_names)
    won = (d.get("rewards") or [0, 0])[mine] == 1
    for si in range(len(steps) - 1):
        ag = steps[si][mine]
        if ag.get("status") != "ACTIVE":
            continue
        obs = ag.get("observation") or {}
        sel = obs.get("select")
        if not sel or sel.get("type") != 0:  # MAIN のみ
            continue
        opts = sel.get("option") or []
        act = (steps[si + 1][mine] or {}).get("action")
        if not act:
            continue
        chosen_types = {opts[i].get("type") for i in act if i < len(opts)}
        has_attack = any(o.get("type") == 13 for o in opts)
        has_attach = any(o.get("type") == 8 for o in opts)
        tot["main_decisions"] += 1
        if 14 in chosen_types:
            tot["end_chosen"] += 1
            if has_attack:
                key = ("W" if won else "L", "grim" if is_grim else "other")
                tot[f"END_with_attack_{key[0]}_{key[1]}"] += 1
                hits.append((fp.name, si, "END_with_ATTACK", "W" if won else "L",
                             "grim" if is_grim else "other"))
            elif has_attach:
                tot[f"END_with_attach_only_{'W' if won else 'L'}"] += 1
                hits.append((fp.name, si, "END_with_ATTACH_no_attack",
                             "W" if won else "L", "grim" if is_grim else "other"))
for k in sorted(tot):
    print(f"{k:35s} {tot[k]}")
print("\n個別ヒット:")
for h in hits:
    print(" ", h)

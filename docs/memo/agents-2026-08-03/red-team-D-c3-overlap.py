#!/usr/bin/env python3
"""red-team-D §2.2 の再現: field_ev.py の検算が標本を共有していることの定量。

field_ev.py と同一条件(帯800-1099・同100点帯対戦・アーキ判定 classify_b→a)で
対面行列を再構築し、(starmie, o) 予測セルに入る「我々自身の対戦」数と、
検算の実測側(我々の対外戦73戦)とのエピソード重複を数える。対戦ゼロ・ローカルJSONのみ。

実行: nice -n 19 python3 docs/memo/agents-2026-08-03/red-team-D-c3-overlap.py
期待出力(2026-08-03時点のデータで): 予測セル N=86 のうち ours=26 /
measurement 30/73 / OVERLAP 26。
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "replay_analysis"))
import band_meta_census as B  # noqa: E402

LO, HI = 800, 1100

games = B.collect()
for sides in games.values():
    for s in sides:
        s["arch"] = B.classify_b(s["deck"]) or B.classify_a(s["deck"])

mat = defaultdict(lambda: [0, 0, set(), set()])
cell = defaultdict(lambda: {"ours": 0, "others": 0, "our_eps": set()})
for ep, (a, b) in games.items():
    if a["score"] is None or b["score"] is None:
        continue
    if not (LO <= a["score"] < HI and LO <= b["score"] < HI):
        continue
    if B.band(a["score"]) != B.band(b["score"]):
        continue
    if not a["arch"] or not b["arch"] or a["arch"] == b["arch"]:
        continue
    win = a if a["reward"] == 1 else (b if b["reward"] == 1 else None)
    if win is None:
        continue
    for side, opp in ((a, b), (b, a)):
        if side["arch"] == "starmie":
            k = cell[opp["arch"]]
            if side["sub"] in B.OUR_SUBS:
                k["ours"] += 1
                k["our_eps"].add(ep)
            else:
                k["others"] += 1
    lose = b if win is a else a
    for key, i in (((win["arch"], lose["arch"]), 0), ((lose["arch"], win["arch"]), 1)):
        mat[key][i] += 1

field = Counter()
for sides in games.values():
    for s in sides:
        if s["sub"] in B.OUR_SUBS or s["score"] is None:
            continue
        if LO <= s["score"] < HI:
            field[s["arch"] or "other"] += 1
tot = sum(field.values())
archs = [a for a, c in field.most_common() if c / tot >= 0.03 and a != "other"]

pred_eps, pred_n, pred_ours = set(), 0, 0
print("== (starmie, o) 予測セル: 我々の対戦 vs 他チームの対戦 ==")
for o in archs:
    w, l, *_ = mat.get(("starmie", o), [0, 0, set(), set()])
    n = w + l
    d = cell[o]
    used = n >= 8
    print(f"  vs {o:<12} N={n:3d} ({'USED' if used else 'dropped(N<8)'})  "
          f"ours={d['ours']} others={d['others']}")
    if used:
        pred_eps |= d["our_eps"]
        pred_n += n
        pred_ours += d["ours"]

meas_eps, ow, on = set(), 0, 0
for ep, sides in games.items():
    for i, s in enumerate(sides):
        o = sides[1 - i]
        if s["sub"] not in B.OUR_SUBS or o["sub"] in B.OUR_SUBS:
            continue
        if s["score"] is None or not (LO <= s["score"] < HI):
            continue
        on += 1
        ow += (s["reward"] == 1)
        meas_eps.add(ep)

print(f"\n予測セル合計 N={pred_n}、うち我々の対戦 {pred_ours} ({100*pred_ours/max(1,pred_n):.1f}%)")
print(f"実測 {ow}/{on}")
print(f"重複エピソード(検算の両側に同一試合): {len(pred_eps & meas_eps)} "
      f"(実測側の {100*len(pred_eps & meas_eps)/max(1,on):.1f}%)")

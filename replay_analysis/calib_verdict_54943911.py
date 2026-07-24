#!/usr/bin/env python3
"""lucario-calib(54943911)検死 — 第2アーキタイプ前向き検証の判定スクリプト。

data.md「Phase B結果+予測の事前登録」(2026-07-24)の登録に従う:
  H1(較正ゲージ) カバー対面合成 35.58% / H2(族内含意) 61.37%
  判定はカバー対面のみ・実効N=N_cov・CIはそのNで計算・N_cov>=20で確定。
座席は eps54943911/meta.txt(ListEpisodesのagents配列順)から取る。
※t1_verdictのデッキ重複方式は本提出では不可(自デッキ=Lucarioでミラーと非識別)。
"""
import csv
import json
import math
import os
from collections import Counter, defaultdict

REPO = "/Users/yujiinoue/Documents/products/pokemonabc"
EPS = os.path.join(REPO, "replay_analysis", "eps54943911")

# カバー対面(較正ゲージが存在する4種)と登録予測
PRED_H1 = {"Lucario": 45.33, "Archaludon": 18.33, "Dragapult": 51.33, "Abomasnow": 31.67}
PRED_H2 = {"Lucario": 59.67, "Archaludon": 62.33, "Dragapult": 68.00, "Abomasnow": 58.67}
CEW_W = {"Lucario": 0.490, "Archaludon": 0.353, "Dragapult": 0.098, "Abomasnow": 0.059}
H1_COMPOSITE, H2_COMPOSITE = 35.58, 61.37

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


def load_names():
    out = {}
    with open(os.path.join(REPO, "verification/data/EN_Card_Data.csv")) as f:
        for r in csv.DictReader(f):
            st = r["Stage (Pokémon)/Type (Energy and Trainer)"] or ""
            out[int(r["Card ID"])] = (r["Card Name"], "Pokémon" in st)
    return out


def wilson(k, n):
    if n == 0:
        return (0.0, 100.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def main():
    names = load_names()
    meta = []
    for part in open(os.path.join(EPS, "meta.txt")).read().strip().split(","):
        ep, seat, rew, opp = part.split(":")
        meta.append((int(ep), int(seat), int(rew), opp))

    tally = defaultdict(lambda: [0, 0])
    for ep, seat, rew, opp in meta:
        if opp == "SELF":
            continue  # Kaggle自己検証エピソード
        d = json.load(open(os.path.join(EPS, f"ep{ep}.json")))
        decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
        opp_deck = decks[1 - seat]
        lineup = {}
        for cid, n in opp_deck.items():
            nm, isp = names.get(cid, ("?", False))
            if isp:
                lineup[nm] = lineup.get(nm, 0) + n
        label = None
        for lab, keys in RULES:
            if any(k in lineup for k in keys):
                label = lab
                break
        if label is None:
            top = sorted(lineup.items(), key=lambda kv: -kv[1])
            label = "Other:" + (top[0][0] if top else "?")
        tally[label][0 if rew == 1 else 1] += 1

    n_tot = sum(sum(v) for v in tally.values())
    w_tot = sum(v[0] for v in tally.values())
    print(f"=== 54943911 ladder N={n_tot} (self-validation excluded) ===")
    for lab, (w, l) in sorted(tally.items(), key=lambda kv: -sum(kv[1])):
        n = w + l
        lo, hi = wilson(w, n)
        cov = "*" if lab in PRED_H1 else " "
        print(f" {cov}{lab:<24} {w}W-{l}L n={n:<3} {100*w/n:5.1f}% (CI {lo:.0f}-{hi:.0f})")

    cov_w = sum(tally[m][0] for m in PRED_H1 if m in tally)
    cov_n = sum(sum(tally[m]) for m in PRED_H1 if m in tally)
    print(f"\nOVERALL {w_tot}W-{n_tot-w_tot}L = {100*w_tot/max(1,n_tot):.1f}%")
    if cov_n:
        p = 100 * cov_w / cov_n
        lo, hi = wilson(cov_w, cov_n)
        d1, d2 = abs(p - H1_COMPOSITE), abs(p - H2_COMPOSITE)
        print(f"COVERED  {cov_w}W-{cov_n-cov_w}L  N_cov={cov_n}  = {p:.1f}% (CI {lo:.1f}-{hi:.1f})")
        print(f"  H1(較正)={H1_COMPOSITE}  |actual-H1|={d1:.1f}pt  CI内: {lo <= H1_COMPOSITE <= hi}")
        print(f"  H2(族内)={H2_COMPOSITE}  |actual-H2|={d2:.1f}pt  CI内: {lo <= H2_COMPOSITE <= hi}")
        print(f"  N_cov>=20: {'YES → 判定確定可' if cov_n >= 20 else f'NO ({cov_n}/20) → 継続'}")
    # 重み付き合成(遭遇率でなくCEW重みでの比較は参考値)
    parts = {m: tally[m] for m in PRED_H1 if sum(tally.get(m, [0, 0])) > 0}
    if parts:
        wsum = sum(CEW_W[m] for m in parts)
        comp = sum(CEW_W[m] * (100 * w / (w + l)) for m, (w, l) in parts.items()) / wsum
        print(f"  [参考] CEW重み合成(観測セルのみ再正規化): {comp:.1f}%")


if __name__ == "__main__":
    main()

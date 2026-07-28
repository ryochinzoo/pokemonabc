#!/usr/bin/env python3
"""54961048(王者再提出)検死 — data.md「王者再提出のT1事前登録」(2026-07-25)の判定。

登録(提出前に固定):
  H1(族外較正) カバー対面合成 42.12% / H2(族内含意) 84.42% / 識別幅 42.3pt
  判定はカバー対面のみ・N_cov>=20・CIは実効Nで計算・自チーム提出との自己対戦は除外。
  符号予測: 最強=Dragapult(80.7)、最弱=Abomasnow(26.7)/Archaludon(26.8)。
T3: 遭遇分布を現行CEW重み(D35: プールN=120のカバー51戦=25/18/5/3)と
  前回全分布(2026-07-22、ref 54858780、N=60)に対して点検。

分類の裁量(D26生存バイアスの再発防止):
  根拠の弱いエピソードは「不明」に落として全統計から除外し、件数と理由を明示する。
  機械検査: ①replayにデッキデータ無し ②自席デッキが王者deck.csvと不一致
  ③相手デッキが60枚でない ④replayのrewardsとListEpisodesのrewardが不一致。
自チーム判定: ListEpisodesのsubmissions[].teamIdで機械照合(teamId 16405138=Yser)。
  2026-07-26取得の61epで自チーム対戦は0件(検証ep 87935205のみ除外)。
"""
import csv
import json
import math
import os
from collections import Counter, defaultdict

REPO = "/Users/yujiinoue/Documents/products/pokemonabc"
HERE = os.path.dirname(os.path.abspath(__file__))
EPS = os.path.join(HERE, "eps54961048")

PRED_H1 = {"Lucario": 47.31, "Archaludon": 26.79, "Dragapult": 80.67, "Abomasnow": 26.67}
PRED_H2 = {"Lucario": 82.67, "Archaludon": 85.00, "Dragapult": 95.33, "Abomasnow": 77.33}
CEW_W = {"Lucario": 0.490, "Archaludon": 0.353, "Dragapult": 0.098, "Abomasnow": 0.059}
H1_COMPOSITE, H2_COMPOSITE = 42.12, 84.42

# 前回の全分布 (2026-07-22、ref 54858780、N=60、data.md:1127-1138)
PRIOR_FULL = {
    "Lucario": 11, "Alakazam": 9, "Wall(Crustle/GreatTusk)": 9, "Archaludon": 8,
    "Dragapult": 5, "Other": 5, "StarmieMirror": 4, "TR Mewtwo": 4,
    "Grimmsnarl": 3, "Garchomp": 1, "Abomasnow": 1,
}

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


def two_sample_z(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (p1 - p2) / se if se > 0 else 0.0


def main():
    names = load_names()
    ours = Counter(
        int(l) for l in open(os.path.join(REPO, "src/input/datasets/decks/starmie-aggro/deck.csv"))
        if l.strip()
    )

    meta = []
    for part in open(os.path.join(EPS, "meta.txt")).read().strip().split(","):
        ep, seat, rew, opp = part.split(":")
        meta.append((int(ep), int(seat), int(rew), opp))

    tally = defaultdict(lambda: [0, 0])
    unknown = []  # (ep, reason)
    excluded_validation = 0
    for ep, seat, rew, opp in meta:
        if opp == "NONE":
            excluded_validation += 1  # Kaggle自己検証エピソード
            continue
        d = json.load(open(os.path.join(EPS, f"ep{ep}.json")))
        if len(d.get("steps", [])) < 2:
            unknown.append((ep, "デッキデータ無し(steps<2)"))
            continue
        decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
        if decks[seat] != ours:
            unknown.append((ep, "自席デッキが王者deck.csvと不一致(座席根拠が弱い)"))
            continue
        rr = (d.get("rewards") or [None, None])[seat]
        if rr != rew:
            unknown.append((ep, f"reward不一致(replay={rr} vs ListEpisodes={rew})"))
            continue
        opp_deck = decks[1 - seat]
        if sum(opp_deck.values()) != 60:
            unknown.append((ep, f"相手デッキ{sum(opp_deck.values())}枚(60枚でない)"))
            continue
        lineup = {}
        for cid, n in opp_deck.items():
            nm, isp = names.get(cid, ("?", False))
            if isp:
                lineup[nm] = lineup.get(nm, 0) + n
        if not lineup:
            unknown.append((ep, "相手デッキにポケモンが1枚も識別できない"))
            continue
        label = None
        for lab, keys in RULES:
            if any(k in lineup for k in keys):
                label = lab
                break
        if label is None:
            top = sorted(lineup.items(), key=lambda kv: -kv[1])
            label = "Other:" + top[0][0]
        tally[label][0 if rew == 1 else 1] += 1

    n_tot = sum(sum(v) for v in tally.values())
    w_tot = sum(v[0] for v in tally.values())
    print(f"=== 54961048 検死 (取得61ep: 検証{excluded_validation}件除外・自チーム0件・"
          f"不明{len(unknown)}件除外 → 分類済みN={n_tot}) ===")
    for ep, reason in unknown:
        print(f"  不明: ep{ep} — {reason}")

    merged = defaultdict(lambda: [0, 0])
    for lab, (w, l) in tally.items():
        key = lab if not lab.startswith("Other") else "Other"
        merged[key][0] += w
        merged[key][1] += l

    print(f"\n{'対面':<26} {'W-L':>8} {'n':>3} {'遭遇率':>6} {'勝率':>6}  95%CI")
    for lab, (w, l) in sorted(merged.items(), key=lambda kv: -sum(kv[1])):
        n = w + l
        lo, hi = wilson(w, n)
        cov = "*" if lab in PRED_H1 else " "
        print(f"{cov}{lab:<26} {w:>3}W-{l:<3}L {n:>3} {100*n/n_tot:5.1f}% {100*w/n:5.1f}%  ({lo:.0f}-{hi:.0f})")
    # Otherの内訳
    others = {k: v for k, v in tally.items() if k.startswith("Other")}
    if others:
        det = ", ".join(f"{k[6:]}({v[0]}W{v[1]}L)" for k, v in sorted(others.items(), key=lambda kv: -sum(kv[1])))
        print(f"  Other内訳: {det}")
    print(f"\nOVERALL {w_tot}W-{n_tot-w_tot}L = {100*w_tot/max(1,n_tot):.1f}%")

    # ===== T1 =====
    print("\n=== T1: H1(族外較正) vs H2(族内含意) ===")
    print(f"{'対面':<14} {'H1予測':>7} {'H2予測':>7} {'実測':>7} {'n':>3}  95%CI        H1_CI内")
    cw = cn = 0
    for m in PRED_H1:
        w, l = merged.get(m, [0, 0])
        n = w + l
        cw += w
        cn += n
        if n == 0:
            print(f"{m:<14} {PRED_H1[m]:7.1f} {PRED_H2[m]:7.1f} {'--':>7} {n:>3}  (データ無し)")
            continue
        act = 100 * w / n
        lo, hi = wilson(w, n)
        ok = "IN" if lo <= PRED_H1[m] <= hi else "OUT"
        print(f"{m:<14} {PRED_H1[m]:7.1f} {PRED_H2[m]:7.1f} {act:7.1f} {n:>3}  ({lo:4.0f}-{hi:4.0f})  {ok}")
    if cn:
        p = 100 * cw / cn
        lo, hi = wilson(cw, cn)
        d1, d2 = abs(p - H1_COMPOSITE), abs(p - H2_COMPOSITE)
        print(f"\nカバー対面合成: {cw}W-{cn-cw}L  N_cov={cn}  = {p:.1f}% (CI {lo:.1f}-{hi:.1f})")
        print(f"  N_cov>=20: {'YES → 判定確定可' if cn >= 20 else f'NO ({cn}/20) → 継続'}")
        print(f"  H1(較正)={H1_COMPOSITE}  |実測-H1|={d1:.1f}pt  CI内: {lo <= H1_COMPOSITE <= hi}")
        print(f"  H2(族内)={H2_COMPOSITE}  |実測-H2|={d2:.1f}pt  CI内: {lo <= H2_COMPOSITE <= hi}")
        print(f"  → 近いのは: {'H1(較正)' if d1 < d2 else 'H2(族内)'}")
        print(f"  T1判定: H1がCI{'内 → 発火せず(的中)' if lo <= H1_COMPOSITE <= hi else '外 → 発火(較正監査へ)'}")
        cov_share = 100 * cn / n_tot
        print(f"  カバレッジ: {cov_share:.1f}% (D35時点 42.5%)")
        # 符号予測
        obs = {m: 100 * merged[m][0] / sum(merged[m]) for m in PRED_H1 if sum(merged.get(m, [0, 0])) > 0}
        if len(obs) >= 2:
            strongest = max(obs, key=obs.get)
            weakest = min(obs, key=obs.get)
            print(f"  符号予測(最強Dragapult/最弱Abomasnow・Archaludon): 実測 最強={strongest} 最弱={weakest}")
        # 参考: CEW重み合成
        parts = {m: merged[m] for m in PRED_H1 if sum(merged.get(m, [0, 0])) > 0}
        wsum = sum(CEW_W[m] for m in parts)
        comp = sum(CEW_W[m] * (100 * w / (w + l)) for m, (w, l) in parts.items()) / wsum
        print(f"  [参考] CEW重み合成(観測セルのみ再正規化): {comp:.1f}%")

    # ===== T3 =====
    print("\n=== T3a: カバー対面の構成比 vs 現行CEW重み(D35: 25/18/5/3, プール51戦) ===")
    obs_cov = {m: sum(merged.get(m, [0, 0])) for m in PRED_H1}
    n_cov = sum(obs_cov.values())
    chi2 = 0.0
    print(f"{'対面':<14} {'CEW重み':>8} {'観測n':>5} {'観測比':>7}  観測95%CI(重みを含むか)")
    for m in PRED_H1:
        e = CEW_W[m] * n_cov
        o = obs_cov[m]
        if e > 0:
            chi2 += (o - e) ** 2 / e
        lo, hi = wilson(o, n_cov)
        inside = lo <= 100 * CEW_W[m] <= hi
        print(f"{m:<14} {100*CEW_W[m]:7.1f}% {o:>5} {100*o/n_cov:6.1f}%  ({lo:.0f}-{hi:.0f}) {'IN' if inside else 'OUT'}")
    crit = 7.815  # chi2 df=3, 95%
    print(f"chi2={chi2:.2f} vs 臨界値7.815(df=3,95%) → {'逸脱=T3発火' if chi2 > crit else '多項95%CI内 → 発火せず'}")

    print("\n=== T3b: 全分布 vs 前回(2026-07-22, ref 54858780, N=60) — 対面別2標本z ===")
    n_prior = sum(PRIOR_FULL.values())
    print(f"{'対面':<26} {'前回':>9} {'今回':>9} {'z':>6}  判定")
    for lab in sorted(set(list(PRIOR_FULL) + list(merged)),
                      key=lambda x: -(sum(merged.get(x, [0, 0])))):
        pk = PRIOR_FULL.get(lab, 0)
        nn = sum(merged.get(lab, [0, 0]))
        z = two_sample_z(nn, n_tot, pk, n_prior)
        sig = "有意シフト" if abs(z) > 1.96 else "CI内"
        print(f"{lab:<26} {100*pk/n_prior:8.1f}% {100*nn/n_tot:8.1f}% {z:6.2f}  {sig}")


if __name__ == "__main__":
    main()

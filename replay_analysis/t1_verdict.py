#!/usr/bin/env python3
"""T1 verdict (playbook §7): does the calibrated gauge predict the real ladder?

Re-run for a new submission:
  1. In a logged-in Kaggle tab, POST /api/i/competitions.EpisodeService/ListEpisodes
     with {"submissionId": <id>} and header x-xsrf-token (cookie XSRF-TOKEN).
     Build COMPACT as "epId:reward,..." sorted by endTime.
     The FIRST episode is Kaggle's self-play validation (no opponent submissionId)
     -> put it in VALIDATION_EP so it is excluded from ladder stats.
  2. curl https://www.kaggle.com/competitions/episodes/{ep}/replay.json (public, ~670KB each)
     into ./eps/ep{id}.json
  3. Update PRED / CEW_W / PRIOR to the pre-registered values, then run this.
"""

import csv
import json
import math
import os
from collections import Counter, defaultdict

REPO = "/Users/yujiinoue/Documents/products/pokemonabc"
HERE = os.path.dirname(os.path.abspath(__file__))
EPS = os.path.join(HERE, "eps")

COMPACT = "87116801:1,87117452:1,87118327:1,87117988:-1,87118530:-1,87119072:1,87119606:-1,87120133:-1,87120678:-1,87121238:1,87121799:1,87122341:-1,87122884:1,87123421:1,87124032:-1,87124513:1,87125065:1,87125586:1,87126116:1,87126623:-1,87127191:-1,87127728:1,87128252:1,87128827:-1,87129330:1,87129860:1,87130421:1,87130913:1,87131447:-1,87131982:-1,87132525:-1,87133071:-1,87133588:1,87134139:-1,87134687:1,87135213:-1,87135757:1,87136280:-1,87136769:-1,87137422:1,87137871:1,87138316:1,87138923:-1,87139596:1,87142228:1,87145924:1,87150657:1,87156450:-1,87157483:-1,87167341:1,87183467:-1,87196490:-1,87203058:1,87204320:-1,87221919:-1,87234218:1,87248026:1,87266659:1,87277701:1,87281051:1,87292292:1"
REWARD = {int(k): int(v) for k, v in (p.split(":") for p in COMPACT.split(","))}
VALIDATION_EP = 87116801  # first episode = Kaggle self-play validation, not a ladder game

# ordered rules: first match wins. keyed on opponent Pokemon lineup (names -> count)
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

# encounter distribution measured 2026-07-21 on ref 54832323 (N=60) -> current CEW weights
PRIOR = {
    "Archaludon": 10, "Lucario": 14, "StarmieMirror": 7, "Alakazam": 12,
    "Other": 12, "Abomasnow": 2, "Wall(Crustle/GreatTusk)": 2, "Grimmsnarl": 1,
}
# T1 pre-registered predictions (data.md 2026-07-22)
PRED = {"Lucario": 48.9, "Archaludon": 21.4, "Abomasnow": 32.3}
CEW_W = {"Lucario": 0.538, "Archaludon": 0.386, "Abomasnow": 0.076}
PRED_COVERED = 37.0
PRED_OVERALL = 54.0


def load_names():
    out = {}
    with open(os.path.join(REPO, "verification/data/EN_Card_Data.csv")) as f:
        for r in csv.DictReader(f):
            st = r["Stage (Pokémon)/Type (Energy and Trainer)"] or ""
            out[int(r["Card ID"])] = (r["Card Name"], "Pokémon" in st)
    return out


def wilson(k, n):
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def main():
    names = load_names()
    ours = Counter(int(l) for l in open(os.path.join(REPO, "src/input/datasets/decks/starmie-aggro/deck.csv")) if l.strip())

    tally = defaultdict(lambda: [0, 0])
    detail = []
    for ep, rew in REWARD.items():
        if ep == VALIDATION_EP:
            continue
        d = json.load(open(os.path.join(EPS, f"ep{ep}.json")))
        decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
        ov = [sum((ours & x).values()) for x in decks]
        mine = 0 if ov[0] >= ov[1] else 1
        opp = decks[1 - mine]
        lineup = {}
        for cid, n in opp.items():
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
        detail.append((ep, label, rew, ov[mine]))

    n_tot = sum(sum(v) for v in tally.values())
    w_tot = sum(v[0] for v in tally.values())
    print(f"=== ladder games N={n_tot} (validation ep {VALIDATION_EP} excluded) ===")
    print(f"{'archetype':<26} {'W-L':>7} {'n':>3} {'enc%':>6} {'win%':>6}  95%CI")
    merged = defaultdict(lambda: [0, 0])
    for lab, (w, l) in tally.items():
        key = lab if not lab.startswith("Other") else "Other(singletons)"
        merged[key][0] += w
        merged[key][1] += l
    for lab, (w, l) in sorted(merged.items(), key=lambda kv: -sum(kv[1])):
        n = w + l
        lo, hi = wilson(w, n)
        print(f"{lab:<26} {w:>3}W-{l:<3}L {n:>3} {100*n/n_tot:5.1f}% {100*w/n:5.1f}%  ({lo:.0f}-{hi:.0f})")
    print(f"\nOVERALL {w_tot}W-{n_tot-w_tot}L = {100*w_tot/n_tot:.1f}%  (predicted {PRED_OVERALL}%)")

    print("\n=== T1: calibrated-gauge prediction vs ladder ===")
    print(f"{'matchup':<14} {'pred':>6} {'actual':>8} {'n':>3}  95%CI          verdict")
    cw = cn = 0
    for m, p in PRED.items():
        w, l = merged.get(m, [0, 0])
        n = w + l
        cw += w
        cn += n
        if n == 0:
            print(f"{m:<14} {p:6.1f} {'--':>8} {n:>3}  (no data)")
            continue
        act = 100 * w / n
        lo, hi = wilson(w, n)
        ok = "IN CI" if lo <= p <= hi else "OUT OF CI"
        print(f"{m:<14} {p:6.1f} {act:8.1f} {n:>3}  ({lo:4.0f}-{hi:4.0f})   {ok}")
    act_cov = 100 * cw / cn if cn else 0
    lo, hi = wilson(cw, cn)
    print(f"\ncovered matchups: predicted {PRED_COVERED:.1f}%  actual {act_cov:.1f}% "
          f"({cw}/{cn}, 95%CI {lo:.0f}-{hi:.0f})")
    print(f"T1 fire condition = actual outside {PRED_COVERED}+-19pt "
          f"({PRED_COVERED-19:.0f}-{PRED_COVERED+19:.0f}) -> "
          f"{'FIRE' if not (PRED_COVERED-19 <= act_cov <= PRED_COVERED+19) else 'NO FIRE'}")
    cov_share = 100 * cn / n_tot
    print(f"CEW coverage of actual encounters: {cov_share:.1f}%")

    print("\n=== T3: encounter distribution shift vs 2026-07-21 (N=60, ref 54832323) ===")
    n_prior = sum(PRIOR.values())
    print(f"{'archetype':<26} {'prior':>10} {'now':>10}  prior 95%CI(now-scale)  shift")
    fire = []
    for lab in sorted(set(list(PRIOR) + list(merged)), key=lambda x: -(sum(merged.get(x, [0, 0])))):
        pk = PRIOR.get(lab if lab in PRIOR else ("Other" if lab.startswith("Other") else lab), 0)
        w, l = merged.get(lab, [0, 0])
        nn = w + l
        lo_p, hi_p = wilson(pk, n_prior)
        now = 100 * nn / n_tot
        flag = ""
        if not (lo_p <= now <= hi_p):
            flag = "  <== SHIFT"
            fire.append((lab, 100 * pk / n_prior, now))
        print(f"{lab:<26} {100*pk/n_prior:9.1f}% {now:9.1f}%  ({lo_p:4.0f}-{hi_p:4.0f})%{flag}")
    print("\nT3 verdict:", "FIRE" if fire else "no fire")
    for lab, a, b in fire:
        print(f"   {lab}: {a:.1f}% -> {b:.1f}%")


if __name__ == "__main__":
    main()

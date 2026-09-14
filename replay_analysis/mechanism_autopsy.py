#!/usr/bin/env python3
"""Mechanism autopsy of 60 ladder games (sub 54858780, EXP8 pilot).

Pre-registered questions:
  Q1 did EXP8's behavior transfer? (Nebula/game, Ignition targets, same-turn conversion)
  Q2 do losses still show energy-lost-on-KO + Jetting-only offense?
  Q3 wall games: did the v2.2 Nebula patch fire? what happened in the 2 losses?

Our deck: Staryu=1030, MegaStarmie=1031, Ignition=17, Water=3. Nebula attackId=1488.
"""

import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
EPS = os.path.join(HERE, "eps")
REPO = "/Users/yujiinoue/Documents/products/pokemonabc"

STARYU, MSTARMIE, IGNITION, WATER = 1030, 1031, 17, 3
NEBULA = 1488
CRUSTLE = 345

COMPACT = "87117452:1,87118327:1,87117988:-1,87118530:-1,87119072:1,87119606:-1,87120133:-1,87120678:-1,87121238:1,87121799:1,87122341:-1,87122884:1,87123421:1,87124032:-1,87124513:1,87125065:1,87125586:1,87126116:1,87126623:-1,87127191:-1,87127728:1,87128252:1,87128827:-1,87129330:1,87129860:1,87130421:1,87130913:1,87131447:-1,87131982:-1,87132525:-1,87133071:-1,87133588:1,87134139:-1,87134687:1,87135213:-1,87135757:1,87136280:-1,87136769:-1,87137422:1,87137871:1,87138316:1,87138923:-1,87139596:1,87142228:1,87145924:1,87150657:1,87156450:-1,87157483:-1,87167341:1,87183467:-1,87196490:-1,87203058:1,87204320:-1,87221919:-1,87234218:1,87248026:1,87266659:1,87277701:1,87281051:1,87292292:1"
REWARD = {int(k): int(v) for k, v in (p.split(":") for p in COMPACT.split(","))}

# archetype per ep from t1 classification (D33)
ARCH = {}
for ep, lab in {
    87123421: "Lucario", 87125065: "Lucario", 87129330: "Lucario", 87131447: "Lucario",
    87133071: "Lucario", 87133588: "Lucario", 87134139: "Lucario", 87136769: "Lucario",
    87138316: "Lucario", 87138923: "Lucario", 87183467: "Lucario",
    87117988: "Archaludon", 87118530: "Archaludon", 87119606: "Archaludon",
    87127191: "Archaludon", 87130913: "Archaludon", 87131982: "Archaludon",
    87157483: "Archaludon", 87292292: "Archaludon",
    87120133: "Alakazam", 87122884: "Alakazam", 87124513: "Alakazam", 87126623: "Alakazam",
    87128827: "Alakazam", 87130421: "Alakazam", 87139596: "Alakazam", 87142228: "Alakazam",
    87234218: "Alakazam",
    87125586: "Wall", 87129860: "Wall", 87135213: "Wall", 87135757: "Wall",
    87136280: "Wall", 87137422: "Wall", 87145924: "Wall", 87248026: "Wall", 87281051: "Wall",
    87120678: "Mirror", 87122341: "Mirror", 87126116: "Mirror", 87134687: "Mirror",
    87118327: "Dragapult", 87119072: "Dragapult", 87128252: "Dragapult",
    87137871: "Dragapult", 87150657: "Dragapult",
    87196490: "Grimmsnarl", 87221919: "Grimmsnarl", 87266659: "Grimmsnarl",
    87121799: "TRMewtwo", 87132525: "TRMewtwo", 87203058: "TRMewtwo", 87277701: "TRMewtwo",
    87204320: "Abomasnow", 87124032: "Garchomp",
    87117452: "Other", 87121238: "Other", 87127728: "Other", 87156450: "Other",
    87167341: "Other",
}.items():
    ARCH[ep] = lab


def our_index(d, ours):
    decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
    ov = [sum((ours & x).values()) for x in decks]
    if ov[0] == ov[1]:
        return None
    return 0 if ov[0] > ov[1] else 1


def per_turn_view(d, view, mine):
    """Walk one agent view (deduped) and return per-turn Counters of our events.

    Events near game end can be missing from one view (an attack we make on our
    last turn never reaches our own next observation if the game ends before it),
    so callers must merge views with per-turn max.
    """
    prev = None
    turns = []  # list of Counter per game-turn
    cur = Counter()
    ign_this_turn = False
    for step in d["steps"]:
        ag = step[view]
        logs = (ag.get("observation") or {}).get("logs") or []
        if logs == prev:
            continue
        prev = logs
        for L in logs:
            t, p = L.get("type"), L.get("playerIndex")
            if t == 2:
                turns.append(cur)
                cur = Counter()
                if p == mine:
                    cur["my_turn"] = 1
                    ign_this_turn = False
            elif t == 11 and p == mine and L.get("cardId") == IGNITION:
                tgt = L.get("cardIdTarget")
                if tgt == MSTARMIE:
                    cur["ign_to_mstar"] += 1
                    ign_this_turn = True
                elif tgt == STARYU:
                    cur["ign_to_staryu"] += 1
            elif t == 15:
                if p == mine:
                    aid, cid = L.get("attackId"), L.get("cardId")
                    if aid == NEBULA:
                        cur["nebula"] += 1
                        if ign_this_turn:
                            cur["ign_conv"] += 1
                    elif cid == MSTARMIE:
                        cur["jetting"] += 1
                    elif cid == STARYU:
                        cur["watergun"] += 1
                else:
                    cur["opp_atk"] += 1
            elif t == 6 and p == mine:
                fa, ta, cid = L.get("fromArea"), L.get("toArea"), L.get("cardId")
                if fa == 4 and ta == 3 and cid in (STARYU, MSTARMIE):
                    cur["our_kos_taken"] += 1
                if fa == 8 and ta == 3 and cid == WATER:
                    cur["water_lost_ko"] += 1
    turns.append(cur)
    return turns


def analyze(path, mine):
    d = json.load(open(path))
    g = dict(nebula=0, jetting=0, watergun=0, opp_atk=0,
             ign_to_mstar=0, ign_to_staryu=0, ign_conv=0,
             water_lost_ko=0, our_kos_taken=0, my_turns=0, turns=0,
             prizes_me=0, prizes_opp=0)
    va = per_turn_view(d, mine, mine)
    vb = per_turn_view(d, 1 - mine, mine)
    # align turn lists (public turn starts appear in both views); pad shorter
    n = max(len(va), len(vb))
    va += [Counter()] * (n - len(va))
    vb += [Counter()] * (n - len(vb))
    keys = ["nebula", "jetting", "watergun", "opp_atk", "ign_to_mstar",
            "ign_to_staryu", "ign_conv", "water_lost_ko", "our_kos_taken", "my_turn"]
    for ta, tb in zip(va, vb):
        for k in keys:
            g["my_turns" if k == "my_turn" else k] += max(ta[k], tb[k])
    g["turns"] = n - 1
    # prize race: PRIZE(6) -> HAND(2) moves, counted in each owner's view
    for side, key in ((mine, "prizes_me"), (1 - mine, "prizes_opp")):
        prevs = None
        for step in d["steps"]:
            ag = step[side]
            logs = (ag.get("observation") or {}).get("logs") or []
            if logs == prevs:
                continue
            prevs = logs
            for L in logs:
                if (L.get("type") == 6 and L.get("playerIndex") == side
                        and L.get("fromArea") == 6 and L.get("toArea") == 2):
                    g[key] += 1
    return g


def main():
    ours = Counter(int(l) for l in open(os.path.join(REPO, "src/input/datasets/decks/starmie-aggro/deck.csv")) if l.strip())
    per_arch = defaultdict(lambda: defaultdict(list))
    rows = []
    for ep, rew in REWARD.items():
        path = os.path.join(EPS, f"ep{ep}.json")
        d = json.load(open(path))
        mine = our_index(d, ours)
        if mine is None:
            print(f"!! ep{ep}: cannot identify our side, skipped")
            continue
        g = analyze(path, mine)
        g["ep"], g["rew"], g["arch"] = ep, rew, ARCH.get(ep, "?")
        rows.append(g)
        per_arch[g["arch"]]["W" if rew == 1 else "L"].append(g)

    def avg(gs, k):
        return sum(x[k] for x in gs) / len(gs) if gs else 0.0

    keys = ["nebula", "jetting", "watergun", "ign_to_mstar", "ign_to_staryu",
            "water_lost_ko", "our_kos_taken", "my_turns"]

    print("=== Q1: EXP8 behavior in production (per game averages, all 60) ===")
    allg = [g for g in rows]
    tot_ign = sum(g["ign_to_mstar"] + g["ign_to_staryu"] for g in allg)
    tot_conv = sum(g["ign_conv"] for g in allg)
    tot_ign_ms = sum(g["ign_to_mstar"] for g in allg)
    print(f"games={len(allg)}  Nebula/game={avg(allg,'nebula'):.2f}  Jetting/game={avg(allg,'jetting'):.2f}  WaterGun/game={avg(allg,'watergun'):.2f}")
    print(f"Ignition attach/game: ->MegaStarmie {avg(allg,'ign_to_mstar'):.2f}  ->Staryu(misfire) {avg(allg,'ign_to_staryu'):.2f}")
    print(f"Ignition->MegaStarmie -> same-turn Nebula conversion: {tot_conv}/{tot_ign_ms} = {100*tot_conv/max(1,tot_ign_ms):.0f}%")
    print(f"(local post-EXP8 reference vs Lucario: Nebula/game 0.62, conversion 63%, misfire 0.19/game)")

    print("\n=== Q2: loss mechanisms by matchup (avg per game) ===")
    hdr = f"{'arch':<12} {'WL':>2} {'n':>2} " + " ".join(f"{k[:9]:>9}" for k in keys)
    print(hdr)
    for arch in ["Lucario", "Archaludon", "Alakazam", "Mirror", "Grimmsnarl", "Wall", "Dragapult", "TRMewtwo", "Other", "Abomasnow", "Garchomp"]:
        for wl in ("W", "L"):
            gs = per_arch[arch][wl]
            if not gs:
                continue
            print(f"{arch:<12} {wl:>2} {len(gs):>2} " + " ".join(f"{avg(gs,k):9.2f}" for k in keys))

    print("\n=== Q3: wall games detail ===")
    for g in rows:
        if g["arch"] == "Wall":
            print(f"ep{g['ep']} {'W' if g['rew']==1 else 'L'} turns={g['turns']:3d} "
                  f"nebula={g['nebula']} jetting={g['jetting']} watergun={g['watergun']} "
                  f"ignMS={g['ign_to_mstar']} prizes {g['prizes_me']}:{g['prizes_opp']}")

    print("\n=== per-loss detail (all 25 losses) ===")
    for g in sorted(rows, key=lambda x: (x["arch"], x["ep"])):
        if g["rew"] == 1:
            continue
        print(f"  {g['arch']:<12} ep{g['ep']} myTurns={g['my_turns']:2d} "
              f"prizes {g['prizes_me']}:{g['prizes_opp']}  nebula={g['nebula']} "
              f"jetting={g['jetting']} ignMS={g['ign_to_mstar']} ignSt={g['ign_to_staryu']} "
              f"waterLost={g['water_lost_ko']}")


if __name__ == "__main__":
    main()

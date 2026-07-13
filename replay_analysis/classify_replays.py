#!/usr/bin/env python3
"""Classify all downloaded Kaggle episodes: how did we win/lose?"""

import glob
import json

MY_SUB = 54435972

RESULT_REASON = {1: "prizes", 2: "deckout", 3: "no-active", 4: "effect"}


def analyze(path):
    d = json.load(open(path))
    info = d.get("info", {})
    epid = info.get("EpisodeId")
    teams = info.get("TeamNames", ["?", "?"])
    rewards = d.get("rewards")
    statuses = d.get("statuses")
    steps = d["steps"]

    # which index is us? agents in info have no sub id; use kaggle list order:
    # we detect by deck: sample deck has 35 copies of card id 3 (water energy)
    my_idx = None
    if len(steps) > 1:
        for ai, ag in enumerate(steps[1]):
            act = ag.get("action") or []
            if isinstance(act, list) and act.count(3) >= 30:
                my_idx = ai
    # fallback: unknown
    turn = 0
    my_turns = 0
    result = None
    last_hp = {}  # serial -> (owner, cardId)
    prev = [None, None]
    my_attacks = 0
    opp_attacks = 0
    for step in steps:
        for ai, ag in enumerate(step):
            logs = (ag.get("observation") or {}).get("logs") or []
            if logs == prev[ai]:
                continue
            prev[ai] = logs
            for L in logs:
                t = L.get("type")
                p = L.get("playerIndex")
                if L.get("playerIndex") == ai or (ai == 1 and t == 23):
                    if t == 2:
                        turn += 1
                        if p == my_idx:
                            my_turns += 1
                    elif t == 15:
                        if p == my_idx:
                            my_attacks += 1
                        else:
                            opp_attacks += 1
                    elif t == 23:
                        result = (L.get("result"), L.get("reason"))
    my_reward = rewards[my_idx] if my_idx is not None else None
    reason = RESULT_REASON.get(result[1], result[1]) if result else "?"
    return {
        "ep": epid,
        "opp": teams[1 - my_idx] if my_idx is not None else "?",
        "me": teams[my_idx] if my_idx is not None else "?",
        "my_idx": my_idx,
        "reward": my_reward,
        "statuses": statuses,
        "turns": turn,
        "my_turns": my_turns,
        "my_atk": my_attacks,
        "opp_atk": opp_attacks,
        "reason": reason,
        "steps": len(steps),
    }


def main():
    rows = []
    for f in sorted(glob.glob("ep*.json")):
        try:
            rows.append(analyze(f))
        except Exception as e:
            rows.append({"ep": f, "error": str(e)})
    for r in rows:
        if "error" in r:
            print(r)
            continue
        wl = {1: "WIN ", -1: "LOSS", 0: "DRAW"}.get(r["reward"], "?   ")
        print(
            f"{wl} ep{r['ep']} vs {r['opp'][:20]:20s} turns={r['turns']:3d} "
            f"myTurns={r['my_turns']:3d} myAtk={r['my_atk']:3d} oppAtk={r['opp_atk']:3d} "
            f"end={r['reason']:9s} statuses={r['statuses']}"
        )


if __name__ == "__main__":
    main()

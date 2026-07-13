#!/usr/bin/env python3
"""Measure early-loss (donk) rate: losses that end within the first few turns.

Run from sample_submission/sample_submission:
    python3 donk_meter.py N our_deck.csv opponent.py opp_deck.csv
"""

import importlib.util
import sys

sys.path.insert(0, ".")
import os as _os
sys.path.insert(1, _os.path.dirname(_os.path.abspath(__file__)))
import selfplay  # noqa: E402
import main as our_main  # noqa: E402


def load_agent(path):
    if path == "random":
        return selfplay.random_agent
    if path == "main.py":
        return our_main.agent
    spec = importlib.util.spec_from_file_location("opp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def main():
    n = int(sys.argv[1])
    our_deck = selfplay.load_deck(sys.argv[2])
    opp_agent = load_agent(sys.argv[3])
    opp_deck = selfplay.load_deck(sys.argv[4])

    wins = losses = draws = 0
    early_losses = 0  # lost with total turns <= 5 (opponent's 2nd-3rd attack)
    early_wins = 0
    turn_sum = 0
    for i in range(n):
        if i % 2 == 0:
            r = selfplay.run_match(our_deck, opp_deck, our_main.agent, opp_agent)
            w = r["winner"]
        else:
            r = selfplay.run_match(opp_deck, our_deck, opp_agent, our_main.agent)
            w = (1 - r["winner"]) if r["winner"] in (0, 1) else r["winner"]
        t = r.get("turns") or 0
        turn_sum += t
        if w == 0:
            wins += 1
            if t <= 5:
                early_wins += 1
        elif w == 1:
            losses += 1
            if t <= 5:
                early_losses += 1
        else:
            draws += 1
    print(
        f"n={n} W{wins}-L{losses}-D{draws}  "
        f"early(<=5t): lossRate={early_losses / n:.1%} winRate={early_wins / n:.1%}  "
        f"avgTurns={turn_sum / n:.1f}"
    )


if __name__ == "__main__":
    main()

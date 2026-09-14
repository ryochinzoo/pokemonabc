#!/usr/bin/env python3
"""Extract both players' deck lists from replay JSONs and summarize archetypes."""

import csv
import glob
import json
import sys
from collections import Counter

import os
CSVP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verification", "data", "EN_Card_Data.csv")


def load_cards():
    info = {}
    for row in csv.DictReader(open(CSVP, encoding="utf-8")):
        cid = int(row["Card ID"])
        if cid not in info:
            info[cid] = (
                row["Card Name"],
                row["Stage (Pokémon)/Type (Energy and Trainer)"],
                row["HP"],
            )
    return info


def main():
    cards = load_cards()
    seen = {}  # deck signature -> (count, example)
    files = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else "top/ep*.json"))
    for f in files:
        d = json.load(open(f))
        teams = d.get("info", {}).get("TeamNames", ["?", "?"])
        rewards = d.get("rewards", [None, None])
        if len(d["steps"]) < 2:
            continue
        for ai, ag in enumerate(d["steps"][1]):
            deck = ag.get("action") or []
            if len(deck) != 60:
                continue
            sig = tuple(sorted(deck))
            c = Counter(deck)
            if sig in seen:
                seen[sig]["n"] += 1
                seen[sig]["wins"] += 1 if rewards[ai] == 1 else 0
                continue
            # summarize: pokemon lines + key trainers
            pok, tr, en = [], [], []
            for cid, cnt in c.most_common():
                name, stage, hp = cards.get(cid, (f"#{cid}", "?", "?"))
                entry = f"{name} x{cnt}"
                if "Pokémon" in stage:
                    pok.append(f"{entry}({stage.replace(' Pokémon', '')},HP{hp})")
                elif "Energy" in stage:
                    en.append(entry)
                else:
                    tr.append(f"{entry}[{stage}]")
            seen[sig] = {
                "n": 1,
                "wins": 1 if rewards[ai] == 1 else 0,
                "pok": pok,
                "tr": tr,
                "en": en,
                "who": teams[ai],
            }
    for i, (sig, v) in enumerate(sorted(seen.items(), key=lambda kv: -kv[1]["n"])):
        print(f"=== deck{i} seen x{v['n']} (wins {v['wins']}) e.g. {v['who']} ===")
        print("  POKEMON:", "; ".join(v["pok"]))
        print("  TRAINER:", "; ".join(v["tr"]))
        print("  ENERGY :", "; ".join(v["en"]))


if __name__ == "__main__":
    main()

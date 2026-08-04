#!/bin/bash
DECKS=/Users/yujiinoue/Documents/products/pokemonabc/src/input/datasets/decks
BENCH=/Users/yujiinoue/Documents/products/pokemonabc/verification/bench.py
OPP=/Users/yujiinoue/Documents/products/pokemonabc/verification/reference/soutasakurai_crustle_agent.py
OPPDECK=/Users/yujiinoue/Documents/products/pokemonabc/verification/decks/soutasakurai_crustle_2026-08-04.csv
LOG="$DECKS/crustle_sweep_2026-08-04.log"
: > "$LOG"
for d in starmie-aggro deckswap-tarountula-sweep deckswap-grimmsnarl deckswap-grimmsnarl-abilityfix; do
  echo "=== ARM: $d ===" >> "$LOG"
  (cd "$DECKS/$d" && nice -n 5 python3 "$BENCH" 200 --opponent "$OPP" --opponent-deck "$OPPDECK" 2>&1 | tail -6) >> "$LOG"
done
touch "$DECKS/crustle_sweep.done"

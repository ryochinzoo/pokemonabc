#!/bin/bash
DECKS=/Users/yujiinoue/Documents/products/pokemonabc/src/input/datasets/decks
V=/Users/yujiinoue/Documents/products/pokemonabc/verification
LOG="$DECKS/lucario_recal_2026-08-05.log"
: > "$LOG"
for d in starmie-aggro deckswap-grimmsnarl deckswap-grimmsnarl-abilityfix; do
  echo "=== ARM: $d vs makthanithin-lucario ===" >> "$LOG"
  (cd "$DECKS/$d" && nice -n 5 python3 "$V/bench.py" 200 --opponent "$V/reference/makthanithin_lucario_agent.py" --opponent-deck "$V/decks/makthanithin_lucario_2026-08-05.csv" 2>&1 | tail -6) >> "$LOG"
done
touch "$DECKS/lucario_recal.done"

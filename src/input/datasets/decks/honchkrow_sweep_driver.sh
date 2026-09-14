#!/bin/bash
DECKS=/Users/yujiinoue/Documents/products/pokemonabc/src/input/datasets/decks
V=/Users/yujiinoue/Documents/products/pokemonabc/verification
LOG="$DECKS/honchkrow_sweep_2026-08-04.log"
: > "$LOG"
cd "$DECKS/deckswap-honchkrow"
echo "=== GATE: vs random N=120 ===" >> "$LOG"
nice -n 5 python3 "$V/bench.py" 120 2>&1 | tail -6 >> "$LOG"
WR=$(grep -o 'WINRATE=[0-9.]*' "$LOG" | tail -1 | cut -d= -f2)
if python3 -c "exit(0 if float('$WR') >= 0.96 else 1)"; then
  echo "GATE PASS ($WR)" >> "$LOG"
  for opp in "alakazam_ryota_agent.py:decks/ryota_alakazam_2026-07-05.csv:Alakazam" \
             "official_lucario_agent.py:decks/official_lucario_2026-07-21.csv:Lucario" \
             "tomato_archaludon_agent.py:decks/tomato_archaludon_2026-07-22.csv:Archaludon" \
             "soutasakurai_crustle_agent.py:decks/soutasakurai_crustle_2026-08-04.csv:Crustle"; do
    IFS=: read agent deck label <<< "$opp"
    echo "=== ARM: vs $label N=200 ===" >> "$LOG"
    nice -n 5 python3 "$V/bench.py" 200 --opponent "$V/reference/$agent" --opponent-deck "$V/$deck" 2>&1 | tail -6 >> "$LOG"
  done
else
  echo "GATE FAIL ($WR) — 掃引中止" >> "$LOG"
fi
touch "$DECKS/honchkrow_sweep.done"

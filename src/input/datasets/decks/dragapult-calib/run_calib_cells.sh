#!/bin/zsh
# dragapult-calib: H1(族外4セル) + H2(族内4セル) を直列で測る(CPU直列規定 playbook §2)。
# N=300/セル(D50 lucario-calib と同じ)。ログ= cells.log(1セル1ブロック)。
set -u
cd "$(dirname "$0")"
V=../../../../../verification
LOG=cells.log
: > "$LOG"

run_cell() {
  local label=$1; shift
  echo "=== CELL $label $(date -u +%H:%M:%S) ===" >> "$LOG"
  python3 "$V/bench.py" 300 "$@" >> "$LOG" 2>&1
  echo "" >> "$LOG"
}

# --- H1: 族外(較正済みゲージが相手デッキを操縦) ---
run_cell H1_lucario    --opponent "$V/reference/official_lucario_agent.py"   --opponent-deck "$V/decks/official_lucario_2026-07-21.csv"
run_cell H1_archaludon --opponent "$V/reference/tomato_archaludon_agent.py" --opponent-deck "$V/decks/tomato_archaludon_2026-07-22.csv"
run_cell H1_dragapult  --opponent "$V/reference/official_dragapult_agent.py" --opponent-deck "$V/decks/official_dragapult_2026-07-22.csv"
run_cell H1_abomasnow  --opponent "$V/reference/official_abomasnow_agent.py" --opponent-deck "$V/decks/official_abomasnow_2026-07-21.csv"

# --- H2: 族内(我々のパイロットが相手デッキも操縦) ---
run_cell H2_lucario    --opponent ./main.py --opponent-deck "$V/decks/official_lucario_2026-07-21.csv"
run_cell H2_archaludon --opponent ./main.py --opponent-deck "$V/decks/tomato_archaludon_2026-07-22.csv"
run_cell H2_dragapult  --opponent ./main.py --opponent-deck "$V/decks/official_dragapult_2026-07-22.csv"
run_cell H2_abomasnow  --opponent ./main.py --opponent-deck "$V/decks/official_abomasnow_2026-07-21.csv"

echo "=== ALL DONE $(date -u +%H:%M:%S) ===" >> "$LOG"

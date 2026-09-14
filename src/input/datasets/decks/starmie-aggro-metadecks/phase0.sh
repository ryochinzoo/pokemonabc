#!/bin/zsh
# Phase 0 先行ゲート (事前登録 plan-2026-07-29-metadecks-repair.md §3、凍結済み)
# 2腕×6セル×N=50、直列。**起動条件: 55058443検死の完了後(M5a)**。
# 対照セルの素材(確認済み): 辞書内=meta_alakazam_2026-07-14.csv(辞書エントリとCounter一致)
#                           辞書外=lunasol_v0.csv(相手操縦=王者main.py別モジュール)
set -u
cd "$(dirname "$0")"
V=../../../../../verification
CHAMP=../starmie-aggro
LOG=phase0.log
: > "$LOG"

run() { # run <dir> <label> <opp_agent> <opp_deck> [expect_key]
  local dir=$1 label=$2 agent=$3 deck=$4 expect=${5:-}
  local extra=()
  [[ -n "$expect" ]] && extra=(--expect-key "$expect")
  echo "--- $label $(date -u +%H:%M:%S) ---" >> "$LOG"
  (cd "$dir" && python3 "$V/probe_metadecks.py" 50 \
      --opponent "$agent" --opponent-deck "$deck" \
      --label "$label" "${extra[@]}") >> "$LOG" 2>&1
}

# --- 王者腕(辞書に正解なし → expect-keyはゲージ4種に付けない) ---
run "$CHAMP" champion_lucario    "$V/reference/official_lucario_agent.py"   "$V/decks/official_lucario_2026-07-21.csv"
run "$CHAMP" champion_archaludon "$V/reference/tomato_archaludon_agent.py"  "$V/decks/tomato_archaludon_2026-07-22.csv"
run "$CHAMP" champion_dragapult  "$V/reference/official_dragapult_agent.py" "$V/decks/official_dragapult_2026-07-22.csv"
run "$CHAMP" champion_abomasnow  "$V/reference/official_abomasnow_agent.py" "$V/decks/official_abomasnow_2026-07-21.csv"
run "$CHAMP" champion_ctrl_alakazam "$V/gauges/alakazam_agent.py" "$V/decks/meta_alakazam_2026-07-14.csv" alakazam
run "$CHAMP" champion_ctrl_lunasol  "$CHAMP/main.py" "$V/decks/lunasol_v0.csv"

# --- 変種腕 ---
run . variant_lucario    "$V/reference/official_lucario_agent.py"   "$V/decks/official_lucario_2026-07-21.csv"   meta_lucario
run . variant_archaludon "$V/reference/tomato_archaludon_agent.py"  "$V/decks/tomato_archaludon_2026-07-22.csv"  meta_archaludon_tomato
run . variant_dragapult  "$V/reference/official_dragapult_agent.py" "$V/decks/official_dragapult_2026-07-22.csv" meta_dragapult
run . variant_abomasnow  "$V/reference/official_abomasnow_agent.py" "$V/decks/official_abomasnow_2026-07-21.csv" meta_abomasnow
run . variant_ctrl_alakazam "$V/gauges/alakazam_agent.py" "$V/decks/meta_alakazam_2026-07-14.csv" alakazam
run . variant_ctrl_lunasol  "$CHAMP/main.py" "$V/decks/lunasol_v0.csv"

echo "=== PHASE0 DONE $(date -u +%H:%M:%S) ===" >> "$LOG"
grep -h "PROBE_JSON" "$LOG"

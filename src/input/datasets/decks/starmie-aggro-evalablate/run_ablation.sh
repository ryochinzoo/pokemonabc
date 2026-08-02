#!/bin/zsh
# ①-b 3腕アブレーション本測定(plan-2026-07-31-evalablation.md)。全腕・全セル直列。
cd "$(dirname "$0")"
LOG=ablation_run.log
: > $LOG
echo "START $(date '+%F %T') main.py sha256=$(shasum -a 256 main.py | cut -c1-12)" | tee -a $LOG
for MODE in full prize_only board_only; do
  ENV=""
  [ "$MODE" != "full" ] && ENV="$MODE"
  for PAIR in "official_lucario_agent.py|official_lucario_2026-07-21.csv|1562" \
              "tomato_archaludon_agent.py|tomato_archaludon_2026-07-22.csv|1040" \
              "official_dragapult_agent.py|official_dragapult_2026-07-22.csv|426" \
              "official_abomasnow_agent.py|official_abomasnow_2026-07-21.csv|172"; do
    AGENT=$(echo $PAIR | cut -d'|' -f1)
    DECK=$(echo $PAIR | cut -d'|' -f2)
    N=$(echo $PAIR | cut -d'|' -f3)
    echo "=== arm=$MODE gauge=$AGENT N=$N t=$(date '+%T') ===" >> $LOG
    V2_EVAL_ABLATE=$ENV python3 ../../../../../verification/bench.py $N \
      --opponent ../../../../../verification/reference/$AGENT \
      --opponent-deck ../../../../../verification/decks/$DECK >> $LOG 2>&1
  done
done
echo "DONE $(date '+%F %T')" >> $LOG

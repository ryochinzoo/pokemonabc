#!/bin/zsh
# 時計ガード受け入れ試験: 予算10倍(6.0s)+広幅(det8/cand48)+模擬バンク、全4ゲージ。
# 合格条件: 全試合で模擬バンク>0(タイムアウト0件) + CRASH=0。消費の最大値を報告。
cd "$(dirname "$0")"
LOG=acceptance_run.log
CLK=acceptance_clock.log
: > $LOG; : > $CLK
echo "START $(date '+%F %T') sha256=$(shasum -a 256 main.py | cut -c1-12)" | tee -a $LOG
for PAIR in "official_lucario_agent.py|official_lucario_2026-07-21.csv|390" \
            "tomato_archaludon_agent.py|tomato_archaludon_2026-07-22.csv|260" \
            "official_dragapult_agent.py|official_dragapult_2026-07-22.csv|106" \
            "official_abomasnow_agent.py|official_abomasnow_2026-07-21.csv|42"; do
  AGENT=$(echo $PAIR | cut -d'|' -f1); DECK=$(echo $PAIR | cut -d'|' -f2); N=$(echo $PAIR | cut -d'|' -f3)
  echo "=== gauge=$AGENT N=$N t=$(date '+%T') ===" >> $LOG
  V2_SIM_BANK=1 V2_BUDGET_SEC=6.0 V2_DET=8 V2_CAND=48 V2_CLOCK_LOG=$PWD/$CLK \
    python3 ../../../../../verification/bench.py $N \
    --opponent ../../../../../verification/reference/$AGENT \
    --opponent-deck ../../../../../verification/decks/$DECK >> $LOG 2>&1
done
echo "DONE $(date '+%F %T')" >> $LOG
echo "--- 消費統計 ---" >> $LOG
sort -t= -k2 -rn $CLK | head -5 >> $LOG
awk -F'[= ]' '{s+=$2; if($2>mx)mx=$2; n++} END{printf "games=%d mean=%.2fs max=%.2fs\n", n, s/n, mx}' $CLK >> $LOG
awk -F'bank_min=' '$2+0 <= 0 {c++} END{printf "bank<=0 (timeout): %d\n", c+0}' $CLK >> $LOG

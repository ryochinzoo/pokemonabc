#!/bin/bash
# P9検死データの夜間トリクル回収。6h待って制限窓を空け、以後4hおきに1回だけ試す。
REPO=/Users/yujiinoue/Documents/products/pokemonabc
LOG=$REPO/replay_analysis/p9_fetch_2026-08-05.log
: > "$LOG"
echo "sleep 6h ($(date))" >> "$LOG"
sleep 21600
for i in 1 2 3 4 5 6 7 8; do
  if python3 "$REPO/replay_analysis/kaggle_gate.py" probe 55236642 >> "$LOG" 2>&1; then
    echo "probe OK ($(date)) — drain開始" >> "$LOG"
    python3 "$REPO/replay_analysis/kaggle_gate.py" drain-replays 55236642 "$REPO/replay_analysis/eps55236642" 200 full >> "$LOG" 2>&1
    break
  fi
  echo "still blocked ($(date)) — 4h待つ" >> "$LOG"
  sleep 14400
done
touch "$REPO/replay_analysis/p9_fetch.done"

#!/bin/zsh
# E3 Phase 0: OFF腕CEWスクリーニング (改訂登録: 4ゲージ×N=300、約20分、CPU直列)
# 目的: ①Dragapult成分の空白を埋める ②修理効果(ON−OFF)と採用判定(ON−王者)を
#       同一計器で分離可能にする ③OFF腕実測を得た時点で点推定の事前予測を
#       本測定より前に追記登録する(改訂の2段規則)
# 注意: これはスクリーニング(N=300/セル、SE≈2.9pt)。採否判定には使わない。
cd "$(dirname "$0")"
V=../../../../../verification
LOG=e3_off_arm_screening.log
{
  echo "=== E3 OFF-arm CEW screening start: $(date) ==="
  echo "deck: alakazam-e3 (meta_alakazam_2026-07-14), pilot = 王者コピー フラグOFF素"
  echo "--- lucario N=300 ---"
  python3 $V/bench.py 300 --opponent $V/reference/official_lucario_agent.py --opponent-deck $V/decks/official_lucario_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "--- archaludon(tomato) N=300 ---"
  python3 $V/bench.py 300 --opponent $V/reference/tomato_archaludon_agent.py --opponent-deck $V/decks/tomato_archaludon_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- dragapult N=300 ---"
  python3 $V/bench.py 300 --opponent $V/reference/official_dragapult_agent.py --opponent-deck $V/decks/official_dragapult_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- abomasnow N=300 ---"
  python3 $V/bench.py 300 --opponent $V/reference/official_abomasnow_agent.py --opponent-deck $V/decks/official_abomasnow_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "=== done: $(date) ==="
} 2>&1 | tee "$LOG"

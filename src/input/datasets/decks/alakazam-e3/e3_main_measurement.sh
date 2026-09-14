#!/bin/zsh
# E3本測定 (D38規則: Neyman配分 合計N=3,200、単発、CPU直列、E3_HAND=1)
# 事前登録: data.md「E3事前登録+改訂+Phase 0」/ 先行ゲートG1/G2通過が前提
# 安全ゲート(vs random≥96%)はG1の300走を再利用(登録: 二重抽選しない)。
# 点推定事前予測(本測定前に登録済み): CEW 58前後、予測圏[56,61]
export E3_HAND=1
cd "$(dirname "$0")"
V=../../../../../verification
LOG=e3_main_measurement.log
{
  echo "=== E3 main measurement start: $(date) === (E3_HAND=$E3_HAND)"
  echo "deck: alakazam-e3 (meta_alakazam_2026-07-14), pilot = 王者 + E3スパイクON (R1 RAD例外 / R2 拡張温存thr10)"
  echo "--- lucario N=1712 ---"
  python3 $V/bench.py 1712 --opponent $V/reference/official_lucario_agent.py --opponent-deck $V/decks/official_lucario_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "--- archaludon(tomato) N=1024 ---"
  python3 $V/bench.py 1024 --opponent $V/reference/tomato_archaludon_agent.py --opponent-deck $V/decks/tomato_archaludon_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- dragapult N=272 ---"
  python3 $V/bench.py 272 --opponent $V/reference/official_dragapult_agent.py --opponent-deck $V/decks/official_dragapult_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- abomasnow N=192 ---"
  python3 $V/bench.py 192 --opponent $V/reference/official_abomasnow_agent.py --opponent-deck $V/decks/official_abomasnow_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "=== done: $(date) ==="
} 2>&1 | tee "$LOG"

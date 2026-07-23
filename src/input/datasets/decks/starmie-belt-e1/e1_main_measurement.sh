#!/bin/zsh
# E1本測定 (D38規則: Neyman配分 合計N=3,200、単発、CPU直列)
# 事前登録: data.md「E1事前登録」+改訂1+改訂2 / 先行ゲート=D39通過
# 起動 2026-07-23 (D41: 窓開7/27を前倒し、ゆうじのスプリント指示)
cd "$(dirname "$0")"
V=../../../../../verification
LOG=e1_main_measurement.log
{
  echo "=== E1 main measurement start: $(date) ==="
  echo "deck: starmie-belt-e1 (-1 Deluxe Bomb / +1 Maximum Belt), pilot frozen (byte-identical to starmie-aggro)"
  echo "--- safety: vs random 300 ---"
  python3 $V/bench.py 300 || echo "BENCH_EXIT=$?"
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

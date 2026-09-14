#!/bin/zsh
# E2本測定 (D38規則: Neyman N=3,200単発) + 対の族内壁スクリーニング(判定外、T7指摘5)
# 事前登録: data.md「E2事前登録」+改訂 / 先行ゲート=2026-07-24通過
cd "$(dirname "$0")"
V=../../../../../verification
LOG=e2_main_measurement.log
{
  echo "=== E2 main measurement start: $(date) ==="
  echo "deck: starmie-boss-e2 (-2 Judge / +2 Boss's Orders, Bomb kept), pilot frozen"
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
  echo "--- wall screening (判定外・族内): E2 variant vs crustle wall N=150 ---"
  python3 $V/bench.py 150 --opponent main.py --opponent-deck $V/decks/ladder_crustle_wall_2026-07-19.csv || echo "BENCH_EXIT=$?"
  echo "--- wall screening (判定外・族内): champion vs crustle wall N=150 (対照) ---"
  (cd ../starmie-aggro && python3 $V/bench.py 150 --opponent main.py --opponent-deck $V/decks/ladder_crustle_wall_2026-07-19.csv) || echo "BENCH_EXIT=$?"
  echo "=== done: $(date) ==="
} 2>&1 | tee "$LOG"

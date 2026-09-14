#!/bin/zsh
# 第2アーキタイプ前向き検証: Phase B 予測計器 (meta_lucario、タイブレーク登録済み)
# 族外4セル=較正済みゲージ(予測仮説) / 族内4セル=同デッキを王者パイロットが操縦(対抗仮説)
# 各N=300、CPU直列。data.md「設計+事前登録」+「設計の改訂」(T7条件3)準拠。
cd "$(dirname "$0")"
V=../../../../../verification
D=$V/decks/meta_lucario_2026-07-14.csv
LOG=phase_b_lucario.log
{
  echo "=== Phase B (meta_lucario) start: $(date) ==="
  echo "--- 族外: official lucario agent N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent $V/reference/official_lucario_agent.py --opponent-deck $V/decks/official_lucario_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "--- 族外: tomato archaludon agent N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent $V/reference/tomato_archaludon_agent.py --opponent-deck $V/decks/tomato_archaludon_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- 族外: official dragapult agent N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent $V/reference/official_dragapult_agent.py --opponent-deck $V/decks/official_dragapult_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- 族外: official abomasnow agent N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent $V/reference/official_abomasnow_agent.py --opponent-deck $V/decks/official_abomasnow_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "--- 族内: 自パイロット×lucario deck N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent main.py --opponent-deck $V/decks/official_lucario_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "--- 族内: 自パイロット×archaludon deck N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent main.py --opponent-deck $V/decks/tomato_archaludon_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- 族内: 自パイロット×dragapult deck N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent main.py --opponent-deck $V/decks/official_dragapult_2026-07-22.csv || echo "BENCH_EXIT=$?"
  echo "--- 族内: 自パイロット×abomasnow deck N=300 ---"
  python3 $V/bench.py 300 --deck $D --opponent main.py --opponent-deck $V/decks/official_abomasnow_2026-07-21.csv || echo "BENCH_EXIT=$?"
  echo "=== done: $(date) ==="
} 2>&1 | tee "$LOG"

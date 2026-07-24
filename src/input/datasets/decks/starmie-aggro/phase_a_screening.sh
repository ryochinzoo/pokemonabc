#!/bin/zsh
# 第2アーキタイプ前向き検証提出: Phase A 安全スクリーニング
# (data.md 2026-07-24「設計+事前登録」+「設計の改訂」T7 5条件反映済み)
# 王者パイロット × 候補デッキ6本、各 vs random N=300(ミラーデッキ、CPU直列)
# 通過=点推定≥96%。CIが96%を含む境界例のみ後でN=600へ1回延長。
cd "$(dirname "$0")"
V=../../../../../verification
LOG=phase_a_screening.log
{
  echo "=== Phase A screening start: $(date) ==="
  echo "pilot: starmie-aggro main.py (王者、不変更) / opponent: random mirror"
  for d in meta_lucario meta_archaludon meta_garchomp meta_grimmsnarl_munkidori meta_tr_mewtwo meta_starmie_dusknoir; do
    echo "--- $d N=300 ---"
    python3 $V/bench.py 300 --deck $V/decks/${d}_2026-07-14.csv || echo "BENCH_EXIT=$?"
  done
  echo "=== done: $(date) ==="
} 2>&1 | tee "$LOG"

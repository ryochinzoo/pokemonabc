#!/bin/bash
# 上位ラダー悉皆調査の本走 — seed → mine → report を通しで回す。
#
# 取得は全て kaggle_gate 経由(8秒/件・429で4時間停止、playbook §8)。
# seed も mine も冪等・再開可能なので、Cooldown で落ちても再実行で差分だけ進む。
#
#   予算見積(上位100チーム × 稼働2提出 = 200提出):
#     seed          1 + 100          = 101 req
#     list_episodes 200              = 200 req
#     プレフィックス 1提出あたり1〜2   ≈ 250 req
#     ------------------------------------------ 計 ~550 req ≈ 75分
#   ただし対戦相手のデッキを追加リクエストゼロで拾うため、targets の
#   一部は取得済みになり実測はこれより短くなる。
#
#   使い方: nohup bash replay_analysis/ladder_census_driver.sh > /dev/null 2>&1 &
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CENSUS="$REPO/replay_analysis/ladder_census.py"
LOG="$REPO/replay_analysis/ladder_census_$(date +%Y-%m-%d).log"
TOP="${TOP:-100}"

exec > >(tee -a "$LOG") 2>&1
echo "=== ladder_census 本走 開始 $(date '+%F %T') / TOP=$TOP ==="
echo "git HEAD: $(cd "$REPO" && git rev-parse --short HEAD)"

cd "$REPO/replay_analysis" || exit 1

echo ""
echo "--- [1/3] seed (leaderboard → team-submissions) ---"
caffeinate -dims python3 "$CENSUS" seed "$TOP"
SEED_RC=$?
echo "seed rc=$SEED_RC"

echo ""
echo "--- [2/3] mine (list_episodes → 適応プレフィックス読み → 60枚) ---"
caffeinate -dims python3 "$CENSUS" mine
MINE_RC=$?
echo "mine rc=$MINE_RC"

echo ""
echo "--- [3/3] report ---"
python3 "$CENSUS" report "$TOP"

echo ""
if [ "$SEED_RC" -eq 0 ] && [ "$MINE_RC" -eq 0 ]; then
  echo "=== 完走 $(date '+%F %T') ==="
  touch "$REPO/replay_analysis/ladder_census.done"
else
  echo "=== 律速で中断 $(date '+%F %T') — 4時間後に同じコマンドを再実行すれば差分だけ進む ==="
fi

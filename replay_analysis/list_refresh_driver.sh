#!/bin/bash
# 斥候リスト全体の門番トリクル更新(garchomp前向き判定+P9補遺ドレインの材料)
REPO=/Users/yujiinoue/Documents/products/pokemonabc
LOG=$REPO/replay_analysis/list_refresh_2026-08-05.log
: > "$LOG"
python3 - >> "$LOG" 2>&1 <<'PY'
import sys, time
sys.path.insert(0, "/Users/yujiinoue/Documents/products/pokemonabc/replay_analysis")
import kaggle_gate
from pathlib import Path
lists = sorted(Path("/Users/yujiinoue/Documents/products/pokemonabc/replay_analysis/ladder_scout/lists").glob("*_list.json"))
subs = [int(p.name.split("_")[0]) for p in lists]
print(f"refresh {len(subs)} lists via gate")
ok = 0
for s in subs:
    try:
        kaggle_gate.list_episodes(s, force=True)
        ok += 1
    except kaggle_gate.Cooldown as e:
        print(f"COOLDOWN at {ok}/{len(subs)}: {e} — 停止(残りは次回)")
        break
print(f"done {ok}/{len(subs)}")
PY
touch $REPO/replay_analysis/list_refresh.done

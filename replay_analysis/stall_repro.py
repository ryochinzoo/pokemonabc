#!/usr/bin/env python3
"""ENDストール9局面の再現: 本番観測をパイロットに食わせ、探索ON/OFFで選択を比較する.

各局面 × {prod(探索ON), v1(V2_NO_SEARCH=1)} × 反復3回(探索は非決定的)。
サブプロセスで deck dir から実行(cg/ と deck.csv の解決のため)。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/Users/yujiinoue/Documents/products/pokemonabc")
DECK_DIR = REPO / "src/input/datasets/decks/starmie-aqua"
EPS = REPO / "replay_analysis/eps55468574"
import tempfile
SCRATCH = Path(tempfile.mkdtemp(prefix="stall_repro_"))  # 一時ファイルはリポジトリ外へ

HITS = [
    ("ep92465703.json", 111), ("ep92467605.json", 45), ("ep92480060.json", 69),
    ("ep92480995.json", 118), ("ep92481935.json", 42), ("ep92544124.json", 68),
    ("ep92865968.json", 84), ("ep92905989.json", 69), ("ep92905989.json", 95),
]

RUNNER = r'''
import json, sys
sys.path.insert(0, ".")
obs = json.load(open(sys.argv[1]))
import main
res = main.agent(obs)
opts = (obs.get("select") or {}).get("option") or []
types = [opts[i].get("type") if i < len(opts) else None for i in res]
print(json.dumps({"result": res, "types": types}))
'''
(SCRATCH / "_runner.py").write_text(RUNNER)

OPT = {8: "ATTACH", 10: "ABILITY", 13: "ATTACK", 14: "END", 7: "PLAY", 9: "EVOLVE", 12: "RETREAT"}

# 自分の同定(deck重なり)
import csv
from collections import Counter
ours = Counter(int(x) for x in (DECK_DIR / "deck.csv").read_text().split())

for fname, si in HITS:
    d = json.loads((EPS / fname).read_text())
    decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
    ov = [sum((ours & x).values()) for x in decks]
    mine = 0 if ov[0] >= ov[1] else 1
    obs = d["steps"][si][mine]["observation"]
    obs_path = SCRATCH / f"_obs_{fname}_{si}.json"
    obs_path.write_text(json.dumps(obs))
    prod_choice = d["steps"][si + 1][mine]["action"]
    opts = (obs.get("select") or {}).get("option") or []
    prod_types = [OPT.get(opts[i].get("type"), opts[i].get("type")) for i in prod_choice if i < len(opts)]
    row = [f"{fname}#{si}", f"本番={prod_types}"]
    for label, env_extra in (("探索ON", {}), ("v1のみ", {"V2_NO_SEARCH": "1"})):
        outcomes = []
        for rep in range(3):
            env = dict(os.environ)
            env.update(env_extra)
            r = subprocess.run([sys.executable, str(SCRATCH / "_runner.py"), str(obs_path)],
                               cwd=DECK_DIR, env=env, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                outcomes.append("ERR:" + r.stderr.strip().splitlines()[-1][:60] if r.stderr else "ERR")
                continue
            out = json.loads(r.stdout.strip().splitlines()[-1])
            outcomes.append(",".join(OPT.get(t, str(t)) for t in out["types"]))
        row.append(f"{label}={outcomes}")
    print(" | ".join(row), flush=True)

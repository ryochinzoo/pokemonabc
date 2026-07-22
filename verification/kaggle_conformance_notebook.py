# Kaggle Notebook 適合走 — 盲点①(libcg二重ロード)と④(darwin/linuxバイナリ差)を
# **本番プラットフォーム上で**一度に閉じる台本 (D38、実行はゆうじのアカウント作業)
#
# ローカルMacでは原理的に閉じない2項目が、Kaggle Notebook(linux・本物の
# kaggle_environments・本番と同じ2vCPU)なら30分で閉じる。ついでに2vCPU上の
# agent()実測msも取れる(実時間予算0.6sの継ぎ目の定量、レビューR5)。
#
# ── 手順 ──────────────────────────────────────────────
# 1. ローカルで提出物を tar.gz に固める(いつもの提出物と同一でよい):
#      cd src/input/datasets/decks/starmie-aggro && tar czf /tmp/agent.tar.gz main.py deck.csv cg/
# 2. Kaggle → Datasets → New Dataset(private) → agent.tar.gz をアップロード。
#    名前は例えば "starmie-conformance"。
# 3. Simulationコンペのページ → New Notebook → 右パネル Add Data で上のDatasetを追加。
# 4. 以下を1セルずつ貼って実行。
# 5. 出力(特に CONFORMANCE / statuses / rewards / timing の行)を丸ごとコピーして
#    ccに渡す。エラーで止まったらそのログごと渡す(初回は1往復の調整を想定)。
#
# ── セル1: 展開と配置 ─────────────────────────────────
import glob
import os
import shutil
import subprocess

src = glob.glob("/kaggle/input/*/agent.tar.gz")[0]
AGENT_DIR = "/kaggle/working/agent"
shutil.rmtree(AGENT_DIR, ignore_errors=True)
os.makedirs(AGENT_DIR)
subprocess.run(["tar", "xzf", src, "-C", AGENT_DIR], check=True)
print(os.listdir(AGENT_DIR))  # main.py / deck.csv / cg が見えること

# ── セル2: デッキ返却経路の適合(conformance.pyの中核、linuxバイナリで) ──
import sys
import time

os.chdir(AGENT_DIR)
sys.path.insert(0, AGENT_DIR)
import main as agent_mod  # ここで cg/libcg.so (linux) がロードされる = 盲点④の実測

obs = {"remainingOverageTime": 600, "select": None, "logs": [],
       "current": None, "search_begin_input": None}
t0 = time.perf_counter()
deck = agent_mod.agent(dict(obs))
ms = (time.perf_counter() - t0) * 1000
ok = isinstance(deck, list) and len(deck) == 60 and all(isinstance(c, int) for c in deck)
print(f"deck-return: {len(deck)}枚 {ms:.1f}ms → CONFORMANCE={'PASS' if ok else 'FAIL'}")

# ── セル3: 本物のランナーで3戦 (盲点①=libcg二重ロードの実地検査) ──
# 注: env側のcgと提出物のcgが同一プロセスに載る、本番と同じ構図がここで初めて再現される
from kaggle_environments import make

for i in range(3):
    env = make("cabt", debug=True)
    env.run([os.path.join(AGENT_DIR, "main.py"), "random"])
    r = [(s.status, s.reward) for s in env.state]
    print(f"game {i}: steps={len(env.steps)} statuses/rewards={r}")
    # 期待: 我々側が DONE / INVALID や ERROR が出たら本文ログごと回収

# ── セル4: 2vCPU上のagent()実測(実時間予算の継ぎ目の定量、任意) ──
# セル3のdebugログに時間が出ない場合はこの簡易版: 適当なobsを1000回は流せないので、
# セル2のms(デッキ返却)と、セル3の1戦あたり所要時間(セル実行時間/3)をメモするだけでよい。

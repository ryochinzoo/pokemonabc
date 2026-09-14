#!/usr/bin/env python3
"""bench: 自己対戦で「我々のエージェントの強さ」を勝率で測る。

selfplay.py の対戦ハーネスをそのまま使い、main.agent を相手（既定はランダムAI）と
N戦やらせて勝率と95%信頼区間を出す。/bench と /try-heuristic の土台。

実行は必ず提出物ディレクトリ（sample_submission/sample_submission/）から:
    cd sample_submission/sample_submission
    python3 <skill_dir>/scripts/bench.py 200
    python3 <skill_dir>/scripts/bench.py 300 --opponent .bench/main_prev.py --baseline 0.50

引数:
    N               対戦数（既定200）。多いほど勝率の信頼区間が狭くなる＝ノイズに強い。
    --opponent      'random'（既定）か、agent(obs_dict) を持つ .py ファイルのパス。
                    過去バージョンの main.py のコピーを渡せば「新旧の直接対決」になる。
    --opponent-deck 相手専用デッキの deck.csv 形式パス。指定すると「デッキ込みの
                    メタ再現対戦」になる（例: --opponent alakazam_agent.py
                    --opponent-deck decks/alakazam_v0.csv）。省略時は両者同一デッキ
                    ＝判断ロジックの差だけを測る従来モード。
    --baseline      小数。指定すると勝率の信頼区間の下限がこの値を下回ったとき exit 1。
                    /try-heuristic が「退行してないか」を機械的に判定する決定論ゲート用。

終了コード:
    0  正常（--baseline 指定時はゲート通過）
    1  --baseline 指定時、信頼区間の下限が baseline 未満（退行の疑い）
    2  エージェントかハーネスがクラッシュ（大会の「絶対に落ちない」要件に違反）
"""

import argparse
import importlib.util
import math
import os
import sys
import time
import traceback

# 提出物ディレクトリ（=カレント）を import パスに入れて main / selfplay / cg を解決する。
sys.path.insert(0, os.getcwd())
# verification/ 自身も import パスへ（selfplay.py をここから解決する）
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))


def load_agent_from_path(path: str):
    """指定した .py から agent(obs_dict) 関数を読み込む（新旧対決の相手用）。"""
    spec = importlib.util.spec_from_file_location("opponent_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """勝率の95% Wilson信頼区間。少ない試行でも妥当な区間を返す。"""
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=200)
    ap.add_argument("--deck", default=None, help="我々側のデッキCSV（省略時は deck.csv）")
    ap.add_argument("--opponent", default="random")
    ap.add_argument("--opponent-deck", default=None)
    ap.add_argument("--baseline", type=float, default=None)
    args = ap.parse_args()

    import selfplay
    import main as our_main

    our_agent = our_main.agent
    if args.opponent == "random":
        opp_agent = selfplay.random_agent
        opp_label = "random"
    else:
        opp_agent = load_agent_from_path(args.opponent)
        opp_label = args.opponent

    # 既定は両者同一デッキ＝デッキ差を消し、判断ロジックの差だけを測る。
    # --opponent-deck 指定時は相手が専用デッキを使う「メタ再現」モードになり、
    # デッキ差＋ロジック差の合算を測る（環境上位アーキタイプへの勝率チェック用）。
    deck = selfplay.load_deck(args.deck) if args.deck else selfplay.load_deck()
    opp_deck = selfplay.load_deck(args.opponent_deck) if args.opponent_deck else deck
    our_label = f"main.py + {args.deck}" if args.deck else "main.py"
    if args.opponent_deck:
        opp_label += f" + {args.opponent_deck}"

    t0 = time.time()
    try:
        # run_series が席を半々で入れ替えるので、agent0_wins は常に「我々の勝ち数」。
        res = selfplay.run_series(args.n, deck, opp_deck, our_agent, opp_agent)
    except Exception:
        traceback.print_exc()
        print("BENCH: エージェントかハーネスがクラッシュしました（『絶対に落ちない』要件に違反）。")
        print("CRASH=1")
        sys.exit(2)

    wins = res["agent0_wins"]
    losses = res["agent1_wins"]
    draws = res["draws"]
    n = res["n"]
    decisive = wins + losses
    wr = wins / n if n else 0.0
    wr_dec = wins / decisive if decisive else 0.0
    lo, hi = wilson(wins, n)
    dt = time.time() - t0

    print(
        f"我々: {our_label}   相手: {opp_label}   対戦数: {n}   "
        f"({dt:.1f}秒, {1000 * dt / max(n, 1):.1f} ms/戦)"
    )
    print(f"結果: {wins}勝 {losses}敗 {draws}分")
    print(f"勝率: {wr:.1%}  (95%信頼区間 {lo:.1%}〜{hi:.1%})   引分除く勝率: {wr_dec:.1%}")
    # 機械可読の行（/try-heuristic や呼び出し側がパースする）
    print(f"WINRATE={wr:.4f}")
    print(f"CI_LOW={lo:.4f}")
    print("CRASH=0")

    if args.baseline is not None:
        if lo < args.baseline:
            print(f"GATE=FAIL  (信頼区間の下限 {lo:.3f} < baseline {args.baseline:.3f})")
            sys.exit(1)
        print(f"GATE=PASS  (信頼区間の下限 {lo:.3f} >= baseline {args.baseline:.3f})")
    sys.exit(0)


if __name__ == "__main__":
    main()

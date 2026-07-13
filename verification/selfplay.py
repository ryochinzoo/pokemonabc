"""ローカル自己対戦ハーネス。

2つのエージェント関数を戦わせて勝敗を出すための、いちばん基礎の道具。
今後「強くしたAIが本当に強いか」を手元で測るために、毎週これを使う。

使い方:
    python3 selfplay.py            # ランダムAI同士で1戦して結果を表示
    python3 selfplay.py 20         # 20戦して勝率を表示

仕組み（ざっくり）:
    battle_start(deck0, deck1) でゲーム開始 → その時点の状況(obs)が返る。
    obs を見て「今どちらのプレイヤーが選ぶ番か(yourIndex)」を確認し、
    その人のエージェント関数に obs を渡して「選んだ番号のリスト」をもらう。
    battle_select(選んだリスト) で次の状況に進む。これを勝敗が決まるまで繰り返す。
"""

import random
import sys
import time

from cg.game import battle_start, battle_select, battle_finish
from cg.api import to_observation_class, LogType


def load_deck(path: str = "deck.csv") -> list[int]:
    """deck.csv（カードIDが1行に1つ、60行）を読み込んでリストにする。"""
    with open(path, "r") as f:
        ids = [line for line in f.read().split("\n") if line.strip()]
    return [int(x) for x in ids[:60]]


def random_agent(obs_dict: dict) -> list[int]:
    """サンプルと同じ「ランダムに選ぶだけ」のAI。比較の基準（ベースライン）。"""
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        # 本番ではここでデッキ(60枚)を返すが、ローカルでは battle_start に渡すので通らない。
        return load_deck()
    n = len(obs.select.option)
    k = min(obs.select.maxCount, n)
    if k <= 0:
        return []
    return random.sample(range(n), k)


def run_match(deck0: list[int], deck1: list[int], agent0, agent1,
              max_steps: int = 200000) -> dict:
    """1試合を最後まで回す。

    Returns:
        dict: winner(0/1/2=引き分け/-1=不明), reason, decisions, turns
    """
    agents = [agent0, agent1]
    obs, start = battle_start(deck0, deck1)
    if obs is None or start.battlePtr in (None, 0):
        raise RuntimeError(
            f"battle_start に失敗 (errorPlayer={start.errorPlayer}, errorType={start.errorType})"
        )

    winner, reason, decisions, max_turn = -1, None, 0, 0
    try:
        for _ in range(max_steps):
            o = to_observation_class(obs)

            # このターンまでに起きた出来事(logs)に「試合終了」が含まれていないか確認
            for log in (o.logs or []):
                if log.type == LogType.RESULT:
                    winner, reason = log.result, log.reason
            if winner != -1:
                break

            if o.current is None or o.select is None:
                break  # これ以上の選択が無い＝終了
            if o.current.result != -1:
                winner = o.current.result
                break

            max_turn = max(max_turn, o.current.turn)
            decisions += 1
            choice = agents[o.current.yourIndex](obs)  # 選ぶ番のプレイヤーに判断させる
            obs = battle_select(choice)
    finally:
        battle_finish()

    return {"winner": winner, "reason": reason, "decisions": decisions, "turns": max_turn}


def run_series(n: int, deck0, deck1, agent0, agent1) -> dict:
    """n試合まわして勝敗を集計（先攻/後攻の有利を均すため半分ずつ入れ替える）。"""
    wins = [0, 0]
    draws = 0
    for i in range(n):
        if i % 2 == 0:
            r = run_match(deck0, deck1, agent0, agent1)
            w = r["winner"]
        else:
            # 席を入れ替えて agent0 を後攻側に
            r = run_match(deck1, deck0, agent1, agent0)
            w = (1 - r["winner"]) if r["winner"] in (0, 1) else r["winner"]
        if w == 0:
            wins[0] += 1
        elif w == 1:
            wins[1] += 1
        else:
            draws += 1
    return {"agent0_wins": wins[0], "agent1_wins": wins[1], "draws": draws, "n": n}


if __name__ == "__main__":
    deck = load_deck()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    t0 = time.time()

    if n == 1:
        r = run_match(deck, deck, random_agent, random_agent)
        winner_label = {0: "プレイヤー0の勝ち", 1: "プレイヤー1の勝ち",
                        2: "引き分け", -1: "不明"}.get(r["winner"], "不明")
        print(f"結果: {winner_label}  (終了理由コード={r['reason']})")
        print(f"判断回数: {r['decisions']} / 最大ターン: {r['turns']}")
    else:
        res = run_series(n, deck, deck, random_agent, random_agent)
        print(f"{res['n']}戦: agent0 {res['agent0_wins']}勝 / "
              f"agent1 {res['agent1_wins']}勝 / 引き分け {res['draws']}")

    print(f"所要時間: {time.time() - t0:.2f}秒")

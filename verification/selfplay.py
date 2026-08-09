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

import json
import random
import sys
import time
from pathlib import Path

from cg.game import battle_start, battle_select, battle_finish
from cg.api import to_observation_class, LogType


def load_deck(path: str = "deck.csv") -> list[int]:
    """deck.csv（カードIDが1行に1つ、60行）を読み込んでリストにする。"""
    with open(path, "r") as f:
        ids = [line.strip().rstrip(",").strip() for line in f.read().split("\n")]
        ids = [x for x in ids if x]
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


def _record_path(path):
    """記録の書き出し先を検査して返す。

    **デッキディレクトリ配下には絶対に書かない**: そこは提出tarにそのまま固められる
    ので、記録が混入すると提出物が汚れる(handover-2026-08-08 で8本8.4MBを退避した)。
    出力は `../pokemonabc-runs/` 配下に置くこと(v2final_sweep_driver.sh と同じ流儀)。
    """
    p = Path(path).resolve()
    if "src/input/datasets/decks" in p.as_posix():
        raise ValueError(
            f"デッキディレクトリ配下には記録できない: {p}\n"
            "  提出tarに混入する。../pokemonabc-runs/ 配下を指定すること")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run_match(deck0: list[int], deck1: list[int], agent0, agent1,
              max_steps: int = 200000, record=None, record_meta=None) -> dict:
    """1試合を最後まで回す。

    Args:
        record: 指定するとイベント列を JSONL で1試合1行 追記する(既定 None = 完全に不活性)。
            エンジンは `obs.logs`(前回の選択以降に起きたこと)を毎手渡してくるだけで
            棋譜を保持しないので、残したければ呼び出し側で積むしかない。
            **未指定時の挙動は変わらない**: 追加で走るのは `events, prev_logs` の初期化と
            `record is not None` の判定だけで、乱数も引かずエンジンも叩かず obs にも触れない。
            なお同一シードでも譜は再現しない(シャッフルはC側の内部乱数で、Python の
            random からは届かない — 2026-08-09実測)。よって対照は決定列のバイト一致では
            なく、旧版との統計的同等性で取る(playbook §1)。
        record_meta: record 時に各行へ混ぜる追加情報(試合番号など)。

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
    events, prev_logs = [], None
    try:
        for _ in range(max_steps):
            o = to_observation_class(obs)

            # 記録は RESULT 走査より前に置く(試合終了ログもイベント列に残すため)。
            # 同じ logs が連続する観測で再掲されうるので card_effect_probe と同じ排除をする。
            if record is not None:
                raw = obs.get("logs")
                if raw and raw != prev_logs:
                    prev_logs = raw
                    turn = o.current.turn if o.current else None
                    events.extend(
                        {"t": turn,
                         "type": int(lg.type) if lg.type is not None else None,
                         "pi": lg.playerIndex, "cid": lg.cardId,
                         "from": lg.fromArea, "to": lg.toArea,
                         "aid": lg.attackId, "val": lg.value,
                         "dmg": lg.putDamageCounter}
                        for lg in (o.logs or []))

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

    result = {"winner": winner, "reason": reason, "decisions": decisions, "turns": max_turn}
    if record is not None:
        row = dict(record_meta or {})
        row.update(result)
        row["events"] = events
        with _record_path(record).open("a") as f:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
    return result


def run_series(n: int, deck0, deck1, agent0, agent1, record=None) -> dict:
    """n試合まわして勝敗を集計（先攻/後攻の有利を均すため半分ずつ入れ替える）。"""
    wins = [0, 0]
    draws = 0
    for i in range(n):
        meta = {"i": i, "swapped": i % 2 == 1} if record is not None else None
        if i % 2 == 0:
            r = run_match(deck0, deck1, agent0, agent1, record=record, record_meta=meta)
            w = r["winner"]
        else:
            # 席を入れ替えて agent0 を後攻側に
            r = run_match(deck1, deck0, agent1, agent0, record=record, record_meta=meta)
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

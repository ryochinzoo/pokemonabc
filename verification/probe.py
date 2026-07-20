#!/usr/bin/env python3
"""行動プローブの定型部分だけを剥がした薄いヘルパー(2026-07-21運用監査 ⑤)。

**測定ロジック本体はここに入れない。** 仮説ごとに使い捨てのプローブを書く規律
(playbook: フレームワーク化は次の仮説を既存の表現力に引っ張るため避ける)を守りつつ、
毎回コピペしていた「デッキdirへのchdir + sys.path + selfplay/main/cg のimport +
相手エージェントのロード + run_series」の15行だけを共通化する。

使い方(プローブ側):
    from verification.probe import setup, load_opponent, run
    main_mod, selfplay = setup("starmie-aggro")   # デッキdirにchdir済み・importsも解決
    opp = load_opponent(".../official_lucario_agent.py")  # 省略でミラー(自分自身)
    stats = {}
    def wrapped(obs):
        res = main_mod.agent(obs)
        # ここに仮説ごとの記録ロジックを書く(共通化しない)
        return res
    result = run(selfplay, "starmie-aggro", wrapped,
                 opp_agent=opp, opp_deck="/abs/path/to/opp_deck.csv", n=100)
"""
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECKS = os.path.join(REPO, "src/input/datasets/decks")


def setup(deck_name: str):
    """デッキディレクトリに chdir し、main / selfplay / cg を import 可能にする。
    戻り値: (main モジュール, selfplay モジュール)。"""
    deck_dir = os.path.join(DECKS, deck_name)
    os.chdir(deck_dir)
    for p in (deck_dir, os.path.join(REPO, "verification")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import selfplay
    import main as main_mod
    return main_mod, selfplay


def load_opponent(path: str):
    """相手agent(obs)->list[int] を .py パスからロード。"""
    spec = importlib.util.spec_from_file_location("opp_probe", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.agent


def run(selfplay, deck_name: str, our_agent, opp_agent=None,
        opp_deck: str | None = None, n: int = 100) -> dict:
    """自陣 deck_name × 相手(既定はミラー)で n 戦。selfplay.run_series の薄いラッパ。"""
    our_deck = selfplay.load_deck(os.path.join(DECKS, deck_name, "deck.csv"))
    foe_deck = selfplay.load_deck(opp_deck) if opp_deck else our_deck
    foe = opp_agent if opp_agent is not None else our_agent
    return selfplay.run_series(n, our_deck, foe_deck, our_agent, foe)

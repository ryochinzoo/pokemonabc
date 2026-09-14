#!/usr/bin/env python3
"""E3 凍結証明(b): リプレイ等価試験 — 決定的なv1層の出力が王者と全一致すること。

    python3 e3_freeze_check.py [N=20]

王者(starmie-aggro)のagent()で対random実戦を進行し、我々の全決定点で
王者の_v1_decide(o) と 変種(alakazam-e3, E3_HANDフラグOFF)の_v1_decide(o) を
同一Observationに対して呼び、出力の完全一致を検査する。探索層は対象外(登録どおり)。
※実行前提: 環境変数 E3_HAND が未設定であること(スクリプト内でも強制解除)。
"""
import importlib.util
import os
import sys

os.environ.pop("E3_HAND", None)  # フラグOFFを強制

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(_REPO, "verification"))
from probe import setup  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20

# 変種(このdir)を通常importし、王者を別名importする
main_mod, selfplay = setup("alakazam-e3")
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_finish, battle_select, battle_start  # noqa: E402

_champ_path = os.path.join(_REPO, "src/input/datasets/decks/starmie-aggro/main.py")
_spec = importlib.util.spec_from_file_location("champ_main", _champ_path)
champ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(champ)

DECK = selfplay.load_deck(os.path.join(_HERE, "deck.csv"))

mismatches, decisions = 0, 0
for gi in range(N):
    our_seat = gi % 2
    obs, start = battle_start(*((DECK, DECK)))
    if obs is None:
        raise RuntimeError(f"battle_start failed: errorPlayer={start.errorPlayer}")
    try:
        for _ in range(200000):
            o = to_observation_class(obs)
            if o.current is None or o.select is None:
                break
            if o.current.result != -1:
                break
            if o.current.yourIndex == our_seat:
                v1_champ = champ._v1_decide(o)
                v1_var = main_mod._v1_decide(o)
                decisions += 1
                if v1_champ != v1_var:
                    mismatches += 1
                    print(f"MISMATCH game{gi} turn{o.current.turn}: "
                          f"champ={v1_champ} variant={v1_var}", file=sys.stderr)
                result = champ.agent(obs)  # 進行は王者のフルagent(実戦系列を再現)
            else:
                result = selfplay.random_agent(obs)
            obs = battle_select(result)
    finally:
        battle_finish()

print(f"freeze-check: {decisions} decisions over {N} games, mismatches={mismatches}")
print("FREEZE_B=" + ("PASS" if mismatches == 0 else "FAIL"))

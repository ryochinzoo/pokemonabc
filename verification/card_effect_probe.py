#!/usr/bin/env python3
"""C5パイロット: 「エンジンに受理される」の先、「効果が実際に発火する」を10枚で確認する。

設計 = docs/memo/agents-2026-08-03/red-team-D.md §4(発火判定表)。
方式: カードごとに試験デッキ(対象×4+最小構成)を組み、**ミラーデッキ vs random** を
N=20戦。我々側 agent をラップして obs の logs(logs==prev で再送排除)と current を記録し、
期待パターンの発火を数える。判定は3値:
  FIRED             — 期待ログが1回以上出た(発火確認)
  OFFERED_NOT_FIRED — 対象カードのPLAY/ATTACH/ABILITYは観測されたのに期待効果ログが無い(no-op候補)
  NEVER_USED        — 使用自体が観測されず(発火条件を作れていない=判定不能。不発≠未実装)

実行はデッキディレクトリ(cg/ がある場所)から:
  cd src/input/datasets/decks/starmie-aggro && python3 ../../../../../verification/card_effect_probe.py 20
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

import selfplay  # noqa: E402
import main as our_main  # noqa: E402
from cg.api import all_card_data  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
CARDS = {c.cardId: c for c in all_card_data()}
STARYU = 1030       # たね水 Staryu(HP70。ID 3 は基本水エネなので取り違えないこと — 初版はここで落ちた)
WATER, GRASS, DARK = 3, 1, 7   # 基本エネ(3={W}, 1={G}, 7={D} — DB照合、下のassertで検証)
# ログ型(cg/api.py LogType)
SHUFFLE, DRAW, MOVE_CARD, SWITCH, CHANGE, PLAY, ATTACH, ATTACK, HP_CHANGE, COIN = \
    0, 4, 6, 8, 9, 10, 11, 15, 16, 22
A_DECK, A_HAND, A_DISCARD, A_ACTIVE, A_BENCH, A_PRIZE, A_STADIUM, A_ENERGY = \
    1, 2, 3, 4, 5, 6, 7, 8


def deck_of(target, n_target=4, base=STARYU, energy=WATER, extra=()):
    d = [target] * n_target + [base] * 4 + list(extra)
    d += [energy] * (60 - len(d))
    return d


def find_grass_basic():
    for c in sorted(CARDS.values(), key=lambda c: c.cardId):
        if c.cardType == 0 and not (c.attacks is None) and c.hp and c.hp <= 80:
            if getattr(c, "energyType", None) == 1 and not getattr(c, "stage1", False) \
               and not getattr(c, "stage2", False) and not getattr(c, "ex", False):
                return c.cardId
    return STARYU


GRASS_BASIC = find_grass_basic()

# (名前, 対象ID, デッキ, 使用の観測(logsから), 発火の観測(logs/state列から))
def used_play(cid):
    return lambda logs, states: any(L.get("type") == PLAY and L.get("cardId") == cid for L in logs)


def used_attach(cid):
    return lambda logs, states: any(L.get("type") == ATTACH and L.get("cardId") == cid for L in logs)


PROBES = [
    ("JumboIceCream(1147)回復", 1147, deck_of(1147),
     used_play(1147),
     lambda logs, st: any(L.get("type") == HP_CHANGE and (L.get("value") or 0) > 0
                          and not L.get("putDamageCounter") for L in logs)),
    ("CrushingHammer(1120)エネ破壊", 1120, deck_of(1120),
     used_play(1120),
     lambda logs, st: any(L.get("type") == MOVE_CARD and L.get("fromArea") == A_ENERGY
                          and L.get("toArea") == A_DISCARD for L in logs)),
    ("Boss's Orders(1182)呼出", 1182, deck_of(1182),
     used_play(1182),
     lambda logs, st: _boss_fired(logs)),
    # 2026-08-04 v2: 初版の「MOVE_CARD→STADIUM」パターンは0/20だったが、スタジアム機能自体は
    # 同日の grimmsnarl 走行で Spikemuth Gym の発火を観測済み → ログパターン仮説を捨て、
    # state の stadium 欄(State.stadium、サイズ0or1)で直接判定する。
    ("BattleCage(1264)スタジアム設置", 1264, deck_of(1264),
     used_play(1264),
     lambda logs, st: any((cur.get("stadium") or []) for cur in st)),
    # v2: Hero's Cape は ACE SPEC(4枚積みは errorType=4 で拒否された=1枚制限の正執行を再確認)→1枚に。
    ("Hero'sCape(1159)maxHp+100", 1159, deck_of(1159, n_target=1),
     used_attach(1159),
     lambda logs, st: _maxhp_jump(st, 100)),
    ("SpikyEnergy(14)反撃20", 14, deck_of(14, energy=WATER, extra=[WATER] * 0),
     used_attach(14),
     lambda logs, st: any(L.get("type") == HP_CHANGE and L.get("value") == -20
                          and L.get("putDamageCounter") for L in logs)),
    ("GrowGrassEnergy(18)maxHp+20", 18, deck_of(18, base=GRASS_BASIC, energy=GRASS),
     used_attach(18),
     lambda logs, st: _maxhp_jump(st, 20)),
    ("RunErrand(756)ドロー2", 756, deck_of(756, n_target=4, base=STARYU, energy=WATER),
     lambda logs, st: True,   # ABILITYはPLAYログに出ない前提 → 発火のみで判定(使用推定は発火と同値)
     lambda logs, st: _draw_burst(logs)),
    # v2: 初版デッキは Mind Bend={P}必須・Staryu={W}必須なのに悪エネのみ → 誰も攻撃できず
    # ダメカンが発生しえない設計ミス(NEVER_USEDをOFFERED_NOT_FIREDと誤表示)。水+悪の混成にして
    # Staryu の攻撃でダメカンを発生させる。used は「自側にダメカンが載った試合」=前提成立の観測に変更。
    ("AdrenaBrain(112)ダメカン移動", 112,
     [112] * 4 + [STARYU] * 4 + [WATER] * 26 + [DARK] * 26,
     lambda logs, st: any(L.get("type") == HP_CHANGE and (L.get("value") or 0) < 0
                          for L in logs),  # 前提=盤に被ダメが発生した(攻撃ダメはputDamageCounter=False)
     lambda logs, st: _adrena_pair(logs)),
    ("Poffin(1086)山→ベンチ", 1086, deck_of(1086),
     used_play(1086),
     lambda logs, st: any(L.get("type") == MOVE_CARD and L.get("fromArea") == A_DECK
                          and L.get("toArea") == A_BENCH for L in logs)),
]


def _boss_fired(logs):
    # PLAY(1182) の後に SWITCH/CHANGE(どちらの playerIndex でも)が出るか
    seen_play = False
    for L in logs:
        if L.get("type") == PLAY and L.get("cardId") == 1182:
            seen_play = True
        elif seen_play and L.get("type") in (SWITCH, CHANGE):
            return True
    return False


def _maxhp_jump(states, delta):
    # 自分側 active/bench のいずれかの maxHp が試合中に +delta 変化したか
    prev = {}
    for cur in states:
        for pi, pl in enumerate(cur.get("players") or []):
            for zone in ("active", "bench"):
                for slot, c in enumerate(pl.get(zone) or []):
                    if not c:
                        continue
                    key = (pi, c.get("serial"))
                    mh = c.get("maxHp")
                    if key in prev and mh is not None and prev[key] is not None \
                       and mh - prev[key] == delta:
                        return True
                    prev[key] = mh
    return False


def _draw_burst(logs):
    # 自ターン中(TURN_START後)の通常ドロー(1枚)以外に、追加のDRAWが連続2枚出るか
    run = 0
    for L in logs:
        if L.get("type") == DRAW:
            run += 1
            if run >= 3:   # ターン頭1枚 + Run Errand 2枚
                return True
        elif L.get("type") != 5:  # DRAW_REVERSE は無視しない(相手側は別型なので混ざらない)
            run = 0
    return False


def _adrena_pair(logs):
    # putDamageCounter=True の負の HP_CHANGE と、正の HP_CHANGE(回復側)が同一ログ塊に出るか
    neg = pos = False
    for L in logs:
        if L.get("type") == HP_CHANGE and L.get("putDamageCounter"):
            if (L.get("value") or 0) < 0:
                neg = True
        if L.get("type") == HP_CHANGE and (L.get("value") or 0) > 0:
            pos = True
    return neg and pos


def run_probe(name, cid, deck, used_fn, fired_fn):
    # エンジン合法性は run_match が落ちるかで検出(壊れたデッキはERRORとして開示)
    used = fired = 0
    err = None
    for i in range(N):
        rec_logs, rec_states = [], []
        prev = [None]

        def wrapped(obs_dict):
            logs = obs_dict.get("logs")
            if logs and logs != prev[0]:
                prev[0] = logs
                rec_logs.extend(logs)
            cur = obs_dict.get("current")
            if cur:
                rec_states.append(cur)
            return our_main.agent(obs_dict)

        seat = i % 2
        try:
            if seat == 0:
                selfplay.run_match(deck, deck, wrapped, selfplay.random_agent)
            else:
                selfplay.run_match(deck, deck, selfplay.random_agent, wrapped)
        except Exception as e:
            err = repr(e)[:80]
            break
        if used_fn(rec_logs, rec_states):
            used += 1
        if fired_fn(rec_logs, rec_states):
            fired += 1
    if err:
        return f"{name:<34} ERROR: {err}"
    if fired:
        verdict = "FIRED"
    elif used:
        verdict = "OFFERED_NOT_FIRED (no-op候補!)"
    else:
        verdict = "NEVER_USED (判定不能)"
    return f"{name:<34} used={used:2d}/{N} fired={fired:2d}/{N}  → {verdict}"


def main():
    # 基本エネIDの前提をDBで検証(名前で確認、間違っていれば即座に落とす)
    for eid, frag in ((WATER, "{W}"), (GRASS, "{G}"), (DARK, "{D}")):
        assert frag in CARDS[eid].name, (eid, CARDS[eid].name)
    print(f"# C5 効果発火検査  N={N}/枚  (ミラー vs random、我々側のログで判定)")
    print(f"  草たね代replace: {GRASS_BASIC} ({CARDS[GRASS_BASIC].name})")
    for name, cid, deck, used_fn, fired_fn in PROBES:
        assert len(deck) == 60, (name, len(deck))
        print(run_probe(name, cid, deck, used_fn, fired_fn))
    print("CRASH=0 (ERROR行が無ければ)")


if __name__ == "__main__":
    main()

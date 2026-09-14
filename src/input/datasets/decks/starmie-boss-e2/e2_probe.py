#!/usr/bin/env python3
"""E2 (Boss's Orders[1182] 再走・Bomb温存) 先行ゲートプローブ — data.md「E2事前登録」+改訂の実装。使い捨て。

    python3 e2_probe.py boss [N=10]   # 変種(-2 Judge +2 Boss's) vs 公式Lucario: ゲート(1)(2)(3)
    python3 e2_probe.py base [N=10]   # 現行王者 vs 公式Lucario: Judgeプレイ率counterfactual

実装ノート(登録の強化であって変更ではない):
- Boss'sプレイ = 我々のOptionType.PLAY選択で手札のcardId==1182(選択時点で確定)。
- 引きずり出し先 = Boss'sプレイ直後に来る「相手ベンチのCARD選択」を我々自身が選ぶので、
  選択時点で対象の(cardId, serial, HP, エネ数)を直接記録(改訂の指摘2の突合データ)。
- 価値イベント(改訂後の定義) = 引きずり出した個体を**同ターンにKO**。
  KO判定はe1_probe同様、ATTACK→HP_CHANGEのログ帰属でtarget_survived==Falseを検出。
- 観測のみ。agent()の入出力には一切触れない(記録側の例外は握りつぶしてカウント)。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(_REPO, "verification"))
from probe import DECKS, REPO, load_opponent, setup  # noqa: E402

PHASE = sys.argv[1] if len(sys.argv) > 1 else "boss"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
DECK_NAME = {"boss": "starmie-boss-e2", "base": "starmie-aggro"}[PHASE]
CARD_ID = {"boss": 1182, "base": 1213}[PHASE]  # boss=Boss's Orders / base=Judge

main_mod, selfplay = setup(DECK_NAME)
from cg.api import (AreaType, LogType, OptionType,  # noqa: E402
                    all_attack, to_observation_class)
from cg.game import battle_finish, battle_select, battle_start  # noqa: E402

ATTACKS = {a.attackId: a for a in all_attack()}

OPP_AGENT = load_opponent(
    os.path.join(REPO, "verification/reference/official_lucario_agent.py"))
OPP_DECK = selfplay.load_deck(
    os.path.join(REPO, "verification/decks/official_lucario_2026-07-21.csv"))
OUR_DECK = selfplay.load_deck(os.path.join(DECKS, DECK_NAME, "deck.csv"))


def play_game(our_seat: int) -> dict:
    g = {
        "our_seat": our_seat,
        "card_plays": 0,               # ゲート(1): CARD_IDをPLAYした回数
        "card_play_turns": [],
        "dragged": [],                 # ゲート(3)①: 引きずり出し記録(id,serial,hp,energy,turn)
        "value_events": 0,             # ゲート(2)改訂: 引きずり出し先を同ターンKO
        "drag_attacked": 0,            # 旧定義(記録のみ): 引きずり出し先を同ターン攻撃
        "card_in_discard_final": 0,    # 燃やし検出用: 終局時の捨て札内CARD_ID枚数
        "attack_events": [],
        "record_errors": 0,
        "winner": None, "turns": 0,
    }
    pending = []            # 我々が選んだATTACKのスナップショット(FIFO)
    boss_await_target = []  # [turn] Boss'sをプレイしたが対象未記録

    def our_field(state):
        ps = state.players[our_seat]
        act = [p for p in (ps.active or []) if p is not None]
        return act, list(ps.bench or [])

    def harvest(o):
        cur_att = None
        for lg in (o.logs or []):
            t = lg.type
            if t == LogType.ATTACK:
                cur_att = lg
            elif t == LogType.TURN_END:
                cur_att = None
            elif t == LogType.HP_CHANGE:
                if (not lg.putDamageCounter) and cur_att is not None \
                        and cur_att.playerIndex == our_seat and lg.playerIndex != our_seat:
                    for snap in pending:
                        if snap["attacker_serial"] == cur_att.serial \
                                and snap["attack_id"] == cur_att.attackId \
                                and snap["target_serial"] == lg.serial \
                                and "damage" not in snap:
                            snap["damage"] = -lg.value
                            snap["target_survived"] = (snap["target_hp_before"] + lg.value) > 0
                            break

    def snapshot_state(o):
        ours = o.current.players[our_seat]
        g["card_in_discard_final"] = sum(
            1 for c in (ours.discard or []) if c.id == CARD_ID)

    def record_choice(o, result):
        sel = o.select
        if sel is None or not sel.option:
            return
        opts = sel.option
        hand = o.current.players[our_seat].hand or []
        opp = 1 - our_seat
        # (1) CARD_ID のプレイ検出
        for i in result:
            if 0 <= i < len(opts) and opts[i].type == OptionType.PLAY \
                    and opts[i].index is not None and opts[i].index < len(hand) \
                    and hand[opts[i].index].id == CARD_ID:
                g["card_plays"] += 1
                g["card_play_turns"].append(o.current.turn)
                if PHASE == "boss":
                    boss_await_target.append(o.current.turn)
        # (2) Boss's直後の「相手ベンチCARD選択」= 引きずり出し先の記録
        if boss_await_target and PHASE == "boss":
            opp_bench_opts = {i for i, op in enumerate(opts)
                              if op.type == OptionType.CARD
                              and op.playerIndex == opp and op.area == AreaType.BENCH}
            if opp_bench_opts:
                turn = boss_await_target.pop(0)
                for i in result:
                    if i in opp_bench_opts:
                        op = opts[i]
                        bench = o.current.players[opp].bench or []
                        pk = bench[op.index] if (op.index is not None
                                                 and op.index < len(bench)) else None
                        if pk is not None:
                            g["dragged"].append({
                                "id": pk.id, "serial": pk.serial, "hp": pk.hp,
                                "energy": len(pk.energies) if pk.energies else 0,
                                "turn": turn,
                            })
                        break
        # (3) ATTACKスナップショット(KO帰属用)
        for i in result:
            if 0 <= i < len(opts) and opts[i].type == OptionType.ATTACK:
                act, _ = our_field(o.current)
                opp_ps = o.current.players[opp]
                opp_act = [p for p in (opp_ps.active or []) if p is not None]
                if act and opp_act:
                    a, oa = act[0], opp_act[0]
                    pending.append({
                        "attack_id": opts[i].attackId,
                        "attack_name": getattr(ATTACKS.get(opts[i].attackId), "name", "?"),
                        "attacker_serial": a.serial,
                        "target_id": oa.id,
                        "target_serial": oa.serial,
                        "target_hp_before": oa.hp,
                        "turn": o.current.turn,
                    })

    decks = (OUR_DECK, OPP_DECK) if our_seat == 0 else (OPP_DECK, OUR_DECK)
    obs, start = battle_start(*decks)
    if obs is None:
        raise RuntimeError(f"battle_start failed: errorPlayer={start.errorPlayer}")
    winner = -1
    try:
        for _ in range(200000):
            o = to_observation_class(obs)
            for log in (o.logs or []):
                if log.type == LogType.RESULT:
                    winner = log.result
            is_ours = o.current is not None and o.current.yourIndex == our_seat
            if is_ours:
                try:
                    harvest(o)
                    snapshot_state(o)
                except Exception:
                    g["record_errors"] += 1
            if winner != -1:
                break
            if o.current is None or o.select is None:
                break
            if o.current.result != -1:
                winner = o.current.result
                break
            g["turns"] = max(g["turns"], o.current.turn)
            if is_ours:
                result = main_mod.agent(obs)
                try:
                    record_choice(o, result)
                except Exception:
                    g["record_errors"] += 1
            else:
                result = OPP_AGENT(obs)
            obs = battle_select(result)
    finally:
        battle_finish()

    g["winner_is_us"] = (winner == our_seat)
    g["winner"] = winner
    g["attack_events"] = [s for s in pending if "damage" in s]
    # 価値イベント判定: 引きずり出し先を同ターンに攻撃/KO
    for d in g["dragged"]:
        hits = [ev for ev in g["attack_events"]
                if ev["target_serial"] == d["serial"] and ev["turn"] == d["turn"]]
        if hits:
            g["drag_attacked"] += 1
            if any(not ev.get("target_survived", True) for ev in hits):
                g["value_events"] += 1
    g["card_burned"] = max(0, g["card_in_discard_final"] - g["card_plays"])
    return g


games = []
for i in range(N):
    games.append(play_game(our_seat=i % 2))
    print(f"game {i+1}/{N} done", file=sys.stderr)

# ---- 集計 ----
name = "Boss's[1182]" if PHASE == "boss" else "Judge[1213]"
played_games = sum(1 for g in games if g["card_plays"] > 0)
plays = sum(g["card_plays"] for g in games)
burned = sum(g["card_burned"] for g in games)
wins = sum(1 for g in games if g["winner_is_us"])
errors = sum(g["record_errors"] for g in games)
value = sum(g["value_events"] for g in games)
drag_att = sum(g["drag_attacked"] for g in games)
dragged = [d for g in games for d in g["dragged"]]

print(f"\n===== E2 probe phase={PHASE} ({DECK_NAME} vs official Lucario, N={N}) =====")
print(f"wins {wins}/{N} | record_errors {errors} (>0なら当該戦無効・要再走=改訂指摘6)")
print(f"[{name}] played in {played_games}/{N} games ({plays} plays) | burned-as-cost {burned}")
if PHASE == "boss":
    print(f"[drag] targets: {[(d['id'], f'hp{d['hp']}', f'e{d['energy']}') for d in dragged]}")
    print(f"[drag] attacked same turn (旧定義・記録のみ): {drag_att}")
    print(f"\n== GATE(1) played >= 4/10: "
          f"{'PASS' if played_games >= 4 else 'FAIL->延長' if N == 10 else 'see 7/20'}"
          f" ({played_games}/{N})")
    print(f"== GATE(2改訂) drag->same-turn-KO >= 1: "
          f"{'PASS' if value >= 1 else 'FAIL->延長' if N == 10 else 'KILL(0/20)'}"
          f" ({value} events)")
    print(f"== GATE(3) 記録: dragged分布(上記) / burned {burned} / base併走でJudge率")

path = os.path.join(_HERE, f"e2_probe_{PHASE}_result.json")
with open(path, "w") as f:
    json.dump({"phase": PHASE, "deck": DECK_NAME, "n": N, "games": games},
              f, indent=1, ensure_ascii=False)
print(f"\nraw -> {path}")

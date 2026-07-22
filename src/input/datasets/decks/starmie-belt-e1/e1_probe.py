#!/usr/bin/env python3
"""E1 (Maximum Belt[1158]) 先行ゲートプローブ — data.md「E1事前登録」+改訂2の実装。使い捨て。

    python3 e1_probe.py belt [N=10]   # 変種(-Bomb+Belt) vs 公式Lucario: ゲート(1)(2)(3)
    python3 e1_probe.py base [N=10]   # 現行王者 vs 公式Lucario: Bomb counterfactual + Nebula=210対照

実装ノート(登録の強化であって変更ではない):
- 素朴なHP差分ではなくエンジンログ(ATTACK/HP_CHANGE/ATTACH)で攻撃→ダメージを直接対応付ける。
  putDamageCounter=True(ダメカン)は除外。クリーンイベント定義=登録どおり
  「Belt装着ポケモンのNebula Beam・相手Active=ex・同一個体残存(=非KO)」でΔHP=260。
- 観測のみ。agent()の入出力には一切触れない(記録側の例外は握りつぶしてカウント)。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(_REPO, "verification"))
from probe import DECKS, REPO, load_opponent, setup  # noqa: E402

PHASE = sys.argv[1] if len(sys.argv) > 1 else "belt"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
DECK_NAME = {"belt": "starmie-belt-e1", "base": "starmie-aggro"}[PHASE]
TOOL_ID = {"belt": 1158, "base": 1167}[PHASE]
MEGA_STARMIE = 1031

main_mod, selfplay = setup(DECK_NAME)
from cg.api import (AreaType, LogType, OptionType,  # noqa: E402
                    all_attack, all_card_data, to_observation_class)
from cg.game import battle_finish, battle_select, battle_start  # noqa: E402

EX_IDS = {c.cardId for c in all_card_data() if c.ex or c.megaEx}
ATTACKS = {a.attackId: a for a in all_attack()}

OPP_AGENT = load_opponent(
    os.path.join(REPO, "verification/reference/official_lucario_agent.py"))
OPP_DECK = selfplay.load_deck(
    os.path.join(REPO, "verification/decks/official_lucario_2026-07-21.csv"))
OUR_DECK = selfplay.load_deck(os.path.join(DECKS, DECK_NAME, "deck.csv"))


def play_game(our_seat: int) -> dict:
    g = {
        "our_seat": our_seat,
        "tool_on_board": False,          # ゲート(1): TOOL_IDが自陣の場に付いたか
        "tool_attaches": [],             # ゲート(2): (貼付先cardId, active/bench)
        "tool_offered_obs": 0,           # 診断: 手札のTOOL_IDをATTACH可能だった観測数
        "tool_taken_obs": 0,             # 診断: そのうち実際に貼った回数
        "tool_in_discard": False,        # base: Bomb起爆の登録プロキシ(捨て札に1167)
        "dmgcounter_hits_on_opp": 0,     # base: 相手側へのダメカン起因HP変化(=Bomb爆発)
        "attack_events": [],             # 攻撃→ダメージの対応付け(クリーンイベント素材)
        "record_errors": 0,
        "winner": None, "turns": 0,
    }
    pending = []          # 我々が選んだATTACKのスナップショット(FIFO)
    serial2tool = {}      # 我々の場: ポケモンserial -> tool id集合 (観測時点)

    def our_field(state):
        ps = state.players[our_seat]
        act = [p for p in (ps.active or []) if p is not None]
        return act, list(ps.bench or [])

    def harvest(o):
        """我々の観測に届いたログから事実を収集(自席視点のみ=重複なし)。"""
        cur_att = None  # ログ列を順に読み、直近のATTACKにHP_CHANGEを帰属させる
        for lg in (o.logs or []):
            t = lg.type
            if t == LogType.ATTACH and lg.playerIndex == our_seat \
                    and lg.cardId == TOOL_ID:
                g["tool_attaches"].append(lg.cardIdTarget)
            elif t == LogType.ATTACK:
                cur_att = lg
            elif t == LogType.TURN_END:
                cur_att = None
            elif t == LogType.HP_CHANGE:
                if lg.putDamageCounter and lg.playerIndex != our_seat:
                    g["dmgcounter_hits_on_opp"] += 1
                if (not lg.putDamageCounter) and cur_att is not None \
                        and cur_att.playerIndex == our_seat and lg.playerIndex != our_seat:
                    # 我々の攻撃による相手側HP変化 → pendingスナップショットと突合
                    for snap in pending:
                        if snap["attacker_serial"] == cur_att.serial \
                                and snap["attack_id"] == cur_att.attackId \
                                and snap["target_serial"] == lg.serial \
                                and "damage" not in snap:
                            snap["damage"] = -lg.value
                            snap["target_survived"] = (snap["target_hp_before"] + lg.value) > 0
                            break

    def snapshot_state(o):
        """観測時点の自陣ツール地図・盤面Belt有無・捨て札を更新。"""
        act, bench = our_field(o.current)
        for p in act + bench:
            tools = {c.id for c in (p.tools or [])}
            serial2tool[p.serial] = tools
            if TOOL_ID in tools:
                g["tool_on_board"] = True
        if any(c.id == TOOL_ID for c in (o.current.players[our_seat].discard or [])):
            g["tool_in_discard"] = True

    def record_choice(o, result):
        """agent()の選択からATTACH提示/選択とATTACKスナップショットを記録。"""
        sel = o.select
        if sel is None or not sel.option:
            return
        opts = sel.option
        hand = o.current.players[our_seat].hand or []
        tool_opt_idx = {i for i, op in enumerate(opts)
                        if op.type == OptionType.ATTACH and op.area == AreaType.HAND
                        and op.index is not None and op.index < len(hand)
                        and hand[op.index].id == TOOL_ID}
        if tool_opt_idx:
            g["tool_offered_obs"] += 1
            if any(i in tool_opt_idx for i in result):
                g["tool_taken_obs"] += 1
        for i in result:
            if 0 <= i < len(opts) and opts[i].type == OptionType.ATTACK:
                act, _ = our_field(o.current)
                opp = o.current.players[1 - our_seat]
                opp_act = [p for p in (opp.active or []) if p is not None]
                if act and opp_act:
                    a, oa = act[0], opp_act[0]
                    pending.append({
                        "attack_id": opts[i].attackId,
                        "attack_name": getattr(ATTACKS.get(opts[i].attackId), "name", "?"),
                        "attacker_id": a.id,
                        "attacker_serial": a.serial,
                        "belt_on_attacker": 1158 in serial2tool.get(a.serial, set()),
                        "target_id": oa.id,
                        "target_serial": oa.serial,
                        "target_hp_before": oa.hp,
                        "target_is_ex": oa.id in EX_IDS,
                        "stadium": [c.id for c in (o.current.stadium or [])],
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
    g["attacks_unresolved"] = len([s for s in pending if "damage" not in s])
    return g


games = []
for i in range(N):
    games.append(play_game(our_seat=i % 2))
    print(f"game {i+1}/{N} done", file=sys.stderr)

# ---- 集計 ----
out = {"phase": PHASE, "deck": DECK_NAME, "n": N, "games": games}
tool_name = "Belt[1158]" if PHASE == "belt" else "Bomb[1167]"
onboard = sum(1 for g in games if g["tool_on_board"])
offered = sum(g["tool_offered_obs"] for g in games)
taken = sum(g["tool_taken_obs"] for g in games)
targets = [t for g in games for t in g["tool_attaches"]]
wins = sum(1 for g in games if g["winner_is_us"])
errors = sum(g["record_errors"] for g in games)

print(f"\n===== E1 probe phase={PHASE} ({DECK_NAME} vs official Lucario, N={N}) =====")
print(f"wins {wins}/{N} | record_errors {errors} | "
      f"unresolved_attacks {sum(g['attacks_unresolved'] for g in games)}")
print(f"[{tool_name}] on-board {onboard}/{N} games | offered {offered} obs / taken {taken}")
print(f"[{tool_name}] attach targets (cardId): {targets}")
if PHASE == "base":
    det = sum(1 for g in games if g["tool_in_discard"])
    blasts = sum(g["dmgcounter_hits_on_opp"] for g in games)
    print(f"[Bomb] detonation proxy (1167 in our discard): {det}/{N} games | "
          f"putDamageCounter hits on opp: {blasts}")

clean, other = [], []
for g in games:
    for ev in g["attack_events"]:
        is_clean = (ev["attack_name"] == "Nebula Beam" and ev["target_is_ex"]
                    and ev.get("target_survived"))
        (clean if is_clean else other).append(ev)

print(f"\n-- clean events (Nebula Beam / target ex / survived): {len(clean)}")
for ev in clean:
    print(f"  t{ev['turn']:>2} {ev['attack_name']} belt={ev['belt_on_attacker']} "
          f"target={ev['target_id']} hp{ev['target_hp_before']} dmg={ev['damage']} "
          f"stadium={ev['stadium']}")
print(f"-- other attack events: {len(other)}")
for ev in other:
    print(f"  t{ev['turn']:>2} {ev['attack_name']} belt={ev['belt_on_attacker']} "
          f"target={ev['target_id']} ex={ev['target_is_ex']} hp{ev['target_hp_before']} "
          f"dmg={ev['damage']} survived={ev.get('target_survived')}")

if PHASE == "belt":
    g1 = onboard >= 3
    belt_clean = [ev for ev in clean if ev["belt_on_attacker"]]
    g3_vals = sorted({ev["damage"] for ev in belt_clean})
    print(f"\n== GATE(1) belt on board >=3/10: {'PASS' if g1 else 'FAIL'} ({onboard}/{N})")
    print(f"== GATE(2) attach targets: {targets} (記録のみ・kill無し)")
    print(f"== GATE(3) belt-clean-events: {len(belt_clean)} 件, damages={g3_vals} "
          f"(260のみ=PASS / 0件=+10延長1回 / 260以外=kill)")

path = os.path.join(_HERE, f"e1_probe_{PHASE}_result.json")
with open(path, "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(f"\nraw -> {path}")

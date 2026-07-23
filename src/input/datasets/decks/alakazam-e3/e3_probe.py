#!/usr/bin/env python3
"""E3 Phase 0 診断プローブ — data.md「E3事前登録+改訂」の実装。使い捨て。

    python3 e3_probe.py [max_games=300]

構成: alakazam-e3(フラグOFF=王者コピー素) vs random・ミラーデッキ(穴D-1の90.0%アンカーと同構成)。
走行規則(改訂): 敗戦20件が貯まるまで、上限N=300。上限到達時は収集分で判定・件数併記。

記録項目(登録の(a)-(d)):
(a) 敗因分類 — エンジンRESULT reason語彙: 1=サイド取り切り / 2=山切れ / 3=場空 / 4=効果。
    膠着はターン>100を代理。第4カテゴリ=マリガン敗(事故)は分離し「過半」判定の分母から除く。
(b) Powerful Hand[1072]攻撃時の自手札枚数分布(打点=手札×20)。
(c) Run Away Draw(Dudunsparce[66]のABILITY)発動時の山残枚数 +
    山→手札変換の駆動源定量: 我々の決定点スナップショット間の deck/hand デルタを
    直前に選んだ行動クラスへ帰属(同一ターン内のみ。ターン跨ぎは turn_boundary チャネルに隔離)。
(d) マリガン率 — HAS_BASIC_POKEMON(hasBasicPokemon=False)ログ。

観測のみ。agent()の入出力には一切触れない(記録側の例外は握りつぶしてカウント)。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(_REPO, "verification"))
from probe import setup  # noqa: E402

MAX_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 300
TARGET_LOSSES = 20

main_mod, selfplay = setup("alakazam-e3")
from cg.api import (AreaType, LogType, OptionType,  # noqa: E402
                    to_observation_class)
from cg.game import battle_finish, battle_select, battle_start  # noqa: E402

DECK = selfplay.load_deck(os.path.join(_HERE, "deck.csv"))
DUDUNSPARCE = 66
POWERFUL_HAND = 1072


def _pokemon_of_option(state, seat, opt):
    """ABILITY等のoptionから発生源ポケモンを解決(分からなければNone)。"""
    for area, idx in ((opt.area, opt.index), (opt.inPlayArea, opt.inPlayIndex)):
        if area is None or idx is None:
            continue
        try:
            p = state.players[seat]
            zone = p.active if area == AreaType.ACTIVE else (
                p.bench if area == AreaType.BENCH else None)
            if zone is not None and idx < len(zone) and zone[idx] is not None:
                return zone[idx]
        except (IndexError, TypeError, AttributeError):
            pass
    return None


# メイン行動(=山/手札消費の「駆動源」になり得る行動)。サブ選択(YES/CARD/NUMBER等)の
# デルタは、同一ターン内の直近のメイン行動へ帰属させる(サーチ札の消費を起動札に付ける)。
_DRIVER_TYPES = {OptionType.PLAY, OptionType.ATTACH, OptionType.EVOLVE,
                 OptionType.ABILITY, OptionType.DISCARD, OptionType.RETREAT,
                 OptionType.ATTACK, OptionType.END}


def _action_class(o, seat, opt):
    """メイン行動の帰属クラス名(サブ選択ならNone)。"""
    state = o.current
    t = opt.type
    if t not in _DRIVER_TYPES:
        return None
    if t == OptionType.PLAY:
        try:
            cid = state.players[seat].hand[opt.index].id
        except (IndexError, TypeError, AttributeError):
            cid = "?"
        return f"PLAY:{cid}"
    if t == OptionType.ABILITY:
        pk = _pokemon_of_option(state, seat, opt)
        return f"ABILITY:{pk.id if pk else '?'}"
    if t == OptionType.EVOLVE:
        try:
            cid = (state.players[seat].hand[opt.index].id
                   if opt.area == AreaType.HAND else "?")
        except (IndexError, TypeError, AttributeError):
            cid = "?"
        return f"EVOLVE:{cid}"
    if t == OptionType.ATTACK:
        return f"ATTACK:{opt.attackId}"
    try:
        return OptionType(t).name
    except ValueError:
        return str(t)


def play_game(our_seat: int) -> dict:
    g = {
        "our_seat": our_seat, "winner": None, "reason": None, "turns": 0,
        "mulligans_us": 0, "mulligans_opp": 0,
        "ph_attacks": [],          # (b) [{turn, hand}]
        "rad_uses": [],            # (c) [{turn, deck, hand}]
        "final_deck_us": None, "final_prize_us": None, "final_prize_opp": None,
        "record_errors": 0,
    }
    # 行動クラス別 deck/hand デルタ帰属(同一ターン内のみ)
    deltas = {}   # class -> [count, deck_delta_sum, hand_delta_sum]
    prev = None   # (action_class, turn, deck, hand)
    driver = None       # 直近のメイン行動クラス(粘着)
    driver_turn = None  # その行動のターン(ターン跨ぎでリセット)

    def snapshot(o):
        ps = o.current.players[our_seat]
        return o.current.turn, ps.deckCount or 0, ps.handCount or 0

    def attribute(o):
        nonlocal prev
        if prev is None:
            return
        cls, pturn, pdeck, phand = prev
        turn, deck, hand = snapshot(o)
        if turn == pturn and cls is not None and cls != "END":
            d = deltas.setdefault(cls, [0, 0, 0])
            d[1] += deck - pdeck
            d[2] += hand - phand
        prev = None

    def record_choice(o, result):
        nonlocal prev, driver, driver_turn
        sel = o.select
        if sel is None or not sel.option:
            return
        opts = sel.option
        state = o.current
        chosen = [opts[i] for i in result if 0 <= i < len(opts)]
        if not chosen:
            return
        opt = chosen[0]
        cls = _action_class(o, our_seat, opt)
        if cls is not None:  # メイン行動: 粘着ドライバー更新+行動数カウント
            driver, driver_turn = cls, state.turn
            deltas.setdefault(cls, [0, 0, 0])[0] += 1
        else:  # サブ選択: 同一ターンの直近メイン行動に帰属
            cls = driver if driver_turn == state.turn else None
        # (b) Powerful Hand攻撃時の手札
        if opt.type == OptionType.ATTACK and opt.attackId == POWERFUL_HAND:
            g["ph_attacks"].append(
                {"turn": state.turn, "hand": state.players[our_seat].handCount or 0})
        # (c) Run Away Draw発動時の山残
        if opt.type == OptionType.ABILITY:
            pk = _pokemon_of_option(state, our_seat, opt)
            if pk is not None and pk.id == DUDUNSPARCE:
                g["rad_uses"].append(
                    {"turn": state.turn,
                     "deck": state.players[our_seat].deckCount or 0,
                     "hand": state.players[our_seat].handCount or 0})
        turn, deck, hand = snapshot(o)
        prev = (cls, turn, deck, hand)

    obs, start = battle_start(*((DECK, DECK)))
    if obs is None:
        raise RuntimeError(f"battle_start failed: errorPlayer={start.errorPlayer}")
    winner, reason = -1, None
    opp_agent = selfplay.random_agent
    try:
        for _ in range(200000):
            o = to_observation_class(obs)
            for lg in (o.logs or []):
                if lg.type == LogType.RESULT:
                    winner = lg.result
                    reason = getattr(lg, "reason", None)
                elif lg.type == LogType.HAS_BASIC_POKEMON and not lg.hasBasicPokemon:
                    key = "mulligans_us" if lg.playerIndex == our_seat else "mulligans_opp"
                    g[key] += 1
            if winner != -1:
                break
            if o.current is None or o.select is None:
                break
            if o.current.result != -1:
                winner = o.current.result
                break
            g["turns"] = max(g["turns"], o.current.turn)
            is_ours = o.current.yourIndex == our_seat
            if is_ours:
                try:
                    attribute(o)
                except Exception:
                    g["record_errors"] += 1
                try:
                    ps = o.current.players[our_seat]
                    g["final_deck_us"] = ps.deckCount
                    g["final_prize_us"] = len(ps.prize or [])
                    g["final_prize_opp"] = len(o.current.players[1 - our_seat].prize or [])
                except Exception:
                    g["record_errors"] += 1
                result = main_mod.agent(obs)
                try:
                    record_choice(o, result)
                except Exception:
                    g["record_errors"] += 1
            else:
                result = opp_agent(obs)
            obs = battle_select(result)
    finally:
        battle_finish()

    g["winner_is_us"] = (winner == our_seat)
    g["winner"] = winner
    g["reason"] = reason
    g["deltas"] = deltas
    return g


games, losses = [], 0
for i in range(MAX_GAMES):
    g = play_game(our_seat=i % 2)
    games.append(g)
    if not g["winner_is_us"]:
        losses += 1
        print(f"game {i+1}: LOSS #{losses} (reason={g['reason']}, turns={g['turns']}, "
              f"mull={g['mulligans_us']})", file=sys.stderr)
    if losses >= TARGET_LOSSES:
        break
    if (i + 1) % 25 == 0:
        print(f"game {i+1}: {losses} losses so far", file=sys.stderr)

# ---- 集計 ----
N = len(games)
wins = N - losses
errors = sum(g["record_errors"] for g in games)
loss_games = [g for g in games if not g["winner_is_us"]]

# (a) 敗因分類
acc, deckout, prizes, no_pokemon, stall, other = [], [], [], [], [], []
for g in loss_games:
    if g["mulligans_us"] > 0:
        acc.append(g)          # 第4カテゴリ: マリガン敗(事故) — 分母から除外
    elif g["reason"] == 2:
        deckout.append(g)
    elif g["reason"] == 1:
        prizes.append(g)
    elif g["reason"] == 3:
        no_pokemon.append(g)
    elif g["turns"] > 100:
        stall.append(g)
    else:
        other.append(g)

# (b) Powerful Hand手札分布
ph_all = [e["hand"] for g in games for e in g["ph_attacks"]]
ph_loss = [e["hand"] for g in loss_games for e in g["ph_attacks"]]
# 低打点敗戦: 敗戦ゲーム内の1072攻撃の平均手札<8 (攻撃ゼロも低打点扱いで別掲)
low_ph, no_ph = [], []
for g in loss_games:
    hands = [e["hand"] for e in g["ph_attacks"]]
    if not hands:
        no_ph.append(g)
    elif sum(hands) / len(hands) < 8:
        low_ph.append(g)

# (c) Run Away Draw / デルタ帰属
rad = [e for g in games for e in g["rad_uses"]]
agg = {}
for g in games:
    for cls, (c, dd, hd) in g["deltas"].items():
        a = agg.setdefault(cls, [0, 0, 0])
        a[0] += c
        a[1] += dd
        a[2] += hd

# (d) マリガン
mull_games = sum(1 for g in games if g["mulligans_us"] > 0)


def wilson(w, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = w / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - m) / d, (c + m) / d)


lo, hi = wilson(wins, N)
print(f"\n===== E3 Phase 0 probe (alakazam-e3 flag-OFF vs random mirror, N={N}) =====")
print(f"wins {wins}/{N} = {wins/N*100:.1f}% (95%CI {lo*100:.1f}-{hi*100:.1f}) "
      f"| 凍結証明(c): 既知90.0%とのCI整合を確認")
print(f"losses {losses} (target {TARGET_LOSSES}) | record_errors {errors}")
print(f"\n(a) 敗因分類 (事故=マリガン敗{len(acc)}件を分母から除外 → 分母{losses-len(acc)}):")
print(f"    山切れ(reason=2): {len(deckout)}")
print(f"    サイド負け(reason=1): {len(prizes)}")
print(f"    場空(reason=3): {len(no_pokemon)}")
print(f"    膠着(turns>100): {len(stall)}")
print(f"    その他: {len(other)} (reasons={[g['reason'] for g in other]})")
print(f"    [文脈] 敗戦ターン分布: {sorted(g['turns'] for g in loss_games)}")
print(f"    [文脈] 敗戦時サイド 自/相手: "
      f"{[(g['final_prize_us'], g['final_prize_opp']) for g in loss_games]}")
denom = losses - len(acc)
sig = len(deckout) + len(set(map(id, low_ph + no_ph)) & set(map(id, prizes + stall + other + no_pokemon)))
print(f"\n(b) Powerful Hand[1072] 攻撃時手札: 全{len(ph_all)}回 "
      f"平均{sum(ph_all)/len(ph_all):.2f}枚" if ph_all else "\n(b) 1072攻撃なし")
if ph_all:
    hist = {}
    for h in ph_all:
        hist[h] = hist.get(h, 0) + 1
    print(f"    分布: {dict(sorted(hist.items()))}")
    print(f"    敗戦ゲーム内のみ: {len(ph_loss)}回 "
          f"平均{(sum(ph_loss)/len(ph_loss)):.2f}枚" if ph_loss else "    敗戦内攻撃なし")
print(f"    敗戦のうち 1072平均手札<8: {len(low_ph)}件 / 1072攻撃ゼロ: {len(no_ph)}件")
print(f"\n(c) Run Away Draw発動: 全{len(rad)}回")
if rad:
    print(f"    発動時山残の分布: {sorted(e['deck'] for e in rad)}")
print("    行動クラス別 deck/handデルタ(同一ターン内帰属, count/Δdeck計/Δhand計/Δhand平均):")
for cls, (c, dd, hd) in sorted(agg.items(), key=lambda kv: kv[1][1]):
    print(f"      {cls:<16} n={c:<5} Δdeck={dd:<6} Δhand={hd:<6} "
          f"Δhand/act={hd/max(c,1):+.2f} Δdeck/act={dd/max(c,1):+.2f}")
print(f"\n(d) マリガン率: {mull_games}/{N} = {mull_games/N*100:.1f}% (事前情報: たね9枚≒30%)")
print(f"\n== 事前予測の判定材料: 事故除く敗戦{denom}件のうち "
      f"山切れ{len(deckout)} + 低打点(平均手札<8 or 1072ゼロ){len(low_ph)+len(no_ph)}"
      f" (重複は原データで確認)")

path = os.path.join(_HERE, "e3_phase0_result.json")
with open(path, "w") as f:
    json.dump({"n": N, "games": games}, f, indent=1, ensure_ascii=False)
print(f"\nraw -> {path}")

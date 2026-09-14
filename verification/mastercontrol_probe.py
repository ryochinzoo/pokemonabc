#!/usr/bin/env python3
"""Phase 0 プローブ: 新デッキ starmie-mastercontrol の2つの前提を、対戦ゼロ相当の少数戦で確定させる。

層S(スクリーニング/計器監査)。**引用禁止** — 勝率は見ない。見るのは「エンジンが何を提示するか」だけ。

P1: エンジンは SETUP_ACTIVE_POKEMON の候補に エースバーン(666) を載せるか。
    載せないなら 特性しゅんぱつりょく は未実装 = エースバーン4枚は完全な死に札。
P2: なみのりビーチ(1262) の「自分の番ごとに1回の水入れ替え」は、どの OptionType で提示されるか。
    ABILITY で出るなら、現行 `_choose_main` の「最初のABILITYを無条件発動」が
    毎ターン盲目的にバトル場を引っ込める = ビーチを入れる前に安全修理が必須。

実行はデッキディレクトリ(cg/ がある場所)から:
  cd src/input/datasets/decks/starmie-mastercontrol \
    && python3 ../../../../../verification/mastercontrol_probe.py 20
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))

import selfplay  # noqa: E402
import main as our_main  # noqa: E402
from cg.api import to_observation_class, all_card_data, OptionType, SelectContext, AreaType  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
# 任意: 相手ゲージ (agent.py, deck.csv)。省略時はミラー。
OPP_AGENT = sys.argv[2] if len(sys.argv) > 2 else None
OPP_DECK = sys.argv[3] if len(sys.argv) > 3 else None
CARDS = {c.cardId: c for c in all_card_data()}

CINDERACE = 666
BEACH = 1262
WALLY = 1229
STARYU = 1030
MEGA_STARMIE = 1031

# V4ロジックの「発火」カウンタ。勝率ではなく、機構が実在して動いているかを数える。
fired = Counter()
min_deck = {}   # (試合, プレイヤー) -> その試合で観測した山札の最小枚数

# --- 収集箱 -----------------------------------------------------------------
setup_active_offers = []      # 1件 = 1回の SETUP_ACTIVE_POKEMON 選択で提示されたカードID集合
setup_active_picks = Counter()  # 実際にバトル場スタートに選ばれたカードID
ability_options = Counter()   # (area, cardId) -> 回数。ABILITY オプションの正体
beach_in_play_turns = 0       # ビーチが場に出ている状態で MAIN 選択が来た回数
beach_played = 0              # ビーチを PLAY した回数
opt_type_hist = Counter()     # MAIN における OptionType の分布
cinderace_active_games = set()  # エースバーンがバトル場に立った試合番号
games_seen = set()


def _name(cid):
    c = CARDS.get(cid)
    return c.name if c else f"?{cid}"


def _resolve_card_id(obs, opt):
    """オプションが指すカードIDを解決する。スタジアム領域も見る点が main.py と違う。"""
    state = obs.current
    me = state.yourIndex if state else 0
    area = opt.area
    idx = opt.index
    try:
        if opt.type == OptionType.PLAY:
            return state.players[me].hand[idx].id
        if area == AreaType.STADIUM:
            st = state.stadium or []
            return st[0].id if st else None
        if area == AreaType.HAND:
            return state.players[me].hand[idx].id
        if area == AreaType.ACTIVE:
            pk = (state.players[me].active or [None])[0]
            return pk.id if pk else None
        if area == AreaType.BENCH:
            return state.players[me].bench[idx].id
    except (IndexError, TypeError, AttributeError):
        return None
    return None


def make_probe_agent(game_no):
    def probe_agent(obs_dict):
        try:
            obs = to_observation_class(obs_dict)
            sel = obs.select
            state = obs.current
            if sel is not None and state is not None:
                me = state.yourIndex
                ctx = sel.context

                # --- P1: 対戦準備のバトル場選択 ---
                if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
                    ids = []
                    for o in sel.option:
                        try:
                            ids.append(state.players[me].hand[o.index].id)
                        except (IndexError, TypeError, AttributeError):
                            ids.append(None)
                    setup_active_offers.append(tuple(ids))

                # --- P2 & MAIN の全景 ---
                if ctx == SelectContext.MAIN:
                    st = (state.stadium or [])
                    if st and st[0].id == BEACH:
                        global beach_in_play_turns
                        beach_in_play_turns += 1
                    for o in sel.option:
                        opt_type_hist[int(o.type)] += 1
                        if o.type == OptionType.ABILITY:
                            ability_options[(int(o.area) if o.area is not None else None,
                                             _resolve_card_id(obs, o))] += 1

                # --- L4: 山札がどこまで薄くなるか（自滅LOの到達可能性） ---
                try:
                    dc = state.players[me].deckCount
                    if dc is not None:
                        min_deck[(game_no, me)] = min(min_deck.get((game_no, me), 99), dc)
                        if dc <= 10:
                            fired["preserve_turns"] += 1
                except (IndexError, TypeError, AttributeError):
                    pass

                # --- エースバーンがバトル場に立ったか ---
                try:
                    act = (state.players[me].active or [None])[0]
                    if act is not None and act.id == CINDERACE:
                        cinderace_active_games.add(game_no)
                except (IndexError, TypeError, AttributeError):
                    pass
                games_seen.add(game_no)
        except Exception:
            pass

        picked = our_main.agent(obs_dict)

        # 選ばれた結果を後追いで記録
        try:
            obs = to_observation_class(obs_dict)
            sel, state = obs.select, obs.current
            if sel is not None and state is not None and picked:
                me = state.yourIndex
                if sel.context == SelectContext.SETUP_ACTIVE_POKEMON:
                    for i in picked:
                        try:
                            setup_active_picks[state.players[me].hand[sel.option[i].index].id] += 1
                        except (IndexError, TypeError, AttributeError):
                            pass
                elif sel.context == SelectContext.MAIN:
                    for i in picked:
                        o = sel.option[i]
                        if o.type == OptionType.PLAY:
                            try:
                                cid = state.players[me].hand[o.index].id
                            except (IndexError, TypeError, AttributeError):
                                cid = None
                            if cid == BEACH:
                                global beach_played
                                beach_played += 1
                            elif cid == WALLY:
                                fired["wally_play"] += 1
                        elif o.type == OptionType.ABILITY and o.area == AreaType.STADIUM:
                            fired["beach_switch"] += 1
                elif sel.context in (SelectContext.HEAL, SelectContext.EFFECT_TARGET):
                    for i in picked:
                        o = sel.option[i]
                        fired["heal_bench" if o.area == AreaType.BENCH else "heal_active"] += 1
                elif sel.context == SelectContext.DRAW_COUNT:
                    for i in picked:
                        num = sel.option[i].number
                        nums = [x.number for x in sel.option if x.number is not None]
                        if nums and num is not None:
                            fired["draw_max" if num == max(nums) else "draw_not_max"] += 1
        except Exception:
            pass
        return picked
    return probe_agent


def main():
    deck = selfplay.load_deck("deck.csv")
    if OPP_AGENT:
        import importlib.util
        spec = importlib.util.spec_from_file_location("opp_mod", OPP_AGENT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        opp_agent, opp_deck = mod.agent, selfplay.load_deck(OPP_DECK)
        label = OPP_AGENT.split("/")[-1]
    else:
        opp_agent, opp_deck, label = None, deck, "ミラー(自パイロット両側)"
    print(f"# starmie-mastercontrol probe / N={N} / 相手={label}")
    print(f"# deck: {len(deck)}枚, ユニーク {len(set(deck))}種")
    wins = 0
    for i in range(N):
        a = make_probe_agent(i)
        b = opp_agent if opp_agent is not None else a
        # 席を交互に入れ替える(先攻/後攻の偏りを均す)
        if i % 2 == 0:
            r = selfplay.run_match(deck, opp_deck, a, b)
            w = r["winner"]
        else:
            r = selfplay.run_match(opp_deck, deck, b, a)
            w = (1 - r["winner"]) if r["winner"] in (0, 1) else r["winner"]
        wins += 1 if w == 0 else 0
    print(f"# (層S・引用禁止) 我々の勝ち {wins}/{N}")

    print()
    print("=" * 70)
    print("P1: SETUP_ACTIVE_POKEMON の候補にエースバーン(666)は載るか")
    print("=" * 70)
    n_off = len(setup_active_offers)
    with_c = sum(1 for ids in setup_active_offers if CINDERACE in ids)
    print(f"  SETUP_ACTIVE_POKEMON 選択の回数: {n_off}")
    print(f"  うちエースバーンが候補に載った回数: {with_c}  ({100.0 * with_c / n_off if n_off else 0:.1f}%)")
    print(f"  → P1 = {'TRUE (特性しゅんぱつりょくは実装されている)' if with_c else 'FALSE (載らない = 死に札)'}")
    print("  バトル場スタートに選ばれたカード:")
    for cid, k in setup_active_picks.most_common():
        print(f"    {k:5d}  {cid:5d}  {_name(cid)}")
    print(f"  エースバーンがバトル場に立った試合: {len(cinderace_active_games)}/{len(games_seen)}")

    print()
    print("=" * 70)
    print("P2: なみのりビーチ(1262) の入れ替えはどう提示されるか")
    print("=" * 70)
    print(f"  ビーチを PLAY した回数: {beach_played}")
    print(f"  ビーチが場にある状態での MAIN 選択回数: {beach_in_play_turns}")
    print("  MAIN で観測された ABILITY オプション (area, cardId) -> 回数:")
    if not ability_options:
        print("    (なし)")
    for (area, cid), k in ability_options.most_common():
        tag = " ★ビーチ" if cid == BEACH else ""
        print(f"    area={area} cid={cid} {_name(cid) if cid else '?'} : {k}{tag}")
    beach_ability = sum(k for (area, cid), k in ability_options.items() if cid == BEACH)
    print(f"  → P2 = {'ABILITY で提示される (安全修理が必須)' if beach_ability else 'ABILITY では提示されない'}")

    print()
    print("  MAIN の OptionType 分布:")
    names = {int(t): t.name for t in OptionType}
    for t, k in opt_type_hist.most_common():
        print(f"    {names.get(t, t):20s} {k}")

    print()
    print("=" * 70)
    print("V4 ロジックの発火カウント (env: " + (
        ", ".join(k for k in os.environ if k.startswith("V4_NO_")) or "全ON") + ")")
    print("=" * 70)
    beach_offered = sum(k for (area, cid), k in ability_options.items() if cid == BEACH)
    print(f"  L1 エースバーン: 候補提示 {with_c} / 選択 {setup_active_picks[CINDERACE]} / "
          f"バトル場に立った試合 {len(cinderace_active_games)}/{len(games_seen)}")
    print(f"  L2 ビーチ入れ替え: 提示 {beach_offered} / 発動 {fired['beach_switch']} "
          f"({100.0 * fired['beach_switch'] / beach_offered if beach_offered else 0:.1f}%)")
    print(f"  L3 ミツル: プレイ {fired['wally_play']} / "
          f"回復対象 ベンチ {fired['heal_bench']} : バトル場 {fired['heal_active']}")
    print(f"  L4 ドロー枚数選択: 最大 {fired['draw_max']} / 最大でない {fired['draw_not_max']}")
    if min_deck:
        vals = sorted(min_deck.values())
        le10 = sum(1 for v in vals if v <= 10)
        le5 = sum(1 for v in vals if v <= 5)
        print(f"     山札の最小枚数: 中央値 {vals[len(vals)//2]} / 最小 {vals[0]} / "
              f"10枚以下に落ちた側 {le10}/{len(vals)} / 5枚以下 {le5}/{len(vals)}")
        print(f"     山札10枚以下での判断回数: {fired['preserve_turns']}")


if __name__ == "__main__":
    main()

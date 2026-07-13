"""Grimmsnarl型デッキ用のスクリプトAI（貪欲法）= 2つ目の標準仮想敵。

環境シェア約半分と観測した Marnie's Grimmsnarl ex 型の再現。
勝ち筋: 進化(Punk Upで悪エネ5枚一括加速) → Shadow Bullet 180+ベンチ30 連打。
構造は alakazam_agent と同じ「進化 > 能力 > プレイ > エネ貼り > 攻撃」の貪欲法。
"""

from cg.api import (
    Observation,
    to_observation_class,
    SelectType,
    SelectContext,
    OptionType,
    AreaType,
)

IMPIDIMP, MORGREM, GRIMMSNARL = 646, 647, 648
DUNSPARCE, DUDUNSPARCE = 65, 66
RARE_CANDY, ULTRA_BALL, NIGHT_STRETCHER = 1079, 1121, 1097
DARK_ENERGY = 7
SHADOW_BULLET = 937

PLAY_PRIORITY = [IMPIDIMP, DUNSPARCE, RARE_CANDY, 1224, 1236, 1214, 1097, 1182, 1121]
SEARCH_PRIORITY = [GRIMMSNARL, RARE_CANDY, MORGREM, DUDUNSPARCE, IMPIDIMP, DUNSPARCE, DARK_ENERGY]
DISCARD_PRIORITY = [DARK_ENERGY, 1121, 1214, 1097, 1224, 1236, 1182]
# エネを貼る/送る先の優先度（Punk Upの5枚配分にも効く）
ATTACH_TARGET_PRIORITY = [GRIMMSNARL, MORGREM, IMPIDIMP]

COST_CONTEXTS = {
    SelectContext.DISCARD,
    SelectContext.TO_DECK,
    SelectContext.TO_DECK_BOTTOM,
    SelectContext.TO_PRIZE,
    SelectContext.DISCARD_ENERGY_CARD,
    SelectContext.DISCARD_TOOL_CARD,
    SelectContext.DISCARD_CARD_OR_ATTACHED_CARD,
    SelectContext.DISCARD_ENERGY,
}


def _pokemon_at(state, player_index, area, index):
    try:
        p = state.players[player_index]
        if area == AreaType.ACTIVE:
            return p.active[index]
        if area == AreaType.BENCH:
            return p.bench[index]
    except (IndexError, TypeError):
        pass
    return None


def _card_id_of_option(obs: Observation, opt):
    state = obs.current
    sel = obs.select
    try:
        if opt.area == AreaType.HAND:
            hand = state.players[opt.playerIndex].hand
            return hand[opt.index].id if hand else None
        if opt.area == AreaType.DECK:
            return sel.deck[opt.index].id if sel.deck else None
        if opt.area == AreaType.DISCARD:
            return state.players[opt.playerIndex].discard[opt.index].id
        if opt.area == AreaType.LOOKING:
            card = state.looking[opt.index] if state.looking else None
            return card.id if card else None
        if opt.area in (AreaType.ACTIVE, AreaType.BENCH):
            pk = _pokemon_at(state, opt.playerIndex, opt.area, opt.index)
            return pk.id if pk else None
    except (IndexError, TypeError, AttributeError):
        pass
    return None


def _rank(card_id, priority):
    return priority.index(card_id) if card_id in priority else len(priority)


def _choose_main(obs: Observation) -> int:
    state = obs.current
    me = state.yourIndex
    options = obs.select.option

    def find(pred):
        for i, o in enumerate(options):
            if pred(o):
                return i
        return None

    # 1. 進化（Grimmsnarl直行=Punk Upが最優先）
    for target in (GRIMMSNARL, DUDUNSPARCE, MORGREM):
        idx = find(
            lambda o, t=target: o.type == OptionType.EVOLVE and _card_id_of_option(obs, o) == t
        )
        if idx is not None:
            return idx
    idx = find(lambda o: o.type == OptionType.EVOLVE)
    if idx is not None:
        return idx

    # 2. 能力（Run Away Draw）
    idx = find(lambda o: o.type == OptionType.ABILITY)
    if idx is not None:
        return idx

    # 3. 手札から出す
    best, best_rank = None, len(PLAY_PRIORITY)
    for i, o in enumerate(options):
        if o.type != OptionType.PLAY:
            continue
        hand = state.players[me].hand
        cid = hand[o.index].id if hand and o.index < len(hand) else None
        r = _rank(cid, PLAY_PRIORITY)
        if r < best_rank:
            best, best_rank = i, r
    if best is not None:
        return best

    # 4. エネ貼り（Grimmsnarl > Morgrem > Impidimp）
    for target in ATTACH_TARGET_PRIORITY:
        idx = find(
            lambda o, t=target: (
                o.type == OptionType.ATTACH
                and (pk := _pokemon_at(state, me, o.inPlayArea, o.inPlayIndex))
                and pk.id == t
            )
        )
        if idx is not None:
            return idx
    idx = find(lambda o: o.type == OptionType.ATTACH)
    if idx is not None:
        return idx

    # 5. 攻撃（Shadow Bullet 最優先）
    idx = find(lambda o: o.type == OptionType.ATTACK and o.attackId == SHADOW_BULLET)
    if idx is not None:
        return idx
    idx = find(lambda o: o.type == OptionType.ATTACK)
    if idx is not None:
        return idx

    idx = find(lambda o: o.type == OptionType.END)
    if idx is not None:
        return idx
    return 0


def _choose_cards(obs: Observation) -> list[int]:
    sel = obs.select
    state = obs.current
    options = sel.option
    is_cost = sel.context in COST_CONTEXTS
    count = sel.minCount if is_cost else sel.maxCount
    count = max(sel.minCount, min(count, sel.maxCount, len(options)))

    # Punk Up等の「ポケモンに付ける/送る先」はアタッカー優先
    if sel.context in (SelectContext.ATTACH_FROM, SelectContext.EFFECT_TARGET):
        ranked = sorted(
            range(len(options)),
            key=lambda i: _rank(_card_id_of_option(obs, options[i]), ATTACH_TARGET_PRIORITY),
        )
        return ranked[:count]

    priority = DISCARD_PRIORITY if is_cost else SEARCH_PRIORITY
    ranked = sorted(
        range(len(options)),
        key=lambda i: _rank(_card_id_of_option(obs, options[i]), priority),
    )
    return ranked[:count]


def agent(obs_dict: dict) -> list[int]:
    obs: Observation = to_observation_class(obs_dict)
    if obs.select is None:
        raise RuntimeError("deck must be passed to battle_start in local play")
    sel = obs.select
    try:
        if sel.type == SelectType.MAIN:
            return [_choose_main(obs)]
        if sel.type == SelectType.YES_NO:
            yes = next((i for i, o in enumerate(sel.option) if o.type == OptionType.YES), 0)
            return [yes]
        if sel.type == SelectType.ATTACK:
            for i, o in enumerate(sel.option):
                if o.attackId == SHADOW_BULLET:
                    return [i]
            return [0]
        if sel.type == SelectType.COUNT:
            best = max(
                range(len(sel.option)),
                key=lambda i: sel.option[i].number if sel.option[i].number is not None else 0,
            )
            return [best]
        if sel.type in (
            SelectType.CARD,
            SelectType.ATTACHED_CARD,
            SelectType.CARD_OR_ATTACHED_CARD,
        ):
            return _choose_cards(obs)
        k = max(sel.minCount, min(1, sel.maxCount))
        return list(range(k))
    except Exception:
        k = max(sel.minCount, min(1, sel.maxCount))
        return list(range(k))

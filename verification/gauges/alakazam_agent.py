"""Alakazam型デッキ用のスクリプトAI（貪欲法）。

偵察で確認したLB上位型（Alakazam + Dudunsparce）を再現するための最小の意思決定。
狙いは2つ:
  1. cabt実機でキーカード挙動（Psychic Draw / Powerful Hand / Run Away Draw /
     ふしぎなアメ）が成立するかの検証に使う。
  2. 成立したら、そのまま bench の標準仮想敵（メタ再現の相手）として使う。

方針は「進化できるなら進化 > 能力 > カードを出す > エネ貼り > 攻撃 > 番を返す」。
Alakazam型は貪欲法がほぼ最適に一致する構造（進化トリガーで手札とダメージが伸びる）
なので、この単純さ自体がアーキタイプ検証になっている。
"""

from cg.api import (
    Observation,
    to_observation_class,
    SelectType,
    SelectContext,
    OptionType,
    AreaType,
)

# ID定数（decks/alakazam_v0.csv と対応）
ABRA, KADABRA, ALAKAZAM = 741, 742, 743
DUNSPARCE, DUDUNSPARCE = 65, 66
RARE_CANDY, ULTRA_BALL, NIGHT_STRETCHER = 1079, 1121, 1097
PSYCHIC_ENERGY = 5
POWERFUL_HAND_ATTACK_ID = 1072

# 手札から出す/探す時の優先度（先頭ほど優先）
PLAY_PRIORITY = [ABRA, DUNSPARCE, RARE_CANDY, 1231, 1224, 1236, 1214, 1181, 1097, 1182, 1121]
SEARCH_PRIORITY = [ALAKAZAM, RARE_CANDY, KADABRA, DUDUNSPARCE, ABRA, DUNSPARCE, PSYCHIC_ENERGY]
# コスト（捨てる/山に戻す）で手放してよい順
DISCARD_PRIORITY = [PSYCHIC_ENERGY, 1121, 1214, 1181, 1097, 1231, 1182, 1224, 1236]

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
    """場のポケモンを (area, index) から引く。見つからなければ None。"""
    try:
        p = state.players[player_index]
        if area == AreaType.ACTIVE:
            return p.active[index]
        if area == AreaType.BENCH:
            return p.bench[index]
    except (IndexError, TypeError):
        pass
    return None


def _card_id_of_option(obs: Observation, opt) -> int | None:
    """CARD系オプションが指すカードIDを解決する。分からなければ None。"""
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
    """メイン選択: 進化 > 能力 > プレイ > エネ貼り > 攻撃 > 番を返す。"""
    state = obs.current
    me = state.yourIndex
    options = obs.select.option

    def find(pred):
        for i, o in enumerate(options):
            if pred(i, o):
                return i
        return None

    # 1. 進化（Alakazam直行を最優先。進化トリガーのドローが目的）
    for target in (ALAKAZAM, DUDUNSPARCE, KADABRA):
        idx = find(
            lambda i, o: o.type == OptionType.EVOLVE and _card_id_of_option(obs, o) == target
        )
        if idx is not None:
            return idx
    idx = find(lambda i, o: o.type == OptionType.EVOLVE)
    if idx is not None:
        return idx

    # 2. 能力（Run Away Draw = Dudunsparce を優先）
    idx = find(
        lambda i, o: o.type == OptionType.ABILITY and _card_id_of_option(obs, o) == DUDUNSPARCE
    )
    if idx is not None:
        return idx
    idx = find(lambda i, o: o.type == OptionType.ABILITY)
    if idx is not None:
        return idx

    # 3. 手札から出す（優先度表に従う。表にない札は出さない=手札に温存して打点にする）
    best = None
    best_rank = len(PLAY_PRIORITY)
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

    # 4. エネ貼り（Alakazam > Kadabra > Abra の順で優先）
    for target in (ALAKAZAM, KADABRA, ABRA):
        idx = find(
            lambda i, o: (
                o.type == OptionType.ATTACH
                and (pk := _pokemon_at(state, me, o.inPlayArea, o.inPlayIndex))
                and pk.id == target
            )
        )
        if idx is not None:
            return idx
    idx = find(lambda i, o: o.type == OptionType.ATTACH)
    if idx is not None:
        return idx

    # 5. 攻撃（Powerful Hand 最優先）
    idx = find(lambda i, o: o.type == OptionType.ATTACK and o.attackId == POWERFUL_HAND_ATTACK_ID)
    if idx is not None:
        return idx
    idx = find(lambda i, o: o.type == OptionType.ATTACK)
    if idx is not None:
        return idx

    # 6. 番を返す
    idx = find(lambda i, o: o.type == OptionType.END)
    if idx is not None:
        return idx
    return 0


def _choose_cards(obs: Observation) -> list[int]:
    """CARD系選択: 文脈がコストなら最小数を安い順に、利得なら最大数を高い順に。"""
    sel = obs.select
    options = sel.option
    is_cost = sel.context in COST_CONTEXTS
    count = sel.minCount if is_cost else sel.maxCount
    count = max(sel.minCount, min(count, sel.maxCount, len(options)))
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
            # 能力の発動・先攻選択・コイン表choiceは常にYES
            yes = next((i for i, o in enumerate(sel.option) if o.type == OptionType.YES), 0)
            return [yes]
        if sel.type == SelectType.ATTACK:
            for i, o in enumerate(sel.option):
                if o.attackId == POWERFUL_HAND_ATTACK_ID:
                    return [i]
            return [0]
        if sel.type == SelectType.COUNT:
            # 引く枚数/ダメカン数などは常に最大を選ぶ
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
        # ENERGY / SKILL / EVOLVE / SPECIAL_CONDITION / 未知の型: 先頭から必要数
        k = max(sel.minCount, min(1, sel.maxCount)) or sel.minCount
        k = max(sel.minCount, min(k, sel.maxCount))
        return list(range(k))
    except Exception:
        # 検証用でも合法手だけは絶対に返す（大会ハード要件と同じ姿勢）
        k = max(sel.minCount, min(1, sel.maxCount))
        return list(range(k))

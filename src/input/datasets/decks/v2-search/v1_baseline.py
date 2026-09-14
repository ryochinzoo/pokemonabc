import os

from cg.api import (
    AreaType,
    CardType,
    Observation,
    OptionType,
    SelectContext,
    SelectType,
    all_attack,
    all_card_data,
    to_observation_class,
)


def read_deck_csv() -> list[int]:
    """Read deck.csv.

    Returns:
        list[int]: A list of card IDs in the deck.
    """
    file_path = "deck.csv"
    if not os.path.exists(file_path):
        file_path = "/kaggle_simulations/agent/" + file_path
    with open(file_path, "r") as file:
        csv = file.read().split("\n")
    deck = []
    for i in range(60):
        deck.append(int(csv[i]))
    return deck


# ---------------------------------------------------------------------------
# カード/ワザの静的データ（初回アクセス時に1度だけエンジンから取得）
# ---------------------------------------------------------------------------

_CARDS = None  # dict[int, CardData]
_ATTACKS = None  # dict[int, Attack]

# ダメージがワザの damage 欄に現れない「スケーリングワザ」の補正表。
# 値は (状態, 自分番号) -> 追加ダメージ。環境で観測した主要打点のみ登録し、
# 未登録のワザは damage 欄の値で評価する（未知ワザでも落ちない）。
# 1072 = Alakazam「Powerful Hand」: 手札×20のダメカン乗せ。
_SCALING_DAMAGE = {
    1072: lambda state, me: state.players[me].handCount * 20,
}
# ダメカン「乗せ」のワザ。弱点・抵抗・軽減の計算を通らない別レーンで扱う。
_PLACEMENT_ATTACKS = {1072}


def _card_db():
    global _CARDS, _ATTACKS
    if _CARDS is None:
        _CARDS = {c.cardId: c for c in all_card_data()}
        _ATTACKS = {a.attackId: a for a in all_attack()}
    return _CARDS, _ATTACKS


# ---------------------------------------------------------------------------
# 盤面の読み取りヘルパ（全て「分からなければ None / 0」で落ちない）
# ---------------------------------------------------------------------------


def _pokemon_at(state, player_index, area, index):
    try:
        p = state.players[player_index]
        if area == AreaType.ACTIVE:
            return p.active[index]
        if area == AreaType.BENCH:
            return p.bench[index]
    except (IndexError, TypeError, AttributeError):
        pass
    return None


def _card_id_of_option(obs: Observation, opt) -> int | None:
    """CARD系オプションが指すカードIDを解決する。"""
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
        if opt.area == AreaType.PRIZE:
            card = state.players[opt.playerIndex].prize[opt.index]
            return card.id if card else None
    except (IndexError, TypeError, AttributeError):
        pass
    return None


def _estimate_damage(attack_id: int, state, me: int) -> int:
    """自分のバトルポケモンがこのワザで相手バトルポケモンに与えるダメージ見積り。

    ダメカン乗せ(_PLACEMENT_ATTACKS)は弱点・抵抗を通らない別レーンで計算する。
    """
    cards, attacks = _card_db()
    atk = attacks.get(attack_id)
    dmg = atk.damage if atk else 0
    bonus = _SCALING_DAMAGE.get(attack_id)
    if bonus is not None:
        try:
            dmg += bonus(state, me)
        except Exception:
            pass
    if attack_id in _PLACEMENT_ATTACKS:
        return dmg  # 乗せダメージ: 弱点・抵抗の適用なし

    try:
        my_active = state.players[me].active[0]
        opp_active = state.players[1 - me].active[0]
        if my_active is None or opp_active is None:
            return dmg
        attacker = cards.get(my_active.id)
        defender = cards.get(opp_active.id)
        if attacker and defender and dmg > 0:
            if defender.weakness is not None and defender.weakness == attacker.energyType:
                dmg *= 2
            if defender.resistance is not None and defender.resistance == attacker.energyType:
                dmg = max(0, dmg - 30)
    except (IndexError, TypeError, AttributeError):
        pass
    return dmg


def _opp_active_hp(state, me: int) -> int | None:
    try:
        opp = state.players[1 - me].active[0]
        return opp.hp if opp else None
    except (IndexError, TypeError, AttributeError):
        return None


def _best_attack_damage_of_card(card_id: int) -> int:
    """カードが持つワザの最大基礎ダメージ（エネ貼り先の価値付けに使う）。"""
    cards, attacks = _card_db()
    c = cards.get(card_id)
    if not c:
        return 0
    best = 0
    for aid in c.attacks:
        a = attacks.get(aid)
        if a:
            best = max(best, a.damage)
        if aid in _SCALING_DAMAGE:
            best = max(best, 120)  # スケーリングワザは高価値とみなす固定見積り
    return best


# ---------------------------------------------------------------------------
# 各選択の方針
# ---------------------------------------------------------------------------

# コスト（手放す）系の文脈。最小数だけ、価値の低い順に払う。
_COST_CONTEXTS = {
    SelectContext.DISCARD,
    SelectContext.TO_DECK,
    SelectContext.TO_DECK_BOTTOM,
    SelectContext.TO_PRIZE,
    SelectContext.DISCARD_ENERGY_CARD,
    SelectContext.DISCARD_TOOL_CARD,
    SelectContext.DISCARD_CARD_OR_ATTACHED_CARD,
    SelectContext.DISCARD_ENERGY,
}


def _discard_value(obs: Observation, opt) -> int:
    """コストとして手放すときの惜しさ（小さいほど先に手放す）。"""
    cards, _ = _card_db()
    cid = _card_id_of_option(obs, opt)
    c = cards.get(cid) if cid is not None else None
    if c is None:
        return 2
    if c.cardType == CardType.BASIC_ENERGY:
        return 0
    if c.cardType in (CardType.ITEM, CardType.TOOL, CardType.STADIUM):
        return 1
    if c.cardType == CardType.SUPPORTER:
        return 2
    return 3  # ポケモンは最後まで残す


def _gain_value(obs: Observation, opt) -> int:
    """手札に加える/場に出すときの価値（小さいほど優先）。"""
    cards, _ = _card_db()
    state = obs.current
    me = state.yourIndex if state else 0
    cid = _card_id_of_option(obs, opt)
    c = cards.get(cid) if cid is not None else None
    if c is None:
        return 5
    if c.cardType == CardType.POKEMON:
        # 自分の場のポケモンの進化先なら最優先
        try:
            in_play = [p.id for p in state.players[me].bench] + [
                p.id for p in state.players[me].active if p
            ]
            for pid in in_play:
                pc = cards.get(pid)
                if pc and c.evolvesFrom and c.evolvesFrom == pc.name:
                    return 0
        except (TypeError, AttributeError):
            pass
        return 1
    if c.cardType in (CardType.ITEM, CardType.SUPPORTER):
        return 2
    if c.cardType == CardType.BASIC_ENERGY:
        return 3
    return 4


def _pokemon_value_for_active(state, me: int, opt) -> tuple:
    """バトル場に出すポケモンの評価（エネが付いている>打点が高い>HPが高い）。"""
    pk = _pokemon_at(
        state, opt.playerIndex if opt.playerIndex is not None else me, opt.area, opt.index
    )
    if pk is None:
        return (0, 0, 0)
    energy = len(pk.energies) if pk.energies else 0
    return (energy, _best_attack_damage_of_card(pk.id), pk.hp or 0)


def _choose_main(obs: Observation) -> list[int]:
    """メイン選択: 進化 > 能力 > プレイ > エネ貼り > 攻撃 > 番を返す。"""
    state = obs.current
    me = state.yourIndex
    options = obs.select.option
    cards, _ = _card_db()

    def first(pred):
        for i, o in enumerate(options):
            if pred(o):
                return i
        return None

    # 1. 進化（進化トリガー能力・HP増を無条件で取る。環境2強の核であり損が少ない）
    evolve_best, evolve_hp = None, -1
    for i, o in enumerate(options):
        if o.type == OptionType.EVOLVE:
            cid = _card_id_of_option(obs, o)
            c = cards.get(cid) if cid else None
            hp = c.hp if c else 0
            if hp > evolve_hp:
                evolve_best, evolve_hp = i, hp
    if evolve_best is not None:
        return [evolve_best]

    # 2. 能力（提示されている=使用可能。原則すべて使う）
    idx = first(lambda o: o.type == OptionType.ABILITY)
    if idx is not None:
        return [idx]

    # 3. 手札から出す（ポケモン > グッズ/スタジアム/どうぐ > サポート）
    play_best, play_rank = None, 99
    for i, o in enumerate(options):
        if o.type != OptionType.PLAY:
            continue
        try:
            cid = state.players[me].hand[o.index].id
        except (IndexError, TypeError, AttributeError):
            cid = None
        c = cards.get(cid) if cid else None
        if c is None:
            rank = 4
        elif c.cardType == CardType.POKEMON:
            rank = 0
        elif c.cardType in (CardType.ITEM, CardType.STADIUM, CardType.TOOL):
            rank = 1
        elif c.cardType == CardType.SUPPORTER:
            rank = 2
        else:
            rank = 3
        if rank < play_rank:
            play_best, play_rank = i, rank
    if play_best is not None:
        return [play_best]

    # 4. エネ貼り（最も打点の高いポケモンに。同点ならバトル場優先）
    attach_best, attach_key = None, (-1, -1)
    for i, o in enumerate(options):
        if o.type != OptionType.ATTACH:
            continue
        pk = _pokemon_at(state, me, o.inPlayArea, o.inPlayIndex)
        dmg = _best_attack_damage_of_card(pk.id) if pk else 0
        is_active = 1 if o.inPlayArea == AreaType.ACTIVE else 0
        if (dmg, is_active) > attach_key:
            attach_best, attach_key = i, (dmg, is_active)
    if attach_best is not None:
        return [attach_best]

    # 5. 攻撃（見積りダメージ最大。リーサルなら最優先）
    attack_best, attack_dmg = None, -1
    opp_hp = _opp_active_hp(state, me)
    for i, o in enumerate(options):
        if o.type != OptionType.ATTACK or o.attackId is None:
            continue
        dmg = _estimate_damage(o.attackId, state, me)
        if opp_hp is not None and dmg >= opp_hp:
            dmg += 10000  # リーサルは他のすべてに優先
        if dmg > attack_dmg:
            attack_best, attack_dmg = i, dmg
    if attack_best is not None:
        return [attack_best]

    # 6. 番を返す
    idx = first(lambda o: o.type == OptionType.END)
    if idx is not None:
        return [idx]
    return [0]


def _choose_cards(obs: Observation) -> list[int]:
    """CARD系選択: 文脈がコストなら最小数を安い順、利得なら最大数を価値順。"""
    sel = obs.select
    state = obs.current
    me = state.yourIndex if state else 0
    options = sel.option
    n = len(options)

    ctx = sel.context
    if ctx in _COST_CONTEXTS:
        count = max(sel.minCount, 0)
        ranked = sorted(range(n), key=lambda i: _discard_value(obs, options[i]))
        return ranked[:count]

    # 相手にダメージ/ダメカンを置く: HPが低い順（KOを最大化）
    if ctx in (
        SelectContext.DAMAGE_COUNTER,
        SelectContext.DAMAGE_COUNTER_ANY,
        SelectContext.DAMAGE,
    ):

        def hp_of(i):
            o = options[i]
            pk = _pokemon_at(state, o.playerIndex, o.area, o.index)
            return pk.hp if pk and pk.hp is not None else 9999

        count = max(sel.minCount, min(sel.maxCount, n))
        return sorted(range(n), key=hp_of)[:count]

    # 回復系: 自分のダメージが大きい順
    if ctx in (SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER):

        def dmg_taken(i):
            o = options[i]
            pk = _pokemon_at(state, o.playerIndex, o.area, o.index)
            if pk and pk.hp is not None and pk.maxHp is not None:
                return -(pk.maxHp - pk.hp)
            return 0

        count = max(sel.minCount, min(sel.maxCount, n))
        return sorted(range(n), key=dmg_taken)[:count]

    # バトル場に出す/入れ替え: エネ付き・高打点を前に
    if ctx in (
        SelectContext.TO_ACTIVE,
        SelectContext.SWITCH,
        SelectContext.SETUP_ACTIVE_POKEMON,
    ):
        count = max(sel.minCount, min(1, sel.maxCount)) or max(sel.minCount, 0)
        ranked = sorted(
            range(n),
            key=lambda i: _pokemon_value_for_active(state, me, options[i]),
            reverse=True,
        )
        return ranked[:count]

    # それ以外（サーチ・手札加え・ベンチ展開など）: 最大数を価値順で
    count = max(sel.minCount, min(sel.maxCount, n))
    ranked = sorted(range(n), key=lambda i: _gain_value(obs, options[i]))
    return ranked[:count]


def _choose_attack_options(obs: Observation) -> list[int]:
    """ATTACK型の選択（使うワザ/無効化するワザ）: ダメージ見積り最大を選ぶ。"""
    sel = obs.select
    state = obs.current
    me = state.yourIndex if state else 0

    def dmg_of(i):
        o = sel.option[i]
        return _estimate_damage(o.attackId, state, me) if o.attackId is not None else 0

    ranked = sorted(range(len(sel.option)), key=dmg_of, reverse=True)
    k = max(sel.minCount, min(1, sel.maxCount))
    return ranked[:k]


def _fallback(sel) -> list[int]:
    """絶対に合法な選択（考えるのを諦めたときの最後の砦）。"""
    k = max(sel.minCount, min(1, sel.maxCount))
    return list(range(k))


def agent(obs_dict: dict) -> list[int]:
    """Implement Your Pokémon Trading Card Game Agent.

    Each element in the returned list must be >= 0 and < len(obs.select.option).
    The list length must be between obs.select.minCount and obs.select.maxCount (inclusive), with no duplicate elements.

    Returns:
        list[int]: A list of option index.
    """
    obs: Observation = to_observation_class(obs_dict)
    if obs.select == None:
        # In the initial selection, the obs.select is None, and it is necessary to return the deck.
        # The deck is a list of 60 card IDs.
        # The deck must comply with the Pokémon Trading Card Game rules.
        return read_deck_csv()

    sel = obs.select
    try:
        if sel.type == SelectType.MAIN:
            return _choose_main(obs)
        if sel.type == SelectType.YES_NO:
            yes = next(
                (i for i, o in enumerate(sel.option) if o.type == OptionType.YES),
                None,
            )
            return [yes] if yes is not None else _fallback(sel)
        if sel.type == SelectType.ATTACK:
            return _choose_attack_options(obs)
        if sel.type == SelectType.COUNT:
            # 引く枚数・ダメカン数などは最大を選ぶ
            ranked = sorted(
                range(len(sel.option)),
                key=lambda i: sel.option[i].number if sel.option[i].number is not None else 0,
                reverse=True,
            )
            k = max(sel.minCount, min(1, sel.maxCount))
            return ranked[:k]
        if sel.type in (
            SelectType.CARD,
            SelectType.ATTACHED_CARD,
            SelectType.CARD_OR_ATTACHED_CARD,
        ):
            result = _choose_cards(obs)
            # 契約の最終確認（範囲・重複・数）を満たさない場合は安全側に落とす
            if (
                sel.minCount <= len(result) <= sel.maxCount
                and len(set(result)) == len(result)
                and all(0 <= r < len(sel.option) for r in result)
            ):
                return result
            return _fallback(sel)
        # ENERGY / SKILL / EVOLVE / SPECIAL_CONDITION / 未知のSelectType
        return _fallback(sel)
    except Exception:
        # どんな内部エラーでも合法手は必ず返す（大会ハード要件）
        return _fallback(sel)

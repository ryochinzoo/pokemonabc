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

_TR_PREFIX = "Team Rocket's"


def _trfix_on() -> bool:
    """2026-08-06 の修理束のON/OFF（アブレーション用）。既定はON。"""
    return not os.environ.get("V3_NO_TRFIX")


def _my_pokemon_in_play(state, me):
    """自分の場（バトル場＋ベンチ）のポケモンを列挙する。"""
    try:
        p = state.players[me]
        for zone in (p.active, p.bench):
            for pk in zone or []:
                if pk is not None:
                    yield pk
    except (IndexError, TypeError, AttributeError):
        return


def _tr_in_play_count(state, me) -> int:
    """場の「ロケット団の」ポケモンの数（Rocket Rush の打点はこれに比例する）。"""
    cards, _ = _card_db()
    n = 0
    for pk in _my_pokemon_in_play(state, me):
        c = cards.get(pk.id)
        if c and (c.name or "").startswith(_TR_PREFIX):
            n += 1
    return n


def _bench_tr_damage(state, me) -> int:
    """ベンチのロケット団ポケモンが背負っているダメカンの最大量。

    Rocket Mirror は「ベンチのロケット団1体のダメカンを全部相手バトル場へ移す」。
    どの個体から移すかは後続の CARD 選択が決めるので、ここでは上界（最大値）を返す。
    """
    cards, _ = _card_db()
    best = 0
    try:
        for pk in state.players[me].bench or []:
            if pk is None or pk.hp is None or pk.maxHp is None:
                continue
            c = cards.get(pk.id)
            if c and (c.name or "").startswith(_TR_PREFIX):
                best = max(best, pk.maxHp - pk.hp)
    except (IndexError, TypeError, AttributeError):
        pass
    return best


# ダメージがワザの damage 欄に現れない「スケーリングワザ」の補正表。
# 値は (状態, 自分番号) -> 追加ダメージ。環境で観測した主要打点のみ登録し、
# 未登録のワザは damage 欄の値で評価する（未知ワザでも落ちない）。
# 1072 = Alakazam「Powerful Hand」: 手札×20のダメカン乗せ。
# 560  = Spidops「Rocket Rush」: 場のロケット団の数×30。**通常ダメージなので弱点を通す**
#        （対 Marnie's Grimmsnarl ex は HP320・草弱点で、盤面6体=180×2=360 が一撃圏）。
# 609  = Wobbuffet「Rocket Mirror」: ベンチのダメカンを相手バトル場へ移す＝乗せレーン。
_SCALING_DAMAGE = {
    1072: lambda state, me: state.players[me].handCount * 20,
    560: lambda state, me: _tr_in_play_count(state, me) * 30 if _trfix_on() else 0,
    609: lambda state, me: _bench_tr_damage(state, me) if _trfix_on() else 0,
}
# 修理束をOFFにしたとき、価値付け側（_best_attack_damage_of_card の固定120）も
# 元の挙動に戻すために、キー集合を分けて持っておく。
_TRFIX_SCALING = {560, 609}
# ダメカン「乗せ」のワザ。弱点・抵抗・軽減の計算を通らない別レーンで扱う。
# 560 は**入れない**（素点に弱点が乗る本物のダメージ）。609 は入れる（移動＝乗せ）。
_PLACEMENT_ATTACKS = {1072, 609}

# 「効果を無視」するワザ: 相手バトルポケモンにかかる効果・弱点・抵抗を通らない。
# 1488 = Mega Starmie「Nebula Beam」(実機検証: 壁Crustleに43/43でKO — data.md 2026-07-20)
_EFFECT_IGNORING_ATTACKS = {1488}

# Ignition Energy: 進化ポケモンに付いている間だけ{C}{C}{C}を供給し、ターン終了時に破棄。
# バトル場のMega Starmie ex(進化)に貼れば即Nebula Beam(210)が撃てる使い切り札。
_IGNITION_ID = 17

# ex/メガのワザの全ダメージを防ぐ「壁」能力の持ち主(初回アクセス時にテキストから抽出)。
# 345=Crustle「Mysterious Rock Inn」(Jetting Blow 0ダメ×203の実測)/ 330=Sylveon「Safeguard」
_EX_WALL_IDS = None

# ---------------------------------------------------------------------------
# V4: starmie-mastercontrol 専用ロジック (2026-08-10)
#   L1 エースバーン(666)の初手バトル場スタート
#   L2 なみのりビーチ(1262)の無償入れ替え ＋ ABILITY無条件発動の安全修理
#   L3 ミツルの思いやり(1229)の2段回復ループ
#   L4 自滅LO(山札切れ)防御
# すべて env で個別にOFFにできる(playbook §3「新機構は必ずフラグでオフ可能に」)。
# 既定は全ON。OFF にすると pilotfix と同じ挙動に戻る。
# ---------------------------------------------------------------------------

# エースバーン: 2進化だが特性「しゅんぱつりょく」で対戦準備にバトル場へ直接出せる。
# HP160 / にげる0 / ワザ「フレアターボ」= コスト1で50点 + 山札から基本エネ3枚をベンチへ。
# 進化ポケモンなので Ignition Energy 1枚で{C}{C}{C}が出る = 初手から撃てる加速機構。
# **進化元もふしぎなアメも入っていないため、場に出せるのは「対戦準備の手札にあった1体」だけ。**
_CINDERACE_ID = 666

# なみのりビーチ(スタジアム): 「おたがいのプレイヤーは、自分の番ごとに1回、自分のバトル場の
# 【水】ポケモンを、ベンチの【水】ポケモンと入れ替えてよい。」
# **にげるコストは変えない。** エネをトラッシュしない別経路の入れ替えである。
# Phase 0 プローブ(2026-08-10)で、エンジンは OptionType.ABILITY / area=STADIUM(7) として
# 提示することを確認した(12戦で117回)。
_BEACH_ID = 1262

# ミツルの思いやり(サポート): 「メガシンカex1匹のHPをすべて回復する。その後、回復した
# ポケモンについているエネルギーを、すべて手札にもどす。」エネ回収は強制。
_WALLY_ID = 1229
_MEGA_STARMIE_ID = 1031

# 山札を大きく削るドローサポート。ゼイユ(手札全トラッシュ→5枚)/リーリエの決心(手札を山へ→6or8枚)。
_BIG_DRAW_IDS = {1192, 1227}

# 温存モードに入る山札枚数。pilotfix の既定は 5 で、COUNT(ドロー枚数)選択が門番されて
# いなかった。ここを 10 に上げ、COUNT も門番する(L4)。
_PRESERVE_DECK_N = 10

# 水タイプ(EnergyType)。なみのりビーチの入れ替え対象判定に使う。
_WATER_ENERGY_TYPE = 3


def _v4_on(name: str) -> bool:
    """V4ロジックの個別ON/OFF(アブレーション用)。既定はON。"""
    return not os.environ.get("V4_NO_" + name)


def _card_db():
    global _CARDS, _ATTACKS
    if _CARDS is None:
        _CARDS = {c.cardId: c for c in all_card_data()}
        _ATTACKS = {a.attackId: a for a in all_attack()}
    return _CARDS, _ATTACKS


def _ex_wall_ids():
    global _EX_WALL_IDS
    if _EX_WALL_IDS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                for sk in c.skills or []:
                    text = getattr(sk, "text", "") or ""
                    # Farigiraf ex(Basic ex限定の壁)は対象外に落とす:
                    # うちのex打点はMega Starmie(非Basic)のみなので影響しない。
                    if (
                        "Prevent all damage done to this Pokémon" in text
                        and "{ex}" in text
                        and "Basic" not in text
                    ):
                        ids.add(c.cardId)
        except Exception:
            ids = {330, 345}
        _EX_WALL_IDS = ids
    return _EX_WALL_IDS


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
    if attack_id in _EFFECT_IGNORING_ATTACKS:
        return dmg  # 効果無視ワザ: 壁能力も弱点・抵抗も通らない素点

    try:
        my_active = state.players[me].active[0]
        opp_active = state.players[1 - me].active[0]
        if my_active is None or opp_active is None:
            return dmg
        attacker = cards.get(my_active.id)
        defender = cards.get(opp_active.id)
        if attacker and defender and dmg > 0:
            if (
                getattr(attacker, "ex", False) or getattr(attacker, "megaEx", False)
            ) and defender.cardId in _ex_wall_ids():
                return 0  # 壁: ex/メガのワザは全ダメージ無効(0ダメ連打の実敗因)
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


import re as _re

_DECK_ENERGY_TYPES = None


def _deck_energy_types():
    """自デッキが供給できるエネルギー型の集合。分からなければ None（＝制限しない）。

    記号→型の対応表は基本エネカードの名前（'Basic {G} Energy'）から自作するので、
    特定カードIDのハードコードをしない。特殊エネは効果テキスト中の {X} を拾う
    （例: Team Rocket's Energy は「{P} と {D} の任意の組合せで2個ぶん」）。
    """
    global _DECK_ENERGY_TYPES
    if _DECK_ENERGY_TYPES is None:
        try:
            cards, _ = _card_db()
            sym2type = {}
            for c in cards.values():
                if c.cardType == CardType.BASIC_ENERGY and c.energyType is not None:
                    m = _re.search(r"\{(\w)\}", c.name or "")
                    if m:
                        sym2type[m.group(1)] = c.energyType
            types = set()
            for cid in set(_my_deck60()):
                c = cards.get(cid)
                if c is None:
                    continue
                if c.cardType == CardType.BASIC_ENERGY:
                    if c.energyType is not None:
                        types.add(c.energyType)
                elif c.cardType == CardType.SPECIAL_ENERGY:
                    for sk in c.skills or []:
                        for s in _re.findall(r"\{(\w)\}", getattr(sk, "text", "") or ""):
                            if s in sym2type:
                                types.add(sym2type[s])
            _DECK_ENERGY_TYPES = types or None
        except Exception:
            _DECK_ENERGY_TYPES = None
    return _DECK_ENERGY_TYPES


def _payable(energies, avail) -> bool:
    """このワザのコストを自デッキのエネルギー型で払えるか（0＝無色は何でも可）。"""
    try:
        for e in energies:
            if e and e not in avail:
                return False
    except TypeError:
        return True
    return True


def _usable_attacks(card):
    """そのカードのワザのうち、自デッキのエネルギーで実際に払えるものだけを返す。

    2026-08-06: 以前は型を見ずコストの枚数だけを数えていた。そのため、デッキに
    存在しない型を要求するポケモン（実測: 水エネ0枚のデッキで Articuno の
    Dark Frost が {W} 要求）が恒久的に「エネが足りない」と判定され、主砲より
    優先してエネを吸い続けていた（本番53戦で 1.7枚/戦・Dark Frost の使用は0回）。
    """
    _, attacks = _card_db()
    avail = None if os.environ.get("V3_NO_TRFIX") else _deck_energy_types()
    for aid in card.attacks or []:
        a = attacks.get(aid)
        if a is None:
            continue
        if avail is not None and a.energies is not None and not _payable(a.energies, avail):
            continue
        yield aid, a


def _max_attack_cost(card_id: int) -> int:
    """カードのワザの最大エネルギーコスト（エネ貼り先の必要数判定）。払えるワザのみ。"""
    cards, _ = _card_db()
    c = cards.get(card_id)
    if not c:
        return 0
    need = 0
    for _aid, a in _usable_attacks(c):
        if a.energies is not None:
            need = max(need, len(a.energies))
    return need


def _best_attack_damage_of_card(card_id: int) -> int:
    """カードが持つワザの最大基礎ダメージ（エネ貼り先の価値付けに使う）。払えるワザのみ。"""
    cards, _ = _card_db()
    c = cards.get(card_id)
    if not c:
        return 0
    best = 0
    for aid, a in _usable_attacks(c):
        best = max(best, a.damage)
        if aid in _SCALING_DAMAGE and (_trfix_on() or aid not in _TRFIX_SCALING):
            best = max(best, 120)  # スケーリングワザは高価値とみなす固定見積り
    return best


# ---------------------------------------------------------------------------
# V4 補助: 水判定 / 攻撃可否 / ビーチ / ミツル
# ---------------------------------------------------------------------------


def _min_attack_cost(card_id: int):
    """打点のある払えるワザの最小コスト。撃てるワザが無ければ None。

    `_max_attack_cost` は「エネを何枚まで吸わせるか」の上限なので、
    「いま撃てるか」の判定には最小側が要る。
    """
    cards, _ = _card_db()
    c = cards.get(card_id)
    if not c:
        return None
    best = None
    for aid, a in _usable_attacks(c):
        if a.energies is None:
            continue
        if a.damage <= 0 and aid not in _SCALING_DAMAGE:
            continue
        n = len(a.energies)
        best = n if best is None else min(best, n)
    return best


def _can_attack_now(pk) -> bool:
    """その個体が「いま」打点のあるワザを撃てるだけのエネを持っているか。"""
    if pk is None:
        return False
    need = _min_attack_cost(pk.id)
    if need is None:
        return False
    have = len(pk.energies) if pk.energies else 0
    return have >= need


def _is_water(card_id) -> bool:
    """なみのりビーチの入れ替え対象になる【水】ポケモンか。"""
    if card_id is None:
        return False
    cards, _ = _card_db()
    c = cards.get(card_id)
    return bool(c and c.cardType == CardType.POKEMON and c.energyType == _WATER_ENERGY_TYPE)


def _is_mega_ex(card_id) -> bool:
    """ミツルの思いやりの対象になる「メガシンカex」か（IDのハードコードを避ける）。"""
    if card_id is None:
        return False
    cards, _ = _card_db()
    c = cards.get(card_id)
    return bool(c and getattr(c, "megaEx", False))


def _damage_on(pk) -> int:
    """その個体が背負っているダメージ量（回復量の見積り）。"""
    try:
        if pk is None or pk.hp is None or pk.maxHp is None:
            return 0
        return max(0, pk.maxHp - pk.hp)
    except (TypeError, AttributeError):
        return 0


def _beach_in_play(state) -> bool:
    """場のスタジアムが なみのりビーチ か。"""
    try:
        st = state.stadium or []
        return bool(st) and st[0].id == _BEACH_ID
    except (IndexError, TypeError, AttributeError):
        return False


def _wally_in_hand(state, me) -> bool:
    try:
        return any(c.id == _WALLY_ID for c in (state.players[me].hand or []))
    except (IndexError, TypeError, AttributeError):
        return False


def _my_deck_count(obs) -> int:
    """自分の山札の残り枚数（読めなければ 99 = 温存しない側に倒す）。"""
    try:
        state = obs.current
        return state.players[state.yourIndex].deckCount or 0
    except (IndexError, TypeError, AttributeError):
        return 99


_UNREACHABLE_EVO = None


def _unreachable_evolution(card_id) -> bool:
    """この進化ポケモンは、自デッキの構成上そもそも場に出せないか。

    [V4] 例: エースバーン(666)は2進化だが、デッキにラビフット(進化元)も
    ふしぎなアメも入っていない。**対戦準備の特性しゅんぱつりょくで出た1体が全て**で、
    手札に来た2枚目以降は完全な死に札になる。

    ところが `_gain_value` は「場のポケモンの進化先」でなければ一律 1 を返すので、
    **ポケパッドやハイパーボールのサーチ先として、ヒトデマン(出せる)と
    エースバーン(出せない)が同点になる**。同点はソートの安定性まかせ = 実質
    カードID順で、666 < 1030 なのでエースバーンが先に選ばれる(T7レンズB B1)。
    カードIDを直書きせず、デッキの中身から判定する。
    """
    global _UNREACHABLE_EVO
    if _UNREACHABLE_EVO is None:
        cards, _ = _card_db()
        try:
            names = {(cards[c].name or "") for c in set(_my_deck60()) if c in cards}
            texts = " ".join(
                (getattr(sk, "text", "") or "")
                for c in set(_my_deck60()) if c in cards
                for sk in (cards[c].skills or [])
            )
            # ふしぎなアメ系(進化元を飛ばす)がデッキにあるなら、この判定は行わない
            skip = "Rare Candy" in names or "evolves from" in texts.lower()
            out = set()
            if not skip:
                for cid in set(_my_deck60()):
                    c = cards.get(cid)
                    if c and c.cardType == CardType.POKEMON and c.evolvesFrom \
                            and c.evolvesFrom not in names:
                        out.add(cid)
            _UNREACHABLE_EVO = out
        except Exception:
            _UNREACHABLE_EVO = set()
    return card_id in _UNREACHABLE_EVO


def _pokemon_id_of_option(state, opt):
    """オプションが指す「場のポケモン」のカードID（指していなければ None）。"""
    try:
        pk = _pokemon_at(state, opt.playerIndex, opt.area, opt.index)
        return pk.id if pk is not None else None
    except (IndexError, TypeError, AttributeError):
        return None


def _best_wally_target(state, me, zone: str):
    """指定ゾーンで最も傷んでいるメガシンカexを返す（回復量が最大の対象）。"""
    best, best_dmg = None, 0
    try:
        pool = state.players[me].bench if zone == "bench" else state.players[me].active
        for pk in pool or []:
            if pk is None or not _is_mega_ex(pk.id):
                continue
            d = _damage_on(pk)
            if d > best_dmg:
                best, best_dmg = pk, d
    except (IndexError, TypeError, AttributeError):
        return None
    return best


def _ignition_in_hand(state, me) -> bool:
    try:
        return any(c.id == _IGNITION_ID for c in (state.players[me].hand or []))
    except (IndexError, TypeError, AttributeError):
        return False


def _wally_play_ok(state, me) -> bool:
    """いまミツルの思いやりを撃つ価値があるか。

    ミツルは「回復した個体のエネをすべて手札に戻す」ので、素直にバトル場の主砲へ撃つと
    **その番は棒立ちになる**。撃ってよいのは、テンポを失わない次の2形だけ:

    (A) 2段回復ループ（指示された本命の形）:
        ベンチに負傷したメガシンカexがいて、バトル場では別個体がいま攻撃できる。
        後ろを全快させ、前は殴り続ける。

    (B) バトル場の即時リセット（ドメイン知識からの拡張）:
        バトル場の負傷メガシンカexに撃っても、**この番のエネ手貼りがまだ残っていて
        手札にイグニッションがある**なら棒立ちにならない。イグニッションは進化ポケモンに
        {C}{C}{C}を供給し、ネビュラビームのコストは●●●なので、貼り直した瞬間に撃てる。
        HP330の全快とワザの両立で、これはこのデッキで最も強い一手になりうる。
        チップダメージで浪費しないよう、回復量が最大HPの1/3以上のときに限る。

    どちらでもないなら撃たない（サポート権は1ターン1回で、手札の他の札の方が価値が高い）。
    """
    bt = _best_wally_target(state, me, "bench")
    if bt is not None:
        try:
            act = (state.players[me].active or [None])[0]
        except (IndexError, TypeError, AttributeError):
            act = None
        # ★回復量の下限とエネ条件が要る。無いと「10点回復するために主砲のエネ3枚を
        # 手札に戻す」が成立してしまう(T7レンズC B1)。分岐(B)は最初から1/3の下限を
        # 持っていたので、その非対称さ自体が(A)の未整備を示していた。
        try:
            worth = bool(bt.maxHp) and _damage_on(bt) * 3 >= bt.maxHp
            cheap = len(bt.energies or []) <= 1   # 剥がされて困るエネを載せていない
        except (TypeError, AttributeError):
            worth = cheap = False
        if worth and cheap and _can_attack_now(act):
            return True  # (A)
    act_t = _best_wally_target(state, me, "active")
    if act_t is not None:
        try:
            enough = act_t.maxHp and _damage_on(act_t) * 3 >= act_t.maxHp
            free_attach = not bool(getattr(state, "energyAttached", False))
        except (TypeError, AttributeError):
            return False
        if enough and free_attach and _ignition_in_hand(state, me):
            return True  # (B)
    return False


def _beach_switch_worthwhile(state, me) -> bool:
    """なみのりビーチの1回きりの入れ替えを、いま使う価値があるか。

    ビーチは**にげるコストを変えない**。エネをトラッシュしない別経路の入れ替えなので、
    「にげるコスト2のメガスターミーexをエネ全損なしで下げられる」のが本質的な利得。
    ただし権利は自分の番に1回だけなので、条件を満たさないなら温存する。
    """
    try:
        act = (state.players[me].active or [None])[0]
        bench = [p for p in (state.players[me].bench or []) if p is not None]
    except (IndexError, TypeError, AttributeError):
        return False
    if act is None or not _is_water(act.id):
        return False
    water_bench = [p for p in bench if _is_water(p.id)]
    if not water_bench:
        return False

    ready_bench = [p for p in water_bench if _can_attack_now(p)]

    # (a) バトル場が撃てず、ベンチに撃てる水がいる → 前に出す
    if not _can_attack_now(act) and ready_bench:
        return True
    # (b) バトル場の負傷メガシンカexを下げて、ベンチでミツルを撃つ準備（L3への前工程）
    try:
        hurt_enough = bool(act.maxHp) and _damage_on(act) * 3 >= act.maxHp
    except (TypeError, AttributeError):
        hurt_enough = False
    if _is_mega_ex(act.id) and hurt_enough and _wally_in_hand(state, me) and ready_bench:
        return True
    # (c) バトル場が瀕死（残HP4割以下）で、ベンチに撃てる水がいる → 主砲を温存する
    try:
        if act.maxHp and act.hp is not None and act.hp * 10 <= act.maxHp * 4 and ready_bench:
            return True
    except (TypeError, AttributeError):
        pass
    return False


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
        # [V4] 進化元がデッキに無い=場に出せない進化ポケモンは、サーチ先として
        # たねポケモンより後ろに置く(ポケパッド4枚の当たりを潰さないため)。
        if _v4_on("CINDERACE") and _unreachable_evolution(cid):
            return 4
        return 1
    if c.cardType in (CardType.ITEM, CardType.SUPPORTER):
        return 2
    if c.cardType == CardType.BASIC_ENERGY:
        return 3
    return 4


def _pokemon_value_for_active(obs: Observation, me: int, opt, ctx=None) -> tuple:
    """バトル場に出すポケモンの評価（エネが付いている>打点が高い>HPが高い）。

    ゲーム開始時の最初のバトルポケモン選択(SETUP_ACTIVE_POKEMON)は、候補が場ではなく
    「手札」にある。場だけを見ていた頃はここで全候補が同点になり、実質ランダムに
    選んでいた(2026-07-21のプローブで発覚)。手札の候補はカードDBから評価する。

    [V4/L1] 対戦準備に限り、エースバーン(666)を最優先に固定する。
    エースバーンは特性しゅんぱつりょくで2進化のままバトル場に出せる唯一の候補で、
    HP160・にげる0・イグニッション1枚でフレアターボ(50点+基本エネ3枚をベンチへ)。
    **既存キー(エネ数, 打点, HP)でも 666(0,50,160) は 1030(0,20,70) に勝つ**ので
    順位は元から正しい(Phase 0 プローブ 2026-08-10: 提示14回中14回選択)。
    ここで明示するのは「将来ベンチにエネが乗った状態で SWITCH に流用されたとき、
    第一キーのエネ数に負けて順位が入れ替わる」のを防ぐため。**文脈を対戦準備に限る**のは、
    逆に道中でエースバーン(打点50)を主砲メガスターミー(210)より前に出さないため。
    """
    state = obs.current
    if (
        ctx == SelectContext.SETUP_ACTIVE_POKEMON
        and _v4_on("CINDERACE")
        and _card_id_of_option(obs, opt) == _CINDERACE_ID
    ):
        return (1 << 30, 0, 0)
    pk = _pokemon_at(
        state, opt.playerIndex if opt.playerIndex is not None else me, opt.area, opt.index
    )
    if pk is not None:
        energy = len(pk.energies) if pk.energies else 0
        return (energy, _best_attack_damage_of_card(pk.id), pk.hp or 0)
    cid = _card_id_of_option(obs, opt)
    if cid is None:
        return (0, 0, 0)
    cards, _ = _card_db()
    c = cards.get(cid)
    return (0, _best_attack_damage_of_card(cid), (c.hp if c else 0) or 0)


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

    # 山札温存モード: 残り山札が少ないとき、山札を消費する行動(ドロー/サーチ系)を
    # 打ち切って攻撃で決めにいく。自滅デッキアウト対策(2026-07-18 実測: 対random負けの
    # 100%が自分のデッキアウトだった)。
    #
    # [V4/L4] 閾値を 5 → _PRESERVE_DECK_N(=10) に引き上げる。このデッキは旧王者から
    # ドロー源を減らした代わりにサーチが濃く、山を掘り切る速度が上がっている。
    # ※副作用: 温存の発動が早まるぶん、膠着敗北(2026-07-19 実ラダー検死で実在)は
    #   増える方向。効果が正負どちらにも振れうる唯一のV4ロジックである。
    try:
        my_deck_count = state.players[me].deckCount or 0
    except (TypeError, AttributeError, IndexError):
        my_deck_count = 99
    preserve_deck = my_deck_count <= (_PRESERVE_DECK_N if _v4_on("LOGUARD") else 5)

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

    # 2. 能力（提示されている=使用可能。原則すべて使う。温存モード中は使わない）
    #
    # [V4/L2] ★安全修理。ここは「提示された最初のABILITYを、エネ貼りより前・攻撃より前に
    # 無条件で発動する」。なみのりビーチの1回入れ替えは OptionType.ABILITY / area=STADIUM
    # として提示される(Phase 0 プローブ 2026-08-10: 12戦で117回)ため、**この規則のままだと
    # 毎ターン盲目的にバトル場のメガスターミーを引っ込める**。
    # ビーチ由来のABILITYを一般ルートから外し、専用判定(_beach_switch_worthwhile)に回す。
    # ビーチは相手の番にも1回使えるが、こちらが制御できるのは自分の番だけである。
    beach_ability_idx = None
    if _v4_on("BEACH"):
        for i, o in enumerate(options):
            if o.type == OptionType.ABILITY and o.area == AreaType.STADIUM:
                if _beach_in_play(state):
                    beach_ability_idx = i
                    break
    if not preserve_deck:
        idx = first(
            lambda o: o.type == OptionType.ABILITY
            and not (beach_ability_idx is not None and o.area == AreaType.STADIUM)
        )
        if idx is not None:
            return [idx]

    # 2.5 [V4/L2] なみのりビーチの無償入れ替え。にげるコスト2のメガスターミーexを
    # エネ全損なしで下げられるのが利得。条件を満たさないなら1回きりの権利を温存する。
    if beach_ability_idx is not None and _beach_switch_worthwhile(state, me):
        return [beach_ability_idx]

    # 3. 手札から出す（ポケモン > グッズ/スタジアム/どうぐ > サポート）
    #
    # [V4/L3] サポートは元々すべて rank 2 で無差別だった。ミツルの思いやり(1229)は
    # 「回復した個体のエネをすべて手札に戻す」ので、**バトル場の主砲に撃つとその番は
    # 棒立ちになる**。2段回復ループ(ビーチで下げる→ベンチでミツル→回収エネを新主砲へ)が
    # 成立するときだけ最優先にし、それ以外では最劣後にする。
    # [V4/L4] 山札が薄いときは大型ドロー(ゼイユ/リーリエ)を最劣後にする。
    wally_ok = _wally_play_ok(state, me) if _v4_on("WALLY") else False
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
        if _v4_on("WALLY") and cid == _WALLY_ID:
            # 成立するときだけ最優先。回収したエネは 4. のエネ貼りがバトル場優先で
            # 貼り直すので、同一ターンに主砲へ戻せる。
            rank = -1 if wally_ok else 9
        # [V4/L4] 大型ドロー(ゼイユ/リーリエ)は、温存モードに入る**手前**から抑える。
        # 旧実装は `preserve_deck and cid in _BIG_DRAW_IDS` で rank9 にしていたが、
        # preserve_deck 下では次行の continue が全サポートを弾くので**完全な死にコード**
        # だった(T7レンズC N2)。閾値の少し上の帯で、大型ドローだけを選択的に止める。
        if _v4_on("LOGUARD") and not preserve_deck and cid in _BIG_DRAW_IDS \
                and my_deck_count <= _PRESERVE_DECK_N * 2:
            rank = 9  # 山が薄いのに手札を捨てて引き直す=自滅LOへの最短路
        if preserve_deck and rank not in (0, -1):
            continue  # 温存モード: ポケモン以外は場に出さない(ドロー/サーチで山を削らない)
        if rank < play_rank:
            play_best, play_rank = i, rank
    if play_best is not None and play_rank < 9:
        return [play_best]

    # 4. エネ貼り。ワザコストが足りないポケモン優先(その中でバトル場>高打点)。
    # 全員足りているなら高打点に予備を1枚だけ(9枚積み・バトル場エネ0の詰み対策)。
    #
    # Ignition Energy(17)は「進化ポケモンに付いていれば{C}{C}{C}を供給、ターン終了時に破棄」。
    # Mega Starmie ex は進化ポケモンなので、**バトル場のMega Starmieに1枚貼るだけで
    # その場でNebula Beam(210)が撃てる**。逆にたね(Staryu)やベンチに貼ると1エネしか
    # 供給せずターン終了で捨てるだけの純損失になる。
    # 現行キーは貼り先しか見ずエネ種を区別しないため、実測では
    # 「バトル場Mega Starmieに貼れる232機会のうち61回(26%)しか使わず、
    #  たねStaryuに33回貼って捨てていた」(data.md 2026-07-21)。
    # 基本エネで3枚に届く局面(have>=2)ではIgnitionを温存する。
    attach_best, attach_key = None, (-1, -1, -1, -1, -99)
    for i, o in enumerate(options):
        if o.type != OptionType.ATTACH:
            continue
        pk = _pokemon_at(state, me, o.inPlayArea, o.inPlayIndex)
        if pk is None:
            continue
        have = len(pk.energies) if pk.energies else 0
        need = _max_attack_cost(pk.id)
        hungry = 1 if have < need else 0
        is_active = 1 if o.inPlayArea == AreaType.ACTIVE else 0
        dmg = _best_attack_damage_of_card(pk.id)
        pri = 1  # 通常のエネ
        try:
            ecid = (
                state.players[me].hand[o.index].id
                if o.area == AreaType.HAND
                else None
            )
        except (IndexError, TypeError, AttributeError):
            ecid = None
        if ecid == _IGNITION_ID:
            c_t = cards.get(pk.id)
            evolved = bool(
                c_t and (getattr(c_t, "stage1", False) or getattr(c_t, "stage2", False))
            )
            # 進化体がバトル場にいて、基本エネでは3に届かない(have<2)ときだけ最優先。
            # ★さらに『イグニッションの{C}{C}{C}が実際に要る』ことを要求する。
            # エースバーンのフレアターボは**1無色**なので基本水1枚で撃てる。
            # この条件が無いと、4枚しかない使い切りのイグニッションが1コストのワザに
            # 吸われ、ミツルで剥がされたメガスターミーを建て直す唯一の手段を失う
            # (夜のタンカは基本エネしか拾えない)。T7レンズB B2。
            pri = 2 if (evolved and is_active and have < 2 and _max_attack_cost(pk.id) >= 3) else 0
        key = (pri, hungry, is_active if hungry else 0, dmg, -have)
        if key > attach_key:
            attach_best, attach_key = i, key
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
    if attack_best is not None and attack_dmg > 0:
        return [attack_best]

    # 5.5 リトリート: 攻撃で進展がない番に、ベンチに「ワザコスト充足＋打点あり」の
    # ポケモンがいれば逃げる。バトル場棒立ち→エネ枯渇→敗北のロック対策
    # (2026-07-19 実ラダー検死: プライズ0のまま35ターン膠着して山札切れが実在)。
    #
    # [V4/L2] ビーチが使えるならリトリートより先に試す。ここに来た時点で
    # 2.5 の条件判定は通過していない（＝下がる価値が無い）が、リトリートで
    # **エネを全損してまで**下がるくらいなら、無償のビーチを使う方が常に良い。
    # メガスターミーexのにげるコストは2なので、これは水どうしの交代で毎回2枚を救う。
    if beach_ability_idx is not None:
        try:
            act = (state.players[me].active or [None])[0]
            if act is not None and _is_water(act.id):
                # ★交代先が現バトル場より弱いなら下がらない。これが無いと、壁(イワパレス)相手に
                # `_estimate_damage`=0 で 5. を素通りしたとき、**エネ3枚の主砲(210)を
                # エネ1枚のヒトデマン(20)と交換する**(T7レンズC B4)。
                act_dmg = _best_attack_damage_of_card(act.id)
                for pk in state.players[me].bench or []:
                    if pk is None or not _is_water(pk.id):
                        continue
                    if _can_attack_now(pk) and _best_attack_damage_of_card(pk.id) >= act_dmg:
                        return [beach_ability_idx]
        except (TypeError, AttributeError, IndexError):
            pass

    retreat_idx = first(lambda o: o.type == OptionType.RETREAT)
    if retreat_idx is not None:
        try:
            for pk in state.players[me].bench or []:
                if pk is None:
                    continue
                need = _max_attack_cost(pk.id)
                have = len(pk.energies) if pk.energies else 0
                if need > 0 and have >= need and _best_attack_damage_of_card(pk.id) > 0:
                    return [retreat_idx]
        except (TypeError, AttributeError):
            pass

    # 5.9 打点0でも攻撃が唯一の進展手段なら攻撃する
    if attack_best is not None:
        return [attack_best]

    # 6. 番を返す
    idx = first(lambda o: o.type == OptionType.END)
    if idx is not None:
        return [idx]
    # [V4] 旧実装は `return [0] if options else []` で、minCount>1 や maxCount<1 のとき
    # 違法手になりうる(robustness-guardが実測で再現。王者にも同居しているが、あちらは
    # バイト同一の再提出系列を保つために意図的に残してある)。
    # V4 は温存モードの発動が早まり rank9 のスキップも増えるぶん**ここに来る頻度が上がる**ので、
    # 件数を契約から導く `_fallback` に置き換える(外側の契約検査に頼らない)。
    return _fallback(obs.select)


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
    # 注: 進化先の脅威度で優先度を変える案(EXP6/6b, 2026-07-21)は、脅威を主キーにすると
    # KOへの変換を失い(-8pt級)、タイブレークに落とすと効果が消える(正味-0.09pt)ため棄却済み。
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
    #
    # [V4/L3] ミツルの思いやりの対象選択がここに来る。既定の「ダメージ最大」だと、
    # バトル場の主砲がいちばん傷んでいるのが普通なので**前の個体を選んでしまい、
    # エネを剥がして棒立ちにする**。2段回復ループが立っている(＝バトル場がいま撃てる)
    # ときは、**ベンチのメガシンカexを優先**して前を殴らせ続ける。
    # EFFECT_TARGET は汎用の文脈なので、**候補がすべて自分のメガシンカexのときだけ**
    # ここに寄せる（＝実質ミツル専用）。それ以外は既定の経路に落とす。
    _mega_only_target = _v4_on("WALLY") and ctx == SelectContext.EFFECT_TARGET and n > 0 and all(
        _is_mega_ex(_pokemon_id_of_option(state, o)) for o in options
    )
    if ctx in (SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER) or _mega_only_target:
        prefer_bench = False
        if _v4_on("WALLY") and ctx != SelectContext.REMOVE_DAMAGE_COUNTER:
            try:
                act = (state.players[me].active or [None])[0]
                # ★負傷していないメガexを選ぶと「回復量0 → エネは戻らず、サポート権だけ失う」
                # (ミツルのエネ回収は『回復した場合』の条件つき)。damage>0 を必ず要求する。
                prefer_bench = _can_attack_now(act) and any(
                    o.area == AreaType.BENCH
                    and _is_mega_ex(_pokemon_id_of_option(state, o))
                    and _damage_on(_pokemon_at(state, o.playerIndex, o.area, o.index)) > 0
                    for o in options
                )
            except (IndexError, TypeError, AttributeError):
                prefer_bench = False

        def dmg_taken(i):
            o = options[i]
            pk = _pokemon_at(state, o.playerIndex, o.area, o.index)
            if pk and pk.hp is not None and pk.maxHp is not None:
                bench_first = 0
                if prefer_bench:
                    # ベンチの負傷メガシンカexを、バトル場のどの個体よりも先に置く
                    bench_first = (
                        0
                        if (o.area == AreaType.BENCH and _is_mega_ex(pk.id) and _damage_on(pk) > 0)
                        else 1
                    )
                return (bench_first, -(pk.maxHp - pk.hp))
            return (2, 0)

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
            key=lambda i: _pokemon_value_for_active(obs, me, options[i], ctx),
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


def _contract_ok(sel, result):
    """agent()の契約(件数・範囲・重複なし)を満たしていれば通し、外れたら安全側に落とす。

    [V4] MAIN と CARD系にはこの検査があったが、**ATTACK と COUNT には無かった**。
    L4 が COUNT分岐に手を入れたので、同じ網をここにも掛ける。
    合法な場合の返り値は完全に同一なので、測定上の挙動は変わらない
    (変わるのは「本来なら違法手を返していた場合」だけ = 対局没収の回避)。
    """
    try:
        if (
            sel.minCount <= len(result) <= sel.maxCount
            and len(set(result)) == len(result)
            and all(0 <= r < len(sel.option) for r in result)
        ):
            return result
    except (TypeError, AttributeError):
        pass
    return _fallback(sel)


def _fallback(sel) -> list[int]:
    """絶対に合法な選択（考えるのを諦めたときの最後の砦）。"""
    try:
        n = len(sel.option or [])
        mn = sel.minCount or 0
        mx = sel.maxCount if sel.maxCount is not None else (1 if n else 0)
        k = min(max(mn, min(1, mx)), n)
        return list(range(k))
    except Exception:
        return []


def _v1_decide(obs: Observation) -> list[int]:
    """v1のヒューリスティック本体。常に合法手を返す（探索層のフォールバック兼基準方策）。"""
    sel = obs.select
    try:
        if sel.type == SelectType.MAIN:
            # CARD分岐と同じ事後契約検査。MAINだけ検査が無く、_choose_mainの
            # 最終フォールバックが範囲外を返しても素通りしていた。
            # 実測(4戦486件)ではMAINは常に minCount=maxCount=1 の int。
            result = _choose_main(obs)
            if (
                sel.minCount <= len(result) <= sel.maxCount
                and len(set(result)) == len(result)
                and all(0 <= r < len(sel.option) for r in result)
            ):
                return result
            return _fallback(sel)
        if sel.type == SelectType.YES_NO:
            yes = next(
                (i for i, o in enumerate(sel.option) if o.type == OptionType.YES),
                None,
            )
            return [yes] if yes is not None else _fallback(sel)
        if sel.type == SelectType.ATTACK:
            return _contract_ok(sel, _choose_attack_options(obs))
        if sel.type == SelectType.COUNT:
            # 引く枚数・ダメカン数などは最大を選ぶ
            #
            # [V4/L4] ★ここが自滅LOの抜け穴だった。`preserve_deck` は _choose_main の
            # ローカル変数で、**COUNT型の選択は一切門番されていない**。温存モードに
            # 入っていても「引く枚数」は最大を取り続け、山を掘り切って自分で負ける。
            # DRAW_COUNT 文脈に限って、山が薄いときは最小を選ぶ。
            # ダメカン数(DAMAGE_COUNTER_COUNT)は山と無関係なので必ず最大のまま。
            reverse = True
            if (
                _v4_on("LOGUARD")
                and sel.context == SelectContext.DRAW_COUNT
                and _my_deck_count(obs) <= _PRESERVE_DECK_N
            ):
                reverse = False
            ranked = sorted(
                range(len(sel.option)),
                key=lambda i: sel.option[i].number if sel.option[i].number is not None else 0,
                reverse=reverse,
            )
            k = max(sel.minCount, min(1, sel.maxCount))
            return _contract_ok(sel, ranked[:k])
        if sel.type in (
            SelectType.CARD,
            SelectType.ATTACHED_CARD,
            SelectType.CARD_OR_ATTACHED_CARD,
        ):
            # 契約の最終確認（範囲・重複・数）を満たさない場合は安全側に落とす
            return _contract_ok(sel, _choose_cards(obs))
        # ENERGY / SKILL / EVOLVE / SPECIAL_CONDITION / 未知のSelectType
        return _fallback(sel)
    except Exception:
        # どんな内部エラーでも合法手は必ず返す（大会ハード要件）
        return _fallback(sel)


# ============================================================
# v2 探索層: エンジン内蔵の SearchBegin/SearchStep で候補手を実際に
# 打って評価する。失敗・時間超過は常に v1 (_v1_decide) に落ちる。
# ============================================================
import ctypes as _ct
import json
import random as _rnd
import time as _time

try:
    from cg.sim import lib as _lib
except Exception:  # エンジンが読めない環境でも v1 として動く
    _lib = None

_SEARCH_BUDGET_SEC = 0.6  # 1手あたりの探索予算
_MAX_CANDIDATES = 24      # 全展開する候補手の上限
_DETERMINIZATIONS = 2     # 隠れ情報のサンプル数
_ROLLOUT_MAX_STEPS = 60   # ロールアウトの最大ステップ数
_OVERRIDE_MARGIN = 120.0  # v1を上書きするのに要する評価差（盤面項スケール）

# 相手デッキ推定の辞書: 2026-07-14 ラダー実測の最頻出60枚（docs/memo/data.md）
_META_DECKS = {
    "alakazam": [5, 5, 13, 19, 19, 19, 19, 66, 66, 140, 305, 305, 305, 343, 741, 741, 741, 741, 742, 742, 742, 742, 743, 743, 743, 743, 1079, 1079, 1079, 1081, 1081, 1081, 1081, 1086, 1086, 1086, 1086, 1097, 1129, 1152, 1152, 1152, 1152, 1182, 1182, 1182, 1184, 1197, 1197, 1197, 1225, 1225, 1225, 1225, 1231, 1231, 1231, 1231, 1266, 1266],
    "grimmsnarl_munkidori": [7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 104, 104, 112, 112, 112, 112, 646, 646, 646, 646, 647, 647, 647, 648, 648, 648, 860, 860, 1079, 1079, 1079, 1080, 1086, 1086, 1086, 1086, 1097, 1097, 1097, 1152, 1152, 1152, 1152, 1161, 1161, 1182, 1182, 1219, 1219, 1219, 1219, 1227, 1227, 1227, 1227, 1231, 1259, 1259, 1259, 1259],
    "kangaskhan_crustle": [1, 11, 11, 11, 11, 14, 14, 14, 14, 18, 18, 18, 18, 343, 344, 344, 344, 344, 345, 345, 345, 345, 756, 756, 756, 756, 1086, 1086, 1086, 1086, 1087, 1122, 1122, 1122, 1122, 1123, 1123, 1123, 1123, 1147, 1147, 1147, 1147, 1159, 1182, 1182, 1197, 1197, 1197, 1197, 1225, 1225, 1225, 1225, 1227, 1227, 1227, 1227, 1264, 1264],
    "starmie_dusknoir": [3, 3, 3, 3, 3, 3, 3, 3, 3, 17, 17, 17, 17, 131, 131, 132, 132, 133, 133, 1030, 1030, 1030, 1030, 1031, 1031, 1031, 1086, 1086, 1086, 1086, 1121, 1121, 1121, 1121, 1122, 1122, 1122, 1152, 1152, 1152, 1152, 1167, 1192, 1192, 1192, 1213, 1213, 1213, 1225, 1225, 1225, 1225, 1227, 1227, 1227, 1227, 1229, 1229, 1229, 1229],
    "tr_mewtwo": [1, 1, 1, 1, 1, 1, 1, 1, 1, 15, 15, 15, 15, 400, 400, 400, 400, 401, 401, 401, 401, 414, 414, 431, 431, 434, 434, 434, 1094, 1094, 1094, 1121, 1134, 1134, 1134, 1134, 1152, 1152, 1152, 1152, 1159, 1175, 1216, 1216, 1216, 1216, 1217, 1218, 1218, 1218, 1220, 1220, 1220, 1220, 1227, 1227, 1227, 1257, 1257, 1257],
}
_FILLER_ID = 1  # パディング用の実在カードID（基本草エネ）

_agent_ptr = None
_my_deck60_cache = None


def _my_deck60() -> list[int]:
    global _my_deck60_cache
    if _my_deck60_cache is None:
        _my_deck60_cache = read_deck_csv()
    return _my_deck60_cache


def _get_agent_ptr():
    global _agent_ptr
    if _agent_ptr is None and _lib is not None:
        _agent_ptr = _lib.AgentStart()
    return _agent_ptr


def _arr(xs: list[int], pad_to: int = 70) -> "_ct.Array":
    """CopyIdPtr は state 側のゾーンサイズぶん読むので、必ず余裕を持って
    実在IDでパディングした配列を渡す（短いと領域外読みになる）。"""
    xs = list(xs)[:pad_to] + [_FILLER_ID] * max(0, pad_to - len(xs))
    return (_ct.c_int * pad_to)(*xs)


def _visible_ids(pl: dict) -> list[int]:
    ids = []
    for zone in ("active", "bench"):
        for c in pl.get(zone) or []:
            if not c:
                continue
            ids.append(c["id"])
            for key in ("energyCards", "tools", "preEvolution"):
                ids += [x["id"] for x in (c.get(key) or [])]
    ids += [c["id"] for c in (pl.get("discard") or [])]
    return ids


def _counter(xs):
    d = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return d


def _infer_enemy_deck(visible: list[int]) -> list[int]:
    """見えている相手カードから60枚を推定。メタ辞書への被覆率最大で選ぶ。"""
    vis = _counter(visible)
    best, best_score = None, -1.0
    for cand in _META_DECKS.values():
        cc = _counter(cand)
        covered = sum(min(n, cc.get(c, 0)) for c, n in vis.items())
        score = covered / max(1, len(visible))
        if score > best_score:
            best, best_score = cand, score
    if best is None or best_score < 0.5:
        # 未知アーキタイプ: 見えたカードを4枚に増量し残りをエネで埋める
        pool = []
        for c, n in vis.items():
            pool += [c] * min(4, max(n, 2))
        pool += [_FILLER_ID] * (60 - len(pool))
        return pool[:60]
    return list(best)


def _determinize(cur: dict, me: int, my_deck60: list[int]):
    """隠れ情報を1サンプル生成: (myDeck, myPrize, foeDeck, foePrize, foeHand)"""
    you, foe = cur["players"][me], cur["players"][1 - me]
    my_unseen = _counter(my_deck60)
    for c in you.get("hand") or []:
        my_unseen[c["id"]] = my_unseen.get(c["id"], 0) - 1
    for c in _visible_ids(you):
        my_unseen[c] = my_unseen.get(c, 0) - 1
    my_pool = [c for c, n in my_unseen.items() for _ in range(max(0, n))]
    _rnd.shuffle(my_pool)
    n_my_prize = len(you.get("prize") or [])
    my_prize, my_deck = my_pool[:n_my_prize], my_pool[n_my_prize:]

    foe_vis = _visible_ids(foe)
    foe_unseen = _counter(_infer_enemy_deck(foe_vis))
    for c in foe_vis:
        foe_unseen[c] = foe_unseen.get(c, 0) - 1
    foe_pool = [c for c, n in foe_unseen.items() for _ in range(max(0, n))]
    _rnd.shuffle(foe_pool)
    n_foe_prize = len(foe.get("prize") or [])
    n_foe_hand = foe.get("handCount") or 0
    foe_prize = foe_pool[:n_foe_prize]
    foe_hand = foe_pool[n_foe_prize:n_foe_prize + n_foe_hand]
    foe_deck = foe_pool[n_foe_prize + n_foe_hand:]
    return my_deck, my_prize, foe_deck, foe_prize, foe_hand


def _evaluate(node_cur: dict, me: int) -> float:
    """探索ノードの静的評価（常に自分視点。yourIndexは手番なので使わない）。"""
    res = node_cur.get("result", -1)
    if res >= 0:
        if res == me:
            return 1e9
        if res == 1 - me:
            return -1e9
        return 0.0
    you, foe = node_cur["players"][me], node_cur["players"][1 - me]
    score = 0.0
    # サイド: 自分の残りが少ない=取れている
    score += 10000.0 * (len(foe.get("prize") or []) - len(you.get("prize") or []))
    def board(pl):
        dmg = hp = energy = pokes = 0
        for zone in ("active", "bench"):
            for c in pl.get(zone) or []:
                if not c:
                    continue
                pokes += 1
                hp += c.get("hp") or 0
                dmg += (c.get("maxHp") or 0) - (c.get("hp") or 0)
                energy += len(c.get("energyCards") or [])
        return dmg, hp, energy, pokes
    fd, fh, fe, fp = board(foe)
    md, mh, me_energy, mp = board(you)
    score += 3.0 * fd - 2.5 * md          # 与ダメ/被ダメ
    score += 30.0 * me_energy - 20.0 * fe  # エネ供給
    score += 40.0 * mp - 30.0 * fp         # 展開数
    score += 10.0 * len(you.get("hand") or []) - 6.0 * (foe.get("handCount") or 0)
    # 山札残数: 少なくなるほど1枚の価値が跳ね上がる(自滅デッキアウト対策)
    my_dc = you.get("deckCount") or 0
    foe_dc = foe.get("deckCount") or 0
    score += 8.0 * min(my_dc, 15) - 8.0 * min(foe_dc, 15)
    score += 30.0 * min(my_dc, 6) - 30.0 * min(foe_dc, 6)
    return score


def _foe_active_missing(cur: dict, me: int) -> bool:
    act = cur["players"][1 - me].get("active") or []
    return len(act) == 0 or act[0] is None


def _rollout_policy(node_obs: dict) -> list[int] | None:
    """探索ノード内の方策: 両者ともv1で指す（強い相手を仮定）。失敗時はNone。"""
    try:
        o = to_observation_class(node_obs)
        if o.select is None:
            return None
        return _v1_decide(o)
    except Exception:
        return None


def _opt_key(op):
    return (op.type, getattr(op, "area", None), getattr(op, "index", None),
            getattr(op, "inPlayArea", None), getattr(op, "inPlayIndex", None),
            getattr(op, "number", None))


def _dedupe_candidates(options) -> tuple[list[int], dict]:
    """同一内容のオプション（同じカードの重複枠など）を1つに束ねる。
    戻り値: (代表インデックスのリスト, キー→代表インデックス)"""
    rep, out = {}, []
    for i, op in enumerate(options):
        key = _opt_key(op)
        if key in rep:
            continue
        rep[key] = i
        out.append(i)
    return out, rep


def _engine_json(r):
    """v2.1c: エンジン戻り値(c_char_p)を安全にJSONへ。NULLはNone。
    string_at(None)はtry/exceptで捕えられないセグフォルト(=対局没収)になるため必ずここを通す。"""
    if r is None:
        return None
    try:
        if isinstance(r, (bytes, bytearray)):
            return json.loads(bytes(r).decode())
        return json.loads(_ct.string_at(r).decode())
    except Exception:
        return None


def _search_decide(obs_dict: dict, sel, v1_answer: list[int]) -> list[int] | None:
    """探索による1手選択。候補手→v1誘導ロールアウト（相手の返しまで）→評価。
    使えない/自信がない場合は None（=v1採用）。"""
    if os.environ.get("V2_NO_SEARCH"):
        return None
    if _lib is None:
        return None
    sbi = obs_dict.get("search_begin_input")
    cur = obs_dict.get("current")
    if not sbi or not cur:
        return None
    me = cur["yourIndex"]
    if _foe_active_missing(cur, me):
        return None  # セットアップ中は対象外(enemyActive注入が必要)
    n_opt = len(sel.option)
    if n_opt <= 1 or not (sel.minCount <= 1 <= sel.maxCount):
        return None  # v0はk=1の選択のみ探索
    candidates, rep = _dedupe_candidates(sel.option)
    candidates = candidates[:_MAX_CANDIDATES]
    if len(candidates) <= 1:
        return None
    # v1の選択を代表インデックスに写像し、必ず候補に含める（比較基準）
    v1_rep = None
    if v1_answer:
        try:
            v1_rep = rep.get(_opt_key(sel.option[v1_answer[0]]))
        except Exception:
            v1_rep = None
    if v1_rep is not None and v1_rep not in candidates:
        candidates.append(v1_rep)
    if v1_rep in candidates:
        candidates.remove(v1_rep)
        candidates.insert(0, v1_rep)  # 予算切れでもv1基準は必ず評価される

    deadline = _time.monotonic() + _SEARCH_BUDGET_SEC
    ptr = _get_agent_ptr()
    if not ptr:
        return None
    sbi_b = sbi.encode("ascii")
    my_deck60 = _my_deck60()
    root_turn = cur.get("turn") or 0
    totals = {c: 0.0 for c in candidates}
    counts = {c: 0 for c in candidates}
    try:
        for _ in range(_DETERMINIZATIONS):
            if _time.monotonic() > deadline:
                break
            md, mp, fd, fp, fh = _determinize(cur, me, my_deck60)
            r = _lib.SearchBegin(ptr, sbi_b, len(sbi_b), _arr(md), _arr(mp),
                                 _arr(fd), _arr(fp), _arr(fh), _arr([]), 0)
            res = _engine_json(r)
            if res is None or res.get("error"):
                return None
            root_id = res["state"]["searchId"]
            for c in candidates:
                if _time.monotonic() > deadline:
                    break
                r = _lib.SearchStep(ptr, _ct.c_int64(root_id), _arr([c], 1), 1)
                node = _engine_json(r)
                if node is None or node.get("error"):
                    totals[c] += -1e6  # エンジンが拒否した手は選ばない
                    counts[c] += 1
                    continue
                # v1誘導ロールアウト: 相手の番が終わる(=turnが2進む)まで
                sid = node["state"]["searchId"]
                nobs = node["state"]["observation"]
                for _step in range(_ROLLOUT_MAX_STEPS):
                    ncur = nobs.get("current") or {}
                    if ncur.get("result", -1) >= 0:
                        break
                    if (ncur.get("turn") or 0) >= root_turn + 2:
                        break
                    if _time.monotonic() > deadline:
                        break
                    pick = _rollout_policy(nobs)
                    if pick is None:
                        break
                    r = _lib.SearchStep(ptr, _ct.c_int64(sid), _arr(pick, max(1, len(pick))), len(pick))
                    nxt = _engine_json(r)
                    if nxt is None or nxt.get("error"):
                        break
                    sid = nxt["state"]["searchId"]
                    nobs = nxt["state"]["observation"]
                totals[c] += _evaluate(nobs.get("current") or {}, me)
                counts[c] += 1
    except Exception:
        return None
    finally:
        try:
            _lib.SearchEnd(ptr)
        except Exception:
            pass
    evaluated = [c for c in candidates if counts[c] >= _DETERMINIZATIONS]
    if not evaluated:
        return None
    best = max(evaluated, key=lambda c: totals[c] / counts[c])
    # v1の選択を明確なマージンで上回るときだけ上書きする
    if v1_rep is None or v1_rep not in evaluated:
        return None
    if best == v1_rep:
        return None
    if totals[best] / counts[best] < totals[v1_rep] / counts[v1_rep] + _OVERRIDE_MARGIN:
        return None
    return [best]


# --- 観測トレーサ（V3_SELECT_TRACE=path のときだけ有効。未設定なら完全に不活性） ---
_TRACE_PATH = os.environ.get("V3_SELECT_TRACE")


def _trace_select(obs: Observation, picked: list[int]) -> None:
    if not _TRACE_PATH:
        return
    try:
        sel = obs.select
        state = obs.current
        cards, _ = _card_db()
        me = state.yourIndex
        eff = getattr(sel, "effect", None)
        eff_id = getattr(eff, "id", None) if eff is not None else None
        opts = []
        for i, o in enumerate(sel.option[:40]):
            rec = {"i": i, "t": int(o.type)}
            for f in ("area", "index", "inPlayArea", "inPlayIndex", "attackId"):
                v = getattr(o, f, None)
                if v is not None:
                    rec[f] = int(v)
            cid = _card_id_of_option(obs, o)
            if cid is None and o.type in (OptionType.ABILITY, OptionType.ATTACK):
                pk = _pokemon_at(state, me, AreaType.ACTIVE, 0)
                cid = pk.id if pk else None
            if cid is not None:
                rec["cid"] = cid
                c = cards.get(cid)
                if c:
                    rec["nm"] = c.name
            if o.type == OptionType.ATTACK and o.attackId is not None:
                rec["est"] = _estimate_damage(o.attackId, state, me)
            if o.type == OptionType.ATTACH:
                pk = _pokemon_at(state, me, o.inPlayArea, o.inPlayIndex)
                if pk:
                    rec["toNm"] = (cards.get(pk.id).name if cards.get(pk.id) else None)
                    rec["toHave"] = len(pk.energies) if pk.energies else 0
            opts.append(rec)
        line = {
            "turn": getattr(state, "turn", None),
            "type": int(sel.type),
            "ctx": int(sel.context) if sel.context is not None else None,
            "tr": _tr_in_play_count(state, me),      # 場のロケット団の数（Rocket Rush の打点源）
            "oppHp": _opp_active_hp(state, me),
            "eff": eff_id,
            "opts": opts, "picked": picked,
        }
        with open(_TRACE_PATH, "a") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _last_resort(obs_dict: dict) -> list[int]:
    """Observationのパースすら失敗したときの、生dictからの合法手。"""
    try:
        sel = obs_dict.get("select")
        if sel is None:
            return read_deck_csv()
        n = len(sel.get("option") or [])
        mn = sel.get("minCount") or 0
        mx = sel.get("maxCount")
        if mx is None:
            mx = 1 if n else 0
        k = min(max(mn, min(1, mx)), n)
        return list(range(k))
    except Exception:
        return []


def agent(obs_dict: dict) -> list[int]:
    """Implement Your Pokémon Trading Card Game Agent.

    Each element in the returned list must be >= 0 and < len(obs.select.option).
    The list length must be between obs.select.minCount and obs.select.maxCount (inclusive), with no duplicate elements.

    Returns:
        list[int]: A list of option index.
    """
    try:
        obs: Observation = to_observation_class(obs_dict)
        if obs.select == None:
            return read_deck_csv()
        sel = obs.select
        v1 = _v1_decide(obs)
        try:
            if sel.type in (SelectType.MAIN, SelectType.ATTACK):
                picked = _search_decide(obs_dict, sel, v1)
                if (
                    picked is not None
                    and sel.minCount <= len(picked) <= sel.maxCount
                    and len(set(picked)) == len(picked)
                    and all(0 <= p < len(sel.option) for p in picked)
                ):
                    _trace_select(obs, picked)
                    return picked
        except Exception:
            pass
        _trace_select(obs, v1)
        return v1
    except Exception:
        # Observationパース・v1本体まで含めて何が起きても合法手を返す
        return _last_resort(obs_dict)

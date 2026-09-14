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
# V5: 盤面価値で「残る / 逃げる / わざと死ぬ」を決める層 (2026-08-11)
#
# 発端は実ラダーの観測(ゆうじ): 「相手を一発で倒せないと逃げる」。
# 実物を特定した — `eps55169074/ep89396266.json` step94:
#   自 Mega Starmie ex HP30/330・水エネ2 / 相手 Mega Lucario ex HP340/340 / 相手サイド残6
#   → 逃げて水エネ2枚を捨て、交代先(エネ1)が結局120しか出せなかった。
#
# **v1 は正しく ATTACK と答えている。上書きしているのは探索層である**(決定レベルで確認):
#   `_evaluate` のサイド項は 10000点/枚、メガexのKOは3枚=30000点。
#   一方 `_OVERRIDE_MARGIN` は 120.0 で、**250倍の桁差**によりマージンが機能していない。
#   さらにロールアウトは root_turn+2 で打ち切るため、
#   「1ターン延命しても次の番に結局死ぬ」が地平の外にあり評価できない。
#
# すべて env で個別にOFFにできる(playbook §3)。既定は全ON。
# ---------------------------------------------------------------------------

_BEACH_ID = 1262          # なみのりビーチ(スタジアム)
_WATER_ENERGY_TYPE = 3    # EnergyType.WATER
_MEGA_STARMIE_ID = 1031
_JETTING_BLOW_ID = 1487   # {W}1個 / 120 + 相手ベンチ1体に50(弱点抵抗なし)
_NEBULA_BEAM_ID = 1488    # 無色3 / 210 / 弱点・抵抗・相手バトル場の効果を受けない

# Jetting Blow の副次ダメージ。**バトル場への打点とは別枠**(ベンチのKO判定に使う)。
_BENCH_SPLASH = {_JETTING_BLOW_ID: 50}
# [V5/L23] 印字0の可変打点ワザ → 悲観上界(相手脅威の見積り専用。自ワザには未使用)
_THREAT_FLOOR = {560: 180, 183: 100}  # 560=TR Spidops Rocket Rush / 183=Fezandipiti Cruel Arrow


def _v5_on(name: str) -> bool:
    """V5ロジックの個別ON/OFF(アブレーション用)。既定はON。"""
    return not os.environ.get("V5_NO_" + name)


def _prize_value(card_id) -> int:
    """この個体がきぜつしたとき、相手が取るサイドの枚数。

    `_evaluate` は盤面のポケモンを一律 40点で数えており、**メガスターミーex(3枚)の死を
    ヒトデマン(1枚)と同じに見ている**(外部レビュー H4)。v1側でこれを補う。
    """
    cards, _ = _card_db()
    c = cards.get(card_id)
    if c is None:
        return 1
    if getattr(c, "megaEx", False):
        return 3
    if getattr(c, "ex", False):
        return 2
    return 1


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


def _max_attack_cost(card_id: int) -> int:
    """カードのワザの最大エネルギーコスト（エネ貼り先の必要数判定）。"""
    cards, attacks = _card_db()
    c = cards.get(card_id)
    if not c:
        return 0
    need = 0
    for aid in c.attacks:
        a = attacks.get(aid)
        if a and a.energies is not None:
            need = max(need, len(a.energies))
    return need


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
        # [V5/L23] ★印字0の可変打点ワザの悲観上界(2026-08-17棚卸し1位)。
        # damage欄=0のワザは従来「脅威0」扱いで、生死判定が「立ったまま死ぬ」側に
        # 系統的に誤っていた(TRスピドプス Rocket Rush 実際最大180 / フェザンディパイ
        # Cruel Arrow 実際100)。印字が非ゼロのワザの過小評価は**あえて据え置き**
        # (勝っている対面の均衡は誤モデル上で測定済み — #33の教訓)。
        if _v5_on("THREATFLOOR"):
            best = max(best, _THREAT_FLOOR.get(aid, 0))
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


def _pokemon_value_for_active(obs: Observation, me: int, opt) -> tuple:
    """バトル場に出すポケモンの評価（エネが付いている>打点が高い>HPが高い）。

    ゲーム開始時の最初のバトルポケモン選択(SETUP_ACTIVE_POKEMON)は、候補が場ではなく
    「手札」にある。場だけを見ていた頃はここで全候補が同点になり、実質ランダムに
    選んでいた(2026-07-21のプローブで発覚)。手札の候補はカードDBから評価する。
    """
    state = obs.current

    # [V5/L22] リーチ時の昇格規律(ゆうじのパターン#4): 相手の残りサイド ≤ この駒の献上価値なら
    # 前に出さない(出した瞬間、次のKOが敗着になる)。全候補が該当なら相対順序は不変=無害。
    def _promo_guard(card_id) -> int:
        if not _v5_on("PROMOGUARD"):
            return 0
        try:
            opp_prizes = len(state.players[1 - me].prize or [])
            if opp_prizes and opp_prizes <= _prize_value(card_id):
                return -1
        except Exception:
            pass
        return 0

    pk = _pokemon_at(
        state, opt.playerIndex if opt.playerIndex is not None else me, opt.area, opt.index
    )
    if pk is not None:
        energy = len(pk.energies) if pk.energies else 0
        return (_promo_guard(pk.id), energy, _best_attack_damage_of_card(pk.id), pk.hp or 0)
    cid = _card_id_of_option(obs, opt)
    if cid is None:
        return (0, 0, 0, 0)
    cards, _ = _card_db()
    c = cards.get(cid)
    return (_promo_guard(cid), 0, _best_attack_damage_of_card(cid), (c.hp if c else 0) or 0)


def _opp_max_damage(state, me) -> int:
    """相手バトル場が次の番に出しうる最大の基本打点(danger判定用)。

    自分の打点見積り(`_estimate_damage`)は自分視点の補正が入るので使わない。
    ここで欲しいのは「自分がKOされるか」の粗い上界だけなので、カードの素点で足りる。
    """
    try:
        opp = (state.players[1 - me].active or [None])[0]
        return _best_attack_damage_of_card(opp.id) if opp else 0
    except (IndexError, TypeError, AttributeError):
        return 0


def _bench_splash_value(state, me, attack_id) -> float:
    """ワザの副次ダメージ(相手ベンチ)の取れ高。

    [V5/L3] Jetting Blow(1487) は「相手のベンチ1体に50」を**無条件で**行う
    (対象は自分で選ぶ／弱点抵抗は適用しない)。ところが `_estimate_damage` は
    `atk.damage`(=120)しか見ておらず、**この50が完全に見積りの外**にあった。
    帰結が2つあった:
      ①相手が壁(イワパレス345)だと Jetting Blow の見積りが 0 になり、
        `attack_dmg > 0` の条件から漏れて**リトリートに落ちる**。
        実際にはベンチへの50は壁を無視して通るので、これは純粋な取りこぼし。
      ②バトル場をKOできる局面で、ベンチも落とせる Jetting Blow より
        素点の大きい Nebula Beam(210)が必ず選ばれ、**2体KOを捨てていた**。
    """
    splash = _BENCH_SPLASH.get(attack_id, 0)
    if not splash:
        return 0.0
    # ★与えられない打点を計上しない(T7 B7)。旧実装は **相手ベンチが空でも 50.0 を返し**、
    # その 50 が `attack_val > 0` を成立させて段5.5の退却弁を永久に塞いでいた
    # (壁 × ベンチ空 の局面で、1点も通らない攻撃を選び続ける)。
    # ★ベンチの壁も見る(T7 N5)。イワパレス345の効果文は
    # 「Prevent all damage done to **this Pokémon** by attacks from your opponent's {ex}」なので、
    # **ベンチに並んだイワパレス自身には副次50も通らない**。
    cards, _ = _card_db()
    val = 0.0
    try:
        my_active = (state.players[me].active or [None])[0]
        atk_card = cards.get(my_active.id) if my_active else None
        atk_is_ex = bool(atk_card and (getattr(atk_card, "ex", False)
                                       or getattr(atk_card, "megaEx", False)))
        for pk in state.players[1 - me].bench or []:
            if pk is None or pk.hp is None:
                continue
            if atk_is_ex and pk.id in _ex_wall_ids():
                continue          # 壁は自分自身を守る。この個体には通らない
            val = max(val, float(splash))
            if pk.hp <= splash:
                # ベンチをKOできる = サイドが動く。素点とは桁を分ける。
                val = max(val, splash + 10000.0 * _prize_value(pk.id))
    except (IndexError, TypeError, AttributeError):
        return 0.0
    return val


def _real_damage_ok(state, me, attack_id) -> bool:
    """このワザで相手バトル場に**実際に打点が通る**か(副次50のチップだけでないか)。"""
    return _estimate_damage(attack_id, state, me) > 0


def _attack_value(state, me, attack_id):
    """この攻撃で盤面から取れる価値。サイドが動く手を素点と別の桁に置く。

    返り値: (価値, **相手バトル場をKOできるか**)

    ★2つ目の返り値を分けているのは `has_lethal` の誤判定を防ぐため(robustness-guard 指摘)。
    価値は「バトル場KOのボーナス」と「ベンチKOのボーナス」を**足し合わせた1つのスカラ**なので、
    `val >= 10000` を「リーサル」と読むと、**バトル場を倒せないのにベンチKOだけで True** になる。
    それが `_flee_to_survive` の早期returnを踏むと、**L2が守るべき局面(次の番に倒され、
    かつ倒されたら負ける)でちょうど無効化される** — V5が直そうとしている事故の再発経路そのもの。
    """
    dmg = _estimate_damage(attack_id, state, me)
    opp_hp = _opp_active_hp(state, me)
    val = float(dmg)
    lethal_on_active = False
    if opp_hp is not None:
        # ★KO を超えた分の打点は無駄になる。上限で切らないと
        #   「どちらもKOできるとき、素点の大きい方」を選んでベンチKOを捨てる。
        # フラグを分けているのは、**全OFFで旧 starmie-aggro と決定が一致する**ことを
        # 検査できるようにするため(playbook §1「対照実験を先に」/ T7 B4)。
        if _v5_on("KOCAP"):
            val = float(min(dmg, opp_hp))
        if dmg >= opp_hp:
            lethal_on_active = True
            try:
                opp = (state.players[1 - me].active or [None])[0]
                val += 10000.0 * _prize_value(opp.id) if opp else 10000.0
            except (IndexError, TypeError, AttributeError):
                val += 10000.0
    if _v5_on("BENCHDMG"):
        val += _bench_splash_value(state, me, attack_id)
    return val, lethal_on_active


def _flee_to_survive(obs: Observation, state, me, options, has_lethal: bool):
    """[V5/L2] 「ここで倒されると負ける」ときだけ、攻撃より退避を優先する。

    ゆうじの観測への回答の後半にあたる。前半(=攻撃できるのに逃げる)は L1 で塞いだので、
    v1 は原則「殴る」= **わざと死ぬのを許す**挙動になる。それが正しいのは
    **倒されてもまだ相手が勝たないとき**だけである。

    ★ご指示の「相手のサイドが3枚以上残っていれば、わざと死んでも大ダメージを与える」は
      **メガスターミーexでは危険**。megaEx はきぜつでサイドを **3枚** 渡すので、
      相手の残りが**ちょうど3枚**だとその場で相手が勝つ。
      正しい条件は `相手の残りサイド > 自分のサイド価値`(メガexなら**4枚以上**)。
      したがってここでは逆(`<=`)を「退避すべき局面」として使う。

    返り値: 選ぶべき options のインデックス、または None(既定の流れに任せる)。
    """
    if not _v5_on("STANDFIGHT") or has_lethal:
        return None          # リーサルがあるなら殴って取る
    try:
        act = (state.players[me].active or [None])[0]
        opp_prizes = len(state.players[1 - me].prize or [])
    except (IndexError, TypeError, AttributeError):
        return None
    if act is None or act.hp is None:
        return None
    if opp_prizes > _prize_value(act.id):
        return None          # 倒されても相手は勝たない → 殴ってよい(わざと死ぬ)
    if act.hp > _opp_max_damage(state, me):
        return None          # そもそも次の番で倒されない

    # ここに来た = 「次の番に倒され、しかも倒されたら負ける」。退避先を探す。
    cards, _ = _card_db()
    try:
        act_dmg = _best_attack_damage_of_card(act.id)
        cand = [
            pk for pk in (state.players[me].bench or [])
            if pk is not None
            and pk.hp is not None
            and pk.hp > _opp_max_damage(state, me)          # 交代先は即死しない
            and _best_attack_damage_of_card(pk.id) >= act_dmg  # かつ弱くならない
        ]
    except (IndexError, TypeError, AttributeError):
        return None
    if not cand:
        return None          # 逃げ先が無いなら殴るしかない

    # 無償のなみのりビーチがあればそれを使う(エネを1枚も捨てない)
    beach = _beach_ability_index(state, options)
    if beach is not None and _is_water(act.id) and any(_is_water(p.id) for p in cand):
        return beach
    # リトリートは にげるコスト ぶんのエネを失う。**3本とも retreatCost を読んでいなかった。**
    for i, o in enumerate(options):
        if o.type != OptionType.RETREAT:
            continue
        c = cards.get(act.id)
        cost = (c.retreatCost or 0) if c else 0
        have = len(act.energies) if act.energies else 0
        if cost > have:
            return None      # 払えない
        return i
    return None


def _beach_ability_index(state, options):
    """なみのりビーチ(1262)の「1ターンに1回の水どうし入替」の選択肢番号。

    エンジンは OptionType.ABILITY / area=STADIUM として提示する(2026-08-10 プローブで確認)。
    ★このデッキはビーチを2枚積んでおり、王者の段2は「提示された最初の特性を無条件で発動」
    なので、**放置すると毎ターン盲目的にバトル場を引っ込める**(mastercontrol で実測: 提示の53.4%)。
    段2から除外して、ここで条件つきに使う。
    """
    try:
        st = state.stadium or []
        if not st or st[0].id != _BEACH_ID:
            return None
    except (IndexError, TypeError, AttributeError):
        return None
    for i, o in enumerate(options):
        if o.type == OptionType.ABILITY and o.area == AreaType.STADIUM:
            return i
    return None


def _is_water(card_id) -> bool:
    if card_id is None:
        return False
    cards, _ = _card_db()
    c = cards.get(card_id)
    return bool(c and c.cardType == CardType.POKEMON and c.energyType == _WATER_ENERGY_TYPE)


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
    try:
        my_deck_count = state.players[me].deckCount or 0
    except (TypeError, AttributeError, IndexError):
        my_deck_count = 99
    preserve_deck = my_deck_count <= 5

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
    # [V5/L4] ★このデッキは なみのりビーチ を2枚積む。ビーチの「1ターンに1回の入替」は
    # OptionType.ABILITY / area=STADIUM として提示されるので、この無条件ルートに任せると
    # **毎ターン盲目的にバトル場を引っ込める**(mastercontrol での実測: 提示の53.4%で発動)。
    # ビーチ由来だけを除外し、_flee_to_survive の条件つき経路に回す。
    beach_idx = _beach_ability_index(state, options) if _v5_on("STANDFIGHT") else None
    if not preserve_deck:
        idx = first(
            lambda o: o.type == OptionType.ABILITY
            and not (beach_idx is not None and o.area == AreaType.STADIUM)
        )
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
            # [V5/L20] ★リーチ時ベンチ規律: 相手の残りサイド≤2のとき、ベンチが既に2体以上
            # あるなら追加のたねを出さない — 1枚役の「餌」が相手の最短勝ち筋(ボスで釣って
            # 2ターン2枚)の部品になる。実測: フィールドの27%の相手がボス系を実使用(0.34回/譜)、
            # 勝ち譜ep92586696は終盤ベンチに餌が無く相手が詰め手を失った。保険2体は残す。
            if _v5_on("BENCHGUARD"):
                try:
                    if (
                        len(state.players[1 - me].prize or []) <= 2
                        and len(
                            [b for b in (state.players[me].bench or []) if b is not None]
                        )
                        >= 2
                    ):
                        continue
                except (IndexError, TypeError, AttributeError):
                    pass
        elif c.cardType in (CardType.ITEM, CardType.STADIUM, CardType.TOOL):
            rank = 1
            # [V5/L10] ★スタジアムはコスト無しの純利得なので、手札に余裕があるときは
            # コスト持ちグッズ(ハイパーボール等)より先に出す。実測の誤り(ep93628219 step64):
            # 手札4枚[イグニッション,水,ボール,ビーチ]でボールを先に使い、ビーチをコストで
            # 捨てた。ビーチ先出しでも残り2枚でボールのコストは払えた。
            # 手札3枚以下ではグッズ優先を維持(スタジアム先出しがボールのコストを枯らす
            # ゆうじの指摘ケース)。
            if _v5_on("PLAYORDER") and c.cardType == CardType.STADIUM:
                try:
                    if len(state.players[me].hand or []) >= 4:
                        rank = 0.5
                except (IndexError, TypeError, AttributeError):
                    pass
            # [V5/L17] ★グッズの順序: コスト無し(ポフィン/ポケギア/タンカ)を先、
            # 「手札から捨てる」コスト持ち(ハイパーボール等)を後。L10の一般化 —
            # 満ちた手札から先に価値を取り出し、捨てコストは痩せた手札で払う
            if (
                _v5_on("ITEMORDER")
                and c.cardType == CardType.ITEM
                and cid in _hand_cost_item_ids()
            ):
                rank = 1.2
            # [V5/L20] ベンチ充填グッズ(ポフィン系)もリーチ時ベンチ規律の対象
            if (
                _v5_on("BENCHGUARD")
                and c.cardType == CardType.ITEM
                and cid in _bench_fill_item_ids()
            ):
                try:
                    if (
                        len(state.players[1 - me].prize or []) <= 2
                        and len(
                            [b for b in (state.players[me].bench or []) if b is not None]
                        )
                        >= 2
                    ):
                        continue
                except (IndexError, TypeError, AttributeError):
                    pass
        elif c.cardType == CardType.SUPPORTER:
            rank = 2
        else:
            rank = 3
        if preserve_deck and rank != 0:
            continue  # 温存モード: ポケモン以外は場に出さない(ドロー/サーチで山を削らない)
        # [V5/L8] ★ボスの指令系は「目前の獲物より価値が高いときだけ」使う。
        # 実測の誤爆(ep92473413 決定38-40): 相手アクティブがHP110のGrimmsnarl ex
        # (120でKO=2枚)なのに、ボスでベンチのMorgrem(1枚)を引き出して殴った。
        # 規則: 自分の打点で相手アクティブをKOできるなら、ボスは「より多くのサイドを
        # 取れるKO可能なベンチ獲物」がいる時だけ。判定不能時は従来動作(使う)に落ちる。
        if (
            rank == 2
            and _v5_on("BOSSGUARD")
            and cid is not None
            and cid in _gust_supporter_ids()
        ):
            try:
                opp = 1 - me
                opp_active = state.players[opp].active[0]
                dmg = _my_active_damage(state, me)
                evn = _opp_evolvable_names(state, me)
                cards_db, _ = _card_db()

                def _ko_key(pk):
                    """KO可能なら (サイド枚数, 進化脅威0-3) の辞書式価値。KO不能は None。
                    サイド同数でも「育つ前に折れる」獲物が上(ep93624572 step40:
                    ソルロック(1枚,脅威0)よりリオル(1枚,脅威=メガルカリオ3))。"""
                    if pk is None or not (dmg > 0 and (pk.hp or 9999) <= dmg):
                        return None
                    c2 = cards_db.get(pk.id)
                    ev = evn.get(c2.name, 0) if c2 is not None else 0
                    return (_prize_value(pk.id), ev)

                active_key = _ko_key(opp_active)
                bench_keys = [
                    k for k in (_ko_key(b) for b in state.players[opp].bench or []) if k
                ]
                best_bench = max(bench_keys) if bench_keys else None
                # [V5/L24] ★2タテ・ボスコンボ(ゆうじ発見 ep93662273 T12): 相手アクティブの
                # 残りHPが我々のベンチ撃ち量(スプラッシュ50)以下なら、ボスで下げても
                # スプラッシュで取り切れる — ボス線の価値 = ベンチ獲物 + 旧アクティブ
                # (例: マンキー1枚 + 50HPのex2枚 = 3枚 > 前を殴る2枚)。
                # 下げた先がテラ(ベンチ無敵)や壁(ex攻撃無効)、または我々のアクティブが
                # ライダー攻撃のエネ({W})を持たない場合は不成立。
                combo = False
                if (
                    _v5_on("BOSSCOMBO")
                    and opp_active is not None
                    and best_bench is not None
                ):
                    try:
                        my_act = state.players[me].active[0]
                        splash = 0
                        if my_act is not None:
                            c_my = cards_db.get(my_act.id)
                            for aid2 in (c_my.attacks if c_my else None) or []:
                                splash = max(splash, _BENCH_SPLASH.get(aid2, 0))
                        has_colored = bool(
                            my_act is not None
                            and any(
                                e is not None and e.id != _IGNITION_ID
                                for e in my_act.energyCards or []
                            )
                        )
                        oc = cards_db.get(opp_active.id)
                        blocked = opp_active.id in _ex_wall_ids() or bool(
                            oc is not None and getattr(oc, "tera", False)
                        )
                        if (
                            splash > 0
                            and has_colored
                            and not blocked
                            and (opp_active.hp or 9999) <= splash
                        ):
                            combo = True
                    except Exception:
                        combo = False
                if (
                    not combo
                    and active_key is not None
                    and (best_bench is None or best_bench <= active_key)
                ):
                    continue  # ボス見送り: この番はアクティブのKOを取りに行く
                if best_bench is not None:
                    # [V5/L8b] ベンチにより価値の高いKO可能な獲物がいる → ボスを
                    # 他のサポート(ドロー系)より優先する(初手権)。実測の誤り
                    # (ep93624572 step40): ボスとゼイユ両方出せる局面で並び順の
                    # ゼイユが選ばれ、リオル1パン+進化ライン折りを逃した
                    rank = 1.9
            except Exception:
                pass
        # [V5/L15] ★手札破壊/リセット系サポート(ゼイユ=全捨て+5、リーリエ/ジャッジ=山へ戻す)は
        # 「手札が痩せているときだけ」使う。残り手札3枚以上での手札全捨ては資源の自壊
        # (実測: ep93637347 T9、あと1枚で勝ちの盤面でゼイユが手札を焼いた。トウコ=
        # 進化+エネのサーチが正解だった)。加算系(トウコ等)を先に、破壊系は後回し(rank 2.3)。
        # 手札2枚以下なら破壊系はむしろ安価なドローエンジンなので従来どおり rank 2。
        if (
            rank == 2
            and _v5_on("SUPPRANK")
            and cid is not None
            and cid in _hand_reset_supporter_ids()
        ):
            try:
                others = len(state.players[me].hand or []) - 1
                # [V5/L19] ★両者リセット(ジャッジ系)は相手の手札が太い(≥6)ときに
                # 「妨害」として解禁 — ただし自分の巻き添えが小さい(残り≤3)ときだけ。
                # L15は自傷防止しか見ていなかった(照合表③-2)
                disruption = False
                if _v5_on("JUDGETIME") and cid in _both_reset_supporter_ids():
                    if (state.players[1 - me].handCount or 0) >= 6 and others <= 3:
                        disruption = True
                if not disruption and others >= 3:
                    rank = 2.3
                # [V5/L18] ★同条件なら「山に戻す」型(リーリエ)を「トラッシュ」型(ゼイユ)より
                # 先に — 資源が生存する側を優先
                if cid in _discard_hand_supporter_ids():
                    rank += 0.02
            except (IndexError, TypeError, AttributeError):
                pass
        if rank < play_rank:
            play_best, play_rank = i, rank
    if play_best is not None:
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
    # [V5/L21] ★弱いバトル場へエネを注がない(ゆうじ8/17 + 敵対レビュー#1/#3、評議会後の必要判定)。
    # 従来キーは「飢えたバトル場」が打点に関係なく最優先で、ガスト等でヒトデマン(20点)が
    # 前に出ると、ベンチの本命(メガ210点)より先に貼って1ターン1枚の権利を捨てていた。
    # 打点50未満のバトル場は、ベンチに飢えた本命(打点120以上)がいる場合のみ優先を外す。
    bank_target_exists = False
    if _v5_on("ENERGYBANK"):
        try:
            for bpk in state.players[me].bench or []:
                if bpk is None:
                    continue
                b_have = len(bpk.energies) if bpk.energies else 0
                if (
                    (_best_attack_damage_of_card(bpk.id) or 0) >= 120
                    and b_have < _max_attack_cost(bpk.id)
                ):
                    bank_target_exists = True
                    break
        except (IndexError, TypeError, AttributeError):
            bank_target_exists = False
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
        if (
            _v5_on("ENERGYBANK")
            and is_active
            and bank_target_exists
            and (dmg or 0) < 50
        ):
            is_active = 0  # 弱い前へ優先で貼らない → 打点比較でベンチの本命が勝つ
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
            pri = 2 if (evolved and is_active and have < 2) else 0
        key = (pri, hungry, is_active if hungry else 0, dmg, -have)
        if key > attach_key:
            attach_best, attach_key = i, key
    if attach_best is not None:
        return [attach_best]

    # 5. 攻撃（盤面の取れ高が最大。リーサルはサイド価値ぶん別の桁に乗る）
    #
    # [V5/L3] 旧実装は `_estimate_damage` の素点だけで選び、
    # ①Jetting Blow のベンチ50を無視 ②KO超過分の無駄打点を割り引かない、の2点で
    # 「2体KOできる Jetting Blow より 素点210の Nebula Beam」を必ず選んでいた。
    attack_best, attack_val, has_lethal = None, -1.0, False
    for i, o in enumerate(options):
        if o.type != OptionType.ATTACK or o.attackId is None:
            continue
        val, lethal = _attack_value(state, me, o.attackId)
        if val > attack_val:
            attack_best, attack_val, has_lethal = i, val, lethal

    # 5.0 [V5/L2] 「次の番に倒され、しかも倒されたら相手が勝つ」ときだけ退避を優先する。
    # それ以外は殴る = **わざと死ぬのを許す**(相手の残りサイドが自分のサイド価値より多いなら、
    # 倒されても相手は勝たないので、打点を通した方が得)。
    flee = _flee_to_survive(obs, state, me, options, has_lethal)
    if flee is not None:
        return [flee]

    # ★段5.5(2026-07-19 の LO 敗北への安全弁)に到達できる条件を保つ(T7 B7)。
    # `attack_val > 0` のままだと、副次50点のチップだけで「攻撃できる」と判定され、
    # **壁相手に1点も通らないまま棒立ちを続け、退却弁が永久に開かない**。
    # 実打点が通るか、ベンチKOが取れるときだけ攻撃で確定する。
    real_progress = attack_val >= 10000.0 or (attack_best is not None and _real_damage_ok(
        state, me, options[attack_best].attackId))
    if attack_best is not None and attack_val > 0 and real_progress:
        return [attack_best]

    # 5.5 リトリート: 攻撃で進展がない番に、ベンチに「ワザコスト充足＋打点あり」の
    # ポケモンがいれば逃げる。バトル場棒立ち→エネ枯渇→敗北のロック対策
    # (2026-07-19 実ラダー検死: プライズ0のまま35ターン膠着して山札切れが実在)。
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
    # [V5/L4] 旧実装の生の `return [0]` は minCount>1 / maxCount<1 で違法手になりうる
    # (robustness-guard が実測で再現)。件数を契約から導く _fallback に置き換える。
    return _fallback(obs.select)


# ---------------------------------------------------------------------------
# [V5/L7-L8] ボスの指令系の価値関数(2026-08-16、ゆうじのカードパターン §1/§3。全てDB導出)
# ---------------------------------------------------------------------------

_EVOLVABLE_NAMES = None
_GUST_IDS = None


def _evolution_threat_map(card_ids):
    """カード集合の進化系譜から {進化元の名前: 系譜で到達しうる最大サイド価値} を作る。

    例: リオル→ルカリオ→メガルカリオex(3枚) なら threat["Riolu"]=3。
    「育つ前に折る」の優先度を、単なる有無(0/1)でなく**育った先の脅威の大きさ**で
    序列化する(ゆうじ指摘 2026-08-16 夜: 進化ポケモンロジックの弱さ)。"""
    threat = {}
    try:
        cards, _ = _card_db()
        children = {}
        for cid in set(card_ids):
            c = cards.get(cid)
            ev = getattr(c, "evolvesFrom", None) if c else None
            if ev:
                children.setdefault(ev, []).append(c)

        def val(c, depth):
            if c is None or depth > 3:
                return 0
            v = _prize_value(c.cardId)
            for ch in children.get(c.name, []):
                v = max(v, val(ch, depth + 1))
            return v

        for ev, chs in children.items():
            threat[ev] = max(val(ch, 0) for ch in chs)
    except Exception:
        pass
    return threat


def _evolvable_names():
    """プール全体の進化脅威マップ {進化元名: 最大到達サイド価値}(キャッシュ)。"""
    global _EVOLVABLE_NAMES
    if _EVOLVABLE_NAMES is None:
        try:
            cards, _ = _card_db()
            _EVOLVABLE_NAMES = _evolution_threat_map(cards.keys())
        except Exception:
            _EVOLVABLE_NAMES = {}
    return _EVOLVABLE_NAMES


def _visible_ids_state(pl) -> list[int]:
    """_visible_ids(dict版)のデータクラス版: 場+付属+捨て札の見えているカードID。"""
    ids = []
    try:
        for pk in list(pl.active or []) + list(pl.bench or []):
            if pk is None:
                continue
            ids.append(pk.id)
            for arr in (pk.energyCards, pk.tools, pk.preEvolution):
                for c in arr or []:
                    if c is not None:
                        ids.append(c.id)
        for c in pl.discard or []:
            if c is not None:
                ids.append(c.id)
    except (TypeError, AttributeError):
        pass
    return ids


def _opp_evolvable_names(state, me) -> dict:
    """相手が「実際に」進化させうるポケモン名(ゆうじ指摘 2026-08-16 夜)。

    メタ辞書で相手デッキを同定できた場合(被覆率≥0.5、_infer_enemy_deck と同一基準)は
    **そのリストに進化先が入っている名前だけ**を脅威とみなす。同定できなければ
    プール全体(_evolvable_names)へフォールバック = 従来挙動より狭まることはあっても
    誤って空にはならない。"""
    try:
        foe = state.players[1 - me]
        vis = _visible_ids_state(foe)
        if vis:
            vc = _counter(vis)
            best, best_score = None, -1.0
            for cand in _META_DECKS.values():
                cc = _counter(cand)
                covered = sum(min(n, cc.get(c, 0)) for c, n in vc.items())
                score = covered / max(1, len(vis))
                if score > best_score:
                    best, best_score = cand, score
            if best is not None and best_score >= 0.5:
                return _evolution_threat_map(best)
    except Exception:
        pass
    return _evolvable_names()


def _gust_supporter_ids():
    """相手ベンチを引きずり出すサポート(ボスの指令系)のID集合(効果文から導出、ID非固定)。"""
    global _GUST_IDS
    if _GUST_IDS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                if c.cardType != CardType.SUPPORTER:
                    continue
                for sk in c.skills or []:
                    # エンジンの効果文は ’(U+2019) を使う。ASCII ' に正規化してから照合
                    t = (getattr(sk, "text", "") or "").replace("’", "'")
                    if "opponent's Benched" in t and "Active" in t and "witch" in t:
                        ids.add(c.cardId)
        except Exception:
            pass
        _GUST_IDS = ids
    return _GUST_IDS


_BENCH_RIDER_ATTACKS = None
_TOOL_RETREAT_REDUCTION = {}


def _attack_has_bench_rider(attack_id) -> bool:
    """ワザがベンチにも当たるか(効果文から導出。ジェットブロー等)。"""
    global _BENCH_RIDER_ATTACKS
    if _BENCH_RIDER_ATTACKS is None:
        s = set()
        try:
            _, attacks = _card_db()
            for a in attacks.values():
                t = (getattr(a, "text", "") or "").replace("’", "'")
                if "Benched" in t and "damage" in t:
                    s.add(a.attackId)
        except Exception:
            pass
        _BENCH_RIDER_ATTACKS = s
    return attack_id in _BENCH_RIDER_ATTACKS


def _tool_retreat_reduction(tool_cid) -> int:
    """どうぐの「にげるコスト軽減」量(効果文から導出: 緊急ボード1/ふうせん2)。"""
    if tool_cid in _TOOL_RETREAT_REDUCTION:
        return _TOOL_RETREAT_REDUCTION[tool_cid]
    red = 0
    try:
        cards, _ = _card_db()
        c = cards.get(tool_cid)
        for sk in (c.skills if c else None) or []:
            t = (getattr(sk, "text", "") or "").replace("’", "'")
            # 軽減量はエネシンボルの個数で書かれる: 「... is {C} less」=1 / 「{C}{C} less」=2。
            # 「more」(重力玉)は除外条件("less"必須)で自然に落ちる
            if "Retreat Cost" in t and "less" in t:
                red = t.count("{C}")
    except Exception:
        red = 0
    _TOOL_RETREAT_REDUCTION[tool_cid] = red
    return red


def _bind_score(pk) -> int:
    """「縛り標的」判定(ゆうじ §2): エネ0 かつ 補正後にげるコスト≥2 なら1。
    引きずり出せば、逃げられず・殴れず、相手の手貼り権を人質に取れる。"""
    try:
        if pk.energies:
            return 0
        cards, _ = _card_db()
        c = cards.get(pk.id)
        rc = (getattr(c, "retreatCost", 0) or 0) if c else 0
        for tool in pk.tools or []:
            if tool is not None:
                rc -= _tool_retreat_reduction(tool.id)
        return 1 if rc >= 2 else 0
    except Exception:
        return 0


_HAND_RESET_SUPPORTERS = None
_HAND_COST_ITEMS = None
_DISCARD_HAND_SUPPORTERS = None
_BOTH_RESET_SUPPORTERS = None
_BENCH_FILL_ITEMS = None


def _hand_cost_item_ids():
    """「手札から捨てる」コストを要求するグッズ(ハイパーボール等)のID集合(効果文導出)。"""
    global _HAND_COST_ITEMS
    if _HAND_COST_ITEMS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                if c.cardType != CardType.ITEM:
                    continue
                for sk in c.skills or []:
                    t = (getattr(sk, "text", "") or "").replace("’", "'")
                    if "iscard" in t and "from your hand" in t:
                        ids.add(c.cardId)
        except Exception:
            pass
        _HAND_COST_ITEMS = ids
    return _HAND_COST_ITEMS


def _discard_hand_supporter_ids():
    """手札を「トラッシュ」する型のリセット(ゼイユ)。山戻し型より資源損失が大きい。"""
    global _DISCARD_HAND_SUPPORTERS
    if _DISCARD_HAND_SUPPORTERS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                if c.cardType != CardType.SUPPORTER:
                    continue
                for sk in c.skills or []:
                    t = (getattr(sk, "text", "") or "").replace("’", "'")
                    if "Discard your hand" in t:
                        ids.add(c.cardId)
        except Exception:
            pass
        _DISCARD_HAND_SUPPORTERS = ids
    return _DISCARD_HAND_SUPPORTERS


def _both_reset_supporter_ids():
    """両者の手札をリセットする妨害型(ジャッジマン等)。"""
    global _BOTH_RESET_SUPPORTERS
    if _BOTH_RESET_SUPPORTERS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                if c.cardType != CardType.SUPPORTER:
                    continue
                for sk in c.skills or []:
                    t = (getattr(sk, "text", "") or "").replace("’", "'")
                    if "shuffles their hand" in t:
                        ids.add(c.cardId)
        except Exception:
            pass
        _BOTH_RESET_SUPPORTERS = ids
    return _BOTH_RESET_SUPPORTERS


def _bench_fill_item_ids():
    """山からたねをベンチに直接並べるグッズ(ポフィン等)のID集合(効果文導出)。"""
    global _BENCH_FILL_ITEMS
    if _BENCH_FILL_ITEMS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                if c.cardType != CardType.ITEM:
                    continue
                for sk in c.skills or []:
                    t = (getattr(sk, "text", "") or "").replace("’", "'")
                    if "onto your Bench" in t:
                        ids.add(c.cardId)
        except Exception:
            pass
        _BENCH_FILL_ITEMS = ids
    return _BENCH_FILL_ITEMS


def _hand_reset_supporter_ids():
    """「自分の手札を捨てる/山に戻す」系サポートのID集合(効果文から導出)。
    ゼイユ(手札全捨て+5)/リーリエ(戻して6)/ジャッジマン(両者戻して4)等。"""
    global _HAND_RESET_SUPPORTERS
    if _HAND_RESET_SUPPORTERS is None:
        ids = set()
        try:
            cards, _ = _card_db()
            for c in cards.values():
                if c.cardType != CardType.SUPPORTER:
                    continue
                for sk in c.skills or []:
                    t = (getattr(sk, "text", "") or "").replace("’", "'")
                    if (
                        "Discard your hand" in t
                        or "Shuffle your hand into your deck" in t
                        or "shuffles their hand" in t
                    ):
                        ids.add(c.cardId)
        except Exception:
            pass
        _HAND_RESET_SUPPORTERS = ids
    return _HAND_RESET_SUPPORTERS


def _my_active_damage(state, me) -> int:
    """自分のバトル場の(基本値ベースの)最大打点。分からなければ0。"""
    try:
        act = state.players[me].active[0]
        return _best_attack_damage_of_card(act.id) or 0
    except (IndexError, TypeError, AttributeError):
        return 0


def _dragout_value(obs: Observation, me: int, opt) -> tuple:
    """相手ベンチから前に引きずり出す獲物の価値(ボスの指令系の対象選択)。

    優先順(ゆうじのカードパターン 2026-08-16。リオル等の名指しはせずDBから導出):
      ①いま自分の打点でKOできる(そのサイド枚数が多い順)。
        「50前払い→引き出して120」の170ラインは、傷ついた個体の残りHP ≤ 打点として
        ここに自然に入る(狙撃順は変えない = EXP6/6bで棄却済みの罠を踏まない)
      ②まだ進化先が存在する個体(育つ前に折る)。残りHPが低いほど優先
      ③エネ・打点が低い個体(前に出させて にげエネを強要=足止め)
    """
    state = obs.current
    try:
        pk = _pokemon_at(state, opt.playerIndex, opt.area, opt.index)
        if pk is None:
            return (0, 0, 0, 0, 0, 0)
        hp = pk.hp or 9999
        dmg = _my_active_damage(state, me)
        koable = 1 if (dmg > 0 and hp <= dmg) else 0
        prizes = _prize_value(pk.id) if koable else 0
        cards, _ = _card_db()
        c = cards.get(pk.id)
        # 「育つ前に折る」は相手デッキ基準の**脅威の大きさ**(0〜3)で序列化。
        # リオル(→メガルカリオ3枚)はズガイドス(→1枚系譜)より優先される
        evolvable = _opp_evolvable_names(state, me).get(c.name, 0) if c is not None else 0
        energy = len(pk.energies) if pk.energies else 0
        atk = _best_attack_damage_of_card(pk.id) or 0
        # 縛り標的(エネ0・補正後にげ≥2)は「折る」の次に優先。相手の手貼り権を人質に取り、
        # ボス2枚目があれば「貼らせて→また下げる」のエネ枯渇ループが自然に成立する
        bind = _bind_score(pk)
        return (koable, prizes, evolvable, bind, -hp, -(energy * 1000 + atk))
    except Exception:
        return (0, 0, 0, 0, 0, 0)


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
        # [V5/L11] ★ワザ由来のダメージ(ctx=DAMAGE)に限り、ex攻撃を無効化する壁
        # (イワパレス等、_ex_wall_ids)を**最後尾に落とす** — 自分のアタッカーがexのとき、
        # 壁への割り振りは0ダメの捨て玉になる(実測: ep93624572 step77 で50を壁に着弾)。
        # ダメカン設置(ctx=13/14)は「ワザのダメージ」ではないため壁を貫通する → 対象外。
        # これは対象の除外(取り逃し)ではなく序列の後退のみ。EXP6/6bの棄却領域
        # (脅威優先への並べ替え)とは別物 — 0ダメ対象の後退はKO変換を増やす側にしか働かない。
        wall_ids = None
        if _v5_on("SNIPEWALL") and ctx == SelectContext.DAMAGE:
            try:
                my_act = state.players[me].active[0]
                cdb, _ = _card_db()
                mc = cdb.get(my_act.id) if my_act is not None else None
                if mc is not None and (
                    getattr(mc, "ex", False) or getattr(mc, "megaEx", False)
                ):
                    wall_ids = _ex_wall_ids()
            except Exception:
                wall_ids = None

        def hp_of(i):
            o = options[i]
            pk = _pokemon_at(state, o.playerIndex, o.area, o.index)
            if pk is None:
                return (0, 9999)
            is_wall = 1 if (wall_ids and pk.id in wall_ids) else 0
            return (is_wall, pk.hp if pk.hp is not None else 9999)

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
        # [V5/L7] ★候補が全て相手側なら「自分を場に出す」でなく「獲物を引きずり出す」選択
        # (ボスの指令。実測: SWITCH/min1/max1/候補=相手ベンチ、eps55468574の4件で確認)。
        # 従来はこの区別が無く、自分用の評価(エネ付き・高打点を前に)を流用して
        # **相手の一番育った駒**を引きずり出していた。獲物の価値(_dragout_value)で選び直す。
        if _v5_on("BOSSTARGET"):
            try:
                if n > 0 and all(
                    o.playerIndex is not None and o.playerIndex != me for o in options
                ):
                    ranked = sorted(
                        range(n),
                        key=lambda i: _dragout_value(obs, me, options[i]),
                        reverse=True,
                    )
                    return ranked[:count]
            except Exception:
                pass
        ranked = sorted(
            range(n),
            key=lambda i: _pokemon_value_for_active(obs, me, options[i]),
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
    # [V5/L9] 使い分け(ゆうじ §3, 2026-08-16): 相手アクティブを**倒せるワザが複数ある**ときだけ、
    # その中で「ベンチにも当たる」ワザを優先する(過剰打点の210より120+裏50)。
    # KOできるワザ同士の入れ替えなので、KOを取り逃す方向には構造的に動けない
    # (EXP6/6bで棄却された「狙撃順を脅威優先に変える」とは別物)。
    if _v5_on("ATTACKSPLIT"):
        try:
            opp = 1 - me
            oa = state.players[opp].active[0]
            ohp = oa.hp if (oa is not None and oa.hp is not None) else None
            if ohp:
                kos = [i for i in ranked if dmg_of(i) >= ohp]
                if len(kos) >= 2:
                    riders = [
                        i for i in kos
                        if sel.option[i].attackId is not None
                        and _attack_has_bench_rider(sel.option[i].attackId)
                    ]
                    if riders:
                        best = max(riders, key=dmg_of)
                        ranked = [best] + [i for i in ranked if i != best]
        except (IndexError, TypeError, AttributeError):
            pass
    k = max(sel.minCount, min(1, sel.maxCount))
    return ranked[:k]


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
    # 2026-08-17 追記(評議会・敵対レビュー指摘#10): 最悪2対面が辞書に不在だった。
    # 実ラダーと60/60一致を検証済みのゲージデッキを純データ追加(ロジック変更なし)
    # 2026-08-17 追記2: ドラパルト(実戦4譜・一致22/60=辞書外だった)。観測済み実リスト
    "lopunny_observed": [11, 11, 11, 11, 13, 14, 14, 14, 66, 66, 66, 66, 174, 305, 305, 305, 305, 848, 848, 848, 848, 849, 849, 849, 1086, 1086, 1086, 1086, 1121, 1121, 1121, 1121, 1122, 1122, 1122, 1122, 1152, 1152, 1152, 1152, 1174, 1174, 1174, 1174, 1182, 1182, 1182, 1197, 1225, 1225, 1225, 1225, 1227, 1227, 1227, 1227, 1229, 1229, 1229, 1229],  # 観測2譜
    "garchomp_observed": [6, 6, 6, 6, 6, 6, 20, 20, 20, 20, 341, 341, 341, 341, 342, 342, 342, 342, 379, 379, 379, 379, 380, 380, 380, 380, 381, 381, 381, 387, 1080, 1086, 1086, 1086, 1086, 1122, 1122, 1123, 1141, 1142, 1142, 1142, 1152, 1152, 1152, 1152, 1173, 1182, 1182, 1182, 1182, 1197, 1197, 1219, 1227, 1227, 1227, 1227, 1256, 1256],  # 観測1譜
    "dragapult_observed": [2, 2, 2, 2, 5, 5, 5, 5, 7, 7, 112, 112, 119, 119, 119, 119, 120, 120, 120, 120, 121, 121, 121, 140, 235, 235, 1071, 1080, 1086, 1086, 1086, 1086, 1097, 1097, 1120, 1120, 1120, 1120, 1121, 1121, 1121, 1121, 1152, 1152, 1152, 1152, 1182, 1182, 1182, 1198, 1198, 1198, 1213, 1227, 1227, 1227, 1227, 1231, 1256, 1256],
    "lucario_makthanithin": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 673, 673, 674, 674, 675, 675, 676, 676, 676, 677, 677, 677, 677, 678, 678, 678, 678, 1102, 1102, 1102, 1102, 1123, 1123, 1141, 1141, 1141, 1141, 1142, 1142, 1142, 1142, 1152, 1152, 1159, 1182, 1182, 1182, 1192, 1192, 1192, 1192, 1227, 1227, 1227, 1227, 1252],
    "archaludon_tomato": [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 57, 169, 169, 169, 169, 190, 190, 190, 190, 666, 666, 666, 666, 1097, 1097, 1097, 1121, 1121, 1121, 1121, 1122, 1122, 1122, 1122, 1147, 1147, 1147, 1147, 1152, 1152, 1152, 1152, 1159, 1182, 1182, 1182, 1182, 1185, 1185, 1185, 1185, 1227, 1227, 1227, 1227, 1244, 1244, 1244, 1244],
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
    # [V5/L1] ★探索が v1 の答えを **RETREAT に** 差し替えるのを禁止する。
    #
    # 理由(実測): `_evaluate` のサイド項は 10000点/枚 で、メガexのKOは3枚=30000点。
    # `_OVERRIDE_MARGIN`(120.0)とは **250倍の桁差**があり、マージンは事実上機能しない。
    # そのうえロールアウトは root_turn+2 で打ち切るので、探索が見ているのは
    # 「この番に死なない」だけで、「1ターン延命して次の番に結局死ぬ」は地平の外にある。
    # 結果、**攻撃が合法で v1 が ATTACK と答えている局面でも必ず逃げる**。
    # 実物 `eps55169074/ep89396266.json` step94 で 5/5 再現(v1=ATTACK → 探索=RETREAT)。
    #
    # 逃げる判断そのものを消すのではなく、**v1 の盤面価値層(_stand_or_flee)に委ねる**。
    # あちらは にげるコスト・交代先の打点・サイド枚数を実際に読む。
    # 補強(主根拠にはしない): data.md:533-560 の iter4 クラス単独A/B は
    # energy単独 53.8%[50.3,57.2] が有意勝ち、retreat/attack の追加はむしろ希釈(51.4%)。
    # ただしあれは v3/iter4 という別実装・ミラー文脈の測定である。
    if _v5_on("OVERRIDE_GATE"):
        try:
            o = sel.option[best]
            # RETREAT だけでなく **なみのりビーチ経由の入替**も塞ぐ(T7 N2)。
            # 診断した機構(サイド項30000 vs マージン120)は選択肢の種類に依存しないので、
            # ビーチ2枚積みのこのデッキでは同じ病理が同じ強さで再現する。
            if o.type == OptionType.RETREAT or (
                o.type == OptionType.ABILITY and o.area == AreaType.STADIUM
            ):
                return None
        except (IndexError, TypeError, AttributeError):
            pass
    # [V5/L6] ★探索が v1 の生産的な手を **END に** 差し替えるのを禁止する(ENDストール)。
    # 機構は L1 と同一: サイド項(±10,000/枚)がマージン(120)を250倍で圧倒し、
    # 地平 root_turn+2 では「行動すると反撃でサイドを失う」だけが見え、
    # 「何もしなくても同じ反撃が来る」は地平の外にある。
    # 実測(2026-08-14、eps55468574 60譜): 選択=END かつ 生産的な手(ATTACK/ATTACH)が
    # 合法だった MAIN 決定 9回、うち8回が敗北譜。9局面すべてで v1 は非END(27/27反復)、
    # 探索ONでのみENDが再現 = 犯人はこの上書き経路(層S、stall_repro.py)。
    # v1 が END を選ぶのは他に合法手が無いときだけ(_choose_main の優先順)なので、
    # best==v1_rep の早期 return と合わせ、この禁止は
    # 「v1 の非END を END へ差し替える」経路だけを正確に塞ぐ。
    if _v5_on("ENDGUARD"):
        try:
            if sel.option[best].type == OptionType.END:
                return None
        except (IndexError, TypeError, AttributeError):
            pass
    # [V5/L12] ★探索が v1 の**無料価値の行動**(PLAY/ATTACH/EVOLVE/ABILITY)を ATTACK に
    # 差し替えるのを禁止する。攻撃はターンを終わらせるため、先に攻撃すると
    # エネ貼り権・グッズ・サポートが全て消滅する。逆順(先に無料行動→後で攻撃)は
    # 何も失わない — 攻撃の合法性は手札に依存しないので必ず残っている。
    # 実測(2026-08-16深夜、ep93632748 step50 = 我々のT3): 手札[タンカ,水,ポフィン,リーリエ]で
    # 即ATTACKし全部を放棄。v1は3/3でPLAY、探索ONで確率的にATTACK再現 = 上書き経路が犯人。
    # RETREAT/END を v1 が提案している場合は対象外(あちらの上書きは別の判断)。
    if _v5_on("ATTACKGUARD"):
        try:
            if sel.option[best].type == OptionType.ATTACK and sel.option[
                v1_rep
            ].type in (
                OptionType.PLAY,
                OptionType.ATTACH,
                OptionType.EVOLVE,
                OptionType.ABILITY,
            ):
                return None
        except (IndexError, TypeError, AttributeError):
            pass
    # [V5/L14] ★v1 が「ボスの指令系サポートのPLAY」を選んでいる場合、探索の上書きを禁止。
    # L8b の初手権(ベンチに上位獲物→ボス優先)は価値推論で選ばれており、探索の
    # PLAY→PLAY 上書き(実測: ep93624572 step40 でボス→ゼイユ)はマージン既知問題の
    # スケールで無根拠に潰しうる。判定不能時は従来動作(上書き許可)に落ちる。
    if _v5_on("GUSTLOCK"):
        try:
            vo = sel.option[v1_rep]
            if vo.type == OptionType.PLAY and vo.index is not None:
                yi = (obs_dict.get("current") or {}).get("yourIndex")
                hand = ((obs_dict.get("current") or {}).get("players") or [{}, {}])[
                    yi
                ].get("hand") or []
                if vo.index < len(hand):
                    cid_v1 = (hand[vo.index] or {}).get("id")
                    if cid_v1 in _gust_supporter_ids():
                        return None
        except Exception:
            pass
    # [V5/L16] ★探索が「手札リセット系サポート(ゼイユ/リーリエ/ジャッジ等)のPLAY」**へ**
    # 上書きするのを禁止。探索はカードテキストを読めず、手札引き直しはロールアウト上
    # 選択肢が増えて過大評価される(捨てる資源の価値が計れない)。実測: ep93637347 step85
    # (手札8枚・あと1枚で勝ち)で v1=EVOLVE(ベンチのメガ育成=正着)を探索がゼイユ/リーリエに
    # 上書きし手札を焼いた。リセットを使う判断は v1(L15: 手札2枚以下のときだけ)に委ねる。
    if _v5_on("RESETLOCK"):
        try:
            bo = sel.option[best]
            if bo.type == OptionType.PLAY and bo.index is not None:
                yi = (obs_dict.get("current") or {}).get("yourIndex")
                hand2 = ((obs_dict.get("current") or {}).get("players") or [{}, {}])[
                    yi
                ].get("hand") or []
                if bo.index < len(hand2):
                    if (hand2[bo.index] or {}).get("id") in _hand_reset_supporter_ids():
                        return None
        except Exception:
            pass
    if totals[best] / counts[best] < totals[v1_rep] / counts[v1_rep] + _OVERRIDE_MARGIN:
        return None
    return [best]


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
                # [V5/L13] ★攻撃選択で v1(L9)が「相手アクティブをKOでき、かつベンチにも
                # 当たる技」を選んでいる場合は探索に上書きさせない。両技ともKOなら
                # その交換はどちらでも勝ち — 差は裏の50が乗るかだけで、これは確定の
                # 追加価値(ゆうじ原則 2026-08-16: 攻撃力ではなく取れる枚数を優先)。
                # 確定KO同士の選り好みは探索の価値が最も薄い領域なので、探索資産
                # (+13.62pt)へのリスクは最小。判定不能時は従来どおり探索へ。
                skip_search = False
                if _v5_on("RIDERLOCK") and sel.type == SelectType.ATTACK and v1:
                    try:
                        o = sel.option[v1[0]]
                        aid = o.attackId
                        if aid is not None and _attack_has_bench_rider(aid):
                            st = obs.current
                            me2 = st.yourIndex
                            oa = st.players[1 - me2].active[0]
                            if (
                                oa is not None
                                and oa.hp is not None
                                and _estimate_damage(aid, st, me2) >= oa.hp
                            ):
                                skip_search = True
                    except Exception:
                        skip_search = False
                if not skip_search:
                    picked = _search_decide(obs_dict, sel, v1)
                    if (
                        picked is not None
                        and sel.minCount <= len(picked) <= sel.maxCount
                        and len(set(picked)) == len(picked)
                        and all(0 <= p < len(sel.option) for p in picked)
                    ):
                        return picked
        except Exception:
            pass
        return v1
    except Exception:
        # Observationパース・v1本体まで含めて何が起きても合法手を返す
        return _last_resort(obs_dict)

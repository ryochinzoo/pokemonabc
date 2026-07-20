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
    if not preserve_deck:
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
        if preserve_deck and rank != 0:
            continue  # 温存モード: ポケモン以外は場に出さない(ドロー/サーチで山を削らない)
        if rank < play_rank:
            play_best, play_rank = i, rank
    if play_best is not None:
        return [play_best]

    # 4. エネ貼り。ワザコストが足りないポケモン優先(その中でバトル場>高打点)。
    # 全員足りているなら高打点に予備を1枚だけ(9枚積み・バトル場エネ0の詰み対策)。
    attach_best, attach_key = None, (-1, -1, -1, -99)
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
        key = (hungry, is_active if hungry else 0, dmg, -have)
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
# v3 探索層: 決定化MCTS + 相手モデリング + サイドトレード評価 (D17)。
# エンジン内蔵の SearchBegin/SearchStep で候補手を実際に打って評価し、
# v1 (_v1_decide) を明確なマージンで上回るときだけ上書きする(D14の保守構造を維持)。
# 失敗・時間超過は常に v1 に落ちる。
#
# アブレーション用フラグ(環境変数。成分別寄与の計測に使う):
#   V2_NO_SEARCH=1     探索を全停止(=v1相当)
#   V3_MCTS=1          第1世代の決定化MCTSを有効化(iter4既定は平坦探索)
#   V3_OPPMODEL=1      9型相手モデリングを有効化(既定はv2.1bの5型argmax)
#   V3_PRIZETRADE=1    サイドトレード評価を有効化(既定はv2.1b評価関数)
#   (旧 V3_NO_* も後方互換で解釈: 指定時はオプトインを打ち消す)
# iter4(D19)のクラス限定上書き:
#   V3_SHADOW=1        上書きを記録するだけで適用しない(反実仮想の露出分布収集)
#   V3_CLASSES=a,b     上書き許可クラス。既定 retreat,attack,energy。"all"でゲート無効
#   V3_NO_LETHAL=1     リーサル/ブランダー層(終局検知のみ・評価関数フリー)を停止
# ============================================================
import ctypes as _ct
import json
import math as _math
import random as _rnd
import time as _time

try:
    from cg.sim import lib as _lib
except Exception:  # エンジンが読めない環境でも v1 として動く
    _lib = None

def _env_int(name: str, default: int) -> int:
    """env上書き可能な整数設定。不正値でimportを落とさない(落ちる=全対局没収)。"""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


_SEARCH_BUDGET_SEC = 0.6   # 1手あたりの探索予算
_MAX_CANDIDATES = 24       # 分岐点で展開する候補手の上限
_DETERMINIZATIONS = _env_int("V3_DETS", 3)  # 隠れ情報のサンプル数
_ROLLOUT_MAX_STEPS = 60    # ロールアウト/前進の最大ステップ数
_OVERRIDE_MARGIN = 120.0   # v1を上書きするのに要する評価差(盤面項スケール)
_HORIZON_TURNS = 2         # 評価地点: 相手の返し番が終わるまで
_MCTS_SIMS = _env_int("V3_SIMS", 40)  # 決定化1本あたりのシミュレーション数
_MCTS_UCB_C = 0.7          # UCB1探索定数(tanh正規化した価値[-1,1]に対して)
_MCTS_MIN_VISITS = _env_int("V3_MINVISITS", 3)  # 上書き資格に要する訪問数/決定化(最大化バイアス対策)
# 木の深さ上限。1=ルート候補のみ分岐し、続きは常にv1ロールアウト(=v2と同じ対比較を
# 保ったままUCBでサンプル配分だけ適応化)。深い木は評価関数の穴を突く手を過大評価して
# 悪化した(v3.0=41.5%, 診断はdata.md 2026-07-19)。
_MAX_TREE_DEPTH = _env_int("V3_DEPTH", 1)
_MCTS_EVAL_SCALE = 3000.0  # 生評価値→tanh正規化のスケール
_MAX_ENGINE_STEPS = 6000   # 1判断あたりのSearchStep上限(メモリ・時間の安全弁)

def _flag_on(name: str) -> bool:
    return os.environ.get(name, "") not in ("", "0")


# iter4(第2世代, D19): 既定=v2.1b完全等価(平坦探索+v2評価+5型辞書)。
# 第1世代の3成分は機構診断(対標本差分推定器の破壊)によりオプトインへ降格。
_FLAG_NO_MCTS = (not _flag_on("V3_MCTS")) or _flag_on("V3_NO_MCTS")
_FLAG_NO_OPPMODEL = (not _flag_on("V3_OPPMODEL")) or _flag_on("V3_NO_OPPMODEL")
_FLAG_NO_PRIZETRADE = (not _flag_on("V3_PRIZETRADE")) or _flag_on("V3_NO_PRIZETRADE")
_LOG_PATH = os.environ.get("V3_LOG")  # 設定時のみ判断ログをJSON行で追記(ローカル計測用)

# クラス限定上書き(iter4層2)とシャドーモード。ability/playへの上書きはv1の
# 実証済みパッチ(能力使用規則・展開規則)保護のため既定で拒否する。
_SHADOW = _flag_on("V3_SHADOW")
_ALLOWED_CLASSES = frozenset(
    (os.environ.get("V3_CLASSES") or "retreat,attack,energy").replace(" ", "").split(","))
_FLAG_NO_LETHAL = _flag_on("V3_NO_LETHAL")
# 直近の上書き提案の由来層: "search"(層2=評価関数比較) / "lethal" / "blunder"(層1=終局検知)
_OVR_CLS = ["search"]

# 相手デッキ推定の辞書: 実ラダー/メタ観測の最頻出60枚(docs/memo/data.md)。
# 前半5つ=v2.1b当時の辞書(V3_NO_OPPMODEL はこの5つのargmaxに退行)。
_META_DECKS = {
    "alakazam": [5, 5, 13, 19, 19, 19, 19, 66, 66, 140, 305, 305, 305, 343, 741, 741, 741, 741, 742, 742, 742, 742, 743, 743, 743, 743, 1079, 1079, 1079, 1081, 1081, 1081, 1081, 1086, 1086, 1086, 1086, 1097, 1129, 1152, 1152, 1152, 1152, 1182, 1182, 1182, 1184, 1197, 1197, 1197, 1225, 1225, 1225, 1225, 1231, 1231, 1231, 1231, 1266, 1266],
    "grimmsnarl_munkidori": [7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 104, 104, 112, 112, 112, 112, 646, 646, 646, 646, 647, 647, 647, 648, 648, 648, 860, 860, 1079, 1079, 1079, 1080, 1086, 1086, 1086, 1086, 1097, 1097, 1097, 1152, 1152, 1152, 1152, 1161, 1161, 1182, 1182, 1219, 1219, 1219, 1219, 1227, 1227, 1227, 1227, 1231, 1259, 1259, 1259, 1259],
    "kangaskhan_crustle": [1, 11, 11, 11, 11, 14, 14, 14, 14, 18, 18, 18, 18, 343, 344, 344, 344, 344, 345, 345, 345, 345, 756, 756, 756, 756, 1086, 1086, 1086, 1086, 1087, 1122, 1122, 1122, 1122, 1123, 1123, 1123, 1123, 1147, 1147, 1147, 1147, 1159, 1182, 1182, 1197, 1197, 1197, 1197, 1225, 1225, 1225, 1225, 1227, 1227, 1227, 1227, 1264, 1264],
    "starmie_dusknoir": [3, 3, 3, 3, 3, 3, 3, 3, 3, 17, 17, 17, 17, 131, 131, 132, 132, 133, 133, 1030, 1030, 1030, 1030, 1031, 1031, 1031, 1086, 1086, 1086, 1086, 1121, 1121, 1121, 1121, 1122, 1122, 1122, 1152, 1152, 1152, 1152, 1167, 1192, 1192, 1192, 1213, 1213, 1213, 1225, 1225, 1225, 1225, 1227, 1227, 1227, 1227, 1229, 1229, 1229, 1229],
    "tr_mewtwo": [1, 1, 1, 1, 1, 1, 1, 1, 1, 15, 15, 15, 15, 400, 400, 400, 400, 401, 401, 401, 401, 414, 414, 431, 431, 434, 434, 434, 1094, 1094, 1094, 1121, 1134, 1134, 1134, 1134, 1152, 1152, 1152, 1152, 1159, 1175, 1216, 1216, 1216, 1216, 1217, 1218, 1218, 1218, 1220, 1220, 1220, 1220, 1227, 1227, 1227, 1257, 1257, 1257],
    # v3追加: 実遭遇分布の主要不利対面(Lucario帯遭遇率25%, D16)と残りのメタ型
    "mega_lucario": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 673, 673, 674, 674, 675, 675, 676, 676, 676, 677, 677, 677, 678, 678, 678, 678, 1102, 1102, 1102, 1102, 1123, 1123, 1141, 1141, 1141, 1141, 1142, 1142, 1142, 1142, 1152, 1152, 1152, 1152, 1159, 1182, 1182, 1192, 1192, 1192, 1192, 1227, 1227, 1227, 1227, 1252, 1252],
    "garchomp": [6, 6, 6, 6, 6, 20, 20, 20, 20, 341, 341, 341, 341, 342, 342, 342, 379, 379, 379, 379, 380, 380, 380, 380, 381, 381, 381, 387, 1080, 1086, 1086, 1086, 1086, 1122, 1122, 1123, 1141, 1141, 1142, 1142, 1142, 1152, 1152, 1152, 1152, 1173, 1173, 1173, 1173, 1182, 1182, 1182, 1182, 1206, 1206, 1219, 1227, 1227, 1227, 1227],
    "archaludon": [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 57, 169, 169, 169, 169, 190, 190, 190, 190, 666, 666, 666, 666, 1097, 1097, 1097, 1121, 1121, 1121, 1121, 1122, 1122, 1122, 1122, 1147, 1147, 1147, 1147, 1152, 1152, 1152, 1152, 1159, 1182, 1182, 1182, 1185, 1185, 1185, 1185, 1213, 1227, 1227, 1227, 1227, 1244, 1244, 1244, 1244],
    "crustle_wall": [1, 1, 1, 1, 1, 1, 1, 1, 7, 7, 7, 7, 112, 112, 344, 344, 344, 344, 345, 345, 345, 345, 1086, 1086, 1086, 1086, 1088, 1094, 1094, 1094, 1094, 1097, 1097, 1097, 1102, 1102, 1102, 1121, 1121, 1121, 1121, 1123, 1123, 1182, 1182, 1182, 1182, 1199, 1199, 1213, 1213, 1224, 1224, 1224, 1224, 1236, 1236, 1261, 1261, 1261],
}
_META_V2_KEYS = ("alakazam", "grimmsnarl_munkidori", "kangaskhan_crustle",
                 "starmie_dusknoir", "tr_mewtwo")
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


# ---------------------------------------------------------------------------
# 相手モデリング (V3_NO_OPPMODEL で v2.1b 相当に退行)
# ---------------------------------------------------------------------------

_OPP_MEM = {"last_turn": -1, "seen": {}}


def _remember_opponent(cur: dict, me: int) -> dict:
    """相手の可視カードをゲーム内で累積記憶する(一度見えて山札に戻った札も推定に使える)。
    各カードの「同時に見えた最大枚数」が採用枚数の下界。ターン番号の巻き戻りで
    新しいゲームと判定してリセットする。"""
    try:
        turn = cur.get("turn") or 0
        if turn < _OPP_MEM["last_turn"]:
            _OPP_MEM["seen"] = {}
        _OPP_MEM["last_turn"] = turn
        seen = _OPP_MEM["seen"]
        for c, n in _counter(_visible_ids(cur["players"][1 - me])).items():
            if n > seen.get(c, 0):
                seen[c] = n
    except Exception:
        pass
    return dict(_OPP_MEM["seen"])


def _infer_enemy_deck(visible: list[int]) -> list[int]:
    """v2.1b互換: 現在見えているカードのみから argmax でメタ5型に当てる。"""
    vis = _counter(visible)
    best, best_score = None, -1.0
    for name in _META_V2_KEYS:
        cand = _META_DECKS[name]
        cc = _counter(cand)
        covered = sum(min(n, cc.get(c, 0)) for c, n in vis.items())
        score = covered / max(1, len(visible))
        if score > best_score:
            best, best_score = cand, score
    if best is None or best_score < 0.5:
        pool = []
        for c, n in vis.items():
            pool += [c] * min(4, max(n, 2))
        pool += [_FILLER_ID] * (60 - len(pool))
        return pool[:60]
    return list(best)


def _archetype_posterior(seen: dict):
    """累積可視カウンタに対する各メタデッキの適合スコア。
    covered=辞書で説明できた枚数, uncovered=説明できない枚数(強い反証として減点)。"""
    total = sum(seen.values())
    out = []
    for name, cand in _META_DECKS.items():
        cc = _counter(cand)
        covered = sum(min(n, cc.get(c, 0)) for c, n in seen.items())
        s = (covered - 0.8 * (total - covered)) / max(1, total)
        out.append((name, cand, s))
    return out, total


def _generic_deck_from_seen(seen: dict) -> list[int]:
    pool = []
    for c, n in seen.items():
        pool += [c] * min(4, max(n, 2))
    pool += [_FILLER_ID] * max(0, 60 - len(pool))
    return pool[:60]


def _sample_enemy_deck(seen: dict) -> list[int]:
    """決定化1本ぶんの相手60枚。argmaxではなく適合スコアに比例してサンプルし、
    決定化間でアーキタイプ推定の不確実性を表現する。"""
    cands, total = _archetype_posterior(seen)
    if total == 0:
        return list(cands[_rnd.randrange(len(cands))][1])
    strong = [(cand, s) for _name, cand, s in cands if s >= 0.35]
    if not strong:
        return _generic_deck_from_seen(seen)
    weights = [max(0.01, s - 0.30) for _cand, s in strong]
    r = _rnd.random() * sum(weights)
    for (cand, _s), w in zip(strong, weights):
        r -= w
        if r <= 0:
            return list(cand)
    return list(strong[-1][0])


def _foe_deck_for_det(cur: dict, me: int, seen: dict) -> list[int]:
    if _FLAG_NO_OPPMODEL:
        return _infer_enemy_deck(_visible_ids(cur["players"][1 - me]))
    return _sample_enemy_deck(seen)


def _determinize(cur: dict, me: int, my_deck60: list[int], foe_deck60: list[int]):
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
    foe_unseen = _counter(foe_deck60)
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


# ---------------------------------------------------------------------------
# 評価関数 (V3_NO_PRIZETRADE で v2.1b 相当に退行)
# ---------------------------------------------------------------------------


def _prize_value(card_id: int) -> int:
    """KOされたとき相手に取られるサイド枚数(非ex=1, ex=2, メガex=3)。"""
    cards, _ = _card_db()
    c = cards.get(card_id)
    if c is None:
        return 1
    if getattr(c, "megaEx", False):
        return 3
    if getattr(c, "ex", False):
        return 2
    return 1


def _evaluate_v2(node_cur: dict, me: int) -> float:
    """v2.1bの静的評価（常に自分視点。yourIndexは手番なので使わない）。"""
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


def _evaluate_v3(node_cur: dict, me: int) -> float:
    """v2評価+サイドトレード: 両陣のダメージを「KOで動くサイド枚数」で重み付けし
    (ex=1.5倍, メガex=2倍)、残りサイド1-2枚の詰めを非線形に加点する。
    非exで相手のexを殴る交換(サイド非対称, D6(e))が正しく高評価になる。"""
    res = node_cur.get("result", -1)
    if res >= 0:
        if res == me:
            return 1e9
        if res == 1 - me:
            return -1e9
        return 0.0
    you, foe = node_cur["players"][me], node_cur["players"][1 - me]
    score = 0.0
    you_p = len(you.get("prize") or [])
    foe_p = len(foe.get("prize") or [])
    score += 10000.0 * (foe_p - you_p)
    # 詰めの非線形加点: 残り2枚→+2000, 残り1枚→+8000(リーサル圏の圧を評価)
    score += 2000.0 * max(0, 3 - you_p) ** 2 - 2000.0 * max(0, 3 - foe_p) ** 2

    def board(pl):
        dmg = energy = pokes = 0.0
        for zone in ("active", "bench"):
            for c in pl.get(zone) or []:
                if not c:
                    continue
                pv = _prize_value(c.get("id"))
                w = 1.0 + 0.5 * (pv - 1)  # サイド直結度によるダメージ重み
                pokes += 1
                dmg += w * ((c.get("maxHp") or 0) - (c.get("hp") or 0))
                energy += len(c.get("energyCards") or [])
        return dmg, energy, pokes

    fd, fe, fp_n = board(foe)
    md, me_energy, mp_n = board(you)
    score += 3.0 * fd - 2.5 * md          # サイド重み付きの与ダメ/被ダメ
    score += 30.0 * me_energy - 20.0 * fe  # エネ供給
    score += 40.0 * mp_n - 30.0 * fp_n     # 展開数
    score += 10.0 * len(you.get("hand") or []) - 6.0 * (foe.get("handCount") or 0)
    my_dc = you.get("deckCount") or 0
    foe_dc = foe.get("deckCount") or 0
    score += 8.0 * min(my_dc, 15) - 8.0 * min(foe_dc, 15)
    score += 30.0 * min(my_dc, 6) - 30.0 * min(foe_dc, 6)
    return score


_evaluate = _evaluate_v2 if _FLAG_NO_PRIZETRADE else _evaluate_v3


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


def _engine_json(r) -> dict | None:
    """エンジン戻り値(c_char_p)を安全にJSONへ。NULLはNone。
    string_at(None)はtry/exceptで捕えられないセグフォルトになるため必ずここを通す。"""
    if r is None:
        return None
    try:
        if isinstance(r, (bytes, bytearray)):
            return json.loads(bytes(r).decode())
        return json.loads(_ct.string_at(r).decode())
    except Exception:
        return None


_CLS_BY_OPTTYPE = {
    OptionType.RETREAT: "retreat",
    OptionType.ATTACK: "attack",
    OptionType.ENERGY: "energy",
    OptionType.ATTACH: "energy",
    OptionType.ABILITY: "ability",
    OptionType.PLAY: "play",
    OptionType.EVOLVE: "evolve",
    OptionType.END: "end",
}


# D23: クラス上書きの価値は対面で符号反転する(energyはGrimm対面で実害-11pt対照確定)。
# 相手アーキタイプの推定が立つ間、該当クラスを対面条件付きで無効化する。
# V3_NO_MATCHUPVETO=1 でアブレーション可。
_CLASS_MATCHUP_VETO = {"energy": ("grimmsnarl_munkidori",)}
_FLAG_NO_MATCHUPVETO = _flag_on("V3_NO_MATCHUPVETO")


def _likely_archetype() -> str | None:
    """累積可視カウンタから最尤メタ型名。情報不足・低適合ならNone(veto不発動)。"""
    try:
        seen = dict(_OPP_MEM["seen"])
        cands, total = _archetype_posterior(seen)
        if total < 4:
            return None
        name, _cand, s = max(cands, key=lambda t: t[2])
        return name if s >= 0.35 else None
    except Exception:
        return None


def _decision_class(sel, picked) -> str:
    """判断クラス: 選んだ先頭オプションの型で分類(害分析とクラスゲートの単位)。"""
    try:
        if not picked:
            return "other"
        return _CLS_BY_OPTTYPE.get(sel.option[picked[0]].type, "other")
    except Exception:
        return "other"


def _preserve_deck_active(obs_dict) -> bool:
    """v1の山札温存モード(D15実証パッチ)中か。層2の上書きはこの間全面拒否する。"""
    try:
        cur = obs_dict.get("current") or {}
        me = cur.get("yourIndex")
        if me not in (0, 1):
            return False
        return (cur["players"][me].get("deckCount") or 0) <= 5
    except Exception:
        return False


def _v3_log(rec: dict) -> None:
    if not _LOG_PATH:
        return
    try:
        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 決定化MCTS (V3_NO_MCTS で v2.1b の平坦全展開に退行)
# 木は「我々の k=1 MAIN/ATTACK 分岐点」でのみ枝分かれし、それ以外の選択
# (相手番・カード選択など)は v1 が自動で指す。葉はホライズン(相手の返し番の
# 終わり)または終局で、静的評価を返す。
# ---------------------------------------------------------------------------


class _Node:
    __slots__ = ("sid", "obs", "untried", "children", "N", "W", "Q", "leaf_val",
                 "depth", "rollout")

    def __init__(self, sid, obs, acts, leaf_val=None, depth=0, rollout=False):
        self.sid = sid          # エンジン内の探索状態ID
        self.obs = obs          # このノードの生observation
        self.untried = list(acts)
        self.children = {}      # option index -> _Node
        self.N = 0
        self.W = 0.0            # 生スコア合計(v1マージン判定用)
        self.Q = 0.0            # tanh正規化スコア合計(UCB用)
        self.leaf_val = leaf_val
        self.depth = depth
        self.rollout = rollout  # True: 訪問ごとに毎回新しいv1ロールアウトで評価(値キャッシュなし)


def _step(ptr, sid, picks, budget):
    if budget["steps"] <= 0:
        return None
    budget["steps"] -= 1
    r = _lib.SearchStep(ptr, _ct.c_int64(sid), _arr(picks, max(1, len(picks))), len(picks))
    node = _engine_json(r)
    if node is None or node.get("error"):
        return None
    return node["state"]["searchId"], node["state"]["observation"]


def _branch_acts_from(o: Observation) -> list[int] | None:
    """分岐点の候補手(代表インデックス, v1の手を先頭に)を作る。"""
    try:
        cands, rep = _dedupe_candidates(o.select.option)
        cands = cands[:_MAX_CANDIDATES]
        if len(cands) <= 1:
            return None
        v1 = _v1_decide(o)
        v1_rep = rep.get(_opt_key(o.select.option[v1[0]])) if v1 else None
        if v1_rep is not None:
            if v1_rep in cands:
                cands.remove(v1_rep)
            cands.insert(0, v1_rep)
        return cands
    except Exception:
        return None


def _advance(ptr, sid, nobs, me, root_turn, deadline, budget):
    """次の分岐点まで v1 で自動前進する。返り値 (sid, nobs, acts)。
    acts が None なら葉(ホライズン/終局/失敗)。"""
    for _ in range(_ROLLOUT_MAX_STEPS):
        cur = nobs.get("current") or {}
        if cur.get("result", -1) >= 0:
            return sid, nobs, None
        if (cur.get("turn") or 0) >= root_turn + _HORIZON_TURNS:
            return sid, nobs, None
        if _time.monotonic() > deadline or budget["steps"] <= 0:
            return sid, nobs, None
        try:
            o = to_observation_class(nobs)
        except Exception:
            return sid, nobs, None
        if o.select is None:
            return sid, nobs, None
        if (cur.get("yourIndex") == me
                and o.select.type in (SelectType.MAIN, SelectType.ATTACK)
                and o.select.minCount <= 1 <= o.select.maxCount
                and len(o.select.option) > 1):
            acts = _branch_acts_from(o)
            if acts is not None:
                return sid, nobs, acts
        try:
            pick = _v1_decide(o)
        except Exception:
            return sid, nobs, None
        stepped = _step(ptr, sid, pick, budget)
        if stepped is None:
            return sid, nobs, None
        sid, nobs = stepped
    return sid, nobs, None


def _rollout_value(ptr, sid, nobs, me, root_turn, deadline, budget) -> float:
    """ノード位置から v1 同士でホライズンまで指し切り、静的評価を返す。"""
    for _ in range(_ROLLOUT_MAX_STEPS):
        cur = nobs.get("current") or {}
        if cur.get("result", -1) >= 0:
            break
        if (cur.get("turn") or 0) >= root_turn + _HORIZON_TURNS:
            break
        if _time.monotonic() > deadline or budget["steps"] <= 0:
            break
        pick = _rollout_policy(nobs)
        if pick is None:
            break
        stepped = _step(ptr, sid, pick, budget)
        if stepped is None:
            break
        sid, nobs = stepped
    return _evaluate(nobs.get("current") or {}, me)


def _simulate(ptr, root: "_Node", me, root_turn, deadline, budget) -> None:
    """MCTS 1シミュレーション: 選択→展開→ロールアウト→逆伝播。"""
    path = [root]
    node = root
    val = None
    while True:
        if node.leaf_val is not None:
            val = node.leaf_val
            break
        if node.rollout:
            # 深さ上限ノード: 訪問のたびに新しいv1ロールアウト(乱数も再サンプル)。
            # 値をキャッシュしないことで「1サンプルのまぐれ」が固定化しない。
            val = _rollout_value(ptr, node.sid, node.obs, me, root_turn, deadline, budget)
            break
        if node.untried:
            a = node.untried.pop(0)
            stepped = _step(ptr, node.sid, [a], budget)
            if stepped is None:
                child = _Node(node.sid, None, [], leaf_val=-1e6)  # エンジンが拒否した手
                val = child.leaf_val
            else:
                sid, nobs = stepped
                sid, nobs, acts = _advance(ptr, sid, nobs, me, root_turn, deadline, budget)
                if acts is None or node.depth + 1 >= _MAX_TREE_DEPTH:
                    child = _Node(sid, nobs, [], depth=node.depth + 1, rollout=True)
                    val = _rollout_value(ptr, sid, nobs, me, root_turn, deadline, budget)
                else:
                    child = _Node(sid, nobs, acts, depth=node.depth + 1)
                    val = _rollout_value(ptr, sid, nobs, me, root_turn, deadline, budget)
            node.children[a] = child
            path.append(child)
            break
        if not node.children:
            val = _evaluate((node.obs or {}).get("current") or {}, me)
            break
        logn = _math.log(max(2, node.N))
        best, best_u = None, -1e18
        for ch in node.children.values():
            if ch.N == 0:
                u = 1e9
            else:
                u = ch.Q / ch.N + _MCTS_UCB_C * _math.sqrt(logn / ch.N)
            if u > best_u:
                best, best_u = ch, u
        node = best
        path.append(node)
    q = _math.tanh(val / _MCTS_EVAL_SCALE)
    for n in path:
        n.N += 1
        n.W += val
        n.Q += q


def _root_candidates(sel, v1_answer):
    """ルートの候補手(代表・v1先頭)と v1 の代表インデックス。不成立なら (None, None)。"""
    candidates, rep = _dedupe_candidates(sel.option)
    candidates = candidates[:_MAX_CANDIDATES]
    if len(candidates) <= 1:
        return None, None
    v1_rep = None
    if v1_answer:
        try:
            v1_rep = rep.get(_opt_key(sel.option[v1_answer[0]]))
        except Exception:
            v1_rep = None
    if v1_rep is None:
        return None, None
    if v1_rep in candidates:
        candidates.remove(v1_rep)
    candidates.insert(0, v1_rep)  # 予算切れでもv1基準は必ず評価される
    return candidates, v1_rep


def _search_common_guard(obs_dict, sel):
    """探索が使えない状況の共通ガード。使えるなら (cur, me, seen) を返す。"""
    if os.environ.get("V2_NO_SEARCH"):
        return None
    if _lib is None:
        return None
    sbi = obs_dict.get("search_begin_input")
    cur = obs_dict.get("current")
    if not sbi or not cur:
        return None
    me = cur.get("yourIndex")
    if me not in (0, 1):
        return None
    seen = _remember_opponent(cur, me)  # 記憶はガードで弾かれる手番でも更新する
    if _foe_active_missing(cur, me):
        return None  # セットアップ中は対象外(enemyActive注入が必要)
    if len(sel.option) <= 1 or not (sel.minCount <= 1 <= sel.maxCount):
        return None  # k=1の選択のみ探索
    return cur, me, seen


def _search_decide_mcts(obs_dict: dict, sel, v1_answer: list[int]) -> list[int] | None:
    """決定化MCTSによる1手選択。自信がない/失敗時は None(=v1採用)。"""
    g = _search_common_guard(obs_dict, sel)
    if g is None:
        return None
    cur, me, seen = g
    candidates, v1_rep = _root_candidates(sel, v1_answer)
    if candidates is None:
        return None

    t0 = _time.monotonic()
    deadline = t0 + _SEARCH_BUDGET_SEC
    ptr = _get_agent_ptr()
    if not ptr:
        return None
    sbi_b = obs_dict["search_begin_input"].encode("utf-8")
    my_deck60 = _my_deck60()
    root_turn = cur.get("turn") or 0
    totals = {c: 0.0 for c in candidates}
    counts = {c: 0 for c in candidates}
    det_hits = {c: 0 for c in candidates}
    dets_done = 0
    try:
        for _d in range(_DETERMINIZATIONS):
            if _time.monotonic() > deadline:
                break
            foe60 = _foe_deck_for_det(cur, me, seen)
            md, mp, fd, fp, fh = _determinize(cur, me, my_deck60, foe60)
            r = _lib.SearchBegin(ptr, sbi_b, len(sbi_b), _arr(md), _arr(mp),
                                 _arr(fd), _arr(fp), _arr(fh), _arr([]), 0)
            res = _engine_json(r)
            if res is None or res.get("error"):
                return None
            root = _Node(res["state"]["searchId"], obs_dict, candidates)
            budget = {"steps": _MAX_ENGINE_STEPS // max(1, _DETERMINIZATIONS)}
            sims = 0
            while (sims < _MCTS_SIMS and budget["steps"] > 0
                   and _time.monotonic() < deadline):
                _simulate(ptr, root, me, root_turn, deadline, budget)
                sims += 1
            for a, ch in root.children.items():
                if ch.N > 0:
                    totals[a] += ch.W
                    counts[a] += ch.N
                    det_hits[a] += 1
            dets_done += 1
    except Exception:
        return None
    finally:
        try:
            _lib.SearchEnd(ptr)
        except Exception:
            pass
    if dets_done == 0:
        return None
    # 完走した全決定化で訪問された候補だけ比較対象にする(打ち切りバイアス対策)。
    # さらにv1以外は十分な訪問数を要求する: 訪問1-2回の候補の「まぐれ高評価」が
    # 平均比較でv1を上書きする最大化バイアス対策(v3.0で上書き率53.6%と過剰だった)。
    min_n = _MCTS_MIN_VISITS * dets_done
    evaluated = [c for c in candidates
                 if det_hits[c] == dets_done
                 and (c == v1_rep or counts[c] >= min_n)]
    if v1_rep not in evaluated:
        return None
    best = max(evaluated, key=lambda c: totals[c] / counts[c])
    best_avg = totals[best] / counts[best]
    v1_avg = totals[v1_rep] / counts[v1_rep]
    override = best != v1_rep and best_avg >= v1_avg + _OVERRIDE_MARGIN
    _v3_log({"turn": root_turn, "cands": len(candidates), "dets": dets_done,
             "visits": sum(counts.values()), "override": override,
             "best": round(best_avg, 1), "v1": round(v1_avg, 1),
             "ms": round(1000 * (_time.monotonic() - t0), 1)})
    if not override:
        return None
    return [best]


def _search_decide_flat(obs_dict: dict, sel, v1_answer: list[int]) -> list[int] | None:
    """v2.1b互換の平坦探索: 全候補を1回ずつ展開し、v1誘導ロールアウトで評価。"""
    g = _search_common_guard(obs_dict, sel)
    if g is None:
        return None
    cur, me, seen = g
    candidates, v1_rep = _root_candidates(sel, v1_answer)
    if candidates is None:
        return None

    deadline = _time.monotonic() + _SEARCH_BUDGET_SEC
    ptr = _get_agent_ptr()
    if not ptr:
        return None
    sbi_b = obs_dict["search_begin_input"].encode("utf-8")
    my_deck60 = _my_deck60()
    root_turn = cur.get("turn") or 0
    totals = {c: 0.0 for c in candidates}
    counts = {c: 0 for c in candidates}
    twin = {c: 0 for c in candidates}   # ロールアウトが終局「勝ち」に到達した回数
    tloss = {c: 0 for c in candidates}  # 同「負け」到達回数(層1=評価関数フリーの材料)
    try:
        for _ in range(_DETERMINIZATIONS):
            if _time.monotonic() > deadline:
                break
            foe60 = _foe_deck_for_det(cur, me, seen)
            md, mp, fd, fp, fh = _determinize(cur, me, my_deck60, foe60)
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
                sid = node["state"]["searchId"]
                nobs = node["state"]["observation"]
                for _step_i in range(_ROLLOUT_MAX_STEPS):
                    ncur = nobs.get("current") or {}
                    if ncur.get("result", -1) >= 0:
                        break
                    if (ncur.get("turn") or 0) >= root_turn + _HORIZON_TURNS:
                        break
                    if _time.monotonic() > deadline:
                        break
                    pick = _rollout_policy(nobs)
                    if pick is None:
                        break
                    r = _lib.SearchStep(ptr, _ct.c_int64(sid),
                                        _arr(pick, max(1, len(pick))), len(pick))
                    nxt = _engine_json(r)
                    if nxt is None or nxt.get("error"):
                        break
                    sid = nxt["state"]["searchId"]
                    nobs = nxt["state"]["observation"]
                fin = (nobs.get("current") or {}).get("result", -1)
                if fin >= 0:
                    if fin == me:
                        twin[c] += 1
                    elif fin == 1 - me:
                        tloss[c] += 1
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
    if not evaluated or v1_rep not in evaluated:
        return None

    # 層1: リーサル/ブランダー(終局検知のみ・評価関数フリー。D19: 最も信用できる層)
    if not _FLAG_NO_LETHAL:
        sure_wins = [c for c in evaluated if twin[c] == counts[c]]
        if sure_wins:
            if v1_rep in sure_wins:
                return None  # v1自身が必勝手ならそのまま
            _OVR_CLS[0] = "lethal"
            return [sure_wins[0]]
        if tloss[v1_rep] == counts[v1_rep]:
            # v1の手が全決定化で終局負けに到達。負けない代替があれば退避
            alts = [c for c in evaluated if c != v1_rep and tloss[c] < counts[c]]
            if alts:
                _OVR_CLS[0] = "blunder"
                return [min(alts, key=lambda c: tloss[c] / counts[c])]

    # 層2: 評価関数比較(マージン上書き。クラスゲートはagent()側で適用)
    best = max(evaluated, key=lambda c: totals[c] / counts[c])
    if best == v1_rep:
        return None
    if totals[best] / counts[best] < totals[v1_rep] / counts[v1_rep] + _OVERRIDE_MARGIN:
        return None
    return [best]


def _search_decide(obs_dict: dict, sel, v1_answer: list[int]) -> list[int] | None:
    _OVR_CLS[0] = "search"
    if _FLAG_NO_MCTS:
        return _search_decide_flat(obs_dict, sel, v1_answer)
    return _search_decide_mcts(obs_dict, sel, v1_answer)


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
                    # iter4 層2ゲート: 上書きは許可クラスのみ。層1(lethal/blunder)は
                    # 評価関数フリーのためゲートと温存vetoを免除。シャドーは全層不適用。
                    layer = _OVR_CLS[0]
                    cls_v1 = _decision_class(sel, v1)
                    cls_new = _decision_class(sel, picked)
                    preserve = _preserve_deck_active(obs_dict)
                    if layer in ("lethal", "blunder"):
                        allowed = True
                    elif preserve:
                        allowed = False  # 山札温存パッチ(D15)の拒否権
                    elif "all" in _ALLOWED_CLASSES:
                        allowed = True
                    else:
                        allowed = (cls_new in _ALLOWED_CLASSES
                                   and cls_v1 in _ALLOWED_CLASSES)
                    arch = None
                    if allowed and layer == "search" and not _FLAG_NO_MATCHUPVETO:
                        arch = _likely_archetype()
                        if arch and any(
                            arch in _CLASS_MATCHUP_VETO.get(c, ())
                            for c in (cls_new, cls_v1)
                        ):
                            allowed = False
                    _v3_log({"ev": "gate", "layer": layer, "cls_v1": cls_v1,
                             "cls_new": cls_new, "preserve": preserve,
                             "arch": arch, "allowed": allowed, "shadow": _SHADOW})
                    if allowed and not _SHADOW:
                        return picked
        except Exception:
            pass
        return v1
    except Exception:
        # Observationパース・v1本体まで含めて何が起きても合法手を返す
        return _last_resort(obs_dict)

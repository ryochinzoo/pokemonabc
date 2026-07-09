import os
import sys
import copy
from collections import defaultdict

from cg.api import AreaType, CardType, EnergyType, Observation, SelectContext, OptionType, Card, Pokemon, all_card_data, to_observation_class
from typing import Dict, Protocol, List, Optional, Any, Tuple

"""
Mega Starmie EX Deck
このデッキでは2つの優先度スコア指標を軸に戦略を立てる
1つ目はカードそのもののスコア
2つ目は行動のスコア
カードそのもののスコアは、自分のカードのスコア、ターゲットの優先度など扱うカードや
仮想敵となるカードの優先順位
行動スコアは、攻撃する、特性を使う、技１，２を選ぶ、一旦撤退するなどのターンごとのサイクル
相手の現在の状況からの判断をスコアにしたものである
そのため、各カードそのものの定義と
行動に対する定義を定めたコードになっている
"""

# デッキ構築に使用するカード

HITODEMAN = 1030 # ×3
MEGA_STARMIE_EX = 1031 # ×2
YUKIWARASHI = 860 # ×3
MEGA_YUKIMENOKO_EX = 861 # ×2
YUKIMENOKO = 103 # ×2
MUNKIDORI = 112 # ×3
YVELTAL = 689 # ×1
SUBOMIE = 235 # ×1
MAUZI = 1071 # ×1
POFIN = 1086 # ×4
POKE_PAD = 1052 # ×4
HYPERBALL = 1121 # ×3
TANKER = 1097 # ×2
BALLON = 1174 # ×1
LILLIE_DETERMINATION = 1227 # ×4
CARMINE = 1192 # ×4
TOUKO = 1225 # ×3
AKAMATSU = 1198 # ×2
BEFEHL_VON_BOSS = 1182 # ×3
DENGEROUS_RUINE = 1260 # ×4
BASIC_WATER_ENERGIE = 3 # ×4
BASIC_UNLICHT_ENERGIE = 7 # ×3
LEGACY_ENERGIE = 12 # ×1

# 仮想敵の系譜
ALAKAZAM_LINE = {741, 742, 743} # ケーシィ系統
CRUSTLE_LINE = {344, 345, 532} # イシズマイ系統
STARMIE_LINE = {1030, 1031} # ヒトデマン系統
LUCARIO_LINE = {677, 678} # リオル系統
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879} # ホップ系統
MARIE_LINE = {642, 643, 644, 645, 646, 647, 648, 649} # マリィ系統
DURALUDON = {169, 170, 190, 839, 840, 992} # ジュラルドン系統 190が特に要注意
DREEPY = {119, 120, 121} # ドラメシヤ系統

ALL_HYPO_ENEMIES = ALAKAZAM_LINE | CRUSTLE_LINE | STARMIE_LINE | LUCARIO_LINE | HOP_LINE | DURALUDON | DREEPY


# 死守すべき重要カードのリスト（トラッシュ・山札戻しは絶対禁止）
IMPORTANT_CARDS = [
    HITODEMAN, MEGA_STARMIE_EX, 
    YUKIWARASHI, MEGA_YUKIMENOKO_EX, YUKIMENOKO,
    MUNKIDORI, BEFEHL_VON_BOSS
]

def _initialize_data() -> Tuple[List[int], Dict[int, Any], Dict[int, Any]]:
    # deck.csv
    deck_path = "deck.csv"

    if not os.path.exists(deck_path):
        deck_path = "/kaggle_simulations/agent/" + deck_path
    with open(deck_path, "r") as file:
        csv = file.read().split("\n")
    mega_starmie_deck = []
    for i in range(60):
        mega_starmie_deck.append(int(csv[i]))

    # get all card data
    all_card = all_card_data()
    CARD_TABLE = { c.cardId: c for c in all_card }

    # get attackIds
    try:
        from cg.api import all_attack
        ALL_ATTACKS = { a.attackId: a for a in all_attack() }
    except Exception:
        ALL_ATTACKS = {}
    return mega_starmie_deck, CARD_TABLE, ALL_ATTACKS


# --- スクリプト読み込み時に「1回だけ」実行される ---
DECK, CARD_TABLE, ALL_ATTACKS = _initialize_data()


# ==========================================
# 1. 盤面解析クラス (BoardState)
# ==========================================
class BoardState:
    def __init__(self, obs: Observation, card_table):
        self.obs = obs
        self.card_table = card_table
        self.me = obs.current.players[obs.current.yourIndex]
        self.opp = obs.current.players[1 - obs.current.yourIndex]

        self._my_area_maps = {
            AreaType.HAND: self.me.hand,
            AreaType.DISCARD: self.me.discard,
            AreaType.ACTIVE: self.me.active,
            AreaType.BENCH: self.me.bench,
            AreaType.PRIZE: self.me.prize,
        }
        self._opp_area_maps = {
            AreaType.HAND: self.opp.hand,
            AreaType.DISCARD: self.opp.discard,
            AreaType.ACTIVE: self.opp.active,
            AreaType.BENCH: self.opp.bench,
            AreaType.PRIZE: self.opp.prize,
        }

    def fetch_card_safely(self, area: AreaType, index: int, is_me: bool = True) -> Pokemon | Card | None:
        """指定されたエリア、インデックスから安全にカード/ポケモンオブジェクトを抽出する"""
        if area == AreaType.DECK:
            deck_list = getattr(self.obs.select, "deck", []) or []
            return deck_list[index] if 0 <= index < len(deck_list) else None
            
        if area == AreaType.STADIUM:
            stadium_list = getattr(self.obs.current, "stadium", []) or []
            return stadium_list[index] if 0 <= index < len(stadium_list) else None
            
        if area == AreaType.LOOKING:
            looking_list = getattr(self.obs.current, "looking", []) or []
            return looking_list[index] if 0 <= index < len(looking_list) else None

        area_map = self._my_area_maps if is_me else self._opp_area_maps
        target_list = area_map.get(area)

        if target_list and 0 <= index < len(target_list):
            return target_list[index]
            
        return None
    
    @property
    def active(self) -> Pokemon | None:
        """自分のバトル場のポケモン"""
        return self.me.active[0] if self.me.active else None
    
    @property
    def opp_active(self) -> Pokemon | None:
        """相手のバトル場のポケモン"""
        return self.opp.active[0] if self.opp.active else None

    @property
    def bench(self) -> List[Pokemon]:
        """自分のベンチポケモン（空枠排除）"""
        return [p for p in self.me.bench if p]

    @property
    def opp_bench(self) -> List[Pokemon]:
        """相手のベンチポケモン（空枠排除）"""
        return [p for p in self.opp.bench if p]

    @property
    def all_my_pokemon(self) -> List[Pokemon]:
        """自分の場にいるすべてのポケモン"""
        return [p for p in (self.me.active + self.me.bench) if p]

    @property
    def all_opp_pokemon(self) -> List[Pokemon]:
        """相手の場にいるすべてのポケモン"""
        return [p for p in (self.opp.active + self.opp.bench) if p]

    @property
    def my_card_ids_in_play(self) -> List[int]:
        """自分の場にいるポケモンのカードID一覧"""
        return [p.id for p in self.all_my_pokemon]

    @property
    def hand_ids(self) -> List[int]:
        """手札のカードID一覧"""
        return [c.id for c in self.me.hand if c] if self.me.hand else []
    
    @property
    def opp_hand_count(self) -> int:
        """相手の手札の枚数"""
        if self.opp.hand is None: 
            return 0
        return sum(1 for c in self.opp.hand if c)

    @property
    def discard_ids(self) -> List[int]:
        """トラッシュのカードID一覧"""
        return [c.id for c in (self.me.discard or []) if c]

    @property
    def water_in_discard(self) -> int:
        """トラッシュの水エネルギーの枚数"""
        return sum(1 for cid in self.discard_ids if cid == EnergyType.WATER)

    @property
    def unlicht_in_discard(self) -> int:
        """トラッシュの悪エネルギーの枚数"""
        return sum(1 for cid in self.discard_ids if cid == EnergyType.DARKNESS)

    # ==========================================
    # 1. 攻めのセンサー
    # ==========================================
    @property
    def opp_active_hp(self) -> int:
        """相手のバトルポケモンの残りHP"""
        if not self.opp_active: 
            return 0
        return self.opp_active.hp

    @property
    def opp_active_prize_value(self) -> int:
        """相手のバトルポケモンを倒したときにもらえるサイド枚数（メガ・ex対応版）"""
        if not self.opp_active: 
            return 0
            
        opp_id_str = str(self.opp_active.id).lower()
        
        # 1. 最優先：IDに「mega」や「m_」が含まれる、または特定のメガ進化IDなら3枚 uso
        if "mega" in opp_id_str or "m_" in opp_id_str or self.opp_active.id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return 3
        # 2. 次点：ex ポケモンなら2枚
        if "ex" in opp_id_str:
            return 2
        # 3. それ以外（非ex、たね、1進化など）は1枚
        return 1

    @property
    def my_remaining_prizes(self) -> int:
        """自分の残りサイド枚数"""
        return len(self.me.prize)

    # ==========================================
    # 2. 守りのセンサー
    # ==========================================
    @property
    def my_active_remaining_hp(self) -> int:
        """自分のバトルポケモンの残りHP"""
        if not self.active: 
            return 0
        return self.active.hp

    @property
    def my_active_prize_value(self) -> int:
        """自分のバトルポケモンが倒されたときに取られるサイド枚数（メガ・ex・レガシー対応版）"""
        if not self.active: 
            return 0
            
        my_id_str = str(self.active.id).lower()
        
        # 1. ベースとなるサイド枚数を判定 uso
        if "mega" in my_id_str or "m_" in my_id_str or self.active.id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            base_prize = 3
        elif "ex" in my_id_str:
            base_prize = 2
        else:
            base_prize = 1
            
        # 2. レガシーエネルギーが付いている場合は、取られるサイドを1枚減らす（最低1枚）
        if self.is_legacy_energy_attached_to_active:
            return max(1, base_prize - 1)
            
        return base_prize

    @property
    def opp_active_max_damage(self) -> int:
        """相手のバトル場が、次のターンに出せる最大技ダメージ"""
        if not self.opp_active: 
            return 0
        return self._calculate_max_available_damage(self.opp_active)

    @property
    def is_legacy_energy_attached_to_active(self) -> bool: #USO
        """自分のバトルポケモンにレガシーエネルギーが付いているか"""
        if not self.active or not getattr(self.active, "attached_cards", None):
            return False
        return any(getattr(card, "id", None) == LEGACY_ENERGIE for card in self.active.attached_cards)

    # ==========================================
    # 3. コンボのセンサー
    # ==========================================
    @property
    def is_stadium_perilous_ruins(self) -> bool:
        """現在のスタジアムが『危険な廃墟』かどうか"""
        stadium = getattr(self.obs.current, "stadium", None)
        if not stadium or not stadium[0]: 
            return False
        return stadium[0].id == DENGEROUS_RUINE

    @property
    def has_ready_mashimashira(self) -> bool:
        """自分の場に、特性が使える状態のマシマシラがいるか"""
        return self._check_mashimashira_readiness()

    @property
    def has_damage_counters_to_move(self) -> bool:
        """自分の場に、マシマシラで移動させられるダメカンが存在するか"""
        return any(getattr(p, "remainDamageCounter", 0) > 0 for p in self.all_my_pokemon)

    # ==========================================
    # 内部の軽量計算ヘルパー
    # ==========================================
    def my_active_can_attack(self) -> bool:
        """自分のバトルポケモンが現在攻撃可能（技を1つ以上持っている）か"""
        if not self.active: 
            return False
        card_data = self.get_card_data(self.active.id)
        if not card_data or not getattr(card_data, "attacks", None): 
            return False
        return len(card_data.attacks) > 0

    def get_my_active_attack_damage(self) -> int:
        """自分のバトルポケモンの現在出せる最大技ダメージを取得"""
        if not self.active: return 0
        card_data = self.get_card_data(self.active.id)
        if not card_data or not getattr(card_data, "attacks", None): 
            return 0
        return max((getattr(atk, "damage", 0) for atk in card_data.attacks), default=0) #uso

    def _calculate_max_available_damage(self, pokemon) -> int:
        """対象のポケモンが『現在付いているエネルギーで』出せる最大技ダメージ（簡易版）"""
        card_data = self.get_card_data(pokemon.id)
        if not card_data or not getattr(card_data, "attacks", None): 
            return 0
            
        # 相手に付いているエネルギーの合計枚数をカウント
        attached_count = len(getattr(pokemon, "energyCards", []) or [])
        
        max_dmg = 0
        for atk in card_data.attacks:
            # 技の必要エネルギー数（costなどのプロパティ名である場合が多いです）
            # もし相手のエネルギー枚数が、技の必要枚数以上、または次のターン手貼りして届く範囲なら計算対象にする
            # （※API仕様のcostの型に合わせて調整してください）
            required_energy = len(getattr(atk, "cost", [])) #uso
            
            # 次のターンの手貼り(+1枚)を含めて足りるか
            if attached_count + 1 >= required_energy:
                dmg = getattr(atk, "damage", 0) #uso
                if dmg > max_dmg:
                    max_dmg = dmg
                    
        return max_dmg

    def _check_mashimashira_readiness(self) -> bool:
        """場にマシマシラ（ID指定等）がいて、悪エネルギーがついているか判定"""
        for p in self.all_my_pokemon:
            if p.id == MUNKIDORI:
                # 添付カードに悪エネルギー（またはEnergyType.DARKNESS）があるかチェック
                attached = getattr(p, "energyCards", []) or []
                if any(getattr(card, "id", None) == EnergyType.DARKNESS for card in attached):
                    return True
        return False

    def count_in_play(self, card_id: int) -> int:
        """指定したカードIDが自分の場に何枚あるか"""
        return sum(1 for pid in self.my_card_ids_in_play if pid == card_id)

    def get_card_data(self, pokemon_id: int):
        """カードテーブルからマスターデータを安全に取得"""
        return self.card_table.get(pokemon_id, None)
    
    def _calculate_prize_value(self, pokemon) -> int:
        """対象のポケモンを倒したときに取れるサイドの枚数を計算する（メガ対応版）"""
        if not pokemon:
            return 0
            
        pokemon_id_str = str(pokemon.id).lower()
        
        # 1. 【最優先】メガシンカならサイドは3枚 #これ系全部USO
        if "mega" in pokemon_id_str or "m_" in pokemon_id_str:
            return 3
        # 2. EX / ex ポケモンならサイドは2枚
        if "ex" in pokemon_id_str:
            return 2
        # 3. それ以外のノーマルカード（非EX）ならサイドは1枚
        return 1
    
    def can_win_by_killing_bench_pokemon(self) -> bool:
        """【勝ち確判定】相手のベンチをボスの指令で引きずり出して倒すことで、試合に勝てるか"""
        if not self.my_active_can_attack():
            return False
            
        my_damage = self.get_my_active_attack_damage()
        
        for bench_pokemon in self.opp_bench:
            can_ko = my_damage >= bench_pokemon.hp
            prize_value = self._calculate_prize_value(bench_pokemon)
            will_win = prize_value >= self.me.remaining_prizes
            
            if can_ko and will_win:
                return True
        return False
    
# ==========================================
# 2. 戦略インターフェース と 各カード戦略オブジェクト
# ==========================================

# 盤面が十分に回っている（完成している）と判断する関数
def is_board_fully_set_up(board: BoardState) -> bool:
    # 進化の土台やシステムが十分に盤面に並んでいるかチェック
    starmie_ready = board.count_in_play(HITODEMAN) + board.count_in_play(MEGA_STARMIE_EX) >= 2
    yukinoko_ready = board.count_in_play(YUKIWARASHI) + board.count_in_play(MEGA_YUKIMENOKO_EX) + board.count_in_play(YUKIMENOKO) >= 2
    return starmie_ready and yukinoko_ready

def evaluate_trash_cost_priority(card_id: int, board: BoardState) -> float:
    """カードをトラッシュする際の見切りやすさスコア（高いほど真っ先に捨てられる）"""
    
    # 1. 絶対にトラッシュしてはいけない重要カードは最悪のペナルティ
    if card_id in IMPORTANT_CARDS:
        return -99999.0
        
    # 2. 使用優先度の低いカードは、いつでも最高のトラッシュ候補（最優先のエサ）
    if card_id in [YVELTAL, SUBOMIE]:
        return 5000.0
        
    # 3. 盤面が十分に回っている（完成している）場合、余った展開グッズ・サポはエサ
    if is_board_fully_set_up(board):
        if card_id == TOUKO:
            return 4500.0
        if card_id == POKE_PAD:
            return 4000.0
        
    # 4. 手札にハイパーボールがあり、ゼイユをコストに回す優先度が高い場合
    if card_id == CARMINE and HYPERBALL in board.hand_ids: #uso?
        return 4200.0
        
    # 通常のカード（デフォルト）
    return 100.0

class CardStrategy(Protocol):
    """すべてのカード固有ロジックが満たす共通インターフェース規格"""
    def evaluate_play(self, board: BoardState) -> float: ...
    def evaluate_attach(self, board: BoardState, target_pokemon: Pokemon) -> float: ...
    def evaluate_placement(self, board: BoardState) -> float: ...
    def evaluate_trash(self, board: BoardState) -> float: ...

class DefaultStrategy:
    """基本戦略（これといった特殊ロジックがない一般カードのデフォルト値）"""
    def evaluate_play(self, board: BoardState) -> float: return 0.0
    def evaluate_attach(self, board: BoardState, target_pokemon: Pokemon) -> float: return 100.0
    def evaluate_placement(self, board: BoardState) -> float: return 100.0
    def evaluate_trash(self, board: BoardState) -> float: return 0.0


class BossOrdersStrategy(DefaultStrategy):
    """『ボスの指令（BEFEHL_VON_BOSS）』の評価脳みそ"""
    def evaluate_play(self, board: BoardState) -> float:
        score = 0.0
        
        # 1. 【攻めの先読み】ベンチの敵を引きずり出せば、このターンに「サイドを取って勝ち確」になるか？
        if board.can_win_by_killing_bench_pokemon():
            return 99999.0  # ガード構文（即決確定値）

        # 2. 【守りの先読み】今、自分のバトル場が返り討ち確定ラインでピンチか
        is_my_active_in_danger = board.my_active_remaining_hp <= board.opp_active_max_damage
        if is_my_active_in_danger:
            score += board.my_active_prize_value * 1200.0
            
        # 3. 【テンポ奪取の評価】相手ベンチに引きずり出せるロック対象候補がいれば加点
        if len(board.opp_bench) > 0:
            score += 500.0
            
        return score


class PerilousRuinsStrategy(DefaultStrategy):
    """『危険な廃墟（DENGEROUS_RUINE）』の評価脳みそ"""
    def evaluate_play(self, board: BoardState) -> float:
        score = 100.0  # 基本の張り替え価値
        
        # マシマシラが準備できていないなら、自傷リスクを避けるため早期リターン
        if not board.has_ready_mashimashira:
            return score
            
        score += 800.0  # コンボ成立加点
        
        # すでに場に動かせるダメカンがあるなら即効性アップ
        if board.has_damage_counters_to_move:
            score += 300.0
            
        return score


class LegacyEnergyStrategy(DefaultStrategy):
    """『レガシーエネルギー（LEGACY_ENERGIE）』の評価脳みそ"""
    def evaluate_play(self, board: BoardState) -> float:
        score = 200.0  # 基本エネ価値
        
        # 次のターンに気絶するリスクを検知
        is_will_be_ko = board.my_active_remaining_hp <= board.opp_active_max_damage
        if not is_will_be_ko:
            return score
            
        return score + 1500.0  # 気絶時のサイドレース破壊価値

    def evaluate_attach(self, board: BoardState, target_pokemon: Pokemon) -> float:
        # メガシンカに貼るのが最優先（3枚ロスを2枚に抑えるため超特大加点）
        if target_pokemon.id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return 5000.0
        # ex ポケモン（2枚ロスを1枚に抑える）
        target_id_str = str(target_pokemon.id).lower()
        if "ex" in target_id_str:
            return 3000.0
        return 100.0


class DarknessEnergyStrategy(DefaultStrategy):
    """『悪エネルギー（BASIC_UNLICHT_ENERGIE）』の貼付脳みそ"""
    def evaluate_attach(self, board: BoardState, target_pokemon: Pokemon) -> float:
        if target_pokemon.id == MUNKIDORI:
            return 4000.0  # アドバンスドレイン特性のトリガー起動用
        if target_pokemon.id == YVELTAL:
            return 10.0    # イベルタルはトラッシュに落としたいので低評価
        return 100.0


class WaterEnergyStrategy(DefaultStrategy):
    """『水エネルギー（BASIC_WATER_ENERGIE）』の貼付脳みそ"""
    def evaluate_attach(self, board: BoardState, target_pokemon: Pokemon) -> float:
        if target_pokemon.id == MEGA_STARMIE_EX:
            return 4000.0
        if target_pokemon.id in {MEGA_YUKIMENOKO_EX, YUKIMENOKO}:
            return 2500.0
        return 100.0


class BenchPokemonStrategy(DefaultStrategy):
    """『ユキメノコ / マシマシラ』のベンチ展開脳みそ"""
    def evaluate_placement(self, board: BoardState) -> float:
        return 100.0 + 2000.0  # 常駐特性が極めて強力なため常時高スコア


class BudewStrategy(DefaultStrategy):
    """『スボミー（SUBOMIE）』のゲームフェーズ依存運用脳みそ"""
    def evaluate_placement(self, board: BoardState) -> float:
        # 序盤（自分の残りサイドが5枚以上）なら「むずむずかふん」を使いたい
        if board.my_remaining_prizes >= 5:
            return 100.0 + 1500.0
        else:
            return 100.0 - 500.0  # 後半はベンチを圧迫するため価値低下

    def evaluate_trash(self, board: BoardState) -> float:
        # 中盤以降はトラッシュに送るコストとして最高スペック
        return 2000.0 if board.my_remaining_prizes < 5 else 0.0


class YveltalStrategy(DefaultStrategy):
    """『イベルタル（YVELTAL）』のトラッシュコスト用脳みそ"""
    def evaluate_trash(self, board: BoardState) -> float:
        return 3000.0  # トラッシュに送る最優先ターゲット
    

class PokePadStrategy(DefaultStrategy):
    """ポケパット：非exの展開用（ヒトデマン、ユキワラシ、イベルタル、スボミー）。十分ならエサ"""
    def evaluate_play(self, board: BoardState) -> float:
        if is_board_fully_set_up(board):
            return 0.0  # 十分回っているならプレイせず、トラッシュ対象（0点）
            
        return 2500.0  # 序盤の展開期は非常に高い価値
class PofinStrategy(DefaultStrategy):
    """なかよしポフィン：山札にHP70以下の非exのたねポケモンがいるなら使う"""
    def evaluate_play(self, board: BoardState) -> float:
        # 1. 盤面がすでに完成しているなら、使う必要がないのでエサ（0点）
        if is_board_fully_set_up(board):
            return 0.0
            
        # 2. 山札に対象となるポケモン（HP70以下のたね）が残っているかチェック
        has_target = False
        for card_id in board.deck_ids: #USO
            # 💡 ここで各カードのデータ（HPや進化段階）を参照する
            card_info = board.get_card_info(card_id)
            if card_info.stage == "Basic" and card_info.hp <= 70 and not card_info.is_ex:
                has_target = True
                break
                
        # 山札に対象が1枚もないなら、使っても意味がないので使用禁止
        if not has_target:
            return -99999.0
            
        return 2600.0  # 対象がいて、盤面が未完成なら高評価
    
class TankerStrategy(DefaultStrategy):
    """夜のタンカ：水エネルギー最優先。なければヒトデマン、ユキワラシの順"""
    def evaluate_play(self, board: BoardState) -> float:
        # 1位：水エネルギーがトラッシュにあるか
        if board.count_in_discard(BASIC_WATER_ENERGIE) > 0:
            return 3200.0
            
        # 2位：ヒトデマンがトラッシュにあるか
        if board.count_in_discard(HITODEMAN) > 0:
            return 2200.0
            
        # 3位：ユキワラシがトラッシュにあるか
        if board.count_in_discard(YUKIWARASHI) > 0:
            return 1700.0
            
        return 0.0  # 何も回収対象がないなら0点

class HyperballStrategy(DefaultStrategy):
    """ハイパーボール：メガスターミー ＞ メガユキメノコ ＞ マシマシラ ＞ ユキメノコの順でサーチ"""
    def evaluate_play(self, board: BoardState) -> float:
        # 手札に「エサにしていいカード（後述のコスト選定ロジック）」が2枚以上あることが前提
        return 2800.0
        
    def determine_target(self, board: BoardState) -> int:
        """ハイパーボールで山札から持ってくるポケモンの優先度選択"""
        # 1位：メガスターミーEX
        if board.count_in_deck(MEGA_STARMIE_EX) > 0:
            return MEGA_STARMIE_EX
        # 2位：メガユキメノコEX
        if board.count_in_deck(MEGA_YUKIMENOKO_EX) > 0:
            return MEGA_YUKIMENOKO_EX
        # 3位：マシマシラ
        if board.count_in_deck(MUNKIDORI) > 0:
            return MUNKIDORI
        # 4位：ユキメノコ
        if board.count_in_deck(YUKIMENOKO) > 0:
            return YUKIMENOKO
            
        return getattr(board.deck_ids, "first", 0) #USO
    
    def choose_trash_cards(self, board: BoardState) -> list[int]:
        """【実行処理】エサ優先度が高い順に2枚選んで返す"""
        candidates = []
        for card_id in board.hand_ids:
            if card_id == HYPERBALL:
                continue
            # ここで上にある共通の「エサ選定ロジック」を呼び出しています
            score = evaluate_trash_cost_priority(card_id, board)
            candidates.append((score, card_id))
            
        # スコアが高い（＝捨てていい）順に並び替えて、トップ2枚のカードIDを返す
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [candidates[0][1], candidates[1][1]]

class BallonStrategy(DefaultStrategy):
    """ふうせん：逃がす戦略でエネルギーが足りなくなった時に限定して使用"""
    def evaluate_play(self, board: BoardState) -> float:
        # バトル場をベンチに下げたい（撤退させたい）意思があるが、
        # 手貼りのエネルギーだけでは「逃げるためのコスト」が足りない場合
        active_pokemon = board.my_active_pokemon
        if active_pokemon.should_retreat and active_pokemon.attached_energy < active_pokemon.retreat_cost:
            return 3500.0  # 条件を満たした時だけスコアを跳ね上げる
            
        return 100.0  # 通常時は温存（低スコア）

class ZeiyuStrategy(DefaultStrategy):
    """ゼイユ：手札をすべてトラッシュして5枚引く。"""
    def evaluate_play(self, board: BoardState) -> float:
        # 手札に重要カードがあるならトラッシュ禁止
        if any(card in board.hand_ids for card in IMPORTANT_CARDS):
            return -99999.0
            
        if HYPERBALL in board.hand_ids:
            return 0.0
            
        # ─── 先攻1ターン目の判定 ───
        # ※環境の仕様に合わせて、先攻最初の番の時に True になる条件をここに指定します
        # 例：board.turn == 1 や board.is_first_turn などの実際の仕様を当てはめる
        is_first_turn_of_game = getattr(board, "is_first_turn", False) #uso

        if is_first_turn_of_game:
            return 3500.0
        # ───────────────────────────
            
        if len(board.hand_ids) <= 3:
            return 2000.0
        return 300.0

class LillieDeterminationStrategy(DefaultStrategy):
    """リーリエの決心：手札をすべて戻すため、キープしたいカードがある時は絶対禁止"""
    def evaluate_play(self, board: BoardState) -> float:
        # 【絶対に戻してはいけない条件】
        # 手札にメガスターミーEXやボスの指令など、山札に戻したくない重要カードがあるなら絶対禁止
        if MEGA_STARMIE_EX in board.hand_ids or BEFEHL_VON_BOSS in board.hand_ids:
            return -99999.0  # 使用禁止（最低スコア）
            
        # サイドの残り枚数が6枚なら、引ける枚数が8枚になるので評価を跳ね上げる
        if board.my_remaining_prizes == 6:
            return 2500.0
            
        # 通常時（6枚ドロー）でも、手札が少ない（リフレッシュしたい）なら高評価
        if len(board.hand_ids) <= 3:
            return 1500.0
            
        return 400.0

class ToukoStrategy(DefaultStrategy):
    """トウコ：進化ポケモンが十分あるならトラッシュ（エサ）対象、そうでなければ使う"""
    def evaluate_play(self, board: BoardState) -> float:
        # すでに盤面が十分に回っている、または手札に対象の進化ポケモンが十分ある場合
        if is_board_fully_set_up(board):
            return 0.0  # プレイ価値なし（＝コスト候補へ）
            
        return 1800.0  # 展開前なら進化のために使う


class AkamatsuStrategy(DefaultStrategy):
    """アカマツ：悪・水エネの状況で判断。マシマシラに悪エネがなければ最優先"""
    def evaluate_play(self, board: BoardState) -> float:
        # マシマシラが場にいるが、悪エネルギーが1つも付いていないかをチェック
        # （※マシマシラを特定してエネルギーをカウントする処理と仮定）
        mashimashira_needs_dark = False
        for pokemon in board.my_pokemon_in_play:
            if pokemon.card_id == MUNKIDORI and pokemon.count_energy(BASIC_UNLICHT_ENERGIE) == 0:
                mashimashira_needs_dark = True
                break
                
        # マシマシラに悪エネがないなら、特性（コンボ）を始動させるために最優先
        if mashimashira_needs_dark:
            return 4000.0
            
        # すでに水と悪が十分に場・手札に潤沢にあるなら優先度を下げる
        if board.count_total_energy(BASIC_WATER_ENERGIE) >= 4 and board.count_total_energy(BASIC_UNLICHT_ENERGIE) >= 2:
            return 500.0
            
        return 2000.0  # 通常時のエネ補給

    def choose_akamatsu_effect(self, board: BoardState) -> dict:
        """
        アカマツの効果で山札からエネルギーを選び、手札とポケモンに割り振る
        """
        # 1. 山札にあるエネルギーの在庫を確認
        has_water = board.count_in_deck(BASIC_WATER_ENERGIE) > 0
        has_dark  = board.count_in_deck(BASIC_UNLICHT_ENERGIE) > 0
        
        # 2. 作戦の核：マシマシラに悪エネルギーが付いているかチェック
        mashimashira = board.find_pokemon_in_play(MUNKIDORI)
        mashimashira_needs_dark = (
            mashimashira is not None and 
            mashimashira.count_energy(BASIC_UNLICHT_ENERGIE) == 0
        )

        # --- パターンA：マシマシラのコンボを始動させたい緊急事態 ---
        if mashimashira_needs_dark and has_dark:
            # 確実に悪エネルギーをマシマシラに「付ける」
            # 片方を手札、片方を場に付けるルールなので、悪を「場（マシマシラ）」にする
            # もう片方の水（あれば）を「手札」に加える
            return {
                "choose_from_deck": [BASIC_UNLICHT_ENERGIE, BASIC_WATER_ENERGIE] if has_water else [BASIC_UNLICHT_ENERGIE],
                "to_hand": BASIC_WATER_ENERGIE if has_water else BASIC_UNLICHT_ENERGIE,
                "to_pokemon": BASIC_UNLICHT_ENERGIE,
                "target_pokemon": mashimashira.id # マシマシラに悪エネをロックオン
            }

        # --- パターンB：通常のエネルギー補給（スターミーやユキメノコ用） ---
        else:
            # 基本は「水エネルギー」をアタッカー（スターミー等）に付けたい
            # 悪エネルギーを手札にキープするか、その逆か
            target_attacker = board.my_active_pokemon # バトル場のアタッカー
            
            if has_water and has_dark:
                return {
                    "choose_from_deck": [BASIC_WATER_ENERGIE, BASIC_UNLICHT_ENERGIE],
                    "to_hand": BASIC_UNLICHT_ENERGIE,      # 悪を手札にキープ（次の手貼り用など）
                    "to_pokemon": BASIC_WATER_ENERGIE,  # 水をアタッカーに即加速
                    "target_pokemon": target_attacker.id
                }
            
            # どちらか片方しか山札にない場合のセーフティ
            only_energy = BASIC_WATER_ENERGIE if has_water else BASIC_UNLICHT_ENERGIE
            return {
                "choose_from_deck": [only_energy],
                "to_hand": only_energy, # 1枚だけなら手札に加える
                "to_pokemon": None,
                "target_pokemon": None
            }

class MasterEvaluator:
    """すべての戦略オブジェクトを保持し、BoardStateからの要求に対して型安全にスコアを返す中央ハブ"""
    def __init__(self, board: BoardState):
        self.board = board
        self.default_strategy = DefaultStrategy()
        
        # ユーザー環境に完全に紐づいた厳密なIDによる脳みそのマッピング
        self.strategies: Dict[int, CardStrategy] = {
            BEFEHL_VON_BOSS: BossOrdersStrategy(),
            DENGEROUS_RUINE: PerilousRuinsStrategy(),
            LEGACY_ENERGIE: LegacyEnergyStrategy(),
            BASIC_UNLICHT_ENERGIE: DarknessEnergyStrategy(),
            BASIC_WATER_ENERGIE: WaterEnergyStrategy(),
            YUKIMENOKO: BenchPokemonStrategy(),
            MEGA_YUKIMENOKO_EX: BenchPokemonStrategy(),
            MUNKIDORI: BenchPokemonStrategy(),
            SUBOMIE: BudewStrategy(),
            YVELTAL: YveltalStrategy(),
            CARMINE: ZeiyuStrategy(),
            LILLIE_DETERMINATION: LillieDeterminationStrategy(),
            TOUKO: ToukoStrategy(),
            AKAMATSU: AkamatsuStrategy(),
            POKE_PAD: PokePadStrategy(),
            POFIN: PofinStrategy(),
            TANKER: TankerStrategy(),
            HYPERBALL: HyperballStrategy(),
            BALLON: BallonStrategy(),
        }

    def _get_strategy(self, card_id: int) -> CardStrategy:
        """IDをベースに辞書から戦略を引き出す（登録がなければ汎用DefaultStrategyを返す）"""
        return self.strategies.get(card_id, self.default_strategy)

    # ------------------------------------------
    # 軸1：ターゲットおよび必要性の静的評価
    # ------------------------------------------
    def evaluate_my_pokemon_need(self, card_id: int, desired_counts: Dict[int, int]) -> float:
        """理想の盤面構成数（DESIRED_COUNTS）に対する、現在の必要充足度"""
        current_count = self.board.count_in_play(card_id)
        desired_count = desired_counts.get(card_id, 0)
        
        if current_count < desired_count:
            return (desired_count - current_count) * 100.0
        return 0.0

    def evaluate_target_priority(self, opp_pokemon: Optional[Pokemon]) -> float:
        """相手のポケモンを標的としてロックオン（ボスの指令など）する際の優先スコア"""
        if opp_pokemon is None:
            return 0.0
        
        score = 0.0
        # 正確な系譜セット（ALL_HYPO_ENEMIES）に属しているか
        if opp_pokemon.id in ALL_HYPO_ENEMIES:
            score += 500.0
            if opp_pokemon.id == 190:  # ジュラルドンラインの最危険個体190ならピンポイント加算
                score += 1000.0

        # 瀕死（残りHPが削れている）個体はサイド回収チャンスのため優先度を動的に上げる
        data = self.board.get_card_data(opp_pokemon.id)
        max_hp = getattr(data, "maxHp", opp_pokemon.hp) if data else opp_pokemon.hp
        
        if opp_pokemon.hp < max_hp:
            score += (max_hp - opp_pokemon.hp) * 2.0
            
        return score

    # ------------------------------------------
    # 軸2：実際の各種行動（Action）に対する判定ゲートウェイ
    # ------------------------------------------
    def evaluate_card_play(self, card_id: int) -> float:
        """手札からトレーナーズ等を使用する（PLAY_CARD）際の価値判定"""
        return self._get_strategy(card_id).evaluate_play(self.board)

    def evaluate_energy_attach(self, card_id: int, target_pokemon: Pokemon) -> float:
        """エネルギーを手札からポケモンに付与する際の価値判定"""
        return self._get_strategy(card_id).evaluate_attach(self.board, target_pokemon)

    def evaluate_pokemon_placement(self, card_id: int) -> float:
        """手札からたねポケモンをベンチに配置する際の価値判定"""
        return self._get_strategy(card_id).evaluate_placement(self.board)

    def evaluate_trash_target(self, card_id: int) -> float:
        """ハイパーボール等のコストとしてカードを捨てる際の処理価値"""
        return self._get_strategy(card_id).evaluate_trash(self.board)


# ==========================================
# 4. データ構造：最終的な評価をコンテナ化
# ==========================================
class GameAction:
    """具体的な1つの行動候補を表し、カードスコアと行動スコアの合算を行う"""
    def __init__(self, action_type: str, target_idx: int = None, card_id: int = None):
        self.action_type = action_type    # "ATTACK", "USE_SUPPORT", "RETREAT" などの文字列
        self.target_idx = target_idx      # ターゲットの席番号（j）
        self.card_id = card_id            # 使用するカードID（グッズやサポートの場合）
        
        self.card_score = 0.0             # 軸1：カードそのもののスコア
        self.action_score = 0.0           # 軸2：行動のサイクルスコア

    @property
    def total_score(self) -> float:
        """2つの優先度スコア指標の合算"""
        return self.card_score + self.action_score

    def __repr__(self):
        return f"<Action: {self.action_type} (Target:{self.target_idx}, Card:{self.card_id}) Score: {self.total_score}>"


class OpponentPredictor:
    @staticmethod
    def predict_next_turn(virtual_board: BoardState) -> dict:
        """自分の行動が終わったと仮定した仮想盤面から、相手の次の最善手を予測する"""
        prediction = {
            "expected_damage_to_active": 0,
            "will_ko_my_active": False,
        }
        opp_active = virtual_board.opp_active
        my_active = virtual_board.active
        
        if not opp_active or not my_active:
            return prediction

        opp_card_data = virtual_board.get_card_data(opp_active.id)
        if opp_card_data and getattr(opp_card_data, "attacks", None):
            attached_count = len(getattr(opp_active, "attached_cards", []) or []) #energyCardsとtoolsの２つ
            virtual_energy_count = attached_count + 1 # 次の手貼りを想定
            
            max_dmg = 0
            for atk in opp_card_data.attacks:
                required_energy = len(getattr(atk, "cost", []))
                if virtual_energy_count >= required_energy:
                    dmg = getattr(atk, "damage", 0)
                    if dmg > max_dmg: 
                        max_dmg = dmg
            
            prediction["expected_damage_to_active"] = max_dmg
            if my_active.hp <= max_dmg:
                prediction["will_ko_my_active"] = True

        return prediction


class AttackAction(GameAction):
    def evaluate(self):
        if not self.board.active or not self.board.opp_active: 
            return
        
        # 軸1: ターゲット評価
        self.card_score = self.evaluator.evaluate_target_priority(self.board.opp_active)
        self.action_score = 5000.0  # 攻撃の基本価値

        # 1〜2手先予測のためのシミュレーション
        my_damage = self.evaluator.get_my_active_attack_damage()
        v_board = copy.deepcopy(self.board)
        if v_board.opp_active:
            v_board.opp_active.hp = max(0, v_board.opp_active.hp - my_damage)

        # 2手先：このターンで倒せるなら即決級
        if v_board.opp_active and v_board.opp_active.hp == 0:
            prize = self.evaluator.calculate_prize_value(self.board.opp_active)
            if prize >= self.board.me.remaining_prizes:
                self.action_score += 99999.0
            else:
                self.action_score += 4000.0
            return

        # 1手先：相手のターンの返しを予測
        prediction = OpponentPredictor.predict_next_turn(v_board)
        if prediction["will_ko_my_active"]:
            lost_prize = self.evaluator.calculate_prize_value(self.board.active)
            if lost_prize >= self.board.opp.remaining_prizes:
                self.action_score -= 99999.0  # 負け確行動の完全回避
            else:
                self.action_score -= (lost_prize * 2000.0) # テンポロス減点
        else:
            # 2手先：次の自分のターンで倒しきれる（確2ライン）なら加点
            if v_board.opp_active and v_board.opp_active.hp <= my_damage:
                self.action_score += 2000.0

class EvolveAction(GameAction):
    def evaluate(self):
        card_id = getattr(self.option_data, "card_id", None)
        if not card_id:
            return
        
        self.card_score = 3000.0 if card_id in [MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX, YUKIMENOKO] else 1000.0
        
        # 行動サイクル：1匹目のメインアタッカー擁立を最優先
        if card_id == MEGA_STARMIE_EX and self.board.count_in_play(MEGA_STARMIE_EX) == 0:
            self.action_score = 6000.0
        else:
            self.action_score = 2500.0

class RetreatAction(GameAction):
    def evaluate(self):
        if not self.board.active: 
            return
        
        # 軸1: ベンチに即動ける後続がいるか
        has_backup = any(p.id == MEGA_STARMIE_EX and len(getattr(p, "attached_cards", [])) >= 2 for p in self.board.bench)
        if has_backup:
            self.card_score = 1500.0
        
        # 軸2: 1手先予測による「きぜつ回避サイクル」
        v_board = copy.deepcopy(self.board)
        prediction = OpponentPredictor.predict_next_turn(v_board)
        if prediction["will_ko_my_active"]:
            self.action_score = 7000.0  # 緊急避難
        else:
            self.action_score = -1000.0 # 無意味な交代はテンポロス

class PlayCardAction(GameAction):
    def evaluate(self):
        card_id = getattr(self.option_data, "card_id", None)
        if not card_id: 
            return
        self.card_score = self.evaluator.evaluate_card_play(card_id)
        self.action_score = 500.0

class AttachEnergyAction(GameAction):
    def evaluate(self):
        card_id = getattr(self.option_data, "card_id", None)
        # 貼り先ポケモンの安全な特定 (環境の仕様に合わせて調整)
        target_idx = getattr(self.option_data, "target_index", 0)
        target_pokemon = self.board.bench[target_idx] if target_idx < len(self.board.bench) else self.board.active
        
        if not card_id or not target_pokemon: 
            return
        self.card_score = self.evaluator.evaluate_energy_attach(card_id, target_pokemon)
        self.action_score = 1000.0


# ==========================================
# 5. ファクトリーとメイン実行ループ (Agent Entrypoint)
# ==========================================
class ActionFactory:
    @staticmethod
    def create_action(idx: int, option: Any, board: BoardState, evaluator: MasterEvaluator) -> GameAction:
        opt_type = getattr(option, "type", None)
        if opt_type == OptionType.ATTACK:
            return AttackAction(idx, option, board, evaluator)
        elif opt_type == OptionType.EVOLVE:
            return EvolveAction(idx, option, board, evaluator)
        elif opt_type == OptionType.RETREAT:
            return RetreatAction(idx, option, board, evaluator)
        elif opt_type == OptionType.PLAY:
            return PlayCardAction(idx, option, board, evaluator)
        elif opt_type == OptionType.ATTACH:
            return AttachEnergyAction(idx, option, board, evaluator)
        return GameAction(idx, option, board, evaluator)


def agent(obs, config):
    board = BoardState(obs, CARD_TABLE)
    evaluator = MasterEvaluator(board)
    
    legal_options = getattr(obs, "legal_options", []) or getattr(obs.current, "legal_options", [])
    if not legal_options:
        return 0
        
    action_objects: List[GameAction] = []
    
    for idx, option in enumerate(legal_options):
        action = ActionFactory.create_action(idx, option, board, evaluator)
        action.evaluate() # ここで各クラス固有の2つの軸＋先読みスコアが自律計算される
        action_objects.append(action)
        
    # 最もスコア（カードスコア ＋ 行動スコア）が高い行動のインデックスを返す
    best_action = max(action_objects, key=lambda a: a.total_score)
    return best_action.option_idx

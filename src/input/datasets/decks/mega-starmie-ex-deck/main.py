import os
import sys
from collections import defaultdict

from cg.api import AreaType, CardType, EnergyType, Observation, SelectContext, OptionType, Card, Pokemon, all_card_data, to_observation_class
from typing import Tuple, List, Dict, Any

"""
Mega Starmie EX Deck
このデッキでは2つの優先度スコア指標を軸に戦略を立てる
1つ目はカードそのもののスコア
2つ目は行動のスコア
カードそのもののスコアは、自分のカードのスコア、ターゲットの優先度など扱うカードや
仮想的となるカードの優先順位
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


# 盤面解析クラス
class BoardState:
    def __init__(self, obs, card_table):
        self.obs = obs
        self.card_table = card_table
        self.me = obs.current.players[obs.current.yourIndex]
        self.opp = obs.current.players[1 - obs.current.yourIndex]
    
    @property
    def active(self):
        """自分のバトル場のポケモン"""
        return self.me.active[0] if self.me.acrive else None
    
    @property
    def opp_active(self):
        """相手のバトル場のポケモン"""
        return self.opp.active[0] if self.opp.active else None
    @property
    def bench(self):
        """自分のベンチポケモン（空枠排除）"""
        return [p for p in self.me.bench if p]

    @property
    def opp_bench(self):
        """相手のベンチポケモン（空枠排除）"""
        return [p for p in self.opp.bench if p]

    @property
    def all_my_pokemon(self):
        """自分の場にいるすべてのポケモン"""
        return [p for p in (self.me.active + self.me.bench) if p]

    @property
    def all_opp_pokemon(self):
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
        """相手の手札の枚数を返す（技のダメージ計算などに使用）"""
        if self.opp.hand is None:
            return 0
        # 空枠（Noneなど）が含まれる可能性を考慮して安全に数える場合
        return sum(1 for c in self.opp.hand if c)

    @property
    def discard_ids(self) -> List[int]:
        """トラッシュのカードID一覧"""
        return [c.id for c in (self.me.discard or []) if c]

    @property
    def water_in_discard(self) -> int:
        """トラッシュの水エネルギーの枚数"""
        return sum(1 for cid in self.discard_ids if cid == BASIC_WATER_ENERGIE)

    @property
    def unlicht_in_discard(self) -> int:
        """トラッシュの悪エネルギーの枚数"""
        return sum(1 for cid in self.discard_ids if cid == BASIC_UNLICHT_ENERGIE)

    def count_in_play(self, card_id: int) -> int:
        """指定したカードIDが自分の場に何枚あるか"""
        return sum(1 for pid in self.my_card_ids_in_play if pid == card_id)

    def get_card_data(self, pokemon_id: int):
        """カードテーブルからマスターデータを安全に取得"""
        return self.card_table.get(pokemon_id, None)


class CardEvaluator:
    """カードそのものの価値や、ターゲットとしての優先度（カードスコア）を決定する"""
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate_my_pokemon_need(self, card_id: int) -> float:
        """自分の場において、そのカード（または系統）がどれだけ必要とされているか"""
        # current_count = self.board.count_in_play(card_id)
        # desired_count = DESIRED_COUNTS.get(card_id, 0)
        
        # # 理想数より不足しているなら高い価値を返す（必要性の評価）
        # if current_count < desired_count:
        #     return (desired_count - current_count) * 100.0
        # return 0.0

    def evaluate_target_priority(self, opp_pokemon) -> float:
        """相手の特定のポケモンに対するロックオン度（標的としての価値）を計算"""
        if opp_pokemon is None:
            return 0.0
        
        score = 0.0
        
        # 仮想敵の系譜（ALL_HYPO_ENEMIES）に属しているか？
        if opp_pokemon.id in ALL_HYPO_ENEMIES:
            score += 500.0  # 仮想敵ならベーススコアを跳ね上げる
            
            # 特定の超危険個体へのピンポイント加算例（190: ジュラルドンなど。これから追加）
            if opp_pokemon.id == 190:
                score += 1000.0

        # 個体の状態（HPやダメージの状況）を考慮した動的評価
        data = self.board.get_card_data(opp_pokemon.id)
        max_hp = getattr(data, "maxHp", opp_pokemon.hp) if data else opp_pokemon.hp
        current_hp = opp_pokemon.hp
        
        # HPが減っている（瀕死に近い）ターゲットは優先度を上げる
        if current_hp < max_hp:
            score += (max_hp - current_hp) * 2.0
            
        return score


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


def agent(obs, config):
    board = BoardState(obs, CARD_TABLE)
    pass

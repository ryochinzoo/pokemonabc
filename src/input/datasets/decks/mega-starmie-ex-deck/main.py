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
import copy
import os
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

from cg.api import (
    AreaType,
    CardType,
    LogType,
    Observation,
    Pokemon,
    SelectContext,
    all_card_data,
    to_observation_class,
)

try:
    from cg.api import all_attack
except ImportError:
    all_attack = None


# ==========================================
# Card IDs
# ==========================================
HITODEMAN = 1030
MEGA_STARMIE_EX = 1031
YUKIWARASHI = 860
MEGA_YUKIMENOKO_EX = 861
YUKIMENOKO = 103
MUNKIDORI = 112
YVELTAL = 689
SUBOMIE = 235
MAUZI = 1071
POFIN = 1086
POKE_PAD = 1152
HYPERBALL = 1121
TANKER = 1097
BALLON = 1174
LILLIE_DETERMINATION = 1227
CARMINE = 1192
TOUKO = 1225
AKAMATSU = 1198
BEFEHL_VON_BOSS = 1182
DENGEROUS_RUINE = 1260
BASIC_WATER_ENERGIE = 3
BASIC_UNLICHT_ENERGIE = 7
LEGACY_ENERGIE = 12
JETTING_BLOW = 1487

DEFAULT_DECK = [
    1030, 1030, 1030, 1031, 1031, 860, 860, 860, 861, 861,
    103, 103, 112, 112, 112, 689, 235, 1071, 1086, 1086,
    1086, 1086, 1152, 1152, 1152, 1152, 1121, 1121, 1121, 1097,
    1097, 1174, 1227, 1227, 1227, 1227, 1192, 1192, 1192, 1192,
    1225, 1225, 1225, 1198, 1198, 1182, 1182, 1182, 1260, 1260,
    1260, 1260, 3, 3, 3, 3, 7, 7, 7, 12,
]

ALAKAZAM_LINE = {741, 742, 743}
CRUSTLE_LINE = {344, 345, 532}
STARMIE_LINE = {1030, 1031}
LUCARIO_LINE = {677, 678}
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}
MARIE_LINE = {642, 643, 644, 645, 646, 647, 648, 649}
DURALUDON_LINE = {169, 170, 190, 839, 840, 992}
DREEPY_LINE = {119, 120, 121}

ALL_HYPO_ENEMIES = (
    ALAKAZAM_LINE
    | CRUSTLE_LINE
    | STARMIE_LINE
    | LUCARIO_LINE
    | HOP_LINE
    | MARIE_LINE
    | DURALUDON_LINE
    | DREEPY_LINE
)

IMPORTANT_CARDS = {
    HITODEMAN,
    MEGA_STARMIE_EX,
    YUKIWARASHI,
    MEGA_YUKIMENOKO_EX,
    YUKIMENOKO,
    MUNKIDORI,
    BEFEHL_VON_BOSS,
}

DESIRED_COUNTS = {
    HITODEMAN: 2,
    MEGA_STARMIE_EX: 1,
    YUKIWARASHI: 2,
    MEGA_YUKIMENOKO_EX: 1,
    YUKIMENOKO: 1,
    MUNKIDORI: 1,
}

KNOWN_PRIZE_VALUES = {
    MEGA_STARMIE_EX: 3,
    MEGA_YUKIMENOKO_EX: 3,
}

ENERGY_CARD_TO_TYPE = {
    BASIC_WATER_ENERGIE: "WATER",
    BASIC_UNLICHT_ENERGIE: "DARKNESS",
}

COLORLESS_TOKENS = {"COLORLESS", "COLOURLESS", "ANY", "NONE"}
SCORE_NEG_INF = -10**18
OPTIONAL_SELECTION_THRESHOLD = 1000.0
MUNKIDORI_SOURCE_SERIAL: Optional[int] = None
MUNKIDORI_TARGET_SERIAL: Optional[int] = None


def _initialize_data() -> Tuple[List[int], Dict[int, Any], Dict[int, Any]]:
    deck_candidates = (
        "deck.csv",
        os.path.join(os.path.dirname(__file__), "deck.csv"),
        "/kaggle_simulations/agent/deck.csv",
    )
    deck_path = next((path for path in deck_candidates if os.path.exists(path)), "")

    deck: List[int] = []
    if deck_path:
        with open(deck_path, "r", encoding="utf-8") as file:
            deck = [
                int(line.strip().rstrip(","))
                for line in file.read().splitlines()
                if line.strip().rstrip(",")
            ][:60]
    if len(deck) != 60:
        deck = list(DEFAULT_DECK)

    card_table = {card.cardId: card for card in all_card_data()}

    attack_table: Dict[int, Any] = {}
    if all_attack is not None:
        try:
            attack_table = {attack.attackId: attack for attack in all_attack()}
        except Exception:
            attack_table = {}

    return deck, card_table, attack_table


DECK, CARD_TABLE, ALL_ATTACKS = _initialize_data()


# ==========================================
# BoardState facade
# ==========================================
class BoardState:
    """cg.apiへのアクセスと仮想盤面差分を集約するFacade。"""

    def __init__(self, obs: Observation, card_table: Dict[int, Any]):
        self.obs = obs
        self.card_table = card_table
        self.me = obs.current.players[obs.current.yourIndex]
        self.opp = obs.current.players[1 - obs.current.yourIndex]

        self._my_active: Optional[Pokemon] = self.me.active[0] if self.me.active else None
        self._opp_active: Optional[Pokemon] = self.opp.active[0] if self.opp.active else None
        self._my_bench_slots: List[Optional[Pokemon]] = list(self.me.bench)
        self._opp_bench_slots: List[Optional[Pokemon]] = list(self.opp.bench)
        self._my_prizes = len(self.me.prize)
        self._opp_prizes = len(self.opp.prize)
        self._stadium_id: Optional[int] = None
        if obs.current.stadium:
            self._stadium_id = obs.current.stadium[0].id

        self._hp: Dict[int, int] = {}
        self._card_ids: Dict[int, int] = {}
        self._extra_energy: Dict[int, List[str]] = {}
        self._spent_energy_serials: set[int] = set()
        self._damage_counter_steps_used = 0
        self._remaining_damage_counter = int(obs.select.remainDamageCounter or 0)
        self._healing_ceiling: Dict[int, int] = {}

    @staticmethod
    def _key(pokemon: Pokemon) -> int:
        return id(pokemon)

    @staticmethod
    def _enum_token(value: Any) -> str:
        text = str(value).upper()
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        return text

    @property
    def your_index(self) -> int:
        return self.obs.current.yourIndex

    @property
    def select_data(self):
        return self.obs.select

    @property
    def select_type(self):
        return self.select_data.type

    @property
    def select_context(self):
        return self.select_data.context

    @property
    def select_options(self) -> List[Any]:
        return list(self.select_data.option or [])

    @property
    def remain_damage_counter(self) -> int:
        return self._remaining_damage_counter

    @property
    def remain_energy_cost(self) -> int:
        return int(self.select_data.remainEnergyCost or 0)

    @property
    def select_deck(self) -> List[Any]:
        return list(self.select_data.deck or [])

    @property
    def deck_is_visible(self) -> bool:
        return bool(self.select_data.deck)

    @property
    def context_card(self):
        return self.select_data.contextCard

    @property
    def context_card_id(self) -> Optional[int]:
        if self.context_card is None:
            return None
        # Card/Pokemon双方で既存コード上確認済みのidを使用。
        return self.context_card.id

    @property
    def effect(self):
        return self.select_data.effect

    @property
    def effect_card_id(self) -> Optional[int]:
        if self.effect is None:
            return None
        return self.effect.id

    def recent_my_attack_id(self) -> Optional[int]:
        for log in reversed(self.obs.logs or []):
            if log.type == LogType.ATTACK and log.playerIndex == self.your_index:
                return log.attackId
        return None

    def selected_damage_amount(self) -> int:
        if self.recent_my_attack_id() == JETTING_BLOW:
            return 50
        if self.effect_card_id == MEGA_STARMIE_EX or self.context_card_id == MEGA_STARMIE_EX:
            return 50
        return 0

    def iter_options(self) -> Iterable[Tuple[int, Any]]:
        return enumerate(self.select_options)

    @property
    def active(self) -> Optional[Pokemon]:
        return self._my_active

    @property
    def opp_active(self) -> Optional[Pokemon]:
        return self._opp_active

    @property
    def bench_slots(self) -> List[Optional[Pokemon]]:
        return list(self._my_bench_slots)

    @property
    def opp_bench_slots(self) -> List[Optional[Pokemon]]:
        return list(self._opp_bench_slots)

    @property
    def bench(self) -> List[Pokemon]:
        return [pokemon for pokemon in self._my_bench_slots if pokemon is not None]

    @property
    def opp_bench(self) -> List[Pokemon]:
        return [pokemon for pokemon in self._opp_bench_slots if pokemon is not None]

    @property
    def all_my_pokemon(self) -> List[Pokemon]:
        result = []
        if self.active is not None:
            result.append(self.active)
        result.extend(self.bench)
        return result

    @property
    def all_opp_pokemon(self) -> List[Pokemon]:
        result = []
        if self.opp_active is not None:
            result.append(self.opp_active)
        result.extend(self.opp_bench)
        return result

    @property
    def hand_ids(self) -> List[int]:
        return [card.id for card in (self.me.hand or []) if card is not None]

    @property
    def discard_ids(self) -> List[int]:
        return [card.id for card in (self.me.discard or []) if card is not None]

    @property
    def my_remaining_prizes(self) -> int:
        return self._my_prizes

    @property
    def opp_remaining_prizes(self) -> int:
        return self._opp_prizes

    @property
    def stadium_id(self) -> Optional[int]:
        return self._stadium_id

    def card_id(self, pokemon: Pokemon) -> int:
        return self._card_ids.get(self._key(pokemon), pokemon.id)

    def current_hp(self, pokemon: Optional[Pokemon]) -> int:
        if pokemon is None:
            return 0
        return self._hp.get(self._key(pokemon), int(pokemon.hp))

    def set_hp(self, pokemon: Optional[Pokemon], hp: int) -> None:
        if pokemon is not None:
            self._hp[self._key(pokemon)] = max(0, int(hp))

    def set_card_id(self, pokemon: Pokemon, card_id: int) -> None:
        self._card_ids[self._key(pokemon)] = card_id

    def set_stadium(self, card_id: int) -> None:
        self._stadium_id = card_id

    def get_card_data(self, card_id: int):
        return self.card_table.get(card_id)

    def get_attack(self, attack_id: Optional[int]):
        if attack_id is None:
            return None
        return ALL_ATTACKS.get(attack_id)

    def get_attacks(self, pokemon: Optional[Pokemon]) -> List[Any]:
        if pokemon is None:
            return []
        data = self.get_card_data(self.card_id(pokemon))
        if data is None:
            return []
        return [ALL_ATTACKS[attack_id] for attack_id in data.attacks if attack_id in ALL_ATTACKS]

    def _energy_token_from_card_id(self, card_id: int) -> str:
        return ENERGY_CARD_TO_TYPE.get(card_id, f"CARD_{card_id}")

    def attached_energy_tokens(self, pokemon: Optional[Pokemon]) -> List[str]:
        if pokemon is None:
            return []

        tokens: List[str] = []
        cards = self.attached_energy_cards(pokemon)
        if pokemon.energyCards:
            tokens.extend(self._energy_token_from_card_id(card.id) for card in cards)
        elif pokemon.energies:
            tokens.extend(self._enum_token(value) for value in pokemon.energies)
        else:
            tokens.extend(self._energy_token_from_card_id(card.id) for card in pokemon.energyCards)

        tokens.extend(self._extra_energy.get(self._key(pokemon), []))
        return tokens

    def attached_energy_cards(self, pokemon: Optional[Pokemon]) -> List[Any]:
        if pokemon is None:
            return []
        return [
            card
            for card in pokemon.energyCards
            if card is not None and card.serial not in self._spent_energy_serials
        ]

    def attached_energy_card_ids(self, pokemon: Optional[Pokemon]) -> List[int]:
        if pokemon is None:
            return []
        return [card.id for card in self.attached_energy_cards(pokemon)]

    def count_energy(self, pokemon: Optional[Pokemon], energy: Optional[Any] = None) -> int:
        if pokemon is None:
            return 0
        if energy is None:
            return len(self.attached_energy_tokens(pokemon))

        if isinstance(energy, int) and energy in ENERGY_CARD_TO_TYPE:
            token = ENERGY_CARD_TO_TYPE[energy]
            return self.attached_energy_tokens(pokemon).count(token)
        if isinstance(energy, int):
            return self.attached_energy_card_ids(pokemon).count(energy)
        return self.attached_energy_tokens(pokemon).count(self._enum_token(energy))

    def count_tools(self, pokemon: Optional[Pokemon]) -> int:
        return len(pokemon.tools) if pokemon is not None else 0

    def effective_retreat_cost(self, pokemon: Optional[Pokemon]) -> int:
        if pokemon is None:
            return 0
        data = self.get_card_data(self.card_id(pokemon))
        cost = int(data.retreatCost or 0) if data is not None else 0
        if any(tool.id == BALLON for tool in pokemon.tools):
            cost -= 2
        return max(0, cost)

    def discard_attached_energy(self, option: Any) -> bool:
        target = self.get_option_target(option)
        cards = self.attached_energy_cards(target)
        if target is None or option.energyIndex is None:
            return False
        index = int(option.energyIndex)
        if not (0 <= index < len(cards)):
            return False
        self._spent_energy_serials.add(cards[index].serial)
        return True

    def get_option_energy_card(self, option: Any) -> Optional[Any]:
        target = self.get_option_target(option)
        cards = self.attached_energy_cards(target)
        if target is None or option.energyIndex is None:
            return None
        index = int(option.energyIndex)
        return cards[index] if 0 <= index < len(cards) else None

    def add_virtual_energy(self, pokemon: Optional[Pokemon], token: str) -> None:
        if pokemon is None:
            return
        self._extra_energy.setdefault(self._key(pokemon), []).append(token)

    def attack_requirements(self, attack: Any) -> List[str]:
        return [self._enum_token(value) for value in attack.energies]

    def can_use_attack(
        self,
        pokemon: Optional[Pokemon],
        attack: Any,
        extra_tokens: Optional[Sequence[str]] = None,
    ) -> bool:
        if pokemon is None or attack is None:
            return False

        pool = Counter(self.attached_energy_tokens(pokemon))
        if extra_tokens:
            pool.update(extra_tokens)

        colorless = 0
        for requirement in self.attack_requirements(attack):
            if requirement in COLORLESS_TOKENS:
                colorless += 1
                continue
            if pool[requirement] <= 0:
                return False
            pool[requirement] -= 1

        return sum(pool.values()) >= colorless

    def legal_attacks(
        self,
        pokemon: Optional[Pokemon],
        extra_tokens: Optional[Sequence[str]] = None,
    ) -> List[Any]:
        return [
            attack
            for attack in self.get_attacks(pokemon)
            if self.can_use_attack(pokemon, attack, extra_tokens)
        ]

    def strongest_attack(
        self,
        pokemon: Optional[Pokemon],
        extra_tokens: Optional[Sequence[str]] = None,
    ):
        attacks = self.legal_attacks(pokemon, extra_tokens)
        if not attacks:
            return None
        return max(attacks, key=lambda attack: int(attack.damage or 0))

    def best_attack_damage(
        self,
        pokemon: Optional[Pokemon],
        extra_tokens: Optional[Sequence[str]] = None,
    ) -> int:
        attack = self.strongest_attack(pokemon, extra_tokens)
        return int(attack.damage or 0) if attack is not None else 0

    def possible_manual_energy_tokens(self, pokemon: Optional[Pokemon]) -> List[str]:
        required = {
            token
            for attack in self.get_attacks(pokemon)
            for token in self.attack_requirements(attack)
            if token not in COLORLESS_TOKENS
        }
        required.update({"WATER", "DARKNESS"})
        return sorted(required)

    def calculate_max_damage(self, pokemon: Optional[Pokemon], next_turn: bool = False) -> int:
        if pokemon is None:
            return 0
        if not next_turn:
            return self.best_attack_damage(pokemon)
        return max(
            [self.best_attack_damage(pokemon)]
            + [self.best_attack_damage(pokemon, [token]) for token in self.possible_manual_energy_tokens(pokemon)]
        )

    def can_attack_next_turn(self, pokemon: Optional[Pokemon]) -> bool:
        return self.calculate_max_damage(pokemon, next_turn=True) > 0

    def count_in_play(self, card_id: int) -> int:
        return sum(1 for pokemon in self.all_my_pokemon if self.card_id(pokemon) == card_id)

    def count_in_discard(self, card_id: int) -> int:
        return self.discard_ids.count(card_id)

    def count_in_deck(self, card_id: int) -> int:
        return sum(1 for card in self.select_deck if card.id == card_id)

    def deck_has_card_matching(self, predicate) -> bool:
        return any(predicate(card.id) for card in self.select_deck)

    def is_poffin_target(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.basic and data.hp <= 70 and not data.ex

    def is_pokemon_card(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.POKEMON

    def is_rule_box_pokemon(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.POKEMON and (data.ex or data.megaEx or data.tera)

    def is_poke_pad_target(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return self.is_pokemon_card(card_id) and not self.is_rule_box_pokemon(card_id)

    def is_evolution_pokemon(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.POKEMON and not data.basic

    def is_basic_energy_card(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.BASIC_ENERGY

    def has_ability(self, pokemon: Optional[Pokemon]) -> bool:
        if pokemon is None:
            return False
        data = self.get_card_data(self.card_id(pokemon))
        return data is not None and bool(data.skills)

    def needs_touko_evolution(self) -> bool:
        return any(
            self.count_in_play(card_id) < DESIRED_COUNTS.get(card_id, 0)
            for card_id in (YUKIMENOKO, MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX)
        )

    def needs_water_energy(self) -> bool:
        starmie = self.find_pokemon(MEGA_STARMIE_EX)
        if starmie is not None and self.count_energy(starmie, BASIC_WATER_ENERGIE) == 0:
            return True
        return self.count_energy(self.active, BASIC_WATER_ENERGIE) == 0 and BASIC_WATER_ENERGIE not in self.hand_ids

    def needs_dark_energy(self) -> bool:
        mashimashira = self.find_pokemon(MUNKIDORI)
        return mashimashira is not None and self.count_energy(mashimashira, BASIC_UNLICHT_ENERGIE) == 0

    def needs_tanker_recovery(self) -> bool:
        if self.needs_water_energy() and self.count_in_discard(BASIC_WATER_ENERGIE) > 0:
            return True
        if self.needs_dark_energy() and self.count_in_discard(BASIC_UNLICHT_ENERGIE) > 0:
            return True
        return any(
            self.count_in_play(card_id) < DESIRED_COUNTS.get(card_id, 0)
            and self.count_in_discard(card_id) > 0
            for card_id in (HITODEMAN, YUKIWARASHI, MUNKIDORI)
        )

    def find_pokemon(self, card_id: int, mine: bool = True) -> Optional[Pokemon]:
        source = self.all_my_pokemon if mine else self.all_opp_pokemon
        return next((pokemon for pokemon in source if self.card_id(pokemon) == card_id), None)

    def total_energy(self, mine: bool = True) -> int:
        source = self.all_my_pokemon if mine else self.all_opp_pokemon
        return sum(self.count_energy(pokemon) for pokemon in source)

    def calculate_prize_value(self, pokemon: Optional[Pokemon]) -> int:
        if pokemon is None:
            return 0
        prize = KNOWN_PRIZE_VALUES.get(self.card_id(pokemon), 1)
        data = self.get_card_data(self.card_id(pokemon))
        if data is not None:
            if data.megaEx:
                prize = 3
            elif data.ex:
                prize = 2
        if any(card.id == LEGACY_ENERGIE for card in self.attached_energy_cards(pokemon)):
            prize = max(1, prize - 1)
        return prize

    @property
    def my_active_remaining_hp(self) -> int:
        return self.current_hp(self.active)

    @property
    def opp_active_max_damage(self) -> int:
        return self.calculate_max_damage(self.opp_active, next_turn=True)

    @property
    def my_active_prize_value(self) -> int:
        return self.calculate_prize_value(self.active)

    @property
    def has_ready_mashimashira(self) -> bool:
        pokemon = self.find_pokemon(MUNKIDORI)
        return pokemon is not None and self.count_energy(pokemon, BASIC_UNLICHT_ENERGIE) > 0

    @property
    def has_damage_counters_to_move(self) -> bool:
        # Pokemon側ダメカン数は未公開。合法なDAMAGE_COUNTER選択の存在を根拠にする。
        return self.remain_damage_counter > 0

    def my_active_can_attack(self) -> bool:
        return bool(self.legal_attacks(self.active))

    def can_take_prize(self, attacker: Optional[Pokemon], defender: Optional[Pokemon]) -> bool:
        return attacker is not None and defender is not None and self.best_attack_damage(attacker) >= self.current_hp(defender)

    def damage_target_value(self, target: Optional[Pokemon], damage: int) -> float:
        if target is None:
            return SCORE_NEG_INF
        if self.option_target_is_mine(target):
            return -99999.0

        hp = self.current_hp(target)
        prize = self.calculate_prize_value(target)
        score = self.calculate_prize_value(target) * 800.0
        if target is self.opp_active:
            score += 300.0
        else:
            score += 700.0
        if self.card_id(target) in ALL_HYPO_ENEMIES:
            score += 1000.0
        if damage >= hp:
            score += prize * 5000.0
        elif hp - damage <= self.best_attack_damage(self.active):
            score += 1800.0
        return score

    def can_win_by_killing_bench_pokemon(self) -> bool:
        if self.active is None:
            return False
        return any(
            self.can_take_prize(self.active, pokemon)
            and self.calculate_prize_value(pokemon) >= self.my_remaining_prizes
            for pokemon in self.opp_bench
        )

    def option_area(self, option: Any):
        return option.area if option.area is not None else option.inPlayArea

    def option_index(self, option: Any) -> int:
        if option.area is not None:
            return int(option.index or 0)
        return int(option.inPlayIndex or 0)

    def option_points_to_me(self, option: Any) -> bool:
        return option.playerIndex is None or option.playerIndex == self.your_index

    def option_target_is_mine(self, target: Pokemon) -> bool:
        return any(target is pokemon for pokemon in self.all_my_pokemon)

    def apply_damage_counter(self, target: Pokemon, adding: bool) -> None:
        if adding:
            self.set_hp(target, self.current_hp(target) - 10)
        else:
            key = self._key(target)
            if key not in self._healing_ceiling:
                self._healing_ceiling[key] = self.current_hp(target) + max(1, self.remain_damage_counter) * 10
            self.set_hp(target, min(self.current_hp(target) + 10, self._healing_ceiling[key]))
        self._remaining_damage_counter = max(0, self._remaining_damage_counter - 1)
        self._damage_counter_steps_used += 1

    def get_option_target(self, option: Any) -> Optional[Pokemon]:
        area = self.option_area(option)
        index = self.option_index(option)
        mine = self.option_points_to_me(option)

        if area == AreaType.ACTIVE:
            return self.active if mine else self.opp_active
        if area == AreaType.BENCH:
            slots = self._my_bench_slots if mine else self._opp_bench_slots
            return slots[index] if 0 <= index < len(slots) else None
        return None

    def option_type_token(self, option: Any) -> str:
        return self._enum_token(option.type)

    def select_descriptor(self) -> str:
        return " ".join(
            (
                self._enum_token(self.select_type),
                self._enum_token(self.select_context),
                self._enum_token(self.effect),
            )
        )

    def switch_with_bench(self, mine: bool, bench_index: int) -> bool:
        slots = self._my_bench_slots if mine else self._opp_bench_slots
        if not (0 <= bench_index < len(slots)) or slots[bench_index] is None:
            return False
        if mine:
            slots[bench_index], self._my_active = self._my_active, slots[bench_index]
        else:
            slots[bench_index], self._opp_active = self._opp_active, slots[bench_index]
        return True

    def evolve_target(self, target: Optional[Pokemon], card_id: int) -> bool:
        if target is None:
            return False
        # 最大HP未公開のため、受けているダメージ量の正確な維持は行わない。
        self.set_card_id(target, card_id)
        return True

    def take_prizes(self, mine: bool, count: int) -> None:
        if mine:
            self._my_prizes = max(0, self._my_prizes - count)
        else:
            self._opp_prizes = max(0, self._opp_prizes - count)

    def _choose_replacement_index(self, mine: bool) -> Optional[int]:
        slots = self._my_bench_slots if mine else self._opp_bench_slots
        candidates = [(index, pokemon) for index, pokemon in enumerate(slots) if pokemon is not None]
        if not candidates:
            return None

        if mine:
            return max(candidates, key=lambda pair: self.calculate_max_damage(pair[1], next_turn=True))[0]
        # 相手が選ぶため、こちらに最も不利な候補を採用する。
        return max(candidates, key=lambda pair: self.calculate_max_damage(pair[1], next_turn=True))[0]

    def resolve_knockout(self, target: Pokemon, target_is_mine: bool) -> None:
        prize = self.calculate_prize_value(target)
        if target_is_mine:
            self.take_prizes(mine=False, count=prize)
            if target is self.active:
                self._my_active = None
                replacement = self._choose_replacement_index(mine=True)
                if replacement is not None:
                    self.switch_with_bench(mine=True, bench_index=replacement)
            else:
                for index, pokemon in enumerate(self._my_bench_slots):
                    if pokemon is target:
                        self._my_bench_slots[index] = None
                        break
        else:
            self.take_prizes(mine=True, count=prize)
            if target is self.opp_active:
                self._opp_active = None
                replacement = self._choose_replacement_index(mine=False)
                if replacement is not None:
                    self.switch_with_bench(mine=False, bench_index=replacement)
            else:
                for index, pokemon in enumerate(self._opp_bench_slots):
                    if pokemon is target:
                        self._opp_bench_slots[index] = None
                        break


# ==========================================
# Strategies
# ==========================================
def is_board_fully_set_up(board: BoardState) -> bool:
    starmie = board.count_in_play(HITODEMAN) + board.count_in_play(MEGA_STARMIE_EX) >= 2
    yuki = (
        board.count_in_play(YUKIWARASHI)
        + board.count_in_play(MEGA_YUKIMENOKO_EX)
        + board.count_in_play(YUKIMENOKO)
        >= 2
    )
    return starmie and yuki


def is_early_game(board: BoardState) -> bool:
    return int(board.obs.current.turn or 0) <= 4 and board.my_remaining_prizes >= 5


def evaluate_trash_cost_priority(card_id: int, board: BoardState) -> float:
    if card_id in IMPORTANT_CARDS:
        return -99999.0
    if card_id == SUBOMIE:
        if board.hand_ids.count(SUBOMIE) > 1:
            return 3600.0
        if is_early_game(board) and not is_board_fully_set_up(board):
            return -3000.0
        if board.my_remaining_prizes <= 4 or is_board_fully_set_up(board):
            return 3200.0
        return 800.0
    if card_id == YVELTAL:
        return 5000.0
    if is_board_fully_set_up(board) and card_id in {TOUKO, POKE_PAD}:
        return 4200.0
    if card_id == CARMINE and HYPERBALL in board.hand_ids:
        return 4000.0
    return 100.0


class CardStrategy(Protocol):
    def evaluate_play(self, board: BoardState) -> float: ...
    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float: ...
    def evaluate_placement(self, board: BoardState) -> float: ...
    def evaluate_trash(self, board: BoardState) -> float: ...


class DefaultStrategy:
    def evaluate_play(self, board: BoardState) -> float:
        return 0.0

    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        return 100.0

    def evaluate_placement(self, board: BoardState) -> float:
        return 100.0

    def evaluate_trash(self, board: BoardState) -> float:
        return 0.0


class BossOrdersStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if board.can_win_by_killing_bench_pokemon():
            return 99999.0
        score = 500.0 if board.opp_bench else 0.0
        if board.active is not None and board.my_active_remaining_hp <= board.opp_active_max_damage:
            score += board.my_active_prize_value * 1200.0
        return score


class PerilousRuinsStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if board.stadium_id == DENGEROUS_RUINE:
            return 0.0
        score = 3200.0
        if is_early_game(board):
            score += 900.0
        if board.has_ready_mashimashira:
            score += 800.0
        if board.has_damage_counters_to_move:
            score += 300.0
        return score


class LegacyEnergyStrategy(DefaultStrategy):
    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        return {3: 5000.0, 2: 3000.0}.get(board.calculate_prize_value(target), 100.0)


class DarknessEnergyStrategy(DefaultStrategy):
    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        if board.card_id(target) == MUNKIDORI:
            return 4000.0
        if board.card_id(target) == YVELTAL:
            return 10.0
        return 100.0


class WaterEnergyStrategy(DefaultStrategy):
    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        if board.card_id(target) == MEGA_STARMIE_EX:
            return 4000.0
        if board.card_id(target) in {MEGA_YUKIMENOKO_EX, YUKIMENOKO}:
            return 2500.0
        return 100.0


class BenchPokemonStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        return 2100.0


class BudewStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        return 1600.0 if board.my_remaining_prizes >= 5 else -400.0

    def evaluate_trash(self, board: BoardState) -> float:
        if board.hand_ids.count(SUBOMIE) > 1:
            return 3600.0
        if is_early_game(board) and not is_board_fully_set_up(board):
            return -3000.0
        return 2200.0 if board.my_remaining_prizes <= 4 or is_board_fully_set_up(board) else 0.0


class YveltalStrategy(DefaultStrategy):
    def evaluate_trash(self, board: BoardState) -> float:
        return 3000.0


class PokePadStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if is_board_fully_set_up(board):
            return 0.0
        if not board.deck_is_visible:
            return 2500.0
        return 2500.0 if board.deck_has_card_matching(board.is_poke_pad_target) else -99999.0


class PofinStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if is_board_fully_set_up(board):
            return 0.0
        if not board.deck_is_visible:
            return 2600.0
        return 2600.0 if board.deck_has_card_matching(board.is_poffin_target) else -99999.0


class TankerStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if not board.needs_tanker_recovery():
            return 0.0
        if board.needs_dark_energy() and board.count_in_discard(BASIC_UNLICHT_ENERGIE):
            return 3600.0
        if board.needs_water_energy() and board.count_in_discard(BASIC_WATER_ENERGIE):
            return 3200.0
        if board.count_in_discard(HITODEMAN):
            return 2200.0
        if board.count_in_discard(YUKIWARASHI):
            return 1700.0
        if board.count_in_discard(MUNKIDORI):
            return 1500.0
        return 0.0


class HyperballStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        scores = sorted(
            [
                evaluate_trash_cost_priority(card_id, board)
                for card_id in board.hand_ids
                if card_id != HYPERBALL
            ],
            reverse=True,
        )
        return 2800.0 if len(scores) >= 2 and scores[1] > -90000.0 else -99999.0


class BallonStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        active_cost = board.effective_retreat_cost(board.active)
        if active_cost >= 2:
            return 1800.0
        if active_cost == 1 and board.my_active_remaining_hp <= board.opp_active_max_damage:
            return 1200.0
        return 100.0


class ZeiyuStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if any(card_id in IMPORTANT_CARDS for card_id in board.hand_ids):
            return -99999.0
        if HYPERBALL in board.hand_ids:
            return 0.0
        return 2000.0 if len(board.hand_ids) <= 3 else 300.0


class LillieDeterminationStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if MEGA_STARMIE_EX in board.hand_ids or BEFEHL_VON_BOSS in board.hand_ids:
            return -99999.0
        if board.my_remaining_prizes == 6:
            return 2500.0
        return 1500.0 if len(board.hand_ids) <= 3 else 400.0


class ToukoStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if not board.needs_touko_evolution() and not board.needs_water_energy() and not board.needs_dark_energy():
            return -800.0
        score = 1800.0
        if board.needs_touko_evolution():
            score += 1200.0
        if board.needs_water_energy():
            score += 800.0
        if board.needs_dark_energy():
            score += 1000.0
        return score


class AkamatsuStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if not board.needs_water_energy() and not board.needs_dark_energy():
            return 300.0
        score = 900.0
        if is_early_game(board):
            score += 700.0
        if board.needs_water_energy():
            score += 900.0
        if board.needs_dark_energy():
            score += 900.0
        return score


# ==========================================
# Evaluators
# ==========================================
class PrizeRaceEvaluator:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate(self) -> float:
        return (self.board.opp_remaining_prizes - self.board.my_remaining_prizes) * 2500.0


class TempoEvaluator:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate(self) -> float:
        return (
            self.board.best_attack_damage(self.board.active) * 3.0
            - self.board.calculate_max_damage(self.board.opp_active, next_turn=True) * 2.5
            + len(self.board.bench) * 120.0
            - len(self.board.opp_bench) * 80.0
        )


class FutureBoardEvaluator:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate(self) -> float:
        score = (self.board.total_energy(True) - self.board.total_energy(False)) * 100.0
        score += sum(self.board.current_hp(pokemon) for pokemon in self.board.all_my_pokemon) * 0.5
        score -= sum(self.board.current_hp(pokemon) for pokemon in self.board.all_opp_pokemon) * 0.25
        score += sum(500.0 for pokemon in self.board.bench if self.board.can_attack_next_turn(pokemon))
        return score


class AbilityResolver:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate(self) -> float:
        score = 0.0
        mashimashira = self.board.find_pokemon(MUNKIDORI)
        if mashimashira is not None and self.board.count_energy(mashimashira, BASIC_UNLICHT_ENERGIE) > 0:
            score += 300.0 if self.board.has_damage_counters_to_move else 100.0
        opp_ability_pokemon = sum(1 for pokemon in self.board.all_opp_pokemon if self.board.has_ability(pokemon))
        my_ability_pokemon = sum(1 for pokemon in self.board.all_my_pokemon if self.board.has_ability(pokemon))
        score += self.board.count_in_play(YUKIMENOKO) * (opp_ability_pokemon * 120.0 - my_ability_pokemon * 30.0)
        return score


class DamageCounterValue:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate_munkidori(self, target: Optional[Pokemon], adding: bool) -> float:
        if target is None:
            return SCORE_NEG_INF
        score = self.evaluate_target(target, adding)
        if adding and not self.board.option_target_is_mine(target):
            score += 1600.0
            if target is self.board.opp_active:
                score += 900.0
        if not adding and self.board.option_target_is_mine(target):
            missing_hp = max(0, int(target.maxHp) - self.board.current_hp(target))
            score += 800.0 + min(3, missing_hp // 10) * 700.0
            if target is self.board.active:
                score += 600.0
        return score

    def evaluate_perilous_ruins(self, target: Optional[Pokemon]) -> float:
        if target is None:
            return SCORE_NEG_INF
        score = self.evaluate_target(target, adding=True)
        if target is not self.board.opp_active:
            score += 400.0
        return score

    def evaluate_yukimenoko(self, target: Optional[Pokemon]) -> float:
        if target is None:
            return SCORE_NEG_INF
        score = self.evaluate_target(target, adding=True)
        if self.board.best_attack_damage(self.board.active) >= max(0, self.board.current_hp(target) - 10):
            score += 1500.0
        return score

    def evaluate_target(self, target: Optional[Pokemon], adding: bool) -> float:
        if target is None:
            return SCORE_NEG_INF
        hp = self.board.current_hp(target)
        prize = self.board.calculate_prize_value(target)
        score = prize * 500.0
        if adding:
            if target is self.board.opp_active:
                score += 1200.0 + self.board.remain_damage_counter * 120.0
            else:
                score += max(0, 2000 - hp * 5)
            if self.board.card_id(target) in ALL_HYPO_ENEMIES:
                score += 1000.0
            if hp <= 10:
                score += 10000.0
            elif hp - 10 <= self.board.best_attack_damage(self.board.active):
                score += 2500.0
        else:
            score += prize * 1200.0
            if target is self.board.active:
                score += 700.0
            if hp <= self.board.opp_active_max_damage:
                score += 1800.0
        return score


class BoardEvaluator:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate(self) -> float:
        score = PrizeRaceEvaluator(self.board).evaluate()
        score += TempoEvaluator(self.board).evaluate()
        score += FutureBoardEvaluator(self.board).evaluate()
        score += AbilityResolver(self.board).evaluate()
        if self.board.my_remaining_prizes == 0:
            score += 1_000_000.0
        if self.board.opp_remaining_prizes == 0:
            score -= 1_000_000.0
        return score


class MasterEvaluator:
    def __init__(self, board: BoardState):
        self.board = board
        self.default_strategy = DefaultStrategy()
        self.damage_counter = DamageCounterValue(board)
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
            POKE_PAD: PokePadStrategy(),
            POFIN: PofinStrategy(),
            TANKER: TankerStrategy(),
            HYPERBALL: HyperballStrategy(),
            BALLON: BallonStrategy(),
            CARMINE: ZeiyuStrategy(),
            LILLIE_DETERMINATION: LillieDeterminationStrategy(),
            TOUKO: ToukoStrategy(),
            AKAMATSU: AkamatsuStrategy(),
        }

    def strategy(self, card_id: int) -> CardStrategy:
        return self.strategies.get(card_id, self.default_strategy)

    def evaluate_card_play(self, card_id: int) -> float:
        return self.strategy(card_id).evaluate_play(self.board)

    def evaluate_energy_attach(self, card_id: int, target: Pokemon) -> float:
        return self.strategy(card_id).evaluate_attach(self.board, target)

    def evaluate_pokemon_placement(self, card_id: int) -> float:
        return self.strategy(card_id).evaluate_placement(self.board)

    def evaluate_trash_target(self, card_id: int) -> float:
        return max(
            evaluate_trash_cost_priority(card_id, self.board),
            self.strategy(card_id).evaluate_trash(self.board),
        )

    def evaluate_target_priority(self, target: Optional[Pokemon]) -> float:
        if target is None:
            return SCORE_NEG_INF
        score = 0.0
        if self.board.card_id(target) in ALL_HYPO_ENEMIES:
            score += 500.0
        if self.board.card_id(target) == 190:
            score += 1000.0
        if self.board.can_take_prize(self.board.active, target):
            score += self.board.calculate_prize_value(target) * 3000.0
        return score


class SearchResolver:
    def __init__(self, board: BoardState, evaluator: MasterEvaluator):
        self.board = board
        self.evaluator = evaluator

    def score_effect_card(self, card_id: int) -> float:
        effect_id = self.board.effect_card_id or self.board.context_card_id
        need = max(0, DESIRED_COUNTS.get(card_id, 0) - self.board.count_in_play(card_id)) * 500.0

        if effect_id == POFIN:
            return need + self.evaluator.evaluate_pokemon_placement(card_id) if self.board.is_poffin_target(card_id) else -99999.0
        if effect_id == POKE_PAD:
            return need + self.evaluator.evaluate_pokemon_placement(card_id) if self.board.is_poke_pad_target(card_id) else -99999.0
        if effect_id == HYPERBALL:
            return need + self.evaluator.evaluate_pokemon_placement(card_id) if self.board.is_pokemon_card(card_id) else -99999.0
        if effect_id == TANKER:
            if card_id == BASIC_UNLICHT_ENERGIE and self.board.needs_dark_energy():
                return 3600.0
            if card_id == BASIC_WATER_ENERGIE and self.board.needs_water_energy():
                return 3200.0
            if card_id in (HITODEMAN, YUKIWARASHI, MUNKIDORI):
                return need + self.evaluator.evaluate_pokemon_placement(card_id)
            if self.board.is_pokemon_card(card_id) or self.board.is_basic_energy_card(card_id):
                return 500.0
            return -99999.0
        if effect_id == TOUKO:
            if card_id == YUKIMENOKO:
                return need + 3600.0
            if card_id == MEGA_STARMIE_EX:
                return need + 3400.0
            if card_id == MEGA_YUKIMENOKO_EX:
                return need + 3000.0
            if card_id == BASIC_UNLICHT_ENERGIE and self.board.needs_dark_energy():
                return 2800.0
            if card_id == BASIC_WATER_ENERGIE:
                return 2400.0 if self.board.needs_water_energy() else 900.0
            return -99999.0
        if effect_id == AKAMATSU:
            if card_id == BASIC_UNLICHT_ENERGIE and not self.board.has_ready_mashimashira:
                return 3200.0
            if card_id == BASIC_WATER_ENERGIE:
                return 2800.0 if self.board.needs_water_energy() else 1600.0
            if self.board.is_basic_energy_card(card_id):
                return 400.0
            return -99999.0

        return self.score_card(card_id)

    def score_card(self, card_id: int) -> float:
        need = max(0, DESIRED_COUNTS.get(card_id, 0) - self.board.count_in_play(card_id)) * 500.0
        data = self.board.get_card_data(card_id)
        if data is None:
            return need
        if data.attacks:
            return need + self.evaluator.evaluate_pokemon_placement(card_id)
        if card_id in {BASIC_WATER_ENERGIE, BASIC_UNLICHT_ENERGIE, LEGACY_ENERGIE}:
            return need + 400.0
        return need + self.evaluator.evaluate_card_play(card_id)


class TargetResolver:
    def __init__(self, board: BoardState, evaluator: MasterEvaluator):
        self.board = board
        self.evaluator = evaluator

    def score_target(self, target: Pokemon, mine: bool) -> float:
        if mine:
            return self.board.calculate_max_damage(target, next_turn=True) + self.board.current_hp(target) * 0.1
        return self.evaluator.evaluate_target_priority(target)


# ==========================================
# Simulation
# ==========================================
class GameSimulator:
    def __init__(self, board: BoardState):
        self.board = board

    def _attack_response_score(self, attacker: Pokemon, defender: Pokemon) -> float:
        damage = self.board.calculate_max_damage(attacker, next_turn=True)
        score = float(damage)
        if damage >= self.board.current_hp(defender):
            score += self.board.calculate_prize_value(defender) * 5000.0
        return score

    def _active_can_leave(self, mine: bool) -> bool:
        player = self.board.me if mine else self.board.opp
        active = self.board.active if mine else self.board.opp_active
        if active is None:
            return False
        if player.asleep or player.paralyzed:
            return False
        return self.board.count_energy(active) >= self.board.effective_retreat_cost(active)

    def _bench_switch_cost(self, mine: bool) -> float:
        active = self.board.active if mine else self.board.opp_active
        if active is None:
            return 0.0
        retreat_cost = self.board.effective_retreat_cost(active)
        if self._active_can_leave(mine):
            return 600.0 + retreat_cost * 300.0
        return 2500.0 + retreat_cost * 400.0

    def _attack_candidates(self, mine: bool) -> List[Tuple[Pokemon, float]]:
        active = self.board.active if mine else self.board.opp_active
        bench = self.board.bench if mine else self.board.opp_bench

        candidates: List[Tuple[Pokemon, float]] = []
        if active is not None and self.board.calculate_max_damage(active, next_turn=True) > 0:
            candidates.append((active, 0.0))

        switch_cost = self._bench_switch_cost(mine)
        for pokemon in bench:
            if self.board.calculate_max_damage(pokemon, next_turn=True) <= 0:
                continue
            candidates.append((pokemon, switch_cost))
        return candidates

    def evaluate_opponent_response(self) -> float:
        if self.board.active is None:
            return 0.0

        candidates = self._attack_candidates(mine=False)

        return max(
            [self._attack_response_score(attacker, self.board.active) - switch_cost for attacker, switch_cost in candidates]
            or [0.0]
        )

    def evaluate_my_followup(self) -> float:
        if self.board.opp_active is None:
            return 0.0

        candidates = self._attack_candidates(mine=True)

        return max(
            [self._attack_response_score(attacker, self.board.opp_active) - switch_cost for attacker, switch_cost in candidates]
            or [0.0]
        )

    def evaluate_after_action(self, action: "GameAction") -> float:
        virtual = copy.deepcopy(self.board)
        action.apply(virtual)
        score = BoardEvaluator(virtual).evaluate()
        score -= self.__class__(virtual).evaluate_opponent_response()
        score += self.__class__(virtual).evaluate_my_followup() * 0.5
        return score


# ==========================================
# Actions
# ==========================================
class GameAction:
    def __init__(self, option_index: int, option: Any, board: BoardState, evaluator: MasterEvaluator):
        self.option_index = option_index
        self.option = option
        self.board = board
        self.evaluator = evaluator
        self.card_score = 0.0
        self.action_score = 0.0

    @property
    def total_score(self) -> float:
        return self.card_score + self.action_score

    def evaluate(self) -> None:
        self.action_score = SelectionResolver(self.board, self.evaluator).score(self.option)

    def apply(self, board: BoardState) -> BoardState:
        return board


class AttackAction(GameAction):
    def evaluate(self) -> None:
        attack = self.board.get_attack(self.option.attackId)
        attacker = self.board.active
        defender = self.board.opp_active
        if attack is None or attacker is None or defender is None or not self.board.can_use_attack(attacker, attack):
            self.action_score = -99999.0
            return
        damage = int(attack.damage or 0)
        self.card_score = self.evaluator.evaluate_target_priority(defender)
        self.action_score = 5000.0 + damage * 5.0
        self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        attack = board.get_attack(self.option.attackId)
        defender = board.opp_active
        if attack is None or defender is None:
            return board
        board.set_hp(defender, board.current_hp(defender) - int(attack.damage or 0))
        if board.current_hp(defender) == 0:
            board.resolve_knockout(defender, target_is_mine=False)
        return board


class EvolveAction(GameAction):
    def evaluate(self) -> None:
        if self.option.cardId is None:
            self.action_score = -99999.0
            return
        self.card_score = 3000.0 if self.option.cardId in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX, YUKIMENOKO} else 1000.0
        self.action_score = 2500.0 + GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        if self.option.cardId is not None:
            board.evolve_target(board.get_option_target(self.option), self.option.cardId)
        return board


class RetreatAction(GameAction):
    def evaluate(self) -> None:
        target = self.board.get_option_target(self.option)
        if target is None:
            self.action_score = -99999.0
            return
        danger = self.board.active is not None and self.board.my_active_remaining_hp <= self.board.opp_active_max_damage
        self.action_score = (7000.0 if danger else -1000.0) + self.board.calculate_max_damage(target, next_turn=True)
        self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        if board.option_area(self.option) == AreaType.BENCH:
            board.switch_with_bench(mine=True, bench_index=board.option_index(self.option))
        return board


class PlayCardAction(GameAction):
    def evaluate(self) -> None:
        if self.option.cardId is None:
            self.action_score = -99999.0
            return
        self.card_score = self.evaluator.evaluate_card_play(self.option.cardId)
        self.action_score = 500.0 + GameSimulator(self.board).evaluate_after_action(self) * 0.03

    def apply(self, board: BoardState) -> BoardState:
        card_id = self.option.cardId
        if card_id == DENGEROUS_RUINE:
            board.set_stadium(DENGEROUS_RUINE)
        elif card_id == BEFEHL_VON_BOSS:
            target = board.get_option_target(self.option)
            if target is not None and target is not board.opp_active:
                for index, pokemon in enumerate(board.opp_bench_slots):
                    if pokemon is target:
                        board.switch_with_bench(mine=False, bench_index=index)
                        break
        # 非公開山札や手札枚数を伴う効果は、選択評価側で扱い、仮想盤面には即時公開差分だけ反映する。
        return board


class AttachEnergyAction(GameAction):
    def energy_token(self) -> str:
        if self.option.cardId is None:
            return "UNKNOWN"
        return ENERGY_CARD_TO_TYPE.get(self.option.cardId, f"CARD_{self.option.cardId}")

    def evaluate(self) -> None:
        target = self.board.get_option_target(self.option)
        if self.option.cardId is None or target is None:
            self.action_score = -99999.0
            return
        self.card_score = self.evaluator.evaluate_energy_attach(self.option.cardId, target)
        before = self.board.best_attack_damage(target)
        after = self.board.best_attack_damage(target, [self.energy_token()])
        self.action_score = 1000.0 + max(0, after - before) * 10.0
        self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        board.add_virtual_energy(board.get_option_target(self.option), self.energy_token())
        return board


class EnergySelectionAction(GameAction):
    def evaluate(self) -> None:
        card = self.board.get_option_energy_card(self.option)
        target = self.board.get_option_target(self.option)
        if card is None:
            self.action_score = 0.0
            return

        if self.board.select_context == SelectContext.TO_HAND_ENERGY:
            self.action_score = 2500.0 if card.id in {BASIC_WATER_ENERGIE, BASIC_UNLICHT_ENERGIE} else 800.0
            return
        if self.board.select_context == SelectContext.TO_DECK_ENERGY:
            self.action_score = -self.evaluator.evaluate_trash_target(card.id)
            return
        if self.board.select_context == SelectContext.SWITCH_ENERGY:
            self.action_score = self.evaluator.evaluate_energy_attach(card.id, target) if target is not None else 0.0
            return

        self.action_score = 0.0


class DiscardEnergyAction(GameAction):
    def evaluate(self) -> None:
        card = self.board.get_option_energy_card(self.option)
        target = self.board.get_option_target(self.option)
        if card is None or target is None:
            self.action_score = -99999.0
            return

        score = 0.0
        if card.id == LEGACY_ENERGIE:
            score -= 8000.0
        elif card.id == BASIC_UNLICHT_ENERGIE and self.board.card_id(target) == MUNKIDORI:
            score -= 5000.0
        elif card.id == BASIC_WATER_ENERGIE and self.board.card_id(target) == MEGA_STARMIE_EX:
            score -= 2500.0
        else:
            score += 1000.0

        remaining = self.board.count_energy(target) - 1
        if remaining < self.board.effective_retreat_cost(target):
            score -= 600.0
        self.action_score = score

    def apply(self, board: BoardState) -> BoardState:
        board.discard_attached_energy(self.option)
        return board


class DamageAction(GameAction):
    def evaluate(self) -> None:
        target = self.board.get_option_target(self.option)
        damage = self.board.selected_damage_amount()
        if damage <= 0:
            self.action_score = self.evaluator.evaluate_target_priority(target)
            return
        self.action_score = self.board.damage_target_value(target, damage)

    def apply(self, board: BoardState) -> BoardState:
        target = board.get_option_target(self.option)
        damage = board.selected_damage_amount()
        if target is not None and damage > 0:
            board.set_hp(target, board.current_hp(target) - damage)
            if board.current_hp(target) == 0:
                board.resolve_knockout(target, target_is_mine=board.option_points_to_me(self.option))
        return board


class YesNoAction(GameAction):
    def evaluate(self) -> None:
        yes = "YES" in self.board.option_type_token(self.option)
        context = self.board.select_context
        card_id = self.board.context_card_id or self.board.effect_card_id

        if context == SelectContext.ACTIVATE and card_id == MUNKIDORI:
            value = 4000.0 if self.board.has_ready_mashimashira and self.board.has_damage_counters_to_move else -500.0
            self.action_score = value if yes else -value
            return

        if context == SelectContext.ACTIVATE and card_id is not None:
            value = self.evaluator.evaluate_card_play(card_id)
            self.action_score = value if yes else -value
            return

        if context == SelectContext.FIRST_EFFECT:
            self.action_score = 0.0
            return

        self.action_score = 0.0


class DamageCounterAction(GameAction):
    def __init__(
        self,
        option_index: int,
        option: Any,
        board: BoardState,
        evaluator: MasterEvaluator,
        adding: bool,
    ):
        super().__init__(option_index, option, board, evaluator)
        self.adding = adding

    def evaluate(self) -> None:
        target = self.board.get_option_target(self.option)
        context = self.board.context_card_id
        if context == MUNKIDORI:
            self.action_score = self.evaluator.damage_counter.evaluate_munkidori(target, self.adding)
        elif context == DENGEROUS_RUINE:
            self.action_score = self.evaluator.damage_counter.evaluate_perilous_ruins(target)
        elif context in {YUKIMENOKO, MEGA_YUKIMENOKO_EX}:
            self.action_score = self.evaluator.damage_counter.evaluate_yukimenoko(target)
        else:
            self.action_score = self.evaluator.damage_counter.evaluate_target(target, self.adding)

    def apply(self, board: BoardState) -> BoardState:
        target = board.get_option_target(self.option)
        if target is not None:
            board.apply_damage_counter(target, self.adding)
            if self.adding and board.current_hp(target) == 0:
                board.resolve_knockout(target, target_is_mine=board.option_points_to_me(self.option))
        return board


# ==========================================
# Selection and damage-counter resolution
# ==========================================
class SelectionResolver:
    def __init__(self, board: BoardState, evaluator: MasterEvaluator):
        self.board = board
        self.evaluator = evaluator
        self.search = SearchResolver(board, evaluator)
        self.targets = TargetResolver(board, evaluator)

    def score(self, option: Any) -> float:
        descriptor = self.board.select_descriptor()

        if option.cardId is not None:
            if self.board.select_context in (
                SelectContext.TO_HAND,
                SelectContext.TO_HAND_ENERGY,
                SelectContext.TO_FIELD,
                SelectContext.TO_BENCH,
            ):
                return self.search.score_effect_card(option.cardId)
            if self.board.deck_is_visible or "DECK" in descriptor or "SEARCH" in descriptor:
                return self.search.score_effect_card(option.cardId)
            if "TRASH" in descriptor or "DISCARD" in descriptor:
                return self.evaluator.evaluate_trash_target(option.cardId)
            if "RECOVER" in descriptor or "RETRIEVE" in descriptor or "HAND" in descriptor:
                return self.search.score_effect_card(option.cardId)
            # 用途不明時はカードの役割を断定しない。
            return 0.0

        target = self.board.get_option_target(option)
        if target is not None:
            mine = self.board.option_points_to_me(option)
            return self.targets.score_target(target, mine)

        return float(option.serial or 0) * 0.001

    def choose(self) -> Optional[int]:
        scored = [(self.score(option), index) for index, option in self.board.iter_options()]
        return max(scored, key=lambda pair: pair[0])[1] if scored else None


class DamageCounterEngine:
    def __init__(self, board: BoardState):
        self.board = board

    def is_adding(self, board: BoardState, option: Any) -> bool:
        descriptor = board.select_descriptor()
        if any(token in descriptor for token in ("REMOVE", "HEAL")):
            return False
        if any(token in descriptor for token in ("PUT", "ADD", "DAMAGE")):
            return True
        if board.context_card_id == MUNKIDORI:
            return not board.option_points_to_me(option)
        if board.context_card_id in {DENGEROUS_RUINE, YUKIMENOKO, MEGA_YUKIMENOKO_EX}:
            return True
        return not board.option_points_to_me(option)

    def _munkidori_lock_bonus(self, target: Pokemon, adding: bool) -> float:
        if self.board.context_card_id != MUNKIDORI:
            return 0.0
        if adding:
            if MUNKIDORI_TARGET_SERIAL is None:
                return 0.0
            return 2500.0 if target.serial == MUNKIDORI_TARGET_SERIAL else -20000.0
        if MUNKIDORI_SOURCE_SERIAL is None:
            return 0.0
        return 2500.0 if target.serial == MUNKIDORI_SOURCE_SERIAL else -20000.0

    def _remember_munkidori_choice(self, target: Pokemon, adding: bool) -> None:
        global MUNKIDORI_SOURCE_SERIAL, MUNKIDORI_TARGET_SERIAL
        if self.board.context_card_id != MUNKIDORI:
            return
        if adding:
            if MUNKIDORI_TARGET_SERIAL is None:
                MUNKIDORI_TARGET_SERIAL = target.serial
            return
        if MUNKIDORI_SOURCE_SERIAL is None:
            MUNKIDORI_SOURCE_SERIAL = target.serial

    def choose_option(self) -> Optional[int]:
        best_index: Optional[int] = None
        best_target: Optional[Pokemon] = None
        best_adding = False
        best_score = SCORE_NEG_INF

        evaluator = MasterEvaluator(self.board)
        for index, option in self.board.iter_options():
            target = self.board.get_option_target(option)
            if target is None:
                continue
            adding = self.is_adding(self.board, option)
            action = DamageCounterAction(index, option, self.board, evaluator, adding)
            action.evaluate()
            virtual = copy.deepcopy(self.board)
            action.apply(virtual)
            score = action.action_score
            score += self._munkidori_lock_bonus(target, adding)
            score -= GameSimulator(virtual).evaluate_opponent_response() * 0.1
            score += GameSimulator(virtual).evaluate_my_followup() * 0.1
            if score > best_score:
                best_score = score
                best_index = index
                best_target = target
                best_adding = adding

        if best_target is not None:
            self._remember_munkidori_choice(best_target, best_adding)
        return best_index


# ==========================================
# Action factory
# ==========================================
class ActionFactory:
    @staticmethod
    def create_action(
        option_index: int,
        option: Any,
        board: BoardState,
        evaluator: MasterEvaluator,
    ) -> GameAction:
        token = board.option_type_token(option)

        if "YES" in token or "NO" in token:
            return YesNoAction(option_index, option, board, evaluator)
        if board.select_context == SelectContext.DAMAGE:
            return DamageAction(option_index, option, board, evaluator)
        if board.select_context in (SelectContext.DISCARD_ENERGY_CARD, SelectContext.DISCARD_ENERGY):
            return DiscardEnergyAction(option_index, option, board, evaluator)
        if board.select_context in (
            SelectContext.TO_HAND_ENERGY,
            SelectContext.TO_DECK_ENERGY,
            SelectContext.SWITCH_ENERGY,
        ):
            return EnergySelectionAction(option_index, option, board, evaluator)
        if option.attackId is not None or "ATTACK" in token:
            return AttackAction(option_index, option, board, evaluator)
        if "EVOLVE" in token:
            return EvolveAction(option_index, option, board, evaluator)
        if "RETREAT" in token or "SWITCH" in token:
            return RetreatAction(option_index, option, board, evaluator)
        if "ATTACH" in token or option.energyIndex is not None:
            return AttachEnergyAction(option_index, option, board, evaluator)
        if "PLAY" in token or "USE" in token:
            return PlayCardAction(option_index, option, board, evaluator)

        return GameAction(option_index, option, board, evaluator)

    @staticmethod
    def build_actions(board: BoardState, evaluator: MasterEvaluator) -> List[GameAction]:
        actions: List[GameAction] = []
        for index, option in board.iter_options():
            action = ActionFactory.create_action(index, option, board, evaluator)
            action.evaluate()
            actions.append(action)
        return actions


# ==========================================
# Agent entrypoint
# ==========================================
def _format_selection(board: BoardState, actions: List[GameAction]) -> List[int]:
    if not actions:
        return []

    minimum = int(board.select_data.minCount or 0)
    maximum = int(board.select_data.maxCount or 0)
    if maximum <= 0:
        return []

    ranked = sorted(actions, key=lambda action: action.total_score, reverse=True)
    selected: List[int] = []

    if len(selected) < minimum:
        for action in ranked:
            if action.option_index not in selected and 0 <= action.option_index < len(board.select_options):
                selected.append(action.option_index)
                if len(selected) >= minimum:
                    break

    threshold = 0.0 if minimum >= maximum else OPTIONAL_SELECTION_THRESHOLD
    for action in ranked:
        if len(selected) >= maximum:
            break
        if action.option_index in selected:
            continue
        if action.total_score >= threshold and 0 <= action.option_index < len(board.select_options):
            selected.append(action.option_index)

    if not selected and minimum == 0:
        return []
    if not selected:
        return [ranked[0].option_index]
    return selected


def agent(obs, config=None):
    global MUNKIDORI_SOURCE_SERIAL, MUNKIDORI_TARGET_SERIAL
    if isinstance(obs, dict):
        obs = to_observation_class(obs)
    if obs.select is None or obs.current is None:
        MUNKIDORI_SOURCE_SERIAL = None
        MUNKIDORI_TARGET_SERIAL = None
        return DECK

    board = BoardState(obs, CARD_TABLE)

    if not board.select_options:
        return []

    if board.context_card_id != MUNKIDORI:
        MUNKIDORI_SOURCE_SERIAL = None
        MUNKIDORI_TARGET_SERIAL = None

    if board.select_context in (
        SelectContext.DAMAGE_COUNTER,
        SelectContext.DAMAGE_COUNTER_ANY,
        SelectContext.REMOVE_DAMAGE_COUNTER,
    ):
        selected = DamageCounterEngine(board).choose_option()
        if selected is not None and 0 <= selected < len(board.select_options):
            return [selected]

    evaluator = MasterEvaluator(board)
    actions = ActionFactory.build_actions(board, evaluator)
    if not actions:
        return []

    selected = _format_selection(board, actions)
    if selected or int(board.select_data.minCount or 0) == 0:
        return selected

    fallback = SelectionResolver(board, evaluator).choose()
    return [fallback] if fallback is not None else []

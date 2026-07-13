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
import sys
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

_MODULE_FILE = globals().get("__file__")
DEBUG_SELECTION = False
_CG_PATH_CANDIDATES = [os.getcwd(), "/kaggle_simulations/agent"]
if _MODULE_FILE:
    _CG_PATH_CANDIDATES.insert(0, os.path.dirname(os.path.abspath(_MODULE_FILE)))
for _path in _CG_PATH_CANDIDATES:
    if _path and _path not in sys.path and os.path.isdir(os.path.join(_path, "cg")):
        sys.path.insert(0, _path)

from cg.api import (
    AreaType,
    CardType,
    LogType,
    Observation,
    OptionType,
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
YUKIMENOKO = 104
MUNKIDORI = 112
YVELTAL = 689
POFIN = 1086
POKE_PAD = 1152
HYPERBALL = 1121
POKEGEAR = 1122
HAND_TRIMMER = 1087
TANKER = 1097
BALLON = 1174
HERO_CAPE = 1159
MEGA_SIGNAL = 1145
LILLIE_DETERMINATION = 1227
CARMINE = 1192
TOUKO = 1225
AKAMATSU = 1198
BEFEHL_VON_BOSS = 1182
DENGEROUS_RUINE = 1260
WALLY_COMPASSION = 1229
BASIC_WATER_ENERGIE = 3
BASIC_UNLICHT_ENERGIE = 7
LEGACY_ENERGIE = 12
BELLOWING_THUNDER = 72
RAPID_FIRE_COMBO = 1092
JETTING_BLOW = 1487
NEBULA_BEAM = 1488
POWERFUL_HAND = 1072
RESENTFUL_REFRAIN = 1240
ABSOLUTE_SNOW = 1241
FULL_MOON_RONDO = 371
CRUEL_ARROW = 183

DEFAULT_DECK = [
    1030, 1030, 1030, 1031, 1031, 860, 860, 860, 861, 861,
    104, 104, 112, 112, 689, 1122, 860, 1086, 1086, 1086,
    1086, 1152, 1152, 1152, 1152, 1121, 1121, 1121, 1097,
    1097, 1174, 1159, 1087, 1227, 1227, 1227, 1227, 1192, 1192,
    1229, 1225, 1225, 1198, 1198, 1182, 1182, 1182, 1260, 1260,
    1260, 1260, 3, 3, 3, 3, 3, 3, 7, 7, 7,
]

ALAKAZAM_LINE = {741, 742, 743}
ALAKAZAM_PRE_EVOS = {741, 742}
CRUSTLE_LINE = {344, 345, 532}
CRUSTLE_PRE_EVOS = {344, 532}
STARMIE_LINE = {1030, 1031}
RIOLU = 677
MEGA_LUCARIO_EX = 678
LUCARIO_LINE = {RIOLU, MEGA_LUCARIO_EX}
LUCARIO_PRE_EVOS = {RIOLU}
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}
MARIE_LINE = {642, 643, 644, 645, 646, 647, 648, 649}
DURALUDON_LINE = {169, 170, 190, 839, 840, 992}
DURALUDON_PRE_EVOS = {169, 170, 839, 840, 992}
DREEPY_LINE = {119, 120, 121}
DREEPY_PRE_EVOS = {119, 120}
DRAGAPULT_EX = 121
SHAYMIN = 343
SETUP_THREAT_PRE_EVOS = ALAKAZAM_PRE_EVOS | LUCARIO_PRE_EVOS | DREEPY_PRE_EVOS | DURALUDON_PRE_EVOS | CRUSTLE_PRE_EVOS
SETUP_THREAT_FINALS = {MEGA_LUCARIO_EX, DRAGAPULT_EX, 190, 743}

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

DEVELOPMENT_PLAY_CARDS = {
    DENGEROUS_RUINE,
    POFIN,
    POKE_PAD,
    POKEGEAR,
    HAND_TRIMMER,
    HYPERBALL,
    TANKER,
    HERO_CAPE,
    MEGA_SIGNAL,
    LILLIE_DETERMINATION,
    CARMINE,
    TOUKO,
    AKAMATSU,
    WALLY_COMPASSION,
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
    1: "GRASS",
    2: "FIRE",
    BASIC_WATER_ENERGIE: "WATER",
    4: "LIGHTNING",
    5: "PSYCHIC",
    6: "FIGHTING",
    BASIC_UNLICHT_ENERGIE: "DARKNESS",
    8: "METAL",
    LEGACY_ENERGIE: "RAINBOW",
}

ENERGY_TYPE_TO_TOKEN = {
    0: "COLORLESS",
    1: "GRASS",
    2: "FIRE",
    3: "WATER",
    4: "LIGHTNING",
    5: "PSYCHIC",
    6: "FIGHTING",
    7: "DARKNESS",
    8: "METAL",
    9: "DRAGON",
    10: "RAINBOW",
    11: "TEAM_ROCKET",
}
COLORLESS_TOKENS = {"COLORLESS", "COLOURLESS", "ANY", "NONE"}
SCORE_NEG_INF = -10**18
OPTIONAL_SELECTION_THRESHOLD = 1000.0
MUNKIDORI_SOURCE_SERIAL: Optional[int] = None
MUNKIDORI_TARGET_SERIAL: Optional[int] = None


def _initialize_data() -> Tuple[List[int], Dict[int, Any], Dict[int, Any]]:
    module_file = globals().get("__file__")
    deck_candidates = ["deck.csv", "/kaggle_simulations/agent/deck.csv"]
    if module_file:
        deck_candidates.insert(1, os.path.join(os.path.dirname(module_file), "deck.csv"))
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

    try:
        card_table = {card.cardId: card for card in all_card_data()}
    except Exception:
        card_table = {}

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
    def turn(self) -> int:
        return int(self.obs.current.turn or 0)

    @property
    def turn_action_count(self) -> int:
        return int(self.obs.current.turnActionCount or 0)

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

    def option_card(self, option: Any) -> Optional[Any]:
        if option.cardId is not None:
            return option
        if option.area is None and option.index is not None and option.type == OptionType.PLAY:
            cards = self.me.hand or []
            index = int(option.index)
            return cards[index] if 0 <= index < len(cards) else None
        if option.area is None or option.index is None:
            return None

        index = int(option.index)
        cards: Optional[Sequence[Any]] = None
        if option.area == AreaType.DECK:
            cards = self.select_deck
        elif option.area == AreaType.LOOKING:
            cards = self.obs.current.looking or []
        elif option.area == AreaType.HAND and option.playerIndex in (None, self.your_index):
            cards = self.me.hand or []
        elif option.area == AreaType.DISCARD and option.playerIndex in (None, self.your_index):
            cards = self.me.discard or []
        elif option.area == AreaType.PRIZE and option.playerIndex in (None, self.your_index):
            cards = self.me.prize or []

        if cards is None or index < 0 or index >= len(cards):
            return None
        return cards[index]

    def option_card_id(self, option: Any) -> Optional[int]:
        if option.cardId is not None:
            return option.cardId
        card = self.option_card(option)
        return None if card is None else card.id

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

    @property
    def has_foreign_stadium(self) -> bool:
        return self.stadium_id is not None and self.stadium_id != DENGEROUS_RUINE

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

    def _energy_type_token(self, value: Any) -> str:
        if isinstance(value, int):
            return ENERGY_TYPE_TO_TOKEN.get(value, str(value))
        try:
            numeric = int(value)
            return ENERGY_TYPE_TO_TOKEN.get(numeric, self._enum_token(value))
        except (TypeError, ValueError):
            return self._enum_token(value)

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
            tokens.extend(self._energy_type_token(value) for value in pokemon.energies)
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

    def attached_water_count(self) -> int:
        return sum(self.count_energy(pokemon, BASIC_WATER_ENERGIE) for pokemon in self.all_my_pokemon)

    def water_energy_is_scarce(self) -> bool:
        visible_water = self.hand_ids.count(BASIC_WATER_ENERGIE) + self.attached_water_count()
        if visible_water >= 3:
            return False
        return visible_water <= 1 or self.needs_water_energy() or self.should_reserve_water_for_starmie

    def primary_water_line(self) -> Optional[str]:
        if not self.water_energy_is_scarce():
            return None
        if any(
            self.card_id(pokemon) == MEGA_STARMIE_EX and self.count_energy(pokemon, BASIC_WATER_ENERGIE) > 0
            for pokemon in self.all_my_pokemon
        ):
            return "STARMIE"
        if any(
            self.card_id(pokemon) == MEGA_YUKIMENOKO_EX and self.count_energy(pokemon, BASIC_WATER_ENERGIE) > 0
            for pokemon in self.all_my_pokemon
        ):
            return "YUKI"
        yuki_line_visible = (
            self.count_in_play(YUKIWARASHI) > 0
            or self.count_in_play(MEGA_YUKIMENOKO_EX) > 0
            or MEGA_YUKIMENOKO_EX in self.hand_ids
        )
        if yuki_line_visible and (self.opponent_has_alakazam_line or int(self.opp.handCount or 0) >= 6):
            return "YUKI"
        return "STARMIE"

    def pokemon_matches_primary_water_line(self, pokemon: Optional[Pokemon]) -> bool:
        line = self.primary_water_line()
        if line is None or pokemon is None:
            return True
        card_id = self.card_id(pokemon)
        if line == "STARMIE":
            return card_id in {HITODEMAN, MEGA_STARMIE_EX}
        if line == "YUKI":
            return card_id in {YUKIWARASHI, MEGA_YUKIMENOKO_EX}
        return True

    def retreat_would_spend_water(self, pokemon: Optional[Pokemon]) -> bool:
        return self.count_energy(pokemon, BASIC_WATER_ENERGIE) > 0 and self.effective_retreat_cost(pokemon) > 0

    def add_virtual_energy(self, pokemon: Optional[Pokemon], token: str) -> None:
        if pokemon is None:
            return
        self._extra_energy.setdefault(self._key(pokemon), []).append(token)

    def attack_requirements(self, attack: Any) -> List[str]:
        return [self._energy_type_token(value) for value in attack.energies]

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
                if pool["RAINBOW"] <= 0:
                    return False
                pool["RAINBOW"] -= 1
            else:
                pool[requirement] -= 1

        return sum(pool.values()) >= colorless

    def attack_energy_shortfall(
        self,
        pokemon: Optional[Pokemon],
        attack: Optional[Any],
        extra_tokens: Optional[Sequence[str]] = None,
    ) -> int:
        if pokemon is None or attack is None:
            return 99

        pool = Counter(self.attached_energy_tokens(pokemon))
        if extra_tokens:
            pool.update(extra_tokens)

        missing = 0
        colorless = 0
        for requirement in self.attack_requirements(attack):
            if requirement in COLORLESS_TOKENS:
                colorless += 1
                continue
            if pool[requirement] > 0:
                pool[requirement] -= 1
            elif pool["RAINBOW"] > 0:
                pool["RAINBOW"] -= 1
            else:
                missing += 1

        available_for_colorless = sum(pool.values())
        if available_for_colorless < colorless:
            missing += colorless - available_for_colorless
        return missing

    def high_impact_attack(self, pokemon: Optional[Pokemon]) -> Optional[Any]:
        attacks = self.get_attacks(pokemon)
        if not attacks:
            return None
        preferred_ids = {NEBULA_BEAM, ABSOLUTE_SNOW}
        preferred = [attack for attack in attacks if attack.attackId in preferred_ids]
        candidates = preferred or attacks
        return max(candidates, key=lambda attack: self.effective_attack_damage(pokemon, attack))

    def high_impact_attack_progress(
        self,
        pokemon: Optional[Pokemon],
        extra_tokens: Optional[Sequence[str]] = None,
    ) -> float:
        attack = self.high_impact_attack(pokemon)
        if pokemon is None or attack is None:
            return 0.0
        missing = self.attack_energy_shortfall(pokemon, attack, extra_tokens)
        damage = self.effective_attack_damage(pokemon, attack)
        if missing <= 0:
            return damage * 8.0 + 2400.0
        if missing <= 3:
            return damage * (4 - missing) * 1.6
        return 0.0

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
        return max(attacks, key=lambda attack: self.effective_attack_damage(pokemon, attack))

    def effective_attack_damage(self, pokemon: Optional[Pokemon], attack: Optional[Any]) -> int:
        if pokemon is None or attack is None:
            return 0
        defender = self.opp_active if self.pokemon_is_mine(pokemon) else self.active
        if self.crustle_blocks_ex_attack(pokemon, defender):
            return 0
        mine = self.pokemon_is_mine(pokemon)
        if attack.attackId == BELLOWING_THUNDER:
            return self.total_basic_energy_cards(mine=mine) * 70
        if attack.attackId == RAPID_FIRE_COMBO:
            return int(attack.damage or 0) + 50
        if attack.attackId == FULL_MOON_RONDO:
            return int(attack.damage or 0) + (len(self.bench) + len(self.opp_bench)) * 20
        if attack.attackId == CRUEL_ARROW:
            return 100
        if attack.attackId == RESENTFUL_REFRAIN:
            if mine:
                return int(self.opp.handCount or 0) * 50
            return int(self.me.handCount or 0) * 50
        if attack.attackId == POWERFUL_HAND:
            if mine:
                return int(self.me.handCount or 0) * 20
            return int(self.opp.handCount or 0) * 20
        return int(attack.damage or 0)

    def my_resentful_refrain_damage(self) -> int:
        return int(self.opp.handCount or 0) * 50

    def hand_trimmer_resentful_refrain_loss(self) -> int:
        opp_hand = int(self.opp.handCount or 0)
        return max(0, opp_hand - 5) * 50

    def can_use_resentful_refrain_now(self) -> bool:
        attack = self.get_attack(RESENTFUL_REFRAIN)
        return (
            self.active is not None
            and self.card_id(self.active) == MEGA_YUKIMENOKO_EX
            and attack is not None
            and self.can_use_attack(self.active, attack)
        )

    def has_ready_resentful_refrain_attacker(self) -> bool:
        attack = self.get_attack(RESENTFUL_REFRAIN)
        if attack is None:
            return False
        return any(
            self.card_id(pokemon) == MEGA_YUKIMENOKO_EX and self.can_use_attack(pokemon, attack)
            for pokemon in self.all_my_pokemon
        )

    def resentful_refrain_pressure_value(self) -> float:
        if not self.has_ready_resentful_refrain_attacker():
            return 0.0
        damage = self.my_resentful_refrain_damage()
        if self.opp_active is None:
            return 0.0
        score = 0.0
        if self.can_use_resentful_refrain_now():
            hp = self.current_hp(self.opp_active)
            if damage >= hp:
                score += self.calculate_prize_value(self.opp_active) * 6000.0
            elif damage >= max(0, hp - 50):
                score += 3200.0
            if damage >= 250:
                score += 1800.0
        elif damage >= self.current_hp(self.opp_active):
            score += 2400.0
        return score

    def best_attack_damage(
        self,
        pokemon: Optional[Pokemon],
        extra_tokens: Optional[Sequence[str]] = None,
    ) -> int:
        attack = self.strongest_attack(pokemon, extra_tokens)
        return self.effective_attack_damage(pokemon, attack)

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

    def is_supporter_card(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.SUPPORTER

    def is_poke_pad_target(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return self.is_pokemon_card(card_id) and not self.is_rule_box_pokemon(card_id)

    def is_mega_signal_target(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.POKEMON and data.megaEx

    def needs_mega_signal_target(self) -> bool:
        if self.wants_mega_starmie_for_hitodeman:
            return True
        if self.count_in_play(YUKIWARASHI) and self.count_in_play(MEGA_YUKIMENOKO_EX) == 0:
            return True
        if self.opponent_has_alakazam_line and self.count_in_play(YUKIWARASHI):
            return True
        return False

    def is_evolution_pokemon(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.POKEMON and not data.basic

    def wally_compassion_value(self) -> float:
        best = -99999.0
        for pokemon in self.all_my_pokemon:
            if self.card_id(pokemon) not in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                continue
            damage = max(0, int(pokemon.maxHp) - self.current_hp(pokemon))
            if damage <= 0:
                continue
            active = pokemon is self.active
            at_risk = active and self.current_hp(pokemon) <= self.opp_active_max_damage
            if not at_risk:
                if damage < 120:
                    continue
                if not active and damage < 160:
                    continue

            score = 700.0 + damage * 14.0
            if active:
                score += 900.0
            if at_risk:
                score += 3600.0 + self.calculate_prize_value(pokemon) * 900.0
            if self.best_attack_damage(pokemon) > 0 and not at_risk:
                score -= 1800.0
            score -= self.count_energy(pokemon) * 650.0
            best = max(best, score)
        return best

    def is_wally_compassion_live(self) -> bool:
        return self.wally_compassion_value() > 0.0

    def is_basic_energy_card(self, card_id: int) -> bool:
        data = self.get_card_data(card_id)
        return data is not None and data.cardType == CardType.BASIC_ENERGY

    def has_ability(self, pokemon: Optional[Pokemon]) -> bool:
        if pokemon is None:
            return False
        data = self.get_card_data(self.card_id(pokemon))
        return data is not None and bool(data.skills)

    def freezing_shroud_targets(self, mine: bool) -> List[Pokemon]:
        source = self.all_my_pokemon if mine else self.all_opp_pokemon
        return [
            pokemon for pokemon in source
            if self.has_ability(pokemon) and self.card_id(pokemon) != YUKIMENOKO
        ]

    def needs_touko_evolution(self) -> bool:
        return any(
            self.count_in_play(card_id) < DESIRED_COUNTS.get(card_id, 0)
            for card_id in (YUKIMENOKO, MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX)
        )

    def needs_water_energy(self) -> bool:
        starmie = self.find_pokemon(MEGA_STARMIE_EX)
        if starmie is not None and self.count_energy(starmie, BASIC_WATER_ENERGIE) == 0:
            return True
        mega_yuki = self.find_pokemon(MEGA_YUKIMENOKO_EX)
        if self.opponent_has_alakazam_line and mega_yuki is not None and self.count_energy(mega_yuki, BASIC_WATER_ENERGIE) == 0:
            return True
        hitodeman = self.find_pokemon(HITODEMAN)
        if hitodeman is not None and self.count_energy(hitodeman, BASIC_WATER_ENERGIE) == 0:
            return True
        return self.count_energy(self.active, BASIC_WATER_ENERGIE) == 0 and BASIC_WATER_ENERGIE not in self.hand_ids

    @property
    def should_reserve_water_for_starmie(self) -> bool:
        return (
            MEGA_STARMIE_EX in self.hand_ids
            or self.count_in_play(HITODEMAN) > 0
            or self.count_in_play(MEGA_STARMIE_EX) > 0
            or self.wants_hitodeman_for_starmie
            or self.wants_mega_starmie_for_hitodeman
        )

    @property
    def wants_hitodeman_for_starmie(self) -> bool:
        can_reach_mega_starmie = (
            MEGA_STARMIE_EX in self.hand_ids
            or MEGA_SIGNAL in self.hand_ids
            or HYPERBALL in self.hand_ids
        )
        return can_reach_mega_starmie and self.count_in_play(HITODEMAN) == 0

    @property
    def wants_mega_starmie_for_hitodeman(self) -> bool:
        return self.count_in_play(HITODEMAN) > 0 and self.count_in_play(MEGA_STARMIE_EX) == 0

    def bench_has_same_basic(self, card_id: int) -> bool:
        return card_id in {HITODEMAN, YUKIWARASHI} and any(self.card_id(pokemon) == card_id for pokemon in self.bench)

    def active_basic_is_decoy(self, target: Optional[Pokemon]) -> bool:
        if target is None or target is not self.active:
            return False
        return self.bench_has_same_basic(self.card_id(target))

    def bench_basic_should_be_built(self, target: Optional[Pokemon]) -> bool:
        if target is None or target is self.active or self.active is None:
            return False
        target_id = self.card_id(target)
        return target_id in {HITODEMAN, YUKIWARASHI} and self.card_id(self.active) == target_id

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

    def total_basic_energy_cards(self, mine: bool = True) -> int:
        source = self.all_my_pokemon if mine else self.all_opp_pokemon
        total = 0
        for pokemon in source:
            for card in self.attached_energy_cards(pokemon):
                data = self.get_card_data(card.id)
                if data is not None and data.cardType == CardType.BASIC_ENERGY:
                    total += 1
        return total

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
    def active_will_be_knocked_out(self) -> bool:
        return self.active is not None and self.my_active_remaining_hp <= self.opp_active_max_damage

    @property
    def active_knockout_loses_game(self) -> bool:
        return self.active_will_be_knocked_out and self.my_active_prize_value >= self.opp_remaining_prizes

    @property
    def should_prioritize_active_attack_now(self) -> bool:
        if self.active is None or not self.my_active_can_attack():
            return False
        if self.card_id(self.active) not in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return False
        return self.active_will_be_knocked_out

    @property
    def has_ready_mashimashira(self) -> bool:
        pokemon = self.find_pokemon(MUNKIDORI)
        return pokemon is not None and self.count_energy(pokemon, BASIC_UNLICHT_ENERGIE) > 0

    @property
    def wants_mashimashira_dark_energy(self) -> bool:
        pokemon = self.find_pokemon(MUNKIDORI)
        if pokemon is not None:
            return self.count_energy(pokemon, BASIC_UNLICHT_ENERGIE) == 0
        return MUNKIDORI in self.hand_ids and BASIC_UNLICHT_ENERGIE in self.hand_ids

    @property
    def can_enable_perilous_ruins(self) -> bool:
        if self.has_ready_mashimashira:
            return True
        pokemon = self.find_pokemon(MUNKIDORI)
        if pokemon is not None:
            return BASIC_UNLICHT_ENERGIE in self.hand_ids or self.count_energy(pokemon, BASIC_UNLICHT_ENERGIE) > 0
        return MUNKIDORI in self.hand_ids and BASIC_UNLICHT_ENERGIE in self.hand_ids

    @property
    def opponent_has_alakazam_line(self) -> bool:
        return any(self.card_id(pokemon) in ALAKAZAM_LINE for pokemon in self.all_opp_pokemon)

    @property
    def opponent_has_crustle_wall(self) -> bool:
        return any(self.card_id(pokemon) == 345 for pokemon in self.all_opp_pokemon)

    @property
    def opponent_active_is_crustle_wall(self) -> bool:
        return self.opp_active is not None and self.card_id(self.opp_active) == 345

    @property
    def opponent_has_crustle_preevo(self) -> bool:
        return any(self.card_id(pokemon) in CRUSTLE_PRE_EVOS for pokemon in self.all_opp_pokemon)

    @property
    def opponent_has_shaymin_bench_shield(self) -> bool:
        return any(self.card_id(pokemon) == SHAYMIN for pokemon in self.all_opp_pokemon)

    def is_ex_pokemon(self, pokemon: Optional[Pokemon]) -> bool:
        if pokemon is None:
            return False
        data = self.get_card_data(self.card_id(pokemon))
        return data is not None and (data.ex or data.megaEx)

    def is_rule_box_pokemon_in_play(self, pokemon: Optional[Pokemon]) -> bool:
        if pokemon is None:
            return False
        data = self.get_card_data(self.card_id(pokemon))
        return data is not None and (data.ex or data.megaEx or data.tera)

    def crustle_blocks_ex_attack(self, attacker: Optional[Pokemon], defender: Optional[Pokemon]) -> bool:
        return defender is not None and self.card_id(defender) == 345 and self.is_ex_pokemon(attacker)

    def shaymin_blocks_bench_attack_damage(self, target: Optional[Pokemon]) -> bool:
        return (
            target is not None
            and target is not self.opp_active
            and self.opponent_has_shaymin_bench_shield
            and self.card_id(target) != SHAYMIN
            and not self.is_rule_box_pokemon_in_play(target)
        )

    @property
    def is_development_starved(self) -> bool:
        if len(self.all_my_pokemon) <= 1:
            return True
        has_attacker = any(
            self.card_id(pokemon) in {HITODEMAN, MEGA_STARMIE_EX, YVELTAL}
            for pokemon in self.all_my_pokemon
        )
        return not has_attacker or not self.my_active_can_attack()

    @property
    def has_no_backup_pokemon(self) -> bool:
        return self.active is not None and not self.bench

    @property
    def has_pre_attack_development_card(self) -> bool:
        return any(card_id in DEVELOPMENT_PLAY_CARDS for card_id in self.hand_ids)

    @property
    def has_damage_counters_to_move(self) -> bool:
        # Pokemon側ダメカン数は未公開。合法なDAMAGE_COUNTER選択の存在を根拠にする。
        return self.remain_damage_counter > 0

    @property
    def has_damaged_my_pokemon(self) -> bool:
        return any(self.current_hp(pokemon) < int(pokemon.maxHp) for pokemon in self.all_my_pokemon)

    @property
    def can_munkidori_shift_for_prize(self) -> bool:
        return any(self.current_hp(pokemon) <= 30 for pokemon in self.all_opp_pokemon)

    def my_active_can_attack(self) -> bool:
        return bool(self.legal_attacks(self.active))

    def can_take_prize(self, attacker: Optional[Pokemon], defender: Optional[Pokemon]) -> bool:
        return attacker is not None and defender is not None and self.best_attack_damage(attacker) >= self.current_hp(defender)

    def damage_target_value(self, target: Optional[Pokemon], damage: int) -> float:
        if target is None:
            return SCORE_NEG_INF
        if self.option_target_is_mine(target):
            return -99999.0
        if self.shaymin_blocks_bench_attack_damage(target):
            return -12000.0

        hp = self.current_hp(target)
        prize = self.calculate_prize_value(target)
        score = self.calculate_prize_value(target) * 800.0
        if target is self.opp_active:
            score += 300.0
        else:
            score += 700.0
        if self.card_id(target) in ALL_HYPO_ENEMIES:
            score += 1000.0
        if self.card_id(target) in SETUP_THREAT_PRE_EVOS:
            score += 2600.0
        elif self.card_id(target) in SETUP_THREAT_FINALS:
            score += 1800.0
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

    def can_boss_around_crustle_for_prize(self) -> bool:
        if self.active is None or not self.opponent_active_is_crustle_wall:
            return False
        if not self.my_active_can_attack():
            return False
        return any(self.can_take_prize(self.active, pokemon) for pokemon in self.opp_bench)

    def can_boss_delay_active_sweeper(self) -> bool:
        if self.opp_active is None or not self.opp_bench:
            return False
        if self.card_id(self.opp_active) != MEGA_LUCARIO_EX:
            return False
        if self.opp_active_max_damage < 180:
            return False
        has_my_mega = any(self.card_id(pokemon) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} for pokemon in self.all_my_pokemon)
        return self.is_development_starved or not has_my_mega or self.my_active_remaining_hp <= self.opp_active_max_damage

    def setup_threat_value(self, target: Optional[Pokemon]) -> float:
        if target is None:
            return 0.0
        card_id = self.card_id(target)
        score = 0.0
        if card_id in DREEPY_PRE_EVOS:
            score += 7600.0
            if card_id == 120:
                score += 1800.0
        elif card_id in LUCARIO_PRE_EVOS:
            score += 7200.0
        elif card_id in ALAKAZAM_PRE_EVOS:
            score += 6200.0
            if card_id == 742:
                score += 1400.0
        elif card_id in DURALUDON_PRE_EVOS:
            score += 5800.0
        elif card_id in CRUSTLE_PRE_EVOS:
            score += 5600.0
        elif card_id in SETUP_THREAT_FINALS:
            score += 4200.0

        if card_id == SHAYMIN:
            score += 2600.0
        if self.can_take_prize(self.active, target):
            score += self.calculate_prize_value(target) * 3600.0
        elif self.best_attack_damage(self.active) >= max(0, self.current_hp(target) - 50):
            score += 1800.0
        score += max(0, 140 - self.current_hp(target)) * 8.0
        return score

    def can_boss_disrupt_setup(self) -> bool:
        if self.active is None or not self.opp_bench:
            return False
        if not self.my_active_can_attack() and not self.active_will_be_knocked_out:
            return False
        return any(self.setup_threat_value(pokemon) >= 6200.0 for pokemon in self.opp_bench)

    def boss_disrupt_setup_target_value(self, target: Optional[Pokemon]) -> float:
        if target is None or self.option_target_is_mine(target) or target is self.opp_active:
            return SCORE_NEG_INF
        score = self.setup_threat_value(target)
        if score <= 0.0:
            score = 800.0
        target_damage = self.calculate_max_damage(target, next_turn=True)
        score -= target_damage * 6.0
        score += self.effective_retreat_cost(target) * 450.0
        score -= self.count_energy(target) * 350.0
        return score

    def boss_delay_target_value(self, target: Optional[Pokemon]) -> float:
        if target is None or self.option_target_is_mine(target) or target is self.opp_active:
            return SCORE_NEG_INF
        target_damage = self.calculate_max_damage(target, next_turn=True)
        score = 7600.0
        score -= target_damage * 18.0
        score += self.effective_retreat_cost(target) * 850.0
        score -= self.count_energy(target) * 550.0
        if self.can_take_prize(target, self.active):
            score -= self.my_active_prize_value * 1800.0
        if self.card_id(target) == RIOLU:
            score += 900.0
        return score

    def boss_around_crustle_target_value(self, target: Optional[Pokemon]) -> float:
        if target is None or self.option_target_is_mine(target) or target is self.opp_active:
            return SCORE_NEG_INF
        if not self.opponent_active_is_crustle_wall:
            return SCORE_NEG_INF
        score = 4200.0
        if self.can_take_prize(self.active, target):
            score += self.calculate_prize_value(target) * 4200.0
        score += max(0, 180 - self.current_hp(target)) * 10.0
        score -= self.calculate_max_damage(target, next_turn=True) * 8.0
        score += self.effective_retreat_cost(target) * 300.0
        return score

    def has_priority_setup_before_energy(self) -> bool:
        for _, option in self.iter_options():
            option_type = option.type
            card_id = self.option_card_id(option)
            if option_type == OptionType.EVOLVE:
                if card_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                    return True
                if card_id == YUKIMENOKO and MEGA_YUKIMENOKO_EX not in self.hand_ids:
                    return True
            if option_type == OptionType.PLAY and card_id is not None:
                if self.is_pokemon_card(card_id) and self.is_poffin_target(card_id):
                    return True
                if card_id in {POFIN, POKE_PAD, HYPERBALL, MEGA_SIGNAL, POKEGEAR, HAND_TRIMMER}:
                    return True
                if card_id in {TOUKO, AKAMATSU} and not self.obs.current.supporterPlayed:
                    return True
        return False

    def option_area(self, option: Any):
        if option.inPlayArea is not None:
            return option.inPlayArea
        return option.area if option.area is not None else option.inPlayArea

    def option_index(self, option: Any) -> int:
        if option.inPlayArea is not None:
            return int(option.inPlayIndex or 0)
        if option.area is not None:
            return int(option.index or 0)
        return int(option.inPlayIndex or 0)

    def option_points_to_me(self, option: Any) -> bool:
        return option.playerIndex is None or option.playerIndex == self.your_index

    def option_target_is_mine(self, target: Pokemon) -> bool:
        return any(target is pokemon for pokemon in self.all_my_pokemon)

    def pokemon_is_mine(self, pokemon: Pokemon) -> bool:
        return any(pokemon is mine for mine in self.all_my_pokemon)

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
    if card_id in {HERO_CAPE, WALLY_COMPASSION}:
        if any(board.card_id(pokemon) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} for pokemon in board.all_my_pokemon):
            return -2400.0
    if card_id == MEGA_SIGNAL and board.needs_mega_signal_target():
        return -2200.0
    if card_id == DENGEROUS_RUINE:
        if board.stadium_id == DENGEROUS_RUINE:
            return 2400.0
        if not board.can_enable_perilous_ruins:
            return -1600.0 if board.has_foreign_stadium else 900.0
        if board.has_foreign_stadium:
            return -9000.0
        if is_early_game(board) or board.has_ready_mashimashira:
            return -6500.0
        return 200.0
    if card_id == BASIC_UNLICHT_ENERGIE and board.wants_mashimashira_dark_energy:
        return -9000.0
    if card_id == YVELTAL:
        if is_early_game(board) and not is_board_fully_set_up(board):
            return -1800.0
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
        if board.can_boss_around_crustle_for_prize():
            return 9800.0
        if board.can_boss_delay_active_sweeper():
            return 7600.0
        if board.can_boss_disrupt_setup():
            return 7200.0
        if board.is_development_starved:
            return -99999.0
        if not board.my_active_can_attack():
            return -3000.0
        score = 500.0 if board.opp_bench else 0.0
        for pokemon in board.opp_bench:
            card_id = board.card_id(pokemon)
            if card_id in CRUSTLE_PRE_EVOS and board.can_take_prize(board.active, pokemon):
                score += 7000.0
            elif card_id in DREEPY_PRE_EVOS and board.can_take_prize(board.active, pokemon):
                score += 6200.0
            elif card_id in SETUP_THREAT_PRE_EVOS:
                score += board.setup_threat_value(pokemon) * 0.45
            elif card_id == DRAGAPULT_EX and board.can_take_prize(board.active, pokemon):
                score += 8000.0
            elif card_id == SHAYMIN:
                score += 2200.0
        if board.active is not None and board.my_active_remaining_hp <= board.opp_active_max_damage:
            score += board.my_active_prize_value * 1200.0
        return score


class PerilousRuinsStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if board.stadium_id == DENGEROUS_RUINE:
            return 0.0
        if not board.can_enable_perilous_ruins:
            if board.has_foreign_stadium:
                return 900.0 if not board.has_no_backup_pokemon else -1800.0
            return -6200.0
        score = 3600.0
        if board.has_foreign_stadium:
            score += 2800.0
        if is_early_game(board):
            score += 900.0
        if board.has_ready_mashimashira:
            score += 1200.0
        elif board.wants_mashimashira_dark_energy:
            score -= 800.0
        if board.has_damage_counters_to_move:
            score += 700.0
        if board.is_development_starved and not board.has_ready_mashimashira:
            score -= 600.0
        if board.has_no_backup_pokemon:
            score -= 2200.0
        return score


class DarknessEnergyStrategy(DefaultStrategy):
    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        if board.card_id(target) == MUNKIDORI:
            return 8000.0 if board.wants_mashimashira_dark_energy else 3500.0
        if board.card_id(target) == YVELTAL:
            score = 1800.0
            if board.opp_active is not None and (
                board.card_id(board.opp_active) in SETUP_THREAT_PRE_EVOS | SETUP_THREAT_FINALS
                or board.calculate_max_damage(board.opp_active, next_turn=True) >= 180
            ):
                score += 3600.0
            if board.opponent_active_is_crustle_wall:
                score += 3000.0
            if board.active is target:
                score += 1200.0
            return score
        if board.wants_mashimashira_dark_energy:
            return -2500.0
        return 100.0


class WaterEnergyStrategy(DefaultStrategy):
    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        target_id = board.card_id(target)
        primary_line = board.primary_water_line()
        if primary_line is not None and not board.pokemon_matches_primary_water_line(target):
            attack = board.high_impact_attack(target)
            can_finish_now = (
                board.opp_active is not None
                and target is board.active
                and attack is not None
                and board.attack_energy_shortfall(target, attack, ["WATER"]) == 0
                and board.effective_attack_damage(target, attack) >= board.current_hp(board.opp_active)
            )
            if can_finish_now:
                return 3600.0
            if target_id == YUKIMENOKO and board.opponent_active_is_crustle_wall:
                return 2400.0
            return -6800.0
        if primary_line == "STARMIE" and target_id in {HITODEMAN, MEGA_STARMIE_EX}:
            return 7600.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 3600.0
        if primary_line == "YUKI" and target_id in {YUKIWARASHI, MEGA_YUKIMENOKO_EX}:
            return 7000.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 3400.0
        if board.opponent_active_is_crustle_wall and board.card_id(target) == YUKIMENOKO:
            return 5200.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 2400.0
        if board.card_id(target) in {YUKIWARASHI, YUKIMENOKO} and board.should_reserve_water_for_starmie:
            return -7600.0
        if board.card_id(target) == YUKIWARASHI and MEGA_YUKIMENOKO_EX in board.hand_ids:
            return -2800.0
        if board.active_basic_is_decoy(target):
            return -2200.0
        if board.bench_basic_should_be_built(target):
            return 6200.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 2400.0
        if board.opponent_has_alakazam_line and board.card_id(target) == MEGA_YUKIMENOKO_EX:
            return 5600.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 2600.0
        if board.card_id(target) == MEGA_STARMIE_EX:
            return 5200.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 2600.0
        if board.card_id(target) == HITODEMAN:
            return 4600.0 if board.count_energy(target, BASIC_WATER_ENERGIE) == 0 else 1800.0
        if board.card_id(target) == MEGA_YUKIMENOKO_EX:
            return 2200.0
        if board.card_id(target) == YUKIMENOKO:
            return -3600.0
        if board.card_id(target) == MUNKIDORI:
            return -1200.0
        if board.card_id(target) == YVELTAL:
            return -4200.0
        return -3200.0


class BenchPokemonStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        return 2100.0


class StaryuStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        score = 2800.0 if board.count_in_play(HITODEMAN) == 0 else 1800.0
        if board.has_no_backup_pokemon:
            score += 2600.0
        if MEGA_STARMIE_EX in board.hand_ids or MEGA_SIGNAL in board.hand_ids or HYPERBALL in board.hand_ids:
            score += 3600.0
        if board.count_in_play(MEGA_STARMIE_EX) == 0:
            score += 1200.0
        if board.opponent_active_is_crustle_wall:
            score += 900.0
        return score


class MegaStarmieStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        score = 2600.0
        if board.count_in_play(HITODEMAN) > 0:
            score += 3600.0
        if board.count_in_play(MEGA_STARMIE_EX) == 0:
            score += 1800.0
        if board.opponent_active_is_crustle_wall:
            score -= 5200.0
        return score


class SnoruntStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        if board.opponent_has_crustle_wall:
            return 3400.0 if board.count_in_play(YUKIWARASHI) == 0 else 2600.0
        if board.opponent_has_alakazam_line:
            return 3000.0 if board.count_in_play(YUKIWARASHI) == 0 else 2400.0
        return 1100.0


class MunkidoriStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        if board.select_context == SelectContext.SETUP_ACTIVE_POKEMON:
            return -2200.0
        if board.select_context == SelectContext.SETUP_BENCH_POKEMON:
            return 900.0
        score = 1400.0 if board.needs_dark_energy() else 700.0
        if board.count_in_play(MUNKIDORI) == 0:
            score += 1600.0
        if board.has_damaged_my_pokemon:
            score += 2200.0
        if BASIC_UNLICHT_ENERGIE in board.hand_ids:
            score += 1400.0
        if board.count_in_play(YUKIMENOKO) > 0:
            score += 900.0
        return score


class YveltalStrategy(DefaultStrategy):
    def evaluate_placement(self, board: BoardState) -> float:
        score = 0.0
        if board.select_context == SelectContext.SETUP_ACTIVE_POKEMON:
            score += 1800.0
        score += 900.0 if is_early_game(board) else 200.0
        if board.opp_active is not None and board.card_id(board.opp_active) in SETUP_THREAT_FINALS:
            score += 1800.0
        if board.opponent_active_is_crustle_wall:
            score += 1800.0
        if any(board.setup_threat_value(pokemon) >= 6200.0 for pokemon in board.opp_bench):
            score += 1200.0
        return score

    def evaluate_trash(self, board: BoardState) -> float:
        if board.opponent_active_is_crustle_wall or any(board.setup_threat_value(pokemon) >= 6200.0 for pokemon in board.opp_bench):
            return -2400.0
        if is_early_game(board) and not is_board_fully_set_up(board):
            return -1800.0
        return 3000.0


class HandTrimmerStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        opp_hand = int(board.opp.handCount or 0)
        my_hand = len(board.hand_ids)
        if opp_hand <= 5:
            return -1600.0
        score = 1800.0 + (opp_hand - 5) * 1400.0
        if board.opponent_has_alakazam_line:
            score += 1600.0
        if board.opp_active is not None and board.card_id(board.opp_active) in SETUP_THREAT_FINALS:
            score += 900.0
        refrain_pressure = board.resentful_refrain_pressure_value()
        if refrain_pressure > 0.0:
            score -= min(9000.0, refrain_pressure)
            score -= board.hand_trimmer_resentful_refrain_loss() * 18.0
            if board.can_use_resentful_refrain_now():
                score -= 2200.0
        if my_hand > 5:
            score -= min(2800.0, (my_hand - 5) * 700.0)
        if board.is_development_starved and my_hand <= 6:
            score -= 1200.0
        return score

    def evaluate_trash(self, board: BoardState) -> float:
        if int(board.opp.handCount or 0) >= 7:
            return -2600.0
        if board.opponent_has_alakazam_line and int(board.opp.handCount or 0) >= 6:
            return -2200.0
        return 600.0


class PokePadStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if is_board_fully_set_up(board):
            return 0.0
        if board.has_no_backup_pokemon:
            return 4200.0
        if not board.deck_is_visible:
            return 2500.0
        return 2500.0 if board.deck_has_card_matching(board.is_poke_pad_target) else -99999.0


class PokegearStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if not board.deck_is_visible:
            return 1800.0
        if not board.deck_has_card_matching(board.is_supporter_card):
            return -99999.0
        if board.is_development_starved or board.has_no_backup_pokemon:
            return 2600.0
        if board.is_wally_compassion_live():
            return 1800.0
        return 1500.0 if not board.obs.current.supporterPlayed else 300.0


class PofinStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if is_board_fully_set_up(board):
            return 0.0
        if board.has_no_backup_pokemon:
            return 5200.0
        if not board.deck_is_visible:
            return 2600.0
        return 2600.0 if board.deck_has_card_matching(board.is_poffin_target) else -99999.0


class TankerStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if not board.needs_tanker_recovery():
            return 0.0
        if board.needs_water_energy() and board.count_in_discard(BASIC_WATER_ENERGIE):
            return 5200.0
        if board.needs_dark_energy() and board.count_in_discard(BASIC_UNLICHT_ENERGIE):
            return 3600.0
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
        if len(scores) < 2 or scores[1] <= -90000.0:
            return -99999.0
        return 5200.0 if board.has_no_backup_pokemon else 2800.0


class BallonStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        active_cost = board.effective_retreat_cost(board.active)
        if active_cost >= 2:
            return 1800.0
        if active_cost == 1 and board.my_active_remaining_hp <= board.opp_active_max_damage:
            return 1200.0
        return 100.0


class HeroCapeStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        candidates = [
            pokemon for pokemon in board.all_my_pokemon
            if board.card_id(pokemon) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}
            and not pokemon.tools
        ]
        if not candidates:
            return 0.0
        active_bonus = 1600.0 if board.active in candidates else 0.0
        danger_bonus = 1200.0 if board.my_active_remaining_hp <= board.opp_active_max_damage else 0.0
        return 2400.0 + active_bonus + danger_bonus

    def evaluate_attach(self, board: BoardState, target: Pokemon) -> float:
        if board.card_id(target) not in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return -4000.0
        if target.tools:
            return -99999.0
        score = 5200.0
        if target is board.active:
            score += 1800.0
        if board.current_hp(target) <= board.opp_active_max_damage + 100:
            score += 1400.0
        return score


class MegaSignalStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if not board.needs_mega_signal_target():
            return 0.0
        if not board.deck_is_visible:
            return 2600.0
        return 3600.0 if board.deck_has_card_matching(board.is_mega_signal_target) else -99999.0


class WallyCompassionStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        return board.wally_compassion_value()


class ZeiyuStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        duplicate_zeiyu = board.hand_ids.count(CARMINE) >= 2
        board_is_thin = len(board.bench) < 2 or board.is_development_starved
        if duplicate_zeiyu and board_is_thin:
            return 3600.0 if board.has_no_backup_pokemon else 2600.0
        if any(card_id in IMPORTANT_CARDS for card_id in board.hand_ids):
            if board.is_development_starved and len(board.hand_ids) <= 3:
                return 900.0
            if duplicate_zeiyu and not is_board_fully_set_up(board):
                return 1200.0
            return -4000.0
        if HYPERBALL in board.hand_ids:
            return 1200.0 if duplicate_zeiyu and board_is_thin else 0.0
        if board.is_development_starved:
            return 2400.0
        return 2000.0 if len(board.hand_ids) <= 3 else 300.0


class LillieDeterminationStrategy(DefaultStrategy):
    def evaluate_play(self, board: BoardState) -> float:
        if board.has_no_backup_pokemon:
            return 3600.0
        penalty = 0.0
        if MEGA_STARMIE_EX in board.hand_ids:
            penalty += 1200.0
        if BEFEHL_VON_BOSS in board.hand_ids and board.opp_bench:
            penalty += 800.0
        if board.my_remaining_prizes == 6:
            return 2500.0 - penalty
        if board.is_development_starved:
            return 2200.0 - penalty
        return (1500.0 if len(board.hand_ids) <= 3 else 400.0) - penalty


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
        score += sum(self.board.high_impact_attack_progress(pokemon) for pokemon in self.board.all_my_pokemon) * 0.25
        return score


class AbilityResolver:
    def __init__(self, board: BoardState):
        self.board = board

    def evaluate(self) -> float:
        score = 0.0
        mashimashira = self.board.find_pokemon(MUNKIDORI)
        if mashimashira is not None and self.board.count_energy(mashimashira, BASIC_UNLICHT_ENERGIE) > 0:
            score += 300.0 if self.board.has_damage_counters_to_move else 100.0
        yuki_count = self.board.count_in_play(YUKIMENOKO)
        if yuki_count:
            opp_targets = self.board.freezing_shroud_targets(mine=False)
            my_targets = self.board.freezing_shroud_targets(mine=True)
            score += yuki_count * (len(opp_targets) * 620.0 - len(my_targets) * 180.0)
            for pokemon in opp_targets:
                hp_after = self.board.current_hp(pokemon) - 10 * yuki_count
                if hp_after <= 0:
                    score += self.board.calculate_prize_value(pokemon) * 4200.0
                elif hp_after <= self.board.best_attack_damage(self.board.active):
                    score += 1800.0
                if self.board.card_id(pokemon) in ALAKAZAM_LINE | LUCARIO_LINE | DREEPY_LINE:
                    score += 900.0
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
            if self.board.card_id(target) in SETUP_THREAT_PRE_EVOS:
                score += 2200.0
            elif self.board.card_id(target) in SETUP_THREAT_FINALS:
                score += 1200.0
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
            BASIC_UNLICHT_ENERGIE: DarknessEnergyStrategy(),
            BASIC_WATER_ENERGIE: WaterEnergyStrategy(),
            HITODEMAN: StaryuStrategy(),
            MEGA_STARMIE_EX: MegaStarmieStrategy(),
            YUKIWARASHI: SnoruntStrategy(),
            YUKIMENOKO: BenchPokemonStrategy(),
            MEGA_YUKIMENOKO_EX: BenchPokemonStrategy(),
            MUNKIDORI: MunkidoriStrategy(),
            YVELTAL: YveltalStrategy(),
            HAND_TRIMMER: HandTrimmerStrategy(),
            POKE_PAD: PokePadStrategy(),
            POKEGEAR: PokegearStrategy(),
            POFIN: PofinStrategy(),
            TANKER: TankerStrategy(),
            HYPERBALL: HyperballStrategy(),
            BALLON: BallonStrategy(),
            HERO_CAPE: HeroCapeStrategy(),
            MEGA_SIGNAL: MegaSignalStrategy(),
            CARMINE: ZeiyuStrategy(),
            LILLIE_DETERMINATION: LillieDeterminationStrategy(),
            TOUKO: ToukoStrategy(),
            AKAMATSU: AkamatsuStrategy(),
            WALLY_COMPASSION: WallyCompassionStrategy(),
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
        if self.board.card_id(target) in SETUP_THREAT_PRE_EVOS:
            score += 3600.0
        elif self.board.card_id(target) in SETUP_THREAT_FINALS:
            score += 2200.0
        if self.board.card_id(target) in CRUSTLE_PRE_EVOS:
            score += 6500.0
        if self.board.card_id(target) == 345:
            score += 2500.0
        if self.board.card_id(target) in DREEPY_PRE_EVOS:
            score += 5200.0
        if self.board.card_id(target) == DRAGAPULT_EX:
            score += 6200.0
        if self.board.card_id(target) == SHAYMIN:
            score += 2600.0
        if self.board.card_id(target) in ALAKAZAM_LINE:
            score += 1200.0
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
        pair_bonus = self.starmie_pair_bonus(card_id)

        if effect_id == POFIN:
            if not self.board.is_poffin_target(card_id):
                return -99999.0
            rescue = 3000.0 if self.board.has_no_backup_pokemon else 0.0
            alakazam_bonus = 2800.0 if self.board.opponent_has_alakazam_line and card_id == YUKIWARASHI else 0.0
            starmie_penalty = 1800.0 if self.board.opponent_has_alakazam_line and card_id == HITODEMAN and self.board.count_in_play(YUKIWARASHI) == 0 else 0.0
            return rescue + need + pair_bonus + alakazam_bonus - starmie_penalty + self.evaluator.evaluate_pokemon_placement(card_id)
        if effect_id == POKE_PAD:
            if not self.board.is_poke_pad_target(card_id):
                return -99999.0
            rescue = 2600.0 if self.board.has_no_backup_pokemon and self.board.is_poffin_target(card_id) else 0.0
            return rescue + need + pair_bonus + self.evaluator.evaluate_pokemon_placement(card_id)
        if effect_id == POKEGEAR:
            if not self.board.is_supporter_card(card_id):
                return -99999.0
            if card_id == WALLY_COMPASSION:
                value = self.board.wally_compassion_value()
                return max(1200.0, value) if value > 0.0 else 500.0
            if card_id == LILLIE_DETERMINATION:
                return 4800.0 if self.board.is_development_starved else 2200.0
            if card_id == TOUKO:
                return 4200.0 if self.board.needs_touko_evolution() or self.board.needs_water_energy() else 1200.0
            if card_id == AKAMATSU:
                return 3800.0 if self.board.needs_water_energy() or self.board.needs_dark_energy() else 1000.0
            if card_id == BEFEHL_VON_BOSS:
                if self.board.can_win_by_killing_bench_pokemon():
                    return 4200.0
                if self.board.can_boss_around_crustle_for_prize():
                    return 3600.0
                if self.board.can_boss_delay_active_sweeper():
                    return 3400.0
                return 1800.0
            if card_id == CARMINE:
                return 1200.0 if self.board.is_development_starved else 300.0
            return self.evaluator.evaluate_card_play(card_id)
        if effect_id == HYPERBALL:
            if not self.board.is_pokemon_card(card_id):
                return -99999.0
            primary_line = self.board.primary_water_line()
            if self.board.opponent_active_is_crustle_wall:
                if card_id == YUKIMENOKO:
                    return need + 7600.0
                if card_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                    return need + 900.0
            if self.board.has_no_backup_pokemon:
                active_id = self.board.card_id(self.board.active) if self.board.active is not None else None
                if card_id == MEGA_YUKIMENOKO_EX and active_id == YUKIWARASHI:
                    return 10200.0 + need + self.evaluator.evaluate_pokemon_placement(card_id)
                if card_id == MEGA_STARMIE_EX and active_id == HITODEMAN:
                    return 10000.0 + need + self.evaluator.evaluate_pokemon_placement(card_id)
                if card_id == YUKIMENOKO:
                    return -500.0
                if card_id in {HITODEMAN, MUNKIDORI, YUKIWARASHI} or self.board.is_poffin_target(card_id):
                    return 8000.0 + need + pair_bonus + self.evaluator.evaluate_pokemon_placement(card_id)
                return 500.0
            alakazam_bonus = 4600.0 if self.board.opponent_has_alakazam_line and card_id == MEGA_YUKIMENOKO_EX else 0.0
            primary_bonus = 0.0
            if primary_line == "STARMIE":
                primary_bonus = 2400.0 if card_id in {HITODEMAN, MEGA_STARMIE_EX} else -1200.0
            elif primary_line == "YUKI":
                primary_bonus = 2400.0 if card_id in {YUKIWARASHI, MEGA_YUKIMENOKO_EX} else -1200.0
            return need + pair_bonus + alakazam_bonus + primary_bonus + self.evaluator.evaluate_pokemon_placement(card_id)
        if effect_id == MEGA_SIGNAL:
            if not self.board.is_mega_signal_target(card_id):
                return -99999.0
            primary_line = self.board.primary_water_line()
            if primary_line == "STARMIE":
                if card_id == MEGA_STARMIE_EX:
                    return need + pair_bonus + 9800.0
                if card_id == MEGA_YUKIMENOKO_EX and not self.board.opponent_has_alakazam_line:
                    return need + 400.0
            elif primary_line == "YUKI":
                if card_id == MEGA_YUKIMENOKO_EX:
                    return need + 9400.0
                if card_id == MEGA_STARMIE_EX:
                    return need + pair_bonus + 1200.0
            if card_id == MEGA_STARMIE_EX and self.board.wants_mega_starmie_for_hitodeman:
                return need + pair_bonus + 8200.0
            if card_id == MEGA_YUKIMENOKO_EX:
                if self.board.opponent_has_alakazam_line:
                    return need + 8800.0
                if self.board.count_in_play(YUKIWARASHI):
                    return need + 5600.0
            return need + pair_bonus + 1200.0
        if effect_id == TANKER:
            if card_id == BASIC_WATER_ENERGIE and self.board.needs_water_energy():
                return 5600.0
            if card_id == BASIC_UNLICHT_ENERGIE and self.board.needs_dark_energy():
                return 3600.0
            if card_id in (HITODEMAN, YUKIWARASHI, MUNKIDORI):
                return need + self.evaluator.evaluate_pokemon_placement(card_id)
            if self.board.is_pokemon_card(card_id) or self.board.is_basic_energy_card(card_id):
                return 500.0
            return -99999.0
        if effect_id == TOUKO:
            primary_line = self.board.primary_water_line()
            if self.board.opponent_active_is_crustle_wall and card_id == YUKIMENOKO:
                return need + 8200.0
            if self.board.opponent_active_is_crustle_wall and card_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                return need + 1200.0
            if self.board.opponent_has_alakazam_line and card_id == MEGA_YUKIMENOKO_EX:
                return need + 9800.0
            if card_id == MEGA_STARMIE_EX:
                alakazam_penalty = 2400.0 if self.board.opponent_has_alakazam_line and self.board.count_in_play(YUKIWARASHI) > 0 else 0.0
                primary_bonus = 1800.0 if primary_line == "STARMIE" else (-1200.0 if primary_line == "YUKI" else 0.0)
                return need + pair_bonus + 4300.0 + primary_bonus - alakazam_penalty
            if card_id == MEGA_YUKIMENOKO_EX:
                primary_bonus = 1800.0 if primary_line == "YUKI" else (-1200.0 if primary_line == "STARMIE" and not self.board.opponent_has_alakazam_line else 0.0)
                return need + (5200.0 if self.board.opponent_has_alakazam_line else 4100.0) + primary_bonus
            if card_id == YUKIMENOKO:
                return need + (2600.0 if self.board.opponent_has_alakazam_line else 1800.0)
            if card_id == BASIC_UNLICHT_ENERGIE and self.board.needs_dark_energy():
                return 2800.0
            if card_id == BASIC_WATER_ENERGIE:
                return 2400.0 if self.board.needs_water_energy() else 900.0
            return -99999.0
        if effect_id == AKAMATSU:
            if card_id == BASIC_WATER_ENERGIE and self.board.needs_water_energy():
                return 4600.0
            if card_id == BASIC_UNLICHT_ENERGIE and not self.board.has_ready_mashimashira:
                return 3400.0 if self.board.needs_dark_energy() else 2200.0
            if card_id == BASIC_WATER_ENERGIE:
                return 1800.0
            if self.board.is_basic_energy_card(card_id):
                return 400.0
            return -99999.0

        return self.score_card(card_id)

    def starmie_pair_bonus(self, card_id: int) -> float:
        if card_id == HITODEMAN and self.board.wants_hitodeman_for_starmie:
            return 5200.0
        if card_id == MEGA_STARMIE_EX and self.board.wants_mega_starmie_for_hitodeman:
            return 5200.0
        return 0.0

    def score_card(self, card_id: int) -> float:
        need = max(0, DESIRED_COUNTS.get(card_id, 0) - self.board.count_in_play(card_id)) * 500.0
        need += self.starmie_pair_bonus(card_id)
        data = self.board.get_card_data(card_id)
        if data is None:
            return need
        if data.attacks:
            return need + self.evaluator.evaluate_pokemon_placement(card_id)
        if card_id in {BASIC_WATER_ENERGIE, BASIC_UNLICHT_ENERGIE}:
            return need + 400.0
        return need + self.evaluator.evaluate_card_play(card_id)


class TargetResolver:
    def __init__(self, board: BoardState, evaluator: MasterEvaluator):
        self.board = board
        self.evaluator = evaluator

    def score_target(self, target: Pokemon, mine: bool) -> float:
        if mine:
            card_id = self.board.card_id(target)
            score = self.board.calculate_max_damage(target, next_turn=True) + self.board.current_hp(target) * 0.1
            if card_id == MUNKIDORI:
                score -= 4200.0
            elif card_id == HITODEMAN:
                score += 900.0
            elif card_id == YUKIWARASHI:
                score += 600.0
            elif card_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                score += 1800.0
            return score
        if (self.board.effect_card_id or self.board.context_card_id) == BEFEHL_VON_BOSS:
            if self.board.can_boss_around_crustle_for_prize():
                return self.board.boss_around_crustle_target_value(target)
            if self.board.can_boss_delay_active_sweeper():
                return self.board.boss_delay_target_value(target)
            if self.board.can_boss_disrupt_setup():
                return self.board.boss_disrupt_setup_target_value(target)
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

    def _development_option_value(self, option: Any) -> float:
        if option is self.option or option.attackId is not None:
            return 0.0
        option_type = option.type
        card_id = self.board.option_card_id(option)
        target = self.board.get_option_target(option)

        if option_type == OptionType.PLAY:
            if card_id is None:
                return 2200.0
            if self.board.is_pokemon_card(card_id):
                return self.evaluator.evaluate_pokemon_placement(card_id)
            return self.evaluator.evaluate_card_play(card_id)

        if option_type == OptionType.EVOLVE:
            if card_id is None:
                return 0.0
            value = self.evaluator.evaluate_pokemon_placement(card_id) + 2200.0
            if card_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                value += 2200.0
            return value

        if option_type == OptionType.ATTACH or option.energyIndex is not None:
            if target is not None and card_id in {BASIC_WATER_ENERGIE, BASIC_UNLICHT_ENERGIE}:
                return self.evaluator.evaluate_energy_attach(card_id, target)
            return 0.0

        if option_type == OptionType.ABILITY:
            target_id = self.board.card_id(target) if target is not None else card_id
            if target_id == MUNKIDORI and self.board.has_ready_mashimashira and self.board.has_damage_counters_to_move:
                return 6200.0
            return 0.0

        return 0.0

    def _best_development_option_value(self) -> float:
        best = 0.0
        for _, option in self.board.iter_options():
            best = max(best, self._development_option_value(option))
        return best


class AttackAction(GameAction):
    def _best_pre_attack_option_value(self) -> float:
        return self._best_development_option_value()

    def evaluate(self) -> None:
        attack = self.board.get_attack(self.option.attackId)
        attacker = self.board.active
        defender = self.board.opp_active
        if attack is None or attacker is None or defender is None or not self.board.can_use_attack(attacker, attack):
            self.action_score = -99999.0
            return
        damage = self.board.effective_attack_damage(attacker, attack)
        self.card_score = self.evaluator.evaluate_target_priority(defender)
        self.action_score = 5000.0 + damage * 5.0
        attacker_id = self.board.card_id(attacker)
        can_knock_out = damage >= self.board.current_hp(defender)
        if self.board.crustle_blocks_ex_attack(attacker, defender):
            self.action_score -= 12000.0
        wins_now = can_knock_out and self.board.calculate_prize_value(defender) >= self.board.my_remaining_prizes
        pre_attack_value = self._best_pre_attack_option_value()
        if can_knock_out:
            self.action_score += self.board.calculate_prize_value(defender) * 5200.0
        urgent_active_attack = self.board.should_prioritize_active_attack_now and attacker_id in {
            MEGA_STARMIE_EX,
            MEGA_YUKIMENOKO_EX,
        }
        if urgent_active_attack:
            self.action_score += 7600.0
            if self.board.active_knockout_loses_game:
                self.action_score += 9000.0
        if (
            attacker_id in {HITODEMAN, YUKIWARASHI, MUNKIDORI}
            and not can_knock_out
            and self.board.has_pre_attack_development_card
        ):
            self.action_score -= 5200.0
        if not wins_now and not can_knock_out and not urgent_active_attack and pre_attack_value >= 1000.0:
            self.action_score -= min(18000.0, 4200.0 + pre_attack_value * 1.8)
        if self.board.card_id(attacker) == MEGA_YUKIMENOKO_EX and self.board.opponent_has_alakazam_line:
            self.action_score += 2200.0
        if attacker_id == MEGA_YUKIMENOKO_EX and attack.attackId == RESENTFUL_REFRAIN:
            if can_knock_out:
                self.action_score += 7200.0
            elif damage >= 250:
                self.action_score += 2400.0
        if attacker_id == YUKIMENOKO and defender is not None:
            if damage >= self.board.current_hp(defender):
                self.action_score += 900.0
            else:
                self.action_score -= 1600.0
        if attacker_id == YVELTAL and attack.attackId == 997:
            defender_id = self.board.card_id(defender)
            if defender_id in SETUP_THREAT_PRE_EVOS | SETUP_THREAT_FINALS:
                self.action_score += 5600.0
            if self.board.opponent_active_is_crustle_wall:
                self.action_score += 5200.0
            if self.board.effective_retreat_cost(defender) >= 2 or self.board.count_energy(defender) < self.board.effective_retreat_cost(defender):
                self.action_score += 2400.0
        self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        attack = board.get_attack(self.option.attackId)
        defender = board.opp_active
        attacker = board.active
        if attack is None or defender is None or attacker is None:
            return board
        board.set_hp(defender, board.current_hp(defender) - board.effective_attack_damage(attacker, attack))
        if board.current_hp(defender) == 0:
            board.resolve_knockout(defender, target_is_mine=False)
        return board


class EvolveAction(GameAction):
    def evaluate(self) -> None:
        card_id = self.board.option_card_id(self.option)
        if card_id is None:
            self.action_score = -99999.0
            return
        target = self.board.get_option_target(self.option)
        target_is_active = target is not None and target is self.board.active
        same_basic_on_bench = (
            target is not None
            and any(
                pokemon is not target and self.board.card_id(pokemon) == self.board.card_id(target)
                for pokemon in self.board.bench
            )
        )

        if card_id == MEGA_STARMIE_EX:
            self.card_score = 3800.0
            if self.board.opponent_active_is_crustle_wall:
                self.card_score -= 7600.0
            if self.board.has_no_backup_pokemon and target_is_active:
                self.card_score += 1800.0
            primary_line = self.board.primary_water_line()
            if primary_line == "STARMIE":
                self.card_score += 2200.0
            elif primary_line == "YUKI":
                self.card_score -= 1800.0
        elif card_id == MEGA_YUKIMENOKO_EX:
            self.card_score = 4600.0
            existing_mega_yuki = [
                pokemon for pokemon in self.board.all_my_pokemon
                if pokemon is not target and self.board.card_id(pokemon) == MEGA_YUKIMENOKO_EX
            ]
            existing_safe = any(
                self.board.current_hp(pokemon) > self.board.opp_active_max_damage
                for pokemon in existing_mega_yuki
            )
            target_can_attack_next = target is not None and self.board.calculate_max_damage(target, next_turn=True) > 0
            active_mega_yuki_in_danger = (
                self.board.active is not None
                and self.board.card_id(self.board.active) == MEGA_YUKIMENOKO_EX
                and self.board.active_will_be_knocked_out
            )
            starmie_path_visible = (
                HITODEMAN in self.board.hand_ids
                or MEGA_STARMIE_EX in self.board.hand_ids
                or MEGA_SIGNAL in self.board.hand_ids
            )
            if (
                existing_mega_yuki
                and not self.board.opponent_has_alakazam_line
                and not target_can_attack_next
                and not active_mega_yuki_in_danger
            ):
                self.card_score -= 4200.0 if existing_safe else 1400.0
                if (
                    existing_safe
                    and starmie_path_visible
                ):
                    self.card_score -= 2600.0
            if self.board.opponent_active_is_crustle_wall:
                self.card_score -= 5200.0
            if self.board.opponent_has_alakazam_line:
                self.card_score += 1400.0
            if target_is_active and self.board.active_will_be_knocked_out and same_basic_on_bench:
                self.card_score -= 3600.0
            elif target_is_active:
                self.card_score += 500.0
            if self.board.has_no_backup_pokemon and target_is_active:
                self.card_score += 2200.0
            primary_line = self.board.primary_water_line()
            if primary_line == "YUKI":
                self.card_score += 2200.0
            elif (
                primary_line == "STARMIE"
                and not self.board.opponent_has_alakazam_line
                and not target_can_attack_next
                and not active_mega_yuki_in_danger
            ):
                self.card_score -= 2200.0
        elif card_id == YUKIMENOKO:
            existing = self.board.count_in_play(YUKIMENOKO)
            self.card_score = 2600.0 if existing == 0 else 900.0
            opp_ability_targets = len(self.board.freezing_shroud_targets(mine=False))
            my_ability_targets = len(self.board.freezing_shroud_targets(mine=True))
            if opp_ability_targets > 0:
                self.card_score += opp_ability_targets * 850.0 - my_ability_targets * 220.0
            if self.board.opponent_has_alakazam_line and self.board.count_in_play(MEGA_YUKIMENOKO_EX) == 0:
                self.card_score += 800.0
            if MEGA_YUKIMENOKO_EX in self.board.hand_ids:
                self.card_score -= 700.0
            if target_is_active:
                self.card_score -= 500.0
            if self.board.has_no_backup_pokemon and target_is_active:
                self.card_score -= 1800.0
        else:
            self.card_score = 1000.0

        self.action_score = 2500.0 + GameSimulator(self.board).evaluate_after_action(self) * 0.05
        if card_id == MEGA_YUKIMENOKO_EX:
            self.action_score += 900.0
            if target_is_active and self.board.active_will_be_knocked_out and same_basic_on_bench:
                self.action_score -= 2600.0
            if (
                self.board.count_in_play(MEGA_YUKIMENOKO_EX) > 0
                and not self.board.opponent_has_alakazam_line
                and not target_can_attack_next
                and not active_mega_yuki_in_danger
            ):
                self.action_score -= 2400.0 if existing_safe else 800.0
            if self.board.opponent_has_alakazam_line:
                self.action_score += 1100.0
            if self.board.opponent_active_is_crustle_wall:
                self.action_score -= 2600.0
        elif card_id == MEGA_STARMIE_EX and self.board.opponent_active_is_crustle_wall:
            self.action_score -= 3200.0
        elif card_id == YUKIMENOKO and MEGA_YUKIMENOKO_EX in self.board.hand_ids:
            self.action_score -= 700.0

    def apply(self, board: BoardState) -> BoardState:
        card_id = board.option_card_id(self.option)
        if card_id is not None:
            board.evolve_target(board.get_option_target(self.option), card_id)
        return board


class RetreatAction(GameAction):
    def _best_retreat_target(self, board: BoardState) -> Optional[Pokemon]:
        target = board.get_option_target(self.option)
        if target is not None:
            return target
        danger = board.active is not None and board.my_active_remaining_hp <= board.opp_active_max_damage
        active_id = board.card_id(board.active) if board.active is not None else None
        return max(
            board.bench,
            key=lambda pokemon: (
                5200 if danger and active_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX, YUKIMENOKO} and board.card_id(pokemon) == YVELTAL else 0,
                3000 if board.card_id(pokemon) == MEGA_STARMIE_EX else 0,
                2200 if board.card_id(pokemon) == MEGA_YUKIMENOKO_EX else 0,
                2500 if board.opponent_has_alakazam_line and board.card_id(pokemon) == MEGA_YUKIMENOKO_EX else 0,
                -3500 if board.card_id(pokemon) in {MUNKIDORI, YUKIMENOKO} else 0,
                board.calculate_max_damage(pokemon, next_turn=True),
                board.current_hp(pokemon),
            ),
            default=None,
        )

    def evaluate(self) -> None:
        target = self._best_retreat_target(self.board)
        if target is None:
            self.action_score = -99999.0
            return
        danger = self.board.active is not None and self.board.my_active_remaining_hp <= self.board.opp_active_max_damage
        active_damage = self.board.calculate_max_damage(self.board.active, next_turn=True)
        target_damage = self.board.calculate_max_damage(target, next_turn=True)
        score = 7000.0 if danger else -1200.0
        score += max(0, target_damage - active_damage) * 20.0
        if active_damage == 0 and target_damage > 0:
            score += 3000.0
        active_id = self.board.card_id(self.board.active) if self.board.active is not None else None
        target_id = self.board.card_id(target)
        active_can_take_prize = self.board.active is not None and self.board.can_take_prize(self.board.active, self.board.opp_active)
        target_can_take_prize = self.board.can_take_prize(target, self.board.opp_active)
        active_is_mega_attacker = active_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}
        target_is_mega_attacker = target_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}
        offensive_switch = target_damage > active_damage + 60 or target_can_take_prize
        defensive_switch = danger and target is not self.board.active and self.board.current_hp(target) > self.board.my_active_remaining_hp + 80
        justified_mega_switch = offensive_switch or defensive_switch
        spends_scarce_water = self.board.retreat_would_spend_water(self.board.active) and self.board.water_energy_is_scarce()
        if spends_scarce_water and not justified_mega_switch:
            score -= 5200.0
            if target_is_mega_attacker and target_damage <= 0:
                score -= 4800.0
            if not target_can_take_prize:
                score -= 2600.0
        if active_can_take_prize:
            score -= 14000.0
        if target_can_take_prize and not active_can_take_prize:
            score += 6200.0
        if active_id == target_id and active_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not justified_mega_switch:
            score -= 3200.0
        if active_is_mega_attacker and target_is_mega_attacker:
            if not danger and not justified_mega_switch:
                if target_damage <= active_damage:
                    score -= 6500.0
                elif target_damage - active_damage < 80:
                    score -= 2500.0
            if danger and not justified_mega_switch and target_damage <= active_damage and target_can_take_prize == active_can_take_prize:
                score -= 1800.0
        if active_id == MUNKIDORI:
            score += 4200.0
            if self.board.has_ready_mashimashira:
                score += 1200.0
        if active_id == YUKIMENOKO:
            score += 2200.0
        if active_id == YVELTAL:
            if target_can_take_prize:
                score += 800.0
            else:
                score -= 6500.0
        if active_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX, YUKIMENOKO} and danger and target_id == YVELTAL:
            score += 5200.0
        if target_id == MEGA_STARMIE_EX:
            score += 3200.0
        elif target_id == MEGA_YUKIMENOKO_EX:
            score += 2400.0
            if self.board.opponent_has_alakazam_line:
                score += 2200.0
        elif target_id in {MUNKIDORI, YUKIMENOKO}:
            score -= 4200.0
        self.action_score = score
        self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        if board.option_area(self.option) == AreaType.BENCH:
            board.switch_with_bench(mine=True, bench_index=board.option_index(self.option))
            return board
        target = self._best_retreat_target(board)
        for index, pokemon in enumerate(board.bench_slots):
            if pokemon is target:
                board.switch_with_bench(mine=True, bench_index=index)
                break
        return board


class PlayCardAction(GameAction):
    def evaluate(self) -> None:
        card_id = self.board.option_card_id(self.option)
        if card_id is None:
            self.action_score = -99999.0
            return
        if self.board.is_pokemon_card(card_id):
            self.card_score = self.evaluator.evaluate_pokemon_placement(card_id)
        else:
            self.card_score = self.evaluator.evaluate_card_play(card_id)
        if self.board.should_prioritize_active_attack_now and card_id in {
            HITODEMAN,
            MEGA_STARMIE_EX,
            POFIN,
            POKE_PAD,
            POKEGEAR,
            MEGA_SIGNAL,
            HYPERBALL,
            CARMINE,
            LILLIE_DETERMINATION,
            TOUKO,
            AKAMATSU,
        }:
            self.card_score -= 7200.0
            if self.board.active_knockout_loses_game:
                self.card_score -= 5000.0
        self.action_score = 500.0 + GameSimulator(self.board).evaluate_after_action(self) * 0.03

    def apply(self, board: BoardState) -> BoardState:
        card_id = board.option_card_id(self.option)
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


class EndAction(GameAction):
    def evaluate(self) -> None:
        best_development = self._best_development_option_value()
        score = -500.0
        if best_development >= 1000.0:
            score -= min(22000.0, 5000.0 + best_development * 2.0)
        if self.board.has_pre_attack_development_card:
            score -= 5200.0
        if self.board.is_development_starved:
            score -= 7600.0
        if len(self.board.hand_ids) >= 4 and not self.board.should_prioritize_active_attack_now:
            score -= 3600.0
        if self.board.has_no_backup_pokemon:
            score -= 4200.0
        self.action_score = score


class AbilityAction(GameAction):
    def evaluate(self) -> None:
        target = self.board.get_option_target(self.option)
        card_id = self.board.card_id(target) if target is not None else self.board.option_card_id(self.option)
        if card_id != MUNKIDORI:
            self.action_score = AbilityResolver(self.board).evaluate()
            return
        if target is None or self.board.count_energy(target, BASIC_UNLICHT_ENERGIE) <= 0:
            self.action_score = -99999.0
            return
        if not self.board.has_damaged_my_pokemon:
            self.action_score = -1200.0
            return
        score = 6200.0
        if self.board.can_munkidori_shift_for_prize:
            score += 5000.0
        if self.board.my_active_remaining_hp <= self.board.opp_active_max_damage:
            score += 1800.0
        score += min(3, max(1, sum((int(p.maxHp) - self.board.current_hp(p)) // 10 for p in self.board.all_my_pokemon))) * 700.0
        self.action_score = score


class CountAction(GameAction):
    def evaluate(self) -> None:
        number = int(getattr(self.option, "number", 0) or 0)
        if self.board.select_context == SelectContext.DRAW_COUNT:
            self.action_score = number * 1000.0
            if self.board.is_development_starved:
                self.action_score += number * 1000.0
            return
        self.action_score = float(number)


class AttachEnergyAction(GameAction):
    def energy_token(self) -> str:
        card_id = self.board.option_card_id(self.option)
        if card_id is None:
            return "UNKNOWN"
        return ENERGY_CARD_TO_TYPE.get(card_id, f"CARD_{card_id}")

    def evaluate(self) -> None:
        target = self.board.get_option_target(self.option)
        card_id = self.board.option_card_id(self.option)
        if card_id is None or target is None:
            self.action_score = -99999.0
            return
        self.card_score = self.evaluator.evaluate_energy_attach(card_id, target)
        if card_id not in ENERGY_CARD_TO_TYPE:
            self.action_score = 900.0
            self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.03
            return
        before = self.board.best_attack_damage(target)
        after = self.board.best_attack_damage(target, [self.energy_token()])
        self.action_score = 1000.0 + max(0, after - before) * 10.0
        target_id = self.board.card_id(target)
        if self.board.active_basic_is_decoy(target):
            self.action_score -= 5200.0
        elif self.board.bench_basic_should_be_built(target):
            self.action_score += 3600.0
        if target_id == YVELTAL and not self.board.can_take_prize(target, self.board.opp_active):
            self.action_score -= 3200.0
        if card_id == BASIC_WATER_ENERGIE and self.board.water_energy_is_scarce():
            if self.board.pokemon_matches_primary_water_line(target):
                self.action_score += 2600.0
            else:
                self.action_score -= 7200.0
        if card_id == BASIC_WATER_ENERGIE and target_id not in {HITODEMAN, MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            if not (target_id == YUKIMENOKO and self.board.opponent_active_is_crustle_wall):
                self.action_score -= 5200.0
        if (
            card_id == BASIC_WATER_ENERGIE
            and target_id in {YUKIWARASHI, YUKIMENOKO}
            and self.board.should_reserve_water_for_starmie
        ):
            self.action_score -= 9000.0
        if card_id == BASIC_WATER_ENERGIE and target_id == YUKIMENOKO and not self.board.opponent_active_is_crustle_wall:
            self.action_score -= 4200.0
        if card_id == BASIC_WATER_ENERGIE and target_id == YUKIWARASHI and MEGA_YUKIMENOKO_EX in self.board.hand_ids:
            self.action_score -= 2600.0
        has_priority_setup = self.board.has_priority_setup_before_energy()
        progress_before = self.board.high_impact_attack_progress(target)
        progress_after = self.board.high_impact_attack_progress(target, [self.energy_token()])
        self.action_score += max(0.0, progress_after - progress_before)
        attack = self.board.high_impact_attack(target)
        completes_ko_now = False
        if attack is not None:
            missing_before = self.board.attack_energy_shortfall(target, attack)
            missing_after = self.board.attack_energy_shortfall(target, attack, [self.energy_token()])
            self.action_score += max(0, missing_before - missing_after) * 900.0
            if missing_after == 0 and missing_before > 0:
                self.action_score += 1800.0
                completes_ko_now = target is self.board.active and self.board.effective_attack_damage(target, attack) >= self.board.current_hp(self.board.opp_active)
        if has_priority_setup and not completes_ko_now:
            self.action_score -= 2600.0
            if card_id == BASIC_WATER_ENERGIE and target_id not in {HITODEMAN, MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
                self.action_score -= 5200.0
        self.action_score += GameSimulator(self.board).evaluate_after_action(self) * 0.05

    def apply(self, board: BoardState) -> BoardState:
        if self.board.option_card_id(self.option) not in ENERGY_CARD_TO_TYPE:
            return board
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
            if self.board.context_card_id == TANKER or self.board.effect_card_id == TANKER:
                if card.id == BASIC_WATER_ENERGIE and self.board.needs_water_energy():
                    self.action_score = 5600.0
                    return
                if card.id == BASIC_UNLICHT_ENERGIE and self.board.needs_dark_energy():
                    self.action_score = 3600.0
                    return
            if self.board.context_card_id == AKAMATSU or self.board.effect_card_id == AKAMATSU:
                if card.id == BASIC_WATER_ENERGIE and self.board.needs_water_energy():
                    self.action_score = 4600.0
                    return
                if card.id == BASIC_UNLICHT_ENERGIE and self.board.needs_dark_energy():
                    self.action_score = 3400.0
                    return
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
        if card.id == BASIC_UNLICHT_ENERGIE and self.board.card_id(target) == MUNKIDORI:
            score -= 5000.0
        elif card.id == BASIC_WATER_ENERGIE and self.board.water_energy_is_scarce():
            score -= 9000.0
            if self.board.card_id(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX, HITODEMAN}:
                score -= 3500.0
        elif card.id == BASIC_WATER_ENERGIE and self.board.card_id(target) == MEGA_STARMIE_EX:
            score -= 2500.0
        else:
            score += 1000.0

        remaining = self.board.count_energy(target) - 1
        if remaining < self.board.effective_retreat_cost(target):
            score -= 600.0
        if (
            card.id == BASIC_WATER_ENERGIE
            and self.board.card_id(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}
            and self.board.count_energy(target, BASIC_WATER_ENERGIE) <= 1
            and self.board.best_attack_damage(target) > 0
        ):
            score -= 4200.0
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
        card_id = self.board.option_card_id(option)

        if card_id is not None:
            if self.board.select_context in (
                SelectContext.SETUP_ACTIVE_POKEMON,
                SelectContext.SETUP_BENCH_POKEMON,
                SelectContext.TO_HAND,
                SelectContext.TO_HAND_ENERGY,
                SelectContext.TO_FIELD,
                SelectContext.TO_BENCH,
                SelectContext.DISCARD,
            ):
                if self.board.select_context == SelectContext.DISCARD:
                    return self.evaluator.evaluate_trash_target(card_id)
                return self.search.score_effect_card(card_id)
            if self.board.deck_is_visible or "DECK" in descriptor or "SEARCH" in descriptor:
                return self.search.score_effect_card(card_id)
            if "TRASH" in descriptor or "DISCARD" in descriptor:
                return self.evaluator.evaluate_trash_target(card_id)
            if "RECOVER" in descriptor or "RETRIEVE" in descriptor or "HAND" in descriptor:
                return self.search.score_effect_card(card_id)
            # 用途不明時はカードの役割を断定しない。
            return 0.0

        target = self.board.get_option_target(option)
        if target is not None:
            mine = self.board.option_points_to_me(option)
            if not mine and (self.board.context_card_id == BEFEHL_VON_BOSS or self.board.effect_card_id == BEFEHL_VON_BOSS):
                if self.board.can_boss_around_crustle_for_prize():
                    return self.board.boss_around_crustle_target_value(target)
                if self.board.can_boss_delay_active_sweeper():
                    return self.board.boss_delay_target_value(target)
                if self.board.can_boss_disrupt_setup():
                    return self.board.boss_disrupt_setup_target_value(target)
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
        option_type = option.type

        if getattr(option, "number", None) is not None or board.select_context in (
            SelectContext.DRAW_COUNT,
            SelectContext.DAMAGE_COUNTER_COUNT,
            SelectContext.REMOVE_DAMAGE_COUNTER_COUNT,
        ):
            return CountAction(option_index, option, board, evaluator)
        if option_type in (OptionType.YES, OptionType.NO) or "YES" in token or "NO" in token:
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
        if option.attackId is not None or option_type == OptionType.ATTACK or "ATTACK" in token:
            return AttackAction(option_index, option, board, evaluator)
        if option_type == OptionType.EVOLVE or "EVOLVE" in token:
            return EvolveAction(option_index, option, board, evaluator)
        if option_type == OptionType.RETREAT or "RETREAT" in token or "SWITCH" in token:
            return RetreatAction(option_index, option, board, evaluator)
        if option_type == OptionType.ATTACH or "ATTACH" in token or option.energyIndex is not None:
            return AttachEnergyAction(option_index, option, board, evaluator)
        if option_type == OptionType.ABILITY or "ABILITY" in token:
            return AbilityAction(option_index, option, board, evaluator)
        if option_type == OptionType.PLAY or "PLAY" in token or "USE" in token:
            return PlayCardAction(option_index, option, board, evaluator)
        if option_type == OptionType.END or "END" in token:
            return EndAction(option_index, option, board, evaluator)

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


def _debug_option_line(board: BoardState, index: int, option: Any, score: float) -> str:
    card_id = board.option_card_id(option)
    fields = [
        f"i={index}",
        f"score={score:.1f}",
        f"type={board._enum_token(option.type)}",
    ]
    if card_id is not None:
        fields.append(f"card={card_id}")
    if option.area is not None:
        fields.append(f"area={board._enum_token(option.area)}")
    if option.index is not None:
        fields.append(f"idx={option.index}")
    if option.playerIndex is not None:
        fields.append(f"p={option.playerIndex}")
    if option.serial is not None:
        fields.append(f"serial={option.serial}")
    if option.attackId is not None:
        fields.append(f"atk={option.attackId}")
    return " ".join(fields)


def _debug_selection(board: BoardState, actions: List[GameAction], selected: List[int], reason: str) -> None:
    if not DEBUG_SELECTION:
        return
    try:
        ranked = sorted(actions, key=lambda action: action.total_score, reverse=True)[:8]
        print(
            "[DBG]",
            f"turn={board.turn}",
            f"action={board.turn_action_count}",
            f"ctx={board._enum_token(board.select_context)}",
            f"type={board._enum_token(board.select_type)}",
            f"effect={board.effect_card_id}",
            f"contextCard={board.context_card_id}",
            f"min={board.select_data.minCount}",
            f"max={board.select_data.maxCount}",
            f"selected={selected}",
            f"reason={reason}",
            file=sys.stderr,
        )
        for action in ranked:
            print("[DBG_OPT]", _debug_option_line(board, action.option_index, action.option, action.total_score), file=sys.stderr)
    except Exception as exc:
        print("[DBG_ERROR]", repr(exc), file=sys.stderr)


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
            _debug_selection(board, ActionFactory.build_actions(board, MasterEvaluator(board)), [selected], "damage-counter")
            return [selected]

    evaluator = MasterEvaluator(board)
    actions = ActionFactory.build_actions(board, evaluator)
    if not actions:
        return []

    selected = _format_selection(board, actions)
    if selected or int(board.select_data.minCount or 0) == 0:
        _debug_selection(board, actions, selected, "scored")
        return selected

    fallback = SelectionResolver(board, evaluator).choose()
    _debug_selection(board, actions, [fallback] if fallback is not None else [], "fallback")
    return [fallback] if fallback is not None else []

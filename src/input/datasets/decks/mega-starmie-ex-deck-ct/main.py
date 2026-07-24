"""
Mega Starmie ex Deck Agent v6

Full-scratch first version.

Principles:
- GameSimulator is a non-mutating candidate ordering layer only.
- Keep API access inside BoardView.
- Use hard guard layers before soft scores.
- Main route: Cinderace acceleration + Salvatore instant Mega evolution + Mega Starmie attack.
"""

import os
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


_MODULE_FILE = globals().get("__file__")
_CG_PATH_CANDIDATES = [os.getcwd(), "/kaggle_simulations/agent"]
if _MODULE_FILE:
    _CG_PATH_CANDIDATES.insert(0, os.path.dirname(os.path.abspath(_MODULE_FILE)))
for _path in _CG_PATH_CANDIDATES:
    if _path and _path not in sys.path and os.path.isdir(os.path.join(_path, "cg")):
        sys.path.insert(0, _path)

from cg.api import (  # noqa: E402
    AreaType,
    CardType,
    EnergyType,
    LogType,
    Observation,
    OptionType,
    Pokemon,
    SelectContext,
    all_card_data,
    to_observation_class,
)

try:
    from cg.api import all_attack  # noqa: E402
except ImportError:
    all_attack = None


# ============================================================
# Card IDs
# ============================================================
HITODEMAN = 1030
MEGA_STARMIE_EX = 1031
YUKIWARASHI = 860
MEGA_YUKIMENOKO_EX = 861
YUKIMENOKO = 104
CINDERACE = 666
YVELTAL = 689
SHAYMIN = 343

POFIN = 1086
POKE_PAD = 1152
HYPERBALL = 1121
POKEGEAR = 1122
ENERGY_SWITCH = 1116
TANKER = 1097
TOOL_SCRAPPER = 1137
HERO_CAPE = 1159
MEGA_SIGNAL = 1145
BEFEHL_VON_BOSS = 1182
CRISPIN = 1198
HILDA = 1225
SALVATORE = 1189
LILLIE_DETERMINATION = 1227
WALLY_COMPASSION = 1229
SURFING_BEACH = 1262

BASIC_WATER_ENERGY = 3
BASIC_DARK_ENERGY = 7
IGNITION_ENERGY = 17

WATER_GUN = 1486
JETTING_BLOW = 1487
NEBULA_BEAM = 1488
CHILLY = 1239
RESENTFUL_REFRAIN = 1240
ABSOLUTE_SNOW = 1241
TURBO_FLARE = 965

HAND_ALAKAZAM_LINE = {741, 742, 743}
COUNTER_ALAKAZAM_LINE = {109, 245}
ALAKAZAM_LINE = HAND_ALAKAZAM_LINE | COUNTER_ALAKAZAM_LINE

CRUSTLE_LINE = {344, 345, 532}
EX_ATTACK_WALLS = {330, 345}

RIOLU = 677
MEGA_LUCARIO_EX = 678
MAKUHITA = 673
HARIYAMA = 674
LUNATONE = 675
SOLROCK = 676
LUCARIO_ENGINE = {RIOLU, MAKUHITA, HARIYAMA, LUNATONE, SOLROCK}
LUCARIO_LINE = LUCARIO_ENGINE | {MEGA_LUCARIO_EX}

ARCHALUDON_EX = 190
DURALUDON_LINE = {169, 170, 190, 839, 840, 992}
FULL_METAL_LAB = 1244

DREEPY_LINE = {119, 120, 121}
DRAGAPULT_EX = 121
BUDEW = 235
MARIE_LINE = {642, 643, 644, 645, 646, 647, 648, 649}

MAIN_LINE = {HITODEMAN, MEGA_STARMIE_EX, YUKIWARASHI, MEGA_YUKIMENOKO_EX}
STARMIE_LINE = {HITODEMAN, MEGA_STARMIE_EX}
YUKI_LINE = {YUKIWARASHI, MEGA_YUKIMENOKO_EX, YUKIMENOKO}
UTILITY_POKEMON = {CINDERACE, YVELTAL, SHAYMIN, YUKIMENOKO}
WATER_POKEMON = {HITODEMAN, MEGA_STARMIE_EX, YUKIWARASHI, MEGA_YUKIMENOKO_EX, YUKIMENOKO}
IMPORTANT_CARDS = {
    HITODEMAN,
    MEGA_STARMIE_EX,
    BASIC_WATER_ENERGY,
    CINDERACE,
    SALVATORE,
    POFIN,
    HYPERBALL,
    MEGA_SIGNAL,
    POKEGEAR,
    TANKER,
    WALLY_COMPASSION,
    HERO_CAPE,
    TOOL_SCRAPPER,
}

MATCHUP_PLANS = {
    "LUCARIO": {
        "name": "Mega Lucario speed engine",
        "main_axis": "STARMIE",
        "must_pressure": LUCARIO_ENGINE | {MEGA_LUCARIO_EX},
        "boss_targets": LUCARIO_ENGINE,
        "setup_cards": {CINDERACE, HITODEMAN, MEGA_STARMIE_EX, SALVATORE, POFIN, HYPERBALL, CRISPIN},
        "attack_ids": {JETTING_BLOW, NEBULA_BEAM, TURBO_FLARE},
        "notes": (
            "They complete the board extremely fast. Do not wait for a slow Froslass line. "
            "Use Cinderace to accelerate, Salvatore to evolve, then push Mega Starmie."
        ),
    },
    "STEEL": {
        "name": "Archaludon and metal tempo",
        "main_axis": "STARMIE",
        "must_pressure": DURALUDON_LINE,
        "boss_targets": DURALUDON_LINE,
        "setup_cards": {HITODEMAN, MEGA_STARMIE_EX, SALVATORE, CRISPIN, TANKER, TOOL_SCRAPPER},
        "attack_ids": {NEBULA_BEAM},
        "notes": (
            "Jetting Blow often loses the durability race. Get to three colorless energy "
            "and keep Nebula Beam online."
        ),
    },
    "WALL": {
        "name": "Crustle and EX attack walls",
        "main_axis": "STARMIE",
        "must_pressure": CRUSTLE_LINE | EX_ATTACK_WALLS,
        "boss_targets": CRUSTLE_LINE,
        "setup_cards": {HITODEMAN, MEGA_STARMIE_EX, SALVATORE, CRISPIN, TOOL_SCRAPPER},
        "attack_ids": {NEBULA_BEAM},
        "notes": (
            "Do not repeat EX attacks that are blocked. Either remove/avoid the wall or "
            "use Nebula Beam's effect-ignoring damage."
        ),
    },
    "ALAKAZAM": {
        "name": "Alakazam hand-size pressure",
        "main_axis": "FROSLASS_OPTIONAL",
        "must_pressure": ALAKAZAM_LINE,
        "boss_targets": ALAKAZAM_LINE,
        "setup_cards": {YUKIWARASHI, MEGA_YUKIMENOKO_EX, SALVATORE, POFIN, HYPERBALL},
        "attack_ids": {RESENTFUL_REFRAIN, JETTING_BLOW},
        "notes": (
            "Mega Froslass can punish a large opponent hand, but never stop an already "
            "available Mega Starmie attack just to wait for it."
        ),
    },
    "BENCH_DAMAGE": {
        "name": "Dragapult and bench spread",
        "main_axis": "STARMIE_WITH_SHAYMIN",
        "must_pressure": DREEPY_LINE | {DRAGAPULT_EX, BUDEW} | MARIE_LINE,
        "boss_targets": DREEPY_LINE | {BUDEW},
        "setup_cards": {SHAYMIN, HITODEMAN, MEGA_STARMIE_EX, SALVATORE, POFIN},
        "attack_ids": {JETTING_BLOW, NEBULA_BEAM},
        "notes": (
            "Protect the bench when the opponent spreads damage, but do not let protection "
            "delay the main attacker forever."
        ),
    },
    "GENERAL": {
        "name": "generic tempo",
        "main_axis": "STARMIE",
        "must_pressure": set(),
        "boss_targets": set(),
        "setup_cards": {HITODEMAN, MEGA_STARMIE_EX, SALVATORE, POFIN, HYPERBALL},
        "attack_ids": {JETTING_BLOW, NEBULA_BEAM},
        "notes": "Build Mega Starmie quickly and attack before hand-shaping becomes a delay.",
    },
}

FORBIDDEN_PATTERNS = {
    "attackable_end": "Do not end the turn while a useful attack is legal.",
    "ignition_without_attack": "Ignition Energy must be consumed by an immediate attack.",
    "meaningless_retreat": "Retreat only for lethal, survival, acceleration handoff, or a better attacker.",
    "zero_energy_mega_wall": "Do not promote an energyless Mega as a wall.",
    "trash_core": "Do not discard Staryu, Mega Starmie, water energy, Salvatore, or survival tools casually.",
    "blocked_ex_loop": "Do not loop blocked EX attacks into Crustle/Sylveon-like walls.",
}

DEFAULT_DECK = [
    1030, 1030, 1030, 1031, 1031, 860, 860, 860, 861, 861,
    1229, 343, 666, 1116, 1122, 860, 1086, 1086, 1086, 3,
    666, 1152, 1152, 1137, 1121, 1121, 1121, 1097, 1097, 1145,
    1159, 689, 1227, 1227, 1227, 1227, 666, 1122, 1229, 1225,
    1189, 1198, 1198, 1189, 1182, 1182, 1262, 1262, 1122, 17,
    3, 3, 3, 3, 3, 3, 3, 7, 7, 1137,
]

SCORE_FORBIDDEN = -10**12
SCORE_LAST_RESORT = -10**7
SCORE_FORCED = 10**9
SCORE_PREFERRED = 10**6

TIER_FORBIDDEN = 0
TIER_BLOCKED_OR_BAD_ACTION = 10
TIER_LOW_VALUE_ACTION = 20
TIER_NON_KO_ATTACK = 30
TIER_HIGH_VALUE_PREP = 40
TIER_PRESERVE_WIN_OR_KO_PREP = 50
TIER_KO = 60
TIER_WIN = 70

NEXT_TURN_PRESSURE_DISCOUNT = 0.35
ACTIVE_EVOLVE_CLEAR_DAMAGE_GAIN = 50


def _read_deck() -> List[int]:
    paths = []
    if _MODULE_FILE:
        paths.append(os.path.join(os.path.dirname(os.path.abspath(_MODULE_FILE)), "deck.csv"))
    paths.extend(["/kaggle_simulations/agent/deck.csv", "deck.csv"])
    for path in paths:
        try:
            with open(path, encoding="utf-8") as file:
                deck = [
                    int(line.strip().rstrip(","))
                    for line in file.read().splitlines()
                    if line.strip()
                ]
            if len(deck) == 60:
                return deck
        except OSError:
            pass
    return list(DEFAULT_DECK)


def _initialize() -> Tuple[List[int], Dict[int, Any], Dict[int, Any]]:
    cards = {card.cardId: card for card in all_card_data()}
    attacks: Dict[int, Any] = {}
    if all_attack is not None:
        try:
            attacks = {attack.attackId: attack for attack in all_attack()}
        except Exception:
            attacks = {}
    return _read_deck(), cards, attacks


DECK, CARD_TABLE, ATTACK_TABLE = _initialize()


# ============================================================
# Small helpers
# ============================================================
def card_id(card: Any) -> Optional[int]:
    if card is None:
        return None
    return card.id


def is_option_type(option: Any, option_type: OptionType) -> bool:
    return option.type == option_type


def safe_int(value: Any, default: int = 0) -> int:
    return default if value is None else int(value)


def damage_on(pokemon: Optional[Pokemon]) -> int:
    if pokemon is None:
        return 0
    return max(0, int(pokemon.maxHp) - int(pokemon.hp))


def hp_left(pokemon: Optional[Pokemon]) -> int:
    return 0 if pokemon is None else int(pokemon.hp)


def max_hp(pokemon: Optional[Pokemon]) -> int:
    return 0 if pokemon is None else int(pokemon.maxHp)


def can_pay_attack_with_tokens(attack: Any, energy_tokens: Sequence[Any]) -> bool:
    if attack is None:
        return False
    requirements = Counter(attack.energies)
    supported_requirements = {EnergyType.WATER, EnergyType.DARKNESS, EnergyType.COLORLESS}
    if any(need not in supported_requirements for need in requirements):
        return False
    tokens = Counter(energy_tokens)
    water_need = requirements[EnergyType.WATER]
    dark_need = requirements[EnergyType.DARKNESS]
    colorless_need = requirements[EnergyType.COLORLESS]
    if tokens[EnergyType.WATER] < water_need:
        return False
    if tokens[EnergyType.DARKNESS] < dark_need:
        return False
    remaining_units = sum(tokens.values()) - water_need - dark_need
    return remaining_units >= colorless_need


def attack_can_damage_opponent_bench(attack: Optional[Any]) -> bool:
    if attack is None:
        return False
    text = str(getattr(attack, "text", "") or "")
    if not text:
        real_attack = ATTACK_TABLE.get(int(getattr(attack, "attackId", -1)))
        text = str(getattr(real_attack, "text", "") or "")
    text = text.replace("\u2019", "'").replace("\xa0", " ").replace("Pok\u00e9mon", "Pokemon").lower()
    if "for each of your opponent's benched pokemon" in text and "to each of your opponent's benched pokemon" not in text:
        return False
    if "opponent's benched pokemon" in text and ("damage" in text or "damage counter" in text):
        return True
    return "opponent's pokemon" in text and "for benched pokemon" in text and ("damage" in text or "damage counter" in text)


def attack_bench_damage_amount(attack: Optional[Any]) -> int:
    if attack is None:
        return 0
    explicit = safe_int(getattr(attack, "bench_damage", 0))
    if explicit > 0 and getattr(attack, "attackId", None) == JETTING_BLOW:
        return explicit
    if getattr(attack, "attackId", None) == JETTING_BLOW:
        return 50
    return 0


def energy_tokens_for_attach(card_id: int, target: Pokemon) -> Optional[Tuple[Any, ...]]:
    if card_id == BASIC_WATER_ENERGY:
        return (EnergyType.WATER,)
    if card_id == BASIC_DARK_ENERGY:
        return (EnergyType.DARKNESS,)
    if card_id == IGNITION_ENERGY:
        data = CARD_TABLE.get(int(target.id))
        if data is None:
            return None
        if data.basic:
            return (EnergyType.COLORLESS,)
        return (EnergyType.COLORLESS, EnergyType.COLORLESS, EnergyType.COLORLESS)
    return None


@dataclass(frozen=True)
class ImmediateOutcome:
    supported: bool = True
    blocked: bool = False
    damage: int = 0
    knockout: bool = False
    prizes_taken: int = 0
    wins_game: bool = False
    bypasses_wall: bool = False
    enables_attack: bool = False
    enabled_attack_ids: Tuple[int, ...] = ()
    avoids_wall: bool = False
    breaks_engine: bool = False
    removes_tool: bool = False
    enables_knockout: bool = False
    retreat_energy_cost: int = 0
    important_energy_loss: int = 0
    improves_damage: bool = False
    target_id: Optional[int] = None
    target_serial: Optional[int] = None
    recommended_target_id: Optional[int] = None
    recommended_target_serial: Optional[int] = None
    reasons: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionScore:
    tier: int
    immediate: float = 0
    development: float = 0
    pressure: float = 0
    resource: float = 0
    risk: float = 0
    legacy: float = 0


HAND_ACTIVITY_LIVE_NOW = "LIVE_NOW"
HAND_ACTIVITY_KEEP = "KEEP"
HAND_ACTIVITY_LOW = "LOW_ACTIVITY"


@dataclass(frozen=True)
class LillieEffectFacts:
    hand_size: int
    shuffle_count: int
    draw_count: Optional[int]


@dataclass(frozen=True)
class HandActivityFacts:
    hand_size: int
    live_now_count: int
    keep_count: int
    low_activity_count: int
    low_activity_ratio: float
    activities: Tuple[Tuple[int, str], ...]
    lillie_effect: LillieEffectFacts


@dataclass(frozen=True)
class AttackEnergyGap:
    attack_id: int
    ready: bool
    missing_units: int
    missing_types: Tuple[Any, ...]


@dataclass(frozen=True)
class ActiveEnergyFacts:
    active_id: int
    energy_cards: Tuple[int, ...]
    energy_tokens: Tuple[Any, ...]
    payable_attack_ids: Tuple[int, ...]
    unpayable_attack_ids: Tuple[int, ...]
    attack_gaps: Tuple[AttackEnergyGap, ...]
    key_attack_id: Optional[int]
    key_attack_ready: bool
    key_attack_missing_units: int
    key_attack_missing_types: Tuple[Any, ...]
    water_remaining_possible: bool
    dark_remaining_possible: bool


@dataclass(frozen=True)
class PokegearSupporterFacts:
    deck_is_public: bool
    known_supporter_count: int
    live_supporter_count: int
    dead_supporter_count: int
    supporter_remaining_possible: Optional[bool]
    no_target_confirmed: bool


@dataclass(frozen=True)
class RoleFacts:
    retreat_cost: int
    free_retreat: bool
    basic: bool
    evolution: bool
    mega: bool
    ex: bool
    prize_value: int
    energy_count: int
    attack_ready: bool
    key_attack_id: Optional[int]
    key_attack_ready: Optional[bool]
    role_completed: Optional[bool]
    duplicate_count: int
    bench_slot_cost: int
    current_position: str
    # Free-retreat candidate fact only; this does not mean the Pokemon should be promoted.
    pivot_candidate: bool
    ready_if_promoted: bool


@dataclass(frozen=True)
class ActiveEvolutionAttackFact:
    attack_id: int
    supported: bool
    damage: int
    blocked: bool
    knockout: bool
    prizes_taken: int
    wins_game: bool
    bench_damage: int
    bypasses_wall: bool


@dataclass(frozen=True)
class SimulationResult:
    index: int
    option: Any
    policy_score: float
    tier: str
    outcome: ImmediateOutcome
    action_score: ActionScore = ActionScore(TIER_LOW_VALUE_ACTION)


# ============================================================
# BoardView
# ============================================================
class BoardView:
    def __init__(self, obs: Observation):
        self.obs = obs
        self.select = obs.select
        self.state = obs.current
        self.me = self.state.players[self.state.yourIndex]
        self.opp = self.state.players[1 - self.state.yourIndex]
        self.my_index = self.state.yourIndex
        self.opp_index = 1 - self.state.yourIndex
        self.hand = self.me.hand or []
        self.hand_ids = [card.id for card in self.hand]
        self.discard = self.me.discard or []
        self.discard_ids = [card.id for card in self.discard]
        self.deck_view = self.select.deck or []
        self.deck_ids = [card.id for card in self.deck_view]
        self.active = self.me.active[0] if self.me.active else None
        self.opp_active = self.opp.active[0] if self.opp.active else None
        self.bench = [pokemon for pokemon in self.me.bench if pokemon is not None]
        self.opp_bench = [pokemon for pokemon in self.opp.bench if pokemon is not None]
        self.all_my_pokemon = ([self.active] if self.active is not None else []) + self.bench
        self.all_opp_pokemon = ([self.opp_active] if self.opp_active is not None else []) + self.opp_bench
        self.bench_space = max(0, int(self.me.benchMax) - len(self.bench))
        self.card_counts = Counter(self.hand_ids + self.discard_ids + [self.pid(p) for p in self.all_my_pokemon])

    def pid(self, pokemon: Optional[Pokemon]) -> int:
        return -1 if pokemon is None else int(pokemon.id)

    def data(self, cid: Optional[int]) -> Optional[Any]:
        return None if cid is None else CARD_TABLE.get(int(cid))

    def attack(self, attack_id: Optional[int]) -> Optional[Any]:
        return None if attack_id is None else ATTACK_TABLE.get(int(attack_id))

    def option_card(self, option: Any) -> Optional[int]:
        if option.cardId is not None:
            return option.cardId
        if option.type == OptionType.PLAY and option.index is not None and 0 <= option.index < len(self.hand):
            return self.hand[option.index].id
        cards = self.cards_in_area(option.area, option.playerIndex)
        if cards is not None and option.index is not None and 0 <= option.index < len(cards):
            obj = cards[option.index]
            if obj is not None:
                return obj.id
        return None

    def cards_in_area(self, area: Optional[AreaType], player: Optional[int]) -> Optional[Sequence[Any]]:
        if area == AreaType.HAND:
            return self.hand if player in (None, self.my_index) else (self.opp.hand or [])
        if area == AreaType.DECK:
            return self.deck_view
        if area == AreaType.DISCARD:
            return self.discard if player in (None, self.my_index) else (self.opp.discard or [])
        if area == AreaType.PRIZE:
            return self.me.prize if player in (None, self.my_index) else self.opp.prize
        if area == AreaType.LOOKING:
            return self.state.looking or []
        return None

    def pokemon_in_area(self, area: Optional[AreaType], index: Optional[int], player: Optional[int]) -> Optional[Pokemon]:
        mine = player in (None, self.my_index)
        active = self.active if mine else self.opp_active
        bench = self.bench if mine else self.opp_bench
        if area == AreaType.ACTIVE:
            return active
        if area == AreaType.BENCH and index is not None and 0 <= index < len(bench):
            return bench[index]
        return None

    def option_target(self, option: Any) -> Optional[Pokemon]:
        target = self.pokemon_in_area(option.inPlayArea, option.inPlayIndex, self.my_index)
        if target is not None:
            return target
        return self.pokemon_in_area(option.area, option.index, option.playerIndex)

    def iter_options(self) -> Iterable[Tuple[int, Any]]:
        for index, option in enumerate(self.select.option or []):
            yield index, option

    def count_in_play(self, cid: int) -> int:
        return sum(1 for pokemon in self.all_my_pokemon if self.pid(pokemon) == cid)

    def count_opp_in_play(self, cid: int) -> int:
        return sum(1 for pokemon in self.all_opp_pokemon if self.pid(pokemon) == cid)

    def has_in_play(self, ids: set[int]) -> bool:
        return any(self.pid(pokemon) in ids for pokemon in self.all_my_pokemon)

    def opp_has(self, ids: set[int]) -> bool:
        return any(self.pid(pokemon) in ids for pokemon in self.all_opp_pokemon)

    def visible_or_unknown_in_deck(self, cid: int) -> bool:
        return not self.deck_view or cid in self.deck_ids

    def remaining_possible(self, cid: int, total: Optional[int] = None) -> bool:
        if self.deck_view:
            return cid in self.deck_ids
        total = DECK.count(cid) if total is None else total
        known_out = self.hand_ids.count(cid) + self.discard_ids.count(cid)
        known_out += sum(1 for pokemon in self.all_my_pokemon if self.pid(pokemon) == cid)
        known_out += sum(1 for pokemon in self.all_opp_pokemon if self.pid(pokemon) == cid)
        return known_out < total

    def deck_has(self, predicate: Callable[[int], bool]) -> bool:
        return not self.deck_view or any(predicate(cid) for cid in self.deck_ids)

    def is_pokemon(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType == CardType.POKEMON

    def is_basic_pokemon(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType == CardType.POKEMON and data.basic

    def is_rule_pokemon(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType == CardType.POKEMON and (data.ex or data.megaEx or data.tera)

    def is_supporter(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType == CardType.SUPPORTER

    def is_energy(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType in {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY}

    def is_poffin_target(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType == CardType.POKEMON and data.basic and data.hp <= 70 and not data.ex

    def is_poke_pad_target(self, cid: Optional[int]) -> bool:
        return self.is_pokemon(cid) and not self.is_rule_pokemon(cid)

    def is_mega_signal_target(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        return data is not None and data.cardType == CardType.POKEMON and data.megaEx

    def evolves_from(self, evolution_id: int, pokemon: Optional[Pokemon]) -> bool:
        if pokemon is None:
            return False
        evo = self.data(evolution_id)
        base = self.data(self.pid(pokemon))
        if evo is None or base is None or evo.evolvesFrom is None:
            return False
        if isinstance(evo.evolvesFrom, int):
            return evo.evolvesFrom == base.cardId
        return str(evo.evolvesFrom) == str(base.name)

    def card_evolves_from_card(self, evolution_id: int, base_id: int) -> bool:
        evo = self.data(evolution_id)
        base = self.data(base_id)
        if evo is None or base is None or evo.evolvesFrom is None:
            return False
        if isinstance(evo.evolvesFrom, int):
            return evo.evolvesFrom == base.cardId
        return str(evo.evolvesFrom) == str(base.name)

    def card_or_evolution_has_bench_damage_threat(self, cid: int, seen: Optional[set[int]] = None) -> bool:
        if seen is None:
            seen = set()
        if cid in seen:
            return False
        seen.add(cid)
        data = self.data(cid)
        if data is None:
            return False
        if any(attack_can_damage_opponent_bench(self.attack(attack_id)) for attack_id in data.attacks):
            return True
        for evolution_id in CARD_TABLE:
            if self.card_evolves_from_card(evolution_id, cid):
                if self.card_or_evolution_has_bench_damage_threat(evolution_id, seen):
                    return True
        return False

    def salvatore_target_evolution(self, pokemon: Optional[Pokemon]) -> Optional[int]:
        pid = self.pid(pokemon)
        if pid == HITODEMAN:
            evolution_id = MEGA_STARMIE_EX
        elif pid == YUKIWARASHI:
            evolution_id = MEGA_YUKIMENOKO_EX
        else:
            return None
        if pokemon is None or hp_left(pokemon) <= 0 or not self.evolves_from(evolution_id, pokemon):
            return None
        if evolution_id in self.hand_ids or self.remaining_possible(evolution_id):
            return evolution_id
        return None

    def has_salvatore_target(self, evolution_id: Optional[int] = None) -> bool:
        return any(
            target is not None and (evolution_id is None or target == evolution_id)
            for target in (self.salvatore_target_evolution(pokemon) for pokemon in self.all_my_pokemon)
        )

    def is_salvatore_target(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        if data is None or data.cardType != CardType.POKEMON or data.basic or getattr(data, "skills", []):
            return False
        return self.has_salvatore_target(cid)

    def energies(self, pokemon: Optional[Pokemon]) -> List[int]:
        if pokemon is None:
            return []
        return [card.id for card in pokemon.energyCards]

    def energy_count(self, pokemon: Optional[Pokemon]) -> int:
        return len(self.energies(pokemon))

    def has_energy(self, pokemon: Optional[Pokemon], cid: int) -> bool:
        return cid in self.energies(pokemon)

    def energy_tokens(self, pokemon: Optional[Pokemon]) -> List[int]:
        return self.energy_tokens_as(pokemon, self.pid(pokemon))

    def energy_tokens_as(self, pokemon: Optional[Pokemon], card_id: Optional[int]) -> List[int]:
        tokens = []
        data = self.data(card_id)
        ignition_units = 1 if data is not None and data.basic else 3
        for cid in self.energies(pokemon):
            if cid == BASIC_WATER_ENERGY:
                tokens.append(EnergyType.WATER)
            elif cid == BASIC_DARK_ENERGY:
                tokens.append(EnergyType.DARKNESS)
            elif cid == IGNITION_ENERGY:
                tokens.extend([EnergyType.COLORLESS] * ignition_units)
            else:
                tokens.append(EnergyType.COLORLESS)
        return tokens

    def can_pay_attack(self, pokemon: Optional[Pokemon], attack: Optional[Any]) -> bool:
        if pokemon is None or attack is None:
            return False
        return can_pay_attack_with_tokens(attack, self.energy_tokens(pokemon))

    def best_damage(self, pokemon: Optional[Pokemon]) -> int:
        data = self.data(self.pid(pokemon))
        if data is None:
            return 0
        best = 0
        for attack_id in data.attacks:
            attack = self.attack(attack_id)
            if self.can_pay_attack(pokemon, attack):
                best = max(best, self.attack_damage(pokemon, attack))
        return best

    def attack_damage(self, attacker: Optional[Pokemon], attack: Optional[Any]) -> int:
        return self.attack_damage_for_card(self.pid(attacker), attack)

    def attack_damage_for_card(self, attacker_id: Optional[int], attack: Optional[Any]) -> int:
        if attack is None:
            return 0
        if attack.attackId == RESENTFUL_REFRAIN:
            return safe_int(self.opp.handCount) * 50
        return int(attack.damage)

    def attack_bypasses_ex_wall(self, attack: Any) -> bool:
        return attack is not None and attack.attackId == NEBULA_BEAM

    def attack_blocked_by_ex_wall_for_card(self, attacker_id: Optional[int], target: Optional[Pokemon], attack: Any) -> bool:
        if target is None or self.pid(target) not in EX_ATTACK_WALLS:
            return False
        if self.attack_bypasses_ex_wall(attack):
            return False
        data = self.data(attacker_id)
        return data is not None and (data.ex or data.megaEx)

    def active_evolution_attack_facts(self, option: Any) -> Tuple[ActiveEvolutionAttackFact, ...]:
        if option.type != OptionType.EVOLVE:
            return ()
        evolution_id = self.option_card(option)
        target = self.option_target(option)
        if target is None or target is not self.active or self.opp_active is None:
            return ()
        if not self.evolves_from(evolution_id, target):
            return ()
        player = getattr(self, "me", None)
        if getattr(player, "asleep", False) or getattr(player, "paralyzed", False):
            return ()
        data = self.data(evolution_id)
        if data is None:
            return ()

        tokens = tuple(self.energy_tokens_as(target, evolution_id))
        facts: List[ActiveEvolutionAttackFact] = []
        for attack_id in getattr(data, "attacks", ()):
            attack = self.attack(attack_id)
            if attack is None or not can_pay_attack_with_tokens(attack, tokens):
                continue
            blocked = self.attack_blocked_by_ex_wall_for_card(evolution_id, self.opp_active, attack)
            damage = 0 if blocked else self.attack_damage_for_card(evolution_id, attack)
            knockout = damage >= hp_left(self.opp_active)
            prizes_taken = self.prize_value(self.opp_active) if knockout else 0
            wins_game = prizes_taken >= self.my_prizes_left() if knockout else False
            facts.append(
                ActiveEvolutionAttackFact(
                    attack_id=int(attack.attackId),
                    supported=True,
                    damage=damage,
                    blocked=blocked,
                    knockout=knockout,
                    prizes_taken=prizes_taken,
                    wins_game=wins_game,
                    bench_damage=0 if blocked else attack_bench_damage_amount(attack),
                    bypasses_wall=self.attack_bypasses_ex_wall(attack) and self.pid(self.opp_active) in EX_ATTACK_WALLS,
                )
            )
        return tuple(facts)

    def legal_attack_options(self) -> List[Any]:
        attacks = []
        for _, option in self.iter_options():
            if option.attackId is None and option.type != OptionType.ATTACK:
                continue
            attack = self.attack(option.attackId)
            if attack is not None:
                attacks.append(attack)
        return attacks

    def can_attack_now(self) -> bool:
        return bool(self.legal_attack_options())

    def is_attack_choice_phase(self) -> bool:
        select_type = getattr(self.select, "type", None)
        if self.select.context == SelectContext.ATTACK or getattr(select_type, "name", None) == "ATTACK":
            return True
        option_types = {option.type for _, option in self.iter_options()}
        return bool(option_types) and option_types.issubset({OptionType.ATTACK, OptionType.END})

    def active_has_ignition(self) -> bool:
        return self.has_energy(self.active, IGNITION_ENERGY)

    def role_facts(self, pokemon: Optional[Pokemon]) -> RoleFacts:
        pid = self.pid(pokemon)
        data = self.data(pid)
        retreat_cost = int(getattr(data, "retreatCost", 0) or 0) if data is not None else 0
        basic = bool(getattr(data, "basic", False)) if data is not None else False
        mega = bool(getattr(data, "megaEx", False)) if data is not None else False
        ex = bool(getattr(data, "ex", False) or getattr(data, "megaEx", False)) if data is not None else False
        evolution = bool(data is not None and data.cardType == CardType.POKEMON and not basic)
        energy_count = self.energy_count(pokemon)
        attack_ready = any(
            self.can_pay_attack(pokemon, self.attack(attack_id))
            for attack_id in (getattr(data, "attacks", []) if data is not None else [])
        )
        key_attack_id = {
            MEGA_STARMIE_EX: NEBULA_BEAM,
            MEGA_YUKIMENOKO_EX: ABSOLUTE_SNOW,
            CINDERACE: TURBO_FLARE,
        }.get(pid)
        key_attack_ready = None
        if key_attack_id is not None:
            key_attack_ready = self.can_pay_attack(pokemon, self.attack(key_attack_id))
        if pokemon is self.active:
            current_position = "ACTIVE"
        elif pokemon in self.bench:
            current_position = "BENCH"
        else:
            current_position = "UNKNOWN"
        return RoleFacts(
            retreat_cost=retreat_cost,
            free_retreat=retreat_cost == 0,
            basic=basic,
            evolution=evolution,
            mega=mega,
            ex=ex,
            prize_value=self.prize_value(pokemon),
            energy_count=energy_count,
            attack_ready=attack_ready,
            key_attack_id=key_attack_id,
            key_attack_ready=key_attack_ready,
            role_completed=key_attack_ready if key_attack_id is not None else None,
            duplicate_count=sum(1 for target in self.all_my_pokemon if self.pid(target) == pid),
            bench_slot_cost=1 if current_position == "BENCH" else 0,
            current_position=current_position,
            pivot_candidate=retreat_cost == 0,
            ready_if_promoted=current_position == "BENCH" and attack_ready,
        )

    def my_prizes_left(self) -> int:
        return len(self.me.prize)

    def prize_value(self, pokemon: Optional[Pokemon]) -> int:
        data = self.data(self.pid(pokemon))
        if data is None:
            return 1
        if data.megaEx:
            return 3
        if data.ex:
            return 2
        return 1

    def active_can_ko(self, target: Optional[Pokemon] = None) -> bool:
        target = self.opp_active if target is None else target
        if target is None:
            return False
        return any(self.attack_damage(self.active, attack) >= hp_left(target) for attack in self.legal_attack_options())

    def active_in_danger(self) -> bool:
        if self.active is None:
            return False
        return hp_left(self.active) <= max(80, self.public_opp_active_damage() + 20)

    def public_opp_active_damage(self) -> int:
        return self.best_damage(self.opp_active)

    def public_lethal_next_turn(self) -> bool:
        if self.active is None or self.opp_active is None:
            return False
        return self.public_opp_active_damage() >= hp_left(self.active)

    def opp_max_damage(self) -> int:
        return max([self.best_damage(pokemon) for pokemon in self.all_opp_pokemon] + [0])

    def opponent_has_bench_damage_threat(self) -> bool:
        for pokemon in self.all_opp_pokemon:
            if self.card_or_evolution_has_bench_damage_threat(self.pid(pokemon)):
                return True
        return False

    def needs_shaymin_bench_guard(self) -> bool:
        return self.opponent_has_bench_damage_threat() or self.opp_has(DREEPY_LINE | {DRAGAPULT_EX} | MARIE_LINE)

    def opponent_profile(self) -> str:
        if self.opp_has(LUCARIO_LINE):
            return "LUCARIO"
        if self.opp_has(DURALUDON_LINE):
            return "STEEL"
        if self.opp_has(CRUSTLE_LINE) or self.opp_has(EX_ATTACK_WALLS):
            return "WALL"
        if self.opp_has(ALAKAZAM_LINE):
            return "ALAKAZAM"
        if self.opp_has(DREEPY_LINE | {DRAGAPULT_EX}) or self.opp_has(MARIE_LINE):
            return "BENCH_DAMAGE"
        return "GENERAL"

    def plan(self) -> Dict[str, Any]:
        return MATCHUP_PLANS[self.opponent_profile()]

    def plan_axis(self) -> str:
        return str(self.plan()["main_axis"])

    def plan_setup_cards(self) -> set[int]:
        return set(self.plan()["setup_cards"])

    def plan_boss_targets(self) -> set[int]:
        return set(self.plan()["boss_targets"])

    def plan_pressure_targets(self) -> set[int]:
        return set(self.plan()["must_pressure"])

    def plan_attack_ids(self) -> set[int]:
        return set(self.plan()["attack_ids"])

    def wants_starmie_axis(self) -> bool:
        return self.plan_axis().startswith("STARMIE") or self.count_in_play(HITODEMAN) > 0

    def needs_basic(self) -> bool:
        return self.bench_space > 0 and (
            self.count_in_play(HITODEMAN) == 0
            or len(self.bench) <= 1
            or self.count_in_play(YUKIWARASHI) == 0 and self.opponent_profile() == "ALAKAZAM"
        )

    def needs_mega_starmie(self) -> bool:
        return self.count_in_play(HITODEMAN) > 0 and self.count_in_play(MEGA_STARMIE_EX) == 0

    def needs_mega_yuki(self) -> bool:
        return self.count_in_play(YUKIWARASHI) > 0 and self.count_in_play(MEGA_YUKIMENOKO_EX) == 0

    def starmie_needs_energy(self) -> bool:
        return any(self.pid(p) == MEGA_STARMIE_EX and self.energy_count(p) < 3 for p in self.all_my_pokemon) or (
            self.count_in_play(HITODEMAN) > 0 and self.count_in_play(MEGA_STARMIE_EX) == 0
        )

    def cinderace_can_accelerate(self) -> bool:
        return self.pid(self.active) == CINDERACE and any(attack.attackId == TURBO_FLARE for attack in self.legal_attack_options())

    def has_bench_energy_receiver(self) -> bool:
        return any(self.pid(p) in MAIN_LINE and self.energy_count(p) < 3 for p in self.bench)

    def wally_live(self) -> bool:
        if self.state.supporterPlayed:
            return False
        for pokemon in self.all_my_pokemon:
            if self.pid(pokemon) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and damage_on(pokemon) >= 100:
                if pokemon is self.active or hp_left(pokemon) <= self.opp_max_damage() + 40:
                    return True
        return False

    def salvatore_live(self) -> bool:
        return not self.state.supporterPlayed and self.has_salvatore_target()

    def can_use_supporter(self, cid: int) -> bool:
        return self.is_supporter(cid) and not self.state.supporterPlayed

    def lillie_effect_facts(self) -> LillieEffectFacts:
        hand_size = len(self.hand_ids)
        shuffle_count = max(0, hand_size - (1 if LILLIE_DETERMINATION in self.hand_ids else 0))
        draw_count = 8 if self.my_prizes_left() == 6 else 6
        return LillieEffectFacts(hand_size=hand_size, shuffle_count=shuffle_count, draw_count=draw_count)

    def has_tool_scrapper_target(self) -> bool:
        return any(getattr(pokemon, "tools", []) for pokemon in self.all_my_pokemon + self.all_opp_pokemon)

    def hand_card_activity(self, cid: int, occurrence: int = 1, total_count: int = 1) -> str:
        if cid == CINDERACE:
            if occurrence > 1 or self.count_in_play(CINDERACE) > 0 or self.bench_space <= 0:
                return HAND_ACTIVITY_LOW
            return HAND_ACTIVITY_LIVE_NOW
        if cid in {HITODEMAN, YUKIWARASHI, SHAYMIN, YVELTAL}:
            if self.bench_space <= 0:
                return HAND_ACTIVITY_LOW
            if cid == SHAYMIN and self.needs_shaymin_bench_guard():
                return HAND_ACTIVITY_LIVE_NOW
            if cid in {HITODEMAN, YUKIWARASHI} and self.count_in_play(cid) == 0:
                return HAND_ACTIVITY_LIVE_NOW
            return HAND_ACTIVITY_KEEP
        if cid == MEGA_STARMIE_EX:
            return HAND_ACTIVITY_LIVE_NOW if self.count_in_play(HITODEMAN) > 0 else HAND_ACTIVITY_LOW
        if cid == MEGA_YUKIMENOKO_EX:
            return HAND_ACTIVITY_LIVE_NOW if self.count_in_play(YUKIWARASHI) > 0 else HAND_ACTIVITY_LOW
        if cid in {BASIC_WATER_ENERGY, BASIC_DARK_ENERGY, IGNITION_ENERGY}:
            return HAND_ACTIVITY_KEEP if self.starmie_needs_energy() or self.has_bench_energy_receiver() else HAND_ACTIVITY_LOW
        if cid == SALVATORE:
            return HAND_ACTIVITY_LIVE_NOW if self.salvatore_live() else HAND_ACTIVITY_LOW
        if cid == WALLY_COMPASSION:
            return HAND_ACTIVITY_LIVE_NOW if self.wally_live() else HAND_ACTIVITY_LOW
        if cid == CRISPIN:
            if self.can_use_supporter(CRISPIN) and (self.starmie_needs_energy() or self.pid(self.active) == CINDERACE):
                return HAND_ACTIVITY_LIVE_NOW
            return HAND_ACTIVITY_LOW
        if cid == LILLIE_DETERMINATION:
            if not self.can_use_supporter(LILLIE_DETERMINATION):
                return HAND_ACTIVITY_LOW
            if len(self.hand_ids) <= 2 or self.needs_basic() or self.needs_mega_starmie() or self.needs_mega_yuki():
                return HAND_ACTIVITY_LIVE_NOW
            return HAND_ACTIVITY_KEEP
        if cid == POKEGEAR:
            facts = self.pokegear_supporter_facts()
            if not self.state.supporterPlayed and (facts.live_supporter_count > 0 or facts.supporter_remaining_possible):
                return HAND_ACTIVITY_LIVE_NOW
            return HAND_ACTIVITY_LOW
        if cid == POKE_PAD:
            return HAND_ACTIVITY_LIVE_NOW if self.needs_basic() else HAND_ACTIVITY_LOW
        if cid == POFIN:
            return HAND_ACTIVITY_LIVE_NOW if self.bench_space > 0 and self.needs_basic() else HAND_ACTIVITY_LOW
        if cid == HYPERBALL:
            return HAND_ACTIVITY_LIVE_NOW if len(self.hand_ids) >= 3 and (self.needs_basic() or self.needs_mega_starmie() or self.needs_mega_yuki()) else HAND_ACTIVITY_KEEP
        if cid == TANKER:
            return HAND_ACTIVITY_LIVE_NOW if any(card_id in MAIN_LINE for card_id in self.discard_ids) else HAND_ACTIVITY_LOW
        if cid == ENERGY_SWITCH:
            return HAND_ACTIVITY_KEEP if self.starmie_needs_energy() else HAND_ACTIVITY_LOW
        if cid == BEFEHL_VON_BOSS:
            return HAND_ACTIVITY_LIVE_NOW if self.can_use_supporter(BEFEHL_VON_BOSS) and bool(self.opp_bench) else HAND_ACTIVITY_LOW
        if cid == TOOL_SCRAPPER:
            return HAND_ACTIVITY_LIVE_NOW if self.has_tool_scrapper_target() else HAND_ACTIVITY_LOW
        if cid == HERO_CAPE:
            return HAND_ACTIVITY_LIVE_NOW if any(self.pid(pokemon) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not getattr(pokemon, "tools", []) for pokemon in self.all_my_pokemon) else HAND_ACTIVITY_LOW
        if cid == SURFING_BEACH:
            return HAND_ACTIVITY_LIVE_NOW if self.has_foreign_stadium() else HAND_ACTIVITY_KEEP
        if cid == MEGA_SIGNAL:
            return HAND_ACTIVITY_LIVE_NOW if self.needs_mega_starmie() or self.needs_mega_yuki() else HAND_ACTIVITY_LOW
        return HAND_ACTIVITY_KEEP

    def hand_activity_facts(self) -> HandActivityFacts:
        totals = Counter(self.hand_ids)
        seen = Counter()
        activities = []
        for cid in self.hand_ids:
            seen[cid] += 1
            activity = self.hand_card_activity(cid, seen[cid], totals[cid])
            activities.append((cid, activity))
        counts = Counter(activity for _, activity in activities)
        hand_size = len(self.hand_ids)
        low_count = counts[HAND_ACTIVITY_LOW]
        return HandActivityFacts(
            hand_size=hand_size,
            live_now_count=counts[HAND_ACTIVITY_LIVE_NOW],
            keep_count=counts[HAND_ACTIVITY_KEEP],
            low_activity_count=low_count,
            low_activity_ratio=low_count / max(1, hand_size),
            activities=tuple(activities),
            lillie_effect=self.lillie_effect_facts(),
        )

    def basic_energy_remaining_possible(self, energy_id: int) -> bool:
        if self.deck_view:
            return energy_id in self.deck_ids
        known_out = self.hand_ids.count(energy_id) + self.discard_ids.count(energy_id)
        known_out += sum(self.energies(pokemon).count(energy_id) for pokemon in self.all_my_pokemon)
        return known_out < DECK.count(energy_id)

    def attack_energy_gap(self, attack: Optional[Any], tokens: Sequence[Any]) -> AttackEnergyGap:
        if attack is None:
            return AttackEnergyGap(attack_id=-1, ready=False, missing_units=999, missing_types=())
        requirements = list(getattr(attack, "energies", []) or [])
        token_counts = Counter(tokens)
        missing = []
        used_tokens = 0
        for energy_type, required in Counter(energy for energy in requirements if energy != EnergyType.COLORLESS).items():
            paid = min(token_counts[energy_type], required)
            used_tokens += paid
            missing.extend([energy_type] * (required - paid))
        colorless_required = sum(1 for energy in requirements if energy == EnergyType.COLORLESS)
        colorless_available = max(0, len(tokens) - used_tokens)
        colorless_missing = max(0, colorless_required - colorless_available)
        missing.extend([EnergyType.COLORLESS] * colorless_missing)
        return AttackEnergyGap(
            attack_id=int(attack.attackId),
            ready=not missing,
            missing_units=len(missing),
            missing_types=tuple(missing),
        )

    def active_energy_facts(self) -> ActiveEnergyFacts:
        active_id = self.pid(self.active)
        data = self.data(active_id)
        energy_cards = tuple(self.energies(self.active))
        tokens = tuple(self.energy_tokens(self.active))
        payable = []
        unpayable = []
        gaps = []
        for attack_id in getattr(data, "attacks", []) if data is not None else []:
            attack = self.attack(attack_id)
            gap = self.attack_energy_gap(attack, tokens)
            gaps.append(gap)
            if gap.ready:
                payable.append(attack_id)
            else:
                unpayable.append(attack_id)
        key_attack_id = {
            MEGA_STARMIE_EX: NEBULA_BEAM,
            MEGA_YUKIMENOKO_EX: ABSOLUTE_SNOW,
            CINDERACE: TURBO_FLARE,
        }.get(active_id)
        key_gap = next((gap for gap in gaps if gap.attack_id == key_attack_id), None)
        return ActiveEnergyFacts(
            active_id=active_id,
            energy_cards=energy_cards,
            energy_tokens=tokens,
            payable_attack_ids=tuple(payable),
            unpayable_attack_ids=tuple(unpayable),
            attack_gaps=tuple(gaps),
            key_attack_id=key_attack_id,
            key_attack_ready=bool(key_gap and key_gap.ready),
            key_attack_missing_units=key_gap.missing_units if key_gap is not None else 0,
            key_attack_missing_types=key_gap.missing_types if key_gap is not None else (),
            water_remaining_possible=self.basic_energy_remaining_possible(BASIC_WATER_ENERGY),
            dark_remaining_possible=self.basic_energy_remaining_possible(BASIC_DARK_ENERGY),
        )

    def _supporter_live_for_pokegear(self, cid: int) -> bool:
        if not self.can_use_supporter(cid):
            return False
        if cid == SALVATORE:
            return self.salvatore_live()
        if cid == WALLY_COMPASSION:
            return self.wally_live()
        if cid == CRISPIN:
            return self.starmie_needs_energy() or self.pid(self.active) == CINDERACE
        if cid == LILLIE_DETERMINATION:
            return len(self.hand_ids) <= 2 or self.needs_basic() or self.needs_mega_starmie() or self.needs_mega_yuki()
        if cid == BEFEHL_VON_BOSS:
            return bool(self.opp_bench)
        if cid == HILDA:
            return self.needs_mega_starmie() or self.needs_mega_yuki()
        return False

    def pokegear_supporter_facts(self) -> PokegearSupporterFacts:
        supporter_ids = {cid for cid in DECK if self.is_supporter(cid)}
        deck_is_public = bool(self.deck_view)
        if deck_is_public:
            known_supporter_ids = [cid for cid in self.deck_ids if cid in supporter_ids]
            live_supporter_count = sum(1 for cid in known_supporter_ids if self._supporter_live_for_pokegear(cid))
            known_supporter_count = len(known_supporter_ids)
            return PokegearSupporterFacts(
                deck_is_public=True,
                known_supporter_count=known_supporter_count,
                live_supporter_count=live_supporter_count,
                dead_supporter_count=known_supporter_count - live_supporter_count,
                supporter_remaining_possible=known_supporter_count > 0,
                no_target_confirmed=live_supporter_count == 0,
            )
        known_out = sum(self.hand_ids.count(cid) + self.discard_ids.count(cid) for cid in supporter_ids)
        total_supporters = sum(DECK.count(cid) for cid in supporter_ids)
        remaining_possible = known_out < total_supporters
        return PokegearSupporterFacts(
            deck_is_public=False,
            known_supporter_count=known_out,
            live_supporter_count=0,
            dead_supporter_count=known_out,
            supporter_remaining_possible=remaining_possible,
            no_target_confirmed=not remaining_possible,
        )

    def has_foreign_stadium(self) -> bool:
        return bool(self.state.stadium) and (not self.state.stadium or self.state.stadium[0].id != SURFING_BEACH)


class ImmediateOutcomeEvaluator:
    def __init__(self, board: BoardView):
        self.b = board

    def evaluate_attack(self, option: Any) -> ImmediateOutcome:
        attack = self.b.attack(option.attackId)
        attacker = self.b.active
        target = self.b.opp_active
        reasons: List[str] = []
        if attack is None or attacker is None or target is None:
            return ImmediateOutcome(supported=False, reasons=("missing_attack_state",))

        target_id = self.b.pid(target)
        target_serial = getattr(target, "serial", None)
        bypasses_wall = self._bypasses_ex_wall(attack)
        blocked = self._blocked_by_ex_wall(attacker, target, attack)
        if bypasses_wall and target_id in EX_ATTACK_WALLS:
            reasons.append("bypasses_ex_wall")
        if blocked:
            reasons.append("blocked_ex_wall")

        damage = 0 if blocked else self.b.attack_damage(attacker, attack)
        knockout = damage >= hp_left(target)
        prizes_taken = self.b.prize_value(target) if knockout else 0
        wins_game = prizes_taken >= self.b.my_prizes_left() if knockout else False
        if knockout:
            reasons.append("knockout")
        if wins_game:
            reasons.append("wins_game")

        # The first stage handles only a single active-target KO.
        # Unsupported here: bench/multiple KOs, damage counter KOs, prize modifiers,
        # and attack effects that KO a separate target.
        return ImmediateOutcome(
            blocked=blocked,
            damage=damage,
            knockout=knockout,
            prizes_taken=prizes_taken,
            wins_game=wins_game,
            bypasses_wall=bypasses_wall and target_id in EX_ATTACK_WALLS,
            target_id=target_id,
            target_serial=target_serial,
            reasons=tuple(reasons),
        )

    def evaluate_attach(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.ATTACH:
            return ImmediateOutcome(supported=False, reasons=("unsupported_attach_option",))
        card_id = self.b.option_card(option)
        target = self.b.option_target(option)
        if card_id is None or target is None:
            return ImmediateOutcome(supported=False, reasons=("missing_attach_state",))

        extra_tokens = energy_tokens_for_attach(card_id, target)
        if extra_tokens is None:
            return ImmediateOutcome(supported=False, reasons=("unsupported_attach_energy",))

        data = self.b.data(self.b.pid(target))
        if data is None:
            return ImmediateOutcome(supported=False, reasons=("missing_attach_state",))

        before_tokens = tuple(self.b.energy_tokens(target))
        after_tokens = before_tokens + extra_tokens
        before_ids = self._energy_payable_attack_ids(data.attacks, before_tokens)
        after_ids = self._energy_payable_attack_ids(data.attacks, after_tokens)
        enabled_ids = tuple(attack_id for attack_id in after_ids if attack_id not in before_ids)

        reasons: List[str] = []
        if enabled_ids:
            reasons.append("enables_attack")
        else:
            reasons.append("no_new_attack")
        if NEBULA_BEAM in enabled_ids:
            reasons.append("enables_nebula_beam")
        immediate_attack_ids = self._unblocked_attack_ids(target, enabled_ids) if target is self.b.active else ()
        if card_id == IGNITION_ENERGY and target is self.b.active and enabled_ids and immediate_attack_ids:
            reasons.append("ignition_immediate_attack")

        return ImmediateOutcome(
            enables_attack=bool(enabled_ids),
            enabled_attack_ids=enabled_ids,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def evaluate_boss_target(self, target: Optional[Pokemon]) -> ImmediateOutcome:
        attacker = self.b.active
        if attacker is None or target is None or target not in self.b.opp_bench:
            return ImmediateOutcome(supported=False, reasons=("missing_boss_state",))
        data = self.b.data(self.b.pid(attacker))
        if data is None:
            return ImmediateOutcome(supported=False, reasons=("missing_boss_state",))

        attack_ids = self._energy_payable_attack_ids(data.attacks, self.b.energy_tokens(attacker))
        outcomes = [self._boss_attack_outcome(attacker, target, attack_id) for attack_id in attack_ids]
        effective_outcomes = [outcome for outcome in outcomes if outcome.supported and not outcome.blocked]
        if not effective_outcomes:
            return self._boss_no_effective_attack(target)

        best = max(
            effective_outcomes,
            key=lambda outcome: (
                outcome.wins_game,
                outcome.knockout,
                outcome.prizes_taken,
                not outcome.blocked,
                outcome.damage,
            ),
        )

        target_id = self.b.pid(target)
        avoids_wall = (
            self.b.opp_active is not None
            and self.b.pid(self.b.opp_active) in EX_ATTACK_WALLS
            and target_id not in EX_ATTACK_WALLS
        )
        # breaks_engine means this Boss target is an important engine piece from
        # MATCHUP_PLANS or existing engine sets, not that it has already been KO'd.
        breaks_engine = target_id in self.b.plan_boss_targets() or target_id in (LUCARIO_ENGINE | CRUSTLE_LINE | DREEPY_LINE)
        reasons = ["boss_target"]
        if best.wins_game:
            reasons.append("boss_wins_game")
        if best.knockout:
            reasons.append("boss_knockout")
        if best.prizes_taken:
            reasons.append("boss_takes_prizes")
        if avoids_wall:
            reasons.append("boss_avoids_wall")
        if breaks_engine:
            reasons.append("boss_breaks_engine")
        if best.damage > 0 and not best.knockout:
            reasons.append("boss_damage_only")

        return ImmediateOutcome(
            damage=best.damage,
            knockout=best.knockout,
            prizes_taken=best.prizes_taken,
            wins_game=best.wins_game,
            bypasses_wall=best.bypasses_wall,
            avoids_wall=avoids_wall,
            breaks_engine=breaks_engine,
            target_id=target_id,
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def _energy_payable_attack_ids(self, attack_ids: Sequence[int], tokens: Sequence[Any]) -> Tuple[int, ...]:
        payable: List[int] = []
        for attack_id in attack_ids:
            attack = self.b.attack(attack_id)
            if can_pay_attack_with_tokens(attack, tokens):
                payable.append(int(attack_id))
        return tuple(payable)

    def _unblocked_attack_ids(self, attacker: Pokemon, attack_ids: Sequence[int]) -> Tuple[int, ...]:
        if self.b.opp_active is None:
            return ()
        unblocked: List[int] = []
        for attack_id in attack_ids:
            attack = self.b.attack(attack_id)
            if attack is not None and not self._blocked_by_ex_wall(attacker, self.b.opp_active, attack):
                unblocked.append(int(attack_id))
        return tuple(unblocked)

    def has_energy_payable_unblocked_active_attack(self) -> bool:
        attacker = self.b.active
        data = self.b.data(self.b.pid(attacker))
        if attacker is None or data is None:
            return False
        for attack_id in data.attacks:
            if self.active_attack_is_payable_unblocked(attack_id):
                return True
        return False

    def active_attack_is_payable_unblocked(self, attack_id: int) -> bool:
        player = getattr(self.b, "me", None)
        if getattr(player, "asleep", False) or getattr(player, "paralyzed", False):
            return False
        attacker = self.b.active
        target = self.b.opp_active
        attack = self.b.attack(attack_id)
        if attacker is None or target is None or attack is None:
            return False
        return self.b.can_pay_attack(attacker, attack) and not self._blocked_by_ex_wall(attacker, target, attack)

    def _boss_attack_outcome(self, attacker: Pokemon, target: Pokemon, attack_id: int) -> ImmediateOutcome:
        attack = self.b.attack(attack_id)
        if attack is None:
            return ImmediateOutcome(supported=False, reasons=("boss_no_effective_attack",))
        blocked = self._blocked_by_ex_wall(attacker, target, attack)
        damage = 0 if blocked else self.b.attack_damage(attacker, attack)
        knockout = damage >= hp_left(target)
        prizes_taken = self.b.prize_value(target) if knockout else 0
        wins_game = prizes_taken >= self.b.my_prizes_left() if knockout else False
        return ImmediateOutcome(
            blocked=blocked,
            damage=damage,
            knockout=knockout,
            prizes_taken=prizes_taken,
            wins_game=wins_game,
            bypasses_wall=self._bypasses_ex_wall(attack) and self.b.pid(target) in EX_ATTACK_WALLS,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
        )

    def _boss_no_effective_attack(self, target: Pokemon) -> ImmediateOutcome:
        return ImmediateOutcome(
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=("boss_target", "boss_no_effective_attack"),
        )

    def evaluate_tool_scrapper_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != TOOL_SCRAPPER:
            return ImmediateOutcome(supported=False, reasons=("tool_scrapper_no_target",))
        outcomes = [
            self.evaluate_tool_scrapper_target(pokemon, index)
            for pokemon in self.b.all_opp_pokemon
            for index, _ in enumerate(pokemon.tools)
        ]
        outcomes = [outcome for outcome in outcomes if outcome.supported]
        if not outcomes:
            return ImmediateOutcome(supported=False, reasons=("tool_scrapper_no_target",))
        return max(outcomes, key=self._tool_scrapper_priority)

    def evaluate_tool_scrapper_target(
        self,
        target: Optional[Pokemon],
        tool_index: Optional[int] = None,
    ) -> ImmediateOutcome:
        if target is None or target not in self.b.all_opp_pokemon:
            return ImmediateOutcome(supported=False, reasons=("tool_scrapper_no_target",))
        tool = self._selected_tool(target, tool_index)
        if tool is None:
            return ImmediateOutcome(supported=False, target_id=self.b.pid(target), target_serial=getattr(target, "serial", None), reasons=("tool_scrapper_no_target",))

        tool_id = int(tool.id)
        before_hp = hp_left(target)
        after_hp = max(0, before_hp - 100) if tool_id == HERO_CAPE else before_hp
        before_damage = self._best_unblocked_damage_to(target)
        attack_ko_before = before_damage >= before_hp
        attack_ko_after = before_damage >= after_hp
        removal_knockout = tool_id == HERO_CAPE and after_hp <= 0
        enables_knockout = (not removal_knockout) and (not attack_ko_before) and attack_ko_after
        prizes_taken = self.b.prize_value(target) if removal_knockout else 0
        wins_game = prizes_taken >= self.b.my_prizes_left() if removal_knockout else False

        reasons = ["tool_scrapper_target", "removes_tool"]
        if tool_id == HERO_CAPE:
            reasons.append("removes_hero_cape")
            reasons.append("removes_key_tool")
        if enables_knockout:
            reasons.append("tool_scrapper_enables_ko")
        if removal_knockout:
            reasons.append("tool_removal_causes_knockout")
        if wins_game:
            reasons.append("wins_game")
        if not enables_knockout and tool_id != HERO_CAPE:
            reasons.append("tool_scrapper_no_immediate_gain")

        return ImmediateOutcome(
            damage=0,
            knockout=removal_knockout,
            prizes_taken=prizes_taken,
            wins_game=wins_game,
            removes_tool=True,
            enables_knockout=enables_knockout,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def _selected_tool(self, target: Pokemon, tool_index: Optional[int]) -> Optional[Any]:
        tools = target.tools
        if not tools:
            return None
        if tool_index is not None:
            return tools[tool_index] if 0 <= tool_index < len(tools) else None
        if len(tools) == 1:
            return tools[0]
        return None

    def _best_unblocked_damage_to(self, target: Pokemon) -> int:
        attacker = self.b.active
        if attacker is None:
            return 0
        data = self.b.data(self.b.pid(attacker))
        if data is None:
            return 0
        best = 0
        for attack_id in self._energy_payable_attack_ids(data.attacks, self.b.energy_tokens(attacker)):
            attack = self.b.attack(attack_id)
            if attack is not None and not self._blocked_by_ex_wall(attacker, target, attack):
                best = max(best, self.b.attack_damage(attacker, attack))
        return best

    def _tool_scrapper_priority(self, outcome: ImmediateOutcome) -> Tuple[Any, ...]:
        return (
            outcome.wins_game,
            outcome.knockout,
            outcome.prizes_taken,
            outcome.enables_knockout,
            "removes_hero_cape" in outcome.reasons,
            "removes_key_tool" in outcome.reasons,
            outcome.removes_tool,
        )

    def evaluate_retreat(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.RETREAT:
            return ImmediateOutcome(supported=False, reasons=("unsupported_retreat_option",))
        active = self.b.active
        if active is None:
            return ImmediateOutcome(supported=False, reasons=("retreat_no_active",))
        target = self.b.option_target(option)
        if target is not None:
            return self.evaluate_switch_target(target, "retreat")

        cost = self._effective_retreat_cost(active)
        important_loss = self._possible_important_energy_loss(active, cost)
        active_damage = self._best_unblocked_damage_from(active)
        reasons = ["retreat", "retreat_cost"]
        if important_loss > 0:
            reasons.append("important_energy_loss")
        if active_damage > 0:
            reasons.append("retreat_from_ready_attacker")
        if self._survival_retreat_reason(active):
            reasons.append("survival_retreat")
        if not self.b.bench:
            reasons.append("retreat_no_target")
        best_target = self._best_retreat_candidate_summary()
        if best_target is not None:
            # recommended_target_* identify the best visible follow-up candidate only;
            # the RETREAT option has not switched the board yet.
            for reason in best_target.reasons:
                if reason in {
                    "retreat_enables_attack",
                    "switch_enables_knockout",
                    "switch_enables_win",
                    "role_handoff",
                    "retreat_improves_damage",
                } and reason not in reasons:
                    reasons.append(reason)
            if "zero_energy_mega_wall" in best_target.reasons and all(
                "zero_energy_mega_wall" in self.evaluate_switch_target(pokemon, "retreat").reasons
                for pokemon in self.b.bench
            ):
                reasons.append("zero_energy_mega_wall")
        if self.b.pid(active) == CINDERACE and self.b.cinderace_can_accelerate() and self.b.has_bench_energy_receiver():
            reasons.append("retreat_from_ready_attacker")

        return ImmediateOutcome(
            enables_attack=bool(best_target and best_target.enables_attack),
            enables_knockout=bool(best_target and best_target.enables_knockout),
            retreat_energy_cost=cost,
            important_energy_loss=important_loss,
            improves_damage=bool(best_target and best_target.improves_damage),
            recommended_target_id=best_target.target_id if best_target is not None else None,
            recommended_target_serial=best_target.target_serial if best_target is not None else None,
            reasons=tuple(reasons),
        )

    def evaluate_switch_target(self, target: Optional[Pokemon], source: str) -> ImmediateOutcome:
        if source not in {"retreat", "surfing_beach"}:
            return ImmediateOutcome(supported=False, reasons=("unsupported_switch_source",))
        active = self.b.active
        if active is None or target is None or target not in self.b.bench:
            return ImmediateOutcome(supported=False, reasons=("retreat_no_target",))
        if source == "surfing_beach" and not self._can_surfing_beach_switch(active, target):
            return ImmediateOutcome(
                supported=False,
                target_id=self.b.pid(target),
                target_serial=getattr(target, "serial", None),
                reasons=("surfing_beach_switch", "unsupported_switch_target"),
            )

        active_damage = self._best_unblocked_damage_from(active)
        target_damage = self._best_unblocked_damage_from(target)
        target_id = self.b.pid(target)
        cost = 0 if source == "surfing_beach" else self._effective_retreat_cost(active)
        important_loss = 0 if source == "surfing_beach" else self._possible_important_energy_loss(active, cost)
        enables_attack = target_damage > 0 and active_damage == 0
        improves_damage = target_damage > active_damage
        active_can_ko = self.b.opp_active is not None and active_damage >= hp_left(self.b.opp_active)
        target_can_ko = self.b.opp_active is not None and target_damage >= hp_left(self.b.opp_active)
        enables_knockout = not active_can_ko and target_can_ko
        enables_win = enables_knockout and self.b.prize_value(self.b.opp_active) >= self.b.my_prizes_left()
        survival = self._survival_retreat_reason(active)
        role_handoff = self._role_handoff(active, target, target_damage)

        reasons = ["switch_target"]
        if source == "surfing_beach":
            reasons.append("surfing_beach_switch")
        else:
            reasons.append("retreat")
            reasons.append("retreat_cost")
        if important_loss > 0:
            reasons.append("important_energy_loss")
        if enables_attack:
            reasons.append("retreat_enables_attack")
        if enables_knockout:
            reasons.append("switch_enables_knockout")
        if enables_win:
            reasons.append("switch_enables_win")
        if role_handoff:
            reasons.append("role_handoff")
        if improves_damage:
            reasons.append("retreat_improves_damage")
        else:
            reasons.append("retreat_no_damage_improvement")
        if active_damage > 0 and not improves_damage and not enables_knockout and not survival and not role_handoff:
            reasons.append("retreat_from_ready_attacker")
        if survival:
            reasons.append("survival_retreat")
        if self._zero_energy_mega_wall(target, target_damage) and not survival and not enables_knockout:
            reasons.append("zero_energy_mega_wall")
        if self.b.pid(active) == CINDERACE and self.b.cinderace_can_accelerate() and self.b.has_bench_energy_receiver():
            reasons.append("retreat_from_ready_attacker")

        return ImmediateOutcome(
            damage=0,
            knockout=False,
            prizes_taken=0,
            wins_game=False,
            enables_attack=enables_attack,
            enables_knockout=enables_knockout,
            retreat_energy_cost=cost,
            important_energy_loss=important_loss,
            improves_damage=improves_damage,
            target_id=target_id,
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def evaluate_retreat_energy_selection(self, option: Any) -> ImmediateOutcome:
        target = self.b.option_target(option) or self.b.active
        if target is None:
            return ImmediateOutcome(supported=False, reasons=("retreat_energy_no_target",))
        energy_id = self._selected_energy_id(target, option)
        if energy_id is None:
            return ImmediateOutcome(supported=False, reasons=("retreat_energy_no_target",))
        important_loss = 1 if self._is_important_energy_card(target, energy_id) else 0
        reasons = ["retreat", "retreat_cost"]
        if important_loss:
            reasons.append("important_energy_loss")
        return ImmediateOutcome(
            important_energy_loss=important_loss,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def evaluate_attack_effect_target(self, option: Any) -> ImmediateOutcome:
        if self.b.select.context != SelectContext.DAMAGE:
            return ImmediateOutcome(supported=False, reasons=("unsupported_attack_effect",))
        if self._recent_my_attack_id() != JETTING_BLOW:
            return ImmediateOutcome(supported=False, reasons=("unsupported_attack_effect",))
        target = self.b.option_target(option)
        if target is None or target not in self.b.opp_bench:
            return ImmediateOutcome(supported=False, reasons=("unsupported_attack_effect",))

        damage = 50
        knockout = damage >= hp_left(target)
        prizes_taken = self.b.prize_value(target) if knockout else 0
        reasons = ["attack_effect_target", "jetting_blow_secondary_damage"]
        if knockout:
            reasons.append("knockout")
        if self.b.pid(target) in self.b.plan_pressure_targets() or self.b.pid(target) in self.b.plan_boss_targets():
            reasons.append("effect_hits_engine")

        return ImmediateOutcome(
            damage=damage,
            knockout=knockout,
            prizes_taken=prizes_taken,
            wins_game=False,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def _effective_retreat_cost(self, pokemon: Optional[Pokemon]) -> int:
        data = self.b.data(self.b.pid(pokemon))
        if data is None:
            return 0
        return max(0, safe_int(getattr(data, "retreatCost", 0)))

    def _possible_important_energy_loss(self, pokemon: Pokemon, cost: int) -> int:
        if cost <= 0:
            return 0
        important_cards = sum(1 for card in pokemon.energyCards if self._is_important_energy_card(pokemon, int(card.id)))
        nonimportant_capacity = sum(1 for card in pokemon.energyCards if not self._is_important_energy_card(pokemon, int(card.id)))
        return min(important_cards, max(0, cost - nonimportant_capacity))

    def _best_retreat_candidate_summary(self) -> Optional[ImmediateOutcome]:
        candidates = [self.evaluate_switch_target(pokemon, "retreat") for pokemon in self.b.bench]
        candidates = [candidate for candidate in candidates if candidate.supported]
        if not candidates:
            return None
        return max(candidates, key=self._retreat_candidate_key)

    def _retreat_candidate_key(self, outcome: ImmediateOutcome) -> Tuple[Any, ...]:
        return (
            "switch_enables_win" in outcome.reasons,
            outcome.enables_knockout,
            outcome.enables_attack,
            "role_handoff" in outcome.reasons,
            outcome.improves_damage,
            "zero_energy_mega_wall" not in outcome.reasons,
            -outcome.important_energy_loss,
        )

    def _is_important_energy_card(self, pokemon: Pokemon, card_id: int) -> bool:
        if card_id in {BASIC_WATER_ENERGY, IGNITION_ENERGY}:
            return True
        if card_id != BASIC_DARK_ENERGY:
            return False
        data = self.b.data(self.b.pid(pokemon))
        if data is None:
            return False
        for attack_id in data.attacks:
            attack = self.b.attack(attack_id)
            if attack is not None and EnergyType.DARKNESS in getattr(attack, "energies", []):
                return True
        return False

    def _selected_energy_id(self, target: Pokemon, option: Any) -> Optional[int]:
        serial = getattr(option, "serial", None)
        if serial is not None:
            for card in target.energyCards:
                if getattr(card, "serial", None) == serial:
                    return int(card.id)
        energy_index = getattr(option, "energyIndex", None)
        if energy_index is not None and 0 <= energy_index < len(target.energyCards):
            return int(target.energyCards[energy_index].id)
        card_id = self.b.option_card(option)
        return None if card_id is None else int(card_id)

    def _best_unblocked_damage_from(self, attacker: Optional[Pokemon]) -> int:
        data = self.b.data(self.b.pid(attacker))
        if data is None:
            return 0
        best = 0
        for attack_id in data.attacks:
            attack = self.b.attack(attack_id)
            if attack is None or not self.b.can_pay_attack(attacker, attack):
                continue
            if self.b.opp_active is not None and self._blocked_by_ex_wall(attacker, self.b.opp_active, attack):
                continue
            best = max(best, self.b.attack_damage(attacker, attack))
        return best

    def _can_surfing_beach_switch(self, active: Pokemon, target: Pokemon) -> bool:
        return self.b.pid(active) in WATER_POKEMON and self.b.pid(target) in WATER_POKEMON

    def _survival_retreat_reason(self, active: Pokemon) -> bool:
        return self.b.active_in_danger() or self.b.public_lethal_next_turn()

    def _role_handoff(self, active: Pokemon, target: Pokemon, target_damage: int) -> bool:
        return (
            self.b.pid(active) in {CINDERACE, YVELTAL, SHAYMIN}
            and self.b.pid(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}
            and target_damage > 0
        )

    def _zero_energy_mega_wall(self, target: Pokemon, target_damage: int) -> bool:
        return self.b.pid(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and self.b.energy_count(target) == 0 and target_damage == 0

    def _recent_my_attack_id(self) -> Optional[int]:
        logs = getattr(getattr(self.b, "obs", None), "logs", None)
        if logs is None:
            logs = getattr(self.b, "logs", [])
        for log in reversed(logs or []):
            if getattr(log, "type", None) == LogType.ATTACK and getattr(log, "playerIndex", None) == self.b.my_index:
                return getattr(log, "attackId", None)
        return None

    def _bypasses_ex_wall(self, attack: Any) -> bool:
        return self.b.attack_bypasses_ex_wall(attack)

    def _blocked_by_ex_wall(self, attacker: Pokemon, target: Pokemon, attack: Any) -> bool:
        return self.b.attack_blocked_by_ex_wall_for_card(self.b.pid(attacker), target, attack)


# ============================================================
# Policy
# ============================================================
class Policy:
    def __init__(self, board: BoardView):
        self.b = board
        self.outcome = ImmediateOutcomeEvaluator(board)

    def score(self, index: int, option: Any) -> float:
        context = self.b.select.context
        if option.type == OptionType.NUMBER:
            return self.score_count(option)
        if option.type in {OptionType.YES, OptionType.NO}:
            return self.score_yes_no(option)
        if context in {SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
            return self.score_setup(option)
        if context in {SelectContext.TO_HAND, SelectContext.TO_FIELD, SelectContext.TO_BENCH, SelectContext.LOOK}:
            return self.score_card_selection(option)
        if context in {SelectContext.DISCARD, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
            return self.score_discard(option)
        if context in {SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY, SelectContext.DAMAGE}:
            return self.score_damage_target(option)
        if context in {SelectContext.REMOVE_DAMAGE_COUNTER, SelectContext.HEAL}:
            return self.score_heal_target(option)
        if context in {SelectContext.SWITCH, SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO, SelectContext.EFFECT_TARGET, SelectContext.EVOLVES_FROM, SelectContext.EVOLVES_TO}:
            return self.score_target_or_card(option)
        if context in {SelectContext.DISCARD_ENERGY, SelectContext.DISCARD_ENERGY_CARD, SelectContext.TO_HAND_ENERGY, SelectContext.TO_DECK_ENERGY, SelectContext.SWITCH_ENERGY, SelectContext.SWITCH_ENERGY_CARD}:
            return self.score_energy_selection(option)
        return self.score_main(option)

    def score_main(self, option: Any) -> float:
        if option.type == OptionType.ATTACK or option.attackId is not None:
            return self.score_attack(option)
        if option.type == OptionType.END:
            return self.score_end()
        if option.type == OptionType.RETREAT:
            return self.score_retreat(option)
        if option.type == OptionType.PLAY:
            return self.score_play(option)
        if option.type == OptionType.ATTACH:
            return self.score_attach(option)
        if option.type == OptionType.EVOLVE:
            return self.score_evolve(option)
        if option.type == OptionType.ABILITY:
            return self.score_ability(option)
        if option.type == OptionType.CARD:
            return self.score_card_selection(option)
        return 0.0

    def action_score(self, option: Any, legacy_score: float, outcome: ImmediateOutcome) -> ActionScore:
        if legacy_score <= SCORE_FORBIDDEN // 2:
            return ActionScore(TIER_FORBIDDEN, legacy=legacy_score)
        if option.type == OptionType.ATTACK or option.attackId is not None:
            return self.attack_action_score(option, legacy_score, outcome)
        if outcome.supported and outcome.wins_game:
            return ActionScore(TIER_WIN, immediate=outcome.prizes_taken, legacy=legacy_score)
        if outcome.supported and outcome.knockout:
            return ActionScore(TIER_KO, immediate=outcome.prizes_taken, pressure=outcome.damage, legacy=legacy_score)
        if self.active_evolution_has_clear_attack_improvement(option):
            return ActionScore(
                TIER_HIGH_VALUE_PREP,
                development=self.prep_development_value(option, legacy_score),
                resource=max(0, min(legacy_score, 200000)),
                legacy=legacy_score,
            )
        if self.is_high_value_attack_preserving_prep(option, legacy_score):
            return ActionScore(
                TIER_HIGH_VALUE_PREP,
                development=self.prep_development_value(option, legacy_score),
                resource=max(0, min(legacy_score, 200000)),
                legacy=legacy_score,
            )
        if legacy_score <= SCORE_LAST_RESORT:
            return ActionScore(TIER_BLOCKED_OR_BAD_ACTION, risk=legacy_score, legacy=legacy_score)
        return ActionScore(TIER_LOW_VALUE_ACTION, resource=max(0, legacy_score), legacy=legacy_score)

    def attack_action_score(self, option: Any, legacy_score: float, outcome: ImmediateOutcome) -> ActionScore:
        if not outcome.supported or outcome.blocked:
            return ActionScore(TIER_BLOCKED_OR_BAD_ACTION, risk=legacy_score, legacy=legacy_score)
        if outcome.wins_game:
            return ActionScore(TIER_WIN, immediate=outcome.prizes_taken, pressure=outcome.damage, legacy=legacy_score)
        if outcome.knockout:
            return ActionScore(TIER_KO, immediate=outcome.prizes_taken, pressure=outcome.damage, legacy=legacy_score)
        return ActionScore(
            TIER_NON_KO_ATTACK,
            pressure=self.attack_pressure_value(option, outcome),
            legacy=legacy_score,
        )

    def attack_pressure_value(self, option: Any, outcome: ImmediateOutcome) -> float:
        attack = self.b.attack(option.attackId)
        target = self.b.opp_active
        if attack is None or target is None or outcome.damage <= 0:
            return 0
        active_hp = max(1, hp_left(target))
        active_pressure = outcome.damage * 1000
        active_pressure += (outcome.damage / active_hp) * 45000
        if active_hp - outcome.damage <= 100:
            active_pressure += 18000
        if self.can_continue_same_attack(attack) and outcome.damage * 2 >= active_hp:
            active_pressure += (25000 + self.b.prize_value(target) * 8000) * NEXT_TURN_PRESSURE_DISCOUNT
        bench_pressure = self.bench_attack_pressure_value(attack)
        return active_pressure + bench_pressure

    def can_continue_same_attack(self, attack: Any) -> bool:
        active = self.b.active
        return active is not None and self.b.can_pay_attack(active, attack)

    def attack_bench_damage_amount(self, attack: Any) -> int:
        return attack_bench_damage_amount(attack)

    def bench_attack_pressure_value(self, attack: Any) -> float:
        bench_damage = self.attack_bench_damage_amount(attack)
        if bench_damage <= 0:
            return 0
        best = 0.0
        for target in self.b.opp_bench:
            target_id = self.b.pid(target)
            target_hp = max(1, hp_left(target))
            important = (
                target_id in self.b.plan_pressure_targets()
                or target_id in LUCARIO_ENGINE
                or target_id in DURALUDON_LINE
                or target_id in CRUSTLE_LINE
                or target_id in EX_ATTACK_WALLS
                or target_id in ALAKAZAM_LINE
                or target_id in DREEPY_LINE
                or target_id in {DRAGAPULT_EX, BUDEW, SHAYMIN}
            )
            value = bench_damage * (450 if important else 120)
            value += (bench_damage / target_hp) * (45000 if important else 8000)
            if bench_damage >= target_hp:
                value += 60000 + self.b.prize_value(target) * 12000
            if self.can_continue_same_attack(attack) and bench_damage * 2 >= target_hp:
                value += (50000 + self.b.prize_value(target) * 12000) * NEXT_TURN_PRESSURE_DISCOUNT
            if important:
                value += 12000
            best = max(best, value)
        return best

    def has_current_non_ko_attack_option(self) -> bool:
        for _, option in self.b.iter_options():
            if option.type != OptionType.ATTACK and option.attackId is None:
                continue
            outcome = self.outcome.evaluate_attack(option)
            if outcome.supported and not outcome.blocked and not outcome.knockout and not outcome.wins_game:
                return True
        return False

    def current_attack_outcomes(self) -> Tuple[ImmediateOutcome, ...]:
        outcomes = []
        for _, option in self.b.iter_options():
            if option.type != OptionType.ATTACK and option.attackId is None:
                continue
            outcomes.append(self.outcome.evaluate_attack(option))
        return tuple(outcomes)

    def active_evolution_has_clear_attack_improvement(self, option: Any) -> bool:
        if option.type != OptionType.EVOLVE or self.b.option_target(option) is not self.b.active:
            return False

        evolved_facts = tuple(fact for fact in self.b.active_evolution_attack_facts(option) if fact.supported)
        unblocked_evolved = tuple(fact for fact in evolved_facts if not fact.blocked)
        if not unblocked_evolved:
            return False

        current_outcomes = self.current_attack_outcomes()
        if any(outcome.supported and not outcome.blocked and (outcome.wins_game or outcome.knockout) for outcome in current_outcomes):
            return False

        current_supported = tuple(outcome for outcome in current_outcomes if outcome.supported)
        current_best_damage = max(
            (
                outcome.damage
                for outcome in current_supported
                if not outcome.blocked and not outcome.knockout and not outcome.wins_game
            ),
            default=0,
        )
        current_has_only_blocked_attacks = bool(current_supported) and not any(
            not outcome.blocked for outcome in current_supported
        )

        if any(fact.wins_game for fact in unblocked_evolved):
            return True
        if any(fact.knockout for fact in unblocked_evolved):
            return True
        if current_has_only_blocked_attacks:
            return True

        evolved_best_damage = max((fact.damage for fact in unblocked_evolved), default=0)
        return evolved_best_damage >= current_best_damage + ACTIVE_EVOLVE_CLEAR_DAMAGE_GAIN

    def is_high_value_attack_preserving_prep(self, option: Any, legacy_score: float) -> bool:
        if legacy_score <= 0 or not self.has_current_non_ko_attack_option():
            return False
        if option.type == OptionType.PLAY:
            cid = self.b.option_card(option)
            if cid in {BEFEHL_VON_BOSS, SURFING_BEACH, WALLY_COMPASSION}:
                return False
            return legacy_score >= 50000
        if option.type == OptionType.EVOLVE:
            target = self.b.option_target(option)
            return target is not None and target is not self.b.active and legacy_score >= 50000
        return False

    def prep_development_value(self, option: Any, legacy_score: float) -> float:
        if option.type == OptionType.EVOLVE:
            return max(legacy_score, 120000)
        if option.type == OptionType.PLAY:
            return min(max(legacy_score, 60000), 260000)
        return max(0, legacy_score)

    def score_setup(self, option: Any) -> float:
        cid = self.b.option_card(option)
        if self.b.select.context == SelectContext.SETUP_ACTIVE_POKEMON:
            if cid == CINDERACE:
                return SCORE_FORCED + 5000
            if cid == HITODEMAN:
                return 9000
            if cid == YUKIWARASHI:
                return 7600
            if cid == YVELTAL:
                return 4200
            if cid == SHAYMIN:
                return 2500
            return self.basic_score(cid)
        if cid == CINDERACE:
            return SCORE_FORBIDDEN
        if cid == HITODEMAN:
            return 9000
        if cid == YUKIWARASHI:
            return 7600 if self.b.count_in_play(HITODEMAN) > 0 else 6200
        if cid == SHAYMIN and self.b.needs_shaymin_bench_guard():
            return 12000
        if cid == YVELTAL:
            return 3000
        return self.basic_score(cid)

    def basic_score(self, cid: Optional[int]) -> float:
        if not self.b.is_basic_pokemon(cid):
            return SCORE_FORBIDDEN
        data = self.b.data(cid)
        return 1000 + (0 if data is None else data.hp)

    def score_attack(self, option: Any) -> float:
        attack = self.b.attack(option.attackId)
        if attack is None:
            return SCORE_FORBIDDEN
        outcome = self.outcome.evaluate_attack(option)
        if not outcome.supported:
            return SCORE_FORBIDDEN
        attacker = self.b.active
        if outcome.blocked:
            if self.has_effective_attack_option() or self.has_real_development_option():
                return SCORE_FORBIDDEN
            return SCORE_LAST_RESORT + 100
        score = SCORE_PREFERRED + outcome.damage * 100

        if outcome.wins_game:
            return SCORE_FORCED + 500000
        if outcome.knockout:
            score += SCORE_FORCED // 2 + outcome.prizes_taken * 120000
        if self.b.pid(attacker) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not outcome.knockout and not self.b.bench:
            if any(card in self.b.hand_ids for card in {POFIN, TANKER, HYPERBALL, POKEGEAR, LILLIE_DETERMINATION}):
                return 40000 + outcome.damage * 100
        if self.b.pid(attacker) in {SHAYMIN, YUKIMENOKO} and not outcome.knockout and self.has_real_development_option():
            return 2000 + outcome.damage * 100
        if attack.attackId in {WATER_GUN, CHILLY} and not outcome.knockout and self.has_real_development_option():
            if outcome.target_id == BUDEW:
                return 180000 + outcome.damage * 100
            if not self.b.bench:
                return 2000 + outcome.damage * 100
            return 30000 + outcome.damage * 100
        if self.b.active_has_ignition():
            score += SCORE_FORCED // 3
            if attack.attackId in {NEBULA_BEAM, ABSOLUTE_SNOW}:
                score += SCORE_FORCED // 3
        if attack.attackId == TURBO_FLARE:
            if self.b.has_bench_energy_receiver():
                if any(card in self.b.hand_ids for card in {POFIN, HYPERBALL, POKEGEAR, SALVATORE, MEGA_SIGNAL, LILLIE_DETERMINATION, CRISPIN, TANKER}):
                    return 50000
                turbo_score = SCORE_PREFERRED + 100000
                if self.b.count_in_play(MEGA_STARMIE_EX) == 0 and self.b.count_in_play(MEGA_YUKIMENOKO_EX) == 0:
                    turbo_score += 120000
                if not any(card in self.b.hand_ids for card in {HYPERBALL, SALVATORE, MEGA_STARMIE_EX}):
                    turbo_score += 70000
                return turbo_score
            return 0
        if attack.attackId in self.b.plan_attack_ids():
            score += 45000
        if attack.attackId == NEBULA_BEAM:
            score += 120000
            if self.b.opponent_profile() in {"STEEL", "WALL", "LUCARIO"}:
                score += 220000
            if self.b.opp_active is not None and self.b.pid(self.b.opp_active) in EX_ATTACK_WALLS | DURALUDON_LINE:
                score += 260000
        if attack.attackId == JETTING_BLOW:
            score += 90000
            if any(a.attackId == NEBULA_BEAM for a in self.b.legal_attack_options()) and self.b.opponent_profile() in {"STEEL", "WALL"} and not outcome.knockout:
                score -= 180000
            if self.b.opponent_profile() in {"STEEL", "WALL"} and not outcome.knockout and self.has_active_nebula_enabling_attach_option():
                score = min(score, 250000 + outcome.damage * 100)
        if attack.attackId == RESENTFUL_REFRAIN:
            score += safe_int(self.b.opp.handCount) * 6000
            if self.b.opponent_profile() == "ALAKAZAM":
                score += 140000
        if attack.attackId == ABSOLUTE_SNOW:
            score += 70000
            if self.b.opponent_profile() == "LUCARIO" or self.b.active_in_danger():
                score += 90000
        if attack.attackId in {WATER_GUN, CHILLY} and not outcome.knockout:
            score -= 140000
        if self.b.pid(attacker) in {HITODEMAN, YUKIWARASHI} and not outcome.knockout and self.has_real_development_option():
            score -= 160000
        return score

    def has_effective_attack_option(self) -> bool:
        for _, option in self.b.iter_options():
            if option.type != OptionType.ATTACK and option.attackId is None:
                continue
            outcome = self.outcome.evaluate_attack(option)
            if outcome.supported and not outcome.blocked:
                return True
        return False

    def has_real_development_option(self) -> bool:
        for _, option in self.b.iter_options():
            if option.type in {OptionType.PLAY, OptionType.ATTACH, OptionType.EVOLVE, OptionType.ABILITY}:
                if self.score_main(option) > 3000:
                    return True
        return False

    def score_end(self) -> float:
        if self.b.is_attack_choice_phase() and self.has_effective_attack_option():
            return SCORE_FORBIDDEN
        if self.has_effective_attack_option():
            penalty = SCORE_FORBIDDEN // 2
            if self.b.active_has_ignition():
                penalty = SCORE_FORBIDDEN
            return penalty
        if self.has_real_development_option():
            return SCORE_FORBIDDEN
        return -100

    def score_retreat(self, option: Any) -> float:
        outcome = self.outcome.evaluate_retreat(option)
        if not outcome.supported:
            return SCORE_FORBIDDEN
        score = -8000
        if "retreat_no_target" in outcome.reasons:
            return SCORE_FORBIDDEN
        if self.b.pid(self.b.active) == CINDERACE and self.b.cinderace_can_accelerate() and self.b.has_bench_energy_receiver():
            return SCORE_FORBIDDEN
        if outcome.retreat_energy_cost > 0 and not (
            "switch_enables_win" in outcome.reasons
            or outcome.enables_knockout
            or outcome.enables_attack
            or outcome.improves_damage
            or "survival_retreat" in outcome.reasons
            or "role_handoff" in outcome.reasons
        ):
            return SCORE_FORBIDDEN
        if "switch_enables_win" in outcome.reasons:
            return SCORE_FORCED + 400000
        if outcome.enables_knockout:
            score += SCORE_FORCED // 2
        if outcome.enables_attack:
            score += 160000
        if "role_handoff" in outcome.reasons:
            score += 140000
        if outcome.improves_damage:
            score += 90000
        if "survival_retreat" in outcome.reasons:
            score += 90000
        if "retreat_from_ready_attacker" in outcome.reasons and not (
            "survival_retreat" in outcome.reasons
            or outcome.enables_knockout
            or outcome.enables_attack
            or "role_handoff" in outcome.reasons
            or outcome.improves_damage
        ):
            score -= 90000
        score -= outcome.retreat_energy_cost * 18000
        score -= outcome.important_energy_loss * 70000
        return score

    def score_play(self, option: Any) -> float:
        cid = self.b.option_card(option)
        if cid is None:
            return SCORE_FORBIDDEN
        if self.b.is_supporter(cid) and self.b.state.supporterPlayed:
            return SCORE_FORBIDDEN
        if cid == POFIN:
            if self.b.bench_space <= 0:
                return SCORE_FORBIDDEN
            score = 65000 if self.b.needs_basic() else 9000
            if self.b.opponent_profile() == "LUCARIO":
                score += 18000
            return score
        if cid == SALVATORE:
            if not self.b.salvatore_live():
                return -8000
            return SCORE_PREFERRED + 125000
        if cid == HYPERBALL:
            if len(self.b.hand_ids) <= 3:
                return -20000
            if self.b.needs_mega_starmie() or self.b.needs_basic():
                return 85000
            return 12000
        if cid == MEGA_SIGNAL:
            if self.b.needs_mega_starmie() or self.b.needs_mega_yuki():
                return 78000
            return -8000
        if cid == POKE_PAD:
            if self.b.needs_basic():
                return 56000
            return 7000
        if cid == POKEGEAR:
            facts = self.b.pokegear_supporter_facts()
            if facts.no_target_confirmed:
                return -8000
            if facts.live_supporter_count > 0:
                return 58000
            if facts.supporter_remaining_possible:
                return 26000
            return 6000
        if cid == LILLIE_DETERMINATION:
            if self.b.state.supporterPlayed:
                return SCORE_FORBIDDEN
            facts = self.b.hand_activity_facts()
            if any(card_id == SALVATORE and activity == HAND_ACTIVITY_LIVE_NOW for card_id, activity in facts.activities):
                return -12000
            if facts.hand_size <= 2 or self.b.needs_basic():
                return 70000
            if facts.hand_size <= 4 and facts.lillie_effect.shuffle_count >= 3:
                return 70000
            if facts.hand_size <= 4 and facts.low_activity_ratio >= 0.5:
                return 70000
            if facts.low_activity_ratio >= 0.8 and facts.lillie_effect.shuffle_count >= 5:
                return 86000
            if facts.low_activity_ratio >= 0.6 and facts.lillie_effect.shuffle_count >= 4:
                return 56000
            if facts.low_activity_ratio <= 0.25 and facts.live_now_count + facts.keep_count >= max(1, facts.hand_size - 1):
                return 8000
            return 16000
        if cid == HILDA:
            if self.b.needs_mega_starmie() or self.b.starmie_needs_energy():
                return 62000
            return 6000
        if cid == CRISPIN:
            facts = self.b.active_energy_facts()
            if facts.key_attack_id is not None and not facts.key_attack_ready:
                missing_types = set(facts.key_attack_missing_types)
                has_required_energy = True
                if EnergyType.WATER in missing_types and not facts.water_remaining_possible:
                    has_required_energy = False
                if EnergyType.DARKNESS in missing_types and not facts.dark_remaining_possible:
                    has_required_energy = False
                if EnergyType.COLORLESS in missing_types and not (facts.water_remaining_possible or facts.dark_remaining_possible):
                    has_required_energy = False
                if has_required_energy:
                    return 82000 if facts.key_attack_missing_units <= 1 else 62000
            return 9000
        if cid == TANKER:
            if BASIC_WATER_ENERGY in self.b.discard_ids and self.b.starmie_needs_energy():
                return 74000
            if HITODEMAN in self.b.discard_ids and self.b.count_in_play(HITODEMAN) == 0:
                return 68000
            return 8000
        if cid == WALLY_COMPASSION:
            return 88000 if self.b.wally_live() else -16000
        if cid == BEFEHL_VON_BOSS:
            return self.score_boss()
        if cid == SURFING_BEACH:
            if self.b.has_foreign_stadium():
                return 42000
            if self.b.active_in_danger() and self.b.active is not None and self.b.pid(self.b.active) in WATER_POKEMON:
                return 28000
            return 4000
        if cid == HERO_CAPE:
            return 54000 if any(self.b.pid(p) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not p.tools for p in self.b.all_my_pokemon) else -12000
        if cid == TOOL_SCRAPPER:
            return self.score_tool_scrapper_outcome(self.outcome.evaluate_tool_scrapper_play(option))
        if cid == ENERGY_SWITCH:
            return 36000 if self.b.starmie_needs_energy() else 3000
        if self.b.is_pokemon(cid):
            return self.score_pokemon_play(cid)
        if cid in self.b.plan_setup_cards():
            return 15000
        return 0

    def score_boss(self) -> float:
        if not self.b.opp_bench:
            return SCORE_FORBIDDEN
        best = SCORE_FORBIDDEN
        for pokemon in self.b.opp_bench:
            best = max(best, self.score_boss_outcome(self.outcome.evaluate_boss_target(pokemon)))
        return best

    def score_boss_outcome(self, outcome: ImmediateOutcome) -> float:
        if not outcome.supported:
            return SCORE_FORBIDDEN
        if outcome.wins_game:
            return SCORE_FORCED + 700000
        score = 0.0
        if outcome.knockout:
            score += SCORE_PREFERRED + outcome.prizes_taken * 140000
        if outcome.avoids_wall and outcome.damage > 0:
            score += 220000
        if outcome.breaks_engine:
            score += 160000
        if outcome.damage > 0:
            score += outcome.damage * 500
        if outcome.target_id == SHAYMIN and self.b.opponent_profile() == "BENCH_DAMAGE":
            score += 20000
        if outcome.reasons == ("boss_target", "boss_no_effective_attack"):
            score -= 50000
        return score

    def score_tool_scrapper_outcome(self, outcome: ImmediateOutcome) -> float:
        if not outcome.supported:
            return -8000
        if outcome.wins_game:
            return SCORE_FORCED + 500000
        if outcome.knockout:
            return SCORE_FORCED // 2 + outcome.prizes_taken * 140000
        if outcome.enables_knockout:
            return SCORE_PREFERRED + 180000
        if "removes_hero_cape" in outcome.reasons:
            return SCORE_PREFERRED + 70000
        if "removes_key_tool" in outcome.reasons:
            return 80000
        if outcome.removes_tool:
            return 22000
        return -8000

    def score_pokemon_play(self, cid: int) -> float:
        if self.b.bench_space <= 0:
            return SCORE_FORBIDDEN
        if cid == CINDERACE:
            return SCORE_FORBIDDEN
        if cid == HITODEMAN:
            return 72000
        if cid == YUKIWARASHI:
            return 42000 if self.b.opponent_profile() in {"ALAKAZAM", "BENCH_DAMAGE"} else 28000
        if cid == SHAYMIN:
            if self.b.needs_shaymin_bench_guard() and self.b.count_in_play(SHAYMIN) == 0:
                return 105000
            return -10000
        if cid == YVELTAL:
            return 14000
        return 1000

    def score_attach(self, option: Any) -> float:
        cid = self.b.option_card(option)
        target = self.b.option_target(option)
        if cid is None or target is None:
            return SCORE_FORBIDDEN
        target_id = self.b.pid(target)
        if cid == HERO_CAPE:
            if target_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not target.tools:
                return 90000 + damage_on(target) * 400
            return SCORE_FORBIDDEN
        attach_outcome = self.outcome.evaluate_attach(option)
        if cid in {BASIC_WATER_ENERGY, BASIC_DARK_ENERGY, IGNITION_ENERGY} and not attach_outcome.supported:
            return SCORE_FORBIDDEN
        if (
            cid in {BASIC_WATER_ENERGY, BASIC_DARK_ENERGY}
            and target is self.b.active
            and target_id == CINDERACE
            and TURBO_FLARE in attach_outcome.enabled_attack_ids
            and self.has_live_turbo_flare_receiver()
            and self.has_turbo_flare_energy_in_deck()
            and not self.active_status_blocks_attack()
        ):
            return 210000
        if cid == IGNITION_ENERGY:
            if target_id == CINDERACE:
                if not self.b.has_bench_energy_receiver():
                    return -40000
                return 12000 if attach_outcome.enables_attack else -40000
            if "ignition_immediate_attack" in attach_outcome.reasons:
                score = SCORE_PREFERRED + 220000
                if NEBULA_BEAM in attach_outcome.enabled_attack_ids:
                    score += 160000
                if ABSOLUTE_SNOW in attach_outcome.enabled_attack_ids:
                    score += 100000
                return score
            if attach_outcome.enables_attack:
                if target_id == MEGA_STARMIE_EX:
                    return 130000
                if target_id == MEGA_YUKIMENOKO_EX:
                    return 100000 if self.b.opponent_profile() == "ALAKAZAM" else 85000
                return 70000
            return -40000
        if cid == BASIC_WATER_ENERGY:
            score = self.score_water_attach(target)
            if NEBULA_BEAM in attach_outcome.enabled_attack_ids:
                score += 180000
            elif attach_outcome.enables_attack:
                score += 90000
            return score
        if cid == BASIC_DARK_ENERGY:
            score = self.score_dark_attach(target)
            if NEBULA_BEAM in attach_outcome.enabled_attack_ids:
                score += 150000
            elif attach_outcome.enables_attack:
                score += 70000
            return score
        return 1000

    def score_water_attach(self, target: Pokemon) -> float:
        tid = self.b.pid(target)
        count = self.b.energy_count(target)
        main_axis_available = self.main_axis_attach_target_available(BASIC_WATER_ENERGY)
        if tid == MEGA_STARMIE_EX:
            return 140000 + (3 - min(3, count)) * 45000
        if tid == HITODEMAN:
            return 85000 if self.b.visible_or_unknown_in_deck(MEGA_STARMIE_EX) or MEGA_STARMIE_EX in self.b.hand_ids else 42000
        if tid == CINDERACE and count == 0 and self.b.has_bench_energy_receiver():
            return 12000 if main_axis_available else 76000
        if tid == MEGA_YUKIMENOKO_EX:
            return 70000 if self.b.opponent_profile() in {"ALAKAZAM", "BENCH_DAMAGE"} else 50000
        if tid == YUKIWARASHI:
            return 50000 if self.b.opponent_profile() == "ALAKAZAM" else 42000
        if tid in UTILITY_POKEMON:
            return SCORE_FORBIDDEN
        return 0

    def score_dark_attach(self, target: Pokemon) -> float:
        tid = self.b.pid(target)
        count = self.b.energy_count(target)
        main_axis_available = self.main_axis_attach_target_available(BASIC_DARK_ENERGY)
        if tid == CINDERACE and count == 0 and self.b.has_bench_energy_receiver():
            return 12000 if main_axis_available else 60000
        if tid == MEGA_STARMIE_EX and count >= 1 and count < 3:
            return 90000
        if tid == YVELTAL:
            if target is self.b.active and not self.b.bench and any(card in self.b.hand_ids for card in {POFIN, HYPERBALL, POKEGEAR, SALVATORE, MEGA_SIGNAL, LILLIE_DETERMINATION, CRISPIN}):
                return 0
            if main_axis_available:
                return 0
            return 36000
        if tid == MEGA_YUKIMENOKO_EX and count >= 1 and count < 3:
            return 28000
        if tid == MEGA_STARMIE_EX and count == 0:
            return -50000
        return -5000

    def main_axis_attach_target_available(self, energy_id: int) -> bool:
        for pokemon in self.b.all_my_pokemon:
            tid = self.b.pid(pokemon)
            count = self.b.energy_count(pokemon)
            if energy_id == BASIC_WATER_ENERGY:
                if tid == MEGA_STARMIE_EX and count < 3:
                    return True
                if tid == HITODEMAN and (self.b.visible_or_unknown_in_deck(MEGA_STARMIE_EX) or MEGA_STARMIE_EX in self.b.hand_ids):
                    return True
                if tid == MEGA_YUKIMENOKO_EX and count < 3:
                    return True
                if tid == YUKIWARASHI and (self.b.visible_or_unknown_in_deck(MEGA_YUKIMENOKO_EX) or MEGA_YUKIMENOKO_EX in self.b.hand_ids):
                    return True
            if energy_id == BASIC_DARK_ENERGY:
                if tid == MEGA_STARMIE_EX and count >= 1 and count < 3:
                    return True
                if tid == MEGA_YUKIMENOKO_EX and count >= 1 and count < 3:
                    return True
        return False

    def has_active_nebula_enabling_attach_option(self) -> bool:
        for _, option in self.b.iter_options():
            if option.type != OptionType.ATTACH:
                continue
            if self.b.option_target(option) is not self.b.active:
                continue
            outcome = self.outcome.evaluate_attach(option)
            if outcome.supported and NEBULA_BEAM in outcome.enabled_attack_ids:
                return True
        return False

    def active_status_blocks_attack(self) -> bool:
        player = getattr(self.b, "me", None)
        return bool(getattr(player, "asleep", False) or getattr(player, "paralyzed", False))

    def has_live_turbo_flare_receiver(self) -> bool:
        for pokemon in self.b.bench:
            tid = self.b.pid(pokemon)
            if self.b.energy_count(pokemon) >= 3:
                continue
            if tid == MEGA_STARMIE_EX:
                return True
            if tid == HITODEMAN and (self.b.visible_or_unknown_in_deck(MEGA_STARMIE_EX) or MEGA_STARMIE_EX in self.b.hand_ids):
                return True
            if tid == MEGA_YUKIMENOKO_EX:
                return True
            if tid == YUKIWARASHI and (self.b.visible_or_unknown_in_deck(MEGA_YUKIMENOKO_EX) or MEGA_YUKIMENOKO_EX in self.b.hand_ids):
                return True
        return False

    def has_turbo_flare_energy_in_deck(self) -> bool:
        if self.b.deck_view:
            return BASIC_WATER_ENERGY in self.b.deck_ids or BASIC_DARK_ENERGY in self.b.deck_ids
        for energy_id in (BASIC_WATER_ENERGY, BASIC_DARK_ENERGY):
            known_out = self.b.hand_ids.count(energy_id) + self.b.discard_ids.count(energy_id)
            known_out += sum(self.b.energies(pokemon).count(energy_id) for pokemon in self.b.all_my_pokemon)
            if known_out < DECK.count(energy_id):
                return True
        return False

    def score_evolve(self, option: Any) -> float:
        cid = self.b.option_card(option)
        target = self.b.option_target(option)
        if cid == MEGA_STARMIE_EX:
            score = 180000
            if target is not None and target is not self.b.active:
                score += 30000
            if self.b.opponent_profile() in {"LUCARIO", "STEEL", "WALL"}:
                score += 140000
        elif cid == MEGA_YUKIMENOKO_EX:
            if self.b.opponent_profile() == "ALAKAZAM":
                score = 140000
            elif self.b.opponent_profile() == "BENCH_DAMAGE":
                score = 90000
            elif self.b.opponent_profile() in {"LUCARIO", "STEEL", "WALL"}:
                score = 45000
            else:
                score = 70000
        else:
            return 5000

        if target is None:
            return score

        base_id = HITODEMAN if cid == MEGA_STARMIE_EX else YUKIWARASHI
        if self.b.pid(target) != base_id or hp_left(target) <= 0:
            return score

        evo_data = self.b.data(cid)
        real_evo_data = CARD_TABLE.get(cid)
        evo_hp = safe_int(getattr(evo_data, "hp", 0) or getattr(real_evo_data, "hp", 0))
        before_hp = safe_int(getattr(target, "maxHp", 0) or getattr(self.b.data(base_id), "hp", 0))
        if evo_hp <= before_hp:
            return score

        active_key_attack_attach = False
        for _, candidate in self.b.iter_options():
            if candidate.type == OptionType.ATTACH and self.b.option_target(candidate) is self.b.active:
                outcome = self.outcome.evaluate_attach(candidate)
                if outcome.supported and any(attack_id in outcome.enabled_attack_ids for attack_id in {NEBULA_BEAM, ABSOLUTE_SNOW}):
                    active_key_attack_attach = True

        energy_count = self.b.energy_count(target)
        same_line_has_more_energy = any(
            pokemon is not target
            and self.b.pid(pokemon) == base_id
            and self.b.energy_count(pokemon) > energy_count
            for pokemon in self.b.all_my_pokemon
        )

        if target is self.b.active:
            if same_line_has_more_energy:
                return score
            player = getattr(self.b, "me", None)
            if getattr(player, "asleep", False) or getattr(player, "paralyzed", False):
                return score
            tokens = self.b.energy_tokens(target)
            usable_attacks = []
            for attack_id in getattr(evo_data, "attacks", ()):
                attack = self.b.attack(attack_id)
                if attack is None or not can_pay_attack_with_tokens(attack, tokens):
                    continue
                if self.b.opp_active is not None and self.b.pid(self.b.opp_active) in EX_ATTACK_WALLS:
                    if attack.attackId != NEBULA_BEAM:
                        continue
                usable_attacks.append(attack.attackId)
            if not usable_attacks:
                return score
            hp_gain_score = min(160000, max(0, evo_hp - before_hp) * 600)
            score += hp_gain_score
            score += 220000
            score += 140000
            score += energy_count * 60000
            score += 260000
            if any(attack_id in usable_attacks for attack_id in {NEBULA_BEAM, ABSOLUTE_SNOW}):
                score += 70000
            return score

        active = self.b.active
        if active is not None and self.b.pid(active) == base_id and self.b.energy_count(active) > energy_count:
            return score
        if active_key_attack_attach and energy_count == 0:
            return score

        hp_gain_score = min(160000, max(0, evo_hp - before_hp) * 600)
        score += hp_gain_score
        score += 220000
        score += 140000
        score += min(2, energy_count) * 60000
        if self.outcome.has_energy_payable_unblocked_active_attack():
            score += 140000
        same_mega_count = self.b.count_in_play(cid)
        if same_mega_count == 0:
            score += 120000
        elif same_mega_count == 1:
            score += 300000
        else:
            score += 60000
        return score

    def score_ability(self, option: Any) -> float:
        cid = self.b.option_card(option)
        if cid == CINDERACE:
            return SCORE_FORCED
        return 20000

    def score_yes_no(self, option: Any) -> float:
        yes = option.type == OptionType.YES
        context = self.b.select.context
        cid = None
        if self.b.select.contextCard is not None:
            cid = self.b.select.contextCard.id
        if context == SelectContext.IS_FIRST:
            return 2000 if yes else 1000
        if context == SelectContext.MULLIGAN:
            return -1000 if yes else 1000
        if context == SelectContext.ACTIVATE:
            if cid == CINDERACE:
                return SCORE_FORCED if yes else SCORE_FORBIDDEN
            return 5000 if yes else 0
        return 1000 if yes else 0

    def score_count(self, option: Any) -> float:
        number = safe_int(option.number)
        context = self.b.select.context
        if context == SelectContext.DRAW_COUNT:
            return number
        if context in {SelectContext.DAMAGE_COUNTER_COUNT, SelectContext.REMOVE_DAMAGE_COUNTER_COUNT}:
            return number
        return number

    def score_card_selection(self, option: Any) -> float:
        cid = self.b.option_card(option)
        effect = self.effect_id()
        if effect == POFIN:
            if not self.b.is_poffin_target(cid):
                return SCORE_FORBIDDEN
            if cid == HITODEMAN:
                return 120000
            if cid == YUKIWARASHI:
                return 70000 if self.b.opponent_profile() == "ALAKAZAM" else 32000
            return 1000
        if effect == POKE_PAD:
            if not self.b.is_poke_pad_target(cid):
                return SCORE_FORBIDDEN
            if cid == HITODEMAN:
                return 110000
            if cid == YUKIWARASHI:
                return 52000
            if cid == YVELTAL:
                return 12000
            return 1000
        if effect == HYPERBALL:
            if not self.b.is_pokemon(cid):
                return SCORE_FORBIDDEN
            if cid == MEGA_STARMIE_EX and self.b.count_in_play(HITODEMAN):
                return 160000
            if cid == HITODEMAN:
                return 120000
            if cid == MEGA_YUKIMENOKO_EX and self.b.opponent_profile() == "ALAKAZAM":
                return 120000
            return self.card_need_score(cid)
        if effect == MEGA_SIGNAL:
            if not self.b.is_mega_signal_target(cid):
                return SCORE_FORBIDDEN
            if cid == MEGA_STARMIE_EX:
                return 150000
            if cid == MEGA_YUKIMENOKO_EX:
                return 110000 if self.b.opponent_profile() == "ALAKAZAM" else 24000
            return 0
        if effect == SALVATORE:
            if cid == MEGA_STARMIE_EX and self.b.is_salvatore_target(cid):
                return 180000
            if cid == MEGA_YUKIMENOKO_EX and self.b.is_salvatore_target(cid):
                return 150000 if self.b.opponent_profile() == "ALAKAZAM" else 30000
            return SCORE_FORBIDDEN
        if effect == POKEGEAR:
            return self.score_pokegear_candidate(cid)
        if effect == TANKER:
            if cid == BASIC_WATER_ENERGY and self.b.starmie_needs_energy():
                return 140000
            if cid == HITODEMAN and self.b.count_in_play(HITODEMAN) == 0:
                return 120000
            if cid == MEGA_STARMIE_EX and self.b.count_in_play(HITODEMAN):
                return 110000
            if self.b.is_pokemon(cid) or self.b.is_energy(cid):
                return 1000
            return SCORE_FORBIDDEN
        if effect == HILDA:
            if cid == MEGA_STARMIE_EX:
                return 150000
            if cid == BASIC_WATER_ENERGY:
                return 120000
            if cid == MEGA_YUKIMENOKO_EX and self.b.opponent_profile() == "ALAKAZAM":
                return 110000
            return SCORE_FORBIDDEN
        if effect == CRISPIN:
            if cid == BASIC_WATER_ENERGY:
                return 140000
            if cid == BASIC_DARK_ENERGY:
                return 90000
            return SCORE_FORBIDDEN
        return self.card_need_score(cid)

    def score_pokegear_candidate(self, cid: Optional[int]) -> float:
        if not self.b.is_supporter(cid):
            return SCORE_FORBIDDEN

        needs_recovery = (
            not self.outcome.has_energy_payable_unblocked_active_attack()
            or self.b.needs_basic()
            or self.b.needs_mega_starmie()
            or self.b.needs_mega_yuki()
            or self.b.starmie_needs_energy()
            or len(self.b.hand_ids) <= 3
        )

        if cid == SALVATORE and self.b.salvatore_live():
            return 180000 if needs_recovery else 160000
        if cid == WALLY_COMPASSION and self.b.wally_live():
            return 130000
        if cid == CRISPIN and self.b.starmie_needs_energy():
            return 125000 if needs_recovery else 110000
        if cid == LILLIE_DETERMINATION:
            if needs_recovery and len(self.b.hand_ids) <= 6:
                return 90000
            if len(self.b.hand_ids) <= 3:
                return 80000
            return 1000
        if cid == BEFEHL_VON_BOSS:
            boss_score = self.score_boss()
            if needs_recovery and boss_score < SCORE_PREFERRED:
                return min(boss_score, -20000)
            return boss_score
        return 1000

    def score_target_or_card(self, option: Any) -> float:
        target = self.b.option_target(option)
        cid = self.b.option_card(option)
        effect = self.effect_id()
        if target is not None:
            if effect == SALVATORE:
                evolution_id = self.b.salvatore_target_evolution(target)
                if evolution_id is None:
                    return SCORE_FORBIDDEN
                data = self.b.data(evolution_id)
                base_data = self.b.data(self.b.pid(target))
                score = 170000 if evolution_id == MEGA_STARMIE_EX else (140000 if self.b.opponent_profile() == "ALAKAZAM" else 20000)
                if target is self.b.active:
                    score += 40000
                energy_count = self.b.energy_count(target)
                score += energy_count * 70000
                if data is not None and base_data is not None:
                    score += min(120000, max(0, safe_int(data.hp) - safe_int(base_data.hp)) * 450)
                    evolved_tokens = []
                    ignition_units = 1 if data.basic else 3
                    for energy_id in self.b.energies(target):
                        if energy_id == BASIC_WATER_ENERGY:
                            evolved_tokens.append(EnergyType.WATER)
                        elif energy_id == BASIC_DARK_ENERGY:
                            evolved_tokens.append(EnergyType.DARKNESS)
                        elif energy_id == IGNITION_ENERGY:
                            evolved_tokens.extend([EnergyType.COLORLESS] * ignition_units)
                    for attack_id in data.attacks:
                        attack = self.b.attack(attack_id)
                        if not can_pay_attack_with_tokens(attack, evolved_tokens):
                            continue
                        score += 60000
                        if attack_id in {NEBULA_BEAM, ABSOLUTE_SNOW}:
                            score += 50000
                        break
                same_line_has_more_energy = any(
                    pokemon is not target
                    and self.b.pid(pokemon) == self.b.pid(target)
                    and self.b.salvatore_target_evolution(pokemon) == evolution_id
                    and self.b.energy_count(pokemon) > energy_count
                    for pokemon in self.b.all_my_pokemon
                )
                if same_line_has_more_energy:
                    score -= 90000
                return score
            if effect == WALLY_COMPASSION:
                return damage_on(target) * 1000 if self.b.pid(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} else SCORE_FORBIDDEN
            if effect == HERO_CAPE:
                return 100000 if self.b.pid(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not target.tools else SCORE_FORBIDDEN
            if effect == TOOL_SCRAPPER:
                return self.score_tool_scrapper_outcome(self.outcome.evaluate_tool_scrapper_target(target, option.toolIndex))
            if effect == BEFEHL_VON_BOSS:
                return self.score_boss_outcome(self.outcome.evaluate_boss_target(target))
            if effect == SURFING_BEACH or self.b.select.context == SelectContext.SWITCH:
                source = "surfing_beach" if effect == SURFING_BEACH else "retreat"
                return self.score_switch_target(target, source)
            if effect == CINDERACE and self.b.select.context in {SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO}:
                return self.score_turbo_flare_attach_target(target)
            return self.target_value(target)
        if cid is not None:
            return self.score_card_selection(option)
        return 0

    def score_turbo_flare_attach_target(self, target: Pokemon) -> float:
        if target not in self.b.all_my_pokemon:
            return SCORE_FORBIDDEN
        pid = self.b.pid(target)
        count = self.b.energy_count(target)
        if pid == MEGA_STARMIE_EX:
            return 230000 + max(0, 3 - count) * 45000 if count < 3 else 15000
        if pid == HITODEMAN:
            if self.b.remaining_possible(MEGA_STARMIE_EX) or MEGA_STARMIE_EX in self.b.hand_ids:
                return 180000 + max(0, 2 - count) * 25000
            return 70000
        if pid == MEGA_YUKIMENOKO_EX:
            if count >= 3:
                return 10000
            base = 150000 if self.b.opponent_profile() in {"ALAKAZAM", "BENCH_DAMAGE"} else 85000
            return base + max(0, 3 - count) * 25000
        if pid == YUKIWARASHI:
            return 95000 if self.b.opponent_profile() == "ALAKAZAM" else 45000
        if pid in UTILITY_POKEMON or pid == CINDERACE:
            return -50000
        return 0

    def score_switch_target(self, target: Pokemon, source: str = "retreat") -> float:
        outcome = self.outcome.evaluate_switch_target(target, source)
        if not outcome.supported:
            return SCORE_FORBIDDEN
        if "switch_enables_win" in outcome.reasons:
            return SCORE_FORCED + 400000
        if outcome.enables_knockout:
            return SCORE_FORCED // 2 + 180000
        if outcome.target_id == SHAYMIN and self.b.needs_shaymin_bench_guard() and "survival_retreat" not in outcome.reasons:
            return SCORE_FORBIDDEN
        if self.b.pid(self.b.active) == CINDERACE and self.b.cinderace_can_accelerate() and self.b.has_bench_energy_receiver():
            return SCORE_FORBIDDEN
        if "zero_energy_mega_wall" in outcome.reasons and "survival_retreat" not in outcome.reasons:
            return SCORE_FORBIDDEN
        if "retreat_from_ready_attacker" in outcome.reasons and "retreat_improves_damage" not in outcome.reasons and "survival_retreat" not in outcome.reasons:
            return SCORE_FORBIDDEN // 3

        score = 0.0
        if "survival_retreat" in outcome.reasons:
            score += 100000
        if outcome.enables_attack:
            score += 150000
        if outcome.improves_damage:
            score += 90000
        if outcome.target_id in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and outcome.enables_attack:
            score += 90000
        if outcome.target_id in {CINDERACE, YVELTAL, SHAYMIN} and "survival_retreat" in outcome.reasons:
            score += 30000
        if "surfing_beach_switch" in outcome.reasons:
            score += 35000
        score -= outcome.retreat_energy_cost * 12000
        score -= outcome.important_energy_loss * 60000
        return score

    def score_damage_target(self, option: Any) -> float:
        outcome = self.outcome.evaluate_attack_effect_target(option)
        if outcome.supported:
            return self.score_attack_effect_target_outcome(outcome)
        if self.b.select.context == SelectContext.DAMAGE:
            return SCORE_LAST_RESORT
        target = self.b.option_target(option)
        if target is None:
            return SCORE_FORBIDDEN
        mine = target in self.b.all_my_pokemon
        if mine:
            return SCORE_FORBIDDEN
        score = self.target_value(target)
        if target is self.b.opp_active:
            score += 60000
        if hp_left(target) <= 50:
            score += 50000
        return score

    def score_attack_effect_target_outcome(self, outcome: ImmediateOutcome) -> float:
        if not outcome.supported:
            return SCORE_FORBIDDEN
        if outcome.wins_game:
            return SCORE_FORCED + 350000
        score = SCORE_PREFERRED + outcome.damage * 1000
        if outcome.knockout:
            score += SCORE_FORCED // 2 + outcome.prizes_taken * 120000
        if "effect_hits_engine" in outcome.reasons:
            score += 90000
        return score

    def score_heal_target(self, option: Any) -> float:
        target = self.b.option_target(option)
        if target is None or target not in self.b.all_my_pokemon:
            return SCORE_FORBIDDEN
        if self.b.pid(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return damage_on(target) * 1000 + self.b.energy_count(target) * 20000
        return damage_on(target) * 100

    def score_energy_selection(self, option: Any) -> float:
        cid = self.b.option_card(option)
        if cid is None and option.energyIndex is not None:
            target = self.b.option_target(option)
            energies = target.energyCards if target is not None else []
            if 0 <= option.energyIndex < len(energies):
                cid = energies[option.energyIndex].id
        context = self.b.select.context
        if context in {SelectContext.TO_HAND_ENERGY, SelectContext.SWITCH_ENERGY, SelectContext.SWITCH_ENERGY_CARD}:
            if cid == BASIC_WATER_ENERGY:
                return 100000
            if cid == BASIC_DARK_ENERGY:
                return 60000
            return 1000
        if cid == BASIC_WATER_ENERGY:
            return SCORE_FORBIDDEN
        if cid == IGNITION_ENERGY:
            return 50000
        if cid == BASIC_DARK_ENERGY:
            return -10000
        return 0

    def score_discard(self, option: Any) -> float:
        cid = self.b.option_card(option)
        if cid is None:
            return 0
        if cid == MEGA_STARMIE_EX:
            return -34000000 if self.b.count_in_play(HITODEMAN) or self.b.needs_mega_starmie() else -300000
        if cid == HITODEMAN:
            return -32000000 if self.b.count_in_play(HITODEMAN) == 0 else -250000
        if cid == BASIC_WATER_ENERGY:
            return -30000000 if self.b.starmie_needs_energy() else -2000000
        if cid == SALVATORE:
            return -35000000 if self.b.salvatore_live() else -200000
        if cid == SHAYMIN and self.b.needs_shaymin_bench_guard():
            return -22000000 if self.b.count_in_play(SHAYMIN) == 0 else -100000
        if cid == HERO_CAPE:
            return -25000000 if any(self.b.pid(p) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX} and not p.tools for p in self.b.all_my_pokemon) else -150000
        if cid == MEGA_SIGNAL:
            return -5000000 if self.b.needs_mega_starmie() or self.b.needs_mega_yuki() else 2000
        if cid in IMPORTANT_CARDS:
            return SCORE_LAST_RESORT
        if cid in {TOOL_SCRAPPER, WALLY_COMPASSION, HERO_CAPE, SALVATORE, POFIN, HYPERBALL}:
            return SCORE_LAST_RESORT
        if cid == YVELTAL:
            return 2000
        if cid == SHAYMIN and not self.b.needs_shaymin_bench_guard():
            return 4000
        if cid == YUKIWARASHI and self.b.count_in_play(YUKIWARASHI) >= 2:
            return 5000
        if cid == MEGA_YUKIMENOKO_EX and self.b.opponent_profile() not in {"ALAKAZAM", "BENCH_DAMAGE"}:
            return 4000
        data = self.b.data(cid)
        if data is not None and data.cardType in {CardType.STADIUM, CardType.TOOL}:
            return 3000
        if data is not None and data.cardType == CardType.SUPPORTER and self.b.state.supporterPlayed:
            return 2500
        return 0

    def target_value(self, pokemon: Optional[Pokemon]) -> float:
        if pokemon is None:
            return SCORE_FORBIDDEN
        pid = self.b.pid(pokemon)
        score = hp_left(pokemon) * -30 + damage_on(pokemon) * 100
        score += self.b.prize_value(pokemon) * 30000
        if pokemon is self.b.opp_active:
            score += 30000
        if pid in self.b.plan_pressure_targets():
            score += 85000
        if pid in LUCARIO_ENGINE:
            score += 120000
        if pid == MEGA_LUCARIO_EX:
            score += 100000
        if pid in DURALUDON_LINE:
            score += 90000
        if pid in CRUSTLE_LINE | EX_ATTACK_WALLS:
            score += 90000
        if pid in ALAKAZAM_LINE:
            score += 85000
        if pid in DREEPY_LINE | {DRAGAPULT_EX}:
            score += 80000
        if pid == BUDEW:
            score += 120000
        if pid == SHAYMIN:
            score += 30000
        if self.b.energy_count(pokemon) >= 2:
            score += 25000
        return score

    def card_need_score(self, cid: Optional[int]) -> float:
        if cid is None:
            return SCORE_FORBIDDEN
        if cid == HITODEMAN:
            return 145000 if cid in self.b.plan_setup_cards() else 120000
        if cid == MEGA_STARMIE_EX:
            base = 130000 if self.b.count_in_play(HITODEMAN) else 40000
            return base + (45000 if cid in self.b.plan_setup_cards() else 0)
        if cid == BASIC_WATER_ENERGY:
            return 90000
        if cid == SALVATORE:
            base = 125000 if cid in self.b.plan_setup_cards() else 85000
            return base if self.b.salvatore_live() else 10000
        if cid == CRISPIN:
            return 70000 if self.b.starmie_needs_energy() else 10000
        if cid == YUKIWARASHI:
            return 55000 if self.b.opponent_profile() == "ALAKAZAM" else 35000
        if cid == MEGA_YUKIMENOKO_EX:
            return 80000 if self.b.opponent_profile() == "ALAKAZAM" else 50000
        if cid == CINDERACE:
            return 65000 if self.b.count_in_play(CINDERACE) == 0 else -5000
        if cid == SHAYMIN and self.b.needs_shaymin_bench_guard() and self.b.count_in_play(SHAYMIN) == 0:
            return 95000
        return 1000

    def effect_id(self) -> Optional[int]:
        if self.b.select.effect is not None:
            return self.b.select.effect.id
        if self.b.select.contextCard is not None:
            return self.b.select.contextCard.id
        return None


# ============================================================
# Non-mutating candidate ordering
# ============================================================
class GameSimulator:
    def __init__(self, board: BoardView, policy: Optional[Policy] = None):
        self.b = board
        self.policy = policy or Policy(board)
        self.outcome = self.policy.outcome

    def rank_options(self) -> List[SimulationResult]:
        results = [
            self.evaluate_candidate(index, option)
            for index, option in self.b.iter_options()
        ]
        return sorted(results, key=self._result_key, reverse=True)

    def evaluate_candidate(self, index: int, option: Any) -> SimulationResult:
        score = self.policy.score(index, option)
        outcome = self._outcome_for(option)
        if hasattr(self.policy, "action_score"):
            action_score = self.policy.action_score(option, score, outcome)
        else:
            action_score = ActionScore(self._legacy_action_tier(score), legacy=score)
        return SimulationResult(
            index=index,
            option=option,
            policy_score=score,
            tier=self._tier(score),
            outcome=outcome,
            action_score=action_score,
        )

    def _outcome_for(self, option: Any) -> ImmediateOutcome:
        if option.type == OptionType.ATTACK or option.attackId is not None:
            return self.outcome.evaluate_attack(option)
        if option.type == OptionType.ATTACH:
            return self.outcome.evaluate_attach(option)
        if option.type == OptionType.RETREAT:
            return self.outcome.evaluate_retreat(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == TOOL_SCRAPPER:
            return self.outcome.evaluate_tool_scrapper_play(option)

        target = self.b.option_target(option)
        if target is not None:
            effect = self.policy.effect_id()
            if effect == TOOL_SCRAPPER:
                return self.outcome.evaluate_tool_scrapper_target(target, option.toolIndex)
            if effect == BEFEHL_VON_BOSS:
                return self.outcome.evaluate_boss_target(target)
            if effect == SURFING_BEACH or self.b.select.context == SelectContext.SWITCH:
                source = "surfing_beach" if effect == SURFING_BEACH else "retreat"
                return self.outcome.evaluate_switch_target(target, source)
            if self.b.select.context == SelectContext.DAMAGE:
                return self.outcome.evaluate_attack_effect_target(option)
        return ImmediateOutcome(supported=False, reasons=("simulator_no_immediate_outcome",))

    def _tier(self, score: float) -> str:
        if score <= SCORE_FORBIDDEN // 2:
            return "forbidden"
        if score >= SCORE_FORCED:
            return "forced"
        if score >= SCORE_PREFERRED:
            return "preferred"
        return "normal"

    def _legacy_action_tier(self, score: float) -> int:
        if score <= SCORE_FORBIDDEN // 2:
            return TIER_FORBIDDEN
        if score >= SCORE_FORCED:
            return TIER_WIN
        if score >= SCORE_PREFERRED:
            return TIER_HIGH_VALUE_PREP
        if score <= SCORE_LAST_RESORT:
            return TIER_BLOCKED_OR_BAD_ACTION
        return TIER_LOW_VALUE_ACTION

    def _result_key(self, result: SimulationResult) -> Tuple[Any, ...]:
        outcome = result.outcome
        action = result.action_score
        return (
            action.tier,
            action.immediate,
            action.pressure,
            action.development,
            action.resource,
            -action.risk,
            outcome.supported,
            outcome.wins_game,
            outcome.knockout,
            outcome.prizes_taken,
            not outcome.blocked,
            outcome.enables_knockout,
            outcome.enables_attack,
            outcome.improves_damage,
            outcome.damage,
            -outcome.important_energy_loss,
            -outcome.retreat_energy_cost,
            action.legacy,
            -result.index,
        )


# ============================================================
# Action selection
# ============================================================
def choose_indices(board: BoardView) -> List[int]:
    ranked = GameSimulator(board).rank_options()
    if not ranked:
        return []
    minimum = safe_int(board.select.minCount)
    maximum = safe_int(board.select.maxCount)
    if maximum <= 0:
        maximum = 1
    if maximum == 1:
        return [ranked[0].index]
    chosen = [result.index for result in ranked if result.policy_score > SCORE_FORBIDDEN // 2][:maximum]
    if len(chosen) < minimum:
        chosen = [result.index for result in ranked[:minimum]]
    return sorted(chosen)


def agent(obs, config=None):
    if not isinstance(obs, Observation):
        obs = to_observation_class(obs)
    if obs.select is None:
        return list(DECK)
    if obs.current is None:
        return []
    board = BoardView(obs)
    return choose_indices(board)

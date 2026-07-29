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
from dataclasses import dataclass, replace
from itertools import combinations
from math import comb
from types import SimpleNamespace
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
SUGURI = 1191
JUDGE = 1213
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
    1159, 1191, 1227, 1227, 1227, 1227, 666, 1122, 1229, 1225,
    1189, 1213, 1213, 1189, 1182, 1182, 1262, 1262, 1122, 17,
    3, 3, 3, 3, 3, 3, 3, 1191, 3, 1137,
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


def active_status_blocks_attack_for_board(board: Any) -> bool:
    player = getattr(board, "me", None)
    return bool(getattr(player, "asleep", False) or getattr(player, "paralyzed", False))


def active_can_declare_attack_this_turn_for_board(board: Any) -> bool:
    if active_status_blocks_attack_for_board(board):
        return False
    state = getattr(board, "state", None)
    turn = getattr(state, "turn", None)
    first_player = getattr(state, "firstPlayer", None)
    your_index = getattr(state, "yourIndex", getattr(board, "my_index", None))
    if turn == 1 and first_player is not None and your_index is not None and int(first_player) == int(your_index):
        return False
    return True


def _normalized_attack_text(attack: Any) -> str:
    text = str(getattr(attack, "text", "") or "")
    if not text:
        real_attack = ATTACK_TABLE.get(int(getattr(attack, "attackId", -1)))
        text = str(getattr(real_attack, "text", "") or "")
    return text.replace("\u2019", "'").replace("\xa0", " ").replace("Pok\u00e9mon", "Pokemon").lower()


def _can_pay_after_losing_energy(
    attack: Any,
    energy_tokens: Sequence[Any],
    loss_count: int,
    required_type: Optional[Any] = None,
) -> bool:
    tokens = tuple(energy_tokens)
    if loss_count <= 0:
        return can_pay_attack_with_tokens(attack, tokens)
    candidate_indexes = [
        index
        for index, token in enumerate(tokens)
        if required_type is None or token == required_type
    ]
    if len(candidate_indexes) < loss_count:
        return False
    for lost_indexes in combinations(candidate_indexes, loss_count):
        lost = set(lost_indexes)
        remaining = tuple(token for index, token in enumerate(tokens) if index not in lost)
        if can_pay_attack_with_tokens(attack, remaining):
            return True
    return False


def can_continue_attack_after_use_with_tokens(attack: Any, energy_tokens: Sequence[Any]) -> bool:
    if not can_pay_attack_with_tokens(attack, energy_tokens):
        return False
    text = _normalized_attack_text(attack)
    if not text or "opponent's active pokemon" in text:
        return True
    if "you may discard" in text or "discard up to" in text or "you may put all energy" in text:
        return True
    tokens = tuple(energy_tokens)
    if "discard all energy from this pokemon" in text or "discard all energy attached to this pokemon" in text:
        return can_pay_attack_with_tokens(attack, ())
    if "shuffle all energy attached to this pokemon into your deck" in text:
        return can_pay_attack_with_tokens(attack, ())
    symbol_types = {
        "{w}": EnergyType.WATER,
        "{d}": EnergyType.DARKNESS,
        "{c}": EnergyType.COLORLESS,
        "{g}": EnergyType.GRASS,
        "{r}": EnergyType.FIRE,
        "{l}": EnergyType.LIGHTNING,
        "{p}": EnergyType.PSYCHIC,
        "{f}": EnergyType.FIGHTING,
        "{m}": EnergyType.METAL,
    }
    for symbol, energy_type in symbol_types.items():
        if f"discard all {symbol} energy from this pokemon" in text:
            remaining = tuple(token for token in tokens if token != energy_type)
            return can_pay_attack_with_tokens(attack, remaining)
        if f"discard a {symbol} energy from this pokemon" in text:
            return _can_pay_after_losing_energy(attack, tokens, 1, energy_type)
    loss_count = 0
    for count in range(9, 1, -1):
        if f"discard {count} energy from this pokemon" in text or f"move {count} energy from this pokemon" in text:
            loss_count = count
            break
    if loss_count == 0 and ("discard an energy from this pokemon" in text or "move an energy from this pokemon" in text):
        loss_count = 1
    if loss_count == 0:
        return True
    return _can_pay_after_losing_energy(attack, tokens, loss_count)


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
    reachable_attack_id: Optional[int] = None
    reachable_damage: int = 0
    reachable_knockout: bool = False
    reachable_prizes_taken: int = 0
    reachable_wins_game: bool = False
    reachable_can_continue_attack: bool = False
    expected_reachable_attack_id: Optional[int] = None
    expected_reachable_damage: float = 0.0
    expected_reachable_knockout: bool = False
    expected_reachable_prizes_taken: float = 0.0
    expected_reachable_wins_game: bool = False
    expected_hit_probability: float = 0.0
    additional_card_consumed: bool = False
    equivalent_normal_attach_available: bool = False
    retreat_energy_cost: int = 0
    important_energy_loss: int = 0
    improves_damage: bool = False
    healed_damage: int = 0
    recovered_energy_count: int = 0
    board_energy_removed: int = 0
    next_knockout_avoided: bool = False
    avoids_prize_loss: bool = False
    prizes_preserved: int = 0
    avoids_board_out: bool = False
    preserves_primary_pokemon: bool = False
    equivalent_evolution_available: bool = False
    completes_next_attacker: bool = False
    development_value: float = 0.0
    development_probability: float = 0.0
    target_id: Optional[int] = None
    target_serial: Optional[int] = None
    recommended_target_id: Optional[int] = None
    recommended_target_serial: Optional[int] = None
    reasons: Tuple[str, ...] = ()


def wally_preservation_fact_is_high_value(outcome: ImmediateOutcome) -> bool:
    return (
        outcome.avoids_board_out
        or outcome.avoids_prize_loss
        or (
            outcome.preserves_primary_pokemon
            and outcome.healed_damage >= 100
            and outcome.recovered_energy_count >= 2
        )
    )


def wally_effect_fact_key(outcome: ImmediateOutcome) -> Tuple[Any, ...]:
    return (
        wally_preservation_fact_is_high_value(outcome),
        outcome.prizes_preserved,
        outcome.avoids_board_out,
        outcome.healed_damage,
        outcome.recovered_energy_count,
        -outcome.board_energy_removed,
    )


@dataclass(frozen=True)
class SameTurnAccess:
    reasons: Tuple[str, ...]
    retreat_energy_cost: int = 0
    important_energy_loss: int = 0


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
class NightStretcherCandidateFacts:
    target_id: int
    target_serial: Optional[int]
    same_turn_usable: bool
    same_turn_attach_available: bool
    same_turn_attack_gap_reduced: bool
    same_turn_attack_enabled: bool
    same_turn_retreat_enabled: bool
    next_attacker_gap_reduced: bool
    next_attacker_completed: bool
    board_out_avoided: bool
    next_turn_evolution_supported: bool
    returns_to_hand_only: bool


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

    def current_turn_attached_energy_ids(self) -> Tuple[Tuple[int, int, int], ...]:
        logs = getattr(getattr(self, "obs", None), "logs", None)
        if logs is None:
            logs = getattr(self, "logs", [])
        attached = []
        for log in logs or []:
            if getattr(log, "type", None) != LogType.ATTACH or getattr(log, "playerIndex", None) != self.my_index:
                continue
            card_id = getattr(log, "cardId", None)
            serial = getattr(log, "serial", None)
            target_serial = getattr(log, "serialTarget", None)
            if card_id is not None and serial is not None and target_serial is not None:
                attached.append((int(card_id), int(serial), int(target_serial)))
        return tuple(attached)

    def energy_switch_has_equivalent_normal_attach_result(self) -> bool:
        current_turn_attached = self.current_turn_attached_energy_ids()
        if not current_turn_attached:
            return False
        for energy_id, energy_serial, source_serial in current_turn_attached:
            source = next((pokemon for pokemon in self.all_my_pokemon if getattr(pokemon, "serial", None) == source_serial), None)
            if source is None:
                continue
            if not any(getattr(card, "serial", None) == energy_serial for card in getattr(source, "energyCards", []) or []):
                continue
            for target in self.all_my_pokemon:
                if target is source:
                    continue
                if energy_tokens_for_attach(energy_id, target) is not None:
                    return True
        return False

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
        known_out += self.known_prize_ids().count(cid)
        known_out += sum(1 for pokemon in self.all_my_pokemon if self.pid(pokemon) == cid)
        return known_out < total

    def remaining_possible_count(self, cid: int, total: Optional[int] = None) -> int:
        if self.deck_view:
            return self.deck_ids.count(cid)
        total = DECK.count(cid) if total is None else total
        known_out = self.hand_ids.count(cid) + self.discard_ids.count(cid)
        known_out += self.known_prize_ids().count(cid)
        known_out += sum(1 for pokemon in self.all_my_pokemon if self.pid(pokemon) == cid)
        return max(0, total - known_out)

    def known_prize_ids(self) -> List[int]:
        prize = getattr(self.me, "prize", None)
        if not isinstance(prize, list):
            return []
        return [card.id for card in prize if card is not None and getattr(card, "id", None) is not None]

    def unknown_prize_count(self) -> int:
        prize = getattr(self.me, "prize", None)
        if isinstance(prize, list):
            return len([card for card in prize if card is None or getattr(card, "id", None) is None])
        try:
            return max(0, self.my_prizes_left())
        except Exception:
            return 0

    def remaining_deck_count(self) -> int:
        if self.deck_view:
            return len(self.deck_ids)
        count = getattr(self.me, "deckCount", None)
        if count is not None:
            return max(0, safe_int(count))
        known_cards = len(self.hand_ids) + len(self.discard_ids) + len(self.all_my_pokemon)
        known_cards += sum(len(self.energies(pokemon)) + len(getattr(pokemon, "tools", []) or []) for pokemon in self.all_my_pokemon)
        return max(0, len(DECK) - known_cards)

    def pokegear_hit_probability(self, cid: int) -> float:
        deck_count = self.remaining_deck_count()
        success_count = min(deck_count, self.remaining_possible_count(cid))
        if deck_count <= 0 or success_count <= 0:
            return 0.0
        if not self.deck_view:
            hidden_count = max(deck_count, deck_count + self.unknown_prize_count())
            success_count = min(success_count, hidden_count)
            look_count = min(7, deck_count, hidden_count)
            miss_count = max(0, hidden_count - success_count)
            miss_probability = 1.0
            for offset in range(look_count):
                remaining_cards = hidden_count - offset
                remaining_misses = miss_count - offset
                if remaining_misses <= 0:
                    miss_probability = 0.0
                    break
                miss_probability *= remaining_misses / remaining_cards
            return max(0.0, min(1.0, 1.0 - miss_probability))
        look_count = min(7, deck_count)
        miss_count = max(0, deck_count - success_count)
        miss_probability = 1.0
        for offset in range(look_count):
            remaining_cards = deck_count - offset
            remaining_misses = miss_count - offset
            if remaining_misses <= 0:
                miss_probability = 0.0
                break
            miss_probability *= remaining_misses / remaining_cards
        return max(0.0, min(1.0, 1.0 - miss_probability))

    def deck_presence_probability(self, cid: int) -> float:
        if self.deck_view:
            return 1.0 if cid in self.deck_ids else 0.0
        deck_count = self.remaining_deck_count()
        hidden_count = max(deck_count, deck_count + self.unknown_prize_count())
        success_count = min(hidden_count, self.remaining_possible_count(cid))
        if deck_count <= 0 or hidden_count <= 0 or success_count <= 0:
            return 0.0
        miss_count = max(0, hidden_count - success_count)
        miss_probability = 1.0
        for offset in range(min(deck_count, hidden_count)):
            remaining_cards = hidden_count - offset
            remaining_misses = miss_count - offset
            if remaining_misses <= 0:
                miss_probability = 0.0
                break
            miss_probability *= remaining_misses / remaining_cards
        return max(0.0, min(1.0, 1.0 - miss_probability))

    def _comb_probability_no_success(self, total: int, success: int, draws: int) -> float:
        if success <= 0:
            return 1.0
        if total <= 0 or draws <= 0:
            return 1.0
        if draws > total:
            draws = total
        if total - success < draws:
            return 0.0
        return comb(total - success, draws) / comb(total, draws)

    def pokegear_chain_hit_probability_from_counts(
        self,
        hidden_count: int,
        deck_count: int,
        look_count: int,
        supporter_count: int,
        evolution_count: int,
    ) -> float:
        if deck_count <= 0 or hidden_count <= 0 or supporter_count <= 0 or evolution_count <= 0:
            return 0.0
        look_count = min(look_count, deck_count, hidden_count)
        deck_count = min(deck_count, hidden_count)
        supporter_count = min(supporter_count, hidden_count)
        evolution_count = min(evolution_count, hidden_count)
        no_supporter_in_look = self._comb_probability_no_success(hidden_count, supporter_count, look_count)
        no_evolution_in_deck = self._comb_probability_no_success(hidden_count, evolution_count, deck_count)
        if evolution_count > hidden_count - deck_count:
            both_missing = 0.0
        else:
            no_evolution_positions = comb(hidden_count - deck_count, evolution_count) / comb(hidden_count, evolution_count)
            remaining_after_evolution = hidden_count - evolution_count
            avoid_look_after_evolution = self._comb_probability_no_success(remaining_after_evolution, look_count, supporter_count)
            both_missing = no_evolution_positions * avoid_look_after_evolution
        probability = 1.0 - no_supporter_in_look - no_evolution_in_deck + both_missing
        return max(0.0, min(1.0, probability))

    def pokegear_chain_hit_probability(self, supporter_id: int, evolution_id: int) -> float:
        if supporter_id == evolution_id:
            return self.pokegear_hit_probability(supporter_id)
        if self.deck_view:
            if evolution_id not in self.deck_ids:
                return 0.0
            return self.pokegear_hit_probability(supporter_id)
        deck_count = self.remaining_deck_count()
        prize_count = self.unknown_prize_count()
        hidden_count = max(deck_count, deck_count + prize_count)
        supporter_count = min(hidden_count, self.remaining_possible_count(supporter_id))
        evolution_count = min(hidden_count, self.remaining_possible_count(evolution_id))
        if deck_count <= 0 or hidden_count <= 0 or supporter_count <= 0 or evolution_count <= 0:
            return 0.0
        look_count = min(7, deck_count, hidden_count)
        return self.pokegear_chain_hit_probability_from_counts(
            hidden_count,
            deck_count,
            look_count,
            supporter_count,
            evolution_count,
        )

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

    def salvatore_can_evolve_from_deck_this_turn(self, pokemon: Optional[Pokemon], evolution_id: int) -> bool:
        if pokemon is None or hp_left(pokemon) <= 0 or not self.evolves_from(evolution_id, pokemon):
            return False
        data = self.data(evolution_id)
        if data is None or getattr(data, "skills", []):
            return False
        return self.remaining_possible(evolution_id)

    def salvatore_deck_target_evolution(self, pokemon: Optional[Pokemon]) -> Optional[int]:
        pid = self.pid(pokemon)
        if pid == HITODEMAN:
            evolution_id = MEGA_STARMIE_EX
        elif pid == YUKIWARASHI:
            evolution_id = MEGA_YUKIMENOKO_EX
        else:
            return None
        return evolution_id if self.salvatore_can_evolve_from_deck_this_turn(pokemon, evolution_id) else None

    def has_salvatore_deck_target(self, evolution_id: Optional[int] = None) -> bool:
        return any(
            target is not None and (evolution_id is None or target == evolution_id)
            for target in (self.salvatore_deck_target_evolution(pokemon) for pokemon in self.all_my_pokemon)
        )

    def has_salvatore_target(self, evolution_id: Optional[int] = None) -> bool:
        return any(
            target is not None and (evolution_id is None or target == evolution_id)
            for target in (self.salvatore_target_evolution(pokemon) for pokemon in self.all_my_pokemon)
        )

    def is_salvatore_target(self, cid: Optional[int]) -> bool:
        data = self.data(cid)
        if data is None or data.cardType != CardType.POKEMON or data.basic or getattr(data, "skills", []):
            return False
        return self.has_salvatore_deck_target(cid)

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
        if not active_can_declare_attack_this_turn_for_board(self):
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
        evaluator = ImmediateOutcomeEvaluator(self)
        for pokemon in self.all_my_pokemon:
            outcome = evaluator._wally_target_outcome(pokemon)
            if (
                outcome.supported
                and outcome.healed_damage >= 100
                and (
                    outcome.preserves_primary_pokemon
                    or hp_left(pokemon) <= self.opp_max_damage() + 40
                )
            ):
                return True
        return False

    def salvatore_live(self) -> bool:
        return not self.state.supporterPlayed and self.has_salvatore_deck_target()

    def can_use_supporter(self, cid: int) -> bool:
        return self.is_supporter(cid) and not self.state.supporterPlayed

    def lillie_effect_facts(self) -> LillieEffectFacts:
        hand_size = len(self.hand_ids)
        shuffle_count = max(0, hand_size - (1 if LILLIE_DETERMINATION in self.hand_ids else 0))
        draw_count = 8 if self.my_prizes_left() == 6 else 6
        return LillieEffectFacts(hand_size=hand_size, shuffle_count=shuffle_count, draw_count=draw_count)

    def has_tool_scrapper_target(self) -> bool:
        return any(getattr(pokemon, "tools", []) for pokemon in self.all_my_pokemon + self.all_opp_pokemon)

    def hero_cape_target_roi(self, pokemon: Optional[Pokemon]) -> str:
        if (
            pokemon is None
            or self.pid(pokemon) not in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}
            or getattr(pokemon, "tools", [])
        ):
            return "invalid"
        if pokemon is self.active:
            incoming_damage = self.best_damage(self.opp_active)
            current_hp = hp_left(pokemon)
            if incoming_damage <= 0:
                return "no_current_damage"
            hits_before = (current_hp + incoming_damage - 1) // incoming_damage
            hits_after = (current_hp + 100 + incoming_damage - 1) // incoming_damage
            if hits_before == 1 and hits_after > 1:
                return "prevents_active_knockout"
            if hits_after > hits_before:
                return "extends_active_survival"
            return "no_clear_benefit"
        role = self.role_facts(pokemon)
        if role.attack_ready or role.energy_count > 0:
            return "invested_without_clear_survival"
        return "no_clear_benefit"

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
            facts = self.night_stretcher_recovery_facts()
            return (
                HAND_ACTIVITY_LIVE_NOW
                if any(not candidate.returns_to_hand_only for candidate in facts)
                else HAND_ACTIVITY_LOW
            )
        if cid == ENERGY_SWITCH:
            return HAND_ACTIVITY_KEEP if self.starmie_needs_energy() else HAND_ACTIVITY_LOW
        if cid == BEFEHL_VON_BOSS:
            return HAND_ACTIVITY_LIVE_NOW if self.can_use_supporter(BEFEHL_VON_BOSS) and bool(self.opp_bench) else HAND_ACTIVITY_LOW
        if cid == TOOL_SCRAPPER:
            return HAND_ACTIVITY_LIVE_NOW if self.has_tool_scrapper_target() else HAND_ACTIVITY_LOW
        if cid == HERO_CAPE:
            target_facts = [
                (pokemon, self.hero_cape_target_roi(pokemon))
                for pokemon in self.all_my_pokemon
            ]
            if any(
                roi in {"prevents_active_knockout", "extends_active_survival"}
                for _, roi in target_facts
            ):
                return HAND_ACTIVITY_LIVE_NOW
            if any(
                roi == "invested_without_clear_survival"
                or (
                    roi in {"no_current_damage", "no_clear_benefit"}
                    and (
                        self.role_facts(pokemon).attack_ready
                        or self.role_facts(pokemon).energy_count > 0
                    )
                )
                for pokemon, roi in target_facts
            ):
                return HAND_ACTIVITY_KEEP
            return HAND_ACTIVITY_LOW
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

    def night_stretcher_recovery_facts(self) -> Tuple[NightStretcherCandidateFacts, ...]:
        effect = None
        if self.select.effect is not None:
            effect = self.select.effect.id
        elif self.select.contextCard is not None:
            effect = self.select.contextCard.id

        cards: List[Any] = []
        if effect == TANKER:
            seen: set[Tuple[int, Optional[int]]] = set()
            for _, option in self.iter_options():
                cid = self.option_card(option)
                if cid is None:
                    continue
                source_cards = self.cards_in_area(option.area, option.playerIndex)
                card = None
                if source_cards is not None and option.index is not None and 0 <= option.index < len(source_cards):
                    card = source_cards[option.index]
                serial = getattr(card, "serial", getattr(option, "serial", None))
                key = (int(cid), serial)
                if key in seen:
                    continue
                seen.add(key)
                cards.append(card if card is not None else SimpleNamespace(id=cid, serial=serial))
        else:
            cards = [
                card
                for card in self.discard
                if self.is_pokemon(card.id)
                or (
                    self.is_energy(card.id)
                    and getattr(self.data(card.id), "cardType", None) == CardType.BASIC_ENERGY
                )
            ]

        return tuple(self.night_stretcher_candidate_facts(card) for card in cards)

    def night_stretcher_candidate_facts(self, card: Any) -> NightStretcherCandidateFacts:
        cid = int(card.id)
        serial = getattr(card, "serial", None)
        data = self.data(cid)
        is_pokemon = self.is_pokemon(cid)
        is_basic_energy = (
            self.is_energy(cid)
            and data is not None
            and data.cardType == CardType.BASIC_ENERGY
        )
        duplicate_in_hand = cid in self.hand_ids

        same_turn_attach_available = False
        same_turn_attack_gap_reduced = False
        same_turn_attack_enabled = False
        same_turn_retreat_enabled = False
        next_attacker_gap_reduced = False
        next_attacker_completed = False
        board_out_avoided = False
        next_turn_evolution_supported = False
        same_turn_usable = False

        if is_basic_energy and not duplicate_in_hand:
            attach_available = not bool(getattr(self.state, "energyAttached", False))
            attach_tokens_by_target = {
                getattr(target, "serial", index): energy_tokens_for_attach(cid, target)
                for index, target in enumerate(self.all_my_pokemon)
            }
            attach_available = attach_available and any(tokens is not None for tokens in attach_tokens_by_target.values())
            same_turn_attach_available = attach_available

            if attach_available and self.active is not None:
                added = energy_tokens_for_attach(cid, self.active)
                if added is not None:
                    before_tokens = tuple(self.energy_tokens(self.active))
                    after_tokens = before_tokens + tuple(added)
                    active_data = self.data(self.pid(self.active))
                    attacks = [
                        self.attack(attack_id)
                        for attack_id in (getattr(active_data, "attacks", []) if active_data is not None else [])
                    ]
                    attacks = [attack for attack in attacks if attack is not None]
                    if attacks:
                        important = max(
                            attacks,
                            key=lambda attack: (
                                self.attack_damage_for_card(self.pid(self.active), attack),
                                len(getattr(attack, "energies", []) or []),
                            ),
                        )
                        before_gap = self.attack_energy_gap(important, before_tokens)
                        after_gap = self.attack_energy_gap(important, after_tokens)
                        same_turn_attack_gap_reduced = after_gap.missing_units < before_gap.missing_units
                        newly_ready = any(
                            not self.attack_energy_gap(attack, before_tokens).ready
                            and self.attack_energy_gap(attack, after_tokens).ready
                            for attack in attacks
                        )
                        if newly_ready:
                            same_turn_attack_enabled = ImmediateOutcomeEvaluator(
                                self
                            ).active_can_declare_attack_this_turn()

                    retreat_cost = ImmediateOutcomeEvaluator(self)._effective_retreat_cost(self.active)
                    current_energy = self.energy_count(self.active)
                    if (
                        retreat_cost > current_energy
                        and retreat_cost <= current_energy + len(added)
                        and not bool(getattr(self.me, "asleep", False))
                        and not bool(getattr(self.me, "paralyzed", False))
                        and ImmediateOutcomeEvaluator(self).active_can_declare_attack_this_turn()
                    ):
                        same_turn_retreat_enabled = any(
                            self.can_pay_attack(target, self.attack(attack_id))
                            and not self.attack_blocked_by_ex_wall_for_card(
                                self.pid(target),
                                self.opp_active,
                                self.attack(attack_id),
                            )
                            for target in self.bench
                            for attack_id in getattr(self.data(self.pid(target)), "attacks", [])
                        )

            if attach_available:
                for target in self.bench:
                    added = energy_tokens_for_attach(cid, target)
                    if added is None:
                        continue
                    target_data = self.data(self.pid(target))
                    attacks = [
                        self.attack(attack_id)
                        for attack_id in (getattr(target_data, "attacks", []) if target_data is not None else [])
                    ]
                    attacks = [attack for attack in attacks if attack is not None]
                    if not attacks:
                        continue
                    important = max(
                        attacks,
                        key=lambda attack: (
                            self.attack_damage_for_card(self.pid(target), attack),
                            len(getattr(attack, "energies", []) or []),
                        ),
                    )
                    before = self.attack_energy_gap(important, self.energy_tokens(target))
                    after = self.attack_energy_gap(
                        important,
                        tuple(self.energy_tokens(target)) + tuple(added),
                    )
                    if after.missing_units < before.missing_units:
                        next_attacker_gap_reduced = True
                    if not before.ready and after.ready:
                        next_attacker_completed = True

            if not attach_available and not self._night_stretcher_ready_evolved_attacker():
                for target in self.all_my_pokemon:
                    evolution_ids = [
                        evolution_id
                        for evolution_id in DECK
                        if self.card_evolves_from_card(evolution_id, self.pid(target))
                    ]
                    for evolution_id in evolution_ids:
                        evolution_data = self.data(evolution_id)
                        attacks = [
                            self.attack(attack_id)
                            for attack_id in (
                                getattr(evolution_data, "attacks", [])
                                if evolution_data is not None
                                else []
                            )
                        ]
                        attacks = [attack for attack in attacks if attack is not None]
                        if not attacks:
                            continue
                        important = max(
                            attacks,
                            key=lambda attack: (
                                self.attack_damage_for_card(evolution_id, attack),
                                len(getattr(attack, "energies", []) or []),
                            ),
                        )
                        before = self.attack_energy_gap(important, self.energy_tokens_as(target, evolution_id))
                        added = energy_tokens_for_attach(cid, target)
                        if added is None:
                            continue
                        after = self.attack_energy_gap(
                            important,
                            tuple(self.energy_tokens_as(target, evolution_id)) + tuple(added),
                        )
                        if after.missing_units < before.missing_units:
                            next_attacker_gap_reduced = True
                        if not before.ready and after.ready:
                            next_attacker_completed = True

            same_turn_usable = any(
                (
                    same_turn_attack_gap_reduced,
                    same_turn_attack_enabled,
                    same_turn_retreat_enabled,
                    next_attacker_gap_reduced and attach_available,
                    next_attacker_completed and attach_available,
                )
            )

        elif is_pokemon and not duplicate_in_hand:
            is_basic = bool(getattr(data, "basic", False)) if data is not None else False
            if is_basic and self.bench_space > 0:
                same_turn_usable = True
                board_out_avoided = len(self.all_my_pokemon) == 1
                next_turn_evolution_supported = any(
                    evolution_id in self.hand_ids
                    and self.card_evolves_from_card(evolution_id, cid)
                    for evolution_id in DECK
                )
            elif not is_basic:
                evolution_targets = [
                    target
                    for target in self.all_my_pokemon
                    if self.card_evolves_from_card(cid, self.pid(target))
                ]
                next_turn_evolution_supported = bool(evolution_targets)
                same_turn_usable = any(
                    not bool(getattr(target, "appearThisTurn", False))
                    for target in evolution_targets
                )

        returns_to_hand_only = not any(
            (
                same_turn_usable,
                same_turn_attack_gap_reduced,
                same_turn_attack_enabled,
                same_turn_retreat_enabled,
                next_attacker_gap_reduced,
                next_attacker_completed,
                board_out_avoided,
                next_turn_evolution_supported,
            )
        )
        return NightStretcherCandidateFacts(
            target_id=cid,
            target_serial=serial,
            same_turn_usable=same_turn_usable,
            same_turn_attach_available=same_turn_attach_available,
            same_turn_attack_gap_reduced=same_turn_attack_gap_reduced,
            same_turn_attack_enabled=same_turn_attack_enabled,
            same_turn_retreat_enabled=same_turn_retreat_enabled,
            next_attacker_gap_reduced=next_attacker_gap_reduced,
            next_attacker_completed=next_attacker_completed,
            board_out_avoided=board_out_avoided,
            next_turn_evolution_supported=next_turn_evolution_supported,
            returns_to_hand_only=returns_to_hand_only,
        )

    def _night_stretcher_ready_evolved_attacker(self) -> bool:
        for target in self.all_my_pokemon:
            data = self.data(self.pid(target))
            if data is None or getattr(data, "basic", False):
                continue
            if any(
                self.can_pay_attack(target, self.attack(attack_id))
                for attack_id in getattr(data, "attacks", [])
            ):
                return True
        return False

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
        stadium = getattr(self.state, "stadium", None) or ()
        if not stadium:
            return False
        current = stadium[0]
        owner = getattr(current, "playerIndex", None)
        return (
            card_id(current) != SURFING_BEACH
            and owner is not None
            and int(owner) != int(self.my_index)
        )


class ImmediateOutcomeEvaluator:
    def __init__(self, board: BoardView):
        self.b = board

    def is_surfing_beach_ability(self, option: Any) -> bool:
        if option.type != OptionType.ABILITY or option.area != AreaType.STADIUM:
            return False
        index = getattr(option, "index", None)
        stadium = getattr(getattr(self.b, "state", None), "stadium", None) or ()
        if index is None or not 0 <= int(index) < len(stadium):
            return False
        return card_id(stadium[int(index)]) == SURFING_BEACH

    def is_surfing_beach_play_ability_available(self, option: Any) -> bool:
        if option.type != OptionType.PLAY or self.b.option_card(option) != SURFING_BEACH:
            return False
        state = getattr(self.b, "state", None)
        if getattr(state, "stadiumPlayed", False):
            return False
        stadium = getattr(state, "stadium", None) or ()
        if stadium and card_id(stadium[0]) == SURFING_BEACH:
            return False
        return any(candidate is option for _, candidate in self.b.iter_options())

    def evaluate_surfing_beach_ability(
        self,
        option: Any,
        after_stadium_play: bool = False,
    ) -> ImmediateOutcome:
        available = (
            self.is_surfing_beach_play_ability_available(option)
            if after_stadium_play
            else self.is_surfing_beach_ability(option)
        )
        if not available:
            return ImmediateOutcome(supported=False, reasons=("unsupported_surfing_beach_ability",))
        candidates = [
            self.evaluate_switch_target(target, "surfing_beach")
            for target in self.b.bench
        ]
        candidates = [candidate for candidate in candidates if candidate.supported]
        if not candidates:
            return ImmediateOutcome(supported=False, reasons=("surfing_beach_ability_no_target",))
        best = max(
            candidates,
            key=lambda outcome: (
                outcome.reachable_wins_game,
                outcome.reachable_knockout,
                outcome.reachable_prizes_taken,
                outcome.reachable_damage,
                outcome.reachable_attack_id is not None,
            ),
        )
        return ImmediateOutcome(
            reachable_attack_id=best.reachable_attack_id,
            reachable_damage=best.reachable_damage,
            reachable_knockout=best.reachable_knockout,
            reachable_prizes_taken=best.reachable_prizes_taken,
            reachable_wins_game=best.reachable_wins_game,
            recommended_target_id=best.target_id,
            recommended_target_serial=best.target_serial,
            reasons=("surfing_beach_ability",) + best.reasons,
        )

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
        after_energy_ids = tuple(self.b.energies(target)) + (int(card_id),)
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
        reachable_outcomes: List[ImmediateOutcome] = []
        if target is self.b.active:
            direct_outcome = self._best_attach_reachable_attack_outcome(target, enabled_ids, after_tokens)
            if direct_outcome is not None:
                reachable_outcomes.append(direct_outcome)
        access_outcome = self._best_attach_access_attack_outcome(target, enabled_ids, after_tokens, after_energy_ids)
        if access_outcome is not None:
            reachable_outcomes.append(access_outcome)
        boss_outcome = self._best_attach_boss_attack_outcome(target, enabled_ids, after_tokens)
        if boss_outcome is not None:
            reachable_outcomes.append(boss_outcome)
        reachable_outcome = self._best_reachable_attack_outcome(reachable_outcomes) if reachable_outcomes else None
        immediate_attack_ids = self._unblocked_attack_ids(target, enabled_ids) if target is self.b.active else ()
        if card_id == IGNITION_ENERGY and target is self.b.active and enabled_ids and immediate_attack_ids:
            reasons.append("ignition_immediate_attack")
        if reachable_outcome is not None and reachable_outcome.knockout:
            reasons.append("attach_reaches_knockout")
        if reachable_outcome is not None and reachable_outcome.wins_game:
            reasons.append("attach_reaches_win")
        if reachable_outcome is not None:
            for reason in reachable_outcome.reasons:
                if reason in {
                    "attach_access_via_retreat",
                    "attach_access_via_surfing_beach",
                    "attach_access_via_boss",
                } and reason not in reasons:
                    reasons.append(reason)

        return ImmediateOutcome(
            enables_attack=bool(enabled_ids),
            enabled_attack_ids=enabled_ids,
            reachable_attack_id=reachable_outcome.reachable_attack_id if reachable_outcome is not None else None,
            reachable_damage=reachable_outcome.damage if reachable_outcome is not None else 0,
            reachable_knockout=bool(reachable_outcome and reachable_outcome.knockout),
            reachable_prizes_taken=reachable_outcome.prizes_taken if reachable_outcome is not None else 0,
            reachable_wins_game=bool(reachable_outcome and reachable_outcome.wins_game),
            reachable_can_continue_attack=bool(reachable_outcome and reachable_outcome.reachable_can_continue_attack),
            retreat_energy_cost=reachable_outcome.retreat_energy_cost if reachable_outcome is not None else 0,
            important_energy_loss=reachable_outcome.important_energy_loss if reachable_outcome is not None else 0,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def _best_attach_reachable_attack_outcome(
        self,
        attacker: Pokemon,
        attack_ids: Sequence[int],
        after_tokens: Sequence[Any],
    ) -> Optional[ImmediateOutcome]:
        if not self.active_can_declare_attack_this_turn():
            return None
        outcomes = [self._attack_outcome_with_tokens(attacker, attack_id, after_tokens, "attach_reachable_attack") for attack_id in attack_ids]
        effective_outcomes = [outcome for outcome in outcomes if outcome.supported and not outcome.blocked]
        if not effective_outcomes:
            return None
        outcome = self._best_reachable_attack_outcome(effective_outcomes)
        attack = self.b.attack(outcome.reachable_attack_id)
        return replace(
            outcome,
            reachable_can_continue_attack=bool(attack and can_continue_attack_after_use_with_tokens(attack, after_tokens)),
        )

    def _best_attach_access_attack_outcome(
        self,
        attach_target: Pokemon,
        attack_ids: Sequence[int],
        after_tokens: Sequence[Any],
        after_energy_ids: Sequence[int],
    ) -> Optional[ImmediateOutcome]:
        if not self._can_declare_attack_after_same_turn_access():
            return None
        access = self._best_same_turn_access(attach_target, bool(attack_ids), after_tokens, after_energy_ids)
        if access is None:
            return None
        outcomes = []
        attackers = (attach_target,) if attach_target in self.b.bench else tuple(self.b.bench)
        for attacker in attackers:
            tokens = after_tokens if attacker is attach_target else self.b.energy_tokens(attacker)
            data = self.b.data(self.b.pid(attacker))
            if data is None:
                continue
            for attack_id in data.attacks:
                outcome = self._attack_outcome_with_tokens(attacker, attack_id, tokens, "attach_access_reachable_attack")
                if outcome.supported and not outcome.blocked:
                    outcomes.append(outcome)
        if not outcomes:
            return None
        best = self._best_reachable_attack_outcome(outcomes)
        return replace(
            best,
            retreat_energy_cost=access.retreat_energy_cost,
            important_energy_loss=access.important_energy_loss,
            reasons=best.reasons + access.reasons,
        )

    def _best_same_turn_access(
        self,
        attach_target: Pokemon,
        attach_enabled_attack: bool,
        after_tokens: Sequence[Any],
        after_energy_ids: Sequence[int],
    ) -> Optional[SameTurnAccess]:
        candidates: List[SameTurnAccess] = []
        if attach_target in self.b.bench and attach_enabled_attack and self._has_surfing_beach_access_option(attach_target):
            candidates.append(SameTurnAccess(("attach_access_via_surfing_beach",), 0, 0))
        retreat_access = self._retreat_access_after_attach(attach_target, after_tokens, after_energy_ids, attach_enabled_attack)
        if retreat_access is not None:
            candidates.append(retreat_access)
        if not candidates:
            return None
        return min(candidates, key=lambda access: (access.retreat_energy_cost, access.important_energy_loss))

    def _retreat_access_after_attach(
        self,
        attach_target: Pokemon,
        after_tokens: Sequence[Any],
        after_energy_ids: Sequence[int],
        attach_enabled_attack: bool,
    ) -> Optional[SameTurnAccess]:
        active = self.b.active
        if active is None:
            return None
        if self.active_status_blocks_attack():
            return None
        cost = self._effective_retreat_cost(active)
        before_tokens = tuple(self.b.energy_tokens(active))
        retreat_tokens = tuple(after_tokens) if attach_target is active else before_tokens
        before_can_retreat = len(before_tokens) >= cost
        after_can_retreat = len(retreat_tokens) >= cost
        if not after_can_retreat:
            return None
        retreat_option_visible = self._has_retreat_access_option()
        if attach_target is active and not before_can_retreat:
            pass
        elif retreat_option_visible and attach_target in self.b.bench and attach_enabled_attack:
            pass
        else:
            return None
        if cost == 0:
            important_loss = 0
        elif attach_target is active:
            important_loss = self._possible_important_energy_loss_from_ids(after_energy_ids, cost)
        else:
            important_loss = self._possible_important_energy_loss(active, cost)
        return SameTurnAccess(("attach_access_via_retreat",), cost, important_loss)

    def _possible_important_energy_loss_from_ids(self, energy_ids: Sequence[int], cost: int) -> int:
        important_cards = sum(1 for energy_id in energy_ids if energy_id in {BASIC_WATER_ENERGY, IGNITION_ENERGY})
        nonimportant_capacity = max(0, len(energy_ids) - important_cards)
        return min(important_cards, max(0, cost - nonimportant_capacity))

    def _best_attach_boss_attack_outcome(
        self,
        attach_target: Pokemon,
        attack_ids: Sequence[int],
        after_tokens: Sequence[Any],
    ) -> Optional[ImmediateOutcome]:
        if attach_target is not self.b.active or not attack_ids:
            return None
        if not self.active_can_declare_attack_this_turn():
            return None
        if self.b.state.supporterPlayed or BEFEHL_VON_BOSS not in self.b.hand_ids or not self.b.opp_bench:
            return None
        if not any(option.type == OptionType.PLAY and self.b.option_card(option) == BEFEHL_VON_BOSS for _, option in self.b.iter_options()):
            return None
        outcomes = []
        for target in self.b.opp_bench:
            for attack_id in attack_ids:
                outcome = self._attack_outcome_with_tokens_against(
                    attach_target,
                    attack_id,
                    after_tokens,
                    target,
                    "attach_boss_reachable_attack",
                )
                if outcome.supported and not outcome.blocked:
                    outcomes.append(outcome)
        if not outcomes:
            return None
        best = self._best_reachable_attack_outcome(outcomes)
        return replace(best, reasons=best.reasons + ("attach_access_via_boss",))

    def evaluate_energy_switch_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != ENERGY_SWITCH:
            return ImmediateOutcome(supported=False, reasons=("unsupported_energy_switch_option",))
        equivalent_attach = self.b.energy_switch_has_equivalent_normal_attach_result()
        if not self.active_can_declare_attack_this_turn():
            return ImmediateOutcome(
                supported=False,
                additional_card_consumed=True,
                equivalent_normal_attach_available=equivalent_attach,
                reasons=("energy_switch_attack_not_declarable",),
            )
        active = self.b.active
        if active is None:
            return ImmediateOutcome(supported=False, additional_card_consumed=True, equivalent_normal_attach_available=equivalent_attach, reasons=("missing_energy_switch_state",))
        data = self.b.data(self.b.pid(active))
        if data is None:
            return ImmediateOutcome(supported=False, additional_card_consumed=True, equivalent_normal_attach_available=equivalent_attach, reasons=("missing_energy_switch_state",))
        before_tokens = tuple(self.b.energy_tokens(active))
        before_ids = self._energy_payable_attack_ids(data.attacks, before_tokens)
        outcomes: List[ImmediateOutcome] = []
        for source in self.b.all_my_pokemon:
            if source is active:
                continue
            for energy_id in self.b.energies(source):
                moved_tokens = energy_tokens_for_attach(energy_id, active)
                if moved_tokens is None:
                    continue
                after_tokens = before_tokens + tuple(moved_tokens)
                after_ids = self._energy_payable_attack_ids(data.attacks, after_tokens)
                enabled_ids = tuple(attack_id for attack_id in after_ids if attack_id not in before_ids)
                for attack_id in enabled_ids:
                    outcome = self._attack_outcome_with_tokens(active, attack_id, after_tokens, "energy_switch_reachable_attack")
                    if outcome.supported and not outcome.blocked:
                        outcomes.append(outcome)
        if not outcomes:
            return ImmediateOutcome(
                supported=True,
                additional_card_consumed=True,
                equivalent_normal_attach_available=equivalent_attach,
                reasons=("energy_switch_no_reachable_attack",),
            )
        best = self._best_reachable_attack_outcome(outcomes)
        reasons = ["energy_switch"]
        if best.knockout:
            reasons.append("energy_switch_reaches_knockout")
        if best.wins_game:
            reasons.append("energy_switch_reaches_win")
        return ImmediateOutcome(
            enables_attack=True,
            enabled_attack_ids=(best.reachable_attack_id,) if best.reachable_attack_id is not None else (),
            reachable_attack_id=best.reachable_attack_id,
            reachable_damage=best.damage,
            reachable_knockout=best.knockout,
            reachable_prizes_taken=best.prizes_taken,
            reachable_wins_game=best.wins_game,
            additional_card_consumed=True,
            equivalent_normal_attach_available=equivalent_attach,
            target_id=self.b.pid(active),
            target_serial=getattr(active, "serial", None),
            reasons=tuple(reasons),
        )

    def _has_retreat_access_option(self) -> bool:
        return any(option.type == OptionType.RETREAT for _, option in self.b.iter_options())

    def _has_surfing_beach_access_option(self, target: Pokemon) -> bool:
        active = self.b.active
        if active is None or not self._can_surfing_beach_switch(active, target):
            return False
        for _, option in self.b.iter_options():
            if option.type in {OptionType.PLAY, OptionType.ABILITY} and self.b.option_card(option) == SURFING_BEACH:
                return True
        return False

    def _can_declare_attack_after_same_turn_access(self) -> bool:
        state = getattr(self.b, "state", None)
        turn = getattr(state, "turn", None)
        first_player = getattr(state, "firstPlayer", None)
        your_index = getattr(state, "yourIndex", getattr(self.b, "my_index", None))
        if turn == 1 and first_player is not None and your_index is not None and int(first_player) == int(your_index):
            return False
        return True

    def _best_reachable_attack_outcome(self, outcomes: Sequence[ImmediateOutcome]) -> ImmediateOutcome:
        return max(
            outcomes,
            key=lambda outcome: (
                outcome.wins_game,
                outcome.knockout,
                outcome.prizes_taken,
                outcome.damage,
            ),
        )

    def _salvatore_evolve_option(self, evolution_id: int, target: Pokemon) -> Any:
        return SimpleNamespace(
            type=OptionType.EVOLVE,
            cardId=int(evolution_id),
            target=target,
            attackId=None,
            area=None,
            index=None,
            playerIndex=None,
            inPlayArea=AreaType.ACTIVE,
            inPlayIndex=0,
            toolIndex=None,
            energyIndex=None,
            serial=None,
            number=None,
        )

    def _salvatore_active_evolve_attack_facts(
        self,
        target: Optional[Pokemon] = None,
        require_unused_supporter: bool = True,
        evolution_id: Optional[int] = None,
    ) -> List[Tuple[Pokemon, int, ActiveEvolutionAttackFact]]:
        if require_unused_supporter and self.b.state.supporterPlayed:
            return []
        if not self.active_can_declare_attack_this_turn():
            return []
        candidates = [target] if target is not None else self.b.all_my_pokemon
        facts: List[Tuple[Pokemon, int, ActiveEvolutionAttackFact]] = []
        for pokemon in candidates:
            if pokemon is None or pokemon is not self.b.active:
                continue
            candidate_evolution_id = evolution_id or self.b.salvatore_deck_target_evolution(pokemon)
            if candidate_evolution_id is None:
                continue
            if not self.b.salvatore_can_evolve_from_deck_this_turn(pokemon, candidate_evolution_id):
                continue
            option = self._salvatore_evolve_option(candidate_evolution_id, pokemon)
            for fact in self.b.active_evolution_attack_facts(option):
                if fact.supported:
                    facts.append((pokemon, candidate_evolution_id, fact))
        return facts

    def _best_salvatore_active_evolve_attack_fact(
        self,
        target: Optional[Pokemon] = None,
        require_unused_supporter: bool = True,
        evolution_id: Optional[int] = None,
    ) -> Optional[Tuple[Pokemon, int, ActiveEvolutionAttackFact]]:
        facts = self._salvatore_active_evolve_attack_facts(target, require_unused_supporter, evolution_id)
        if not facts:
            return None
        return max(
            facts,
            key=lambda item: (
                not item[2].blocked,
                item[2].wins_game,
                item[2].knockout,
                item[2].prizes_taken,
                item[2].damage,
            ),
        )

    def _active_evolution_fact_to_reachable_outcome(self, target: Pokemon, fact: ActiveEvolutionAttackFact, reason: str) -> ImmediateOutcome:
        reasons = [reason]
        if fact.blocked:
            reasons.append("blocked_ex_wall")
        if fact.knockout:
            reasons.append("reachable_knockout")
        if fact.wins_game:
            reasons.append("reachable_win")
        return ImmediateOutcome(
            supported=fact.supported,
            blocked=fact.blocked,
            reachable_attack_id=fact.attack_id,
            reachable_damage=fact.damage,
            reachable_knockout=fact.knockout,
            reachable_prizes_taken=fact.prizes_taken,
            reachable_wins_game=fact.wins_game,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def evaluate_active_evolution(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.EVOLVE:
            return ImmediateOutcome(supported=False, reasons=("unsupported_active_evolution_option",))
        target = self.b.option_target(option)
        if target is None or target is not self.b.active:
            return ImmediateOutcome(supported=False, reasons=("active_evolution_not_active_target",))
        if not self.active_can_declare_attack_this_turn():
            return ImmediateOutcome(
                supported=False,
                target_id=self.b.pid(target),
                target_serial=getattr(target, "serial", None),
                reasons=("active_evolution_attack_not_declarable",),
            )
        facts = [fact for fact in self.b.active_evolution_attack_facts(option) if fact.supported]
        if not facts:
            return ImmediateOutcome(supported=False, target_id=self.b.pid(target), target_serial=getattr(target, "serial", None), reasons=("active_evolution_no_same_turn_attack_chain",))
        best = max(
            facts,
            key=lambda fact: (
                not fact.blocked,
                fact.wins_game,
                fact.knockout,
                fact.prizes_taken,
                fact.damage,
            ),
        )
        return self._active_evolution_fact_to_reachable_outcome(target, best, "active_evolution_reachable_attack")

    def _salvatore_fact_to_expected_outcome(
        self,
        target: Pokemon,
        fact: ActiveEvolutionAttackFact,
        reason: str,
        probability: float,
    ) -> ImmediateOutcome:
        reasons = [reason, "salvatore_evolution_deck_uncertain"]
        if fact.blocked:
            reasons.append("blocked_ex_wall")
        if fact.knockout:
            reasons.append("expected_reachable_knockout")
        if fact.wins_game:
            reasons.append("expected_reachable_win")
        return ImmediateOutcome(
            supported=fact.supported,
            blocked=fact.blocked,
            expected_reachable_attack_id=fact.attack_id,
            expected_reachable_damage=fact.damage * probability,
            expected_reachable_knockout=fact.knockout,
            expected_reachable_prizes_taken=fact.prizes_taken * probability,
            expected_reachable_wins_game=fact.wins_game,
            expected_hit_probability=probability,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def _best_salvatore_chain_outcome(self, outcomes: Sequence[ImmediateOutcome]) -> ImmediateOutcome:
        return max(
            outcomes,
            key=lambda outcome: (
                outcome.reachable_wins_game or outcome.expected_reachable_wins_game,
                outcome.reachable_knockout or outcome.expected_reachable_knockout,
                outcome.reachable_prizes_taken + outcome.expected_reachable_prizes_taken,
                outcome.reachable_damage + outcome.expected_reachable_damage,
            ),
        )

    def _best_salvatore_active_evolve_attack_outcome(
        self,
        target: Optional[Pokemon] = None,
        reason: str = "salvatore_active_evolve_attack",
        require_unused_supporter: bool = True,
        evolution_id: Optional[int] = None,
        confirmed_evolution_candidate: bool = False,
    ) -> Optional[ImmediateOutcome]:
        outcomes: List[ImmediateOutcome] = []
        for pokemon, candidate_evolution_id, fact in self._salvatore_active_evolve_attack_facts(
            target,
            require_unused_supporter,
            evolution_id,
        ):
            if fact.blocked:
                continue
            if confirmed_evolution_candidate or (self.b.deck_view and candidate_evolution_id in self.b.deck_ids):
                outcomes.append(self._active_evolution_fact_to_reachable_outcome(pokemon, fact, reason))
            else:
                probability = self.b.deck_presence_probability(candidate_evolution_id)
                if probability > 0:
                    outcomes.append(self._salvatore_fact_to_expected_outcome(pokemon, fact, reason, probability))
        return self._best_salvatore_chain_outcome(outcomes) if outcomes else None

    def evaluate_salvatore_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != SALVATORE:
            return ImmediateOutcome(supported=False, reasons=("unsupported_salvatore_play",))
        if self.b.state.supporterPlayed:
            return ImmediateOutcome(supported=True, reasons=("salvatore_supporter_already_used",))
        outcome = self._best_salvatore_active_evolve_attack_outcome(reason="salvatore_play_reachable_attack")
        development = self._best_salvatore_development_outcome()
        if outcome is None:
            if development is None:
                return ImmediateOutcome(supported=True, reasons=("salvatore_no_same_turn_attack_chain",))
            return replace(
                development,
                reasons=development.reasons + ("salvatore_no_same_turn_attack_chain",),
            )
        if development is None:
            return outcome
        direct_damage = self._best_unblocked_damage_from(self.b.active)
        reachable_damage = outcome.reachable_damage
        if reachable_damage <= 0 and outcome.expected_hit_probability > 0:
            reachable_damage = outcome.expected_reachable_damage / outcome.expected_hit_probability
        return replace(
            outcome,
            improves_damage=reachable_damage > direct_damage,
            equivalent_evolution_available=development.equivalent_evolution_available,
            completes_next_attacker=development.completes_next_attacker,
            development_value=development.development_value,
            development_probability=development.development_probability,
        )

    def _best_salvatore_development_outcome(self) -> Optional[ImmediateOutcome]:
        candidates: List[ImmediateOutcome] = []
        for target in self.b.all_my_pokemon:
            evolution_id = self.b.salvatore_deck_target_evolution(target)
            if evolution_id is None:
                continue
            data = self.b.data(evolution_id)
            if data is None:
                continue
            probability = self.b.deck_presence_probability(evolution_id)
            if probability <= 0:
                continue
            tokens = tuple(self.b.energy_tokens_as(target, evolution_id))
            best_damage = 0
            for attack_id in getattr(data, "attacks", ()):
                attack = self.b.attack(attack_id)
                if attack is None or not can_pay_attack_with_tokens(attack, tokens):
                    continue
                if self.b.attack_blocked_by_ex_wall_for_card(evolution_id, self.b.opp_active, attack):
                    continue
                best_damage = max(best_damage, self.b.attack_damage_for_card(evolution_id, attack))
            equivalent = any(
                option.type == OptionType.EVOLVE
                and self.b.option_card(option) == evolution_id
                and self.b.option_target(option) is target
                for _, option in self.b.iter_options()
            )
            opp_damage = self.b.opp_max_damage()
            evolution_hp = safe_int(getattr(data, "hp", 0))
            avoids_board_out = (
                target is self.b.active
                and len(self.b.all_my_pokemon) == 1
                and opp_damage > 0
                and hp_left(target) <= opp_damage
                and evolution_hp - damage_on(target) > opp_damage
            )
            candidates.append(
                ImmediateOutcome(
                    supported=True,
                    avoids_board_out=avoids_board_out,
                    equivalent_evolution_available=equivalent,
                    completes_next_attacker=best_damage > 0,
                    development_value=best_damage * probability,
                    development_probability=probability,
                    target_id=self.b.pid(target),
                    target_serial=getattr(target, "serial", None),
                    reasons=("salvatore_development_fact",),
                )
            )
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda fact: (
                fact.avoids_board_out,
                fact.completes_next_attacker,
                not fact.equivalent_evolution_available,
                fact.development_value,
            ),
        )

    def _wally_target_outcome(self, target: Optional[Pokemon]) -> ImmediateOutcome:
        if target is None or target not in self.b.all_my_pokemon:
            return ImmediateOutcome(supported=False, reasons=("wally_missing_target",))
        if self.b.pid(target) not in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return ImmediateOutcome(supported=False, reasons=("wally_invalid_target",))
        healed_damage = damage_on(target)
        if healed_damage <= 0:
            return ImmediateOutcome(supported=False, target_id=self.b.pid(target), target_serial=getattr(target, "serial", None), reasons=("wally_no_damage",))
        energy_count = self.b.energy_count(target)
        opp_damage = self.b.opp_max_damage()
        avoids_next_knockout = (
            target is self.b.active
            and opp_damage > 0
            and hp_left(target) <= opp_damage
            and safe_int(getattr(target, "maxHp", 0)) > opp_damage
        )
        avoids_board_out = avoids_next_knockout and len(self.b.all_my_pokemon) == 1
        reasons = ["wally_heals_damage"]
        if energy_count > 0:
            reasons.append("wally_recovers_energy")
        if avoids_next_knockout:
            reasons.extend(("wally_avoids_next_knockout", "wally_avoids_prize_loss"))
        if avoids_board_out:
            reasons.append("wally_avoids_board_out")
        return ImmediateOutcome(
            supported=True,
            healed_damage=healed_damage,
            recovered_energy_count=energy_count,
            board_energy_removed=energy_count,
            next_knockout_avoided=avoids_next_knockout,
            avoids_prize_loss=avoids_next_knockout,
            prizes_preserved=self.b.prize_value(target) if avoids_next_knockout else 0,
            avoids_board_out=avoids_board_out,
            preserves_primary_pokemon=target is self.b.active,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=tuple(reasons),
        )

    def evaluate_wally_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != WALLY_COMPASSION:
            return ImmediateOutcome(supported=False, reasons=("unsupported_wally_play",))
        if self.b.state.supporterPlayed:
            return ImmediateOutcome(supported=False, reasons=("wally_supporter_already_used",))
        outcomes = [
            self._wally_target_outcome(target)
            for target in self.b.all_my_pokemon
        ]
        outcomes = [outcome for outcome in outcomes if outcome.supported]
        if not outcomes:
            return ImmediateOutcome(supported=False, reasons=("wally_no_effective_target",))
        best = max(outcomes, key=wally_effect_fact_key)
        return replace(
            best,
            recommended_target_id=best.target_id,
            recommended_target_serial=best.target_serial,
            reasons=("wally_play",) + best.reasons,
        )

    def evaluate_wally_target(self, target: Optional[Pokemon]) -> ImmediateOutcome:
        outcome = self._wally_target_outcome(target)
        if not outcome.supported:
            return outcome
        return replace(outcome, reasons=("wally_target",) + outcome.reasons)

    def evaluate_salvatore_target(self, target: Optional[Pokemon]) -> ImmediateOutcome:
        if target is None:
            return ImmediateOutcome(supported=False, reasons=("missing_salvatore_target",))
        outcome = self._best_salvatore_active_evolve_attack_outcome(
            target,
            "salvatore_target_reachable_attack",
            require_unused_supporter=False,
        )
        if outcome is None:
            return ImmediateOutcome(supported=True, target_id=self.b.pid(target), target_serial=getattr(target, "serial", None), reasons=("salvatore_target_no_same_turn_attack_chain",))
        return outcome

    def evaluate_salvatore_evolution_candidate(self, option: Any) -> ImmediateOutcome:
        evolution_id = self.b.option_card(option)
        if evolution_id not in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return ImmediateOutcome(supported=False, reasons=("unsupported_salvatore_evolution_candidate",))
        outcome = self._best_salvatore_active_evolve_attack_outcome(
            reason="salvatore_evolution_candidate_reachable_attack",
            require_unused_supporter=False,
            evolution_id=evolution_id,
            confirmed_evolution_candidate=True,
        )
        if outcome is None:
            return ImmediateOutcome(supported=True, target_id=evolution_id, reasons=("salvatore_evolution_candidate_no_same_turn_attack_chain",))
        return outcome

    def evaluate_pokegear_candidate(self, option: Any) -> ImmediateOutcome:
        cid = self.b.option_card(option)
        if cid != SALVATORE:
            return ImmediateOutcome(supported=False, reasons=("pokegear_candidate_no_same_turn_chain",))
        if self.b.state.supporterPlayed:
            return ImmediateOutcome(supported=True, reasons=("pokegear_salvatore_candidate_supporter_already_used",))
        outcome = self._best_salvatore_active_evolve_attack_outcome(
            reason="pokegear_salvatore_candidate_reachable_attack",
        )
        if outcome is None:
            return ImmediateOutcome(supported=True, reasons=("pokegear_salvatore_candidate_no_same_turn_attack_chain",))
        return outcome

    def evaluate_pokegear_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != POKEGEAR:
            return ImmediateOutcome(supported=False, reasons=("unsupported_pokegear_play",))
        if self.b.state.supporterPlayed or not self.b.remaining_possible(SALVATORE):
            return ImmediateOutcome(supported=True, reasons=("pokegear_no_same_turn_salvatore_chain",))
        chain = self._best_salvatore_active_evolve_attack_fact(require_unused_supporter=True)
        probability = self.b.pokegear_hit_probability(SALVATORE)
        if chain is not None:
            _target, evolution_id, _fact = chain
            if _fact.blocked:
                return ImmediateOutcome(supported=True, expected_hit_probability=probability, reasons=("pokegear_no_same_turn_salvatore_chain",))
            probability = self.b.pokegear_chain_hit_probability(SALVATORE, evolution_id)
        if chain is None or probability <= 0:
            return ImmediateOutcome(supported=True, expected_hit_probability=probability, reasons=("pokegear_no_same_turn_salvatore_chain",))
        target, _evolution_id, fact = chain
        return ImmediateOutcome(
            supported=True,
            expected_reachable_attack_id=fact.attack_id,
            expected_reachable_damage=fact.damage * probability,
            expected_reachable_knockout=fact.knockout,
            expected_reachable_prizes_taken=fact.prizes_taken * probability,
            expected_reachable_wins_game=fact.wins_game,
            expected_hit_probability=probability,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=("pokegear_expected_salvatore_chain",),
        )

    def active_status_blocks_attack(self) -> bool:
        return active_status_blocks_attack_for_board(self.b)

    def active_can_declare_attack_this_turn(self) -> bool:
        return active_can_declare_attack_this_turn_for_board(self.b)

    def _attack_outcome_with_tokens(
        self,
        attacker: Pokemon,
        attack_id: int,
        tokens: Sequence[Any],
        reason: str,
    ) -> ImmediateOutcome:
        return self._attack_outcome_with_tokens_against(attacker, attack_id, tokens, self.b.opp_active, reason)

    def _attack_outcome_with_tokens_against(
        self,
        attacker: Pokemon,
        attack_id: int,
        tokens: Sequence[Any],
        target: Optional[Pokemon],
        reason: str,
    ) -> ImmediateOutcome:
        attack = self.b.attack(attack_id)
        if attack is None or target is None:
            return ImmediateOutcome(supported=False, reachable_attack_id=int(attack_id), reasons=("missing_reachable_attack_state",))
        if not can_pay_attack_with_tokens(attack, tokens):
            return ImmediateOutcome(supported=False, reachable_attack_id=int(attack_id), reasons=("reachable_attack_not_payable",))
        blocked = self._blocked_by_ex_wall(attacker, target, attack)
        damage = 0 if blocked else self.b.attack_damage(attacker, attack)
        knockout = damage >= hp_left(target)
        prizes_taken = self.b.prize_value(target) if knockout else 0
        wins_game = prizes_taken >= self.b.my_prizes_left() if knockout else False
        reasons = [reason]
        if blocked:
            reasons.append("blocked_ex_wall")
        if knockout:
            reasons.append("reachable_knockout")
        if wins_game:
            reasons.append("reachable_win")
        return ImmediateOutcome(
            blocked=blocked,
            damage=damage,
            knockout=knockout,
            prizes_taken=prizes_taken,
            wins_game=wins_game,
            reachable_attack_id=int(attack_id),
            reasons=tuple(reasons),
        )

    def evaluate_boss_target(self, target: Optional[Pokemon]) -> ImmediateOutcome:
        attacker = self.b.active
        if attacker is None or target is None or target not in self.b.opp_bench:
            return ImmediateOutcome(supported=False, reasons=("missing_boss_state",))
        data = self.b.data(self.b.pid(attacker))
        if data is None:
            return ImmediateOutcome(supported=False, reasons=("missing_boss_state",))
        if not self.active_can_declare_attack_this_turn():
            return self._boss_no_effective_attack(target)

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

    def evaluate_boss_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != BEFEHL_VON_BOSS:
            return ImmediateOutcome(supported=False, reasons=("unsupported_boss_play",))
        if not any(candidate is option for _, candidate in self.b.iter_options()):
            return ImmediateOutcome(supported=True, reasons=("boss_play_option_not_legal",))
        if self.b.state.supporterPlayed:
            return ImmediateOutcome(supported=True, reasons=("boss_play_supporter_already_used",))
        if self.b.active is None or not self.b.opp_bench:
            return ImmediateOutcome(supported=True, reasons=("boss_play_missing_state",))
        if not self.active_can_declare_attack_this_turn():
            return ImmediateOutcome(supported=False, reasons=("boss_play_attack_not_declarable",))

        candidates = []
        for target in self.b.opp_bench:
            outcome = self.evaluate_boss_target(target)
            if outcome.supported and not outcome.blocked and (outcome.wins_game or (outcome.knockout and outcome.prizes_taken > 0)):
                candidates.append(outcome)
        if not candidates:
            return ImmediateOutcome(supported=True, reasons=("boss_play_no_reachable_prize_attack",))

        best = max(
            candidates,
            key=lambda outcome: (
                outcome.wins_game,
                outcome.knockout,
                outcome.prizes_taken,
                outcome.damage,
            ),
        )
        reasons = ["boss_play_reachable_attack"]
        if best.wins_game:
            reasons.append("boss_play_reachable_win")
        if best.knockout:
            reasons.append("boss_play_reachable_knockout")
        if best.prizes_taken:
            reasons.append("boss_play_takes_prizes")
        return ImmediateOutcome(
            supported=True,
            reachable_damage=best.damage,
            reachable_knockout=best.knockout,
            reachable_prizes_taken=best.prizes_taken,
            reachable_wins_game=best.wins_game,
            target_id=best.target_id,
            target_serial=best.target_serial,
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
        if not self.active_can_declare_attack_this_turn():
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
            reachable_attack_id=best_target.reachable_attack_id if best_target is not None else None,
            reachable_damage=best_target.reachable_damage if best_target is not None else 0,
            reachable_knockout=bool(best_target and best_target.reachable_knockout),
            reachable_prizes_taken=best_target.reachable_prizes_taken if best_target is not None else 0,
            reachable_wins_game=bool(best_target and best_target.reachable_wins_game),
            retreat_energy_cost=cost,
            important_energy_loss=important_loss,
            improves_damage=bool(best_target and best_target.improves_damage),
            recommended_target_id=best_target.target_id if best_target is not None else None,
            recommended_target_serial=best_target.target_serial if best_target is not None else None,
            reasons=tuple(reasons),
        )

    def evaluate_switch_target(self, target: Optional[Pokemon], source: str) -> ImmediateOutcome:
        if source not in {"retreat", "surfing_beach", "suguri"}:
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

        active_damage = 0 if source == "suguri" and self.active_status_blocks_attack() else self._best_unblocked_damage_from(active)
        target_attack_outcome = None
        if source != "retreat" or not self.active_status_blocks_attack():
            target_attack_outcome = self._best_switch_target_attack_outcome(target)
        target_damage = target_attack_outcome.damage if target_attack_outcome is not None else 0
        target_id = self.b.pid(target)
        cost = 0 if source in {"surfing_beach", "suguri"} else self._effective_retreat_cost(active)
        important_loss = 0 if source in {"surfing_beach", "suguri"} else self._possible_important_energy_loss(active, cost)
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
        elif source == "suguri":
            reasons.append("suguri_switch")
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
            reachable_attack_id=target_attack_outcome.reachable_attack_id if target_attack_outcome is not None else None,
            reachable_damage=target_attack_outcome.damage if target_attack_outcome is not None else 0,
            reachable_knockout=bool(target_attack_outcome and target_attack_outcome.knockout),
            reachable_prizes_taken=target_attack_outcome.prizes_taken if target_attack_outcome is not None else 0,
            reachable_wins_game=bool(target_attack_outcome and target_attack_outcome.wins_game),
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

    def _best_switch_target_attack_outcome(self, target: Pokemon) -> Optional[ImmediateOutcome]:
        if not self._can_declare_attack_after_same_turn_access():
            return None
        data = self.b.data(self.b.pid(target))
        if data is None:
            return None
        outcomes = [
            self._attack_outcome_with_tokens(target, attack_id, self.b.energy_tokens(target), "switch_reachable_attack")
            for attack_id in data.attacks
        ]
        effective_outcomes = [outcome for outcome in outcomes if outcome.supported and not outcome.blocked]
        if not effective_outcomes:
            return None
        return self._best_reachable_attack_outcome(effective_outcomes)

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
            if self.effect_id() == SALVATORE and self.b.option_target(option) is not None:
                return self.score_target_or_card(option)
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
        cid = self.b.option_card(option)
        if (
            option.type == OptionType.PLAY
            and cid == TANKER
        ) or (
            self.effect_id() == TANKER
            and cid is not None
        ):
            candidate = self.night_stretcher_candidate_for_option(option)
            if candidate is None:
                return ActionScore(TIER_BLOCKED_OR_BAD_ACTION)
            development = self.night_stretcher_development_value(candidate)
            if candidate.returns_to_hand_only:
                return ActionScore(
                    TIER_BLOCKED_OR_BAD_ACTION,
                    resource=1,
                    legacy=self.night_stretcher_identity_tiebreak(candidate),
                )
            if self.night_stretcher_is_deferred_until_evolution(candidate):
                return ActionScore(
                    TIER_LOW_VALUE_ACTION,
                    resource=1,
                    legacy=self.night_stretcher_identity_tiebreak(candidate),
                )
            return ActionScore(
                TIER_HIGH_VALUE_PREP if self.night_stretcher_is_concrete_same_turn(candidate) else TIER_LOW_VALUE_ACTION,
                development=development,
                legacy=self.night_stretcher_identity_tiebreak(candidate),
            )
        is_wally_action = (
            option.type == OptionType.PLAY and cid == WALLY_COMPASSION
        ) or (
            self.effect_id() == WALLY_COMPASSION
            and self.b.option_target(option) is not None
        )
        if is_wally_action and outcome.supported:
            if self.wally_preservation_is_high_value(outcome):
                return ActionScore(
                    TIER_HIGH_VALUE_PREP,
                    immediate=outcome.prizes_preserved,
                    pressure=int(outcome.avoids_board_out),
                    development=outcome.healed_damage,
                    resource=outcome.recovered_energy_count,
                    risk=outcome.board_energy_removed,
                    legacy=legacy_score,
                )
            return ActionScore(
                TIER_LOW_VALUE_ACTION,
                legacy=legacy_score,
            )
        if option.type == OptionType.PLAY and cid == SALVATORE and not (
            outcome.reachable_attack_id is not None
            or outcome.expected_reachable_attack_id is not None
            or outcome.avoids_board_out
        ):
            return ActionScore(
                TIER_LOW_VALUE_ACTION,
                development=0 if outcome.equivalent_evolution_available else outcome.development_value,
                resource=0,
                legacy=legacy_score,
            )
        handoff_pressure_score = self.cinderace_handoff_pressure_score(outcome, legacy_score)
        if handoff_pressure_score is not None:
            return handoff_pressure_score
        if outcome.supported and outcome.wins_game:
            return ActionScore(TIER_WIN, immediate=outcome.prizes_taken, legacy=legacy_score)
        if outcome.supported and outcome.knockout:
            return ActionScore(TIER_KO, immediate=outcome.prizes_taken, pressure=outcome.damage, legacy=legacy_score)
        if outcome.supported and outcome.reachable_wins_game:
            return ActionScore(
                TIER_PRESERVE_WIN_OR_KO_PREP,
                immediate=outcome.reachable_prizes_taken,
                pressure=outcome.reachable_damage,
                resource=max(0, min(legacy_score, 200000)),
                risk=outcome.retreat_energy_cost * 18000 + outcome.important_energy_loss * 70000,
                legacy=legacy_score,
            )
        if outcome.supported and outcome.reachable_knockout:
            return ActionScore(
                TIER_PRESERVE_WIN_OR_KO_PREP,
                immediate=outcome.reachable_prizes_taken,
                pressure=outcome.reachable_damage,
                resource=max(0, min(legacy_score, 200000)),
                risk=outcome.retreat_energy_cost * 18000 + outcome.important_energy_loss * 70000,
                legacy=legacy_score,
            )
        if (
            option.type == OptionType.PLAY
            and cid == SALVATORE
            and outcome.supported
            and (
                outcome.avoids_board_out
                or (
                    outcome.reachable_attack_id is not None
                    and outcome.improves_damage
                )
            )
        ):
            return ActionScore(
                TIER_HIGH_VALUE_PREP,
                pressure=outcome.reachable_damage,
                development=outcome.development_value,
                legacy=legacy_score,
            )
        if (
            outcome.supported
            and outcome.expected_reachable_attack_id is not None
            and (
                outcome.expected_reachable_wins_game
                or outcome.expected_reachable_knockout
                or (
                    option.type == OptionType.PLAY
                    and cid == SALVATORE
                    and outcome.improves_damage
                )
            )
            and self.expected_search_chain_is_high_value(outcome)
        ):
            return ActionScore(
                TIER_HIGH_VALUE_PREP,
                immediate=outcome.expected_reachable_prizes_taken,
                pressure=outcome.expected_reachable_damage,
                resource=max(0, min(legacy_score, 200000)),
                legacy=legacy_score,
            )
        attach_pressure_score = self.active_attach_reachable_pressure_score(option, legacy_score, outcome)
        if attach_pressure_score is not None:
            return attach_pressure_score
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

    def night_stretcher_candidate_key(self, facts: NightStretcherCandidateFacts) -> Tuple[Any, ...]:
        return (
            not facts.returns_to_hand_only,
            facts.same_turn_attack_enabled,
            facts.same_turn_retreat_enabled,
            facts.board_out_avoided,
            facts.next_attacker_completed,
            facts.same_turn_attack_gap_reduced,
            facts.next_attacker_gap_reduced and facts.same_turn_attach_available,
            facts.same_turn_usable,
            facts.next_attacker_gap_reduced,
            facts.next_turn_evolution_supported,
            -(facts.target_serial if facts.target_serial is not None else 10**9),
        )

    def recommended_night_stretcher_candidate(self) -> Optional[NightStretcherCandidateFacts]:
        facts = self.b.night_stretcher_recovery_facts()
        if not facts:
            return None
        return max(facts, key=self.night_stretcher_candidate_key)

    def night_stretcher_candidate_for_option(self, option: Any) -> Optional[NightStretcherCandidateFacts]:
        if option.type == OptionType.PLAY and self.b.option_card(option) == TANKER:
            return self.recommended_night_stretcher_candidate()
        if self.effect_id() != TANKER:
            return None
        cid = self.b.option_card(option)
        source_cards = self.b.cards_in_area(option.area, option.playerIndex)
        card = None
        if source_cards is not None and option.index is not None and 0 <= option.index < len(source_cards):
            card = source_cards[option.index]
        serial = getattr(card, "serial", getattr(option, "serial", None))
        if cid is None:
            return None
        return self.b.night_stretcher_candidate_facts(
            card if card is not None else SimpleNamespace(id=cid, serial=serial)
        )

    def night_stretcher_development_value(self, facts: NightStretcherCandidateFacts) -> int:
        if facts.returns_to_hand_only:
            return 0
        if facts.same_turn_attack_enabled or facts.same_turn_retreat_enabled:
            return 7
        if facts.board_out_avoided:
            return 6
        if facts.next_attacker_completed:
            return 5
        if facts.same_turn_attack_gap_reduced:
            return 4
        if facts.next_attacker_gap_reduced and facts.same_turn_attach_available:
            return 3
        if facts.next_turn_evolution_supported and facts.same_turn_usable:
            return 2
        if facts.same_turn_usable:
            return 1
        if facts.next_attacker_gap_reduced or facts.next_turn_evolution_supported:
            return 1
        return 0

    def night_stretcher_identity_tiebreak(self, facts: NightStretcherCandidateFacts) -> int:
        return -(facts.target_serial if facts.target_serial is not None else 10**9)

    def night_stretcher_is_concrete_same_turn(self, facts: NightStretcherCandidateFacts) -> bool:
        return any(
            (
                facts.same_turn_attack_gap_reduced,
                facts.same_turn_attack_enabled,
                facts.same_turn_retreat_enabled,
                facts.next_attacker_completed and facts.same_turn_attach_available,
                facts.board_out_avoided,
            )
        )

    def night_stretcher_is_deferred_until_evolution(
        self,
        facts: NightStretcherCandidateFacts,
    ) -> bool:
        if not (
            facts.same_turn_attack_enabled
            or facts.same_turn_attack_gap_reduced
        ):
            return False
        active_data = self.b.data(self.b.pid(self.b.active))
        if active_data is None or not getattr(active_data, "basic", False):
            return False
        return any(
            option.type == OptionType.EVOLVE
            for _, option in self.b.iter_options()
        )

    def night_stretcher_policy_value(self, facts: Optional[NightStretcherCandidateFacts]) -> float:
        if facts is None:
            return -8000
        if facts.returns_to_hand_only:
            return -1000
        if facts.same_turn_attack_enabled:
            return 90000
        if facts.same_turn_retreat_enabled:
            return 88000
        if facts.board_out_avoided:
            return 84000
        if facts.next_attacker_completed:
            return 82000
        if facts.same_turn_attack_gap_reduced:
            return 74000
        if facts.next_attacker_gap_reduced and facts.same_turn_attach_available:
            return 70000
        if facts.same_turn_usable:
            return 52000
        if facts.next_attacker_gap_reduced:
            return 32000
        if facts.next_turn_evolution_supported:
            return 26000
        return -1000

    def wally_preservation_is_high_value(self, outcome: ImmediateOutcome) -> bool:
        return wally_preservation_fact_is_high_value(outcome)

    def best_current_attack_outcome(self) -> Optional[ImmediateOutcome]:
        outcomes: List[ImmediateOutcome] = []
        for _, candidate in self.b.iter_options():
            if candidate.type != OptionType.ATTACK and candidate.attackId is None:
                continue
            outcome = self.outcome.evaluate_attack(candidate)
            if outcome.supported and not outcome.blocked:
                outcomes.append(outcome)
        if not outcomes:
            return None
        return max(outcomes, key=lambda outcome: (outcome.wins_game, outcome.knockout, outcome.prizes_taken, outcome.damage))

    def cinderace_handoff_improves_current_turn(self, outcome: ImmediateOutcome) -> bool:
        if not (
            self.b.pid(self.b.active) == CINDERACE
            and self.b.cinderace_can_accelerate()
            and self.b.has_bench_energy_receiver()
            and "role_handoff" in outcome.reasons
        ):
            return False
        current = self.best_current_attack_outcome()
        if current is not None and current.wins_game:
            return False
        if outcome.reachable_wins_game:
            return True
        current_prizes = current.prizes_taken if current is not None else 0
        if outcome.reachable_prizes_taken > current_prizes:
            return True
        current_knockout = bool(current and current.knockout)
        if outcome.reachable_knockout and not current_knockout:
            return True
        return bool(
            not current_knockout
            and not outcome.reachable_knockout
            and outcome.reachable_attack_id is not None
            and outcome.improves_damage
        )

    def cinderace_handoff_pressure_score(
        self,
        outcome: ImmediateOutcome,
        legacy_score: float,
    ) -> Optional[ActionScore]:
        if not self.cinderace_handoff_improves_current_turn(outcome):
            return None
        risk = outcome.retreat_energy_cost * 18000 + outcome.important_energy_loss * 70000
        if outcome.reachable_wins_game:
            return ActionScore(
                TIER_WIN,
                immediate=outcome.reachable_prizes_taken,
                pressure=outcome.reachable_damage,
                risk=risk,
                legacy=legacy_score,
            )
        if outcome.reachable_knockout:
            return ActionScore(
                TIER_KO,
                immediate=outcome.reachable_prizes_taken,
                pressure=outcome.reachable_damage,
                risk=risk,
                legacy=legacy_score,
            )
        return ActionScore(
            TIER_NON_KO_ATTACK,
            pressure=self.reachable_attack_pressure_value(outcome),
            resource=max(0, min(legacy_score, 200000)),
            risk=risk,
            legacy=legacy_score,
        )

    def expected_search_chain_is_high_value(self, outcome: ImmediateOutcome) -> bool:
        if outcome.expected_hit_probability < 0.25:
            return False
        direct = self.best_current_attack_outcome()
        if direct is not None and (direct.wins_game or direct.knockout):
            return False
        direct_damage = direct.damage if direct is not None else 0
        direct_threshold = direct_damage
        if direct is not None and self.b.opp_active is not None and direct.damage * 2 >= hp_left(self.b.opp_active):
            direct_threshold += 80
        if direct_damage >= 200 and outcome.expected_reachable_prizes_taken < 1.0:
            return False
        expected_value = outcome.expected_reachable_damage + outcome.expected_reachable_prizes_taken * 120
        return expected_value > max(30, direct_threshold)

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
        return self.attack_pressure_value_for_attack(attack, outcome, self.can_continue_same_attack(attack))

    def attack_pressure_value_for_attack(
        self,
        attack: Any,
        outcome: ImmediateOutcome,
        can_continue_attack: bool,
    ) -> float:
        target = self.b.opp_active
        if attack is None or target is None or outcome.damage <= 0:
            return 0
        active_hp = max(1, hp_left(target))
        active_pressure = outcome.damage * 1000
        active_pressure += (outcome.damage / active_hp) * 45000
        if active_hp - outcome.damage <= 100:
            active_pressure += 18000
        if can_continue_attack and outcome.damage * 2 >= active_hp:
            active_pressure += (25000 + self.b.prize_value(target) * 8000) * NEXT_TURN_PRESSURE_DISCOUNT
        bench_pressure = self.bench_attack_pressure_value(attack, can_continue_attack)
        return active_pressure + bench_pressure

    def can_continue_same_attack(self, attack: Any) -> bool:
        active = self.b.active
        return active is not None and self.b.can_pay_attack(active, attack)

    def attack_bench_damage_amount(self, attack: Any) -> int:
        return attack_bench_damage_amount(attack)

    def bench_attack_pressure_value(self, attack: Any, can_continue_attack: Optional[bool] = None) -> float:
        bench_damage = self.attack_bench_damage_amount(attack)
        if bench_damage <= 0:
            return 0
        if can_continue_attack is None:
            can_continue_attack = self.can_continue_same_attack(attack)
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
            if can_continue_attack and bench_damage * 2 >= target_hp:
                value += (50000 + self.b.prize_value(target) * 12000) * NEXT_TURN_PRESSURE_DISCOUNT
            if important:
                value += 12000
            best = max(best, value)
        return best

    def active_attach_reachable_pressure_score(
        self,
        option: Any,
        legacy_score: float,
        outcome: ImmediateOutcome,
    ) -> Optional[ActionScore]:
        if option.type != OptionType.ATTACH or self.b.option_target(option) is not self.b.active:
            return None
        if not outcome.supported or outcome.reachable_attack_id is None:
            return None
        if outcome.reachable_attack_id not in outcome.enabled_attack_ids:
            return None
        if outcome.reachable_wins_game or outcome.reachable_knockout or outcome.reachable_prizes_taken > 0:
            return None
        reachable_pressure = self.reachable_attack_pressure_value(outcome)
        current_pressure = self.best_current_non_ko_attack_pressure()
        if current_pressure is None or reachable_pressure <= current_pressure:
            return None
        return ActionScore(
            TIER_NON_KO_ATTACK,
            pressure=reachable_pressure,
            resource=max(0, min(legacy_score, 200000)),
            legacy=legacy_score,
        )

    def reachable_attack_pressure_value(self, outcome: ImmediateOutcome) -> float:
        attack = self.b.attack(outcome.reachable_attack_id)
        if attack is None:
            return 0
        pressure_outcome = ImmediateOutcome(
            supported=outcome.supported,
            blocked=outcome.blocked,
            damage=outcome.reachable_damage,
            knockout=outcome.reachable_knockout,
            prizes_taken=outcome.reachable_prizes_taken,
            wins_game=outcome.reachable_wins_game,
            target_id=outcome.target_id,
            target_serial=outcome.target_serial,
            reasons=outcome.reasons,
        )
        return self.attack_pressure_value_for_attack(
            attack,
            pressure_outcome,
            outcome.reachable_can_continue_attack,
        )

    def best_current_non_ko_attack_pressure(self) -> Optional[float]:
        best: Optional[float] = None
        for _, option in self.b.iter_options():
            attack_id = getattr(option, "attackId", None)
            if getattr(option, "type", None) != OptionType.ATTACK or attack_id is None:
                continue
            outcome = self.outcome.evaluate_attack(option)
            if not outcome.supported or outcome.blocked or outcome.knockout or outcome.wins_game:
                return None
            value = self.attack_pressure_value(option, outcome)
            best = value if best is None else max(best, value)
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
            if cid in {BEFEHL_VON_BOSS, SURFING_BEACH, WALLY_COMPASSION, SALVATORE}:
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
        if (
            self.b.pid(self.b.active) == CINDERACE
            and self.b.cinderace_can_accelerate()
            and self.b.has_bench_energy_receiver()
            and not self.cinderace_handoff_improves_current_turn(outcome)
        ):
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
        if cid == JUDGE:
            direct = self.best_current_attack_outcome()
            if direct is not None and (direct.wins_game or direct.knockout):
                return 6000
            if safe_int(getattr(self.b.opp, "handCount", 0)) >= 8:
                return 90000
            if self.b.opponent_profile() == "ALAKAZAM":
                return 76000
            return 6000
        if cid == SUGURI:
            active_data = self.b.data(self.b.pid(self.b.active))
            opp_data = self.b.data(self.b.pid(self.b.opp_active))
            if active_data is None or active_data.basic:
                return 6000
            direct = self.best_current_attack_outcome()
            if direct is not None and (direct.wins_game or direct.knockout):
                return 6000
            if direct is not None and opp_data is not None and (opp_data.ex or opp_data.megaEx):
                boosted_damage = direct.damage + 30
                boosted_knockout = self.b.opp_active is not None and boosted_damage >= hp_left(self.b.opp_active)
                boosted_prizes = self.b.prize_value(self.b.opp_active) if boosted_knockout else 0
                if boosted_knockout and (boosted_prizes > direct.prizes_taken or boosted_prizes >= self.b.my_prizes_left()):
                    return 94000
            for target in self.b.bench:
                outcome = self.outcome.evaluate_switch_target(target, "suguri")
                if outcome.supported and (outcome.reachable_wins_game or outcome.enables_knockout or outcome.improves_damage or (self.outcome.active_status_blocks_attack() and outcome.enables_attack)):
                    return 88000
            return 6000
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
            return self.night_stretcher_policy_value(
                self.recommended_night_stretcher_candidate()
            )
        if cid == WALLY_COMPASSION:
            outcome = self.outcome.evaluate_wally_play(option)
            if outcome.supported and (
                self.b.wally_live()
                or self.wally_preservation_is_high_value(outcome)
            ):
                return self.wally_effect_legacy_value(outcome)
            return -16000
        if cid == BEFEHL_VON_BOSS:
            return self.score_boss()
        if cid == SURFING_BEACH:
            return self.score_surfing_beach_play(option)
        if cid == HERO_CAPE:
            return max(
                (self.score_hero_cape_target(target) for target in self.b.all_my_pokemon),
                default=SCORE_FORBIDDEN,
            )
        if cid == TOOL_SCRAPPER:
            return self.score_tool_scrapper_outcome(self.outcome.evaluate_tool_scrapper_play(option))
        if cid == ENERGY_SWITCH:
            outcome = self.outcome.evaluate_energy_switch_play(option)
            if (
                outcome.additional_card_consumed
                and not outcome.reachable_wins_game
                and not outcome.reachable_knockout
                and outcome.reachable_attack_id is None
            ):
                return -1000 if outcome.equivalent_normal_attach_available else 3000
            return 36000 if self.b.starmie_needs_energy() else 3000
        if self.b.is_pokemon(cid):
            return self.score_pokemon_play(cid)
        if cid in self.b.plan_setup_cards():
            return 15000
        return 0

    def score_hero_cape_target(self, target: Optional[Pokemon]) -> float:
        roi = self.b.hero_cape_target_roi(target)
        if roi == "invalid":
            return SCORE_FORBIDDEN
        if roi == "prevents_active_knockout":
            return 90000 + self.b.prize_value(target) * 20000 + self.b.energy_count(target) * 10000
        if roi == "extends_active_survival":
            return 28000 + self.b.prize_value(target) * 4000 + min(2, self.b.energy_count(target)) * 3000
        if roi == "invested_without_clear_survival":
            return -4000
        return -12000

    def best_surfing_beach_play_outcome(self, option: Any) -> Optional[ImmediateOutcome]:
        outcome = self.outcome.evaluate_surfing_beach_ability(
            option,
            after_stadium_play=True,
        )
        if not outcome.supported:
            return None
        return outcome

    def score_surfing_beach_play(self, option: Any) -> float:
        stadium = getattr(getattr(self.b, "state", None), "stadium", None) or ()
        current = stadium[0] if stadium else None
        if current is not None and card_id(current) == SURFING_BEACH:
            return -12000

        outcome = self.best_surfing_beach_play_outcome(option)
        scores = []
        immediate_switch_value = bool(
            outcome
            and (
                "retreat_enables_attack" in outcome.reasons
                or "retreat_improves_damage" in outcome.reasons
                or (
                    self.b.public_lethal_next_turn()
                    and "survival_retreat" in outcome.reasons
                )
            )
        )
        if immediate_switch_value:
            if outcome is not None and outcome.reachable_wins_game:
                scores.append(52000)
            elif outcome is not None and outcome.reachable_knockout:
                scores.append(48000)
            else:
                scores.append(36000)

        if current is not None:
            owner = getattr(current, "playerIndex", None)
            my_index = getattr(self.b, "my_index", getattr(self.b.state, "yourIndex", None))
            if owner is not None and my_index is not None and int(owner) != int(my_index):
                scores.append(42000)

        return max(scores, default=-12000)

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
            return self.score_hero_cape_target(target)
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
        return self.outcome.active_status_blocks_attack()

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
            usable_facts = tuple(
                fact
                for fact in self.b.active_evolution_attack_facts(option)
                if fact.supported and not fact.blocked
            )
            if not usable_facts:
                return score
            hp_gain_score = min(160000, max(0, evo_hp - before_hp) * 600)
            score += hp_gain_score
            score += 220000
            score += 140000
            score += energy_count * 60000
            score += 260000
            if any(fact.attack_id in {NEBULA_BEAM, ABSOLUTE_SNOW} for fact in usable_facts):
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
        if context == SelectContext.FIRST_EFFECT and cid == SUGURI:
            direct = self.best_current_attack_outcome()
            opp_data = self.b.data(self.b.pid(self.b.opp_active))
            active_data = self.b.data(self.b.pid(self.b.active))
            direct_damage = direct.damage if direct is not None else 0
            direct_knockout = bool(direct and direct.knockout)
            direct_prizes = direct.prizes_taken if direct is not None else 0
            if direct is None and self.outcome.active_can_declare_attack_this_turn():
                direct_damage = self.outcome._best_unblocked_damage_from(self.b.active)
                direct_knockout = self.b.opp_active is not None and direct_damage >= hp_left(self.b.opp_active)
                direct_prizes = self.b.prize_value(self.b.opp_active) if direct_knockout else 0
            direct_wins = bool(direct and direct.wins_game)
            if direct is None:
                direct_wins = direct_knockout and direct_prizes >= self.b.my_prizes_left()
            if active_data is None or active_data.basic or direct_knockout or direct_wins:
                return 1000
            boosted_score = 1000
            if direct_damage > 0 and not direct_knockout and opp_data is not None and (opp_data.ex or opp_data.megaEx):
                boosted_damage = direct_damage + 30
                boosted_knockout = self.b.opp_active is not None and boosted_damage >= hp_left(self.b.opp_active)
                boosted_prizes = self.b.prize_value(self.b.opp_active) if boosted_knockout else 0
                if boosted_knockout and (boosted_prizes > direct_prizes or boosted_prizes >= self.b.my_prizes_left()):
                    boosted_score = 94000
            switch_score = 0
            for target in self.b.bench:
                outcome = self.outcome.evaluate_switch_target(target, "suguri")
                if outcome.supported and (outcome.reachable_wins_game or outcome.enables_knockout or outcome.improves_damage or (self.outcome.active_status_blocks_attack() and outcome.enables_attack)):
                    switch_score = max(switch_score, 88000)
            return switch_score if yes else boosted_score
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
            candidate = self.night_stretcher_candidate_for_option(option)
            return (
                self.night_stretcher_policy_value(candidate)
                if candidate is not None
                else SCORE_FORBIDDEN
            )
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
        if cid in {JUDGE, SUGURI}:
            return self.score_play(SimpleNamespace(type=OptionType.PLAY, cardId=cid))
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
                evolution_id = self.b.salvatore_deck_target_evolution(target)
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
                    and self.b.salvatore_deck_target_evolution(pokemon) == evolution_id
                    and self.b.energy_count(pokemon) > energy_count
                    for pokemon in self.b.all_my_pokemon
                )
                if same_line_has_more_energy:
                    score -= 90000
                return score
            if effect == WALLY_COMPASSION:
                outcome = self.outcome.evaluate_wally_target(target)
                return self.wally_effect_legacy_value(outcome) if outcome.supported else SCORE_FORBIDDEN
            if effect == HERO_CAPE:
                return self.score_hero_cape_target(target)
            if effect == TOOL_SCRAPPER:
                return self.score_tool_scrapper_outcome(self.outcome.evaluate_tool_scrapper_target(target, option.toolIndex))
            if effect == BEFEHL_VON_BOSS:
                return self.score_boss_outcome(self.outcome.evaluate_boss_target(target))
            if effect == SUGURI:
                return self.score_switch_target(target, "suguri")
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
        if (
            self.b.pid(self.b.active) == CINDERACE
            and self.b.cinderace_can_accelerate()
            and self.b.has_bench_energy_receiver()
            and not self.cinderace_handoff_improves_current_turn(outcome)
        ):
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
        if self.effect_id() == WALLY_COMPASSION:
            outcome = self.outcome.evaluate_wally_target(target)
            return self.wally_effect_legacy_value(outcome) if outcome.supported else SCORE_FORBIDDEN
        if self.b.pid(target) in {MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX}:
            return damage_on(target) * 1000 + self.b.energy_count(target) * 20000
        return damage_on(target) * 100

    def wally_effect_legacy_value(self, outcome: ImmediateOutcome) -> float:
        if not outcome.supported:
            return 0
        return outcome.healed_damage * 1000 + outcome.recovered_energy_count * 20000

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
        end_result = next((result for result in results if result.option.type == OptionType.END), None)
        return sorted(results, key=lambda result: self._rank_result_key(result, end_result), reverse=True)

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
        if option.type == OptionType.ABILITY and self.outcome.is_surfing_beach_ability(option):
            return self.outcome.evaluate_surfing_beach_ability(option)
        if option.type == OptionType.ATTACH:
            return self.outcome.evaluate_attach(option)
        if option.type == OptionType.RETREAT:
            return self.outcome.evaluate_retreat(option)
        if option.type == OptionType.EVOLVE:
            return self.outcome.evaluate_active_evolution(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == ENERGY_SWITCH:
            return self.outcome.evaluate_energy_switch_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == TOOL_SCRAPPER:
            return self.outcome.evaluate_tool_scrapper_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == SALVATORE:
            return self.outcome.evaluate_salvatore_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == WALLY_COMPASSION:
            return self.outcome.evaluate_wally_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == POKEGEAR:
            return self.outcome.evaluate_pokegear_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == BEFEHL_VON_BOSS:
            return self.outcome.evaluate_boss_play(option)

        target = self.b.option_target(option)
        if target is not None:
            effect = self.policy.effect_id()
            if effect == SALVATORE:
                return self.outcome.evaluate_salvatore_target(target)
            if effect == WALLY_COMPASSION:
                return self.outcome.evaluate_wally_target(target)
            if effect == TOOL_SCRAPPER:
                return self.outcome.evaluate_tool_scrapper_target(target, option.toolIndex)
            if effect == BEFEHL_VON_BOSS:
                return self.outcome.evaluate_boss_target(target)
            if effect == SUGURI:
                return self.outcome.evaluate_switch_target(target, "suguri")
            if effect == SURFING_BEACH or self.b.select.context == SelectContext.SWITCH:
                source = "surfing_beach" if effect == SURFING_BEACH else "retreat"
                return self.outcome.evaluate_switch_target(target, source)
            if self.b.select.context == SelectContext.DAMAGE:
                return self.outcome.evaluate_attack_effect_target(option)
        cid = self.b.option_card(option)
        if cid is not None and self.policy.effect_id() == SALVATORE:
            return self.outcome.evaluate_salvatore_evolution_candidate(option)
        if cid is not None and self.policy.effect_id() == POKEGEAR:
            return self.outcome.evaluate_pokegear_candidate(option)
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

    def _rank_result_key(self, result: SimulationResult, end_result: Optional[SimulationResult]) -> Tuple[Any, ...]:
        if self._retreat_supported_only_loses_to_end(result, end_result):
            outcome = result.outcome
            action = result.action_score
            return (
                action.tier,
                action.immediate,
                action.pressure,
                action.development,
                action.resource,
                -action.risk,
                False,
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
        return self._result_key(result)

    def _retreat_supported_only_loses_to_end(
        self,
        result: SimulationResult,
        end_result: Optional[SimulationResult],
    ) -> bool:
        if end_result is None or result.option.type != OptionType.RETREAT:
            return False
        action = result.action_score
        end_action = end_result.action_score
        if (
            action.tier,
            action.immediate,
            action.pressure,
            action.development,
            action.resource,
            -action.risk,
        ) != (
            end_action.tier,
            end_action.immediate,
            end_action.pressure,
            end_action.development,
            end_action.resource,
            -end_action.risk,
        ):
            return False
        if result.policy_score >= end_result.policy_score:
            return False
        return not self._retreat_has_clear_immediate_benefit(result.outcome)

    def _retreat_has_clear_immediate_benefit(self, outcome: ImmediateOutcome) -> bool:
        if (
            outcome.reachable_wins_game
            or outcome.reachable_knockout
            or outcome.reachable_prizes_taken > 0
            or outcome.reachable_attack_id is not None
            or outcome.enables_knockout
            or outcome.enables_attack
            or outcome.improves_damage
            or outcome.damage > 0
            or outcome.wins_game
            or outcome.knockout
            or outcome.prizes_taken > 0
        ):
            return True
        benefit_reasons = {
            "status_clear",
            "retreat_clears_status",
            "retreat_enables_attack",
            "retreat_improves_damage",
            "switch_enables_knockout",
            "switch_enables_win",
            "bypasses_ex_wall",
            "avoids_wall",
        }
        return any(reason in benefit_reasons for reason in outcome.reasons)

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

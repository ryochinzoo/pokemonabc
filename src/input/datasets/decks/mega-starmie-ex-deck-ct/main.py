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
import re
import sys
from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum
from itertools import combinations
from math import comb
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union


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


EnergyToken = Union[EnergyType, int]
ENERGY_TOKEN_VALUES = frozenset(int(token.value) for token in EnergyType)


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
ULTRA_BALL = 1121
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
    SALVATORE,
    POFIN,
    ULTRA_BALL,
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
        "setup_cards": {CINDERACE, HITODEMAN, MEGA_STARMIE_EX, SALVATORE, POFIN, ULTRA_BALL, CRISPIN},
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
        "setup_cards": {YUKIWARASHI, MEGA_YUKIMENOKO_EX, SALVATORE, POFIN, ULTRA_BALL},
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
        "setup_cards": {HITODEMAN, MEGA_STARMIE_EX, SALVATORE, POFIN, ULTRA_BALL},
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

_TRACKED_SUPPORTER_TURN_KEY: Optional[Tuple[int, int]] = None
_TRACKED_SUPPORTER_CARD_ID: Optional[int] = None
_TRACKED_TOOL_SCRAPPER_SELECTION_KEY: Optional[
    Tuple[int, int, Optional[int]]
] = None
_TRACKED_TOOL_SCRAPPER_TOOL_KEYS: set = set()


def _reset_current_turn_supporter_tracking() -> None:
    global _TRACKED_SUPPORTER_TURN_KEY, _TRACKED_SUPPORTER_CARD_ID
    _TRACKED_SUPPORTER_TURN_KEY = None
    _TRACKED_SUPPORTER_CARD_ID = None


def _reset_tool_scrapper_selection_tracking() -> None:
    global _TRACKED_TOOL_SCRAPPER_SELECTION_KEY
    _TRACKED_TOOL_SCRAPPER_SELECTION_KEY = None
    _TRACKED_TOOL_SCRAPPER_TOOL_KEYS.clear()


def _current_turn_supporter_from_observation(
    obs: Observation,
) -> Optional[int]:
    global _TRACKED_SUPPORTER_TURN_KEY, _TRACKED_SUPPORTER_CARD_ID
    state = getattr(obs, "current", None)
    if state is None:
        _reset_current_turn_supporter_tracking()
        return None
    turn_key = (
        safe_int(getattr(state, "turn", None), -1),
        safe_int(getattr(state, "yourIndex", None), -1),
    )
    if turn_key != _TRACKED_SUPPORTER_TURN_KEY:
        _TRACKED_SUPPORTER_TURN_KEY = turn_key
        _TRACKED_SUPPORTER_CARD_ID = None
    for log in getattr(obs, "logs", None) or []:
        if (
            getattr(log, "type", None) != LogType.PLAY
            or safe_int(getattr(log, "playerIndex", None), -1)
            != turn_key[1]
        ):
            continue
        card_id = getattr(log, "cardId", None)
        card_data = (
            None
            if card_id is None
            else CARD_TABLE.get(int(card_id))
        )
        if (
            card_data is not None
            and card_data.cardType == CardType.SUPPORTER
        ):
            _TRACKED_SUPPORTER_CARD_ID = int(card_id)
    return _TRACKED_SUPPORTER_CARD_ID


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
    tokens = Counter(energy_tokens)
    typed_requirements = {
        energy_type: count
        for energy_type, count in requirements.items()
        if energy_type != EnergyType.COLORLESS
    }
    if any(tokens[energy_type] < count for energy_type, count in typed_requirements.items()):
        return False
    colorless_need = requirements[EnergyType.COLORLESS]
    remaining_units = sum(tokens.values()) - sum(typed_requirements.values())
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


def is_hero_cape_action(card_id: int) -> bool:
    return card_id == HERO_CAPE


def attached_energy_tokens_for_card(
    energy_data: Any,
    pokemon_data: Any,
) -> Optional[Tuple[Any, ...]]:
    if energy_data is None:
        return None
    if getattr(energy_data, "cardType", None) == CardType.BASIC_ENERGY:
        energy_type = getattr(energy_data, "energyType", None)
        return (energy_type,) if energy_type is not None else None
    if getattr(energy_data, "cardType", None) != CardType.SPECIAL_ENERGY:
        return None

    text = normalized_public_effect_text(energy_data)
    clauses = split_public_effect_clauses(text)
    symbol_types = {
        "c": EnergyType.COLORLESS,
        "g": EnergyType.GRASS,
        "r": EnergyType.FIRE,
        "w": EnergyType.WATER,
        "l": EnergyType.LIGHTNING,
        "p": EnergyType.PSYCHIC,
        "f": EnergyType.FIGHTING,
        "d": EnergyType.DARKNESS,
        "m": EnergyType.METAL,
    }

    def tokens(match: Optional[Any]) -> Optional[Tuple[Any, ...]]:
        if match is None:
            return None
        symbols = re.findall(r"\{([a-z])\}", match.group(1))
        if not symbols or any(symbol not in symbol_types for symbol in symbols):
            return None
        return tuple(symbol_types[symbol] for symbol in symbols)

    unconditional_tokens: Optional[Tuple[Any, ...]] = None
    evolution_tokens: Optional[Tuple[Any, ...]] = None
    has_end_of_turn_discard = False
    for clause in clauses:
        unconditional_match = re.fullmatch(
            r"(?:"
            r"(?:as long as|while) this card is attached to a pokemon,?\s+"
            r"(?:it|this card) provides|"
            r"this card provides"
            r")\s+((?:\{[a-z]\})+)\s+energy",
            clause,
        )
        evolution_match = re.fullmatch(
            r"if this card is attached to an evolution pokemon,?\s+"
            r"(?:it|this card) provides\s+((?:\{[a-z]\})+)\s+energy instead",
            clause,
        )
        discard_match = re.fullmatch(
            r"if this card is attached to (?:1 of your|a) pokemon,?\s+"
            r"discard it at the end of your turn",
            clause,
        )
        if unconditional_match is not None and unconditional_tokens is None:
            unconditional_tokens = tokens(unconditional_match)
        elif evolution_match is not None and evolution_tokens is None:
            evolution_tokens = tokens(evolution_match)
        elif discard_match is not None and not has_end_of_turn_discard:
            has_end_of_turn_discard = True
        else:
            return None

    if unconditional_tokens is None:
        return None
    if evolution_tokens is None:
        return None if has_end_of_turn_discard else unconditional_tokens
    if pokemon_data is None:
        return None
    return (
        evolution_tokens
        if not getattr(pokemon_data, "basic", False)
        else unconditional_tokens
    )


def attached_energy_unsupported_reason(energy_data: Any) -> str:
    if getattr(energy_data, "cardType", None) == CardType.SPECIAL_ENERGY:
        return "unsupported_attached_special_energy"
    return "unsupported_attached_energy"


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
    reachable_attack_pressure: float = 0.0
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
    adds_board_out_buffer: bool = False
    preserves_primary_pokemon: bool = False
    equivalent_evolution_available: bool = False
    completes_next_attacker: bool = False
    develops_bench_next_attacker: bool = False
    evolution_hp_gain: int = 0
    completes_evolution_line: bool = False
    completed_same_line_attackers: int = 0
    same_turn_attack_connected: bool = False
    same_turn_attack_option_count: int = 0
    post_evolution_ready_attack_count: int = 0
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
class ToolScrapperTargetFacts:
    option_index: int
    owner_index: int
    target_id: int
    target_serial: Optional[int]
    tool_index: int
    tool_id: int
    tool_serial: Optional[int]
    attached_to_opponent: bool
    currently_attached: bool
    already_selected: bool


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
class PokePadTargetFacts:
    target_id: int
    searchable: bool
    same_turn_deployable: bool
    duplicate_in_hand: bool
    duplicate_in_play: bool
    evolution_demand: int
    base_supply: int
    active_only_board: bool
    board_out_buffer: bool
    evolution_line_shortage: bool
    turbo_flare_route_live: bool
    turbo_flare_energy_target: bool
    current_pipeline_state: str
    reachable_pipeline_state: str
    same_turn_attack_preserved: bool
    development_value: float
    role: str
    useful: bool


@dataclass(frozen=True)
class UltraBallTargetFacts:
    target_id: int
    legal: bool
    searchable: bool
    setup_window_open: bool
    setup_role_live: bool
    same_turn_deployable: bool
    evolution_base_in_play: bool
    duplicate_in_hand: bool
    duplicate_in_play: bool
    role: str
    useful: bool
    development_value: float


@dataclass(frozen=True)
class SalvatoreDevelopmentFacts:
    base_id: int
    base_serial: Optional[int]
    evolution_id: int
    source_in_play: bool
    evolution_searchable: bool
    hp_gain: int
    completes_evolution_line: bool
    develops_bench_next_attacker: bool
    completed_same_line_attackers: int
    equivalent_normal_evolution: bool
    same_turn_attack_connected: bool
    same_turn_attack_option_count: int
    post_evolution_ready_attack_count: int
    development_probability: float
    development_value: float


@dataclass(frozen=True)
class HildaEvolutionCandidateFacts:
    target_id: int
    legal: bool
    base_in_play: bool
    currently_evolvable: bool
    missing_evolution_line: bool
    same_turn_attack_connected: bool
    completed_same_line_count: int
    attack_axis_gap: Optional[int]
    attack_axis_damage: int
    current_value: float


@dataclass(frozen=True)
class HildaEnergyCandidateFacts:
    target_id: int
    legal: bool
    same_turn_attach_available: bool
    best_attach_target_id: Optional[int]
    best_attach_target_serial: Optional[int]
    best_target_is_evolution: bool
    provided_colorless_units: int
    attack_gap_before: Optional[int]
    attack_gap_after: Optional[int]
    attack_gap_reduction: int
    enabled_attack_ids: Tuple[int, ...]
    enabled_attack_damage: int
    discarded_at_end_of_turn: bool
    current_value: float


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


class CandidateProjectionConfidence(str, Enum):
    EXACT = "EXACT"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class CandidateProjection:
    option_index: int
    option_type: Any
    confidence: CandidateProjectionConfidence
    combat_result_exact: bool
    terminal_win: bool
    damage_to_opponent: int
    opponent_active_ko: bool
    prizes_taken: int
    projected_active_serial: Optional[int]
    projected_active_card_id: Optional[int]
    projected_active_hp: Optional[int]
    projected_active_prize_value: Optional[int]
    projected_active_can_attack: bool
    next_attacker_ready: bool
    ends_turn: bool
    unsupported_reason: Optional[str] = None
    reasons: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateProjectionFacts:
    supported: bool
    option_type: Any
    card_id: Optional[int]
    attack_id: Optional[int]
    projected_active_card_id: Optional[int]
    projected_active_serial: Optional[int]
    projected_active_hp: Optional[int]
    projected_active_max_hp: Optional[int]
    projected_active_energy_tokens: Optional[Tuple[Any, ...]]
    projected_active_tool_ids: Tuple[int, ...]
    projected_active_changed: bool
    projected_opponent_active_hp: Optional[int]
    terminal_win: bool
    opponent_active_ko: bool
    unsupported_reason: Optional[str] = None


class ActiveBenchTransitionOrigin(str, Enum):
    RETREAT = "RETREAT"
    SURFING_BEACH = "SURFING_BEACH"
    SUGURI = "SUGURI"
    BOSS_FORCED_SWITCH = "BOSS_FORCED_SWITCH"


ACTIVE_BENCH_TRANSITION_ORIGIN_REASONS = frozenset({
    "transition_origin_unknown",
    "transition_origin_not_supported",
    "transition_origin_option_invalid",
    "transition_origin_identity_mismatch",
    "transition_origin_player_mismatch",
    "transition_origin_binding_unresolved",
    "transition_origin_result_missing",
    "transition_origin_option_not_current",
    "transition_origin_legality_unresolved",
    "transition_effect_continuity_mismatch",
    "transition_sequence_unresolved",
    "transition_suguri_choice_required",
    "transition_suguri_non_switch_effect",
    "retreat_energy_discard_unresolved",
})

ACTIVE_BENCH_TRANSITION_REASONS = frozenset({
    "transition_target_missing",
    "transition_target_not_current_bench",
    "transition_target_identity_mismatch",
    "transition_target_serial_mismatch",
    "transition_target_slot_mismatch",
    "transition_player_mismatch",
    "transition_old_active_missing",
    "transition_projected_bench_unresolved",
    "transition_bench_order_unresolved",
    "transition_energy_identity_unresolved",
    "transition_energy_tokens_unresolved",
    "transition_tool_identity_unresolved",
    "transition_status_unresolved",
    "transition_duplicate_pokemon_serial",
    "transition_duplicate_attached_card_serial",
    "transition_promotion_not_supported",
})


@dataclass(frozen=True)
class ActiveBenchTransitionOriginBindingFacts:
    supported: bool
    origin: Optional[ActiveBenchTransitionOrigin]
    acting_player_index: Optional[int]
    affected_player_index: Optional[int]
    origin_decision_option_index: Optional[int]
    origin_option_type: Optional[OptionType]
    origin_option_card_id: Optional[int]
    expected_switch_effect_id: Optional[int]
    binding_exact: bool
    unsupported_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.supported:
            if self.binding_exact:
                raise ValueError("unsupported_transition_origin_binding_exact")
            if self.unsupported_reason not in ACTIVE_BENCH_TRANSITION_ORIGIN_REASONS:
                raise ValueError("unsupported_transition_origin_binding_missing_reason")
            return
        if (
            not self.binding_exact
            or self.unsupported_reason is not None
            or not isinstance(self.origin, ActiveBenchTransitionOrigin)
            or self.acting_player_index not in {0, 1}
            or self.affected_player_index not in {0, 1}
            or type(self.origin_decision_option_index) is not int
            or self.origin_decision_option_index < 0
            or not isinstance(self.origin_option_type, OptionType)
        ):
            raise ValueError("incomplete_supported_transition_origin_binding")
        if self.origin == ActiveBenchTransitionOrigin.RETREAT:
            if (
                self.origin_option_type != OptionType.RETREAT
                or self.origin_option_card_id is not None
                or self.expected_switch_effect_id is not None
                or self.acting_player_index != self.affected_player_index
            ):
                raise ValueError("invalid_retreat_transition_origin_binding")
            return
        expected_type = (
            OptionType.ABILITY
            if self.origin == ActiveBenchTransitionOrigin.SURFING_BEACH
            else OptionType.PLAY
        )
        if (
            self.origin_option_type != expected_type
            or type(self.origin_option_card_id) is not int
            or type(self.expected_switch_effect_id) is not int
            or self.origin_option_card_id != self.expected_switch_effect_id
        ):
            raise ValueError("invalid_effect_transition_origin_binding")
        same_side = self.acting_player_index == self.affected_player_index
        if self.origin == ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH:
            if same_side:
                raise ValueError("invalid_boss_transition_origin_players")
        elif not same_side:
            raise ValueError("invalid_self_transition_origin_players")


@dataclass(frozen=True)
class AttachedEnergyPublicFacts:
    card_id: int
    serial: int
    tokens: Tuple[EnergyToken, ...]

    def __post_init__(self) -> None:
        if type(self.card_id) is not int or type(self.serial) is not int:
            raise TypeError("invalid_attached_energy_identity")
        if not self.tokens or any(
            not isinstance(token, EnergyType)
            and (
                type(token) is not int
                or token not in ENERGY_TOKEN_VALUES
            )
            for token in self.tokens
        ):
            raise TypeError("invalid_attached_energy_tokens")


@dataclass(frozen=True)
class AttachedToolPublicFacts:
    card_id: int
    serial: int

    def __post_init__(self) -> None:
        if type(self.card_id) is not int or type(self.serial) is not int:
            raise TypeError("invalid_attached_tool_identity")


@dataclass(frozen=True)
class PokemonPublicSnapshotFacts:
    card_id: int
    serial: int
    hp: int
    max_hp: int
    damage_counters: int
    attached_energy: Tuple[AttachedEnergyPublicFacts, ...]
    attached_tools: Tuple[AttachedToolPublicFacts, ...]

    def __post_init__(self) -> None:
        if type(self.card_id) is not int or type(self.serial) is not int:
            raise TypeError("invalid_transition_pokemon_identity")
        if self.max_hp < 0 or self.hp < 0 or self.hp > self.max_hp:
            raise ValueError("invalid_transition_pokemon_hp")
        if self.damage_counters != self.max_hp - self.hp:
            raise ValueError("invalid_transition_pokemon_damage_counters")
        energy_serials = tuple(facts.serial for facts in self.attached_energy)
        tool_serials = tuple(facts.serial for facts in self.attached_tools)
        if len(set(energy_serials)) != len(energy_serials):
            raise ValueError("duplicate_attached_energy_serial")
        if len(set(tool_serials)) != len(tool_serials):
            raise ValueError("duplicate_attached_tool_serial")
        if len(set(energy_serials + tool_serials)) != len(energy_serials + tool_serials):
            raise ValueError("duplicate_attached_card_serial")


@dataclass(frozen=True)
class ActiveSpecialConditionFacts:
    asleep: bool
    paralyzed: bool
    confused: bool
    burned: bool
    poisoned: bool


@dataclass(frozen=True)
class ActiveBenchTransitionFacts:
    supported: bool
    origin_binding: ActiveBenchTransitionOriginBindingFacts
    target_decision_option_index: Optional[int]
    old_active: Optional[PokemonPublicSnapshotFacts]
    old_active_status_before: Optional[ActiveSpecialConditionFacts]
    new_active: Optional[PokemonPublicSnapshotFacts]
    new_active_status_after: Optional[ActiveSpecialConditionFacts]
    projected_bench: Optional[Tuple[PokemonPublicSnapshotFacts, ...]]
    bench_count_before: Optional[int]
    target_card_id: Optional[int]
    target_serial: Optional[int]
    target_player_index: Optional[int]
    target_original_slot: Optional[int]
    status_exact: bool
    transition_exact: bool
    unsupported_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.supported:
            if self.transition_exact:
                raise ValueError("unsupported_active_bench_transition_exact")
            if self.unsupported_reason not in (
                ACTIVE_BENCH_TRANSITION_ORIGIN_REASONS
                | ACTIVE_BENCH_TRANSITION_REASONS
            ):
                raise ValueError("unsupported_active_bench_transition_missing_reason")
            return
        if (
            not self.transition_exact
            or not self.status_exact
            or self.unsupported_reason is not None
            or not self.origin_binding.supported
            or not self.origin_binding.binding_exact
            or type(self.target_decision_option_index) is not int
            or self.target_decision_option_index < 0
            or self.old_active is None
            or self.old_active_status_before is None
            or self.new_active is None
            or self.new_active_status_after is None
            or self.projected_bench is None
            or type(self.bench_count_before) is not int
            or type(self.target_card_id) is not int
            or type(self.target_serial) is not int
            or self.target_player_index not in {0, 1}
            or type(self.target_original_slot) is not int
        ):
            raise ValueError("incomplete_supported_active_bench_transition")
        if self.target_player_index != self.origin_binding.affected_player_index:
            raise ValueError("supported_transition_player_mismatch")
        if (
            self.target_card_id != self.new_active.card_id
            or self.target_serial != self.new_active.serial
        ):
            raise ValueError("supported_transition_target_mismatch")
        if len(self.projected_bench) != self.bench_count_before:
            raise ValueError("supported_transition_bench_count_mismatch")
        if not 0 <= self.target_original_slot < len(self.projected_bench):
            raise ValueError("supported_transition_target_slot_mismatch")
        if self.projected_bench[self.target_original_slot] != self.old_active:
            raise ValueError("supported_transition_old_active_slot_mismatch")
        projected_serials = tuple(
            pokemon.serial
            for pokemon in (self.new_active,) + self.projected_bench
        )
        if len(set(projected_serials)) != len(projected_serials):
            raise ValueError("duplicate_projected_pokemon_serial")
        attached_owners: Dict[int, int] = {}
        for pokemon in (self.new_active,) + self.projected_bench:
            attached_serials = tuple(
                facts.serial
                for facts in pokemon.attached_energy + pokemon.attached_tools
            )
            for attached_serial in attached_serials:
                previous_owner = attached_owners.setdefault(
                    attached_serial,
                    pokemon.serial,
                )
                if previous_owner != pokemon.serial:
                    raise ValueError("duplicate_projected_attached_card_serial")


@dataclass(frozen=True)
class ProjectedActivePublicFacts:
    card_id: int
    serial: Optional[int]
    hp: int
    max_hp: int
    damage_counters: int
    energy_card_ids: Tuple[int, ...]
    energy_tokens: Optional[Tuple[EnergyToken, ...]]
    tool_ids: Tuple[int, ...]
    asleep: bool
    paralyzed: bool
    confused: bool
    burned: bool
    poisoned: bool

    def __post_init__(self) -> None:
        if self.max_hp < 0 or self.hp < 0 or self.hp > self.max_hp:
            raise ValueError("invalid_projected_active_hp")
        if self.damage_counters != self.max_hp - self.hp:
            raise ValueError("invalid_projected_active_damage_counters")
        if self.energy_tokens is not None and any(
            not isinstance(token, EnergyType)
            and (
                type(token) is not int
                or token not in ENERGY_TOKEN_VALUES
            )
            for token in self.energy_tokens
        ):
            raise TypeError("invalid_projected_active_energy_token")


@dataclass(frozen=True)
class P6AttackDecisionInputFacts:
    supported: bool
    decision_option_index: Optional[int]
    attack_id: Optional[int]
    combat_result_exact: bool
    confirmed_damage: Optional[int]
    opponent_active_ko: Optional[bool]
    immediate_prizes_taken: Optional[int]
    candidate_wins_game: Optional[bool]
    our_active: Optional[ProjectedActivePublicFacts]
    opponent_active_after_attack: Optional[ProjectedActivePublicFacts]
    projected_bench_unchanged: bool
    unsupported_reason: Optional[str] = None
    prepared_our_bench: Optional[Tuple[PokemonPublicSnapshotFacts, ...]] = None
    prepared_opponent_bench: Optional[
        Tuple[PokemonPublicSnapshotFacts, ...]
    ] = None
    prepared_board_exact: bool = False

    def __post_init__(self) -> None:
        if not self.supported:
            return
        if self.unsupported_reason is not None:
            raise ValueError("supported_attack_decision_has_unsupported_reason")
        if (
            self.attack_id is None
            or not self.combat_result_exact
            or self.confirmed_damage is None
            or self.opponent_active_ko is None
            or self.immediate_prizes_taken is None
            or self.candidate_wins_game is None
            or self.our_active is None
            or not self.projected_bench_unchanged
        ):
            raise ValueError("incomplete_supported_attack_decision")
        prepared_benches_present = (
            self.prepared_our_bench is not None
            or self.prepared_opponent_bench is not None
        )
        if self.prepared_board_exact != prepared_benches_present:
            raise ValueError("incomplete_prepared_attack_board")
        if self.prepared_board_exact and (
            self.prepared_our_bench is None
            or self.prepared_opponent_bench is None
        ):
            raise ValueError("incomplete_prepared_attack_bench")
        if (
            not self.opponent_active_ko
            and not self.candidate_wins_game
            and self.opponent_active_after_attack is None
        ):
            raise ValueError("missing_projected_opponent_active")


def projected_active_public_facts(
    board: Any,
    active: Optional[Pokemon],
    *,
    status_owner: Optional[Any] = None,
    projected_card_id: Optional[int] = None,
    projected_serial: Optional[int] = None,
    projected_hp: Optional[int] = None,
    projected_max_hp: Optional[int] = None,
    projected_energy_card_ids: Optional[Sequence[int]] = None,
    projected_energy_tokens: Optional[Sequence[EnergyToken]] = None,
    projected_tool_ids: Optional[Sequence[int]] = None,
) -> Optional[ProjectedActivePublicFacts]:
    if active is None:
        return None
    active_card_id = (
        board.pid(active)
        if projected_card_id is None
        else int(projected_card_id)
    )
    active_serial = (
        getattr(active, "serial", None)
        if projected_serial is None
        else int(projected_serial)
    )
    active_hp = hp_left(active) if projected_hp is None else int(projected_hp)
    active_max_hp = (
        max_hp(active)
        if projected_max_hp is None
        else int(projected_max_hp)
    )
    energy_card_ids = (
        tuple(int(card_id) for card_id in board.energies(active))
        if projected_energy_card_ids is None
        else tuple(int(card_id) for card_id in projected_energy_card_ids)
    )
    resolved_tokens: List[EnergyToken] = []
    energy_mapping_supported = True
    pokemon_data = board.data(active_card_id)
    for energy_card_id in energy_card_ids:
        tokens = attached_energy_tokens_for_card(
            board.data(energy_card_id),
            pokemon_data,
        )
        if tokens is None or any(
            not isinstance(token, EnergyType)
            and (
                type(token) is not int
                or token not in ENERGY_TOKEN_VALUES
            )
            for token in tokens
        ):
            energy_mapping_supported = False
            break
        resolved_tokens.extend(tokens)
    energy_tokens = (
        tuple(resolved_tokens)
        if energy_mapping_supported
        else None
    )
    if projected_energy_tokens is not None:
        projected_tokens = tuple(projected_energy_tokens)
        if any(
            not isinstance(token, EnergyType)
            and (
                type(token) is not int
                or token not in ENERGY_TOKEN_VALUES
            )
            for token in projected_tokens
        ):
            raise TypeError("invalid_projected_active_energy_token")
        if energy_tokens is None:
            raise ValueError("projected_active_energy_mapping_unsupported")
        if projected_tokens != energy_tokens:
            raise ValueError("projected_active_energy_identity_mismatch")
    tool_ids = (
        tuple(
            int(card_id(public_card))
            for public_card in tuple(getattr(active, "tools", None) or ())
        )
        if projected_tool_ids is None
        else tuple(int(tool_id) for tool_id in projected_tool_ids)
    )
    owner = status_owner or SimpleNamespace()
    return ProjectedActivePublicFacts(
        card_id=active_card_id,
        serial=active_serial,
        hp=active_hp,
        max_hp=active_max_hp,
        damage_counters=active_max_hp - active_hp,
        energy_card_ids=energy_card_ids,
        energy_tokens=energy_tokens,
        tool_ids=tool_ids,
        asleep=bool(getattr(owner, "asleep", False)),
        paralyzed=bool(getattr(owner, "paralyzed", False)),
        confused=bool(getattr(owner, "confused", False)),
        burned=bool(getattr(owner, "burned", False)),
        poisoned=bool(getattr(owner, "poisoned", False)),
    )


@dataclass(frozen=True)
class OpponentPublicThreatFacts:
    supported: bool
    best_confirmed_damage: int
    can_ko_projected_active: bool
    prizes_lost: int
    usable_attack_ids: Tuple[int, ...]
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class PrizeExchangeFacts:
    supported: bool
    immediate_prizes_taken: int
    my_prizes_left_after_candidate: int
    confirmed_reply_supported: bool
    confirmed_reply_prizes_lost: int
    opponent_prizes_left_after_reply: Optional[int]
    net_prize_exchange: Optional[int]
    candidate_wins_game: bool
    confirmed_reply_wins_game: Optional[bool]
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class BoardOutFacts:
    supported: bool
    projected_bench_count: Optional[int]
    board_out_if_projected_active_ko: Optional[bool]
    confirmed_reply_supported: bool
    confirmed_reply_ko: Optional[bool]
    confirmed_reply_causes_board_out: Optional[bool]
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class NextAttackerFacts:
    supported: bool
    projected_bench_count: Optional[int]
    ready_next_attacker_exists: Optional[bool]
    ready_next_attacker_count: Optional[int]
    best_confirmed_damage: Optional[int]
    can_ko_projected_opponent_active: Optional[bool]
    best_next_attacker_card_id: Optional[int]
    best_next_attacker_serial: Optional[int]
    best_attack_id: Optional[int]
    usable_attack_ids: Tuple[int, ...]
    confirmed_reply_supported: bool
    confirmed_reply_ko: Optional[bool]
    confirmed_reply_has_ready_next_attacker: Optional[bool]
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class DirectDecisionOutcomeFacts:
    supported: bool
    attack_id: Optional[int]
    confirmed_damage: Optional[int]
    opponent_active_ko: Optional[bool]
    immediate_prizes_taken: Optional[int]
    candidate_wins_game: Optional[bool]
    reply_information_supported: bool
    confirmed_reply_damage: Optional[int]
    confirmed_reply_ko: Optional[bool]
    confirmed_reply_prizes_lost: Optional[int]
    confirmed_loss_by_prize: Optional[bool]
    confirmed_loss_by_board_out: Optional[bool]
    confirmed_loss: Optional[bool]
    net_prize_exchange: Optional[int]
    my_prizes_left_after_candidate: Optional[int]
    opponent_prizes_left_after_reply: Optional[int]
    projected_active_survives_confirmed_reply: Optional[bool]
    has_ready_next_attacker_after_reply: Optional[bool]
    next_attacker_can_ko: Optional[bool]
    next_attacker_confirmed_damage: Optional[int]
    unsupported_reason: Optional[str] = None


class DirectAttackCandidateState(str, Enum):
    TERMINAL_WIN = "TERMINAL_WIN"
    FULLY_KNOWN = "FULLY_KNOWN"
    REPLY_UNKNOWN = "REPLY_UNKNOWN"
    OVERALL_UNSUPPORTED = "OVERALL_UNSUPPORTED"
    PARTIAL_UNKNOWN = "PARTIAL_UNKNOWN"


class DirectAttackComparison(str, Enum):
    LEFT_BETTER = "LEFT_BETTER"
    RIGHT_BETTER = "RIGHT_BETTER"
    EQUIVALENT = "EQUIVALENT"
    INCOMPARABLE = "INCOMPARABLE"


class DirectAttackComparisonReason(str, Enum):
    BOTH_IMMEDIATE_WIN = "BOTH_IMMEDIATE_WIN"
    LEFT_IMMEDIATE_WIN = "LEFT_IMMEDIATE_WIN"
    RIGHT_IMMEDIATE_WIN = "RIGHT_IMMEDIATE_WIN"
    LEFT_AVOIDS_CONFIRMED_LOSS = "LEFT_AVOIDS_CONFIRMED_LOSS"
    RIGHT_AVOIDS_CONFIRMED_LOSS = "RIGHT_AVOIDS_CONFIRMED_LOSS"
    BOTH_CONFIRMED_LOSS = "BOTH_CONFIRMED_LOSS"
    SAFE_DOMINANCE = "SAFE_DOMINANCE"
    SAME_CANONICAL_OUTCOME = "SAME_CANONICAL_OUTCOME"
    OVERALL_UNSUPPORTED = "OVERALL_UNSUPPORTED"
    REPLY_UNKNOWN = "REPLY_UNKNOWN"
    PARTIAL_UNKNOWN = "PARTIAL_UNKNOWN"
    CONFLICTING_ADVANTAGES = "CONFLICTING_ADVANTAGES"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


@dataclass(frozen=True)
class DirectAttackShadowCandidate:
    option_index: int
    attack_id: Optional[int]
    facts: DirectDecisionOutcomeFacts


@dataclass(frozen=True)
class DirectAttackComparisonResult:
    left_option_index: int
    right_option_index: int
    relation: DirectAttackComparison
    reason: DirectAttackComparisonReason
    left_state: DirectAttackCandidateState
    right_state: DirectAttackCandidateState


@dataclass(frozen=True)
class CurrentDirectAttackCandidateFacts:
    candidates: Tuple[DirectAttackShadowCandidate, ...]
    blocked_reasons: Tuple[str, ...]


@dataclass(frozen=True)
class Phase3PreparedAttackBindingFacts:
    adapter: str
    origin_option_index: Optional[int]
    supported: bool
    candidate: Optional[DirectAttackShadowCandidate]
    unsupported_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.adapter:
            raise ValueError("phase3_adapter_required")
        if self.candidate is not None:
            if (
                type(self.origin_option_index) is not int
                or self.origin_option_index < 0
                or self.candidate.option_index != self.origin_option_index
            ):
                raise ValueError("invalid_candidate_phase3_binding")
            if self.candidate.facts.supported:
                if not self.supported or self.unsupported_reason is not None:
                    raise ValueError("supported_phase3_candidate_has_reason")
            elif self.supported or self.unsupported_reason is None:
                raise ValueError("invalid_unsupported_phase3_candidate")
        elif self.supported or self.unsupported_reason is None:
            raise ValueError("invalid_unsupported_phase3_binding")


@dataclass(frozen=True)
class Phase3CurrentPreparedComparisonFacts:
    current_candidate: DirectAttackShadowCandidate
    prepared_binding: Phase3PreparedAttackBindingFacts
    result: DirectAttackComparisonResult

    def __post_init__(self) -> None:
        prepared_candidate = self.prepared_binding.candidate
        if prepared_candidate is None:
            raise ValueError("phase3_comparison_prepared_candidate_required")
        if (
            self.result.left_option_index
            != self.current_candidate.option_index
            or self.result.right_option_index
            != prepared_candidate.option_index
        ):
            raise ValueError("phase3_comparison_identity_mismatch")


@dataclass(frozen=True)
class Phase3DirectAttackShadowFacts:
    current_candidates: Tuple[DirectAttackShadowCandidate, ...]
    prepared_bindings: Tuple[Phase3PreparedAttackBindingFacts, ...]
    prepared_candidates: Tuple[DirectAttackShadowCandidate, ...]
    prepared_duplicate_deduplications: int
    multiple_prepared_attack_origins: Tuple[int, ...]
    origin_conflicts: Tuple[int, ...]
    blocked_reasons: Tuple[str, ...]
    comparisons: Tuple[Phase3CurrentPreparedComparisonFacts, ...]

    def __post_init__(self) -> None:
        if self.prepared_duplicate_deduplications < 0:
            raise ValueError("invalid_phase3_deduplication_count")
        if any(
            binding in self.prepared_bindings[:index]
            for index, binding in enumerate(self.prepared_bindings)
        ):
            raise ValueError("duplicate_phase3_prepared_binding")
        candidate_bindings = tuple(
            binding
            for binding in self.prepared_bindings
            if binding.candidate is not None
        )
        if self.prepared_candidates != tuple(
            binding.candidate for binding in candidate_bindings
        ):
            raise ValueError("phase3_prepared_candidate_projection_mismatch")
        expected_pairs = tuple(
            (current_candidate, prepared_binding)
            for current_candidate in self.current_candidates
            for prepared_binding in candidate_bindings
        )
        actual_pairs = tuple(
            (
                comparison.current_candidate,
                comparison.prepared_binding,
            )
            for comparison in self.comparisons
        )
        if actual_pairs != expected_pairs:
            raise ValueError("phase3_current_prepared_cross_product_mismatch")


class Phase4CurrentValueGateReason(str, Enum):
    CURRENT_IMMEDIATE_WIN = "CURRENT_IMMEDIATE_WIN"
    CURRENT_CONFIRMED_KO = "CURRENT_CONFIRMED_KO"
    CURRENT_CONFIRMED_PRIZE_GAIN = "CURRENT_CONFIRMED_PRIZE_GAIN"
    UNCERTAIN_ACTION_UNSUPPORTED = "UNCERTAIN_ACTION_UNSUPPORTED"
    NO_LEGAL_CURRENT_ATTACK = "NO_LEGAL_CURRENT_ATTACK"
    NO_SUPPORTED_CURRENT_ATTACK = "NO_SUPPORTED_CURRENT_ATTACK"
    CURRENT_HAS_OVERALL_UNSUPPORTED = "CURRENT_HAS_OVERALL_UNSUPPORTED"
    CURRENT_HAS_REPLY_UNKNOWN = "CURRENT_HAS_REPLY_UNKNOWN"
    CURRENT_HAS_PARTIAL_UNKNOWN = "CURRENT_HAS_PARTIAL_UNKNOWN"
    CURRENT_HAS_CONFIRMED_LOSS = "CURRENT_HAS_CONFIRMED_LOSS"
    CURRENT_CONFIRMED_NON_KO_NO_PRIZE = (
        "CURRENT_CONFIRMED_NON_KO_NO_PRIZE"
    )
    CURRENT_VALUE_NOT_GATE_ELIGIBLE = "CURRENT_VALUE_NOT_GATE_ELIGIBLE"


@dataclass(frozen=True)
class Phase4UncertainActionFacts:
    option_index: int
    option_type: Any
    legal: bool
    immediate_outcome_supported: bool
    self_preparation: bool
    opponent_disruption: bool
    board_development: bool
    healing_survival: bool
    evidence_reasons: Tuple[str, ...]
    uncertainty_reasons: Tuple[str, ...]
    uncertain_action_supported: bool

    def __post_init__(self) -> None:
        if type(self.option_index) is not int or self.option_index < 0:
            raise ValueError("invalid_phase4_uncertain_action_index")
        has_evidence = any((
            self.self_preparation,
            self.opponent_disruption,
            self.board_development,
            self.healing_survival,
        ))
        if has_evidence != bool(self.evidence_reasons):
            raise ValueError("phase4_uncertain_action_evidence_mismatch")
        expected_supported = (
            self.legal
            and self.immediate_outcome_supported
            and has_evidence
            and bool(self.uncertainty_reasons)
        )
        if self.uncertain_action_supported != expected_supported:
            raise ValueError("phase4_uncertain_action_support_mismatch")


@dataclass(frozen=True)
class Phase4CurrentValueGateFacts:
    current_candidates: Tuple[DirectAttackShadowCandidate, ...]
    current_candidate_count: int
    current_supported_candidate_count: int
    current_states: Tuple[DirectAttackCandidateState, ...]
    current_has_immediate_win: bool
    current_has_confirmed_ko: bool
    current_has_confirmed_prize_gain: bool
    current_has_confirmed_loss: bool
    current_has_reply_unknown: bool
    current_has_overall_unsupported: bool
    current_has_partial_unknown: bool
    current_has_confirmed_non_ko_no_prize: bool
    uncertain_actions: Tuple[Phase4UncertainActionFacts, ...]
    uncertain_action_supported: bool
    gate_open: bool
    gate_reason: Phase4CurrentValueGateReason
    gate_reasons: Tuple[Phase4CurrentValueGateReason, ...]

    def __post_init__(self) -> None:
        if self.current_candidate_count != len(self.current_candidates):
            raise ValueError("phase4_current_candidate_count_mismatch")
        if not 0 <= self.current_supported_candidate_count <= self.current_candidate_count:
            raise ValueError("invalid_phase4_current_candidate_counts")
        supported_candidates = tuple(
            candidate
            for candidate in self.current_candidates
            if candidate.facts.supported
        )
        if self.current_supported_candidate_count != len(supported_candidates):
            raise ValueError("phase4_supported_candidate_count_mismatch")
        expected_states = tuple(
            classify_direct_attack_candidate(candidate.facts)
            for candidate in self.current_candidates
        )
        if self.current_states != expected_states:
            raise ValueError("phase4_current_states_mismatch")
        if self.current_has_reply_unknown != (
            DirectAttackCandidateState.REPLY_UNKNOWN in self.current_states
        ):
            raise ValueError("phase4_reply_unknown_mismatch")
        if self.current_has_overall_unsupported != (
            DirectAttackCandidateState.OVERALL_UNSUPPORTED
            in self.current_states
        ):
            raise ValueError("phase4_overall_unsupported_mismatch")
        if self.current_has_partial_unknown != (
            DirectAttackCandidateState.PARTIAL_UNKNOWN in self.current_states
        ):
            raise ValueError("phase4_partial_unknown_mismatch")
        protected_candidates = tuple(
            candidate
            for candidate in supported_candidates
            if candidate.facts.confirmed_loss is not True
        )
        expected_outcomes = (
            any(
                candidate.facts.candidate_wins_game is True
                for candidate in protected_candidates
            ),
            any(
                candidate.facts.opponent_active_ko is True
                for candidate in protected_candidates
            ),
            any(
                candidate.facts.immediate_prizes_taken is not None
                and candidate.facts.immediate_prizes_taken > 0
                for candidate in protected_candidates
            ),
            any(
                candidate.facts.confirmed_loss is True
                for candidate in supported_candidates
            ),
            any(
                candidate.facts.candidate_wins_game is False
                and candidate.facts.opponent_active_ko is False
                and candidate.facts.immediate_prizes_taken == 0
                for candidate in protected_candidates
            ),
        )
        if expected_outcomes != (
            self.current_has_immediate_win,
            self.current_has_confirmed_ko,
            self.current_has_confirmed_prize_gain,
            self.current_has_confirmed_loss,
            self.current_has_confirmed_non_ko_no_prize,
        ):
            raise ValueError("phase4_current_outcome_aggregate_mismatch")
        if self.uncertain_action_supported != any(
            facts.uncertain_action_supported for facts in self.uncertain_actions
        ):
            raise ValueError("phase4_uncertain_action_aggregate_mismatch")
        if not self.gate_reasons or self.gate_reason not in self.gate_reasons:
            raise ValueError("phase4_gate_reason_missing")
        if self.gate_open and (
            not self.uncertain_action_supported
            or self.current_has_immediate_win
            or self.current_has_confirmed_ko
            or self.current_has_confirmed_prize_gain
        ):
            raise ValueError("invalid_open_phase4_gate")


@dataclass(frozen=True)
class _DirectAttackCanonicalOutcome:
    confirmed_loss: bool
    my_prizes_left_after_candidate: int
    opponent_prizes_left_after_reply: int
    projected_active_survives_confirmed_reply: bool
    has_ready_next_attacker_after_reply: Optional[bool]
    next_attacker_can_ko: Optional[bool]
    next_attacker_confirmed_damage: Optional[int]
    confirmed_damage: int


def _direct_attack_canonical_outcome(
    facts: DirectDecisionOutcomeFacts,
) -> Optional[_DirectAttackCanonicalOutcome]:
    if (
        facts.candidate_wins_game is not False
        or facts.confirmed_loss is None
        or facts.my_prizes_left_after_candidate is None
        or facts.opponent_prizes_left_after_reply is None
        or facts.projected_active_survives_confirmed_reply is None
        or facts.confirmed_damage is None
    ):
        return None

    survives = facts.projected_active_survives_confirmed_reply
    ready = facts.has_ready_next_attacker_after_reply
    can_ko = facts.next_attacker_can_ko
    damage = facts.next_attacker_confirmed_damage
    if not survives:
        if ready is None:
            return None
        if ready and (can_ko is None or damage is None):
            return None

    return _DirectAttackCanonicalOutcome(
        confirmed_loss=facts.confirmed_loss,
        my_prizes_left_after_candidate=facts.my_prizes_left_after_candidate,
        opponent_prizes_left_after_reply=(
            facts.opponent_prizes_left_after_reply
        ),
        projected_active_survives_confirmed_reply=survives,
        has_ready_next_attacker_after_reply=ready,
        next_attacker_can_ko=can_ko,
        next_attacker_confirmed_damage=damage,
        confirmed_damage=facts.confirmed_damage,
    )


def classify_direct_attack_candidate(
    facts: DirectDecisionOutcomeFacts,
) -> DirectAttackCandidateState:
    if not facts.supported:
        return DirectAttackCandidateState.OVERALL_UNSUPPORTED
    if facts.candidate_wins_game is True:
        return DirectAttackCandidateState.TERMINAL_WIN
    if not facts.reply_information_supported:
        return DirectAttackCandidateState.REPLY_UNKNOWN
    if _direct_attack_canonical_outcome(facts) is None:
        return DirectAttackCandidateState.PARTIAL_UNKNOWN
    return DirectAttackCandidateState.FULLY_KNOWN


def _compare_higher_is_better(left: int, right: int) -> int:
    return (left > right) - (left < right)


def _compare_prize_state(
    left: _DirectAttackCanonicalOutcome,
    right: _DirectAttackCanonicalOutcome,
) -> Optional[int]:
    comparisons = (
        _compare_higher_is_better(
            right.my_prizes_left_after_candidate,
            left.my_prizes_left_after_candidate,
        ),
        _compare_higher_is_better(
            left.opponent_prizes_left_after_reply,
            right.opponent_prizes_left_after_reply,
        ),
    )
    directions = {value for value in comparisons if value != 0}
    if len(directions) > 1:
        return None
    return next(iter(directions), 0)


def _compare_continuation_state(
    left: _DirectAttackCanonicalOutcome,
    right: _DirectAttackCanonicalOutcome,
) -> Optional[int]:
    left_survives = left.projected_active_survives_confirmed_reply
    right_survives = right.projected_active_survives_confirmed_reply
    if left_survives and right_survives:
        return 0
    if left_survives != right_survives:
        defeated = right if left_survives else left
        if defeated.has_ready_next_attacker_after_reply is False:
            return 1 if left_survives else -1
        return None

    left_ready = left.has_ready_next_attacker_after_reply
    right_ready = right.has_ready_next_attacker_after_reply
    if left_ready is None or right_ready is None:
        return None
    if left_ready != right_ready:
        return 1 if left_ready else -1
    if not left_ready:
        return 0

    left_can_ko = left.next_attacker_can_ko
    right_can_ko = right.next_attacker_can_ko
    if left_can_ko is None or right_can_ko is None:
        return None
    if left_can_ko != right_can_ko:
        return 1 if left_can_ko else -1
    if (
        left.next_attacker_confirmed_damage is None
        or right.next_attacker_confirmed_damage is None
    ):
        return None
    return _compare_higher_is_better(
        left.next_attacker_confirmed_damage,
        right.next_attacker_confirmed_damage,
    )


def compare_direct_attack_candidates(
    left: DirectAttackShadowCandidate,
    right: DirectAttackShadowCandidate,
) -> DirectAttackComparisonResult:
    left_state = classify_direct_attack_candidate(left.facts)
    right_state = classify_direct_attack_candidate(right.facts)

    def result(
        relation: DirectAttackComparison,
        reason: DirectAttackComparisonReason,
    ) -> DirectAttackComparisonResult:
        return DirectAttackComparisonResult(
            left_option_index=left.option_index,
            right_option_index=right.option_index,
            relation=relation,
            reason=reason,
            left_state=left_state,
            right_state=right_state,
        )

    left_terminal = left_state == DirectAttackCandidateState.TERMINAL_WIN
    right_terminal = right_state == DirectAttackCandidateState.TERMINAL_WIN
    if left_terminal and right_terminal:
        return result(
            DirectAttackComparison.EQUIVALENT,
            DirectAttackComparisonReason.BOTH_IMMEDIATE_WIN,
        )
    if left_terminal:
        return result(
            DirectAttackComparison.LEFT_BETTER,
            DirectAttackComparisonReason.LEFT_IMMEDIATE_WIN,
        )
    if right_terminal:
        return result(
            DirectAttackComparison.RIGHT_BETTER,
            DirectAttackComparisonReason.RIGHT_IMMEDIATE_WIN,
        )

    states = {left_state, right_state}
    if DirectAttackCandidateState.OVERALL_UNSUPPORTED in states:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.OVERALL_UNSUPPORTED,
        )
    if DirectAttackCandidateState.REPLY_UNKNOWN in states:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.REPLY_UNKNOWN,
        )
    if DirectAttackCandidateState.PARTIAL_UNKNOWN in states:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.PARTIAL_UNKNOWN,
        )
    if states != {DirectAttackCandidateState.FULLY_KNOWN}:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.INSUFFICIENT_INFORMATION,
        )

    left_canonical = _direct_attack_canonical_outcome(left.facts)
    right_canonical = _direct_attack_canonical_outcome(right.facts)
    if left_canonical is None or right_canonical is None:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.INSUFFICIENT_INFORMATION,
        )

    if left_canonical.confirmed_loss != right_canonical.confirmed_loss:
        if left_canonical.confirmed_loss:
            relation = DirectAttackComparison.RIGHT_BETTER
            reason = DirectAttackComparisonReason.RIGHT_AVOIDS_CONFIRMED_LOSS
        else:
            relation = DirectAttackComparison.LEFT_BETTER
            reason = DirectAttackComparisonReason.LEFT_AVOIDS_CONFIRMED_LOSS
        return result(relation, reason)
    if left_canonical.confirmed_loss:
        return result(
            DirectAttackComparison.EQUIVALENT,
            DirectAttackComparisonReason.BOTH_CONFIRMED_LOSS,
        )

    primary_comparisons = (
        _compare_prize_state(left_canonical, right_canonical),
        _compare_continuation_state(left_canonical, right_canonical),
    )
    if any(value is None for value in primary_comparisons):
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.CONFLICTING_ADVANTAGES,
        )

    directions = {
        value for value in primary_comparisons
        if value is not None and value != 0
    }
    if len(directions) > 1:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.CONFLICTING_ADVANTAGES,
        )

    damage_comparison = _compare_higher_is_better(
        left_canonical.confirmed_damage,
        right_canonical.confirmed_damage,
    )
    if damage_comparison:
        directions.add(damage_comparison)
    if len(directions) > 1:
        return result(
            DirectAttackComparison.INCOMPARABLE,
            DirectAttackComparisonReason.CONFLICTING_ADVANTAGES,
        )
    if not directions:
        return result(
            DirectAttackComparison.EQUIVALENT,
            DirectAttackComparisonReason.SAME_CANONICAL_OUTCOME,
        )
    if directions == {1}:
        relation = DirectAttackComparison.LEFT_BETTER
    else:
        relation = DirectAttackComparison.RIGHT_BETTER
    return result(
        relation,
        DirectAttackComparisonReason.SAFE_DOMINANCE,
    )


def unique_direct_attack_shadow_winner(
    candidates: Sequence[DirectAttackShadowCandidate],
    comparisons: Sequence[DirectAttackComparisonResult],
) -> Optional[DirectAttackShadowCandidate]:
    winners: List[DirectAttackShadowCandidate] = []
    for candidate in candidates:
        relevant = [
            comparison
            for comparison in comparisons
            if candidate.option_index in {
                comparison.left_option_index,
                comparison.right_option_index,
            }
        ]
        if len(relevant) != len(candidates) - 1:
            continue
        has_strict_win = False
        non_losing = True
        for comparison in relevant:
            candidate_is_left = (
                comparison.left_option_index == candidate.option_index
            )
            winning_relation = (
                DirectAttackComparison.LEFT_BETTER
                if candidate_is_left
                else DirectAttackComparison.RIGHT_BETTER
            )
            if comparison.relation == winning_relation:
                has_strict_win = True
            elif comparison.relation != DirectAttackComparison.EQUIVALENT:
                non_losing = False
                break
        if non_losing and has_strict_win:
            winners.append(candidate)
    return winners[0] if len(winners) == 1 else None


class ThreatEvidenceKind(str, Enum):
    CERTAIN = "CERTAIN"
    PUBLICLY_REACHABLE = "PUBLICLY_REACHABLE"
    HIDDEN_DEPENDENT = "HIDDEN_DEPENDENT"


class PublicEffectKind(str, Enum):
    NO_RELEVANT_EFFECT = "NO_RELEVANT_EFFECT"
    DAMAGE_AFFECTING = "DAMAGE_AFFECTING"
    AFTER_DAMAGE_TRIGGERED_EFFECT = "AFTER_DAMAGE_TRIGGERED_EFFECT"
    HP_AFFECTING = "HP_AFFECTING"
    WEAKNESS_RESISTANCE_AFFECTING = "WEAKNESS_RESISTANCE_AFFECTING"
    RETREAT_COST_AFFECTING = "RETREAT_COST_AFFECTING"
    RETREAT_OR_SWITCH_TRIGGERED_EFFECT = "RETREAT_OR_SWITCH_TRIGGERED_EFFECT"
    OTHER_RELEVANT_EFFECT = "OTHER_RELEVANT_EFFECT"
    UNKNOWN = "UNKNOWN"


def normalized_public_effect_text(card_data: Any) -> str:
    return " ".join(
        str(getattr(skill, "text", "") or "")
        for skill in (getattr(card_data, "skills", ()) or ())
    ).replace("\u2019", "'").replace("\xa0", " ").replace("Pok\u00e9mon", "Pokemon").lower()


def split_public_effect_clauses(text: str) -> Tuple[str, ...]:
    return tuple(
        clause.strip(" \t\r\n.,;:")
        for clause in re.split(r"(?:[.!?;]+|\r?\n+)", text)
        if clause.strip(" \t\r\n.,;:")
    )


def public_hp_bonus(card_data: Any) -> Optional[int]:
    text = normalized_public_effect_text(card_data)
    match = re.search(r"\bgets\s+\+(\d+)\s+hp\b", text)
    return int(match.group(1)) if match is not None else None


def public_energy_types(value: Any) -> Tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(value)
    return (value,)


def public_attack_damage_type(
    board: Any,
    attacker: Optional[Pokemon],
    attack: Any,
    attacker_card_id: Optional[int] = None,
) -> Optional[Any]:
    direct_type = getattr(attack, "energyType", None)
    if direct_type is not None:
        return direct_type
    attacker_id = (
        board.pid(attacker)
        if attacker_card_id is None
        else int(attacker_card_id)
    )
    attacker_data = board.data(attacker_id)
    canonical_attacker = CARD_TABLE.get(attacker_id)
    return getattr(
        attacker_data,
        "energyType",
        getattr(canonical_attacker, "energyType", None),
    )


def public_attack_matches_weakness_or_resistance(
    board: Any,
    attacker: Optional[Pokemon],
    target: Optional[Pokemon],
    attack: Any,
    target_card_id: Optional[int] = None,
    attacker_card_id: Optional[int] = None,
) -> Optional[bool]:
    target_id = (
        board.pid(target)
        if target_card_id is None
        else int(target_card_id)
    )
    target_data = board.data(target_id)
    canonical_target = CARD_TABLE.get(target_id)
    weakness = getattr(
        target_data,
        "weakness",
        getattr(canonical_target, "weakness", None),
    )
    resistance = getattr(
        target_data,
        "resistance",
        getattr(canonical_target, "resistance", None),
    )
    modifiers = public_energy_types(weakness) + public_energy_types(resistance)
    if not modifiers:
        return False
    attack_type = public_attack_damage_type(
        board,
        attacker,
        attack,
        attacker_card_id=attacker_card_id,
    )
    if attack_type is None:
        return None
    return attack_type in modifiers


def classify_public_effect(card_data: Any) -> Tuple[PublicEffectKind, ...]:
    if card_data is None or getattr(card_data, "cardType", None) not in {
        CardType.STADIUM,
        CardType.TOOL,
    }:
        return (PublicEffectKind.UNKNOWN,)
    text = normalized_public_effect_text(card_data)
    if not text:
        return (PublicEffectKind.UNKNOWN,)

    def classify_clause(clause: str) -> Tuple[PublicEffectKind, ...]:
        def fullmatches(*patterns: str) -> bool:
            return any(re.fullmatch(pattern, clause) is not None for pattern in patterns)

        after_damage_triggered = fullmatches(
            r"if (?:the pokemon this card is attached to|the attached pokemon|"
            r"this pokemon) is in the active spot and is damaged by an attack "
            r"from your opponent's pokemon "
            r"\(even if (?:this|that) pokemon is knocked out\), move an energy "
            r"from the attacking pokemon to (?:1|one) of your opponent's "
            r"benched pokemon",
        )
        if after_damage_triggered:
            return (PublicEffectKind.AFTER_DAMAGE_TRIGGERED_EFFECT,)

        clause_kinds: List[PublicEffectKind] = []
        if re.search(r"\bgets\s+\+\d+\s+hp\b", clause) or "maximum hp" in clause:
            clause_kinds.append(PublicEffectKind.HP_AFFECTING)
        if "weakness" in clause or "resistance" in clause:
            clause_kinds.append(PublicEffectKind.WEAKNESS_RESISTANCE_AFFECTING)
        if (
            "retreat cost" in clause
            or "can't retreat" in clause
            or "cannot retreat" in clause
        ):
            clause_kinds.append(PublicEffectKind.RETREAT_COST_AFFECTING)

        transition_words = (
            "retreats",
            "retreated",
            "switch",
            "moves from the active spot to the bench",
            "moved from the active spot to the bench",
            "moves from active to the bench",
            "moved from active to the bench",
            "moves from the bench to the active spot",
            "moved from the bench to the active spot",
            "becomes active",
            "became active",
        )
        transition_triggers = ("when ", "whenever ", "after ", "if ", "each time ")
        separate_switch_action = (
            ("may switch" in clause or "can switch" in clause)
            and "active" in clause
            and "benched" in clause
            and not any(trigger in clause for trigger in transition_triggers)
        )
        if (
            any(word in clause for word in transition_words)
            and any(trigger in clause for trigger in transition_triggers)
        ):
            clause_kinds.append(
                PublicEffectKind.RETREAT_OR_SWITCH_TRIGGERED_EFFECT
            )

        damage_markers = (
            "more damage",
            "less damage",
            "damage done",
            "damage from attacks",
            "do damage",
            "does damage",
            "take damage",
            "takes damage",
        )
        if any(marker in clause for marker in damage_markers):
            clause_kinds.append(PublicEffectKind.DAMAGE_AFFECTING)

        other_relevant_markers = (
            "damage counter",
            "can't attack",
            "cannot attack",
            "attack cost",
            "attacks cost",
            "is now asleep",
            "is now burned",
            "is now confused",
            "is now paralyzed",
            "is now poisoned",
            "prevent all effects of attacks",
            "heal ",
            "heals ",
            "knocked out",
            "prize card",
            "prize cards",
        )
        if any(marker in clause for marker in other_relevant_markers):
            clause_kinds.append(PublicEffectKind.OTHER_RELEVANT_EFFECT)
        ambiguous_effect_markers = (
            "mysterious",
            "unknown effect",
            "unexplained",
            "change what happens",
            "changes what happens",
            "special effect",
            "other effect",
        )
        if any(marker in clause for marker in ambiguous_effect_markers):
            clause_kinds.append(PublicEffectKind.UNKNOWN)
        if clause_kinds:
            fully_supported = fullmatches(
                r"(?:the pokemon this card is attached to|the attached pokemon|"
                r"this pokemon) gets \+\d+ hp",
                r"(?:your|your opponent's) pokemon's attacks do \d+ "
                r"(?:more|less) damage",
                r"attacks used by the pokemon this card is attached to do \d+ "
                r"(?:more|less) damage to the opponent's active pokemon",
                r"\{[a-z]\} pokemon \(both yours and your opponent's\) take "
                r"\d+ less damage from attacks from the opponent's pokemon "
                r"\(after applying weakness and resistance\)",
                r"the retreat cost of (?:the pokemon this card is attached to|"
                r"the attached pokemon|this pokemon) is (?:\{[a-z]\}|\d+) less",
                r"(?:the attached pokemon|this pokemon|the opponent's active "
                r"pokemon) (?:can't|cannot) retreat",
                r"(?:when|whenever|after|each time) .+ "
                r"(?:retreats|is switched|moves from the active spot to the bench|"
                r"moves from the bench to the active spot|becomes active), "
                r"put \d+ damage counters? on (?:it|that pokemon)",
                r"heal \d+ damage from (?:the attached pokemon|this pokemon)",
                r"(?:it|the attached pokemon|this pokemon) (?:can't|cannot) "
                r"attack during your next turn",
                r"when (?:the attached pokemon|this pokemon) is knocked out, "
                r"(?:your opponent|the opponent) takes? \d+ fewer prize cards?",
            )
            if not fully_supported:
                clause_kinds.append(PublicEffectKind.UNKNOWN)
            return tuple(dict.fromkeys(clause_kinds))

        draw_only = re.fullmatch(
            r"(?:(?:once|when|whenever|at|after|before) [^,]+,\s*)?"
            r"(?:(?:that player|each player|you|your opponent) "
            r"(?:may |can )?)?"
            r"draw (?:up to )?(?:a|an|one|\d+) cards?",
            clause,
        )
        switch_only = re.fullmatch(
            r"once during each player's turn, that player may switch their "
            r"active (?:\{[a-z]\} )?pokemon with 1 of their benched "
            r"(?:\{[a-z]\} )?pokemon",
            clause,
        )
        search_to_hand_only = re.fullmatch(
            r"(?:(?:once|when|whenever|at|after|before) [^,]+,\s*)?"
            r"(?:(?:that player|each player|you|your opponent) "
            r"(?:may |can )?)?"
            r"search (?:their|your) deck for .+, reveal it, and put it into "
            r"(?:their|your) hand",
            clause,
        )
        shuffle_only = re.fullmatch(
            r"(?:then, )?(?:that player|each player|you|your opponent) "
            r"shuffles? (?:their|your) deck",
            clause,
        )
        if (
            (separate_switch_action and switch_only is not None)
            or draw_only is not None
            or search_to_hand_only is not None
            or shuffle_only is not None
        ):
            return (PublicEffectKind.NO_RELEVANT_EFFECT,)
        return (PublicEffectKind.UNKNOWN,)

    clauses = split_public_effect_clauses(text)
    if not clauses:
        return (PublicEffectKind.UNKNOWN,)
    kinds = [
        kind
        for clause in clauses
        for kind in classify_clause(clause)
    ]
    return tuple(dict.fromkeys(kinds))


class PublicRetreatStatus(str, Enum):
    PAYABLE = "PAYABLE"
    NOT_PAYABLE = "NOT_PAYABLE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class PublicRetreatEvaluation:
    status: PublicRetreatStatus
    effective_cost: Optional[int]
    attached_energy_count: int
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class OpponentThreatFact:
    attacker_serial: Optional[int]
    attacker_card_id: int
    attack_id: int
    attack_name: str
    evidence_kind: ThreatEvidenceKind
    can_attack_with_current_energy: bool
    estimated_damage: Optional[int]
    can_ko_our_active: bool
    prizes_if_ko: int
    wins_game_if_ko: bool
    unsupported_reason: Optional[str] = None


@dataclass(frozen=True)
class OpponentPublicThreat:
    certain_active_threats: Tuple[OpponentThreatFact, ...] = ()
    publicly_reachable_bench_threats: Tuple[OpponentThreatFact, ...] = ()
    best_certain_damage: int = 0
    certain_active_can_ko: bool = False
    certain_active_prizes_if_ko: int = 0
    certain_active_wins_game: bool = False
    has_hidden_dependent_risk: bool = False
    hidden_dependent_reasons: Tuple[str, ...] = ()
    public_retreat: PublicRetreatEvaluation = PublicRetreatEvaluation(
        status=PublicRetreatStatus.NOT_PAYABLE,
        effective_cost=None,
        attached_energy_count=0,
        unsupported_reason="not_evaluated",
    )
    unsupported_public_threats: Tuple[OpponentThreatFact, ...] = ()


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
        self.used_supporter_id_this_turn = (
            _current_turn_supporter_from_observation(obs)
        )
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

    def setup_window_open(self) -> bool:
        return self.select.context in {
            SelectContext.SETUP_ACTIVE_POKEMON,
            SelectContext.SETUP_BENCH_POKEMON,
        }

    def cinderace_setup_role_live(self) -> bool:
        return self.setup_window_open()

    def ultra_ball_target_facts(
        self,
        cid: Optional[int],
        *,
        visible_search_candidate: bool = False,
    ) -> Optional[UltraBallTargetFacts]:
        if cid is None or not self.is_pokemon(cid):
            return None
        searchable = visible_search_candidate or (
            self.remaining_deck_count() > 0 and self.remaining_possible(cid)
        )
        setup_window_open = self.setup_window_open()
        setup_role_live = cid == CINDERACE and self.cinderace_setup_role_live()
        same_turn_deployable = self.is_basic_pokemon(cid) and self.bench_space > 0
        evolution_base_in_play = any(
            self.card_evolves_from_card(cid, self.pid(pokemon))
            for pokemon in self.all_my_pokemon
        )
        duplicate_in_hand = cid in self.hand_ids
        duplicate_in_play = self.count_in_play(cid) > 0
        role = "no_current_role"
        useful = False
        development_value = 0.0
        if not searchable:
            role = "not_searchable"
        elif cid == CINDERACE:
            role = "setup_role_live" if setup_role_live else "setup_window_closed"
            useful = setup_role_live
            development_value = 1.0 if useful else 0.0
        elif evolution_base_in_play and not duplicate_in_hand:
            role = "current_evolution_needed"
            useful = True
            development_value = 3.0
        elif (
            cid in {HITODEMAN, YUKIWARASHI}
            and same_turn_deployable
            and not duplicate_in_hand
            and not duplicate_in_play
        ):
            role = "deployable_evolution_base"
            useful = True
            development_value = 2.5 if cid == HITODEMAN else 2.0
        elif (
            cid == SHAYMIN
            and same_turn_deployable
            and not duplicate_in_hand
            and not duplicate_in_play
            and self.needs_shaymin_bench_guard()
        ):
            role = "bench_damage_guard"
            useful = True
            development_value = 3.0
        return UltraBallTargetFacts(
            target_id=cid,
            legal=True,
            searchable=searchable,
            setup_window_open=setup_window_open,
            setup_role_live=setup_role_live,
            same_turn_deployable=same_turn_deployable,
            evolution_base_in_play=evolution_base_in_play,
            duplicate_in_hand=duplicate_in_hand,
            duplicate_in_play=duplicate_in_play,
            role=role,
            useful=useful,
            development_value=development_value,
        )

    def ultra_ball_target_facts_in_deck(self) -> Tuple[UltraBallTargetFacts, ...]:
        facts = []
        for cid in dict.fromkeys(DECK):
            target = self.ultra_ball_target_facts(cid)
            if target is not None and target.searchable:
                facts.append(target)
        return tuple(facts)

    def useful_ultra_ball_targets(self) -> Tuple[UltraBallTargetFacts, ...]:
        return tuple(
            facts
            for facts in self.ultra_ball_target_facts_in_deck()
            if facts.useful
        )

    def has_deployable_basic_play_option(self) -> bool:
        if self.bench_space <= 0:
            return False
        return any(
            self.is_basic_pokemon(cid) and cid != CINDERACE
            for cid in self.hand_ids
        ) or any(
            option.type == OptionType.PLAY
            and self.is_basic_pokemon(self.option_card(option))
            and self.option_card(option) != CINDERACE
            for _, option in self.iter_options()
        )

    def live_turbo_flare_receiver_count(self) -> int:
        count = 0
        for pokemon in self.bench:
            cid = self.pid(pokemon)
            if cid not in MAIN_LINE or self.energy_count(pokemon) >= 3:
                continue
            evolution_id = {
                HITODEMAN: MEGA_STARMIE_EX,
                YUKIWARASHI: MEGA_YUKIMENOKO_EX,
            }.get(cid)
            if evolution_id is None or (
                evolution_id in self.hand_ids
                or self.visible_or_unknown_in_deck(evolution_id)
            ):
                count += 1
        return count

    def poke_pad_pipeline_state(self, cid: int) -> str:
        evolution_id = {
            HITODEMAN: MEGA_STARMIE_EX,
            YUKIWARASHI: MEGA_YUKIMENOKO_EX,
        }.get(cid)
        line_ids = {cid}
        if evolution_id is not None:
            line_ids.add(evolution_id)
        line = [
            pokemon
            for pokemon in self.all_my_pokemon
            if self.pid(pokemon) in line_ids
        ]
        if not line:
            return "none"
        if any(self.role_facts(pokemon).attack_ready for pokemon in line):
            return "attack_ready"
        if any(self.energy_count(pokemon) > 0 for pokemon in line):
            return "attack_pipeline_started"
        if evolution_id is not None and (
            evolution_id in self.hand_ids
            or self.visible_or_unknown_in_deck(evolution_id)
        ):
            return "evolution_base_available"
        return "bench_presence_only"

    def poke_pad_target_facts(
        self,
        cid: Optional[int],
        *,
        visible_search_candidate: bool = False,
    ) -> Optional[PokePadTargetFacts]:
        if cid is None or not self.is_poke_pad_target(cid):
            return None
        searchable = visible_search_candidate or (
            self.remaining_deck_count() > 0 and self.remaining_possible(cid)
        )
        basic = self.is_basic_pokemon(cid)
        same_turn_deployable = basic and self.bench_space > 0
        duplicate_in_hand = cid in self.hand_ids
        duplicate_in_play = self.count_in_play(cid) > 0
        evolution_id = {
            HITODEMAN: MEGA_STARMIE_EX,
            YUKIWARASHI: MEGA_YUKIMENOKO_EX,
        }.get(cid)
        evolution_demand = self.hand_ids.count(evolution_id) if evolution_id is not None else 0
        base_supply = (
            self.hand_ids.count(cid) + self.count_in_play(cid)
            if evolution_id is not None
            else 0
        )
        active_only_board = len(self.all_my_pokemon) == 1
        board_out_buffer = (
            active_only_board
            and same_turn_deployable
            and not duplicate_in_hand
            and not self.has_deployable_basic_play_option()
        )
        evolution_line_shortage = (
            evolution_id is not None
            and evolution_demand > base_supply
        )
        turbo_flare_route_live = (
            self.cinderace_can_accelerate()
            and (
                self.basic_energy_remaining_possible(BASIC_WATER_ENERGY)
                or self.basic_energy_remaining_possible(BASIC_DARK_ENERGY)
            )
        )
        turbo_flare_energy_target = (
            evolution_id is not None
            and same_turn_deployable
            and not duplicate_in_hand
            and turbo_flare_route_live
            and self.live_turbo_flare_receiver_count() < 2
            and (
                evolution_id in self.hand_ids
                or self.visible_or_unknown_in_deck(evolution_id)
            )
        )
        current_pipeline_state = (
            self.poke_pad_pipeline_state(cid)
            if evolution_id is not None
            else "none"
        )
        reachable_pipeline_state = current_pipeline_state
        if turbo_flare_energy_target:
            reachable_pipeline_state = "attack_pipeline_started"
        elif evolution_line_shortage:
            reachable_pipeline_state = "evolution_base_available"
        elif board_out_buffer:
            reachable_pipeline_state = "bench_presence_only"
        same_turn_attack_preserved = False
        role = "no_current_role"
        useful = False
        development_value = 0.0
        if cid == CINDERACE:
            role = "setup_window_closed"
        elif not searchable:
            role = "not_searchable"
        elif not same_turn_deployable:
            role = "bench_unavailable"
        elif cid == SHAYMIN:
            role = "bench_damage_guard"
            useful = (
                self.needs_shaymin_bench_guard()
                and not duplicate_in_hand
                and not duplicate_in_play
            )
            development_value = 4.0 if useful else 0.0
        elif evolution_id is not None:
            if turbo_flare_energy_target:
                role = "turbo_flare_attack_pipeline"
                useful = True
                development_value = 3.0
                if cid == HITODEMAN and self.wants_starmie_axis():
                    development_value += 0.25
            elif evolution_line_shortage:
                role = "evolution_line_shortage"
                useful = True
                development_value = 2.0 + min(
                    0.5,
                    0.1 * (evolution_demand - base_supply),
                )
            elif board_out_buffer:
                role = "board_out_buffer"
                useful = True
                development_value = 1.0
        same_turn_attack_preserved = (
            useful
            and bool(self.legal_attack_options())
        )
        return PokePadTargetFacts(
            target_id=cid,
            searchable=searchable,
            same_turn_deployable=same_turn_deployable,
            duplicate_in_hand=duplicate_in_hand,
            duplicate_in_play=duplicate_in_play,
            evolution_demand=evolution_demand,
            base_supply=base_supply,
            active_only_board=active_only_board,
            board_out_buffer=board_out_buffer,
            evolution_line_shortage=evolution_line_shortage,
            turbo_flare_route_live=turbo_flare_route_live,
            turbo_flare_energy_target=turbo_flare_energy_target,
            current_pipeline_state=current_pipeline_state,
            reachable_pipeline_state=reachable_pipeline_state,
            same_turn_attack_preserved=same_turn_attack_preserved,
            development_value=development_value,
            role=role,
            useful=useful,
        )

    def poke_pad_target_facts_in_deck(self) -> Tuple[PokePadTargetFacts, ...]:
        facts = []
        for cid in dict.fromkeys(DECK):
            target = self.poke_pad_target_facts(cid)
            if target is not None and target.searchable:
                facts.append(target)
        return tuple(facts)

    def useful_poke_pad_targets(self) -> Tuple[PokePadTargetFacts, ...]:
        return tuple(facts for facts in self.poke_pad_target_facts_in_deck() if facts.useful)

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
        pokemon_data = self.data(card_id)
        for cid in self.energies(pokemon):
            energy_tokens = attached_energy_tokens_for_card(
                self.data(cid),
                pokemon_data,
            )
            if energy_tokens is not None:
                tokens.extend(energy_tokens)
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
        if self.pid(self.active) != CINDERACE:
            return False
        if any(attack.attackId == TURBO_FLARE for attack in self.legal_attack_options()):
            return True
        turbo_flare = self.attack(TURBO_FLARE)
        return bool(
            turbo_flare is not None
            and active_can_declare_attack_this_turn_for_board(self)
            and self.can_pay_attack(self.active, turbo_flare)
        )

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
        return any(
            getattr(pokemon, "tools", [])
            for pokemon in self.all_opp_pokemon
        )

    def _tool_scrapper_selection_key(
        self,
    ) -> Tuple[int, int, Optional[int]]:
        effect = getattr(self.select, "effect", None)
        return (
            safe_int(getattr(self.state, "turn", None), -1),
            self.my_index,
            getattr(effect, "serial", None),
        )

    def _sync_tool_scrapper_selection_tracking(self) -> None:
        global _TRACKED_TOOL_SCRAPPER_SELECTION_KEY
        selection_key = self._tool_scrapper_selection_key()
        if selection_key != _TRACKED_TOOL_SCRAPPER_SELECTION_KEY:
            _TRACKED_TOOL_SCRAPPER_SELECTION_KEY = selection_key
            _TRACKED_TOOL_SCRAPPER_TOOL_KEYS.clear()

    def _tool_scrapper_option_key(
        self,
        option: Any,
    ) -> Optional[Tuple[int, Optional[int], Optional[int], int]]:
        target = self.option_target(option)
        tool_index = getattr(option, "toolIndex", None)
        if (
            target is None
            or tool_index is None
            or not 0 <= int(tool_index) < len(getattr(target, "tools", []))
        ):
            return None
        tool = target.tools[int(tool_index)]
        owner_index = safe_int(
            getattr(option, "playerIndex", None),
            self.my_index if target in self.all_my_pokemon else self.opp_index,
        )
        return (
            owner_index,
            getattr(target, "serial", None),
            getattr(tool, "serial", None),
            int(tool_index),
        )

    def tool_scrapper_target_facts(
        self,
        option_index: int,
        option: Any,
    ) -> Optional[ToolScrapperTargetFacts]:
        if (
            self.select.context != SelectContext.DISCARD_TOOL_CARD
            or card_id(self.select.effect) != TOOL_SCRAPPER
            or option.type != OptionType.TOOL_CARD
        ):
            return None
        target = self.option_target(option)
        key = self._tool_scrapper_option_key(option)
        if target is None or key is None:
            return None
        tool_index = int(option.toolIndex)
        tool = target.tools[tool_index]
        owner_index = key[0]
        self._sync_tool_scrapper_selection_tracking()
        duplicate_of_earlier_option = any(
            previous_index < option_index
            and self._tool_scrapper_option_key(previous_option) == key
            for previous_index, previous_option in self.iter_options()
        )
        return ToolScrapperTargetFacts(
            option_index=option_index,
            owner_index=owner_index,
            target_id=self.pid(target),
            target_serial=getattr(target, "serial", None),
            tool_index=tool_index,
            tool_id=int(tool.id),
            tool_serial=getattr(tool, "serial", None),
            attached_to_opponent=(
                owner_index == self.opp_index
                and target in self.all_opp_pokemon
            ),
            currently_attached=any(
                candidate is tool
                for candidate in getattr(target, "tools", [])
            ),
            already_selected=(
                key in _TRACKED_TOOL_SCRAPPER_TOOL_KEYS
                or duplicate_of_earlier_option
            ),
        )

    def record_tool_scrapper_selections(
        self,
        selected_indices: Sequence[int],
    ) -> None:
        if (
            self.select.context != SelectContext.DISCARD_TOOL_CARD
            or card_id(self.select.effect) != TOOL_SCRAPPER
        ):
            return
        self._sync_tool_scrapper_selection_tracking()
        for option_index in selected_indices:
            if not 0 <= option_index < len(self.select.option or []):
                continue
            option = self.select.option[option_index]
            key = self._tool_scrapper_option_key(option)
            if key is not None:
                _TRACKED_TOOL_SCRAPPER_TOOL_KEYS.add(key)

    def confirmed_opp_active_damage_for_survival_tool(self) -> Optional[int]:
        threat = OpponentPublicThreatEvaluator.evaluate(self)
        if any(
            fact.unsupported_reason is not None
            for fact in threat.certain_active_threats
        ):
            return None
        return threat.best_certain_damage

    def hero_cape_target_roi(self, pokemon: Optional[Pokemon]) -> str:
        if (
            pokemon is None
            or not any(candidate is pokemon for candidate in self.all_my_pokemon)
            or getattr(pokemon, "tools", [])
        ):
            return "invalid"
        incoming_damage = (
            self.confirmed_opp_active_damage_for_survival_tool()
            if pokemon is self.active
            else 0
        )
        if incoming_damage is None:
            return "incoming_damage_unconfirmed"
        if incoming_damage <= 0:
            return "no_current_damage"
        current_hp = hp_left(pokemon)
        hp_bonus = public_hp_bonus(self.data(HERO_CAPE))
        if hp_bonus is None or hp_bonus <= 0:
            return "invalid"
        if incoming_damage < current_hp:
            return "no_clear_benefit"
        if incoming_damage < current_hp + hp_bonus:
            return "prevents_active_knockout"
        return "cape_still_knocked_out"

    def hand_card_activity(self, cid: int, occurrence: int = 1, total_count: int = 1) -> str:
        if cid == CINDERACE:
            return (
                HAND_ACTIVITY_LIVE_NOW
                if occurrence == 1 and self.cinderace_setup_role_live()
                else HAND_ACTIVITY_LOW
            )
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
            return HAND_ACTIVITY_LIVE_NOW if self.useful_poke_pad_targets() else HAND_ACTIVITY_LOW
        if cid == POFIN:
            return HAND_ACTIVITY_LIVE_NOW if self.bench_space > 0 and self.needs_basic() else HAND_ACTIVITY_LOW
        if cid == ULTRA_BALL:
            return (
                HAND_ACTIVITY_LIVE_NOW
                if len(self.hand_ids) >= 3 and self.useful_ultra_ball_targets()
                else HAND_ACTIVITY_KEEP
            )
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


class OpponentPublicThreatEvaluator:
    """Build public-information-only opponent threat facts without mutation.

    CERTAIN uses only the currently public Active and its attached Energy.
    PUBLICLY_REACHABLE additionally permits a publicly payable Retreat into a
    currently powered Bench attacker, but does not claim that transition was
    simulated. HIDDEN_DEPENDENT is represented only as an unquantified risk;
    hidden card identities are never inspected or invented here.
    """

    _SUPPORTED_ENERGY_REQUIREMENTS = frozenset(
        {
            EnergyType.COLORLESS,
            EnergyType.GRASS,
            EnergyType.FIRE,
            EnergyType.WATER,
            EnergyType.LIGHTNING,
            EnergyType.PSYCHIC,
            EnergyType.FIGHTING,
            EnergyType.DARKNESS,
            EnergyType.METAL,
        }
    )

    def __init__(
        self,
        board: BoardView,
        projected_active: Optional[CandidateProjectionFacts] = None,
        projected_our_active: Optional[ProjectedActivePublicFacts] = None,
    ):
        self.b = board
        self.projected_active = projected_active
        self.projected_our_active = projected_our_active

    @classmethod
    def evaluate(cls, board: BoardView) -> OpponentPublicThreat:
        return cls(board)._evaluate()

    @classmethod
    def evaluate_projected_facts(
        cls,
        board: BoardView,
        projection: CandidateProjectionFacts,
        opponent_active: Optional[ProjectedActivePublicFacts] = None,
    ) -> OpponentPublicThreatFacts:
        if not projection.supported:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="candidate_projection_unsupported",
            )
        if projection.terminal_win:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="terminal_win",
            )
        if projection.opponent_active_ko:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="opponent_promotion_required",
            )
        if (
            projection.projected_active_card_id is None
            or projection.projected_active_hp is None
        ):
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="missing_projected_active",
            )
        if opponent_active is None and board.opp_active is None:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="missing_current_opponent_active",
            )

        evaluator = cls(board, projected_active=projection)
        candidates = tuple(
            evaluator._attack_facts(
                board.opp_active,
                ThreatEvidenceKind.CERTAIN,
                active_position=True,
            )
            if opponent_active is None
            else evaluator._attack_facts_from_public_active(
                opponent_active,
                ThreatEvidenceKind.CERTAIN,
                active_position=True,
            )
        )
        return evaluator._projected_threat_facts(candidates)

    @classmethod
    def evaluate_public_active_facts(
        cls,
        board: BoardView,
        our_active: ProjectedActivePublicFacts,
        opponent_active: Optional[ProjectedActivePublicFacts],
        *,
        terminal_win: bool,
        opponent_active_ko: bool,
    ) -> OpponentPublicThreatFacts:
        if terminal_win:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="terminal_win",
            )
        if opponent_active_ko:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="opponent_promotion_required",
            )
        if opponent_active is None:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=0,
                can_ko_projected_active=False,
                prizes_lost=0,
                usable_attack_ids=(),
                unsupported_reason="missing_current_opponent_active",
            )
        evaluator = cls(board, projected_our_active=our_active)
        candidates = tuple(
            evaluator._attack_facts_from_public_active(
                opponent_active,
                ThreatEvidenceKind.CERTAIN,
                active_position=True,
            )
        )
        return evaluator._projected_threat_facts(candidates)

    def _projected_threat_facts(
        self,
        candidates: Tuple[OpponentThreatFact, ...],
    ) -> OpponentPublicThreatFacts:
        payable = tuple(
            fact for fact in candidates
            if fact.can_attack_with_current_energy
        )
        unsupported = tuple(
            fact
            for fact in candidates
            if fact.unsupported_reason is not None
        )
        confirmed = tuple(
            fact
            for fact in payable
            if fact.unsupported_reason is None
            and fact.estimated_damage is not None
        )
        if unsupported:
            return OpponentPublicThreatFacts(
                supported=False,
                best_confirmed_damage=max(
                    (safe_int(fact.estimated_damage) for fact in confirmed),
                    default=0,
                ),
                can_ko_projected_active=any(
                    fact.can_ko_our_active for fact in confirmed
                ),
                prizes_lost=max(
                    (fact.prizes_if_ko for fact in confirmed),
                    default=0,
                ),
                usable_attack_ids=tuple(
                    fact.attack_id for fact in confirmed
                ),
                unsupported_reason=unsupported[0].unsupported_reason,
            )
        return OpponentPublicThreatFacts(
            supported=True,
            best_confirmed_damage=max(
                (safe_int(fact.estimated_damage) for fact in confirmed),
                default=0,
            ),
            can_ko_projected_active=any(
                fact.can_ko_our_active for fact in confirmed
            ),
            prizes_lost=max(
                (fact.prizes_if_ko for fact in confirmed),
                default=0,
            ),
            usable_attack_ids=tuple(
                fact.attack_id for fact in confirmed
            ),
            unsupported_reason=None,
        )

    def _evaluate(self) -> OpponentPublicThreat:
        active_candidates = tuple(
            self._attack_facts(
                self.b.opp_active,
                ThreatEvidenceKind.CERTAIN,
                active_position=True,
            )
        )
        active_facts = tuple(
            fact
            for fact in active_candidates
            if fact.can_attack_with_current_energy
        )
        public_retreat = self._public_retreat_evaluation()
        bench_candidates: Tuple[OpponentThreatFact, ...] = ()
        if public_retreat.status == PublicRetreatStatus.PAYABLE:
            bench_candidates = tuple(
                fact
                for attacker in self.b.opp_bench
                for fact in self._attack_facts(
                    attacker,
                    ThreatEvidenceKind.PUBLICLY_REACHABLE,
                    active_position=False,
                )
            )
        bench_facts = tuple(
            fact
            for fact in bench_candidates
            if fact.can_attack_with_current_energy
        )

        supported_certain = tuple(
            fact
            for fact in active_facts
            if fact.unsupported_reason is None
        )
        certain_kos = tuple(fact for fact in supported_certain if fact.can_ko_our_active)
        unsupported = tuple(
            fact
            for fact in active_candidates + bench_candidates
            if fact.unsupported_reason is not None
        )
        hidden_reasons = self._hidden_dependent_reasons(public_retreat)
        return OpponentPublicThreat(
            certain_active_threats=active_facts,
            publicly_reachable_bench_threats=bench_facts,
            best_certain_damage=max(
                (safe_int(fact.estimated_damage) for fact in supported_certain),
                default=0,
            ),
            certain_active_can_ko=bool(certain_kos),
            certain_active_prizes_if_ko=max(
                (fact.prizes_if_ko for fact in certain_kos),
                default=0,
            ),
            certain_active_wins_game=any(
                fact.wins_game_if_ko for fact in certain_kos
            ),
            has_hidden_dependent_risk=bool(hidden_reasons),
            hidden_dependent_reasons=hidden_reasons,
            public_retreat=public_retreat,
            unsupported_public_threats=unsupported,
        )

    def _attacker_card_id(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
    ) -> int:
        if isinstance(attacker, ProjectedActivePublicFacts):
            return attacker.card_id
        return self.b.pid(attacker)

    def _attacker_energy_card_ids(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
    ) -> Tuple[int, ...]:
        if isinstance(attacker, ProjectedActivePublicFacts):
            return attacker.energy_card_ids
        return tuple(self.b.energies(attacker))

    def _attacker_energy_tokens(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
    ) -> Tuple[EnergyToken, ...]:
        if isinstance(attacker, ProjectedActivePublicFacts):
            return attacker.energy_tokens or ()
        return tuple(self.b.energy_tokens(attacker))

    def _attacker_tool_ids(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
    ) -> Tuple[int, ...]:
        if isinstance(attacker, ProjectedActivePublicFacts):
            return attacker.tool_ids
        return tuple(
            safe_int(card_id(public_card), default=-1)
            for public_card in tuple(getattr(attacker, "tools", None) or ())
        )

    def _attacker_status_blocks_attack(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
    ) -> bool:
        if isinstance(attacker, ProjectedActivePublicFacts):
            return attacker.asleep or attacker.paralyzed
        return self._opponent_active_status_blocks_attack()

    def _attacker_confused(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
    ) -> bool:
        if isinstance(attacker, ProjectedActivePublicFacts):
            return attacker.confused
        return bool(getattr(getattr(self.b, "opp", None), "confused", False))

    def _attack_facts(
        self,
        attacker: Optional[Union[Pokemon, ProjectedActivePublicFacts]],
        evidence_kind: ThreatEvidenceKind,
        active_position: bool,
    ) -> Iterable[OpponentThreatFact]:
        if attacker is None:
            return ()
        attacker_card_id = self._attacker_card_id(attacker)
        data = self.b.data(attacker_card_id)
        if data is None:
            return (
                self._fact(
                    attacker,
                    attack=None,
                    evidence_kind=evidence_kind,
                    can_attack=False,
                    damage=None,
                    unsupported_reason="missing_attacker_card_data",
                ),
            )

        facts = []
        attack_timing_blocks = (
            active_position
            and (
                self._attacker_status_blocks_attack(attacker)
                or not self._opponent_can_attack_on_next_turn()
            )
        )
        for attack_id in getattr(data, "attacks", ()) or ():
            attack = self.b.attack(attack_id)
            if attack is None:
                facts.append(
                    self._fact(
                        attacker,
                        attack=None,
                        attack_id=safe_int(attack_id),
                        evidence_kind=evidence_kind,
                        can_attack=False,
                        damage=None,
                        unsupported_reason="missing_attack_data",
                    )
                )
                continue
            energy_reason = self._energy_unsupported_reason(attacker, attack)
            if energy_reason is not None:
                facts.append(
                    self._fact(
                        attacker,
                        attack=attack,
                        evidence_kind=evidence_kind,
                        can_attack=False,
                        damage=None,
                        unsupported_reason=energy_reason,
                    )
                )
                continue
            can_attack = (
                not attack_timing_blocks
                and can_pay_attack_with_tokens(
                    attack,
                    self._attacker_energy_tokens(attacker),
                )
            )
            if not can_attack:
                facts.append(
                    self._fact(
                        attacker,
                        attack=attack,
                        evidence_kind=evidence_kind,
                        can_attack=False,
                        damage=None,
                    )
                )
                continue
            if active_position and bool(
                self._attacker_confused(attacker)
            ):
                facts.append(
                    self._fact(
                        attacker,
                        attack=attack,
                        evidence_kind=evidence_kind,
                        can_attack=True,
                        damage=None,
                        unsupported_reason="opponent_active_confused",
                    )
                )
                continue
            damage, damage_reason = (
                self._certain_damage_from_public_active(attacker, attack)
                if isinstance(attacker, ProjectedActivePublicFacts)
                else self._certain_damage(attacker, attack)
            )
            facts.append(
                self._fact(
                    attacker,
                    attack=attack,
                    evidence_kind=evidence_kind,
                    can_attack=True,
                    damage=damage,
                    unsupported_reason=damage_reason,
                )
            )
        return tuple(facts)

    def _attack_facts_from_public_active(
        self,
        attacker: ProjectedActivePublicFacts,
        evidence_kind: ThreatEvidenceKind,
        active_position: bool,
    ) -> Iterable[OpponentThreatFact]:
        return self._attack_facts(
            attacker,
            evidence_kind,
            active_position,
        )

    def _fact(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
        attack: Optional[Any],
        evidence_kind: ThreatEvidenceKind,
        can_attack: bool,
        damage: Optional[int],
        unsupported_reason: Optional[str] = None,
        attack_id: Optional[int] = None,
    ) -> OpponentThreatFact:
        resolved_attack_id = safe_int(
            attack_id
            if attack_id is not None
            else getattr(attack, "attackId", None),
            default=-1,
        )
        target_hp = self._our_active_hp()
        can_ko = bool(
            can_attack
            and damage is not None
            and unsupported_reason is None
            and target_hp is not None
            and damage >= target_hp
        )
        prizes = self._our_active_prize_value() if can_ko else 0
        opponent_prizes_left = len(getattr(getattr(self.b, "opp", None), "prize", ()) or ())
        return OpponentThreatFact(
            attacker_serial=(
                attacker.serial
                if isinstance(attacker, ProjectedActivePublicFacts)
                else getattr(attacker, "serial", None)
            ),
            attacker_card_id=self._attacker_card_id(attacker),
            attack_id=resolved_attack_id,
            attack_name=str(
                getattr(attack, "name", None)
                or resolved_attack_id
            ),
            evidence_kind=evidence_kind,
            can_attack_with_current_energy=can_attack,
            estimated_damage=damage,
            can_ko_our_active=can_ko,
            prizes_if_ko=prizes,
            wins_game_if_ko=bool(
                can_ko
                and opponent_prizes_left > 0
                and prizes >= opponent_prizes_left
            ),
            unsupported_reason=unsupported_reason,
        )

    def _energy_unsupported_reason(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
        attack: Any,
    ) -> Optional[str]:
        requirements = tuple(getattr(attack, "energies", ()) or ())
        if any(
            requirement not in self._SUPPORTED_ENERGY_REQUIREMENTS
            for requirement in requirements
        ):
            return "unsupported_attack_energy_type"
        attacker_card_id = self._attacker_card_id(attacker)
        for energy_id in self._attacker_energy_card_ids(attacker):
            energy_data = self.b.data(energy_id)
            if attached_energy_tokens_for_card(
                energy_data,
                self.b.data(attacker_card_id),
            ) is None:
                return attached_energy_unsupported_reason(energy_data)
        if (
            isinstance(attacker, ProjectedActivePublicFacts)
            and attacker.energy_tokens is None
        ):
            return "unsupported_attached_energy"
        return None

    def _certain_damage(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
        attack: Any,
    ) -> Tuple[Optional[int], Optional[str]]:
        target = self.b.active
        target_card_id = self._our_active_card_id()
        if target_card_id is None:
            return None, "missing_our_active"
        if self._attack_blocked_by_our_active(attacker, attack):
            return 0, None

        text = _normalized_attack_text(attack)
        variable_markers = (
            "for each",
            "more damage",
            "less damage",
            "times the number",
            "equal to",
            "instead of",
        )
        if (
            any(marker in text for marker in variable_markers)
            or (safe_int(getattr(attack, "damage", 0)) == 0 and "damage" in text)
        ):
            return None, "dynamic_attack_damage_unmodeled"

        public_effect_reason = self._public_damage_effect_unsupported_reason(
            attacker,
        )
        if public_effect_reason is not None:
            return None, public_effect_reason

        target_data = self.b.data(target_card_id)
        if target_data is None:
            return None, "missing_our_active_card_data"
        ignores_weakness_resistance = (
            "isn't affected by weakness or resistance" in text
            or "is not affected by weakness or resistance" in text
        )
        if not ignores_weakness_resistance:
            modifier_match = public_attack_matches_weakness_or_resistance(
                self.b,
                (
                    None
                    if isinstance(attacker, ProjectedActivePublicFacts)
                    else attacker
                ),
                target,
                attack,
                target_card_id=target_card_id,
                attacker_card_id=(
                    attacker.card_id
                    if isinstance(attacker, ProjectedActivePublicFacts)
                    else None
                ),
            )
            if modifier_match is not False:
                return None, "weakness_resistance_damage_unmodeled"

        return self.b.attack_damage_for_card(
            self._attacker_card_id(attacker),
            attack,
        ), None

    def _certain_damage_from_public_active(
        self,
        attacker: ProjectedActivePublicFacts,
        attack: Any,
    ) -> Tuple[Optional[int], Optional[str]]:
        return self._certain_damage(attacker, attack)

    def _public_damage_effect_kind(self, public_card: Any) -> Tuple[PublicEffectKind, ...]:
        return classify_public_effect(self.b.data(card_id(public_card)))

    def _public_damage_effect_unsupported_reason(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
        target: Optional[Pokemon] = None,
    ) -> Optional[str]:
        attacker_tool_ids = self._attacker_tool_ids(attacker)
        target_tool_ids = (
            tuple(
                safe_int(card_id(public_card), default=-1)
                for public_card in tuple(
                    getattr(target, "tools", None) or ()
                )
            )
            if target is not None
            else self._our_active_tool_ids()
        )
        return self._public_damage_effect_unsupported_reason_from_tool_ids(
            attacker_tool_ids,
            target_tool_ids,
        )

    def _public_damage_effect_unsupported_reason_from_tool_ids(
        self,
        attacker_tool_ids: Sequence[int],
        target_tool_ids: Sequence[int],
    ) -> Optional[str]:
        stadium = getattr(getattr(self.b, "state", None), "stadium", None) or ()
        for public_card in stadium:
            kinds = self._public_damage_effect_kind(public_card)
            if PublicEffectKind.DAMAGE_AFFECTING in kinds:
                return "public_stadium_damage_modifier_unmodeled"
            if PublicEffectKind.WEAKNESS_RESISTANCE_AFFECTING in kinds:
                return "public_stadium_weakness_resistance_unmodeled"
            if (
                PublicEffectKind.OTHER_RELEVANT_EFFECT in kinds
                or PublicEffectKind.UNKNOWN in kinds
            ):
                return "public_stadium_damage_effect_unknown"
        public_tool_ids = tuple(attacker_tool_ids) + tuple(target_tool_ids)
        for public_tool_id in public_tool_ids:
            kinds = classify_public_effect(self.b.data(public_tool_id))
            if PublicEffectKind.DAMAGE_AFFECTING in kinds:
                return "public_tool_damage_modifier_unmodeled"
            if PublicEffectKind.WEAKNESS_RESISTANCE_AFFECTING in kinds:
                return "public_tool_weakness_resistance_unmodeled"
            if (
                PublicEffectKind.OTHER_RELEVANT_EFFECT in kinds
                or PublicEffectKind.UNKNOWN in kinds
            ):
                return "public_tool_damage_effect_unknown"
        return None

    def _our_active_card_id(self) -> Optional[int]:
        if self.projected_our_active is not None:
            return self.projected_our_active.card_id
        if self.projected_active is not None:
            return self.projected_active.projected_active_card_id
        return None if self.b.active is None else self.b.pid(self.b.active)

    def _our_active_hp(self) -> Optional[int]:
        if self.projected_our_active is not None:
            return self.projected_our_active.hp
        if self.projected_active is not None:
            return self.projected_active.projected_active_hp
        return None if self.b.active is None else hp_left(self.b.active)

    def _our_active_prize_value(self) -> int:
        if self.projected_our_active is not None:
            data = self.b.data(self.projected_our_active.card_id)
            if data is None:
                return 1
            if getattr(data, "megaEx", False):
                return 3
            if getattr(data, "ex", False):
                return 2
            return 1
        if self.projected_active is not None:
            data = self.b.data(self.projected_active.projected_active_card_id)
            if data is None:
                return 1
            if getattr(data, "megaEx", False):
                return 3
            if getattr(data, "ex", False):
                return 2
            return 1
        return self.b.prize_value(self.b.active)

    def _our_active_tool_ids(self) -> Tuple[int, ...]:
        if self.projected_our_active is not None:
            return self.projected_our_active.tool_ids
        if self.projected_active is not None:
            return self.projected_active.projected_active_tool_ids
        return tuple(
            safe_int(card_id(public_card), default=-1)
            for public_card in tuple(
                getattr(self.b.active, "tools", None) or ()
            )
        )

    def _attack_blocked_by_our_active(
        self,
        attacker: Union[Pokemon, ProjectedActivePublicFacts],
        attack: Any,
    ) -> bool:
        return self._attack_blocked_by_our_active_card(
            self._attacker_card_id(attacker),
            attack,
        )

    def _attack_blocked_by_our_active_card(
        self,
        attacker_card_id: int,
        attack: Any,
    ) -> bool:
        target_card_id = self._our_active_card_id()
        if target_card_id not in EX_ATTACK_WALLS:
            return False
        if self.b.attack_bypasses_ex_wall(attack):
            return False
        attacker_data = self.b.data(attacker_card_id)
        return bool(
            attacker_data is not None
            and (
                getattr(attacker_data, "ex", False)
                or getattr(attacker_data, "megaEx", False)
            )
        )

    def _opponent_active_status_blocks_attack(self) -> bool:
        return active_status_blocks_attack_for_board(
            SimpleNamespace(me=getattr(self.b, "opp", None))
        )

    def _opponent_can_attack_on_next_turn(self) -> bool:
        state = getattr(self.b, "state", None)
        turn = getattr(state, "turn", None)
        first_player = getattr(state, "firstPlayer", None)
        my_index = safe_int(getattr(self.b, "my_index", getattr(state, "yourIndex", 0)))
        opponent_index = safe_int(getattr(self.b, "opp_index", 1 - my_index))
        if turn is None or first_player is None:
            return True
        next_turn = safe_int(turn) + 1
        return not (
            next_turn == 1
            and safe_int(first_player) == opponent_index
        )

    def _public_retreat_effect_unsupported_reason(
        self,
        active: Pokemon,
        incoming: Optional[Pokemon] = None,
    ) -> Optional[str]:
        placements = (
            (
                "stadium",
                tuple(
                    getattr(getattr(self.b, "state", None), "stadium", None)
                    or ()
                ),
            ),
            ("departing_tool", tuple(getattr(active, "tools", None) or ())),
            ("incoming_tool", tuple(getattr(incoming, "tools", None) or ())),
        )
        for placement, public_cards in placements:
            for public_card in public_cards:
                kinds = classify_public_effect(self.b.data(card_id(public_card)))
                if PublicEffectKind.RETREAT_OR_SWITCH_TRIGGERED_EFFECT in kinds:
                    return "public_retreat_or_switch_effect_unmodeled"
                if (
                    placement != "incoming_tool"
                    and PublicEffectKind.RETREAT_COST_AFFECTING in kinds
                ):
                    return "public_retreat_cost_modifier_unmodeled"
                if PublicEffectKind.UNKNOWN in kinds:
                    return f"public_retreat_{placement}_effect_unknown"
        return None

    def _public_retreat_evaluation(self) -> PublicRetreatEvaluation:
        active = self.b.opp_active
        if active is None:
            return PublicRetreatEvaluation(
                PublicRetreatStatus.NOT_PAYABLE,
                None,
                0,
                None,
            )
        attached_energy_count = len(self.b.energies(active))
        attached_energy_units = len(self.b.energy_tokens(active))
        data = self.b.data(self.b.pid(active))
        if data is None:
            return PublicRetreatEvaluation(
                PublicRetreatStatus.UNSUPPORTED,
                None,
                attached_energy_count,
                "missing_opponent_active_card_data",
            )
        cost = ImmediateOutcomeEvaluator(self.b)._effective_retreat_cost(active)
        if not self.b.opp_bench:
            return PublicRetreatEvaluation(
                PublicRetreatStatus.NOT_PAYABLE,
                cost,
                attached_energy_count,
                None,
            )
        if not self._opponent_can_attack_on_next_turn():
            return PublicRetreatEvaluation(
                PublicRetreatStatus.NOT_PAYABLE,
                cost,
                attached_energy_count,
                None,
            )
        if self._opponent_active_status_blocks_attack():
            return PublicRetreatEvaluation(
                PublicRetreatStatus.NOT_PAYABLE,
                cost,
                attached_energy_count,
                None,
            )
        public_effect_reason = self._public_retreat_effect_unsupported_reason(active)
        if public_effect_reason is not None:
            return PublicRetreatEvaluation(
                PublicRetreatStatus.UNSUPPORTED,
                cost,
                attached_energy_count,
                public_effect_reason,
            )
        if cost == 0:
            return PublicRetreatEvaluation(
                PublicRetreatStatus.PAYABLE,
                cost,
                attached_energy_count,
                None,
            )
        for energy_id in self.b.energies(active):
            energy_data = self.b.data(energy_id)
            if attached_energy_tokens_for_card(
                energy_data,
                data,
            ) is None:
                return PublicRetreatEvaluation(
                    PublicRetreatStatus.UNSUPPORTED,
                    cost,
                    attached_energy_count,
                    attached_energy_unsupported_reason(energy_data),
                )
        status = (
            PublicRetreatStatus.PAYABLE
            if attached_energy_units >= cost
            else PublicRetreatStatus.NOT_PAYABLE
        )
        return PublicRetreatEvaluation(
            status,
            cost,
            attached_energy_count,
            None,
        )

    def _active_needs_one_hidden_energy(self) -> bool:
        attacker = self.b.opp_active
        if (
            attacker is None
            or self._opponent_active_status_blocks_attack()
            or not self._opponent_can_attack_on_next_turn()
            or bool(getattr(getattr(self.b, "opp", None), "confused", False))
        ):
            return False
        data = self.b.data(self.b.pid(attacker))
        if data is None:
            return False
        current_tokens = self.b.energy_tokens(attacker)
        for attack_id in getattr(data, "attacks", ()) or ():
            attack = self.b.attack(attack_id)
            if (
                attack is None
                or self._energy_unsupported_reason(attacker, attack) is not None
                or can_pay_attack_with_tokens(attack, current_tokens)
            ):
                continue
            if any(
                can_pay_attack_with_tokens(
                    attack,
                    tuple(current_tokens) + (energy_type,),
                )
                for energy_type in self._SUPPORTED_ENERGY_REQUIREMENTS
            ):
                return True
        return False

    def _hidden_dependent_reasons(
        self,
        public_retreat: PublicRetreatEvaluation,
    ) -> Tuple[str, ...]:
        opponent = getattr(self.b, "opp", None)
        hidden_card_source_exists = bool(
            safe_int(getattr(opponent, "handCount", 0)) > 0
            or safe_int(getattr(opponent, "deckCount", 0)) > 0
        )
        if not hidden_card_source_exists:
            return ()
        reasons = []
        if self._active_needs_one_hidden_energy():
            reasons.append("needs_hidden_energy_attach")
        if (
            public_retreat.status == PublicRetreatStatus.NOT_PAYABLE
            and self._opponent_can_attack_on_next_turn()
        ):
            ready_bench_exists = any(
                fact.can_attack_with_current_energy
                for attacker in self.b.opp_bench
                for fact in self._attack_facts(
                    attacker,
                    ThreatEvidenceKind.PUBLICLY_REACHABLE,
                    active_position=False,
                )
            )
            if ready_bench_exists:
                reasons.append("needs_hidden_switch_effect")
        return tuple(reasons)


def _pokemon_public_snapshot_facts_with_reason(
    board: BoardView,
    pokemon: Optional[Pokemon],
) -> Tuple[Optional[PokemonPublicSnapshotFacts], Optional[str]]:
    if pokemon is None:
        return None, "transition_projected_bench_unresolved"
    pokemon_card_id = board.pid(pokemon)
    pokemon_serial = getattr(pokemon, "serial", None)
    if type(pokemon_card_id) is not int or type(pokemon_serial) is not int:
        return None, "transition_projected_bench_unresolved"

    pokemon_data = board.data(pokemon_card_id)
    attached_energy: List[AttachedEnergyPublicFacts] = []
    for public_card in tuple(getattr(pokemon, "energyCards", None) or ()):
        energy_id = getattr(public_card, "id", None)
        energy_serial = getattr(public_card, "serial", None)
        if type(energy_id) is not int or type(energy_serial) is not int:
            return None, "transition_energy_identity_unresolved"
        tokens = attached_energy_tokens_for_card(
            board.data(energy_id),
            pokemon_data,
        )
        if tokens is None or not tokens:
            return None, "transition_energy_tokens_unresolved"
        try:
            attached_energy.append(
                AttachedEnergyPublicFacts(
                    card_id=energy_id,
                    serial=energy_serial,
                    tokens=tuple(tokens),
                )
            )
        except TypeError:
            return None, "transition_energy_tokens_unresolved"

    attached_tools: List[AttachedToolPublicFacts] = []
    for public_card in tuple(getattr(pokemon, "tools", None) or ()):
        tool_id = getattr(public_card, "id", None)
        tool_serial = getattr(public_card, "serial", None)
        if type(tool_id) is not int or type(tool_serial) is not int:
            return None, "transition_tool_identity_unresolved"
        attached_tools.append(
            AttachedToolPublicFacts(
                card_id=tool_id,
                serial=tool_serial,
            )
        )

    current_hp = hp_left(pokemon)
    current_max_hp = max_hp(pokemon)
    try:
        return PokemonPublicSnapshotFacts(
            card_id=pokemon_card_id,
            serial=pokemon_serial,
            hp=current_hp,
            max_hp=current_max_hp,
            damage_counters=current_max_hp - current_hp,
            attached_energy=tuple(attached_energy),
            attached_tools=tuple(attached_tools),
        ), None
    except ValueError as error:
        if str(error) in {
            "duplicate_attached_energy_serial",
            "duplicate_attached_tool_serial",
            "duplicate_attached_card_serial",
        }:
            return None, "transition_duplicate_attached_card_serial"
        return None, "transition_projected_bench_unresolved"


def pokemon_public_snapshot_facts(
    board: BoardView,
    pokemon: Pokemon,
) -> Optional[PokemonPublicSnapshotFacts]:
    facts, _reason = _pokemon_public_snapshot_facts_with_reason(
        board,
        pokemon,
    )
    return facts


def _active_special_condition_facts(owner: Any) -> ActiveSpecialConditionFacts:
    return ActiveSpecialConditionFacts(
        asleep=bool(getattr(owner, "asleep", False)),
        paralyzed=bool(getattr(owner, "paralyzed", False)),
        confused=bool(getattr(owner, "confused", False)),
        burned=bool(getattr(owner, "burned", False)),
        poisoned=bool(getattr(owner, "poisoned", False)),
    )


def _unsupported_active_bench_transition(
    origin_binding: ActiveBenchTransitionOriginBindingFacts,
    reason: str,
) -> ActiveBenchTransitionFacts:
    return ActiveBenchTransitionFacts(
        supported=False,
        origin_binding=origin_binding,
        target_decision_option_index=None,
        old_active=None,
        old_active_status_before=None,
        new_active=None,
        new_active_status_after=None,
        projected_bench=None,
        bench_count_before=None,
        target_card_id=None,
        target_serial=None,
        target_player_index=None,
        target_original_slot=None,
        status_exact=False,
        transition_exact=False,
        unsupported_reason=reason,
    )


def active_bench_transition_facts(
    board: BoardView,
    *,
    origin_binding: ActiveBenchTransitionOriginBindingFacts,
    target_decision_option_index: int,
    target: Pokemon,
    projected_active_status: ActiveSpecialConditionFacts,
    status_exact: bool,
) -> ActiveBenchTransitionFacts:
    if not origin_binding.supported or not origin_binding.binding_exact:
        return _unsupported_active_bench_transition(
            origin_binding,
            origin_binding.unsupported_reason
            or "transition_origin_binding_unresolved",
        )

    context = getattr(getattr(board, "select", None), "context", None)
    if context in {
        SelectContext.TO_ACTIVE,
        SelectContext.SETUP_ACTIVE_POKEMON,
    }:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_promotion_not_supported",
        )
    if context != SelectContext.SWITCH:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_missing",
        )

    expected_effect_id = origin_binding.expected_switch_effect_id
    effect = getattr(getattr(board, "select", None), "effect", None)
    actual_effect_id = getattr(effect, "id", None)
    if actual_effect_id != expected_effect_id:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_origin_identity_mismatch",
        )

    options = dict(board.iter_options())
    if (
        type(target_decision_option_index) is not int
        or target_decision_option_index not in options
    ):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_missing",
        )
    option = options[target_decision_option_index]
    if (
        getattr(option, "type", None) != OptionType.CARD
        or getattr(option, "area", None) != AreaType.BENCH
    ):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_missing",
        )

    affected_player_index = origin_binding.affected_player_index
    option_player_index = getattr(option, "playerIndex", None)
    if option_player_index != affected_player_index:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_player_mismatch",
        )
    if affected_player_index == getattr(board, "my_index", None):
        affected_active = getattr(board, "active", None)
        affected_bench = tuple(getattr(board, "bench", ()) or ())
        affected_status_owner = getattr(board, "me", None)
    elif affected_player_index == getattr(board, "opp_index", None):
        affected_active = getattr(board, "opp_active", None)
        affected_bench = tuple(getattr(board, "opp_bench", ()) or ())
        affected_status_owner = getattr(board, "opp", None)
    else:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_player_mismatch",
        )
    if affected_active is None:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_old_active_missing",
        )
    if target is None:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_missing",
        )

    identity_slots = tuple(
        slot
        for slot, pokemon in enumerate(affected_bench)
        if pokemon is target
    )
    if len(identity_slots) > 1:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_bench_order_unresolved",
        )
    if not identity_slots:
        target_serial = getattr(target, "serial", None)
        if any(
            getattr(pokemon, "serial", None) == target_serial
            for pokemon in affected_bench
        ):
            reason = "transition_target_identity_mismatch"
        else:
            reason = "transition_target_not_current_bench"
        return _unsupported_active_bench_transition(origin_binding, reason)
    target_original_slot = identity_slots[0]
    option_slot = getattr(option, "index", None)
    if option_slot != target_original_slot:
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_slot_mismatch",
        )

    resolved_target = board.option_target(option)
    if resolved_target is not target:
        if (
            resolved_target is not None
            and getattr(resolved_target, "serial", None)
            != getattr(target, "serial", None)
        ):
            reason = "transition_target_serial_mismatch"
        else:
            reason = "transition_target_identity_mismatch"
        return _unsupported_active_bench_transition(origin_binding, reason)
    if (
        getattr(target, "serial", None) is None
        or board.pid(target) < 0
    ):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_serial_mismatch",
        )

    if not status_exact or not isinstance(
        projected_active_status,
        ActiveSpecialConditionFacts,
    ):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_status_unresolved",
        )

    old_active_facts, old_active_reason = (
        _pokemon_public_snapshot_facts_with_reason(
            board,
            affected_active,
        )
    )
    if old_active_facts is None:
        return _unsupported_active_bench_transition(
            origin_binding,
            old_active_reason or "transition_projected_bench_unresolved",
        )
    new_active_facts, new_active_reason = (
        _pokemon_public_snapshot_facts_with_reason(
            board,
            target,
        )
    )
    if new_active_facts is None:
        return _unsupported_active_bench_transition(
            origin_binding,
            new_active_reason or "transition_projected_bench_unresolved",
        )

    projected_bench: List[PokemonPublicSnapshotFacts] = []
    for slot, pokemon in enumerate(affected_bench):
        if slot == target_original_slot:
            projected_bench.append(old_active_facts)
            continue
        pokemon_facts, pokemon_reason = (
            _pokemon_public_snapshot_facts_with_reason(
                board,
                pokemon,
            )
        )
        if pokemon_facts is None:
            return _unsupported_active_bench_transition(
                origin_binding,
                pokemon_reason or "transition_projected_bench_unresolved",
            )
        projected_bench.append(pokemon_facts)

    projected_pokemon = (new_active_facts,) + tuple(projected_bench)
    projected_serials = tuple(
        pokemon.serial
        for pokemon in projected_pokemon
    )
    if len(set(projected_serials)) != len(projected_serials):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_duplicate_pokemon_serial",
        )
    attached_owner_by_serial: Dict[int, int] = {}
    for pokemon in projected_pokemon:
        for attached in pokemon.attached_energy + pokemon.attached_tools:
            previous_owner = attached_owner_by_serial.setdefault(
                attached.serial,
                pokemon.serial,
            )
            if previous_owner != pokemon.serial:
                return _unsupported_active_bench_transition(
                    origin_binding,
                    "transition_duplicate_attached_card_serial",
                )

    return ActiveBenchTransitionFacts(
        supported=True,
        origin_binding=origin_binding,
        target_decision_option_index=target_decision_option_index,
        old_active=old_active_facts,
        old_active_status_before=_active_special_condition_facts(
            affected_status_owner,
        ),
        new_active=new_active_facts,
        new_active_status_after=projected_active_status,
        projected_bench=tuple(projected_bench),
        bench_count_before=len(affected_bench),
        target_card_id=new_active_facts.card_id,
        target_serial=new_active_facts.serial,
        target_player_index=option_player_index,
        target_original_slot=target_original_slot,
        status_exact=True,
        transition_exact=True,
        unsupported_reason=None,
    )


def _unsupported_effect_transition_origin_binding(
    reason: str,
    *,
    origin: Optional[ActiveBenchTransitionOrigin] = None,
    origin_decision_option_index: Optional[int] = None,
) -> ActiveBenchTransitionOriginBindingFacts:
    return ActiveBenchTransitionOriginBindingFacts(
        supported=False,
        origin=origin,
        acting_player_index=None,
        affected_player_index=None,
        origin_decision_option_index=origin_decision_option_index,
        origin_option_type=None,
        origin_option_card_id=None,
        expected_switch_effect_id=None,
        binding_exact=False,
        unsupported_reason=reason,
    )


def _result_option_is_current(
    board: BoardView,
    result: Optional[SimulationResult],
) -> bool:
    if result is None or type(getattr(result, "index", None)) is not int:
        return False
    matches = tuple(
        index
        for index, option in board.iter_options()
        if option is getattr(result, "option", None)
    )
    return matches == (result.index,)


def _public_transition_side_signature(
    board: BoardView,
    *,
    opponent: bool,
) -> Optional[Tuple[Any, ...]]:
    active = (
        getattr(board, "opp_active", None)
        if opponent
        else getattr(board, "active", None)
    )
    bench = tuple(
        (
            getattr(board, "opp_bench", ())
            if opponent
            else getattr(board, "bench", ())
        )
        or ()
    )
    owner = (
        getattr(board, "opp", None)
        if opponent
        else getattr(board, "me", None)
    )
    active_facts, active_reason = _pokemon_public_snapshot_facts_with_reason(
        board,
        active,
    )
    if active_facts is None or active_reason is not None:
        return None
    bench_facts = []
    for pokemon in bench:
        facts, reason = _pokemon_public_snapshot_facts_with_reason(
            board,
            pokemon,
        )
        if facts is None or reason is not None:
            return None
        bench_facts.append(facts)
    return (
        active_facts,
        tuple(bench_facts),
        _active_special_condition_facts(owner),
    )


def _effect_sequence_state_key(
    board: BoardView,
) -> Optional[Tuple[int, int, int, int]]:
    state = getattr(board, "state", None)
    values = (
        getattr(state, "turn", None),
        getattr(state, "turnActionCount", None),
        getattr(state, "yourIndex", None),
        getattr(state, "firstPlayer", None),
    )
    if any(type(value) is not int for value in values):
        return None
    return values


def _effect_sequence_boards_match(
    earlier: BoardView,
    later: BoardView,
    *,
    action_count_delta: int,
) -> bool:
    earlier_key = _effect_sequence_state_key(earlier)
    later_key = _effect_sequence_state_key(later)
    if earlier_key is None or later_key is None:
        return False
    earlier_turn, earlier_actions, earlier_player, earlier_first = earlier_key
    later_turn, later_actions, later_player, later_first = later_key
    if (
        later_turn != earlier_turn
        or later_actions != earlier_actions + action_count_delta
        or later_player != earlier_player
        or later_first != earlier_first
        or getattr(earlier, "my_index", None) != earlier_player
        or getattr(later, "my_index", None) != later_player
    ):
        return False
    return all(
        earlier_signature is not None
        and earlier_signature == later_signature
        for earlier_signature, later_signature in (
            (
                _public_transition_side_signature(
                    earlier,
                    opponent=False,
                ),
                _public_transition_side_signature(
                    later,
                    opponent=False,
                ),
            ),
            (
                _public_transition_side_signature(
                    earlier,
                    opponent=True,
                ),
                _public_transition_side_signature(
                    later,
                    opponent=True,
                ),
            ),
        )
    )


def _wally_public_card_copies(cards: Sequence[Any]) -> Optional[Tuple[Tuple[int, int], ...]]:
    copies = tuple((getattr(card, "id", None), getattr(card, "serial", None)) for card in tuple(cards or ()))
    if any(type(cid) is not int or type(serial) is not int for cid, serial in copies):
        return None
    serials = tuple(serial for _card_id, serial in copies)
    return copies if len(set(serials)) == len(serials) else None


def _wally_hand_option_copy(
    board: BoardView, option: Any, *, require_hand_area: bool,
) -> Optional[Tuple[int, int]]:
    index = getattr(option, "index", None)
    hand = tuple(getattr(board, "hand", ()) or ())
    if type(index) is not int or not 0 <= index < len(hand):
        return None
    if require_hand_area and getattr(option, "area", None) != AreaType.HAND:
        return None
    card = hand[index]
    card_id = getattr(card, "id", None)
    serial = getattr(card, "serial", None)
    if (
        type(card_id) is not int
        or type(serial) is not int
        or board.option_card(option) != card_id
        or getattr(option, "serial", serial) not in {None, serial}
    ):
        return None
    return card_id, serial


def _wally_target_position(
    board: BoardView, option: Any,
) -> Optional[Tuple[bool, int, Pokemon]]:
    if getattr(option, "playerIndex", None) != getattr(board, "my_index", None):
        return None
    area = getattr(option, "area", None)
    slot = getattr(option, "index", None)
    target = board.option_target(option)
    if area == AreaType.ACTIVE and slot == 0 and target is board.active:
        return True, 0, target
    bench = tuple(getattr(board, "bench", ()) or ())
    if area == AreaType.BENCH and type(slot) is int and 0 <= slot < len(bench):
        if target is not bench[slot]:
            return None
        return False, slot, target
    return None


def _wally_recovery_board_facts(
    origin_board: BoardView, origin_result: Optional[SimulationResult],
    target_board: BoardView, target_result: Optional[SimulationResult],
    post_board: BoardView,
) -> Tuple[Optional[PokemonPublicSnapshotFacts], Optional[str]]:
    if not _result_option_is_current(origin_board, origin_result):
        return None, "wally_origin_option_not_current"
    origin_option = origin_result.option
    if (
        getattr(getattr(origin_board, "select", None), "context", None)
        != SelectContext.MAIN
        or getattr(origin_option, "type", None) != OptionType.PLAY
        or origin_board.option_card(origin_option) != WALLY_COMPASSION
        or getattr(origin_board.state, "supporterPlayed", None) is not False
        or getattr(origin_board, "my_index", None)
        != getattr(getattr(origin_board, "state", None), "yourIndex", None)
    ):
        return None, "wally_origin_binding_mismatch"
    wally_copy = _wally_hand_option_copy(
        origin_board, origin_option, require_hand_area=False,
    )
    if wally_copy is None or wally_copy[0] != WALLY_COMPASSION:
        return None, "wally_origin_card_copy_unresolved"
    if not _result_option_is_current(target_board, target_result):
        return None, "wally_target_option_not_current"
    target_option = target_result.option
    effect = getattr(target_board.select, "effect", None)
    if (
        getattr(getattr(target_board, "select", None), "context", None)
        != SelectContext.HEAL
        or getattr(target_option, "type", None) != OptionType.CARD
        or getattr(effect, "id", None) != WALLY_COMPASSION
        or getattr(effect, "serial", None) != wally_copy[1]
        or getattr(effect, "playerIndex", None)
        != getattr(target_board, "my_index", None)
    ):
        return None, "wally_target_binding_mismatch"
    position = _wally_target_position(target_board, target_option)
    if position is None:
        return None, "wally_target_position_unresolved"
    target_is_active, target_slot, target = position
    if target_board.pid(target) not in {
        MEGA_STARMIE_EX, MEGA_YUKIMENOKO_EX,
    } or damage_on(target) <= 0:
        return None, "wally_target_not_damaged_mega_ex"

    origin_key = _effect_sequence_state_key(origin_board)
    target_key = _effect_sequence_state_key(target_board)
    post_key = _effect_sequence_state_key(post_board)
    if (
        origin_key is None
        or target_key is None
        or post_key is None
        or target_key != (origin_key[0], origin_key[1] + 1, *origin_key[2:])
        or post_key != (origin_key[0], origin_key[1] + 2, *origin_key[2:])
        or getattr(target_board.state, "supporterPlayed", None) is not True
        or getattr(post_board.state, "supporterPlayed", None) is not True
        or getattr(getattr(post_board, "select", None), "context", None)
        != SelectContext.MAIN
    ):
        return None, "wally_effect_sequence_mismatch"

    sides = tuple(
        _public_transition_side_signature(board, opponent=opponent)
        for board in (origin_board, target_board, post_board)
        for opponent in (False, True)
    )
    controls = tuple(
        (
            getattr(board.state, "stadiumPlayed", None),
            getattr(board.state, "energyAttached", None),
            getattr(board.state, "retreated", None),
            _wally_public_card_copies(getattr(board.state, "stadium", ()) or ()),
        )
        for board in (origin_board, target_board, post_board)
    )
    origin_our, origin_opp, target_our, target_opp, _post_our, post_opp = sides
    if (
        any(signature is None for signature in sides)
        or any(control[-1] is None for control in controls)
        or origin_our != target_our
        or not origin_opp == target_opp == post_opp
        or not controls[0] == controls[1] == controls[2]
    ):
        return None, "wally_unrelated_public_board_changed"

    before, before_reason = _pokemon_public_snapshot_facts_with_reason(target_board, target)
    if before is None:
        return None, before_reason or "wally_target_snapshot_unrepresentable"
    post_targets = (
        (getattr(post_board, "active", None),)
        if target_is_active
        else tuple(getattr(post_board, "bench", ()) or ())[
            target_slot:target_slot + 1
        ]
    )
    if len(post_targets) != 1:
        return None, "wally_target_position_changed"
    after, after_reason = _pokemon_public_snapshot_facts_with_reason(
        post_board, post_targets[0],
    )
    expected_after = replace(before, hp=before.max_hp, damage_counters=0, attached_energy=())
    if after is None or after_reason is not None or after != expected_after:
        return None, "wally_recovery_projection_mismatch"

    expected_our = (
        (expected_after, target_our[1], target_our[2])
        if target_is_active
        else (
            target_our[0],
            target_our[1][:target_slot]
            + (expected_after,)
            + target_our[1][target_slot + 1:],
            target_our[2],
        )
    )
    if sides[4] != expected_our:
        return None, "wally_unrelated_own_board_changed"

    zones = tuple(
        _wally_public_card_copies(getattr(board, zone, ()))
        for board in (origin_board, target_board, post_board)
        for zone in ("hand", "discard")
    )
    origin_hand, origin_discard, target_hand, target_discard, post_hand, post_discard = zones
    recovered = tuple((facts.card_id, facts.serial) for facts in before.attached_energy)
    if (
        any(copies is None for copies in zones)
        or Counter(target_hand) != Counter(origin_hand) - Counter((wally_copy,))
        or Counter(target_discard) != Counter(origin_discard)
        or Counter(post_hand) != Counter(target_hand) + Counter(recovered)
        or Counter(post_discard) != Counter(target_discard) + Counter((wally_copy,))
    ):
        return None, "wally_card_copy_movement_mismatch"
    return before, None


def _wally_public_boards_equal(first: BoardView, second: BoardView) -> bool:
    state_names = ("supporterPlayed", "stadiumPlayed", "energyAttached", "retreated")
    return (
        _effect_sequence_state_key(first) == _effect_sequence_state_key(second)
        and _public_transition_side_signature(first, opponent=False)
        == _public_transition_side_signature(second, opponent=False)
        and _public_transition_side_signature(first, opponent=True)
        == _public_transition_side_signature(second, opponent=True)
        and all(
            getattr(first.state, name, None) == getattr(second.state, name, None)
            for name in state_names
        )
        and _wally_public_card_copies(getattr(first.state, "stadium", ()) or ())
        == _wally_public_card_copies(getattr(second.state, "stadium", ()) or ())
        and _wally_public_card_copies(getattr(first, "hand", ()))
        == _wally_public_card_copies(getattr(second, "hand", ()))
        and _wally_public_card_copies(getattr(first, "discard", ()))
        == _wally_public_card_copies(getattr(second, "discard", ()))
        and getattr(getattr(first, "select", None), "context", None)
        == SelectContext.MAIN
        and getattr(getattr(second, "select", None), "context", None)
        == SelectContext.MAIN
    )


def _effect_origin_play_log_matches(
    board: BoardView,
    *,
    card_id: int,
    player_index: int,
    origin_option: Any,
) -> bool:
    logs = getattr(getattr(board, "obs", None), "logs", None)
    if logs is None:
        logs = getattr(board, "logs", None)
    matching = tuple(
        log
        for log in tuple(logs or ())
        if getattr(log, "type", None) == LogType.PLAY
        and getattr(log, "playerIndex", None) == player_index
        and getattr(log, "cardId", None) == card_id
    )
    origin_serial = getattr(origin_option, "serial", None)
    if type(origin_serial) is int:
        matching = tuple(
            log
            for log in matching
            if getattr(log, "serial", None) == origin_serial
        )
    return len(matching) == 1


def _effect_origin_option_card_id(
    board: BoardView,
    option: Any,
) -> Optional[int]:
    if (
        getattr(option, "type", None) == OptionType.ABILITY
        and getattr(option, "area", None) == AreaType.STADIUM
    ):
        index = getattr(option, "index", None)
        stadium = tuple(
            getattr(getattr(board, "state", None), "stadium", None) or ()
        )
        if type(index) is int and 0 <= index < len(stadium):
            stadium_card_id = getattr(stadium[index], "id", None)
            return (
                stadium_card_id
                if type(stadium_card_id) is int
                else None
            )
        return None
    card_id = board.option_card(option)
    return card_id if type(card_id) is int else None


def _effect_driven_switch_origin_binding_facts(
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    switch_board: BoardView,
    *,
    origin: ActiveBenchTransitionOrigin,
    expected_option_type: OptionType,
    expected_card_id: int,
    affected_player_index: int,
    play_log_board: Optional[BoardView] = None,
) -> ActiveBenchTransitionOriginBindingFacts:
    origin_index = getattr(origin_result, "index", None)
    if origin_result is None:
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_result_missing",
            origin=origin,
        )
    if not _result_option_is_current(origin_board, origin_result):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_option_not_current",
            origin=origin,
            origin_decision_option_index=origin_index,
        )
    origin_option = origin_result.option
    if (
        getattr(origin_option, "type", None) != expected_option_type
        or _effect_origin_option_card_id(origin_board, origin_option)
        != expected_card_id
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_option_invalid",
            origin=origin,
            origin_decision_option_index=origin_index,
        )
    acting_player_index = getattr(origin_board, "my_index", None)
    expected_affected_player_index = (
        getattr(switch_board, "opp_index", None)
        if origin == ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH
        else getattr(switch_board, "my_index", None)
    )
    if (
        acting_player_index not in {0, 1}
        or getattr(switch_board, "my_index", None) != acting_player_index
        or affected_player_index not in {0, 1}
        or affected_player_index != expected_affected_player_index
        or (
            origin == ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH
            and affected_player_index == acting_player_index
        )
        or (
            origin != ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH
            and affected_player_index != acting_player_index
        )
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_player_mismatch",
            origin=origin,
            origin_decision_option_index=origin_index,
        )
    if (
        getattr(getattr(switch_board, "select", None), "context", None)
        != SelectContext.SWITCH
        or getattr(
            getattr(getattr(switch_board, "select", None), "effect", None),
            "id",
            None,
        )
        != expected_card_id
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_effect_continuity_mismatch",
            origin=origin,
            origin_decision_option_index=origin_index,
        )
    if play_log_board is not None and not _effect_origin_play_log_matches(
        play_log_board,
        card_id=expected_card_id,
        player_index=acting_player_index,
        origin_option=origin_option,
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_sequence_unresolved",
            origin=origin,
            origin_decision_option_index=origin_index,
        )
    return ActiveBenchTransitionOriginBindingFacts(
        supported=True,
        origin=origin,
        acting_player_index=acting_player_index,
        affected_player_index=affected_player_index,
        origin_decision_option_index=origin_index,
        origin_option_type=expected_option_type,
        origin_option_card_id=expected_card_id,
        expected_switch_effect_id=expected_card_id,
        binding_exact=True,
        unsupported_reason=None,
    )


def surfing_beach_transition_origin_binding_facts(
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    switch_board: BoardView,
) -> ActiveBenchTransitionOriginBindingFacts:
    if origin_result is None or not _result_option_is_current(
        origin_board,
        origin_result,
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_result_missing"
            if origin_result is None
            else "transition_origin_option_not_current",
            origin=ActiveBenchTransitionOrigin.SURFING_BEACH,
            origin_decision_option_index=getattr(origin_result, "index", None),
        )
    if not ImmediateOutcomeEvaluator(origin_board).is_surfing_beach_ability(
        origin_result.option,
    ) or not bool(getattr(origin_result.outcome, "supported", False)):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_legality_unresolved",
            origin=ActiveBenchTransitionOrigin.SURFING_BEACH,
            origin_decision_option_index=origin_result.index,
        )
    if not _effect_sequence_boards_match(
        origin_board,
        switch_board,
        action_count_delta=1,
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_sequence_unresolved",
            origin=ActiveBenchTransitionOrigin.SURFING_BEACH,
            origin_decision_option_index=origin_result.index,
        )
    return _effect_driven_switch_origin_binding_facts(
        origin_board,
        origin_result,
        switch_board,
        origin=ActiveBenchTransitionOrigin.SURFING_BEACH,
        expected_option_type=OptionType.ABILITY,
        expected_card_id=SURFING_BEACH,
        affected_player_index=origin_board.my_index,
    )


def suguri_transition_origin_binding_facts(
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    effect_choice_board: BoardView,
    effect_choice_result: Optional[SimulationResult],
    switch_board: BoardView,
) -> ActiveBenchTransitionOriginBindingFacts:
    origin_index = getattr(origin_result, "index", None)
    if origin_result is None or not _result_option_is_current(
        origin_board,
        origin_result,
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_result_missing"
            if origin_result is None
            else "transition_origin_option_not_current",
            origin=ActiveBenchTransitionOrigin.SUGURI,
            origin_decision_option_index=origin_index,
        )
    if (
        not origin_board.can_use_supporter(SUGURI)
        or getattr(origin_result.option, "type", None) != OptionType.PLAY
        or _effect_origin_option_card_id(
            origin_board,
            origin_result.option,
        )
        != SUGURI
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_legality_unresolved",
            origin=ActiveBenchTransitionOrigin.SUGURI,
            origin_decision_option_index=origin_index,
        )
    if (
        effect_choice_result is None
        or not _result_option_is_current(
            effect_choice_board,
            effect_choice_result,
        )
        or getattr(
            getattr(effect_choice_board, "select", None),
            "context",
            None,
        )
        != SelectContext.FIRST_EFFECT
        or getattr(
            getattr(
                getattr(effect_choice_board, "select", None),
                "contextCard",
                None,
            ),
            "id",
            None,
        )
        != SUGURI
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_suguri_choice_required",
            origin=ActiveBenchTransitionOrigin.SUGURI,
            origin_decision_option_index=origin_index,
        )
    if getattr(effect_choice_result.option, "type", None) != OptionType.YES:
        return _unsupported_effect_transition_origin_binding(
            "transition_suguri_non_switch_effect",
            origin=ActiveBenchTransitionOrigin.SUGURI,
            origin_decision_option_index=origin_index,
        )
    if (
        not _effect_sequence_boards_match(
            origin_board,
            effect_choice_board,
            action_count_delta=1,
        )
        or not _effect_sequence_boards_match(
            effect_choice_board,
            switch_board,
            action_count_delta=0,
        )
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_sequence_unresolved",
            origin=ActiveBenchTransitionOrigin.SUGURI,
            origin_decision_option_index=origin_index,
        )
    return _effect_driven_switch_origin_binding_facts(
        origin_board,
        origin_result,
        switch_board,
        origin=ActiveBenchTransitionOrigin.SUGURI,
        expected_option_type=OptionType.PLAY,
        expected_card_id=SUGURI,
        affected_player_index=origin_board.my_index,
        play_log_board=effect_choice_board,
    )


def boss_transition_origin_binding_facts(
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    switch_board: BoardView,
) -> ActiveBenchTransitionOriginBindingFacts:
    origin_index = getattr(origin_result, "index", None)
    if origin_result is None or not _result_option_is_current(
        origin_board,
        origin_result,
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_result_missing"
            if origin_result is None
            else "transition_origin_option_not_current",
            origin=ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH,
            origin_decision_option_index=origin_index,
        )
    if (
        not origin_board.can_use_supporter(BEFEHL_VON_BOSS)
        or getattr(origin_result.option, "type", None) != OptionType.PLAY
        or _effect_origin_option_card_id(
            origin_board,
            origin_result.option,
        )
        != BEFEHL_VON_BOSS
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_origin_legality_unresolved",
            origin=ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH,
            origin_decision_option_index=origin_index,
        )
    if not _effect_sequence_boards_match(
        origin_board,
        switch_board,
        action_count_delta=1,
    ):
        return _unsupported_effect_transition_origin_binding(
            "transition_sequence_unresolved",
            origin=ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH,
            origin_decision_option_index=origin_index,
        )
    return _effect_driven_switch_origin_binding_facts(
        origin_board,
        origin_result,
        switch_board,
        origin=ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH,
        expected_option_type=OptionType.PLAY,
        expected_card_id=BEFEHL_VON_BOSS,
        affected_player_index=origin_board.opp_index,
        play_log_board=switch_board,
    )


def effect_driven_switch_transition_facts(
    switch_board: BoardView,
    origin_binding: ActiveBenchTransitionOriginBindingFacts,
    target_result: Optional[SimulationResult],
) -> ActiveBenchTransitionFacts:
    if (
        origin_binding.origin == ActiveBenchTransitionOrigin.RETREAT
        or origin_binding.origin not in {
            ActiveBenchTransitionOrigin.SURFING_BEACH,
            ActiveBenchTransitionOrigin.SUGURI,
            ActiveBenchTransitionOrigin.BOSS_FORCED_SWITCH,
        }
    ):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_origin_not_supported",
        )
    if target_result is None or not _result_option_is_current(
        switch_board,
        target_result,
    ):
        return _unsupported_active_bench_transition(
            origin_binding,
            "transition_target_missing",
        )
    target = switch_board.option_target(target_result.option)
    return active_bench_transition_facts(
        switch_board,
        origin_binding=origin_binding,
        target_decision_option_index=target_result.index,
        target=target,
        projected_active_status=ActiveSpecialConditionFacts(
            asleep=False,
            paralyzed=False,
            confused=False,
            burned=False,
            poisoned=False,
        ),
        status_exact=True,
    )


def _retreat_discarded_energy_facts(
    board: BoardView,
    result: Optional[SimulationResult],
) -> Optional[AttachedEnergyPublicFacts]:
    if result is None or not _result_option_is_current(board, result):
        return None
    if (
        getattr(getattr(board, "select", None), "context", None)
        not in {
            SelectContext.DISCARD_ENERGY,
            SelectContext.DISCARD_ENERGY_CARD,
        }
        or getattr(result.option, "type", None)
        not in {OptionType.ENERGY, OptionType.ENERGY_CARD}
    ):
        return None
    active = getattr(board, "active", None)
    if active is None or board.option_target(result.option) is not active:
        return None
    active_facts, reason = _pokemon_public_snapshot_facts_with_reason(
        board,
        active,
    )
    if active_facts is None or reason is not None:
        return None
    energy_cards = tuple(getattr(active, "energyCards", None) or ())
    option_serial = getattr(result.option, "serial", None)
    energy_index = getattr(result.option, "energyIndex", None)
    selected = None
    if type(energy_index) is int and 0 <= energy_index < len(energy_cards):
        selected = energy_cards[energy_index]
        if (
            type(option_serial) is int
            and getattr(selected, "serial", None) != option_serial
        ):
            return None
    elif type(option_serial) is int:
        matches = tuple(
            card
            for card in energy_cards
            if getattr(card, "serial", None) == option_serial
        )
        if len(matches) != 1:
            return None
        selected = matches[0]
    if selected is None:
        return None
    selected_id = getattr(selected, "id", None)
    selected_serial = getattr(selected, "serial", None)
    if type(selected_id) is not int or type(selected_serial) is not int:
        return None
    option_card_id = getattr(result.option, "cardId", None)
    if option_card_id is not None and option_card_id != selected_id:
        return None
    matches = tuple(
        facts
        for facts in active_facts.attached_energy
        if facts.card_id == selected_id and facts.serial == selected_serial
    )
    return matches[0] if len(matches) == 1 else None


def retreat_transition_origin_binding_facts(
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    discard_steps: Sequence[Tuple[BoardView, SimulationResult]],
    switch_board: BoardView,
) -> ActiveBenchTransitionOriginBindingFacts:
    origin_index = getattr(origin_result, "index", None)
    unsupported = lambda: _unsupported_effect_transition_origin_binding(
        "retreat_energy_discard_unresolved",
        origin=ActiveBenchTransitionOrigin.RETREAT,
        origin_decision_option_index=origin_index,
    )
    if (
        origin_result is None
        or not _result_option_is_current(origin_board, origin_result)
        or getattr(origin_result.option, "type", None) != OptionType.RETREAT
        or getattr(getattr(origin_board, "select", None), "context", None)
        != SelectContext.MAIN
        or not bool(getattr(origin_result.outcome, "supported", False))
        or bool(getattr(getattr(origin_board, "state", None), "retreated", False))
    ):
        return unsupported()
    active = getattr(origin_board, "active", None)
    active_data = (
        origin_board.data(origin_board.pid(active))
        if active is not None
        else None
    )
    raw_cost = getattr(active_data, "retreatCost", None)
    if (
        active is None
        or type(raw_cost) is not int
        or raw_cost < 0
        or OpponentPublicThreatEvaluator(
            origin_board,
        )._public_retreat_effect_unsupported_reason(active) is not None
    ):
        return unsupported()
    cost = ImmediateOutcomeEvaluator(origin_board)._effective_retreat_cost(
        active,
    )
    steps = tuple(discard_steps or ())
    if len(steps) != cost:
        return unsupported()
    origin_key = _effect_sequence_state_key(origin_board)
    expected_key = (
        None
        if origin_key is None
        else (
            origin_key[0],
            origin_key[1] + 1,
            origin_key[2],
            origin_key[3],
        )
    )
    origin_our = _public_transition_side_signature(
        origin_board,
        opponent=False,
    )
    origin_opponent = _public_transition_side_signature(
        origin_board,
        opponent=True,
    )
    if (
        expected_key is None
        or origin_our is None
        or origin_opponent is None
        or getattr(origin_board, "my_index", None) != origin_key[2]
    ):
        return unsupported()
    remaining_energy = list(origin_our[0].attached_energy)
    selected_serials = set()
    for step_index, step in enumerate(steps):
        if not isinstance(step, tuple) or len(step) != 2:
            return unsupported()
        discard_board, discard_result = step
        expected_active = replace(
            origin_our[0],
            attached_energy=tuple(remaining_energy),
        )
        if (
            _effect_sequence_state_key(discard_board) != expected_key
            or _public_transition_side_signature(
                discard_board,
                opponent=False,
            )
            != (expected_active, origin_our[1], origin_our[2])
            or _public_transition_side_signature(
                discard_board,
                opponent=True,
            )
            != origin_opponent
            or getattr(
                getattr(discard_board, "select", None),
                "remainEnergyCost",
                None,
            )
            != cost - step_index
        ):
            return unsupported()
        selected = _retreat_discarded_energy_facts(
            discard_board,
            discard_result,
        )
        if selected is None or selected.serial in selected_serials:
            return unsupported()
        selected_serials.add(selected.serial)
        remaining_energy = [
            facts
            for facts in remaining_energy
            if facts.serial != selected.serial
        ]

    final_active = replace(
        origin_our[0],
        attached_energy=tuple(remaining_energy),
    )
    if (
        _effect_sequence_state_key(switch_board) != expected_key
        or getattr(getattr(switch_board, "select", None), "context", None)
        != SelectContext.SWITCH
        or getattr(
            getattr(getattr(switch_board, "select", None), "effect", None),
            "id",
            None,
        )
        is not None
        or not bool(getattr(getattr(switch_board, "state", None), "retreated", False))
        or _public_transition_side_signature(
            switch_board,
            opponent=False,
        )
        != (final_active, origin_our[1], origin_our[2])
        or _public_transition_side_signature(
            switch_board,
            opponent=True,
        )
        != origin_opponent
    ):
        return unsupported()
    acting_player_index = getattr(origin_board, "my_index", None)
    if (
        acting_player_index not in {0, 1}
        or getattr(switch_board, "my_index", None) != acting_player_index
    ):
        return unsupported()
    return ActiveBenchTransitionOriginBindingFacts(
        supported=True,
        origin=ActiveBenchTransitionOrigin.RETREAT,
        acting_player_index=acting_player_index,
        affected_player_index=acting_player_index,
        origin_decision_option_index=origin_result.index,
        origin_option_type=OptionType.RETREAT,
        origin_option_card_id=None,
        expected_switch_effect_id=None,
        binding_exact=True,
        unsupported_reason=None,
    )


def retreat_transition_facts(
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    discard_steps: Sequence[Tuple[BoardView, SimulationResult]],
    switch_board: BoardView,
    target_result: Optional[SimulationResult],
) -> ActiveBenchTransitionFacts:
    binding = retreat_transition_origin_binding_facts(
        origin_board,
        origin_result,
        discard_steps,
        switch_board,
    )
    if not binding.supported:
        return _unsupported_active_bench_transition(
            binding,
            binding.unsupported_reason or "retreat_energy_discard_unresolved",
        )
    if target_result is None or not _result_option_is_current(
        switch_board,
        target_result,
    ):
        return _unsupported_active_bench_transition(
            binding,
            "transition_target_missing",
        )
    return active_bench_transition_facts(
        switch_board,
        origin_binding=binding,
        target_decision_option_index=target_result.index,
        target=switch_board.option_target(target_result.option),
        projected_active_status=ActiveSpecialConditionFacts(
            asleep=False,
            paralyzed=False,
            confused=False,
            burned=False,
            poisoned=False,
        ),
        status_exact=True,
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
        if self._suguri_damage_boost_applies(attacker, target, attack, blocked):
            damage += 30
            reasons.append("suguri_damage_boost")
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
    def evaluate_basic_pokemon_play(
        self,
        option: Any,
    ) -> ImmediateOutcome:
        if option.type != OptionType.PLAY:
            return ImmediateOutcome(
                supported=False,
                reasons=("basic_pokemon_play_required",),
            )

        played_card_id = self.b.option_card(option)
        if (
            played_card_id is None
            or not self.b.is_basic_pokemon(played_card_id)
        ):
            return ImmediateOutcome(
                supported=False,
                reasons=("basic_pokemon_card_required",),
            )

        if self.b.bench_space <= 0:
            return ImmediateOutcome(
                supported=False,
                target_id=played_card_id,
                reasons=("basic_pokemon_play_no_bench_space",),
            )

        adds_board_out_buffer = len(self.b.bench) == 0

        reasons = ["basic_pokemon_play"]
        if adds_board_out_buffer:
            reasons.append(
                "basic_pokemon_play_adds_board_out_buffer"
            )

        return ImmediateOutcome(
            supported=True,
            adds_board_out_buffer=adds_board_out_buffer,
            target_id=played_card_id,
            reasons=tuple(reasons),
    )

    def evaluate_attach(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.ATTACH:
            return ImmediateOutcome(supported=False, reasons=("unsupported_attach_option",))
        card_id = self.b.option_card(option)
        target = self.b.option_target(option)
        if card_id is None or target is None:
            return ImmediateOutcome(supported=False, reasons=("missing_attach_state",))

        card_data = self.b.data(card_id)
        card_type = getattr(card_data, "cardType", None)
        if card_type in {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY}:
            return self.evaluate_energy_attach(option)
        if card_type == CardType.TOOL:
            return self.evaluate_tool_attach(option)
        return ImmediateOutcome(
            supported=False,
            target_id=self.b.pid(target),
            target_serial=getattr(target, "serial", None),
            reasons=("unsupported_attach_card_type",),
        )

    def evaluate_energy_attach(self, option: Any) -> ImmediateOutcome:
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

    def evaluate_tool_attach(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.ATTACH:
            return ImmediateOutcome(supported=False, reasons=("unsupported_tool_attach_option",))
        card_id = self.b.option_card(option)
        target = self.b.option_target(option)
        if card_id is None or target is None:
            return ImmediateOutcome(supported=False, reasons=("missing_attach_state",))

        target_id = self.b.pid(target)
        target_serial = getattr(target, "serial", None)
        if not any(candidate is target for candidate in self.b.all_my_pokemon):
            return ImmediateOutcome(
                supported=False,
                target_id=target_id,
                target_serial=target_serial,
                reasons=("invalid_tool_attach_target",),
            )
        if getattr(target, "tools", []):
            return ImmediateOutcome(
                supported=False,
                target_id=target_id,
                target_serial=target_serial,
                reasons=("target_already_has_tool",),
            )

        tool_data = self.b.data(card_id)
        if getattr(tool_data, "cardType", None) != CardType.TOOL:
            return ImmediateOutcome(
                supported=False,
                target_id=target_id,
                target_serial=target_serial,
                reasons=("unsupported_tool_attach_card_type",),
            )
        hp_bonus = public_hp_bonus(tool_data)
        effect_kinds = classify_public_effect(tool_data)
        if hp_bonus is None or hp_bonus <= 0 or effect_kinds != (PublicEffectKind.HP_AFFECTING,):
            return ImmediateOutcome(
                supported=False,
                target_id=target_id,
                target_serial=target_serial,
                reasons=("unsupported_tool_attach_effect",),
            )

        incoming_damage = (
            self.b.confirmed_opp_active_damage_for_survival_tool()
            if target is self.b.active
            else 0
        )
        current_hp = hp_left(target)
        next_knockout_without_tool = (
            incoming_damage is not None
            and incoming_damage > 0
            and incoming_damage >= current_hp
        )
        next_knockout_with_tool = (
            incoming_damage is not None
            and incoming_damage > 0
            and incoming_damage >= current_hp + hp_bonus
        )
        next_knockout_avoided = next_knockout_without_tool and not next_knockout_with_tool
        reasons = ["tool_attach", "static_hp_boost"]
        if incoming_damage is None:
            reasons.append("incoming_damage_unconfirmed")
        elif incoming_damage <= 0:
            reasons.append("no_known_incoming_damage")
        elif not next_knockout_without_tool:
            reasons.append("survives_without_tool")
        elif next_knockout_avoided:
            reasons.append("next_knockout_avoided")
        else:
            reasons.append("knockout_not_avoided")

        role = self.b.role_facts(target)
        preserves_primary = next_knockout_avoided and (
            self.b.prize_value(target) > 1
            or role.attack_ready
            or role.energy_count > 0
        )
        return ImmediateOutcome(
            next_knockout_avoided=next_knockout_avoided,
            avoids_prize_loss=next_knockout_avoided,
            prizes_preserved=self.b.prize_value(target) if next_knockout_avoided else 0,
            avoids_board_out=next_knockout_avoided and target is self.b.active and not self.b.bench,
            preserves_primary_pokemon=preserves_primary,
            target_id=target_id,
            target_serial=target_serial,
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
            develops_bench_next_attacker=development.develops_bench_next_attacker,
            evolution_hp_gain=development.evolution_hp_gain,
            completes_evolution_line=development.completes_evolution_line,
            completed_same_line_attackers=development.completed_same_line_attackers,
            same_turn_attack_connected=development.same_turn_attack_connected,
            same_turn_attack_option_count=development.same_turn_attack_option_count,
            post_evolution_ready_attack_count=development.post_evolution_ready_attack_count,
            development_value=development.development_value,
            development_probability=development.development_probability,
        )

    def _salvatore_completed_same_line_attackers(self, evolution_id: int) -> int:
        return sum(
            1
            for pokemon in self.b.all_my_pokemon
            if self.b.pid(pokemon) == evolution_id
            and self._best_unblocked_damage_from(pokemon) > 0
        )

    def _salvatore_development_fact(
        self,
        target: Pokemon,
    ) -> Optional[SalvatoreDevelopmentFacts]:
        evolution_id = self.b.salvatore_deck_target_evolution(target)
        if evolution_id is None:
            return None
        evolution_data = self.b.data(evolution_id)
        base_data = self.b.data(self.b.pid(target))
        if evolution_data is None or base_data is None:
            return None
        probability = self.b.deck_presence_probability(evolution_id)
        if probability <= 0:
            return None
        equivalent = any(
            option.type == OptionType.EVOLVE
            and self.b.option_card(option) == evolution_id
            and self.b.option_target(option) is target
            for _, option in self.b.iter_options()
        )
        tokens = tuple(self.b.energy_tokens_as(target, evolution_id))
        post_evolution_ready_attack_count = 0
        for attack_id in getattr(evolution_data, "attacks", ()):
            attack = self.b.attack(attack_id)
            if attack is None or not can_pay_attack_with_tokens(attack, tokens):
                continue
            if self.b.attack_blocked_by_ex_wall_for_card(
                evolution_id,
                self.b.opp_active,
                attack,
            ):
                continue
            post_evolution_ready_attack_count += 1
        same_turn_attack_option_count = (
            post_evolution_ready_attack_count
            if target is self.b.active
            and self.active_can_declare_attack_this_turn()
            else 0
        )
        same_turn_attack_connected = same_turn_attack_option_count > 0
        completed_same_line_attackers = (
            self._salvatore_completed_same_line_attackers(evolution_id)
        )
        hp_gain = max(
            0,
            safe_int(getattr(evolution_data, "hp", 0))
            - safe_int(getattr(base_data, "hp", 0)),
        )
        completes_evolution_line = self.b.card_evolves_from_card(
            evolution_id,
            self.b.pid(target),
        )
        develops_bench_next_attacker = (
            target is not self.b.active
            and completes_evolution_line
        )
        # HP gain is the single numeric development axis.  Line completion,
        # next-attacker status, same-line saturation and same-turn attack remain
        # separate facts so none of them re-adds attack damage.
        development_value = (
            max(1, hp_gain)
            * probability
            / (1 + completed_same_line_attackers)
            if completes_evolution_line
            else 0.0
        )
        return SalvatoreDevelopmentFacts(
            base_id=self.b.pid(target),
            base_serial=getattr(target, "serial", None),
            evolution_id=evolution_id,
            source_in_play=target in self.b.all_my_pokemon,
            evolution_searchable=True,
            hp_gain=hp_gain,
            completes_evolution_line=completes_evolution_line,
            develops_bench_next_attacker=develops_bench_next_attacker,
            completed_same_line_attackers=completed_same_line_attackers,
            equivalent_normal_evolution=equivalent,
            same_turn_attack_connected=same_turn_attack_connected,
            same_turn_attack_option_count=same_turn_attack_option_count,
            post_evolution_ready_attack_count=post_evolution_ready_attack_count,
            development_probability=probability,
            development_value=development_value,
        )

    def _salvatore_development_facts(self) -> Tuple[SalvatoreDevelopmentFacts, ...]:
        return tuple(
            fact
            for target in self.b.all_my_pokemon
            for fact in (self._salvatore_development_fact(target),)
            if fact is not None
        )

    def _salvatore_development_outcome(
        self,
        fact: SalvatoreDevelopmentFacts,
    ) -> ImmediateOutcome:
        target = next(
            (
                pokemon
                for pokemon in self.b.all_my_pokemon
                if getattr(pokemon, "serial", None) == fact.base_serial
            ),
            None,
        )
        opp_damage = self.b.opp_max_damage()
        evolution_data = self.b.data(fact.evolution_id)
        evolution_hp = safe_int(getattr(evolution_data, "hp", 0))
        avoids_board_out = (
            target is self.b.active
            and len(self.b.all_my_pokemon) == 1
            and opp_damage > 0
            and hp_left(target) <= opp_damage
            and evolution_hp - damage_on(target) > opp_damage
        )
        return ImmediateOutcome(
            supported=True,
            avoids_board_out=avoids_board_out,
            equivalent_evolution_available=fact.equivalent_normal_evolution,
            completes_next_attacker=fact.post_evolution_ready_attack_count > 0,
            develops_bench_next_attacker=fact.develops_bench_next_attacker,
            evolution_hp_gain=fact.hp_gain,
            completes_evolution_line=fact.completes_evolution_line,
            completed_same_line_attackers=fact.completed_same_line_attackers,
            same_turn_attack_connected=fact.same_turn_attack_connected,
            same_turn_attack_option_count=fact.same_turn_attack_option_count,
            post_evolution_ready_attack_count=fact.post_evolution_ready_attack_count,
            development_value=fact.development_value,
            development_probability=fact.development_probability,
            target_id=fact.base_id,
            target_serial=fact.base_serial,
            recommended_target_id=fact.base_id,
            recommended_target_serial=fact.base_serial,
            reasons=("salvatore_development_fact",),
        )

    def _best_salvatore_development_outcome(self) -> Optional[ImmediateOutcome]:
        facts = self._salvatore_development_facts()
        if not facts:
            return None
        best = max(
            facts,
            key=lambda fact: (
                fact.same_turn_attack_connected,
                fact.post_evolution_ready_attack_count,
                fact.develops_bench_next_attacker,
                fact.completed_same_line_attackers == 0,
                not fact.equivalent_normal_evolution,
                fact.development_value,
            ),
        )
        return self._salvatore_development_outcome(best)

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
        development_fact = self._salvatore_development_fact(target)
        if development_fact is None:
            return ImmediateOutcome(
                supported=False,
                reasons=("salvatore_target_has_no_current_evolution",),
            )
        outcome = self._best_salvatore_active_evolve_attack_outcome(
            target,
            "salvatore_target_reachable_attack",
            require_unused_supporter=False,
        )
        if outcome is None:
            development = self._salvatore_development_outcome(development_fact)
            return replace(
                development,
                reasons=development.reasons
                + ("salvatore_target_no_same_turn_attack_chain",),
            )
        development = self._salvatore_development_outcome(development_fact)
        return replace(
            outcome,
            equivalent_evolution_available=development.equivalent_evolution_available,
            completes_next_attacker=development.completes_next_attacker,
            develops_bench_next_attacker=development.develops_bench_next_attacker,
            evolution_hp_gain=development.evolution_hp_gain,
            completes_evolution_line=development.completes_evolution_line,
            completed_same_line_attackers=development.completed_same_line_attackers,
            same_turn_attack_connected=True,
            same_turn_attack_option_count=development.same_turn_attack_option_count,
            post_evolution_ready_attack_count=development.post_evolution_ready_attack_count,
            development_value=development.development_value,
            development_probability=development.development_probability,
        )

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

    def evaluate_poke_pad_candidate(self, option: Any) -> ImmediateOutcome:
        cid = self.b.option_card(option)
        facts = self.b.poke_pad_target_facts(cid, visible_search_candidate=True)
        if facts is None:
            return ImmediateOutcome(supported=False, reasons=("invalid_poke_pad_candidate",))
        return ImmediateOutcome(
            supported=True,
            development_value=facts.development_value,
            target_id=cid,
            reasons=(f"poke_pad_target_{facts.role}",),
        )

    def _best_retained_non_ko_attack(
        self,
    ) -> Optional[Tuple[Any, ImmediateOutcome, float]]:
        best: Optional[Tuple[Any, ImmediateOutcome, float]] = None
        pressure_policy = Policy(self.b)
        for _, option in self.b.iter_options():
            if option.type != OptionType.ATTACK and option.attackId is None:
                continue
            outcome = self.evaluate_attack(option)
            if (
                not outcome.supported
                or outcome.blocked
                or outcome.knockout
                or outcome.wins_game
            ):
                return None
            pressure = pressure_policy.attack_pressure_value(option, outcome)
            if best is None or (
                pressure,
                outcome.damage,
            ) > (
                best[2],
                best[1].damage,
            ):
                best = (option, outcome, pressure)
        return best

    def evaluate_poke_pad_play(self, option: Any) -> ImmediateOutcome:
        if option.type != OptionType.PLAY or self.b.option_card(option) != POKE_PAD:
            return ImmediateOutcome(supported=False, reasons=("unsupported_poke_pad_play",))
        useful = self.b.useful_poke_pad_targets()
        if not useful:
            return ImmediateOutcome(supported=True, reasons=("poke_pad_no_useful_target",))
        recommended = max(
            useful,
            key=lambda facts: (
                facts.development_value,
                -facts.target_id,
            ),
        )
        retained = self._best_retained_non_ko_attack()
        if retained is not None:
            attack_option, attack_outcome, attack_pressure = retained
            return ImmediateOutcome(
                supported=True,
                reachable_attack_id=attack_option.attackId,
                reachable_damage=attack_outcome.damage,
                reachable_attack_pressure=attack_pressure,
                reachable_can_continue_attack=True,
                development_value=recommended.development_value,
                recommended_target_id=recommended.target_id,
                reasons=(
                    "poke_pad_useful_target_available",
                    "poke_pad_preserves_current_non_ko_attack",
                    f"poke_pad_reachable_{recommended.reachable_pipeline_state}",
                ),
            )
        return ImmediateOutcome(
            supported=True,
            development_value=recommended.development_value,
            recommended_target_id=recommended.target_id,
            reasons=(
                "poke_pad_useful_target_available",
                f"poke_pad_reachable_{recommended.reachable_pipeline_state}",
            ),
        )

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

    def _current_turn_supporter_id(self) -> Optional[int]:
        if not getattr(self.b.state, "supporterPlayed", False):
            return None
        return getattr(
            self.b,
            "used_supporter_id_this_turn",
            None,
        )

    def _suguri_target_is_eligible(self, target: Optional[Pokemon]) -> bool:
        target_data = self.b.data(self.b.pid(target))
        return bool(
            target is not None
            and target_data is not None
            and (target_data.ex or target_data.megaEx)
        )

    def _suguri_damage_boost_applies(
        self,
        attacker: Optional[Pokemon],
        target: Optional[Pokemon],
        attack: Optional[Any],
        blocked: bool,
    ) -> bool:
        return bool(
            attacker is self.b.active
            and attack is not None
            and not blocked
            and self._current_turn_supporter_id() == SUGURI
            and self._suguri_target_is_eligible(target)
            and self.active_can_declare_attack_this_turn()
            and self.b.can_pay_attack(attacker, attack)
            and self.b.attack_damage(attacker, attack) > 0
        )

    def evaluate_suguri_damage_boost(self) -> ImmediateOutcome:
        attacker = self.b.active
        target = self.b.opp_active
        attacker_data = self.b.data(self.b.pid(attacker))
        if (
            attacker is None
            or target is None
            or attacker_data is None
            or not self._suguri_target_is_eligible(target)
            or not self.active_can_declare_attack_this_turn()
        ):
            return ImmediateOutcome(
                supported=False,
                reasons=("suguri_damage_boost_no_legal_attack",),
            )

        outcomes: List[ImmediateOutcome] = []
        for attack_id in attacker_data.attacks:
            attack = self.b.attack(attack_id)
            if (
                attack is None
                or not self.b.can_pay_attack(attacker, attack)
                or self._blocked_by_ex_wall(attacker, target, attack)
            ):
                continue
            base_damage = self.b.attack_damage(attacker, attack)
            if base_damage <= 0:
                continue
            boosted_damage = base_damage + 30
            knockout = boosted_damage >= hp_left(target)
            prizes_taken = self.b.prize_value(target) if knockout else 0
            wins_game = (
                prizes_taken >= self.b.my_prizes_left()
                if knockout
                else False
            )
            outcomes.append(
                ImmediateOutcome(
                    reachable_attack_id=int(attack.attackId),
                    reachable_damage=boosted_damage,
                    reachable_knockout=knockout,
                    reachable_prizes_taken=prizes_taken,
                    reachable_wins_game=wins_game,
                    target_id=self.b.pid(target),
                    target_serial=getattr(target, "serial", None),
                    reasons=("suguri_damage_boost",),
                )
            )
        if not outcomes:
            return ImmediateOutcome(
                supported=False,
                reasons=("suguri_damage_boost_no_legal_attack",),
            )
        return max(
            outcomes,
            key=lambda outcome: (
                outcome.reachable_wins_game,
                outcome.reachable_knockout,
                outcome.reachable_prizes_taken,
                outcome.reachable_damage,
            ),
        )

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
        supported = [outcome for outcome in outcomes if outcome.supported]
        if supported:
            return max(supported, key=self._tool_scrapper_priority)
        unmodeled = next(
            (
                outcome
                for outcome in outcomes
                if "tool_removal_effect_unmodeled" in outcome.reasons
            ),
            None,
        )
        if unmodeled is not None:
            return unmodeled
        return ImmediateOutcome(supported=False, reasons=("tool_scrapper_no_target",))

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
        tool_data = self.b.data(tool_id)
        effect_kinds = classify_public_effect(tool_data)
        hp_bonus = public_hp_bonus(tool_data)
        unmodeled_kinds = {
            PublicEffectKind.DAMAGE_AFFECTING,
            PublicEffectKind.AFTER_DAMAGE_TRIGGERED_EFFECT,
            PublicEffectKind.WEAKNESS_RESISTANCE_AFFECTING,
            PublicEffectKind.RETREAT_COST_AFFECTING,
            PublicEffectKind.RETREAT_OR_SWITCH_TRIGGERED_EFFECT,
            PublicEffectKind.OTHER_RELEVANT_EFFECT,
            PublicEffectKind.UNKNOWN,
        }
        if (
            any(kind in unmodeled_kinds for kind in effect_kinds)
            or (
                PublicEffectKind.HP_AFFECTING in effect_kinds
                and hp_bonus is None
            )
        ):
            return ImmediateOutcome(
                supported=False,
                removes_tool=True,
                target_id=self.b.pid(target),
                target_serial=getattr(target, "serial", None),
                reasons=(
                    "tool_scrapper_target",
                    "removes_tool",
                    "tool_removal_effect_unmodeled",
                ),
            )

        before_hp = hp_left(target)
        after_hp = max(0, before_hp - hp_bonus) if hp_bonus is not None else before_hp
        before_damage = self._best_unblocked_damage_to(target)
        attack_ko_before = before_damage >= before_hp
        attack_ko_after = before_damage >= after_hp
        removal_knockout = hp_bonus is not None and after_hp <= 0
        enables_knockout = (not removal_knockout) and (not attack_ko_before) and attack_ko_after
        prizes_taken = self.b.prize_value(target) if removal_knockout else 0
        wins_game = prizes_taken >= self.b.my_prizes_left() if removal_knockout else False

        reasons = ["tool_scrapper_target", "removes_tool"]
        if hp_bonus is not None:
            reasons.append("removes_hp_boost_tool")
            reasons.append(f"removed_hp_bonus_{hp_bonus}")
            if is_hero_cape_action(tool_id):
                reasons.append("removes_hero_cape")
        if enables_knockout:
            reasons.append("tool_scrapper_enables_ko")
        if removal_knockout:
            reasons.append("tool_removal_causes_knockout")
        if wins_game:
            reasons.append("wins_game")
        if (
            not enables_knockout
            and PublicEffectKind.NO_RELEVANT_EFFECT in effect_kinds
        ):
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
            "removes_hp_boost_tool" in outcome.reasons,
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
# Candidate public projection
# ============================================================
class CandidateProjectionEvaluator:
    @classmethod
    def project(cls, board: BoardView, result: SimulationResult) -> CandidateProjection:
        option = result.option
        option_type = getattr(option, "type", None)
        if option_type == OptionType.ATTACK:
            return cls._project_attack(board, result)
        if option_type == OptionType.RETREAT:
            return cls._project_retreat(board, result)
        if option_type == OptionType.END:
            return cls._project_end(board, result)
        return cls._unsupported(result, "unsupported_action_type")

    @classmethod
    def project_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
    ) -> CandidateProjectionFacts:
        option = result.option
        option_type = getattr(option, "type", None)
        if option_type == OptionType.ATTACK:
            return cls._project_attack_facts(board, result)
        if option_type == OptionType.RETREAT:
            return cls._project_switch_facts(board, result, "retreat")
        if (
            getattr(getattr(board, "select", None), "context", None)
            == SelectContext.SWITCH
            and board.option_target(option) is not None
        ):
            return cls._project_switch_facts(board, result, "switch")
        if option_type == OptionType.EVOLVE:
            return cls._project_active_evolution_facts(board, result)
        if option_type == OptionType.ATTACH:
            return cls._project_attach_facts(board, result)
        if option_type == OptionType.END:
            return cls._project_unchanged_facts(board, result)
        return cls._unsupported_facts(board, result, "unsupported_action_type")

    @classmethod
    def direct_attack_p6_input_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
        projection: CandidateProjectionFacts,
    ) -> P6AttackDecisionInputFacts:
        option_type = getattr(result.option, "type", None)
        if (
            option_type != OptionType.ATTACK
            or getattr(result.option, "attackId", None) is None
        ):
            return cls._unsupported_attack_decision_input(
                "direct_attack_required",
            )
        if not result.outcome.supported:
            return cls._unsupported_attack_decision_input(
                "attack_immediate_outcome_unsupported",
                projection.attack_id,
                result.index,
                immediate_prizes_taken=result.outcome.prizes_taken,
                candidate_wins_game=bool(result.outcome.wins_game),
                projected_bench_unchanged=True,
            )
        if not projection.supported:
            return cls._unsupported_attack_decision_input(
                projection.unsupported_reason
                or "candidate_projection_unsupported",
                projection.attack_id,
                result.index,
                immediate_prizes_taken=result.outcome.prizes_taken,
                candidate_wins_game=bool(result.outcome.wins_game),
                projected_bench_unchanged=True,
            )
        if (
            projection.option_type != OptionType.ATTACK
            or projection.attack_id is None
        ):
            return cls._unsupported_attack_decision_input(
                "attack_projection_mismatch",
                projection.attack_id,
                result.index,
                immediate_prizes_taken=result.outcome.prizes_taken,
                candidate_wins_game=bool(result.outcome.wins_game),
                projected_bench_unchanged=True,
            )

        our_active = projected_active_public_facts(
            board,
            getattr(board, "active", None),
            status_owner=getattr(board, "me", None),
            projected_card_id=projection.projected_active_card_id,
            projected_serial=projection.projected_active_serial,
            projected_hp=projection.projected_active_hp,
            projected_max_hp=projection.projected_active_max_hp,
            projected_energy_tokens=(
                projection.projected_active_energy_tokens
                if projection.projected_active_energy_tokens is not None
                else None
            ),
            projected_tool_ids=projection.projected_active_tool_ids,
        )
        opponent_active = None
        if not projection.opponent_active_ko and not projection.terminal_win:
            opponent_active = projected_active_public_facts(
                board,
                getattr(board, "opp_active", None),
                status_owner=getattr(board, "opp", None),
                projected_hp=projection.projected_opponent_active_hp,
            )
        return P6AttackDecisionInputFacts(
            supported=True,
            decision_option_index=result.index,
            attack_id=projection.attack_id,
            combat_result_exact=True,
            confirmed_damage=result.outcome.damage,
            opponent_active_ko=projection.opponent_active_ko,
            immediate_prizes_taken=result.outcome.prizes_taken,
            candidate_wins_game=bool(result.outcome.wins_game),
            our_active=our_active,
            opponent_active_after_attack=opponent_active,
            projected_bench_unchanged=True,
            unsupported_reason=None,
        )

    @classmethod
    def _wally_owned_prepared_decision(
        cls, board: BoardView, origin_result: SimulationResult,
        decision: P6AttackDecisionInputFacts,
    ) -> P6AttackDecisionInputFacts:
        if not decision.supported:
            return replace(
                decision,
                decision_option_index=origin_result.index,
            )
        our_bench, our_reason = cls._public_bench_snapshot_facts(board, opponent=False)
        opponent_bench, opponent_reason = cls._public_bench_snapshot_facts(board, opponent=True)
        if our_reason is not None or opponent_reason is not None:
            return cls._unsupported_attack_decision_input(
                our_reason or opponent_reason or "prepared_attack_board_unrepresentable",
                decision.attack_id,
                origin_result.index,
                decision.immediate_prizes_taken,
                decision.candidate_wins_game,
                decision.projected_bench_unchanged,
            )
        return replace(
            decision,
            decision_option_index=origin_result.index,
            prepared_our_bench=our_bench,
            prepared_opponent_bench=opponent_bench,
            prepared_board_exact=True,
        )

    @classmethod
    def wally_recovery_direct_attack_p6_input_facts(
        cls, origin_board: BoardView, origin_result: Optional[SimulationResult],
        target_board: BoardView, target_result: Optional[SimulationResult],
        post_board: BoardView, attack_result: Optional[SimulationResult],
    ) -> P6AttackDecisionInputFacts:
        _before, reason = _wally_recovery_board_facts(
            origin_board, origin_result, target_board, target_result, post_board,
        )
        if reason is not None:
            return cls._unsupported_attack_decision_input(reason)
        if not _result_option_is_current(post_board, attack_result):
            return cls._unsupported_attack_decision_input(
                "wally_direct_attack_option_not_current",
            )
        direct = cls.direct_attack_p6_input_facts(
            post_board, attack_result, cls.project_facts(post_board, attack_result),
        )
        return cls._wally_owned_prepared_decision(post_board, origin_result, direct)

    @classmethod
    def wally_recovery_active_basic_attach_p6_input_facts(
        cls, origin_board: BoardView, origin_result: Optional[SimulationResult],
        target_board: BoardView, target_result: Optional[SimulationResult],
        post_board: BoardView, attach_board: BoardView,
        attach_result: Optional[SimulationResult],
    ) -> P6AttackDecisionInputFacts:
        before, reason = _wally_recovery_board_facts(
            origin_board, origin_result, target_board, target_result, post_board,
        )
        if reason is not None:
            return cls._unsupported_attack_decision_input(reason)
        if not _wally_public_boards_equal(post_board, attach_board):
            return cls._unsupported_attack_decision_input(
                "wally_attach_board_mismatch",
            )
        if not _result_option_is_current(attach_board, attach_result):
            return cls._unsupported_attack_decision_input(
                "wally_attach_option_not_current",
            )
        selected_copy = _wally_hand_option_copy(
            attach_board, attach_result.option, require_hand_area=True,
        )
        if selected_copy is None:
            return cls._unsupported_attack_decision_input(
                "wally_attach_energy_copy_unresolved",
            )
        recovered_copies = tuple(
            (facts.card_id, facts.serial) for facts in before.attached_energy
        )
        preexisting_copies = _wally_public_card_copies(getattr(target_board, "hand", ()))
        if (
            preexisting_copies is None
            or (
                selected_copy not in recovered_copies
                and selected_copy not in preexisting_copies
            )
        ):
            return cls._unsupported_attack_decision_input(
                "wally_attach_energy_copy_not_owned",
            )
        decision = cls.active_basic_energy_attach_p6_input_facts(
            attach_board, attach_result,
        )
        return cls._wally_owned_prepared_decision(
            attach_board, origin_result, decision,
        )

    @staticmethod
    def _public_bench_snapshot_facts(
        board: BoardView,
        *,
        opponent: bool,
    ) -> Tuple[
        Optional[Tuple[PokemonPublicSnapshotFacts, ...]],
        Optional[str],
    ]:
        bench = tuple(
            (
                getattr(board, "opp_bench", ())
                if opponent
                else getattr(board, "bench", ())
            )
            or ()
        )
        facts_list = []
        for pokemon in bench:
            facts, reason = _pokemon_public_snapshot_facts_with_reason(
                board,
                pokemon,
            )
            if facts is None:
                return None, reason or "prepared_attack_board_unrepresentable"
            facts_list.append(facts)
        return tuple(facts_list), None

    @classmethod
    def _prepared_transition_board_facts(
        cls,
        switch_board: BoardView,
        post_transition_board: BoardView,
        transition: ActiveBenchTransitionFacts,
    ) -> Tuple[
        Optional[Tuple[PokemonPublicSnapshotFacts, ...]],
        Optional[Tuple[PokemonPublicSnapshotFacts, ...]],
        Optional[str],
    ]:
        if (
            not transition.supported
            or not transition.transition_exact
            or not transition.status_exact
        ):
            return None, None, (
                transition.unsupported_reason
                or "effect_transition_required"
            )
        switch_key = _effect_sequence_state_key(switch_board)
        post_key = _effect_sequence_state_key(post_transition_board)
        if (
            switch_key is None
            or post_key is None
            or post_key != switch_key
            or getattr(switch_board, "my_index", None)
            != getattr(post_transition_board, "my_index", None)
        ):
            return None, None, "prepared_transition_sequence_mismatch"

        pre_our = _public_transition_side_signature(
            switch_board,
            opponent=False,
        )
        pre_opponent = _public_transition_side_signature(
            switch_board,
            opponent=True,
        )
        post_our = _public_transition_side_signature(
            post_transition_board,
            opponent=False,
        )
        post_opponent = _public_transition_side_signature(
            post_transition_board,
            opponent=True,
        )
        if any(
            signature is None
            for signature in (
                pre_our,
                pre_opponent,
                post_our,
                post_opponent,
            )
        ):
            return None, None, "prepared_attack_board_unrepresentable"

        affected_is_ours = (
            transition.origin_binding.affected_player_index
            == getattr(switch_board, "my_index", None)
        )
        if affected_is_ours:
            if (
                pre_our[0] != transition.old_active
                or pre_our[2] != transition.old_active_status_before
                or post_our
                != (
                    transition.new_active,
                    transition.projected_bench,
                    transition.new_active_status_after,
                )
                or post_opponent != pre_opponent
            ):
                return None, None, "prepared_transition_projection_mismatch"
        else:
            if (
                transition.origin_binding.affected_player_index
                != getattr(switch_board, "opp_index", None)
                or pre_opponent[0] != transition.old_active
                or pre_opponent[2] != transition.old_active_status_before
                or post_opponent
                != (
                    transition.new_active,
                    transition.projected_bench,
                    transition.new_active_status_after,
                )
                or post_our != pre_our
            ):
                return None, None, "prepared_transition_projection_mismatch"
        return post_our[1], post_opponent[1], None

    @classmethod
    def active_bench_transition_attack_p6_input_facts(
        cls,
        switch_board: BoardView,
        post_transition_board: BoardView,
        transition: ActiveBenchTransitionFacts,
        attack_result: Optional[SimulationResult],
    ) -> P6AttackDecisionInputFacts:
        our_bench, opponent_bench, board_reason = (
            cls._prepared_transition_board_facts(
                switch_board,
                post_transition_board,
                transition,
            )
        )
        if board_reason is not None:
            return cls._unsupported_attack_decision_input(board_reason)
        if attack_result is None:
            return cls._unsupported_attack_decision_input(
                "prepared_attack_result_required",
            )
        if not _result_option_is_current(
            post_transition_board,
            attack_result,
        ):
            return cls._unsupported_attack_decision_input(
                "prepared_attack_option_not_current",
            )
        if (
            transition.origin_binding.origin
            == ActiveBenchTransitionOrigin.SUGURI
            and "suguri_damage_boost"
            in tuple(getattr(attack_result.outcome, "reasons", ()) or ())
        ):
            return cls._unsupported_attack_decision_input(
                "suguri_switch_attack_branch_mismatch",
                getattr(attack_result.option, "attackId", None),
                attack_result.index,
            )

        projection = cls.project_facts(
            post_transition_board,
            attack_result,
        )
        decision = cls.direct_attack_p6_input_facts(
            post_transition_board,
            attack_result,
            projection,
        )
        if not decision.supported:
            return decision
        return replace(
            decision,
            prepared_our_bench=our_bench,
            prepared_opponent_bench=opponent_bench,
            prepared_board_exact=True,
        )

    @classmethod
    def active_evolution_attack_p6_input_facts(
        cls,
        board: BoardView,
        evolution_result: Optional[SimulationResult],
        attack_fact: Optional[ActiveEvolutionAttackFact],
    ) -> P6AttackDecisionInputFacts:
        if evolution_result is None:
            return cls._unsupported_attack_decision_input(
                "active_evolution_result_required",
            )
        option = evolution_result.option
        if getattr(option, "type", None) != OptionType.EVOLVE:
            return cls._unsupported_attack_decision_input(
                "active_evolution_required",
            )

        active = getattr(board, "active", None)
        opponent_active = getattr(board, "opp_active", None)
        if active is None:
            return cls._unsupported_attack_decision_input(
                "missing_current_active",
            )
        if board.option_target(option) is not active:
            return cls._unsupported_attack_decision_input(
                "current_active_evolution_target_required",
            )
        evolution_id = board.option_card(option)
        if (
            evolution_id is None
            or not board.evolves_from(evolution_id, active)
        ):
            return cls._unsupported_attack_decision_input(
                "invalid_active_evolution",
            )
        current_options = tuple(
            (index, current_option)
            for index, current_option in board.iter_options()
            if current_option is option
        )
        if (
            len(current_options) != 1
            or current_options[0][0] != evolution_result.index
        ):
            return cls._unsupported_attack_decision_input(
                "active_evolution_option_not_current",
            )
        if opponent_active is None:
            return cls._unsupported_attack_decision_input(
                "missing_current_opponent_active",
            )
        if any(
            bool(getattr(getattr(board, "me", None), status, False))
            for status in (
                "asleep",
                "confused",
                "paralyzed",
                "burned",
                "poisoned",
            )
        ):
            return cls._unsupported_attack_decision_input(
                "active_evolution_special_condition_unmodeled",
            )
        if attack_fact is None:
            return cls._unsupported_attack_decision_input(
                "active_evolution_attack_fact_required",
            )

        reachable_facts = tuple(
            board.active_evolution_attack_facts(option)
        )
        if not reachable_facts:
            return cls._unsupported_attack_decision_input(
                "active_evolution_no_same_turn_attack_chain",
            )
        if not evolution_result.outcome.supported:
            return cls._unsupported_attack_decision_input(
                "active_evolution_immediate_outcome_unsupported",
            )
        if sum(fact == attack_fact for fact in reachable_facts) != 1:
            return cls._unsupported_attack_decision_input(
                "active_evolution_attack_fact_mismatch",
                getattr(attack_fact, "attack_id", None),
            )

        projection = cls.project_facts(board, evolution_result)
        if not projection.supported:
            return cls._unsupported_attack_decision_input(
                projection.unsupported_reason
                or "active_evolution_projection_unsupported",
                attack_fact.attack_id,
            )
        if (
            type(projection.projected_active_card_id) is not int
            or projection.projected_active_card_id != int(evolution_id)
            or projection.projected_active_serial
            != getattr(active, "serial", None)
            or type(projection.projected_active_hp) is not int
            or type(projection.projected_active_max_hp) is not int
            or (
                projection.projected_active_max_hp
                - projection.projected_active_hp
                != damage_on(active)
            )
        ):
            return cls._unsupported_attack_decision_input(
                "active_evolution_damage_counters_unrepresentable",
                attack_fact.attack_id,
            )
        if projection.projected_active_energy_tokens is None:
            return cls._unsupported_attack_decision_input(
                "projected_active_energy_mapping_unsupported",
                attack_fact.attack_id,
            )
        try:
            our_active = projected_active_public_facts(
                board,
                active,
                status_owner=getattr(board, "me", None),
                projected_card_id=projection.projected_active_card_id,
                projected_serial=projection.projected_active_serial,
                projected_hp=projection.projected_active_hp,
                projected_max_hp=projection.projected_active_max_hp,
                projected_energy_tokens=(
                    projection.projected_active_energy_tokens
                ),
                projected_tool_ids=projection.projected_active_tool_ids,
            )
        except (TypeError, ValueError, OverflowError):
            return cls._unsupported_attack_decision_input(
                "active_evolution_snapshot_unrepresentable",
                attack_fact.attack_id,
            )
        if (
            our_active is None
            or our_active.damage_counters != damage_on(active)
            or our_active.energy_card_ids
            != tuple(int(card_id) for card_id in board.energies(active))
            or our_active.energy_tokens
            != tuple(projection.projected_active_energy_tokens)
            or our_active.tool_ids != cls._tool_ids(active)
            or any(
                (
                    our_active.asleep,
                    our_active.confused,
                    our_active.paralyzed,
                    our_active.burned,
                    our_active.poisoned,
                )
            )
        ):
            return cls._unsupported_attack_decision_input(
                "active_evolution_snapshot_unrepresentable",
                attack_fact.attack_id,
            )

        attack_id = getattr(attack_fact, "attack_id", None)
        evolution_data = board.data(evolution_id)
        if (
            type(attack_id) is not int
            or evolution_data is None
            or attack_id
            not in tuple(getattr(evolution_data, "attacks", ()) or ())
        ):
            return cls._unsupported_attack_decision_input(
                "reachable_attack_identity_unknown",
                attack_id,
            )
        attack = board.attack(attack_id)
        if attack is None:
            return cls._unsupported_attack_decision_input(
                "missing_reachable_attack_definition",
                attack_id,
            )
        if not can_pay_attack_with_tokens(
            attack,
            projection.projected_active_energy_tokens,
        ):
            return cls._unsupported_attack_decision_input(
                "reachable_attack_energy_unpayable",
                attack_id,
            )

        limitations = list(cls._attack_projection_limitations(attack))
        attack_text = _normalized_attack_text(attack)
        variable_damage_markers = (
            "for each",
            "times the amount",
            "number of",
            "more damage for each",
            "damage for each",
        )
        if (
            attack_id != RESENTFUL_REFRAIN
            and (
                any(
                    marker in attack_text
                    for marker in variable_damage_markers
                )
                or (
                    safe_int(getattr(attack, "damage", 0)) == 0
                    and "damage" in attack_text
                )
            )
        ):
            limitations.append("dynamic_attack_damage_unmodeled")
        if (
            ImmediateOutcomeEvaluator(board)._current_turn_supporter_id()
            == SUGURI
        ):
            limitations.append("suguri_damage_boost_unmodeled")

        public_effect_reason = OpponentPublicThreatEvaluator(
            board
        )._public_damage_effect_unsupported_reason(
            active,
            opponent_active,
        )
        if public_effect_reason is not None:
            limitations.append(public_effect_reason)
        for public_card in (
            tuple(
                getattr(getattr(board, "state", None), "stadium", None)
                or ()
            )
            + tuple(getattr(active, "tools", None) or ())
            + tuple(getattr(opponent_active, "tools", None) or ())
        ):
            if (
                PublicEffectKind.AFTER_DAMAGE_TRIGGERED_EFFECT
                in classify_public_effect(board.data(card_id(public_card)))
            ):
                limitations.append(
                    "public_after_damage_effect_unmodeled"
                )
        ignores_weakness_resistance = (
            "isn't affected by weakness or resistance" in attack_text
            or "is not affected by weakness or resistance" in attack_text
        )
        if not ignores_weakness_resistance:
            modifier_match = public_attack_matches_weakness_or_resistance(
                board,
                active,
                opponent_active,
                attack,
                attacker_card_id=int(evolution_id),
            )
            if modifier_match is not False:
                limitations.append(
                    "weakness_resistance_damage_unmodeled"
                )
        if cls._has_unmodeled_between_turn_damage(board):
            limitations.append("between_turn_effect_unmodeled")
        limitations = list(cls._unique(limitations))
        if limitations:
            return cls._unsupported_attack_decision_input(
                limitations[0],
                attack_id,
            )

        expected_blocked = board.attack_blocked_by_ex_wall_for_card(
            int(evolution_id),
            opponent_active,
            attack,
        )
        expected_damage = (
            0
            if expected_blocked
            else board.attack_damage_for_card(int(evolution_id), attack)
        )
        expected_knockout = expected_damage >= hp_left(opponent_active)
        expected_prizes_taken = (
            board.prize_value(opponent_active)
            if expected_knockout
            else 0
        )
        expected_wins_game = bool(
            expected_knockout
            and expected_prizes_taken >= board.my_prizes_left()
        )
        expected_bench_damage = (
            0
            if expected_blocked
            else attack_bench_damage_amount(attack)
        )
        expected_bypasses_wall = bool(
            board.attack_bypasses_ex_wall(attack)
            and board.pid(opponent_active) in EX_ATTACK_WALLS
        )
        if (
            type(attack_fact.supported) is not bool
            or not attack_fact.supported
            or type(attack_fact.damage) is not int
            or type(attack_fact.blocked) is not bool
            or type(attack_fact.knockout) is not bool
            or type(attack_fact.prizes_taken) is not int
            or type(attack_fact.wins_game) is not bool
            or type(attack_fact.bench_damage) is not int
            or type(attack_fact.bypasses_wall) is not bool
            or attack_fact.blocked != expected_blocked
            or attack_fact.damage != expected_damage
            or attack_fact.knockout != expected_knockout
            or attack_fact.prizes_taken != expected_prizes_taken
            or attack_fact.wins_game != expected_wins_game
            or attack_fact.bench_damage != expected_bench_damage
            or attack_fact.bypasses_wall != expected_bypasses_wall
        ):
            return cls._unsupported_attack_decision_input(
                "reachable_combat_facts_inconsistent",
                attack_id,
            )

        opponent_active_after_attack = None
        if not expected_knockout and not expected_wins_game:
            try:
                opponent_active_after_attack = projected_active_public_facts(
                    board,
                    opponent_active,
                    status_owner=getattr(board, "opp", None),
                    projected_hp=max(
                        0,
                        hp_left(opponent_active) - expected_damage,
                    ),
                )
            except (TypeError, ValueError, OverflowError):
                return cls._unsupported_attack_decision_input(
                    "opponent_active_snapshot_unrepresentable",
                    attack_id,
                )
            if opponent_active_after_attack is None:
                return cls._unsupported_attack_decision_input(
                    "opponent_active_snapshot_unrepresentable",
                    attack_id,
                )

        return P6AttackDecisionInputFacts(
            supported=True,
            decision_option_index=None,
            attack_id=attack_id,
            combat_result_exact=True,
            confirmed_damage=expected_damage,
            opponent_active_ko=expected_knockout,
            immediate_prizes_taken=expected_prizes_taken,
            candidate_wins_game=expected_wins_game,
            our_active=our_active,
            opponent_active_after_attack=opponent_active_after_attack,
            projected_bench_unchanged=True,
            unsupported_reason=None,
        )

    @classmethod
    def static_hp_tool_attach_p6_input_facts(
        cls,
        board: BoardView,
        attach_result: Optional[SimulationResult],
        attack_result: Optional[SimulationResult],
    ) -> P6AttackDecisionInputFacts:
        if attach_result is None:
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_attach_result_required",
            )
        attach_option = attach_result.option
        if getattr(attach_option, "type", None) != OptionType.ATTACH:
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_attach_required",
            )

        active = getattr(board, "active", None)
        if active is None:
            return cls._unsupported_attack_decision_input(
                "missing_current_active",
            )
        if board.option_target(attach_option) is not active:
            return cls._unsupported_attack_decision_input(
                "current_active_attach_target_required",
            )

        attached_card_id = board.option_card(attach_option)
        attached_card_data = (
            board.data(attached_card_id)
            if attached_card_id is not None
            else None
        )
        if (
            attached_card_id is None
            or getattr(attached_card_data, "cardType", None)
            != CardType.TOOL
        ):
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_required",
            )

        hp_bonus = public_hp_bonus(attached_card_data)
        if hp_bonus is None:
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_bonus_required",
            )
        if type(hp_bonus) is not int:
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_bonus_not_fixed_integer",
            )
        if hp_bonus <= 0:
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_bonus_not_positive",
            )
        if classify_public_effect(attached_card_data) != (
            PublicEffectKind.HP_AFFECTING,
        ):
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_effect_unmodeled",
            )
        if not attach_result.outcome.supported:
            return cls._unsupported_attack_decision_input(
                "attach_immediate_outcome_unsupported",
            )
        if attack_result is None:
            return cls._unsupported_attack_decision_input(
                "direct_attack_result_required",
            )

        attack_projection = cls.project_facts(board, attack_result)
        attack_decision = cls.direct_attack_p6_input_facts(
            board,
            attack_result,
            attack_projection,
        )
        if not attack_decision.supported:
            return (
                replace(
                    attack_decision,
                    decision_option_index=attach_result.index,
                )
                if attack_decision.attack_id is not None
                else attack_decision
            )
        if attack_decision.our_active is None:
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_snapshot_unrepresentable",
                attack_decision.attack_id,
                attach_result.index,
                attack_decision.immediate_prizes_taken,
                attack_decision.candidate_wins_game,
                attack_decision.projected_bench_unchanged,
            )

        try:
            projected_active = replace(
                attack_decision.our_active,
                hp=attack_decision.our_active.hp + hp_bonus,
                max_hp=attack_decision.our_active.max_hp + hp_bonus,
                tool_ids=(
                    attack_decision.our_active.tool_ids
                    + (int(attached_card_id),)
                ),
            )
        except (TypeError, ValueError, OverflowError):
            return cls._unsupported_attack_decision_input(
                "static_hp_tool_snapshot_unrepresentable",
                attack_decision.attack_id,
                attach_result.index,
                attack_decision.immediate_prizes_taken,
                attack_decision.candidate_wins_game,
                attack_decision.projected_bench_unchanged,
            )
        return replace(
            attack_decision,
            decision_option_index=attach_result.index,
            our_active=projected_active,
        )

    @classmethod
    def active_basic_energy_attach_p6_input_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
    ) -> P6AttackDecisionInputFacts:
        option = result.option
        if getattr(option, "type", None) != OptionType.ATTACH:
            return cls._unsupported_attack_decision_input(
                "active_basic_energy_attach_required",
            )

        active = getattr(board, "active", None)
        opponent_active = getattr(board, "opp_active", None)
        if active is None:
            return cls._unsupported_attack_decision_input(
                "missing_current_active",
            )
        if board.option_target(option) is not active:
            return cls._unsupported_attack_decision_input(
                "current_active_attach_target_required",
            )

        attached_card_id = board.option_card(option)
        attached_card_data = (
            board.data(attached_card_id)
            if attached_card_id is not None
            else None
        )
        if (
            attached_card_id is None
            or getattr(attached_card_data, "cardType", None)
            != CardType.BASIC_ENERGY
        ):
            return cls._unsupported_attack_decision_input(
                "basic_energy_attach_required",
            )

        outcome = result.outcome
        if not outcome.supported:
            return cls._unsupported_attack_decision_input(
                "attach_immediate_outcome_unsupported",
            )
        if opponent_active is None:
            return cls._unsupported_attack_decision_input(
                "missing_current_opponent_active",
            )

        attack_id = getattr(outcome, "reachable_attack_id", None)
        if attack_id is None:
            return cls._unsupported_attack_decision_input(
                "reachable_attack_required",
            )
        try:
            attack_id = int(attack_id)
        except (TypeError, ValueError):
            return cls._unsupported_attack_decision_input(
                "reachable_attack_identity_unknown",
            )
        intermediate_reasons = {
            "attach_access_via_retreat",
            "attach_access_via_boss",
            "attach_access_via_surfing_beach",
        }
        intermediate_reason = next(
            (
                reason
                for reason in tuple(getattr(outcome, "reasons", ()) or ())
                if reason in intermediate_reasons
            ),
            None,
        )
        if intermediate_reason is not None:
            return cls._unsupported_attack_decision_input(
                intermediate_reason,
                attack_id,
            )
        if not outcome.enables_attack:
            return cls._unsupported_attack_decision_input(
                "attach_does_not_enable_attack",
                attack_id,
            )
        try:
            enabled_attack_ids = tuple(
                int(enabled_attack_id)
                for enabled_attack_id in outcome.enabled_attack_ids
            )
        except (TypeError, ValueError):
            return cls._unsupported_attack_decision_input(
                "reachable_attack_identity_unknown",
                attack_id,
            )
        if len(enabled_attack_ids) != 1:
            return cls._unsupported_attack_decision_input(
                "reachable_attack_identity_not_unique",
                attack_id,
            )
        if enabled_attack_ids[0] != attack_id:
            return cls._unsupported_attack_decision_input(
                "reachable_attack_identity_mismatch",
                attack_id,
            )

        active_data = board.data(board.pid(active))
        if (
            active_data is None
            or attack_id not in tuple(getattr(active_data, "attacks", ()) or ())
        ):
            return cls._unsupported_attack_decision_input(
                "reachable_attack_identity_unknown",
                attack_id,
            )
        attack = board.attack(attack_id)
        if attack is None:
            return cls._unsupported_attack_decision_input(
                "missing_reachable_attack_definition",
                attack_id,
            )
        attack_text = _normalized_attack_text(attack)
        variable_damage_markers = (
            "for each",
            "times the amount",
            "number of",
            "more damage for each",
            "damage for each",
        )
        if (
            attack_id != RESENTFUL_REFRAIN
            and (
                any(
                    marker in attack_text
                    for marker in variable_damage_markers
                )
                or (
                    safe_int(getattr(attack, "damage", 0)) == 0
                    and "damage" in attack_text
                )
            )
        ):
            return cls._unsupported_attack_decision_input(
                "dynamic_attack_damage_unmodeled",
                attack_id,
            )
        if (
            ImmediateOutcomeEvaluator(board)._current_turn_supporter_id()
            == SUGURI
        ):
            return cls._unsupported_attack_decision_input(
                "suguri_damage_boost_unmodeled",
                attack_id,
            )

        limitations = list(cls._attack_projection_limitations(attack))
        limitations.extend(
            cls._public_damage_projection_limitations(
                board,
                active,
                opponent_active,
                attack,
            )
        )
        if cls._has_unmodeled_between_turn_damage(board):
            limitations.append("between_turn_effect_unmodeled")
        limitations = list(cls._unique(limitations))
        if limitations:
            return cls._unsupported_attack_decision_input(
                limitations[0],
                attack_id,
            )

        reachable_damage = getattr(outcome, "reachable_damage", None)
        reachable_knockout = getattr(outcome, "reachable_knockout", None)
        reachable_prizes_taken = getattr(
            outcome,
            "reachable_prizes_taken",
            None,
        )
        reachable_wins_game = getattr(outcome, "reachable_wins_game", None)
        if (
            type(reachable_damage) is not int
            or reachable_damage < 0
            or type(reachable_knockout) is not bool
            or type(reachable_prizes_taken) is not int
            or reachable_prizes_taken < 0
            or type(reachable_wins_game) is not bool
        ):
            return cls._unsupported_attack_decision_input(
                "reachable_combat_exactness_unconfirmed",
                attack_id,
            )
        if reachable_damage != board.attack_damage(active, attack):
            return cls._unsupported_attack_decision_input(
                "reachable_combat_facts_inconsistent",
                attack_id,
                immediate_prizes_taken=reachable_prizes_taken,
                candidate_wins_game=reachable_wins_game,
                projected_bench_unchanged=True,
            )

        expected_knockout = reachable_damage >= hp_left(opponent_active)
        expected_prizes_taken = (
            board.prize_value(opponent_active)
            if expected_knockout
            else 0
        )
        expected_wins_game = bool(
            expected_knockout
            and expected_prizes_taken >= board.my_prizes_left()
        )
        if (
            reachable_knockout != expected_knockout
            or reachable_prizes_taken != expected_prizes_taken
            or reachable_wins_game != expected_wins_game
        ):
            return cls._unsupported_attack_decision_input(
                "reachable_combat_facts_inconsistent",
                attack_id,
                immediate_prizes_taken=reachable_prizes_taken,
                candidate_wins_game=reachable_wins_game,
                projected_bench_unchanged=True,
            )

        attached_tokens = energy_tokens_for_attach(
            int(attached_card_id),
            active,
        )
        if attached_tokens is None:
            return cls._unsupported_attack_decision_input(
                "unsupported_attach_energy",
                attack_id,
            )
        projected_energy_card_ids = (
            tuple(int(card_id) for card_id in board.energies(active))
            + (int(attached_card_id),)
        )
        projected_energy_tokens = (
            tuple(board.energy_tokens(active))
            + tuple(attached_tokens)
        )
        try:
            our_active = projected_active_public_facts(
                board,
                active,
                status_owner=getattr(board, "me", None),
                projected_energy_card_ids=projected_energy_card_ids,
                projected_energy_tokens=projected_energy_tokens,
            )
        except (TypeError, ValueError) as error:
            return cls._unsupported_attack_decision_input(
                str(error) or "projected_active_energy_mapping_unsupported",
                attack_id,
            )

        opponent_active_after_attack = None
        if not reachable_knockout and not reachable_wins_game:
            try:
                opponent_active_after_attack = projected_active_public_facts(
                    board,
                    opponent_active,
                    status_owner=getattr(board, "opp", None),
                    projected_hp=max(
                        0,
                        hp_left(opponent_active) - reachable_damage,
                    ),
                )
            except (TypeError, ValueError) as error:
                return cls._unsupported_attack_decision_input(
                    str(error)
                    or "projected_active_energy_mapping_unsupported",
                    attack_id,
                )
        return P6AttackDecisionInputFacts(
            supported=True,
            decision_option_index=None,
            attack_id=attack_id,
            combat_result_exact=True,
            confirmed_damage=reachable_damage,
            opponent_active_ko=reachable_knockout,
            immediate_prizes_taken=reachable_prizes_taken,
            candidate_wins_game=reachable_wins_game,
            our_active=our_active,
            opponent_active_after_attack=opponent_active_after_attack,
            projected_bench_unchanged=True,
            unsupported_reason=None,
        )

    @staticmethod
    def _unsupported_attack_decision_input(
        reason: str,
        attack_id: Optional[int] = None,
        decision_option_index: Optional[int] = None,
        immediate_prizes_taken: Optional[int] = None,
        candidate_wins_game: Optional[bool] = None,
        projected_bench_unchanged: bool = False,
    ) -> P6AttackDecisionInputFacts:
        return P6AttackDecisionInputFacts(
            supported=False,
            decision_option_index=decision_option_index,
            attack_id=attack_id,
            combat_result_exact=False,
            confirmed_damage=None,
            opponent_active_ko=None,
            immediate_prizes_taken=immediate_prizes_taken,
            candidate_wins_game=candidate_wins_game,
            our_active=None,
            opponent_active_after_attack=None,
            projected_bench_unchanged=projected_bench_unchanged,
            unsupported_reason=reason,
        )

    @classmethod
    def prize_exchange_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
        projection: Optional[CandidateProjectionFacts] = None,
        threat: Optional[OpponentPublicThreatFacts] = None,
    ) -> PrizeExchangeFacts:
        outcome = result.outcome
        projection = projection or cls.project_facts(board, result)
        threat = threat or (
            OpponentPublicThreatEvaluator.evaluate_projected_facts(
                board,
                projection,
            )
            if projection.supported
            else None
        )
        return cls._prize_exchange_from_combat_facts(
            board,
            candidate_supported=bool(outcome.supported),
            immediate_prizes_taken=max(0, safe_int(outcome.prizes_taken)),
            candidate_wins_game=bool(outcome.wins_game),
            projection_supported=projection.supported,
            projection_unsupported_reason=projection.unsupported_reason,
            threat=threat,
        )

    @classmethod
    def _prize_exchange_from_combat_facts(
        cls,
        board: BoardView,
        *,
        candidate_supported: bool,
        immediate_prizes_taken: int,
        candidate_wins_game: bool,
        projection_supported: bool,
        projection_unsupported_reason: Optional[str],
        threat: Optional[OpponentPublicThreatFacts],
    ) -> PrizeExchangeFacts:
        immediate_prizes_taken = max(
            0,
            safe_int(immediate_prizes_taken),
        )
        my_prizes_left_after_candidate = max(
            0,
            board.my_prizes_left() - immediate_prizes_taken,
        )
        if not candidate_supported:
            return PrizeExchangeFacts(
                supported=False,
                immediate_prizes_taken=immediate_prizes_taken,
                my_prizes_left_after_candidate=my_prizes_left_after_candidate,
                confirmed_reply_supported=False,
                confirmed_reply_prizes_lost=0,
                opponent_prizes_left_after_reply=None,
                net_prize_exchange=None,
                candidate_wins_game=bool(candidate_wins_game),
                confirmed_reply_wins_game=None,
                unsupported_reason="candidate_immediate_outcome_unsupported",
            )

        if not projection_supported:
            return cls._reply_unsupported_prize_exchange_values(
                candidate_wins_game,
                immediate_prizes_taken,
                my_prizes_left_after_candidate,
                projection_unsupported_reason
                or "candidate_projection_unsupported",
            )

        if threat is None or not threat.supported:
            return cls._reply_unsupported_prize_exchange_values(
                candidate_wins_game,
                immediate_prizes_taken,
                my_prizes_left_after_candidate,
                (
                    None if threat is None else threat.unsupported_reason
                ) or "opponent_public_threat_unsupported",
            )

        opponent_prizes = getattr(
            getattr(board, "opp", None),
            "prize",
            None,
        )
        if opponent_prizes is None:
            return cls._reply_unsupported_prize_exchange_values(
                candidate_wins_game,
                immediate_prizes_taken,
                my_prizes_left_after_candidate,
                "missing_opponent_prize_state",
            )

        confirmed_reply_prizes_lost = (
            max(0, safe_int(threat.prizes_lost))
            if threat.can_ko_projected_active
            else 0
        )
        opponent_prizes_left_after_reply = max(
            0,
            len(opponent_prizes) - confirmed_reply_prizes_lost,
        )
        return PrizeExchangeFacts(
            supported=True,
            immediate_prizes_taken=immediate_prizes_taken,
            my_prizes_left_after_candidate=my_prizes_left_after_candidate,
            confirmed_reply_supported=True,
            confirmed_reply_prizes_lost=confirmed_reply_prizes_lost,
            opponent_prizes_left_after_reply=(
                opponent_prizes_left_after_reply
            ),
            net_prize_exchange=(
                immediate_prizes_taken
                - confirmed_reply_prizes_lost
            ),
            candidate_wins_game=bool(candidate_wins_game),
            confirmed_reply_wins_game=bool(
                threat.can_ko_projected_active
                and opponent_prizes_left_after_reply == 0
            ),
            unsupported_reason=None,
        )

    @staticmethod
    def _reply_unsupported_prize_exchange(
        outcome: ImmediateOutcome,
        immediate_prizes_taken: int,
        my_prizes_left_after_candidate: int,
        reason: str,
    ) -> PrizeExchangeFacts:
        return CandidateProjectionEvaluator._reply_unsupported_prize_exchange_values(
            bool(outcome.wins_game),
            immediate_prizes_taken,
            my_prizes_left_after_candidate,
            reason,
        )

    @staticmethod
    def _reply_unsupported_prize_exchange_values(
        candidate_wins_game: bool,
        immediate_prizes_taken: int,
        my_prizes_left_after_candidate: int,
        reason: str,
    ) -> PrizeExchangeFacts:
        return PrizeExchangeFacts(
            supported=True,
            immediate_prizes_taken=immediate_prizes_taken,
            my_prizes_left_after_candidate=my_prizes_left_after_candidate,
            confirmed_reply_supported=False,
            confirmed_reply_prizes_lost=0,
            opponent_prizes_left_after_reply=None,
            net_prize_exchange=None,
            candidate_wins_game=bool(candidate_wins_game),
            confirmed_reply_wins_game=None,
            unsupported_reason=reason,
        )

    @classmethod
    def board_out_facts(
        cls,
        board: BoardView,
        projection: CandidateProjectionFacts,
        threat: Optional[OpponentPublicThreatFacts] = None,
    ) -> BoardOutFacts:
        threat = threat or (
            OpponentPublicThreatEvaluator.evaluate_projected_facts(
                board,
                projection,
            )
            if projection.supported
            else None
        )
        return cls._board_out_from_projected_active(
            board,
            projection_supported=projection.supported,
            projected_active_card_id=projection.projected_active_card_id,
            projected_active_hp=projection.projected_active_hp,
            projection_unsupported_reason=projection.unsupported_reason,
            threat=threat,
        )

    @classmethod
    def _board_out_from_projected_active(
        cls,
        board: BoardView,
        *,
        projection_supported: bool,
        projected_active_card_id: Optional[int],
        projected_active_hp: Optional[int],
        projection_unsupported_reason: Optional[str],
        threat: Optional[OpponentPublicThreatFacts],
    ) -> BoardOutFacts:
        if (
            not projection_supported
            or projected_active_card_id is None
            or projected_active_hp is None
        ):
            return BoardOutFacts(
                supported=False,
                projected_bench_count=None,
                board_out_if_projected_active_ko=None,
                confirmed_reply_supported=False,
                confirmed_reply_ko=None,
                confirmed_reply_causes_board_out=None,
                unsupported_reason=(
                    projection_unsupported_reason
                    or "candidate_projection_unsupported"
                ),
            )

        projected_bench_count = len(getattr(board, "bench", ()) or ())
        board_out_if_projected_active_ko = projected_bench_count == 0
        if threat is None or not threat.supported:
            return BoardOutFacts(
                supported=True,
                projected_bench_count=projected_bench_count,
                board_out_if_projected_active_ko=(
                    board_out_if_projected_active_ko
                ),
                confirmed_reply_supported=False,
                confirmed_reply_ko=None,
                confirmed_reply_causes_board_out=None,
                unsupported_reason=(
                    (None if threat is None else threat.unsupported_reason)
                    or "opponent_public_threat_unsupported"
                ),
            )

        confirmed_reply_ko = bool(threat.can_ko_projected_active)
        return BoardOutFacts(
            supported=True,
            projected_bench_count=projected_bench_count,
            board_out_if_projected_active_ko=(
                board_out_if_projected_active_ko
            ),
            confirmed_reply_supported=True,
            confirmed_reply_ko=confirmed_reply_ko,
            confirmed_reply_causes_board_out=bool(
                confirmed_reply_ko
                and board_out_if_projected_active_ko
            ),
            unsupported_reason=None,
        )

    @classmethod
    def next_attacker_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
        projection: CandidateProjectionFacts,
        threat: Optional[OpponentPublicThreatFacts] = None,
    ) -> NextAttackerFacts:
        if (
            not projection.supported
            or projection.projected_opponent_active_hp is None
            or projection.opponent_active_ko
            or board.opp_active is None
        ):
            return cls._unsupported_next_attacker_facts(
                projection.unsupported_reason
                or (
                    "opponent_promotion_required"
                    if projection.opponent_active_ko
                    else "candidate_projection_unsupported"
                )
            )

        projected_bench, bench_reason = cls._projected_bench_for_next_attacker(
            board,
            result,
            projection,
        )
        if projected_bench is None:
            return cls._unsupported_next_attacker_facts(bench_reason)

        threat = threat or OpponentPublicThreatEvaluator.evaluate_projected_facts(
            board,
            projection,
        )
        return cls._next_attacker_for_projected_bench(
            board,
            projected_bench=projected_bench,
            projected_opponent_active_hp=(
                projection.projected_opponent_active_hp
            ),
            threat=threat,
        )

    @classmethod
    def _next_attacker_for_projected_bench(
        cls,
        board: BoardView,
        *,
        projected_bench: Tuple[Pokemon, ...],
        projected_opponent_active_hp: int,
        threat: OpponentPublicThreatFacts,
    ) -> NextAttackerFacts:
        projected_bench_count = len(projected_bench)
        serials = tuple(
            getattr(pokemon, "serial", None)
            for pokemon in projected_bench
        )
        if any(serial is None for serial in serials):
            return cls._unsupported_next_attacker_facts(
                "missing_projected_bench_serial",
                projected_bench_count,
            )
        if len(set(serials)) != len(serials):
            return cls._unsupported_next_attacker_facts(
                "duplicate_projected_bench_serial",
                projected_bench_count,
            )

        confirmed_by_serial: Dict[
            int,
            Tuple[Pokemon, Tuple[Tuple[int, int, bool], ...]],
        ] = {}
        damage_probe = OpponentPublicThreatEvaluator(board)
        attack_evaluator = ImmediateOutcomeEvaluator(board)
        target = board.opp_active
        target_hp = max(
            0,
            safe_int(projected_opponent_active_hp),
        )
        uncertain_damage_markers = (
            "for each",
            "more damage",
            "less damage",
            "times the number",
            "equal to",
            "instead of",
            "flip a coin",
            "flip coins",
            "if heads",
            "if tails",
            "at random",
            "random",
        )

        for pokemon in projected_bench:
            pokemon_id = board.pid(pokemon)
            pokemon_data = board.data(pokemon_id)
            if pokemon_data is None:
                return cls._unsupported_next_attacker_facts(
                    "missing_projected_bench_card_data",
                    projected_bench_count,
                )
            tokens = cls._exact_energy_tokens_as(
                board,
                pokemon,
                pokemon_id,
            )
            if tokens is None:
                return cls._unsupported_next_attacker_facts(
                    "projected_bench_energy_unsupported",
                    projected_bench_count,
                )

            confirmed_attacks: List[Tuple[int, int, bool]] = []
            for attack_id in dict.fromkeys(
                getattr(pokemon_data, "attacks", ()) or ()
            ):
                attack = board.attack(attack_id)
                if attack is None:
                    return cls._unsupported_next_attacker_facts(
                        "missing_projected_bench_attack_data",
                        projected_bench_count,
                    )
                if not can_pay_attack_with_tokens(attack, tokens):
                    continue
                attack_text = _normalized_attack_text(attack)
                if any(
                    marker in attack_text
                    for marker in uncertain_damage_markers
                ):
                    continue
                _, damage_reason = damage_probe._certain_damage(
                    pokemon,
                    attack,
                )
                if damage_reason is not None:
                    continue
                limitations = cls._unique(
                    cls._attack_projection_limitations(attack)
                    + cls._public_damage_projection_limitations(
                        board,
                        pokemon,
                        target,
                        attack,
                    )
                )
                if limitations:
                    continue
                outcome = attack_evaluator._attack_outcome_with_tokens_against(
                    pokemon,
                    safe_int(attack_id),
                    tokens,
                    target,
                    "next_attacker_public_fact",
                )
                if not outcome.supported:
                    continue
                damage = max(0, safe_int(outcome.damage))
                confirmed_attacks.append(
                    (
                        safe_int(attack_id),
                        damage,
                        bool(damage > 0 and damage >= target_hp),
                    )
                )

            if confirmed_attacks:
                confirmed_by_serial[safe_int(
                    getattr(pokemon, "serial", None)
                )] = (
                    pokemon,
                    tuple(confirmed_attacks),
                )

        attack_candidates = [
            (
                knockout,
                damage,
                serial,
                attack_id,
                pokemon,
                attacks,
            )
            for serial, (pokemon, attacks) in confirmed_by_serial.items()
            for attack_id, damage, knockout in attacks
        ]
        if attack_candidates:
            best = min(
                attack_candidates,
                key=lambda item: (
                    not item[0],
                    -item[1],
                    item[2],
                    item[3],
                ),
            )
            (
                best_ko,
                best_damage,
                best_serial,
                best_attack_id,
                best_pokemon,
                best_attacks,
            ) = best
            usable_attack_ids = tuple(
                sorted({
                    attack_id
                    for attack_id, _, _ in best_attacks
                })
            )
            best_card_id = board.pid(best_pokemon)
        else:
            best_ko = False
            best_damage = 0
            best_serial = None
            best_card_id = None
            best_attack_id = None
            usable_attack_ids = ()

        ready_exists = bool(confirmed_by_serial)
        if not threat.supported:
            return NextAttackerFacts(
                supported=True,
                projected_bench_count=projected_bench_count,
                ready_next_attacker_exists=ready_exists,
                ready_next_attacker_count=len(confirmed_by_serial),
                best_confirmed_damage=best_damage,
                can_ko_projected_opponent_active=bool(best_ko),
                best_next_attacker_card_id=best_card_id,
                best_next_attacker_serial=best_serial,
                best_attack_id=best_attack_id,
                usable_attack_ids=usable_attack_ids,
                confirmed_reply_supported=False,
                confirmed_reply_ko=None,
                confirmed_reply_has_ready_next_attacker=None,
                unsupported_reason=(
                    threat.unsupported_reason
                    or "opponent_public_threat_unsupported"
                ),
            )

        confirmed_reply_ko = bool(threat.can_ko_projected_active)
        return NextAttackerFacts(
            supported=True,
            projected_bench_count=projected_bench_count,
            ready_next_attacker_exists=ready_exists,
            ready_next_attacker_count=len(confirmed_by_serial),
            best_confirmed_damage=best_damage,
            can_ko_projected_opponent_active=bool(best_ko),
            best_next_attacker_card_id=best_card_id,
            best_next_attacker_serial=best_serial,
            best_attack_id=best_attack_id,
            usable_attack_ids=usable_attack_ids,
            confirmed_reply_supported=True,
            confirmed_reply_ko=confirmed_reply_ko,
            confirmed_reply_has_ready_next_attacker=bool(
                confirmed_reply_ko and ready_exists
            ),
            unsupported_reason=None,
        )

    @classmethod
    def attack_decision_outcome_facts(
        cls,
        board: BoardView,
        decision: P6AttackDecisionInputFacts,
    ) -> DirectDecisionOutcomeFacts:
        return cls._attack_decision_p6_facts(
            board,
            decision,
        )[-1]

    @classmethod
    def _attack_decision_p6_facts(
        cls,
        board: BoardView,
        decision: P6AttackDecisionInputFacts,
    ) -> Tuple[
        OpponentPublicThreatFacts,
        PrizeExchangeFacts,
        BoardOutFacts,
        NextAttackerFacts,
        DirectDecisionOutcomeFacts,
    ]:
        if decision.supported and decision.prepared_board_exact:
            current_our_bench, our_reason = (
                cls._public_bench_snapshot_facts(
                    board,
                    opponent=False,
                )
            )
            current_opponent_bench, opponent_reason = (
                cls._public_bench_snapshot_facts(
                    board,
                    opponent=True,
                )
            )
            if (
                our_reason is not None
                or opponent_reason is not None
                or current_our_bench != decision.prepared_our_bench
                or current_opponent_bench
                != decision.prepared_opponent_bench
            ):
                decision = cls._unsupported_attack_decision_input(
                    "prepared_attack_board_mismatch",
                    decision.attack_id,
                    decision.decision_option_index,
                    decision.immediate_prizes_taken,
                    decision.candidate_wins_game,
                    decision.projected_bench_unchanged,
                )
        if decision.supported:
            return cls._supported_attack_decision_p6_facts(board, decision)

        reason = (
            decision.unsupported_reason
            or "candidate_projection_unsupported"
        )
        threat = OpponentPublicThreatFacts(
            supported=False,
            best_confirmed_damage=0,
            can_ko_projected_active=False,
            prizes_lost=0,
            usable_attack_ids=(),
            unsupported_reason="candidate_projection_unsupported",
        )
        candidate_outcome_supported = (
            reason != "attack_immediate_outcome_unsupported"
            and reason != "direct_attack_required"
        )
        prize_exchange = cls._prize_exchange_from_combat_facts(
            board,
            candidate_supported=candidate_outcome_supported,
            immediate_prizes_taken=(
                decision.immediate_prizes_taken
                if decision.immediate_prizes_taken is not None
                else 0
            ),
            candidate_wins_game=bool(decision.candidate_wins_game),
            projection_supported=False,
            projection_unsupported_reason=reason,
            threat=threat,
        )
        board_out = cls._board_out_from_projected_active(
            board,
            projection_supported=False,
            projected_active_card_id=None,
            projected_active_hp=None,
            projection_unsupported_reason=reason,
            threat=threat,
        )
        next_attacker = cls._unsupported_next_attacker_facts(reason)
        direct_outcome = cls._unsupported_direct_decision_outcome(
            reason,
            decision.attack_id,
        )
        return (
            threat,
            prize_exchange,
            board_out,
            next_attacker,
            direct_outcome,
        )

    @classmethod
    def _supported_attack_decision_p6_facts(
        cls,
        board: BoardView,
        decision: P6AttackDecisionInputFacts,
    ) -> Tuple[
        OpponentPublicThreatFacts,
        PrizeExchangeFacts,
        BoardOutFacts,
        NextAttackerFacts,
        DirectDecisionOutcomeFacts,
    ]:
        if (
            not decision.supported
            or decision.our_active is None
            or decision.attack_id is None
            or decision.confirmed_damage is None
            or decision.opponent_active_ko is None
            or decision.immediate_prizes_taken is None
            or decision.candidate_wins_game is None
            or not decision.combat_result_exact
            or not decision.projected_bench_unchanged
        ):
            raise ValueError("unsupported_attack_decision_p6_input")

        threat = OpponentPublicThreatEvaluator.evaluate_public_active_facts(
            board,
            decision.our_active,
            decision.opponent_active_after_attack,
            terminal_win=decision.candidate_wins_game,
            opponent_active_ko=decision.opponent_active_ko,
        )
        prize_exchange = cls._prize_exchange_from_combat_facts(
            board,
            candidate_supported=True,
            immediate_prizes_taken=decision.immediate_prizes_taken,
            candidate_wins_game=decision.candidate_wins_game,
            projection_supported=True,
            projection_unsupported_reason=None,
            threat=threat,
        )
        board_out = cls._board_out_from_projected_active(
            board,
            projection_supported=True,
            projected_active_card_id=decision.our_active.card_id,
            projected_active_hp=decision.our_active.hp,
            projection_unsupported_reason=None,
            threat=threat,
        )
        if (
            decision.opponent_active_ko
            or decision.opponent_active_after_attack is None
            or board.opp_active is None
        ):
            next_attacker = cls._unsupported_next_attacker_facts(
                "opponent_promotion_required"
                if decision.opponent_active_ko
                else "candidate_projection_unsupported"
            )
        else:
            next_attacker = cls._next_attacker_for_projected_bench(
                board,
                projected_bench=tuple(getattr(board, "bench", ()) or ()),
                projected_opponent_active_hp=(
                    decision.opponent_active_after_attack.hp
                ),
                threat=threat,
            )
        direct_outcome = cls._direct_decision_outcome_from_combat_facts(
            attack_id=decision.attack_id,
            confirmed_damage=decision.confirmed_damage,
            opponent_active_ko=decision.opponent_active_ko,
            candidate_wins_game=decision.candidate_wins_game,
            threat=threat,
            prize_exchange=prize_exchange,
            board_out=board_out,
            next_attacker=next_attacker,
        )
        return (
            threat,
            prize_exchange,
            board_out,
            next_attacker,
            direct_outcome,
        )

    @classmethod
    def direct_decision_outcome_facts(
        cls,
        result: SimulationResult,
        projection: CandidateProjectionFacts,
        threat: OpponentPublicThreatFacts,
        prize_exchange: PrizeExchangeFacts,
        board_out: BoardOutFacts,
        next_attacker: NextAttackerFacts,
    ) -> DirectDecisionOutcomeFacts:
        option_type = getattr(result.option, "type", None)
        if (
            option_type != OptionType.ATTACK
            or getattr(result.option, "attackId", None) is None
        ):
            return cls._unsupported_direct_decision_outcome(
                "direct_attack_required",
            )
        if not result.outcome.supported:
            return cls._unsupported_direct_decision_outcome(
                "attack_immediate_outcome_unsupported",
                projection.attack_id,
            )
        if not projection.supported:
            return cls._unsupported_direct_decision_outcome(
                projection.unsupported_reason
                or "candidate_projection_unsupported",
                projection.attack_id,
            )
        if (
            projection.option_type != OptionType.ATTACK
            or projection.attack_id is None
        ):
            return cls._unsupported_direct_decision_outcome(
                "attack_projection_mismatch",
                projection.attack_id,
            )
        if not prize_exchange.supported:
            return cls._unsupported_direct_decision_outcome(
                prize_exchange.unsupported_reason
                or "prize_exchange_unsupported",
                projection.attack_id,
            )

        return cls._direct_decision_outcome_from_combat_facts(
            attack_id=projection.attack_id,
            confirmed_damage=result.outcome.damage,
            opponent_active_ko=projection.opponent_active_ko,
            candidate_wins_game=bool(result.outcome.wins_game),
            threat=threat,
            prize_exchange=prize_exchange,
            board_out=board_out,
            next_attacker=next_attacker,
        )

    @classmethod
    def _direct_decision_outcome_from_combat_facts(
        cls,
        *,
        attack_id: int,
        confirmed_damage: int,
        opponent_active_ko: bool,
        candidate_wins_game: bool,
        threat: OpponentPublicThreatFacts,
        prize_exchange: PrizeExchangeFacts,
        board_out: BoardOutFacts,
        next_attacker: NextAttackerFacts,
    ) -> DirectDecisionOutcomeFacts:
        next_attacker_can_ko = (
            next_attacker.can_ko_projected_opponent_active
            if next_attacker.supported
            else None
        )
        next_attacker_confirmed_damage = (
            next_attacker.best_confirmed_damage
            if next_attacker.supported
            else None
        )
        reply_information_supported = bool(
            threat.supported
            and prize_exchange.confirmed_reply_supported
            and board_out.confirmed_reply_supported
        )
        if not reply_information_supported:
            return DirectDecisionOutcomeFacts(
                supported=True,
                attack_id=attack_id,
                confirmed_damage=confirmed_damage,
                opponent_active_ko=opponent_active_ko,
                immediate_prizes_taken=(
                    prize_exchange.immediate_prizes_taken
                ),
                candidate_wins_game=candidate_wins_game,
                reply_information_supported=False,
                confirmed_reply_damage=None,
                confirmed_reply_ko=None,
                confirmed_reply_prizes_lost=None,
                confirmed_loss_by_prize=None,
                confirmed_loss_by_board_out=None,
                confirmed_loss=None,
                net_prize_exchange=prize_exchange.net_prize_exchange,
                my_prizes_left_after_candidate=(
                    prize_exchange.my_prizes_left_after_candidate
                ),
                opponent_prizes_left_after_reply=(
                    prize_exchange.opponent_prizes_left_after_reply
                ),
                projected_active_survives_confirmed_reply=None,
                has_ready_next_attacker_after_reply=None,
                next_attacker_can_ko=next_attacker_can_ko,
                next_attacker_confirmed_damage=(
                    next_attacker_confirmed_damage
                ),
                unsupported_reason=(
                    threat.unsupported_reason
                    or prize_exchange.unsupported_reason
                    or board_out.unsupported_reason
                    or next_attacker.unsupported_reason
                    or "reply_information_unsupported"
                ),
            )

        confirmed_loss_by_prize = (
            prize_exchange.confirmed_reply_wins_game
        )
        confirmed_loss_by_board_out = (
            board_out.confirmed_reply_causes_board_out
        )
        return DirectDecisionOutcomeFacts(
            supported=True,
            attack_id=attack_id,
            confirmed_damage=confirmed_damage,
            opponent_active_ko=opponent_active_ko,
            immediate_prizes_taken=(
                prize_exchange.immediate_prizes_taken
            ),
            candidate_wins_game=candidate_wins_game,
            reply_information_supported=True,
            confirmed_reply_damage=threat.best_confirmed_damage,
            confirmed_reply_ko=threat.can_ko_projected_active,
            confirmed_reply_prizes_lost=(
                prize_exchange.confirmed_reply_prizes_lost
            ),
            confirmed_loss_by_prize=confirmed_loss_by_prize,
            confirmed_loss_by_board_out=confirmed_loss_by_board_out,
            confirmed_loss=bool(
                confirmed_loss_by_prize
                or confirmed_loss_by_board_out
            ),
            net_prize_exchange=prize_exchange.net_prize_exchange,
            my_prizes_left_after_candidate=(
                prize_exchange.my_prizes_left_after_candidate
            ),
            opponent_prizes_left_after_reply=(
                prize_exchange.opponent_prizes_left_after_reply
            ),
            projected_active_survives_confirmed_reply=not bool(
                threat.can_ko_projected_active
            ),
            has_ready_next_attacker_after_reply=(
                next_attacker.confirmed_reply_has_ready_next_attacker
            ),
            next_attacker_can_ko=next_attacker_can_ko,
            next_attacker_confirmed_damage=(
                next_attacker_confirmed_damage
            ),
            unsupported_reason=None,
        )

    @staticmethod
    def _unsupported_direct_decision_outcome(
        reason: str,
        attack_id: Optional[int] = None,
    ) -> DirectDecisionOutcomeFacts:
        return DirectDecisionOutcomeFacts(
            supported=False,
            attack_id=attack_id,
            confirmed_damage=None,
            opponent_active_ko=None,
            immediate_prizes_taken=None,
            candidate_wins_game=None,
            reply_information_supported=False,
            confirmed_reply_damage=None,
            confirmed_reply_ko=None,
            confirmed_reply_prizes_lost=None,
            confirmed_loss_by_prize=None,
            confirmed_loss_by_board_out=None,
            confirmed_loss=None,
            net_prize_exchange=None,
            my_prizes_left_after_candidate=None,
            opponent_prizes_left_after_reply=None,
            projected_active_survives_confirmed_reply=None,
            has_ready_next_attacker_after_reply=None,
            next_attacker_can_ko=None,
            next_attacker_confirmed_damage=None,
            unsupported_reason=reason,
        )

    @classmethod
    def _projected_bench_for_next_attacker(
        cls,
        board: BoardView,
        result: SimulationResult,
        projection: CandidateProjectionFacts,
    ) -> Tuple[Optional[Tuple[Pokemon, ...]], Optional[str]]:
        option_type = getattr(result.option, "type", None)
        current_bench = tuple(getattr(board, "bench", ()) or ())
        is_switch = (
            option_type == OptionType.RETREAT
            or (
                getattr(getattr(board, "select", None), "context", None)
                == SelectContext.SWITCH
                and board.option_target(result.option) is not None
            )
        )
        if is_switch:
            if (
                option_type == OptionType.RETREAT
                and safe_int(result.outcome.retreat_energy_cost) > 0
            ):
                return None, "retreat_energy_discard_unresolved"
            target_serial = projection.projected_active_serial
            active = getattr(board, "active", None)
            active_serial = getattr(active, "serial", None)
            if target_serial is None or active is None or active_serial is None:
                return None, "missing_switch_projection_state"
            target_matches = tuple(
                pokemon
                for pokemon in current_bench
                if getattr(pokemon, "serial", None) == target_serial
            )
            if len(target_matches) != 1:
                return None, "ambiguous_switch_projection_target"
            return (
                tuple(
                    pokemon
                    for pokemon in current_bench
                    if getattr(pokemon, "serial", None) != target_serial
                )
                + (active,)
            ), None

        if option_type not in {
            OptionType.END,
            OptionType.ATTACK,
            OptionType.EVOLVE,
            OptionType.ATTACH,
        }:
            return None, "unsupported_next_attacker_action_type"
        return current_bench, None

    @staticmethod
    def _unsupported_next_attacker_facts(
        reason: Optional[str],
        projected_bench_count: Optional[int] = None,
    ) -> NextAttackerFacts:
        return NextAttackerFacts(
            supported=False,
            projected_bench_count=projected_bench_count,
            ready_next_attacker_exists=None,
            ready_next_attacker_count=None,
            best_confirmed_damage=None,
            can_ko_projected_opponent_active=None,
            best_next_attacker_card_id=None,
            best_next_attacker_serial=None,
            best_attack_id=None,
            usable_attack_ids=(),
            confirmed_reply_supported=False,
            confirmed_reply_ko=None,
            confirmed_reply_has_ready_next_attacker=None,
            unsupported_reason=reason or "next_attacker_unsupported",
        )

    @classmethod
    def _project_attack_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
    ) -> CandidateProjectionFacts:
        projection = cls.project(board, result)
        active = getattr(board, "active", None)
        opponent = getattr(board, "opp_active", None)
        if active is None or opponent is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_attack_state",
            )
        if (
            projection.confidence != CandidateProjectionConfidence.EXACT
            or not projection.combat_result_exact
        ):
            return cls._unsupported_facts(
                board,
                result,
                projection.unsupported_reason or "attack_projection_not_exact",
            )
        return cls._supported_facts(
            board,
            result,
            active=active,
            active_card_id=board.pid(active),
            active_hp=hp_left(active),
            active_max_hp=max_hp(active),
            energy_tokens=cls._exact_energy_tokens_as(
                board,
                active,
                board.pid(active),
            ),
            tool_ids=cls._tool_ids(active),
            opponent_hp=max(
                0,
                hp_left(opponent) - max(0, safe_int(result.outcome.damage)),
            ),
            terminal_win=bool(result.outcome.wins_game),
            opponent_active_ko=bool(result.outcome.knockout),
        )

    @classmethod
    def _project_switch_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
        source: str,
    ) -> CandidateProjectionFacts:
        active = getattr(board, "active", None)
        target = board.option_target(result.option)
        if active is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_current_active",
            )
        if target is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_explicit_switch_target",
            )
        if target not in getattr(board, "bench", ()):
            return cls._unsupported_facts(
                board,
                result,
                "invalid_switch_target",
            )
        if not result.outcome.supported:
            return cls._unsupported_facts(
                board,
                result,
                f"{source}_immediate_outcome_unsupported",
            )
        transition_reason = OpponentPublicThreatEvaluator(
            board
        )._public_retreat_effect_unsupported_reason(active, target)
        if transition_reason is not None:
            return cls._unsupported_facts(
                board,
                result,
                transition_reason,
            )
        return cls._supported_facts(
            board,
            result,
            active=target,
            active_card_id=board.pid(target),
            active_hp=hp_left(target),
            active_max_hp=max_hp(target),
            energy_tokens=cls._exact_energy_tokens_as(
                board,
                target,
                board.pid(target),
            ),
            tool_ids=cls._tool_ids(target),
            opponent_hp=cls._current_opponent_hp(board),
            terminal_win=False,
            opponent_active_ko=False,
        )

    @classmethod
    def _project_active_evolution_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
    ) -> CandidateProjectionFacts:
        target = board.option_target(result.option)
        evolution_id = board.option_card(result.option)
        if target is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_evolution_target",
            )
        if target is not getattr(board, "active", None):
            return cls._unsupported_facts(
                board,
                result,
                "evolution_target_not_active",
            )
        if (
            evolution_id is None
            or not board.evolves_from(evolution_id, target)
        ):
            return cls._unsupported_facts(
                board,
                result,
                "invalid_active_evolution",
            )
        evolution_data = board.data(evolution_id)
        if evolution_data is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_evolution_card_data",
            )
        if tuple(getattr(evolution_data, "skills", ()) or ()):
            return cls._unsupported_facts(
                board,
                result,
                "evolution_skill_effect_unmodeled",
            )

        tool_bonus = 0
        for tool_id in cls._tool_ids(target):
            tool_data = board.data(tool_id)
            kinds = classify_public_effect(tool_data)
            hp_bonus = public_hp_bonus(tool_data)
            if kinds == (PublicEffectKind.HP_AFFECTING,) and hp_bonus is not None:
                tool_bonus += hp_bonus
                continue
            if kinds == (PublicEffectKind.NO_RELEVANT_EFFECT,):
                continue
            return cls._unsupported_facts(
                board,
                result,
                "evolution_tool_effect_unmodeled",
            )

        evolved_max_hp = (
            safe_int(getattr(evolution_data, "hp", None), default=-1)
            + tool_bonus
        )
        if evolved_max_hp <= 0:
            return cls._unsupported_facts(
                board,
                result,
                "missing_evolution_hp",
            )
        damage_counters = damage_on(target)
        return cls._supported_facts(
            board,
            result,
            active=target,
            active_card_id=int(evolution_id),
            active_hp=max(0, evolved_max_hp - damage_counters),
            active_max_hp=evolved_max_hp,
            energy_tokens=cls._exact_energy_tokens_as(
                board,
                target,
                int(evolution_id),
            ),
            tool_ids=cls._tool_ids(target),
            opponent_hp=cls._current_opponent_hp(board),
            terminal_win=False,
            opponent_active_ko=False,
        )

    @classmethod
    def _project_attach_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
    ) -> CandidateProjectionFacts:
        active = getattr(board, "active", None)
        target = board.option_target(result.option)
        attached_card_id = board.option_card(result.option)
        if active is None or target is None or attached_card_id is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_attach_state",
            )
        if target is not active:
            return cls._unsupported_facts(
                board,
                result,
                "attach_target_not_active",
            )
        if not result.outcome.supported:
            return cls._unsupported_facts(
                board,
                result,
                "attach_immediate_outcome_unsupported",
            )
        attached_data = board.data(attached_card_id)
        attached_type = getattr(attached_data, "cardType", None)
        current_tokens = cls._exact_energy_tokens_as(
            board,
            active,
            board.pid(active),
        )
        if attached_type == CardType.BASIC_ENERGY:
            extra_tokens = energy_tokens_for_attach(
                int(attached_card_id),
                active,
            )
            if current_tokens is None or extra_tokens is None:
                return cls._unsupported_facts(
                    board,
                    result,
                    "unsupported_attach_energy",
                )
            return cls._supported_facts(
                board,
                result,
                active=active,
                active_card_id=board.pid(active),
                active_hp=hp_left(active),
                active_max_hp=max_hp(active),
                energy_tokens=current_tokens + tuple(extra_tokens),
                tool_ids=cls._tool_ids(active),
                opponent_hp=cls._current_opponent_hp(board),
                terminal_win=False,
                opponent_active_ko=False,
            )
        if attached_type == CardType.TOOL:
            hp_bonus = public_hp_bonus(attached_data)
            if (
                hp_bonus is None
                or hp_bonus <= 0
                or classify_public_effect(attached_data)
                != (PublicEffectKind.HP_AFFECTING,)
            ):
                return cls._unsupported_facts(
                    board,
                    result,
                    "unsupported_tool_attach_effect",
                )
            return cls._supported_facts(
                board,
                result,
                active=active,
                active_card_id=board.pid(active),
                active_hp=hp_left(active) + hp_bonus,
                active_max_hp=max_hp(active) + hp_bonus,
                energy_tokens=current_tokens,
                tool_ids=cls._tool_ids(active) + (int(attached_card_id),),
                opponent_hp=cls._current_opponent_hp(board),
                terminal_win=False,
                opponent_active_ko=False,
            )
        return cls._unsupported_facts(
            board,
            result,
            "unsupported_attach_card_type",
        )

    @classmethod
    def _project_unchanged_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
    ) -> CandidateProjectionFacts:
        active = getattr(board, "active", None)
        projection = cls.project(board, result)
        if active is None:
            return cls._unsupported_facts(
                board,
                result,
                "missing_current_active",
            )
        if projection.confidence != CandidateProjectionConfidence.EXACT:
            return cls._unsupported_facts(
                board,
                result,
                projection.unsupported_reason or "unchanged_projection_not_exact",
            )
        return cls._supported_facts(
            board,
            result,
            active=active,
            active_card_id=board.pid(active),
            active_hp=hp_left(active),
            active_max_hp=max_hp(active),
            energy_tokens=cls._exact_energy_tokens_as(
                board,
                active,
                board.pid(active),
            ),
            tool_ids=cls._tool_ids(active),
            opponent_hp=cls._current_opponent_hp(board),
            terminal_win=False,
            opponent_active_ko=False,
        )

    @classmethod
    def _supported_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
        *,
        active: Pokemon,
        active_card_id: int,
        active_hp: int,
        active_max_hp: int,
        energy_tokens: Optional[Tuple[Any, ...]],
        tool_ids: Tuple[int, ...],
        opponent_hp: Optional[int],
        terminal_win: bool,
        opponent_active_ko: bool,
    ) -> CandidateProjectionFacts:
        current = getattr(board, "active", None)
        return CandidateProjectionFacts(
            supported=True,
            option_type=getattr(result.option, "type", None),
            card_id=board.option_card(result.option),
            attack_id=getattr(result.option, "attackId", None),
            projected_active_card_id=int(active_card_id),
            projected_active_serial=getattr(active, "serial", None),
            projected_active_hp=max(0, int(active_hp)),
            projected_active_max_hp=max(0, int(active_max_hp)),
            projected_active_energy_tokens=energy_tokens,
            projected_active_tool_ids=tool_ids,
            projected_active_changed=bool(
                current is None
                or getattr(current, "serial", None)
                != getattr(active, "serial", None)
                or board.pid(current) != int(active_card_id)
            ),
            projected_opponent_active_hp=opponent_hp,
            terminal_win=terminal_win,
            opponent_active_ko=opponent_active_ko,
            unsupported_reason=None,
        )

    @classmethod
    def _unsupported_facts(
        cls,
        board: BoardView,
        result: SimulationResult,
        reason: str,
    ) -> CandidateProjectionFacts:
        return CandidateProjectionFacts(
            supported=False,
            option_type=getattr(result.option, "type", None),
            card_id=board.option_card(result.option),
            attack_id=getattr(result.option, "attackId", None),
            projected_active_card_id=None,
            projected_active_serial=None,
            projected_active_hp=None,
            projected_active_max_hp=None,
            projected_active_energy_tokens=None,
            projected_active_tool_ids=(),
            projected_active_changed=False,
            projected_opponent_active_hp=None,
            terminal_win=False,
            opponent_active_ko=False,
            unsupported_reason=reason,
        )

    @staticmethod
    def _tool_ids(pokemon: Pokemon) -> Tuple[int, ...]:
        return tuple(
            int(public_card.id)
            for public_card in tuple(
                getattr(pokemon, "tools", None) or ()
            )
        )

    @staticmethod
    def _current_opponent_hp(board: BoardView) -> Optional[int]:
        opponent = getattr(board, "opp_active", None)
        return None if opponent is None else hp_left(opponent)

    @staticmethod
    def _exact_energy_tokens_as(
        board: BoardView,
        pokemon: Pokemon,
        pokemon_card_id: int,
    ) -> Optional[Tuple[Any, ...]]:
        pokemon_data = board.data(pokemon_card_id)
        tokens: List[Any] = []
        for energy_id in tuple(board.energies(pokemon)):
            energy_tokens = attached_energy_tokens_for_card(
                board.data(energy_id),
                pokemon_data,
            )
            if energy_tokens is None:
                return None
            tokens.extend(energy_tokens)
        return tuple(tokens)

    @classmethod
    def _project_attack(cls, board: BoardView, result: SimulationResult) -> CandidateProjection:
        active = getattr(board, "active", None)
        outcome = result.outcome
        if active is None:
            return cls._unsupported(result, "missing_current_active")
        attack = board.attack(getattr(result.option, "attackId", None))
        if attack is None:
            return cls._unsupported(result, "missing_attack_definition")

        limitations = list(cls._attack_projection_limitations(attack))
        target = getattr(board, "opp_active", None)
        if target is not None:
            limitations.extend(
                cls._public_damage_projection_limitations(
                    board,
                    active,
                    target,
                    attack,
                )
            )
        if not outcome.supported:
            limitations.insert(0, "attack_immediate_outcome_unsupported")
        if cls._has_unmodeled_between_turn_damage(board):
            limitations.append("between_turn_effect_unmodeled")
        limitations = list(cls._unique(limitations))
        confidence = (
            CandidateProjectionConfidence.UNSUPPORTED
            if not outcome.supported
            else CandidateProjectionConfidence.PARTIAL
            if limitations
            else CandidateProjectionConfidence.EXACT
        )
        combat_result_exact = bool(
            outcome.supported
            and not cls._combat_result_limitations(limitations)
        )
        readiness_unknown = any(
            reason in limitations
            for reason in {
                "self_damage_attack_unmodeled",
                "attack_switch_effect_unmodeled",
                "attack_active_leaves_play_unmodeled",
                "energy_discard_projection_unmodeled",
            }
        )
        next_ready = cls._pokemon_energy_ready(board, active) and not readiness_unknown
        reasons = cls._unique(
            ("attack_projection",)
            + tuple(outcome.reasons)
            + tuple(limitations)
        )
        return CandidateProjection(
            option_index=result.index,
            option_type=result.option.type,
            confidence=confidence,
            combat_result_exact=combat_result_exact,
            terminal_win=bool(outcome.wins_game),
            damage_to_opponent=max(0, safe_int(outcome.damage)),
            opponent_active_ko=bool(outcome.knockout),
            prizes_taken=max(0, safe_int(outcome.prizes_taken)),
            projected_active_serial=getattr(active, "serial", None),
            projected_active_card_id=board.pid(active),
            projected_active_hp=hp_left(active),
            projected_active_prize_value=board.prize_value(active),
            projected_active_can_attack=False,
            next_attacker_ready=next_ready,
            ends_turn=True,
            unsupported_reason=limitations[0] if limitations else None,
            reasons=reasons,
        )

    @classmethod
    def _project_retreat(cls, board: BoardView, result: SimulationResult) -> CandidateProjection:
        if getattr(board, "active", None) is None:
            return cls._unsupported(result, "missing_current_active")
        outcome = result.outcome
        target_serial = (
            outcome.target_serial
            if outcome.target_serial is not None
            else outcome.recommended_target_serial
        )
        target_id = (
            outcome.target_id
            if outcome.target_id is not None
            else outcome.recommended_target_id
        )
        if target_serial is None:
            return cls._unsupported(result, "missing_retreat_target")
        matches = [
            target
            for target in getattr(board, "bench", ())
            if getattr(target, "serial", None) == target_serial
        ]
        if len(matches) != 1:
            reason = "ambiguous_retreat_target" if len(matches) > 1 else "missing_retreat_target"
            return cls._unsupported(result, reason)
        target = matches[0]
        if target_id is not None and board.pid(target) != target_id:
            return cls._unsupported(result, "retreat_target_mismatch")
        if not outcome.supported:
            return cls._unsupported(result, "retreat_immediate_outcome_unsupported")

        retreat_limitation = OpponentPublicThreatEvaluator(
            board
        )._public_retreat_effect_unsupported_reason(board.active, target)
        ready = (
            retreat_limitation is None
            and cls._pokemon_energy_ready(board, target)
            and active_can_declare_attack_this_turn_for_board(board)
        )
        reasons = cls._unique(
            ("retreat_projection",)
            + tuple(outcome.reasons)
            + ((retreat_limitation,) if retreat_limitation is not None else ())
        )
        return CandidateProjection(
            option_index=result.index,
            option_type=result.option.type,
            confidence=(
                CandidateProjectionConfidence.PARTIAL
                if retreat_limitation is not None
                else CandidateProjectionConfidence.EXACT
            ),
            combat_result_exact=retreat_limitation is None,
            terminal_win=False,
            damage_to_opponent=0,
            opponent_active_ko=False,
            prizes_taken=0,
            projected_active_serial=getattr(target, "serial", None),
            projected_active_card_id=board.pid(target),
            projected_active_hp=hp_left(target),
            projected_active_prize_value=board.prize_value(target),
            projected_active_can_attack=ready,
            next_attacker_ready=ready,
            ends_turn=False,
            unsupported_reason=retreat_limitation,
            reasons=reasons,
        )

    @classmethod
    def _project_end(cls, board: BoardView, result: SimulationResult) -> CandidateProjection:
        active = getattr(board, "active", None)
        if active is None:
            return cls._unsupported(result, "missing_current_active")
        limitations = cls._end_projection_limitations(board)
        return CandidateProjection(
            option_index=result.index,
            option_type=result.option.type,
            confidence=(
                CandidateProjectionConfidence.PARTIAL
                if limitations
                else CandidateProjectionConfidence.EXACT
            ),
            combat_result_exact=True,
            terminal_win=False,
            damage_to_opponent=0,
            opponent_active_ko=False,
            prizes_taken=0,
            projected_active_serial=getattr(active, "serial", None),
            projected_active_card_id=board.pid(active),
            projected_active_hp=hp_left(active),
            projected_active_prize_value=board.prize_value(active),
            projected_active_can_attack=False,
            next_attacker_ready=(
                cls._pokemon_energy_ready(board, active)
                and not limitations
            ),
            ends_turn=True,
            unsupported_reason=limitations[0] if limitations else None,
            reasons=("end_current_public_board",) + limitations,
        )

    @classmethod
    def _unsupported(cls, result: SimulationResult, reason: str) -> CandidateProjection:
        return CandidateProjection(
            option_index=result.index,
            option_type=getattr(result.option, "type", None),
            confidence=CandidateProjectionConfidence.UNSUPPORTED,
            combat_result_exact=False,
            terminal_win=False,
            damage_to_opponent=0,
            opponent_active_ko=False,
            prizes_taken=0,
            projected_active_serial=None,
            projected_active_card_id=None,
            projected_active_hp=None,
            projected_active_prize_value=None,
            projected_active_can_attack=False,
            next_attacker_ready=False,
            ends_turn=False,
            unsupported_reason=reason,
            reasons=(reason,),
        )

    @staticmethod
    def _pokemon_energy_ready(board: BoardView, pokemon: Pokemon) -> bool:
        data = board.data(board.pid(pokemon))
        if data is None:
            return False
        return any(
            attack is not None and board.can_pay_attack(pokemon, attack)
            for attack in (board.attack(attack_id) for attack_id in getattr(data, "attacks", ()))
        )

    @classmethod
    def _attack_projection_limitations(cls, attack: Any) -> Tuple[str, ...]:
        text = _normalized_attack_text(attack)
        reasons: List[str] = []
        if attack_can_damage_opponent_bench(attack):
            reasons.append("multi_ko_unmodeled")
        if "damage counter" in text:
            reasons.append("damage_counter_effect_unmodeled")
        if (
            "damage to itself" in text
            or "damage to this pokemon" in text
            or ("put" in text and "damage counter" in text and "this pokemon" in text)
        ):
            reasons.append("self_damage_attack_unmodeled")
        if "heal" in text and "this pokemon" in text:
            reasons.append("self_heal_attack_unmodeled")
        if "switch this pokemon with" in text or "switch out this pokemon" in text:
            reasons.append("attack_switch_effect_unmodeled")
        if (
            "return this pokemon" in text
            or "shuffle this pokemon" in text
            or "put this pokemon and all attached cards" in text
        ):
            reasons.append("attack_active_leaves_play_unmodeled")
        if (
            ("discard" in text or "move" in text)
            and "energy" in text
            and ("this pokemon" in text or "attached to this pokemon" in text)
        ):
            reasons.append("energy_discard_projection_unmodeled")
        if (
            ("attach" in text or "move" in text)
            and "energy" in text
            and ("your benched pokemon" in text or "to your pokemon" in text)
        ):
            reasons.append("attack_board_effect_unmodeled")
        if "tool" in text or "stadium" in text:
            reasons.append("tool_stadium_effect_unmodeled")
        if any(
            marker in text
            for marker in (
                "is now asleep",
                "is now burned",
                "is now confused",
                "is now paralyzed",
                "is now poisoned",
            )
        ):
            reasons.append("opponent_status_effect_unmodeled")
        if "during your opponent's next turn" in text:
            reasons.append("delayed_attack_effect_unmodeled")
        return cls._unique(reasons)

    @staticmethod
    def _combat_result_limitations(limitations: Sequence[str]) -> Tuple[str, ...]:
        combat_reasons = {
            "attack_immediate_outcome_unsupported",
            "multi_ko_unmodeled",
            "damage_counter_effect_unmodeled",
            "tool_stadium_effect_unmodeled",
            "weakness_resistance_damage_unmodeled",
            "public_damage_effect_unclassified",
            "public_stadium_damage_modifier_unmodeled",
            "public_stadium_damage_effect_unknown",
            "public_stadium_weakness_resistance_unmodeled",
            "public_tool_damage_modifier_unmodeled",
            "public_tool_damage_effect_unknown",
            "public_tool_weakness_resistance_unmodeled",
            "public_after_damage_effect_unmodeled",
        }
        return tuple(reason for reason in limitations if reason in combat_reasons)

    @classmethod
    def _public_damage_projection_limitations(
        cls,
        board: BoardView,
        attacker: Pokemon,
        target: Pokemon,
        attack: Any,
    ) -> Tuple[str, ...]:
        reasons: List[str] = []
        public_effect_reason = OpponentPublicThreatEvaluator(
            board
        )._public_damage_effect_unsupported_reason(attacker, target)
        if public_effect_reason is not None:
            if public_effect_reason in {
                "public_stadium_damage_effect_unknown",
                "public_tool_damage_effect_unknown",
            }:
                reasons.append("public_damage_effect_unclassified")
            reasons.append(public_effect_reason)

        for public_card in (
            tuple(getattr(getattr(board, "state", None), "stadium", None) or ())
            + tuple(getattr(attacker, "tools", None) or ())
            + tuple(getattr(target, "tools", None) or ())
        ):
            if PublicEffectKind.AFTER_DAMAGE_TRIGGERED_EFFECT in classify_public_effect(
                board.data(card_id(public_card))
            ):
                reasons.append("public_after_damage_effect_unmodeled")

        text = _normalized_attack_text(attack)
        ignores_weakness_resistance = (
            "isn't affected by weakness or resistance" in text
            or "is not affected by weakness or resistance" in text
        )
        if not ignores_weakness_resistance:
            modifier_match = public_attack_matches_weakness_or_resistance(
                board,
                attacker,
                target,
                attack,
            )
            if modifier_match is not False:
                reasons.append("weakness_resistance_damage_unmodeled")
        return cls._unique(reasons)

    @classmethod
    def _end_projection_limitations(cls, board: BoardView) -> Tuple[str, ...]:
        player = getattr(board, "me", None)
        reasons: List[str] = []
        if getattr(player, "asleep", False):
            reasons.append("asleep_next_attack_uncertain")
        if getattr(player, "confused", False):
            reasons.append("confused_attack_outcome_uncertain")
        if getattr(player, "paralyzed", False):
            reasons.append("paralyzed_next_attack_uncertain")
        if cls._has_unmodeled_between_turn_damage(board):
            reasons.append("between_turn_effect_unmodeled")
        return cls._unique(reasons)

    @staticmethod
    def _has_unmodeled_between_turn_damage(board: BoardView) -> bool:
        player = getattr(board, "me", None)
        return bool(
            getattr(player, "burned", False)
            or getattr(player, "poisoned", False)
        )

    @staticmethod
    def _unique(reasons: Iterable[str]) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(reasons))


def phase3_prepared_attack_binding_facts(
    adapter: str,
    origin_board: BoardView,
    origin_result: Optional[SimulationResult],
    decision_board: BoardView,
    decision: P6AttackDecisionInputFacts,
) -> Phase3PreparedAttackBindingFacts:
    if not adapter:
        raise ValueError("phase3_adapter_required")
    if not _result_option_is_current(origin_board, origin_result):
        return Phase3PreparedAttackBindingFacts(
            adapter=adapter,
            origin_option_index=None,
            supported=False,
            candidate=None,
            unsupported_reason="phase3_origin_option_not_current",
        )

    origin_option_index = origin_result.index
    decision_option_index = decision.decision_option_index
    if (
        decision_option_index is not None
        and decision_option_index != origin_option_index
    ):
        return Phase3PreparedAttackBindingFacts(
            adapter=adapter,
            origin_option_index=origin_option_index,
            supported=False,
            candidate=None,
            unsupported_reason="phase3_origin_option_index_mismatch",
        )
    outcome = CandidateProjectionEvaluator.attack_decision_outcome_facts(
        decision_board,
        decision,
    )
    return Phase3PreparedAttackBindingFacts(
        adapter=adapter,
        origin_option_index=origin_option_index,
        supported=outcome.supported,
        candidate=DirectAttackShadowCandidate(
            option_index=origin_option_index,
            attack_id=decision.attack_id,
            facts=outcome,
        ),
        unsupported_reason=(
            None
            if outcome.supported
            else (
                outcome.unsupported_reason
                or decision.unsupported_reason
                or "phase3_prepared_adapter_unsupported"
            )
        ),
    )


def phase3_direct_attack_shadow_facts(
    board: BoardView,
    results: Sequence[SimulationResult],
    prepared_bindings: Sequence[Phase3PreparedAttackBindingFacts],
) -> Phase3DirectAttackShadowFacts:
    current = current_direct_attack_candidate_facts(board, results)
    blocked_reasons = list(current.blocked_reasons)
    bindings_list: List[Phase3PreparedAttackBindingFacts] = []
    prepared_duplicate_deduplications = 0
    for binding in prepared_bindings:
        if binding in bindings_list:
            prepared_duplicate_deduplications += 1
            continue
        bindings_list.append(binding)
        if binding.candidate is None:
            blocked_reasons.append(
                f"{binding.adapter}:{binding.unsupported_reason}"
            )
    bindings = tuple(bindings_list)
    candidate_bindings = tuple(
        binding for binding in bindings if binding.candidate is not None
    )
    bindings_by_origin: Dict[int, List[Phase3PreparedAttackBindingFacts]] = {}
    for binding in candidate_bindings:
        bindings_by_origin.setdefault(binding.origin_option_index, []).append(
            binding
        )
    origin_conflicts = tuple(sorted(
        origin_option_index
        for origin_option_index, origin_bindings
        in bindings_by_origin.items()
        if len({binding.adapter for binding in origin_bindings}) > 1
    ))
    multiple_prepared_attack_origins = tuple(sorted(
        origin_option_index
        for origin_option_index, origin_bindings
        in bindings_by_origin.items()
        if len({
            (binding.candidate.attack_id, binding.candidate.facts)
            for binding in origin_bindings
        }) > 1
    ))
    prepared_candidates = tuple(
        binding.candidate for binding in candidate_bindings
    )
    comparisons = tuple(
        Phase3CurrentPreparedComparisonFacts(
            current_candidate=current_candidate,
            prepared_binding=prepared_binding,
            result=compare_direct_attack_candidates(
                current_candidate,
                prepared_binding.candidate,
            ),
        )
        for current_candidate in current.candidates
        for prepared_binding in candidate_bindings
    )
    return Phase3DirectAttackShadowFacts(
        current_candidates=current.candidates,
        prepared_bindings=bindings,
        prepared_candidates=prepared_candidates,
        prepared_duplicate_deduplications=prepared_duplicate_deduplications,
        multiple_prepared_attack_origins=multiple_prepared_attack_origins,
        origin_conflicts=origin_conflicts,
        blocked_reasons=tuple(blocked_reasons),
        comparisons=comparisons,
    )


def current_direct_attack_candidate_facts(
    board: BoardView,
    results: Sequence[SimulationResult],
) -> CurrentDirectAttackCandidateFacts:
    candidates: List[DirectAttackShadowCandidate] = []
    blocked_reasons: List[str] = []
    for result in results:
        option = getattr(result, "option", None)
        if (
            getattr(option, "type", None) != OptionType.ATTACK
            or getattr(option, "attackId", None) is None
        ):
            continue
        if not _result_option_is_current(board, result):
            blocked_reasons.append("current_attack_option_not_current")
            continue
        projection = CandidateProjectionEvaluator.project_facts(board, result)
        decision = CandidateProjectionEvaluator.direct_attack_p6_input_facts(
            board,
            result,
            projection,
        )
        if decision.decision_option_index != result.index:
            blocked_reasons.append("current_attack_option_index_mismatch")
            continue
        outcome = CandidateProjectionEvaluator.attack_decision_outcome_facts(
            board,
            decision,
        )
        candidates.append(DirectAttackShadowCandidate(
            option_index=result.index,
            attack_id=decision.attack_id,
            facts=outcome,
        ))
    return CurrentDirectAttackCandidateFacts(
        candidates=tuple(candidates),
        blocked_reasons=tuple(blocked_reasons),
    )


def _phase4_uncertain_action_facts(
    board: BoardView,
    result: SimulationResult,
) -> Optional[Phase4UncertainActionFacts]:
    option = getattr(result, "option", None)
    if getattr(option, "type", None) == OptionType.ATTACK:
        return None
    outcome = getattr(result, "outcome", None)
    if not isinstance(outcome, ImmediateOutcome):
        return None

    evidence_reasons: List[str] = []

    def evidence(name: str, present: bool) -> bool:
        if present:
            evidence_reasons.append(name)
        return present

    self_preparation = any((
        evidence("enables_attack", outcome.enables_attack),
        evidence("enabled_attack_ids", bool(outcome.enabled_attack_ids)),
        evidence("avoids_wall", outcome.avoids_wall),
        evidence("improves_damage", outcome.improves_damage),
        evidence("completes_next_attacker", outcome.completes_next_attacker),
    ))
    opponent_disruption = any((
        evidence("breaks_engine", outcome.breaks_engine),
        evidence("removes_tool", outcome.removes_tool),
        evidence("board_energy_removed", outcome.board_energy_removed > 0),
    ))
    board_development = any((
        evidence(
            "develops_bench_next_attacker",
            outcome.develops_bench_next_attacker,
        ),
        evidence("completes_evolution_line", outcome.completes_evolution_line),
        evidence(
            "completed_same_line_attackers",
            outcome.completed_same_line_attackers > 0,
        ),
        evidence(
            "post_evolution_ready_attack_count",
            outcome.post_evolution_ready_attack_count > 0,
        ),
    ))
    healing_survival = any((
        evidence("healed_damage", outcome.healed_damage > 0),
        evidence("recovered_energy_count", outcome.recovered_energy_count > 0),
        evidence("next_knockout_avoided", outcome.next_knockout_avoided),
        evidence("avoids_prize_loss", outcome.avoids_prize_loss),
        evidence("prizes_preserved", outcome.prizes_preserved > 0),
        evidence("avoids_board_out", outcome.avoids_board_out),
        evidence("preserves_primary_pokemon", outcome.preserves_primary_pokemon),
        evidence("evolution_hp_gain", outcome.evolution_hp_gain > 0),
    ))
    has_evidence = any((
        self_preparation,
        opponent_disruption,
        board_development,
        healing_survival,
    ))
    legal = _result_option_is_current(board, result)
    if not legal:
        uncertainty_reasons = ("action_not_current",)
    elif not outcome.supported:
        uncertainty_reasons = (
            tuple(outcome.reasons)
            or ("immediate_outcome_unsupported",)
        )
    elif not has_evidence:
        uncertainty_reasons = ("no_existing_uncertain_action_evidence",)
    else:
        uncertainty_reasons = tuple(
            reason
            for present, reason in (
                (self_preparation, "prepared_outcome_not_confirmed"),
                (opponent_disruption, "opponent_reply_after_disruption_unknown"),
                (board_development, "development_continuation_unknown"),
                (healing_survival, "survival_continuation_unknown"),
            )
            if present
        )
    uncertain_action_supported = (
        legal
        and outcome.supported
        and has_evidence
        and bool(uncertainty_reasons)
    )
    return Phase4UncertainActionFacts(
        option_index=result.index,
        option_type=getattr(option, "type", None),
        legal=legal,
        immediate_outcome_supported=outcome.supported,
        self_preparation=self_preparation,
        opponent_disruption=opponent_disruption,
        board_development=board_development,
        healing_survival=healing_survival,
        evidence_reasons=tuple(evidence_reasons),
        uncertainty_reasons=uncertainty_reasons,
        uncertain_action_supported=uncertain_action_supported,
    )


def phase4_current_value_gate_facts(
    board: BoardView,
    results: Sequence[SimulationResult],
) -> Phase4CurrentValueGateFacts:
    current = current_direct_attack_candidate_facts(board, results)
    current_candidates = current.candidates
    current_states = tuple(
        classify_direct_attack_candidate(candidate.facts)
        for candidate in current_candidates
    )
    supported_candidates = tuple(
        candidate
        for candidate in current_candidates
        if candidate.facts.supported
    )

    def protected_candidate(
        candidate: DirectAttackShadowCandidate,
    ) -> bool:
        return (
            candidate.facts.supported
            and candidate.facts.confirmed_loss is not True
        )

    current_has_immediate_win = any(
        protected_candidate(candidate)
        and candidate.facts.candidate_wins_game is True
        for candidate in current_candidates
    )
    current_has_confirmed_ko = any(
        protected_candidate(candidate)
        and candidate.facts.opponent_active_ko is True
        for candidate in current_candidates
    )
    current_has_confirmed_prize_gain = any(
        protected_candidate(candidate)
        and candidate.facts.immediate_prizes_taken is not None
        and candidate.facts.immediate_prizes_taken > 0
        for candidate in current_candidates
    )
    current_has_confirmed_loss = any(
        candidate.facts.supported
        and candidate.facts.confirmed_loss is True
        for candidate in current_candidates
    )
    current_has_reply_unknown = (
        DirectAttackCandidateState.REPLY_UNKNOWN in current_states
    )
    current_has_overall_unsupported = (
        DirectAttackCandidateState.OVERALL_UNSUPPORTED in current_states
    )
    current_has_partial_unknown = (
        DirectAttackCandidateState.PARTIAL_UNKNOWN in current_states
    )
    current_has_confirmed_non_ko_no_prize = any(
        candidate.facts.supported
        and candidate.facts.confirmed_loss is not True
        and candidate.facts.candidate_wins_game is False
        and candidate.facts.opponent_active_ko is False
        and candidate.facts.immediate_prizes_taken == 0
        for candidate in current_candidates
    )
    uncertain_actions = tuple(
        facts
        for result in results
        for facts in (_phase4_uncertain_action_facts(board, result),)
        if facts is not None
    )
    uncertain_action_supported = any(
        facts.uncertain_action_supported for facts in uncertain_actions
    )

    protected_reasons = tuple(
        reason
        for present, reason in (
            (
                current_has_immediate_win,
                Phase4CurrentValueGateReason.CURRENT_IMMEDIATE_WIN,
            ),
            (
                current_has_confirmed_ko,
                Phase4CurrentValueGateReason.CURRENT_CONFIRMED_KO,
            ),
            (
                current_has_confirmed_prize_gain,
                Phase4CurrentValueGateReason.CURRENT_CONFIRMED_PRIZE_GAIN,
            ),
        )
        if present
    )
    if protected_reasons:
        gate_open = False
        gate_reasons = protected_reasons
    elif not uncertain_action_supported:
        gate_open = False
        gate_reasons = (
            Phase4CurrentValueGateReason.UNCERTAIN_ACTION_UNSUPPORTED,
        )
    else:
        open_reasons: List[Phase4CurrentValueGateReason] = []
        if not current_candidates:
            open_reasons.append(
                Phase4CurrentValueGateReason.NO_LEGAL_CURRENT_ATTACK
            )
        if current_candidates and not supported_candidates:
            open_reasons.append(
                Phase4CurrentValueGateReason.NO_SUPPORTED_CURRENT_ATTACK
            )
        if current_has_overall_unsupported:
            open_reasons.append(
                Phase4CurrentValueGateReason.CURRENT_HAS_OVERALL_UNSUPPORTED
            )
        if current_has_reply_unknown:
            open_reasons.append(
                Phase4CurrentValueGateReason.CURRENT_HAS_REPLY_UNKNOWN
            )
        if current_has_partial_unknown:
            open_reasons.append(
                Phase4CurrentValueGateReason.CURRENT_HAS_PARTIAL_UNKNOWN
            )
        if current_has_confirmed_loss:
            open_reasons.append(
                Phase4CurrentValueGateReason.CURRENT_HAS_CONFIRMED_LOSS
            )
        if current_has_confirmed_non_ko_no_prize:
            open_reasons.append(
                Phase4CurrentValueGateReason.CURRENT_CONFIRMED_NON_KO_NO_PRIZE
            )
        gate_open = bool(open_reasons)
        gate_reasons = tuple(open_reasons) or (
            Phase4CurrentValueGateReason.CURRENT_VALUE_NOT_GATE_ELIGIBLE,
        )

    return Phase4CurrentValueGateFacts(
        current_candidates=current_candidates,
        current_candidate_count=len(current_candidates),
        current_supported_candidate_count=len(supported_candidates),
        current_states=current_states,
        current_has_immediate_win=current_has_immediate_win,
        current_has_confirmed_ko=current_has_confirmed_ko,
        current_has_confirmed_prize_gain=current_has_confirmed_prize_gain,
        current_has_confirmed_loss=current_has_confirmed_loss,
        current_has_reply_unknown=current_has_reply_unknown,
        current_has_overall_unsupported=current_has_overall_unsupported,
        current_has_partial_unknown=current_has_partial_unknown,
        current_has_confirmed_non_ko_no_prize=(
            current_has_confirmed_non_ko_no_prize
        ),
        uncertain_actions=uncertain_actions,
        uncertain_action_supported=uncertain_action_supported,
        gate_open=gate_open,
        gate_reason=gate_reasons[0],
        gate_reasons=gate_reasons,
    )


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
        if (
            context == SelectContext.DISCARD_TOOL_CARD
            and self.effect_id() == TOOL_SCRAPPER
        ):
            return self.score_tool_scrapper_target_option(
                index,
                option,
            )
        if context == SelectContext.TO_ACTIVE:
            return self.score_promotion_target(option)
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
        if option.type == OptionType.ATTACH and cid == HERO_CAPE:
            if not outcome.supported:
                return ActionScore(
                    TIER_BLOCKED_OR_BAD_ACTION,
                    legacy=legacy_score,
                )
            if outcome.next_knockout_avoided:
                return ActionScore(
                    TIER_HIGH_VALUE_PREP,
                    legacy=legacy_score,
                )
            return ActionScore(
                TIER_BLOCKED_OR_BAD_ACTION,
                legacy=legacy_score,
            )
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
        if option.type == OptionType.PLAY and cid == POKE_PAD:
            if not outcome.supported or outcome.development_value <= 0:
                return ActionScore(
                    TIER_BLOCKED_OR_BAD_ACTION,
                    risk=1,
                    legacy=legacy_score,
                )
            if outcome.reachable_attack_id is not None:
                return ActionScore(
                    TIER_NON_KO_ATTACK,
                    pressure=outcome.reachable_attack_pressure,
                    development=outcome.development_value,
                )
            return ActionScore(
                TIER_LOW_VALUE_ACTION,
                resource=outcome.development_value,
            )
        if self.effect_id() == POKE_PAD and cid is not None:
            facts = self.b.poke_pad_target_facts(
                cid,
                visible_search_candidate=True,
            )
            if facts is None:
                return ActionScore(TIER_FORBIDDEN)
            if cid == CINDERACE or not facts.same_turn_deployable:
                return ActionScore(
                    TIER_LOW_VALUE_ACTION,
                    risk=1,
                )
            return ActionScore(
                TIER_LOW_VALUE_ACTION,
                resource=max(0, legacy_score),
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
                development=(
                    0
                    if (
                        outcome.equivalent_evolution_available
                        or self.has_competing_current_development_option()
                    )
                    else outcome.development_value
                ),
                resource=0,
                legacy=legacy_score,
            )
        safe_pre_ko_basic_play = (
            self.safe_pre_ko_basic_play_action_score(
                option,
                legacy_score,
                outcome,
            )
        )
        if safe_pre_ko_basic_play is not None:
            return safe_pre_ko_basic_play
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

    @staticmethod
    def _played_basic_has_ability(
        card_data: Any,
    ) -> bool:
        for attribute in ("ability", "abilities"):
            value = getattr(card_data, attribute, None)
            if value not in (None, "", (), []):
                return True
        return False

    def _best_current_nonwinning_knockout(
        self,
    ) -> Optional[
        Tuple[Any, ImmediateOutcome, float, int]
    ]:
        candidates: List[
            Tuple[Any, ImmediateOutcome, float, int]
        ] = []

        for index, candidate in self.b.iter_options():
            if (
                candidate.type != OptionType.ATTACK
                and candidate.attackId is None
            ):
                continue

            attack_outcome = self.outcome.evaluate_attack(
                candidate
            )

            if (
                not attack_outcome.supported
                or attack_outcome.blocked
                or not attack_outcome.knockout
                or attack_outcome.wins_game
            ):
                continue

            candidates.append((
                candidate,
                attack_outcome,
                self.score_attack(candidate),
                index,
            ))

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
                item[1].prizes_taken,
                item[1].damage,
                item[2],
                -item[3],
            ),
        )

    def _basic_play_preserves_current_knockout(
        self,
        option: Any,
        attack_option: Any,
    ) -> bool:
        played_card_id = self.b.option_card(option)
        if played_card_id is None:
            return False

        played_card_data = self.b.data(played_card_id)

        # 場に出した瞬間に公開Abilityが影響するBasicは、
        # この最小修正では安全を証明できないため対象外。
        if (
            played_card_data is None
            or self._played_basic_has_ability(
                played_card_data
            )
        ):
            return False

        attack = self.b.attack(
            attack_option.attackId
        )
        if attack is None:
            return False

        text = _normalized_attack_text(attack)

        # Basic PLAYによって変化するのは、
        # 自分の手札枚数・Bench数・場のPokémon数。
        # それらをdamage入力に使うAttackは対象外にする。
        changed_own_state_markers = (
            "your hand",
            "cards in your hand",
            "your benched pokemon",
            "pokemon on your bench",
            "your pokemon in play",
            "pokemon you have in play",
            "number of your pokemon",
        )

        return not any(
            marker in text
            for marker in changed_own_state_markers
        )

    def safe_pre_ko_basic_play_action_score(
        self,
        option: Any,
        legacy_score: float,
        outcome: ImmediateOutcome,
    ) -> Optional[ActionScore]:
        if (
            option.type != OptionType.PLAY
            or not outcome.supported
            or not outcome.adds_board_out_buffer
            or len(self.b.bench) != 0
            or self.b.bench_space <= 0
            or not self.b.is_basic_pokemon(
                self.b.option_card(option)
            )
        ):
            return None

        preserved = (
            self._best_current_nonwinning_knockout()
        )
        if preserved is None:
            return None

        (
            attack_option,
            attack_outcome,
            _,
            _,
        ) = preserved

        if not self._basic_play_preserves_current_knockout(
            option,
            attack_option,
        ):
            return None

        return ActionScore(
            TIER_KO,
            immediate=attack_outcome.prizes_taken,
            pressure=attack_outcome.damage,
            development=int(
                outcome.adds_board_out_buffer
            ),
            legacy=legacy_score,
        )

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
            if cid in {
                BEFEHL_VON_BOSS,
                SURFING_BEACH,
                WALLY_COMPASSION,
                SALVATORE,
                ULTRA_BALL,
            }:
                return False
            return legacy_score >= 50000
        
        
        if option.type == OptionType.EVOLVE:
            target = self.b.option_target(option)
            return target is not None and target is not self.b.active and legacy_score >= 50000
        return False

    def has_competing_current_development_option(self) -> bool:
        for _, option in self.b.iter_options():
            if (
                option.type == OptionType.PLAY
                and self.b.is_basic_pokemon(self.b.option_card(option))
                and self.score_pokemon_play(self.b.option_card(option))
                > SCORE_FORBIDDEN
            ):
                return True
            if option.type == OptionType.EVOLVE:
                return True
            if option.type == OptionType.ATTACH:
                attach_outcome = self.outcome.evaluate_attach(option)
                if (
                    attach_outcome.supported
                    and (
                        attach_outcome.enables_attack
                        or attach_outcome.enables_knockout
                        or attach_outcome.improves_damage
                    )
                ):
                    return True
        return False

    def prep_development_value(self, option: Any, legacy_score: float) -> float:
        if option.type == OptionType.EVOLVE:
            return max(legacy_score, 120000)
        if option.type == OptionType.PLAY:
            return min(max(legacy_score, 60000), 260000)
        return max(0, legacy_score)
    def score_promotion_target(self, option: Any) -> float:
        target = self.b.option_target(option)
        if target is None or target not in self.b.bench:
            return SCORE_FORBIDDEN

        target_role = self.b.role_facts(target)
        target_damage = self.outcome._best_unblocked_damage_from(target)
        target_ready = (
            target_role.ready_if_promoted
            and target_damage > 0
        )

        ready_candidate_exists = False
        for _, candidate in self.b.iter_options():
            candidate_target = self.b.option_target(candidate)
            if (
                candidate_target is None
                or candidate_target not in self.b.bench
            ):
                continue

            candidate_role = self.b.role_facts(candidate_target)
            candidate_damage = self.outcome._best_unblocked_damage_from(
                candidate_target
            )

            if (
                candidate_role.ready_if_promoted
                and candidate_damage > 0
            ):
                ready_candidate_exists = True
                break

        # 攻撃準備済み候補が確認できる場合だけ、promotion順位を上書きする。
        # 1体も準備できていない場合は、未確定の新方針を作らず現行fallbackを維持。
        if not ready_candidate_exists:
            return self.score_card_selection(option)

        if not target_ready:
            return SCORE_LAST_RESORT

        knockout_bonus = (
            SCORE_PREFERRED // 4
            if (
                self.b.opp_active is not None
                and target_damage >= hp_left(self.b.opp_active)
            )
            else 0
        )

        return (
            SCORE_PREFERRED // 2
            + knockout_bonus
            + target_damage * 1000
            + hp_left(target)
        )

    def score_setup(self, option: Any) -> float:
        cid = self.b.option_card(option)
        if self.b.select.context == SelectContext.SETUP_ACTIVE_POKEMON:
            if cid == CINDERACE and self.b.cinderace_setup_role_live():
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
            if any(card in self.b.hand_ids for card in {POFIN, TANKER, ULTRA_BALL, POKEGEAR, LILLIE_DETERMINATION}):
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
                if any(card in self.b.hand_ids for card in {POFIN, ULTRA_BALL, POKEGEAR, SALVATORE, MEGA_SIGNAL, LILLIE_DETERMINATION, CRISPIN, TANKER}):
                    return 50000
                turbo_score = SCORE_PREFERRED + 100000
                if self.b.count_in_play(MEGA_STARMIE_EX) == 0 and self.b.count_in_play(MEGA_YUKIMENOKO_EX) == 0:
                    turbo_score += 120000
                if not any(card in self.b.hand_ids for card in {ULTRA_BALL, SALVATORE, MEGA_STARMIE_EX}):
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

    def judge_has_important_non_supporter_action(self) -> bool:
        for _, option in self.b.iter_options():
            cid = self.b.option_card(option)
            if option.type == OptionType.PLAY:
                if self.b.is_supporter(cid):
                    continue
                if self.score_main(option) > 6000:
                    return True
                continue
            if option.type == OptionType.EVOLVE:
                if self.score_evolve(option) > 6000:
                    return True
                continue
            if option.type != OptionType.ATTACH or not self.b.is_energy(cid):
                continue
            outcome = self.outcome.evaluate_attach(option)
            if not outcome.supported:
                continue
            if (
                outcome.enables_attack
                or outcome.enables_knockout
                or outcome.improves_damage
                or self.score_attach(option) > 6000
            ):
                return True
        return False

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
        if cid == ULTRA_BALL:
            if len(self.b.hand_ids) < 3:
                return -20000
            useful = self.b.useful_ultra_ball_targets()
            if not useful:
                return -8000
            search_value = max(
                facts.development_value * 40000
                for facts in useful
            )
            deployable_basic_scores = [
                self.score_pokemon_play(self.b.option_card(candidate))
                for _, candidate in self.b.iter_options()
                if (
                    candidate.type == OptionType.PLAY
                    and self.b.is_basic_pokemon(
                        self.b.option_card(candidate)
                    )
                )
            ]
            meaningful_basic_scores = [
                score
                for score in deployable_basic_scores
                if score > 0
            ]
            if meaningful_basic_scores:
                return min(
                    search_value,
                    max(meaningful_basic_scores) - 1,
                )
            return search_value
        if cid == MEGA_SIGNAL:
            if self.b.needs_mega_starmie() or self.b.needs_mega_yuki():
                return 78000
            return -8000
        if cid == POKE_PAD:
            useful = self.b.useful_poke_pad_targets()
            return max(
                (facts.development_value for facts in useful),
                default=-8000,
            )
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
            if self.b.opponent_profile() != "ALAKAZAM":
                return 6000
            hand_reduction = max(
                0,
                safe_int(getattr(self.b.opp, "handCount", 0)) - 4,
            )
            if (
                hand_reduction <= 0
                or self.judge_has_important_non_supporter_action()
            ):
                return 6000
            return 40000 + hand_reduction * 12000
        if cid == SUGURI:
            direct = self.best_current_attack_outcome()
            if direct is not None and (direct.wins_game or direct.knockout):
                return 6000
            boosted = self.outcome.evaluate_suguri_damage_boost()
            if boosted.reachable_knockout:
                return 94000
            active_data = self.b.data(self.b.pid(self.b.active))
            if active_data is not None and not active_data.basic:
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
        if "removes_hp_boost_tool" in outcome.reasons:
            return SCORE_PREFERRED + 70000
        if "removes_key_tool" in outcome.reasons:
            return 80000
        if outcome.removes_tool:
            return 22000
        return -8000

    def score_tool_scrapper_target_option(
        self,
        option_index: int,
        option: Any,
    ) -> float:
        facts = self.b.tool_scrapper_target_facts(
            option_index,
            option,
        )
        if (
            facts is None
            or not facts.attached_to_opponent
            or not facts.currently_attached
            or facts.already_selected
        ):
            return SCORE_FORBIDDEN
        target = self.b.option_target(option)
        outcome = self.outcome.evaluate_tool_scrapper_target(
            target,
            facts.tool_index,
        )
        if not outcome.removes_tool:
            return SCORE_FORBIDDEN
        return max(
            1,
            self.score_tool_scrapper_outcome(outcome),
        )

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
            if target is self.b.active and not self.b.bench and any(card in self.b.hand_ids for card in {POFIN, ULTRA_BALL, POKEGEAR, SALVATORE, MEGA_SIGNAL, LILLIE_DETERMINATION, CRISPIN}):
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
            if direct is not None and (direct.knockout or direct.wins_game):
                return 1000
            boosted_score = 1000
            boosted = self.outcome.evaluate_suguri_damage_boost()
            if boosted.reachable_knockout:
                boosted_score = 94000
            active_data = self.b.data(self.b.pid(self.b.active))
            switch_score = (
                1000
                if active_data is None or active_data.basic
                else 0
            )
            if active_data is not None and not active_data.basic:
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

    def hilda_evolution_candidate_facts(
        self,
        cid: Optional[int],
    ) -> Optional[HildaEvolutionCandidateFacts]:
        data = self.b.data(cid)
        if (
            cid is None
            or data is None
            or data.cardType != CardType.POKEMON
            or bool(getattr(data, "basic", False))
        ):
            return None
        bases = [
            pokemon
            for pokemon in self.b.all_my_pokemon
            if self.b.card_evolves_from_card(cid, self.b.pid(pokemon))
        ]
        completed_same_line_count = self.b.count_in_play(cid)
        currently_evolvable = any(
            not bool(getattr(pokemon, "appearThisTurn", False))
            for pokemon in bases
        )
        attack_axis_gap: Optional[int] = None
        attack_axis_damage = 0
        same_turn_attack_connected = False
        for pokemon in bases:
            tokens = tuple(self.b.energy_tokens_as(pokemon, cid))
            for attack_id in getattr(data, "attacks", ()):
                attack = self.b.attack(attack_id)
                if attack is None:
                    continue
                gap = self.b.attack_energy_gap(attack, tokens)
                if attack_axis_gap is None or gap.missing_units < attack_axis_gap:
                    attack_axis_gap = gap.missing_units
                if (
                    pokemon is self.b.active
                    and not bool(getattr(pokemon, "appearThisTurn", False))
                    and self.outcome.active_can_declare_attack_this_turn()
                    and gap.ready
                    and not self.b.attack_blocked_by_ex_wall_for_card(
                        cid,
                        self.b.opp_active,
                        attack,
                    )
                ):
                    same_turn_attack_connected = True
                    attack_axis_damage = max(
                        attack_axis_damage,
                        self.b.attack_damage_for_card(cid, attack),
                    )
        base_in_play = bool(bases)
        missing_evolution_line = completed_same_line_count == 0
        if not base_in_play:
            current_value = 0.01
        else:
            # Current evolution legality, missing-line completion and the
            # closest current attack axis are each represented once.
            structural_value = (
                int(currently_evolvable) * 2
                + int(missing_evolution_line)
                + (
                    1 / (1 + attack_axis_gap)
                    if attack_axis_gap is not None
                    else 0
                )
            )
            current_value = (
                attack_axis_damage + structural_value
            ) / (1 + completed_same_line_count)
        return HildaEvolutionCandidateFacts(
            target_id=cid,
            legal=True,
            base_in_play=base_in_play,
            currently_evolvable=currently_evolvable,
            missing_evolution_line=missing_evolution_line,
            same_turn_attack_connected=same_turn_attack_connected,
            completed_same_line_count=completed_same_line_count,
            attack_axis_gap=attack_axis_gap,
            attack_axis_damage=attack_axis_damage,
            current_value=current_value,
        )

    def hilda_energy_candidate_facts(
        self,
        cid: Optional[int],
    ) -> Optional[HildaEnergyCandidateFacts]:
        if cid is None or not self.b.is_energy(cid):
            return None
        attach_available = not bool(
            getattr(self.b.state, "energyAttached", False)
        )
        discarded_at_end = cid == IGNITION_ENERGY
        best_key: Optional[Tuple[Any, ...]] = None
        best_values: Tuple[
            Optional[int],
            Optional[int],
            bool,
            int,
            Optional[int],
            Optional[int],
            int,
            Tuple[int, ...],
            int,
            float,
        ] = (None, None, False, 0, None, None, 0, (), 0, 0.01)
        if attach_available:
            for pokemon in self.b.all_my_pokemon:
                projected_ids = [self.b.pid(pokemon)]
                if not bool(getattr(pokemon, "appearThisTurn", False)):
                    projected_ids.extend(
                        evolution_id
                        for evolution_id in dict.fromkeys(self.b.hand_ids)
                        if (
                            evolution_id != self.b.pid(pokemon)
                            and self.b.card_evolves_from_card(
                                evolution_id,
                                self.b.pid(pokemon),
                            )
                        )
                    )
                for projected_id in projected_ids:
                    projected_target = SimpleNamespace(id=projected_id)
                    added_tokens = energy_tokens_for_attach(
                        cid,
                        projected_target,
                    )
                    pokemon_data = self.b.data(projected_id)
                    if added_tokens is None or pokemon_data is None:
                        continue
                    target_is_evolution = not bool(
                        getattr(pokemon_data, "basic", False)
                    )
                    best_before: Optional[int] = None
                    best_after: Optional[int] = None
                    best_reduction = 0
                    enabled_ids: List[int] = []
                    enabled_damage = 0
                    current_tokens = tuple(
                        self.b.energy_tokens_as(pokemon, projected_id)
                    )
                    for attack_id in getattr(pokemon_data, "attacks", ()):
                        attack = self.b.attack(attack_id)
                        if attack is None:
                            continue
                        before = self.b.attack_energy_gap(
                            attack,
                            current_tokens,
                        )
                        after = self.b.attack_energy_gap(
                            attack,
                            current_tokens + tuple(added_tokens),
                        )
                        reduction = max(
                            0,
                            before.missing_units - after.missing_units,
                        )
                        if reduction > best_reduction:
                            best_reduction = reduction
                            best_before = before.missing_units
                            best_after = after.missing_units
                        if (
                            pokemon is self.b.active
                            and self.outcome.active_can_declare_attack_this_turn()
                            and not before.ready
                            and after.ready
                            and not self.b.attack_blocked_by_ex_wall_for_card(
                                projected_id,
                                self.b.opp_active,
                                attack,
                            )
                        ):
                            enabled_ids.append(attack_id)
                            enabled_damage = max(
                                enabled_damage,
                                self.b.attack_damage_for_card(
                                    projected_id,
                                    attack,
                                ),
                            )
                    retained_gap_reduction = (
                        best_reduction
                        if not discarded_at_end
                        else 0
                    )
                    current_value = (
                        enabled_damage
                        + len(enabled_ids)
                        if enabled_ids
                        else retained_gap_reduction
                    )
                    key = (
                        bool(enabled_ids),
                        enabled_damage,
                        len(enabled_ids),
                        retained_gap_reduction,
                        best_reduction,
                    )
                    if best_key is None or key > best_key:
                        best_key = key
                        best_values = (
                            projected_id,
                            getattr(pokemon, "serial", None),
                            target_is_evolution,
                            len(added_tokens),
                            best_before,
                            best_after,
                            best_reduction,
                            tuple(enabled_ids),
                            enabled_damage,
                            max(0.01, current_value),
                        )
        (
            best_target_id,
            best_target_serial,
            best_target_is_evolution,
            provided_units,
            gap_before,
            gap_after,
            gap_reduction,
            enabled_attack_ids,
            enabled_attack_damage,
            current_value,
        ) = best_values
        return HildaEnergyCandidateFacts(
            target_id=cid,
            legal=True,
            same_turn_attach_available=attach_available,
            best_attach_target_id=best_target_id,
            best_attach_target_serial=best_target_serial,
            best_target_is_evolution=best_target_is_evolution,
            provided_colorless_units=provided_units,
            attack_gap_before=gap_before,
            attack_gap_after=gap_after,
            attack_gap_reduction=gap_reduction,
            enabled_attack_ids=enabled_attack_ids,
            enabled_attack_damage=enabled_attack_damage,
            discarded_at_end_of_turn=discarded_at_end,
            current_value=current_value,
        )

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
            facts = self.b.poke_pad_target_facts(cid, visible_search_candidate=True)
            if facts is None:
                return SCORE_FORBIDDEN
            if facts.useful:
                return facts.development_value
            if cid == CINDERACE or not facts.same_turn_deployable:
                return -8000
            if facts.duplicate_in_hand or facts.duplicate_in_play:
                return 0
            # Mandatory-selection tiebreak only.  This does not make the
            # corresponding Poké Pad PLAY useful.
            return 0.01
        if effect == ULTRA_BALL:
            facts = self.b.ultra_ball_target_facts(
                cid,
                visible_search_candidate=True,
            )
            if facts is None:
                return SCORE_FORBIDDEN
            if facts.useful:
                return facts.development_value * 40000
            # Mandatory-selection tiebreak only.  A legal roleless target remains
            # selectable without making the preceding Ultra Ball PLAY useful.
            return 0.01 if cid == CINDERACE else 0.02
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
            evolution_facts = self.hilda_evolution_candidate_facts(cid)
            if evolution_facts is not None:
                return max(0.01, evolution_facts.current_value)
            energy_facts = self.hilda_energy_candidate_facts(cid)
            if energy_facts is not None:
                return max(0.01, energy_facts.current_value)
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
                outcome = self.outcome.evaluate_salvatore_target(target)
                if not outcome.supported:
                    return SCORE_FORBIDDEN
                attack_value = (
                    outcome.reachable_damage
                    if outcome.reachable_attack_id is not None
                    else outcome.expected_reachable_damage
                )
                return (
                    outcome.development_value
                    + attack_value
                    + max(
                        outcome.same_turn_attack_option_count,
                        outcome.post_evolution_ready_attack_count,
                    )
                )
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
        if cid == CINDERACE:
            return (
                SCORE_LAST_RESORT
                if self.b.cinderace_setup_role_live()
                else 6000
            )
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
        if cid in {TOOL_SCRAPPER, WALLY_COMPASSION, HERO_CAPE, SALVATORE, POFIN, ULTRA_BALL}:
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
            return 65000 if self.b.cinderace_setup_role_live() else 0
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
        if option.type == OptionType.PLAY and self.b.option_card(option) == POKE_PAD:
            return self.outcome.evaluate_poke_pad_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == BEFEHL_VON_BOSS:
            return self.outcome.evaluate_boss_play(option)
        if option.type == OptionType.PLAY and self.b.option_card(option) == SUGURI:
            return self.outcome.evaluate_suguri_damage_boost()
        if (
            option.type == OptionType.PLAY
            and self.b.is_basic_pokemon(
                self.b.option_card(option)
            )
        ):
            return (
                self.outcome.evaluate_basic_pokemon_play(
                    option
                )
            )
        if (
            option.type == OptionType.NO
            and self.b.select.context == SelectContext.FIRST_EFFECT
            and getattr(self.b.select.contextCard, "id", None) == SUGURI
        ):
            return self.outcome.evaluate_suguri_damage_boost()

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
        if cid is not None and self.policy.effect_id() == POKE_PAD:
            return self.outcome.evaluate_poke_pad_candidate(option)
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
    if (
        board.select.context == SelectContext.DISCARD_TOOL_CARD
        and card_id(board.select.effect) == TOOL_SCRAPPER
    ):
        chosen = [
            result.index
            for result in ranked
            if result.policy_score > SCORE_FORBIDDEN // 2
        ][:maximum]
        board.record_tool_scrapper_selections(chosen)
        return sorted(chosen)
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
        _reset_current_turn_supporter_tracking()
        _reset_tool_scrapper_selection_tracking()
        return list(DECK)
    if obs.current is None:
        _reset_current_turn_supporter_tracking()
        _reset_tool_scrapper_selection_tracking()
        return []
    board = BoardView(obs)
    return choose_indices(board)

import json
import math
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from itertools import permutations

import main


def attack(attack_id, damage, energies=()):
    return SimpleNamespace(attackId=attack_id, damage=damage, energies=list(energies))


def energy_card(card_id, serial):
    return SimpleNamespace(id=card_id, serial=serial)


def pokemon(card_id, hp=100, max_hp=100, serial=1, energies=(), appear_this_turn=False):
    return SimpleNamespace(
        id=card_id,
        hp=hp,
        maxHp=max_hp,
        serial=serial,
        energyCards=[energy_card(card_id, index) for index, card_id in enumerate(energies, start=1)],
        tools=[],
        appearThisTurn=appear_this_turn,
    )


def option(option_type, attack_id=None):
    return SimpleNamespace(
        type=option_type,
        attackId=attack_id,
        cardId=None,
        index=None,
        area=None,
        playerIndex=None,
        inPlayArea=None,
        inPlayIndex=None,
        toolIndex=None,
        energyIndex=None,
        serial=None,
    )


def attach_option(card_id, target):
    opt = option(main.OptionType.ATTACH)
    opt.cardId = card_id
    opt.target = target
    return opt


def play_option(card_id):
    opt = option(main.OptionType.PLAY)
    opt.cardId = card_id
    return opt


def card_choice(card_id):
    opt = option(3)
    opt.cardId = card_id
    return opt


def evolve_option(card_id, target):
    opt = option(main.OptionType.EVOLVE)
    opt.cardId = card_id
    opt.target = target
    return opt


def tool_target_option(target, tool_index=None):
    opt = option(main.OptionType.CARD)
    opt.target = target
    opt.toolIndex = tool_index
    return opt


def switch_target_option(target):
    opt = option(main.OptionType.CARD)
    opt.target = target
    return opt


def energy_select_option(target, energy_index=None, serial=None):
    opt = option(main.OptionType.ENERGY_CARD)
    opt.target = target
    opt.energyIndex = energy_index
    opt.serial = serial
    return opt


def attack_log(attack_id, player_index=0):
    return SimpleNamespace(type=main.LogType.ATTACK, playerIndex=player_index, attackId=attack_id)


class FakeBoard:
    def __init__(
        self,
        active_id=main.MEGA_STARMIE_EX,
        target_id=999,
        target_hp=100,
        prizes_left=6,
        options=None,
        active_energies=(),
        bench=None,
        opp_bench=None,
        attacks=None,
        plan_boss_targets=None,
        effect_id=main.BEFEHL_VON_BOSS,
        active_in_danger=False,
        public_lethal=False,
        salvatore_live=False,
        needs_mega_starmie=False,
        needs_mega_yuki=False,
        deck_ids=None,
        discard_ids=None,
        turn=None,
        first_player=None,
        your_index=0,
        deck_count=40,
    ):
        self.active = pokemon(active_id, hp=280, max_hp=280, serial=10, energies=active_energies)
        self.bench = bench or []
        self.bench_space = 5 - len(self.bench)
        self.opp_active = pokemon(target_id, hp=target_hp, max_hp=max(target_hp, 100), serial=20)
        self.opp_bench = opp_bench or []
        self.all_my_pokemon = [self.active] + self.bench
        self.all_opp_pokemon = [self.opp_active] + self.opp_bench
        self.opp = SimpleNamespace(handCount=4)
        self.select = SimpleNamespace(effect=SimpleNamespace(id=effect_id) if effect_id is not None else None, contextCard=None, context=main.SelectContext.MAIN, remainEnergyCost=0, minCount=1, maxCount=1)
        self.state = SimpleNamespace(
            supporterPlayed=False,
            stadiumPlayed=False,
            turn=turn,
            firstPlayer=first_player,
            yourIndex=your_index,
        )
        self.me = SimpleNamespace(deckCount=deck_count, asleep=False, paralyzed=False, prize=[None] * prizes_left)
        self._hand_ids = []
        self.deck_ids = [] if deck_ids is None else list(deck_ids)
        self.deck_view = [SimpleNamespace(id=card_id) for card_id in self.deck_ids]
        self.discard_ids = [] if discard_ids is None else list(discard_ids)
        self._prizes_left = prizes_left
        self._plan_boss_targets = set() if plan_boss_targets is None else set(plan_boss_targets)
        self._active_in_danger = active_in_danger
        self._public_lethal = public_lethal
        self._salvatore_live = salvatore_live
        self._needs_mega_starmie = needs_mega_starmie
        self._needs_mega_yuki = needs_mega_yuki
        self.my_index = 0
        self.logs = []
        self._attacks = attacks or {
            main.JETTING_BLOW: attack(main.JETTING_BLOW, 50, [main.EnergyType.WATER]),
            main.NEBULA_BEAM: attack(main.NEBULA_BEAM, 180, [main.EnergyType.COLORLESS] * 3),
            main.WATER_GUN: attack(main.WATER_GUN, 10, [main.EnergyType.WATER]),
            main.CHILLY: attack(main.CHILLY, 30, [main.EnergyType.WATER]),
            main.RESENTFUL_REFRAIN: attack(main.RESENTFUL_REFRAIN, 0, [main.EnergyType.WATER]),
            main.ABSOLUTE_SNOW: attack(main.ABSOLUTE_SNOW, 150, [main.EnergyType.WATER, main.EnergyType.COLORLESS, main.EnergyType.COLORLESS]),
            main.TURBO_FLARE: attack(main.TURBO_FLARE, 50, [main.EnergyType.COLORLESS]),
            997: attack(997, 20, [main.EnergyType.DARKNESS]),
            998: attack(998, 110, [main.EnergyType.DARKNESS, main.EnergyType.DARKNESS, main.EnergyType.COLORLESS]),
            999001: attack(999001, 10, [main.EnergyType.COLORLESS]),
        }
        self._data = {
            main.MEGA_STARMIE_EX: SimpleNamespace(ex=True, megaEx=True, attacks=[main.JETTING_BLOW, main.NEBULA_BEAM]),
            main.MEGA_YUKIMENOKO_EX: SimpleNamespace(ex=True, megaEx=True, attacks=[main.RESENTFUL_REFRAIN, main.ABSOLUTE_SNOW]),
            main.HITODEMAN: SimpleNamespace(ex=False, megaEx=False, attacks=[main.WATER_GUN]),
            main.YUKIWARASHI: SimpleNamespace(ex=False, megaEx=False, attacks=[main.CHILLY]),
            main.CINDERACE: SimpleNamespace(ex=False, megaEx=False, attacks=[main.TURBO_FLARE]),
            main.YVELTAL: SimpleNamespace(ex=False, megaEx=False, attacks=[997, 998]),
            main.SHAYMIN: SimpleNamespace(ex=False, megaEx=False, attacks=[]),
            main.BUDEW: SimpleNamespace(ex=False, megaEx=False, attacks=[323]),
            999: SimpleNamespace(ex=False, megaEx=False, attacks=[]),
            998: SimpleNamespace(ex=True, megaEx=True, attacks=[]),
            main.RIOLU: SimpleNamespace(ex=False, megaEx=False, attacks=[]),
            330: SimpleNamespace(ex=False, megaEx=False, attacks=[]),
            345: SimpleNamespace(ex=False, megaEx=False, attacks=[]),
        }
        for card_id, data in self._data.items():
            real_data = main.CARD_TABLE.get(card_id)
            data.cardId = card_id
            data.name = real_data.name if real_data is not None else str(card_id)
            data.evolvesFrom = real_data.evolvesFrom if real_data is not None else None
            data.cardType = real_data.cardType if real_data is not None else main.CardType.POKEMON
            data.hp = real_data.hp if real_data is not None else getattr(data, "hp", 100)
            data.skills = real_data.skills if real_data is not None else []
            if not hasattr(data, "retreatCost"):
                data.retreatCost = 1
            if not hasattr(data, "basic"):
                data.basic = card_id in {main.HITODEMAN, main.YUKIWARASHI, main.CINDERACE, main.YVELTAL, main.SHAYMIN, main.BUDEW}
        self._data[main.MEGA_STARMIE_EX].retreatCost = 2
        self._data[main.MEGA_YUKIMENOKO_EX].retreatCost = 1
        self._data[main.CINDERACE].retreatCost = 0
        self._data[main.YVELTAL].retreatCost = 0
        self._data[main.SHAYMIN].retreatCost = 1
        self._options = options or []

    def attack(self, attack_id):
        return self._attacks.get(attack_id) or main.ATTACK_TABLE.get(attack_id)

    def pid(self, target):
        return -1 if target is None else target.id

    def data(self, card_id):
        return self._data.get(card_id) or main.CARD_TABLE.get(card_id)

    def is_supporter(self, card_id):
        data = self.data(card_id)
        return data is not None and data.cardType == main.CardType.SUPPORTER

    def is_pokemon(self, card_id):
        data = self.data(card_id)
        return data is not None and data.cardType == main.CardType.POKEMON

    def is_energy(self, card_id):
        data = self.data(card_id)
        return data is not None and data.cardType in {main.CardType.BASIC_ENERGY, main.CardType.SPECIAL_ENERGY}

    def can_use_supporter(self, card_id):
        return self.is_supporter(card_id) and not self.state.supporterPlayed

    def attack_damage(self, attacker, atk):
        return self.attack_damage_for_card(self.pid(attacker), atk)

    def attack_damage_for_card(self, attacker_id, atk):
        if atk.attackId == main.RESENTFUL_REFRAIN:
            return int(self.opp.handCount) * 50
        return int(atk.damage)

    def option_card(self, opt):
        return opt.cardId

    def option_target(self, opt):
        return getattr(opt, "target", None)

    def energies(self, target):
        return [card.id for card in target.energyCards]

    def energy_tokens(self, target):
        return self.energy_tokens_as(target, self.pid(target))

    def energy_tokens_as(self, target, card_id):
        tokens = []
        data = self.data(card_id)
        ignition_units = 1 if data is not None and data.basic else 3
        for card in target.energyCards:
            if card.id == main.BASIC_WATER_ENERGY:
                tokens.append(main.EnergyType.WATER)
            elif card.id == main.BASIC_DARK_ENERGY:
                tokens.append(main.EnergyType.DARKNESS)
            elif card.id == main.IGNITION_ENERGY:
                tokens.extend([main.EnergyType.COLORLESS] * ignition_units)
        return tokens

    def energy_count(self, target):
        return len(target.energyCards)

    def can_pay_attack(self, target, atk):
        return main.can_pay_attack_with_tokens(atk, self.energy_tokens(target))

    def best_damage(self, target):
        return main.BoardView.best_damage(self, target)

    def opp_max_damage(self):
        return main.BoardView.opp_max_damage(self)

    def attack_bypasses_ex_wall(self, atk):
        return atk is not None and atk.attackId == main.NEBULA_BEAM

    def attack_blocked_by_ex_wall_for_card(self, attacker_id, target, atk):
        if target is None or self.pid(target) not in main.EX_ATTACK_WALLS:
            return False
        if self.attack_bypasses_ex_wall(atk):
            return False
        data = self.data(attacker_id)
        return data is not None and (data.ex or data.megaEx)

    def active_evolution_attack_facts(self, opt):
        return main.BoardView.active_evolution_attack_facts(self, opt)

    def prize_value(self, target):
        data = self.data(target.id)
        if data is not None and data.megaEx:
            return 3
        if data is not None and data.ex:
            return 2
        return 1

    def my_prizes_left(self):
        return self._prizes_left

    def active_has_ignition(self):
        return False

    def active_in_danger(self):
        return self._active_in_danger

    def public_lethal_next_turn(self):
        return self._public_lethal

    def has_foreign_stadium(self):
        return False

    def plan_attack_ids(self):
        return {main.JETTING_BLOW, main.NEBULA_BEAM}

    def plan_boss_targets(self):
        return self._plan_boss_targets

    def plan_pressure_targets(self):
        return set()

    def opponent_profile(self):
        return main.BoardView.opponent_profile(self)

    def opp_has(self, ids):
        return any(self.pid(pokemon) in ids for pokemon in self.all_opp_pokemon)

    def opponent_has_bench_damage_threat(self):
        return main.BoardView.opponent_has_bench_damage_threat(self)

    def card_evolves_from_card(self, evolution_id, base_id):
        return main.BoardView.card_evolves_from_card(self, evolution_id, base_id)

    def evolves_from(self, evolution_id, target):
        return main.BoardView.evolves_from(self, evolution_id, target)

    def remaining_possible(self, card_id, total=None):
        return main.BoardView.remaining_possible(self, card_id, total)

    def remaining_possible_count(self, card_id, total=None):
        return main.BoardView.remaining_possible_count(self, card_id, total)

    def known_prize_ids(self):
        return main.BoardView.known_prize_ids(self)

    def unknown_prize_count(self):
        return main.BoardView.unknown_prize_count(self)

    def remaining_deck_count(self):
        return main.BoardView.remaining_deck_count(self)

    def deck_presence_probability(self, card_id):
        return main.BoardView.deck_presence_probability(self, card_id)

    def _comb_probability_no_success(self, total, success, draws):
        return main.BoardView._comb_probability_no_success(self, total, success, draws)

    def pokegear_chain_hit_probability_from_counts(self, hidden_count, deck_count, look_count, supporter_count, evolution_count):
        return main.BoardView.pokegear_chain_hit_probability_from_counts(
            self,
            hidden_count,
            deck_count,
            look_count,
            supporter_count,
            evolution_count,
        )

    def pokegear_hit_probability(self, card_id):
        return main.BoardView.pokegear_hit_probability(self, card_id)

    def pokegear_chain_hit_probability(self, supporter_id, evolution_id):
        return main.BoardView.pokegear_chain_hit_probability(self, supporter_id, evolution_id)

    def salvatore_target_evolution(self, target):
        return main.BoardView.salvatore_target_evolution(self, target)

    def salvatore_can_evolve_from_deck_this_turn(self, target, evolution_id):
        return main.BoardView.salvatore_can_evolve_from_deck_this_turn(self, target, evolution_id)

    def salvatore_deck_target_evolution(self, target):
        return main.BoardView.salvatore_deck_target_evolution(self, target)

    def has_salvatore_deck_target(self, evolution_id=None):
        return main.BoardView.has_salvatore_deck_target(self, evolution_id)

    def has_salvatore_target(self, evolution_id=None):
        return main.BoardView.has_salvatore_target(self, evolution_id)

    def is_salvatore_target(self, card_id):
        return main.BoardView.is_salvatore_target(self, card_id)

    def card_or_evolution_has_bench_damage_threat(self, card_id, seen=None):
        return main.BoardView.card_or_evolution_has_bench_damage_threat(self, card_id, seen)

    def needs_shaymin_bench_guard(self):
        return self.opponent_has_bench_damage_threat() or self.opponent_profile() == "BENCH_DAMAGE"

    def count_in_play(self, card_id):
        return sum(1 for p in self.all_my_pokemon if self.pid(p) == card_id)

    @property
    def hand_ids(self):
        return self._hand_ids

    def legal_attack_options(self):
        return [self.attack(opt.attackId) for opt in self._options if opt.attackId is not None]

    def iter_options(self):
        for index, opt in enumerate(self._options):
            yield index, opt

    def energy_switch_has_equivalent_normal_attach_result(self):
        return main.BoardView.energy_switch_has_equivalent_normal_attach_result(self)

    def current_turn_attached_energy_ids(self):
        return main.BoardView.current_turn_attached_energy_ids(self)

    def is_attack_choice_phase(self):
        return True

    def starmie_needs_energy(self):
        return True

    def needs_basic(self):
        return False

    def visible_or_unknown_in_deck(self, card_id):
        return True

    def lillie_effect_facts(self):
        return main.BoardView.lillie_effect_facts(self)

    def has_tool_scrapper_target(self):
        return main.BoardView.has_tool_scrapper_target(self)

    def hero_cape_target_roi(self, target):
        return main.BoardView.hero_cape_target_roi(self, target)

    def hand_card_activity(self, card_id, occurrence=1, total_count=1):
        return main.BoardView.hand_card_activity(self, card_id, occurrence, total_count)

    def hand_activity_facts(self):
        return main.BoardView.hand_activity_facts(self)

    def basic_energy_remaining_possible(self, energy_id):
        return main.BoardView.basic_energy_remaining_possible(self, energy_id)

    def attack_energy_gap(self, atk, tokens):
        return main.BoardView.attack_energy_gap(self, atk, tokens)

    def active_energy_facts(self):
        return main.BoardView.active_energy_facts(self)

    def _supporter_live_for_pokegear(self, card_id):
        return main.BoardView._supporter_live_for_pokegear(self, card_id)

    def pokegear_supporter_facts(self):
        return main.BoardView.pokegear_supporter_facts(self)

    def role_facts(self, target):
        return main.BoardView.role_facts(self, target)

    def has_bench_energy_receiver(self):
        return False

    def cinderace_can_accelerate(self):
        return False

    def salvatore_live(self):
        return self._salvatore_live or main.BoardView.salvatore_live(self)

    def wally_live(self):
        return main.BoardView.wally_live(self)

    def needs_mega_starmie(self):
        return self._needs_mega_starmie

    def needs_mega_yuki(self):
        return self._needs_mega_yuki


def policy_for(board):
    return main.Policy(board)


def test_energy_payment_rules():
    water = main.EnergyType.WATER
    dark = main.EnergyType.DARKNESS
    colorless = main.EnergyType.COLORLESS
    fire = main.EnergyType.FIRE
    cases = [
        ([water], [colorless], False),
        ([dark], [colorless], False),
        ([water, colorless], [water, dark], True),
        ([dark, colorless], [dark, water], True),
        ([water, dark], [water, dark], True),
        ([water, dark], [water, colorless], False),
        ([colorless, colorless, colorless], [colorless, colorless, colorless], True),
        ([water, colorless, colorless], [water, colorless, colorless, colorless], True),
        ([water, water, colorless], [water, colorless, colorless, colorless], False),
        ([water, dark, colorless], [water, dark, colorless, colorless, colorless], True),
        ([fire], [water], False),
    ]

    for index, (requirements, tokens, expected) in enumerate(cases, start=1):
        original_requirements = list(requirements)
        original_tokens = list(tokens)
        for ordered_requirements in set(permutations(requirements)):
            for ordered_tokens in set(permutations(tokens)):
                assert main.can_pay_attack_with_tokens(attack(index, 10, ordered_requirements), ordered_tokens) is expected
        assert requirements == original_requirements
        assert tokens == original_tokens


def test_attack_outcomes_and_policy_guards():
    jet = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    nebula = option(main.OptionType.ATTACK, main.NEBULA_BEAM)
    weak = option(main.OptionType.ATTACK, 999001)
    end = option(main.OptionType.END)
    assert main.attack_can_damage_opponent_bench(main.ATTACK_TABLE[main.JETTING_BLOW])
    assert main.attack_can_damage_opponent_bench(main.ATTACK_TABLE[937])
    assert not main.attack_can_damage_opponent_bench(main.ATTACK_TABLE[115])
    assert FakeBoard().card_or_evolution_has_bench_damage_threat(main.HITODEMAN)
    assert not FakeBoard().card_or_evolution_has_bench_damage_threat(main.YVELTAL)
    assert FakeBoard(target_id=main.HITODEMAN).needs_shaymin_bench_guard()

    board = FakeBoard(target_id=999, target_hp=100, options=[jet, end])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack(jet)
    assert outcome.supported and not outcome.blocked and outcome.damage == 50
    assert policy_for(board).score_end() == main.SCORE_FORBIDDEN
    board.select.type = 0
    assert policy_for(board).score_end() == main.SCORE_FORBIDDEN

    wall_board = FakeBoard(target_id=330, target_hp=100, options=[jet, end])
    wall_outcome = main.ImmediateOutcomeEvaluator(wall_board).evaluate_attack(jet)
    assert wall_outcome.blocked and wall_outcome.damage == 0
    assert policy_for(wall_board).score_end() != main.SCORE_FORBIDDEN
    assert main.choose_indices(wall_board) == [1]

    setup_before_end = FakeBoard(active_id=main.HITODEMAN, target_hp=100, options=[play_option(main.POFIN), end])
    assert policy_for(setup_before_end).score_end() == main.SCORE_FORBIDDEN
    assert main.choose_indices(setup_before_end) == [0]

    nebula_wall_board = FakeBoard(target_id=330, target_hp=100, options=[nebula, end])
    nebula_outcome = main.ImmediateOutcomeEvaluator(nebula_wall_board).evaluate_attack(nebula)
    assert not nebula_outcome.blocked
    assert nebula_outcome.bypasses_wall
    assert "bypasses_ex_wall" in nebula_outcome.reasons

    ko_board = FakeBoard(target_id=999, target_hp=40, options=[jet, weak])
    assert policy_for(ko_board).score_attack(jet) > policy_for(ko_board).score_attack(weak)

    win_board = FakeBoard(target_id=999, target_hp=40, prizes_left=1, options=[jet, weak])
    win_outcome = main.ImmediateOutcomeEvaluator(win_board).evaluate_attack(jet)
    assert win_outcome.knockout and win_outcome.wins_game
    assert policy_for(win_board).score_attack(jet) >= main.SCORE_FORCED

    class NeedsBasicBoard(FakeBoard):
        def needs_basic(self):
            return True

    empty_bench_mega_rebuild = NeedsBasicBoard(
        active_id=main.MEGA_STARMIE_EX,
        options=[play_option(main.POFIN), jet],
        active_energies=[main.BASIC_WATER_ENERGY],
        bench=[],
        target_hp=300,
    )
    empty_bench_mega_rebuild._hand_ids = [main.POFIN, main.CRISPIN, main.MEGA_STARMIE_EX]
    assert policy_for(empty_bench_mega_rebuild).score_play(play_option(main.POFIN)) > policy_for(empty_bench_mega_rebuild).score_attack(jet)

    empty_bench_mega_ko = NeedsBasicBoard(
        active_id=main.MEGA_STARMIE_EX,
        options=[play_option(main.POFIN), jet],
        active_energies=[main.BASIC_WATER_ENERGY],
        bench=[],
        target_hp=40,
    )
    empty_bench_mega_ko._hand_ids = [main.POFIN, main.CRISPIN, main.MEGA_STARMIE_EX]
    assert policy_for(empty_bench_mega_ko).score_attack(jet) > policy_for(empty_bench_mega_ko).score_play(play_option(main.POFIN))

    develop_before_attack = FakeBoard(
        active_id=main.YUKIWARASHI,
        options=[play_option(main.SALVATORE), option(main.OptionType.ATTACK, main.CHILLY)],
        active_energies=[main.BASIC_WATER_ENERGY],
        salvatore_live=True,
        needs_mega_yuki=True,
    )
    assert policy_for(develop_before_attack).score_play(play_option(main.SALVATORE)) > policy_for(develop_before_attack).score_attack(option(main.OptionType.ATTACK, main.CHILLY))

    water_gun = option(main.OptionType.ATTACK, main.WATER_GUN)
    staryu_develop = FakeBoard(
        active_id=main.HITODEMAN,
        options=[play_option(main.CRISPIN), water_gun],
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=100,
    )
    assert policy_for(staryu_develop).score_play(play_option(main.CRISPIN)) > policy_for(staryu_develop).score_attack(water_gun)

    staryu_ko = FakeBoard(
        active_id=main.HITODEMAN,
        options=[play_option(main.CRISPIN), water_gun],
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=10,
    )
    assert policy_for(staryu_ko).score_attack(water_gun) > policy_for(staryu_ko).score_play(play_option(main.CRISPIN))

    budew_pressure = FakeBoard(
        active_id=main.HITODEMAN,
        target_id=main.BUDEW,
        target_hp=30,
        options=[play_option(main.CRISPIN), water_gun],
        active_energies=[main.BASIC_WATER_ENERGY],
    )
    assert policy_for(budew_pressure).score_attack(water_gun) > policy_for(budew_pressure).score_play(play_option(main.CRISPIN))
    assert policy_for(budew_pressure).score_attack(water_gun) < main.SCORE_FORCED

    empty_bench_weak_attack = FakeBoard(
        active_id=main.HITODEMAN,
        options=[play_option(main.YUKIWARASHI), play_option(main.YVELTAL), water_gun],
        active_energies=[main.BASIC_WATER_ENERGY],
        bench=[],
        target_hp=290,
    )
    assert policy_for(empty_bench_weak_attack).score_play(play_option(main.YUKIWARASHI)) > policy_for(empty_bench_weak_attack).score_attack(water_gun)
    assert policy_for(empty_bench_weak_attack).score_play(play_option(main.YVELTAL)) > policy_for(empty_bench_weak_attack).score_attack(water_gun)

    empty_bench_budew_pressure = FakeBoard(
        active_id=main.HITODEMAN,
        target_id=main.BUDEW,
        target_hp=30,
        options=[play_option(main.YUKIWARASHI), water_gun],
        active_energies=[main.BASIC_WATER_ENERGY],
        bench=[],
    )
    assert policy_for(empty_bench_budew_pressure).score_attack(water_gun) > policy_for(empty_bench_budew_pressure).score_play(play_option(main.YUKIWARASHI))

    smash_kick = option(main.OptionType.ATTACK, 477)
    shaymin_with_hand = FakeBoard(
        active_id=main.SHAYMIN,
        options=[play_option(main.LILLIE_DETERMINATION), play_option(main.POKEGEAR), smash_kick],
        attacks={477: attack(477, 30, [main.EnergyType.COLORLESS, main.EnergyType.COLORLESS])},
        active_energies=[main.IGNITION_ENERGY],
        bench=[pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=34)],
        target_hp=300,
        needs_mega_starmie=True,
    )
    shaymin_with_hand._hand_ids = [
        main.LILLIE_DETERMINATION,
        main.POKEGEAR,
        main.HERO_CAPE,
        main.BASIC_DARK_ENERGY,
    ]
    assert policy_for(shaymin_with_hand).score_play(play_option(main.LILLIE_DETERMINATION)) > policy_for(shaymin_with_hand).score_attack(smash_kick)
    assert policy_for(shaymin_with_hand).score_play(play_option(main.POKEGEAR)) > policy_for(shaymin_with_hand).score_attack(smash_kick)

    shaymin_ko = FakeBoard(
        active_id=main.SHAYMIN,
        options=[play_option(main.LILLIE_DETERMINATION), smash_kick],
        attacks={477: attack(477, 30, [main.EnergyType.COLORLESS, main.EnergyType.COLORLESS])},
        active_energies=[main.IGNITION_ENERGY],
        target_hp=30,
        needs_mega_starmie=True,
    )
    assert policy_for(shaymin_ko).score_attack(smash_kick) > policy_for(shaymin_ko).score_play(play_option(main.LILLIE_DETERMINATION))

    class TurboBoard(FakeBoard):
        def has_bench_energy_receiver(self):
            return True

        def count_in_play(self, card_id):
            return 0

        @property
        def hand_ids(self):
            return [main.HYPERBALL, main.HERO_CAPE, main.BASIC_DARK_ENERGY, main.MEGA_STARMIE_EX]

        def needs_basic(self):
            return True

    turbo = option(main.OptionType.ATTACK, main.TURBO_FLARE)
    turbo_board = TurboBoard(active_id=main.CINDERACE, options=[play_option(main.HYPERBALL), turbo])
    assert policy_for(turbo_board).score_attack(turbo) < main.SCORE_FORCED
    assert policy_for(turbo_board).score_play(play_option(main.HYPERBALL)) > policy_for(turbo_board).score_attack(turbo)

    class TurboOnlyBoard(TurboBoard):
        @property
        def hand_ids(self):
            return set()

    turbo_only_board = TurboOnlyBoard(active_id=main.CINDERACE, options=[turbo])
    assert policy_for(turbo_only_board).score_attack(turbo) > 1000000

    turbo_without_receiver = FakeBoard(active_id=main.CINDERACE, options=[play_option(main.POKEGEAR), turbo])
    turbo_without_receiver._hand_ids = [
        main.POKEGEAR,
        main.HERO_CAPE,
        main.BASIC_DARK_ENERGY,
        main.MEGA_STARMIE_EX,
    ]
    assert not turbo_without_receiver.has_bench_energy_receiver()
    assert policy_for(turbo_without_receiver).score_attack(turbo) < policy_for(turbo_without_receiver).score_play(play_option(main.POKEGEAR))
    assert policy_for(turbo_without_receiver).score_attack(turbo) == 0

    turbo_without_receiver_or_pokegear = FakeBoard(active_id=main.CINDERACE, options=[play_option(main.SURFING_BEACH), turbo])
    turbo_without_receiver_or_pokegear._hand_ids = [
        main.SURFING_BEACH,
        main.HERO_CAPE,
        main.BASIC_DARK_ENERGY,
        main.MEGA_STARMIE_EX,
    ]
    assert policy_for(turbo_without_receiver_or_pokegear).score_play(play_option(main.SURFING_BEACH)) == -12000
    assert policy_for(turbo_without_receiver_or_pokegear).score_attack(turbo) > policy_for(turbo_without_receiver_or_pokegear).score_play(play_option(main.SURFING_BEACH))


def test_attach_outcomes():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ignition = main.IGNITION_ENERGY
    colorless = main.EnergyType.COLORLESS

    evolved_target = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=40)
    basic_target = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=41)
    assert main.energy_tokens_for_attach(ignition, evolved_target) == (colorless, colorless, colorless)
    assert main.energy_tokens_for_attach(ignition, basic_target) == (colorless,)

    three_colorless = attack(999002, 90, [colorless, colorless, colorless])
    basic_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[ignition])
    evolved_board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[ignition])
    assert basic_board.energy_tokens(basic_board.active) == [colorless]
    assert evolved_board.energy_tokens(evolved_board.active) == [colorless, colorless, colorless]
    assert not basic_board.can_pay_attack(basic_board.active, three_colorless)
    assert evolved_board.can_pay_attack(evolved_board.active, three_colorless)

    cinderace = pokemon(main.CINDERACE, hp=160, max_hp=160, serial=42)
    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=43)
    board = FakeBoard(active_id=main.CINDERACE, bench=[staryu])
    water_to_cinderace = attach_option(water, cinderace)
    water_to_staryu = attach_option(water, staryu)
    dark_to_cinderace = attach_option(dark, cinderace)
    assert policy_for(board).score_attach(water_to_staryu) > policy_for(board).score_attach(water_to_cinderace)
    assert policy_for(board).score_attach(water_to_staryu) > policy_for(board).score_attach(dark_to_cinderace)

    class LiveReceiverBoard(FakeBoard):
        def has_bench_energy_receiver(self):
            return True

    turbo_exception_board = LiveReceiverBoard(active_id=main.CINDERACE, bench=[staryu], deck_ids=[water])
    assert policy_for(turbo_exception_board).score_attach(attach_option(water, turbo_exception_board.active)) > policy_for(turbo_exception_board).score_attach(attach_option(water, staryu))

    turbo_dark_energy_only = LiveReceiverBoard(active_id=main.CINDERACE, bench=[staryu], deck_ids=[dark])
    assert policy_for(turbo_dark_energy_only).score_attach(attach_option(water, turbo_dark_energy_only.active)) > policy_for(turbo_dark_energy_only).score_attach(attach_option(water, staryu))
    assert policy_for(turbo_dark_energy_only).score_attach(attach_option(dark, turbo_dark_energy_only.active)) > policy_for(turbo_dark_energy_only).score_attach(attach_option(dark, staryu))

    turbo_ignition_only = LiveReceiverBoard(active_id=main.CINDERACE, bench=[staryu], deck_ids=[main.IGNITION_ENERGY])
    assert policy_for(turbo_ignition_only).score_attach(attach_option(water, turbo_ignition_only.active)) < policy_for(turbo_exception_board).score_attach(attach_option(water, turbo_exception_board.active))

    turbo_no_basic_energy = LiveReceiverBoard(active_id=main.CINDERACE, bench=[staryu])
    turbo_no_basic_energy._hand_ids = [water] * main.DECK.count(water) + [dark] * main.DECK.count(dark)
    assert policy_for(turbo_no_basic_energy).score_attach(attach_option(water, staryu)) > policy_for(turbo_no_basic_energy).score_attach(attach_option(water, turbo_no_basic_energy.active))
    assert policy_for(turbo_no_basic_energy).score_attach(attach_option(dark, turbo_no_basic_energy.active)) < policy_for(turbo_dark_energy_only).score_attach(attach_option(dark, turbo_dark_energy_only.active))

    partial_starmie_for_direct_attach = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=142)
    turbo_with_direct_main = LiveReceiverBoard(active_id=main.CINDERACE, bench=[partial_starmie_for_direct_attach])
    assert policy_for(turbo_with_direct_main).score_attach(attach_option(water, partial_starmie_for_direct_attach)) > policy_for(turbo_with_direct_main).score_attach(attach_option(water, turbo_with_direct_main.active))

    bench_cinderace = pokemon(main.CINDERACE, hp=160, max_hp=160, serial=143)
    non_active_turbo_board = LiveReceiverBoard(active_id=main.YVELTAL, bench=[staryu, bench_cinderace])
    assert policy_for(non_active_turbo_board).score_attach(attach_option(water, staryu)) > policy_for(non_active_turbo_board).score_attach(attach_option(water, bench_cinderace))

    turbo_already_enabled = LiveReceiverBoard(active_id=main.CINDERACE, active_energies=[water], bench=[staryu])
    assert policy_for(turbo_already_enabled).score_attach(attach_option(water, staryu)) > policy_for(turbo_already_enabled).score_attach(attach_option(water, turbo_already_enabled.active))

    no_receiver_board = FakeBoard(active_id=main.CINDERACE, bench=[])
    assert policy_for(no_receiver_board).score_attach(attach_option(water, no_receiver_board.active)) < 0
    assert policy_for(no_receiver_board).score_attach(attach_option(dark, no_receiver_board.active)) < 210000

    asleep_turbo_board = LiveReceiverBoard(active_id=main.CINDERACE, bench=[staryu])
    asleep_turbo_board.me = SimpleNamespace(asleep=True, paralyzed=False)
    assert policy_for(asleep_turbo_board).score_attach(attach_option(water, staryu)) > policy_for(asleep_turbo_board).score_attach(attach_option(water, asleep_turbo_board.active))
    assert policy_for(asleep_turbo_board).score_attach(attach_option(dark, asleep_turbo_board.active)) < policy_for(turbo_dark_energy_only).score_attach(attach_option(dark, turbo_dark_energy_only.active))

    snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=44)
    water_to_snorunt = attach_option(water, snorunt)
    assert policy_for(board).score_attach(water_to_staryu) > policy_for(board).score_attach(water_to_snorunt)
    assert policy_for(board).score_attach(water_to_snorunt) > policy_for(board).score_attach(water_to_cinderace)

    partial_starmie = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=45, energies=[water])
    board_with_partial_starmie = FakeBoard(active_id=main.CINDERACE, active_energies=[water], bench=[partial_starmie, staryu])
    assert policy_for(board_with_partial_starmie).score_attach(attach_option(dark, partial_starmie)) > policy_for(board_with_partial_starmie).score_attach(attach_option(dark, board_with_partial_starmie.active))

    shaymin = pokemon(main.SHAYMIN, hp=80, max_hp=80, serial=46)
    yveltal = pokemon(main.YVELTAL, hp=120, max_hp=120, serial=47)
    utility_board = FakeBoard(active_id=main.CINDERACE, bench=[partial_starmie, shaymin, yveltal])
    assert policy_for(utility_board).score_attach(attach_option(water, partial_starmie)) > policy_for(utility_board).score_attach(attach_option(water, shaymin))
    assert policy_for(utility_board).score_attach(attach_option(dark, partial_starmie)) > policy_for(utility_board).score_attach(attach_option(dark, yveltal))

    active_unfinished = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water, dark], bench=[staryu])
    assert policy_for(active_unfinished).score_attach(attach_option(water, active_unfinished.active)) > policy_for(active_unfinished).score_attach(attach_option(water, staryu))

    live_snorunt_board = FakeBoard(active_id=main.CINDERACE, bench=[snorunt], deck_ids=[water])
    live_snorunt_board._hand_ids = [main.MEGA_YUKIMENOKO_EX]
    assert policy_for(live_snorunt_board).score_attach(attach_option(water, live_snorunt_board.active)) > policy_for(live_snorunt_board).score_attach(attach_option(water, snorunt))

    partial_mega_yuki_receiver = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=144, energies=[water])
    turbo_with_mega_yuki = FakeBoard(active_id=main.CINDERACE, bench=[partial_mega_yuki_receiver], deck_ids=[water])
    assert policy_for(turbo_with_mega_yuki).score_attach(attach_option(water, turbo_with_mega_yuki.active)) > policy_for(turbo_with_mega_yuki).score_attach(attach_option(water, partial_mega_yuki_receiver))

    full_mega_yuki_receiver = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=145, energies=[water, water, dark])
    turbo_with_full_receiver = FakeBoard(active_id=main.CINDERACE, bench=[full_mega_yuki_receiver], deck_ids=[water])
    assert policy_for(turbo_with_full_receiver).score_attach(attach_option(water, turbo_with_full_receiver.active)) < policy_for(turbo_with_mega_yuki).score_attach(attach_option(water, turbo_with_mega_yuki.active))

    class DeadEvolutionBoard(FakeBoard):
        def visible_or_unknown_in_deck(self, card_id):
            return False

        def has_bench_energy_receiver(self):
            return True

    dead_snorunt_board = DeadEvolutionBoard(active_id=main.CINDERACE, bench=[snorunt])
    dead_snorunt_board._hand_ids = []
    assert policy_for(dead_snorunt_board).score_attach(attach_option(water, dead_snorunt_board.active)) > policy_for(dead_snorunt_board).score_attach(attach_option(water, snorunt))
    assert policy_for(dead_snorunt_board).score_attach(attach_option(water, dead_snorunt_board.active)) < policy_for(live_snorunt_board).score_attach(attach_option(water, live_snorunt_board.active))

    dead_staryu_board = DeadEvolutionBoard(active_id=main.CINDERACE, bench=[staryu])
    dead_staryu_board._hand_ids = []
    assert policy_for(dead_staryu_board).score_attach(attach_option(water, dead_staryu_board.active)) > policy_for(dead_staryu_board).score_attach(attach_option(water, staryu))
    assert policy_for(dead_staryu_board).score_attach(attach_option(water, dead_staryu_board.active)) < policy_for(turbo_exception_board).score_attach(attach_option(water, turbo_exception_board.active))

    class UtilityOnlyReceiverBoard(FakeBoard):
        def has_bench_energy_receiver(self):
            return True

    utility_only = UtilityOnlyReceiverBoard(active_id=main.CINDERACE, bench=[shaymin])
    assert policy_for(utility_only).score_attach(attach_option(dark, utility_only.active)) > 0

    class YveltalSoloSetupBoard(FakeBoard):
        @property
        def hand_ids(self):
            return [main.HYPERBALL, main.CRISPIN, main.SALVATORE, main.BASIC_DARK_ENERGY]

        def needs_basic(self):
            return True

    yveltal_solo = YveltalSoloSetupBoard(active_id=main.YVELTAL, bench=[])
    assert policy_for(yveltal_solo).score_play(play_option(main.HYPERBALL)) > policy_for(yveltal_solo).score_attach(attach_option(dark, yveltal_solo.active))

    yveltal_with_bench = YveltalSoloSetupBoard(active_id=main.YVELTAL, bench=[staryu])
    assert policy_for(yveltal_with_bench).score_attach(attach_option(dark, yveltal_with_bench.active)) > policy_for(yveltal_solo).score_attach(attach_option(dark, yveltal_solo.active))

    board = FakeBoard(active_energies=[])
    original_energy_cards = list(board.active.energyCards)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(water, board.active))
    assert outcome.enables_attack
    assert main.JETTING_BLOW in outcome.enabled_attack_ids
    assert "enables_attack" in outcome.reasons
    assert board.active.energyCards == original_energy_cards

    board = FakeBoard(active_energies=[dark, dark])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(water, board.active))
    assert outcome.enables_attack
    assert main.NEBULA_BEAM in outcome.enabled_attack_ids
    assert "enables_nebula_beam" in outcome.reasons

    board = FakeBoard(active_energies=[water, dark])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(dark, board.active))
    assert main.NEBULA_BEAM in outcome.enabled_attack_ids

    board = FakeBoard(active_energies=[])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(dark, board.active))
    assert main.JETTING_BLOW not in outcome.enabled_attack_ids

    board = FakeBoard(active_energies=[water])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(ignition, board.active))
    assert outcome.enables_attack
    assert main.NEBULA_BEAM in outcome.enabled_attack_ids
    assert "enables_nebula_beam" in outcome.reasons
    assert "ignition_immediate_attack" in outcome.reasons
    assert policy_for(board).score_attach(attach_option(ignition, board.active)) > 0

    class NeedsBasicBoard(FakeBoard):
        def needs_basic(self):
            return True

    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=51)
    cinderace_ignition_board = NeedsBasicBoard(active_id=main.CINDERACE, bench=[staryu], options=[play_option(main.POFIN), attach_option(ignition, staryu)])
    cinderace_ignition_board._hand_ids = [main.IGNITION_ENERGY, main.POFIN, main.MEGA_STARMIE_EX]
    assert policy_for(cinderace_ignition_board).score_play(play_option(main.POFIN)) > policy_for(cinderace_ignition_board).score_attach(attach_option(ignition, cinderace_ignition_board.active))

    cinderace_solo_ignition = FakeBoard(active_id=main.CINDERACE, bench=[], options=[play_option(main.POKEGEAR), attach_option(ignition, staryu)])
    cinderace_solo_ignition._hand_ids = [main.IGNITION_ENERGY, main.POKEGEAR, main.LILLIE_DETERMINATION]
    assert not cinderace_solo_ignition.has_bench_energy_receiver()
    assert policy_for(cinderace_solo_ignition).score_play(play_option(main.POKEGEAR)) > policy_for(cinderace_solo_ignition).score_attach(attach_option(ignition, cinderace_solo_ignition.active))

    class CinderaceReceiverBoard(FakeBoard):
        def has_bench_energy_receiver(self):
            return True

    cinderace_receiver_ignition = CinderaceReceiverBoard(active_id=main.CINDERACE, bench=[staryu], options=[attach_option(ignition, staryu)])
    assert cinderace_receiver_ignition.has_bench_energy_receiver()
    assert policy_for(cinderace_receiver_ignition).score_attach(attach_option(ignition, cinderace_receiver_ignition.active)) > policy_for(cinderace_solo_ignition).score_attach(attach_option(ignition, cinderace_solo_ignition.active))

    main_ignition_board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water], options=[attach_option(ignition, evolved_target)])
    main_ignition_board._hand_ids = [main.IGNITION_ENERGY, main.POFIN, main.MEGA_STARMIE_EX]
    assert policy_for(main_ignition_board).score_attach(attach_option(ignition, main_ignition_board.active)) > policy_for(cinderace_ignition_board).score_attach(attach_option(ignition, cinderace_ignition_board.active))

    mega_yuki = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=52, energies=[water])
    shaymin = pokemon(main.SHAYMIN, hp=80, max_hp=80, serial=53)
    yveltal = pokemon(main.YVELTAL, hp=110, max_hp=110, serial=54)
    ignition_targets_board = FakeBoard(active_id=main.CINDERACE, bench=[evolved_target, mega_yuki, shaymin, yveltal])
    assert policy_for(ignition_targets_board).score_attach(attach_option(ignition, evolved_target)) > policy_for(ignition_targets_board).score_attach(attach_option(ignition, mega_yuki))
    assert policy_for(ignition_targets_board).score_attach(attach_option(ignition, mega_yuki)) > policy_for(ignition_targets_board).score_attach(attach_option(ignition, ignition_targets_board.active))
    assert policy_for(ignition_targets_board).score_attach(attach_option(ignition, shaymin)) < 0
    assert policy_for(ignition_targets_board).score_attach(attach_option(ignition, yveltal)) < 0

    jetting_only_attacks = {
        main.JETTING_BLOW: attack(main.JETTING_BLOW, 50, [colorless, colorless, colorless]),
        main.NEBULA_BEAM: attack(main.NEBULA_BEAM, 180, [main.EnergyType.WATER, colorless, colorless, colorless]),
    }
    wall_board = FakeBoard(target_id=330, active_energies=[], attacks=jetting_only_attacks)
    outcome = main.ImmediateOutcomeEvaluator(wall_board).evaluate_attach(attach_option(ignition, wall_board.active))
    assert outcome.enables_attack
    assert main.JETTING_BLOW in outcome.enabled_attack_ids
    assert "ignition_immediate_attack" not in outcome.reasons

    wall_board = FakeBoard(target_id=330, active_energies=[water])
    outcome = main.ImmediateOutcomeEvaluator(wall_board).evaluate_attach(attach_option(ignition, wall_board.active))
    assert outcome.enables_attack
    assert main.NEBULA_BEAM in outcome.enabled_attack_ids
    assert "enables_nebula_beam" in outcome.reasons
    assert "ignition_immediate_attack" in outcome.reasons

    normal_board = FakeBoard(target_id=999, active_energies=[], attacks=jetting_only_attacks)
    outcome = main.ImmediateOutcomeEvaluator(normal_board).evaluate_attach(attach_option(ignition, normal_board.active))
    assert outcome.enables_attack
    assert main.JETTING_BLOW in outcome.enabled_attack_ids
    assert "ignition_immediate_attack" in outcome.reasons

    bench_target = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=30, energies=[water])
    board = FakeBoard(active_energies=[], bench=[bench_target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(ignition, bench_target))
    assert outcome.enables_attack
    assert main.NEBULA_BEAM in outcome.enabled_attack_ids
    assert "ignition_immediate_attack" not in outcome.reasons

    board = FakeBoard(active_energies=[water, ignition])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(water, board.active))
    assert not outcome.enables_attack
    assert outcome.enabled_attack_ids == ()
    assert "no_new_attack" in outcome.reasons
    immediate_board = FakeBoard(active_energies=[water])
    assert policy_for(board).score_attach(attach_option(ignition, board.active)) < policy_for(immediate_board).score_attach(attach_option(ignition, immediate_board.active))

    jet = option(main.OptionType.ATTACK, main.JETTING_BLOW)

    class SteelBoard(FakeBoard):
        def opponent_profile(self):
            return "STEEL"

    steel_nebula_route = SteelBoard(
        active_energies=[water, dark],
        target_hp=300,
        options=[jet],
    )
    steel_nebula_route._options = [attach_option(water, steel_nebula_route.active), jet]
    assert policy_for(steel_nebula_route).score_attach(attach_option(water, steel_nebula_route.active)) > policy_for(steel_nebula_route).score_attack(jet)

    class WallBoard(FakeBoard):
        def opponent_profile(self):
            return "WALL"

    wall_nebula_route = WallBoard(
        active_energies=[water, dark],
        target_hp=300,
        options=[jet],
    )
    wall_nebula_route._options = [attach_option(water, wall_nebula_route.active), jet]
    assert policy_for(wall_nebula_route).score_attach(attach_option(water, wall_nebula_route.active)) > policy_for(wall_nebula_route).score_attack(jet)

    bench_starmie = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=64, energies=[water, dark])
    steel_bench_nebula = SteelBoard(
        active_energies=[water],
        bench=[bench_starmie],
        target_hp=300,
        options=[jet],
    )
    steel_bench_nebula._options = [attach_option(water, bench_starmie), jet]
    assert policy_for(steel_bench_nebula).score_attack(jet) > policy_for(steel_bench_nebula).score_attach(attach_option(water, bench_starmie))

    steel_no_nebula_attach = SteelBoard(
        active_energies=[water, dark],
        target_hp=300,
        options=[jet],
    )
    assert policy_for(steel_no_nebula_attach).score_attack(jet) > policy_for(steel_no_nebula_attach).score_attach(attach_option(water, steel_no_nebula_attach.active))

    steel_jet_ko = SteelBoard(
        active_energies=[water, dark],
        target_hp=40,
        prizes_left=2,
        options=[jet],
    )
    steel_jet_ko._options = [attach_option(water, steel_jet_ko.active), jet]
    assert policy_for(steel_jet_ko).score_attack(jet) > policy_for(steel_jet_ko).score_attach(attach_option(water, steel_jet_ko.active))

    steel_jet_win = SteelBoard(
        active_energies=[water, dark],
        target_hp=40,
        prizes_left=1,
        options=[jet],
    )
    steel_jet_win._options = [attach_option(water, steel_jet_win.active), jet]
    assert policy_for(steel_jet_win).score_attack(jet) > policy_for(steel_jet_win).score_attach(attach_option(water, steel_jet_win.active))

    normal_nebula_route = FakeBoard(
        active_energies=[water, dark],
        target_hp=300,
        options=[jet],
    )
    normal_nebula_route._options = [attach_option(water, normal_nebula_route.active), jet]
    assert policy_for(normal_nebula_route).score_attack(jet) > policy_for(normal_nebula_route).score_attach(attach_option(water, normal_nebula_route.active))

    board = FakeBoard(active_energies=[])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_option(999999, board.active))
    assert not outcome.supported
    assert "unsupported_attach_energy" in outcome.reasons


def test_turbo_flare_attach_target_priority():
    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=60)
    shaymin = pokemon(main.SHAYMIN, hp=80, max_hp=80, serial=61, energies=[main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY])
    cinderace = pokemon(main.CINDERACE, hp=150, max_hp=160, serial=62)
    board = FakeBoard(
        active_id=main.CINDERACE,
        bench=[shaymin, staryu, cinderace],
        effect_id=main.CINDERACE,
    )
    board.select.context = main.SelectContext.ATTACH_TO

    policy = policy_for(board)
    staryu_score = policy.score_target_or_card(switch_target_option(staryu))
    shaymin_score = policy.score_target_or_card(switch_target_option(shaymin))
    cinderace_score = policy.score_target_or_card(switch_target_option(cinderace))

    assert staryu_score > shaymin_score
    assert staryu_score > cinderace_score
    assert shaymin_score < 0

    board.select.context = main.SelectContext.ATTACH_FROM
    assert policy.score_target_or_card(switch_target_option(staryu)) > policy.score_target_or_card(switch_target_option(shaymin))


def test_boss_outcomes():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY

    win_target = pokemon(998, hp=40, max_hp=300, serial=50)
    board = FakeBoard(prizes_left=2, active_energies=[water], opp_bench=[win_target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(win_target)
    assert outcome.wins_game and outcome.knockout and outcome.prizes_taken == 3
    assert "boss_wins_game" in outcome.reasons
    assert policy_for(board).score_boss() >= main.SCORE_FORCED

    ko_target = pokemon(999, hp=40, max_hp=100, serial=51)
    no_ko_target = pokemon(999, hp=100, max_hp=100, serial=52)
    board = FakeBoard(active_energies=[water], opp_bench=[ko_target, no_ko_target])
    assert policy_for(board).score_boss_outcome(main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(ko_target)) > policy_for(board).score_boss_outcome(main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(no_ko_target))

    target = pokemon(999, hp=100, max_hp=100, serial=53)
    board = FakeBoard(target_id=330, active_energies=[water], opp_bench=[target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(target)
    assert outcome.avoids_wall
    assert "boss_avoids_wall" in outcome.reasons
    assert outcome.damage > 0

    wall_target = pokemon(330, hp=100, max_hp=100, serial=54)
    board = FakeBoard(active_energies=[water], opp_bench=[wall_target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(wall_target)
    assert not outcome.avoids_wall

    engine_target = pokemon(main.RIOLU, hp=70, max_hp=70, serial=55)
    board = FakeBoard(active_energies=[water], opp_bench=[engine_target], plan_boss_targets={main.RIOLU})
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(engine_target)
    assert outcome.breaks_engine
    assert "boss_breaks_engine" in outcome.reasons

    board = FakeBoard(active_energies=[], opp_bench=[target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(target)
    assert outcome.damage == 0 and not outcome.knockout
    assert "boss_no_effective_attack" in outcome.reasons

    board = FakeBoard(active_energies=[water], opp_bench=[wall_target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(wall_target)
    assert outcome.damage == 0 and not outcome.knockout
    assert "boss_no_effective_attack" in outcome.reasons

    blocked_and_zero_attacks = {
        main.JETTING_BLOW: attack(main.JETTING_BLOW, 50, [main.EnergyType.WATER]),
        main.NEBULA_BEAM: attack(main.NEBULA_BEAM, 0, [main.EnergyType.WATER]),
    }
    board = FakeBoard(active_energies=[water], opp_bench=[wall_target], attacks=blocked_and_zero_attacks)
    board._data[main.MEGA_STARMIE_EX].attacks = [main.JETTING_BLOW, main.NEBULA_BEAM]
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(wall_target)
    assert not outcome.blocked
    assert outcome.damage == 0 and not outcome.knockout
    assert "boss_no_effective_attack" not in outcome.reasons

    board = FakeBoard(active_energies=[water, dark, dark], opp_bench=[wall_target])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(wall_target)
    assert outcome.bypasses_wall
    assert outcome.damage > 0

    instant_win = pokemon(998, hp=40, max_hp=300, serial=56)
    normal_ko = pokemon(999, hp=40, max_hp=100, serial=57)
    engine = pokemon(main.RIOLU, hp=70, max_hp=70, serial=58)
    damage_only = pokemon(999, hp=200, max_hp=200, serial=59)
    board = FakeBoard(prizes_left=2, active_energies=[water], opp_bench=[damage_only, engine, normal_ko, instant_win], plan_boss_targets={main.RIOLU})
    scores = {
        target.serial: policy_for(board).score_target_or_card(attach_option(main.BEFEHL_VON_BOSS, target))
        for target in [instant_win, normal_ko, engine, damage_only]
    }
    assert scores[instant_win.serial] > scores[normal_ko.serial] > scores[engine.serial] > scores[damage_only.serial]
    engine_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_target(engine)
    assert engine_outcome.breaks_engine
    assert policy_for(board).score_boss_outcome(engine_outcome) == engine_outcome.damage * 500 + 160000


def test_boss_play_reachable_ko_rank_rules():
    water = main.BASIC_WATER_ENERGY
    boss = play_option(main.BEFEHL_VON_BOSS)
    attack_option = option(main.OptionType.ATTACK, main.NEBULA_BEAM)
    target = pokemon(999, hp=210, max_hp=210, serial=760)
    board = FakeBoard(
        target_hp=300,
        active_energies=[water, water, water],
        opp_bench=[target],
        options=[attack_option, boss],
        attacks={
            main.NEBULA_BEAM: attack(main.NEBULA_BEAM, 210, [main.EnergyType.COLORLESS, main.EnergyType.COLORLESS, main.EnergyType.COLORLESS]),
        },
    )
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_play(boss)
    assert outcome.supported
    assert outcome.damage == 0 and not outcome.knockout and outcome.prizes_taken == 0 and not outcome.wins_game
    assert outcome.reachable_damage == 210
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert not outcome.reachable_wins_game
    assert outcome.target_serial == 760
    assert "boss_play_reachable_knockout" in outcome.reasons
    assert "boss_play_takes_prizes" in outcome.reasons

    ranked = main.GameSimulator(board).rank_options()
    boss_result = next(result for result in ranked if result.option is boss)
    attack_result = next(result for result in ranked if result.option is attack_option)
    assert boss_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert attack_result.action_score.tier < boss_result.action_score.tier
    assert ranked[0].option is boss


def test_boss_play_reachable_engine_ko_rank_rules():
    water = main.BASIC_WATER_ENERGY
    boss = play_option(main.BEFEHL_VON_BOSS)
    hilda = play_option(main.HILDA)
    attack_option = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    target = pokemon(main.RIOLU, hp=120, max_hp=120, serial=8)
    board = FakeBoard(
        target_hp=300,
        active_energies=[water],
        opp_bench=[target],
        options=[hilda, boss, attack_option],
        plan_boss_targets={main.RIOLU},
        attacks={
            main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER]),
        },
    )
    ranked = main.GameSimulator(board).rank_options()
    boss_result = next(result for result in ranked if result.option is boss)
    hilda_result = next(result for result in ranked if result.option is hilda)
    assert boss_result.outcome.reachable_damage == 120
    assert boss_result.outcome.reachable_knockout
    assert boss_result.outcome.reachable_prizes_taken == 1
    assert boss_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert hilda_result.action_score.tier < boss_result.action_score.tier
    assert ranked[0].option is boss


def test_boss_play_reachable_win_and_wall_rank_rules():
    water = main.BASIC_WATER_ENERGY
    boss = play_option(main.BEFEHL_VON_BOSS)
    direct_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    win_target = pokemon(999, hp=120, max_hp=120, serial=91)
    board = FakeBoard(
        target_hp=300,
        prizes_left=1,
        active_energies=[water],
        opp_bench=[win_target],
        options=[boss, direct_attack],
        attacks={
            main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER]),
        },
    )
    ranked = main.GameSimulator(board).rank_options()
    boss_result = next(result for result in ranked if result.option is boss)
    assert boss_result.outcome.reachable_wins_game
    assert boss_result.outcome.reachable_knockout
    assert boss_result.outcome.reachable_prizes_taken == 1
    assert boss_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert boss_result.action_score.tier != main.TIER_WIN

    wall_bench = pokemon(999, hp=120, max_hp=120, serial=92)
    wall_board = FakeBoard(
        target_id=330,
        target_hp=300,
        active_energies=[water],
        opp_bench=[wall_bench],
        options=[boss, direct_attack],
        attacks={
            main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER]),
        },
    )
    wall_ranked = main.GameSimulator(wall_board).rank_options()
    wall_boss = next(result for result in wall_ranked if result.option is boss)
    assert wall_boss.outcome.reachable_knockout
    assert wall_boss.outcome.reachable_prizes_taken == 1
    assert not wall_boss.outcome.avoids_wall
    assert wall_boss.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_boss_play_negative_guards():
    water = main.BASIC_WATER_ENERGY

    def board_with_boss(**kwargs):
        boss = play_option(main.BEFEHL_VON_BOSS)
        target = kwargs.pop("target", pokemon(999, hp=120, max_hp=120, serial=93))
        attacks = kwargs.pop("attacks", {main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER])})
        board = FakeBoard(
            target_hp=300,
            active_energies=kwargs.pop("active_energies", [water]),
            opp_bench=kwargs.pop("opp_bench", [target]),
            options=kwargs.pop("options", [boss]),
            attacks=attacks,
            **kwargs,
        )
        return board, boss

    guarded_cases = []

    board, boss = board_with_boss()
    board.state.supporterPlayed = True
    guarded_cases.append((board, boss))

    board, boss = board_with_boss(opp_bench=[])
    guarded_cases.append((board, boss))

    board, boss = board_with_boss()
    board.active = None
    guarded_cases.append((board, boss))

    board, boss = board_with_boss(active_energies=[])
    guarded_cases.append((board, boss))

    wall_target = pokemon(330, hp=120, max_hp=120, serial=94)
    board, boss = board_with_boss(target=wall_target, opp_bench=[wall_target])
    guarded_cases.append((board, boss))

    no_ko_target = pokemon(999, hp=200, max_hp=200, serial=95)
    board, boss = board_with_boss(target=no_ko_target, opp_bench=[no_ko_target])
    guarded_cases.append((board, boss))

    board, boss = board_with_boss()
    board.me.asleep = True
    guarded_cases.append((board, boss))

    board, boss = board_with_boss()
    board.me.paralyzed = True
    guarded_cases.append((board, boss))

    board, boss = board_with_boss(turn=1, first_player=0, your_index=0)
    guarded_cases.append((board, boss))

    for board, boss in guarded_cases:
        outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_play(boss)
        assert outcome.reachable_attack_id is None
        assert outcome.reachable_damage == 0
        assert not outcome.reachable_knockout
        assert outcome.reachable_prizes_taken == 0
        assert not outcome.reachable_wins_game
        result = action_score_for_option(board, boss)
        assert result.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    boss = play_option(main.BEFEHL_VON_BOSS)
    board = FakeBoard(
        target_hp=300,
        active_energies=[water],
        opp_bench=[pokemon(999, hp=120, max_hp=120, serial=96)],
        options=[],
        attacks={main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER])},
    )
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_play(boss)
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 0
    assert not outcome.reachable_wins_game

    non_boss = play_option(main.POFIN)
    board = FakeBoard(options=[non_boss])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_play(non_boss)
    assert not outcome.supported


def test_boss_attack_declaration_guards_fact_policy_and_rank():
    water = main.BASIC_WATER_ENERGY
    cases = [
        ("asleep", {"asleep": True}),
        ("paralyzed", {"paralyzed": True}),
        ("first_player_turn_one", {"turn": 1, "first_player": 0, "your_index": 0}),
    ]

    for _name, flags in cases:
        boss = play_option(main.BEFEHL_VON_BOSS)
        end = option(main.OptionType.END)
        target = pokemon(999, hp=120, max_hp=120, serial=810)
        board = FakeBoard(
            target_hp=300,
            active_energies=[water],
            opp_bench=[target],
            options=[boss, end],
            attacks={main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER])},
            turn=flags.get("turn"),
            first_player=flags.get("first_player"),
            your_index=flags.get("your_index", 0),
        )
        board.me.asleep = flags.get("asleep", False)
        board.me.paralyzed = flags.get("paralyzed", False)

        evaluator = main.ImmediateOutcomeEvaluator(board)
        target_outcome = evaluator.evaluate_boss_target(target)
        assert target_outcome.damage == 0
        assert not target_outcome.knockout
        assert target_outcome.prizes_taken == 0
        assert not target_outcome.wins_game
        assert target_outcome.reasons == ("boss_target", "boss_no_effective_attack")

        play_outcome = evaluator.evaluate_boss_play(boss)
        assert play_outcome.reachable_damage == 0
        assert not play_outcome.reachable_knockout
        assert play_outcome.reachable_prizes_taken == 0
        assert not play_outcome.reachable_wins_game

        policy = main.Policy(board)
        assert policy.score_boss() == -50000
        assert policy.score_play(boss) == -50000
        assert not policy.has_real_development_option()
        assert policy.score_end() == -100

        ranked = main.GameSimulator(board).rank_options()
        boss_result = next(result for result in ranked if result.option is boss)
        end_result = next(result for result in ranked if result.option is end)
        assert boss_result.action_score.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP
        assert boss_result.policy_score == -50000
        assert end_result.policy_score == -100
        assert ranked.index(end_result) < ranked.index(boss_result)
        assert ranked[0].option is end


def test_boss_play_target_selection_matches_boss_context():
    water = main.BASIC_WATER_ENERGY
    boss = play_option(main.BEFEHL_VON_BOSS)
    lower_prize_target = pokemon(999, hp=210, max_hp=210, serial=811)
    best_target = pokemon(998, hp=210, max_hp=210, serial=812)
    board = FakeBoard(
        target_hp=300,
        active_energies=[water, water, water],
        opp_bench=[lower_prize_target, best_target],
        options=[boss],
        attacks={
            main.NEBULA_BEAM: attack(main.NEBULA_BEAM, 210, [main.EnergyType.COLORLESS, main.EnergyType.COLORLESS, main.EnergyType.COLORLESS]),
        },
    )
    board._data[main.MEGA_STARMIE_EX].attacks = [main.NEBULA_BEAM]

    play_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_boss_play(boss)
    assert play_outcome.reachable_knockout
    assert play_outcome.target_serial == best_target.serial

    lower_option = switch_target_option(lower_prize_target)
    best_option = switch_target_option(best_target)
    board._options = [lower_option, best_option]
    ranked = main.GameSimulator(board).rank_options()
    assert ranked[0].option is best_option
    assert ranked[0].outcome.knockout
    assert ranked[0].outcome.target_serial == play_outcome.target_serial


def test_boss_play_direct_attack_guards():
    water = main.BASIC_WATER_ENERGY
    boss = play_option(main.BEFEHL_VON_BOSS)
    direct_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    bench_target = pokemon(999, hp=120, max_hp=120, serial=97)
    ko_board = FakeBoard(
        target_hp=120,
        active_energies=[water],
        opp_bench=[bench_target],
        options=[boss, direct_attack],
        attacks={main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER])},
    )
    ko_ranked = main.GameSimulator(ko_board).rank_options()
    assert ko_ranked[0].option is direct_attack
    assert ko_ranked[0].action_score.tier == main.TIER_KO
    assert next(result for result in ko_ranked if result.option is boss).action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP

    win_board = FakeBoard(
        target_hp=120,
        prizes_left=1,
        active_energies=[water],
        opp_bench=[bench_target],
        options=[boss, direct_attack],
        attacks={main.JETTING_BLOW: attack(main.JETTING_BLOW, 120, [main.EnergyType.WATER])},
    )
    win_ranked = main.GameSimulator(win_board).rank_options()
    assert win_ranked[0].option is direct_attack
    assert win_ranked[0].action_score.tier == main.TIER_WIN
    assert next(result for result in win_ranked if result.option is boss).action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_tool_scrapper_outcomes():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    hero = energy_card(main.HERO_CAPE, 901)
    normal_tool = energy_card(999777, 902)

    target = pokemon(999, hp=140, max_hp=240, serial=60)
    target.tools = [hero]
    board = FakeBoard(active_energies=[water], opp_bench=[target], effect_id=main.TOOL_SCRAPPER)
    original_tools = list(target.tools)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target)
    assert outcome.damage == 0
    assert outcome.removes_tool
    assert outcome.enables_knockout
    assert "removes_hero_cape" in outcome.reasons
    assert "tool_scrapper_enables_ko" in outcome.reasons
    assert target.tools == original_tools
    assert policy_for(board).score_play(play_option(main.TOOL_SCRAPPER)) >= main.SCORE_PREFERRED

    target = pokemon(999, hp=40, max_hp=140, serial=61)
    target.tools = [hero]
    board = FakeBoard(active_energies=[water], opp_bench=[target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target)
    assert outcome.damage == 0
    assert outcome.removes_tool
    assert outcome.knockout
    assert outcome.prizes_taken == 1
    assert not outcome.enables_knockout
    assert "tool_removal_causes_knockout" in outcome.reasons

    ex_target = pokemon(998, hp=70, max_hp=170, serial=601)
    ex_target.tools = [hero]
    board = FakeBoard(active_energies=[], opp_bench=[ex_target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(ex_target)
    assert outcome.damage == 0
    assert outcome.knockout
    assert outcome.prizes_taken == 3
    assert not outcome.enables_knockout

    board = FakeBoard(active_energies=[], opp_bench=[ex_target], prizes_left=3, effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(ex_target)
    assert outcome.damage == 0
    assert outcome.wins_game
    assert policy_for(board).score_play(play_option(main.TOOL_SCRAPPER)) >= main.SCORE_FORCED

    normal_ex = pokemon(997, hp=70, max_hp=170, serial=602)
    normal_ex.tools = [hero]
    board = FakeBoard(active_energies=[], opp_bench=[normal_ex], effect_id=main.TOOL_SCRAPPER)
    board._data[997] = SimpleNamespace(ex=True, megaEx=False, attacks=[])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(normal_ex)
    assert outcome.damage == 0
    assert outcome.knockout
    assert outcome.prizes_taken == 2

    target = pokemon(999, hp=300, max_hp=400, serial=62)
    target.tools = [hero]
    board = FakeBoard(active_energies=[water], opp_bench=[target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target)
    assert outcome.damage == 0
    assert outcome.removes_tool
    assert not outcome.enables_knockout
    assert "removes_hero_cape" in outcome.reasons

    target = pokemon(999, hp=140, max_hp=140, serial=63)
    board = FakeBoard(active_energies=[water], opp_bench=[target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target)
    assert outcome.damage == 0
    assert not outcome.supported
    assert "tool_scrapper_no_target" in outcome.reasons
    assert policy_for(board).score_play(play_option(main.TOOL_SCRAPPER)) < 0

    target = pokemon(999, hp=140, max_hp=240, serial=64)
    target.tools = [normal_tool, hero]
    board = FakeBoard(active_energies=[water], opp_bench=[target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target, 0)
    assert outcome.damage == 0
    assert outcome.removes_tool
    assert "removes_hero_cape" not in outcome.reasons
    assert not outcome.enables_knockout

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target)
    assert outcome.damage == 0
    assert not outcome.supported
    assert "tool_scrapper_no_target" in outcome.reasons

    target = pokemon(999, hp=140, max_hp=140, serial=65)
    target.tools = [normal_tool]
    board = FakeBoard(active_energies=[water], opp_bench=[target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(target)
    assert outcome.damage == 0
    assert outcome.removes_tool
    assert not outcome.enables_knockout
    assert "removes_hero_cape" not in outcome.reasons

    wall_target = pokemon(330, hp=140, max_hp=240, serial=66)
    wall_target.tools = [hero]
    board = FakeBoard(active_energies=[water], opp_bench=[wall_target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(wall_target)
    assert outcome.damage == 0
    assert not outcome.enables_knockout

    board = FakeBoard(active_energies=[water, dark, dark], opp_bench=[wall_target], effect_id=main.TOOL_SCRAPPER)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_tool_scrapper_target(wall_target)
    assert outcome.damage == 0

    win_target = pokemon(999, hp=40, max_hp=140, serial=67)
    win_target.tools = [hero]
    ko_target = pokemon(999, hp=140, max_hp=240, serial=68)
    ko_target.tools = [hero]
    key_target = pokemon(999, hp=300, max_hp=400, serial=69)
    key_target.tools = [hero]
    normal_target = pokemon(999, hp=140, max_hp=140, serial=70)
    normal_target.tools = [normal_tool]
    board = FakeBoard(active_energies=[water], opp_bench=[normal_target, key_target, ko_target, win_target], effect_id=main.TOOL_SCRAPPER)
    scores = {
        target.serial: policy_for(board).score_target_or_card(tool_target_option(target))
        for target in [win_target, ko_target, key_target, normal_target]
    }
    assert scores[win_target.serial] > scores[ko_target.serial] > scores[key_target.serial] > scores[normal_target.serial]


def test_retreat_and_switch_outcomes():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ignition = main.IGNITION_ENERGY

    weak_wall = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=80, energies=[water])
    board = FakeBoard(active_energies=[water, dark, dark], bench=[weak_wall])
    retreat = option(main.OptionType.RETREAT)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.retreat_energy_cost == 2
    assert outcome.important_energy_loss == 0
    assert outcome.target_id is None
    assert outcome.target_serial is None
    assert outcome.recommended_target_id == weak_wall.id
    assert outcome.recommended_target_serial == weak_wall.serial
    assert "retreat_from_ready_attacker" in outcome.reasons
    switch_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(weak_wall, "retreat")
    assert switch_outcome.target_id == weak_wall.id
    assert switch_outcome.target_serial == weak_wall.serial
    assert switch_outcome.recommended_target_id is None
    assert switch_outcome.recommended_target_serial is None
    assert switch_outcome.damage == 0
    assert not switch_outcome.knockout
    assert not switch_outcome.wins_game
    assert "retreat_no_damage_improvement" in switch_outcome.reasons
    assert policy_for(board).score_switch_target(weak_wall) < 0
    assert policy_for(board).score_retreat(retreat) == main.SCORE_FORBIDDEN

    ready_starmie = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=81, energies=[water, dark, dark])
    board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[ready_starmie], target_hp=180)
    board._data[main.YUKIWARASHI].retreatCost = 1
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(ready_starmie, "retreat")
    assert outcome.enables_attack
    assert outcome.enables_knockout
    assert not outcome.knockout
    assert outcome.damage == 0
    assert "retreat_enables_attack" in outcome.reasons
    assert "switch_enables_knockout" in outcome.reasons
    assert policy_for(board).score_switch_target(ready_starmie) >= main.SCORE_FORCED // 2

    board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[ready_starmie], target_hp=180, prizes_left=1)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(ready_starmie, "retreat")
    assert "switch_enables_win" in outcome.reasons
    assert not outcome.wins_game

    board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[ready_starmie], target_hp=180)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.target_id is None
    assert outcome.target_serial is None
    assert outcome.recommended_target_id == ready_starmie.id
    assert outcome.recommended_target_serial == ready_starmie.serial
    assert outcome.enables_attack
    assert outcome.enables_knockout
    assert "switch_enables_knockout" in outcome.reasons

    board = FakeBoard(active_id=main.CINDERACE, active_energies=[ignition], bench=[ready_starmie], target_hp=260)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(ready_starmie, "retreat")
    assert "retreat_from_ready_attacker" not in outcome.reasons
    assert outcome.improves_damage
    assert "role_handoff" in outcome.reasons

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert "role_handoff" in outcome.reasons
    assert policy_for(board).score_retreat(retreat) > 0

    class AcceleratingBoard(FakeBoard):
        def cinderace_can_accelerate(self):
            return True

        def has_bench_energy_receiver(self):
            return True

    board = AcceleratingBoard(active_id=main.CINDERACE, active_energies=[ignition], bench=[ready_starmie], target_hp=300)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(ready_starmie, "retreat")
    assert "retreat_from_ready_attacker" in outcome.reasons
    assert policy_for(board).score_switch_target(ready_starmie) > 0
    assert policy_for(board).score_retreat(retreat) > 0

    empty_mega = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=82, energies=[])
    board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[empty_mega])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(empty_mega, "retreat")
    assert "zero_energy_mega_wall" in outcome.reasons
    assert policy_for(board).score_switch_target(empty_mega) == main.SCORE_FORBIDDEN

    board = FakeBoard(active_energies=[water], bench=[weak_wall])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.important_energy_loss > 0
    assert policy_for(board).score_retreat(retreat) < 0

    board = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water, dark], bench=[ready_starmie])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.retreat_energy_cost == 1
    assert outcome.important_energy_loss == 0

    board = FakeBoard(active_energies=[water, dark], bench=[ready_starmie])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.retreat_energy_cost == 2
    assert outcome.important_energy_loss == 1

    board = FakeBoard(active_energies=[ignition], bench=[ready_starmie])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.important_energy_loss > 0

    water_target = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=83, energies=[water, dark, dark])
    board = FakeBoard(active_id=main.HITODEMAN, active_energies=[], bench=[water_target], target_hp=180, effect_id=main.SURFING_BEACH)
    board.select.context = main.SelectContext.EFFECT_TARGET
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(water_target, "surfing_beach")
    assert outcome.target_id == water_target.id
    assert outcome.target_serial == water_target.serial
    assert outcome.recommended_target_id is None
    assert outcome.recommended_target_serial is None
    assert outcome.retreat_energy_cost == 0
    assert outcome.important_energy_loss == 0
    assert "surfing_beach_switch" in outcome.reasons
    assert policy_for(board).score_target_or_card(switch_target_option(water_target)) > 0

    non_water_target = pokemon(main.YVELTAL, hp=120, max_hp=120, serial=831, energies=[dark])
    board = FakeBoard(active_id=main.HITODEMAN, active_energies=[], bench=[non_water_target], effect_id=main.SURFING_BEACH)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(non_water_target, "surfing_beach")
    assert not outcome.supported

    class BenchDamageBoard(FakeBoard):
        def opponent_profile(self):
            return "BENCH_DAMAGE"

        def is_pokemon(self, card_id):
            return card_id in self._data

    class GenericBenchThreatBoard(FakeBoard):
        def opponent_has_bench_damage_threat(self):
            return True

        def is_pokemon(self, card_id):
            return card_id in self._data

    shaymin = pokemon(main.SHAYMIN, hp=80, max_hp=80, serial=832)
    board = BenchDamageBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[shaymin])
    assert policy_for(board).score_switch_target(shaymin) == main.SCORE_FORBIDDEN

    board = BenchDamageBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[shaymin], active_in_danger=True)
    assert policy_for(board).score_switch_target(shaymin) > main.SCORE_FORBIDDEN

    board = GenericBenchThreatBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[shaymin])
    assert policy_for(board).score_switch_target(shaymin) == main.SCORE_FORBIDDEN

    wall_target = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=84, energies=[water, dark, dark])
    board = FakeBoard(active_id=main.HITODEMAN, active_energies=[water], target_id=330, bench=[wall_target], target_hp=200)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(wall_target, "retreat")
    assert outcome.damage == 0
    assert outcome.improves_damage

    other_mega = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=85, energies=[])
    board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[empty_mega, ready_starmie, other_mega], target_hp=180)
    chosen = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(empty_mega, "retreat")
    assert chosen.target_serial == empty_mega.serial
    assert "zero_energy_mega_wall" in chosen.reasons

    board = FakeBoard(active_energies=[water, ignition, dark], bench=[ready_starmie])
    board.select.context = main.SelectContext.DISCARD_ENERGY_CARD
    board.select.remainEnergyCost = 1
    by_serial = energy_select_option(board.active, serial=board.active.energyCards[1].serial)
    by_index = energy_select_option(board.active, energy_index=2)
    assert main.ImmediateOutcomeEvaluator(board).evaluate_retreat_energy_selection(by_serial).important_energy_loss == 1
    assert main.ImmediateOutcomeEvaluator(board).evaluate_retreat_energy_selection(by_index).important_energy_loss == 0
    assert policy_for(board).score_energy_selection(by_serial) == 0

    low_hp_active = pokemon(main.MEGA_STARMIE_EX, hp=70, max_hp=280, serial=86, energies=[])
    board = FakeBoard(bench=[ready_starmie])
    board.active = low_hp_active
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert "survival_retreat" not in outcome.reasons

    board = FakeBoard(active_in_danger=True, bench=[ready_starmie])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert "survival_retreat" in outcome.reasons

    board = FakeBoard(bench=[])
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert outcome.target_id is None
    assert outcome.target_serial is None
    assert outcome.recommended_target_id is None
    assert outcome.recommended_target_serial is None
    assert "retreat_no_target" in outcome.reasons


def test_cinderace_receiver_handoff_issue7():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ignition = main.IGNITION_ENERGY

    class CinderaceReceiverBoard(FakeBoard):
        def cinderace_can_accelerate(self):
            return main.BoardView.cinderace_can_accelerate(self)

        def has_bench_energy_receiver(self):
            return main.BoardView.has_bench_energy_receiver(self)

    def handoff_board(target_hp, prizes_left=6):
        turbo = option(main.OptionType.ATTACK, main.TURBO_FLARE)
        retreat = option(main.OptionType.RETREAT)
        end = option(main.OptionType.END)
        ready_starmie = pokemon(
            main.MEGA_STARMIE_EX,
            hp=280,
            max_hp=280,
            serial=900,
            energies=[water, dark, dark],
        )
        developing_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=901)
        board = CinderaceReceiverBoard(
            active_id=main.CINDERACE,
            active_energies=[ignition],
            bench=[ready_starmie, developing_staryu],
            target_hp=target_hp,
            prizes_left=prizes_left,
            options=[turbo, retreat, end],
        )
        board._attacks[main.NEBULA_BEAM] = attack(
            main.NEBULA_BEAM,
            210,
            [main.EnergyType.COLORLESS] * 3,
        )
        return board, turbo, retreat

    ko_board, ko_turbo, ko_retreat = handoff_board(target_hp=200)
    ko_ranked = main.GameSimulator(ko_board).rank_options()
    ko_result = next(result for result in ko_ranked if result.option is ko_retreat)
    assert ko_board.has_bench_energy_receiver()
    assert ko_result.outcome.reachable_knockout
    assert ko_result.outcome.reachable_prizes_taken == 1
    assert ko_result.outcome.reachable_damage == 210
    assert ko_ranked[0].option is ko_retreat
    assert ko_ranked.index(ko_result) < next(
        index for index, result in enumerate(ko_ranked) if result.option is ko_turbo
    )

    damage_board, damage_turbo, damage_retreat = handoff_board(target_hp=300)
    damage_ranked = main.GameSimulator(damage_board).rank_options()
    damage_result = next(result for result in damage_ranked if result.option is damage_retreat)
    turbo_result = next(result for result in damage_ranked if result.option is damage_turbo)
    assert damage_result.outcome.improves_damage
    assert damage_result.outcome.reachable_damage == 210
    assert turbo_result.outcome.damage == 50
    assert damage_result.action_score.tier == main.TIER_NON_KO_ATTACK
    assert damage_result.action_score.pressure > turbo_result.action_score.pressure
    assert damage_ranked[0].option is damage_retreat

    win_board, win_turbo, win_retreat = handoff_board(target_hp=200, prizes_left=1)
    win_ranked = main.GameSimulator(win_board).rank_options()
    win_result = next(result for result in win_ranked if result.option is win_retreat)
    assert win_result.outcome.reachable_wins_game
    assert win_ranked[0].option is win_retreat
    assert win_ranked.index(win_result) < next(
        index for index, result in enumerate(win_ranked) if result.option is win_turbo
    )

    comparison_board, comparison_turbo, comparison_retreat = handoff_board(
        target_hp=40,
        prizes_left=2,
    )
    current_ko = main.ImmediateOutcome(
        damage=50,
        knockout=True,
        prizes_taken=1,
        wins_game=False,
    )

    win_policy = policy_for(comparison_board)
    win_policy.best_current_attack_outcome = lambda: current_ko
    handoff_win = main.ImmediateOutcome(
        reachable_attack_id=main.NEBULA_BEAM,
        reachable_damage=210,
        reachable_knockout=True,
        reachable_prizes_taken=1,
        reachable_wins_game=True,
        improves_damage=True,
        reasons=("role_handoff", "switch_enables_win"),
    )
    turbo_ko_score = win_policy.action_score(comparison_turbo, 1290000, current_ko)
    handoff_win_score = win_policy.action_score(comparison_retreat, 500000000, handoff_win)
    assert win_policy.cinderace_handoff_improves_current_turn(handoff_win)
    assert handoff_win_score.tier == main.TIER_WIN
    assert handoff_win_score.tier > turbo_ko_score.tier

    prize_policy = policy_for(comparison_board)
    prize_policy.best_current_attack_outcome = lambda: current_ko
    handoff_more_prizes = main.ImmediateOutcome(
        reachable_attack_id=main.NEBULA_BEAM,
        reachable_damage=210,
        reachable_knockout=True,
        reachable_prizes_taken=2,
        reachable_wins_game=False,
        improves_damage=True,
        reasons=("role_handoff", "switch_enables_knockout"),
    )
    handoff_prize_score = prize_policy.action_score(
        comparison_retreat,
        500000000,
        handoff_more_prizes,
    )
    assert prize_policy.cinderace_handoff_improves_current_turn(handoff_more_prizes)
    assert handoff_prize_score.tier == main.TIER_KO
    assert handoff_prize_score.immediate > turbo_ko_score.immediate

    equal_board, equal_turbo, equal_retreat = handoff_board(target_hp=40, prizes_left=2)
    equal_ranked = main.GameSimulator(equal_board).rank_options()
    equal_retreat_result = next(
        result for result in equal_ranked
        if result.option is equal_retreat
    )
    equal_turbo_result = next(
        result for result in equal_ranked
        if result.option is equal_turbo
    )
    assert equal_turbo_result.outcome.knockout
    assert not equal_turbo_result.outcome.wins_game
    assert equal_retreat_result.outcome.reachable_knockout
    assert equal_retreat_result.outcome.reachable_prizes_taken == equal_turbo_result.outcome.prizes_taken
    assert not policy_for(equal_board).cinderace_handoff_improves_current_turn(equal_retreat_result.outcome)
    assert equal_ranked[0].option is equal_turbo

    turbo = option(main.OptionType.ATTACK, main.TURBO_FLARE)
    retreat = option(main.OptionType.RETREAT)
    end = option(main.OptionType.END)
    unfinished_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=902)
    unfinished_board = CinderaceReceiverBoard(
        active_id=main.CINDERACE,
        active_energies=[ignition],
        bench=[unfinished_staryu],
        target_hp=300,
        options=[turbo, retreat, end],
    )
    unfinished_ranked = main.GameSimulator(unfinished_board).rank_options()
    assert unfinished_board.has_bench_energy_receiver()
    assert unfinished_ranked[0].option is turbo
    assert policy_for(unfinished_board).score_retreat(retreat) == main.SCORE_FORBIDDEN

    turbo = option(main.OptionType.ATTACK, main.TURBO_FLARE)
    retreat = option(main.OptionType.RETREAT)
    end = option(main.OptionType.END)
    partial_starmie = pokemon(
        main.MEGA_STARMIE_EX,
        hp=280,
        max_hp=280,
        serial=903,
        energies=[water],
    )
    completion_board = CinderaceReceiverBoard(
        active_id=main.CINDERACE,
        active_energies=[ignition],
        bench=[partial_starmie],
        target_hp=300,
        options=[turbo, retreat, end],
        deck_ids=[water, dark],
    )
    completion_tokens = completion_board.energy_tokens(partial_starmie) + [
        main.EnergyType.COLORLESS,
        main.EnergyType.COLORLESS,
    ]
    assert not completion_board.can_pay_attack(partial_starmie, completion_board.attack(main.NEBULA_BEAM))
    assert main.can_pay_attack_with_tokens(completion_board.attack(main.NEBULA_BEAM), completion_tokens)
    assert main.GameSimulator(completion_board).rank_options()[0].option is turbo

    direct_board, direct_turbo, direct_retreat = handoff_board(target_hp=40, prizes_left=1)
    direct_ranked = main.GameSimulator(direct_board).rank_options()
    direct_result = next(result for result in direct_ranked if result.option is direct_turbo)
    assert direct_result.outcome.wins_game
    assert direct_result.outcome.knockout
    assert direct_ranked[0].option is direct_turbo
    assert policy_for(direct_board).score_retreat(direct_retreat) == main.SCORE_FORBIDDEN

    replay_board_value, _next_action = replay_board("参考ログ/v8/第1弾/88525828.json", 58, 1)
    replay_ranked = main.GameSimulator(replay_board_value).rank_options()
    replay_retreat = next(
        result for result in replay_ranked
        if result.option.type == main.OptionType.RETREAT
    )
    assert replay_retreat.outcome.reachable_damage == 210
    assert not replay_retreat.outcome.reachable_knockout
    assert replay_retreat.outcome.improves_damage
    assert replay_ranked[0].option is replay_retreat.option


def test_attack_effect_target_outcomes():
    target = pokemon(999, hp=40, max_hp=100, serial=90)
    other = pokemon(999, hp=100, max_hp=100, serial=91)
    board = FakeBoard(opp_bench=[target, other], prizes_left=1)
    board.select.context = main.SelectContext.DAMAGE
    board.logs = [attack_log(main.JETTING_BLOW)]
    original_hp = target.hp
    original_bench = list(board.opp_bench)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(target))
    assert outcome.supported
    assert outcome.damage == 50
    assert outcome.knockout
    assert outcome.prizes_taken == 1
    assert not outcome.wins_game
    assert outcome.target_id == target.id
    assert outcome.target_serial == target.serial
    assert "jetting_blow_secondary_damage" in outcome.reasons
    assert "wins_game" not in outcome.reasons
    assert policy_for(board).score_damage_target(switch_target_option(target)) < main.SCORE_FORCED
    assert target.hp == original_hp
    assert board.opp_bench == original_bench

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(other))
    assert outcome.supported
    assert outcome.damage == 50
    assert not outcome.knockout

    board.logs = [attack_log(main.NEBULA_BEAM)]
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(target))
    assert not outcome.supported
    assert "unsupported_attack_effect" in outcome.reasons

    board.logs = []
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(target))
    assert not outcome.supported
    assert policy_for(board).score_damage_target(switch_target_option(target)) == main.SCORE_LAST_RESORT

    direct_attack_id_option = switch_target_option(target)
    direct_attack_id_option.attackId = main.JETTING_BLOW
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(direct_attack_id_option)
    assert not outcome.supported

    board.logs = [attack_log(main.JETTING_BLOW)]
    board.select.context = main.SelectContext.EFFECT_TARGET
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(target))
    assert not outcome.supported

    board.select.context = main.SelectContext.DAMAGE
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(board.opp_active))
    assert not outcome.supported

    board.logs = [attack_log(main.JETTING_BLOW)]
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack_effect_target(switch_target_option(target))
    assert outcome.supported
    assert policy_for(board).score_damage_target(switch_target_option(target)) > main.SCORE_LAST_RESORT


def test_discard_cost_priority():
    def discard_choice(card_id):
        return SimpleNamespace(
            type=3,
            cardId=card_id,
            area=None,
            index=None,
            playerIndex=None,
            inPlayArea=None,
            inPlayIndex=None,
            toolIndex=None,
            energyIndex=None,
            attackId=None,
            serial=None,
            number=None,
        )

    class BenchDamageBoard(FakeBoard):
        def opponent_profile(self):
            return "BENCH_DAMAGE"

        def is_pokemon(self, card_id):
            return card_id in self._data

    class GenericBenchThreatBoard(FakeBoard):
        def opponent_has_bench_damage_threat(self):
            return True

        def is_pokemon(self, card_id):
            return card_id in self._data

    bench_damage = BenchDamageBoard(options=[play_option(main.SHAYMIN), play_option(main.HITODEMAN)])
    assert policy_for(bench_damage).score_play(play_option(main.SHAYMIN)) > policy_for(bench_damage).score_play(play_option(main.HITODEMAN))

    generic_bench_threat = GenericBenchThreatBoard(options=[play_option(main.SHAYMIN), play_option(main.HITODEMAN)])
    assert policy_for(generic_bench_threat).score_play(play_option(main.SHAYMIN)) > policy_for(generic_bench_threat).score_play(play_option(main.HITODEMAN))

    shaymin_search = BenchDamageBoard(options=[discard_choice(main.SHAYMIN), discard_choice(main.YVELTAL)])
    shaymin_search.select.context = main.SelectContext.TO_HAND
    shaymin_search.select.effect = SimpleNamespace(id=main.HYPERBALL)
    assert policy_for(shaymin_search).score_card_selection(discard_choice(main.SHAYMIN)) > policy_for(shaymin_search).score_card_selection(discard_choice(main.YVELTAL))

    generic_shaymin_search = GenericBenchThreatBoard(options=[discard_choice(main.SHAYMIN), discard_choice(main.YVELTAL)])
    generic_shaymin_search.select.context = main.SelectContext.TO_HAND
    generic_shaymin_search.select.effect = SimpleNamespace(id=main.HYPERBALL)
    assert policy_for(generic_shaymin_search).score_card_selection(discard_choice(main.SHAYMIN)) > policy_for(generic_shaymin_search).score_card_selection(discard_choice(main.YVELTAL))

    pokegear_salvatore = FakeBoard(
        options=[discard_choice(main.CRISPIN), discard_choice(main.SALVATORE), discard_choice(main.LILLIE_DETERMINATION)],
        salvatore_live=True,
        needs_mega_starmie=True,
    )
    pokegear_salvatore.select.context = main.SelectContext.TO_HAND
    pokegear_salvatore.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert main.choose_indices(pokegear_salvatore) == [1]
    assert policy_for(pokegear_salvatore).score_card_selection(discard_choice(main.SALVATORE)) > policy_for(pokegear_salvatore).score_card_selection(discard_choice(main.CRISPIN))

    pokegear_complete = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        target_id=main.HITODEMAN,
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_complete.select.context = main.SelectContext.TO_HAND
    pokegear_complete.select.effect = SimpleNamespace(id=main.POKEGEAR)
    pokegear_complete._hand_ids = [
        main.POKEGEAR,
        main.BASIC_WATER_ENERGY,
        main.CRISPIN,
        main.HERO_CAPE,
    ]
    pokegear_complete.starmie_needs_energy = lambda: False
    assert policy_for(pokegear_complete).score_card_selection(discard_choice(main.LILLIE_DETERMINATION)) == 1000

    pokegear_wall_blocked = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        target_id=330,
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_wall_blocked.select.context = main.SelectContext.TO_HAND
    pokegear_wall_blocked.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert not main.ImmediateOutcomeEvaluator(pokegear_wall_blocked).has_energy_payable_unblocked_active_attack()

    pokegear_nebula_wall = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.IGNITION_ENERGY,),
        target_id=330,
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_nebula_wall.select.context = main.SelectContext.TO_HAND
    pokegear_nebula_wall.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert main.ImmediateOutcomeEvaluator(pokegear_nebula_wall).has_energy_payable_unblocked_active_attack()

    pokegear_asleep = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        target_id=main.HITODEMAN,
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_asleep.me = SimpleNamespace(asleep=True, paralyzed=False)
    assert not main.ImmediateOutcomeEvaluator(pokegear_asleep).has_energy_payable_unblocked_active_attack()

    pokegear_paralyzed = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        target_id=main.HITODEMAN,
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_paralyzed.me = SimpleNamespace(asleep=False, paralyzed=True)
    assert not main.ImmediateOutcomeEvaluator(pokegear_paralyzed).has_energy_payable_unblocked_active_attack()

    pokegear_recovery = FakeBoard(
        active_id=main.HITODEMAN,
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
        needs_mega_starmie=True,
    )
    pokegear_recovery.select.context = main.SelectContext.TO_HAND
    pokegear_recovery.select.effect = SimpleNamespace(id=main.POKEGEAR)
    pokegear_recovery._hand_ids = [
        main.WALLY_COMPASSION,
        main.BASIC_WATER_ENERGY,
        main.TANKER,
        main.POKEGEAR,
        main.MEGA_STARMIE_EX,
    ]
    assert policy_for(pokegear_recovery).score_card_selection(discard_choice(main.LILLIE_DETERMINATION)) > policy_for(pokegear_recovery).score_card_selection(discard_choice(main.BEFEHL_VON_BOSS))

    boss_lethal_candidate = pokemon(998, hp=50, max_hp=50, serial=41)
    pokegear_boss_lethal = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        prizes_left=3,
        opp_bench=[boss_lethal_candidate],
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_boss_lethal.select.context = main.SelectContext.TO_HAND
    pokegear_boss_lethal.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert policy_for(pokegear_boss_lethal).score_card_selection(discard_choice(main.BEFEHL_VON_BOSS)) > policy_for(pokegear_boss_lethal).score_card_selection(discard_choice(main.LILLIE_DETERMINATION))

    boss_engine_candidate = pokemon(main.RIOLU, hp=50, max_hp=70, serial=42)
    pokegear_boss_engine = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        opp_bench=[boss_engine_candidate],
        plan_boss_targets={main.RIOLU},
        options=[discard_choice(main.BEFEHL_VON_BOSS), discard_choice(main.LILLIE_DETERMINATION)],
    )
    pokegear_boss_engine.select.context = main.SelectContext.TO_HAND
    pokegear_boss_engine.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert policy_for(pokegear_boss_engine).score_card_selection(discard_choice(main.BEFEHL_VON_BOSS)) > policy_for(pokegear_boss_engine).score_card_selection(discard_choice(main.LILLIE_DETERMINATION))

    pokegear_dead_salvatore = FakeBoard(
        active_id=main.CINDERACE,
        options=[discard_choice(main.SALVATORE), discard_choice(main.CRISPIN)],
    )
    pokegear_dead_salvatore.select.context = main.SelectContext.TO_HAND
    pokegear_dead_salvatore.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert policy_for(pokegear_dead_salvatore).score_card_selection(discard_choice(main.SALVATORE)) < policy_for(pokegear_dead_salvatore).score_card_selection(discard_choice(main.CRISPIN))
    assert policy_for(pokegear_dead_salvatore).score_card_selection(discard_choice(main.SALVATORE)) == 1000

    pokegear_crispin_needed = FakeBoard(
        active_id=main.HITODEMAN,
        options=[discard_choice(main.CRISPIN), discard_choice(main.LILLIE_DETERMINATION)],
        needs_mega_starmie=True,
    )
    pokegear_crispin_needed.select.context = main.SelectContext.TO_HAND
    pokegear_crispin_needed.select.effect = SimpleNamespace(id=main.POKEGEAR)
    pokegear_crispin_needed._hand_ids = [
        main.POKEGEAR,
        main.CRISPIN,
        main.BEFEHL_VON_BOSS,
        main.HERO_CAPE,
        main.CINDERACE,
        main.YVELTAL,
        main.SHAYMIN,
    ]
    assert policy_for(pokegear_crispin_needed).score_card_selection(discard_choice(main.CRISPIN)) > policy_for(pokegear_crispin_needed).score_card_selection(discard_choice(main.LILLIE_DETERMINATION))

    pokegear_crispin_not_needed = FakeBoard(options=[discard_choice(main.CRISPIN)])
    pokegear_crispin_not_needed.select.context = main.SelectContext.TO_HAND
    pokegear_crispin_not_needed.select.effect = SimpleNamespace(id=main.POKEGEAR)
    pokegear_crispin_not_needed.starmie_needs_energy = lambda: False
    assert policy_for(pokegear_crispin_not_needed).score_card_selection(discard_choice(main.CRISPIN)) == 1000

    yuki_sub_attacker = FakeBoard(
        options=[discard_choice(main.MEGA_YUKIMENOKO_EX), discard_choice(main.YUKIWARASHI), discard_choice(main.SHAYMIN)],
        needs_mega_yuki=True,
    )
    assert policy_for(yuki_sub_attacker).card_need_score(main.MEGA_YUKIMENOKO_EX) > policy_for(yuki_sub_attacker).card_need_score(main.SHAYMIN)
    assert policy_for(yuki_sub_attacker).score_play(play_option(main.YUKIWARASHI)) > policy_for(yuki_sub_attacker).score_play(play_option(main.YVELTAL))
    assert policy_for(yuki_sub_attacker).score_evolve(discard_choice(main.MEGA_YUKIMENOKO_EX)) > 0

    lillie_for_missing_evolution = FakeBoard(
        active_id=main.HITODEMAN,
        bench=[pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=31)],
        options=[play_option(main.LILLIE_DETERMINATION), play_option(main.CRISPIN)],
        needs_mega_starmie=True,
        needs_mega_yuki=True,
    )
    lillie_for_missing_evolution._hand_ids = [
        main.LILLIE_DETERMINATION,
        main.CRISPIN,
        main.BEFEHL_VON_BOSS,
        main.HERO_CAPE,
    ]
    assert policy_for(lillie_for_missing_evolution).score_play(play_option(main.LILLIE_DETERMINATION)) > policy_for(lillie_for_missing_evolution).score_play(play_option(main.CRISPIN))

    lillie_preserves_live_route = FakeBoard(
        active_id=main.HITODEMAN,
        options=[play_option(main.LILLIE_DETERMINATION), play_option(main.SALVATORE)],
        salvatore_live=True,
        needs_mega_starmie=True,
    )
    lillie_preserves_live_route._hand_ids = [
        main.LILLIE_DETERMINATION,
        main.SALVATORE,
        main.BASIC_WATER_ENERGY,
        main.BEFEHL_VON_BOSS,
    ]
    assert policy_for(lillie_preserves_live_route).score_play(play_option(main.LILLIE_DETERMINATION)) < 0
    assert policy_for(lillie_preserves_live_route).score_play(play_option(main.SALVATORE)) > policy_for(lillie_preserves_live_route).score_play(play_option(main.LILLIE_DETERMINATION))

    options = [
        discard_choice(main.BASIC_WATER_ENERGY),
        discard_choice(main.HERO_CAPE),
        discard_choice(main.SALVATORE),
        discard_choice(main.CRISPIN),
        discard_choice(main.MEGA_SIGNAL),
    ]
    board = FakeBoard(active_id=main.CINDERACE, options=options)
    board.select.context = main.SelectContext.DISCARD
    board.select.effect = SimpleNamespace(id=main.HYPERBALL)
    board.select.minCount = 2
    board.select.maxCount = 2
    assert main.choose_indices(board) == [3, 4]

    live_salvatore = FakeBoard(active_id=main.HITODEMAN, options=[discard_choice(main.SALVATORE), discard_choice(main.CRISPIN)], salvatore_live=True, needs_mega_starmie=True)
    live_salvatore.select.context = main.SelectContext.DISCARD
    live_salvatore.select.effect = SimpleNamespace(id=main.HYPERBALL)
    assert main.choose_indices(live_salvatore) == [1]

    mega_signal_live = FakeBoard(active_id=main.HITODEMAN, options=[discard_choice(main.MEGA_SIGNAL), discard_choice(main.CRISPIN)], needs_mega_starmie=True)
    mega_signal_live.select.context = main.SelectContext.DISCARD
    mega_signal_live.select.effect = SimpleNamespace(id=main.HYPERBALL)
    assert main.choose_indices(mega_signal_live) == [1]

    shaymin_protect = BenchDamageBoard(options=[discard_choice(main.SHAYMIN), discard_choice(main.CRISPIN)])
    shaymin_protect.select.context = main.SelectContext.DISCARD
    shaymin_protect.select.effect = SimpleNamespace(id=main.HYPERBALL)
    assert main.choose_indices(shaymin_protect) == [1]

    generic_shaymin_protect = GenericBenchThreatBoard(options=[discard_choice(main.SHAYMIN), discard_choice(main.CRISPIN)])
    generic_shaymin_protect.select.context = main.SelectContext.DISCARD
    generic_shaymin_protect.select.effect = SimpleNamespace(id=main.HYPERBALL)
    assert main.choose_indices(generic_shaymin_protect) == [1]


def test_main_axis_evolve_priority():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY

    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=101)
    jet = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    starmie_followup = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water, dark, dark], bench=[staryu], target_hp=300)
    starmie_evolve = evolve_option(main.MEGA_STARMIE_EX, staryu)
    redundant_attach = attach_option(water, starmie_followup.active)
    starmie_followup._options = [starmie_evolve, redundant_attach, jet]
    starmie_policy = policy_for(starmie_followup)
    assert starmie_policy.score_evolve(starmie_evolve) > starmie_policy.score_attack(jet)
    assert starmie_policy.score_evolve(starmie_evolve) > starmie_policy.score_attach(redundant_attach)

    snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=102)
    resentful = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    froslass_followup = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water, dark, dark], bench=[snorunt], target_hp=300)
    froslass_followup.opp.handCount = 0
    froslass_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, snorunt)
    froslass_followup._options = [froslass_evolve, resentful]
    froslass_policy = policy_for(froslass_followup)
    assert froslass_policy.score_evolve(froslass_evolve) > froslass_policy.score_attack(resentful)

    high_damage_froslass = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water, dark, dark], bench=[snorunt], target_hp=500)
    high_damage_froslass.opp.handCount = 8
    high_damage_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, snorunt)
    high_damage_froslass._options = [high_damage_evolve, resentful]
    high_damage_policy = policy_for(high_damage_froslass)
    assert high_damage_policy.score_attack(resentful) > high_damage_policy.score_evolve(high_damage_evolve)

    nebula_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=103)
    nebula_board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water, dark], bench=[nebula_staryu], target_hp=300)
    nebula_attach = attach_option(water, nebula_board.active)
    nebula_evolve = evolve_option(main.MEGA_STARMIE_EX, nebula_staryu)
    nebula_board._options = [nebula_attach, nebula_evolve]
    nebula_policy = policy_for(nebula_board)
    assert nebula_policy.score_attach(nebula_attach) > nebula_policy.score_evolve(nebula_evolve)

    absolute_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=104)
    absolute_board = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water, dark], bench=[absolute_snorunt], target_hp=300)
    absolute_attach = attach_option(water, absolute_board.active)
    absolute_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, absolute_snorunt)
    absolute_board._options = [absolute_attach, absolute_evolve]
    absolute_policy = policy_for(absolute_board)
    assert absolute_policy.score_attach(absolute_attach) > absolute_policy.score_evolve(absolute_evolve)

    ko_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=105)
    ko_board = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water], bench=[ko_snorunt], target_hp=100)
    ko_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, ko_snorunt)
    ko_board._options = [ko_evolve, resentful]
    assert policy_for(ko_board).score_attack(resentful) > policy_for(ko_board).score_evolve(ko_evolve)

    win_board = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water], bench=[ko_snorunt], target_hp=100, prizes_left=1)
    win_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, ko_snorunt)
    win_board._options = [win_evolve, resentful]
    assert policy_for(win_board).score_attack(resentful) > policy_for(win_board).score_evolve(win_evolve)

    bench_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=106)
    active_staryu_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[water], bench=[bench_staryu])
    active_staryu_evolve = evolve_option(main.MEGA_STARMIE_EX, active_staryu_board.active)
    bench_staryu_evolve = evolve_option(main.MEGA_STARMIE_EX, bench_staryu)
    active_staryu_board._options = [active_staryu_evolve, bench_staryu_evolve]
    active_staryu_policy = policy_for(active_staryu_board)
    assert active_staryu_policy.score_evolve(active_staryu_evolve) > active_staryu_policy.score_evolve(bench_staryu_evolve)

    bench_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=107)
    active_snorunt_board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[water], bench=[bench_snorunt])
    active_snorunt_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, active_snorunt_board.active)
    bench_snorunt_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, bench_snorunt)
    active_snorunt_board._options = [active_snorunt_evolve, bench_snorunt_evolve]
    active_snorunt_policy = policy_for(active_snorunt_board)
    assert active_snorunt_policy.score_evolve(active_snorunt_evolve) > active_snorunt_policy.score_evolve(bench_snorunt_evolve)

    powered_bench_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=108, energies=[water])
    bench_better_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[], bench=[powered_bench_staryu])
    empty_active_evolve = evolve_option(main.MEGA_STARMIE_EX, bench_better_board.active)
    powered_bench_evolve = evolve_option(main.MEGA_STARMIE_EX, powered_bench_staryu)
    bench_better_board._options = [empty_active_evolve, powered_bench_evolve]
    bench_better_policy = policy_for(bench_better_board)
    assert bench_better_policy.score_evolve(powered_bench_evolve) > bench_better_policy.score_evolve(empty_active_evolve)

    wall_board = FakeBoard(active_id=main.HITODEMAN, target_id=330, active_energies=[water])
    wall_active_evolve = evolve_option(main.MEGA_STARMIE_EX, wall_board.active)
    wall_board._options = [wall_active_evolve]
    assert policy_for(wall_board).score_evolve(wall_active_evolve) < main.SCORE_PREFERRED

    salvatore_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[water])
    salvatore_evolve = evolve_option(main.MEGA_STARMIE_EX, salvatore_board.active)
    salvatore_board._options = [salvatore_evolve]
    normal_score = policy_for(salvatore_board).score_evolve(salvatore_evolve)
    salvatore_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    assert policy_for(salvatore_board).score_evolve(salvatore_evolve) == normal_score

    support_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=109)
    support_board = FakeBoard(active_id=main.CINDERACE, bench=[support_staryu], salvatore_live=True, needs_mega_starmie=True)
    support_evolve = evolve_option(main.MEGA_STARMIE_EX, support_staryu)
    salvatore = play_option(main.SALVATORE)
    support_board._options = [support_evolve, salvatore]
    assert policy_for(support_board).score_play(salvatore) > policy_for(support_board).score_evolve(support_evolve)


def test_salvatore_live_and_target_priority():
    water = main.BASIC_WATER_ENERGY
    ignition = main.IGNITION_ENERGY
    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=201)
    snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=202)

    starmie_with_backup = FakeBoard(active_id=main.MEGA_STARMIE_EX, bench=[staryu])
    assert starmie_with_backup.salvatore_live()
    assert starmie_with_backup.is_salvatore_target(main.MEGA_STARMIE_EX)

    froslass_with_backup = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, bench=[snorunt])
    assert froslass_with_backup.salvatore_live()
    assert froslass_with_backup.is_salvatore_target(main.MEGA_YUKIMENOKO_EX)

    dead_starmie_route = FakeBoard(active_id=main.CINDERACE, bench=[staryu], discard_ids=[main.MEGA_STARMIE_EX] * main.DECK.count(main.MEGA_STARMIE_EX))
    assert not dead_starmie_route.salvatore_live()
    assert not dead_starmie_route.is_salvatore_target(main.MEGA_STARMIE_EX)

    dead_froslass_route = FakeBoard(active_id=main.CINDERACE, bench=[snorunt], discard_ids=[main.MEGA_YUKIMENOKO_EX] * main.DECK.count(main.MEGA_YUKIMENOKO_EX))
    assert not dead_froslass_route.salvatore_live()
    assert not dead_froslass_route.is_salvatore_target(main.MEGA_YUKIMENOKO_EX)

    bench_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=203)
    active_staryu_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[water], bench=[bench_staryu])
    active_staryu_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    staryu_policy = policy_for(active_staryu_board)
    assert staryu_policy.score_target_or_card(switch_target_option(active_staryu_board.active)) > staryu_policy.score_target_or_card(switch_target_option(bench_staryu))

    bench_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=204)
    active_snorunt_board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[water], bench=[bench_snorunt])
    active_snorunt_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    snorunt_policy = policy_for(active_snorunt_board)
    assert snorunt_policy.score_target_or_card(switch_target_option(active_snorunt_board.active)) > snorunt_policy.score_target_or_card(switch_target_option(bench_snorunt))

    ignition_staryu_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[ignition])
    ignition_staryu_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    water_staryu_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[water])
    water_staryu_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    empty_staryu_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[])
    empty_staryu_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    assert policy_for(ignition_staryu_board).score_target_or_card(switch_target_option(ignition_staryu_board.active)) > policy_for(water_staryu_board).score_target_or_card(switch_target_option(water_staryu_board.active))
    assert policy_for(water_staryu_board).score_target_or_card(switch_target_option(water_staryu_board.active)) > policy_for(empty_staryu_board).score_target_or_card(switch_target_option(empty_staryu_board.active))

    ignition_snorunt_board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[water, ignition])
    ignition_snorunt_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    water_snorunt_board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[water])
    water_snorunt_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    empty_snorunt_board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[])
    empty_snorunt_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    assert policy_for(ignition_snorunt_board).score_target_or_card(switch_target_option(ignition_snorunt_board.active)) > policy_for(water_snorunt_board).score_target_or_card(switch_target_option(water_snorunt_board.active))
    assert policy_for(water_snorunt_board).score_target_or_card(switch_target_option(water_snorunt_board.active)) > policy_for(empty_snorunt_board).score_target_or_card(switch_target_option(empty_snorunt_board.active))

    powered_bench_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=205, energies=[water])
    bench_staryu_board = FakeBoard(active_id=main.HITODEMAN, active_energies=[], bench=[powered_bench_staryu])
    bench_staryu_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    bench_staryu_policy = policy_for(bench_staryu_board)
    assert bench_staryu_policy.score_target_or_card(switch_target_option(powered_bench_staryu)) > bench_staryu_policy.score_target_or_card(switch_target_option(bench_staryu_board.active))

    powered_bench_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=206, energies=[water])
    bench_snorunt_board = FakeBoard(active_id=main.YUKIWARASHI, active_energies=[], bench=[powered_bench_snorunt])
    bench_snorunt_board.select.effect = SimpleNamespace(id=main.SALVATORE)
    bench_snorunt_policy = policy_for(bench_snorunt_board)
    assert bench_snorunt_policy.score_target_or_card(switch_target_option(powered_bench_snorunt)) > bench_snorunt_policy.score_target_or_card(switch_target_option(bench_snorunt_board.active))

    two_starmie = pokemon(main.MEGA_STARMIE_EX, hp=330, max_hp=330, serial=207)
    extra_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=208)
    no_third_starmie = FakeBoard(active_id=main.MEGA_STARMIE_EX, bench=[two_starmie, extra_staryu])
    assert main.DECK.count(main.MEGA_STARMIE_EX) == 2
    assert not no_third_starmie.salvatore_live()

    supporter_used = FakeBoard(active_id=main.MEGA_STARMIE_EX, bench=[staryu])
    supporter_used.state.supporterPlayed = True
    assert not supporter_used.salvatore_live()

    no_basic = FakeBoard(active_id=main.CINDERACE, bench=[])
    assert not no_basic.salvatore_live()

    first_starmie = FakeBoard(active_id=main.HITODEMAN, active_energies=[water], bench=[])
    assert first_starmie.salvatore_live()
    assert policy_for(first_starmie).score_play(play_option(main.SALVATORE)) > 1000000

    card_choice = FakeBoard(active_id=main.HITODEMAN, active_energies=[water], bench=[])
    card_choice.select.effect = SimpleNamespace(id=main.SALVATORE)
    card_policy = policy_for(card_choice)
    assert card_policy.score_target_or_card(play_option(main.MEGA_STARMIE_EX)) > 0
    assert card_policy.score_target_or_card(play_option(main.MEGA_YUKIMENOKO_EX)) == main.SCORE_FORBIDDEN


def test_game_simulator_candidate_ordering():
    class TiedPolicy:
        def __init__(self, board):
            self.outcome = main.ImmediateOutcomeEvaluator(board)

        def score(self, index, opt):
            return 12345

        def effect_id(self):
            return None

    weak = option(main.OptionType.ATTACK, 999001)
    jet = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    board = FakeBoard(options=[weak, jet], active_energies=[main.BASIC_WATER_ENERGY], target_hp=100)
    original_active_hp = board.active.hp
    original_target_hp = board.opp_active.hp
    original_energies = list(board.active.energyCards)

    ranked = main.GameSimulator(board, TiedPolicy(board)).rank_options()
    assert ranked[0].option.attackId == main.JETTING_BLOW
    assert board.active.hp == original_active_hp
    assert board.opp_active.hp == original_target_hp
    assert board.active.energyCards == original_energies

    reversed_board = FakeBoard(options=[jet, weak], active_energies=[main.BASIC_WATER_ENERGY], target_hp=100)
    reversed_ranked = main.GameSimulator(reversed_board, TiedPolicy(reversed_board)).rank_options()
    assert reversed_ranked[0].option.attackId == main.JETTING_BLOW

    forced_policy = SimpleNamespace(
        outcome=main.ImmediateOutcomeEvaluator(board),
        score=lambda index, opt: main.SCORE_FORCED,
        effect_id=lambda: None,
    )
    forbidden_policy = SimpleNamespace(
        outcome=main.ImmediateOutcomeEvaluator(board),
        score=lambda index, opt: main.SCORE_FORBIDDEN,
        effect_id=lambda: None,
    )
    assert main.GameSimulator(board, forced_policy).evaluate_candidate(0, jet).tier == "forced"
    assert main.GameSimulator(board, forbidden_policy).evaluate_candidate(0, jet).tier == "forbidden"


def test_structured_action_score_phase1():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY

    def custom_attack(attack_id, damage, bench_damage=0, energies=(main.EnergyType.WATER,)):
        text = ""
        if bench_damage:
            text = "This attack does damage to 1 of your opponent's Benched Pokemon."
        return SimpleNamespace(
            attackId=attack_id,
            damage=damage,
            energies=list(energies),
            text=text,
            bench_damage=bench_damage,
        )

    class ImportantBenchBoard(FakeBoard):
        def __init__(self, important_ids=(), *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._important_ids = set(important_ids)

        def plan_pressure_targets(self):
            return set(self._important_ids)

    def ranked(board):
        return main.GameSimulator(board).rank_options()

    active_150 = option(main.OptionType.ATTACK, 910150)
    active_120_bench_50 = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    attacks = {
        910150: custom_attack(910150, 150),
        main.JETTING_BLOW: custom_attack(main.JETTING_BLOW, 120, bench_damage=50),
    }

    low_bench = pokemon(999, hp=200, max_hp=200, serial=301)
    board = FakeBoard(
        target_hp=300,
        active_energies=[water],
        opp_bench=[low_bench],
        attacks=attacks,
        options=[active_150, active_120_bench_50],
    )
    assert ranked(board)[0].option.attackId == 910150

    important_bench = pokemon(main.RIOLU, hp=100, max_hp=100, serial=302)
    board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=attacks,
        options=[active_150, active_120_bench_50],
    )
    assert ranked(board)[0].option.attackId == main.JETTING_BLOW

    sturdy_important = pokemon(main.RIOLU, hp=300, max_hp=300, serial=303)
    board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=240,
        active_energies=[water],
        opp_bench=[sturdy_important],
        attacks=attacks,
        options=[active_150, active_120_bench_50],
    )
    assert ranked(board)[0].option.attackId == 910150

    payable_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=attacks,
        options=[active_120_bench_50],
    )
    unpayable_attacks = {
        main.JETTING_BLOW: custom_attack(main.JETTING_BLOW, 120, bench_damage=50, energies=(main.EnergyType.DARKNESS,)),
    }
    unpayable_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=unpayable_attacks,
        options=[active_120_bench_50],
    )
    payable_score = ranked(payable_board)[0].action_score.pressure
    unpayable_score = ranked(unpayable_board)[0].action_score.pressure
    assert payable_score > unpayable_score

    jet = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    engine = pokemon(main.RIOLU, hp=100, max_hp=100, serial=304)
    low = pokemon(999, hp=100, max_hp=100, serial=305)
    jet_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[engine, low],
        options=[jet],
    )
    assert ranked(jet_board)[0].action_score.pressure > main.Policy(jet_board).score_attack(jet) // 10
    jet_board.select.context = main.SelectContext.DAMAGE
    jet_board.logs = [attack_log(main.JETTING_BLOW)]
    assert main.Policy(jet_board).score_damage_target(switch_target_option(engine)) > main.Policy(jet_board).score_damage_target(switch_target_option(low))

    high_salvatore_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=306)],
        target_hp=300,
    )
    salvatore = play_option(main.SALVATORE)
    end = option(main.OptionType.END)
    high_salvatore_board._hand_ids = [main.SALVATORE]
    high_salvatore_board._options = [salvatore, jet, end]
    salvatore_ranked = ranked(high_salvatore_board)
    assert salvatore_ranked[0].option.attackId == main.JETTING_BLOW
    assert salvatore_ranked[-1].option.type == main.OptionType.END

    high_lillie_board = FakeBoard(active_energies=[water], target_hp=300)
    lillie = play_option(main.LILLIE_DETERMINATION)
    high_lillie_board._hand_ids = [main.LILLIE_DETERMINATION, main.YVELTAL, main.SHAYMIN, main.HERO_CAPE]
    high_lillie_board._options = [lillie, jet]
    assert ranked(high_lillie_board)[0].option.cardId == main.LILLIE_DETERMINATION

    low_pokegear_board = FakeBoard(active_energies=[water], target_hp=300)
    pokegear = play_option(main.POKEGEAR)
    low_pokegear_board._hand_ids = [main.POKEGEAR]
    low_pokegear_board._options = [pokegear, jet]
    assert ranked(low_pokegear_board)[0].option.attackId == main.JETTING_BLOW

    poffin_board = FakeBoard(active_energies=[water], target_hp=300)
    poffin = play_option(main.POFIN)
    poffin_board._hand_ids = [main.POFIN]
    poffin_board._options = [poffin, jet]
    assert ranked(poffin_board)[0].option.attackId == main.JETTING_BLOW

    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=307)
    evolve = evolve_option(main.MEGA_STARMIE_EX, staryu)
    evolve_board = FakeBoard(active_energies=[water, dark, dark], bench=[staryu], target_hp=300)
    evolve_board._options = [evolve, jet]
    assert ranked(evolve_board)[0].option.cardId == main.MEGA_STARMIE_EX

    ko_board = FakeBoard(active_energies=[water], bench=[staryu], target_hp=50)
    ko_board._hand_ids = [main.SALVATORE]
    ko_board._options = [salvatore, jet]
    assert ranked(ko_board)[0].option.attackId == main.JETTING_BLOW

    win_board = FakeBoard(active_energies=[water], bench=[staryu], target_hp=50, prizes_left=1)
    win_board._hand_ids = [main.SALVATORE]
    win_board._options = [salvatore, jet]
    assert ranked(win_board)[0].option.attackId == main.JETTING_BLOW


def test_attack_pressure_issue4():
    water = main.BASIC_WATER_ENERGY

    def custom_attack(attack_id, damage, energies=(main.EnergyType.WATER,), bench_damage=0):
        text = ""
        if bench_damage:
            text = "This attack does damage to 1 of your opponent's Benched Pokemon."
        return SimpleNamespace(
            attackId=attack_id,
            damage=damage,
            energies=list(energies),
            text=text,
            bench_damage=bench_damage,
        )

    class ImportantBenchBoard(FakeBoard):
        def __init__(self, important_ids=(), *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._important_ids = set(important_ids)

        def plan_pressure_targets(self):
            return set(self._important_ids)

    def ranked(board):
        return main.GameSimulator(board).rank_options()

    active_150 = option(main.OptionType.ATTACK, 940150)
    active_240 = option(main.OptionType.ATTACK, 940240)
    jetting = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    attacks = {
        940150: custom_attack(940150, 150),
        940240: custom_attack(940240, 240),
        main.JETTING_BLOW: custom_attack(main.JETTING_BLOW, 120, bench_damage=50),
    }

    low_bench = pokemon(999, hp=200, max_hp=200, serial=401)
    low_bench_board = FakeBoard(
        target_hp=300,
        active_energies=[water],
        opp_bench=[low_bench],
        attacks=attacks,
        options=[active_150, jetting],
    )
    assert ranked(low_bench_board)[0].option.attackId == 940150

    important_bench = pokemon(main.RIOLU, hp=100, max_hp=100, serial=402)
    important_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=attacks,
        options=[active_150, jetting],
    )
    assert ranked(important_board)[0].option.attackId == main.JETTING_BLOW

    high_active_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=attacks,
        options=[active_240, jetting],
    )
    assert ranked(high_active_board)[0].option.attackId == 940240

    unpayable_attacks = {
        main.JETTING_BLOW: custom_attack(main.JETTING_BLOW, 120, energies=(main.EnergyType.DARKNESS,), bench_damage=50),
    }
    continuing_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=attacks,
        options=[jetting],
    )
    not_continuing_board = ImportantBenchBoard(
        important_ids={main.RIOLU},
        target_hp=300,
        active_energies=[water],
        opp_bench=[important_bench],
        attacks=unpayable_attacks,
        options=[jetting],
    )
    assert ranked(continuing_board)[0].action_score.pressure > ranked(not_continuing_board)[0].action_score.pressure

    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=403)
    salvatore = play_option(main.SALVATORE)
    lillie = play_option(main.LILLIE_DETERMINATION)
    crispin = play_option(main.CRISPIN)
    pokegear = play_option(main.POKEGEAR)
    evolve = evolve_option(main.MEGA_STARMIE_EX, staryu)
    end = option(main.OptionType.END)

    ko_board = FakeBoard(active_energies=[water], bench=[staryu], target_hp=50)
    ko_board._hand_ids = [main.SALVATORE]
    ko_board._options = [salvatore, jetting]
    assert ranked(ko_board)[0].option.attackId == main.JETTING_BLOW

    win_board = FakeBoard(active_energies=[water], bench=[staryu], target_hp=50, prizes_left=1)
    win_board._hand_ids = [main.SALVATORE]
    win_board._options = [salvatore, jetting]
    assert ranked(win_board)[0].option.attackId == main.JETTING_BLOW

    salvatore_board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water], bench=[staryu], target_hp=300)
    salvatore_board._hand_ids = [main.SALVATORE]
    salvatore_board._options = [salvatore, jetting, end]
    assert ranked(salvatore_board)[0].option.attackId == main.JETTING_BLOW
    assert ranked(salvatore_board)[-1].option.type == main.OptionType.END

    lillie_board = FakeBoard(active_energies=[water], target_hp=300)
    lillie_board._hand_ids = [main.LILLIE_DETERMINATION, main.YVELTAL, main.SHAYMIN, main.HERO_CAPE]
    lillie_board._options = [lillie, jetting]
    assert ranked(lillie_board)[0].option.cardId == main.LILLIE_DETERMINATION

    crispin_board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water], target_hp=300)
    crispin_board._hand_ids = [main.CRISPIN]
    crispin_board._options = [crispin, jetting]
    assert ranked(crispin_board)[0].option.cardId == main.CRISPIN

    pokegear_board = FakeBoard(deck_ids=[main.SALVATORE], salvatore_live=True, active_energies=[water], target_hp=300)
    pokegear_board._hand_ids = [main.POKEGEAR]
    pokegear_board._options = [pokegear, jetting]
    assert ranked(pokegear_board)[0].option.cardId == main.POKEGEAR

    evolve_board = FakeBoard(active_energies=[water, main.BASIC_DARK_ENERGY, main.BASIC_DARK_ENERGY], bench=[staryu], target_hp=300)
    evolve_board._options = [evolve, jetting]
    assert ranked(evolve_board)[0].option.cardId == main.MEGA_STARMIE_EX


def test_play_fact_helpers_issue3a():
    board = FakeBoard(active_id=main.CINDERACE)
    board._hand_ids = [
        main.CINDERACE,
        main.CINDERACE,
        main.MEGA_STARMIE_EX,
        main.MEGA_YUKIMENOKO_EX,
        main.TOOL_SCRAPPER,
        main.POFIN,
        main.SALVATORE,
        main.WALLY_COMPASSION,
        main.HERO_CAPE,
        main.MEGA_SIGNAL,
    ]
    facts = board.hand_activity_facts()
    assert facts.hand_size == 10
    assert facts.low_activity_count >= 8
    assert facts.low_activity_ratio >= 0.8

    board = FakeBoard(bench=[pokemon(main.HITODEMAN), pokemon(main.YUKIWARASHI)])
    board._hand_ids = [
        main.MEGA_STARMIE_EX,
        main.MEGA_YUKIMENOKO_EX,
        main.BASIC_WATER_ENERGY,
        main.BASIC_DARK_ENERGY,
        main.IGNITION_ENERGY,
        main.ENERGY_SWITCH,
        main.SURFING_BEACH,
        main.HYPERBALL,
        main.SHAYMIN,
        main.POKEGEAR,
    ]
    facts = board.hand_activity_facts()
    assert facts.hand_size == 10
    assert facts.low_activity_ratio < 0.5

    board = FakeBoard(active_id=main.CINDERACE)
    board._hand_ids = [main.CINDERACE, main.CINDERACE]
    assert [activity for _, activity in board.hand_activity_facts().activities] == [
        main.HAND_ACTIVITY_LOW,
        main.HAND_ACTIVITY_LOW,
    ]

    board = FakeBoard(active_id=main.CINDERACE)
    board._hand_ids = [main.MEGA_STARMIE_EX]
    assert board.hand_activity_facts().activities[0][1] == main.HAND_ACTIVITY_LOW
    board = FakeBoard(bench=[pokemon(main.HITODEMAN)])
    board._hand_ids = [main.MEGA_STARMIE_EX]
    assert board.hand_activity_facts().activities[0][1] == main.HAND_ACTIVITY_LIVE_NOW

    board = FakeBoard()
    board._hand_ids = [main.TOOL_SCRAPPER]
    assert board.hand_activity_facts().activities[0][1] == main.HAND_ACTIVITY_LOW
    tool_target = pokemon(999)
    tool_target.tools = [energy_card(main.HERO_CAPE, 9001)]
    board = FakeBoard(opp_bench=[tool_target])
    board._hand_ids = [main.TOOL_SCRAPPER]
    assert board.hand_activity_facts().activities[0][1] == main.HAND_ACTIVITY_LIVE_NOW

    board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[main.BASIC_WATER_ENERGY])
    energy_facts = board.active_energy_facts()
    assert main.JETTING_BLOW in energy_facts.payable_attack_ids
    assert energy_facts.key_attack_id == main.NEBULA_BEAM
    assert not energy_facts.key_attack_ready
    assert energy_facts.key_attack_missing_units == 2

    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[main.BASIC_WATER_ENERGY, main.BASIC_DARK_ENERGY, main.IGNITION_ENERGY],
    )
    assert board.active_energy_facts().key_attack_ready

    board = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[main.BASIC_WATER_ENERGY])
    energy_facts = board.active_energy_facts()
    assert energy_facts.key_attack_id == main.ABSOLUTE_SNOW
    assert not energy_facts.key_attack_ready
    assert energy_facts.key_attack_missing_units == 2

    board = FakeBoard(active_id=main.CINDERACE, active_energies=[main.BASIC_DARK_ENERGY])
    energy_facts = board.active_energy_facts()
    assert energy_facts.key_attack_id == main.TURBO_FLARE
    assert energy_facts.key_attack_ready

    board = FakeBoard(deck_ids=[main.BASIC_WATER_ENERGY, main.BASIC_DARK_ENERGY])
    assert board.basic_energy_remaining_possible(main.BASIC_WATER_ENERGY)
    assert board.basic_energy_remaining_possible(main.BASIC_DARK_ENERGY)
    board = FakeBoard(
        discard_ids=[main.BASIC_WATER_ENERGY] * main.DECK.count(main.BASIC_WATER_ENERGY)
        + [main.BASIC_DARK_ENERGY] * main.DECK.count(main.BASIC_DARK_ENERGY)
    )
    assert not board.basic_energy_remaining_possible(main.BASIC_WATER_ENERGY)
    assert not board.basic_energy_remaining_possible(main.BASIC_DARK_ENERGY)

    board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[main.IGNITION_ENERGY])
    energy_facts = board.active_energy_facts()
    assert energy_facts.energy_tokens == (
        main.EnergyType.COLORLESS,
        main.EnergyType.COLORLESS,
        main.EnergyType.COLORLESS,
    )
    assert energy_facts.key_attack_ready

    board = FakeBoard(deck_ids=[main.SALVATORE], salvatore_live=True)
    gear = board.pokegear_supporter_facts()
    assert gear.deck_is_public
    assert gear.known_supporter_count == 1
    assert gear.live_supporter_count == 1
    assert not gear.no_target_confirmed

    board = FakeBoard(deck_ids=[main.LILLIE_DETERMINATION])
    board._hand_ids = [main.BASIC_WATER_ENERGY] * 10
    gear = board.pokegear_supporter_facts()
    assert gear.deck_is_public
    assert gear.known_supporter_count == 1
    assert gear.live_supporter_count == 0
    assert gear.dead_supporter_count == 1
    assert gear.no_target_confirmed

    board = FakeBoard(deck_ids=[main.BASIC_WATER_ENERGY])
    gear = board.pokegear_supporter_facts()
    assert gear.deck_is_public
    assert gear.known_supporter_count == 0
    assert gear.no_target_confirmed

    board = FakeBoard()
    gear = board.pokegear_supporter_facts()
    assert not gear.deck_is_public
    assert gear.supporter_remaining_possible
    assert not gear.no_target_confirmed

    supporter_out = [card_id for card_id in main.DECK if main.CARD_TABLE[card_id].cardType == main.CardType.SUPPORTER]
    board = FakeBoard(discard_ids=supporter_out)
    gear = board.pokegear_supporter_facts()
    assert not gear.deck_is_public
    assert not gear.supporter_remaining_possible
    assert gear.no_target_confirmed


def test_play_fact_connected_scoring_issue3b():
    water = main.BASIC_WATER_ENERGY
    jet = option(main.OptionType.ATTACK, main.JETTING_BLOW)

    def score_play(board, card_id):
        return main.Policy(board).score_play(play_option(card_id))

    def top_option(board):
        return main.GameSimulator(board).rank_options()[0].option

    low_hand = [
        main.CINDERACE,
        main.CINDERACE,
        main.MEGA_STARMIE_EX,
        main.MEGA_YUKIMENOKO_EX,
        main.TOOL_SCRAPPER,
        main.POFIN,
        main.SALVATORE,
        main.WALLY_COMPASSION,
        main.HERO_CAPE,
        main.MEGA_SIGNAL,
    ]
    board = FakeBoard(active_id=main.CINDERACE, active_energies=[water], target_hp=300, options=[play_option(main.LILLIE_DETERMINATION), jet])
    board._hand_ids = low_hand
    assert board.hand_activity_facts().low_activity_ratio >= 0.8
    assert score_play(board, main.LILLIE_DETERMINATION) == 86000
    assert top_option(board).cardId == main.LILLIE_DETERMINATION

    live_hand = [
        main.MEGA_STARMIE_EX,
        main.MEGA_YUKIMENOKO_EX,
        main.BASIC_WATER_ENERGY,
        main.BASIC_DARK_ENERGY,
        main.IGNITION_ENERGY,
        main.ENERGY_SWITCH,
        main.SURFING_BEACH,
        main.HYPERBALL,
        main.SHAYMIN,
        main.POKEGEAR,
    ]
    board = FakeBoard(bench=[pokemon(main.HITODEMAN), pokemon(main.YUKIWARASHI)], active_energies=[water], target_hp=300, options=[play_option(main.LILLIE_DETERMINATION), jet])
    board._hand_ids = live_hand
    assert board.hand_activity_facts().low_activity_ratio < 0.5
    assert score_play(board, main.LILLIE_DETERMINATION) == 8000
    assert top_option(board).attackId == main.JETTING_BLOW

    board = FakeBoard(deck_ids=[main.SALVATORE], salvatore_live=True, active_energies=[water], target_hp=300, options=[play_option(main.POKEGEAR), jet])
    board._hand_ids = [main.POKEGEAR]
    assert board.pokegear_supporter_facts().live_supporter_count == 1
    assert score_play(board, main.POKEGEAR) == 58000
    assert top_option(board).cardId == main.POKEGEAR

    board = FakeBoard(deck_ids=[main.BASIC_WATER_ENERGY], active_energies=[water], target_hp=300, options=[play_option(main.POKEGEAR), jet])
    board._hand_ids = [main.POKEGEAR]
    assert board.pokegear_supporter_facts().no_target_confirmed
    assert score_play(board, main.POKEGEAR) == -8000
    assert top_option(board).attackId == main.JETTING_BLOW

    board = FakeBoard(active_energies=[water], target_hp=300, options=[play_option(main.POKEGEAR), jet])
    board._hand_ids = [main.POKEGEAR]
    assert board.pokegear_supporter_facts().supporter_remaining_possible
    assert score_play(board, main.POKEGEAR) == 26000
    assert top_option(board).attackId == main.JETTING_BLOW

    board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water], target_hp=300, options=[play_option(main.CRISPIN), jet])
    board._hand_ids = [main.CRISPIN]
    assert board.active_energy_facts().key_attack_missing_units == 2
    assert score_play(board, main.CRISPIN) == 62000
    assert top_option(board).cardId == main.CRISPIN

    board = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[water, main.BASIC_DARK_ENERGY], target_hp=300, options=[play_option(main.CRISPIN), jet])
    board._hand_ids = [main.CRISPIN]
    assert board.active_energy_facts().key_attack_missing_units == 1
    assert score_play(board, main.CRISPIN) == 82000
    assert top_option(board).cardId == main.CRISPIN

    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water, main.BASIC_DARK_ENERGY, main.IGNITION_ENERGY],
        target_hp=300,
        options=[play_option(main.CRISPIN), jet],
    )
    board._hand_ids = [main.CRISPIN]
    assert board.active_energy_facts().key_attack_ready
    assert score_play(board, main.CRISPIN) == 9000
    assert top_option(board).attackId == main.JETTING_BLOW

    board = FakeBoard(salvatore_live=True, active_energies=[water], target_hp=300, options=[play_option(main.SALVATORE), jet])
    board._hand_ids = [main.SALVATORE]
    assert score_play(board, main.SALVATORE) == main.SCORE_PREFERRED + 125000
    assert top_option(board).attackId == main.JETTING_BLOW

    board = FakeBoard(active_energies=[water], target_hp=300, options=[play_option(main.SALVATORE), jet])
    board._hand_ids = [main.SALVATORE]
    assert score_play(board, main.SALVATORE) == -8000
    assert top_option(board).attackId == main.JETTING_BLOW


def test_crispin_fact_required_energy_issue3b1():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    crispin = play_option(main.CRISPIN)

    def crispin_score(required, deck_ids=None, discard_ids=None, energies=()):
        attacks = {
            main.JETTING_BLOW: attack(main.JETTING_BLOW, 50, [main.EnergyType.WATER]),
            main.NEBULA_BEAM: attack(main.NEBULA_BEAM, 180, required),
        }
        board = FakeBoard(
            active_id=main.MEGA_STARMIE_EX,
            active_energies=energies,
            attacks=attacks,
            deck_ids=deck_ids,
            discard_ids=discard_ids,
        )
        board._hand_ids = [main.CRISPIN]
        return main.Policy(board).score_play(crispin), board.active_energy_facts()

    score, facts = crispin_score([main.EnergyType.WATER], deck_ids=[water])
    assert facts.key_attack_missing_types == (main.EnergyType.WATER,)
    assert score == 82000

    score, facts = crispin_score([main.EnergyType.DARKNESS], deck_ids=[dark])
    assert facts.key_attack_missing_types == (main.EnergyType.DARKNESS,)
    assert score == 82000

    score, facts = crispin_score([main.EnergyType.WATER, main.EnergyType.DARKNESS], deck_ids=[water, dark])
    assert facts.key_attack_missing_types == (main.EnergyType.WATER, main.EnergyType.DARKNESS)
    assert score == 62000

    score, facts = crispin_score(
        [main.EnergyType.WATER],
        discard_ids=[water] * main.DECK.count(water),
    )
    assert not facts.water_remaining_possible
    assert score == 9000

    score, facts = crispin_score(
        [main.EnergyType.DARKNESS],
        discard_ids=[dark] * main.DECK.count(dark),
    )
    assert not facts.dark_remaining_possible
    assert score == 9000

    score, facts = crispin_score(
        [main.EnergyType.WATER, main.EnergyType.DARKNESS],
        discard_ids=[water] * main.DECK.count(water) + [dark] * main.DECK.count(dark),
    )
    assert not facts.water_remaining_possible
    assert not facts.dark_remaining_possible
    assert score == 9000

    score, facts = crispin_score(
        [main.EnergyType.WATER],
        deck_ids=[water],
        energies=[water],
    )
    assert facts.key_attack_ready
    assert score == 9000


def test_role_facts_issue3c():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY

    cinderace_board = FakeBoard(active_id=main.CINDERACE)
    cinderace_board._data[main.CINDERACE].basic = main.CARD_TABLE[main.CINDERACE].basic
    cinderace = cinderace_board.role_facts(cinderace_board.active)
    assert cinderace.retreat_cost == 0
    assert cinderace.free_retreat
    assert cinderace.pivot_candidate
    assert cinderace.evolution
    assert not cinderace.basic
    assert cinderace.key_attack_id == main.TURBO_FLARE
    assert cinderace.key_attack_ready is False

    yveltal_board = FakeBoard(active_id=main.YVELTAL)
    yveltal = yveltal_board.role_facts(yveltal_board.active)
    assert yveltal.retreat_cost == 0
    assert yveltal.free_retreat
    assert yveltal.basic
    assert not yveltal.evolution
    assert yveltal.key_attack_id is None
    assert yveltal.key_attack_ready is None
    assert yveltal.role_completed is None

    shaymin_board = FakeBoard(active_id=main.SHAYMIN)
    shaymin = shaymin_board.role_facts(shaymin_board.active)
    assert shaymin.retreat_cost == 1
    assert not shaymin.free_retreat
    assert not shaymin.pivot_candidate
    assert shaymin.role_completed is None

    backup_starmie = pokemon(main.MEGA_STARMIE_EX, hp=330, max_hp=330, serial=301)
    starmie_board = FakeBoard(active_id=main.MEGA_STARMIE_EX, bench=[backup_starmie])
    starmie = starmie_board.role_facts(starmie_board.active)
    assert starmie.prize_value == 3
    assert starmie.duplicate_count == 2
    assert starmie.mega
    assert starmie.ex
    assert starmie.key_attack_id == main.NEBULA_BEAM

    froslass_board = FakeBoard(active_id=main.MEGA_YUKIMENOKO_EX, active_energies=[water, dark, dark])
    froslass = froslass_board.role_facts(froslass_board.active)
    assert froslass.attack_ready
    assert froslass.key_attack_id == main.ABSOLUTE_SNOW
    assert froslass.key_attack_ready
    assert froslass.role_completed

    staryu_board = FakeBoard(active_id=main.HITODEMAN)
    staryu = staryu_board.role_facts(staryu_board.active)
    assert staryu.basic
    assert not staryu.evolution
    assert staryu.key_attack_id is None
    assert staryu.role_completed is None

    snorunt_board = FakeBoard(active_id=main.YUKIWARASHI)
    snorunt = snorunt_board.role_facts(snorunt_board.active)
    assert snorunt.basic
    assert not snorunt.evolution
    assert snorunt.key_attack_id is None
    assert snorunt.role_completed is None

    bench_staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=302, energies=[water])
    bench_board = FakeBoard(active_id=main.CINDERACE, bench=[bench_staryu])
    bench_facts = bench_board.role_facts(bench_staryu)
    assert bench_facts.current_position == "BENCH"
    assert bench_facts.bench_slot_cost == 1
    assert bench_facts.attack_ready
    assert bench_facts.ready_if_promoted

    ignition_starmie = FakeBoard(active_id=main.MEGA_STARMIE_EX, active_energies=[main.IGNITION_ENERGY])
    ignition_facts = ignition_starmie.role_facts(ignition_starmie.active)
    assert ignition_facts.key_attack_id == main.NEBULA_BEAM
    assert ignition_facts.key_attack_ready

    empty_staryu = FakeBoard(active_id=main.HITODEMAN)
    assert not empty_staryu.role_facts(empty_staryu.active).attack_ready


def p0_froslass_attach_board(
    status: Optional[str] = None,
    turn: Optional[int] = None,
    first_player: Optional[int] = None,
    your_index: int = 0,
):
    water = main.BASIC_WATER_ENERGY
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=501, energies=[water])],
        target_hp=140,
        prizes_left=1,
        turn=turn,
        first_player=first_player,
        your_index=your_index,
    )
    board.opp.handCount = 19
    if status == "asleep":
        board.me = SimpleNamespace(asleep=True, paralyzed=False)
    elif status == "paralyzed":
        board.me = SimpleNamespace(asleep=False, paralyzed=True)
    else:
        board.me = SimpleNamespace(asleep=False, paralyzed=False)
    active_attach = attach_option(water, board.active)
    bench_attach = attach_option(water, board.bench[0])
    board._options = [bench_attach, active_attach]
    return board, active_attach, bench_attach


def action_score_for_option(board: FakeBoard, target_option: Any) -> main.ActionScore:
    for result in main.GameSimulator(board).rank_options():
        if result.option is target_option:
            return result.action_score
    raise AssertionError("option not ranked")


class ReplayObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, _name):
        return None


def replay_object(value):
    if isinstance(value, dict):
        return ReplayObject(**{key: replay_object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [replay_object(item) for item in value]
    return value


def replay_board(relative_path: str, step: int, player_index: int = 0):
    root = Path(__file__).resolve().parents[5]
    data = json.loads((root / relative_path).read_text(encoding="utf-8"))
    entry = data["steps"][step][player_index]
    board = main.BoardView(replay_object(entry["observation"]))
    next_action = data["steps"][step + 1][player_index]["action"]
    return board, next_action


def replay_ct_board(relative_path: str, step: int):
    root = Path(__file__).resolve().parents[5]
    data = json.loads((root / relative_path).read_text(encoding="utf-8"))
    initial_decks = data["steps"][0][0]["visualize"][0]["action"]
    matching_players = [
        player_index
        for player_index, initial_deck in enumerate(initial_decks)
        if Counter(initial_deck) == Counter(main.DECK)
    ]
    assert len(matching_players) == 1
    player_index = matching_players[0]
    entry = data["steps"][step][player_index]
    board = main.BoardView(replay_object(entry["observation"]))
    next_action = data["steps"][step + 1][player_index]["action"]
    return board, next_action


def option_description(board: main.BoardView, option: Any) -> tuple:
    if option.type == main.OptionType.ATTACH:
        target = board.option_target(option)
        return ("ATTACH", board.option_card(option), board.pid(target), getattr(target, "serial", None))
    if option.type == main.OptionType.PLAY:
        return ("PLAY", board.option_card(option), None, None)
    if option.type == main.OptionType.ATTACK or option.attackId is not None:
        return ("ATTACK", option.attackId, None, None)
    if option.type == main.OptionType.RETREAT:
        return ("RETREAT", None, None, None)
    if option.type == main.OptionType.END:
        return ("END", None, None, None)
    target = board.option_target(option)
    return (int(option.type), board.option_card(option), board.pid(target), getattr(target, "serial", None))


def test_replay_88489763_step96_boss_play_rank():
    board, _next_action = replay_board("参考ログ/v8/第1弾/88489763.json", 96, 0)
    ranked = main.GameSimulator(board).rank_options()
    boss_results = [
        result
        for result in ranked
        if result.option.type == main.OptionType.PLAY and board.option_card(result.option) == main.BEFEHL_VON_BOSS
    ]
    assert boss_results
    boss_result = boss_results[0]
    assert boss_result.outcome.reachable_damage == 210
    assert boss_result.outcome.reachable_knockout
    assert boss_result.outcome.reachable_prizes_taken == 1
    assert not boss_result.outcome.reachable_wins_game
    assert boss_result.outcome.target_serial == 74
    assert boss_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert ranked[0].option is boss_result.option


def test_replay_88477647_step83_boss_play_rank():
    board, _next_action = replay_board("参考ログ/v8/第1弾/88477647.json", 83, 1)
    ranked = main.GameSimulator(board).rank_options()
    boss_results = [
        result
        for result in ranked
        if result.option.type == main.OptionType.PLAY and board.option_card(result.option) == main.BEFEHL_VON_BOSS
    ]
    assert boss_results
    boss_result = boss_results[0]
    assert boss_result.outcome.reachable_damage == 120
    assert boss_result.outcome.reachable_knockout
    assert boss_result.outcome.reachable_prizes_taken == 1
    assert not boss_result.outcome.reachable_wins_game
    assert boss_result.outcome.target_serial == 8
    assert boss_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert ranked[0].option is boss_result.option


def energy_ids(pokemon_obj):
    return [card.id for card in pokemon_obj.energyCards]


def test_active_attach_reachable_attack_p0_statusless_win():
    active_ko_board, active_attach, _bench_attach = p0_froslass_attach_board(turn=2, first_player=1, your_index=0)

    outcome = main.ImmediateOutcomeEvaluator(active_ko_board).evaluate_attach(active_attach)
    assert outcome.enables_attack
    assert main.RESENTFUL_REFRAIN in outcome.enabled_attack_ids
    assert not outcome.enables_knockout
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 950
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert outcome.reachable_wins_game
    assert not outcome.knockout
    assert outcome.prizes_taken == 0
    assert not outcome.wins_game

    ranked = main.GameSimulator(active_ko_board).rank_options()
    assert ranked[0].option is active_attach
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_active_attach_reachable_attack_p0_asleep_blocks_reachable():
    board, active_attach, _bench_attach = p0_froslass_attach_board("asleep")

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(active_attach)
    assert outcome.enables_attack
    assert main.RESENTFUL_REFRAIN in outcome.enabled_attack_ids
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert not outcome.reachable_wins_game
    assert action_score_for_option(board, active_attach).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_active_attach_reachable_attack_p0_paralyzed_blocks_reachable():
    board, active_attach, _bench_attach = p0_froslass_attach_board("paralyzed")

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(active_attach)
    assert outcome.enables_attack
    assert main.RESENTFUL_REFRAIN in outcome.enabled_attack_ids
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert not outcome.reachable_wins_game
    assert action_score_for_option(board, active_attach).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_active_attach_reachable_attack_p0_first_player_turn_one_blocks_reachable():
    board, active_attach, _bench_attach = p0_froslass_attach_board(turn=1, first_player=0, your_index=0)

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(active_attach)
    assert outcome.enables_attack
    assert main.RESENTFUL_REFRAIN in outcome.enabled_attack_ids
    assert outcome.reachable_attack_id is None
    assert outcome.reachable_damage == 0
    assert outcome.reachable_prizes_taken == 0
    assert not outcome.reachable_knockout
    assert not outcome.reachable_wins_game
    assert action_score_for_option(board, active_attach).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_active_attach_reachable_attack_p0_second_player_first_turn_reachable():
    board, active_attach, _bench_attach = p0_froslass_attach_board(turn=2, first_player=1, your_index=0)

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(active_attach)
    assert outcome.enables_attack
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_knockout
    assert outcome.reachable_wins_game
    assert action_score_for_option(board, active_attach).tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_active_attach_reachable_attack_p0_first_player_later_turn_reachable():
    board, active_attach, _bench_attach = p0_froslass_attach_board(turn=3, first_player=0, your_index=0)

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(active_attach)
    assert outcome.enables_attack
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_knockout
    assert outcome.reachable_wins_game
    assert action_score_for_option(board, active_attach).tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_active_attach_reachable_attack_p0_already_legal_guard():
    water = main.BASIC_WATER_ENERGY

    direct_attack = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    already_ready_board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[water],
        target_hp=140,
        prizes_left=1,
        turn=2,
        first_player=1,
        your_index=0,
    )
    already_ready_board.opp.handCount = 19
    redundant_attach = attach_option(water, already_ready_board.active)
    already_ready_board._options = [redundant_attach, direct_attack]
    redundant_outcome = main.ImmediateOutcomeEvaluator(already_ready_board).evaluate_attach(redundant_attach)
    assert not redundant_outcome.enabled_attack_ids
    assert not redundant_outcome.reachable_knockout
    ranked = main.GameSimulator(already_ready_board).rank_options()
    assert ranked[0].option is direct_attack
    assert ranked[0].action_score.tier == main.TIER_WIN


def test_active_attack_declare_turn_rule_call_sites_p0():
    water = main.BASIC_WATER_ENERGY

    first_turn = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[water],
        target_hp=140,
        prizes_left=1,
        turn=1,
        first_player=0,
        your_index=0,
    )
    first_turn.opp.handCount = 19
    assert not main.ImmediateOutcomeEvaluator(first_turn).has_energy_payable_unblocked_active_attack()

    second_player_first_turn = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[water],
        target_hp=140,
        prizes_left=1,
        turn=2,
        first_player=1,
        your_index=0,
    )
    second_player_first_turn.opp.handCount = 19
    assert main.ImmediateOutcomeEvaluator(second_player_first_turn).has_energy_payable_unblocked_active_attack()

    later_turn = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[water],
        target_hp=140,
        prizes_left=1,
        turn=3,
        first_player=0,
        your_index=0,
    )
    later_turn.opp.handCount = 19
    assert main.ImmediateOutcomeEvaluator(later_turn).has_energy_payable_unblocked_active_attack()


def test_active_attack_declare_turn_rule_policy_regressions_p0():
    water = main.BASIC_WATER_ENERGY

    staryu = pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=601)
    evolve_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[staryu],
        target_hp=300,
        turn=2,
        first_player=1,
        your_index=0,
    )
    evolve = evolve_option(main.MEGA_STARMIE_EX, staryu)
    non_ko_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    redundant_attach = attach_option(water, evolve_board.active)
    evolve_policy = policy_for(evolve_board)
    assert evolve_policy.score_evolve(evolve) > evolve_policy.score_attack(non_ko_attack)
    assert evolve_policy.score_evolve(evolve) > evolve_policy.score_attach(redundant_attach)

    class StablePokegearBoard(FakeBoard):
        def starmie_needs_energy(self):
            return False

        def needs_mega_starmie(self):
            return False

        def needs_mega_yuki(self):
            return False

    pokegear_board = StablePokegearBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[water],
        bench=[pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=602)],
        target_hp=300,
        salvatore_live=True,
        turn=2,
        first_player=1,
        your_index=0,
    )
    pokegear_board._hand_ids = [main.POKEGEAR, main.YVELTAL, main.SHAYMIN, main.BASIC_DARK_ENERGY]
    pokegear_policy = policy_for(pokegear_board)
    assert pokegear_policy.score_pokegear_candidate(main.SALVATORE) == 160000
    assert pokegear_policy.score_pokegear_candidate(main.LILLIE_DETERMINATION) == 1000


def test_active_attach_reachable_attack_p0_blocked_guard():
    water = main.BASIC_WATER_ENERGY

    blocked_board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        target_id=330,
        target_hp=40,
        prizes_left=1,
    )
    blocked_board.opp.handCount = 20
    blocked_attach = attach_option(water, blocked_board.active)
    blocked_outcome = main.ImmediateOutcomeEvaluator(blocked_board).evaluate_attach(blocked_attach)
    assert blocked_outcome.enables_attack
    assert not blocked_outcome.enables_knockout
    assert not blocked_outcome.reachable_knockout
    assert not blocked_outcome.reachable_wins_game


def test_active_attach_reachable_attack_p0_bench_guard():
    water = main.BASIC_WATER_ENERGY

    bench_only = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=502)
    bench_board = FakeBoard(
        active_id=main.CINDERACE,
        active_energies=[water],
        bench=[bench_only],
        target_hp=40,
        prizes_left=1,
    )
    bench_board.opp.handCount = 20
    bench_outcome = main.ImmediateOutcomeEvaluator(bench_board).evaluate_attach(attach_option(water, bench_only))
    assert bench_outcome.enables_attack
    assert not bench_outcome.enables_knockout
    assert not bench_outcome.reachable_knockout


def test_active_attach_reachable_attack_p0_multiple_attack_best_choice():
    water = main.BASIC_WATER_ENERGY

    custom_attack_a = 920001
    custom_attack_b = 920002
    multi_board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        target_hp=100,
        prizes_left=2,
        attacks={
            custom_attack_a: attack(custom_attack_a, 80, [main.EnergyType.WATER]),
            custom_attack_b: attack(custom_attack_b, 120, [main.EnergyType.WATER]),
        },
    )
    multi_board._data[main.MEGA_YUKIMENOKO_EX].attacks = [custom_attack_a, custom_attack_b]
    multi_outcome = main.ImmediateOutcomeEvaluator(multi_board).evaluate_attach(attach_option(water, multi_board.active))
    assert set(multi_outcome.enabled_attack_ids) == {custom_attack_a, custom_attack_b}
    assert multi_outcome.reachable_attack_id == custom_attack_b
    assert multi_outcome.reachable_damage == 120
    assert multi_outcome.reachable_knockout


def test_active_attach_reachable_attack_p0_other_card_guard():
    dark = main.BASIC_DARK_ENERGY

    starmie_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[dark, dark],
        target_hp=180,
        prizes_left=1,
    )
    starmie_outcome = main.ImmediateOutcomeEvaluator(starmie_board).evaluate_attach(attach_option(dark, starmie_board.active))
    assert main.NEBULA_BEAM in starmie_outcome.enabled_attack_ids
    assert starmie_outcome.reachable_attack_id == main.NEBULA_BEAM
    assert starmie_outcome.reachable_wins_game


def p1_bench_attach_surfing_board(
    include_access=True,
    target_id=999,
    target_hp=180,
    prizes_left=3,
    bench_id=main.MEGA_STARMIE_EX,
    bench_energies=None,
):
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    if bench_energies is None:
        bench_energies = [dark, dark]
    bench = pokemon(bench_id, hp=280, max_hp=280, serial=701, energies=bench_energies)
    zero_attack = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    bench_attach = attach_option(water, bench)
    options = [zero_attack, bench_attach, option(main.OptionType.END)]
    if include_access:
        options.insert(2, play_option(main.SURFING_BEACH))
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[water],
        bench=[bench],
        target_id=target_id,
        target_hp=target_hp,
        prizes_left=prizes_left,
        options=options,
        effect_id=None,
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.opp.handCount = 0
    return board, bench_attach, zero_attack, bench


def test_bench_attach_same_turn_access_p1_surfing_beach_ko():
    board, bench_attach, zero_attack, bench = p1_bench_attach_surfing_board()
    before_energies = [card.id for card in bench.energyCards]

    ranked = main.GameSimulator(board).rank_options()
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach)

    assert outcome.enables_attack
    assert main.NEBULA_BEAM in outcome.enabled_attack_ids
    assert outcome.reachable_attack_id == main.NEBULA_BEAM
    assert outcome.reachable_damage == 180
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert not outcome.reachable_wins_game
    assert "attach_access_via_surfing_beach" in outcome.reasons
    assert not outcome.knockout
    assert ranked[0].option is bench_attach
    assert ranked[0].option is not zero_attack
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert [card.id for card in bench.energyCards] == before_energies


def test_bench_attach_same_turn_access_p1_surfing_beach_win():
    board, bench_attach, _zero_attack, _bench = p1_bench_attach_surfing_board(prizes_left=1)

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.reachable_knockout
    assert outcome.reachable_wins_game
    assert ranked[0].option is bench_attach
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_bench_attach_same_turn_access_p1_missing_access_guard():
    board, bench_attach, zero_attack, _bench = p1_bench_attach_surfing_board(include_access=False)

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.enables_attack
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert ranked[0].option is zero_attack
    assert action_score_for_option(board, bench_attach).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_bench_attach_same_turn_access_p1_blocked_guard():
    board, bench_attach, zero_attack, _bench = p1_bench_attach_surfing_board(
        target_id=330,
        target_hp=40,
        bench_id=main.MEGA_YUKIMENOKO_EX,
        bench_energies=[],
    )

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach)

    assert outcome.enables_attack
    assert main.RESENTFUL_REFRAIN in outcome.enabled_attack_ids
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert action_score_for_option(board, bench_attach).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_bench_attach_same_turn_access_p1_direct_ko_guard():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    bench = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=702, energies=[dark, dark])
    direct_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    bench_attach = attach_option(water, bench)
    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[bench],
        target_hp=50,
        prizes_left=3,
        options=[direct_attack, bench_attach, play_option(main.SURFING_BEACH)],
        effect_id=None,
        turn=3,
        first_player=0,
        your_index=0,
    )

    ranked = main.GameSimulator(board).rank_options()

    assert main.ImmediateOutcomeEvaluator(board).evaluate_attack(direct_attack).knockout
    assert main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach).reachable_knockout
    assert ranked[0].option is direct_attack
    assert ranked[0].action_score.tier == main.TIER_KO


def test_retreat_ready_attacker_same_turn_access_p1():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ready = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=703, energies=[water, dark, dark])
    retreat = option(main.OptionType.RETREAT)
    weak_attack = option(main.OptionType.ATTACK, 997)
    board = FakeBoard(
        active_id=main.YVELTAL,
        active_energies=[dark],
        bench=[ready],
        target_hp=180,
        prizes_left=3,
        options=[weak_attack, retreat, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.reachable_attack_id == main.NEBULA_BEAM
    assert outcome.reachable_damage == 180
    assert outcome.reachable_knockout
    assert outcome.retreat_energy_cost == 0
    assert ranked[0].option is retreat
    assert ranked[0].option is not weak_attack
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_rework_bench_attach_access_does_not_inherit_other_bench_ko():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    bench_a = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=720, energies=[])
    bench_b = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=721, energies=[water])
    attach_a = attach_option(water, bench_a)
    retreat = option(main.OptionType.RETREAT)
    board = FakeBoard(
        active_id=main.YVELTAL,
        active_energies=[],
        bench=[bench_a, bench_b],
        target_hp=150,
        prizes_left=3,
        options=[attach_a, retreat, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.opp.handCount = 4

    attach_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_a)
    retreat_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    ranked = main.GameSimulator(board).rank_options()

    assert attach_outcome.enables_attack
    assert attach_outcome.reachable_attack_id == main.CHILLY
    assert attach_outcome.reachable_damage == 30
    assert not attach_outcome.reachable_knockout
    assert action_score_for_option(board, attach_a).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert retreat_outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert retreat_outcome.reachable_knockout
    assert ranked[0].option is retreat
    assert ranked[0].option is not attach_a


def test_rework_active_attach_first_retreat_access_still_reaches_ready_bench_ko():
    water = main.BASIC_WATER_ENERGY
    ready = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=722, energies=[water])
    attach_to_active = attach_option(water, None)
    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[ready],
        target_hp=150,
        prizes_left=3,
        options=[attach_to_active, option(main.OptionType.ATTACK, main.JETTING_BLOW), option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board._data[main.MEGA_STARMIE_EX].retreatCost = 2
    attach_to_active.target = board.active
    board.opp.handCount = 4

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_to_active)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_knockout
    assert "attach_access_via_retreat" in outcome.reasons
    assert ranked[0].option is attach_to_active


def rework_attach_boss_board(turn=3, first_player=0, your_index=0, status=None, supporter_played=False, include_boss=True):
    water = main.BASIC_WATER_ENERGY
    boss_target = pokemon(999, hp=40, max_hp=100, serial=730)
    active_attach = attach_option(water, None)
    options = [active_attach, option(main.OptionType.END)]
    if include_boss:
        options.insert(1, play_option(main.BEFEHL_VON_BOSS))
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        target_hp=999,
        prizes_left=3,
        opp_bench=[boss_target],
        options=options,
        turn=turn,
        first_player=first_player,
        your_index=your_index,
    )
    active_attach.target = board.active
    board.opp.handCount = 4
    board._hand_ids = [main.BEFEHL_VON_BOSS, water] if include_boss else [water]
    board.state.supporterPlayed = supporter_played
    if status == "asleep":
        board.me = SimpleNamespace(asleep=True, paralyzed=False)
    elif status == "paralyzed":
        board.me = SimpleNamespace(asleep=False, paralyzed=True)
    else:
        board.me = SimpleNamespace(asleep=False, paralyzed=False)
    return board, active_attach


def test_rework_attach_boss_attack_declare_guard():
    legal_board, legal_attach = rework_attach_boss_board(turn=3, first_player=0, your_index=0)
    first_turn_board, first_turn_attach = rework_attach_boss_board(turn=1, first_player=0, your_index=0)
    asleep_board, asleep_attach = rework_attach_boss_board(status="asleep")
    paralyzed_board, paralyzed_attach = rework_attach_boss_board(status="paralyzed")

    legal_outcome = main.ImmediateOutcomeEvaluator(legal_board).evaluate_attach(legal_attach)
    first_turn_outcome = main.ImmediateOutcomeEvaluator(first_turn_board).evaluate_attach(first_turn_attach)
    asleep_outcome = main.ImmediateOutcomeEvaluator(asleep_board).evaluate_attach(asleep_attach)
    paralyzed_outcome = main.ImmediateOutcomeEvaluator(paralyzed_board).evaluate_attach(paralyzed_attach)

    assert legal_outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert legal_outcome.reachable_knockout
    assert "attach_access_via_boss" in legal_outcome.reasons
    for outcome in (first_turn_outcome, asleep_outcome, paralyzed_outcome):
        assert outcome.enables_attack
        assert outcome.reachable_attack_id is None
        assert not outcome.reachable_knockout
        assert not outcome.reachable_wins_game


def test_rework_attach_boss_existing_availability_guards():
    no_boss_board, no_boss_attach = rework_attach_boss_board(include_boss=False)
    supporter_board, supporter_attach = rework_attach_boss_board(supporter_played=True)

    no_boss_outcome = main.ImmediateOutcomeEvaluator(no_boss_board).evaluate_attach(no_boss_attach)
    supporter_outcome = main.ImmediateOutcomeEvaluator(supporter_board).evaluate_attach(supporter_attach)

    assert no_boss_outcome.enables_attack
    assert no_boss_outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert not no_boss_outcome.reachable_knockout
    assert "attach_access_via_boss" not in no_boss_outcome.reasons
    assert supporter_outcome.enables_attack
    assert supporter_outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert not supporter_outcome.reachable_knockout
    assert "attach_access_via_boss" not in supporter_outcome.reasons


def test_rework_status_blocks_normal_retreat_access():
    water = main.BASIC_WATER_ENERGY
    ready = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=740, energies=[water, main.BASIC_DARK_ENERGY, main.BASIC_DARK_ENERGY])
    retreat = option(main.OptionType.RETREAT)
    board = FakeBoard(
        active_id=main.YVELTAL,
        active_energies=[],
        bench=[ready],
        target_hp=180,
        prizes_left=3,
        options=[retreat, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )

    board.me = SimpleNamespace(asleep=True, paralyzed=False)
    asleep_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert asleep_outcome.reachable_attack_id is None
    assert not asleep_outcome.reachable_knockout

    board.me = SimpleNamespace(asleep=False, paralyzed=True)
    paralyzed_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_retreat(retreat)
    assert paralyzed_outcome.reachable_attack_id is None
    assert not paralyzed_outcome.reachable_knockout


def test_rework_surfing_beach_status_allows_legal_switch_target_attack():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ready = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=741, energies=[water, dark, dark])
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[ready],
        target_hp=180,
        prizes_left=3,
        options=[play_option(main.SURFING_BEACH), option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.me = SimpleNamespace(asleep=True, paralyzed=False)

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(ready, "surfing_beach")

    assert outcome.reachable_attack_id == main.NEBULA_BEAM
    assert outcome.reachable_knockout
    assert outcome.retreat_energy_cost == 0


def test_rework_attach_surfing_status_requires_surfing_option():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    with_access_board, with_access_attach, _zero_attack, _bench = p1_bench_attach_surfing_board()
    with_access_board.me = SimpleNamespace(asleep=True, paralyzed=False)

    without_access_board, without_access_attach, _zero_attack, _bench = p1_bench_attach_surfing_board(include_access=False)
    without_access_board.me = SimpleNamespace(asleep=True, paralyzed=False)

    with_access_outcome = main.ImmediateOutcomeEvaluator(with_access_board).evaluate_attach(with_access_attach)
    without_access_outcome = main.ImmediateOutcomeEvaluator(without_access_board).evaluate_attach(without_access_attach)

    assert with_access_outcome.reachable_attack_id == main.NEBULA_BEAM
    assert with_access_outcome.reachable_knockout
    assert "attach_access_via_surfing_beach" in with_access_outcome.reasons
    assert without_access_outcome.enables_attack
    assert without_access_outcome.reachable_attack_id is None
    assert not without_access_outcome.reachable_knockout


def test_l1_paid_retreat_energy_ledger_allows_reachable_after_attach():
    water = main.BASIC_WATER_ENERGY
    ready = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=801, energies=[water])
    attach_to_active = attach_option(water, None)
    bench = [ready]
    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=bench,
        target_hp=150,
        prizes_left=3,
        options=[attach_to_active, option(main.OptionType.ATTACK, main.JETTING_BLOW), option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board._data[main.MEGA_STARMIE_EX].retreatCost = 2
    attach_to_active.target = board.active
    before_active_energy = [card.id for card in board.active.energyCards]
    before_bench_energy = [card.id for card in ready.energyCards]

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_to_active)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 200
    assert outcome.reachable_knockout
    assert outcome.retreat_energy_cost == 2
    assert outcome.important_energy_loss == 2
    assert "attach_access_via_retreat" in outcome.reasons
    assert ranked[0].option is attach_to_active
    assert [card.id for card in board.active.energyCards] == before_active_energy
    assert [card.id for card in ready.energyCards] == before_bench_energy


def test_l1_paid_retreat_energy_ledger_blocks_unpayable_retreat_chain():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ready = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=802, energies=[dark, dark])
    attach_to_bench = attach_option(water, ready)
    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[ready],
        target_hp=150,
        prizes_left=3,
        options=[attach_to_bench, option(main.OptionType.RETREAT), option(main.OptionType.ATTACK, main.JETTING_BLOW), option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board._data[main.MEGA_STARMIE_EX].retreatCost = 2

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach_to_bench)

    assert outcome.enables_attack
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert action_score_for_option(board, attach_to_bench).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_l1_free_retreat_and_surfing_beach_have_no_energy_loss():
    board, bench_attach, _zero_attack, _bench = p1_bench_attach_surfing_board()

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach)

    assert outcome.reachable_knockout
    assert outcome.retreat_energy_cost == 0
    assert outcome.important_energy_loss == 0


def test_l1_energy_switch_moves_energy_to_active_without_board_mutation():
    water = main.BASIC_WATER_ENERGY
    source = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=803, energies=[water])
    energy_switch = play_option(main.ENERGY_SWITCH)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[source],
        target_hp=150,
        prizes_left=3,
        options=[energy_switch, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.opp.handCount = 4
    before_active_energy = [card.id for card in board.active.energyCards]
    before_source_energy = [card.id for card in source.energyCards]

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_energy_switch_play(energy_switch)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.enables_attack
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 200
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert ranked[0].option is energy_switch
    assert [card.id for card in board.active.energyCards] == before_active_energy
    assert [card.id for card in source.energyCards] == before_source_energy


def test_l1_energy_switch_no_source_energy_no_promotion():
    energy_switch = play_option(main.ENERGY_SWITCH)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=804, energies=[])],
        target_hp=150,
        prizes_left=3,
        options=[energy_switch, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.opp.handCount = 4

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_energy_switch_play(energy_switch)

    assert outcome.supported
    assert outcome.reachable_attack_id is None
    assert not outcome.reachable_knockout
    assert action_score_for_option(board, energy_switch).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_energy_switch_redundant_attach_route_loses_to_direct_bench_attach():
    water = main.BASIC_WATER_ENERGY
    bench_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=805, energies=[])
    active_attach = attach_option(water, None)
    bench_attach = attach_option(water, bench_snorunt)
    board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[],
        bench=[bench_snorunt],
        options=[active_attach, bench_attach, option(main.OptionType.END)],
        turn=1,
        first_player=0,
        your_index=0,
    )
    active_attach.target = board.active

    active_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(active_attach)
    bench_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(bench_attach)
    ranked = main.GameSimulator(board).rank_options()

    assert active_outcome.enables_attack
    assert bench_outcome.enables_attack
    assert active_outcome.enabled_attack_ids == bench_outcome.enabled_attack_ids
    assert policy_for(board).score(0, active_attach) == policy_for(board).score(1, bench_attach)

    energy_switch = play_option(main.ENERGY_SWITCH)
    after_active_attach = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water],
        bench=[pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=806, energies=[])],
        options=[energy_switch, option(main.OptionType.END)],
        turn=1,
        first_player=0,
        your_index=0,
    )
    after_active_attach.logs = [
        SimpleNamespace(type=main.LogType.ATTACH, playerIndex=0, cardId=water, serial=1, serialTarget=10)
    ]

    switch_outcome = main.ImmediateOutcomeEvaluator(after_active_attach).evaluate_energy_switch_play(energy_switch)
    switch_ranked = main.GameSimulator(after_active_attach).rank_options()

    assert switch_outcome.additional_card_consumed
    assert switch_outcome.equivalent_normal_attach_available
    assert switch_outcome.reachable_attack_id is None
    assert not switch_outcome.reachable_knockout
    assert policy_for(after_active_attach).score(0, energy_switch) < policy_for(after_active_attach).score(1, after_active_attach._options[1])
    assert switch_ranked[0].option is after_active_attach._options[1]


def test_energy_switch_redundant_attach_route_generalizes_beyond_snorunt():
    water = main.BASIC_WATER_ENERGY
    energy_switch = play_option(main.ENERGY_SWITCH)
    end = option(main.OptionType.END)

    staryu_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[water],
        bench=[pokemon(main.HITODEMAN, hp=60, max_hp=60, serial=808, energies=[])],
        options=[energy_switch, end],
        turn=1,
        first_player=0,
        your_index=0,
    )
    staryu_board.logs = [
        SimpleNamespace(type=main.LogType.ATTACH, playerIndex=0, cardId=water, serial=1, serialTarget=10)
    ]
    staryu_outcome = main.ImmediateOutcomeEvaluator(staryu_board).evaluate_energy_switch_play(energy_switch)
    staryu_ranked = main.GameSimulator(staryu_board).rank_options()
    assert staryu_outcome.additional_card_consumed
    assert staryu_outcome.equivalent_normal_attach_available
    assert staryu_outcome.reachable_attack_id is None
    assert staryu_ranked[0].option is end

    mixed_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[water],
        bench=[pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=809, energies=[])],
        options=[energy_switch, end],
        turn=1,
        first_player=0,
        your_index=0,
    )
    mixed_board.logs = [
        SimpleNamespace(type=main.LogType.ATTACH, playerIndex=0, cardId=water, serial=1, serialTarget=10)
    ]
    mixed_outcome = main.ImmediateOutcomeEvaluator(mixed_board).evaluate_energy_switch_play(energy_switch)
    mixed_ranked = main.GameSimulator(mixed_board).rank_options()
    assert mixed_outcome.additional_card_consumed
    assert mixed_outcome.equivalent_normal_attach_available
    assert mixed_outcome.reachable_attack_id is None
    assert mixed_ranked[0].option is end

    old_energy_board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water],
        bench=[pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=810, energies=[])],
        options=[energy_switch, end],
        turn=3,
        first_player=0,
        your_index=0,
    )
    old_energy_outcome = main.ImmediateOutcomeEvaluator(old_energy_board).evaluate_energy_switch_play(energy_switch)
    old_energy_ranked = main.GameSimulator(old_energy_board).rank_options()
    assert old_energy_outcome.additional_card_consumed
    assert not old_energy_outcome.equivalent_normal_attach_available
    assert old_energy_outcome.reachable_attack_id is None
    assert old_energy_ranked[0].option is energy_switch


def test_energy_switch_only_win_is_not_suppressed():
    water = main.BASIC_WATER_ENERGY
    source = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=807, energies=[water])
    energy_switch = play_option(main.ENERGY_SWITCH)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[source],
        target_hp=150,
        prizes_left=1,
        options=[energy_switch, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.opp.handCount = 4

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_energy_switch_play(energy_switch)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.additional_card_consumed
    assert not outcome.equivalent_normal_attach_available
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert outcome.reachable_wins_game
    assert ranked[0].option is energy_switch


def test_issue8_starmie_demand_without_same_turn_gain_is_not_real_development():
    water = main.BASIC_WATER_ENERGY
    energy_switch = play_option(main.ENERGY_SWITCH)
    direct_attack = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    end = option(main.OptionType.END)

    for target_hp, prizes_left in ((500, 3), (150, 3), (150, 1)):
        source = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=811, energies=[water])
        board = FakeBoard(
            active_id=main.MEGA_YUKIMENOKO_EX,
            active_energies=[water],
            bench=[source],
            target_hp=target_hp,
            prizes_left=prizes_left,
            options=[energy_switch, direct_attack, end],
            turn=3,
            first_player=0,
            your_index=0,
        )
        board.opp.handCount = 4

        outcome = main.ImmediateOutcomeEvaluator(board).evaluate_energy_switch_play(energy_switch)
        action_score = action_score_for_option(board, energy_switch)
        ranked = main.GameSimulator(board).rank_options()

        assert board.starmie_needs_energy()
        assert outcome.additional_card_consumed
        assert outcome.reachable_attack_id is None
        assert not outcome.reachable_knockout
        assert outcome.reachable_prizes_taken == 0
        assert not outcome.reachable_wins_game
        assert "energy_switch_no_reachable_attack" in outcome.reasons
        assert action_score.tier == main.TIER_LOW_VALUE_ACTION
        assert action_score.development == 0
        assert action_score.resource < 36000
        assert ranked[0].option is direct_attack
        assert next(
            index for index, result in enumerate(ranked) if result.option is direct_attack
        ) < next(
            index for index, result in enumerate(ranked) if result.option is energy_switch
        )


def test_issue8_energy_switch_newly_unlocked_attack_keeps_value():
    water = main.BASIC_WATER_ENERGY
    source = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=812, energies=[water])
    energy_switch = play_option(main.ENERGY_SWITCH)
    end = option(main.OptionType.END)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[source],
        target_hp=500,
        prizes_left=3,
        options=[energy_switch, end],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board.opp.handCount = 4

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_energy_switch_play(energy_switch)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.additional_card_consumed
    assert outcome.enables_attack
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage > 0
    assert not outcome.reachable_knockout
    assert ranked[0].option is energy_switch


def test_l4_attach_boss_prize_attack_reachable():
    water = main.BASIC_WATER_ENERGY
    boss = play_option(main.BEFEHL_VON_BOSS)
    attach = attach_option(water, None)
    direct_attack = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    boss_target = pokemon(999, hp=150, max_hp=150, serial=901)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        opp_bench=[boss_target],
        target_hp=300,
        prizes_left=3,
        options=[attach, boss, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    attach.target = board.active
    board.opp.handCount = 4
    board._hand_ids = [main.BEFEHL_VON_BOSS, water]

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 200
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert "attach_access_via_boss" in outcome.reasons
    assert ranked[0].option is attach
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_l4_attach_boss_requires_boss_available_and_unused_supporter():
    water = main.BASIC_WATER_ENERGY
    attach = attach_option(water, None)
    boss_target = pokemon(999, hp=150, max_hp=150, serial=902)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        opp_bench=[boss_target],
        target_hp=300,
        prizes_left=3,
        options=[attach, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    attach.target = board.active
    board.opp.handCount = 4
    board._hand_ids = [water]

    no_boss = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach)
    assert no_boss.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert not no_boss.reachable_knockout
    assert "attach_access_via_boss" not in no_boss.reasons

    board._hand_ids = [main.BEFEHL_VON_BOSS, water]
    board._options = [attach, play_option(main.BEFEHL_VON_BOSS), option(main.OptionType.END)]
    board.state.supporterPlayed = True
    used_supporter = main.ImmediateOutcomeEvaluator(board).evaluate_attach(attach)
    assert used_supporter.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert not used_supporter.reachable_knockout
    assert "attach_access_via_boss" not in used_supporter.reasons
    assert action_score_for_option(board, attach).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_replay_87482904_t11_t13_energy_ledger():
    path = "参考ログ/v7.3/勝ちログ/87482904.json"
    for step, actual_target_serial, damage in ((70, 3, 450), (81, 4, 350)):
        board, next_action = replay_board(path, step)
        actual = board.select.option[next_action[0]]
        ranked = main.GameSimulator(board).rank_options()
        top = ranked[0]
        outcome = top.outcome
        target = board.option_target(top.option)
        froslass = next(pokemon_obj for pokemon_obj in board.bench if board.pid(pokemon_obj) == main.MEGA_YUKIMENOKO_EX)
        before_active_energy = energy_ids(board.active)
        before_froslass_energy = energy_ids(froslass)

        assert option_description(board, actual) == ("ATTACH", main.BASIC_WATER_ENERGY, main.HITODEMAN, actual_target_serial)
        assert top.option.type == main.OptionType.ATTACH
        assert board.option_card(top.option) == main.BASIC_WATER_ENERGY
        assert target is froslass
        assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
        assert outcome.reachable_damage == damage
        assert outcome.reachable_knockout
        assert outcome.reachable_prizes_taken == 3
        assert outcome.reachable_wins_game
        assert outcome.retreat_energy_cost == 0
        assert outcome.important_energy_loss == 0
        assert "attach_access_via_retreat" in outcome.reasons
        assert energy_ids(board.active) == before_active_energy
        assert energy_ids(froslass) == before_froslass_energy


def test_replay_87482904_t15_energy_ledger():
    board, next_action = replay_board("参考ログ/v7.3/勝ちログ/87482904.json", 92)
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]
    target = board.option_target(top.option)
    before_active_energy = energy_ids(board.active)
    before_target_energy = energy_ids(target)

    assert option_description(board, board.select.option[next_action[0]]) == (
        "ATTACH",
        main.BASIC_WATER_ENERGY,
        main.MEGA_YUKIMENOKO_EX,
        12,
    )
    assert top.option is board.select.option[next_action[0]]
    assert top.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert top.outcome.reachable_damage == 350
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 3
    assert top.outcome.reachable_wins_game
    assert top.outcome.retreat_energy_cost == 0
    assert top.outcome.important_energy_loss == 0
    assert energy_ids(board.active) == before_active_energy
    assert energy_ids(target) == before_target_energy


def test_replay_87491060_t9_retreat_ready_attacker_energy_ledger():
    board, next_action = replay_board("参考ログ/v7.3/勝ちログ/87491060.json", 78)
    actual = board.select.option[next_action[0]]
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]
    ready_froslass = next(
        pokemon_obj
        for pokemon_obj in board.bench
        if board.pid(pokemon_obj) == main.MEGA_YUKIMENOKO_EX and energy_ids(pokemon_obj) == [main.BASIC_WATER_ENERGY]
    )
    before_active_energy = energy_ids(board.active)
    before_ready_energy = energy_ids(ready_froslass)

    assert option_description(board, actual) == ("ATTACK", 997, None, None)
    assert top.option.type == main.OptionType.RETREAT
    assert top.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert top.outcome.reachable_damage == 600
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 1
    assert top.outcome.retreat_energy_cost == 0
    assert top.outcome.important_energy_loss == 0
    assert energy_ids(board.active) == before_active_energy
    assert energy_ids(ready_froslass) == before_ready_energy


def test_replay_87488357_t19_energy_switch_ledger():
    board, next_action = replay_board("参考ログ/v7.3/負けログ/87488357.json", 127)
    actual = board.select.option[next_action[0]]
    source = board.bench[0]
    before_active_energy = energy_ids(board.active)
    before_source_energy = energy_ids(source)

    assert option_description(board, actual) == ("PLAY", main.ENERGY_SWITCH, None, None)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_energy_switch_play(actual)
    ranked = main.GameSimulator(board).rank_options()

    assert ranked[0].option is actual
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 350
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert not outcome.reachable_wins_game
    assert energy_ids(board.active) == before_active_energy
    assert energy_ids(source) == before_source_energy


def test_replay_87482904_t11_t13_l2_attach_retreat_attack_rank():
    path = "参考ログ/v7.3/勝ちログ/87482904.json"
    for step in (70, 81):
        board, next_action = replay_board(path, step)
        actual = board.select.option[next_action[0]]
        ranked = main.GameSimulator(board).rank_options()
        top = ranked[0]

        assert option_description(board, actual)[0] == "ATTACH"
        assert option_description(board, actual)[2] == main.HITODEMAN
        assert top.option.type == main.OptionType.ATTACH
        assert board.pid(board.option_target(top.option)) == main.MEGA_YUKIMENOKO_EX
        assert top.option is not actual
        assert top.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
        assert top.outcome.reachable_knockout
        assert top.outcome.reachable_prizes_taken == 3
        assert top.outcome.reachable_wins_game
        assert option_description(board, ranked[-1].option)[0] in {"END", "PLAY", "ATTACH", "RETREAT", "ATTACK"}


def test_replay_87482904_t15_l2_three_prize_rank():
    board, next_action = replay_board("参考ログ/v7.3/勝ちログ/87482904.json", 92)
    actual = board.select.option[next_action[0]]
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]

    assert top.option is actual
    assert board.pid(board.option_target(top.option)) == main.MEGA_YUKIMENOKO_EX
    assert top.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert top.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert top.outcome.reachable_damage == 350
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 3
    assert top.outcome.reachable_wins_game


def test_replay_87491060_t9_l3_retreat_ready_attacker_rank():
    board, next_action = replay_board("参考ログ/v7.3/勝ちログ/87491060.json", 78)
    actual = board.select.option[next_action[0]]
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]

    assert option_description(board, actual) == ("ATTACK", 997, None, None)
    assert top.option.type == main.OptionType.RETREAT
    assert top.option is not actual
    assert top.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert top.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert top.outcome.reachable_damage == 600
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 1


def test_replay_87637402_t13_l4_attach_boss_prize_rank():
    board, next_action = replay_board("参考ログ/v7.4/負け試合/87637402.json", 85)
    actual = board.select.option[next_action[0]]
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]

    assert option_description(board, actual) == ("ATTACH", main.BASIC_WATER_ENERGY, main.MEGA_STARMIE_EX, 6)
    assert top.option is actual
    assert top.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert top.outcome.reachable_attack_id == main.JETTING_BLOW
    assert top.outcome.reachable_damage == 120
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 1
    assert not top.outcome.reachable_wins_game
    assert "attach_access_via_boss" in top.outcome.reasons


def test_replay_87488357_t19_l5_energy_switch_prize_rank():
    board, next_action = replay_board("参考ログ/v7.3/負けログ/87488357.json", 127)
    actual = board.select.option[next_action[0]]
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]

    assert option_description(board, actual) == ("PLAY", main.ENERGY_SWITCH, None, None)
    assert top.option is actual
    assert top.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert top.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert top.outcome.reachable_damage == 350
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 1


def test_meaningless_retreat_supported_does_not_override_policy_legacy():
    cases = [
        ("参考ログ/v7.5/88275270.json", 9, 0, -6000, -100, 1),
        ("参考ログ/v7.5/88287673.json", 11, 0, -98000, -100, 0),
        ("参考ログ/v7.5/88290457.json", 14, 0, -98000, -100, 0),
    ]

    for replay_path, step, player_index, retreat_score, end_score, energy_loss in cases:
        board, _next_action = replay_board(replay_path, step, player_index)
        ranked = main.GameSimulator(board).rank_options()
        retreat_result = next(result for result in ranked if result.option.type == main.OptionType.RETREAT)
        end_result = next(result for result in ranked if result.option.type == main.OptionType.END)

        assert retreat_result.outcome.supported
        assert not end_result.outcome.supported
        assert retreat_result.policy_score == retreat_score
        assert end_result.policy_score == end_score
        assert retreat_result.policy_score < end_result.policy_score
        assert not retreat_result.outcome.reachable_attack_id
        assert not retreat_result.outcome.reachable_knockout
        assert not retreat_result.outcome.reachable_wins_game
        assert retreat_result.outcome.important_energy_loss == energy_loss
        assert ranked.index(end_result) < ranked.index(retreat_result)


def test_low_damage_utility_retreat_residual_depends_on_policy_score():
    board, _next_action = replay_board("参考ログ/v7.5/88283897.json", 133, 1)
    ranked = main.GameSimulator(board).rank_options()
    retreat_result = next(result for result in ranked if result.option.type == main.OptionType.RETREAT)
    end_result = next(result for result in ranked if result.option.type == main.OptionType.END)

    assert retreat_result.outcome.supported
    assert not end_result.outcome.supported
    assert retreat_result.policy_score == 224000
    assert end_result.policy_score == -100
    assert retreat_result.outcome.reachable_attack_id == 997
    assert retreat_result.outcome.reachable_damage == 20
    assert not retreat_result.outcome.reachable_knockout
    assert not retreat_result.outcome.reachable_wins_game
    if retreat_result.policy_score > end_result.policy_score:
        assert ranked.index(retreat_result) < ranked.index(end_result)


def test_ignition_retreat_ko_chain_remains_above_end():
    board, _next_action = replay_board("参考ログ/v7.5/88276357.json", 30, 0)
    ranked = main.GameSimulator(board).rank_options()
    top = ranked[0]
    target = board.option_target(top.option)

    assert board.pid(target) == main.MEGA_STARMIE_EX
    assert top.outcome.supported
    assert top.outcome.reachable_attack_id == main.JETTING_BLOW
    assert top.outcome.reachable_damage == 120
    assert top.outcome.reachable_knockout
    assert top.outcome.reachable_prizes_taken == 1
    assert top.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_non_retreat_outcome_priority_is_not_overridden_by_legacy():
    high_legacy_non_ko = option(main.OptionType.ATTACK, 1)
    low_legacy_win = option(main.OptionType.ATTACK, 2)
    board = FakeBoard(options=[high_legacy_non_ko, low_legacy_win])

    class StaticOutcome:
        def evaluate_attack(self, attack_option):
            if attack_option is high_legacy_non_ko:
                return main.ImmediateOutcome(supported=True, damage=10)
            return main.ImmediateOutcome(supported=True, damage=200, knockout=True, prizes_taken=1, wins_game=True)

    class SameTierPolicy(main.Policy):
        def __init__(self, policy_board):
            super().__init__(policy_board)
            self.outcome = StaticOutcome()

        def score(self, index, score_option):
            return 90000 if score_option is high_legacy_non_ko else 100

        def action_score(self, score_option, legacy_score, outcome):
            return main.ActionScore(main.TIER_LOW_VALUE_ACTION, legacy=legacy_score)

    ranked = main.GameSimulator(board, SameTierPolicy(board)).rank_options()
    non_ko_result = next(result for result in ranked if result.option is high_legacy_non_ko)
    win_result = next(result for result in ranked if result.option is low_legacy_win)

    assert non_ko_result.action_score.tier == win_result.action_score.tier
    assert non_ko_result.action_score.legacy > win_result.action_score.legacy
    assert win_result.outcome.wins_game
    assert win_result.outcome.knockout
    assert ranked[0].option is low_legacy_win


def best_active_attach_reachable_result(board, attack_id):
    ranked = main.GameSimulator(board).rank_options()
    candidates = [
        result
        for result in ranked
        if result.option.type == main.OptionType.ATTACH
        and board.option_target(result.option) is board.active
        and result.outcome.reachable_attack_id == attack_id
    ]
    assert candidates
    return max(candidates, key=lambda result: result.action_score.pressure)


def attack_result_by_id(board, attack_id):
    ranked = main.GameSimulator(board).rank_options()
    return next(result for result in ranked if getattr(result.option, "attackId", None) == attack_id)


def test_active_attach_reachable_pressure_replay_rank_rules():
    attach_wins = [
        ("参考ログ/v7.5/88275805.json", 67, 1),
        ("参考ログ/v7.5/88295393.json", 89, 1),
    ]
    attack_wins = [
        ("参考ログ/v7.5/88275805.json", 104, 1),
        ("参考ログ/v7.5/88285297.json", 73, 1),
    ]

    for replay_path, step, player_index in attach_wins:
        board, _next_action = replay_board(replay_path, step, player_index)
        ranked = main.GameSimulator(board).rank_options()
        policy = main.Policy(board)
        attack_result = attack_result_by_id(board, main.JETTING_BLOW)
        attach_result = best_active_attach_reachable_result(board, main.NEBULA_BEAM)
        attach_pressure = policy.reachable_attack_pressure_value(attach_result.outcome)

        assert attack_result.outcome.damage == 120
        assert not attack_result.outcome.knockout
        assert attach_result.outcome.reachable_damage == 210
        assert not attach_result.outcome.reachable_knockout
        assert attach_result.outcome.reachable_can_continue_attack
        assert attach_pressure == attach_result.action_score.pressure
        assert attach_pressure > attack_result.action_score.pressure
        assert attach_result.action_score.tier == main.TIER_NON_KO_ATTACK
        assert ranked.index(attach_result) < ranked.index(attack_result)

    for replay_path, step, player_index in attack_wins:
        board, _next_action = replay_board(replay_path, step, player_index)
        ranked = main.GameSimulator(board).rank_options()
        policy = main.Policy(board)
        attack_result = attack_result_by_id(board, main.JETTING_BLOW)
        attach_result = best_active_attach_reachable_result(board, main.NEBULA_BEAM)
        attach_pressure = policy.reachable_attack_pressure_value(attach_result.outcome)

        assert attack_result.outcome.damage == 120
        assert not attack_result.outcome.knockout
        assert attach_result.outcome.reachable_damage == 210
        assert not attach_result.outcome.reachable_knockout
        assert attach_result.outcome.reachable_can_continue_attack
        assert policy.bench_attack_pressure_value(board.attack(main.JETTING_BLOW)) > 0
        assert attach_pressure <= attack_result.action_score.pressure
        assert attach_result.action_score.tier != main.TIER_NON_KO_ATTACK
        assert ranked.index(attack_result) < ranked.index(attach_result)


def test_active_attach_reachable_pressure_direct_ko_and_win_guards():
    for replay_path, step in [
        ("参考ログ/v7.5/88283897.json", 65),
        ("参考ログ/v7.5/88283897.json", 82),
    ]:
        board, _next_action = replay_board(replay_path, step, 1)
        ranked = main.GameSimulator(board).rank_options()
        attack_result = attack_result_by_id(board, main.JETTING_BLOW)
        attach_result = best_active_attach_reachable_result(board, main.NEBULA_BEAM)

        assert attack_result.outcome.knockout
        assert attach_result.outcome.reachable_knockout
        assert attack_result.action_score.tier == main.TIER_KO
        assert ranked.index(attack_result) < ranked.index(attach_result)

    attack_option = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    attach = attach_option(main.BASIC_WATER_ENERGY, None)
    board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=40,
        prizes_left=1,
        options=[attack_option, attach],
        turn=3,
        first_player=0,
        your_index=0,
    )
    attach.target = board.active
    ranked = main.GameSimulator(board).rank_options()
    attack_result = attack_result_by_id(board, main.JETTING_BLOW)

    assert attack_result.outcome.wins_game
    assert ranked[0].option is attack_option


def test_active_attach_reachable_pressure_guards_and_froslass_hand_count():
    attack_option = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    bench_attach = attach_option(main.BASIC_WATER_ENERGY, None)
    no_improve_attach = attach_option(main.BASIC_WATER_ENERGY, None)
    blocked_attach = attach_option(main.BASIC_WATER_ENERGY, None)

    bench = pokemon(main.MEGA_STARMIE_EX, hp=330, max_hp=330, serial=31, energies=[main.BASIC_WATER_ENERGY])
    bench_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        bench=[bench],
        options=[attack_option, bench_attach],
        turn=3,
        first_player=0,
        your_index=0,
    )
    bench_attach.target = bench
    bench_attach_result = next(result for result in main.GameSimulator(bench_board).rank_options() if result.option is bench_attach)
    assert bench_attach_result.action_score.tier != main.TIER_NON_KO_ATTACK

    no_improve_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY],
        options=[attack_option, no_improve_attach],
        turn=3,
        first_player=0,
        your_index=0,
    )
    no_improve_attach.target = no_improve_board.active
    no_improve_result = next(result for result in main.GameSimulator(no_improve_board).rank_options() if result.option is no_improve_attach)
    assert no_improve_result.outcome.reachable_attack_id is None
    assert no_improve_result.action_score.tier != main.TIER_NON_KO_ATTACK

    blocked_board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        target_id=330,
        options=[blocked_attach],
        turn=3,
        first_player=0,
        your_index=0,
    )
    blocked_attach.target = blocked_board.active
    blocked_result = next(result for result in main.GameSimulator(blocked_board).rank_options() if result.option is blocked_attach)
    assert blocked_result.outcome.reachable_attack_id is None
    assert blocked_result.action_score.tier != main.TIER_NON_KO_ATTACK

    current_attack = option(main.OptionType.ATTACK, main.ABSOLUTE_SNOW)
    attach = attach_option(main.BASIC_WATER_ENERGY, None)
    froslass_low = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        target_hp=400,
        options=[current_attack, attach],
        turn=3,
        first_player=0,
        your_index=0,
    )
    froslass_low.opp.handCount = 2
    attach.target = froslass_low.active
    low_ranked = main.GameSimulator(froslass_low).rank_options()
    low_attack = attack_result_by_id(froslass_low, main.ABSOLUTE_SNOW)
    low_attach = best_active_attach_reachable_result(froslass_low, main.RESENTFUL_REFRAIN)
    assert low_attach.outcome.reachable_damage == 100
    assert low_attach.action_score.tier != main.TIER_NON_KO_ATTACK
    assert low_ranked.index(low_attack) < low_ranked.index(low_attach)

    high_attack = option(main.OptionType.ATTACK, main.ABSOLUTE_SNOW)
    high_attach = attach_option(main.BASIC_WATER_ENERGY, None)
    froslass_high = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        target_hp=400,
        options=[high_attack, high_attach],
        turn=3,
        first_player=0,
        your_index=0,
    )
    froslass_high.opp.handCount = 6
    high_attach.target = froslass_high.active
    high_ranked = main.GameSimulator(froslass_high).rank_options()
    high_attack_result = attack_result_by_id(froslass_high, main.ABSOLUTE_SNOW)
    high_attach_result = best_active_attach_reachable_result(froslass_high, main.RESENTFUL_REFRAIN)
    assert high_attach_result.outcome.reachable_damage == 300
    assert high_attach_result.action_score.pressure > high_attack_result.action_score.pressure
    assert high_attach_result.action_score.tier == main.TIER_NON_KO_ATTACK
    assert high_ranked.index(high_attach_result) < high_ranked.index(high_attack_result)

    current_attack_id = 900101
    discard_attack_id = 900102
    current_attack = option(main.OptionType.ATTACK, current_attack_id)
    no_continue_attach = attach_option(main.BASIC_WATER_ENERGY, None)
    pressure_attacks = {
        current_attack_id: SimpleNamespace(
            attackId=current_attack_id,
            name="Current Pressure",
            text="",
            damage=150,
            energies=[main.EnergyType.WATER, main.EnergyType.WATER],
        ),
        discard_attack_id: SimpleNamespace(
            attackId=discard_attack_id,
            name="Energy Spend",
            text="Discard an Energy from this Pokemon.",
            damage=160,
            energies=[main.EnergyType.WATER, main.EnergyType.WATER, main.EnergyType.WATER],
        ),
    }
    no_continue_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY],
        target_hp=300,
        options=[current_attack, no_continue_attach],
        attacks=pressure_attacks,
        turn=3,
        first_player=0,
        your_index=0,
    )
    no_continue_board._data[main.MEGA_STARMIE_EX].attacks = [current_attack_id, discard_attack_id]
    no_continue_attach.target = no_continue_board.active
    policy = main.Policy(no_continue_board)
    current_outcome = policy.outcome.evaluate_attack(current_attack)
    assert policy.best_current_non_ko_attack_pressure() == policy.attack_pressure_value(current_attack, current_outcome)
    mixed_non_attack = SimpleNamespace(type=main.OptionType.PLAY, cardId=main.POFIN)
    filter_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY],
        target_hp=300,
        options=[mixed_non_attack, current_attack],
        attacks=pressure_attacks,
        turn=3,
        first_player=0,
        your_index=0,
    )
    filter_board._data[main.MEGA_STARMIE_EX].attacks = [current_attack_id, discard_attack_id]
    filter_policy = main.Policy(filter_board)
    assert filter_policy.best_current_non_ko_attack_pressure() == filter_policy.attack_pressure_value(current_attack, filter_policy.outcome.evaluate_attack(current_attack))
    no_continue_result = next(
        result
        for result in main.GameSimulator(no_continue_board).rank_options()
        if result.option is no_continue_attach
    )
    assert no_continue_result.outcome.reachable_attack_id == discard_attack_id
    assert no_continue_result.outcome.reachable_damage == 160
    assert not no_continue_result.outcome.reachable_can_continue_attack
    assert policy.reachable_attack_pressure_value(no_continue_result.outcome) < policy.best_current_non_ko_attack_pressure()
    assert no_continue_result.action_score.tier != main.TIER_NON_KO_ATTACK

    continue_attack = option(main.OptionType.ATTACK, current_attack_id)
    continue_attach = attach_option(main.BASIC_WATER_ENERGY, None)
    continue_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY, main.BASIC_DARK_ENERGY],
        target_hp=300,
        options=[continue_attack, continue_attach],
        attacks=pressure_attacks,
        turn=3,
        first_player=0,
        your_index=0,
    )
    continue_board._data[main.MEGA_STARMIE_EX].attacks = [current_attack_id, discard_attack_id]
    continue_attach.target = continue_board.active
    continue_policy = main.Policy(continue_board)
    continue_result = next(
        result
        for result in main.GameSimulator(continue_board).rank_options()
        if result.option is continue_attach
    )
    assert continue_result.outcome.reachable_attack_id == discard_attack_id
    assert continue_result.outcome.reachable_damage == 160
    assert continue_result.outcome.reachable_can_continue_attack
    assert continue_policy.reachable_attack_pressure_value(continue_result.outcome) > continue_policy.best_current_non_ko_attack_pressure()
    assert continue_result.action_score.tier == main.TIER_NON_KO_ATTACK


def test_l6_zero_damage_attack_loses_to_confirmed_chain_but_is_not_forbidden():
    board, bench_attach, zero_attack, _bench = p1_bench_attach_surfing_board()
    ranked = main.GameSimulator(board).rank_options()
    zero_result = next(result for result in ranked if result.option is zero_attack)

    assert main.ImmediateOutcomeEvaluator(board).evaluate_attack(zero_attack).damage == 0
    assert ranked[0].option is bench_attach
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert zero_result.action_score.tier == main.TIER_NON_KO_ATTACK
    assert zero_result.outcome.supported
    assert not zero_result.outcome.knockout
    assert not zero_result.outcome.wins_game


def test_l7_rank_contract_direct_ko_before_reachable_chain():
    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    bench = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=910, energies=[dark, dark])
    direct_ko = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    chain_attach = attach_option(water, bench)
    end = option(main.OptionType.END)
    board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[bench],
        target_hp=50,
        prizes_left=3,
        options=[chain_attach, play_option(main.SURFING_BEACH), direct_ko, end],
        turn=3,
        first_player=0,
        your_index=0,
    )

    ranked = main.GameSimulator(board).rank_options()

    assert ranked[0].option is direct_ko
    assert ranked[0].action_score.tier == main.TIER_KO
    assert action_score_for_option(board, chain_attach).tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert ranked[-1].option is end


def test_l8_public_same_board_same_rank_and_common_guards():
    water = main.BASIC_WATER_ENERGY
    bench = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=920, energies=[])
    attach = attach_option(water, bench)
    zero_attack = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    end = option(main.OptionType.END)
    board_a = FakeBoard(
        active_id=main.YVELTAL,
        bench=[bench],
        target_hp=150,
        prizes_left=3,
        options=[attach, option(main.OptionType.RETREAT), zero_attack, end],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board_a.opp.handCount = 4
    board_b = FakeBoard(
        active_id=main.YVELTAL,
        bench=[pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=920, energies=[])],
        target_hp=150,
        prizes_left=3,
        options=[attach_option(water, None), option(main.OptionType.RETREAT), zero_attack, end],
        turn=3,
        first_player=0,
        your_index=0,
    )
    board_b._options[0].target = board_b.bench[0]
    board_b.opp.handCount = 4
    board_b.opp.hand = [energy_card(main.BASIC_WATER_ENERGY, 990), energy_card(main.BASIC_DARK_ENERGY, 991)]

    ranked_a = [result.action_score for result in main.GameSimulator(board_a).rank_options()]
    ranked_b = [result.action_score for result in main.GameSimulator(board_b).rank_options()]

    assert ranked_a == ranked_b
    assert main.ImmediateOutcomeEvaluator(board_a).evaluate_attach(attach).reachable_knockout
    assert main.ImmediateOutcomeEvaluator(board_a).evaluate_attack(zero_attack).damage == main.ImmediateOutcomeEvaluator(board_b).evaluate_attack(zero_attack).damage


def pokegear_salvatore_chain_board(options=None, deck_count=42, hand_ids=None, supporter_played=False, target_hp=290, target_id=678, deck_ids=None):
    chilly = option(main.OptionType.ATTACK, main.CHILLY)
    play_pokegear = play_option(main.POKEGEAR)
    play_salvatore = play_option(main.SALVATORE)
    end = option(main.OptionType.END)
    board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=(main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY, main.BASIC_WATER_ENERGY),
        target_id=target_id,
        target_hp=target_hp,
        prizes_left=6,
        options=options or [play_pokegear, play_salvatore, chilly, end],
        turn=4,
        first_player=0,
        your_index=1,
        deck_count=deck_count,
        deck_ids=deck_ids,
    )
    board.opp.handCount = 9
    board.state.supporterPlayed = supporter_played
    board._hand_ids = hand_ids or [
        main.BASIC_DARK_ENERGY,
        main.POKEGEAR,
        main.WALLY_COMPASSION,
        main.SURFING_BEACH,
        main.BASIC_WATER_ENERGY,
        main.TANKER,
    ]
    return board, play_pokegear, play_salvatore, chilly, end


def public_salvatore_deck():
    return [main.SALVATORE, main.SALVATORE, main.MEGA_YUKIMENOKO_EX] + [main.BASIC_WATER_ENERGY] * 39


def test_pokegear_salvatore_chain_replay_88272517_t4_rank():
    board, next_action = replay_board("参考ログ/v7.5/ポケギア使ってセイジ出せよ.json", 37, 1)

    assert next_action == [5]
    assert board.state.turn == 4
    assert board.state.firstPlayer == 0
    assert board.state.yourIndex == 1
    assert board.pid(board.active) == main.YUKIWARASHI
    assert getattr(board.active, "serial", None) == 78
    assert energy_ids(board.active) == [main.BASIC_WATER_ENERGY] * 3
    assert board.pid(board.opp_active) == 678
    assert main.hp_left(board.opp_active) == 290
    assert board.opp.handCount == 9
    assert board.my_prizes_left() == 6
    assert not board.state.supporterPlayed

    replay_attack = board.select.option[5]
    assert replay_attack.attackId == main.CHILLY
    attack_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_attack(replay_attack)
    assert attack_outcome.damage == 10
    assert not attack_outcome.knockout

    ranked = main.GameSimulator(board).rank_options()
    pokegear_result = next(result for result in ranked if option_description(board, result.option) == ("PLAY", main.POKEGEAR, None, None))
    attack_result = next(result for result in ranked if result.option is replay_attack)

    assert ranked[0].option is pokegear_result.option
    assert pokegear_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert pokegear_result.outcome.expected_reachable_attack_id == main.RESENTFUL_REFRAIN
    assert math.isclose(pokegear_result.outcome.expected_hit_probability, 0.2692722787542399, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(pokegear_result.outcome.expected_reachable_damage, 121.17252543940796, rel_tol=1e-12, abs_tol=1e-12)
    assert pokegear_result.outcome.expected_reachable_knockout
    assert math.isclose(pokegear_result.outcome.expected_reachable_prizes_taken, 0.8078168362627198, rel_tol=1e-12, abs_tol=1e-12)
    assert attack_result.action_score.tier == main.TIER_NON_KO_ATTACK
    assert attack_outcome.damage == 10
    assert not attack_outcome.knockout


def test_pokegear_salvatore_candidate_chain_is_definite_after_search():
    salvatore = card_choice(main.SALVATORE)
    lillie = card_choice(main.LILLIE_DETERMINATION)
    crispin = card_choice(main.CRISPIN)
    board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(options=[crispin, salvatore, lillie], deck_ids=public_salvatore_deck())
    board.select.context = main.SelectContext.TO_HAND
    board.select.effect = SimpleNamespace(id=main.POKEGEAR)

    ranked = main.GameSimulator(board).rank_options()
    salvatore_result = next(result for result in ranked if result.option is salvatore)

    assert ranked[0].option is salvatore
    assert salvatore_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert salvatore_result.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert salvatore_result.outcome.reachable_damage == 450
    assert salvatore_result.outcome.reachable_knockout
    assert salvatore_result.outcome.reachable_prizes_taken == 3


def test_salvatore_play_chain_reaches_froslass_attack_ko():
    board, _pokegear, salvatore_play, chilly, end = pokegear_salvatore_chain_board(options=None, deck_ids=public_salvatore_deck())
    board._options = [salvatore_play, chilly, end]

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(salvatore_play)
    ranked = main.GameSimulator(board).rank_options()

    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 450
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 3
    assert ranked[0].option is salvatore_play
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_salvatore_target_chain_uses_existing_evolution_attack_facts():
    board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(deck_ids=public_salvatore_deck())
    target_option = switch_target_option(board.active)
    board._options = [target_option]
    board.select.context = main.SelectContext.TO_FIELD
    board.select.effect = SimpleNamespace(id=main.SALVATORE)

    facts = board.active_evolution_attack_facts(evolve_option(main.MEGA_YUKIMENOKO_EX, board.active))
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_target(board.active)
    ranked = main.GameSimulator(board).rank_options()

    assert any(fact.attack_id == main.RESENTFUL_REFRAIN and fact.damage == 450 and fact.knockout and fact.prizes_taken == 3 for fact in facts)
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 450
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 3
    assert ranked[0].option is target_option
    assert ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_pokegear_salvatore_chain_negative_guards():
    used_pokegear = play_option(main.POKEGEAR)
    used_supporter, _pokegear, _play_salvatore, chilly, _end = pokegear_salvatore_chain_board(
        options=[used_pokegear, option(main.OptionType.ATTACK, main.CHILLY)],
        supporter_played=True,
    )
    assert not main.ImmediateOutcomeEvaluator(used_supporter).evaluate_pokegear_play(used_pokegear).expected_reachable_knockout
    used_supporter.select.context = main.SelectContext.TO_HAND
    used_supporter.select.effect = SimpleNamespace(id=main.POKEGEAR)
    used_supporter_candidate = card_choice(main.SALVATORE)
    used_supporter._options = [used_supporter_candidate]
    used_supporter_candidate_outcome = main.ImmediateOutcomeEvaluator(used_supporter).evaluate_pokegear_candidate(used_supporter_candidate)
    assert used_supporter_candidate_outcome.reachable_attack_id is None
    assert not used_supporter_candidate_outcome.reachable_knockout
    assert used_supporter_candidate_outcome.expected_reachable_attack_id is None
    assert not used_supporter_candidate_outcome.expected_reachable_knockout
    assert used_supporter_candidate_outcome.expected_reachable_damage == 0
    assert used_supporter_candidate_outcome.expected_reachable_prizes_taken == 0
    assert action_score_for_option(used_supporter, used_supporter_candidate).tier != main.TIER_HIGH_VALUE_PREP

    no_evolution_pokegear = play_option(main.POKEGEAR)
    no_evolution, _pokegear, _play_salvatore, _chilly, _end = pokegear_salvatore_chain_board(
        options=[no_evolution_pokegear, option(main.OptionType.ATTACK, main.CHILLY)],
        hand_ids=[main.POKEGEAR],
    )
    no_evolution.discard_ids = [main.MEGA_YUKIMENOKO_EX, main.MEGA_YUKIMENOKO_EX]
    assert not main.ImmediateOutcomeEvaluator(no_evolution).evaluate_pokegear_play(no_evolution_pokegear).expected_reachable_knockout

    no_energy_pokegear = play_option(main.POKEGEAR)
    no_energy, _pokegear, _play_salvatore, _chilly, _end = pokegear_salvatore_chain_board(options=[no_energy_pokegear, chilly])
    no_energy.active.energyCards = []
    assert not main.ImmediateOutcomeEvaluator(no_energy).evaluate_pokegear_play(no_energy_pokegear).expected_reachable_knockout

    wall_pokegear = play_option(main.POKEGEAR)
    wall, _pokegear, _play_salvatore, _chilly, _end = pokegear_salvatore_chain_board(options=[wall_pokegear, chilly], target_hp=290)
    wall.opp_active.id = 330
    assert not main.ImmediateOutcomeEvaluator(wall).evaluate_pokegear_play(wall_pokegear).expected_reachable_knockout

    no_salvatore, _pokegear, _play_salvatore, _chilly, _end = pokegear_salvatore_chain_board(
        options=[card_choice(main.LILLIE_DETERMINATION), card_choice(main.CRISPIN)]
    )
    no_salvatore.select.context = main.SelectContext.TO_HAND
    no_salvatore.select.effect = SimpleNamespace(id=main.POKEGEAR)
    assert all(board_option.cardId != main.SALVATORE for _, board_option in no_salvatore.iter_options())


def test_deck_counts_after_judge_suguri_update():
    deck_csv_ids = [
        int(line.strip().rstrip(","))
        for line in (Path(__file__).resolve().parent / "deck.csv").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    for deck in (main.DEFAULT_DECK, main.DECK, deck_csv_ids):
        assert len(deck) == 60
        assert deck.count(main.YVELTAL) == 0
        assert deck.count(main.BASIC_DARK_ENERGY) == 0
        assert deck.count(main.CRISPIN) == 0
        assert deck.count(main.SUGURI) == 2
        assert deck.count(main.JUDGE) == 2
        assert deck.count(main.BASIC_WATER_ENERGY) == 9


def test_judge_play_rank_rules():
    judge = play_option(main.JUDGE)
    non_ko_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    prep = play_option(main.POFIN)
    high_hand_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=120,
        options=[judge, non_ko_attack, prep],
        turn=3,
        first_player=0,
        your_index=0,
    )
    high_hand_board.opp.handCount = 8
    high_hand_ranked = main.GameSimulator(high_hand_board).rank_options()
    assert high_hand_ranked[0].option is judge
    assert action_score_for_option(high_hand_board, judge).tier == main.TIER_HIGH_VALUE_PREP
    assert [result.option for result in high_hand_ranked].index(judge) < [result.option for result in high_hand_ranked].index(non_ko_attack)
    assert [result.option for result in high_hand_ranked].index(judge) < [result.option for result in high_hand_ranked].index(prep)
    high_hand_board.select.context = main.SelectContext.TO_HAND
    high_hand_board.select.effect = SimpleNamespace(id=main.POKEGEAR)
    judge_candidate = card_choice(main.JUDGE)
    assert policy_for(high_hand_board).score_card_selection(judge_candidate) == policy_for(high_hand_board).score_play(judge)

    direct_ko = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    direct_ko_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=40,
        options=[judge, direct_ko],
        turn=3,
        first_player=0,
        your_index=0,
    )
    direct_ko_board.opp.handCount = 8
    direct_ko_ranked = main.GameSimulator(direct_ko_board).rank_options()
    assert direct_ko_ranked[0].option is direct_ko
    assert action_score_for_option(direct_ko_board, direct_ko).tier == main.TIER_KO
    assert [result.option for result in direct_ko_ranked].index(direct_ko) < [result.option for result in direct_ko_ranked].index(judge)

    froslass_attack = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    low_hand_board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=400,
        options=[judge, froslass_attack],
        turn=3,
        first_player=0,
        your_index=0,
    )
    low_hand_board.opp.handCount = 7
    low_hand_ranked = main.GameSimulator(low_hand_board).rank_options()
    assert low_hand_ranked[0].option is froslass_attack
    assert action_score_for_option(low_hand_board, judge).tier != main.TIER_HIGH_VALUE_PREP

    alakazam_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=741,
        target_hp=120,
        options=[judge, non_ko_attack, prep],
        turn=3,
        first_player=0,
        your_index=0,
    )
    alakazam_board.opp.handCount = 4
    alakazam_ranked = main.GameSimulator(alakazam_board).rank_options()
    assert alakazam_ranked[0].option is judge
    assert action_score_for_option(alakazam_board, judge).tier == main.TIER_HIGH_VALUE_PREP
    assert [result.option for result in alakazam_ranked].index(judge) < [result.option for result in alakazam_ranked].index(prep)


def test_suguri_play_rank_rules():
    suguri = play_option(main.SUGURI)
    attack_option = option(main.OptionType.ATTACK, main.JETTING_BLOW)

    basic_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=70,
        options=[suguri, option(main.OptionType.ATTACK, main.WATER_GUN)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    assert action_score_for_option(basic_board, suguri).tier != main.TIER_HIGH_VALUE_PREP

    non_ex_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=999,
        target_hp=70,
        options=[suguri, attack_option],
        turn=3,
        first_player=0,
        your_index=0,
    )
    assert action_score_for_option(non_ex_board, suguri).tier != main.TIER_HIGH_VALUE_PREP

    low_damage_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=100,
        options=[suguri, attack_option],
        attacks={main.JETTING_BLOW: attack(main.JETTING_BLOW, 10, [main.EnergyType.WATER])},
        turn=3,
        first_player=0,
        your_index=0,
    )
    assert action_score_for_option(low_damage_board, suguri).tier != main.TIER_HIGH_VALUE_PREP

    already_ko_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=40,
        options=[suguri, attack_option],
        turn=3,
        first_player=0,
        your_index=0,
    )
    already_ko_ranked = main.GameSimulator(already_ko_board).rank_options()
    assert already_ko_ranked[0].option is attack_option
    assert action_score_for_option(already_ko_board, attack_option).tier == main.TIER_KO
    assert [result.option for result in already_ko_ranked].index(attack_option) < [result.option for result in already_ko_ranked].index(suguri)

    boost_ko_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=70,
        prizes_left=3,
        options=[suguri, attack_option, play_option(main.POFIN)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    boost_ko_ranked = main.GameSimulator(boost_ko_board).rank_options()
    assert boost_ko_ranked[0].option is suguri
    assert action_score_for_option(boost_ko_board, suguri).tier == main.TIER_HIGH_VALUE_PREP
    assert action_score_for_option(boost_ko_board, suguri).tier < main.TIER_KO
    assert [result.option for result in boost_ko_ranked].index(suguri) < [result.option for result in boost_ko_ranked].index(attack_option)
    boost_ko_board.select.context = main.SelectContext.TO_HAND
    boost_ko_board.select.effect = SimpleNamespace(id=main.POKEGEAR)
    suguri_candidate = card_choice(main.SUGURI)
    assert policy_for(boost_ko_board).score_card_selection(suguri_candidate) == policy_for(boost_ko_board).score_play(suguri)

    plus_30_mode = option(main.OptionType.NO)
    switch_mode = option(main.OptionType.YES)
    mode_switch_target = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=830, energies=[main.BASIC_WATER_ENERGY])
    mode_boost_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=70,
        prizes_left=3,
        bench=[mode_switch_target],
        options=[switch_mode, plus_30_mode],
        turn=3,
        first_player=0,
        your_index=0,
    )
    mode_boost_board.select.context = main.SelectContext.FIRST_EFFECT
    mode_boost_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    mode_boost_ranked = main.GameSimulator(mode_boost_board).rank_options()
    mode_boost_direct = main.ImmediateOutcomeEvaluator(mode_boost_board).evaluate_attack(attack_option)
    assert mode_boost_direct.damage == 50
    assert not mode_boost_direct.knockout
    assert mode_boost_direct.prizes_taken == 0
    assert not mode_boost_direct.wins_game
    assert policy_for(mode_boost_board).score(1, plus_30_mode) == 94000
    assert policy_for(mode_boost_board).score(0, switch_mode) == 88000
    assert mode_boost_ranked[0].option is plus_30_mode
    assert policy_for(mode_boost_board).score(1, plus_30_mode) > policy_for(mode_boost_board).score(0, switch_mode)
    assert [result.option for result in mode_boost_ranked].index(plus_30_mode) < [result.option for result in mode_boost_ranked].index(switch_mode)

    non_ex_mode_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=999,
        target_hp=70,
        bench=[mode_switch_target],
        options=[switch_mode, plus_30_mode],
        turn=3,
        first_player=0,
        your_index=0,
    )
    non_ex_mode_board.select.context = main.SelectContext.FIRST_EFFECT
    non_ex_mode_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    assert policy_for(non_ex_mode_board).score(1, plus_30_mode) < 50000

    low_damage_mode_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=100,
        options=[switch_mode, plus_30_mode],
        attacks={main.JETTING_BLOW: attack(main.JETTING_BLOW, 10, [main.EnergyType.WATER])},
        turn=3,
        first_player=0,
        your_index=0,
    )
    low_damage_mode_board.select.context = main.SelectContext.FIRST_EFFECT
    low_damage_mode_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    low_damage_direct = main.ImmediateOutcomeEvaluator(low_damage_mode_board).evaluate_attack(attack_option)
    assert low_damage_direct.damage == 10
    assert not low_damage_direct.knockout
    assert low_damage_direct.prizes_taken == 0
    assert not low_damage_direct.wins_game
    assert policy_for(low_damage_mode_board).score(1, plus_30_mode) < 50000

    ready_froslass = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=831, energies=[main.BASIC_WATER_ENERGY])
    mode_switch_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=999,
        target_hp=150,
        bench=[ready_froslass],
        options=[switch_mode, plus_30_mode],
        turn=3,
        first_player=0,
        your_index=0,
    )
    mode_switch_board.me.asleep = True
    mode_switch_board.opp.handCount = 4
    mode_switch_board.select.context = main.SelectContext.FIRST_EFFECT
    mode_switch_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    mode_switch_ranked = main.GameSimulator(mode_switch_board).rank_options()
    assert mode_switch_ranked[0].option is switch_mode
    assert policy_for(mode_switch_board).score(0, switch_mode) == 88000
    assert policy_for(mode_switch_board).score(0, switch_mode) > policy_for(mode_switch_board).score(1, plus_30_mode)
    assert policy_for(mode_switch_board).score(1, plus_30_mode) < 50000
    assert [result.option for result in mode_switch_ranked].index(switch_mode) < [result.option for result in mode_switch_ranked].index(plus_30_mode)

    basic_board.select.context = main.SelectContext.FIRST_EFFECT
    basic_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    assert policy_for(basic_board).score(0, switch_mode) < 50000
    assert policy_for(basic_board).score(1, plus_30_mode) < 50000

    basic_ready_froslass = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=832, energies=[main.BASIC_WATER_ENERGY])
    basic_switch_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=999,
        target_hp=150,
        bench=[basic_ready_froslass],
        options=[switch_mode, plus_30_mode],
        turn=3,
        first_player=0,
        your_index=0,
    )
    basic_switch_board.me.asleep = True
    basic_switch_board.opp.handCount = 4
    basic_switch_board.select.context = main.SelectContext.FIRST_EFFECT
    basic_switch_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    assert policy_for(basic_switch_board).score(0, switch_mode) == 1000
    assert policy_for(basic_switch_board).score(1, plus_30_mode) == 1000

    direct_ko_ready_froslass = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=833, energies=[main.BASIC_WATER_ENERGY])
    direct_ko_switch_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=999,
        target_hp=40,
        bench=[direct_ko_ready_froslass],
        options=[attack_option, switch_mode, plus_30_mode],
        turn=3,
        first_player=0,
        your_index=0,
    )
    direct_ko_switch_board.opp.handCount = 4
    direct_ko_switch_board.select.context = main.SelectContext.FIRST_EFFECT
    direct_ko_switch_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    direct_ko_mode_ranked = main.GameSimulator(direct_ko_switch_board).rank_options()
    assert direct_ko_mode_ranked[0].option is attack_option
    assert action_score_for_option(direct_ko_switch_board, attack_option).tier == main.TIER_KO
    direct_ko_outcome = main.ImmediateOutcomeEvaluator(direct_ko_switch_board).evaluate_attack(attack_option)
    assert direct_ko_outcome.knockout
    assert not direct_ko_outcome.wins_game
    assert policy_for(direct_ko_switch_board).score(1, switch_mode) == 1000
    assert policy_for(direct_ko_switch_board).score(2, plus_30_mode) == 1000

    direct_win_switch_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=40,
        prizes_left=2,
        bench=[direct_ko_ready_froslass],
        options=[attack_option, switch_mode, plus_30_mode],
        turn=3,
        first_player=0,
        your_index=0,
    )
    direct_win_switch_board.opp.handCount = 4
    direct_win_switch_board.select.context = main.SelectContext.FIRST_EFFECT
    direct_win_switch_board.select.contextCard = SimpleNamespace(id=main.SUGURI)
    direct_win_outcome = main.ImmediateOutcomeEvaluator(direct_win_switch_board).evaluate_attack(attack_option)
    assert direct_win_outcome.knockout
    assert direct_win_outcome.wins_game
    direct_win_mode_ranked = main.GameSimulator(direct_win_switch_board).rank_options()
    assert direct_win_mode_ranked[0].option is attack_option
    assert policy_for(direct_win_switch_board).score(1, switch_mode) == 1000
    assert policy_for(direct_win_switch_board).score(2, plus_30_mode) == 1000


def test_suguri_switch_target_rank_rules():
    ready_froslass = pokemon(main.MEGA_YUKIMENOKO_EX, hp=310, max_hp=310, serial=810, energies=[main.BASIC_WATER_ENERGY])
    no_energy_starmie = pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=811, energies=[])
    ready_target = switch_target_option(ready_froslass)
    invalid_target = switch_target_option(no_energy_starmie)
    status_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=150,
        bench=[ready_froslass, no_energy_starmie],
        options=[ready_target, invalid_target],
        turn=3,
        first_player=0,
        your_index=0,
    )
    status_board.me.asleep = True
    status_board.opp.handCount = 4
    status_board.select.context = main.SelectContext.SWITCH
    status_board.select.effect = SimpleNamespace(id=main.SUGURI)

    ranked = main.GameSimulator(status_board).rank_options()
    ready_outcome = main.ImmediateOutcomeEvaluator(status_board).evaluate_switch_target(ready_froslass, "suguri")
    invalid_outcome = main.ImmediateOutcomeEvaluator(status_board).evaluate_switch_target(no_energy_starmie, "suguri")

    assert ranked[0].option is ready_target
    assert ready_outcome.enables_attack
    assert "suguri_switch" in ready_outcome.reasons
    assert not invalid_outcome.enables_attack
    assert [result.option for result in ranked].index(ready_target) < [result.option for result in ranked].index(invalid_target)

    weak_target = pokemon(main.SHAYMIN, hp=80, max_hp=80, serial=812, energies=[])
    weak_option = switch_target_option(weak_target)
    no_improvement_board = FakeBoard(
        active_energies=[main.BASIC_WATER_ENERGY],
        target_hp=120,
        bench=[weak_target],
        options=[weak_option],
        turn=3,
        first_player=0,
        your_index=0,
    )
    no_improvement_board.select.context = main.SelectContext.SWITCH
    no_improvement_board.select.effect = SimpleNamespace(id=main.SUGURI)
    assert policy_for(no_improvement_board).score_target_or_card(weak_option) <= 0


def test_pokegear_salvatore_chain_direct_ko_and_low_probability_guards():
    pokegear = play_option(main.POKEGEAR)
    direct_ko = option(main.OptionType.ATTACK, main.RESENTFUL_REFRAIN)
    board = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=(main.BASIC_WATER_ENERGY,),
        target_id=678,
        target_hp=290,
        prizes_left=6,
        options=[pokegear, direct_ko],
        turn=4,
        first_player=0,
        your_index=1,
        deck_count=42,
    )
    board.opp.handCount = 9
    board._hand_ids = [main.POKEGEAR]

    ranked = main.GameSimulator(board).rank_options()
    assert ranked[0].option is direct_ko
    assert ranked[0].action_score.tier == main.TIER_KO

    low_pokegear = play_option(main.POKEGEAR)
    low_probability, _pokegear, _play_salvatore, chilly, _end = pokegear_salvatore_chain_board(
        options=[low_pokegear, option(main.OptionType.ATTACK, main.CHILLY)],
        deck_count=60,
    )
    low_probability.discard_ids = [main.SALVATORE]
    outcome = main.ImmediateOutcomeEvaluator(low_probability).evaluate_pokegear_play(low_pokegear)
    action_score = action_score_for_option(low_probability, low_pokegear)
    assert outcome.expected_hit_probability < 0.25
    assert outcome.expected_reachable_knockout
    assert action_score.tier != main.TIER_HIGH_VALUE_PREP


def test_salvatore_effect_resolution_keeps_chain_after_supporter_played():
    board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(deck_ids=public_salvatore_deck())
    target_option = switch_target_option(board.active)
    board._options = [target_option, play_option(main.LILLIE_DETERMINATION)]
    board.select.context = main.SelectContext.TO_FIELD
    board.select.effect = SimpleNamespace(id=main.SALVATORE)
    board.state.supporterPlayed = True

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_target(board.active)

    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_damage == 450
    assert outcome.reachable_knockout
    assert main.Policy(board).score_play(board._options[1]) == main.SCORE_FORBIDDEN


def test_salvatore_requires_evolution_card_in_deck_not_only_hand():
    board, _pokegear, salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        hand_ids=[main.SALVATORE, main.MEGA_YUKIMENOKO_EX],
        deck_ids=[main.SALVATORE, main.BASIC_WATER_ENERGY, main.HITODEMAN],
    )
    board._options = [salvatore_play, option(main.OptionType.END)]

    assert board.salvatore_target_evolution(board.active) == main.MEGA_YUKIMENOKO_EX
    assert board.salvatore_deck_target_evolution(board.active) is None
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(salvatore_play)
    assert outcome.reachable_attack_id is None
    assert action_score_for_option(board, salvatore_play).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_pokegear_probability_accounts_for_unknown_prizes():
    board, pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[play_option(main.POKEGEAR), option(main.OptionType.ATTACK, main.CHILLY)],
        deck_count=42,
    )

    probability = board.pokegear_hit_probability(main.SALVATORE)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_play(pokegear)

    assert 0.25 < probability < 0.308943
    assert outcome.expected_hit_probability < probability
    assert outcome.expected_reachable_knockout


def test_salvatore_text_allows_this_turn_pokemon_target_chain():
    board, _pokegear, salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(deck_ids=public_salvatore_deck())
    board.active.appearThisTurn = True

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(salvatore_play)

    assert "put into play this turn" in main.CARD_TABLE[main.SALVATORE].skills[0].text
    assert board.salvatore_can_evolve_from_deck_this_turn(board.active, main.MEGA_YUKIMENOKO_EX)
    assert outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert outcome.reachable_knockout


def test_salvatore_first_player_first_turn_does_not_claim_same_turn_attack():
    salvatore_play = play_option(main.SALVATORE)
    board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[salvatore_play, option(main.OptionType.END)],
    )
    board.state.turn = 1
    board.state.firstPlayer = 1
    board.state.yourIndex = 1

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(board._options[0])

    assert board.salvatore_live()
    assert outcome.reachable_attack_id is None
    assert action_score_for_option(board, board._options[0]).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_salvatore_evolution_candidate_reaches_attack_outcome():
    froslass = card_choice(main.MEGA_YUKIMENOKO_EX)
    starmie = card_choice(main.MEGA_STARMIE_EX)
    board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(options=[starmie, froslass])
    board.select.context = main.SelectContext.EVOLVES_TO
    board.select.effect = SimpleNamespace(id=main.SALVATORE)
    board.state.supporterPlayed = True

    ranked = main.GameSimulator(board).rank_options()
    froslass_result = next(result for result in ranked if result.option is froslass)

    assert ranked[0].option is froslass
    assert froslass_result.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert froslass_result.outcome.reachable_damage == 450
    assert froslass_result.outcome.reachable_knockout
    assert froslass_result.outcome.reachable_prizes_taken == 3


def test_pokegear_expected_chain_competes_with_strong_non_ko_attack():
    weak_attack = option(main.OptionType.ATTACK, main.CHILLY)
    weak_board, pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[play_option(main.POKEGEAR), weak_attack],
        target_id=999,
        target_hp=290,
        deck_ids=public_salvatore_deck(),
    )
    weak_ranked = main.GameSimulator(weak_board).rank_options()
    assert weak_ranked[0].option is weak_board._options[0]

    strong_pokegear = play_option(main.POKEGEAR)
    strong_attack = option(main.OptionType.ATTACK, main.CHILLY)
    strong_board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[strong_pokegear, strong_attack],
        target_id=999,
        target_hp=290,
    )
    strong_board._attacks[main.CHILLY] = attack(main.CHILLY, 220, [main.EnergyType.WATER])
    strong_ranked = main.GameSimulator(strong_board).rank_options()
    strong_pokegear_result = next(result for result in strong_ranked if result.option is strong_pokegear)
    assert strong_ranked[0].option is strong_attack
    assert strong_pokegear_result.action_score.tier != main.TIER_HIGH_VALUE_PREP

    direct_ko_pokegear = play_option(main.POKEGEAR)
    direct_ko = option(main.OptionType.ATTACK, main.CHILLY)
    direct_board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[direct_ko_pokegear, direct_ko],
        target_id=999,
        target_hp=10,
    )
    direct_ranked = main.GameSimulator(direct_board).rank_options()
    assert direct_ranked[0].option is direct_ko
    assert direct_ranked[0].action_score.tier == main.TIER_KO


def test_pokegear_salvatore_chain_additional_failure_guards():
    no_salvatore_pokegear = play_option(main.POKEGEAR)
    no_salvatore, _pokegear, _salvatore_play, chilly, _end = pokegear_salvatore_chain_board(
        options=[no_salvatore_pokegear, option(main.OptionType.ATTACK, main.CHILLY)],
    )
    no_salvatore.discard_ids = [main.SALVATORE, main.SALVATORE]
    assert not main.ImmediateOutcomeEvaluator(no_salvatore).evaluate_pokegear_play(no_salvatore_pokegear).expected_reachable_knockout

    no_candidate, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[card_choice(main.LILLIE_DETERMINATION), card_choice(main.CRISPIN)]
    )
    no_candidate.select.context = main.SelectContext.TO_HAND
    no_candidate.select.effect = SimpleNamespace(id=main.POKEGEAR)
    ranked = main.GameSimulator(no_candidate).rank_options()
    assert all(result.option.cardId != main.SALVATORE for result in ranked)


def test_pokegear_chain_probability_fixed_literal_value():
    board = FakeBoard(active_id=main.YUKIWARASHI, deck_count=42, prizes_left=6)

    probability = board.pokegear_chain_hit_probability(main.SALVATORE, main.MEGA_STARMIE_EX)

    assert math.isclose(probability, 0.2692722787542399, rel_tol=1e-12, abs_tol=1e-12)


def test_pokegear_chain_probability_matches_small_bruteforce():
    board = FakeBoard(active_id=main.YUKIWARASHI)

    total = 0
    success = 0
    hidden_positions = range(6)
    deck_positions = set(range(4))
    look_positions = set(range(2))
    for supporter_position in hidden_positions:
        for evolution_position in hidden_positions:
            if evolution_position == supporter_position:
                continue
            total += 1
            if supporter_position in look_positions and evolution_position in deck_positions:
                success += 1

    expected = success / total
    actual = board.pokegear_chain_hit_probability_from_counts(
        hidden_count=6,
        deck_count=4,
        look_count=2,
        supporter_count=1,
        evolution_count=1,
    )

    assert math.isclose(expected, 0.2, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)


def test_pokegear_expected_chain_values_are_multiplied_once():
    board, _next_action = replay_board("参考ログ/v7.5/ポケギア使ってセイジ出せよ.json", 37, 1)
    pokegear = next(option for option in board.select.option if option_description(board, option) == ("PLAY", main.POKEGEAR, None, None))

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_play(pokegear)

    probability = 0.2692722787542399
    assert math.isclose(outcome.expected_hit_probability, probability, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(outcome.expected_reachable_damage, 450 * probability, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(outcome.expected_reachable_prizes_taken, 3 * probability, rel_tol=1e-12, abs_tol=1e-12)
    assert not math.isclose(outcome.expected_reachable_damage, 450 * probability * probability, rel_tol=1e-12, abs_tol=1e-12)


def test_remaining_possible_ignores_opponent_cards_for_own_deck():
    board = FakeBoard(
        active_id=main.YUKIWARASHI,
        opp_bench=[pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=501)],
        deck_count=42,
    )
    board.discard_ids = [main.MEGA_STARMIE_EX]

    assert main.DECK.count(main.MEGA_STARMIE_EX) >= 2
    assert board.remaining_possible_count(main.MEGA_STARMIE_EX) == main.DECK.count(main.MEGA_STARMIE_EX) - 1
    assert board.remaining_possible(main.MEGA_STARMIE_EX)


def test_salvatore_public_deck_without_evolution_has_no_certain_chain():
    salvatore = play_option(main.SALVATORE)
    pokegear = play_option(main.POKEGEAR)
    target = switch_target_option(None)
    candidate = card_choice(main.SALVATORE)
    board, _pokegear, _salvatore_play, _chilly, _end = pokegear_salvatore_chain_board(
        options=[pokegear, salvatore],
        hand_ids=[main.SALVATORE, main.MEGA_YUKIMENOKO_EX],
        deck_ids=[main.SALVATORE, main.BASIC_WATER_ENERGY, main.HITODEMAN],
    )
    target.target = board.active

    play_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(salvatore)
    target_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_target(board.active)
    board.select.context = main.SelectContext.TO_HAND
    board.select.effect = SimpleNamespace(id=main.POKEGEAR)
    candidate_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_candidate(candidate)
    pokegear_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_play(pokegear)

    for outcome in (play_outcome, target_outcome, candidate_outcome, pokegear_outcome):
        assert outcome.reachable_attack_id is None
        assert not outcome.reachable_knockout
        assert outcome.expected_reachable_attack_id is None
        assert not outcome.expected_reachable_knockout


def test_salvatore_public_deck_with_evolution_has_certain_chain():
    salvatore_candidate = card_choice(main.SALVATORE)
    board, pokegear, salvatore, _chilly, _end = pokegear_salvatore_chain_board(deck_ids=public_salvatore_deck())

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(salvatore)
    target_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_target(board.active)
    board.select.context = main.SelectContext.TO_HAND
    board.select.effect = SimpleNamespace(id=main.POKEGEAR)
    candidate_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_candidate(salvatore_candidate)
    pokegear_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_play(pokegear)

    for certain_outcome in (outcome, target_outcome, candidate_outcome):
        assert certain_outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
        assert certain_outcome.reachable_damage == 450
        assert certain_outcome.reachable_knockout
        assert certain_outcome.reachable_prizes_taken == 3
        assert certain_outcome.expected_reachable_attack_id is None
    assert pokegear_outcome.reachable_attack_id is None
    assert pokegear_outcome.expected_reachable_attack_id == main.RESENTFUL_REFRAIN
    assert pokegear_outcome.expected_hit_probability > 0
    assert pokegear_outcome.expected_reachable_damage > 0


def test_salvatore_nonpublic_evolution_one_copy_returns_expected_not_certain():
    salvatore_candidate = card_choice(main.SALVATORE)
    board, _pokegear, salvatore, _chilly, _end = pokegear_salvatore_chain_board(deck_count=42)
    board.discard_ids = [main.MEGA_YUKIMENOKO_EX]

    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_play(salvatore)
    target_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_salvatore_target(board.active)
    board.select.context = main.SelectContext.TO_HAND
    board.select.effect = SimpleNamespace(id=main.POKEGEAR)
    candidate_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_candidate(salvatore_candidate)

    for expected_outcome in (outcome, target_outcome, candidate_outcome):
        assert expected_outcome.reachable_attack_id is None
        assert not expected_outcome.reachable_knockout
        assert expected_outcome.expected_reachable_attack_id == main.RESENTFUL_REFRAIN
        assert expected_outcome.expected_hit_probability == 42 / 48
        assert expected_outcome.expected_reachable_damage == 450 * 42 / 48
        assert expected_outcome.expected_reachable_prizes_taken == 3 * 42 / 48
        assert expected_outcome.expected_reachable_knockout


def test_salvatore_chain_contexts_do_not_claim_energy_insufficient_or_wall():
    salvatore_candidate = card_choice(main.SALVATORE)

    no_energy, pokegear, salvatore, _chilly, _end = pokegear_salvatore_chain_board(deck_ids=public_salvatore_deck())
    no_energy.active.energyCards = []
    no_energy.select.context = main.SelectContext.TO_HAND
    no_energy.select.effect = SimpleNamespace(id=main.POKEGEAR)
    no_energy_outcomes = (
        main.ImmediateOutcomeEvaluator(no_energy).evaluate_salvatore_play(salvatore),
        main.ImmediateOutcomeEvaluator(no_energy).evaluate_salvatore_target(no_energy.active),
        main.ImmediateOutcomeEvaluator(no_energy).evaluate_pokegear_candidate(salvatore_candidate),
        main.ImmediateOutcomeEvaluator(no_energy).evaluate_pokegear_play(pokegear),
    )

    wall, pokegear, salvatore, _chilly, _end = pokegear_salvatore_chain_board(deck_ids=public_salvatore_deck())
    wall.opp_active.id = 330
    wall.select.context = main.SelectContext.TO_HAND
    wall.select.effect = SimpleNamespace(id=main.POKEGEAR)
    wall_outcomes = (
        main.ImmediateOutcomeEvaluator(wall).evaluate_salvatore_play(salvatore),
        main.ImmediateOutcomeEvaluator(wall).evaluate_salvatore_target(wall.active),
        main.ImmediateOutcomeEvaluator(wall).evaluate_pokegear_candidate(salvatore_candidate),
        main.ImmediateOutcomeEvaluator(wall).evaluate_pokegear_play(pokegear),
    )

    for outcome in no_energy_outcomes + wall_outcomes:
        assert outcome.reachable_attack_id is None
        assert not outcome.reachable_knockout
        assert outcome.expected_reachable_attack_id is None
        assert not outcome.expected_reachable_knockout


def test_pokegear_uses_chain_probability_below_salvatore_hit_only():
    board, pokegear, _salvatore, _chilly, _end = pokegear_salvatore_chain_board(
        options=[play_option(main.POKEGEAR), option(main.OptionType.ATTACK, main.CHILLY)],
        deck_count=42,
    )
    board.discard_ids = [main.MEGA_YUKIMENOKO_EX]

    salvatore_only = board.pokegear_hit_probability(main.SALVATORE)
    chain_probability = board.pokegear_chain_hit_probability(main.SALVATORE, main.MEGA_YUKIMENOKO_EX)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_pokegear_play(pokegear)

    assert salvatore_only > 0.25
    assert chain_probability < 0.25
    assert outcome.expected_hit_probability == chain_probability
    assert outcome.expected_hit_probability < salvatore_only


def test_pokegear_chain_probability_boundary_does_not_raise_tier40():
    pokegear = play_option(main.POKEGEAR)
    attack_option = option(main.OptionType.ATTACK, main.CHILLY)
    board, _pokegear, _salvatore, _chilly, _end = pokegear_salvatore_chain_board(
        options=[pokegear, attack_option],
        deck_count=42,
    )
    board.discard_ids = [main.MEGA_YUKIMENOKO_EX]

    ranked = main.GameSimulator(board).rank_options()
    pokegear_result = next(result for result in ranked if result.option is pokegear)

    assert board.pokegear_hit_probability(main.SALVATORE) > 0.25
    assert pokegear_result.outcome.expected_hit_probability < 0.25
    assert pokegear_result.action_score.tier != main.TIER_HIGH_VALUE_PREP


def test_active_evolution_reachable_attack_beats_expected_pokegear_v8():
    water = main.BASIC_WATER_ENERGY
    pokegear = play_option(main.POKEGEAR)
    end = option(main.OptionType.END)
    board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water, water, water],
        target_hp=140,
        options=[],
        deck_ids=[main.SALVATORE, main.MEGA_YUKIMENOKO_EX],
        turn=3,
        first_player=0,
        your_index=0,
    )
    evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, board.active)
    board._options = [pokegear, evolve, end]
    board._hand_ids = [main.POKEGEAR, main.MEGA_YUKIMENOKO_EX]

    ranked = main.GameSimulator(board).rank_options()
    evolve_result = next(result for result in ranked if result.option is evolve)
    pokegear_result = next(result for result in ranked if result.option is pokegear)

    assert evolve_result.outcome.damage == 0
    assert not evolve_result.outcome.knockout
    assert evolve_result.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert evolve_result.outcome.reachable_damage == 200
    assert evolve_result.outcome.reachable_knockout
    assert evolve_result.outcome.reachable_prizes_taken == 1
    assert not evolve_result.outcome.reachable_wins_game
    assert evolve_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert pokegear_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert ranked[0].option is evolve


def test_active_evolution_reachable_win_stays_below_direct_win_attack_v8():
    water = main.BASIC_WATER_ENERGY
    direct_win = option(main.OptionType.ATTACK, main.CHILLY)
    end = option(main.OptionType.END)
    attacks = {
        main.CHILLY: attack(main.CHILLY, 80, [main.EnergyType.WATER]),
        main.RESENTFUL_REFRAIN: attack(main.RESENTFUL_REFRAIN, 0, [main.EnergyType.WATER]),
        main.ABSOLUTE_SNOW: attack(main.ABSOLUTE_SNOW, 150, [main.EnergyType.WATER, main.EnergyType.COLORLESS, main.EnergyType.COLORLESS]),
    }
    board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water, water, water],
        target_hp=70,
        prizes_left=1,
        options=[],
        attacks=attacks,
        turn=3,
        first_player=0,
        your_index=0,
    )
    evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, board.active)
    board._options = [evolve, direct_win, end]

    ranked = main.GameSimulator(board).rank_options()
    evolve_result = next(result for result in ranked if result.option is evolve)
    attack_result = next(result for result in ranked if result.option is direct_win)

    assert evolve_result.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert evolve_result.outcome.reachable_knockout
    assert evolve_result.outcome.reachable_prizes_taken == 1
    assert evolve_result.outcome.reachable_wins_game
    assert evolve_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert attack_result.outcome.knockout
    assert attack_result.outcome.wins_game
    assert attack_result.action_score.tier == main.TIER_WIN
    assert ranked[0].option is direct_win


def test_active_evolution_reachable_ko_stays_below_direct_ko_attack_v8():
    water = main.BASIC_WATER_ENERGY
    direct_ko = option(main.OptionType.ATTACK, main.CHILLY)
    end = option(main.OptionType.END)
    attacks = {
        main.CHILLY: attack(main.CHILLY, 80, [main.EnergyType.WATER]),
        main.RESENTFUL_REFRAIN: attack(main.RESENTFUL_REFRAIN, 0, [main.EnergyType.WATER]),
        main.ABSOLUTE_SNOW: attack(main.ABSOLUTE_SNOW, 150, [main.EnergyType.WATER, main.EnergyType.COLORLESS, main.EnergyType.COLORLESS]),
    }
    board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water, water, water],
        target_hp=70,
        prizes_left=2,
        options=[],
        attacks=attacks,
        turn=3,
        first_player=0,
        your_index=0,
    )
    evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, board.active)
    board._options = [evolve, direct_ko, end]

    ranked = main.GameSimulator(board).rank_options()
    evolve_result = next(result for result in ranked if result.option is evolve)
    attack_result = next(result for result in ranked if result.option is direct_ko)

    assert evolve_result.outcome.reachable_knockout
    assert not evolve_result.outcome.reachable_wins_game
    assert evolve_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert attack_result.outcome.knockout
    assert not attack_result.outcome.wins_game
    assert attack_result.action_score.tier == main.TIER_KO
    assert ranked[0].option is direct_ko


def test_active_evolution_reachable_attack_negative_guards_v8():
    water = main.BASIC_WATER_ENERGY
    bench_target = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=601, energies=[water, water, water])
    bench_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, bench_target)
    bench_board = FakeBoard(
        active_id=main.CINDERACE,
        active_energies=[main.IGNITION_ENERGY],
        bench=[bench_target],
        target_hp=70,
        options=[bench_evolve, option(main.OptionType.END)],
        turn=3,
        first_player=0,
        your_index=0,
    )
    bench_outcome = main.ImmediateOutcomeEvaluator(bench_board).evaluate_active_evolution(bench_evolve)
    bench_score = action_score_for_option(bench_board, bench_evolve)
    bench_facts = bench_board.active_evolution_attack_facts(bench_evolve)

    no_energy_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[],
        bench=[pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=704, energies=[water, water, water])],
        target_hp=70,
        options=[],
        turn=3,
        first_player=0,
        your_index=0,
    )
    no_energy_evolve = evolve_option(main.MEGA_STARMIE_EX, no_energy_board.active)
    no_energy_bench_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, no_energy_board.bench[0])
    no_energy_board._options = [no_energy_evolve, no_energy_bench_evolve, option(main.OptionType.END)]
    no_energy_outcome = main.ImmediateOutcomeEvaluator(no_energy_board).evaluate_active_evolution(no_energy_evolve)
    no_energy_score = action_score_for_option(no_energy_board, no_energy_evolve)
    no_energy_ranked = main.GameSimulator(no_energy_board).rank_options()
    no_energy_facts = no_energy_board.active_evolution_attack_facts(no_energy_evolve)

    non_ko_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[water, water, water],
        target_hp=300,
        options=[],
        turn=3,
        first_player=0,
        your_index=0,
    )
    non_ko_evolve = evolve_option(main.MEGA_STARMIE_EX, non_ko_board.active)
    non_ko_board._options = [non_ko_evolve, option(main.OptionType.END)]
    non_ko_outcome = main.ImmediateOutcomeEvaluator(non_ko_board).evaluate_active_evolution(non_ko_evolve)
    non_ko_score = action_score_for_option(non_ko_board, non_ko_evolve)

    wall_board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water],
        target_id=330,
        target_hp=70,
        options=[],
        turn=3,
        first_player=0,
        your_index=0,
    )
    wall_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, wall_board.active)
    wall_board._options = [wall_evolve, option(main.OptionType.END)]
    wall_outcome = main.ImmediateOutcomeEvaluator(wall_board).evaluate_active_evolution(wall_evolve)
    wall_score = action_score_for_option(wall_board, wall_evolve)

    asleep_board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water, water, water],
        bench=[pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=701, energies=[water, water, water])],
        target_hp=70,
        options=[],
        deck_ids=[main.SALVATORE],
        turn=3,
        first_player=0,
        your_index=0,
    )
    asleep_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, asleep_board.active)
    asleep_bench_evolve = evolve_option(main.MEGA_STARMIE_EX, asleep_board.bench[0])
    asleep_pokegear = play_option(main.POKEGEAR)
    asleep_board._options = [asleep_evolve, asleep_bench_evolve, asleep_pokegear, option(main.OptionType.END)]
    asleep_board._hand_ids = [main.POKEGEAR, main.MEGA_YUKIMENOKO_EX]
    asleep_board.me.asleep = True
    asleep_outcome = main.ImmediateOutcomeEvaluator(asleep_board).evaluate_active_evolution(asleep_evolve)
    asleep_score = action_score_for_option(asleep_board, asleep_evolve)
    asleep_ranked = main.GameSimulator(asleep_board).rank_options()
    asleep_facts = asleep_board.active_evolution_attack_facts(asleep_evolve)

    paralyzed_board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water, water, water],
        bench=[pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=702, energies=[water, water, water])],
        target_hp=70,
        options=[],
        deck_ids=[main.SALVATORE],
        turn=3,
        first_player=0,
        your_index=0,
    )
    paralyzed_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, paralyzed_board.active)
    paralyzed_bench_evolve = evolve_option(main.MEGA_STARMIE_EX, paralyzed_board.bench[0])
    paralyzed_pokegear = play_option(main.POKEGEAR)
    paralyzed_board._options = [paralyzed_evolve, paralyzed_bench_evolve, paralyzed_pokegear, option(main.OptionType.END)]
    paralyzed_board._hand_ids = [main.POKEGEAR, main.MEGA_YUKIMENOKO_EX]
    paralyzed_board.me.paralyzed = True
    paralyzed_outcome = main.ImmediateOutcomeEvaluator(paralyzed_board).evaluate_active_evolution(paralyzed_evolve)
    paralyzed_score = action_score_for_option(paralyzed_board, paralyzed_evolve)
    paralyzed_ranked = main.GameSimulator(paralyzed_board).rank_options()
    paralyzed_facts = paralyzed_board.active_evolution_attack_facts(paralyzed_evolve)

    first_turn_board = FakeBoard(
        active_id=main.YUKIWARASHI,
        active_energies=[water, water, water],
        bench=[pokemon(main.HITODEMAN, hp=70, max_hp=70, serial=703, energies=[water, water, water])],
        target_hp=70,
        options=[],
        deck_ids=[main.SALVATORE],
        turn=1,
        first_player=0,
        your_index=0,
    )
    first_turn_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, first_turn_board.active)
    first_turn_bench_evolve = evolve_option(main.MEGA_STARMIE_EX, first_turn_board.bench[0])
    first_turn_pokegear = play_option(main.POKEGEAR)
    first_turn_board._options = [first_turn_evolve, first_turn_bench_evolve, first_turn_pokegear, option(main.OptionType.END)]
    first_turn_board._hand_ids = [main.POKEGEAR, main.MEGA_YUKIMENOKO_EX]
    first_turn_outcome = main.ImmediateOutcomeEvaluator(first_turn_board).evaluate_active_evolution(first_turn_evolve)
    first_turn_score = action_score_for_option(first_turn_board, first_turn_evolve)
    first_turn_ranked = main.GameSimulator(first_turn_board).rank_options()
    first_turn_facts = first_turn_board.active_evolution_attack_facts(first_turn_evolve)

    assert bench_facts == ()
    assert bench_outcome.reachable_attack_id is None
    assert not bench_outcome.reachable_knockout
    assert not bench_outcome.reachable_wins_game
    assert bench_score.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    assert no_energy_facts == ()
    assert no_energy_outcome.reachable_attack_id is None
    assert not no_energy_outcome.reachable_knockout
    assert not no_energy_outcome.reachable_wins_game
    assert no_energy_score.tier != main.TIER_HIGH_VALUE_PREP
    assert no_energy_score.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert no_energy_ranked[0].option is not no_energy_evolve

    assert non_ko_outcome.reachable_attack_id == main.NEBULA_BEAM
    assert non_ko_outcome.reachable_damage == 180
    assert not non_ko_outcome.reachable_knockout
    assert not non_ko_outcome.reachable_wins_game
    assert non_ko_score.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    assert wall_outcome.blocked
    assert wall_outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert wall_outcome.reachable_damage == 0
    assert not wall_outcome.reachable_knockout
    assert not wall_outcome.reachable_wins_game
    assert wall_score.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    for guarded_facts, guarded_outcome, guarded_score, guarded_ranked, guarded_evolve in (
        (asleep_facts, asleep_outcome, asleep_score, asleep_ranked, asleep_evolve),
        (paralyzed_facts, paralyzed_outcome, paralyzed_score, paralyzed_ranked, paralyzed_evolve),
        (first_turn_facts, first_turn_outcome, first_turn_score, first_turn_ranked, first_turn_evolve),
    ):
        assert guarded_facts == ()
        assert guarded_outcome.reachable_attack_id is None
        assert not guarded_outcome.reachable_knockout
        assert not guarded_outcome.reachable_wins_game
        assert guarded_score.tier != main.TIER_PRESERVE_WIN_OR_KO_PREP
        assert guarded_score.tier != main.TIER_HIGH_VALUE_PREP
        assert guarded_ranked[0].option is not guarded_evolve


def test_replay_88493411_active_evolution_rank_v8():
    for step in (38, 40, 42):
        board, _next_action = replay_board("参考ログ/v8/第1弾/88493411.json", step, 1)
        ranked = main.GameSimulator(board).rank_options()
        evolve_results = [
            result
            for result in ranked
            if result.option.type == main.OptionType.EVOLVE
            and board.option_card(result.option) == main.MEGA_YUKIMENOKO_EX
            and board.pid(board.option_target(result.option)) == main.YUKIWARASHI
            and getattr(board.option_target(result.option), "serial", None) == 78
        ]
        assert len(evolve_results) == 1
        evolve_result = evolve_results[0]
        pokegear_results = [
            result
            for result in ranked
            if result.option.type == main.OptionType.PLAY
            and board.option_card(result.option) == main.POKEGEAR
        ]

        assert evolve_result.outcome.reachable_attack_id == main.ABSOLUTE_SNOW
        assert evolve_result.outcome.reachable_damage == 150
        assert evolve_result.outcome.reachable_knockout
        assert evolve_result.outcome.reachable_prizes_taken == 1
        assert not evolve_result.outcome.reachable_wins_game
        assert evolve_result.outcome.damage == 0
        assert not evolve_result.outcome.knockout
        assert not evolve_result.outcome.wins_game
        assert evolve_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
        if step in (38, 40):
            assert pokegear_results
            assert ranked.index(evolve_result) < min(ranked.index(result) for result in pokegear_results)
        else:
            assert step == 42
            assert not pokegear_results
        assert ranked[0].option is evolve_result.option


def test_surfing_beach_ability_entry_outcome_and_guards():
    def beach_ability():
        result = option(main.OptionType.ABILITY)
        result.area = main.AreaType.STADIUM
        result.index = 0
        return result

    def beach_board(
        *,
        bench,
        target_id=999,
        target_hp=180,
        prizes_left=6,
        turn=3,
        first_player=0,
        stadium_id=main.SURFING_BEACH,
        active_id=main.HITODEMAN,
        active_energies=(),
    ):
        ability = beach_ability()
        board = FakeBoard(
            active_id=active_id,
            active_energies=active_energies,
            target_id=target_id,
            target_hp=target_hp,
            prizes_left=prizes_left,
            bench=bench,
            options=[ability, option(main.OptionType.END)],
            turn=turn,
            first_player=first_player,
            your_index=0,
        )
        board.state.stadium = [SimpleNamespace(id=stadium_id, serial=900)]
        return board, ability

    ready = pokemon(
        main.MEGA_STARMIE_EX,
        hp=330,
        max_hp=330,
        serial=67,
        energies=[main.BASIC_WATER_ENERGY] * 3,
    )
    board, ability = beach_board(bench=[ready], target_hp=180)
    outcome = main.ImmediateOutcomeEvaluator(board).evaluate_surfing_beach_ability(ability)
    ranked = main.GameSimulator(board).rank_options()
    ability_result = next(result for result in ranked if result.option is ability)

    assert outcome.supported
    assert outcome.reachable_attack_id == main.NEBULA_BEAM
    assert outcome.reachable_damage == 180
    assert outcome.reachable_knockout
    assert outcome.reachable_prizes_taken == 1
    assert not outcome.reachable_wins_game
    assert outcome.recommended_target_id == main.MEGA_STARMIE_EX
    assert outcome.recommended_target_serial == 67
    assert outcome.damage == 0
    assert not outcome.knockout
    assert outcome.prizes_taken == 0
    assert not outcome.wins_game
    assert ability_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert ranked[0].option is ability

    weak = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=68, energies=[])
    board.bench = [weak, ready]
    board.all_my_pokemon = [board.active, weak, ready]
    entry = main.ImmediateOutcomeEvaluator(board).evaluate_surfing_beach_ability(ability)
    board._options = [switch_target_option(weak), switch_target_option(ready)]
    board.select.context = main.SelectContext.EFFECT_TARGET
    board.select.effect = SimpleNamespace(id=main.SURFING_BEACH)
    target_ranked = main.GameSimulator(board).rank_options()
    selected_target = board.option_target(target_ranked[0].option)
    selected_outcome = main.ImmediateOutcomeEvaluator(board).evaluate_switch_target(selected_target, "surfing_beach")
    assert selected_target.serial == entry.recommended_target_serial
    assert selected_outcome.reachable_attack_id == entry.reachable_attack_id
    assert selected_outcome.reachable_damage == entry.reachable_damage
    assert selected_outcome.reachable_knockout == entry.reachable_knockout
    assert selected_outcome.reachable_prizes_taken == entry.reachable_prizes_taken
    assert selected_outcome.reachable_wins_game == entry.reachable_wins_game

    for status in ("asleep", "paralyzed"):
        status_board, status_ability = beach_board(bench=[ready], target_hp=180)
        status_board.me.asleep = status == "asleep"
        status_board.me.paralyzed = status == "paralyzed"
        status_outcome = main.ImmediateOutcomeEvaluator(status_board).evaluate_surfing_beach_ability(status_ability)
        assert status_outcome.reachable_attack_id == main.NEBULA_BEAM
        assert status_outcome.reachable_knockout

    no_bench, no_bench_ability = beach_board(bench=[])
    no_bench_outcome = main.ImmediateOutcomeEvaluator(no_bench).evaluate_surfing_beach_ability(no_bench_ability)
    assert not no_bench_outcome.supported
    assert action_score_for_option(no_bench, no_bench_ability).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    non_water = pokemon(
        main.YVELTAL,
        hp=120,
        max_hp=120,
        serial=69,
        energies=[main.BASIC_DARK_ENERGY] * 3,
    )
    non_water_board, non_water_ability = beach_board(bench=[non_water], target_hp=100)
    non_water_outcome = main.ImmediateOutcomeEvaluator(non_water_board).evaluate_surfing_beach_ability(non_water_ability)
    assert not non_water_outcome.supported
    assert non_water_outcome.reachable_attack_id is None

    empty = pokemon(main.MEGA_STARMIE_EX, hp=330, max_hp=330, serial=70, energies=[])
    empty_board, empty_ability = beach_board(bench=[empty], target_hp=100)
    empty_outcome = main.ImmediateOutcomeEvaluator(empty_board).evaluate_surfing_beach_ability(empty_ability)
    assert empty_outcome.reachable_attack_id is None
    assert not empty_outcome.reachable_knockout
    assert action_score_for_option(empty_board, empty_ability).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    wall_ready = pokemon(
        main.MEGA_STARMIE_EX,
        hp=330,
        max_hp=330,
        serial=71,
        energies=[main.BASIC_WATER_ENERGY],
    )
    wall_board, wall_ability = beach_board(bench=[wall_ready], target_id=345, target_hp=40)
    wall_outcome = main.ImmediateOutcomeEvaluator(wall_board).evaluate_surfing_beach_ability(wall_ability)
    assert wall_outcome.reachable_attack_id is None
    assert not wall_outcome.reachable_knockout
    assert not wall_outcome.reachable_wins_game
    assert action_score_for_option(wall_board, wall_ability).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    first_turn, first_turn_ability = beach_board(
        bench=[ready],
        target_hp=180,
        turn=1,
        first_player=0,
    )
    first_turn_outcome = main.ImmediateOutcomeEvaluator(first_turn).evaluate_surfing_beach_ability(first_turn_ability)
    assert first_turn_outcome.reachable_attack_id is None
    assert not first_turn_outcome.reachable_knockout
    assert action_score_for_option(first_turn, first_turn_ability).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP

    direct_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    direct_ko_board, direct_ko_ability = beach_board(
        bench=[wall_ready],
        target_hp=40,
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[main.BASIC_WATER_ENERGY],
    )
    direct_ko_board._options = [direct_ko_ability, direct_attack]
    direct_ko_ranked = main.GameSimulator(direct_ko_board).rank_options()
    assert direct_ko_ranked[0].option is direct_attack
    assert action_score_for_option(direct_ko_board, direct_attack).tier == main.TIER_KO
    assert action_score_for_option(direct_ko_board, direct_ko_ability).tier == main.TIER_PRESERVE_WIN_OR_KO_PREP

    direct_win_board, direct_win_ability = beach_board(
        bench=[ready],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=40,
        prizes_left=2,
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[main.BASIC_WATER_ENERGY],
    )
    direct_win_board._options = [direct_win_ability, direct_attack]
    direct_win_ranked = main.GameSimulator(direct_win_board).rank_options()
    assert direct_win_ranked[0].option is direct_attack
    assert action_score_for_option(direct_win_board, direct_attack).tier == main.TIER_WIN
    assert action_score_for_option(direct_win_board, direct_win_ability).tier == main.TIER_PRESERVE_WIN_OR_KO_PREP

    other_stadium, other_ability = beach_board(bench=[ready], stadium_id=999999)
    other_outcome = main.ImmediateOutcomeEvaluator(other_stadium).evaluate_surfing_beach_ability(other_ability)
    assert not other_outcome.supported
    assert action_score_for_option(other_stadium, other_ability).tier != main.TIER_PRESERVE_WIN_OR_KO_PREP


def test_surfing_beach_ability_entry_replay_ranks_v8():
    win_board, _ = replay_board("参考ログ/v8/第2弾/88471771.json", 92, 1)
    win_ranked = main.GameSimulator(win_board).rank_options()
    win_result = next(result for result in win_ranked if result.option.type == main.OptionType.ABILITY)
    assert win_result.outcome.recommended_target_serial == 67
    assert win_result.outcome.reachable_attack_id == main.NEBULA_BEAM
    assert win_result.outcome.reachable_damage == 210
    assert win_result.outcome.reachable_knockout
    assert win_result.outcome.reachable_prizes_taken == 3
    assert win_result.outcome.reachable_wins_game
    assert win_result.outcome.damage == 0
    assert not win_result.outcome.knockout
    assert not win_result.outcome.wins_game
    assert win_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert win_ranked[0].option is win_result.option

    ko_board, _ = replay_board("参考ログ/v8/第2弾/88473355.json", 22, 0)
    ko_ranked = main.GameSimulator(ko_board).rank_options()
    ko_result = next(result for result in ko_ranked if result.option.type == main.OptionType.ABILITY)
    hero_result = next(
        result
        for result in ko_ranked
        if result.option.type == main.OptionType.ATTACH
        and ko_board.option_card(result.option) == main.HERO_CAPE
        and getattr(ko_board.option_target(result.option), "serial", None) == 11
    )
    assert ko_result.outcome.recommended_target_serial == 11
    assert ko_result.outcome.reachable_attack_id == main.RESENTFUL_REFRAIN
    assert ko_result.outcome.reachable_damage == 350
    assert ko_result.outcome.reachable_knockout
    assert ko_result.outcome.reachable_prizes_taken == 1
    assert not ko_result.outcome.reachable_wins_game
    assert ko_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert ko_ranked.index(ko_result) < ko_ranked.index(hero_result)
    assert ko_ranked[0].option is ko_result.option

    guard_board, _ = replay_board("参考ログ/v8/第2弾/88471771.json", 71, 1)
    guard_ranked = main.GameSimulator(guard_board).rank_options()
    guard_ability = next(result for result in guard_ranked if result.option.type == main.OptionType.ABILITY)
    guard_attack = next(
        result
        for result in guard_ranked
        if result.option.type == main.OptionType.ATTACK and result.outcome.knockout
    )
    assert guard_ability.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert guard_attack.action_score.tier == main.TIER_KO
    assert guard_ranked[0].option is guard_attack.option


def test_issue9_hero_cape_roi_target_and_current_lethal_guard():
    target_board, _ = replay_ct_board("参考ログ/v8/第2弾/88474425.json", 46)
    target_ranked = main.GameSimulator(target_board).rank_options()
    target_hero = next(
        result
        for result in target_ranked
        if result.option.type == main.OptionType.ATTACH
        and target_board.option_card(result.option) == main.HERO_CAPE
        and getattr(target_board.option_target(result.option), "serial", None) == 6
    )
    target_poffin = next(
        result
        for result in target_ranked
        if result.option.type == main.OptionType.PLAY
        and target_board.option_card(result.option) == main.POFIN
    )

    assert target_board.best_damage(target_board.opp_active) == 0
    assert target_board.hero_cape_target_roi(target_board.option_target(target_hero.option)) == "no_current_damage"
    assert target_hero.policy_score == -12000
    assert target_ranked.index(target_poffin) < target_ranked.index(target_hero)

    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    hero = attach_option(main.HERO_CAPE, None)
    poffin = play_option(main.POFIN)
    guard_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        target_id=main.MEGA_STARMIE_EX,
        target_hp=330,
        options=[hero, poffin, option(main.OptionType.END)],
    )
    hero.target = guard_board.active
    guard_board.active.hp = 150
    guard_board.opp_active.energyCards = [
        energy_card(water, 801),
        energy_card(dark, 802),
        energy_card(dark, 803),
    ]
    guard_ranked = main.GameSimulator(guard_board).rank_options()
    guard_hero = next(result for result in guard_ranked if result.option is hero)

    assert guard_board.best_damage(guard_board.opp_active) == 180
    assert guard_board.hero_cape_target_roi(guard_board.active) == "prevents_active_knockout"
    assert guard_hero.policy_score == 160000
    assert guard_ranked[0].option is hero

    extends_hero = attach_option(main.HERO_CAPE, None)
    extends_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        target_id=main.MEGA_YUKIMENOKO_EX,
        target_hp=330,
        options=[extends_hero, option(main.OptionType.END)],
    )
    extends_hero.target = extends_board.active
    extends_board.active.hp = 250
    extends_board.opp.handCount = 0
    extends_board.opp_active.energyCards = [
        energy_card(water, 811),
        energy_card(dark, 812),
        energy_card(dark, 813),
    ]
    extends_result = next(
        result
        for result in main.GameSimulator(extends_board).rank_options()
        if result.option is extends_hero
    )

    assert extends_board.best_damage(extends_board.opp_active) == 150
    assert extends_board.hero_cape_target_roi(extends_board.active) == "extends_active_survival"
    assert extends_result.policy_score == 43000
    assert 0 < extends_result.policy_score < guard_hero.policy_score

    unchanged_hero = attach_option(main.HERO_CAPE, None)
    unchanged_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        target_id=main.MEGA_YUKIMENOKO_EX,
        target_hp=330,
        options=[unchanged_hero, option(main.OptionType.END)],
    )
    unchanged_hero.target = unchanged_board.active
    unchanged_board.active.hp = 330
    unchanged_board.opp.handCount = 0
    unchanged_board.opp_active.energyCards = [
        energy_card(water, 821),
        energy_card(dark, 822),
        energy_card(dark, 823),
    ]
    unchanged_result = next(
        result
        for result in main.GameSimulator(unchanged_board).rank_options()
        if result.option is unchanged_hero
    )

    assert unchanged_board.best_damage(unchanged_board.opp_active) == 150
    assert unchanged_board.hero_cape_target_roi(unchanged_board.active) == "no_clear_benefit"
    assert unchanged_result.policy_score == -12000


def test_issue9_surfing_beach_play_roi_targets_and_guards():
    empty_board, _ = replay_ct_board("参考ログ/v8/第1弾/88489763.json", 9)
    empty_ranked = main.GameSimulator(empty_board).rank_options()
    empty_beaches = [
        result
        for result in empty_ranked
        if result.option.type == main.OptionType.PLAY
        and empty_board.option_card(result.option) == main.SURFING_BEACH
    ]

    assert len(empty_beaches) == 2
    assert all(result.policy_score == -12000 for result in empty_beaches)
    assert empty_ranked[0].option.type == main.OptionType.END

    overwrite_board, _ = replay_ct_board("参考ログ/v8/第1弾/88489763.json", 19)
    overwrite_ranked = main.GameSimulator(overwrite_board).rank_options()
    overwrite_beach = next(
        result
        for result in overwrite_ranked
        if result.option.type == main.OptionType.PLAY
        and overwrite_board.option_card(result.option) == main.SURFING_BEACH
    )
    current_stadium = overwrite_board.state.stadium[0]

    assert current_stadium.id == main.FULL_METAL_LAB
    assert current_stadium.playerIndex != overwrite_board.my_index
    assert overwrite_beach.policy_score == 42000
    assert overwrite_ranked[0].option is overwrite_beach.option

    water = main.BASIC_WATER_ENERGY
    dark = main.BASIC_DARK_ENERGY
    ready = pokemon(
        main.MEGA_STARMIE_EX,
        hp=280,
        max_hp=280,
        serial=741,
        energies=[water, dark, dark],
    )
    beach = play_option(main.SURFING_BEACH)
    ability_guard = FakeBoard(
        active_id=main.MEGA_YUKIMENOKO_EX,
        active_energies=[],
        bench=[ready],
        target_hp=180,
        prizes_left=3,
        options=[beach, option(main.OptionType.END)],
        effect_id=None,
        turn=3,
        first_player=0,
        your_index=0,
    )
    ability_guard.me = SimpleNamespace(asleep=True, paralyzed=False)
    ability_outcome = main.Policy(ability_guard).best_surfing_beach_play_outcome(beach)
    ability_ranked = main.GameSimulator(ability_guard).rank_options()
    beach_result = next(result for result in ability_ranked if result.option is beach)

    assert ability_outcome is not None
    assert ability_outcome.reachable_attack_id == main.NEBULA_BEAM
    assert ability_outcome.reachable_knockout
    assert beach_result.policy_score == 48000
    assert ability_ranked[0].option is beach
    assert not beach_result.outcome.supported
    assert beach_result.outcome.reachable_attack_id is None

    direct_outcome = main.ImmediateOutcomeEvaluator(ability_guard).evaluate_switch_target(
        ready,
        "surfing_beach",
    )
    ability_guard.state.stadiumPlayed = True
    unavailable_policy = main.Policy(ability_guard)

    assert direct_outcome.reachable_knockout
    assert unavailable_policy.best_surfing_beach_play_outcome(beach) is None
    assert unavailable_policy.score_surfing_beach_play(beach) == -12000

    ability_guard.state.stadiumPlayed = False
    ability_guard.state.stadium = [
        SimpleNamespace(id=main.SURFING_BEACH, playerIndex=ability_guard.my_index)
    ]
    same_stadium_policy = main.Policy(ability_guard)

    assert same_stadium_policy.best_surfing_beach_play_outcome(beach) is None
    assert same_stadium_policy.score_surfing_beach_play(beach) == -12000


def test_salvatore_structured_play_value_and_guards_v8():
    water = main.BASIC_WATER_ENERGY
    salvatore = play_option(main.SALVATORE)

    ko_board, _pokegear, _play_salvatore, chilly, end = pokegear_salvatore_chain_board(
        deck_ids=public_salvatore_deck(),
    )
    ko_board._options = [salvatore, chilly, end]
    ko_result = next(
        result
        for result in main.GameSimulator(ko_board).rank_options()
        if result.option is salvatore
    )
    assert ko_result.outcome.reachable_knockout
    assert not ko_result.outcome.reachable_wins_game
    assert ko_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP

    win_board, _pokegear, _play_salvatore, chilly, end = pokegear_salvatore_chain_board(
        deck_ids=public_salvatore_deck(),
    )
    win_board._prizes_left = 3
    win_board.me.prize = [None] * 3
    win_board._options = [salvatore, chilly, end]
    win_result = next(
        result
        for result in main.GameSimulator(win_board).rank_options()
        if result.option is salvatore
    )
    assert win_result.outcome.reachable_wins_game
    assert win_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP

    improvement_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[water],
        target_hp=300,
        deck_ids=[main.MEGA_STARMIE_EX, water, water],
        turn=3,
        first_player=0,
        your_index=0,
    )
    water_gun = option(main.OptionType.ATTACK, main.WATER_GUN)
    improvement_board._hand_ids = [main.SALVATORE]
    improvement_board._options = [salvatore, water_gun]
    improvement_ranked = main.GameSimulator(improvement_board).rank_options()
    improvement_result = next(result for result in improvement_ranked if result.option is salvatore)
    assert improvement_result.outcome.reachable_attack_id == main.JETTING_BLOW
    assert improvement_result.outcome.reachable_damage == 50
    assert improvement_result.outcome.improves_damage
    assert not improvement_result.outcome.reachable_knockout
    assert improvement_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert improvement_ranked[0].option is salvatore

    no_candidate_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        target_hp=300,
        deck_ids=[water, water],
        options=[salvatore, option(main.OptionType.ATTACK, main.JETTING_BLOW)],
    )
    no_candidate_board._hand_ids = [main.SALVATORE]
    no_candidate_ranked = main.GameSimulator(no_candidate_board).rank_options()
    no_candidate_result = next(result for result in no_candidate_ranked if result.option is salvatore)
    assert no_candidate_result.outcome.reachable_attack_id is None
    assert not no_candidate_result.outcome.completes_next_attacker
    assert no_candidate_result.action_score.tier != main.TIER_HIGH_VALUE_PREP
    assert no_candidate_ranked[0].option.attackId == main.JETTING_BLOW

    no_chain_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[],
        target_hp=300,
        deck_ids=[main.MEGA_STARMIE_EX, water],
        options=[salvatore, option(main.OptionType.END)],
    )
    no_chain_board._hand_ids = [main.SALVATORE]
    no_chain_result = next(
        result
        for result in main.GameSimulator(no_chain_board).rank_options()
        if result.option is salvatore
    )
    assert no_chain_result.outcome.reachable_attack_id is None
    assert not no_chain_result.outcome.completes_next_attacker
    assert no_chain_result.action_score.tier == main.TIER_LOW_VALUE_ACTION

    normal_evolve = evolve_option(main.MEGA_STARMIE_EX, no_chain_board.active)
    no_chain_board._options = [salvatore, normal_evolve, option(main.OptionType.END)]
    equivalent_ranked = main.GameSimulator(no_chain_board).rank_options()
    equivalent_salvatore = next(result for result in equivalent_ranked if result.option is salvatore)
    assert equivalent_salvatore.outcome.equivalent_evolution_available
    assert equivalent_salvatore.action_score.development == 0
    assert equivalent_ranked.index(
        next(result for result in equivalent_ranked if result.option is normal_evolve)
    ) < equivalent_ranked.index(equivalent_salvatore)

    bench_snorunt = pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=812, energies=[])
    salvatore_only_board = FakeBoard(
        active_id=main.HITODEMAN,
        active_energies=[water],
        bench=[bench_snorunt],
        target_hp=50,
        deck_ids=[main.MEGA_STARMIE_EX, water],
        turn=3,
        first_player=0,
        your_index=0,
    )
    unrelated_evolve = evolve_option(main.MEGA_YUKIMENOKO_EX, bench_snorunt)
    salvatore_only_board._hand_ids = [main.SALVATORE, main.MEGA_YUKIMENOKO_EX]
    salvatore_only_board._options = [salvatore, unrelated_evolve, water_gun]
    salvatore_only_ranked = main.GameSimulator(salvatore_only_board).rank_options()
    salvatore_only_result = next(result for result in salvatore_only_ranked if result.option is salvatore)
    assert salvatore_only_result.outcome.reachable_knockout
    assert salvatore_only_result.action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert salvatore_only_ranked[0].option is salvatore


def test_wally_structured_play_target_value_and_guards_v8():
    water = main.BASIC_WATER_ENERGY
    wally = play_option(main.WALLY_COMPASSION)
    jetting = option(main.OptionType.ATTACK, main.JETTING_BLOW)

    no_target_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        target_hp=300,
        options=[wally, jetting],
    )
    no_target_board._hand_ids = [main.WALLY_COMPASSION]
    no_target_ranked = main.GameSimulator(no_target_board).rank_options()
    no_target_result = next(result for result in no_target_ranked if result.option is wally)
    assert not no_target_result.outcome.supported
    assert no_target_result.action_score.tier != main.TIER_HIGH_VALUE_PREP
    assert no_target_ranked[0].option is jetting

    preservation_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water, water],
        target_hp=300,
        options=[wally, jetting],
    )
    preservation_board.active.hp = 40
    preservation_board.active.maxHp = 330
    preservation_board.opp_active = pokemon(
        main.CINDERACE,
        hp=300,
        max_hp=300,
        serial=920,
        energies=[main.IGNITION_ENERGY],
    )
    preservation_board.all_opp_pokemon = [preservation_board.opp_active]
    preservation_board._hand_ids = [main.WALLY_COMPASSION]
    preservation_ranked = main.GameSimulator(preservation_board).rank_options()
    preservation_result = next(result for result in preservation_ranked if result.option is wally)
    assert preservation_result.outcome.healed_damage == 290
    assert preservation_result.outcome.recovered_energy_count == 2
    assert preservation_result.outcome.board_energy_removed == 2
    assert preservation_result.outcome.next_knockout_avoided
    assert preservation_result.outcome.avoids_prize_loss
    assert preservation_result.outcome.prizes_preserved == 3
    assert preservation_result.outcome.avoids_board_out
    assert preservation_result.outcome.preserves_primary_pokemon
    assert preservation_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert preservation_result.action_score.immediate == 3
    assert preservation_result.action_score.pressure == 1
    assert preservation_result.action_score.development == 290
    assert preservation_result.action_score.resource == 2
    assert preservation_result.action_score.risk == 2
    assert preservation_ranked[0].option is wally

    low_value_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[],
        target_hp=300,
        options=[wally, jetting],
    )
    low_value_board.active.hp = 310
    low_value_board.active.maxHp = 330
    low_value_board._hand_ids = [main.WALLY_COMPASSION]
    low_value_ranked = main.GameSimulator(low_value_board).rank_options()
    low_value_result = next(result for result in low_value_ranked if result.option is wally)
    assert low_value_result.outcome.healed_damage == 20
    assert not main.wally_preservation_fact_is_high_value(low_value_result.outcome)
    assert low_value_result.action_score.tier == main.TIER_LOW_VALUE_ACTION

    direct_ko_board = preservation_board
    direct_ko_board.opp_active.hp = 50
    direct_ko_board._prizes_left = 6
    direct_ko_board.me.prize = [None] * 6
    direct_ko_ranked = main.GameSimulator(direct_ko_board).rank_options()
    assert direct_ko_ranked[0].option is jetting
    assert direct_ko_ranked[0].action_score.tier == main.TIER_KO

    direct_win_board = preservation_board
    direct_win_board._prizes_left = 1
    direct_win_board.me.prize = [None]
    direct_win_ranked = main.GameSimulator(direct_win_board).rank_options()
    assert direct_win_ranked[0].option is jetting
    assert direct_win_ranked[0].action_score.tier == main.TIER_WIN

    active_target = pokemon(
        main.MEGA_STARMIE_EX,
        hp=210,
        max_hp=330,
        serial=930,
        energies=[water],
    )
    bench_target = pokemon(
        main.MEGA_YUKIMENOKO_EX,
        hp=90,
        max_hp=310,
        serial=931,
        energies=[water, water],
    )
    target_board = FakeBoard(
        active_id=main.MEGA_STARMIE_EX,
        active_energies=[water],
        bench=[bench_target],
        options=[wally],
    )
    target_board.active = active_target
    target_board.all_my_pokemon = [active_target, bench_target]
    target_board._hand_ids = [main.WALLY_COMPASSION]
    play_outcome = main.ImmediateOutcomeEvaluator(target_board).evaluate_wally_play(wally)
    assert play_outcome.recommended_target_serial == bench_target.serial

    active_option = switch_target_option(active_target)
    bench_option = switch_target_option(bench_target)
    target_board._options = [active_option, bench_option]
    target_board.select.context = main.SelectContext.HEAL
    target_board.select.effect = SimpleNamespace(id=main.WALLY_COMPASSION)
    target_ranked = main.GameSimulator(target_board).rank_options()
    assert target_ranked[0].option is bench_option
    assert target_board.option_target(target_ranked[0].option).serial == play_outcome.recommended_target_serial
    for result in target_ranked:
        fact = main.ImmediateOutcomeEvaluator(target_board).evaluate_wally_target(
            target_board.option_target(result.option)
        )
        if main.wally_preservation_fact_is_high_value(fact):
            assert result.action_score.development == fact.healed_damage
            assert result.action_score.resource == fact.recovered_energy_count
            assert result.action_score.risk == fact.board_energy_removed
        else:
            assert result.action_score.development == 0
            assert result.action_score.resource == 0
            assert result.action_score.risk == 0

    target_board._options = [bench_option]
    single_target_ranked = main.GameSimulator(target_board).rank_options()
    assert len(single_target_ranked) == 1
    assert single_target_ranked[0].option is bench_option
    assert single_target_ranked[0].outcome.supported


def test_low_value_wally_uses_legacy_only_with_replay_guards_v8():
    cases = (
        ("参考ログ/v8/第1弾/88487636.json", 63, main.OptionType.EVOLVE, None, 30, 1),
        ("参考ログ/v8/第1弾/88487636.json", 64, main.OptionType.PLAY, main.TANKER, 30, 1),
        ("参考ログ/v8/第1弾/88478712.json", 85, main.OptionType.PLAY, main.ENERGY_SWITCH, 60, 1),
        ("参考ログ/v8/第1弾/88478712.json", 88, None, None, 60, 0),
    )

    for path, step, expected_type, expected_card, healed_damage, recovered_energy in cases:
        board, _next_action = replay_board(path, step, 0)
        ranked = main.GameSimulator(board).rank_options()
        wally_results = [
            result
            for result in ranked
            if result.option.type == main.OptionType.PLAY
            and board.option_card(result.option) == main.WALLY_COMPASSION
        ]

        assert wally_results
        if expected_type is not None:
            assert ranked[0].option.type == expected_type
            if expected_card is not None:
                assert board.option_card(ranked[0].option) == expected_card

        for result in wally_results:
            assert result.action_score.tier == main.TIER_LOW_VALUE_ACTION
            assert result.action_score.development == 0
            assert result.action_score.resource == 0
            assert result.action_score.risk == 0
            assert result.outcome.healed_damage == healed_damage
            assert result.outcome.recovered_energy_count == recovered_energy
            assert result.outcome.board_energy_removed == recovered_energy
            assert result.outcome.recommended_target_id is not None
            assert result.outcome.recommended_target_serial is not None

        if step == 88:
            end_result = next(result for result in ranked if result.option.type == main.OptionType.END)
            assert end_result.action_score.tier == main.TIER_LOW_VALUE_ACTION
            assert end_result.action_score.development == 0
            assert end_result.action_score.resource == 0
            assert end_result.action_score.risk == 0
            assert all(result.action_score.legacy < end_result.action_score.legacy for result in wally_results)


def night_stretcher_board(
    *,
    active=None,
    bench=None,
    hand=None,
    discard=None,
    options=None,
    energy_attached=False,
    prizes_left=6,
    target_hp=100,
):
    active = active or pokemon(main.CINDERACE, hp=140, max_hp=140, serial=10)
    bench = list(bench or [])
    hand = list(hand or [])
    discard = list(discard or [])
    options = list(options or [])
    me = SimpleNamespace(
        active=[active],
        bench=bench,
        benchMax=5,
        hand=hand,
        discard=discard,
        prize=[None] * prizes_left,
        deckCount=40,
        asleep=False,
        paralyzed=False,
        handCount=len(hand),
    )
    opponent = SimpleNamespace(
        active=[pokemon(999, hp=target_hp, max_hp=max(100, target_hp), serial=20)],
        bench=[],
        benchMax=5,
        hand=[],
        discard=[],
        prize=[None] * 6,
        deckCount=40,
        asleep=False,
        paralyzed=False,
        handCount=0,
    )
    select = SimpleNamespace(
        option=options,
        context=main.SelectContext.MAIN,
        effect=None,
        contextCard=None,
        deck=None,
        minCount=1,
        maxCount=1,
        remainEnergyCost=0,
        remainDamageCounter=0,
        type=None,
    )
    current = SimpleNamespace(
        players=[me, opponent],
        yourIndex=0,
        firstPlayer=1,
        turn=3,
        energyAttached=energy_attached,
        supporterPlayed=False,
        retreated=False,
        stadium=None,
        looking=[],
    )
    return main.BoardView(SimpleNamespace(select=select, current=current, logs=[]))


def test_night_stretcher_recovery_facts_issue6():
    tanker = play_option(main.TANKER)

    no_target = night_stretcher_board(options=[tanker])
    no_target_facts = no_target.night_stretcher_recovery_facts()
    assert not no_target_facts

    hand_cinderace = energy_card(main.CINDERACE, 90)
    discarded_cinderace = energy_card(main.CINDERACE, 83)
    hand_only = night_stretcher_board(
        hand=[hand_cinderace],
        discard=[discarded_cinderace],
        options=[tanker],
    )
    hand_only_fact = hand_only.night_stretcher_recovery_facts()[0]
    assert hand_only_fact.returns_to_hand_only
    assert not hand_only_fact.same_turn_usable

    water = energy_card(main.BASIC_WATER_ENERGY, 114)
    attack_ready = night_stretcher_board(discard=[water], options=[tanker])
    attack_fact = attack_ready.night_stretcher_recovery_facts()[0]
    assert attack_fact.same_turn_attach_available
    assert attack_fact.same_turn_attack_gap_reduced
    assert attack_fact.same_turn_attack_enabled
    assert not attack_fact.returns_to_hand_only

    next_attacker = pokemon(
        main.MEGA_STARMIE_EX,
        hp=280,
        max_hp=280,
        serial=30,
        energies=[main.BASIC_WATER_ENERGY],
    )
    next_ready = night_stretcher_board(
        active=pokemon(
            main.CINDERACE,
            hp=140,
            max_hp=140,
            serial=10,
            energies=[main.BASIC_WATER_ENERGY],
        ),
        bench=[next_attacker],
        discard=[water],
        options=[tanker],
    )
    next_fact = next_ready.night_stretcher_recovery_facts()[0]
    assert next_fact.next_attacker_gap_reduced
    assert not next_fact.returns_to_hand_only

    future_froslass = energy_card(main.MEGA_YUKIMENOKO_EX, 12)
    future_evolution = night_stretcher_board(
        bench=[
            pokemon(
                main.YUKIWARASHI,
                hp=70,
                max_hp=70,
                serial=31,
                appear_this_turn=True,
            )
        ],
        discard=[future_froslass],
        options=[tanker],
        energy_attached=True,
    )
    evolution_fact = future_evolution.night_stretcher_recovery_facts()[0]
    assert evolution_fact.next_turn_evolution_supported
    assert not evolution_fact.same_turn_usable
    assert not evolution_fact.returns_to_hand_only

    board_out_basic = energy_card(main.YUKIWARASHI, 32)
    board_out = night_stretcher_board(
        active=pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=10),
        discard=[board_out_basic],
        options=[tanker],
    )
    board_out_fact = board_out.night_stretcher_recovery_facts()[0]
    assert board_out_fact.board_out_avoided
    assert board_out_fact.same_turn_usable
    assert not board_out_fact.returns_to_hand_only


def test_night_stretcher_paid_retreat_fact_issue6():
    board, _next_action = replay_board("参考ログ/v8/第2弾/88471771.json", 92, 1)
    candidate = main.Policy(board).recommended_night_stretcher_candidate()
    assert candidate is not None
    assert candidate.target_id == main.BASIC_WATER_ENERGY
    assert candidate.target_serial == 113
    assert candidate.same_turn_attach_available
    assert candidate.same_turn_retreat_enabled
    assert not candidate.returns_to_hand_only


def test_night_stretcher_structured_action_score_issue6():
    hand_only_play = play_option(main.TANKER)
    hand_only = night_stretcher_board(
        active=pokemon(
            main.MEGA_STARMIE_EX,
            hp=280,
            max_hp=280,
            serial=10,
            energies=[main.BASIC_WATER_ENERGY],
        ),
        hand=[energy_card(main.CINDERACE, 90)],
        discard=[energy_card(main.CINDERACE, 83)],
        options=[hand_only_play, option(main.OptionType.ATTACK, main.JETTING_BLOW)],
    )
    hand_only_ranked = main.GameSimulator(hand_only).rank_options()
    hand_only_result = next(result for result in hand_only_ranked if result.option is hand_only_play)
    assert hand_only_result.action_score.tier == main.TIER_BLOCKED_OR_BAD_ACTION
    assert hand_only_result.action_score.development == 0
    assert hand_only_result.action_score.resource == 1
    assert hand_only_result.action_score.legacy == -83
    assert hand_only_ranked[0].option.type == main.OptionType.ATTACK

    useful_play = play_option(main.TANKER)
    useful = night_stretcher_board(
        discard=[energy_card(main.BASIC_WATER_ENERGY, 114)],
        options=[useful_play, option(main.OptionType.END)],
    )
    useful_ranked = main.GameSimulator(useful).rank_options()
    useful_result = next(result for result in useful_ranked if result.option is useful_play)
    assert useful_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert useful_result.action_score.development > 0
    assert useful_result.action_score.resource == 0
    assert useful_result.action_score.legacy == -114
    assert useful_ranked[0].option is useful_play

    no_target_play = play_option(main.TANKER)
    no_target = night_stretcher_board(options=[no_target_play, option(main.OptionType.END)])
    no_target_result = next(
        result
        for result in main.GameSimulator(no_target).rank_options()
        if result.option is no_target_play
    )
    assert no_target_result.policy_score == -8000
    assert no_target_result.action_score.tier == main.TIER_BLOCKED_OR_BAD_ACTION
    assert no_target_result.action_score.development == 0
    assert no_target_result.action_score.resource == 0

    for prizes_left, expected_tier in (
        (2, main.TIER_KO),
        (1, main.TIER_WIN),
    ):
        night_play = play_option(main.TANKER)
        direct_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
        direct = night_stretcher_board(
            active=pokemon(
                main.MEGA_STARMIE_EX,
                hp=280,
                max_hp=280,
                serial=10,
                energies=[main.BASIC_WATER_ENERGY],
            ),
            discard=[energy_card(main.BASIC_WATER_ENERGY, 114)],
            options=[night_play, direct_attack],
            prizes_left=prizes_left,
            target_hp=50,
        )
        ranked = main.GameSimulator(direct).rank_options()
        assert ranked[0].option is direct_attack
        assert ranked[0].action_score.tier == expected_tier


def test_night_stretcher_play_select_alignment_targets_issue6():
    cases = (
        ("参考ログ/v8/第1弾/88460902.json", 50, 51, 1, main.BASIC_WATER_ENERGY, 115, main.CINDERACE, 83),
        ("参考ログ/v8/第1弾/88487636.json", 85, 86, 0, main.MEGA_YUKIMENOKO_EX, 12, main.BASIC_WATER_ENERGY, 58),
        ("参考ログ/v8/第2弾/88467945.json", 158, 159, 1, main.MEGA_YUKIMENOKO_EX, 72, main.BASIC_WATER_ENERGY, 116),
        ("参考ログ/v8/第2弾/88468549.json", 76, 77, 0, main.YUKIWARASHI, 9, main.BASIC_WATER_ENERGY, 59),
    )
    for path, play_step, select_step, player, expected_id, expected_serial, bad_id, bad_serial in cases:
        play_board, _ = replay_board(path, play_step, player)
        play_policy = main.Policy(play_board)
        play_candidate = play_policy.recommended_night_stretcher_candidate()
        assert play_candidate is not None
        assert (play_candidate.target_id, play_candidate.target_serial) == (expected_id, expected_serial)

        select_board, _ = replay_board(path, select_step, player)
        select_ranked = main.GameSimulator(select_board).rank_options()
        selected = select_ranked[0]
        selected_candidate = main.Policy(select_board).night_stretcher_candidate_for_option(selected.option)
        assert selected_candidate is not None
        assert (selected_candidate.target_id, selected_candidate.target_serial) == (expected_id, expected_serial)
        assert (selected_candidate.target_id, selected_candidate.target_serial) == (
            play_candidate.target_id,
            play_candidate.target_serial,
        )

        bad_result = next(
            result
            for result in select_ranked
            if (
                main.Policy(select_board).night_stretcher_candidate_for_option(result.option).target_id,
                main.Policy(select_board).night_stretcher_candidate_for_option(result.option).target_serial,
            )
            == (bad_id, bad_serial)
        )
        bad_candidate = main.Policy(select_board).night_stretcher_candidate_for_option(bad_result.option)
        assert bad_candidate is not None
        assert bad_candidate.returns_to_hand_only
        assert bad_result.action_score.tier == main.TIER_BLOCKED_OR_BAD_ACTION
        assert bad_result.action_score.development == 0
        assert bad_result.action_score.resource == 1
        assert bad_result.action_score.legacy == -bad_serial

    duplicate_play, _ = replay_board("参考ログ/v8/第1弾/88460902.json", 92, 1)
    duplicate_select, _ = replay_board("参考ログ/v8/第1弾/88460902.json", 93, 1)
    duplicate_play_candidate = main.Policy(duplicate_play).recommended_night_stretcher_candidate()
    duplicate_select_result = main.GameSimulator(duplicate_select).rank_options()[0]
    duplicate_select_candidate = main.Policy(
        duplicate_select
    ).night_stretcher_candidate_for_option(duplicate_select_result.option)
    assert duplicate_play_candidate is not None
    assert duplicate_select_candidate is not None
    assert (
        duplicate_play_candidate.target_id,
        duplicate_play_candidate.target_serial,
    ) == (
        duplicate_select_candidate.target_id,
        duplicate_select_candidate.target_serial,
    )


def test_night_stretcher_minimal_rework_tier_guards_issue6():
    bench_only_play = play_option(main.TANKER)
    bench_only = night_stretcher_board(
        active=pokemon(
            main.MEGA_STARMIE_EX,
            hp=280,
            max_hp=280,
            serial=10,
            energies=[main.BASIC_WATER_ENERGY],
        ),
        bench=[pokemon(main.SHAYMIN, hp=70, max_hp=70, serial=30)],
        discard=[energy_card(main.YUKIWARASHI, 32)],
        options=[bench_only_play],
    )
    bench_only_candidate = main.Policy(bench_only).recommended_night_stretcher_candidate()
    bench_only_result = main.GameSimulator(bench_only).rank_options()[0]
    assert bench_only_candidate is not None
    assert bench_only_candidate.same_turn_usable
    assert not bench_only_candidate.board_out_avoided
    assert not bench_only_candidate.same_turn_attack_enabled
    assert not bench_only_candidate.same_turn_retreat_enabled
    assert not bench_only_candidate.next_attacker_completed
    assert not bench_only_candidate.returns_to_hand_only
    assert bench_only_result.action_score.tier == main.TIER_LOW_VALUE_ACTION

    future_play = play_option(main.TANKER)
    current_attack = option(main.OptionType.ATTACK, main.JETTING_BLOW)
    future_evolution = night_stretcher_board(
        active=pokemon(
            main.MEGA_STARMIE_EX,
            hp=280,
            max_hp=280,
            serial=10,
            energies=[main.BASIC_WATER_ENERGY],
        ),
        bench=[
            pokemon(
                main.YUKIWARASHI,
                hp=70,
                max_hp=70,
                serial=31,
                appear_this_turn=True,
            )
        ],
        discard=[energy_card(main.MEGA_YUKIMENOKO_EX, 12)],
        options=[future_play, current_attack],
    )
    future_policy = main.Policy(future_evolution)
    future_candidate = future_policy.recommended_night_stretcher_candidate()
    future_ranked = main.GameSimulator(future_evolution).rank_options()
    future_result = next(result for result in future_ranked if result.option is future_play)
    assert future_candidate is not None
    assert future_candidate.next_turn_evolution_supported
    assert not future_candidate.same_turn_usable
    assert not future_policy.night_stretcher_is_concrete_same_turn(future_candidate)
    assert future_result.action_score.tier == main.TIER_LOW_VALUE_ACTION
    assert future_ranked[0].option is current_attack

    duplicate_play = play_option(main.TANKER)
    duplicate_basic = night_stretcher_board(
        active=pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=10),
        bench=[pokemon(main.YUKIWARASHI, hp=70, max_hp=70, serial=31)],
        discard=[energy_card(main.YUKIWARASHI, 32)],
        options=[duplicate_play],
    )
    duplicate_policy = main.Policy(duplicate_basic)
    duplicate_candidate = duplicate_policy.recommended_night_stretcher_candidate()
    duplicate_result = main.GameSimulator(duplicate_basic).rank_options()[0]
    assert duplicate_candidate is not None
    assert duplicate_candidate.same_turn_usable
    assert not duplicate_candidate.board_out_avoided
    assert not duplicate_policy.night_stretcher_is_concrete_same_turn(duplicate_candidate)
    assert duplicate_result.action_score.tier == main.TIER_LOW_VALUE_ACTION

    board_out_play = play_option(main.TANKER)
    board_out = night_stretcher_board(
        active=pokemon(main.MEGA_STARMIE_EX, hp=280, max_hp=280, serial=10),
        discard=[energy_card(main.YUKIWARASHI, 32)],
        options=[board_out_play],
    )
    board_out_policy = main.Policy(board_out)
    board_out_candidate = board_out_policy.recommended_night_stretcher_candidate()
    board_out_result = main.GameSimulator(board_out).rank_options()[0]
    assert board_out_candidate is not None
    assert board_out_candidate.same_turn_usable
    assert board_out_candidate.board_out_avoided
    assert board_out_policy.night_stretcher_is_concrete_same_turn(board_out_candidate)
    assert board_out_result.action_score.tier == main.TIER_HIGH_VALUE_PREP


def test_night_stretcher_useful_replay_guards_issue6():
    turbo_board, _ = replay_board("参考ログ/v8/第1弾/88476546.json", 12, 1)
    turbo_ranked = main.GameSimulator(turbo_board).rank_options()
    turbo_result = next(
        result
        for result in turbo_ranked
        if result.option.type == main.OptionType.PLAY
        and turbo_board.option_card(result.option) == main.TANKER
    )
    turbo_candidate = main.Policy(turbo_board).recommended_night_stretcher_candidate()
    assert turbo_candidate is not None
    assert turbo_candidate.same_turn_attack_enabled
    assert turbo_candidate.target_id == main.BASIC_WATER_ENERGY
    assert turbo_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert turbo_ranked[0].option is turbo_result.option

    win_board, _ = replay_board("参考ログ/v8/第2弾/88471771.json", 92, 1)
    win_ranked = main.GameSimulator(win_board).rank_options()
    night_result = next(
        result
        for result in win_ranked
        if result.option.type == main.OptionType.PLAY
        and win_board.option_card(result.option) == main.TANKER
    )
    assert night_result.action_score.tier == main.TIER_HIGH_VALUE_PREP
    assert win_ranked[0].action_score.tier == main.TIER_PRESERVE_WIN_OR_KO_PREP
    assert win_ranked.index(night_result) > 0

    evolution_board, _ = replay_board("参考ログ/v8/第2弾/88465210.json", 12, 0)
    evolution_candidate = main.Policy(evolution_board).recommended_night_stretcher_candidate()
    evolution_result = main.GameSimulator(evolution_board).rank_options()[0]
    assert evolution_candidate is not None
    assert evolution_candidate.next_turn_evolution_supported
    assert not evolution_candidate.same_turn_usable
    assert evolution_result.outcome.reachable_attack_id is None
    assert evolution_result.action_score.tier == main.TIER_LOW_VALUE_ACTION
    assert evolution_result.action_score.development == 1


if __name__ == "__main__":
    test_energy_payment_rules()
    test_attack_outcomes_and_policy_guards()
    test_attach_outcomes()
    test_boss_outcomes()
    test_boss_play_reachable_ko_rank_rules()
    test_boss_play_reachable_engine_ko_rank_rules()
    test_boss_play_reachable_win_and_wall_rank_rules()
    test_boss_play_negative_guards()
    test_boss_attack_declaration_guards_fact_policy_and_rank()
    test_boss_play_target_selection_matches_boss_context()
    test_boss_play_direct_attack_guards()
    test_replay_88489763_step96_boss_play_rank()
    test_replay_88477647_step83_boss_play_rank()
    test_tool_scrapper_outcomes()
    test_retreat_and_switch_outcomes()
    test_cinderace_receiver_handoff_issue7()
    test_attack_effect_target_outcomes()
    test_discard_cost_priority()
    test_main_axis_evolve_priority()
    test_salvatore_live_and_target_priority()
    test_game_simulator_candidate_ordering()
    test_structured_action_score_phase1()
    test_attack_pressure_issue4()
    test_play_fact_helpers_issue3a()
    test_play_fact_connected_scoring_issue3b()
    test_crispin_fact_required_energy_issue3b1()
    test_role_facts_issue3c()
    test_active_attach_reachable_attack_p0_statusless_win()
    test_active_attach_reachable_attack_p0_asleep_blocks_reachable()
    test_active_attach_reachable_attack_p0_paralyzed_blocks_reachable()
    test_active_attach_reachable_attack_p0_first_player_turn_one_blocks_reachable()
    test_active_attach_reachable_attack_p0_second_player_first_turn_reachable()
    test_active_attach_reachable_attack_p0_first_player_later_turn_reachable()
    test_active_attach_reachable_attack_p0_already_legal_guard()
    test_active_attack_declare_turn_rule_call_sites_p0()
    test_active_attack_declare_turn_rule_policy_regressions_p0()
    test_active_attach_reachable_attack_p0_blocked_guard()
    test_active_attach_reachable_attack_p0_bench_guard()
    test_active_attach_reachable_attack_p0_multiple_attack_best_choice()
    test_active_attach_reachable_attack_p0_other_card_guard()
    test_bench_attach_same_turn_access_p1_surfing_beach_ko()
    test_bench_attach_same_turn_access_p1_surfing_beach_win()
    test_bench_attach_same_turn_access_p1_missing_access_guard()
    test_bench_attach_same_turn_access_p1_blocked_guard()
    test_bench_attach_same_turn_access_p1_direct_ko_guard()
    test_retreat_ready_attacker_same_turn_access_p1()
    test_rework_bench_attach_access_does_not_inherit_other_bench_ko()
    test_rework_active_attach_first_retreat_access_still_reaches_ready_bench_ko()
    test_rework_attach_boss_attack_declare_guard()
    test_rework_attach_boss_existing_availability_guards()
    test_rework_status_blocks_normal_retreat_access()
    test_rework_surfing_beach_status_allows_legal_switch_target_attack()
    test_rework_attach_surfing_status_requires_surfing_option()
    test_l1_paid_retreat_energy_ledger_allows_reachable_after_attach()
    test_l1_paid_retreat_energy_ledger_blocks_unpayable_retreat_chain()
    test_l1_free_retreat_and_surfing_beach_have_no_energy_loss()
    test_l1_energy_switch_moves_energy_to_active_without_board_mutation()
    test_l1_energy_switch_no_source_energy_no_promotion()
    test_energy_switch_redundant_attach_route_loses_to_direct_bench_attach()
    test_energy_switch_redundant_attach_route_generalizes_beyond_snorunt()
    test_energy_switch_only_win_is_not_suppressed()
    test_issue8_starmie_demand_without_same_turn_gain_is_not_real_development()
    test_issue8_energy_switch_newly_unlocked_attack_keeps_value()
    test_l4_attach_boss_prize_attack_reachable()
    test_l4_attach_boss_requires_boss_available_and_unused_supporter()
    test_replay_87482904_t11_t13_energy_ledger()
    test_replay_87482904_t15_energy_ledger()
    test_replay_87491060_t9_retreat_ready_attacker_energy_ledger()
    test_replay_87488357_t19_energy_switch_ledger()
    test_replay_87482904_t11_t13_l2_attach_retreat_attack_rank()
    test_replay_87482904_t15_l2_three_prize_rank()
    test_replay_87491060_t9_l3_retreat_ready_attacker_rank()
    test_replay_87637402_t13_l4_attach_boss_prize_rank()
    test_replay_87488357_t19_l5_energy_switch_prize_rank()
    test_meaningless_retreat_supported_does_not_override_policy_legacy()
    test_low_damage_utility_retreat_residual_depends_on_policy_score()
    test_ignition_retreat_ko_chain_remains_above_end()
    test_non_retreat_outcome_priority_is_not_overridden_by_legacy()
    test_active_attach_reachable_pressure_replay_rank_rules()
    test_active_attach_reachable_pressure_direct_ko_and_win_guards()
    test_active_attach_reachable_pressure_guards_and_froslass_hand_count()
    test_l6_zero_damage_attack_loses_to_confirmed_chain_but_is_not_forbidden()
    test_l7_rank_contract_direct_ko_before_reachable_chain()
    test_l8_public_same_board_same_rank_and_common_guards()
    test_pokegear_salvatore_chain_replay_88272517_t4_rank()
    test_pokegear_salvatore_candidate_chain_is_definite_after_search()
    test_salvatore_play_chain_reaches_froslass_attack_ko()
    test_salvatore_target_chain_uses_existing_evolution_attack_facts()
    test_pokegear_salvatore_chain_negative_guards()
    test_deck_counts_after_judge_suguri_update()
    test_judge_play_rank_rules()
    test_suguri_play_rank_rules()
    test_suguri_switch_target_rank_rules()
    test_pokegear_salvatore_chain_direct_ko_and_low_probability_guards()
    test_salvatore_effect_resolution_keeps_chain_after_supporter_played()
    test_salvatore_requires_evolution_card_in_deck_not_only_hand()
    test_pokegear_probability_accounts_for_unknown_prizes()
    test_salvatore_text_allows_this_turn_pokemon_target_chain()
    test_salvatore_first_player_first_turn_does_not_claim_same_turn_attack()
    test_salvatore_evolution_candidate_reaches_attack_outcome()
    test_pokegear_expected_chain_competes_with_strong_non_ko_attack()
    test_pokegear_salvatore_chain_additional_failure_guards()
    test_pokegear_chain_probability_fixed_literal_value()
    test_pokegear_chain_probability_matches_small_bruteforce()
    test_pokegear_expected_chain_values_are_multiplied_once()
    test_remaining_possible_ignores_opponent_cards_for_own_deck()
    test_salvatore_public_deck_without_evolution_has_no_certain_chain()
    test_salvatore_public_deck_with_evolution_has_certain_chain()
    test_salvatore_nonpublic_evolution_one_copy_returns_expected_not_certain()
    test_salvatore_chain_contexts_do_not_claim_energy_insufficient_or_wall()
    test_pokegear_uses_chain_probability_below_salvatore_hit_only()
    test_pokegear_chain_probability_boundary_does_not_raise_tier40()
    test_active_evolution_reachable_attack_beats_expected_pokegear_v8()
    test_active_evolution_reachable_win_stays_below_direct_win_attack_v8()
    test_active_evolution_reachable_ko_stays_below_direct_ko_attack_v8()
    test_active_evolution_reachable_attack_negative_guards_v8()
    test_replay_88493411_active_evolution_rank_v8()
    test_surfing_beach_ability_entry_outcome_and_guards()
    test_surfing_beach_ability_entry_replay_ranks_v8()
    test_issue9_hero_cape_roi_target_and_current_lethal_guard()
    test_issue9_surfing_beach_play_roi_targets_and_guards()
    test_salvatore_structured_play_value_and_guards_v8()
    test_wally_structured_play_target_value_and_guards_v8()
    test_low_value_wally_uses_legacy_only_with_replay_guards_v8()
    test_night_stretcher_recovery_facts_issue6()
    test_night_stretcher_paid_retreat_fact_issue6()
    test_night_stretcher_structured_action_score_issue6()
    test_night_stretcher_play_select_alignment_targets_issue6()
    test_night_stretcher_minimal_rework_tier_guards_issue6()
    test_night_stretcher_useful_replay_guards_issue6()
    print("immediate outcome tests OK")

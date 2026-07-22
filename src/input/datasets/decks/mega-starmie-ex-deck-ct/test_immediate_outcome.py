from types import SimpleNamespace
from itertools import permutations

import main


def attack(attack_id, damage, energies=()):
    return SimpleNamespace(attackId=attack_id, damage=damage, energies=list(energies))


def energy_card(card_id, serial):
    return SimpleNamespace(id=card_id, serial=serial)


def pokemon(card_id, hp=100, max_hp=100, serial=1, energies=()):
    return SimpleNamespace(
        id=card_id,
        hp=hp,
        maxHp=max_hp,
        serial=serial,
        energyCards=[energy_card(card_id, index) for index, card_id in enumerate(energies, start=1)],
        tools=[],
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
        self.state = SimpleNamespace(supporterPlayed=False)
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
        tokens = []
        data = self.data(self.pid(target))
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
        return "GENERAL"

    def opponent_has_bench_damage_threat(self):
        return main.BoardView.opponent_has_bench_damage_threat(self)

    def card_evolves_from_card(self, evolution_id, base_id):
        return main.BoardView.card_evolves_from_card(self, evolution_id, base_id)

    def evolves_from(self, evolution_id, target):
        return main.BoardView.evolves_from(self, evolution_id, target)

    def remaining_possible(self, card_id, total=None):
        if self.deck_view:
            return card_id in self.deck_ids
        total = main.DECK.count(card_id) if total is None else total
        known_out = self.hand_ids.count(card_id) + self.discard_ids.count(card_id)
        known_out += sum(1 for pokemon in self.all_my_pokemon if self.pid(pokemon) == card_id)
        known_out += sum(1 for pokemon in self.all_opp_pokemon if self.pid(pokemon) == card_id)
        return known_out < total

    def salvatore_target_evolution(self, target):
        return main.BoardView.salvatore_target_evolution(self, target)

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
        return False

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
    assert policy_for(turbo_without_receiver_or_pokegear).score_attack(turbo) < policy_for(turbo_without_receiver_or_pokegear).score_play(play_option(main.SURFING_BEACH))


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
    assert policy_for(board).score_switch_target(ready_starmie) < 0
    assert policy_for(board).score_retreat(retreat) == main.SCORE_FORBIDDEN

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
    assert salvatore_ranked[0].option.cardId == main.SALVATORE
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
    assert ranked(salvatore_board)[0].option.cardId == main.SALVATORE
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
    assert top_option(board).cardId == main.SALVATORE

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


if __name__ == "__main__":
    test_energy_payment_rules()
    test_attack_outcomes_and_policy_guards()
    test_attach_outcomes()
    test_boss_outcomes()
    test_tool_scrapper_outcomes()
    test_retreat_and_switch_outcomes()
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
    print("immediate outcome tests OK")

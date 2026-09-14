---
name: agent-api
description: Reference for writing the Pokémon TCG agent's decision logic — the agent() return contract, the Observation/SelectData/Option/State data model, and how to read options by type. Use when implementing or modifying main.py's agent(), interpreting an Observation, or choosing option indices.
---

# agent-api

Decision-relevant summary of `src/input/datasets/decks/starmie-aggro/cg/api.py`
(`cg/api.py` is byte-identical across deck directories). Open that file
for full enum members and field lists; this is the orientation. Assume enums/dataclasses may
gain members during the competition — handle unknown values gracefully.

## Return contract

`agent(obs_dict: dict) -> list[int]`. Convert with
`obs = to_observation_class(obs_dict)`.

- If `obs.select is None`: it's the initial deck selection — return a `list[int]` of 60
  card IDs (the deck).
- Otherwise return **indices into `obs.select.option`** satisfying:
  `minCount <= len(result) <= maxCount`, each index in `[0, len(option))`, no duplicates.
  `maxCount` never exceeds `len(option)`.

## SelectData (`obs.select`)

What you're being asked to choose:
- `type: SelectType` — the kind of selection (MAIN, CARD, ENERGY, ATTACK, COUNT, YES_NO, …).
- `context: SelectContext` — the specific intent (e.g. `SETUP_ACTIVE_POKEMON`, `SWITCH`,
  `DISCARD`, `ATTACK`, `IS_FIRST`, `MULLIGAN`). This is the most informative field for "why
  am I choosing?".
- `minCount`, `maxCount`, `remainDamageCounter`, `remainEnergyCost`.
- `option: list[Option]` — the choices; your return values index into this.
- `deck`, `contextCard`, `effect` — extra context (often None).

## Option

Read fields based on `option.type` (`OptionType`):
- `MAIN`-type turn actions: `PLAY`, `ATTACH`, `EVOLVE`, `ABILITY`, `DISCARD`, `RETREAT`,
  `ATTACK`, `END`.
- Card/area selections: `CARD`, `TOOL_CARD`, `ENERGY_CARD`, `ENERGY` — use
  `area`/`index`/`playerIndex` (+ `toolIndex`/`energyIndex`/`count`).
- `ATTACK` uses `attackId`; `NUMBER` uses `number`; `YES`/`NO`; `SKILL` uses
  `cardId`/`serial`; `SPECIAL_CONDITION` uses `specialConditionType`.
Most Option fields are `None` unless relevant to that option type.

## State (`obs.current`)

Game state when a selection is requested (None at initial deck selection):
- `turn`, `turnActionCount`, `yourIndex` (0/1 — you), `firstPlayer`, `result`
  (winner index, -1 if ongoing).
- Per-turn flags: `supporterPlayed`, `stadiumPlayed`, `energyAttached`, `retreated`.
- `players: list[PlayerState]` (length 2) — `active`, `bench`, `benchMax`, `deckCount`,
  `discard`, `prize`, `handCount`, `hand` (None for opponent), and condition flags
  (`poisoned`/`burned`/`asleep`/`paralyzed`/`confused`). `Pokemon` carries `hp`/`maxHp`,
  attached `energies`/`energyCards`/`tools`/`preEvolution`.
- `obs.logs: list[Log]` — events since your last selection (draws, moves, attacks, HP
  changes, results); `LogType.RESULT.reason` explains a game's ending.

## Lookahead (optional)

For planning, `cg/api.py` exposes `search_begin / search_step / search_end /
search_release` to simulate forward from the current observation given predicted hidden
information (opponent deck/hand/prize/active). See the docstrings — inputs must match the
real counts or they raise `ValueError`.

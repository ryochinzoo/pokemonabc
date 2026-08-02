# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Team workspace for the Pokémon TCG AI Battle Challenge (Kaggle). An agent =
**deck (60 cards) × pilot (`main.py`)**. The game engine is a **precompiled C
library** (`cg/libcg.*`, `cg/cg.dll`) accessed through `ctypes`.

**READ `docs/memo/playbook.md` BEFORE planning any development or measurement
work** — it encodes the team's debiasing discipline (control experiments first,
out-of-family calibration, pre-registered N and kill criteria, `/council` for
big decisions) and the operational rules that past sessions learned the hard way.

## Layout

- `src/input/datasets/decks/<deck-name>/` — one directory per deck experiment,
  each containing `main.py` + `deck.csv` + `cg/`. This is the **deck directory**;
  run and test from inside it. Engine binaries (`*.dylib`/`*.so`/`*.dll`) are
  gitignored — copy them in from the Kaggle sample_submission if missing.
- `verification/` — local benchmarking toolbox (bench.py, donk_meter.py,
  selfplay.py, gauges, experiment decks, card DB). **Read
  `verification/README.md` before submitting anything.**
- `replay_analysis/` — fetch & analyze real Kaggle episode replays
  (`https://www.kaggle.com/competitions/episodes/{id}/replay.json`, public).
- `docs/memo/` — decision log / measured data / handover. Source material for
  the Strategy-track report. Record decisions in `decisions.md` format.

## The agent contract (`main.py`)

`agent(obs_dict: dict) -> list[int]` returns option indices and MUST satisfy:
- `obs.select.minCount <= len(result) <= obs.select.maxCount`
- every index in `[0, len(obs.select.option))`, no duplicates
- When `obs.select is None`, return the 60-card deck (list of card IDs).

**The agent must never crash and never return an illegal selection** — that
voids matches. Run `@robustness-guard` after changing agent logic.

## Team rules (agreed process)

- **Measure before submitting**: pass the gate in `verification/README.md`
  before any Kaggle submission. **Effect-size judging uses the calibrated
  encounter-weighted score (CEW) over out-of-family gauges, not self-piloted
  in-family gauges** (D27: in-family benches over-estimate by +8~+62pt; D29). The
  only independent checks are validity, not effect size: CRASH=0 / vs random ≥96%
  / `check.py --submission <deck-dir>`.
- **Submissions are budgeted** (5/day, final ranking = latest 2): keep the two
  most recent submissions = our two best versions.
- **Deck legality: the engine DOES enforce it, and rejection means a lost match.**
  (2026-08-03 correction — the previous note here claimed the engine ignores the
  4-copies-per-name rule; that was falsified, see data.md 2026-08-03.) Measured
  `battle_start(...).errorType`: `2` = copy-limit violation (5 of one ID, **or 6
  across two IDs sharing a name**, or >4 special energy), `3` = no Basic Pokémon,
  `4` = ACE SPEC violation (>1 ACE SPEC in the deck, even two different ones).
  An illegal deck sets `errorPlayer >= 0` → the runner marks the agent INVALID
  → reward −1. Use `conformance.py`, which already calls this path.
  **The whole card pool is usable**: all 2,022 cards in `EN_Card_Data.csv` are
  accepted (`verification/card_support_scan.py`; the 29 ACE SPECs need to be 1-of).
- Pure standard library only in submitted code; no third-party packages.
- Enums/dataclasses in `cg/api.py` may gain new members during the competition —
  never assume exhaustiveness.
- `verification/reference/steel_agent.py` is a public third-party notebook
  (Apache 2.0) kept **for study only — never submit it or derivatives-by-copy**;
  the Strategy track judges originality.

## Tooling

- `/bench N` — win-rate vs random or gauges (see skill).
- `/try-heuristic` — explore→implement→verify→record loop for pilot changes.
- `/submission-check` — pre-flight checks before a real submission.
- `/lookup-card`, `/agent-api`, `/kaggle-coach` — reference skills.
- Formatting: `ruff format`, `ruff check` (not installed by default).

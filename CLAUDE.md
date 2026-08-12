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

## セッション開始時に必ずやること

**`kaggle_cli.our_submissions()` を1回叩いて、今のチャンピオンを確定してから始める。**
リポジトリは読めても、Kaggleの最新状態は読めない。2026-08-11 に実際に踏んだ:
「我々は678.7点」という前提で1時間以上作業したが、前日に **821.9点の提出**が入っており、
**デッキ比較の対象ごと間違えていた**。1リクエストで防げる。

ゆうじ側の開始テンプレは `docs/memo/session-start-template.md`。

## 道具の索引

**探す前に `docs/memo/tools-index.md` を読む。**「知りたいこと → コマンド」の逆引き表。
道具は60本以上あるが常設は20本弱で、残りは**走らせず読む**使い捨ての検死。
ローカル対戦の正しい回し方・CEWの現行重み・データの置き場も同じ文書にある。

外部APIは **`kaggle_gate.py` / `kaggle_cli.py` 経由のみ**(直の `curl`/`kaggle` は禁止。
8秒間隔・429で4時間停止を共有。playbook §8)。**常時自動では回さない** — 値が要るのは
判断の直前だけ(デッキ転換の検討時、提出の+24h検死)。census は1週間以上空いたら取り直す。

### 罠（すべて2026-08-10に実際に踏んだ。詳細は data.md 同日節）

1. **応答は次のstepに記録される**: 選択肢は `steps[N]...option`、答えは **`steps[N+1].action`**。
   `steps[N].action` を使うと29%しか当たらない(2026-08-11確定、4,593決定で99.9%)。
   `option.index` = 手札位置も**正しい**(型整合7,510件で破綻0)。
   → 修正済み。battle_report.py / misplay_scan.py は両方この規則で動く。
2. **`yourIndex` は手番の人ではない。** 手番でない側にも観測と選択肢が残っており、
   これで絞ると決定数が倍になる。判別は **`status == "ACTIVE"`** のみ。
3. **素朴に数えると桁で過大に出る。** 見逃し 98→18→1、ループ 517→264→0。
   **「勝ち譜のほうがミスが多い」のような逆向きの異常は、計器の故障を疑う合図。**
4. **推測で検証しない。**「手札から消えたカード」は推測、
   **エンジンの `logs`(PLAY=10/ATTACH=11/ATTACK=15 は cardId 付き)は事実**。
5. **律速の判定に短い数字で部分一致しない。** 裸の `"429"` が提出ID `55374292` に
   一致して4時間停止を誤発火した。
6. **LLMは資料の誤りを増幅する。** 誤った対戦ログから「詳細で説得力のある講評」が
   返ってきたが、そのプレイは起きていなかった。**資料の正しさは渡す側の責任。**
   NotebookLM に数を数えさせない — 集計は手元で出して .md に焼き込む。

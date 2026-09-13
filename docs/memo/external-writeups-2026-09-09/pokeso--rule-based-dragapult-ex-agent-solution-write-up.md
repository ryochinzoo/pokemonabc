<!-- 公開 Kaggle ノートブック(著者 pokeso)の markdown セルのみを研究目的で転記(2026-09-09、kaggle kernels pull)。出典: https://www.kaggle.com/code/pokeso/rule-based-dragapult-ex-agent-solution-write-up
     コード・画像は省略。引用は 15 語以内・出典明記の範囲で。提出物への転用禁止(CLAUDE.md の steel_agent と同じ扱い)。 -->

## 1. Overview

My agent plays a **Dragapult ex** deck and is entirely rule-based: for every option the engine presents (play, attach, evolve, ability, retreat, attack, …), a scoring function returns a single number, and the agent picks the highest-scoring option. There is no learned model. The strength comes from three things:

1. A carefully ordered **score ladder** that encodes the deck's game plan (assemble Phantom Dive as fast as possible, then convert every attack into prizes).
2. **Exact lethal solvers** that enumerate kill lines (main damage + spread + Boss's Orders + Adrena-Brain + pending energy attach) before anything else is considered.
3. **Lightweight probability models** (hypergeometric draw odds, Monte Carlo ordering) used only where a binary rule was measurably wrong.

> **日本語:** エンジンが提示する全選択肢をスコア化し最大を選ぶ方式。①デッキの勝ち筋を順序付けた評価ラダー、②「本体200＋ばら撒き＋ボス＋アドレナ＋手貼り予約」まで含むリーサル全探索、③二値ルールが間違う局面だけに入れた軽量な確率モデル、の3本柱です。


## 2. The score ladder

Every action band lives in a fixed numeric range, so priorities are auditable and diffs are testable:

| Band | Range | Examples |
|---|---|---|
| Lethal lines | 660–830 | pending-attach lethal 830, dark-arm Adrena lethal 829, Boss lethal 675 |
| Evolutions | 700+ | dive-capable active Drakloak 706, recon-before-evolve 710 |
| Abilities / supporters | 300–660 | Recon Directive 620, Lillie scaled by hand size, Unfair Stamp scaled by **opponent** hand size |
| Goods / fetch | 350–660 | fetch tiers: evolve-now 400 > candy-now 395 > body-in-hand 390 > … |
| Deferred energy attach | 292–299 | attach *after* draws/supporters so the target choice uses the latest board |
| Attacks | 240–265 | attack is近 last — after all value is extracted from the turn |
| End turn | 10 | never chosen while anything constructive remains |

Two details mattered a lot: **deferred attach** (energy is attached at the end of the turn by default, so Lillie/recon draws inform the target — but jumps to 672/830 when it completes a dive or a lethal), and **turn-order encoding** (goods and evolutions before Unfair Stamp, stamp before Lillie, attach and retreat before attack).

> **日本語:** 全行動を固定の点数帯に割り当て、優先順位を監査・テスト可能にしました。特に効いたのは「手貼りをターン終盤に遅延させ、ドロー後の最新盤面で貼り先を決める（ただしダイブ完成やリーサルなら即座に昇格）」と「グッズ→スタンプ→リーリエ→逃げ→攻撃の順序の明示的なコード化」です。

**Code (excerpt from `main.py`):**

[code excerpt omitted — read the notebook]

## 3. Lethal solvers

Before the ladder is consulted, the agent scans for guaranteed wins this turn:

- **Spread subset enumeration:** Phantom Dive places 6 damage counters freely; with ≤5 bench targets the winning subset can be brute-forced (2⁵ = 31 combinations), including "wipe the board" wins.
- **Pending-resource lethals:** the scan also considers *resources not yet spent* — a manual energy attach that completes the dive (830), a dark energy onto Munkidori that enables Adrena-Brain (829), Night Stretcher recovering Munkidori for a lethal (672), and Boss's Orders pulling the kill target (675). A per-turn lock remembers the planned Boss target so the follow-up select executes the same plan.

> **日本語:** ラダーの前に「この番に勝ち切れるか」を全列挙します。ばら撒き6個の配分はベンチ最大5体なので31通りの総当たりで厳密に解け、さらに「まだ使っていない資源」（ダイブを完成させる手貼り、アドレナを起動する悪手貼り、タンカ回収、ボスの呼び出し）込みのリーサルも予約実行します。

**Code — Lethal solvers (1/2): spread subset enumeration / ばら撒き部分集合の全列挙**

[code excerpt omitted — read the notebook]

**Code — Lethal solvers (2/2): Boss lethal with a per-turn lock / ボスのリーサル予約**

[code excerpt omitted — read the notebook]

## 4. Damage-counter spread planner

Non-lethal spreads follow strict priorities: (1) win-now subsets, (2) efficient KOs — with a bonus for opposing *basics* (killing the evolution engine), (3) set up next-turn win shapes (drop a 210 HP ex to ≤200 = Boss + dive range), (4) leftover counters placed to not overshoot remaining HP. Mirror-specific rule: never leave exactly 3+ counters on a clean opposing Pokémon when your own Drakloak is exposed — that is free Adrena-Brain ammo against you. Mist Energy targets are excluded (spread is a *move effect*).

> **日本語:** 非リーサル時のばら撒きは「勝ち形→効率KO（たね狩り優先）→次ターン勝ち形の仕込み→余りは過剰のせ回避」の順。ミラーでは「きれいな相手に3個置くと自分のドロンチがアドレナの的になる」ため2個までに制限。ミストエネルギー持ちは対象外にします。

**Code (excerpt from `main.py`):**

[code excerpt omitted — read the notebook]

## 5. Probability models (added only where measurement justified them)

I catalogued ~20 candidate spots where a fixed rule could be replaced by a probability estimate, measured each one's frequency × decision-flip rate on 30 recorded self-play games (5,477 decision states), and implemented top-down with a strict A/B gate (see §7). Survivors:

- **Hypergeometric draw odds** for "can I reach the missing energy/body this turn?" — counting all routes: raw energy, Night Stretcher via trash, Akamatsu, Meowth ex → Catch → Akamatsu, Ultra Ball → Meowth chains.
- **Return-KO risk on forced promotion:** a wall Dragapult is demoted when the opponent's *visible board* can provably one-shot it (attack costs payable with attached +1 manual, weakness ×2).
- **Lillie shuffle risk:** −150 to Lillie when the hand holds a plan card (Dragapult body with a charged Drakloak on bench) and post-shuffle re-access probability is <50%.
- **Monte Carlo ordering (100 rollouts, ~3 ms, cached per turn):** decides "Recon Directive before or after Lillie?" by simulating both orders against the actual deck remainder.
- **Unfair Stamp timing:** scored by *opponent* hand size (min(440, 250+25×n)); with opponent at ≤3 cards it fires only if we can realistically dive this turn (P ≥ 55%) or the prize race justifies it.

Several other probabilistic refinements (Akamatsu conservation, stamp re-draw risk, mirror evolve-gate softening, candy-route odds, spread weighting) measured **exactly neutral** over 1,000-game A/Bs and were rejected — a useful negative result: in a mirror-heavy ladder, low-frequency refinements rarely move win rate even when logically correct.

> **日本語:** 確率化の候補を約20件洗い出し、自己対戦30試合・5,477局面で「頻度×判断が変わる率」を実測してから上位のみ実装しました。生き残ったのは超幾何分布のドロー確率（タンカ/アカマツ/ニャース連鎖まで供給ルートを数える）、死に出し壁の返しKO確率、リーリエのシャッフル損失リスク、ていさつ↔リーリエ順序の100回モンテカルロ、相手手札枚数ベースのスタンプ評価です。論理的に正しくても1,000戦で中立だった案は不採用にしました。

**Code — Probability (1/2): hypergeometric draw odds with supply chains / 供給連鎖込みの超幾何ドロー確率**

[code excerpt omitted — read the notebook]

**Code — Probability (2/2): Unfair Stamp timing by opponent hand size / 相手手札枚数ベースのスタンプ評価**

[code excerpt omitted — read the notebook]

## 6. Opponent modeling & shallow search

The agent infers the opponent's archetype from visible cards against a small library of real ladder decks (plus the mirror), and switches gates accordingly — e.g. vs Alakazam, Unfair Stamp becomes proactive under stadium conditions; vs Crustle, Dragapult stops evolving beyond one wall and Dudunsparce ex becomes the attacker. A shallow determinized search (with exact prized-card fixing once identified) can override the rule choice, but only past a pessimism margin: +12 in the mirror, +60 vs off-meta libraries where rollout optimism is dangerous.

> **日本語:** 見えたカードから相手デッキをライブラリ照合し、フーディン・イワパレスなどマッチアップ別のルールに切替。決め打ち探索も持ちますが、ルール選択を覆すには悲観マージン（ミラー+12点、非ミラー+60点）を要求して幻覚勝ち筋を防ぎました。

**Code (excerpt from `main.py`):**

[code excerpt omitted — read the notebook]

## 7. Development process (probably the real "solution")

- **Replay-driven fixes:** every ladder loss suspected of a misplay became (a) a minimal root-cause analysis on the exact decision state, (b) a fix, and (c) a **replay regression test** that feeds the recorded observation to the agent and asserts the corrected choice. The final agent ships with ~40 regression suites.
- **Fast A/B harness:** search-off self-play at ~6.4 games/sec (alternating seats, two module instances). Every change ran 1,000 games vs. the previous version with a hard stop below 50%.
- **Respect the noise:** with n=100 the standard error is ±5% — several "regressions" at n=100–300 turned out to be exactly 50.0% when isolated and re-run. Rule of thumb: don't conclude anything under 1,000 games (±1.6%).
- **Ladder variance is real:** one submission peaked ~890 rating on a lucky run and decayed later; a 1,000-game head-to-head showed the *newer* agent was actually stronger. Trust head-to-heads, not single ladder runs.

> **日本語:** 実際の負けリプレイ→原因特定→修正→「そのリプレイ局面を食わせて正しい手を選ぶか」の回帰テスト化、を約40本積み上げました。検証は自己対戦6.4試合/秒のハーネスで毎回1,000戦（50%割れで停止）。n=100の勝率は±5%ブレるので結論を出さない、レートの上振れを実力と混同しない、が重要な教訓でした。

**Code (excerpt from `main.py`):**

[code excerpt omitted — read the notebook]

## 8. Closing

Final submissions were two adjacent versions of the same lineage (the last one adding five replay-driven fixes from the final night). Thanks to the hosts for a genuinely fun environment — a card game with hidden information, prize-card uncertainty, and a rich action space turned out to be a great playground for classical, testable AI engineering.

Questions welcome — happy to elaborate on any component.

> **日本語:** 最終提出は同系統の2バージョン（最終夜のリプレイ修正5件込み）。隠れ情報・サイド落ち・広い行動空間を持つカードゲームは、テスト可能な古典的AI設計の良い題材でした。質問があればコメントでどうぞ。

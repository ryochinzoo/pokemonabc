# Writeup 全文ドラフト v3 (v1=2026-07-28 / v2=G1・G5・G7反映 / v3=2026-07-30)

> **位置づけ**: これは「逆算」方針(D56、ゆうじ承認)の産物 — 記事を先に書き切って、
> **どこで論証が詰まるかを計器として使う**ためのドラフト。8/8の実験終了前に書くことで、
> 発見したギャップがまだ埋められる。数値はすべて `claims-ledger.md` 経由(T6)。
> 語数=約1,950語(本文のみ。末尾のギャップ表は本文外)。
> **v2の変更**: G1(#26を§5へ再配置=「で、強くなったのか」への直答) / G5(審査基準④への
> 直答=対面別勝率の開示) / G7(§4にキーカード活用の採用側1文)。いずれも追加測定ゼロ。
> **v3の変更**: ①前向き検証を **n=4** に更新(55058443検死。T3非発火=再較正の前向き確認も併記)
> ②§3に**規則の自己監査3段目**(台帳#29: 自作ゲートの偽発火率44%と、それを根拠にした再審が
> 反証された経緯) ③§6に**4例目**(辞書修理: 機構実在・修理成功・副作用ゲートでkill)
> ④到着レートを訂正後の**打ち切り機構**へ差し替え(台帳#28) ⑤図参照を5点に(Fig.1-5)
> ⑥誤り2件を訂正(前向き検証n=3→4 / 「較正の法則がn=4」は族内バイアス法則n=3との混同)。
> **語数=1,909語**(空白区切り。上限2,000に対し余裕91語)。

---

## Measure Before You Believe: Calibrating a Self-Play Agent Against the Real Ladder

### 1. Approach Overview

Our central problem was not "how do we make the agent stronger" but that **we could not tell
whether it had become stronger.** A Pokémon TCG match is high-variance, and the obvious measuring
device — our own agent piloting the opponent's deck in self-play — is the one most likely to
flatter us. It did: our in-family benchmarks overstated win rates by **+8 to +62 percentage
points**, depending on who really pilots that deck on the ladder [#1].

So we inverted the usual order: build an instrument, calibrate it against the real Kaggle
ladder, and require every proposed improvement to be pre-registered and judged on it. Then the
step that matters most and that we nearly skipped — **we audited the judging rule itself,
repeatedly, and reported what we found even when it reversed our own decisions.**

That discipline produced a second class of result, in the game domain rather than the
methodology: **human deck-building orthodoxy does not survive contact with an AI pilot.** Three
times a combo that is standard in human play proved to be dead weight, and each time only the
calibrated instrument could show it. Those two threads are this report's two backbones.

Throughout, we treat the leaderboard score as evidence about the world, not as the verdict:
the same agent varies by **±150–400 rating points** across resubmissions [#20].

### 2. Pilot Design

The agent is a greedy selector over a hand-written evaluator, wrapped in a
**search-and-override layer** that uses the competition's own engine (officially released, and
permitted in submissions) to look ahead by determinization and overrule the greedy choice when
the two disagree by more than a margin. Two findings about this architecture are worth more than
the architecture itself.

**First, we never ran the control experiment on our most important component until month
seven.** The override layer had been justified by a single in-family measurement (N=200) taken
*before* the calibration law was known. When we finally ran it as a proper ablation on the
calibrated out-of-family instrument, the layer was worth **+13.62pt (95% CI [+11.40, +15.84],
12.0σ, N=3,200 per arm)** [#26, Fig. 4]. The result vindicated the component and indicted the process:
our own playbook said "control experiment first," and the rule had never once been applied to
the layer that rule was written to protect.

**Second, our published diagnosis of that layer's failure mode was wrong.** We had attributed an
earlier regression to "maximisation bias under unequal visit counts." Reading the code again
seven months later, the override margin is `120.0` while a prize card is worth `±10,000` and a
terminal state `±1e9` — the margin is **1.2% of one prize card** [#27]. The override was not
making a trade-off; it was maximising a lottery ticket. The mechanism we had confidently named
did not exist in the shipped agent.

The one pilot change we adopted came from behavioural diagnosis, not intuition. Ignition Energy
supplies three colourless energy on an *evolved* Pokémon, putting Mega Starmie ex in range of its
210-damage attack at once. Logging showed the agent took only 26% of the chances to attach it to
the active evolved Pokémon, wasting the rest on Basics. A targeting rule lifted the calibrated composite by **+2.50pt
(independent replications +2.18 / +2.81, N=1,600 per cell, 1.7σ)** [#5], and the behaviour
transferred to production: **85% (56/66) of Ignition attachments converted into the intended
attack, with 0.30 misfires per game across 60 ladder games** [#6]. The combo itself is known to
human players; our contribution is the probe that found the agent was not executing it.

### 3. Verification Infrastructure

This is the part of the project we would defend hardest, and it has two halves.

**Half one: the instrument.** Measuring the same deck piloted by different agents showed the
in-family error is not random — it scales with the skill gap between the real pilot and ours:
**+62pt** against a strong public agent, **+41pt** against the host's sample agent, **+8pt**
against a teammate's (N=300 each) [#1]. That had a concrete consequence: the host's public
sample Lucario agent is **not a proxy for our ladder opponents — it is one of them.** Its deck
matches the list we actually face **60 cards out of 60**, and our win rate against it (44.0%,
N=300) is consistent with the ladder's (50%, N=14, CI 26–74) [#2, Fig. 1]. We rebuilt the
benchmark suite around opponents of that kind.

Then we required the instrument to make its living prospectively. Before each of four
submissions, and before reading a single replay, we pre-registered **two numeric predictions**:
what the calibrated out-of-family instrument implied, and what the in-family benchmark implied.
The ladder then arbitrated (Fig. 2):

| Submission | Calibrated | In-family | Ladder actual |
|---|---|---|---|
| EXP8 pilot | **37.0%** | 84% | **35.0%** (N=20, CI 18–57) |
| Second archetype | **35.58%** | 61.37% | **38.1%** (N=21, CI 20.8–59.1) |
| Champion re-run | **42.12%** | 84.42% | **30.0%** (N=20, CI 14.5–51.9) |
| Champion, re-weighted | **44.39%** | 85.12% | **33.3%** (N=21, CI 17.2–54.6) |

In all four the in-family figure fell outside the confidence interval and the calibrated figure
fell inside; deviations were −2.0 / +2.5 / −12.1 / −11.1pt with no systematic sign [#3]. The
fourth was also the first forward test of encounter weights we had re-estimated retrospectively,
and they held (χ²=6.74 against 7.815). We state the limit plainly: with N≈20 covered games the
interval is roughly ±19pt, so this excludes *gross* miscalibration, not error of ±10pt.

**Half two: the rule.** Our original adoption rule required four independent non-regression
gates. Its operating characteristic: a change with truly zero effect is flagged as a regression
**65.1%** of the time, against **68.8%** power to detect a real +5pt gain [#10] — rejecting good
work about as often as recognising it. We replaced it with a single calibrated
encounter-weighted composite.

We then audited the replacement, and it was also not good enough: its **+2.0pt adoption
threshold is only about 1.09σ**, admitting a 6.5–14% false-adoption rate per experiment [#22].
Reallocating the same games by Neyman allocation cut the standard error from 1.03 to 0.82pt for
free, and confidence intervals became mandatory.

The third instalment is the least flattering. A screening gate we wrote for our final
experiment — *stop if the control cell's misidentification rate rises* — fires **44% of the time
when the true difference is zero** [#29]: at N=50 per arm, comparing point estimates is a coin
toss. We found this only after the gate had killed that experiment, then argued from it that the
kill should be reopened. The review of that argument demanded a log we had not kept; producing it
disconfirmed our own case and the kill stood. **We had rebuilt, inside a rule we wrote ourselves,
the defect we had removed two months earlier.**

The same scepticism applies to the measurement procedure. Our model of when ladder games arrive
after a submission was wrong in mechanism: submissions do not decay, they are **evicted** the
moment they fall out of the team's two most recent — every one of ten stopped within three hours
*before* that eviction, despite lifetimes ranging from 12 to 62 hours [#28, Fig. 3].

### 4. Deck Construction

Our list is a Mega Starmie ex aggro build whose defining property is what we removed — every
removal forced by measurement rather than theory.

**Human orthodoxy did not transfer, three times.** (1) The Dusknoir engine — six slots that
cannot attack — is standard in human lists; the version without it beat the version with it
**64.7% head-to-head (N=150, CI 57–72)** [#4]. (2) Cinderace energy acceleration, present in
winning human lists, fired **0.12 times per game** in our hands and moved nothing [#8].
(3) We increased Basic count to reduce mulligans from 60.1% to 25.9% and the agent got
*monotonically worse* (composite 34.5 / 33.0 / 31.2 for 4 / 8 / 10 Basics) — replay analysis
showed the engine implements no mulligan penalty at all [#9]. The lesson generalises: a card's
value is a property of the deck **and the pilot together**, and a list validated by human play
is validated on a different pilot.

Three further interventions each died at a different stage, which is why we present them
together. Swapping our ACE SPEC for Maximum Belt is mechanically real — we logged the +50
threshold firing — yet as piloted it gave **−0.57pt (CI [−2.82, +1.68])** [#23]. A second did
occur in play and still netted **−0.01pt (CI [−2.28, +2.26])** [#24]. A third had a genuine
**+16.63pt** ceiling and died at the safety gate: its win rate against a random opponent fell to
**90.5% (N=211, CI 85.8–93.8)**, below our 96% floor, because damage and self-mill drew on the
same resource [#25]. Mechanism true, occurrence zero; occurrence real, effect zero; effect real,
legitimacy absent.

What survived is built around one enabling card: Ignition Energy is the fastest route to the
210-damage attack, and it became a key card only once the targeting rule of §2 taught the pilot
to aim it — in this format a card is "key" only relative to the pilot holding it.

### 5. Results

"How strong is the agent" is best answered by three calibrated effect sizes, one per component.
**Deck**: beats its human-orthodox ancestor **64.7% head-to-head** [#4]. **Search-and-override
layer**: **+13.62pt (CI [+11.40, +15.84], 12.0σ)**, the largest verified number in the project
[#26]. **Pilot rule**: **+2.50pt**, independently replicated [#5]. Everything else we tried
failed its pre-registered gate.

On the ladder the champion reached **783**, with byte-identical resubmissions scoring 765 and
747 — a spread that is itself our best evidence for treating single scores as noisy [#20].
Against our four calibrated gauges it scores **47.3 / 26.8 / 80.7 / 26.7%**: we disclose the weak
matchups rather than average them away, and weight them by measured encounter rate. That
transparency, plus **CRASH=0 across 60 consecutive ladder games** and no crash signature in any
earlier submission [#14], is our answer on robustness.

The loop that produced the most value was **submit → autopsy → fix → re-measure**: replays
showed the agent attacking a wall Pokémon for zero damage, and after a stadium-detection patch
that matchup went 7–2 with the loop absent [#15] — a behavioural claim, not a rating one.

### 6. What Didn't Work, and Limitations

Ten-plus registered experiments produced one adopted pilot change and one adopted deck change.

The last one is the sharpest. The search's model of the opponent's deck had gone stale: against
our two most frequent opponents it reconstructed the right list **0% of the time**, padding the
unseen deck with placeholder energy instead. Repairing it worked exactly as designed — 100%
identification — and we killed it anyway, because a control cell showed the repaired version
misidentifies decks *outside* its dictionary more often (11%→22% pooled). Proving a component is
broken does not entitle you to the fix.

The most useful item, though, is a reversal. Our largest negative result — rejecting a general
Monte-Carlo rewrite — did **not** survive re-examination on the calibrated instrument:
**+2.62pt, 95% CI [−0.68, +5.93]**, so the sign now points toward the version we discarded,
though the interval contains zero [#12]. We report it as an instrument success, not an
embarrassment. One further line was closed by code inspection rather than measurement, and we
label it so [#21]. Limits: the in-family bias law rests on **three** pilot pairs and is extrapolated, matchup-level
samples are small, and our gauges cover 38% of what we actually meet.

### 7. Conclusion

For a high-variance stochastic game, the measurement apparatus is not the scaffolding around
the agent — it is the main body of work. What we would tell our past selves is narrower than
"measure more": **calibrate against the environment you are actually scored in; pre-register
the number you expect; then keep auditing the rule that decides, including after you have
already fixed it once — and be ready for it to overturn a decision you were proud of.**

---
---

# ギャップ表(本文外 — 執筆して初めて露出した穴、重要度順)

書き切って詰まった箇所。**8/8までに埋められるものだけが対象**(以降は測定窓が閉じる)。

| # | ギャップ | 埋める手段 | 状態 |
|---|---|---|---|
| **G1** | **「で、強くなったのか」への答えが弱い**(§5。採用がEXP8 +2.5ptのみに見える。審査基準①②⑤が直撃) | #26(+13.62pt)を「探索層の価値」でなく**エージェントの正味の強さ**として§5へ再配置。デッキ側#4(64.7%)と並べ「2大構成要素の効果量を較正済み計器で測ってある」形にする。追加測定ゼロ | **✅v2で解消** |
| **G2** | 較正法則の観測点が少ない | 前向き検証は **v3で n=4 に到達**(55058443検死)。族内バイアス法則(#1)は n=3 のままで、穴Dの副次エンドポイント(各N=300)が8/3に n=4 化する | **前向きは✅ / 族内は8/3** |
| **G3** | 新重み(T3再較正)が前向き未検証 | 55058443で登録→**T3非発火(χ²=6.74<7.815)で確認済み**。§3に1文追加 | **✅解消** |
| **G4** | §5が薄い | G1の再配置で解消。fig_rating_timelineの更新は残 | **✅ほぼ解消**(図1点残) |
| **G5** | 頑健性(審査基準④)への直答がCRASH=0だけ | CEW4対面の内訳(47.3/26.8/80.7/26.7)を開示し、「弱い対面を隠さずゲージ化して重み付けする」構造そのものを④の答えにする | **✅v2で解消** |
| **G6** | 図が2点しかない(Report 10%=図表の効果的使用) | **fig_search_ablation.svg**(#26のON/OFF対照、+13.62pt・CI・12.0σ)と**fig_eviction.svg**(#28の打ち切り機構、10提出のdumbbell)を新規作成。dataviz手順に従い配色を`validate_palette.js`で検証(light/dark全項目PASS)、目視で衝突2件を修正 | **✅4点→5点**(fig_deck_matrixは族内数値のため単体使用禁止) |
| **G7** | Deck 20%が removal 中心で「何を選んだか」が薄い | Ignition→Nebulaの採用側を§4にも1文 | **✅v2で解消** |
| **G8** | ミラー・Alakazamが計器外(カバレッジ38%) | 測定では埋めない。§6で限界として明記(実施済み) | **✅書いた** |
| **G9**(新) | 図の参照が本文と結びついていない | Fig.1-5 の参照を§3/§5に挿入済み。ただし**キャプション文と図タイトルの整合はwriteup清書時にT6で機械照合**する | 8/17以降 |
| **G10**(新) | 台帳#29(自作ゲートの偽発火率44%)は**未再現** | 作動特性は解析計算なので再現不要だが、「壊れた計器がたまたま正しく鳴った」という主張は run1/run2 の2標本(プールp=0.0556)に依存する。**§3では「44%」を断定し、「鳴った内容が正しかった」側は弱確証として書く**(台帳の指示どおり) | 書き方で解決済 |

**v1時点の結論(維持)**: G1が最大で、しかも**追加測定ゼロで埋まった**(構成の問題であって
証拠の問題ではなかった)。新規実験を要するギャップは1件も出ず、**8/1以降を穴D専有にする
D54の裁定は執筆側から見ても正しい**。

**v3時点の残タスク(いずれも測定不要)**: 族内バイアス法則の n=4 化(8/3の穴D副次で自動)/
fig_rating_timeline の更新1点 / 8/17以降の清書とT6機械照合。
**執筆側から見て、8/8までに新たに走らせるべき実験は無い。**

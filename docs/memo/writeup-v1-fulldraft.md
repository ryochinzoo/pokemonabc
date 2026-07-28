# Writeup 全文ドラフト v2 (v1=2026-07-28、v2=2026-07-29 G1/G5/G7反映)

> **位置づけ**: これは「逆算」方針(D56、ゆうじ承認)の産物 — 記事を先に書き切って、
> **どこで論証が詰まるかを計器として使う**ためのドラフト。8/8の実験終了前に書くことで、
> 発見したギャップがまだ埋められる。数値はすべて `claims-ledger.md` 経由(T6)。
> 語数=約1,950語(本文のみ。末尾のギャップ表は本文外)。
> **v2の変更**: G1(#26を§5へ再配置=「で、強くなったのか」への直答) / G5(審査基準④への
> 直答=対面別勝率の開示) / G7(§4にキーカード活用の採用側1文)。いずれも追加測定ゼロ。

---

## Measure Before You Believe: Calibrating a Self-Play Agent Against the Real Ladder

### 1. Approach Overview

Our central problem was not "how do we make the agent stronger." It was that **we could not
tell whether it had become stronger.** A Pokémon TCG match is high-variance, and the obvious
measuring device — our own agent piloting the opponent's deck in self-play — is exactly the
device most likely to flatter us. It did. When we finally measured that bias, our in-family
benchmarks were overstating win rates by **+8 to +62 percentage points** depending on who
really pilots that deck on the ladder [#1].

So we inverted the usual order. Before optimising the agent, we built an instrument; then we
calibrated the instrument against the real Kaggle ladder; then we required every proposed
improvement to be pre-registered and judged on that calibrated instrument. Then we did the
step that we think matters most, and that we nearly skipped: **we audited the judging rule
itself, repeatedly, and reported what we found even when it reversed our own past decisions.**

That discipline produced a second class of result, in the game domain rather than the
methodology: **human deck-building orthodoxy does not survive contact with an AI pilot.**
Three separate times, a combo that is standard in human play was dead weight for our agent —
and each time we could only see it because the instrument was calibrated. Those two threads,
methodology and domain, are the two backbones of this report.

Throughout, we treat the leaderboard score as evidence about the world, not as the verdict:
the same agent varies by **±150–400 rating points** across resubmissions [#20].

### 2. Pilot Design

The agent is a greedy action selector over a hand-written evaluator, wrapped in a
**search-and-override layer** that uses the competition's own engine (officially released, and
explicitly permitted in submissions) to look ahead by determinization and overrule the greedy
choice when the lookahead disagrees by more than a margin.

Two findings about our own architecture are worth more than the architecture itself.

**First, we never ran the control experiment on our most important component until month
seven.** The override layer had been justified by a single in-family measurement (N=200) taken
*before* the calibration law was known. When we finally ran it as a proper ablation on the
calibrated out-of-family instrument, the layer was worth **+13.62pt (95% CI [+11.40, +15.84],
12.0σ, N=3,200 per arm)** [#26]. The result vindicated the component and indicted the process:
our own playbook said "control experiment first," and the rule had never once been applied to
the layer that rule was written to protect.

**Second, when we did look inside that layer, our published diagnosis of its failure mode was
wrong.** In an earlier generation we had attributed a regression to "maximisation bias under
unequal visit counts." Reading the code again seven months later, the override margin is
`120.0` while a prize card is worth `±10,000` and a terminal state `±1e9` — the margin is
**1.2% of a single prize card** [#27]. The override was not making a considered trade-off; it
was maximising a lottery ticket. The mechanism we had confidently named did not exist in the
shipped agent. We report the correction rather than the original claim.

The one pilot change we adopted came from behavioural diagnosis rather than intuition.
Ignition Energy supplies three colourless energy when attached to an *evolved* Pokémon,
which puts Mega Starmie ex in range of its 210-damage attack immediately. Logging showed the
agent used only 26% of the opportunities to attach it to the active evolved Pokémon, wasting
attachments on Basics. A targeting rule lifted the calibrated composite by **+2.50pt
(independent replications +2.18 / +2.81, N=1,600 per cell, 1.7σ)** [#5], and the behaviour
transferred to production: **85% (56/66) of Ignition attachments converted into the intended
attack, with 0.30 misfires per game across 60 ladder games** [#6]. We note explicitly that the
*combo* is known to human players; our contribution is the behavioural probe that found the
agent was not executing it, and the calibrated verification that the fix survived.

### 3. Verification Infrastructure

This is the part of the project we would defend hardest, and it has two halves.

**Half one: the instrument.** We measured the same deck piloted by different agents and found
the in-family error is not random — it scales with the skill gap between the real pilot and
ours: **+62pt** against a strong public agent, **+41pt** against the host's sample agent,
**+8pt** against a teammate's agent (N=300 each) [#1]. This turned out to have a concrete
consequence: the host's public sample Lucario agent is **not a proxy for our ladder opponents —
it is one of them.** Its deck matches the list we actually face **60 cards out of 60**, and our
measured win rate against it (44.0%, N=300) is consistent with what the ladder gave us
(50%, N=14, CI 26–74) [#2]. We rebuilt our benchmark suite around opponents of that kind.

Then we required the instrument to make its living prospectively. Before each of three
submissions, and before reading a single replay, we pre-registered **two numeric predictions**:
what the calibrated out-of-family instrument implied, and what the in-family benchmark implied.
The ladder then arbitrated:

| Submission | Calibrated prediction | In-family prediction | Ladder actual |
|---|---|---|---|
| EXP8 pilot | **37.0%** | 84% | **35.0%** (N=20, CI 18–57) |
| Second archetype | **35.58%** | 61.37% | **38.1%** (N_cov=21, CI 20.8–59.1) |
| Champion re-run | **42.12%** | 84.42% | **30.0%** (N_cov=20, CI 14.5–51.9) |

In all three the in-family figure fell outside the confidence interval and the calibrated
figure fell inside; the deviations were −2.0 / +2.5 / −12.1pt with no systematic sign [#3].
We state the limit plainly: with N≈20 covered games the interval is roughly ±19pt, so this
excludes *gross* miscalibration, not error of ±10pt.

**Half two: the rule.** Our original adoption rule required a candidate to pass four
independent non-regression gates. We eventually computed its operating characteristic:
a change with truly zero effect would be wrongly flagged as a regression **65.1%** of the time,
against **68.8%** power to detect a real +5pt gain [#10]. The device was rejecting good work
roughly as often as it recognised it. We replaced it with a single calibrated
encounter-weighted composite.

We then audited the replacement, and it was also not good enough: its **+2.0pt adoption
threshold is only about 1.09σ**, admitting a 6.5–14% false-adoption rate per experiment [#22].
Reallocating the same number of games by Neyman allocation cut the standard error from 1.03 to
0.82pt for free, and confidence intervals became mandatory. The point is not that we arrived at
a good rule. It is that **a judging rule needs auditing after you fix it, not only before.**

We extended the same scepticism to the measurement procedure itself: measuring when ladder
games actually arrive after a submission showed that **30–40% of them land more than 12 hours
later**, and that ratings keep moving for 48–56 hours [#28] — so a score read early is not a
score.

### 4. Deck Construction

Our list is a Mega Starmie ex aggro build. Its defining property is what we removed, and every
removal was forced by measurement rather than by theory.

**Human orthodoxy did not transfer, three times.** (1) The Dusknoir engine — six slots that
cannot attack — is standard in human lists; the version without it beat the version with it
**64.7% head-to-head (N=150, CI 57–72)** [#4]. (2) Cinderace energy acceleration, present in
winning human lists, fired **0.12 times per game** in our hands and moved nothing [#8].
(3) We increased Basic count to reduce mulligans from 60.1% to 25.9% and the agent got
*monotonically worse* (composite 34.5 / 33.0 / 31.2 for 4 / 8 / 10 Basics) — replay analysis
showed the engine implements no mulligan penalty at all [#9]. The lesson generalises: a card's
value is a property of the deck **and the pilot together**, and a list validated by human play
is validated on a different pilot.

The ACE SPEC slot became our clearest case study, because we ran the same intervention through
four different failure modes. Swapping Deluxe Bomb for Maximum Belt is mechanically real — we
verified the +50 damage threshold firing in engine logs — yet as piloted it produced
**−0.57pt (95% CI [−2.82, +1.68])**, excluding the +2pt we required [#23]. A second
intervention did occur in play but still netted **−0.01pt (CI [−2.28, +2.26])** [#24]. A third
had a genuine **+16.63pt** ceiling on the screening instrument, and died at the safety gate
instead: its win rate against a random opponent fell to **90.5% (N=211, CI 85.8–93.8)**,
excluding our 96% floor, because the damage and the self-mill drew on the same resource [#25].
Mechanism true, occurrence zero; occurrence real, effect zero; effect real, legitimacy absent.

What survived is a list built around one enabling card: Ignition Energy is the deck's fastest
route to the 210-damage attack, and it only became a key card once the targeting rule of §2
taught the pilot to aim it — the clearest example that in this format a card is "key" only
relative to the pilot that holds it.

### 5. Results

The honest form of "how strong is the agent" is not a leaderboard number but three calibrated
effect sizes, one per component. **Deck**: the measured list beats its human-orthodox ancestor
**64.7% head-to-head** [#4]. **Search-and-override layer**: worth **+13.62pt (CI [+11.40,
+15.84], 12.0σ)** on the calibrated composite — the single largest verified number in the
project [#26]. **Pilot rule**: **+2.50pt**, independently replicated [#5]. Everything else we
tried — ten-plus registered experiments — failed its pre-registered gate and was discarded.

On the ladder the champion configuration reached **783**, with byte-identical resubmissions
scoring 765 and 747 — a spread that is itself our best evidence for treating single scores as
noisy [#20]. Against our four calibrated gauges the same agent scores **47.3 / 26.8 / 80.7 /
26.7%**: we disclose the weak matchups rather than average them away, and the composite weights
them by measured encounter rate — our answer to situational-robustness is this transparency
plus **CRASH=0 across 60 consecutive ladder games** and no crash signature in any earlier
submission [#14].

The loop that produced the most value was **submit → autopsy → fix → re-measure.** Real-ladder
replays showed our agent repeatedly attacking into a wall Pokémon for zero damage; a
stadium-detection patch changed the behaviour, and in production the same matchup went 7 wins
to 2 with the zero-damage loop absent [#15]. We claim the behavioural change, not a rating
effect.

### 6. What Didn't Work, and Limitations

Ten-plus registered experiments produced one adopted pilot change and one adopted deck change.
We think the most useful item is a reversal. Our largest negative result — the rejection of a
general Monte-Carlo search rewrite — did **not** survive re-examination on the calibrated
instrument: the difference was **+2.62pt with 95% CI [−0.68, +5.93]**, i.e. the sign now points
toward the version we discarded, though the interval contains zero and N=1,200 per arm cannot
settle it [#12]. We report this as an instrument success rather than an embarrassment. Separately,
one line of work was closed by code inspection rather than measurement, and we label it that way
[#21]. The calibration law itself rests on **three** observation points and is extrapolated;
matchup-level samples are small; and our encounter weights are tied to one rating band.

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

| # | ギャップ | どこで詰まったか | 埋める手段 | コスト | 判定 |
|---|---|---|---|---|---|
| **G1** | **「で、強くなったのか」への答えが弱い** | §5。採用は EXP8 +2.50pt(弱確証)のみ。10件以上やって1件。審査基準①②⑤が直撃する | **#26(+13.62pt)を「探索層の価値」でなく「我々のエージェントの正味の強さの実測」として§5に再配置**。デッキ側#4(64.7%)と合わせ「我々の2大構成要素の効果量はどちらも較正済み計器で測ってある」の形にする。**追加測定ゼロ、構成変更のみ** | 0 | **✅v2で実施済み** |
| **G2** | 較正法則の観測点が n=3 のまま | §3の主砲。「法則」と呼ぶには薄い | 穴Dの副次エンドポイント(台帳#1 n=4化、各N=300=計600戦≈15分)が既に登録済み。**8/3に自動的に埋まる** | 15分 | 登録済み・待つ |
| **G3** | 新重み(T3再較正)が前向き未検証 | §3。「規則を監査し続ける」の最新回が未完 | **本日の提出55058443で登録済み**。7/29 +24hの検死で結論 | 0(実行済) | 進行中 |
| **G4** | §5が薄い(300語枠に対し実質2段落) | Model⑤に直答する節が最も痩せている | G1の再配置でほぼ解消。加えて fig_rating_timeline の更新(#14の提出を追加) | 図1点 | G1と同時 |
| **G5** | 「頑健性」(審査基準④)への直答が CRASH=0 だけ | §5。④は「特定の初期状態・マッチアップ・状況的優位に依存しない」こと | **既存データで書ける**: CEW 4対面の内訳(勝率47.3/26.8/80.7/26.7)を出し、「強い対面と弱い対面を隠さず開示し、弱い対面をゲージ化して重み付けしている」構造そのものを④の答えにする | 0 | ✅v2で実施済み |
| **G6** | 図が2点(fig_prospective・較正ギャップ)しかない | Report 10%=「図表の効果的な使用」 | 3点目=**#26のON/OFF対照棒グラフ**(データ既存)。4点目=到着レート曲線(#28、データ既存) | 図2点 | 実施 |
| **G7** | Deck 20%に対し「キーカードの活用」の記述が removal 中心 | §4が「何を捨てたか」に偏り、「何を選んだか」が薄い | Ignition→Nebula の採用側の物語(#5/#6)を§4にも1文置く(現在§2のみ) | 0 | ✅v2で実施済み |
| **G8** | ミラー・Alakazam が計器外(カバレッジ33.3%) | §3/§6の限界節 | **測定では埋めない**(ゲージ新設は8/8まで届かない)。限界として明記する方針で確定 | 0 | 書くだけ |

**結論**: G1が最大で、しかも**追加測定ゼロで埋まる**(構成の問題であって証拠の問題ではなかった)。
新規実験を要するギャップは1件も出なかった — **8/1以降を穴D専有にするD54の裁定は、
執筆側から見ても正しい**。

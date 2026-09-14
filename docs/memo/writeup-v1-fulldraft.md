# Writeup 全文ドラフト v7 (v7=2026-09-02 終戦後清書 / v1=2026-07-28 / v2=G1・G5・G7反映 / v3=2026-07-30 / v4=打点構造訂正 / v5=2026-07-31外部レビュー反映 / v6=2026-08-14 aqua凍結追随)

> **v7 の変更(2026-09-02 深夜、第1稿。計画 = ~/.claude/plans/2-ai-concurrent-catmull.md)**:
> ①語数規準を **`wc -w` 全文込み ≤1,960** に変更(v6の「≈1,985」は外挿値で、実測は 2,079 だった)
> ②刈り込み C1-C12(§2 マージン120の二重記述を統合 / §3 前向き表を Fig.3 へ / §1・§3・§4・§6 の圧縮 / §5 頑健性文を最終夜へ吸収)
> ③挿入 I1 §5 "The final night"(**行動のみ・効果量なし**。`{P0}`〜`{P4}` は検死完了後に k/n で埋める)/
> I2 §6 "Two lines, one horizon problem"(りょーちん独立線、匿名版。実名は本人同意後)/ I3 §2 ENDガード(#37)/ I4 §7 一文
> ④T6: 未引用段落に引用を付けた(§4 リプレイ訂正 → #30 / §6 辞書修理 → #43(新設)/ §6 限界 → #22,#44(新設))、#9 と #34 に本文の数値を追記
> ⑤図番号を出現順に振り直し(Fig.1 探索対照 / 2 較正ギャップ / 3 前向き / 4 打ち切り / 5 支出明細 / 6 検死 / 7 地平×不確実性、`make_figures.CAPTIONS`)
> ⑥物語3箇所(§2 退却の発見 / §5 最終夜 / §5 ボスの価値序列)は **ゆうじ自筆で差し替える予定**(9/7)。本稿はその足場。
> v6 本文は git(a2cb966 以降の作業ツリー)と本ファイルの履歴に残る。

> **v6の変更(2026-08-14、D78の記事側実装 = writeup-v6-plan-2026-08-14.md をゆうじ承認で適用)**:
> ①§2末尾に退却物語(#27完結編。#32/#33、帰属保留を明示) ②§4冒頭を最終リスト(水単aqua、祖先から
> 12枚差)へ差し替え+凍結直前1枚差し実験(#34、pilot-scoped表現) ③§5を効果量カルテット化+頑健性行を
> 最終2提出の実測へ(**{N}は凍結後の実測で埋める**。8/14時点83) ④**T6: 8/2先行研究監査(台帳:60-88行)の
> 必須項目を反映** — #26にsham対照併記(+0.42 [−3.27,+4.10]) / §6に必須限界3件(非推移性・帯層別・
> プロセス隔離)+1bアンカー弱点 / #1を「発見」から降ろし独立公開の同型観測に言及 / #8に公開反証
> (74.4% N=1,000)併記でpilot-scoped化 / #9を「紙の定説への反証」に強化 / #20の§1表現を外部報告と
> 自前実測の併記に修正 / §1の定石失敗を3→5例に更新(#34) ⑤語数超過のため全節を圧縮
> (**v6計画の語数会計は約120語の計算誤り**: 1,998−150+253=2,101であり計画の言う≈1,981にならない。
> 圧縮はC1/C3/C4/C5+全節の刈り込みで対応)。L-a/L-b(+85語)は取り下げ(ゆうじ承認、台帳行生存・9月復活可)。
> 発見者の匿名表記("A teammate spotted")とタイトル据え置きもゆうじ承認済み(2026-08-14)。
> **着地語数: v5と同一の測り方で ≈1,985語(v5=1,998)** — 罫線・記号除外のトークン数 2,046 vs v5の2,059、
> 差 −13。正確な最終計数はKaggle投稿形式での9月清書時にT6で確定する。Fig.5参照はv5時点から本文に不在
> (v3チェンジログの「5点」と不整合、G9で照合予定 — v6で壊したものではない)。

> **v5の変更(2026-07-31、外部レビューループの成果。数値ゼロ or 台帳済みの編集のみ)**:
> ①タイトルに第2の背骨(deck orthodoxy)を明示 ②§4のルール断定2件を訂正
> (マリガンペナルティは実装あり=エンジンソース照合 / Dusknoirは「攻撃できない」でなく
> 「犠牲特性のための枠」) ③§5「stadium-detection」→「wall-ability」訂正(壁はCrustleの特性)
> ④§5に加重複合44.39%を明記(台帳#3の行4=H1と同一値)+38%カバレッジを併置(§6から移動)
> ⑤§5の783を byte-identical 3連の並びに降格 ⑥§7末尾にデッキ×パイロットのエコー1文。
> **注意: 台帳#9の機構文(「マリガンペナルティ未実装」)は本文と食い違う状態。台帳側の訂正が必要。**
> 未反映(台帳行が先): §4冒頭のコンセプト文+サイド経済段落 — 末尾「v5保留分」参照。
> **v5.1(2026-08-01)**: 外部妥当性監査(ablation-validity.md)を受け語数中立で2点 —
> ①§3の限界文を「絶対水準の錨のみ・A-vs-B比較は未検証」を含む形に置換(26語→25語)
> ②§5「largest verified」→「largest instrument-verified」(+1語)。計±0語。

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
> **v4の変更(2026-07-30)**: §4のキーカード段落を訂正 — 実測では210打点は攻撃の24%・打点の29%で、
> 主役は同じポケモンの1エネ攻撃(120+ベンチ50)だった(data.md「Alakazam対面の記述解析」)。

---

> **v8 の変更(2026-09-02、外部評議会 D85 の裁定を実装)**: 主役を最終エージェントに置き換え(§1 で提出物・成績・テーゼ)。
> §2 に60枚と勝ち筋(Fig.2)、§3 に実局面 ep102267456 T10 → ボスの価値序列 → 上書き経路の家系 → 検死とレビューの発見
> (KO判定がエネを見ない: 709/809・30/809・反転30%)、§4 に対面プロファイル(Fig.3、ルカリオ36.1%・ブリジュラス26.9%)と
> ブロック勝率、§5 は計器を1節に圧縮(探索+13.62 は7月の門なし層で測定と明記)、§6 に未測定・辞書5→10本・死んだ規則・
> 限界・独立2線。落としたもの: 押し出し図・支出明細図・自己監査三部作・「defend hardest」等の手続きの告白・±150–400。
> 図は8枚(決定フロー/デッキ/対面/較正/前向き/探索/検死/独立2線)、脚注から台帳参照を全削除。タイトル変更。

> **v8.2 の変更(2026-09-09、材料の旅 = plan simulations-strategy-wild-beaver、ゆうじ承認)**: 運営回答「表・図・Gallery の文字は語数外」を受けて、
> ①冒頭に審査基準→証拠の対応表 ②§4 の対面列挙を表に移し、対戦ゼロで測った初期状態プロファイル(先攻/後攻 57.7/40.1、マリガン 59.9%、Mega着地 67/46、相手レート帯)を追加(#53〜#56、Fig.11)
> ③§2 に12枚系譜(#58、Fig.9)・ミツル 755/755(#57)・専門家予測の符号逆(#7)・Kahneman & Klein 2009 ④§5 に Nosek 2018 ⑤§1 にレート分布の中央値(#59、Fig.10)
> ⑥§4 に時間バンク 587s(#38)と決定一致率 4.28%(#42)⑦§6 りょーちんを実名(ryoheihara、本人承諾 9/8)⑧圧縮: §2 内訳列挙・§3 END文・§5 冒頭と判定規則段落・§6 辞書文。
> 語数規準を「全文 wc -w ≤2,000 かつ 地の文 ≤1,900」に改定(t6_check --prose-limit)。図 8→11 枚。v8.1 は git と本ファイルの履歴に残る。
> **v8.3(2026-09-10 未明)**: de-AI パス 11 段落(ゆうじ承認、de-ai-pass-2026-09-09.md)+ 評議会「編集長」裁定(§1 冒頭の分割、自己言及3文の削除、§3/§4/§5 の1文目反転、§7 はテーゼで終える、対応表の最終行)。数値不変。Fig.12(公式ビジュアライザの実盤面)追加で図 12 枚。
> **v8.4(2026-09-10 未明)**: 審査員ペルソナ評議会(J-MI / J-TPC / 赤チーム、plan-2026-09-10-council-writeup.md)の裁定を実装。訂正: Mega 着地を「自分の2ターン目まで」で再集計(92.0/74.3、旧 67.2/46.1 は通し番号の混同で撤回、#55)/ T10 に Hero's Cape と返しの Aura Jab 130(両ラインとも負け、#39/#60)/ 「自己対戦ゼロ」にドスク直接対決の例外を明記 / 専門家予測 → 自前の事前予測(出所 D19 ペルソナ、#7)/ たね実験を screening N=300 に等身大化(#9)/ マリガン代償 4.4pt(CI は 0 を含む、#54)/ 規則は「1規則+1門」(#49)/ Cinderace は removed でなく rejected / Night Stretcher +3(#58)/ Marnie's Grimmsnarl ex / ryoheihara → Ryohei Hara。追加: §2 設計段落(1エネ攻撃とミツル・Ignition・Beach、#60)/ §4 対面の算術(#60)と先攻の基準線 58.5%(#53)/ §6 最終枠の理由1文。移動: §5 判定規則監査 → Fig.5 caption、§6 MC 再審 → Fig.6 caption、§7 の −3.29 再掲を削除。

## What a Card Is Worth When an AI Plays It: A Mega Starmie ex Agent, Measured Against the Real Ladder

| Judging criterion | Where the evidence is |
|---|---|
| Approach and its rationale | §1, §3, Fig. 1 |
| Original and technically sound | §5, Figs. 4–6 |
| Consistent under repeated matches | §4: blocks, latency, decision diff |
| Not over-reliant on start or matchup | §4, Fig. 3, Fig. 11 |
| Performance | §1, Fig. 10 |
| Deck concept and key cards | §2, Fig. 2, Fig. 9 |
| Report structure and figures | Figs. 1–12 inline beside the paragraphs that cite them; sourced captions at the end |

### 1. The agent

This report is about one agent. Its deck is mono-Water Mega Starmie ex: two species, four Basic Pokémon, sixty cards. Its pilot is a hand-written greedy evaluator, fourteen rules a human player taught it, and a 0.6-second engine lookahead that may overrule the greedy choice behind eight one-way gates (Fig. 1). Over its last 1,000 ladder games it won 51.2%, finished at 656.7, rank 2,898 of 6,807 and above the field's median of 621.5 (Fig. 10), and never crashed [#38, #40, #59].

The report has one idea: a card is worth nothing by itself. Its value belongs to the deck, the pilot and the field together, so we measured the three parts separately: the deck against its human-orthodox parent, the pilot on an instrument calibrated against the real ladder, the field by reading the last 1,000 replays.

### 2. The deck and its plan

The list (Fig. 2) differs from its human-orthodox parent by twelve cards (Fig. 9) [#58]. The plan is a race built on one number: Jetting Blow costs a single Water. Mega Starmie ex takes three prizes from an opposing Mega ex, or two from an ex and one from a Basic with the 50-damage bench splash; Wally's Compassion heals it fully and returns its energy, which costs one attachment when the attack needs one, and it was played 755 times in 1,000 games, every time on a damaged Mega Starmie ex [#57, #60]. Ignition Energy alone pays for the three-energy Nebula Beam (210), the finisher and the only attack that goes through a Crustle's Mysterious Rock Inn; Surfing Beach is its only switch [#60]. Jetting Blow was 71.4% of its attacks, Nebula Beam 18.5% [#46]; the paper plan was a 210-damage deck and the replays say it is a 120-plus-50 deck [#30].

Measurement rejected three human-orthodox choices. The Dusknoir sacrifice engine takes six slots in most human lists, and our own forecast from the coaching canon, written down before the run, was that cutting it would cost 5 to 10 points; the list without it won 64.7% head-to-head (N=150) [#4, #7]. Cinderace energy acceleration, tried and dropped, saw 0.12 uses per game in our hands, while another team runs it as the core of a 74.4% agent, so that failure belongs to our pilot and not to the card [#8]. Eight or ten Basics instead of four cut the mulligan rate from 60.1% to 25.9% and did not help, 34.5 → 33.0 → 31.2 on the calibrated composite (a screening run, Fig. 2) [#9], so the list mulligans 60% of the time on purpose, 59.9% in production; games with a mulligan won 4.4 points less, an interval that includes zero [#54]. Kahneman and Klein (2009) trust expert intuition only where the expert has had fast feedback from a regular environment; the coaching canon's feedback came from human pilots, none from this one, so we measured each orthodoxy.

The August list ran two Boss's Orders; a third copy, the most-adopted card among the 105 top-band teams we crawled, measured −1.53pt with the pilot byte-identical [#34]. That pilot had no idea whom to drag out. The final list runs three, with the targeting rules of §3; the effect of that combination, measured after the deadline, is in §6.

### 3. How it plays a turn, and where it disobeys itself

Turn ten of a ladder game against Mega Lucario ex (Fig. 12). Our Mega Starmie ex sits at 60 HP with one Water; the opponent's Mega Lucario ex, wearing Hero's Cape, is at 90 of 440, two prizes from winning against our four; our hand is Buddy-Buddy Poffin and Boss's Orders. Jetting Blow for 120 knocks it out for three prizes. The agent played Boss's Orders instead, dragged the 80-HP Makuhita forward and took one; a Mega Lucario ex answered with Aura Jab for 130 and the game, as it would have answered the three-prize line [#39, #60]. It is here as the misfire at its simplest: three prizes on the table, one taken.

The value ordering it should have used is the one a player uses, and it is in the code: knock out what you can knock out now, most prizes first; failing that, drag out the piece that will evolve into a threat, Riolu before it becomes Mega Lucario; failing that, the piece that cannot retreat, so the opponent's energy attachment is held hostage. Over the last 1,000 games the agent's 809 Boss's Orders went to knock-outs 577 times, to evolving threats 184 times, to bound targets 16 and to the weakest piece 32 [#39]. The turn above is not a failure of the ordering. The greedy layer did not propose Boss's Orders; the engine lookahead overrode it into Boss's Orders, and the gates let it: every gate protects the greedy choice from the lookahead, and none stops the lookahead from reaching for Boss's Orders on its own (Fig. 1).

The same unguarded direction had shown up before. In July a replay caught the agent retreating a fully-powered attacker instead of attacking a Mega Lucario it could not one-shot: on that board the production pilot chose RETREAT 12 of 12 times while the greedy layer said ATTACK, because an override margin of 120 sat against a prize term of ±10,000 and gated nothing [#27]. We repaired it, reproduced ATTACK 12 of 12, and the bundle it shipped in, a pilot layer plus a twelve-card deck change, measured +6.03pt (N=6,400, pre-registered) [#32]; then the registered falsification sensor fired, the matchup where retreat is most frequent got worse by 1.37pt [#33], so we kept the bundle and withdrew the mechanism story. Repairing a mechanism and moving a rating are different proofs.

The audit of the last 1,000 games (Fig. 7): 0 crashes, 0 END-stalls in 24,429 decisions, targets matching the rule's own first choice 809 of 809, and the one falsifiable prediction failed: 49 of 809 Boss plays were misfires by the rule's own count, every one a lookahead override [#39]. We wrote the Boss's Orders rules on the last night before the deadline and froze seven behavioural predictions first. Outside review then found its blind spot: the knock-out test used the printed maximum, 210, and ignored attached energy; counting energy, 243 of the 809 targets change status, 709 (87.6%) remain the best target and 30 plays remain misfires [#39]. The fix, measured after the deadline on the calibrated instrument: −2.42pt (95% CI [−5.85, +1.01]), a correct diagnosis and no detectable improvement [#51].

### 4. Robustness, and where it still loses

The rating is an average over opponents it meets at different rates (Fig. 3): earned against walls and Dragapult, lost to its two most frequent opponents [#45].

| Opponent, last 1,000 games [#45] | Record | Win rate |
|---|---|---|
| Wall decks (Crustle) | 94–16 | 85.5% |
| Dragapult ex | 68–31 | 68.7% |
| Alakazam | 113–86 | 56.8% |
| Mega Starmie ex (mirror) | 25–30 | 45.5% |
| Marnie's Grimmsnarl ex | 29–44 | 39.7% |
| Mega Lucario ex | 78–138 | 36.1% |
| Archaludon ex | 29–79 | 26.9% |

The two losing matchups have mechanisms we can name. Mega Lucario ex deals 400 in two turns, Mega Brave then Aura Jab, while Mega Starmie ex needs three Jetting Blows for its 340, and Nebula Beam plus Jetting Blow is 330, ten short; that is why the Boss's Orders ordering folds Riolu early, 184 of its 809 targets across all opponents [#39, #60]. Archaludon ex gives two prizes for our three and takes them in two Metal Defenders, so on paper every trade there is two-for-three against us [#19, #60]. The five matchups the instrument covers sum to 41.8% against 51.2% overall: the agent earns its rating outside the instrument's coverage, a limit of the instrument as much as of the deck [#45].

It does depend on the start of the game (Fig. 11): 57.7% going first, 40.1% going second, first in 64.9% of games [#53]. The seat effect is the environment's more than the deck's: whoever went first won 58.5% of these games [#53]. A quarter of its losses ended without a prize taken, and Mega Starmie ex was on the board by its own second turn in 92.0% of wins against 74.3% of losses, going second 90.7% against 65.1% [#55]. Its opponents' median rating was 651.6 [#56].

What did hold, over the same 1,000 games:

| Consistency check [#38, #47, #42, #20] | Result |
|---|---|
| Crashes or stderr | 0 in 1,000 games |
| Worst per-game p99 decision time; lowest time bank | 602 ms; 587 of 600 s |
| 200-game blocks (wins–losses), ratings 582–742 | 103–95, 103–97, 104–95, 105–93, 97–102 |
| Last night's layer vs the earlier pilot, 4,575 replayed decisions (its Boss's Orders rules could not fire there) | 4.28% changed, 0 exceptions |
| Three byte-identical resubmissions of the earlier champion | 783 to 747, a 36-point spread |

### 5. How we know: an instrument calibrated against the real ladder

Apart from the Dusknoir head-to-head, none of the numbers above come from self-play, because self-play flatters. When different agents piloted the same opposing deck, our own pilot's benchmark overstated the win rate by +62 points against a strong public agent, by +41 against the host's sample and by +8 against a teammate's July build (N=300 each; upper bounds) [#1, Fig. 4]. The host's sample Lucario agent is itself a ladder opponent, 60 cards of 60, and our win rate against it (44.0%, N=300) agrees with the ladder's (50%, N=14, CI 26–74) [#2].

The instrument then had to predict. We borrowed the discipline psychology adopted after its replication crisis: predictions registered before the data, kill criteria fixed in advance (Nosek et al., 2018). Before each of four submissions we registered the calibrated number and the self-play number and let the ladder arbitrate (Fig. 5). Self-play fell outside the ladder's confidence interval four times out of four; the calibrated figure fell inside, with deviations −2.0 / +2.5 / −12.1 / −11.1 points and no systematic sign [#3]. With N≈20 covered games those intervals are ±19 points wide, so they rule out gross miscalibration only. Among the public analyses we could find, none had registered a ladder prediction before reading replays [#3].

The engine lookahead is worth +13.62pt on that instrument (N=3,200 per arm), and a sham lookahead +0.42pt [#26, Fig. 6], measured in July, before any of its gates existed. The greedy layer's one measured rule, Ignition Energy attached to the evolved attacker rather than a Basic, added +2.50pt (replications +2.18 / +2.81) [#5] and converted 85% (56/66) of production attachments into the intended attack [#6].

### 6. What we did not measure, and what we got wrong

The submitted agent's effect size was not measured before the deadline; the effect sizes above belong to earlier pilots and decks, and the last night's rules cleared only the safety gates (no crash, 98.75% against random, a legal move on every decision) [#38]. We spent the final slot on it deliberately: a third Boss's Orders had measured negative under a pilot that could not use it, and only production could test the card with its rules, so we froze the behavioural predictions first. We measured it afterwards, on the same instrument, against the list our discipline would have submitted: **−3.29pt (95% CI [−5.19, −1.39])**, negative in all five matchups, worst against Mega Lucario (−7.62) [#50]. Holding the deck fixed and swapping only the pilot isolates the last night's rules: −2.78pt (95% CI [−3.97, −1.59]) [#52]. We submitted the weaker agent; the instrument measured it afterwards.

That night we also doubled, five to ten and unmeasured, the hard-coded list of opponent decks the lookahead samples from, although an earlier repair of that dictionary had been killed for misidentifying decks outside it (11%→22% pooled) [#43, #48]. One rule and one gate of that layer were wired to a selection type the engine never issued and did nothing in 1,000 games [#49].

The instrument's limits are in the caption of Fig. 4 [#22, #44]. Inside the team, Ryohei Hara built a second pilot independently, with no shared code, computing exactly what this turn can reach with hypergeometric odds and nothing beyond it; it converged on the same mono-Water list, and its blind spot was the next turn where ours was the same turn (Fig. 8) [#41].

### 7. Conclusion

If a deadline forces an unmeasured change, freeze the behavioural predictions first, measure it afterwards anyway, and publish both; ours came back negative. A card is worth what the deck, the pilot and the field make of it, and an AI pilot changes all three: the human list lost three of its orthodoxies to measurement, the human value ordering for Boss's Orders changed 809 decisions in the direction a player would choose [#39] and still shipped inside a bundle that measured worse than the list our rule would have submitted [#50], and the lookahead that adds +13.62pt [#26] is also where every unguarded mistake came from.

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

---

# v5保留分(台帳行が立ってから本文へ。出典スクリプトは全て replay_analysis/ に永続化済み)

> **v6(2026-08-14)**: L-a/L-b は**取り下げ**(ゆうじ承認)。語数枠は§2退却物語に振替。
> 台帳行は生存しており、9月の清書で余語が出れば下記の検算済み文をそのまま復活できる。

**必要な台帳行(起票案、ラベルはチーム判断)**:
- L-a: サイド経済 — 総取得230vs229(56戦)/KOあたり1.35vs2.18枚/勝利中央値4KOターン・敗北3。
  確証(計数)。出典 `prize_race.py` → `prize-race.md`。※最終KOは観測に現れず補完(手法注記あり)
- L-b: 二峰性+着地一貫性 — 完封17/56(勝10負7)、完封負けの立ち上がり指標は完封勝ちと同一
  (初手たね1.3vs1.4、Mega着地T3.2vs3.1)、**Mega着地55/56**。確証(計数)。出典 `shutout_anatomy.py`
- L-c: 台帳#9の機構文訂正 — マリガンペナルティは実装あり(SetupProc.h: 相手が0..N追加ドロー)。
  EXP7の実測結論(単調悪化)は不変
- L-d: 打点誤差の局在 — FML×{M}下0%(21/21が−30)/それ以外98.7-100%。出典 `damage_pairing_diff.py`
  (※シフト補正済みペアリング、`semantic_check.py` でattack 240/240・play 715/715整合確認)
- L-e: NZ未知壁 — Neutralization Zone(1247, ACE SPECスタジアム)は評価器の不可視壁。
  出現2/56戦で2敗(うち1つは5-0からの唯一の山札切れ)。計器4本に不在=効果測定不能のため凍結内では不修正

**L-a/L-b が立ったら入れる本文(検算済み語数)**:

§4冒頭差し替え(+15語):
> Our list is a Mega Starmie ex aggro build with a single commitment — maximum setup
> consistency, spent on an asymmetric prize race: Mega Starmie was online by turn 3–4 in
> **55 of 56** ladder games, win or lose. Everything else was removed, and every removal was
> forced by measurement rather than theory.

§4末尾に追加(+70語、55/56は冒頭に移したので削除済み版):
> Replay accounting then measured the plan's shape. Prizes traded even — **230 vs 229** across
> 56 games — inside an asymmetric geometry: our KOs average **1.35** prizes, theirs **2.18**;
> we need a median of four KO-turns to win, they need three. The deck compensates by frequency,
> not by pivoting: **17 of 56** games were one-directional shutouts. The gust repair for
> targeting had already measured ±0 [#24]: the deck accepts the asymmetric race because the
> fix does nothing.

**語数会計(実測)**: v5本文=**1,998語**(C2=eviction圧縮適用済み。適用前2,021で上限超過だった)。
上記2件(+85)を入れる前に残りの圧縮 C1(§3自己監査3段目 −55)/C3(§6辞書修理 −30)/
C4(§6 v3 −18)/C5(§2冒頭 −12) = **−115が必須**。着地見込み ≈1,969語。
さらに安全域(≤1,950)が欲しければ §3 Half-one と §1 から −25。

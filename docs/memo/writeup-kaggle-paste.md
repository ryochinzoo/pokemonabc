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

This report is about one agent. Its deck is mono-Water Mega Starmie ex: two species, four Basic Pokémon, sixty cards. Its pilot is a hand-written greedy evaluator, fourteen rules a human player taught it, and a 0.6-second engine lookahead that may overrule the greedy choice behind eight one-way gates (Fig. 1). Over its last 1,000 ladder games it won 51.2%, finished at 656.7, rank 2,898 of 6,807 and above the field's median of 621.5 (Fig. 10), and never crashed.

The report has one idea: a card is worth nothing by itself. Its value belongs to the deck, the pilot and the field together, so we measured the three parts separately: the deck against its human-orthodox parent, the pilot on an instrument calibrated against the real ladder, the field by reading the last 1,000 replays.

### 2. The deck and its plan

The list (Fig. 2) differs from its human-orthodox parent by twelve cards (Fig. 9). The plan is a race built on one number: Jetting Blow costs a single Water. Mega Starmie ex takes three prizes from an opposing Mega ex, or two from an ex and one from a Basic with the 50-damage bench splash; Wally's Compassion heals it fully and returns its energy, which costs one attachment when the attack needs one, and it was played 755 times in 1,000 games, every time on a damaged Mega Starmie ex. Ignition Energy alone pays for the three-energy Nebula Beam (210), the finisher and the only attack that goes through a Crustle's Mysterious Rock Inn; Surfing Beach is its only switch. Jetting Blow was 71.4% of its attacks, Nebula Beam 18.5%; the paper plan was a 210-damage deck and the replays say it is a 120-plus-50 deck.

Measurement rejected three human-orthodox choices. The Dusknoir sacrifice engine takes six slots in most human lists, and our own forecast from the coaching canon, written down before the run, was that cutting it would cost 5 to 10 points; the list without it won 64.7% head-to-head (N=150). Cinderace energy acceleration, tried and dropped, saw 0.12 uses per game in our hands, while another team runs it as the core of a 74.4% agent, so that failure belongs to our pilot and not to the card. Eight or ten Basics instead of four cut the mulligan rate from 60.1% to 25.9% and did not help, 34.5 → 33.0 → 31.2 on the calibrated composite (a screening run, Fig. 2), so the list mulligans 60% of the time on purpose, 59.9% in production; games with a mulligan won 4.4 points less, an interval that includes zero. Kahneman and Klein (2009) trust expert intuition only where the expert has had fast feedback from a regular environment; the coaching canon's feedback came from human pilots, none from this one, so we measured each orthodoxy.

The August list ran two Boss's Orders; a third copy, the most-adopted card among the 105 top-band teams we crawled, measured −1.53pt with the pilot byte-identical. That pilot had no idea whom to drag out. The final list runs three, with the targeting rules of §3; the effect of that combination, measured after the deadline, is in §6.

### 3. How it plays a turn, and where it disobeys itself

Turn ten of a ladder game against Mega Lucario ex (Fig. 12). Our Mega Starmie ex sits at 60 HP with one Water; the opponent's Mega Lucario ex, wearing Hero's Cape, is at 90 of 440, two prizes from winning against our four; our hand is Buddy-Buddy Poffin and Boss's Orders. Jetting Blow for 120 knocks it out for three prizes. The agent played Boss's Orders instead, dragged the 80-HP Makuhita forward and took one; a Mega Lucario ex answered with Aura Jab for 130 and the game, as it would have answered the three-prize line. It is here as the misfire at its simplest: three prizes on the table, one taken.

The value ordering it should have used is the one a player uses, and it is in the code: knock out what you can knock out now, most prizes first; failing that, drag out the piece that will evolve into a threat, Riolu before it becomes Mega Lucario; failing that, the piece that cannot retreat, so the opponent's energy attachment is held hostage. Over the last 1,000 games the agent's 809 Boss's Orders went to knock-outs 577 times, to evolving threats 184 times, to bound targets 16 and to the weakest piece 32. The turn above is not a failure of the ordering. The greedy layer did not propose Boss's Orders; the engine lookahead overrode it into Boss's Orders, and the gates let it: every gate protects the greedy choice from the lookahead, and none stops the lookahead from reaching for Boss's Orders on its own (Fig. 1).

The same unguarded direction had shown up before. In July a replay caught the agent retreating a fully-powered attacker instead of attacking a Mega Lucario it could not one-shot: on that board the production pilot chose RETREAT 12 of 12 times while the greedy layer said ATTACK, because an override margin of 120 sat against a prize term of ±10,000 and gated nothing. We repaired it, reproduced ATTACK 12 of 12, and the bundle it shipped in, a pilot layer plus a twelve-card deck change, measured +6.03pt (N=6,400, pre-registered); then the registered falsification sensor fired, the matchup where retreat is most frequent got worse by 1.37pt, so we kept the bundle and withdrew the mechanism story. Repairing a mechanism and moving a rating are different proofs.

The audit of the last 1,000 games (Fig. 7): 0 crashes, 0 END-stalls in 24,429 decisions, targets matching the rule's own first choice 809 of 809, and the one falsifiable prediction failed: 49 of 809 Boss plays were misfires by the rule's own count, every one a lookahead override. We wrote the Boss's Orders rules on the last night before the deadline and froze seven behavioural predictions first. Outside review then found its blind spot: the knock-out test used the printed maximum, 210, and ignored attached energy; counting energy, 243 of the 809 targets change status, 709 (87.6%) remain the best target and 30 plays remain misfires. The fix, measured after the deadline on the calibrated instrument: −2.42pt (95% CI [−5.85, +1.01]), a correct diagnosis and no detectable improvement.

### 4. Robustness, and where it still loses

The rating is an average over opponents it meets at different rates (Fig. 3): earned against walls and Dragapult, lost to its two most frequent opponents.

| Opponent, last 1,000 games | Record | Win rate |
|---|---|---|
| Wall decks (Crustle) | 94–16 | 85.5% |
| Dragapult ex | 68–31 | 68.7% |
| Alakazam | 113–86 | 56.8% |
| Mega Starmie ex (mirror) | 25–30 | 45.5% |
| Marnie's Grimmsnarl ex | 29–44 | 39.7% |
| Mega Lucario ex | 78–138 | 36.1% |
| Archaludon ex | 29–79 | 26.9% |

The two losing matchups have mechanisms we can name. Mega Lucario ex deals 400 in two turns, Mega Brave then Aura Jab, while Mega Starmie ex needs three Jetting Blows for its 340, and Nebula Beam plus Jetting Blow is 330, ten short; that is why the Boss's Orders ordering folds Riolu early, 184 of its 809 targets across all opponents. Archaludon ex gives two prizes for our three and takes them in two Metal Defenders, so on paper every trade there is two-for-three against us. The five matchups the instrument covers sum to 41.8% against 51.2% overall: the agent earns its rating outside the instrument's coverage, a limit of the instrument as much as of the deck.

It does depend on the start of the game (Fig. 11): 57.7% going first, 40.1% going second, first in 64.9% of games. The seat effect is the environment's more than the deck's: whoever went first won 58.5% of these games. A quarter of its losses ended without a prize taken, and Mega Starmie ex was on the board by its own second turn in 92.0% of wins against 74.3% of losses, going second 90.7% against 65.1%. Its opponents' median rating was 651.6.

What did hold, over the same 1,000 games:

| Consistency check | Result |
|---|---|
| Crashes or stderr | 0 in 1,000 games |
| Worst per-game p99 decision time; lowest time bank | 602 ms; 587 of 600 s |
| 200-game blocks (wins–losses), ratings 582–742 | 103–95, 103–97, 104–95, 105–93, 97–102 |
| Last night's layer vs the earlier pilot, 4,575 replayed decisions (its Boss's Orders rules could not fire there) | 4.28% changed, 0 exceptions |
| Three byte-identical resubmissions of the earlier champion | 783 to 747, a 36-point spread |

### 5. How we know: an instrument calibrated against the real ladder

Apart from the Dusknoir head-to-head, none of the numbers above come from self-play, because self-play flatters. When different agents piloted the same opposing deck, our own pilot's benchmark overstated the win rate by +62 points against a strong public agent, by +41 against the host's sample and by +8 against a teammate's July build (N=300 each; upper bounds). The host's sample Lucario agent is itself a ladder opponent, 60 cards of 60, and our win rate against it (44.0%, N=300) agrees with the ladder's (50%, N=14, CI 26–74).

The instrument then had to predict. We borrowed the discipline psychology adopted after its replication crisis: predictions registered before the data, kill criteria fixed in advance (Nosek et al., 2018). Before each of four submissions we registered the calibrated number and the self-play number and let the ladder arbitrate (Fig. 5). Self-play fell outside the ladder's confidence interval four times out of four; the calibrated figure fell inside, with deviations −2.0 / +2.5 / −12.1 / −11.1 points and no systematic sign. With N≈20 covered games those intervals are ±19 points wide, so they rule out gross miscalibration only. Among the public analyses we could find, none had registered a ladder prediction before reading replays.

The engine lookahead is worth +13.62pt on that instrument (N=3,200 per arm), and a sham lookahead +0.42pt, measured in July, before any of its gates existed. The greedy layer's one measured rule, Ignition Energy attached to the evolved attacker rather than a Basic, added +2.50pt (replications +2.18 / +2.81) and converted 85% (56/66) of production attachments into the intended attack.

### 6. What we did not measure, and what we got wrong

The submitted agent's effect size was not measured before the deadline; the effect sizes above belong to earlier pilots and decks, and the last night's rules cleared only the safety gates (no crash, 98.75% against random, a legal move on every decision). We spent the final slot on it deliberately: a third Boss's Orders had measured negative under a pilot that could not use it, and only production could test the card with its rules, so we froze the behavioural predictions first. We measured it afterwards, on the same instrument, against the list our discipline would have submitted: **−3.29pt (95% CI [−5.19, −1.39])**, negative in all five matchups, worst against Mega Lucario (−7.62). Holding the deck fixed and swapping only the pilot isolates the last night's rules: −2.78pt (95% CI [−3.97, −1.59]). We submitted the weaker agent; the instrument measured it afterwards.

That night we also doubled, five to ten and unmeasured, the hard-coded list of opponent decks the lookahead samples from, although an earlier repair of that dictionary had been killed for misidentifying decks outside it (11%→22% pooled). One rule and one gate of that layer were wired to a selection type the engine never issued and did nothing in 1,000 games.

The instrument's limits are in the caption of Fig. 4. Inside the team, Ryohei Hara built a second pilot independently, with no shared code, computing exactly what this turn can reach with hypergeometric odds and nothing beyond it; it converged on the same mono-Water list, and its blind spot was the next turn where ours was the same turn (Fig. 8).

### 7. Conclusion

If a deadline forces an unmeasured change, freeze the behavioural predictions first, measure it afterwards anyway, and publish both; ours came back negative. A card is worth what the deck, the pilot and the field make of it, and an AI pilot changes all three: the human list lost three of its orthodoxies to measurement, the human value ordering for Boss's Orders changed 809 decisions in the direction a player would choose and still shipped inside a bundle that measured worse than the list our rule would have submitted, and the lookahead that adds +13.62pt is also where every unguarded mistake came from.

<!-- ↓ Kaggle 本文末尾の「Figure captions」表の中身(表なので語数外) -->

1. Fig. 1 — How the pilot chooses an action: a greedy evaluator and fourteen human-taught rules propose a move; a 0.6-second engine lookahead may override it; eight one-way gates block the overrides we had seen go wrong. Prior art: search over a hand-written evaluation won every Legends of Code and Magic contest until deep RL took over (Kowalski & Miernik 2023, IEEE CoG); heuristic-guided MCTS led the Hearthstone AI Competition (2018–2020); LLM agents on this game are harness-sensitive (PTCG-Bench, arXiv:2605.29653, 2026).
2. Fig. 2 — The 60-card list and its plan: the one-energy 120 + 50 attack is 71% of all attacks in the last 1,000 ladder games, the 210 attack is the finisher, four Basics were chosen by measurement, and Deluxe Bomb is the ACE SPEC (a Belt in its place measured −0.57pt, 95% CI −2.82 to +1.68).
3. Fig. 3 — Win rate by opponent archetype over the last 1,000 ladder games (n ≥ 55 shown, overall 51.2%).
4. Fig. 4 — Self-play overstates win rate by +8 to +62 points depending on who really pilots the opposing deck (July 21 agent, N = 300 per bar). Limits of the instrument built on it: the +2.0pt adoption threshold sits inside the ladder's non-transitivity residual (6.2pp); calibration is validated only in the 700–799 band and anchors on the host's sample pilot; the benches share one process, and the sham control excludes only contamination above 3.68pt.
5. Fig. 5 — Four submissions, four predictions registered before reading any replay: the calibrated figure fell inside the ladder's confidence interval each time, the self-play figure outside. The discipline is psychology's after its replication crisis (Nosek, Ebersole, DeHaven & Mellor 2018, PNAS 115:2600). The adoption rule was audited too: four independent non-regression gates flagged a zero-effect change as a regression 65.1% of the time; the composite that replaced them has a +2.0pt threshold of only ~1.09σ, so confidence intervals became mandatory.
6. Fig. 6 — The engine-lookahead layer ablated on the calibrated instrument: +13.62pt (95% CI +11.40 to +15.84, N = 3,200 per arm), measured in July before its gates existed; a sham lookahead measured +0.42pt. Our largest negative result, rejecting a general Monte-Carlo rewrite, did not survive re-examination on the same instrument (+2.62pt, CI −0.68 to +5.93).
7. Fig. 7 — The final agent, last 1,000 games: the gates held by construction, one frozen prediction failed (49 of 809 Boss's Orders plays misfired, every one a lookahead override), outside review found the energy-blind knock-out test, and the post-deadline measurement is −3.29pt against the list our discipline would have submitted.
8. Fig. 8 — Two development lines in one team, ours and Ryohei Hara's, placed their look-ahead in different cells and failed in different cells; both converged on mono-Water independently.
9. Fig. 9 — From the human-orthodox parent list to the submitted one: twelve cards, each with a measurement or a reason. The Dusknoir engine went against our own pre-run forecast from the coaching canon (−5 to −10 predicted, +14.7 measured). Expert intuition is reliable only with rapid feedback from a regular environment (Kahneman & Klein 2009, American Psychologist 64:515); no one had such feedback about an AI pilot.
10. Fig. 10 — Final ratings of all 6,807 teams (public leaderboard, Sep 1): the submission's 656.7 sits above the median of 621.5 at rank 2,898; 90% of teams finished below 853.5.
11. Fig. 11 — Where the final agent depends on the start of the game, last 1,000 ladder games: 57.7% going first, 40.1% going second, while whoever went first won 58.5%; a mulligan in 59.9% of games, and games with a mulligan won 4.4 points less (95% CI −1.9 to +10.7); Mega Starmie ex on the board by its own second turn in 92% of wins and 74% of losses; 44.4% against opponents above 700. Organizers of AI card-game competitions neutralise first-player advantage by running both seat orders (Kowalski & Miernik 2023); the ladder does not.
12. Fig. 12 — Turn ten of ladder game 102267456 in the official visualizer, before the agent acts: the opponent's Mega Lucario ex (top) at 90 of 440 HP with Hero's Cape, our Mega Starmie ex (bottom) at 60 HP with one Water, Buddy-Buddy Poffin and Boss's Orders in hand, prizes 4 to 2 against us. Jetting Blow for 120 takes three prizes; the agent played Boss's Orders on the 80-HP Makuhita, and a Mega Lucario ex answered with Aura Jab for 130 either way. Host's visualizer screenshot, used as permitted.

<!-- ↓ Media Gallery の画像タイトル(≤255 字) -->

1. Fig. 1 — How the pilot chooses an action: greedy evaluator + fourteen human-taught rules propose; a 0.6 s engine lookahead may override; eight one-way gates block known-bad overrides. Kowalski & Miernik 2023; Hearthstone AI Competition; PTCG-Bench.
2. Fig. 2 — The 60-card list and its plan: the one-energy 120 + 50 attack is 71% of attacks in the last 1,000 ladder games; the 210 attack is the finisher; four Basics by measurement; Deluxe Bomb is the ACE SPEC (a Belt instead: −0.57pt, CI −2.82 to +1.68).
3. Fig. 3 — Win rate by opponent archetype over the last 1,000 ladder games (n ≥ 55 shown, overall 51.2%).
4. Fig. 4 — Self-play overstates win rate by +8 to +62 points depending on who pilots the opposing deck (July 21 agent, N = 300 per bar). Limits: +2.0pt threshold inside the ladder's 6.2pp non-transitivity; validated only in the 700–799 band.
5. Fig. 5 — Four submissions, four predictions registered before reading any replay: calibrated figure inside the ladder's CI each time, self-play outside (Nosek et al. 2018, PNAS 115:2600). Adoption rule audited: four gates false-alarmed 65.1%.
6. Fig. 6 — The engine-lookahead layer ablated on the calibrated instrument: +13.62pt (95% CI +11.40 to +15.84, N = 3,200 per arm), July, before its gates existed; sham lookahead +0.42pt. A rejected Monte-Carlo rewrite re-measured at +2.62pt.
7. Fig. 7 — The final agent, last 1,000 games: the gates held, one frozen prediction failed (49 of 809 Boss's Orders plays misfired, all lookahead overrides), outside review found the energy-blind knock-out test, and the post-deadline measurement is −3.29pt.
8. Fig. 8 — Two development lines in one team, ours and Ryohei Hara's, placed their look-ahead in different cells and failed in different cells; both converged on mono-Water independently.
9. Fig. 9 — From the human-orthodox parent list to the submitted one: twelve cards, each with a measurement or a reason. The Dusknoir engine went against our own pre-run forecast (−5 to −10 predicted, +14.7 measured); cf. Kahneman & Klein 2009 on intuition.
10. Fig. 10 — Final ratings of all 6,807 teams (public leaderboard, Sep 1): the submission's 656.7 sits above the median of 621.5 at rank 2,898; 90% of teams finished below 853.5.
11. Fig. 11 — Start-of-game dependence, last 1,000 games: 57.7% going first vs 40.1% second (whoever went first won 58.5%); mulligan in 59.9% of games, −4.4pt with CI including zero; Mega Starmie ex out by its own second turn in 92% of wins, 74% of losses.
12. Fig. 12 — Turn ten of ladder game 102267456 in the official visualizer: the opponent's Mega Lucario ex (Hero's Cape) at 90 of 440, our Mega Starmie ex at 60 with one Water, Poffin and Boss's Orders in hand, prizes 4–2 against us.

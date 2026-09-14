<!-- 公開 Kaggle ノートブック(著者 busyaprime)の markdown セルのみを研究目的で転記(2026-09-09、kaggle kernels pull)。出典: https://www.kaggle.com/code/busyaprime/last-submission-aug-16-the-top-is-still-rising
     コード・画像は省略。引用は 15 語以内・出典明記の範囲で。提出物への転用禁止(CLAUDE.md の steel_agent と同じ扱い)。 -->

# Last submission: Aug 16. The top is still rising.

Every team in this competition stopped writing code on the same day. The final public
leaderboard has 6807 teams on it and not one of them submitted after **2026-08-16**. The
leaderboard file the competition API hands out timestamps the last of those final
submissions at 23:58:53 that evening. The deadline the competition page showed,
2026-08-31, was the results date, not the submission date.

The host kept publishing a fresh dump of games every single day until 2026-08-30, so
there are fourteen days of a competition running with the field frozen solid, which is a
rare thing to be able to look at: the agents cannot learn, cannot be patched, cannot
react. Only the matchmaking and the dice change.

Three things come out of those fourteen days, and the third is the one that will change
how you read this competition's own published numbers:

1. **The top average score went up 67.5 points after the last line of code was written**,
   comparing the seven days before the freeze with the fourteen days after it.
2. **The gap between the top and the median widened by 13.9 percent** across the freeze,
   after narrowing all through July. The field converged while it could still copy, and
   came apart once it could not.
3. **The daily episode count is a byte quota, not a headcount.** Every dump is 20 GiB to
   within 0.26 percent, 75 days out of 76. Episodes per day fell 40.5 percent only
   because the average episode grew 68.1 percent. Nothing about participation changed.

At the end there is a function you can paste anywhere: give it a score and it tells you
where that score finishes, out of 6807, in a field that can no longer move.

Everything here recomputes from two attached tables, and both of them are now final.


## 1. The two tables

`kaggle/pokemon-tcg-ai-battle-episodes-index` is the host's own file. It has one row per
day: how many episodes were dumped, how many bytes they came to, and the top and median
average score across them. The final index has 76 days, 2026-06-16 to 2026-08-30.

The second table is derived from the competition's final leaderboard, which the API hands
to anyone. It carries no team name and no member name, only two aggregates: how many
teams made their final submission on each date, and the score at each rank. That is
everything the figures below need and nothing that identifies anybody.


## 2. The palette, and a rule that is not about distance

Five series colours, picked by a greedy max-min search over a grid of candidate hues,
keeping the set whose closest pair is furthest apart in the **worst** of four views: ordinary vision plus deuteranopia,
protanopia and tritanopia. The cell prints the closest pair per view, so that claim is
checkable rather than asserted.

One detail matters more than the palette. Simulating colour blindness needs a different
algorithm per kind. The 1999 single-matrix simplification is accurate for protanopia and
deuteranopia and **is not valid for tritanopia**, which needs the two half planes of
Brettel 1997 with the half chosen per colour. Getting that wrong does not merely misreport
a number; used as the objective of a palette search it steers the search, because a bad
blue-yellow model does not punish the blue-magenta region.

So the rule enforced on every figure here is not that colours are far apart, because the
measurement of "far apart" is itself something that can be quietly wrong. It is that
**colour is never the only channel**: the audit has six defect classes and the sixth fails
any figure that draws a series in a colour named nowhere in text or legend.


## 3. The day everybody stopped

The competition page showed 2026-08-31 as the deadline; that was the results date. The
submission deadline had already gone, and the leaderboard remembers exactly when.


## 4. What a frozen ladder did next

Now the interesting part. Nobody can change anything, and the numbers keep moving.

An agent's daily average is not a property of the agent alone. It is the outcome of who
it was matched against, in what order, with what deck draws. When the field stops
changing, every remaining movement is that, and this is the only window in the whole
competition where it can be seen on its own.


The top rising while frozen is the headline, but the shape underneath it is the better
finding. Watch what the distance between the best and the middle does.


That reverses something I published myself. An earlier notebook of mine on a different
arena,
[The Arena Ladder Compressed In 18 Days](https://www.kaggle.com/code/busyaprime/the-arena-ladder-compressed-in-18-days),
found only the compression, and compression was real here too: the gap falls from 397 to
92 across July as the field copies whatever works. What I did not have then was the other
half. Once copying stops, the gap goes back the other way, and it does it without a
single line of new code.


## 5. The number that is not what it looks like

The index reports an episode count per day. It has fallen by about forty percent since
June, and the obvious reading is that fewer games are being played.

That reading is wrong, and the file says so itself.


Every dump is the same size to within 0.26 percent, and that is the whole argument. The
episode count is not a measure of anything the players did: it is 20 GiB divided by the
size of an episode.

The rank correlation is worth being careful about rather than proud of. Megabytes per
episode is computed here as total bytes divided by episode count, so correlating one
against the other is correlating x with c/x, and a rank correlation near minus one is
guaranteed by that construction before any data is looked at. It comes out at -0.9998
over the 75 full days rather than exactly -1 only because the dump size is near-constant
instead of constant. Run the same one-liner over all 76 rows, including the partial first
day, and you get -0.9219 instead. None of those three numbers is the evidence. The
evidence is that the divisor does not move.

If you are building anything on top of this index, that matters: normalise by bytes, not
by episodes.


## 6. Two medians, both correct

One more trap in the same file, and it is 476 points wide.


## 7. Where a score finishes

The field is frozen, so this is not an estimate. Paste in a score and the answer is final.


The middle of that table is where the competition actually lives. Around a score of 1000,
18 teams sit within five points of each other and the next rank up is 0.10 points away,
so a difference far smaller than a single game's noise separates dozens of places.

## 8. What to take from this

**The submission deadline and the deadline on the page are not the same date.** Check the
leaderboard's own final submission timestamp before you plan around a competition's dates.

**A frozen field is a free measurement.** Every point the ladder moved across the fourteen
frozen days is matchmaking and variance, not skill, and there is no other stretch of this
competition where those two can be separated.

**Do not read the episode count as participation.** It is a byte quota. Normalise by
bytes or you will report the opposite of what happened.

**Two medians in the same file can both be right, and they are not on one ruler.** The
leaderboard median and the dump's median differ by 476 points because they describe
different populations, and the dump's daily top exceeds the best final leaderboard score
on 2 of the 76 days, which tells you they are also different statistics.

If a number here disagrees with a figure, the figure is right and I made a mistake. Tell
me in the comments and I will fix it.

## Sources

- [`pokemon-tcg-ai-battle-episodes-index`](https://www.kaggle.com/datasets/kaggle/pokemon-tcg-ai-battle-episodes-index),
  the host's own daily index, final at 76 rows
- [`ptcg-ai-battle-frozen-field`](https://www.kaggle.com/datasets/busyaprime/ptcg-ai-battle-frozen-field),
  two aggregates derived from the final public leaderboard, with no team or member names
  in them
- [What actually wins on the ladder](https://www.kaggle.com/code/busyaprime/what-actually-wins-on-the-ladder),
  an earlier notebook of mine on this competition, built on the episodes of 2026-07-31

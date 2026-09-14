<!-- 公開 Kaggle ノートブック(著者 hosikusa)の markdown セルのみを研究目的で転記(2026-09-09、kaggle kernels pull)。出典: https://www.kaggle.com/code/hosikusa/optimization-of-deck-and-agent-scores-using-a-gene
     コード・画像は省略。引用は 15 語以内・出典明記の範囲で。提出物への転用禁止(CLAUDE.md の steel_agent と同じ扱い)。 -->

**Summary**

The Pokémon Trading Card Game has an enormous number of possible deck combinations, and there are likewise countless scoring values that an AI agent can use to decide actions, making it difficult for humans to tune them to a given competitive environment.
Because the cards in a deck and the AI agent’s scoring parameters are scalar values, we believed mathematical optimization could be applied to produce better decks and agents. We used a genetic algorithm, a canonical optimization method, to optimize both the decks and the scores used by the agents.

**Program Overview**

![](https://www.googleapis.com/download/storage/v1/b/kaggle-user-content/o/inbox%2F35325620%2F1a0bb8cc6b345d6407de8cb920ac9145%2FScreenshot%202026-08-08%20153249.png?generation=1786170808676858&alt=media)

*1 deck.json
{
  "Kyogre": [721, 2, 2, 4],
  "Snover": [722, 4, 3, 4],
  "Mega_Abomasnow_ex": [723, 4, 3, 4],
  "Ultra_Ball": [1121, 4, 3, 4],
  "Precious_Trolley": [1126, 1, 1, 1],
  "Carmine": [1192, 4, 2, 4],
  "Lillie_Determination": [1227, 4, 2, 4],
  "Surfing_Beach": [1262, 3, 2, 4],
  "Basic_Water_Energy": [3, 32, 30, 40]
}

This file contains the design variables you want to optimize (the deck).
Each entry is defined as:
[Card ID, Initial Count, Minimum Count, Maximum Count]
These values are specified for every card.

*2 scores.json
{
  "Score_1": [100,100,50,200,5],
  "Score_2": [20,20,10,40,1],
  "Score_3": [10,10,5,20,1],
...
  "Score_36": [90,90,45,180,5],
  "Score_37": [100,100,50,200,5],
  "Score_38": [100,100,50,200,5]
}

This file contains the design variables you want to optimize for the rule‑based agent (the scores).
Each score is defined as:
[Initial Value, Current Value, Minimum Value, Maximum Value, Step Size]
These values are specified for every score parameter.

*3 replays
This directory stores the battle result logs.

*4 run_battle.py
This is the local battle program used to simulate matches.

*5 best_individual.json
This file stores the optimization result.
It contains the combination of design variables (deck + score parameters) that achieved the highest number of wins, which is the objective function.

*6 Opt.py
This is the optimization program.
The following constants allow you to configure the optimization:

![](https://www.googleapis.com/download/storage/v1/b/kaggle-user-content/o/inbox%2F35325620%2F41a2a5b8938c671950e24fd7e66c4440%2F1.png?generation=1786174006618122&alt=media)

These parameters control how the optimization process runs.

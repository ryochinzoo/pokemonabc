<!-- 公開 Kaggle ノートブック(著者 uentsz)の markdown セルのみを研究目的で転記(2026-09-09、kaggle kernels pull)。出典: https://www.kaggle.com/code/uentsz/team-pokesonic-361st-rule-based-grimmsnarl-agent
     コード・画像は省略。引用は 15 語以内・出典明記の範囲で。提出物への転用禁止(CLAUDE.md の steel_agent と同じ扱い)。 -->

[embedded image omitted]

# Rule-based Grimmsnarl Agent (361st/6807 teams, score 921.2)

This notebook publishes the full source of our rule-based Marnie's Grimmsnarl ex agent,
and builds the `submission.tar.gz` from it.

The agent is not a single file. It is a deck package (`kasai.grimmsnarl.v560`) sitting on
top of **Agent Kernel**, a shared foundation for the rule-based agents our team built —
84 Python files in total, plus 1367 JSON files of card metadata that the
Kernel reads at runtime. That does not fit in a notebook cell, so the code lives in an
attached dataset and this notebook assembles it.

- **Source code**: the `grimmsnarl-agent-with-agent-kernel-v5-6-7` dataset attached to this notebook. Browse it file
  by file from the *Input* panel on the right.
- **Design writeup**: how Agent Kernel represents and compares decisions, and where it
  falls short — see the linked discussion topic.

## What is in the dataset

| Path | Contents |
|---|---|
| `main.py` | Entry point. Wiring only; it hands control to the Kernel |
| `kasai/grimmsnarl/v560/` | The deck: board representation, turn goals, matchups, option scoring |
| `ptcg_ai/agent_kernel/` | Agent Kernel: the `Decision` type, phase derivation, match memory, board evaluation |
| `ptcg_ai/deck_inference/` | Opponent archetype estimation |
| `data/` | Card metadata, archetype definitions, and the deck-inference snapshot read at runtime |
| `spec.md`, `concept.md` | Design notes for the deck |

## Decklist

| # | Card | ID |
|---:|---|---:|
| 10 | Basic {D} Energy | 7 |
| 4 | Marnie's Impidimp | 646 |
| 4 | Munkidori | 112 |
| 4 | Buddy-Buddy Poffin | 1086 |
| 4 | Poké Pad | 1152 |
| 4 | Team Rocket's Petrel | 1219 |
| 4 | Lillie's Determination | 1227 |
| 4 | Spikemuth Gym | 1259 |
| 3 | Marnie's Morgrem | 647 |
| 3 | Marnie's Grimmsnarl ex | 648 |
| 3 | Rare Candy | 1079 |
| 3 | Night Stretcher | 1097 |
| 2 | Snorunt | 860 |
| 2 | Froslass | 104 |
| 2 | Boss’s Orders | 1182 |
| 1 | Unfair Stamp | 1080 |
| 1 | Pokégear 3.0 | 1122 |
| 1 | Tool Scrapper | 1137 |
| 1 | Dawn | 1231 |


## Build the submission

The agent code comes from the attached dataset; the `cg` library comes from the
competition's own dataset. Both are copied into one directory and packed into
`submission.tar.gz`.

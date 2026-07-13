---
name: lookup-card
description: Look up Pokémon TCG card data by Card ID, name, or type from EN_Card_Data.csv / JP_Card_Data.csv. Use when building or analyzing a deck, checking a card's HP/type/attacks/effect, or resolving a card ID seen in an Observation.
---

# lookup-card

Query the card reference data in this repo. Two CSVs at the repo root, one row per card,
2102 cards each, sharing the same Card ID space:
- `verification/data/EN_Card_Data.csv` — English (default)
- `JP_Card_Data.csv` — Japanese

Columns (identical in both):
`Card ID, Card Name, Expansion, Collection No., Stage (Pokémon)/Type (Energy and Trainer),
Rule, Category, Previous stage, HP, Type, Weakness, Resistance (Type), Retreat, Move Name,
Cost, Damage, Effect Explanation`

Notes on the data:
- Types use brace codes, e.g. `{G}` grass, `{R}` fire, `{W}` water, `{L}` lightning,
  `{P}` psychic, `{F}` fighting, `{D}` darkness, `{M}` metal, `{C}` colorless.
- A multi-attack card spans **multiple rows** with the same Card ID; the Move Name / Cost /
  Damage / Effect columns differ per row, other columns repeat.
- `n/a` or empty cells mean the field doesn't apply (e.g. HP for Trainer/Energy cards).

## How to look up

Use the repo root as the working directory. Prefer `verification/data/EN_Card_Data.csv` unless the user asks
for Japanese. Use Python (csv module) for anything beyond a trivial match so quoted commas
in effect text are handled correctly — don't grep the raw CSV for structured queries.

- **By Card ID** (exact): filter rows where column `Card ID` equals the value. Return all
  matching rows (a card may have several attack rows).
- **By name**: case-insensitive substring match on `Card Name`.
- **By type / stage / category**: filter on the relevant column (`Type`, `Stage ...`,
  `Category`).

Present results as a compact table or per-card summary (ID, name, HP, type, weakness,
retreat, and each Move Name → Cost/Damage/Effect). If a query matches many cards, show the
count and the first ~20, and ask whether to narrow.

`$ARGUMENTS` is the user's query (an ID, a name fragment, or a `column=value` filter).

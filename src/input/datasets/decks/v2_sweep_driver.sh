#!/bin/bash
# タマンチュラv2 統制掃引(直列)。事前登録: data.md 2026-08-06節
D=/Users/yujiinoue/Documents/products/pokemonabc/src/input/datasets/decks
V=/Users/yujiinoue/Documents/products/pokemonabc/verification
LOG="$D/v2_sweep_2026-08-06.log"
: > "$LOG"

run() {  # $1=dir $2=label $3=N $4=agent $5=deck
  echo "=== ARM=$1 vs $2 N=$3 ===" >> "$LOG"
  if [ -z "$4" ]; then
    (cd "$D/$1" && nice -n 5 python3 "$V/bench.py" "$3" 2>&1 | tail -5) >> "$LOG"
  else
    (cd "$D/$1" && nice -n 5 python3 "$V/bench.py" "$3" --opponent "$V/reference/$4" --opponent-deck "$5" 2>&1 | tail -5) >> "$LOG"
  fi
}

# ① 安全ゲート(vs random)
for d in deckswap-tarountula-pilotfix deckswap-tarountula-v2; do run "$d" random 120 "" ""; done

# ② 較正済み外部ゲージ4種 × 2腕
for d in deckswap-tarountula-pilotfix deckswap-tarountula-v2; do
  run "$d" フーディン     200 alakazam_ryota_agent.py       "$V/decks/ryota_alakazam_2026-07-05.csv"
  run "$d" メガルカリオ   200 makthanithin_lucario_agent.py "$V/decks/makthanithin_lucario_2026-08-05.csv"
  run "$d" ブリジュラス   200 tomato_archaludon_agent.py    "$V/decks/tomato_archaludon_2026-07-22.csv"
  run "$d" イワパレス     200 soutasakurai_crustle_agent.py "$V/decks/soutasakurai_crustle_2026-08-04.csv"
done

# ③ オーロンゲ族内ゲージ(★本命) — P9素も測って修理前後の差を出す
for d in deckswap-tarountula deckswap-tarountula-pilotfix deckswap-tarountula-v2; do
  run "$d" オーロンゲ族内 200 grimmsnarl_infamily_agent.py "$V/decks/meta_grimmsnarl_800_2026-08-03.csv"
done

# ④ 王者の非退行(計器が壊れていないことの対照)
run starmie-aggro フーディン   200 alakazam_ryota_agent.py       "$V/decks/ryota_alakazam_2026-07-05.csv"
run starmie-aggro メガルカリオ 200 makthanithin_lucario_agent.py "$V/decks/makthanithin_lucario_2026-08-05.csv"

touch "$D/v2_sweep.done"

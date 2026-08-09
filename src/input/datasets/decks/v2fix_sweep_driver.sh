#!/bin/bash
# 2026-08-07 v2(純非ex)3修理の掃引 — 事前登録③(data.md)に対応
#
# 腕: 全OFF (V4_NO_TOOLFIX/COSTFIX/TOOLVETO=1) vs 全ON (未設定)
# 全OFF腕は変更前v2と169,430決定すべて一致済み(リファクタ無罪)。
#
# 運用規則:
#   - 直列。ベンチは同時に1本だけ(並列は数値を静かに汚す)
#   - tail -6 で1行目の (秒, ms/戦) を残す = CPU負荷のカナリア
#     我々の操縦者は _SEARCH_BUDGET_SEC=0.6 の実時間予算制なので、
#     負荷差があると静かに v1 へ退化して比較が壊れる
#   - vs random を先に通す。0.96(点推定 x>=384/400、D55 M2)を割ったら掃引しない
#   - 走行中に main.py を書き換えない(各ベンチは新規プロセスで読み直す)
set -u
V=/Users/yujiinoue/Documents/products/pokemonabc/verification
D=/Users/yujiinoue/Documents/products/pokemonabc/src/input/datasets/decks
ARM_DIR="$D/deckswap-tarountula-v2"
LOG="$D/v2fix_sweep_$(date +%Y-%m-%d_%H%M).log"

# トグルは必ず個別に env へ渡す。
# zsh は クォートしない "$vars" を単語分割しないため `env $vars cmd` 形式は
# 先頭1つしか適用されず、腕が静かに片方だけになる(2026-08-07 に実際に踏んだ)。
#
# main.py が読む環境変数は6つ + トレーサ1つ。**全部を明示的に潰す**。
# 3つしか面倒を見ていなかった初版は、`V2_NO_SEARCH=1` が漏れると
# **VETO が完全な no-op になり、しかもログは正常に見える**(T7レンズ2の BLOCKING 指摘)。
# `V3_SELECT_TRACE` の漏れも両腕が同じファイルに追記して壊れる。
CLEAN="-u V3_NO_TRFIX -u V3_NO_ENERGYFIX -u V2_NO_SEARCH -u V3_SELECT_TRACE"
off_env() { env $CLEAN V4_NO_TOOLFIX=1 V4_NO_COSTFIX=1 V4_NO_TOOLVETO=1 "$@"; }
on_env()  { env $CLEAN -u V4_NO_TOOLFIX -u V4_NO_COSTFIX -u V4_NO_TOOLVETO "$@"; }
# 腕が正しく立ったかをログに残す(誤設定をログから検出できるようにする)
echo_env() { echo "  effective env: $(env | grep -E '^V[234]_' | tr '\n' ' ')"; }

run() {  # $1=arm(off|on) $2=label $3=N $4=agent.py $5=deck.csv(空なら同一デッキ)
  local arm="$1" label="$2" n="$3" agent="$4" deck="${5:-}"
  local opts=()
  [ -n "$agent" ] && opts+=(--opponent "$V/reference/$agent")
  [ -n "$deck" ]  && opts+=(--opponent-deck "$deck")
  [ -z "$agent" ] && opts=(--opponent random)
  echo "" >> "$LOG"
  echo "=== [$arm] $label  N=$n ===" >> "$LOG"
  ( cd "$ARM_DIR" && \
    if [ "$arm" = off ]; then off_env nice -n 5 python3 "$V/bench.py" "$n" "${opts[@]}"; \
    else on_env nice -n 5 python3 "$V/bench.py" "$n" "${opts[@]}"; fi \
  ) 2>&1 | tail -6 >> "$LOG"
}

echo "掃引開始 $(date)" > "$LOG"
echo "腕: 全OFF vs 全ON / デッキ: v2(純非ex, ex 0枚) / 直列" >> "$LOG"

# ── 安全ゲート(これを割ったらゲージに1戦も使わない)
for arm in off on; do run "$arm" "vs random(安全ゲート)" 120 "" ""; done
for arm in off on; do
  wr=$(grep -A6 "\[$arm\] vs random" "$LOG" | grep -m1 "^WINRATE=" | cut -d= -f2)
  ok=$(python3 -c "print(1 if float('${wr:-0}') >= 0.96 else 0)")
  if [ "$ok" != "1" ]; then
    echo "GATE FAIL [$arm] WINRATE=$wr < 0.96 — 掃引中止" >> "$LOG"; echo "GATE FAIL [$arm] $wr"; exit 1
  fi
done
echo "安全ゲート通過。ゲージ掃引に進む" >> "$LOG"

# ── 較正済み外部ゲージ(族外。効果量の判定はここだけを使う)
for arm in off on; do run "$arm" "フーディン(29.2%)"     400 alakazam_ryota_agent.py      "$V/decks/ryota_alakazam_2026-07-05.csv"; done
for arm in off on; do run "$arm" "メガルカリオ(13.2%)"   400 makthanithin_lucario_agent.py "$V/decks/makthanithin_lucario_2026-08-05.csv"; done
for arm in off on; do run "$arm" "イワパレス(13.5%)"     200 soutasakurai_crustle_agent.py "$V/decks/soutasakurai_crustle_2026-08-04.csv"; done
for arm in off on; do run "$arm" "ブリジュラス(10.7%)"   200 tomato_archaludon_agent.py    "$V/decks/tomato_archaludon_2026-07-22.csv"; done

# ── 族内ゲージ(発火確認専用。絶対値は引用禁止、差だけ読む)
for arm in off on; do run "$arm" "オーロンゲ(族内・発火確認)" 150 grimmsnarl_infamily_agent.py "$V/decks/meta_grimmsnarl_800_2026-08-03.csv"; done

echo "" >> "$LOG"; echo "掃引終了 $(date)" >> "$LOG"
echo "DONE -> $LOG"

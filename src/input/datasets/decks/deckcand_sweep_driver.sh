#!/bin/bash
# デッキ候補の測定(層S) — 操縦者をバイト同一に固定し、デッキだけを変える。
#
# **層S(スクリーニング/標的選定)。引用禁止。**
#   D9(deck×pilot 非分離)により「デッキ単体の強さ」とは読まない。
#   読んでよいのは「我々の操縦者 3f55780b を載せたときの到達点」だけ。
#   採否判定に使うには、勝ち残った腕を層Bで新規独立測定する必要がある(D26 勝者の呪い)。
#
# 前回 v2fix_sweep_driver.sh が抱えていた3つの欠陥を潰してある:
#   ① mode 644 で実行できず zsh に落ちる            → chmod +x し、bash で起動する
#   ② `env $CLEAN cmd` は zsh で無音失敗する          → 変数展開を使わず全部直書き
#   ③ echo_env() が定義だけで一度も呼ばれていない      → 各セルの直前で必ず呼ぶ
#
# さらに前回の掃引の設計欠陥(対照が3〜5日前の別ドライバ由来)も潰す:
#   **対照 pilotfix を同じ走行・同じ日・同じドライバで測る。**
set -u
cd "$(dirname "$0")"
REPO=../../../..
V=$REPO/verification
LOG="${LOG:-/tmp/deckcand_sweep_$(date +%Y%m%d_%H%M).log}"

ARMS="deckswap-tarountula-pilotfix deckcand-lucario deckcand-alakazam deckcand-archaludon"

# 対面名 / ゲージagent / ゲージデッキ / N   (族外4面のみ。族内オーロンゲは判定に使えないので入れない)
CELLS=(
  "フーディン|reference/alakazam_ryota_agent.py|decks/ryota_alakazam_2026-07-05.csv|200"
  "メガルカリオ|reference/makthanithin_lucario_agent.py|decks/makthanithin_lucario_2026-08-05.csv|200"
  "イワパレス|reference/soutasakurai_crustle_agent.py|decks/soutasakurai_crustle_2026-08-04.csv|200"
  "ブリジュラス|reference/tomato_archaludon_agent.py|decks/tomato_archaludon_2026-07-22.csv|200"
)

echo_env() {   # ★必ず呼ぶ。実効環境をログに残さない測定は信用しない(2026-08-07 の事故)
  local e
  e="$(env | grep -E '^V[234]_' | tr '\n' ' ')"
  echo "    effective env: ${e:-(V2_/V3_/V4_ は未設定 = すべて既定 ON)}"
}

{
echo "### 層S(スクリーニング/標的選定) — 引用禁止。D9により『デッキ単体の強さ』とは読まない。"
echo "# deckcand sweep  $(date '+%F %T')"
echo "# 操縦者は全腕で同一: $(md5 -q deckswap-tarountula-pilotfix/main.py)"
echo "# 直列実行(自パイロットは実時間予算 _SEARCH_BUDGET_SEC=0.6 のため並列禁止 — playbook §2)"
for arm in $ARMS; do
  echo "== $arm  deck.csv md5 $(md5 -q $arm/deck.csv)  main.py md5 $(md5 -q $arm/main.py)"
done

for arm in $ARMS; do
  echo ""
  echo "########## $arm ##########"

  echo "  [安全ゲート] vs random N=120"
  echo_env
  ( cd "$arm" && nice -n 5 env -u V3_NO_TRFIX -u V3_NO_ENERGYFIX -u V2_NO_SEARCH -u V3_SELECT_TRACE \
      python3 ../$REPO/verification/bench.py 120 2>&1 | tail -6 )

  for cell in "${CELLS[@]}"; do
    IFS='|' read -r name agent deck n <<< "$cell"
    echo "  [$name] N=$n  agent=$agent"
    echo_env
    ( cd "$arm" && nice -n 5 env -u V3_NO_TRFIX -u V3_NO_ENERGYFIX -u V2_NO_SEARCH -u V3_SELECT_TRACE \
        python3 ../$REPO/verification/bench.py "$n" \
          --opponent      "../$REPO/verification/$agent" \
          --opponent-deck "../$REPO/verification/$deck" 2>&1 | tail -6 )
  done
done
echo ""
echo "# done $(date '+%F %T')"
} 2>&1 | tee "$LOG"
echo "LOG=$LOG"

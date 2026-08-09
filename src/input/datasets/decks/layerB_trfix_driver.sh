#!/bin/bash
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"   # zsh で起動されても bash に落とす(単語分割の罠)
#
# 層B測定ドライバ — pilotfix(TRFIX束あり) vs P9素(なし)。デッキはバイト同一。
# 事前登録: docs/memo/prereg-2026-08-09-layerB-trfix.md
#
# T7(実装レンズ)の13点チェックリストに対応させてある。前ドライバの欠陥は全部ここで潰す:
#   ①zsh対策は「shebang頼み」ではなく2行目の exec と配列展開の両方で担保
#   ②`{...} | tee` を使わない(subshell の exit が効かず futility 中断が実装不能になる)
#   ③effective env は**測定プロセス自身**に印字させる(driver shell の env では意味がない)
#   ④腕をセル粒度で交互に回す(腕と壁時計時刻の交絡を切る)
#   ⑤1セル1ファイル。tail / grep -A は使わない。rc と CRASH と WINRATE を全部検査して fail closed
#   ⑥勝数は `結果: N勝` から取り、WINRATE と突き合わせる(cew_stats は wins/n を要求する)
#
# 統計レンズ NB6: 同じ総Nを2ブロックに割る。合算SEは不変(損失ゼロ)で、
#   **腕×走行の交互作用に1自由度**が生まれる。過分散が走行間か腕内かを初めて分離できる。
set -euo pipefail
cd "$(dirname "$0")"

REPO=$(cd ../../../.. && pwd)
V="$REPO/verification"
TS=$(date +%Y%m%d_%H%M)
OUT="${OUT:-/tmp/layerB_trfix_$TS}"
mkdir -p "$OUT"
LOG="$OUT/driver.log"
exec > >(tee -a "$LOG") 2>&1

LOCK="/tmp/pokemonabc_measure.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "FATAL: 別の測定が走っている (lock $LOCK, pid $(cat "$LOCK"))"; exit 1
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

if pgrep -f "bench\.py|parbench\.py|selfplay\.py|equiv_probe\.py" | grep -qv "^$$\$"; then
  echo "FATAL: 測定プロセスが既に走っている。直列規律に反する"; pgrep -fl "bench\.py|parbench\.py"; exit 1
fi

# --- 腕・セル定義(すべて配列。素の変数展開は使わない) -------------------------
ARM_A="deckswap-tarountula-pilotfix"      # TRFIX束あり = 実ラダーに載っている腕
ARM_B="deckswap-tarountula"               # TRFIX束なし = P9素
declare -a ARMS=("$ARM_A" "$ARM_B")

# name|agent|deck|block1_n|block2_n   (cew.py の Neyman配分 1248/380/934/638 を2分割・全部偶数)
declare -a CELLS=(
  "alakazam|reference/alakazam_ryota_agent.py|decks/ryota_alakazam_2026-07-05.csv|624|624"
  "crustle|reference/soutasakurai_crustle_agent.py|decks/soutasakurai_crustle_2026-08-04.csv|190|190"
  "lucario|reference/makthanithin_lucario_agent.py|decks/makthanithin_lucario_2026-08-05.csv|468|466"
  "archaludon|reference/tomato_archaludon_agent.py|decks/tomato_archaludon_2026-07-22.csv|320|318"
)
GATE_N=240
TIMEBOX_SEC=$((4 * 3600))
START=$SECONDS

# ENVCLEAN は**一箇所だけ**で定義し、環境プローブと全 bench 呼び出しの両方で使う。
# こうしないと「掃除リスト」と「検証リスト」がドリフトする。
declare -a ENVCLEAN=(env -u V3_NO_TRFIX -u V3_NO_ENERGYFIX -u V2_NO_SEARCH -u V3_SELECT_TRACE -u V4_NO_TOOLFIX -u V4_NO_COSTFIX -u V4_NO_TOOLVETO -u DEBUG_AGENT)

# --- ヘッダ: 成果物の同一性をログに固定し、違ったら起動しない ------------------
echo "### 層B測定 — 事前登録 docs/memo/prereg-2026-08-09-layerB-trfix.md"
echo "# start $(date '+%F %T')   out=$OUT"
echo "# git HEAD: $(git -C "$REPO" rev-parse HEAD)"
echo "# git dirty:"; git -C "$REPO" status --porcelain | sed 's/^/#   /'
echo "# python: $(python3 -V 2>&1)   uptime:$(uptime | sed 's/.*load/ load/')"

declare -A WANT=( ["$ARM_A/main.py"]=3f55780be02a55743e81af154c6376c1
                  ["$ARM_B/main.py"]=725ef4c9c2d4d8c3c2a9e5b0b2b7b8f1 )
for arm in "${ARMS[@]}"; do
  mm=$(md5 -q "$arm/main.py"); dd=$(md5 -q "$arm/deck.csv")
  echo "# $arm  main.py=$mm  deck.csv=$dd"
  [ "$dd" = "a246be4f11fefcffdb70e3fe9c1f618d" ] || { echo "FATAL: $arm の deck.csv が想定と違う"; exit 1; }
done
[ "$(md5 -q "$ARM_A/main.py")" = "3f55780be02a55743e81af154c6376c1" ] || { echo "FATAL: 腕Aの main.py が想定と違う"; exit 1; }
for c in "${CELLS[@]}"; do
  IFS='|' read -r nm ag dk _ _ <<< "$c"
  echo "# gauge $nm  agent=$(md5 -q "$V/$ag")  deck=$(md5 -q "$V/$dk")"
done

# --- 実効環境の検査: **測定プロセス自身**に印字させ、空でなければ止める ---------
eff=$("${ENVCLEAN[@]}" python3 -c 'import os;print({k:v for k,v in sorted(os.environ.items()) if k.startswith(("V2_","V3_","V4_"))})')
echo "# EFFECTIVE_ENV(測定プロセス内) = $eff"
[ "$eff" = "{}" ] || { echo "FATAL: 測定プロセスに V2_/V3_/V4_ が残っている: $eff"; exit 1; }

# --- 1セル走らせて wins/n を取り出す。全部検査して fail closed --------------------
run_cell() {   # $1=arm $2=cellname $3=agent $4=deck $5=n $6=tag
  local arm=$1 nm=$2 ag=$3 dk=$4 n=$5 tag=$6
  local f="$OUT/${arm}__${nm}__${tag}.txt" rc=0
  local -a opp=()
  [ "$nm" = "random" ] || opp=(--opponent "$V/$ag" --opponent-deck "$V/$dk")
  ( cd "$arm" && "${ENVCLEAN[@]}" python3 "$V/bench.py" "$n" "${opp[@]}" ) > "$f" 2>&1 || rc=$?
  [ "$rc" -eq 0 ]                                       || { echo "FATAL rc=$rc  $f"; exit 1; }
  grep -qxF 'CRASH=0' "$f"                              || { echo "FATAL CRASH!=0  $f"; exit 1; }
  [ "$(grep -cE '^WINRATE=[0-9.]+$' "$f")" -eq 1 ]      || { echo "FATAL WINRATE行が1本でない  $f"; exit 1; }
  local wr w l d ms
  wr=$(grep -m1 -E '^WINRATE=' "$f" | cut -d= -f2)
  read -r w l d <<< "$(sed -nE 's/^結果: ([0-9]+)勝 ([0-9]+)敗 ([0-9]+)分$/\1 \2 \3/p' "$f")"
  [ -n "${w:-}" ]                                       || { echo "FATAL 勝数が読めない  $f"; exit 1; }
  python3 -c "import sys;sys.exit(0 if abs($w/$n-$wr)<1e-4 else 1)" \
                                                        || { echo "FATAL 勝数とWINRATEが不一致  $f"; exit 1; }
  ms=$(sed -nE 's/.*, ([0-9.]+) ms\/戦.*/\1/p' "$f" | head -1)
  echo "CELL $arm $nm $tag $w/$n draws=$d ms=${ms:-?} wr=$wr"
}

# --- 安全ゲート(両腕。落ちたら本測定に入らない) --------------------------------
echo ""; echo "===== 安全ゲート vs random N=$GATE_N ====="
for arm in "${ARMS[@]}"; do
  line=$(run_cell "$arm" random "" "" "$GATE_N" gate); echo "$line"
  w=$(echo "$line" | awk '{print $5}' | cut -d/ -f1)
  python3 -c "import sys;sys.exit(0 if $w/$GATE_N>=0.96 else 1)" \
    || { echo "FATAL: $arm の vs random が 96% 未満(正当性の欠格)。README 提出前ゲート#2"; exit 1; }
done

# --- 本測定: セル粒度で腕を交互に。さらに2ブロックに割る(NB6) ------------------
for tag in b1 b2; do
  echo ""; echo "===== ブロック $tag ====="
  for c in "${CELLS[@]}"; do
    IFS='|' read -r nm ag dk n1 n2 <<< "$c"
    n=$([ "$tag" = b1 ] && echo "$n1" || echo "$n2")
    for arm in "${ARMS[@]}"; do            # ★同じセルの中で腕を交互に = 腕と時刻の交絡を切る
      [ $((SECONDS - START)) -lt "$TIMEBOX_SEC" ] || { echo "TIMEBOX 4h 超過。完走セルのみ報告"; exit 2; }
      run_cell "$arm" "$nm" "$ag" "$dk" "$n" "$tag"
    done
  done
done

echo ""; echo "# done $(date '+%F %T')  elapsed=$((SECONDS-START))s"
echo "# 集計は次で行う(セル別 wins/n を合算してから):"
echo "#   grep '^CELL' $LOG"
echo "#   python3 $V/cew_stats.py --a 'alakazam=W/N,crustle=W/N,lucario=W/N,archaludon=W/N' \\"
echo "#                           --b '...' --label-a pilotfix --label-b P9素"

#!/bin/bash
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"          # zsh 起動でも bash に落とす
[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"  # 無人走行
#
# 新・メガスターミー・マスターコントロール 層B掃引
#   事前登録 docs/memo/prereg-2026-08-11-starmie-aqua.md
#   腕A: starmie-aggro   (725ef4c9 / 4e0a5c4c) = 実ラダー793.9の実物(基準線・本日再提出 55411039)
#   腕B: starmie-aqua    (45910ac6 / be51da6d) = 水単デッキ + V5盤面価値層 全ON
#   族外5面 プールσ配分 3,200/腕、計 6,400戦 + ゲート480戦、直列。
#   **セル粒度で腕を交互 + 8ブロック**(主判定を batch-means CI にして過分散を自己較正する)。
#
# ★macOS の bash は 3.2 なので **`declare -A` は使えない**(実行時に unbound variable で即死)。
#   `bash -n` は構文しか見ないので通ってしまう。連想配列は使わず並列の添字配列で書く。
# ★`set -u` 下では空配列の `"${arr[@]}"` も unbound variable になる。
#   `${arr[@]+"${arr[@]}"}` を使う(`"${arr[@]:-}"` は空文字列を1個渡してしまうので不可)。
#
# ★環境の対称性(重要): 腕Bは腕Aの main.py のコピーに V4 ロジックを足したものなので、
#   V3_* の意味は両腕で同一。**全部 unset すれば両腕とも「既存修理ぜんぶON」で揃い、
#   差は『デッキ + V4ロジック4件』だけになる。**
#   → **このドライバは unset のみ。set は絶対に足さないこと**(足した瞬間に腕が非対称になる)。
set -euo pipefail
cd "$(dirname "$0")"
REPO=$(cd ../../../.. && pwd); V="$REPO/verification"
CHECKPY="$REPO/.claude/skills/submission-check/scripts/check.py"   # verification/ には無い
OUT="${OUT:-$REPO/../pokemonabc-runs/aqua_sweep}"; mkdir -p "$OUT"  # /tmp は再起動で消える
RES="$OUT/results.tsv"; ELAPSED="$OUT/elapsed"
exec > >(tee -a "$OUT/driver.log") 2>&1

LOCK=/tmp/pokemonabc_measure.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "FATAL: 別の測定が走っている (pid $(cat "$LOCK"))"; exit 1; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT
if pgrep -f "bench\.py|parbench\.py|selfplay\.py|equiv_probe\.py|mastercontrol_probe\.py" >/dev/null; then
  echo "FATAL: 測定プロセスが既に走っている(直列規律)"; exit 1; fi

ARM_A="starmie-aggro"; ARM_B="starmie-aqua"
# name|agent|deck|1ブロックあたりのN  (Neyman 1096/912/576/408/208 を4分割、全部偶数)
CELLS=(
  "alakazam|reference/alakazam_ryota_agent.py|decks/ryota_alakazam_2026-07-05.csv|142"
  "grimmsnarl|reference/tetsutani_grimmsnarl_agent.py|reference/tetsutani_grimmsnarl/deck.csv|94"
  "lucario|reference/makthanithin_lucario_agent.py|decks/makthanithin_lucario_2026-08-05.csv|64"
  "crustle|reference/soutasakurai_crustle_agent.py|decks/soutasakurai_crustle_2026-08-04.csv|52"
  "archaludon|reference/tomato_archaludon_agent.py|decks/tomato_archaludon_2026-07-22.csv|48"
)
BLOCKS=(b1 b2 b3 b4 b5 b6 b7 b8)
GATE_N=240; TIMEBOX=$((5*3600))
PREV=0; [ -f "$ELAPSED" ] && PREV=$(cat "$ELAPSED")   # 再開しても通算8hで打ち切る
START=$SECONDS
ENVCLEAN=(env -u V3_NO_TRFIX -u V3_NO_ENERGYFIX -u V2_NO_SEARCH -u V3_SELECT_TRACE \
              -u V4_NO_TOOLFIX -u V4_NO_COSTFIX -u V4_NO_TOOLVETO -u DEBUG_AGENT \
              -u V4_NO_CINDERACE -u V4_NO_BEACH -u V4_NO_WALLY -u V4_NO_LOGUARD \
              -u V5_NO_OVERRIDE_GATE -u V5_NO_BENCHDMG -u V5_NO_STANDFIGHT \
              -u V2_BUDGET_SEC -u V2_CAND -u V2_DET -u V2_SIM_BANK)

echo "### 事前登録 docs/memo/prereg-2026-08-11-starmie-aqua.md  (N は登録時に凍結済み)"
echo "# start $(date '+%F %T')  out=$OUT  (通算経過 ${PREV}s から再開)"
echo "# git HEAD: $(git -C "$REPO" rev-parse --short HEAD)"
echo "# git dirty:"; git -C "$REPO" status --porcelain | sed 's/^/#   /'
# bash 3.2: 連想配列は使えないので並列の添字配列で
WK=("$ARM_A/main.py" "$ARM_A/deck.csv" "$ARM_B/main.py" "$ARM_B/deck.csv")
WV=(725ef4c9 4e0a5c4c 45910ac6 be51da6d)
for i in 0 1 2 3; do
  got=$(md5 -q "${WK[$i]}" | cut -c1-8)
  echo "# ${WK[$i]} = $got (期待 ${WV[$i]})"
  [ "$got" = "${WV[$i]}" ] || { echo "FATAL: ${WK[$i]} のハッシュが事前登録と違う"; exit 1; }
done
eff=$("${ENVCLEAN[@]}" python3 -c 'import os;print({k:v for k,v in os.environ.items() if k.startswith(("V2_","V3_","V4_"))})')
echo "# EFFECTIVE_ENV(測定プロセス内) = $eff"
[ "$eff" = "{}" ] || { echo "FATAL: 環境が汚れている: $eff"; exit 1; }

# ---- Phase 0: 効果量と独立な正当性ゲート(事前登録 §3) ----------------------
echo ""; echo "===== Phase 0: 正当性ゲート ====="
for arm in "$ARM_A" "$ARM_B"; do
  r=$( cd "$arm" && "${ENVCLEAN[@]}" python3 "$V/conformance.py" 2>&1 | tail -1 )
  echo "# $arm conformance: $r"
  [ "$r" = "CONFORMANCE=PASS" ] || { echo "FATAL: $arm が conformance で落ちた"; exit 1; }
done
# V4ロジックが実際に立っているかの直接確認。
# フラグが読めない/定数が解決できないと、4ロジックとも無言で no-op になり
# 「V4 ≈ 0pt」と見分けがつかなくなる(D72 の TOOLKINDS_OK と同じ趣旨のガード)。
v5=$( cd "$ARM_B" && "${ENVCLEAN[@]}" python3 -c '
import main as m
assert all(m._v5_on(k) for k in ("OVERRIDE_GATE","BENCHDMG","STANDFIGHT")), "V5フラグがOFF"
assert m._prize_value(1031) == 3 and m._prize_value(1030) == 1, "サイド価値が壊れている"
assert m._BENCH_SPLASH.get(1487) == 50, "Jetting Blow のベンチ50が登録されていない"
r = m._attack_value.__doc__ or ""
assert "KO" in r, "_attack_value の契約が変わっている"
print("V5_OK")' )
echo "# $ARM_B $v5"
[ "$v5" = "V5_OK" ] || { echo "FATAL: 腕BのV5ロジックが立っていない"; exit 1; }
echo "# submission-check: $(python3 "$CHECKPY" --submission "$ARM_B" --tar "$OUT/armB.tar.gz" 2>&1 | tail -1)"

# ---- 1セル。既存の有効な結果があればスキップ(再開可能) ----------------------
CELL_MS=""     # 直近セルの ms/戦(腕間カナリア用)
run() {  # $1=arm $2=cell $3=agent $4=deck $5=n $6=tag
  local arm=$1 nm=$2 ag=$3 dk=$4 n=$5 tag=$6
  local f="$OUT/${arm}__${nm}__${tag}.txt" rc=0
  if [ -s "$f" ] && grep -qxF 'CRASH=0' "$f" && [ "$(grep -cE '^WINRATE=' "$f")" -eq 1 ]; then
    echo "SKIP $arm $nm $tag"; report "$f" "$arm" "$nm" "$tag" "$n"; return 0; fi
  local opp=(); [ "$nm" = random ] || opp=(--opponent "$V/$ag" --opponent-deck "$V/$dk")
  ( cd "$arm" && "${ENVCLEAN[@]}" python3 "$V/bench.py" "$n" ${opp[@]+"${opp[@]}"} ) >"$f" 2>&1 || rc=$?
  [ "$rc" -eq 0 ] || { echo "FATAL rc=$rc $f"; sed -n '1,5p' "$f"; exit 1; }
  report "$f" "$arm" "$nm" "$tag" "$n"
}
report() {  # $1=file $2=arm $3=cell $4=tag $5=n — 全数検査して fail closed
  local f=$1 n=$5 w l d ms wr
  grep -qxF 'CRASH=0' "$f" || { echo "FATAL CRASH!=0 $f"; exit 1; }
  [ "$(grep -cE '^WINRATE=[0-9.]+$' "$f")" -eq 1 ] || { echo "FATAL WINRATE行が1本でない $f"; exit 1; }
  read -r w l d <<< "$(sed -nE 's/^結果: ([0-9]+)勝 ([0-9]+)敗 ([0-9]+)分$/\1 \2 \3/p' "$f")"
  [ -n "${w:-}" ] || { echo "FATAL 勝数が読めない $f"; exit 1; }
  wr=$(grep -m1 -E '^WINRATE=' "$f" | cut -d= -f2)
  python3 -c "import sys;sys.exit(0 if abs($w/$n-$wr)<1e-4 else 1)" \
    || { echo "FATAL 勝数とWINRATEが不一致 $f"; exit 1; }
  ms=$(sed -nE 's/.*, ([0-9.]+) ms\/戦.*/\1/p' "$f" | head -1)
  # 結果は追記ログではなく**キー付きの表**に置く(再開時の二重計上を防ぐ)
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$2" "$3" "$4" "$w" "$n" "${ms:-0}" >> "$RES"
  echo "CELL $2 $3 $4 $w/$n draws=$d ms=${ms:-?}"
  CELL_MS="${ms:-0}"
}

echo ""; echo "===== 安全ゲート vs random N=$GATE_N ====="
for arm in "$ARM_A" "$ARM_B"; do
  run "$arm" random "" "" "$GATE_N" gate     # $( ) で包まない(FATAL が飲まれる)
  w=$(awk -F'\t' -v a="$arm" '$1==a&&$2=="random"{print $4}' "$RES" | tail -1)
  python3 -c "import sys;sys.exit(0 if $w/$GATE_N>=0.96 else 1)" \
    || { echo "FATAL: $arm の vs random が 96% 未満。正当性の欠格"; exit 1; }
done

for bi in 0 1 2 3 4 5 6 7; do
  tag=${BLOCKS[$bi]}
  echo ""; echo "===== ブロック $tag ====="
  for c in "${CELLS[@]}"; do
    IFS='|' read -r nm ag dk n <<< "$c"
    # ★ブロックごとに腕の順序を入れ替える(熱ドリフト等が片方の腕だけに乗らないように)
    if [ $((bi % 2)) -eq 0 ]; then ORD=("$ARM_A" "$ARM_B"); else ORD=("$ARM_B" "$ARM_A"); fi
    msA=""; for arm in "${ORD[@]}"; do
      [ $((PREV + SECONDS - START)) -lt "$TIMEBOX" ] \
        || { echo "TIMEBOX 通算8h 超過。**合成は出さない**(未完セルがあると別指標になる)"; \
             echo $((PREV+SECONDS-START)) > "$ELAPSED"; exit 2; }
      run "$arm" "$nm" "$ag" "$dk" "$n" "$tag"
      if [ -z "$msA" ]; then msA="$CELL_MS"; else
        # 同一ゲージ内での腕間 ms/戦 カナリア(ゲージ間の比較は無意味なのでやらない)
        python3 -c "
import sys
a,b=float('$msA'),float('$CELL_MS')
sys.exit(1 if a>0 and b>0 and abs(a-b)/max(a,b)>0.30 else 0)" \
          || echo "WARN: $nm $tag の ms/戦 が腕間で30%超ずれた ($msA vs $CELL_MS) — CPU負荷を疑う"
      fi
    done
    echo $((PREV+SECONDS-START)) > "$ELAPSED"
  done
done
echo ""; echo "# done $(date '+%F %T')  通算 $((PREV+SECONDS-START))s"
echo "# 集計は必ず次で行う(driver.log を grep しない = 再開時に二重計上する):"
echo "#   python3 $REPO/verification/aqua_aggregate.py $RES"

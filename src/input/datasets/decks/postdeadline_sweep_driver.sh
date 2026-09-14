#!/bin/bash
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"
[ -n "${CAFFEINATED:-}" ] || exec env CAFFEINATED=1 caffeinate -dimsu bash "$0" "$@"
# 締切後の層B測定(prereg-2026-09-03-postdeadline-AB.md)。endguard_sweep_driver.sh の2腕設計をそのまま流用し、腕だけ引数化。
#   A: starmie-aqua(対照、D78凍結の実物 45910ac6/be51da6d) vs starmie-aqua-bosslogic(最終提出 b67466a9/d2fd11c0)
#   B: starmie-aqua-bosslogic(対照) vs starmie-aqua-bosslogic-efix(ENERGYKO 修理)
set -euo pipefail
cd "$(dirname "$0")"
REPO=$(cd ../../../.. && pwd); V="$REPO/verification"
case "${1:-}" in
  A) ARMS=(starmie-aqua starmie-aqua-bosslogic); TAGDIR=postdeadline_A ;;
  B) ARMS=(starmie-aqua-bosslogic starmie-aqua-bosslogic-efix); TAGDIR=postdeadline_B ;;
  C) ARMS=(starmie-aqua-endguard-boss3 starmie-aqua-bosslogic); TAGDIR=postdeadline_C ;;
  *) echo "usage: $0 A|B"; exit 2 ;;
esac
OUT="${OUT:-$REPO/../pokemonabc-runs/$TAGDIR}"; mkdir -p "$OUT"
RES="$OUT/results.tsv"
exec > >(tee -a "$OUT/driver.log") 2>&1
LOCK=/tmp/pokemonabc_measure.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "FATAL: 別の測定が走っている"; exit 1; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT
CELLS=(
  "alakazam|reference/alakazam_ryota_agent.py|decks/ryota_alakazam_2026-07-05.csv|142"
  "grimmsnarl|reference/tetsutani_grimmsnarl_agent.py|reference/tetsutani_grimmsnarl/deck.csv|94"
  "lucario|reference/makthanithin_lucario_agent.py|decks/makthanithin_lucario_2026-08-05.csv|64"
  "crustle|reference/soutasakurai_crustle_agent.py|decks/soutasakurai_crustle_2026-08-04.csv|52"
  "archaludon|reference/tomato_archaludon_agent.py|decks/tomato_archaludon_2026-07-22.csv|48"
)
BLOCKS=(b1 b2 b3 b4 b5 b6 b7 b8)
ENVCLEAN=(env -u V2_NO_SEARCH -u V3_NO_TRFIX -u V3_SELECT_TRACE -u V5_NO_OVERRIDE_GATE -u V5_NO_BENCHDMG \
              -u V5_NO_STANDFIGHT -u V5_NO_KOCAP -u V5_NO_ENDGUARD -u V5_NO_BOSSGUARD -u V5_NO_BOSSCOMBO \
              -u V5_NO_GUSTLOCK -u V5_NO_RESETLOCK -u V5_NO_RIDERLOCK -u V5_NO_ENERGYKO)
echo "# start $(date '+%F %T')  sweep=$1 out=$OUT"
for a in "${ARMS[@]}"; do rm -rf "$a/__pycache__" "$a/cg/__pycache__"; echo "# $a main=$(md5 -q $a/main.py | cut -c1-8) deck=$(md5 -q $a/deck.csv | cut -c1-8) dylib=$(md5 -q $a/cg/libcg.dylib | cut -c1-8) api=$(md5 -q $a/cg/api.py | cut -c1-8)"; done
ps aux | grep -E "bench\.py|selfplay|parbench" | grep -v grep && { echo "FATAL: 他の bench/selfplay が走っている"; exit 1; } || true
eff=$("${ENVCLEAN[@]}" python3 -c 'import os;print({k:v for k,v in os.environ.items() if k.startswith(("V2_","V3_","V5_"))})')
[ "$eff" = "{}" ] || { echo "FATAL: 環境が汚れている: $eff"; exit 1; }
run() {  # arm cell agent deck n tag
  local f="$OUT/$1__$2__$6.txt" rc=0
  if [ -s "$f" ] && grep -qxF 'CRASH=0' "$f"; then echo "SKIP $1 $2 $6"; else
    local opp=(--opponent "$V/$3" --opponent-deck "$V/$4")
    ( cd "$1" && "${ENVCLEAN[@]}" python3 "$V/bench.py" "$5" "${opp[@]}" ) >"$f" 2>&1 || rc=$?
    [ "$rc" -eq 0 ] || { echo "FATAL rc=$rc $f"; sed -n '1,4p' "$f"; exit 1; }
  fi
  grep -qxF 'CRASH=0' "$f" || { echo "FATAL CRASH!=0 $f"; exit 1; }
  local w; w=$(sed -nE 's/^結果: ([0-9]+)勝.*/\1/p' "$f")
  [ -n "$w" ] || { echo "FATAL 勝数が読めない $f"; exit 1; }
  printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$6" "$w" "$5" >> "$RES"
  echo "CELL $1 $2 $6 $w/$5  $(uptime | sed -E 's/.*load averages?: //')"
}
for bi in 0 1 2 3 4 5 6 7; do
  tag=${BLOCKS[$bi]}; echo ""; echo "===== ブロック $tag ====="
  for c in "${CELLS[@]}"; do
    IFS='|' read -r nm ag dk n <<< "$c"
    for k in 0 1; do
      arm=${ARMS[$(( (bi + k) % 2 ))]}
      run "$arm" "$nm" "$ag" "$dk" "$n" "$tag"
    done
  done
done
echo ""; echo "# done $(date '+%F %T')"

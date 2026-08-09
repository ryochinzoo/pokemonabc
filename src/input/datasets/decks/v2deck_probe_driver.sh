#!/bin/bash
[ -n "${BASH_VERSION:-}" ] || exec bash "$0" "$@"   # zsh で起動されても bash に落とす
#
# v2デッキ探り — 事前登録 docs/memo/prereg-2026-08-09-v2deck-grimmsnarl.md
# 操縦者を 3f55780b にバイト固定し、デッキだけを変えて 族外オーロンゲゲージに当てる。
# 200戦ずつ2ブロック、ブロック内で腕を交互(腕と壁時計時刻の交絡を切る + 腕×ブロックに1自由度)。
set -euo pipefail
cd "$(dirname "$0")"
REPO=$(cd ../../../.. && pwd); V="$REPO/verification"
OUT="${OUT:-/tmp/v2deck_probe_$(date +%Y%m%d_%H%M)}"; mkdir -p "$OUT"
exec > >(tee -a "$OUT/driver.log") 2>&1

LOCK=/tmp/pokemonabc_measure.lock
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "FATAL: 別の測定が走っている"; exit 1; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT
if pgrep -f "bench\.py|parbench\.py|selfplay\.py" >/dev/null; then
  echo "FATAL: bench/selfplay が既に走っている(直列規律)"; exit 1; fi

declare -a ARMS=("deckswap-tarountula-pilotfix" "deckcand-v2deck")
declare -a ENVCLEAN=(env -u V3_NO_TRFIX -u V3_NO_ENERGYFIX -u V2_NO_SEARCH -u V3_SELECT_TRACE \
                         -u V4_NO_TOOLFIX -u V4_NO_COSTFIX -u V4_NO_TOOLVETO -u DEBUG_AGENT)
AG="$V/reference/tetsutani_grimmsnarl_agent.py"
DK="$V/reference/tetsutani_grimmsnarl/deck.csv"

echo "### 層S(標的選定専用) — 引用禁止。採否には使わない。"
echo "# $(date '+%F %T')  out=$OUT"
echo "# git HEAD: $(git -C "$REPO" rev-parse --short HEAD)"
for a in "${ARMS[@]}"; do echo "# $a  main=$(md5 -q "$a/main.py" | cut -c1-8)  deck=$(md5 -q "$a/deck.csv" | cut -c1-8)"; done
echo "# gauge agent=$(md5 -q "$AG" | cut -c1-8)  deck=$(md5 -q "$DK" | cut -c1-8)"
# 両腕の main.py が同一であることを機械確認(デッキだけが変数であることの担保)
[ "$(md5 -q "${ARMS[0]}/main.py")" = "$(md5 -q "${ARMS[1]}/main.py")" ] \
  || { echo "FATAL: 2腕の main.py が違う。デッキだけが変数という前提が壊れている"; exit 1; }
eff=$("${ENVCLEAN[@]}" python3 -c 'import os;print({k:v for k,v in os.environ.items() if k.startswith(("V2_","V3_","V4_"))})')
echo "# EFFECTIVE_ENV(測定プロセス内) = $eff"
[ "$eff" = "{}" ] || { echo "FATAL: 環境が汚れている: $eff"; exit 1; }

run() {  # $1=arm $2=n $3=tag
  local f="$OUT/$1__$3.txt" rc=0
  ( cd "$1" && "${ENVCLEAN[@]}" python3 "$V/bench.py" "$2" --opponent "$AG" --opponent-deck "$DK" ) >"$f" 2>&1 || rc=$?
  [ "$rc" -eq 0 ] || { echo "FATAL rc=$rc $f"; exit 1; }
  grep -qxF 'CRASH=0' "$f" || { echo "FATAL CRASH!=0 $f"; exit 1; }
  local w l d ms
  read -r w l d <<< "$(sed -nE 's/^結果: ([0-9]+)勝 ([0-9]+)敗 ([0-9]+)分$/\1 \2 \3/p' "$f")"
  [ -n "${w:-}" ] || { echo "FATAL 勝数が読めない $f"; exit 1; }
  ms=$(sed -nE 's/.*, ([0-9.]+) ms\/戦.*/\1/p' "$f" | head -1)
  echo "CELL $1 $3 $w/$2 draws=$d ms=${ms:-?}"
}

for tag in b1 b2; do
  echo ""; echo "===== ブロック $tag (各腕200戦) ====="
  for a in "${ARMS[@]}"; do run "$a" 200 "$tag"; done
done
echo ""; echo "# done $(date '+%F %T')"

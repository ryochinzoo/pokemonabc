#!/bin/zsh
# SVG → PNG(Kaggle Media Gallery 用、2x、ライトテーマ固定)。2026-09-02 新設。
# この Mac に rsvg-convert / cairosvg / inkscape / magick が無いため Chrome headless を使う。
# Chrome は OS のダーク設定を拾うので、@media (prefers-color-scheme: dark) ブロックを剥がした
# 一時コピーを描画する(Kaggle は白背景)。使い方: figures/export_png.sh [fig_*.svg ...](省略時は全部)
set -e
HERE=${0:a:h}
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT="$HERE/png"; mkdir -p "$OUT"
TMP=$(mktemp -d)
files=("$@"); [ ${#files} -eq 0 ] && files=("$HERE"/fig_*.svg)
for svg in "${files[@]}"; do
  base=$(basename "$svg" .svg)
  W=$(grep -o 'width="[0-9.]*"' "$svg" | head -1 | tr -dc '0-9.'); H=$(grep -o 'height="[0-9.]*"' "$svg" | head -1 | tr -dc '0-9.')
  # ダークブロックを剥がす(python で確実に: @media ... { ... } を最短一致で除去)
  python3 - "$svg" "$TMP/$base.svg" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
s = re.sub(r"@media \(prefers-color-scheme: dark\)\{.*?\}\s*\}", "", s, flags=re.S)
open(sys.argv[2], "w").write(s)
PY
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --screenshot="$OUT/$base.png" \
    --window-size=${W%.*},${H%.*} --force-device-scale-factor=2 --default-background-color=ffffffff \
    "file://$TMP/$base.svg" >/dev/null 2>&1
  echo "$base.png  $(file -b "$OUT/$base.png" | cut -d, -f2)"
done
rm -rf "$TMP"

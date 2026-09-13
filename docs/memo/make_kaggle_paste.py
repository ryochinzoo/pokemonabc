#!/usr/bin/env python3
"""Kaggle 貼り付け版の生成: writeup 本文から台帳タグ [#N] を剥がし、語数を印字する.

使い方: python3 docs/memo/make_kaggle_paste.py  → docs/memo/writeup-kaggle-paste.md
本文範囲と語数の定義は t6_check.py と同一(公開版 = タグ除去後の全文)。
図キャプション(Media Gallery 用)を末尾に別枠で付ける(本文語数には数えない)。
"""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from t6_check import CITE, body_of  # noqa: E402

body = body_of((HERE / "writeup-v1-fulldraft.md").read_text())
pub = CITE.sub("", body)
pub = re.sub(r"[ \t]+\n", "\n", pub)
out = HERE / "writeup-kaggle-paste.md"
spec = importlib.util.spec_from_file_location("mf", HERE / "figures" / "make_figures.py")
mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)
caps = "\n".join(f"{n}. {c}" for _, n, c in sorted(mf.CAPTIONS, key=lambda x: x[1]))
caps = CITE.sub("", re.sub(r" Ledger #\d+(/#\d+)*\.", "", caps))
titles = "\n".join(f"{n}. {t}" for n, t in sorted(mf.GALLERY_TITLES.items()))
out.write_text(pub + "\n\n<!-- ↓ Kaggle 本文末尾の「Figure captions」表の中身(表なので語数外) -->\n\n" + caps
               + "\n\n<!-- ↓ Media Gallery の画像タイトル(≤255 字) -->\n\n" + titles + "\n")
n_pub = len([w for w in pub.split() if not re.fullmatch(r"\|[-|:]*", w)])
print(f"wrote {out}  本文語数(公開版、表の罫線トークン除く) = {n_pub}")

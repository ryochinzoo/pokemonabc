#!/usr/bin/env python3
"""_META_DECKS辞書修理: 4エントリの機械生成+挿入+検算 (事前登録 plan-2026-07-29 M6a/任意#3)。

- 指定CSV(正本)から4エントリを機械生成し、王者main.pyの _META_DECKS 先頭に挿入した
  変種 main.py をこのdirに書き出す。
- 検算: 生成物をimportし Counter(エントリ)==Counter(CSV) かつ len==60 をassert。
- 出力: 両main.pyのSHA256(data.md転記用)。
- トラップ排除: meta_lucario_2026-07-14.csv(交差54/60)は参照しない。
"""
import csv
import hashlib
import importlib.util
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../../../../.."))
V = os.path.join(REPO, "verification")
CHAMP = os.path.join(HERE, "../starmie-aggro/main.py")

# 正本CSV(事前登録§2で固定。meta_lucario_2026-07-14.csv は使用禁止=取り違えトラップ)
SOURCES = [
    ("meta_lucario", "decks/official_lucario_2026-07-21.csv"),
    ("meta_archaludon_tomato", "decks/tomato_archaludon_2026-07-22.csv"),
    ("meta_dragapult", "decks/official_dragapult_2026-07-22.csv"),
    ("meta_abomasnow", "decks/official_abomasnow_2026-07-21.csv"),
]


def read_ids(path):
    ids = []
    with open(path) as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line:
                ids.append(int(line))
    return ids


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    entries = {}
    for key, rel in SOURCES:
        ids = sorted(read_ids(os.path.join(V, rel)))
        assert len(ids) == 60, f"{key}: {len(ids)}枚 != 60"
        entries[key] = ids

    src = open(CHAMP).read()
    anchor = "_META_DECKS = {\n"
    assert src.count(anchor) == 1, "アンカー行が一意でない"
    lines = "".join(
        f'    "{k}": {v!r},\n' for k, v in entries.items()
    )
    out = src.replace(anchor, anchor + lines)  # 先頭挿入(strict > の挿入順先勝ち対策)
    out_path = os.path.join(HERE, "main.py")
    with open(out_path, "w") as f:
        f.write(out)

    # 検算: importして中身をCSVと多重集合一致で照合
    spec = importlib.util.spec_from_file_location("variant_main", out_path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, HERE)  # cg/ 解決
    os.chdir(HERE)            # read_deck_csv がcwd依存でも安全に
    spec.loader.exec_module(mod)
    md = mod._META_DECKS
    assert list(md.keys())[:4] == [k for k, _ in SOURCES], "先頭挿入の順序が不正"
    assert len(md) == 9, f"エントリ数 {len(md)} != 9 (新4+既存5)"
    for key, rel in SOURCES:
        want = Counter(read_ids(os.path.join(V, rel)))
        got = Counter(md[key])
        assert got == want and sum(got.values()) == 60, f"{key}: Counter不一致"
    print("ASSERT: 4エントリとも Counter一致 & len==60 & 先頭挿入 & 計9エントリ")
    print(f"SHA256 champion main.py: {sha(CHAMP)}")
    print(f"SHA256 variant  main.py: {sha(out_path)}")


if __name__ == "__main__":
    main()

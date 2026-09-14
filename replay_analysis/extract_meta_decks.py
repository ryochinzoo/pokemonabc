#!/usr/bin/env python3
"""実ラダーの「最頻出デッキ」をアーキタイプ別に抽出する。

D61の教訓: 我々が7/14に抽出した Alakazam デッキは最頻出の実物と **60/60 完全一致**しており、
公開ノートブック版(50.8 / 51.6 一致)より**実ラダーに近かった**。
デッキは公開版から借りるのではなく、**実ラダーの譜から取る**。

入力: `ladder_scout/decks.jsonl`(72体・4,263エピソードぶんの実デッキ)
出力: `verification/decks/meta_<arch>_<band>_2026-08-03.csv` と一致度レポート

使い方: python3 replay_analysis/extract_meta_decks.py [下限 800] [上限 1100]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import band_meta_census as B  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "verification/decks"


def main(lo=800, hi=1100):
    games = B.collect()
    # 提出単位でデッキを1つに畳む(同じ提出は同じ60枚のはず)
    by_sub = {}
    arch_of = {}
    score_of = {}
    for sides in games.values():
        for s in sides:
            sub, sc = s["sub"], s["score"]
            if sub is None or sub in B.OUR_SUBS or sc is None:
                continue
            if not (lo <= sc < hi):
                continue
            key = tuple(sorted(s["deck"]))
            by_sub[sub] = key
            arch_of[sub] = B.classify_b(s["deck"]) or B.classify_a(s["deck"]) or "other"
            score_of[sub] = max(score_of.get(sub, 0), sc)

    per_arch = defaultdict(Counter)          # arch -> deck(tuple) -> 提出数
    for sub, deck in by_sub.items():
        per_arch[arch_of[sub]][deck] += 1

    print(f"# 実ラダー最頻出デッキの抽出  帯 {lo}-{hi-1}  "
          f"(distinct 提出 {len(by_sub)}体)\n")
    OUT.mkdir(exist_ok=True)
    for arch, ctr in sorted(per_arch.items(), key=lambda kv: -sum(kv[1].values())):
        n_sub = sum(ctr.values())
        if n_sub < 8 or arch == "other":
            continue
        deck, n_top = ctr.most_common(1)[0]
        # 全提出に対する加重平均一致(D61と同じ指標)
        agree = sum(len(list((Counter(deck) & Counter(d)).elements())) * c
                    for d, c in ctr.items()) / n_sub
        uniq = len(ctr)
        print(f"## {arch}  提出{n_sub}体 / 相異なるデッキ{uniq}種")
        print(f"   最頻出デッキ: {n_top}体が完全一致({100*n_top/n_sub:.0f}%)  "
              f"加重平均一致 **{agree:.1f}/60**")
        path = OUT / f"meta_{arch}_{lo}_2026-08-03.csv"
        path.write_text("\n".join(str(c) for c in deck) + "\n")
        # 中身(ポケモンのみ)
        names = B.NAMES
        line = Counter()
        for c in deck:
            nm, isp = names.get(c, ("?", False))
            if isp:
                line[nm] += 1
        print("   ポケモン: " + ", ".join(f"{k}×{v}" for k, v in line.most_common()))
        print(f"   → {path.relative_to(REPO)}\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 800,
         int(sys.argv[2]) if len(sys.argv) > 2 else 1100)

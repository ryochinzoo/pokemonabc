#!/usr/bin/env python3
"""公開ノートブック291件のアーキタイプ別露出の計数(模倣可能性の代理指標、探索的)。

2系統を分けて数える(混ぜない):
  - スラッグ言及: ノートブック名にアーキタイプ語が入る(作者が主題として掲げた下界)
  - 中身言及: コード/ipynb 本文に署名語が出る(**上界**。§3.2 の罠 = 相手モデル辞書や
    対策記述を含むため「操縦者の本数」ではない。実行ベース分類は斥候Bの担当)

採用数・強さとの Spearman も出す(k≤9、係数の精度ではなく符号と外れ値が主張)。

使い方: python3 replay_analysis/notebook_exposure.py
"""
from collections import defaultdict
from pathlib import Path

INBOX = Path(__file__).resolve().parent.parent / "verification/reference/_inbox"

KEY = {
    "grimmsnarl": ["grimmsnarl", "marnie"],
    "alakazam": ["alakazam", "kadabra"],
    "crustle": ["crustle", "great-tusk", "great tusk", "greattusk"],
    "lucario": ["lucario"],
    "archaludon": ["archaludon", "duraludon"],
    "tarountula": ["tarountula", "spidops"],
    "starmie": ["starmie", "staryu"],
    "dragapult": ["dragapult"],
    "garchomp": ["garchomp"],
}

# 手元の確定値(2026-08-03/04 時点。出典は ood-imitability.md §5.1)
ADOPT = {"alakazam": 902, "grimmsnarl": 788, "archaludon": 327, "crustle": 317,
         "lucario": 229, "dragapult": 161, "garchomp": 133, "tarountula": 121,
         "starmie": 120}
WR = {"alakazam": 45.4, "grimmsnarl": 56.1, "archaludon": 44.8, "crustle": 59.7,
      "lucario": 47.2, "dragapult": 42.1, "tarountula": 52.9, "starmie": 47.8}


def spearman(xs, ys):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: -v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            for k in range(i, j + 1):
                r[s[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den


def main():
    dirs = [d for d in INBOX.iterdir() if d.is_dir()]
    slug_hits = defaultdict(list)
    content_hits = defaultdict(int)
    for d in dirs:
        slug = d.name.lower()
        for a, keys in KEY.items():
            if any(k.replace(" ", "-") in slug or k.replace(" ", "") in slug for k in keys):
                slug_hits[a].append(d.name)
        text = ""
        for f in list(d.rglob("*.py"))[:8] + list(d.rglob("*.ipynb"))[:4]:
            try:
                text += f.read_text(errors="ignore").lower()[:400000]
            except Exception:
                pass
        for a, keys in KEY.items():
            if any(k in text for k in keys):
                content_hits[a] += 1
    print(f"# ノートブック露出(全{len(dirs)}件)  ※中身言及は上界(相手モデル辞書を含む)")
    print(f"{'arch':<12}{'スラッグ':>7}{'中身':>6}{'採用(個体)':>10}{'帯内勝率':>9}")
    for a in KEY:
        wr = f"{WR[a]:.1f}%" if a in WR else "不足"
        print(f"{a:<12}{len(slug_hits[a]):>7}{content_hits[a]:>6}{ADOPT[a]:>10}{wr:>9}")
    ks = [a for a in KEY if a in WR]
    print("\nSpearman(符号と外れ値のみ主張):")
    print(f"  rho(採用, 帯内非ミラー勝率) k={len(ks)}: "
          f"{spearman([ADOPT[a] for a in ks], [WR[a] for a in ks]):+.3f}")
    print(f"  rho(採用, スラッグ言及)    k={len(KEY)}: "
          f"{spearman([ADOPT[a] for a in KEY], [len(slug_hits[a]) for a in KEY]):+.3f}")
    print("  外れ値: grimmsnarl(採用2位・スラッグ3件) → ノートブック経路では説明不能。"
          "garchomp(標準化63%・採用7位) → レシピがあっても可視性が無ければ増えない。")


if __name__ == "__main__":
    main()

"""v2最終掃引の集計 — 事前登録 docs/memo/prereg-2026-08-09-v2final.md に対応。

**fail closed**: 登録どおりの全セルが登録どおりの N で揃っていなければ**合成を出さない**。
理由: `cew_stats.py:cew_with_se` は渡されたセルで重みを再正規化するので、
**欠けたまま合成すると「ノイズの多い同じ指標」ではなく「別の指標」になる**。
これは止まらずに「もっともらしい間違った答え」を出す唯一の経路なので、コードで塞ぐ。

主判定は2本出す:
  ① 合算CI     — 二項分散のみ(`cew_stats.py` と同じモデル)
  ② batch-means CI — ブロックごとの合成差 d_j から `d̄ ± t5·sd(d_j)/√6`
     **過分散があれば自動的に締まり、無ければ締まらない。** 主判定はこちら。
副次: λ̂ = sd(d_j)·√6 / SE_binomial (D69以来の未決問題「過分散は実在するか」の決着)

使い方: python3 verification/v2final_aggregate.py <results.tsv>
"""
import collections
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cew import WEIGHTS  # noqa: E402  重みの唯一の正典

ARM_A = "deckswap-tarountula-pilotfix"
ARM_B = "deckswap-tarountula-v2"
BLOCKS = ["b1", "b2", "b3", "b4", "b5", "b6"]
PER_BLOCK = {"alakazam": 292, "grimmsnarl": 368, "crustle": 52, "lucario": 168, "archaludon": 124}
T5_95 = 2.5706          # t(df=5), 両側95%
ADOPT = 2.0             # D29 の標準採用閾値(真にN非依存)


def load(path):
    """(arm, cell, tag) をキーに **最後の行で上書き** する。再開時の二重計上を防ぐ。"""
    rows = {}
    with open(path) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            arm, cell, tag, w, n = p[0], p[1], p[2], int(p[3]), int(p[4])
            rows[(arm, cell, tag)] = (w, n)
    return rows


def composite(cells):
    """cells: {gauge: (wins, n)} -> (CEW%, 二項SE%)"""
    tw = sum(WEIGHTS[g] for g in cells)
    c = v = 0.0
    for g, (w, n) in cells.items():
        wt = WEIGHTS[g] / tw
        p = w / n
        c += wt * p
        v += wt ** 2 * p * (1 - p) / n
    return c * 100, math.sqrt(v) * 100


def main(path):
    rows = load(path)
    print("### v2最終掃引の集計(事前登録 prereg-2026-08-09-v2final.md)\n")

    # ---- fail closed: 完全性の検査 ----
    missing = [(a, c, t) for a in (ARM_A, ARM_B) for c in PER_BLOCK for t in BLOCKS
               if (a, c, t) not in rows]
    if missing:
        print(f"未完のセルが {len(missing)} 件ある。**合成は出さない**(欠けたまま合成すると別指標になる)")
        for m in missing[:12]:
            print("   欠", m)
        return 2

    tot = {}
    for arm in (ARM_A, ARM_B):
        cells = {}
        for c in PER_BLOCK:
            w = sum(rows[(arm, c, t)][0] for t in BLOCKS)
            n = sum(rows[(arm, c, t)][1] for t in BLOCKS)
            want = PER_BLOCK[c] * len(BLOCKS)
            if n != want:
                print(f"FATAL: {arm} {c} の N が {n}(登録は {want})。**合成は出さない**")
                return 2
            cells[c] = (w, n)
        tot[arm] = cells

    print("| セル | 重み | 腕A pilotfix | 腕B v2全部乗せ | 差 |")
    print("|---|---|---|---|---|")
    for c in sorted(PER_BLOCK, key=lambda k: -WEIGHTS[k]):
        wa, na = tot[ARM_A][c]
        wb, nb = tot[ARM_B][c]
        print(f"| {c} | {WEIGHTS[c]:.4f} | {100*wa/na:.2f}% ({wa}/{na}) | "
              f"{100*wb/nb:.2f}% ({wb}/{nb}) | {100*wb/nb - 100*wa/na:+.2f}pt |")

    ca, sa = composite(tot[ARM_A])
    cb, sb = composite(tot[ARM_B])
    d = cb - ca
    se_bin = math.sqrt(sa ** 2 + sb ** 2)
    print(f"\n合成: 腕A {ca:.2f}%  腕B {cb:.2f}%   **差 {d:+.2f}pt**")
    print(f"① 合算CI(二項のみ): SE {se_bin:.3f}pt  95%CI [{d-1.96*se_bin:+.2f}, {d+1.96*se_bin:+.2f}]")

    # ---- ② batch-means(主判定)----
    dj = []
    for t in BLOCKS:
        a = composite({c: rows[(ARM_A, c, t)] for c in PER_BLOCK})[0]
        b = composite({c: rows[(ARM_B, c, t)] for c in PER_BLOCK})[0]
        dj.append(b - a)
    dbar = sum(dj) / len(dj)
    sd = math.sqrt(sum((x - dbar) ** 2 for x in dj) / (len(dj) - 1))
    se_bm = sd / math.sqrt(len(dj))
    lo, hi = dbar - T5_95 * se_bm, dbar + T5_95 * se_bm
    lam = se_bm / se_bin if se_bin else float("nan")
    print(f"② batch-means(主判定): ブロック別の差 " + ", ".join(f"{x:+.2f}" for x in dj))
    print(f"   d̄ {dbar:+.2f}pt  sd {sd:.3f}  SE {se_bm:.3f}pt  **95%CI [{lo:+.2f}, {hi:+.2f}]**")
    print(f"   ★λ̂ = SE_batch / SE_binomial = **{lam:.2f}**"
          f"  ({'過分散あり' if lam > 1.2 else '過分散は検出されず'}; "
          f"cew.py が記録した 1.40 との比較)")

    # ---- 事前登録 §5 の判定 ----
    print("\n### 判定(事前登録 §5、測定前に凍結)")
    detected = lo > 0
    adopt = dbar >= ADOPT
    if lo > 0 and adopt:
        v = "**効果を検出し、採用域 → 8/11 の枠で提出(ゆうじ承認 + T4懐疑パスを前置)**"
    elif lo > 0:
        v = f"効果は検出したが 点推定 {dbar:+.2f}pt < 採用閾値 +{ADOPT}pt → **提出しない**"
    elif hi < 0:
        v = "**v2 は有害** → 提出しない。v2系統を打ち切る"
    else:
        v = "**検出できず** → 提出しない。pilotfix で凍結"
    print(f"  CI下限 > 0 か: {detected}   点推定 ≥ +{ADOPT}pt か: {adopt}")
    print(f"  → {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results.tsv"))

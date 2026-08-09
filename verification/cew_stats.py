#!/usr/bin/env python3
"""cew_stats.py — CEWに**信頼区間**を付ける。cew.py(点推定)の補完。

なぜ必要か: 採用閾値は「基準線比 +2pt」だが、**その+2ptが何σなのかを誰も計算していなかった**。
2026-07-23の墓場バッチで、Neyman配分 N=800 のCEWの解析SEが約1.6ptと判明した。
つまり素朴に測ると +2pt は約1σでしかない。**閾値を跨いだかだけを見て採否を決めると、
測定ノイズを採用してしまう。**

CEW = Σ w_i・p_i (w=D35の遭遇重み)。各成分は二項なので
    Var(CEW) = Σ w_i^2・p_i(1-p_i)/n_i
2構成の比較は SE_diff = sqrt(SE_a^2 + SE_b^2)。

使い方(勝数と試合数を成分ごとに渡す):
    python3 verification/cew_stats.py \\
        --a alakazam=1173/1248,crustle=371/380,lucario=177/934,archaludon=80/638 \\
        --b alakazam=1180/1248,crustle=373/380,lucario=220/934,archaludon=95/638

    # 単一構成なら --a だけでよい。--reps で反復の過分散検定(χ²)も行う:
    python3 verification/cew_stats.py --reps "1173/1248,371/380,177/934,80/638" ...

2026-08-09: ゲージ集合を T3再較正で入れ替えた(cew.py 参照)。
  旧: lucario / archaludon / dragapult / abomasnow  ← dragapult は実シェアの7.4倍、
      abomasnow は 800-1099帯の census に出現しないのに 5.6% の重みを持っていた。
  新: alakazam / crustle / lucario / archaludon     ← 実シェア上位の較正済み族外4面。
"""
import argparse
import math

from cew import WEIGHTS

# --reps の位置引数の順序。WEIGHTS の宣言順と一致させること。
ORDER = ["alakazam", "crustle", "lucario", "archaludon"]


def parse_cells(spec: str) -> dict:
    out = {}
    for part in spec.split(","):
        name, frac = part.split("=")
        w, n = frac.split("/")
        out[name.strip()] = (int(w), int(n))
    return out


def cew_with_se(cells: dict) -> tuple:
    """cells: {gauge: (wins, n)} -> (CEW%, SE%)"""
    tw = sum(WEIGHTS[g] for g in cells)
    cew = var = 0.0
    for g, (w, n) in cells.items():
        wt = WEIGHTS[g] / tw          # 一部成分のみでも重みを再正規化(cew.pyと同じ規約)
        p = w / n
        cew += wt * p
        var += (wt ** 2) * p * (1 - p) / n
    return cew * 100, math.sqrt(var) * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", help="構成A: gauge=wins/n,...")
    ap.add_argument("--b", help="構成B(比較する場合)")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--reps", nargs="*", help='反復: "w/n,w/n,w/n,w/n" を alakazam,crustle,lucario,archaludon の順で')
    args = ap.parse_args()

    if args.reps:
        print("=== 反復ごとのCEWと過分散検定 ===")
        vals, ses = [], []
        for i, rep in enumerate(args.reps, 1):
            cells = {}
            for g, frac in zip(ORDER, rep.split(",")):
                w, n = frac.split("/")
                cells[g] = (int(w), int(n))
            c, s = cew_with_se(cells)
            vals.append(c)
            ses.append(s)
            print(f"  反復{i}: CEW = {c:6.2f}%   (解析SE {s:.3f}pt)")
        k = len(vals)
        mean = sum(vals) / k
        var_obs = sum((v - mean) ** 2 for v in vals) / (k - 1)
        sd_obs = math.sqrt(var_obs)
        sigma = sum(ses) / k                       # 理論(二項)SE
        chi2 = (k - 1) * var_obs / (sigma ** 2)
        crit = {1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488, 5: 11.070}.get(k - 1)
        print(f"\n  平均CEW = {mean:.2f}%   (これが新しい基準線。全{k}反復の合算)")
        print(f"  実測SD  = {sd_obs:.3f}pt   理論(二項)SE = {sigma:.3f}pt   比 = {sd_obs/sigma:.2f}x")
        print(f"  過分散検定 χ²({k-1}) = {chi2:.2f}   95%臨界値 = {crit}"
              f"   → {'**過分散あり**' if chi2 > crit else '過分散は検出されず'}")
        print(f"  ※df={k-1}は検出力が低い。『過分散なし』ではなく『検出できず』と書くこと。")
        print(f"\n  【重要】単一測定(N=800相当)のSEは約{sigma:.2f}pt。基準線を固定しても")
        print(f"  新旧差のSEは約{math.sqrt(sigma**2 + (sigma/math.sqrt(k))**2):.2f}pt"
              f" → 採用閾値+2.0ptは約{2.0/math.sqrt(sigma**2 + (sigma/math.sqrt(k))**2):.2f}σ。")
        return

    ca, sa = cew_with_se(parse_cells(args.a))
    print(f"{args.label_a}: CEW = {ca:.2f}%  ± {1.96*sa:.2f} (95%)   SE={sa:.3f}pt")
    if args.b:
        cb, sb = cew_with_se(parse_cells(args.b))
        d = cb - ca
        sd = math.sqrt(sa ** 2 + sb ** 2)
        lo, hi = d - 1.96 * sd, d + 1.96 * sd
        print(f"{args.label_b}: CEW = {cb:.2f}%  ± {1.96*sb:.2f} (95%)   SE={sb:.3f}pt")
        print(f"\n差 ({args.label_b} − {args.label_a}) = {d:+.2f}pt   SE_diff = {sd:.3f}pt")
        print(f"95%CI = [{lo:+.2f}, {hi:+.2f}]")
        print(f"  0 を含む: {'はい(差は検出されず)' if lo <= 0 <= hi else 'いいえ'}")
        print(f"  +2pt を含む: {'はい(+2pt優位を排除できない)' if lo <= 2.0 <= hi else 'いいえ(排除できた)'}")


if __name__ == "__main__":
    main()

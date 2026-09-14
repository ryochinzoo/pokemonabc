"""マスターコントロール掃引の集計 — 事前登録 docs/memo/prereg-2026-08-10-starmie-mastercontrol.md。

`v2final_aggregate.py`(D72)と同じ方式。腕・ブロック数・セル別Nだけが違うので、
**あちらは D72 の記録として一切触らず**、こちらを別ファイルに置く。

**fail closed**: 登録どおりの全セルが登録どおりの N で揃っていなければ**合成を出さない**。
理由: 重みは渡されたセルで再正規化されるので、**欠けたまま合成すると
「ノイズの多い同じ指標」ではなく「別の指標」になる**。
止まらずに「もっともらしい間違った答え」を出す唯一の経路なので、コードで塞ぐ。

主判定は2本出す:
  ① 合算CI     — 二項分散のみ
  ② batch-means CI — ブロックごとの合成差 d_j から d̄ ± t3·sd(d_j)/√4
     **過分散があれば自動的に締まり、無ければ締まらない。** 主判定はこちら。
副次: λ̂ = SE_batch / SE_binomial(D72 は同一走行内で λ̂=0.86 = 過分散なしだった。再確認する)

使い方: python3 verification/mastercontrol_aggregate.py <results.tsv>
"""
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cew import WEIGHTS, BASELINE  # noqa: E402  重みの唯一の正典

ARM_A = "starmie-aggro"                  # 基準線 = 実ラダー793.9の実物
ARM_B = "starmie-aqua"                   # 水単デッキ + V5盤面価値層
BLOCKS = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
PER_BLOCK = {"alakazam": 142, "grimmsnarl": 94, "lucario": 64, "crustle": 52, "archaludon": 48}
# ★t分位点は len(BLOCKS) から導出する。`v2final_aggregate.py` は T5_95 をハードコードしており、
# ブロック数だけ変えて t を直し忘れると **CIが狭くなるのに何のエラーも出ない**(T7レンズA指摘)。
_T_95 = {1: 12.706, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706, 6: 2.4469,
         7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281, 11: 2.2010, 15: 2.1314}
T_95 = _T_95[len(BLOCKS) - 1]
ADOPT = 2.0             # D29 の標準採用閾値(真にN非依存)

# 事前登録 §4 の対面別予測区間(T1のセンサー。測定前に凍結済み)
PREDICTED = {"alakazam": (55, 75), "grimmsnarl": (25, 55), "crustle": (75, 92),
             "lucario": (33, 53), "archaludon": (25, 45)}
JP = {"alakazam": "フーディン", "grimmsnarl": "オーロンゲ", "crustle": "イワパレス",
      "lucario": "メガルカリオ", "archaludon": "ブリジュラス"}


def load(path):
    """(arm, cell, tag) をキーに **最後の行で上書き** する。再開時の二重計上を防ぐ。"""
    rows = {}
    with open(path) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            rows[(p[0], p[1], p[2])] = (int(p[3]), int(p[4]))
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
    print("### 極・水単アグロスターミー掃引の集計"
          "(事前登録 prereg-2026-08-11-starmie-aqua.md)\n")

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

    print("| セル | 重み | 腕A starmie-aggro(基準線) | 腕B starmie-aqua | 差 | 事前予測 | 判定 |")
    print("|---|---|---|---|---|---|---|")
    outside = []
    for c in sorted(PER_BLOCK, key=lambda k: -WEIGHTS[k]):
        wa, na = tot[ARM_A][c]
        wb, nb = tot[ARM_B][c]
        pb = 100 * wb / nb
        lo, hi = PREDICTED[c]
        ok = lo <= pb <= hi
        if not ok:
            outside.append((c, pb, lo, hi))
        print(f"| {JP[c]} | {WEIGHTS[c]:.4f} | {100*wa/na:.2f}% ({wa}/{na}) | "
              f"{pb:.2f}% ({wb}/{nb}) | {pb - 100*wa/na:+.2f}pt | {lo}〜{hi}% | "
              f"{'◯' if ok else '**外**'} |")

    ca, sa = composite(tot[ARM_A])
    cb, sb = composite(tot[ARM_B])
    d = cb - ca
    se_bin = math.sqrt(sa ** 2 + sb ** 2)
    print(f"\n合成: 腕A {ca:.2f}%  腕B {cb:.2f}%   **差 {d:+.2f}pt**")
    print(f"  (参考: cew.py の BASELINE 定数 = {BASELINE:.2f}%。"
          f"判定は本走行で同時に測った腕A {ca:.2f}% を基準にする — 事前登録 §3)")
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
    lo, hi = dbar - T_95 * se_bm, dbar + T_95 * se_bm
    lam = se_bm / se_bin if se_bin else float("nan")
    print("② batch-means(主判定): ブロック別の差 " + ", ".join(f"{x:+.2f}" for x in dj))
    print(f"   d̄ {dbar:+.2f}pt  sd {sd:.3f}  SE {se_bm:.3f}pt  **95%CI [{lo:+.2f}, {hi:+.2f}]**")
    print(f"   ★λ̂ = SE_batch / SE_binomial = **{lam:.2f}**"
          f"  ({'過分散あり' if lam > 1.2 else '過分散は検出されず'}; D72 は 0.86)")

    # ---- 事前登録 §3 の判定 ----
    print("\n### 判定(事前登録 §3、測定前に凍結)")
    adopt = d >= ADOPT
    if adopt:
        v = ("**採用候補 → ゆうじに提出承認を求める**"
             "(T4懐疑パス: ベイズ検査 + 独立追試 + ラダー予測の事前登録を前置)")
    elif d > 0:
        v = f"0 < Δ {d:+.2f}pt < +{ADOPT}pt → **昇格せず。提出しない。記録のみ**"
    else:
        v = f"Δ {d:+.2f}pt ≤ 0 → **棄却**"
    print(f"  主判定: 点推定 Δ ≥ +{ADOPT}pt か: {adopt}")
    print(f"  併記(CI): batch-means 95%CI [{lo:+.2f}, {hi:+.2f}] / CI下限 > 0 か: {lo > 0}")
    print("  ※ +2pt は魔法の壁ではない。跨いだかだけで判定せず、必ずCIを併記する(playbook §1)")
    print(f"  → {v}")

    # ---- T1センサー: 対面別予測区間の外に出たか ----
    print("\n### T1センサー(事前登録 §4 の予測区間)")
    if outside:
        print(f"  **{len(outside)} セルが予測区間の外に出た** → T1発火を検討する:")
        for c, pb, lo_, hi_ in outside:
            print(f"    {JP[c]}: 実測 {pb:.2f}% vs 予測 {lo_}〜{hi_}%")
    else:
        print("  全セルが予測区間内。T1不発。")

    # ---- 反証テスト(事前登録 §5): 退却の修理は勝率に変換されたか ----
    luc = 100 * tot[ARM_B]["lucario"][0] / tot[ARM_B]["lucario"][1]
    print("\n### 反証テスト(事前登録 §5): 副センサー = メガルカリオ対面")
    print("  「倒せない→逃げる」が最も多発するはずのセル。L1が本物ならここが最大に動く。")
    print(f"  腕A 実測 {100*tot[ARM_A]['lucario'][0]/tot[ARM_A]['lucario'][1]:.2f}% → 腕B {luc:.2f}%")
    if luc < 45:
        print("  → **反証**: 45%未満。退却の修理は勝率に変換されていない。")
        print("     (発火は実証済みなので『機構が動いていない』ではなく『動いたが効かない』と記録すること)")
    else:
        print("  → 支持: 45%以上。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results.tsv"))

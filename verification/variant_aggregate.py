"""1枚差し3腕掃引(variant_sweep)の集計 — 事前登録 docs/memo/prereg-2026-08-13-final2.md §1。

`aqua_aggregate.py`(D76bis)と同じ方式の3腕版。**あちらは D76bis の記録として一切触らず**、
こちらを別ファイルに置く(mastercontrol_aggregate.py と同じ運用)。

**fail closed**: 登録どおりの全セルが登録どおりの N で揃っていなければ**合成を出さない**。
重みは渡されたセルで再正規化されるので、欠けたまま合成すると別の指標になる。

判定(事前登録 §1、掃引完了前に凍結):
  argmax変種(boss/pad の合成が高い方)が
    ① 合成(点推定) ≥ 対照 かつ ② 全セルで 変種 ≥ 対照 − 8pt
  を両方満たす → その変種を提出。該当なし → aqua バイト同一を提出。

使い方: python3 verification/variant_aggregate.py <results.tsv>
"""
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cew import WEIGHTS  # noqa: E402  重みの唯一の正典

CONTROL = "starmie-aqua"                 # 対照 = 実ラダー733.7の実物(45910ac6/be51da6d)
VARIANTS = ["starmie-aqua-boss",         # −1 夜のタンカ / +1 ボスの指令
            "starmie-aqua-pad"]          # −1 ジャッジマン / +1 ポケパッド
ARMS = [CONTROL] + VARIANTS
BLOCKS = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
PER_BLOCK = {"alakazam": 142, "grimmsnarl": 94, "lucario": 64, "crustle": 52, "archaludon": 48}
_T_95 = {1: 12.706, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706, 6: 2.4469,
         7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281, 11: 2.2010, 15: 2.1314}
T_95 = _T_95[len(BLOCKS) - 1]
CELL_FLOOR = -8.0       # 事前登録 §1: 対照−8pt超の崩落セルがあれば変種は失格
JP = {"alakazam": "フーディン", "grimmsnarl": "オーロンゲ", "crustle": "イワパレス",
      "lucario": "メガルカリオ", "archaludon": "ブリジュラス"}


def load(path):
    """(arm, cell, tag) をキーに最後の行で上書きする。再開時の二重計上を防ぐ。"""
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
    print("### 1枚差し3腕掃引の集計(事前登録 prereg-2026-08-13-final2.md §1)\n")

    missing = [(a, c, t) for a in ARMS for c in PER_BLOCK for t in BLOCKS
               if (a, c, t) not in rows]
    if missing:
        print(f"未完のセルが {len(missing)} 件ある。**合成は出さない**(欠けたまま合成すると別指標になる)")
        for m in missing[:12]:
            print("   欠", m)
        return 2

    tot = {}
    for arm in ARMS:
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

    print("| セル | 重み | 対照 aqua | boss | Δboss | pad | Δpad |")
    print("|---|---|---|---|---|---|---|")
    cell_delta = {v: {} for v in VARIANTS}
    for c in sorted(PER_BLOCK, key=lambda k: -WEIGHTS[k]):
        wa, na = tot[CONTROL][c]
        pa = 100 * wa / na
        parts = [f"| {JP[c]} | {WEIGHTS[c]:.4f} | {pa:.2f}% ({wa}/{na})"]
        for v in VARIANTS:
            wv, nv = tot[v][c]
            pv = 100 * wv / nv
            cell_delta[v][c] = pv - pa
            parts.append(f"{pv:.2f}% | {pv - pa:+.2f}pt")
        print(" | ".join(parts) + " |")

    ca, sa = composite(tot[CONTROL])
    print(f"\n合成: 対照 aqua **{ca:.2f}%**(二項SE {sa:.3f}pt)")
    verdicts = {}
    for v in VARIANTS:
        cv, sv = composite(tot[v])
        d = cv - ca
        se_bin = math.sqrt(sa ** 2 + sv ** 2)
        dj = []
        for t in BLOCKS:
            a = composite({c: rows[(CONTROL, c, t)] for c in PER_BLOCK})[0]
            b = composite({c: rows[(v, c, t)] for c in PER_BLOCK})[0]
            dj.append(b - a)
        dbar = sum(dj) / len(dj)
        sd = math.sqrt(sum((x - dbar) ** 2 for x in dj) / (len(dj) - 1))
        se_bm = sd / math.sqrt(len(dj))
        lo, hi = dbar - T_95 * se_bm, dbar + T_95 * se_bm
        lam = se_bm / se_bin if se_bin else float("nan")
        worst = min(cell_delta[v].items(), key=lambda kv: kv[1])
        ok_comp = d >= 0
        ok_cell = worst[1] >= CELL_FLOOR
        verdicts[v] = (d, ok_comp and ok_cell)
        print(f"\n{v}: 合成 **{cv:.2f}%**  Δ {d:+.2f}pt")
        print(f"  ① 合算CI(二項): SE {se_bin:.3f}pt  95%CI [{d-1.96*se_bin:+.2f}, {d+1.96*se_bin:+.2f}]")
        print("  ② batch-means: ブロック別 " + ", ".join(f"{x:+.2f}" for x in dj))
        print(f"     d̄ {dbar:+.2f}pt  SE {se_bm:.3f}pt  95%CI [{lo:+.2f}, {hi:+.2f}]  λ̂ {lam:.2f}")
        print(f"  規則①(合成 ≥ 対照): {'合' if ok_comp else '否'}"
              f"  規則②(全セル ≥ 対照−8pt、最悪 {JP[worst[0]]} {worst[1]:+.2f}pt): "
              f"{'合' if ok_cell else '否'}")

    print("\n### 判定(事前登録 §1、機械適用)")
    passing = [(d, v) for v, (d, ok) in verdicts.items() if ok]
    if passing:
        d, v = max(passing)
        print(f"  → **{v} を提出**(argmax変種、Δ {d:+.2f}pt、規則①②合格。正当性ゲートへ)")
    else:
        print("  → 合格した変種なし。**aqua バイト同一(45910ac6/be51da6d)を提出**")
    print("  ※ どの分岐でも提出は1本だけ。窓 = {aqua 55421865(733.7), 新提出}(§1-5)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results.tsv"))

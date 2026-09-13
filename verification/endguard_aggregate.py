"""ENDガード2腕掃引(endguard_sweep)の集計 — 事前登録 docs/memo/prereg-2026-08-14-endguard.md(v2)。

variant_aggregate.py(D78)の2腕版。あちらは記録として触らない。
**fail closed**: 登録どおりの全セルが登録どおりの N で揃っていなければ合成を出さない。

判定(v2で凍結、掃引起動前):
  採用候補   : Δ ≥ +2.0pt かつ batch-means 95%CI下限 > 0 かつ 全セル ≥ 対照−8pt
               → さらに T4(独立追試 N=3,200)で pooled Δ ≥ +2.0pt を要してから
                 最終2枠差し替えの「検討」に載る(実施判断=ゆうじ)
  灰色域     : 上記に満たない Δ ≥ 0 → **不採用**(閾値は動かさない)。記録のみ。
               探り提出は D75(提出の門のみ)でゆうじ判断
  棄却       : Δ < 0 かつ CI が 0 を排除 → ガード棄却
  機構センサー: grimmsnarl セルの Δ ≤ 0 → 「ENDストール→オーロンゲ敗北」の機構帰属を反証
               (合成が良くても writeup にオーロンゲ物語としては書かない)
  計器チェック: 対照合成が過去2走(54.45 / 54.31)の帯から |Δ| > 1.5pt 外れたら計器故障を疑い停止

使い方: python3 verification/endguard_aggregate.py <results.tsv>
"""
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cew import WEIGHTS  # noqa: E402  重みの唯一の正典

CONTROL = "starmie-aqua"                     # 対照 = 実ラダー最終2枠の実物(45910ac6/be51da6d)
VARIANT = "starmie-aqua-endguard"            # main.py L6 のみ差(deck.csv バイト同一)
ARMS = [CONTROL, VARIANT]
BLOCKS = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
PER_BLOCK = {"alakazam": 142, "grimmsnarl": 94, "lucario": 64, "crustle": 52, "archaludon": 48}
T_95 = 2.3646                                # t(df=7)
ADOPT_DELTA = 2.0
CELL_FLOOR = -8.0
CONTROL_HISTORY = (54.45, 54.31)             # 8/13 / 8/11 の独立2走
CONTROL_TOL = 1.5
JP = {"alakazam": "フーディン", "grimmsnarl": "オーロンゲ", "crustle": "イワパレス",
      "lucario": "メガルカリオ", "archaludon": "ブリジュラス"}


def load(path):
    rows = {}
    with open(path) as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            rows[(p[0], p[1], p[2])] = (int(p[3]), int(p[4]))
    return rows


def composite(cells):
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
    print("### ENDガード2腕掃引の集計(事前登録 prereg-2026-08-14-endguard.md v2、機械適用)\n")

    missing = [(a, c, t) for a in ARMS for c in PER_BLOCK for t in BLOCKS
               if (a, c, t) not in rows]
    if missing:
        print(f"未完のセルが {len(missing)} 件。**合成は出さない**")
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
                print(f"FATAL: {arm} {c} の N が {n}(登録は {want})。合成は出さない")
                return 2
            cells[c] = (w, n)
        tot[arm] = cells

    print("| セル | 重み | 対照 aqua | endguard | Δ |")
    print("|---|---|---|---|---|")
    cell_delta = {}
    for c in sorted(PER_BLOCK, key=lambda k: -WEIGHTS[k]):
        wa, na = tot[CONTROL][c]
        wv, nv = tot[VARIANT][c]
        pa, pv = 100 * wa / na, 100 * wv / nv
        cell_delta[c] = pv - pa
        print(f"| {JP[c]} | {WEIGHTS[c]:.4f} | {pa:.2f}% ({wa}/{na}) | {pv:.2f}% ({wv}/{nv}) | {pv-pa:+.2f}pt |")

    ca, sa = composite(tot[CONTROL])
    cv, sv = composite(tot[VARIANT])
    d = cv - ca
    se_bin = math.sqrt(sa ** 2 + sv ** 2)
    dj = []
    for t in BLOCKS:
        a = composite({c: rows[(CONTROL, c, t)] for c in PER_BLOCK})[0]
        b = composite({c: rows[(VARIANT, c, t)] for c in PER_BLOCK})[0]
        dj.append(b - a)
    dbar = sum(dj) / len(dj)
    sd = math.sqrt(sum((x - dbar) ** 2 for x in dj) / (len(dj) - 1))
    se_bm = sd / math.sqrt(len(dj))
    lo, hi = dbar - T_95 * se_bm, dbar + T_95 * se_bm
    lam = se_bm / se_bin if se_bin else float("nan")

    print(f"\n合成: 対照 **{ca:.2f}%**(二項SE {sa:.3f}) / endguard **{cv:.2f}%**  Δ **{d:+.2f}pt**")
    print(f"  合算CI(二項): 95%CI [{d-1.96*se_bin:+.2f}, {d+1.96*se_bin:+.2f}]")
    print("  batch-means: " + ", ".join(f"{x:+.2f}" for x in dj))
    print(f"    d̄ {dbar:+.2f}pt  SE {se_bm:.3f}  95%CI [{lo:+.2f}, {hi:+.2f}]  λ̂ {lam:.2f}")

    print("\n### 判定(機械適用)")
    hist_dev = min(abs(ca - h) for h in CONTROL_HISTORY)
    if hist_dev > CONTROL_TOL:
        print(f"  ⛔ 計器チェック不合格: 対照合成 {ca:.2f} が過去2走({CONTROL_HISTORY})から"
              f" {hist_dev:.2f}pt 逸脱(許容 {CONTROL_TOL})。**判定を出さず停止**")
        return 3
    print(f"  計器チェック: 対照 {ca:.2f} vs 過去2走 → 逸脱 {hist_dev:.2f}pt ≤ {CONTROL_TOL} 合")

    worst = min(cell_delta.items(), key=lambda kv: kv[1])
    grim = cell_delta["grimmsnarl"]
    mech = "支持" if grim > 0 else "**反証**(オーロンゲ物語は書かない)"
    print(f"  機構センサー(grimmsnarlセル Δ {grim:+.2f}pt): {mech}")
    print(f"  セル床(最悪 {JP[worst[0]]} {worst[1]:+.2f}pt ≥ {CELL_FLOOR}): "
          f"{'合' if worst[1] >= CELL_FLOOR else '否'}")

    if d >= ADOPT_DELTA and lo > 0 and worst[1] >= CELL_FLOOR:
        print(f"  → **採用候補**(Δ {d:+.2f} ≥ +{ADOPT_DELTA} かつ CI下限 {lo:+.2f} > 0 かつ セル床合格)")
        print("    次: T4独立追試 N=3,200 → pooled Δ ≥ +2.0 なら最終2枠差し替えの検討へ(ゆうじ判断)")
    elif d < 0 and hi < 0:
        print(f"  → **棄却**(Δ {d:+.2f} < 0、CIが0を排除)。記録して終了")
    else:
        print(f"  → **灰色域 = 不採用**(Δ {d:+.2f}。閾値は動かさない)。記録のみ。"
              "探り提出は D75(提出の門のみ)でゆうじ判断")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results.tsv"))

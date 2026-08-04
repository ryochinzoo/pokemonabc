#!/usr/bin/env python3
"""新規性プレミアムの減衰 — 「フィールドは見たことのないデッキに系統的に弱いか」。

3つの時計を持つ:
  1. **同一対面ペアの週次勝率**(マッチアップ構造の交絡を対で固定): decks.jsonl は
     両側のデッキが100%既知だが時刻が無い → パネル48,752点の (episodeId, createTime)
     から**単調内挿**で時刻を付与する(エピソードIDはKaggle全体で時刻単調。検証つき)。
  2. **レーティング調整済み残差**(追跡個体の全試合、相手アーキ不要): win − P(win|Δrating)。
     昇り坂の機械的高勝率(Elo収束)を物差しごと除いた「レート期待からの超過成績」。
  3. **採用曲線**(全既知 submissionId の dateSubmitted、取得追加ゼロ):
     アーキタイプ別の週次参入数。SUMI のシェア曲線の「個体数」版。

副産物: アーキタイプ別デッキ標準化率(distinct提出単位) = 模倣可能性の直接観測。

使い方: python3 replay_analysis/novelty_decay.py
"""
import json
import math
import random
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import band_meta_census as B  # noqa: E402

HERE = Path(__file__).resolve().parent
LS = HERE / "ladder_scout"
T0 = datetime(2026, 6, 16, tzinfo=timezone.utc).timestamp()
DAY = 86400.0
ARCHS = ["grimmsnarl", "alakazam", "crustle", "lucario", "archaludon",
         "tarountula", "starmie", "dragapult", "garchomp"]
rng = random.Random(20260804)


def week(t):
    return int((t - T0) // (7 * DAY))


def wk_label(w):
    return datetime.fromtimestamp(T0 + w * 7 * DAY, tz=timezone.utc).strftime("%m/%d")


def load_panel():
    meta = {int(k): v for k, v in json.loads((LS / "submeta.json").read_text()).items()}
    rows = [json.loads(l) for l in open(LS / "panel.jsonl")]
    return meta, rows


def build_interp(rows):
    """episodeId → epoch秒の単調内挿。単調性違反率を開示する。"""
    pts = sorted({(r["ep"], r["t"]) for r in rows})
    inv = sum(1 for i in range(1, len(pts)) if pts[i][1] < pts[i - 1][1])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    print(f"  内挿アンカー {len(pts)} 点 / 隣接時刻逆転 {inv} 件 "
          f"({100*inv/max(1,len(pts)):.2f}% — IDは時刻に対しほぼ単調)")

    def f(ep):
        i = bisect_left(xs, ep)
        if i == 0:
            return ys[0]
        if i >= len(xs):
            return ys[-1]
        if xs[i] == ep:
            return ys[i]
        x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
        return y0 + (y1 - y0) * (ep - x0) / (x1 - x0)
    return f, (xs[0], xs[-1])


def episode_universe(meta, rows, interp, rng_ok):
    """対面ペア用の統合宇宙: panel(正確な時刻) ∪ decks.jsonl(内挿時刻、アーキ100%既知)。
    返り値: {ep: (t, aA, aB, winner∈{0,1}, subA, subB, scA, scB, src)}"""
    uni = {}
    for r in rows:
        if r["ep"] in uni:
            continue
        ma = (meta.get(r["sub"]) or {}).get("arch")
        oa = (meta.get(r["osub"]) or {}).get("arch")
        if not ma or not oa:
            continue
        if r["rw"] == 1:
            win = 0
        elif r["orw"] == 1:
            win = 1
        else:
            continue
        uni[r["ep"]] = (r["t"], ma, oa, win, r["sub"], r["osub"],
                        r["sc"], r["osc"], "panel")
    lo_ep, hi_ep = rng_ok
    n_extra = n_out = 0
    for line in open(LS / "decks.jsonl"):
        r = json.loads(line)
        ep = r["ep"]
        if ep in uni:
            continue
        s0, s1 = r["s"]
        a0 = B.classify_b(s0["d"]) or B.classify_a(s0["d"])
        a1 = B.classify_b(s1["d"]) or B.classify_a(s1["d"])
        if not a0 or not a1:
            continue
        if s0["rw"] == 1:
            win = 0
        elif s1["rw"] == 1:
            win = 1
        else:
            continue
        if not (lo_ep <= ep <= hi_ep):
            n_out += 1          # 内挿範囲外(外挿になるので落とす。開示)
            continue
        uni[ep] = (interp(ep), a0, a1, win, s0["sub"], s1["sub"],
                   s0["sc"], s1["sc"], "decks")
        n_extra += 1
    print(f"  統合宇宙: {len(uni)} エピソード(panel由来 {len(uni)-n_extra} / "
          f"decks.jsonl追加 {n_extra} / 内挿範囲外で落とした {n_out})")
    return uni


def fit_pwin(rows):
    usable = []
    for r in rows:
        if r["sc"] is None or r["osc"] is None:
            continue
        if r["rw"] == 1:
            w = 1
        elif r["orw"] == 1:
            w = 0
        else:
            continue
        usable.append((r["sc"] - r["osc"], w))
    a = b = 0.0
    for _ in range(60):
        ga = gb = haa = hab = hbb = 0.0
        for d, w in usable:
            p = 1 / (1 + math.exp(-(a + b * d)))
            ga += w - p
            gb += (w - p) * d
            haa += p * (1 - p)
            hab += p * (1 - p) * d
            hbb += p * (1 - p) * d * d
        det = haa * hbb - hab * hab
        if det <= 0:
            break
        da = (ga * hbb - gb * hab) / det
        db = (gb * haa - ga * hab) / det
        a += da
        b += db
        if abs(da) < 1e-10 and abs(db) < 1e-12:
            break
    return lambda d: 1 / (1 + math.exp(-(a + b * d))), a, b


def boot_mean_ci(cluster_vals, n_boot=800):
    """cluster_vals: {cluster: (sum, n)}。クラスタ(個体)ブートストラップの平均CI。"""
    items = list(cluster_vals.values())
    if not items:
        return None
    stats = []
    for _ in range(n_boot):
        s = n = 0.0
        for _ in range(len(items)):
            x, m = items[rng.randrange(len(items))]
            s += x
            n += m
        stats.append(s / n if n else 0.0)
    stats.sort()
    return stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)]


def main():
    meta, rows = load_panel()
    print("# 新規性プレミアムの減衰 — 3つの時計\n")
    print("## 0. 内挿と宇宙の構築")
    interp, rng_ok = build_interp(rows)
    uni = episode_universe(meta, rows, interp, rng_ok)

    # ---- 1. 採用曲線(全既知subのdateSubmitted、単位=個体) ----
    print("""
## 1. 採用曲線 — 週次の新規参入個体数(単位=distinct submissionId、dateSubmitted 既知分)
  ※decks.jsonl でアーキタイプ既知の3,359体のうち参入日既知の割合も開示。""")
    dated = [(s, m) for s, m in meta.items() if m.get("arch") in ARCHS and m.get("date")]
    known_arch = [s for s, m in meta.items() if m.get("arch") in ARCHS]
    print(f"  アーキ既知 {len(known_arch)} 体中、参入日既知 {len(dated)} 体 "
          f"({100*len(dated)/max(1,len(known_arch)):.0f}%)")
    byw = defaultdict(Counter)
    for s, m in dated:
        byw[week(m["date"])][m["arch"]] += 1
    wks = sorted(byw)
    print("  週      " + "".join(f"{x[:6]:>8}" for x in ARCHS) + "     計")
    cum = Counter()
    for w in wks:
        tot = sum(byw[w].values())
        cum.update(byw[w])
        print(f"  {wk_label(w)}" + "".join(f"{byw[w].get(x,0):>8}" for x in ARCHS)
              + f"{tot:>7}")
    print("  累計   " + "".join(f"{cum.get(x,0):>8}" for x in ARCHS))

    # ---- 2. 同一対面ペアの週次勝率(交絡=マッチアップ構造を対で固定) ----
    print("""
## 2. 同一対面ペアの週次勝率(単位=遭遇。distinct個体数併記、N<8は「不足」)
  「フィールドが新顔に慣れる」なら、対 tarountula の勝率は週とともに上がるはず。
  対照ペア(古参同士)も並べ、時計そのものの歪みと見分ける。帯は混在(開示)。""")
    pairs = [("alakazam", "tarountula"), ("grimmsnarl", "tarountula"),
             ("crustle", "tarountula"), ("archaludon", "tarountula"),
             ("alakazam", "grimmsnarl"), ("alakazam", "crustle"),
             ("grimmsnarl", "crustle")]
    for x, y in pairs:
        cells = defaultdict(lambda: [0, 0, set(), set()])
        for ep, (t, a0, a1, win, s0, s1, *_rest) in uni.items():
            if {a0, a1} != {x, y}:
                continue
            w = week(t)
            xa_side = 0 if a0 == x else 1
            xwin = (win == xa_side)
            cells[w][0 if xwin else 1] += 1
            cells[w][2].add(s0 if xa_side == 0 else s1)
            cells[w][3].add(s1 if xa_side == 0 else s0)
        line = []
        for w in sorted(cells):
            wn, ln_, sx, sy = cells[w]
            n = wn + ln_
            if n < 8:
                line.append(f"{wk_label(w)}:不足(N={n})")
                continue
            lo, hi = B.wilson(wn, n)
            line.append(f"{wk_label(w)}:{100*wn/n:.0f}%[{lo:.0f},{hi:.0f}]"
                        f"(N={n},{len(sx)}/{len(sy)}体)")
        print(f"  {x} が {y} に勝つ率:")
        print("    " + "  ".join(line) if line else "    データ無し")

    # ---- 3. レーティング調整済み残差の週次系列(追跡個体、相手アーキ不要) ----
    print("""
## 3. レート期待からの超過成績(週次、追跡個体、個体クラスタbootstrap CI)
  residual = win − P(win|Δrating)。P は全追跡視点へのロジスティックfit。
  Elo収束(昇り坂は勝率>50%が機械的に出る)を物差しごと除いた成績。
  **シェアが増えるほど超過成績が0へ落ちる**なら SUMI 曲線のレート調整版が成立。""")
    pwin, a_fit, b_fit = fit_pwin(rows)
    print(f"  fit: a={a_fit:+.4f} b={b_fit:.6f}")
    by_aw = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))   # arch -> wk -> {sub:(sum,n)}
    res_aw = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        m = meta.get(r["sub"]) or {}
        arch = m.get("arch")
        if arch not in ARCHS or m.get("ours"):
            continue
        if r["sc"] is None or r["osc"] is None:
            continue
        if r["rw"] == 1:
            w = 1
        elif r["orw"] == 1:
            w = 0
        else:
            continue
        res = w - pwin(r["sc"] - r["osc"])
        wk = week(r["t"])
        cell = res_aw[arch][wk]
        s_, n_ = cell.get(r["sub"], (0.0, 0))
        cell[r["sub"]] = (s_ + res, n_ + 1)
    for arch in ["grimmsnarl", "alakazam", "tarountula"]:
        wks2 = sorted(res_aw[arch])
        line = []
        for wk in wks2:
            cell = res_aw[arch][wk]
            n = sum(v[1] for v in cell.values())
            if n < 60:
                line.append(f"{wk_label(wk)}:不足(N={n})")
                continue
            m_ = 100 * sum(v[0] for v in cell.values()) / n
            ci = boot_mean_ci(cell)
            line.append(f"{wk_label(wk)}:{m_:+.1f}pt[{100*ci[0]:+.1f},{100*ci[1]:+.1f}]"
                        f"(N={n},{len(cell)}体)")
        print(f"  {arch}: " + "  ".join(line))
    # grimmsnarl 現職のみ(参入7/14以前)
    print("  --- grimmsnarl 現職(参入7/14以前の個体)のみ ---")
    cutoff = datetime(2026, 7, 14, tzinfo=timezone.utc).timestamp()
    line = []
    for wk in sorted(res_aw["grimmsnarl"]):
        cell = {s: v for s, v in res_aw["grimmsnarl"][wk].items()
                if (meta.get(s) or {}).get("date") and meta[s]["date"] < cutoff}
        n = sum(v[1] for v in cell.values())
        if n < 40:
            line.append(f"{wk_label(wk)}:不足(N={n})")
            continue
        m_ = 100 * sum(v[0] for v in cell.values()) / n
        ci = boot_mean_ci(cell)
        line.append(f"{wk_label(wk)}:{m_:+.1f}pt[{100*ci[0]:+.1f},{100*ci[1]:+.1f}]"
                    f"(N={n},{len(cell)}体)")
    print("  " + "  ".join(line))

    # ---- 4. デッキ標準化率(模倣可能性の直接観測。単位=distinct提出) ----
    print("""
## 4. デッキ標準化率 — 同一60枚の完全一致率(単位=distinct submissionId)
  「模倣可能性が高い」の最も直接的な痕跡 = 全員が同じ60枚を持っている。""")
    by_sub_deck = {}
    for line_ in open(LS / "decks.jsonl"):
        r = json.loads(line_)
        for s in r["s"]:
            if s["sub"] is not None and s["sub"] not in by_sub_deck:
                by_sub_deck[s["sub"]] = tuple(sorted(s["d"]))
    per = defaultdict(Counter)
    for sub, dk in by_sub_deck.items():
        arch = (meta.get(sub) or {}).get("arch")
        if arch in ARCHS:
            per[arch][dk] += 1
    print(f"  {'arch':<12}{'個体':>6}{'相異なる60枚':>12}{'最頻一致率':>11}{'上位3構成の和':>13}")
    for arch in sorted(per, key=lambda a: -sum(per[a].values())):
        ctr = per[arch]
        n = sum(ctr.values())
        top = ctr.most_common(3)
        t1 = top[0][1] / n
        t3 = sum(c for _, c in top) / n
        print(f"  {arch:<12}{n:>6}{len(ctr):>12}{100*t1:>10.1f}%{100*t3:>12.1f}%")

    # ---- 5. tarountula 深掘り(全121個体を追跡済み) ----
    print("""
## 5. tarountula 深掘り — 参入からの日数別の超過成績(個体クラスタ、全121個体)
  「新顔ボーナス」が個体の加齢で減衰するか。Elo収束は物差しで除いてある。""")
    buckets = defaultdict(dict)      # 日数バケット -> {sub: (sum,n)}
    for r in rows:
        m = meta.get(r["sub"]) or {}
        if m.get("arch") != "tarountula" or not m.get("date"):
            continue
        if r["sc"] is None or r["osc"] is None:
            continue
        if r["rw"] == 1:
            w = 1
        elif r["orw"] == 1:
            w = 0
        else:
            continue
        age = (r["t"] - m["date"]) / DAY
        bk = ("0-2日" if age < 3 else "3-6日" if age < 7 else
              "7-13日" if age < 14 else "14日+")
        res = w - pwin(r["sc"] - r["osc"])
        s_, n_ = buckets[bk].get(r["sub"], (0.0, 0))
        buckets[bk][r["sub"]] = (s_ + res, n_ + 1)
    for bk in ["0-2日", "3-6日", "7-13日", "14日+"]:
        cell = buckets.get(bk, {})
        n = sum(v[1] for v in cell.values())
        if n < 40:
            print(f"  {bk:<7} 不足(N={n})")
            continue
        m_ = 100 * sum(v[0] for v in cell.values()) / n
        ci = boot_mean_ci(cell)
        print(f"  {bk:<7} 残差 {m_:+5.1f}pt [{100*ci[0]:+.1f},{100*ci[1]:+.1f}]"
              f"  (N={n}, {len(cell)}体)")


if __name__ == "__main__":
    main()

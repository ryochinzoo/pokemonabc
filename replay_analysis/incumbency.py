#!/usr/bin/env python3
"""現職衰退分析 — 「シェアが増えると誰が沈むのか」を個体識別×レーティングで分離する。

検証対象(記事主砲候補A): メタは強さでなく模倣可能性で決まる。
  - Jake(8位): Grimmsnarl はデータが多いから作りやすく、それが更に Grimmsnarl を増やす
  - SUMI: シェア 17→51% と増えるほど非ミラー勝率が 50.3% に収束(rating無しの遭遇集計)

**SUMI が原理的に区別できない3仮説**を、我々のパネル(時刻×submissionId×rating)で分離する:
  H1 対抗適応: フィールドが対策を増やし、**現職(早期参入の個体)のレーティングが下がる**
  H2 構成効果: 後発参入者が弱いだけ。**現職は下がらず、後発コホートの均衡Rが低い**
  H3 機械効果: Elo収束の産物。新規subは昇り坂で勝率>50%、飽和で成熟し50%へ。
              **現職も後発も均衡Rは不変**なら、SUMIの飽和曲線はこれだけで説明される

事前固定の反証条件: 現職の均衡Rトレンドが全アーキタイプで0近傍(CIが0を跨ぐ)かつ
コホート差も無ければ、「シェア増加が勝率を押し下げる」という因果の芯は**潰れた**と報告する。

単位: 「個体」= distinct submissionId(提出は凍結コードなので個体の強さは不変)。
     「チーム」= teamId は再提出で中身が変わるため個体としては使わない(開示のみ)。

使い方: python3 replay_analysis/incumbency.py [帯下限 800] [帯上限 1100]
入力:   ladder_scout/panel.jsonl + submeta.json(meta_timeline.py panel が生成)
"""
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import band_meta_census as B  # noqa: E402

HERE = Path(__file__).resolve().parent
LS = HERE / "ladder_scout"
T0 = datetime(2026, 6, 16, tzinfo=timezone.utc).timestamp()   # 最古の提出日の週初
DAY = 86400.0
ARCHS = ["grimmsnarl", "alakazam", "crustle", "lucario", "archaludon",
         "tarountula", "starmie", "dragapult", "garchomp"]
CONV_SKIP = 30          # 収束前として捨てる冒頭試合数
MIN_EQ_GAMES = 40       # 均衡レーティングを出す最少試合数
MIN_SLOPE_GAMES = 80    # 個体内トレンドを出す最少試合数
MIN_SLOPE_SPAN = 10     # 同、最少日数
rng = random.Random(20260803)


def day(t):
    return (t - T0) / DAY


def week(t):
    return int(day(t) // 7)


def wk_label(w):
    d = datetime.fromtimestamp(T0 + w * 7 * DAY, tz=timezone.utc)
    return d.strftime("%m/%d")


def load():
    meta = json.loads((LS / "submeta.json").read_text())
    meta = {int(k): v for k, v in meta.items()}
    rows = [json.loads(l) for l in open(LS / "panel.jsonl")]
    by_sub = defaultdict(list)
    for r in rows:
        by_sub[r["sub"]].append(r)
    for v in by_sub.values():
        v.sort(key=lambda r: r["t"])
    return meta, rows, by_sub


def ols(xy):
    n = len(xy)
    sx = sum(x for x, y in xy)
    sy = sum(y for x, y in xy)
    sxx = sum(x * x for x, y in xy)
    sxy = sum(x * y for x, y in xy)
    d = n * sxx - sx * sx
    if d == 0:
        return None
    return (n * sxy - sx * sy) / d


def boot_ci(vals, weights=None, f=None, n_boot=1000):
    """個体レベルのブートストラップ percentile CI。f は再標本への統計量。"""
    if f is None:
        if weights:
            def f(idx):
                wsum = sum(weights[i] for i in idx)
                return sum(vals[i] * weights[i] for i in idx) / wsum if wsum else 0.0
        else:
            def f(idx):
                return sum(vals[i] for i in idx) / len(idx)
    stats = []
    n = len(vals)
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(f(idx))
    stats.sort()
    return stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)]


def main(lo=800, hi=1100):
    meta, rows, by_sub = load()
    tracked = sorted(s for s, m in meta.items()
                     if m.get("tracked") and not m.get("ours") and m.get("arch") in ARCHS)
    print(f"# 現職衰退分析  追跡個体 {len(tracked)}(我々除外)  視点行 {len(rows)}")
    per_arch = defaultdict(list)
    for s in tracked:
        per_arch[meta[s]["arch"]].append(s)
    print("  個体数: " + ", ".join(f"{a}={len(per_arch[a])}" for a in ARCHS if per_arch[a]))
    nodate = [s for s in tracked if not meta[s].get("date")]
    if nodate:
        print(f"  参入日未知で以後の分析から除外: {len(nodate)} 体(開示)")
        tracked = [s for s in tracked if meta[s].get("date")]

    # ---- A. 経験的 P(win|Δrating) 曲線(残差の物差し) ----
    print("\n## A. P(win | Δrating)(全追跡視点、両者スコア既知・決着のみ)")
    bins = defaultdict(lambda: [0, 0])
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
        d = r["sc"] - r["osc"]
        usable.append((r, d, w))
        if abs(d) <= 400:
            bins[int(d // 50) * 50][w == 0] += 1
    # ロジスティック1変数フィット(切片0を仮定しない): w ~ 1/(1+exp(-(a+b*Δ)))
    a = b = 0.0
    for _ in range(60):
        ga = gb = haa = hab = hbb = 0.0
        for _, d, w in usable:
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
    print(f"  ロジスティック fit: P = 1/(1+exp(-({a:+.4f} + {b:.6f}·Δ)))  "
          f"(Δ=76.6/b 相当のEloスケール s={math.log(10)/b/4:.0f}…10^(Δ/(4s))近似)"
          if b else "  fit失敗")
    print("  Δビン(50pt):  ", end="")
    for d0 in sorted(bins):
        w, l = bins[d0]
        print(f"[{d0:+d}..{d0+49:+d}] {100*w/(w+l):.0f}%({w+l})", end="  ")
    print()

    def pwin(d):
        return 1 / (1 + math.exp(-(a + b * d)))

    # ---- B. コホート(参入週 → 均衡レーティング)= 構成効果の検査 ----
    print(f"""
## B. コホート分析 — 後発参入の個体は弱いか(単位=個体)
  均衡R = その個体の試合 {CONV_SKIP+1} 戦目以降の initialScore 中央値({MIN_EQ_GAMES}戦未満は除外・開示)。
  『後発コホートの均衡Rが低い』= 構成効果(H2)の証拠。""")
    eq_of = {}
    excluded = defaultdict(int)
    for s in tracked:
        g = [r["sc"] for r in by_sub[s][CONV_SKIP:] if r["sc"] is not None]
        if len(by_sub[s]) < MIN_EQ_GAMES:
            excluded[meta[s]["arch"]] += 1
            continue
        g.sort()
        eq_of[s] = g[len(g) // 2]
    print(f"  {'arch':<12}{'個体':>5}{'除外':>5}{'  参入日と均衡Rの回帰勾配(pt/週)と95%CI(個体bootstrap)'}")
    for arch in ARCHS:
        subs = [s for s in per_arch[arch] if s in eq_of]
        if len(subs) < 5:
            print(f"  {arch:<12}{len(subs):>5}{excluded[arch]:>5}   個体数不足で勾配は出さない")
            continue
        xy = [(day(meta[s]["date"]) / 7, eq_of[s]) for s in subs]
        sl = ols(xy)
        idx_pairs = list(range(len(xy)))

        def slope_stat(idx, xy=xy):
            pts = [xy[i] for i in idx]
            s2 = ols(pts)
            return s2 if s2 is not None else 0.0
        lo_ci, hi_ci = boot_ci([0] * len(xy), f=lambda idx: slope_stat(idx), n_boot=600)
        print(f"  {arch:<12}{len(subs):>5}{excluded[arch]:>5}   {sl:+7.1f} pt/週  "
              f"[{lo_ci:+.1f}, {hi_ci:+.1f}]"
              + ("  **後発ほど低い**" if hi_ci < 0 else
                 ("  **後発ほど高い**" if lo_ci > 0 else "  (0を跨ぐ)")))
        # コホート表(2週刻み)
        coh = defaultdict(list)
        for s in subs:
            coh[week(meta[s]["date"]) // 2 * 2].append(eq_of[s])
        cells = []
        for w0 in sorted(coh):
            v = sorted(coh[w0])
            cells.append(f"{wk_label(w0)}週~: n={len(v)} 中央{v[len(v)//2]:.0f}")
        print(f"  {'':<12}     {'  '.join(cells)}")

    # ---- C. 現職の個体内トレンド = 対抗適応(H1)の検査 ----
    print(f"""
## C. 現職の個体内レーティングトレンド(単位=個体、{MIN_SLOPE_GAMES}戦以上かつ{MIN_SLOPE_SPAN}日以上)
  提出は凍結コード。個体の強さは不変なので、収束後({CONV_SKIP}戦目以降)の
  レーティング勾配が負 = **環境がその個体に不利に動いた**(対抗適応 or フィールド全体の強化)。
  アーキタイプ間の差で全体ドリフトを消す(diff-in-diff)。""")
    slope_of = {}
    for s in tracked:
        g = [(day(r["t"]), r["sc"]) for r in by_sub[s][CONV_SKIP:] if r["sc"] is not None]
        if len(g) < MIN_SLOPE_GAMES - CONV_SKIP:
            continue
        if g[-1][0] - g[0][0] < MIN_SLOPE_SPAN:
            continue
        sl = ols([(x / 7, y) for x, y in g])
        if sl is not None:
            slope_of[s] = (sl, len(g), g[-1][0] - g[0][0])
    print(f"  {'arch':<12}{'個体':>5}{'平均勾配':>10}{'95%CI(個体bootstrap)':>22}{'  観測窓の中央値'}")
    arch_slopes = {}
    for arch in ARCHS:
        ss = [s for s in per_arch[arch] if s in slope_of]
        if len(ss) < 4:
            print(f"  {arch:<12}{len(ss):>5}   個体数不足(開示: 候補{len(per_arch[arch])}体)")
            continue
        vals = [slope_of[s][0] for s in ss]
        m = sum(vals) / len(vals)
        lo_ci, hi_ci = boot_ci(vals)
        spans = sorted(slope_of[s][2] for s in ss)
        arch_slopes[arch] = (m, lo_ci, hi_ci, len(ss))
        print(f"  {arch:<12}{len(ss):>5}{m:+9.1f}pt/週   [{lo_ci:+6.1f}, {hi_ci:+6.1f}]"
              f"      {spans[len(spans)//2]:.0f}日"
              + ("  **有意に下降**" if hi_ci < 0 else ("  **有意に上昇**" if lo_ci > 0 else "")))

    # ---- C2. 緩い閾値(50戦・7日)+ 下降個体率 ----
    print("""
### C2. 緩い閾値版(50戦以上・7日以上)— 長寿個体への選択偏りを緩める
  上の表は長寿個体に限られる=斥候で選んだ高スコア個体に偏りうる。""")
    slope2 = {}
    for s in tracked:
        if len(by_sub[s]) < 50:
            continue
        g = [(day(r["t"]), r["sc"]) for r in by_sub[s][CONV_SKIP:] if r["sc"] is not None]
        if len(g) < 20 or (g[-1][0] - g[0][0]) < 7:
            continue
        sl = ols([(x / 7, y) for x, y in g])
        if sl is not None:
            slope2[s] = sl
    for arch in ARCHS:
        ss = [s for s in per_arch[arch] if s in slope2]
        if len(ss) < 4:
            continue
        vals = [slope2[s] for s in ss]
        m = sum(vals) / len(vals)
        lo_ci, hi_ci = boot_ci(vals)
        neg = sum(1 for v in vals if v < 0)
        print(f"  {arch:<12} 個体{len(ss):>4}  平均{m:+7.1f}pt/週 [{lo_ci:+6.1f},{hi_ci:+6.1f}]"
              f"  下降個体 {neg}/{len(ss)}"
              + ("  **有意に下降**" if hi_ci < 0 else ("  **有意に上昇**" if lo_ci > 0 else "")))

    # ---- C3. 機構チェック — 下降は「自アーキ特異」か「全体の潮流」か ----
    print("""
### C3. 機構チェック — ゼロサム・レーティングでは強い新規参入が現職全員から点を奪う
  観測プールの週次スコア分布と、新規参入の流量(既知の全submissionIdのdateSubmitted)。
  全アーキが同時に沈むなら、それは対抗適応ではなく**プールの深化**。""")
    pool = defaultdict(list)
    for r in rows:
        w = week(r["t"])
        if r["sc"] is not None:
            pool[w].append(r["sc"])
        if r["osc"] is not None:
            pool[w].append(r["osc"])
    entries = defaultdict(int)
    for s, m2 in meta.items():
        if m2.get("date"):
            entries[week(m2["date"])] += 1
    print("  週        観測側n   スコア平均   中央   新規参入(全既知sub)")
    for w in sorted(pool):
        v = sorted(pool[w])
        if len(v) < 200:
            continue
        print(f"  {wk_label(w)}  {len(v):>8}   {sum(v)/len(v):>8.0f}  {v[len(v)//2]:>6.0f}"
              f"   {entries.get(w, 0):>6}")

    # ---- D. 週次の帯内シェア(相手ドロー推定)と現職成績の重ね合わせ ----
    print(f"""
## D. 週次シェア(相手ドロー推定、追跡側スコア {lo}-{hi-1} のときの相手側)× 現職の週次成績
  シェアの単位=遭遇(相手ドロー)。distinct個体数も併記。相手アーキ未知率は週ごとに開示。""")
    share_wk = defaultdict(lambda: defaultdict(int))
    share_subs = defaultdict(lambda: defaultdict(set))
    unk_wk = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["sc"] is None or not (lo <= r["sc"] < hi):
            continue
        w = week(r["t"])
        oa = (meta.get(r["osub"]) or {}).get("arch")
        unk_wk[w][1] += 1
        if not oa or oa == "other":
            unk_wk[w][0] += 1
            continue
        share_wk[w][oa] += 1
        share_subs[w][oa].add(r["osub"])
    wks = sorted(w for w in share_wk if unk_wk[w][1] >= 80)
    hdr = "  週      n(既知)  未知率  " + "".join(f"{x[:6]:>8}" for x in ARCHS)
    print(hdr)
    for w in wks:
        tot = sum(share_wk[w].values())
        u, t_all = unk_wk[w]
        line = f"  {wk_label(w)}  {tot:>7}  {100*u/t_all:5.1f}%  "
        for x in ARCHS:
            line += f"{100*share_wk[w].get(x,0)/tot:7.1f}%"
        print(line)
    print("  (distinct個体: 最終週の例 " + ", ".join(
        f"{x}={len(share_subs[wks[-1]][x])}" for x in ARCHS if share_subs[wks[-1]][x]) + ")"
        if wks else "  標本不足")

    # ---- E. 現職 vs 後発の週次レーティング中央値(アーキ別) ----
    print("""
## E. 現職(参入が最初の1/3)vs 後発(最後の1/3)の週次レーティング中央値
  個体固定で環境変化だけを拾う。現職線が右肩下がり+シェア増と同期なら H1。""")
    for arch in ARCHS:
        subs = [s for s in per_arch[arch] if meta[s].get("date")]
        if len(subs) < 9:
            print(f"  {arch:<12} 個体数不足({len(subs)})")
            continue
        subs.sort(key=lambda s: meta[s]["date"])
        third = len(subs) // 3
        inc, late = set(subs[:third]), set(subs[-third:])
        inc_d = (wk_label(week(meta[subs[0]]['date'])),
                 wk_label(week(meta[subs[third-1]]['date'])))
        late_d = (wk_label(week(meta[subs[-third]]['date'])),
                  wk_label(week(meta[subs[-1]]['date'])))
        series = {"現職": defaultdict(list), "後発": defaultdict(list)}
        for s in subs:
            grp = "現職" if s in inc else ("後発" if s in late else None)
            if not grp:
                continue
            for i, r in enumerate(by_sub[s]):
                if i < CONV_SKIP or r["sc"] is None:
                    continue
                series[grp][week(r["t"])].append(r["sc"])
        line1 = []
        for w in sorted(set(series["現職"]) | set(series["後発"])):
            i_v = sorted(series["現職"].get(w, []))
            l_v = sorted(series["後発"].get(w, []))
            iv = f"{i_v[len(i_v)//2]:.0f}" if len(i_v) >= 15 else "—"
            lv = f"{l_v[len(l_v)//2]:.0f}" if len(l_v) >= 15 else "—"
            line1.append(f"{wk_label(w)}:{iv}/{lv}")
        print(f"  {arch:<12} 現職{len(inc)}体(参入{inc_d[0]}~{inc_d[1]}) "
              f"後発{len(late)}体(参入{late_d[0]}~{late_d[1]})  [週:現職R/後発R、n<15は—]")
        print(f"  {'':<12} " + "  ".join(line1))

    # ---- E2. 現職の相手レーティング分布(マッチメイキング交絡の開示) ----
    print("""
### E2. 現職の相手レーティング中央値の週次推移(マッチメイキング交絡の開示)
  運営仕様(discussion/726690): 相手選択=自スコア中心のガウス窓 → 相手Rは自Rを追従する。
  「勝率低下=相手が強くなっただけ」の切り分けは生の勝率では不可能で、
  残差分析(novelty_decay.py §3)が Δrating を条件付けて処理している。ここでは
  現職の (自R, 相手R, 相手R−自R) を開示し、相手が系統的に強い方向へズレたかを見る。""")
    for arch in ["grimmsnarl", "alakazam", "tarountula"]:
        subs = [s for s in per_arch[arch] if meta[s].get("date")]
        if len(subs) < 9:
            continue
        subs.sort(key=lambda s: meta[s]["date"])
        inc = set(subs[: len(subs) // 3])
        wkrows = defaultdict(lambda: ([], [], []))
        for s in inc:
            for i, r in enumerate(by_sub[s]):
                if i < CONV_SKIP or r["sc"] is None or r["osc"] is None:
                    continue
                w = week(r["t"])
                wkrows[w][0].append(r["sc"])
                wkrows[w][1].append(r["osc"])
                wkrows[w][2].append(r["osc"] - r["sc"])
        cells = []
        for w in sorted(wkrows):
            a_, b_, d_ = (sorted(x) for x in wkrows[w])
            if len(a_) < 15:
                cells.append(f"{wk_label(w)}:n={len(a_)}不足")
                continue
            cells.append(f"{wk_label(w)}: 自{a_[len(a_)//2]:.0f} 相手{b_[len(b_)//2]:.0f} "
                         f"差{d_[len(d_)//2]:+.0f} (n={len(a_)})")
        print(f"  {arch:<12}現職{len(inc)}体: " + "  ".join(cells))

    # ---- F. LOTO φ(操縦者の均質性)— パネル版 ----
    print(f"""
## F. 操縦者の均質性 φ(パネル版 LOTO、同帯{lo}-{hi-1}・非ミラー・両アーキ既知)
  φ≈1: 同アーキの個体は交換可能(モデル= deck が結果を決める=模倣が完全)。
  φ≫1: 同じデッキ看板でも個体差が大きい(操縦者が結果を左右)。""")
    epis = {}
    for r in rows:
        if r["ep"] in epis:
            continue
        oa = (meta.get(r["osub"]) or {}).get("arch")
        ma = (meta.get(r["sub"]) or {}).get("arch")
        if not ma or not oa or ma == "other" or oa == "other" or ma == oa:
            continue
        if r["sc"] is None or r["osc"] is None:
            continue
        if not (lo <= r["sc"] < hi and lo <= r["osc"] < hi):
            continue
        if B.band(r["sc"]) != B.band(r["osc"]):
            continue
        if r["rw"] == 1:
            win = 0
        elif r["orw"] == 1:
            win = 1
        else:
            continue
        epis[r["ep"]] = (r["sub"], ma, r["osub"], oa, win)   # win: 0=sub勝ち,1=osub勝ち
    cell = defaultdict(lambda: [0, 0])
    team_cell = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for sub, ma, osub, oa, win in epis.values():
        cell[(ma, oa)][win] += 1
        cell[(oa, ma)][1 - win] += 1
        team_cell[(sub, ma)][oa][win] += 1
        team_cell[(osub, oa)][ma][1 - win] += 1
    print(f"  {'arch':<12}{'個体':>5}{'総戦':>7}{'平均残差':>9}{'95%CI':>17}{'φ':>7}"
          f"{'Brier':>7}{'vs50':>5}{'  z<-2 / z>+2 の個体数'}")
    for arch in ARCHS:
        rs = []
        for (sub, ma), cells in team_cell.items():
            if ma != arch:
                continue
            n_t = sum(w + l for w, l in cells.values())
            if n_t < 15:
                continue
            E = var = brier = 0.0
            W = n_used = 0
            for oa, (w, l) in cells.items():
                cw, cl = cell[(ma, oa)]
                rw_, rl_ = cw - w, cl - l
                if rw_ + rl_ < 10:
                    continue
                p = rw_ / (rw_ + rl_)
                E += (w + l) * p
                var += (w + l) * p * (1 - p)
                brier += w * (1 - p) ** 2 + l * p * p
                W += w
                n_used += w + l
            if n_used >= 15 and var > 0:
                rs.append((W - E, n_used, var, brier))
        if len(rs) < 3:
            print(f"  {arch:<12}{len(rs):>5}   個体数不足")
            continue
        sumWE = sum(x for x, n, v, br in rs)
        sumN = sum(n for x, n, v, br in rs)
        sumV = sum(v for x, n, v, br in rs)
        bm = sum(br for x, n, v, br in rs) / sumN
        phi = sum(x * x / v for x, n, v, br in rs) / len(rs)
        z_lo = sum(1 for x, n, v, br in rs if x / math.sqrt(v) < -2)
        z_hi = sum(1 for x, n, v, br in rs if x / math.sqrt(v) > 2)
        m = 100 * sumWE / sumN
        se = 100 * math.sqrt(sumV) / sumN
        print(f"  {arch:<12}{len(rs):>5}{sumN:>7}{m:+8.1f}pt  [{m-1.96*se:+6.1f},{m+1.96*se:+6.1f}]"
              f"{phi:7.2f}{bm:7.3f}{'勝' if bm < 0.25 else '負':>4}   {z_lo} / {z_hi}")
    print("  ※Brier: 零情報(常に50%)=0.250。下回れば held-out 個体に対し情報あり(赤チームD要件)。")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 800,
         int(sys.argv[2]) if len(sys.argv) > 2 else 1100)

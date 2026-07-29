#!/usr/bin/env python3
"""レポート用図表の生成(標準ライブラリのみ、SVG出力)。

データはdocs/memo/data.mdの確定値を転記(出典コメント付き)。数値を更新したら再実行。
    python3 docs/memo/figures/make_figures.py
"""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 図1: デッキ頑健性マトリクス (data.md 2026-07-20 EXP1全8対面プール、150戦/対面、
#      両側v2.1c操縦。mirror行はrank9=対現行直接対決の対称値、aggro=直接対決値)
# ---------------------------------------------------------------------------
MATCHUPS = ["Alakazam", "Archaludon", "Grimmsnarl", "Lucario", "Kangaskhan\n+Crustle",
            "Garchomp", "TR Mewtwo", "Crustle wall"]
ROWS = [
    ("rank9 (Dusknoir line)", [60.0, 67.0, 78.0, 68.0, 50.0, 67.0, 83.0, 76.7]),
    ("starmie-aggro (D21)",   [62.7, 85.3, 94.0, 91.3, 80.0, 84.0, 93.3, 94.0]),
]


def color(v: float) -> str:
    """50%=白 → 95%=濃緑 / <50%=赤系。"""
    if v >= 50:
        t = min(1.0, (v - 50) / 45)
        r, g, b = int(255 - 155 * t), int(255 - 55 * t), int(255 - 155 * t)
    else:
        t = min(1.0, (50 - v) / 30)
        r, g, b = 255, int(255 - 120 * t), int(255 - 120 * t)
    return f"rgb({r},{g},{b})"


def fig_deck_matrix():
    cw, ch, lx, ty = 92, 46, 190, 70
    w = lx + cw * len(MATCHUPS) + 20
    h = ty + ch * len(ROWS) + 60
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">']
    s.append(f'<text x="{lx}" y="24" font-size="15" font-weight="bold">'
             f'Deck robustness matrix — same pilot (v2.1c) both sides, N=150/cell</text>')
    s.append(f'<text x="{lx}" y="42" font-size="11" fill="#555">'
             f'Removing the 6-slot Dusknoir combo line improves every matchup '
             f'(sign-consistent, weighted +15.7pt) — data.md 2026-07-20</text>')
    for j, m in enumerate(MATCHUPS):
        for k, line in enumerate(m.split("\n")):
            s.append(f'<text x="{lx + j * cw + cw / 2}" y="{ty - 18 + k * 12}" '
                     f'text-anchor="middle" font-size="11">{line}</text>')
    for i, (name, vals) in enumerate(ROWS):
        y = ty + i * ch
        s.append(f'<text x="{lx - 8}" y="{y + ch / 2 + 4}" text-anchor="end">{name}</text>')
        for j, v in enumerate(vals):
            x = lx + j * cw
            s.append(f'<rect x="{x}" y="{y}" width="{cw - 3}" height="{ch - 3}" '
                     f'fill="{color(v)}" stroke="#999"/>')
            s.append(f'<text x="{x + cw / 2 - 1}" y="{y + ch / 2 + 4}" text-anchor="middle" '
                     f'font-weight="bold">{v:.0f}%</text>')
    dy = ty + len(ROWS) * ch
    diffs = [b - a for a, b in zip(ROWS[0][1], ROWS[1][1])]
    s.append(f'<text x="{lx - 8}" y="{dy + 24}" text-anchor="end" fill="#555">Δ</text>')
    for j, d in enumerate(diffs):
        s.append(f'<text x="{lx + j * cw + cw / 2}" y="{dy + 24}" text-anchor="middle" '
                 f'fill="{"#1a7f1a" if d > 0 else "#b22"}">{d:+.0f}</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_deck_matrix.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図2: 提出レーティング時系列 (data.md 提出履歴表。値は観測時点のpublicScore)
# ---------------------------------------------------------------------------
SUBS = [
    ("06-28", 343.9, "random baseline"),
    ("07-08", 507.3, "v1 greedy+eval"),
    ("07-15", 520.1, "v2 +search"),
    ("07-17", 650.2, "v2.1 ×Kangaskhan"),
    ("07-18", 625.7, "v2.1b ×Starmie r9"),
    ("07-19", 718.6, "v2.1c NULL-guard"),
    ("07-19", 487.5, "v3 calibration"),
    ("07-19", 728.7, "v2.1c ×starmie-aggro"),
    ("07-21", 742.5, "v2.2+EXP8"),
]


def fig_rating_timeline():
    w, h, lx, by = 730, 330, 60, 270
    ymin, ymax = 300, 800
    def yy(v):
        return by - (v - ymin) / (ymax - ymin) * (by - 50)
    xs = [lx + 30 + i * 68 for i in range(len(SUBS))]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="11">']
    s.append('<text x="60" y="24" font-size="15" font-weight="bold">'
             'Kaggle rating by submission (public score at observation)</text>')
    for g in range(300, 801, 100):
        s.append(f'<line x1="{lx}" y1="{yy(g)}" x2="{w - 15}" y2="{yy(g)}" '
                 f'stroke="#ddd"/><text x="{lx - 6}" y="{yy(g) + 4}" '
                 f'text-anchor="end" fill="#777">{g}</text>')
    pts = []
    for (d, v, label), x in zip(SUBS, xs):
        pts.append((x, yy(v)))
        s.append(f'<text x="{x}" y="{by + 18}" text-anchor="middle" fill="#555">{d}</text>')
    main_line = [p for p, (d, v, l) in zip(pts, SUBS) if "calibration" not in l]
    path = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in main_line)
    s.append(f'<path d="{path}" fill="none" stroke="#2b6cb0" stroke-width="2"/>')
    for (d, v, label), (x, y) in zip(SUBS, pts):
        calib = "calibration" in label
        s.append(f'<circle cx="{x}" cy="{y}" r="5" '
                 f'fill="{"#e2a400" if calib else "#2b6cb0"}"/>')
        anchor = "middle"
        dy = -10 if not calib else 18
        s.append(f'<text x="{x}" y="{y + dy}" text-anchor="{anchor}" font-size="10">'
                 f'{v:.0f}</text>')
        s.append(f'<text x="{x}" y="{y + dy - 11 if not calib else y + dy + 11}" '
                 f'text-anchor="middle" font-size="9" fill="#555">{label}</text>')
    s.append(f'<text x="{lx}" y="{h - 8}" font-size="10" fill="#777">'
             f'Yellow = deliberate calibration submission (v3 probe). '
             f'Same-agent LB variance is 150-400pt (host thread).</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_rating_timeline.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図3: 較正の前向き検証 (data.md 2026-07-22 T1検証, D33)
#   同じ実ラダー20戦(較正カバー対面)に対する2つの計器の予測と実測。
#   族内=自パイロットが相手デッキを操縦したゲージの含意 / 較正済み=族外エージェント。
#   実測ひげ=Wilson 95%CI。予測はD32 T1でリプレイ閲覧前に事前登録済み。
# ---------------------------------------------------------------------------
PROSP = [
    # (row label, n, intra-family %, calibrated pred %, ladder actual %, CI lo, CI hi)
    ("vs Lucario",            11, 85.3, 48.9, 45.5, 21.3, 72.0),
    ("vs Archaludon",          8, 82.0, 21.4, 25.0,  7.1, 59.1),
    ("Weighted composite",    20, 83.9, 37.0, 35.0, 18.1, 56.7),
]
C_INTRA, C_CALIB, C_ACT = "#999999", "#2b6cb0", "#1a1a1a"


def fig_prospective():
    w, lx, rx = 720, 170, 660
    row_h, ty = 64, 96
    h = ty + row_h * len(PROSP) + 56
    def xx(v):
        return lx + (v / 100.0) * (rx - lx)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">']
    s.append('<text x="24" y="24" font-size="15" font-weight="bold">'
             'Prospective test: two instruments, one ladder (same 20 games)</text>')
    s.append('<text x="24" y="42" font-size="11" fill="#555">'
             'Predictions pre-registered before viewing any replay (D32 T1). '
             'Sub 54858780, first 60 ladder games, calibrated-coverage slice n=20.</text>')
    s.append('<text x="24" y="57" font-size="11" fill="#555">'
             'In-family gauge (we pilot the opponent deck) missed by +49pt; '
             'calibrated out-of-family gauges missed by 2pt.</text>')
    # axis
    ay = ty + row_h * len(PROSP)
    for g in range(0, 101, 25):
        s.append(f'<line x1="{xx(g)}" y1="{ty - 14}" x2="{xx(g)}" y2="{ay}" stroke="#e5e5e5"/>')
        s.append(f'<text x="{xx(g)}" y="{ay + 16}" text-anchor="middle" fill="#777" '
                 f'font-size="10">{g}%</text>')
    s.append(f'<line x1="{xx(50)}" y1="{ty - 14}" x2="{xx(50)}" y2="{ay}" stroke="#ccc"/>')
    for i, (name, n, intra, calib, act, lo, hi) in enumerate(PROSP):
        y = ty + i * row_h + row_h // 2 - 8
        s.append(f'<text x="{lx - 10}" y="{y + 4}" text-anchor="end" '
                 f'{"font-weight=\"bold\"" if i == 2 else ""}>{name}</text>')
        s.append(f'<text x="{lx - 10}" y="{y + 17}" text-anchor="end" font-size="10" '
                 f'fill="#777">n={n}</text>')
        # CI whisker for actual
        s.append(f'<line x1="{xx(lo)}" y1="{y}" x2="{xx(hi)}" y2="{y}" '
                 f'stroke="{C_ACT}" stroke-width="1" opacity="0.45"/>')
        for cap in (lo, hi):
            s.append(f'<line x1="{xx(cap)}" y1="{y - 4}" x2="{xx(cap)}" y2="{y + 4}" '
                     f'stroke="{C_ACT}" stroke-width="1" opacity="0.45"/>')
        # intra-family implied (discredited instrument): open circle
        s.append(f'<circle cx="{xx(intra)}" cy="{y}" r="6" fill="white" '
                 f'stroke="{C_INTRA}" stroke-width="2"/>')
        # calibrated prediction: filled circle
        s.append(f'<circle cx="{xx(calib)}" cy="{y}" r="6" fill="{C_CALIB}" '
                 f'stroke="white" stroke-width="1.5"/>')
        # ladder actual: diamond
        d = 6
        s.append(f'<path d="M{xx(act)},{y - d} L{xx(act) + d},{y} L{xx(act)},{y + d} '
                 f'L{xx(act) - d},{y} Z" fill="{C_ACT}" stroke="white" stroke-width="1.5"/>')
        # gap annotation between calibrated and actual on composite row
        if i == 2:
            s.append(f'<text x="{xx(intra)}" y="{y - 14}" text-anchor="middle" font-size="10" '
                     f'fill="#777">in-family implied {intra:.0f}%</text>')
            s.append(f'<text x="{xx(calib) - 4}" y="{y - 14}" text-anchor="end" font-size="10" '
                     f'fill="{C_CALIB}">predicted {calib:.0f}%</text>')
            s.append(f'<text x="{xx(act) + 2}" y="{y + 26}" text-anchor="middle" font-size="10" '
                     f'fill="{C_ACT}">actual {act:.0f}%</text>')
    # legend (identity also carried by direct labels above)
    ly = ay + 34
    s.append(f'<circle cx="30" cy="{ly}" r="6" fill="white" stroke="{C_INTRA}" stroke-width="2"/>')
    s.append(f'<text x="42" y="{ly + 4}" font-size="11" fill="#333">in-family gauge (self-piloted opponent)</text>')
    s.append(f'<circle cx="286" cy="{ly}" r="6" fill="{C_CALIB}"/>')
    s.append(f'<text x="298" y="{ly + 4}" font-size="11" fill="#333">calibrated gauge (pre-registered)</text>')
    s.append(f'<path d="M516,{ly - 6} L522,{ly} L516,{ly + 6} L510,{ly} Z" fill="{C_ACT}"/>')
    s.append(f'<text x="528" y="{ly + 4}" font-size="11" fill="#333">ladder actual (95% CI)</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_prospective.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図4: 較正ギャップ (data.md 2026-07-21 ★較正の一般法則 / D27)
#   同一エージェント(v2.2, 2026-07-21)の同一対面を3つの計器で測った値。
#   実ラダーのNは小さい(CI併記)。Starmie系はラダー直接対決が無いため2本。
# ---------------------------------------------------------------------------
CALGAP = [
    # (archetype, in-family %, out-of-family %, ladder % or None, ladder n, ci_lo, ci_hi)
    ("Archaludon\n(steel pilot)",   82.0, 21.0, 20.0, 10,  3.5, 55.8),
    ("Lucario\n(official agent)",   85.3, 44.0, 50.0, 14, 26.8, 73.2),
    ("Starmie family\n(teammate)",  92.0, 83.7, None,  0,  0,    0),
]
C_INF, C_OUF, C_LAD = "#bbbbbb", "#2b6cb0", "#1a1a1a"


def fig_calibration_gap():
    w, h = 720, 360
    lx, by, top = 70, 290, 78
    group_w, bar_w, gap = 190, 44, 8
    def yy(v):
        return by - v / 100.0 * (by - top)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">']
    s.append('<text x="24" y="24" font-size="15" font-weight="bold">'
             'Calibration gap: the same matchup on three instruments</text>')
    s.append('<text x="24" y="42" font-size="11" fill="#555">'
             'Same agent (v2.2, 2026-07-21). In-family = we pilot the opponent deck. '
             'Error grows with the real opponent pilot\'s skill: +62 / +41 / +8pt.</text>')
    for g in range(0, 101, 25):
        s.append(f'<line x1="{lx}" y1="{yy(g)}" x2="{w - 20}" y2="{yy(g)}" stroke="#e5e5e5"/>')
        s.append(f'<text x="{lx - 6}" y="{yy(g) + 4}" text-anchor="end" fill="#777" '
                 f'font-size="10">{g}%</text>')
    for i, (name, inf, ouf, lad, n, lo, hi) in enumerate(CALGAP):
        gx = lx + 30 + i * (group_w + 30)
        bars = [(inf, C_INF), (ouf, C_OUF)] + ([(lad, C_LAD)] if lad is not None else [])
        for k, (v, c) in enumerate(bars):
            x = gx + k * (bar_w + gap)
            s.append(f'<rect x="{x}" y="{yy(v)}" width="{bar_w}" height="{by - yy(v)}" '
                     f'fill="{c}" rx="3"/>')
            s.append(f'<text x="{x + bar_w / 2}" y="{yy(v) - 6}" text-anchor="middle" '
                     f'font-size="11" fill="#333">{v:.0f}</text>')
        if lad is not None:
            x = gx + 2 * (bar_w + gap) + bar_w / 2
            s.append(f'<line x1="{x}" y1="{yy(lo)}" x2="{x}" y2="{yy(hi)}" '
                     f'stroke="#666" stroke-width="1.5"/>')
            for cap in (lo, hi):
                s.append(f'<line x1="{x - 5}" y1="{yy(cap)}" x2="{x + 5}" y2="{yy(cap)}" '
                         f'stroke="#666" stroke-width="1.5"/>')
            s.append(f'<text x="{x}" y="{yy(hi) - 6}" text-anchor="middle" font-size="9" '
                     f'fill="#777">n={n}</text>')
        else:
            x = gx + 2 * (bar_w + gap) + bar_w / 2
            s.append(f'<text x="{x}" y="{yy(10)}" text-anchor="middle" font-size="9" '
                     f'fill="#999">no ladder</text>')
            s.append(f'<text x="{x}" y="{yy(10) + 11}" text-anchor="middle" font-size="9" '
                     f'fill="#999">sample</text>')
        for k, line in enumerate(name.split("\n")):
            s.append(f'<text x="{gx + (2 * (bar_w + gap) + bar_w) / 2}" y="{by + 16 + k * 11}" '
                     f'text-anchor="middle" font-size="10">{line}</text>')
    ly = h - 14
    s.append(f'<rect x="70" y="{ly - 9}" width="12" height="12" fill="{C_INF}" rx="2"/>')
    s.append(f'<text x="88" y="{ly + 1}" font-size="11" fill="#333">in-family gauge</text>')
    s.append(f'<rect x="200" y="{ly - 9}" width="12" height="12" fill="{C_OUF}" rx="2"/>')
    s.append(f'<text x="218" y="{ly + 1}" font-size="11" fill="#333">out-of-family gauge</text>')
    s.append(f'<rect x="360" y="{ly - 9}" width="12" height="12" fill="{C_LAD}" rx="2"/>')
    s.append(f'<text x="378" y="{ly + 1}" font-size="11" fill="#333">real ladder (95% CI)</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_calibration_gap.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図5: 探索・上書き層のON/OFF対照実験 (台帳#26 / data.md E4-rev1 2026-07-25, D52)
#      CEW-lite(Lucario+Archaludon 再正規化57.14:42.86)、各腕N=3,200、全6,400戦CRASH=0
# 図6: 提出の打ち切り機構 (台帳#28 / data.md「★★到着レートの機構を訂正」, D57)
#      各提出の「最終対戦」と「latest-2から押し出される時刻」。10/10が押出の0-3h前に停止
# 配色: dataviz skill の検証済みカテゴリカル slot1/slot2。
#   light #2a78d6 / #eb6834、dark #3987e5 / #d95926 — validate_palette.js 全項目PASS
#   (light: CVD ΔE 24.7 / normal 33.6、dark: 26.8 / 31.8、いずれも contrast >=3:1)
# ---------------------------------------------------------------------------

# SVG内に埋める配色定義(ライト/ダーク両対応。閲覧側のテーマで切替わる)
_THEME_CSS = """<style>
  .s1{fill:#2a78d6} .s1s{stroke:#2a78d6} .s2{fill:#eb6834} .s2s{stroke:#eb6834}
  .ink{fill:#0b0b0b} .ink2{fill:#52514e} .grid{stroke:#dcdcd8} .axis{stroke:#b8b8b2}
  .surf{fill:#fcfcfb} .surfs{stroke:#fcfcfb}
  @media (prefers-color-scheme: dark){
    .s1{fill:#3987e5} .s1s{stroke:#3987e5} .s2{fill:#d95926} .s2s{stroke:#d95926}
    .ink{fill:#ffffff} .ink2{fill:#c3c2b7} .grid{stroke:#33332f} .axis{stroke:#55554f}
    .surf{fill:#1a1a19} .surfs{stroke:#1a1a19}
  }
</style>"""


def fig_search_ablation():
    """単一系列(同一指標の2条件)なので凡例なし・直接ラベル。見出しは差分。"""
    ARMS = [("search + override layer ON", 38.72), ("layer OFF (V2_NO_SEARCH=1)", 25.09)]
    DELTA, CI = 13.62, (11.40, 15.84)
    w, h = 660, 336
    lx, rx, ty = 250, 610, 78          # 左ラベル幅 / 右端 / プロット上端
    bar_h, gap = 24, 30                # bar は 24px cap(marks-and-anatomy)
    xmax = 45.0
    def X(v): return lx + (rx - lx) * v / xmax
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">', _THEME_CSS,
         f'<rect width="{w}" height="{h}" class="surf"/>']
    s.append(f'<text x="24" y="30" font-size="15" font-weight="bold" class="ink">'
             f'The search layer is worth +13.62pt on the calibrated instrument</text>')
    s.append(f'<text x="24" y="50" font-size="11" class="ink2">'
             f'Control experiment, N=3,200 per arm (6,400 games, CRASH=0). '
             f'Metric: calibrated out-of-family composite (CEW-lite).</text>')
    # 縦グリッド
    for gv in range(0, int(xmax) + 1, 10):
        s.append(f'<line x1="{X(gv)}" y1="{ty - 6}" x2="{X(gv)}" y2="{ty + 2 * (bar_h + gap)}" '
                 f'class="grid" stroke-width="1"/>')
        s.append(f'<text x="{X(gv)}" y="{ty + 2 * (bar_h + gap) + 16}" text-anchor="middle" '
                 f'font-size="10" class="ink2">{gv}%</text>')
    for i, (name, v) in enumerate(ARMS):
        y = ty + i * (bar_h + gap)
        cls = "s1" if i == 0 else "s2"
        s.append(f'<text x="{lx - 12}" y="{y + bar_h / 2 + 4}" text-anchor="end" '
                 f'class="ink">{name}</text>')
        # 4px rounded data-end / square at baseline: 右端だけ丸める
        bw = X(v) - lx
        s.append(f'<path d="M{lx},{y} H{lx + bw - 4} a4,4 0 0 1 4,4 V{y + bar_h - 4} '
                 f'a4,4 0 0 1 -4,4 H{lx} Z" class="{cls}"/>')
        s.append(f'<text x="{X(v) + 8}" y="{y + bar_h / 2 + 4}" class="ink" '
                 f'font-weight="bold">{v:.2f}%</text>')
    # 差分ブラケット + CI
    by = ty + 2 * (bar_h + gap) + 64   # 軸ラベル(+16)から48px下げて衝突を回避
    s.append(f'<line x1="{X(ARMS[1][1])}" y1="{by}" x2="{X(ARMS[0][1])}" y2="{by}" '
             f'class="axis" stroke-width="2"/>')
    for v in (ARMS[0][1], ARMS[1][1]):
        s.append(f'<line x1="{X(v)}" y1="{by - 5}" x2="{X(v)}" y2="{by + 5}" '
                 f'class="axis" stroke-width="2"/>')
    s.append(f'<text x="{(X(ARMS[0][1]) + X(ARMS[1][1])) / 2}" y="{by - 14}" '
             f'text-anchor="middle" font-size="13" font-weight="bold" class="ink">'
             f'+{DELTA:.2f}pt</text>')
    s.append(f'<text x="{(X(ARMS[0][1]) + X(ARMS[1][1])) / 2}" y="{by + 22}" '
             f'text-anchor="middle" font-size="11" class="ink2">'
             f'95% CI [+{CI[0]:.2f}, +{CI[1]:.2f}] &#183; 12.0&#963;</text>')
    s.append(f'<text x="24" y="{h - 12}" font-size="10" class="ink2">'
             f'Until month seven this component had never been ablated: its only evidence was '
             f'one in-family run of N=200. Ledger #26.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_search_ablation.svg", "w").write("\n".join(s))


def fig_eviction():
    """2系列なので凡例あり + 直接ラベル(dumbbell)。順序は提出時刻。"""
    # (ref, 提出日, 最終対戦h, 押出h, gap)  data.md「★★到着レートの機構を訂正」
    # gap は ListEpisodes の生値から算出した実測差(表の丸め値の減算ではない)
    ROWS = [
        ("54832323", "07-19", 58.7, 59.5, 0.7), ("54858780", "07-20", 43.5, 45.6, 2.1),
        ("54890989", "07-22", 31.1, 31.8, 0.7), ("54905566", "07-22", 36.0, 38.9, 3.0),
        ("54924233", "07-23", 35.3, 37.8, 2.5), ("54943911", "07-24", 55.0, 57.6, 2.6),
        ("54961048", "07-24", 62.5, 64.2, 1.7), ("55004671", "07-26", 47.9, 47.9, 0.0),
        ("55032182", "07-27", 25.4, 25.6, 0.1), ("55058443", "07-28", 11.9, 11.9, 0.0),
    ]
    w = 700
    lx, rx, ty, row_h = 150, 640, 96, 26
    h = ty + len(ROWS) * row_h + 74
    xmax = 70.0
    def X(v): return lx + (rx - lx) * v / xmax
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">', _THEME_CSS,
         f'<rect width="{w}" height="{h}" class="surf"/>']
    s.append(f'<text x="24" y="30" font-size="15" font-weight="bold" class="ink">'
             f'Submissions do not decay &#8212; they are evicted</text>')
    s.append(f'<text x="24" y="50" font-size="11" class="ink2">'
             f'Only a team\'s latest 2 submissions play ladder games. All 10 stopped within '
             f'0&#8211;3h BEFORE being pushed out of that window,</text>')
    s.append(f'<text x="24" y="66" font-size="11" class="ink2">'
             f'even though their lifetimes span 11.9h to 62.5h. What looked like a decay curve '
             f'was our own submission cadence.</text>')
    for gv in range(0, int(xmax) + 1, 10):
        s.append(f'<line x1="{X(gv)}" y1="{ty - 8}" x2="{X(gv)}" y2="{ty + len(ROWS) * row_h - 8}" '
                 f'class="grid" stroke-width="1"/>')
        s.append(f'<text x="{X(gv)}" y="{ty + len(ROWS) * row_h + 8}" text-anchor="middle" '
                 f'font-size="10" class="ink2">{gv}h</text>')
    for i, (ref, day, last, ev, gapv) in enumerate(ROWS):
        y = ty + i * row_h
        s.append(f'<text x="{lx - 12}" y="{y + 4}" text-anchor="end" font-size="11" '
                 f'class="ink">{ref}</text>')
        s.append(f'<text x="{lx - 12}" y="{y + 16}" text-anchor="end" font-size="9" '
                 f'class="ink2">{day}</text>')
        s.append(f'<line x1="{X(min(last, ev))}" y1="{y}" x2="{X(max(last, ev))}" y2="{y}" '
                 f'class="axis" stroke-width="2" stroke-linecap="round"/>')
        # 押出(orange, r6.5)を下、最終対戦(blue, r4)を上に重ねる。
        # gap≈0 の行でも「オレンジの環に青の芯」として両方見える(gap 0.0 は最強の証拠なので消さない)
        s.append(f'<circle cx="{X(ev)}" cy="{y}" r="6.5" class="s2 surfs" stroke-width="2"/>')
        s.append(f'<circle cx="{X(last)}" cy="{y}" r="4" class="s1"/>')
        s.append(f'<text x="{X(max(last, ev)) + 14}" y="{y + 4}" font-size="10" class="ink2">'
                 f'gap {gapv:.1f}h</text>')
    ly = h - 22
    s.append(f'<circle cx="30" cy="{ly - 4}" r="4" class="s1"/>')
    s.append(f'<text x="42" y="{ly}" font-size="11" class="ink2">last ladder game</text>')
    s.append(f'<circle cx="185" cy="{ly - 4}" r="6.5" class="s2"/>')
    s.append(f'<text x="197" y="{ly}" font-size="11" class="ink2">'
             f'evicted from the latest-2 window</text>')
    s.append(f'<text x="{rx - 10}" y="{ly}" text-anchor="end" font-size="10" class="ink2">'
             f'Ledger #28 &#183; hours since submission</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_eviction.svg", "w").write("\n".join(s))


if __name__ == "__main__":
    fig_deck_matrix()   # 注意: 族内測定の数値(D30-B1)。単体では使わず較正の物語の対比のみ
    fig_rating_timeline()
    fig_prospective()
    fig_calibration_gap()
    fig_search_ablation()
    fig_eviction()
    print("wrote 6 figures to", OUT)

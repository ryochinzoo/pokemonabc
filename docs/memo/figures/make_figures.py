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
    """v7版(2026-09-02): 4提出×(較正予測 / ラダー実測CI / 族内含意)のダンベル。台帳#3。
    旧版(1提出目の対面内訳)は git 履歴に残る。数値は claims-ledger.md #3 と一致させること。"""
    ROWS = [
        # (label, calibrated, actual, ci_lo, ci_hi, in_family, n)
        ("EXP8 pilot", 37.0, 35.0, 18, 57, 84.0, 20),
        ("Second archetype", 35.58, 38.1, 20.8, 59.1, 61.37, 21),
        ("Champion re-run", 42.12, 30.0, 14.5, 51.9, 84.42, 20),
        ("Champion, re-weighted", 44.39, 33.3, 17.2, 54.6, 85.12, 21),
    ]
    w, h = 720, 430
    lx, rx, ty, by = 210, 680, 110, 330
    def xx(v):
        return lx + v / 100 * (rx - lx)
    s2 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
          f'font-family="Helvetica,Arial" font-size="12">', _THEME_CSS,
          f'<rect width="{w}" height="{h}" class="surf"/>',
          '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">'
          'Four submissions, four pre-registered predictions, one ladder</text>',
          '<text x="24" y="48" class="ink2">Both figures registered before reading any replay. '
          'The calibrated figure fell inside the ladder\'s 95% CI all four times;</text>',
          '<text x="24" y="66" class="ink2">the in-family figure (our agent piloting the opponent\'s deck) fell outside all four times.</text>']
    for g in range(0, 101, 25):
        s2.append(f'<line x1="{xx(g):.1f}" y1="{ty - 14}" x2="{xx(g):.1f}" y2="{by}" class="grid"/>'
                  f'<text x="{xx(g):.1f}" y="{by + 18}" text-anchor="middle" class="ink2">{g}%</text>')
    step = (by - ty) / len(ROWS)
    for i, (lab, cal, act, lo, hi, inf, n) in enumerate(ROWS):
        y = ty + i * step + step / 2
        s2.append(f'<text x="{lx - 12}" y="{y + 4:.1f}" text-anchor="end" class="ink">{lab}</text>')
        s2.append(f'<text x="{lx - 12}" y="{y + 18:.1f}" text-anchor="end" class="ink2" font-size="10">n={n}</text>')
        s2.append(f'<line x1="{xx(lo):.1f}" y1="{y:.1f}" x2="{xx(hi):.1f}" y2="{y:.1f}" class="axis" stroke-width="1.5"/>')
        for v in (lo, hi):
            s2.append(f'<line x1="{xx(v):.1f}" y1="{y - 5:.1f}" x2="{xx(v):.1f}" y2="{y + 5:.1f}" class="axis" stroke-width="1.5"/>')
        s2.append(f'<path d="M {xx(act):.1f} {y - 6:.1f} L {xx(act) + 6:.1f} {y:.1f} L {xx(act):.1f} {y + 6:.1f} L {xx(act) - 6:.1f} {y:.1f} Z" class="ink"/>')
        s2.append(f'<circle cx="{xx(cal):.1f}" cy="{y:.1f}" r="6" class="s1"/>')
        s2.append(f'<circle cx="{xx(inf):.1f}" cy="{y:.1f}" r="6" fill="none" class="s2s" stroke-width="2.5"/>')
    ly = by + 44
    s2.append(f'<circle cx="34" cy="{ly}" r="6" class="s1"/><text x="46" y="{ly + 4}" class="ink">calibrated prediction</text>')
    s2.append(f'<path d="M 220 {ly - 6} L 226 {ly} L 220 {ly + 6} L 214 {ly} Z" class="ink"/><text x="236" y="{ly + 4}" class="ink">ladder actual (95% CI)</text>')
    s2.append(f'<circle cx="420" cy="{ly}" r="6" fill="none" class="s2s" stroke-width="2.5"/><text x="432" y="{ly + 4}" class="ink">in-family implied</text>')
    s2.append(f'<text x="24" y="{h - 10}" class="ink2" font-size="10">Deviations of the calibrated figure: −2.0 / +2.5 / −12.1 / −11.1pt, no systematic sign.</text>')
    s2.append("</svg>")
    open(f"{OUT}/fig_prospective.svg", "w").write("\n".join(s2))


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
             'Same agent (July 21, 2026). In-family = we pilot the opponent deck. '
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
    ARMS = [("search + override layer ON", 38.72), ("layer OFF", 25.09)]
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
             f'Until late July this component had never been ablated: its only evidence was '
             f'one in-family run of N=200.</text>')
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
             f' &#183; hours since submission</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_eviction.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図5(v7, 2026-09-02): 最終週の窓遷移 = レートの支出明細(台帳 #40)。
#   値は終戦後の確定 publicScore(our-submissions 2026-09-02)。全て単一ドロー。順位主張には使わない。
#   りょーちん翼(55527437 / 55554191)は帰属が本人未確認なので白抜き。日時は日単位(分は書かない)。
# ---------------------------------------------------------------------------
EXPEND = [  # (日付ラベル, 提出ID, 確定レート, ours/teammate, 名前, 押し出したもの→買ったもの)
    ("≤Aug 12", 55421865, 710.8, "ours", "aqua #1", ""),
    ("Aug 13", 55468574, 659.8, "ours", "aqua #2 (same bytes)", "bought: a second draw of the same bytes"),
    ("Aug 15", 55519487, 697.0, "ours", "END-guard", "evicted 710.8 → bought: 0 END-stalls / 46 games in production"),
    ("Aug 16", 55527437, 504.0, "teammate", "teammate", ""),
    ("Aug 16", 55552195, 593.0, "ours", "Boss v1", "evicted 697.0 → bought: first Boss value function in production"),
    ("Aug 17", 55554191, 533.7, "teammate", "teammate", ""),
    ("Aug 17", 55558557, 656.7, "ours", "Boss final", "evicted 593.0 → the final agent, predictions frozen first"),
]


def fig_rating_expenditure():
    w, h = 900, 470
    lx, rx, ty, by = 70, 860, 96, 300
    ymin, ymax = 450, 760
    n = len(EXPEND)
    xs = [lx + 30 + i * (rx - lx - 60) / (n - 1) for i in range(n)]

    def yy(v):
        return by - (v - ymin) / (ymax - ymin) * (by - ty)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">', _THEME_CSS,
         f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">'
         'The last week, as an expenditure statement: every new submission evicts the team\'s '
         'next-but-one</text>',
         '<text x="24" y="48" class="ink2">Final rating of each submission (frozen Aug 17 08:59 JST; ladder ran to Aug 31).</text>',
         '<text x="24" y="66" class="ink2">Filled = ours, hollow = teammate\'s (attribution unconfirmed). Dashed = team display, the higher of the latest two.</text>']
    for g in range(500, 761, 50):
        s.append(f'<line x1="{lx}" y1="{yy(g):.1f}" x2="{rx}" y2="{yy(g):.1f}" class="grid"/>'
                 f'<text x="{lx - 6}" y="{yy(g) + 4:.1f}" text-anchor="end" class="ink2">{g}</text>')
    # 表示スコア(直近2件の最大)の階段線
    disp = []
    for i in range(n):
        window = EXPEND[max(0, i - 1):i + 1]
        disp.append(max(e[2] for e in window))
    pts = " ".join(f"{xs[i]:.1f},{yy(disp[i]):.1f}" for i in range(n))
    s.append(f'<polyline points="{pts}" fill="none" class="s1s" stroke-width="2" stroke-dasharray="5,4" opacity="0.7"/>')
    for i, (day, sid, v, who, name, bought) in enumerate(EXPEND):
        x, y = xs[i], yy(v)
        if who == "ours":
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="s1"/>')
        else:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="none" class="s2s" stroke-width="2.5"/>')
        s.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-weight="bold" class="ink">{v:.1f}</text>')
        s.append(f'<text x="{x:.1f}" y="{by + 18}" text-anchor="middle" class="ink">{day}</text>')
        s.append(f'<text x="{x:.1f}" y="{by + 33}" text-anchor="middle" class="ink2" font-size="10">{name}</text>')
    # 支出明細の注記(下部、ours のみ)
    yb = by + 58
    for day, sid, v, who, name, bought in EXPEND:
        if bought:
            s.append(f'<text x="24" y="{yb}" class="ink2" font-size="11">{day}: {bought}</text>')
            yb += 15
    s.append(f'<line x1="24" y1="{h - 30}" x2="{w - 24}" y2="{h - 30}" class="grid"/>')
    s.append(f'<text x="24" y="{h - 12}" class="ink2" font-size="10"> (exploratory: single draws, '
             'same-submission spread ±36–72 in #20). Not evidence of strength; a record of what each slot was spent on.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_rating_expenditure.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図7(v7): 同じ地平問題に独立2解(台帳 #41、ryochin-v8-ideas-2026-08-14.md)。数値なしの概念図。
# ---------------------------------------------------------------------------
def fig_horizon_uncertainty():
    w, h = 780, 450
    gx, gy, gw, gh = 230, 100, 500, 260   # 2×2 グリッド
    cw, ch = gw / 2, gh / 2
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'font-family="Helvetica,Arial" font-size="12">', _THEME_CSS,
         f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">'
         'Two independent pilots, one horizon problem, two different blind spots</text>',
         '<text x="24" y="48" class="ink2">Where each development line placed its look-ahead, '
         'and where each one failed. Same team, no shared code.</text>']
    for i in range(3):
        s.append(f'<line x1="{gx + i * cw:.1f}" y1="{gy}" x2="{gx + i * cw:.1f}" y2="{gy + gh}" class="axis"/>')
        s.append(f'<line x1="{gx}" y1="{gy + i * ch:.1f}" x2="{gx + gw}" y2="{gy + i * ch:.1f}" class="axis"/>')
    # 軸ラベル
    s.append(f'<text x="{gx + cw / 2:.1f}" y="{gy + gh + 22}" text-anchor="middle" class="ink" font-weight="bold">within this turn</text>')
    s.append(f'<text x="{gx + cw * 1.5:.1f}" y="{gy + gh + 22}" text-anchor="middle" class="ink" font-weight="bold">next turn and beyond</text>')
    s.append(f'<text x="{gx + gw / 2:.1f}" y="{gy + gh + 40}" text-anchor="middle" class="ink2">time horizon of the look-ahead</text>')
    s.append(f'<text x="{gx - 12}" y="{gy + ch / 2:.1f}" text-anchor="end" class="ink" font-weight="bold">exact enumeration</text>')
    s.append(f'<text x="{gx - 12}" y="{gy + ch / 2 + 15:.1f}" text-anchor="end" class="ink2" font-size="11">(hypergeometric odds)</text>')
    s.append(f'<text x="{gx - 12}" y="{gy + ch * 1.5:.1f}" text-anchor="end" class="ink" font-weight="bold">sampled worlds</text>')
    s.append(f'<text x="{gx - 12}" y="{gy + ch * 1.5 + 15:.1f}" text-anchor="end" class="ink2" font-size="11">(determinized rollouts)</text>')
    s.append(f'<text x="{gx - 12}" y="{gy - 14}" text-anchor="end" class="ink2">handling of hidden information</text>')

    def box(col, row, cls, title, lines):
        x0, y0 = gx + col * cw + 10, gy + row * ch + 10
        s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{cw - 20:.1f}" height="{ch - 20:.1f}" rx="6" '
                 f'fill="none" class="{cls}s" stroke-width="2.5"/>')
        s.append(f'<text x="{x0 + 10:.1f}" y="{y0 + 22:.1f}" font-weight="bold" class="{cls}">{title}</text>')
        for k, ln in enumerate(lines):
            s.append(f'<text x="{x0 + 10:.1f}" y="{y0 + 42 + k * 15:.1f}" class="ink2" font-size="11">{ln}</text>')

    box(0, 0, "s2", "Ryohei Hara's line",
        ["reachability of this turn's attacks via", "attach / retreat / Boss routes; exact", "hit odds for search cards (comb).",
         "Blind spot: nothing beyond the turn."])
    box(1, 1, "s1", "our line (search + override)",
        ["engine-rule rollouts to root+2 turns", "over sampled opponent hands.",
         "Blind spots: override margin 120 vs", "prize term ±10,000; compound same-", "turn plays outside the horizon."])
    s.append(f'<text x="{gx + cw * 1.5:.1f}" y="{gy + ch / 2:.1f}" text-anchor="middle" class="ink2" font-size="11">(neither line)</text>')
    s.append(f'<text x="{gx + cw / 2:.1f}" y="{gy + ch * 1.5:.1f}" text-anchor="middle" class="ink2" font-size="11">(neither line)</text>')
    s.append(f'<text x="24" y="{h - 22}" class="ink2" font-size="10"> (exploratory). Ryohei Hara\'s line ran no win-rate measurement;</text>')
    s.append(f'<text x="24" y="{h - 8}" class="ink2" font-size="10">the claim is only that the two lines converged on mono-Water independently and failed in different cells.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_horizon_uncertainty.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# 図6(v7): bosslogic 本番検死 — 予測 vs 実測(台帳 #39)。数値は replay_analysis/eps55558557_autopsy.json から読む。
#   分母を必ず表示。対照 = 55552195(v1バイト)の同じプローブ。効果量は無い(行動のみ)。
# ---------------------------------------------------------------------------
def fig_bosslogic_autopsy():
    """v8 再設計(J-B の指摘): 「門が保持された(構造上)」と「予測が本当に試された」を分け、レビューの発見を足す。
    数値は replay_analysis/eps55558557_autopsy.json(v2、エネ考慮込み)と eps55552195_autopsy.json(対照)から読む。"""
    import json as _json
    main_p = os.path.abspath(os.path.join(os.path.dirname(OUT), "..", "..", "replay_analysis", "eps55558557_autopsy.json"))
    ctrl_p = os.path.abspath(os.path.join(os.path.dirname(OUT), "..", "..", "replay_analysis", "eps55552195_autopsy.json"))
    if not os.path.exists(main_p):
        print("fig_bosslogic_autopsy: skipped (no", main_p, ")")
        return
    T = _json.load(open(main_p))["totals"]
    C = _json.load(open(ctrl_p))["totals"] if os.path.exists(ctrl_p) else {}
    fmt = lambda k, n: f"{k:,} / {n:,}"
    groups = [
        ("Gates that hold by construction (the gate blocks this path; a non-zero count would mean a bug)", [
            ("Lookahead replaced a productive move with END", fmt(T.get("P5_end_stall", 0), T.get("main", 0)), f"earlier build without the gate: 9 / 1,479", "hold"),
            ("Lookahead attacked before free plays (evolve, attach, play)", fmt(T.get("P4_L12_violation", 0), T.get("main", 0)), f"v1 bytes: {C.get('P4_L12_violation', 0)} / {C.get('main', 0)}", "hold"),
            ("Boss's Orders target = the rule's own first choice", fmt(T.get("P1_conform", 0), T.get("P1_boss_target", 0)), "targets are never searched", "hold"),
        ]),
        ("Predictions that were really tested (frozen before submission)", [
            ("Crashes or stderr in production (predicted 0)", fmt(T.get("crash_games", 0), T.get("games", 0)), "0 stderr, worst per-game p99 602 ms", "pass"),
            ("Boss's Orders misfires (predicted 0)", f"{T.get('P2_misfire', 0)} / {T.get('P2_boss_played', 0)} by the rule; {T.get('P2e_misfire', 0)} / {T.get('P2_boss_played', 0)} counting energy",
             "every one a lookahead override", "fail"),
        ]),
        ("Found afterwards by outside review", [
            ("The 'can I knock it out' test ignored attached energy", f"{T.get('P1_koable_flips_with_energy', 0)} / {T.get('P1_boss_target', 0)} targets change status", f"{T.get('P1e_conform', 0)} / {T.get('P1_boss_target', 0)} still the best target", "found"),
            ("One rule and one gate were wired to a selection type the engine issued 0 times", "0 / 1,000 games", "attack-split rule and bench-rider lock never ran", "found"),
        ]),
        ("Measured after the deadline on the calibrated instrument (6,400 games per comparison, pre-registered)", [
            ("vs the list our discipline would have submitted (same pilot lineage, Boss's Orders ×2)", "−3.29pt  [−5.19, −1.39]", "negative in all five matchups; worst vs Mega Lucario −7.62", "worse"),
            ("the last night's rules alone (same deck, pilot swapped)", "−2.78pt  [−3.97, −1.59]", "Grimmsnarl −4.65, Lucario −4.88", "worse"),
            ("the energy-aware fix for the blind spot above", "−2.42pt  [−5.85, +1.01]", "correct diagnosis, no detectable improvement", "ns"),
        ]),
    ]
    w = 900
    h = 100 + sum(30 + 30 * len(rows) for _, rows in groups) + 54
    s2 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">', _THEME_CSS,
          f'<rect width="{w}" height="{h}" class="surf"/>',
          '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">The final agent over its last 1,000 ladder games</text>',
          f'<text x="24" y="48" class="ink2">{T.get("games", 0):,} games, {T.get("main", 0):,} main-phase decisions, {T.get("P2_boss_played", 0)} Boss\'s Orders played. '
          'Behaviour above the line; effect sizes, measured after the deadline, below it.</text>']
    y = 84
    chip = {"hold": ("axis", "held"), "pass": ("s1", "PASS"), "fail": ("s2", "FAIL"), "found": ("axis", "noted"), "worse": ("s2", "worse"), "ns": ("axis", "n.s.")}
    for title, rows in groups:
        s2.append(f'<text x="24" y="{y}" font-weight="bold" class="ink">{title}</text>')
        s2.append(f'<line x1="24" y1="{y + 8}" x2="{w - 24}" y2="{y + 8}" class="axis"/>')
        y += 30
        for lab, kn, note, kind in rows:
            cls, txt = chip[kind]
            s2.append(f'<text x="24" y="{y}" class="ink">{lab}</text>')
            s2.append(f'<text x="520" y="{y}" class="ink" font-weight="bold" font-size="11">{kn}</text>')
            s2.append(f'<text x="520" y="{y + 13}" class="ink2" font-size="10">{note}</text>')
            if kind in ("pass", "fail", "worse"):
                s2.append(f'<rect x="{w - 84}" y="{y - 13}" width="56" height="18" rx="4" class="{cls}"/>')
                s2.append(f'<text x="{w - 56}" y="{y}" text-anchor="middle" fill="#fff" font-weight="bold" font-size="11">{txt}</text>')
            else:
                s2.append(f'<rect x="{w - 84}" y="{y - 13}" width="56" height="18" rx="4" fill="none" class="axis" stroke-width="1.5"/>')
                s2.append(f'<text x="{w - 56}" y="{y}" text-anchor="middle" class="ink2" font-weight="bold" font-size="11">{txt}</text>')
            y += 30
        y += 6
    s2.append(f'<text x="24" y="{h - 26}" class="ink2" font-size="10">Sources: Kaggle replays of submission 55558557 (option list at step N, answer at step N+1), re-scored with the submitted code\'s own helpers;</text>')
    s2.append(f'<text x="24" y="{h - 12}" class="ink2" font-size="10">post-deadline rows: the calibrated out-of-family composite of Figs. 4–6, 8 blocks × 5 opponents, batch-means 95% CI.</text>')
    s2.append("</svg>")
    open(f"{OUT}/fig_bosslogic_autopsy.svg", "w").write("\n".join(s2))


# ---------------------------------------------------------------------------
# v8 (2026-09-02, 外部評議会の裁定): 決定フロー / デッキとプラン / 対面プロファイル / 検死の再設計
# ---------------------------------------------------------------------------
def _box(s, x, y, w, h, title, lines, cls="axis", title_cls="ink"):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" class="{cls}" stroke-width="1.8"/>')
    s.append(f'<text x="{x + 10}" y="{y + 20}" font-weight="bold" class="{title_cls}" font-size="12">{title}</text>')
    for k, ln in enumerate(lines):
        s.append(f'<text x="{x + 10}" y="{y + 38 + k * 14}" class="ink2" font-size="11">{ln}</text>')


def _arrow(s, x1, y1, x2, y2):
    s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="axis" stroke-width="1.8"/>')
    # 矢尻(水平 or 垂直)
    if y1 == y2:
        d = 1 if x2 > x1 else -1
        s.append(f'<path d="M {x2} {y2} L {x2 - 8 * d} {y2 - 4} L {x2 - 8 * d} {y2 + 4} Z" class="axis" fill="#b8b8b2"/>')
    else:
        d = 1 if y2 > y1 else -1
        s.append(f'<path d="M {x2} {y2} L {x2 - 4} {y2 - 8 * d} L {x2 + 4} {y2 - 8 * d} Z" class="axis" fill="#b8b8b2"/>')


def fig_decision_flow():
    w, h = 900, 450
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">',
         _THEME_CSS, f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">How the pilot chooses an action</text>',
         '<text x="24" y="48" class="ink2">A greedy evaluator and fourteen human-taught rules propose a move; a short engine lookahead may override it;</text>',
         '<text x="24" y="66" class="ink2">eight one-way gates block the overrides we had seen go wrong.</text>']
    y1, bh = 96, 96
    _box(s, 24, y1, 150, bh, "Observation", ["board, hands, prizes,", "legal options from", "the official engine"])
    _arrow(s, 174, y1 + 48, 196, y1 + 48)
    _box(s, 196, y1, 210, bh, "Greedy evaluator", ["evolve > ability > play >", "attach > attack > end;", "damage and prize value"])
    _arrow(s, 406, y1 + 48, 428, y1 + 48)
    _box(s, 428, y1, 230, bh, "14 rules taught by a player", ["Boss's Orders: knock out now >", "the piece that evolves > bind;", "play order, hand resets, bench"])
    _arrow(s, 658, y1 + 48, 680, y1 + 48)
    _box(s, 680, y1, 196, bh, "Proposed move (v1)", ["always legal;", "the fallback if anything", "below fails"], cls="s1s", title_cls="s1")
    # 下段
    y2 = y1 + bh + 52
    _arrow(s, 778, y1 + bh, 778, y2)
    _box(s, 640, y2, 236, bh, "Engine lookahead", ["2 sampled opponent hands,", "rollouts to the turn after next,", "at most 0.6 s per decision"])
    _arrow(s, 640, y2 + 48, 618, y2 + 48)
    _box(s, 408, y2, 210, bh, "Override?", ["only if the lookahead value", "beats v1 by a margin (120)", "— 250× smaller than a prize"], cls="s2s", title_cls="s2")
    _arrow(s, 408, y2 + 48, 386, y2 + 48)
    _box(s, 176, y2, 210, bh, "8 one-way gates", ["never override into: retreat,", "END, attack before free plays,", "hand reset; keep v1's Boss"], cls="s2s", title_cls="s2")
    _arrow(s, 176, y2 + 48, 154, y2 + 48)
    _box(s, 24, y2, 130, bh, "Action", ["checked against the", "engine's option list"], cls="s1s", title_cls="s1")
    s.append(f'<text x="24" y="{h - 52}" class="ink2" font-size="11">The gates protect the proposed move from the lookahead, not the reverse: the lookahead can still turn a non-Boss proposal into Boss\'s Orders.</text>')
    s.append(f'<text x="24" y="{h - 36}" class="ink2" font-size="11">That unguarded direction is where the misfires in Fig. 7 came from.</text>')
    s.append(f'<text x="24" y="{h - 20}" class="ink2" font-size="11">Rules and gates are derived from card text at run time; the ten opponent-deck lists used for hidden-hand sampling are not.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_decision_flow.svg", "w").write("\n".join(s))


DECK = [  # (group, count, name)
    ("Pokémon (8)", 4, "Staryu"), ("Pokémon (8)", 4, "Mega Starmie ex"),
    ("Energy (16)", 12, "Basic Water Energy"), ("Energy (16)", 4, "Ignition Energy"),
    ("Supporters (19)", 4, "Hilda"), ("Supporters (19)", 4, "Lillie's Determination"), ("Supporters (19)", 4, "Wally's Compassion"),
    ("Supporters (19)", 3, "Boss's Orders"), ("Supporters (19)", 2, "Carmine"), ("Supporters (19)", 2, "Judge"),
    ("Items (14)", 4, "Ultra Ball"), ("Items (14)", 4, "Buddy-Buddy Poffin"), ("Items (14)", 4, "Pokégear 3.0"), ("Items (14)", 2, "Night Stretcher"),
    ("Stadium / ACE SPEC (3)", 2, "Surfing Beach"), ("Stadium / ACE SPEC (3)", 1, "Deluxe Bomb"),
]
ATTACK_USE = [("Jetting Blow  (1 Water: 120 + 50 to a Benched Pokémon)", 71.4), ("Nebula Beam  (3 Energy: 210)", 18.5), ("Water Gun  (Staryu: 20)", 10.2)]


def fig_deck_plan():
    w, h = 960, 540
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">',
         _THEME_CSS, f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">The 60-card list and its plan: two knock-outs with one attacker</text>',
         '<text x="24" y="48" class="ink2">Mono-Water, two species, four Basics. Every removal from the parent list was forced by measurement, not by theory.</text>']
    # 左: リスト
    y = 84
    last = None
    for grp, n, name in DECK:
        if grp != last:
            y += 8 if last else 0
            s.append(f'<text x="24" y="{y}" font-weight="bold" class="ink">{grp}</text>')
            y += 18
            last = grp
        s.append(f'<text x="40" y="{y}" class="ink2">{n} × {name}</text>')
        y += 16
    # 右上: 技使用率
    bx, by, bw = 400, 92, 300
    s.append(f'<text x="{bx}" y="{by - 12}" font-weight="bold" class="ink">Which attack it actually uses (last 1,000 ladder games, 4,318 attacks)</text>')
    for i, (lab, pct) in enumerate(ATTACK_USE):
        yy = by + 10 + i * 46
        s.append(f'<text x="{bx}" y="{yy}" class="ink2" font-size="11">{lab}</text>')
        s.append(f'<rect x="{bx}" y="{yy + 6}" width="{bw * pct / 100:.1f}" height="16" rx="3" ' + ('class="s1"' if i == 0 else 'fill="#c9c9c4"') + '/>')
        s.append(f'<text x="{bx + bw * pct / 100 + 6:.1f}" y="{yy + 19}" class="ink" font-weight="bold">{pct:.1f}%</text>')
    # 右下: プラン
    py = by + 160
    plan = [
        "The plan. Six prizes in two turns: 3 from a Mega ex, or 2 from an ex plus 1 from a Basic hit",
        "by the 50-damage splash. Jetting Blow costs one Water, so Wally's Compassion's energy",
        "return costs one attachment; Ignition Energy alone pays for Nebula Beam; Surfing Beach",
        "is the only switch. It is a race, run every game.",
        "",
        "Four Basics, on purpose. The list mulligans 60% of the time. Eight or ten Basics cut that",
        "to 26% and did not help (34.5 → 33.0 → 31.2; screening, N = 300 per gauge, July list and pilot).",
        "",
        "Rejected by measurement: the Dusknoir sacrifice engine (the list without it won 64.7%",
        "head-to-head, N = 150); Cinderace energy acceleration, tried and dropped (0.12 uses per",
        "game in our hands). Deluxe Bomb is the ACE SPEC; a Belt in its place measured −0.57pt",
        "(95% CI −2.82 to +1.68).",
        "",
        "Boss's Orders ×3. The August list ran two; a third copy measured −1.53pt with the old",
        "pilot, which had no idea whom to drag out. Re-added with the value ordering in Fig. 1.",
    ]
    s.append(f'<rect x="{bx - 10}" y="{py - 6}" width="{w - bx - 14}" height="{len(plan) * 15 + 14}" rx="6" fill="none" class="axis" stroke-width="1.2"/>')
    for k, ln in enumerate(plan):
        s.append(f'<text x="{bx}" y="{py + 14 + k * 15}" class="{"ink" if ln.startswith(("The plan", "Four Basics", "Rejected", "Boss")) else "ink2"}" font-size="11">{ln}</text>')
    s.append(f'<text x="24" y="{h - 10}" class="ink2" font-size="10">Sources: deck list as submitted; attack counts from Kaggle replays; measurements on the calibrated out-of-family composite (see Figs. 4–6).</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_deck_plan.svg", "w").write("\n".join(s))


MATCHUPS_FINAL = [  # (label, W, L) — probe_autopsy on the last 1,000 ladder games, n >= 55 only
    ("Wall decks (Crustle)", 94, 16), ("Dragapult ex", 68, 31), ("Alakazam", 113, 86), ("Mega Starmie ex (mirror)", 25, 30),
    ("Marnie's Grimmsnarl ex", 29, 44), ("Mega Lucario ex", 78, 138), ("Archaludon ex", 29, 79),
]


def fig_matchup_profile():
    w, h = 760, 430
    lx, rx, ty, by = 230, 700, 96, 330
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">',
         _THEME_CSS, f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">Where the final agent wins, and where it still loses</text>',
         '<text x="24" y="48" class="ink2">Win rate by opponent archetype over the last 1,000 ladder games (matchups with n ≥ 55). Overall 51.2%.</text>',
         '<text x="24" y="66" class="ink2">It earns its rating against walls and Dragapult and loses to its two most frequent opponents.</text>']
    def xx(v):
        return lx + v / 100 * (rx - lx)
    for g in (0, 25, 50, 75, 100):
        s.append(f'<line x1="{xx(g):.1f}" y1="{ty - 8}" x2="{xx(g):.1f}" y2="{by}" class="grid"/>'
                 f'<text x="{xx(g):.1f}" y="{by + 18}" text-anchor="middle" class="ink2">{g}%</text>')
    s.append(f'<line x1="{xx(50):.1f}" y1="{ty - 8}" x2="{xx(50):.1f}" y2="{by}" class="axis" stroke-width="1.5" stroke-dasharray="4,3"/>')
    step = (by - ty) / len(MATCHUPS_FINAL)
    for i, (lab, W, L) in enumerate(MATCHUPS_FINAL):
        n = W + L
        pct = 100 * W / n
        y = ty + i * step + 6
        s.append(f'<text x="{lx - 12}" y="{y + 15}" text-anchor="end" class="ink">{lab}</text>')
        s.append(f'<rect x="{lx}" y="{y}" width="{xx(pct) - lx:.1f}" height="{step - 12:.1f}" rx="3" class="{"s1" if pct >= 50 else "s2"}"/>')
        s.append(f'<text x="{xx(pct) + 6:.1f}" y="{y + 15}" class="ink" font-weight="bold">{pct:.0f}%</text>')
        s.append(f'<text x="{xx(pct) + 48:.1f}" y="{y + 15}" class="ink2" font-size="11">{W}–{L}, n = {n}</text>')
    s.append(f'<text x="24" y="{h - 26}" class="ink2" font-size="10">Omitted (n &lt; 55): Abomasnow 7–11, Garchomp 8–7, Team Rocket\'s Mewtwo 7–3, Mega Kangaskhan 4–0. '
             f'Archetype from the opponent\'s 60-card list.</text>')
    s.append(f'<text x="24" y="{h - 10}" class="ink2" font-size="10">Source: Kaggle replays of submission 55558557, Aug 22–31 (the API returns the latest 1,000 episodes).</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_matchup_profile.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# Fig. 9: デッキの系譜(台帳 #58。理由の数値は #4/#7/#34/#50)。2026-09-09 材料の旅で新設。
# ---------------------------------------------------------------------------
LINEAGE = [  # (group, removed, added, why lines)
    ("Dusknoir engine", "−2 Duskull, −2 Dusclops, −2 Dusknoir", "",
     ["Measured out: the list without it won 64.7% head-to-head (N = 150).",
      "Our forecast from the coaching canon, written before the run, was −5 to −10; the sign was wrong."]),
    ("Poké Pad", "−4 Poké Pad", "",
     ["82% of the 105 top-band teams run it. Adding one back measured −1.58pt",
      "(95% CI −3.45 to +0.29) with the pilot byte-identical."]),
    ("Supporter trim", "−1 Carmine, −1 Judge", "",
     ["Part of the mono-Water rebuild; measured as a bundle, not per card."]),
    ("Mono-Water core", "", "+3 Basic Water, +1 Mega Starmie ex, +1 Pokégear 3.0",
     ["Energy for the one-energy 120 + 50 plan, a fourth copy of the only attacker."]),
    ("Recovery and switch", "", "+3 Night Stretcher (−1 on Aug 17), +2 Surfing Beach",
     ["Bring the attacker back; Surfing Beach is the deck's only switch."]),
    ("Boss's Orders 0 → 2 → 3", "", "+2 (Aug 11), +1 (Aug 17)",
     ["The third copy measured −1.53pt (95% CI −2.76 to −0.30) with the old pilot.",
      "Re-added with the targeting rules of Fig. 1; the bundle measured −3.29pt after the deadline."]),
]


def fig_deck_lineage():
    w, h = 960, 520
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">',
         _THEME_CSS, f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">From the human-orthodox list to the submitted one: twelve cards, each with a measurement or a reason</text>',
         '<text x="24" y="48" class="ink2">Parent = a July 14 human-style list with the Dusknoir engine. Twelve cards moved by Aug 11; on Aug 17 a Night Stretcher became the third Boss\'s Orders.</text>']
    cx = [24, 250, 560]
    y = 84
    for lab, x in zip(("Change", "Removed", "Added"), cx):
        s.append(f'<text x="{x}" y="{y}" font-weight="bold" class="ink">{lab}</text>')
    s.append(f'<line x1="24" y1="{y + 8}" x2="{w - 24}" y2="{y + 8}" class="axis"/>')
    y += 30
    for grp, rem, add, why in LINEAGE:
        s.append(f'<text x="{cx[0]}" y="{y}" class="ink" font-weight="bold">{grp}</text>')
        if rem:
            s.append(f'<text x="{cx[1]}" y="{y}" class="s2" font-size="11">{rem}</text>')
        if add:
            s.append(f'<text x="{cx[2]}" y="{y}" class="s1" font-size="11">{add}</text>')
        for k, ln in enumerate(why):
            s.append(f'<text x="{cx[1]}" y="{y + 17 + k * 15}" class="ink2" font-size="11">{ln}</text>')
        y += 17 + len(why) * 15 + 18
        s.append(f'<line x1="24" y1="{y - 12}" x2="{w - 24}" y2="{y - 12}" class="grid"/>')
    s.append(f'<text x="24" y="{h - 42}" class="ink2" font-size="11">Net parent → final: −6 Dusknoir line, −4 Poké Pad, −1 Carmine, −1 Judge / +3 Water, +2 Night Stretcher, +1 Mega Starmie ex, +1 Pokégear 3.0, +2 Surfing Beach, +3 Boss\'s Orders.</text>')
    s.append(f'<text x="24" y="{h - 26}" class="ink2" font-size="10">Sources: deck.csv of the parent (Jul 14), aqua (Aug 11) and the submission (Aug 17); effect sizes on the calibrated out-of-family composite (Figs. 4–6), pilot byte-identical within each test.</text>')
    s.append(f'<text x="24" y="{h - 10}" class="ink2" font-size="10">Expert intuition is reliable only where the expert has had fast feedback from a regular environment (Kahneman &amp; Klein 2009); no one had such feedback about an AI pilot, so every orthodoxy was measured.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_deck_lineage.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# Fig. 10: 公開リーダーボード 6,807 チームの分布(台帳 #59。lake/leaderboard の 2026-09-01T17:56 CSV を 50 点刻みで再集計)
# ---------------------------------------------------------------------------
LB_HIST = [(-600, 1), (-350, 1), (-300, 1), (-250, 2), (-200, 1), (-150, 6), (-100, 6), (-50, 14), (0, 22), (50, 59), (100, 75),
           (150, 110), (200, 190), (250, 180), (300, 198), (350, 261), (400, 365), (450, 433), (500, 529), (550, 664), (600, 694),
           (650, 812), (700, 650), (750, 388), (800, 446), (850, 247), (900, 204), (950, 123), (1000, 71), (1050, 19), (1100, 14),
           (1150, 12), (1200, 4), (1250, 4), (1350, 1)]
LB_N, LB_MEDIAN, LB_P90, OURS = 6807, 621.5, 853.5, 656.7


def fig_rating_distribution():
    w, h = 760, 400
    lx, rx, ty, by = 60, 720, 90, 320
    x0, x1 = -400, 1400
    def xx(v):
        return lx + (v - x0) / (x1 - x0) * (rx - lx)
    ymax = 850
    def yy(c):
        return by - c / ymax * (by - ty)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">',
         _THEME_CSS, f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">Where 656.7 sits: the final ratings of all 6,807 teams</text>',
         '<text x="24" y="48" class="ink2">Public leaderboard snapshot of Sep 1, 50-point bins. Median 621.5; 90% of teams below 853.5. This submission: rank 2,898, top 42.6%.</text>']
    for g in (0, 200, 400, 600, 800, 1000, 1200, 1400):
        s.append(f'<line x1="{xx(g):.1f}" y1="{ty}" x2="{xx(g):.1f}" y2="{by}" class="grid"/>'
                 f'<text x="{xx(g):.1f}" y="{by + 18}" text-anchor="middle" class="ink2">{g}</text>')
    for b, c in LB_HIST:
        if b < x0:
            continue
        s.append(f'<rect x="{xx(b) + 1:.1f}" y="{yy(c):.1f}" width="{xx(b + 50) - xx(b) - 2:.1f}" height="{by - yy(c):.1f}" fill="#c9c9c4"/>')
    s.append(f'<line x1="{xx(LB_MEDIAN):.1f}" y1="{ty}" x2="{xx(LB_MEDIAN):.1f}" y2="{by}" class="axis" stroke-width="1.5" stroke-dasharray="4,3"/>')
    s.append(f'<text x="{xx(LB_MEDIAN) - 6:.1f}" y="{ty + 14}" text-anchor="end" class="ink2" font-size="11">median 621.5</text>')
    s.append(f'<line x1="{xx(OURS):.1f}" y1="{ty}" x2="{xx(OURS):.1f}" y2="{by}" class="s1s" stroke-width="2.5"/>')
    s.append(f'<text x="{xx(OURS) + 6:.1f}" y="{ty + 14}" class="s1" font-weight="bold" font-size="11">this submission 656.7 (rank 2,898 of 6,807)</text>')
    s.append(f'<line x1="{xx(LB_P90):.1f}" y1="{ty}" x2="{xx(LB_P90):.1f}" y2="{by}" class="axis" stroke-width="1" stroke-dasharray="2,3"/>')
    s.append(f'<text x="{xx(LB_P90) + 6:.1f}" y="{ty + 32}" class="ink2" font-size="11">90th percentile 853.5</text>')
    s.append(f'<text x="{lx}" y="{by + 36}" class="ink2" font-size="11">Kaggle rating at the end of the Simulation ladder</text>')
    s.append(f'<text x="24" y="{h - 10}" class="ink2" font-size="10">Source: kaggle competitions leaderboard --download, 2026-09-01T17:56 UTC; 6,807 teams; ties at 656.7 occupy ranks 2,897–2,899.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_rating_distribution.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# Fig. 11: 初期状態への依存(台帳 #53〜#56、first_player_split.py、最終 1,000 譜)
# ---------------------------------------------------------------------------
START_FIRST = [("Going first", 372, 645), ("Going second", 140, 349), ("Whoever went first", 581, 994)]
START_MULL = [("0", 215, 397), ("1", 138, 248), ("2", 68, 141), ("3", 37, 86), ("4+", 54, 122)]
START_MEGA = [("in wins", 471, 512), ("in losses", 358, 482), ("losses, going second", 136, 209)]
START_BAND = [("500s", 88, 158), ("600s", 302, 576), ("700s", 88, 198), ("800s", 3, 20)]


def _wilson(k, n, z=1.96):
    import math
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    hh = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return 100 * (c - hh), 100 * (c + hh)


def _panel(s, x, y, w, h, title, rows, note):
    s.append(f'<text x="{x}" y="{y}" font-weight="bold" class="ink">{title}</text>')
    bx, bw = x + 96, w - 150
    top = y + 16
    step = (h - 40) / len(rows)
    def xx(v):
        return bx + v / 100 * bw
    s.append(f'<line x1="{xx(50):.1f}" y1="{top - 4}" x2="{xx(50):.1f}" y2="{top + step * len(rows)}" class="axis" stroke-dasharray="4,3"/>')
    for i, (lab, k, n) in enumerate(rows):
        yy = top + i * step
        pct = 100 * k / n
        lo, hi = _wilson(k, n)
        s.append(f'<text x="{bx - 8}" y="{yy + 13}" text-anchor="end" class="ink2" font-size="11">{lab}</text>')
        s.append(f'<rect x="{bx}" y="{yy + 2}" width="{xx(pct) - bx:.1f}" height="{step - 8:.1f}" rx="3" class="{"s1" if pct >= 50 else "s2"}"/>')
        s.append(f'<line x1="{xx(lo):.1f}" y1="{yy + step / 2 - 2:.1f}" x2="{xx(hi):.1f}" y2="{yy + step / 2 - 2:.1f}" class="axis" stroke-width="1.2"/>')
        s.append(f'<text x="{xx(hi) + 6:.1f}" y="{yy + 13}" class="ink" font-size="11" font-weight="bold">{pct:.1f}%</text>')
        s.append(f'<text x="{xx(hi) + 48:.1f}" y="{yy + 13}" class="ink2" font-size="10">{k}/{n}</text>')
    for k, ln in enumerate(note if isinstance(note, (list, tuple)) else [note]):
        s.append(f'<text x="{x}" y="{y + h - 18 + k * 13}" class="ink2" font-size="10">{ln}</text>')


def fig_start_profile():
    w, h = 960, 500
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="Helvetica,Arial" font-size="12">',
         _THEME_CSS, f'<rect width="{w}" height="{h}" class="surf"/>',
         '<text x="24" y="28" font-size="15" font-weight="bold" class="ink">Where the final agent depends on the start of the game (last 1,000 ladder games, 95% Wilson intervals)</text>',
         '<text x="24" y="48" class="ink2">Overall 51.2%. It wins going first, pays for its four Basics in mulligans, loses a quarter of its losses without taking a prize,</text>',
         '<text x="24" y="64" class="ink2">and holds its rate against opponents of its own rating.</text>']
    _panel(s, 24, 96, 450, 180, "Going first or second", START_FIRST,
           ["It went first in 65% of games: it always takes first after winning the toss; opponents did 349 of 477 times.",
            "By coin toss, a randomized comparison: won the toss 60.2%, lost it 42.1%."])
    _panel(s, 500, 96, 436, 180, "Mulligans before the game (four Basics: 59.9% of games)", START_MULL,
           ["The hypergeometric expectation is 60.1%; games with a mulligan won 4.4 points less",
            "(95% CI −1.9 to +10.7); opponents mulligan in 31% of games."])
    _panel(s, 24, 292, 450, 180, "Mega Starmie ex on the board by its own second turn", START_MEGA,
           ["Going second it landed in 90.7% of wins and 65.1% of losses. It never landed in 1 win",
            "and 86 losses; 123 of 482 losses ended without a prize taken."])
    _panel(s, 500, 292, 436, 180, "Win rate by opponent rating (median opponent 651.6)", START_BAND,
           ["Interquartile range of opponents 610–695: the 51.2% is earned against peers;",
            "above 700 it won 44.4% (95% CI 37.7–51.4), 3 of 20 in the 800s."])
    s.append(f'<text x="24" y="{h - 10}" class="ink2" font-size="10">Source: replays and episode list of submission 55558557 (Aug 22–31); first player and mulligans from the engine\'s own logs; zero games were replayed for this figure.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_start_profile.svg", "w").write("\n".join(s))


# ---------------------------------------------------------------------------
# v7 の図番号(出現順)とキャプション。t6_check.py が本文の "Fig. N" と照合する。
#   fig_deck_matrix / fig_rating_timeline はギャラリー不掲載(族内数値 / 旧版)。
# ---------------------------------------------------------------------------
CAPTIONS = [  # Kaggle 本文末尾の「Figure captions」表 = これ(出典と計器の限界はここに置く。表は運営回答で語数外)
    ("fig_decision_flow.svg", 1, "Fig. 1 — How the pilot chooses an action: a greedy evaluator and fourteen human-taught rules propose a move; a 0.6-second engine lookahead may override it; eight one-way gates block the overrides we had seen go wrong. Prior art: search over a hand-written evaluation won every Legends of Code and Magic contest until deep RL took over (Kowalski & Miernik 2023, IEEE CoG); heuristic-guided MCTS led the Hearthstone AI Competition (2018–2020); LLM agents on this game are harness-sensitive (PTCG-Bench, arXiv:2605.29653, 2026)."),
    ("fig_deck_plan.svg", 2, "Fig. 2 — The 60-card list and its plan: the one-energy 120 + 50 attack is 71% of all attacks in the last 1,000 ladder games, the 210 attack is the finisher, four Basics were chosen by measurement, and Deluxe Bomb is the ACE SPEC (a Belt in its place measured −0.57pt, 95% CI −2.82 to +1.68)."),
    ("fig_matchup_profile.svg", 3, "Fig. 3 — Win rate by opponent archetype over the last 1,000 ladder games (n ≥ 55 shown, overall 51.2%)."),
    ("fig_calibration_gap.svg", 4, "Fig. 4 — Self-play overstates win rate by +8 to +62 points depending on who really pilots the opposing deck (July 21 agent, N = 300 per bar). Limits of the instrument built on it: the +2.0pt adoption threshold sits inside the ladder's non-transitivity residual (6.2pp); calibration is validated only in the 700–799 band and anchors on the host's sample pilot; the benches share one process, and the sham control excludes only contamination above 3.68pt."),
    ("fig_prospective.svg", 5, "Fig. 5 — Four submissions, four predictions registered before reading any replay: the calibrated figure fell inside the ladder's confidence interval each time, the self-play figure outside. The discipline is psychology's after its replication crisis (Nosek, Ebersole, DeHaven & Mellor 2018, PNAS 115:2600). The adoption rule was audited too: four independent non-regression gates flagged a zero-effect change as a regression 65.1% of the time; the composite that replaced them has a +2.0pt threshold of only ~1.09σ, so confidence intervals became mandatory."),
    ("fig_search_ablation.svg", 6, "Fig. 6 — The engine-lookahead layer ablated on the calibrated instrument: +13.62pt (95% CI +11.40 to +15.84, N = 3,200 per arm), measured in July before its gates existed; a sham lookahead measured +0.42pt. Our largest negative result, rejecting a general Monte-Carlo rewrite, did not survive re-examination on the same instrument (+2.62pt, CI −0.68 to +5.93)."),
    ("fig_bosslogic_autopsy.svg", 7, "Fig. 7 — The final agent, last 1,000 games: the gates held by construction, one frozen prediction failed (49 of 809 Boss's Orders plays misfired, every one a lookahead override), outside review found the energy-blind knock-out test, and the post-deadline measurement is −3.29pt against the list our discipline would have submitted."),
    ("fig_horizon_uncertainty.svg", 8, "Fig. 8 — Two development lines in one team, ours and Ryohei Hara's, placed their look-ahead in different cells and failed in different cells; both converged on mono-Water independently."),
    ("fig_deck_lineage.svg", 9, "Fig. 9 — From the human-orthodox parent list to the submitted one: twelve cards, each with a measurement or a reason. The Dusknoir engine went against our own pre-run forecast from the coaching canon (−5 to −10 predicted, +14.7 measured). Expert intuition is reliable only with rapid feedback from a regular environment (Kahneman & Klein 2009, American Psychologist 64:515); no one had such feedback about an AI pilot."),
    ("fig_rating_distribution.svg", 10, "Fig. 10 — Final ratings of all 6,807 teams (public leaderboard, Sep 1): the submission's 656.7 sits above the median of 621.5 at rank 2,898; 90% of teams finished below 853.5."),
    ("fig_start_profile.svg", 11, "Fig. 11 — Where the final agent depends on the start of the game, last 1,000 ladder games: 57.7% going first, 40.1% going second, while whoever went first won 58.5%; a mulligan in 59.9% of games, and games with a mulligan won 4.4 points less (95% CI −1.9 to +10.7); Mega Starmie ex on the board by its own second turn in 92% of wins and 74% of losses; 44.4% against opponents above 700. Organizers of AI card-game competitions neutralise first-player advantage by running both seat orders (Kowalski & Miernik 2023); the ladder does not."),
    ("fig_board_t10.png", 12, "Fig. 12 — Turn ten of ladder game 102267456 in the official visualizer, before the agent acts: the opponent's Mega Lucario ex (top) at 90 of 440 HP with Hero's Cape, our Mega Starmie ex (bottom) at 60 HP with one Water, Buddy-Buddy Poffin and Boss's Orders in hand, prizes 4 to 2 against us. Jetting Blow for 120 takes three prizes; the agent played Boss's Orders on the 80-HP Makuhita, and a Mega Lucario ex answered with Aura Jab for 130 either way. Host's visualizer screenshot, used as permitted."),
]

GALLERY_TITLES = {  # Kaggle Media Gallery の画像タイトル(サーバ上限 255 字。出典は短縮形)
    1: "Fig. 1 — How the pilot chooses an action: greedy evaluator + fourteen human-taught rules propose; a 0.6 s engine lookahead may override; eight one-way gates block known-bad overrides. Kowalski & Miernik 2023; Hearthstone AI Competition; PTCG-Bench.",
    2: "Fig. 2 — The 60-card list and its plan: the one-energy 120 + 50 attack is 71% of attacks in the last 1,000 ladder games; the 210 attack is the finisher; four Basics by measurement; Deluxe Bomb is the ACE SPEC (a Belt instead: −0.57pt, CI −2.82 to +1.68).",
    3: "Fig. 3 — Win rate by opponent archetype over the last 1,000 ladder games (n ≥ 55 shown, overall 51.2%).",
    4: "Fig. 4 — Self-play overstates win rate by +8 to +62 points depending on who pilots the opposing deck (July 21 agent, N = 300 per bar). Limits: +2.0pt threshold inside the ladder's 6.2pp non-transitivity; validated only in the 700–799 band.",
    5: "Fig. 5 — Four submissions, four predictions registered before reading any replay: calibrated figure inside the ladder's CI each time, self-play outside (Nosek et al. 2018, PNAS 115:2600). Adoption rule audited: four gates false-alarmed 65.1%.",
    6: "Fig. 6 — The engine-lookahead layer ablated on the calibrated instrument: +13.62pt (95% CI +11.40 to +15.84, N = 3,200 per arm), July, before its gates existed; sham lookahead +0.42pt. A rejected Monte-Carlo rewrite re-measured at +2.62pt.",
    7: "Fig. 7 — The final agent, last 1,000 games: the gates held, one frozen prediction failed (49 of 809 Boss's Orders plays misfired, all lookahead overrides), outside review found the energy-blind knock-out test, and the post-deadline measurement is −3.29pt.",
    8: "Fig. 8 — Two development lines in one team, ours and Ryohei Hara's, placed their look-ahead in different cells and failed in different cells; both converged on mono-Water independently.",
    9: "Fig. 9 — From the human-orthodox parent list to the submitted one: twelve cards, each with a measurement or a reason. The Dusknoir engine went against our own pre-run forecast (−5 to −10 predicted, +14.7 measured); cf. Kahneman & Klein 2009 on intuition.",
    10: "Fig. 10 — Final ratings of all 6,807 teams (public leaderboard, Sep 1): the submission's 656.7 sits above the median of 621.5 at rank 2,898; 90% of teams finished below 853.5.",
    11: "Fig. 11 — Start-of-game dependence, last 1,000 games: 57.7% going first vs 40.1% second (whoever went first won 58.5%); mulligan in 59.9% of games, −4.4pt with CI including zero; Mega Starmie ex out by its own second turn in 92% of wins, 74% of losses.",
    12: "Fig. 12 — Turn ten of ladder game 102267456 in the official visualizer: the opponent's Mega Lucario ex (Hero's Cape) at 90 of 440, our Mega Starmie ex at 60 with one Water, Poffin and Boss's Orders in hand, prizes 4–2 against us.",
}


if __name__ == "__main__":
    fig_deck_matrix()   # 注意: 族内測定の数値(D30-B1)。単体では使わず較正の物語の対比のみ
    fig_rating_timeline()
    fig_prospective()
    fig_calibration_gap()
    fig_search_ablation()
    fig_eviction()
    fig_rating_expenditure()
    fig_horizon_uncertainty()
    fig_bosslogic_autopsy()
    fig_decision_flow()
    fig_deck_plan()
    fig_matchup_profile()
    fig_deck_lineage()          # Fig. 9  (2026-09-09)
    fig_rating_distribution()   # Fig. 10 (2026-09-09)
    fig_start_profile()         # Fig. 11 (2026-09-09)
    print(f"wrote {len(CAPTIONS)} captioned figures (+ 3 uncaptioned) to", OUT)

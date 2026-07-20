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
]


def fig_rating_timeline():
    w, h, lx, by = 640, 330, 60, 270
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
             f'Yellow = deliberate calibration submission (v3, real-ladder probe). '
             f'Same-agent variance on LB is 150-400pt (host thread) — local N=300+ CI '
             f'benches carry more information.</text>')
    s.append("</svg>")
    open(f"{OUT}/fig_rating_timeline.svg", "w").write("\n".join(s))


if __name__ == "__main__":
    fig_deck_matrix()
    fig_rating_timeline()
    print("wrote", OUT + "/fig_deck_matrix.svg", OUT + "/fig_rating_timeline.svg")

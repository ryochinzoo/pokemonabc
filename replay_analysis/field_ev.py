#!/usr/bin/env python3
"""フィールドEV — 「そのデッキは、その帯の顔ぶれに対して何%勝つか」。

デッキ選定の基準を「上位が使っているから」ではなく
**「フィールドに対するEV × シェアの低さ」**に置く(D63)。根拠は SUMI の Archaludonバブル
(Sim discussion/729926): 勝率65%のときシェア0%、フィールドになった瞬間48%→31%。
「**LBで支配的に見えた時点でEVは既に戻り始めている**」。

EV_d(帯) = Σ_i share_i × WR(d vs i)   ※ミラーは0.5として算入、覆えない対面は再正規化

**検算**: 我々(starmie)の予測EVと、我々の実ラダー実測勝率を突き合わせる。
これが合わなければモデルごと捨てる(合わせに行かない)。

汚染規律: セルは `band_meta_census.py` と同じく **distinct 提出数**を併記し、
少数パイロットのセルは EV に使うが**印を付ける**(台帳#11 / D9)。

使い方: python3 replay_analysis/field_ev.py [帯の下限 既定800]
"""
import math
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import band_meta_census as B  # noqa: E402

MIN_SUBS_TRUST = 25          # 両側がこれ以上なら「デッキ級」


def wilson(k, n):
    if n == 0:
        return (0.0, 100.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def main(lo=800, hi=1100):
    games = B.collect()
    for sides in games.values():
        for s in sides:
            s["arch"] = B.classify_b(s["deck"]) or B.classify_a(s["deck"])

    # --- フィールド構成(我々自身は除外、対象帯のみ) ---
    field = Counter()
    for sides in games.values():
        for s in sides:
            if s["sub"] in B.OUR_SUBS or s["score"] is None:
                continue
            if lo <= s["score"] < hi:
                field[s["arch"] or "other"] += 1
    tot = sum(field.values())
    print(f"# フィールドEV  対象帯 {lo}-{hi-1}  (側 n={tot}、我々自身は除外)\n")
    print("## フィールド構成")
    for a, c in field.most_common(9):
        print(f"  {a:<14}{100*c/tot:5.1f}%  ({c})")

    # --- 対面行列(同帯対戦のみ) ---
    mat = defaultdict(lambda: [0, 0, set(), set()])
    for sides in games.values():
        a, b = sides
        if a["score"] is None or b["score"] is None:
            continue
        if not (lo <= a["score"] < hi and lo <= b["score"] < hi):
            continue
        if B.band(a["score"]) != B.band(b["score"]):
            continue
        if not a["arch"] or not b["arch"] or a["arch"] == b["arch"]:
            continue
        win = a if a["reward"] == 1 else (b if b["reward"] == 1 else None)
        if win is None:
            continue
        lose = b if win is a else a
        for key, i, me, opp in (((win["arch"], lose["arch"]), 0, win, lose),
                                ((lose["arch"], win["arch"]), 1, lose, win)):
            mat[key][i] += 1
            mat[key][2].add(me["sub"])
            mat[key][3].add(opp["sub"])

    archs = [a for a, c in field.most_common() if c / tot >= 0.03 and a != "other"]
    # **落としたセルを必ず開示する**。2026-08-03、初版は N<15 のセルを黙って除外し、
    # tarountula の負け対面2つ(grimmsnarl/lucario)だけが落ちて EV が 54%→62% に水増しされた。
    # 「静かな打ち切りは『全部覆った』ように読める」(Workflow の no-silent-caps と同じ穴)。
    MIN_N = 10
    print(f"\n## フィールドEV(対象アーキタイプ {len(archs)}種、シェア3%以上、セルは N>={MIN_N})")
    print(f"  {'デッキ':<14}{'EV':>7}{'覆域':>7}{'内訳(相手: 勝率×シェア%、†=どちらかが{MIN_SUBS_TRUST}体未満)'}")
    out = []
    for d in archs:
        num = den = 0.0
        parts, dropped = [], []
        for o in archs:
            sh = field[o] / tot
            if o == d:
                num += sh * 0.5
                den += sh
                parts.append(f"{o[:5]} 50.0*{100*sh:.0f}(ミラー)")
                continue
            w, l, sx, sy = mat.get((d, o), [0, 0, set(), set()])
            if w + l < MIN_N:
                dropped.append(f"{o}({100*sh:.0f}%, N={w+l})")
                continue
            wr = w / (w + l)
            thin = min(len(sx), len(sy)) < MIN_SUBS_TRUST
            num += sh * wr
            den += sh
            parts.append(f"{o[:5]} {100*wr:.0f}{'†' if thin else ''}*{100*sh:.0f}")
        if den == 0:
            continue
        out.append((num / den, den, d, parts, dropped))
    for ev, den, d, parts, dropped in sorted(out, reverse=True):
        print(f"  {d:<14}{100*ev:6.1f}%{100*den:6.1f}%  " + " / ".join(parts))
        if dropped:
            print(f"  {'':<14}{'':>7}{'':>7}  ↑ **標本不足で除外**: " + ", ".join(dropped)
                  + "  ← EVはこの分だけ偏りうる")

    # --- 検算: 我々の予測 vs 実測 ---
    print("\n## 検算 — starmie(我々)の予測EV vs 実ラダー実測")
    num = den = 0.0
    detail = []
    for o in archs:
        sh = field[o] / tot
        w, l, sx, sy = mat.get(("starmie", o), [0, 0, set(), set()])
        if w + l < 8:
            continue
        wr = w / (w + l)
        num += sh * wr
        den += sh
        detail.append(f"vs {o} {100*wr:.0f}% (N={w+l})")
    pred = 100 * num / den if den else float("nan")
    ow = on = 0
    for sides in games.values():
        for i, s in enumerate(sides):
            o = sides[1 - i]
            if s["sub"] not in B.OUR_SUBS or o["sub"] in B.OUR_SUBS:
                continue
            if s["score"] is None or not (lo <= s["score"] < hi):
                continue
            on += 1
            ow += (s["reward"] == 1)
    clo, chi = wilson(ow, on)
    print(f"  予測EV {pred:.1f}%(覆域{100*den:.0f}%) — {' / '.join(detail)}")
    print(f"  実測   {100*ow/max(1,on):.1f}%  ({ow}/{on}、95%CI[{clo:.1f},{chi:.1f}])")
    ok = clo <= pred <= chi
    print(f"  → 予測は実測CI{'内' if ok else '外'} = モデルは{'棄却されない' if ok else '棄却'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 800)

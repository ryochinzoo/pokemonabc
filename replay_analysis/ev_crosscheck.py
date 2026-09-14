#!/usr/bin/env python3
"""EV検算の拡張 — C3(「モデルは検算に通った」)の k点交差検証。

前任者の検算は **1点**(starmie 予測41.5 vs 実測41.1、実測CI±11pt)だった。
本スクリプトは field_ev.py と同じモデル EV_d = Σ share_i × WR(d vs i) を
**全アーキタイプ**に適用し、census の実測勝率と k点で突き合わせる。さらに:

  1. **循環度の開示**: 旧検算の対面行列は我々自身の試合を含んでいた。
     starmie 行に占める我々の試合の割合を出す(高ければ旧検算はほぼ同語反復)。
  2. **LOTO(leave-one-team-out)**: アーキタイプ級の勝率で「見たことのない
     1チーム」の成績を予測できるか。残差の過分散 φ で操縦者の均質性も測れる
     (φ≈1 = デッキがチームを決める / φ≫1 = 操縦者で割れる)。

単位規律(引き継ぎ§3.1): 主語が「チーム」の行は distinct submissionId、
「遭遇」の行は側で数える。各表に単位・N・CI・distinct を明記。
落としたセルは share つきで開示する。

使い方: python3 replay_analysis/ev_crosscheck.py [帯下限 800] [帯上限 1100]
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import band_meta_census as B  # noqa: E402

MIN_CELL_N = 10          # field_ev.py と同じ
MIN_TEAM_GAMES = 15      # LOTO の対象チーム(同帯・非ミラー・既知対面の試合数)


def main(lo=800, hi=1100):
    games = B.collect()
    for sides in games.values():
        for s in sides:
            s["arch"] = B.classify_b(s["deck"]) or B.classify_a(s["deck"])

    # ---- 0. 標本フレームの開示 ----
    # 我々の試合宇宙は「追跡72体+我々」の対戦ログ = 追跡体が過剰標本。
    # 追跡体は opponents.json をスコア降順に取った = 高スコア側に偏る。
    n_ep = len(games)
    print(f"# EV検算の拡張(k点) 帯 {lo}-{hi-1}  総エピソード {n_ep}")
    print("""
## 0. 標本フレーム(先に開示)
  - 宇宙 = ladder_scout/decks.jsonl(追跡72体の近傍) + 我々の全譜。
    追跡体はスコア降順サンプル = 各アーキタイプの**上澄みが過剰標本**。
  - 対面セルの「max1体シェア」= そのセルの遭遇のうち最多1提出が占める率。
    高いセルは「デッキの勝率」ではなく「その提出の勝率」(台帳#11)。""")

    # ---- 1. フィールド構成(側=遭遇単位、我々除外) ----
    field = defaultdict(int)
    field_subs = defaultdict(set)
    for sides in games.values():
        for s in sides:
            if s["sub"] in B.OUR_SUBS or s["score"] is None:
                continue
            if lo <= s["score"] < hi:
                field[s["arch"] or "other"] += 1
                field_subs[s["arch"] or "other"].add(s["sub"])
    tot = sum(field.values())
    print(f"\n## 1. フィールド構成(単位=側/遭遇、我々除外、n={tot})")
    for a in sorted(field, key=lambda x: -field[x]):
        print(f"  {a:<12}{100*field[a]/tot:5.1f}%  (側{field[a]}, distinct提出 {len(field_subs[a])})")

    # ---- 対面行列(同帯・非ミラー) ----
    # field-only 版(我々の試合を除外)と、旧 field_ev 版(込み)の両方を持つ。
    def build_matrix(include_ours):
        mat = defaultdict(lambda: [0, 0])          # (d,o) -> [w,l]  d側から見て
        per_team = defaultdict(lambda: [0, 0])     # (d,o,sub) -> [w,l]
        subs_in = defaultdict(lambda: (set(), set()))
        ours_in = defaultdict(int)                 # (d,o) -> 我々が絡む遭遇数
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
            involves_ours = a["sub"] in B.OUR_SUBS or b["sub"] in B.OUR_SUBS
            if not include_ours and involves_ours:
                continue
            for me, opp in ((a, b), (b, a)):
                if me["reward"] not in (1, -1) and opp["reward"] not in (1, -1):
                    continue
                win = 1 if me["reward"] == 1 else (0 if opp["reward"] == 1 else None)
                if win is None:
                    continue
                key = (me["arch"], opp["arch"])
                mat[key][0 if win else 1] += 1
                per_team[(me["arch"], opp["arch"], me["sub"])][0 if win else 1] += 1
                subs_in[key][0].add(me["sub"])
                subs_in[key][1].add(opp["sub"])
                if involves_ours:
                    ours_in[key] += 1
        return mat, per_team, subs_in, ours_in

    mat_f, per_team_f, subs_f, _ = build_matrix(include_ours=False)
    mat_o, _, _, ours_o = build_matrix(include_ours=True)

    # ---- 2. k点検算(遭遇単位・非ミラー・field-only) ----
    archs = [a for a in sorted(field, key=lambda x: -field[x])
             if a != "other" and field[a] / tot >= 0.02]
    print(f"""
## 2. k点検算 — 予測EV(非ミラー) vs 実測勝率(非ミラー)
  単位=遭遇(側)。対面行列・実測とも同帯対戦・両者{lo}-{hi-1}・我々の試合は除外。
  予測 = Σ share'_o × WR(d vs o)(share' は覆えた対面で再正規化、セルは N>={MIN_CELL_N})
  実測 = d側の全既知対面(落としたセル含む)での勝ち/遭遇。**同じ試合集合を使うため
  この差は『遭遇分布がシェア分布とどれだけ違うか+落としたセル』を測る整合性検査であり、
  真の予測力検査は §4 の LOTO。**""")
    print(f"  {'arch':<12}{'share':>6}{'予測EV':>8}{'自込予':>7}{'覆域':>6}{'実測':>7}{'95%CI':>15}"
          f"{'N':>6}{'distinct':>9}{'max1体':>7}{'|Δ|EV':>7}{'|Δ|50':>7}  勝者")
    k_points = []
    for d in archs:
        preds = {}
        drop_note = []
        for tag, m in (("field", mat_f), ("incl", mat_o)):
            num = den = 0.0
            dropped = []
            for o in archs:
                if o == d:
                    continue
                sh = field[o] / tot
                w, l = m.get((d, o), [0, 0])
                if w + l < MIN_CELL_N:
                    dropped.append(f"{o}(share{100*sh:.0f}%,N={w+l})")
                    continue
                num += sh * w / (w + l)
                den += sh
            preds[tag] = (100 * num / den if den else None, den)
            if tag == "field":
                drop_note = dropped
        # 実測: d側の非ミラー既知対面(セル落ち含む。切り捨て無し=全セル算入)
        W = sum(mat_f.get((d, o), [0, 0])[0] for o in archs if o != d)
        L = sum(mat_f.get((d, o), [0, 0])[1] for o in archs if o != d)
        N = W + L
        pred, den = preds["field"]
        pred_i, _ = preds["incl"]
        if N == 0 or pred is None:
            print(f"  {d:<12}  — 標本ゼロで判定不能")
            continue
        act = 100 * W / N
        clo, chi = B.wilson(W, N)
        dsubs = set()
        maxteam = 0
        for (dd, oo, sub), (w, l) in per_team_f.items():
            if dd == d and oo in archs:
                dsubs.add(sub)
                maxteam = max(maxteam, w + l)
        inside = clo <= pred <= chi
        # 零情報モデル(常に50%)との比較 — 赤チームD指摘: 零情報でも旧検算は通る
        e_ev, e_50 = abs(pred - act), abs(50.0 - act)
        winner = "EV" if e_ev < e_50 else ("50" if e_50 < e_ev else "同点")
        k_points.append((d, pred, act, clo, chi, N, inside, e_ev, e_50, winner))
        print(f"  {d:<12}{100*field[d]/tot:5.1f}%{pred:7.1f}%{pred_i:6.1f}%{100*den:5.0f}%"
              f"{act:6.1f}%  [{clo:5.1f},{chi:5.1f}]{N:>6}{len(dsubs):>9}{100*maxteam/N:6.1f}%"
              f"{e_ev:6.1f}{e_50:7.1f}   {winner}{'' if inside else '  **CI外**'}")
        if drop_note:
            print(f"  {'':<12}      ↑ 落としたセル(field版): " + ", ".join(drop_note))
    n_in = sum(1 for p in k_points if p[6])
    ev_w = sum(1 for p in k_points if p[9] == "EV")
    z_w = sum(1 for p in k_points if p[9] == "50")
    losers = [p[0] for p in k_points if p[9] == "50"]
    print(f"\n  → CI内 {n_in}/{len(k_points)} 点(弱い検査)。"
          f"**対 零情報モデル: EVの勝ち {ev_w} / 負け {z_w}"
          + (f"(負けた点: {', '.join(losers)})" if losers else "") + "**")
    print("  ※『自込予』= 我々のエピソードを行列に含めた旧 field_ev 方式の予測。"
          "starmie 行以外は field 版と一致するはず(我々は starmie のため)。")

    # ---- 3. 旧検算(41.5 vs 41.1)の循環度 ----
    print("""
## 3. 旧検算の循環度 — starmie 行に我々の試合は何%入っていたか
  field_ev.py の対面行列は我々の試合を除外していない。予測に使う行列と
  実測(我々の勝率)が同じ試合を含むなら、一致は予測力の証拠にならない。""")
    for o in archs:
        if o == "starmie":
            continue
        w, l = mat_o.get(("starmie", o), [0, 0])
        n = w + l
        if n == 0:
            continue
        ours = ours_o.get(("starmie", o), 0)
        print(f"  starmie vs {o:<12} N={n:<5} うち我々が絡む {ours:<5}"
              f"({100*ours/n:5.1f}%)")

    # ---- 4. LOTO — チーム単位の out-of-sample 予測 ----
    print(f"""
## 4. LOTO(leave-one-team-out) — 真の予測力検査(単位=チーム=distinct submissionId)
  対象: 同帯・非ミラー・既知対面の試合が {MIN_TEAM_GAMES} 以上あるチーム。
  そのチームの試合を行列から抜いて WR_-t(d vs o) を作り、そのチームの
  対戦履歴に沿って期待勝数 E を出し、実勝数 W と比べる。
  residual = (W-E)/n。φ = Σ(W-E)²/Σp(1-p)(≈1なら二項ノイズのみ=操縦者は均質)。""")
    team_games = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # sub -> o -> [w,l]
    arch_of_team = {}
    for (d, o, sub), (w, l) in per_team_f.items():
        if d not in archs or o not in archs:
            continue
        team_games[sub][o][0] += w
        team_games[sub][o][1] += l
        arch_of_team[sub] = d
    rows = defaultdict(list)
    for sub, cells in team_games.items():
        d = arch_of_team[sub]
        n_t = sum(w + l for w, l in cells.values())
        if n_t < MIN_TEAM_GAMES:
            continue
        E = var = brier = 0.0
        W = n_used = 0
        for o, (w, l) in cells.items():
            cw, cl = mat_f.get((d, o), [0, 0])
            rw, rl = cw - w, cl - l          # 自分を抜く
            if rw + rl < MIN_CELL_N:
                continue
            p = rw / (rw + rl)
            E += (w + l) * p
            var += (w + l) * p * (1 - p)
            brier += w * (1 - p) ** 2 + l * p * p     # ゲームレベル Brier(モデル)
            W += w
            n_used += w + l
        if n_used < MIN_TEAM_GAMES:
            continue
        rows[d].append((sub, n_used, W, E, var, brier))
    print(f"  {'arch':<12}{'チーム数':>7}{'総戦':>6}{'平均残差':>9}{'95%CI':>15}"
          f"{'φ':>6}{'Brier':>7}{'vs50':>6}{'  幅(最小..最大)'}")
    import math
    for d in archs:
        rs = rows.get(d, [])
        if not rs:
            print(f"  {d:<12}      0  — {MIN_TEAM_GAMES}戦以上のチームが無い(標本不足)")
            continue
        sumWE = sum(w - e for _, n, w, e, v, br in rs)
        sumN = sum(n for _, n, w, e, v, br in rs)
        sumV = sum(v for _, n, w, e, v, br in rs)
        sumB = sum(br for _, n, w, e, v, br in rs)
        mean_res = 100 * sumWE / sumN
        se = 100 * math.sqrt(sumV) / sumN
        phi = sum((w - e) ** 2 / v for _, n, w, e, v, br in rs) / len(rs) if sumV else float("nan")
        per = sorted(100 * (w - e) / n for _, n, w, e, v, br in rs)
        # 零情報(常に50%)のBrierは0.25。skill = 1 - B_model/0.25
        bm = sumB / sumN
        print(f"  {d:<12}{len(rs):>7}{sumN:>6}{mean_res:+8.1f}pt"
              f"  [{mean_res-1.96*se:+6.1f},{mean_res+1.96*se:+6.1f}]{phi:6.2f}"
              f"{bm:7.3f}{'勝' if bm < 0.25 else '負':>5}"
              f"   {per[0]:+.0f}pt .. {per[-1]:+.0f}pt")
    print("  ※Brier: ゲームレベル平均二乗誤差。零情報(常に50%)=0.250。"
          "モデルが下回れば held-out チームに対して情報を持つ。")
    print("""
  読み方: 平均残差のCIが0を跨げば「アーキタイプ級WRで未知チームを予測できる」。
  φ が 1 を大きく超えるアーキタイプは、同じデッキ看板でも操縦者で成績が割れている。""")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 800,
         int(sys.argv[2]) if len(sys.argv) > 2 else 1100)

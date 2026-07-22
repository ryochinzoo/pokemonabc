#!/usr/bin/env python3
"""CEW = 較正済み遭遇加重合成指標（decisions.md D29 / D31）。

提出可否の主指標。族外(較正済み)ゲージの勝率を、実ラダーの遭遇率で加重した1指標。
手計算だと重み一つの付け忘れで採否が反転しうる(D31は+2.18pt vs 閾値+2.0ptの僅差)ため、
ここに固定して再現可能にする。

    python3 verification/cew.py --lucario 48.9 --archaludon 21.4 --abomasnow 32.3
    # → CEW と 基準比、採用/棄却の判定を出す

**重みは「現在の帯の実遭遇分布」に紐づく。帯が変われば再計算する**(playbook §2)。
再計算せずに使い続けると「較正が古いまま最適化を続ける」事故になる(D26で実際に発生)。
"""
import argparse
import datetime as _dt

# --- 重み表（算出日・N・出典を必ず残す。ここが古びると全判定が狂う） ---
# 2026-07-22 D35改訂(ゆうじ承認): ①Dragapult第4成分を追加(カバレッジ42.5%へ)
# ②Archaludon成分の参照エージェントは tomato_archaludon_agent.py を優先
#   (実ラダー相手の正体=tomato系譜、deck 60/60一致×2。steelは副参照として保持。
#    較正は三者一致: steel21.4 ≈ tomato22.0 ≈ 実ラダー25.0)
WEIGHTS_DATE = _dt.date(2026, 7, 22)
WEIGHTS_SOURCE = "D35 / data.md 2026-07-22 (実ラダー2提出プール N=120)"
WEIGHTS = {          # 較正済みゲージが存在する42.5%(51/120)の遭遇を再正規化した重み
    "lucario": 0.490,     # 公式Lucario agent(遭遇25/120)
    "archaludon": 0.353,  # tomato Archaludon優先・steel副参照(遭遇18/120)
    "dragapult": 0.098,   # 公式Dragapult agent(遭遇5/120)
    "abomasnow": 0.059,   # 公式Abomasnow agent(遭遇3/120)
}
BASELINE = 41.03     # D38 (2026-07-23): 墓場バッチ(i) 4反復×Neyman N=800 の平均(計3,200戦)。
                     # プールSE 0.82pt。旧41.51(成分N非均一)から実質不変だが測定として上位。
                     # 成分N: Lucario1712 / tomato1024 / Dragapult272 / Abomasnow192
ADOPT_THRESHOLD = 2.0  # 基準比 +2.0pt 以上で採用検討。
                     # D38前提: 測定は Neyman配分 合計N=3,200 (1712/1024/272/192)。
                     # この構成での実効: 誤採用率4.2% / 真+2.5ptへの検出力67%
                     # (基準線の系統誤差0.82ptが床。検定力計算=data.md 2026-07-23 D38節)。
                     # 一様N=800/セルは同じ3,200戦で誤採用6.4%に劣化するので使わない。
                     # CIの計算は cew_stats.py。
STALE_DAYS = 7       # この日数を超えたら再検死の警告


def cew(winrates: dict) -> float:
    total_w = sum(WEIGHTS[k] for k in winrates if k in WEIGHTS)
    if total_w == 0:
        raise ValueError("既知のゲージ名(lucario/archaludon/abomasnow)が1つも無い")
    # 一部のゲージだけ渡された場合も、渡された分の重みで正規化して合成
    return sum(WEIGHTS[k] * v for k, v in winrates.items() if k in WEIGHTS) / total_w


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lucario", type=float, help="vs 公式Lucario の勝率(%%)")
    ap.add_argument("--archaludon", type=float,
                    help="vs tomato Archaludon(優先)/steel(副) の勝率(%%)")
    ap.add_argument("--dragapult", type=float, help="vs 公式Dragapult の勝率(%%)")
    ap.add_argument("--abomasnow", type=float, help="vs 公式Abomasnow の勝率(%%)")
    ap.add_argument("--baseline", type=float, default=BASELINE,
                    help=f"比較する基準線(既定 {BASELINE})")
    args = ap.parse_args()

    wr = {k: v for k, v in vars(args).items()
          if k in WEIGHTS and v is not None}
    if not wr:
        ap.error("少なくとも1つのゲージ勝率を渡すこと")

    age = (_dt.date.today() - WEIGHTS_DATE).days
    print(f"重み算出日: {WEIGHTS_DATE} ({age}日前)  出典: {WEIGHTS_SOURCE}")
    if age > STALE_DAYS:
        print(f"⚠ 重みが{age}日前のもの。実ラダー遭遇分布を再検死してから使うこと"
              f"(playbook §2、replay_analysis)。")
    missing = [k for k in WEIGHTS if k not in wr]
    if missing:
        print(f"※ 未指定ゲージ {missing} は除外し、残りの重みで正規化した")

    val = cew(wr)
    diff = val - args.baseline
    print(f"CEW = {val:.2f}%   基準 {args.baseline:.2f}%   差 {diff:+.2f}pt")
    verdict = "採用検討(要 独立追試)" if diff >= ADOPT_THRESHOLD else "棄却域"
    print(f"判定: {verdict}  (採用閾値 +{ADOPT_THRESHOLD}pt)")


if __name__ == "__main__":
    main()

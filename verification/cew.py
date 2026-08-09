#!/usr/bin/env python3
"""CEW = 較正済み遭遇加重合成指標（decisions.md D29 / D31）。

提出可否の主指標。族外(較正済み)ゲージの勝率を、実ラダーの遭遇率で加重した1指標。
手計算だと重み一つの付け忘れで採否が反転しうる(D31は+2.18pt vs 閾値+2.0ptの僅差)ため、
ここに固定して再現可能にする。

    python3 verification/cew.py --alakazam 92.25 --grimmsnarl 39.0 \
                                --crustle 98.25 --lucario 17.0 --archaludon 12.25
    # → CEW と 基準比、採用/棄却の判定を出す

**重みは「現在の帯の実遭遇分布」に紐づく。帯が変われば再計算する**(playbook §2)。
再計算せずに使い続けると「較正が古いまま最適化を続ける」事故になる(D26で実際に発生)。
"""
import argparse
import datetime as _dt

# --- 重み表（算出日・N・出典を必ず残す。ここが古びると全判定が狂う） ---
#
# ★2026-08-09 再導出 (T3 = 義務・承認不要)。**D62(2026-08-02)で決定済みだったが未実装**
#   だったものを実行した(decisions.md:1546「cew(棄却済み重みのまま=D62決定の未実装)」)。
#   出典: data.md:3995-3998「800-1099帯のフィールド構成」側 n=6,341、我々自身は除外。
#   斥候72体 / 4,263エピソード。独立分類器2本の一致率 97.0%。
#
#   旧重み(2026-07-26)がどれだけ狂っていたか — 帯が動いた結果:
#     lucario    旧45.1% / 実シェア13.2%  = 3.4倍に過大
#     archaludon 旧33.8% / 実シェア10.7%  = 3.2倍に過大
#     dragapult  旧15.5% / 実シェア 2.1%  = 7.4倍に過大
#     abomasnow  旧 5.6% / **800-1099帯の census に出現しない** = 56倍に過大
#   逆に、実シェア最大の alakazam(29.2%) と crustle(13.5%) が**重み0で入っていなかった**。
#   これが D62 の χ²=37.68 の中身であり、「層Bの受け皿が無い」の正体。
#
#   ※初版(同日)は「grimmsnarl(19.3%)は族外ゲージが存在しない(D64)ので判定に入れない」と
#     書いていた。**その日のうちに誤りと判明**したので下の第2版で追加した。上書きせず残す。
WEIGHTS_DATE = _dt.date(2026, 8, 9)
WEIGHTS_SOURCE = ("T3再較正 2026-08-09 / data.md:3995-3998 800-1099帯フィールド構成 "
                  "(側 n=6,341、自チーム除外) / D62決定の実装")
COVERAGE_PCT = 85.9  # 較正済み族外ゲージが覆う帯シェア(29.2+19.3+13.5+13.2+10.7)
WEIGHTS = {          # 覆域 85.9% を再正規化した重み
    "alakazam": 0.3399,    # share 29.2% — reference/alakazam_ryota_agent.py + decks/ryota_alakazam_2026-07-05.csv
    "grimmsnarl": 0.2247,  # share 19.3% — reference/tetsutani_grimmsnarl_agent.py(2026-08-09 新設)
    "crustle": 0.1572,     # share 13.5% — reference/soutasakurai_crustle_agent.py + decks/soutasakurai_crustle_2026-08-04.csv
    "lucario": 0.1537,     # share 13.2% — reference/makthanithin_lucario_agent.py(較正済み)
                           #   ※ official_lucario_agent.py は +45pt甘いので**使わない**(D61/2026-08-05)
    "archaludon": 0.1246,  # share 10.7% — reference/tomato_archaludon_agent.py(steelは副参照・直列必須)
}
# ★2026-08-09 第2版: オーロンゲを追加して覆域 66.6% → 85.9%。
#   D64 は「Grimmsnarl の族外ゲージは公開コードから構築不能」で正式クローズしていたが、
#   これは誤りだった。公開ノートブック内に **base64 で畳まれた実装**があり、
#   分類器(`def agent` / `%%writefile` を探す)にも「実行して数える」方式にも映らなかった。
#   実測: pilotfix vs 族外オーロンゲ = **39.0% [32.5, 45.9] (N=200, CRASH=0)**。
#   族内ゲージの 43.0% [36.3,49.9] とは差 −4.0pt で CI が大きく重なり、
#   **この対面では族内の過大評価は検出されなかった**(Lucario +45pt / Alakazam +44pt とは異なる)。
BASELINE = 59.70     # ★実ラダーに現在載っている腕 = pilotfix(main.py 3f55780b / deck.csv a246be4f)。
                     # 5面: alakazam 92.25 / grimmsnarl 39.0 / crustle 98.25 / lucario 17.0 / archaludon 12.25。
                     # 合成SE 0.971pt(族外4面 N=400/セル、オーロンゲ N=200)。
                     # **4面時代の 65.70% から −6.00pt** — 2番目に大きい対面を見ていなかったぶん、
                     # 我々は自分の実力を約6pt 高く見積もっていた。
                     # ⚠ **オーロンゲのセルはまだ単一測定(N=200)**。他4面は独立2反復の合算。
                     #   基準線は複数反復で置く規律に照らすと、このセルは第2反復が要る。
                     # 以下は4面時代(2026-08-09 第1版)の記録。上書きせず残す:
                     # **独立2回の合算 N=400/セル**: 92.25 / 98.25 / 17.0 / 12.25 → 4面 65.70。
                     #   反復1 (2026-08-06掃引) 94.0/97.5/19.0/12.5 → CEW 66.75
                     #   反復2 (2026-08-09掃引) 90.5/99.0/15.0/12.0 → CEW 64.64
                     #   実測SD 1.49pt vs 理論SE 1.06pt = 1.40倍。過分散 χ²(1)=1.95 は
                     #   臨界値3.841未満だが **df=1 は検出力が低い**ので「過分散なし」ではなく
                     #   「検出できず」と読むこと。
                     # ⚠ 初版は反復1だけを見て 66.75 に置いていた。**単一測定を基準線にすると
                     #   採用ゲートが約1pt ずれる。** 基準線は必ず複数反復の合算で置く。
                     # 参考(いずれも反復1のみ): P9素 64.81 / v2(ミュウツー全抜き) 64.05。
                     # 旧BASELINE 43.13 は旧ゲージ集合のもので、新指標とは**別物・比較不能**。
ADOPT_THRESHOLD = 2.0  # 基準比 +2.0pt 以上で採用検討(閾値自体は D29 のまま据え置き)。
                     # ⚠ **下のNeyman配分は4面時代のもので、5面には未更新**。
                     #   オーロンゲ(重み0.2247・p≈0.39=最大分散)が入ったので再導出が要る。
                     #   実測 σ から見て、オーロンゲには相当なNが割り当たるはず。
                     # ★4面時代のNeyman配分(2026-08-09第1版、σ は pilotfix セル実測から):
                     #   合計N=3,200 = alakazam 1248 / crustle 380 / lucario 934 / archaludon 638
                     #   (全セル偶数 — run_series が i%2 で席を入れ替えるため)
                     #   腕あたり合成SE 0.471pt / 頭対頭2腕差のSE 0.667pt
                     #   **80%検出力のMDE = 1.87pt**(旧設計の族外4面 N=1,200/腕 では 2.67pt)
                     #   → 総CPUを増やさずに MDE が 30% 改善する。配分が実フィールドと
                     #     揃っていなかったぶんが、そのまま検出力の損失だった。
                     # CIの計算は cew_stats.py。
STALE_DAYS = 7       # この日数を超えたら再検死の警告


def cew(winrates: dict) -> float:
    total_w = sum(WEIGHTS[k] for k in winrates if k in WEIGHTS)
    if total_w == 0:
        raise ValueError(f"既知のゲージ名({'/'.join(WEIGHTS)})が1つも無い")
    # 一部のゲージだけ渡された場合も、渡された分の重みで正規化して合成
    return sum(WEIGHTS[k] * v for k, v in winrates.items() if k in WEIGHTS) / total_w


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alakazam", type=float, help="vs ryota Alakazam の勝率(%%)  重み34.0%%")
    ap.add_argument("--grimmsnarl", type=float, help="vs tetsutani Grimmsnarl の勝率(%%)  重み22.5%%")
    ap.add_argument("--crustle", type=float, help="vs soutasakurai Crustle の勝率(%%)  重み15.7%%")
    ap.add_argument("--lucario", type=float,
                    help="vs **makthanithin** Lucario の勝率(%%)  重み15.4%%"
                         "（公式Lucarioは+45pt甘いので使わない）")
    ap.add_argument("--archaludon", type=float,
                    help="vs tomato Archaludon(優先)/steel(副) の勝率(%%)  重み12.5%%")
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

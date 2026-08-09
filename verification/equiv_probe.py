"""決定レベルの等価性プローブ（勝率ではなく1手ずつ突き合わせる）。

同一の Observation を「対象の実装」と「対照の実装」の両方の `_v1_decide` に食わせ、
返り値が一致するかを数える。

**純関数層の対照はこれを既定にする**（2026-08-08 に制定。playbook §2 の
「デッキA/Bは150戦〜の直接対決」はデッキ差分の話で、コード差分の等価性はこちらが正しい）。

理由（2026-08-07 の実測）:
- 自己対戦で対照実験を組むと**両側が探索（実時間予算 0.6 秒）を回す**ため、
  外部ゲージ相手の数十倍かかる。400 戦で 3 時間 26 分走って未完了だった。
- 同じことを決定レベルで突き合わせたら**数分**で済み、しかも
  「勝率が 50% だった」より強い証拠（**同一性そのもの**）が出る。

読み方:
- 全トグル OFF なら **100% 一致**でなければならない（リファクタ無罪の直接証明）。
  1 件でも不一致なら、それは「効果」ではなく**混入**である。
- 全トグル ON の不一致率 = 介入が実際に何手変えたか（発火の決定レベル測定）。

**この道具の射程（誇張しないこと）**:
- 比較するのは `_v1_decide`（純関数層）**だけ**。探索層 `_search_decide` の上書きは見ない。
- 数える「決定」は**探索のロールアウト内の仮想局面が大半**で、実局面ではない。
  等価性の証明には十分（どんな状態分布でも同一なら同一）だが、
  **不一致率を「実戦で何%変わる」と読んではいけない**。
- 層S（スクリーニング／計器監査）。効果量の判定・ゲート充足の宣言・記事本文に使わない。

使い方（cwd = 比較対象のデッキディレクトリ）:

    cd src/input/datasets/decks/deckswap-tarountula-v2
    python3 ../../../../../verification/equiv_probe.py \\
        --control ../deckswap-v2-control/main.py --games 12

    # 介入 ON/OFF を切り替えるときは env を直書きする（`env $var` は zsh で無音失敗する）
    V4_NO_TOOLFIX=1 V4_NO_COSTFIX=1 V4_NO_TOOLVETO=1 python3 .../equiv_probe.py --control ...
"""
import argparse
import importlib.util
import os
import random
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _effective_env() -> dict:
    """agent が読む環境変数を全数拾う。ドライバの誤設定をログから検出できるようにする。

    2026-08-07 の事故: main.py は 7 つ読むのに 3 つしか潰しておらず、
    探索無効フラグが漏れて VETO が no-op になったのにログは正常に見えた。
    """
    return {k: v for k, v in sorted(os.environ.items()) if k.startswith(("V2_", "V3_", "V4_"))}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--control", required=True,
                   help="対照実装の main.py へのパス（cwd からの相対でよい）")
    p.add_argument("--games", type=int, default=12, help="自己対戦の試合数（既定 12）")
    p.add_argument("--seed", type=int, default=None,
                   help="Python 側 random のシード。エンジン内部の乱数までは固定できない点に注意")
    p.add_argument("--examples", type=int, default=8, help="表示する不一致の実例数")
    args = p.parse_args()

    if not os.path.exists("main.py") or not os.path.exists("deck.csv"):
        print("ERROR: cwd に main.py / deck.csv がありません。デッキディレクトリで実行してください。",
              file=sys.stderr)
        return 2
    if not os.path.exists(args.control):
        print(f"ERROR: 対照が見つかりません: {args.control}", file=sys.stderr)
        return 2

    sys.path.insert(0, _HERE)
    sys.path.insert(0, os.getcwd())

    import selfplay  # noqa: E402  （verification/ から）

    NEW = _load("probe_target", "main.py")
    CTRL = _load("probe_control", os.path.abspath(args.control))

    if args.seed is not None:
        random.seed(args.seed)

    stat: Counter = Counter()
    diffs: list = []
    _orig = NEW._v1_decide

    def spy(obs):
        a = _orig(obs)
        try:
            b = CTRL._v1_decide(obs)
        except Exception:  # 対照が落ちたら記録して続行（対象の挙動は変えない）
            stat["ctrl_error"] += 1
            return a
        stat["total"] += 1
        if list(a) == list(b):
            stat["same"] += 1
        else:
            stat["diff"] += 1
            try:
                sel = obs.select
                kind = f"type={int(sel.type)} ctx={sel.context}"
                oa = sel.option[a[0]] if a else None
                ob = sel.option[b[0]] if b else None
                stat[f"diff:{(kind, int(oa.type) if oa else None, int(ob.type) if ob else None)}"] += 1
                if len(diffs) < args.examples:
                    diffs.append((kind, list(a), list(b)))
            except Exception:
                pass
        return a

    NEW._v1_decide = spy

    print("### 層S（スクリーニング／計器監査） — 引用禁止。"
          "効果量の判定・ゲート充足の宣言・記事本文に使わないこと。")
    print(f"対象   : {os.path.abspath('main.py')}")
    print(f"対照   : {os.path.abspath(args.control)}")
    print(f"デッキ : {os.path.abspath('deck.csv')}（両側で共有）")
    print(f"試合数 : {args.games}   seed={args.seed}")
    print(f"実効env: {_effective_env() or '(V2_/V3_/V4_ は未設定 = すべて既定 ON)'}")

    deck = selfplay.load_deck("deck.csv")
    for _ in range(args.games):
        selfplay.run_match(deck, deck, NEW.agent, NEW.agent)

    tot = stat["total"] or 1
    same_pct = 100.0 * stat["same"] / tot
    print(f"決定数 {stat['total']}   一致 {stat['same']} ({same_pct:.2f}%)   "
          f"不一致 {stat['diff']} ({100.0 * stat['diff'] / tot:.2f}%)")
    if stat["ctrl_error"]:
        print(f"   ※対照が例外を投げた回数: {stat['ctrl_error']}（この分は分母から除外）")
    for k, v in stat.most_common():
        if str(k).startswith("diff:"):
            print(f"   {v:>5}  {k}")
    for d in diffs:
        print(f"   例: {d[0]}  新={d[1]} 旧={d[2]}")

    # 機械可読（ドライバから拾えるように）
    print(f"TOTAL={stat['total']}")
    print(f"SAME={stat['same']}")
    print(f"DIFF={stat['diff']}")
    print(f"SAME_PCT={same_pct:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

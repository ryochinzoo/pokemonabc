#!/usr/bin/env python3
"""sham-search プラセボ対照 — 計測系がRNG汚染されていないかの検査 (2026-08-02、層S)。

**背景**: 公開ノートブック `lucifer19/battlecore-compact-agent` §3.3 が、
「探索を全部走らせて結果を捨てる」プラセボ腕を作ったところ、構成上ベースラインと
挙動が同一のはずなのに 0.48 ではなく **0.450** を出した、と報告している。診断:
「*In a shared process, agent-side searches perturb the live engine's RNG stream.
The measurement gate itself was contaminated. Any oracle-vs-baseline comparison
made in that arena was invalid — in either direction.*」
彼らはアリーナを 1エージェント=1 OSプロセス に作り直した。

**我々への当たり**: `verification/bench.py` と `selfplay.py` に fork/subprocess は無く、
両者は同一プロセスで走る。台帳#26(探索層 ON/OFF = **+13.62pt**、我々の最大の数値)は
`V2_NO_SEARCH` 環境変数の ON/OFF で測られているため、同型の汚染を負いうる。
汚染は片側に効く(我々だけが探索を呼び、相手ゲージは呼ばない=非対称)。

**設計**(main.py は無編集。ハーネス側だけで閉じる):
  - OFF腕 : `V2_NO_SEARCH=1`。`_search_decide` は即 None を返す = **エンジン仕事ゼロ**
  - SHAM腕: 環境変数を立てず `_search_decide` を**完全に実行してから結果を捨てる**
            = エンジン仕事あり、**選ぶ手は OFF腕と同一(v1の答え)**
  → 両腕は**同じ方策**を打つ。差が出るなら、それは純粋に RNG 消費の副作用 = 汚染量。

判定(実行前に固定):
  - |SHAM − OFF| の 95%CI が 0 を含む → **汚染は検出されず**。#26 はこの経路では無傷
  - CI が 0 を外す → **計測系が汚染されている**。#26 の +13.62pt は汚染量ぶん補正が要る

使い方(デッキディレクトリから):
  cd src/input/datasets/decks/starmie-aggro
  python3 ../../../../../verification/sham_search_probe.py 1500 \
      --opponent ../../../../../verification/reference/official_lucario_agent.py \
      --opponent-deck ../../../../../verification/decks/official_lucario_2026-07-21.csv
"""
import argparse
import importlib.util
import math
import os
import sys
import time

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import selfplay  # noqa: E402


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wilson(w: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def run_arm(label: str, n: int, deck, opp_deck, opp_agent, sham: bool) -> dict:
    """sham=True: 探索を完走させてから結果を捨てる / False: V2_NO_SEARCH=1 で呼ばない。"""
    if sham:
        os.environ.pop("V2_NO_SEARCH", None)
    else:
        os.environ["V2_NO_SEARCH"] = "1"

    m = load_module("main.py", f"main_{label}")
    calls = {"reached": 0, "would_have_moved": 0}

    if sham:
        orig = m._search_decide

        def shammed(obs_dict, sel, v1_answer):
            calls["reached"] += 1
            r = orig(obs_dict, sel, v1_answer)  # 完全に実行する(エンジン仕事あり)
            if r is not None:
                calls["would_have_moved"] += 1
            return None  # ← 結果を捨てる。打つ手は v1 と同一

        m._search_decide = shammed

    t0 = time.monotonic()
    res = selfplay.run_series(n, deck, opp_deck, m.agent, opp_agent)
    dt = time.monotonic() - t0
    w, l = res["agent0_wins"], res["agent1_wins"]
    tot = w + l
    lo, hi = wilson(w, tot)
    print(
        f"  {label:5s}: {w}勝 {l}敗  勝率 {100*w/tot:5.2f}%  CI[{lo:.2f}, {hi:.2f}]"
        f"  ({dt:.0f}s)" + (f"  探索到達 {calls['reached']} / 手を持っていた {calls['would_have_moved']}" if sham else "")
    )
    return {"w": w, "n": tot, "p": w / tot}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=1500)
    ap.add_argument("--opponent", required=True)
    ap.add_argument("--opponent-deck", required=True)
    args = ap.parse_args()

    deck = selfplay.load_deck("deck.csv")
    opp_deck = selfplay.load_deck(args.opponent_deck)
    opp_agent = load_module(args.opponent, "opp").agent

    print(f"sham-search プラセボ対照 / 各腕 N={args.n} / 相手 {os.path.basename(args.opponent)}")
    print("両腕とも打つ手は v1 と同一。差が出るなら純粋に RNG 消費の副作用。\n")

    off = run_arm("OFF", args.n, deck, opp_deck, opp_agent, sham=False)
    sham = run_arm("SHAM", args.n, deck, opp_deck, opp_agent, sham=True)

    d = 100 * (sham["p"] - off["p"])
    se = 100 * math.sqrt(
        sham["p"] * (1 - sham["p"]) / sham["n"] + off["p"] * (1 - off["p"]) / off["n"]
    )
    print(f"\n  差 (SHAM − OFF) = {d:+.2f} pt   95%CI [{d-1.96*se:+.2f}, {d+1.96*se:+.2f}]   SE={se:.2f}")
    if abs(d) - 1.96 * se > 0:
        print("  → **汚染を検出**。同一プロセスでの探索がエンジンのRNGを乱している。")
        print("     台帳#26(+13.62pt)はこの量ぶん補正が要る。プロセス隔離したハーネスで再測すること。")
    else:
        print("  → 汚染は検出されず(この検出力の範囲で)。台帳#26 はこの経路では無傷。")
        print(f"     検出力の限界: |真の汚染| > {1.96*se:.2f} pt なら検出できたはず。")


if __name__ == "__main__":
    main()

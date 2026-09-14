#!/usr/bin/env python3
"""Phase 0 先行ゲート計装 (事前登録 plan-2026-07-29-metadecks-repair.md §3, M6b)。

対象dir(王者 or 変種)をcwdにして実行。main.py は一切編集せず、モジュール属性
`_infer_enemy_deck` を観測専用ラッパで置換して素通しする(_determinize は呼び出し時に
モジュールグローバルを引くのでこれで捕捉できる)。相手エージェントは
bench.py と同じ load 方式=別モジュールインスタンスのため、自陣側の計装だけが記録される。

記録(呼び出しごと): (選択キー or FALLBACK, overlap=|推定60 ∩ 真60|多重集合)
戦単位の集約 = **最終呼び出し**(事前登録M1)。探索が一度も走らなかった戦は NO_CALL。

    cd decks/starmie-aggro-metadecks   # または decks/starmie-aggro
    python3 ../../../../../verification/probe_metadecks.py 50 \
        --opponent ../../../../../verification/reference/official_lucario_agent.py \
        --opponent-deck ../../../../../verification/decks/official_lucario_2026-07-21.csv \
        --expect-key meta_lucario --label variant_lucario

出力(機械可読): PROBE_JSON={...}
"""
import argparse
import importlib.util
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))


def load_agent_from_path(path: str):
    spec = importlib.util.spec_from_file_location("opponent_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def read_ids(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line:
                out.append(int(line))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=50)
    ap.add_argument("--opponent", required=True, help="相手agentの.py or 'random'")
    ap.add_argument("--opponent-deck", required=True, help="相手デッキCSV(=真の60枚)")
    ap.add_argument("--expect-key", default=None, help="変種側の正解キー(王者側はNone)")
    ap.add_argument("--label", default="probe")
    args = ap.parse_args()

    import selfplay
    import main as our_main

    true60 = Counter(read_ids(args.opponent_deck))
    assert sum(true60.values()) == 60

    # 辞書エントリの逆引き表(出力リスト→キー)。Counter一致で判定
    entry_sig = {k: Counter(v) for k, v in our_main._META_DECKS.items()}

    records = []          # 現在の試合の呼び出し列
    orig = our_main._infer_enemy_deck

    def wrapped(visible):
        out = orig(visible)
        c = Counter(out)
        key = next((k for k, sig in entry_sig.items() if sig == c), "FALLBACK")
        ov = sum(min(n, true60.get(cid, 0)) for cid, n in c.items())
        records.append((key, ov))
        return out

    our_main._infer_enemy_deck = wrapped

    opp_agent = (selfplay.random_agent if args.opponent == "random"
                 else load_agent_from_path(args.opponent))
    our_deck = selfplay.load_deck()
    opp_deck = read_ids(args.opponent_deck)

    per_game = []         # (final_key, final_overlap) or ("NO_CALL", -1)
    wins = 0
    for i in range(args.n):
        records.clear()
        if i % 2 == 0:
            r = selfplay.run_match(our_deck, opp_deck, our_main.agent, opp_agent)
            w = r["winner"]
        else:
            r = selfplay.run_match(opp_deck, our_deck, opp_agent, our_main.agent)
            w = (1 - r["winner"]) if r["winner"] in (0, 1) else r["winner"]
        wins += (w == 0)
        per_game.append(records[-1] if records else ("NO_CALL", -1))

    games = [g for g in per_game if g[0] != "NO_CALL"]
    n_eff = len(games)
    key_counts = Counter(k for k, _ in games)
    correct = key_counts.get(args.expect_key, 0) if args.expect_key else 0
    fallback = key_counts.get("FALLBACK", 0)
    wrong = n_eff - correct - fallback if args.expect_key else n_eff - fallback
    ov54 = sum(1 for _, ov in games if ov >= 54)
    ov60_when_correct = (
        all(ov == 60 for k, ov in games if k == args.expect_key)
        if args.expect_key and correct else None)

    out = {
        "label": args.label,
        "n": args.n, "n_eff": n_eff, "no_call": args.n - n_eff,
        "wins": wins,
        "final_key_counts": dict(key_counts),
        "correct_rate": round(correct / n_eff, 4) if n_eff and args.expect_key else None,
        "fallback_rate": round(fallback / n_eff, 4) if n_eff else None,
        "wrong_key_rate": round(wrong / n_eff, 4) if n_eff else None,
        "overlap_ge54_rate": round(ov54 / n_eff, 4) if n_eff else None,
        "mean_final_overlap": round(sum(ov for _, ov in games) / n_eff, 2) if n_eff else None,
        "coverage_identity_ok": ov60_when_correct,
    }
    print(f"PROBE_JSON={json.dumps(out, ensure_ascii=False)}")


if __name__ == "__main__":
    main()

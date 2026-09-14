#!/usr/bin/env python3
"""族内(in-family)測定の汚染量を実測する (2026-07-30、穴D M9a の前倒し検証)。

**問題**: `bench.py --opponent main.py --opponent-deck <他デッキ>` は、相手側モジュールの
`_my_deck60()` が **cwd の deck.csv** を読むため(main.py:16-30 `read_deck_csv`)、
相手が実際に握っているデッキと食い違う。`_determinize` は
`my_unseen = _counter(my_deck60)` から可視カードを引き算し `max(0, n)` で負をクランプするため、
**自分の山を誤ったまま決定化する = 探索が無音で劣化する**。
プロセス内で cwd は1つしか無いので、どちらを cwd にしても必ず片側が壊れる。

**修理**: モジュールをロードした後に `_my_deck60_cache` を正しい60枚で直接埋める。
main.py は無編集(ハーネス側だけで閉じる)。

**測定**: 同じ対戦を BROKEN(現行の走らせ方) と FIXED(両側のキャッシュを正す) で回し、
勝率差 = 汚染量 を出す。

    python3 verification/infamily_probe.py 300 \
        --our-deck deck.csv --opp-deck ../../../../../verification/decks/official_lucario_2026-07-21.csv

cwd は我々の提出物dir(deck.csv と cg/ がある場所)。
"""
import argparse
import importlib.util
import os
import sys
import time

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_deck(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line:
                out.append(int(line))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=300)
    ap.add_argument("--our-deck", default="deck.csv")
    ap.add_argument("--opp-deck", required=True)
    ap.add_argument("--opp-main", default=None,
                    help="相手側 main.py (既定=cwd の main.py = 族内測定)")
    args = ap.parse_args()

    import selfplay

    our_deck = read_deck(args.our_deck)
    opp_deck = read_deck(args.opp_deck)
    opp_path = args.opp_main or os.path.join(os.getcwd(), "main.py")

    for mode in ("BROKEN", "FIXED"):
        # 毎回ロードし直してキャッシュ状態を独立させる
        ours = load_module(os.path.join(os.getcwd(), "main.py"), f"our_{mode}")
        opp = load_module(opp_path, f"opp_{mode}")
        # 我々側は cwd の deck.csv を読むので常に正しい。相手側だけが問題。
        if mode == "FIXED":
            ours._my_deck60_cache = list(our_deck)
            opp._my_deck60_cache = list(opp_deck)   # ←これが修理の全部
        else:
            # 現行の走らせ方を忠実に再現(相手は cwd の deck.csv を自分の山だと思い込む)
            pass
        t0 = time.time()
        res = selfplay.run_series(args.n, our_deck, opp_deck, ours.agent, opp.agent)
        dt = time.time() - t0
        w, n = res["agent0_wins"], res["n"]
        cached = opp._my_deck60()
        ok = sorted(cached) == sorted(opp_deck)
        print(f"{mode:<7} 我々 {w}/{n} = {100*w/n:5.2f}%   "
              f"({dt:.0f}s)  相手が自分の山だと思っている60枚が正しいか: {ok}")


if __name__ == "__main__":
    main()

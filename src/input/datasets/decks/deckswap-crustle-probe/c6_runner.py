#!/usr/bin/env python3
"""C6計装: crustle の vs random フロア割れ(78.3%)の機構弁別。

bench.py の安全ゲート走行(vs random・両者同一デッキ)を再現しつつ、
selfplay.run_match が返す (winner, reason, turns) を試合単位で保存する。
reason: 1=サイド0(取り切られ) / 2=山切れ(そのターン開始時に山0) / 3=場に出せない / 4=カード効果。

仮説の弁別(data.md 事前登録参照):
  H_deckout(赤チームD): 我々の敗北の過半が reason=2(自山切れ)
  H_kanga(前任者):     我々の敗北の過半が reason=1(サイド献上で取り切られ)
"""
import json
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
VERIF = os.path.abspath(os.path.join(HERE, "../../../../../verification"))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(1, VERIF)

import selfplay  # noqa: E402
import main as our_main  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
deck = selfplay.load_deck("deck.csv")

rows = []
for i in range(N):
    our_seat = i % 2  # 席を半々で入れ替え(bench.py の run_series と同じ意図)
    if our_seat == 0:
        r = selfplay.run_match(deck, deck, our_main.agent, selfplay.random_agent)
    else:
        r = selfplay.run_match(deck, deck, selfplay.random_agent, our_main.agent)
    won = r["winner"] == our_seat
    rows.append({"i": i, "seat": our_seat, "won": won,
                 "winner": r["winner"], "reason": r["reason"], "turns": r["turns"]})

with open("c6_games.jsonl", "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

wins = sum(1 for r in rows if r["won"])
losses = [r for r in rows if not r["won"] and r["winner"] in (0, 1)]
draws = [r for r in rows if r["winner"] not in (0, 1)]
print(f"N={N}  wins={wins} ({wins/N:.1%})  losses={len(losses)}  draws/unknown={len(draws)}")
lr = collections.Counter(r["reason"] for r in losses)
wr_ = collections.Counter(r["reason"] for r in rows if r["won"])
print(f"敗北の終了理由: {dict(lr)}   (1=サイド取り切られ 2=自山切れ 3=場に出せない 4=効果)")
print(f"勝利の終了理由: {dict(wr_)}")
lt = [r["turns"] for r in losses]
wt = [r["turns"] for r in rows if r["won"]]
if lt:
    print(f"敗北時ターン: mean={sum(lt)/len(lt):.1f} min={min(lt)} max={max(lt)}")
if wt:
    print(f"勝利時ターン: mean={sum(wt)/len(wt):.1f} min={min(wt)} max={max(wt)}")
print("CRASH=0")

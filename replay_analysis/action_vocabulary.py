#!/usr/bin/env python3
"""行動語彙の比較 — 上位帯のエージェントは、我々より何を「多く」やっているのか。

**問い**(ゆうじ 2026-08-03): 「現状のデッキとロジックでは足りない。アグロでできることは
限られている。上位デッキは多エネ・多ポケモンを操るロジックを検証してエビデンスにできる」
→ これを**印象ではなく計数**にする。運営も評価軸に **deckcrafting** を名指ししている
(Strategy discussion/708494)。

方式: **ログから数える**(選択からは数えない)。理由は既存実装の2つの教訓:
  - `entry.action` は1つ前のstepのselectへの答え(off-by-one、decision_census.py)
  - `observation.logs` は step 間で**再送**される → `logs == prev[player]` で重複排除
    (台帳#31。素朴加算は2〜3倍に膨らむ)
  - 攻撃の同定は `cardId` ではなく **`attackId`**(台帳#30)

数えるもの(すべて「そのエージェント自身の playerIndex」に帰属するログのみ):
  ATTACK(15) / PLAY(10) / ATTACH(11) / EVOLVE(12) / SWITCH(8)+CHANGE(9) /
  状態異常の付与(17-21) / TURN_START(2)

使い方: python3 replay_analysis/action_vocabulary.py [1エージェントあたりの試合数]
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

ATTACK, PLAY, ATTACH, EVOLVE, SWITCH, CHANGE, TURN_START = 15, 10, 11, 12, 8, 9, 2
STATUS = {17: "poison", 18: "burn", 19: "sleep", 20: "paralyze", 21: "confuse"}

# 生リプレイを残してあるディレクトリ(アーキタイプ1体ずつ+我々)
SOURCES = [
    ("crustle    1063", HERE / "ladder_scout/sub55039428", 55039428),
    ("grimmsnarl 1046", HERE / "ladder_scout/sub55085151", 55085151),
    ("alakazam   1012", HERE / "ladder_scout/sub54976675", 54976675),
    ("dudunspar  1006", HERE / "ladder_scout/sub55172896", 55172896),
    ("archaludon  918", HERE / "ladder_scout/sub54987008", 54987008),
    ("tarountula  910", HERE / "ladder_scout/sub55027607", 55027607),
    ("lucario     903", HERE / "ladder_scout/sub54513186", 54513186),
    ("★我々 王者  783", HERE / "eps55058443", 55058443),
    ("★我々 幅探査", HERE / "eps55169074", 55169074),
]


def load_names():
    out = {}
    with open(REPO / "verification/data/EN_Card_Data.csv") as f:
        for r in csv.DictReader(f):
            out[int(r["Card ID"])] = r["Card Name"]
    return out


NAMES = load_names()


def scan_game(path, my_index):
    """1試合ぶんの、自分側の行動カウント。"""
    try:
        d = json.loads(path.read_text())
    except Exception:
        return None
    c = Counter()
    attacks = Counter()        # attackId -> n
    attackers = Counter()      # cardId -> n
    played = Counter()         # cardId -> n
    prev = [None, None]
    for step in d.get("steps", []):
        for si, ag in enumerate(step):
            logs = (ag.get("observation") or {}).get("logs")
            if logs is None or logs == prev[si]:
                continue                      # 再送の重複排除(台帳#31)
            prev[si] = logs
            for L in logs:
                t, p = L.get("type"), L.get("playerIndex")
                if t == TURN_START:
                    c["turns_total"] += 1
                    if p == my_index:
                        c["my_turns"] += 1
                if p != my_index:
                    continue
                if t == ATTACK:
                    c["attack"] += 1
                    attacks[L.get("attackId")] += 1
                    attackers[L.get("cardId")] += 1
                elif t == PLAY:
                    c["play"] += 1
                    played[L.get("cardId")] += 1
                elif t == ATTACH:
                    c["attach"] += 1
                elif t == EVOLVE:
                    c["evolve"] += 1
                elif t in (SWITCH, CHANGE):
                    c["switch"] += 1
                elif t in STATUS and not L.get("isRecover"):
                    c["status_taken"] += 1     # 自分が受けた状態異常
    return c, attacks, attackers, played


def main(per_agent=30):
    print(f"# 行動語彙の比較(各エージェント最大{per_agent}試合、ログ計数・自分側のみ)\n")
    rows = []
    for label, d, sub in SOURCES:
        lf = d / "_list.json"
        if not lf.exists():
            print(f"  ({label}: _list.json 無し、skip)")
            continue
        meta = {e["id"]: e["agents"] for e in json.loads(lf.read_text()).get("episodes", [])
                if len(e.get("agents", [])) == 2}
        files = sorted(d.glob("ep*.json"), reverse=True)[:per_agent]
        tot = Counter()
        A, K, P = Counter(), Counter(), Counter()
        n = 0
        for f in files:
            ep = int(f.stem[2:])
            if ep not in meta:
                continue
            idx = next((i for i, a in enumerate(meta[ep])
                        if a.get("submissionId") == sub), None)
            if idx is None:
                continue
            r = scan_game(f, idx)
            if not r:
                continue
            c, a, k, p = r
            tot += c
            A += a
            K += k
            P += p
            n += 1
        if not n:
            continue
        top1 = A.most_common(1)[0][1] / max(1, sum(A.values())) if A else 0
        rows.append(dict(
            label=label, n=n,
            turns=tot["my_turns"] / n,
            atk=tot["attack"] / n,
            n_atk=len(A), top1=100 * top1,
            n_species=len(K),
            play=tot["play"] / n, n_play=len(P),
            attach=tot["attach"] / n, evolve=tot["evolve"] / n,
            switch=tot["switch"] / n, status=tot["status_taken"] / n,
            topcards=P.most_common(5)))

    hdr = (f"{'エージェント':<18}{'n':>4}{'自ターン':>8}{'攻撃/戦':>8}{'攻撃種':>7}"
           f"{'最頻攻撃%':>10}{'攻撃役':>7}{'カード/戦':>9}{'種類':>6}"
           f"{'エネ付':>7}{'進化':>6}{'入替':>6}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['label']:<18}{r['n']:>4}{r['turns']:>8.1f}{r['atk']:>8.1f}"
              f"{r['n_atk']:>7}{r['top1']:>9.0f}%{r['n_species']:>7}"
              f"{r['play']:>9.1f}{r['n_play']:>6}{r['attach']:>7.1f}"
              f"{r['evolve']:>6.1f}{r['switch']:>6.1f}")

    print("\n## よく使うカード(上位5、種類数の中身)")
    for r in rows:
        top = ", ".join(f"{NAMES.get(c, c)}×{n}" for c, n in r["topcards"])
        print(f"  {r['label']:<18} {top}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)

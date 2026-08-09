#!/usr/bin/env python3
"""プローブ検死(キャンペーン共通ツール): T1判定+タイミング+ガード挙動+CRASH検査。

t1_verdict.py の対面分類(デッキベース、RULES先勝ち)を継承し、
①エピソード一覧を ListEpisodes(公開POST、ログイン不要と2026-08-02確認)から取得
②先頭=バリデーション自己対戦を自動除外 ③チーム内対戦(相手が自チーム提出)を別枠
④remainingOverageTime 差分で本番課金テレメトリ ⑤statuses で CRASH 検査。

使い方:
  python3 replay_analysis/probe_autopsy.py <submissionId> <epsDir> <H1覆域予測%> [自デッキcsv] [覆域対面CSV]
  例: python3 replay_analysis/probe_autopsy.py 55163442 replay_analysis/eps55163442 44.04
  P9: python3 replay_analysis/probe_autopsy.py <ref> <epsDir> 68.8 \
        src/input/datasets/decks/deckswap-tarountula/deck.csv "Alakazam,Lucario,Archaludon"

2026-08-04 修理(red-team-D指摘): ①OUR_TEAM_SUBS に 55169074 を追加 ②自側同定デッキが
starmie-clockguard 固定だった(P9=tarountulaで誤同定)→引数化 ③覆域対面が旧CEW4面固定だった
(P9の登録は Alakazam/Lucario/Archaludon の3面)→引数化。省略時は旧挙動=過去プローブの再現に影響なし。
"""
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUR_TEAM_SUBS = {55163442, 55070495, 55060473, 55058443, 54961048, 54858780, 54832323,
                 55169074,  # P2幅プローブ(2026-08-04追加)
                 55209782, 55216410,  # 2026-08-03 ゆうじのproto提出2本(CLI一覧で発見、2026-08-04追記)
                 55236642,  # P9 deckswap-tarountula(2026-08-04提出)。新規提出のたびにここへ追記する
                 # 2026-08-08 追記: 8/3-8/5 のりょーちん提出4本 + 8/7 の pilotfix。
                 # これが欠けると**チーム内対戦が外部対面として集計される**(red-team-D §8.1 #3 と同種)。
                 55258782, 55260998, 55264776, 55270074,  # proto3 / proto4 / proto5 / v9
                 55308422,  # pilotfix
                 55376467}  # 2026-08-09 v2(デッキ非ex化 + 3修理全ON)。T1事前登録は data.md
COVERED = {"Lucario", "Archaludon", "Abomasnow", "Dragapult"}  # 既定=旧CEW4面(argv[5]で上書き可)
RULES = [
    ("Lucario", ["Mega Lucario ex"]),
    ("Archaludon", ["Archaludon ex"]),
    ("Abomasnow", ["Mega Abomasnow ex"]),
    ("Wall(Crustle/GreatTusk)", ["Crustle"]),
    ("StarmieMirror", ["Mega Starmie ex"]),
    ("Alakazam", ["Alakazam"]),
    ("Grimmsnarl", ["Marnie's Grimmsnarl ex"]),
    ("Dragapult", ["Dragapult ex"]),
    ("TR Mewtwo", ["Team Rocket's Mewtwo ex"]),
    ("Kangaskhan", ["Mega Kangaskhan ex"]),
    ("Garchomp", ["Cynthia's Garchomp ex", "Garchomp ex"]),
]


def load_names():
    out = {}
    with open(REPO / "verification/data/EN_Card_Data.csv") as f:
        for r in csv.DictReader(f):
            st = r["Stage (Pokémon)/Type (Energy and Trainer)"] or ""
            out[int(r["Card ID"])] = (r["Card Name"], "Pokémon" in st)
    return out


def wilson(k, n):
    if n == 0:
        return (0.0, 100.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def main(sub_id, eps_dir, h1, deck_csv=None, covered=None):
    covered = covered if covered is not None else COVERED
    # 2026-08-05: playbook §8 に従い、一覧取得は門番(kaggle_gate)経由のみ。キャッシュ優先。
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kaggle_gate
    eps = kaggle_gate.list_episodes(sub_id)["episodes"]
    eps = [e for e in eps if e.get("state") == "COMPLETED"]
    eps.sort(key=lambda e: e["createTime"])
    validation = eps[0]["id"] if eps else None
    rows = []
    for e in eps:
        me = next(a for a in e["agents"] if a.get("submissionId") == sub_id)
        opp = next((a for a in e["agents"] if a is not me), {})
        rows.append(dict(ep=e["id"], reward=me.get("reward"),
                         opp_sub=opp.get("submissionId"),
                         team_internal=opp.get("submissionId") in OUR_TEAM_SUBS))

    names = load_names()
    deck_path = Path(deck_csv) if deck_csv else (
        REPO / "src/input/datasets/decks/starmie-clockguard/deck.csv")
    ours = Counter(int(l) for l in open(deck_path) if l.strip())

    tally = defaultdict(lambda: [0, 0])
    internal = [0, 0]
    deltas, ep_consumed, bank_min = [], [], 600.0
    statuses = Counter()
    n_real = 0
    for row in rows:
        f = Path(eps_dir) / f"ep{row['ep']}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        # statuses(最終step)
        for a in d["steps"][-1]:
            statuses[a.get("status")] += 1
        if row["ep"] == validation:
            continue
        # 自分の同定はデッキ重なりで(両者streams)
        decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
        ov = [sum((ours & x).values()) for x in decks]
        mine = 0 if ov[0] >= ov[1] else 1
        # タイミング: 自分ACTIVE観測の remainingOverageTime 差分
        rots = []
        for step in d["steps"]:
            if mine >= len(step):
                continue
            e2 = step[mine]
            if e2.get("status") != "ACTIVE":
                continue
            rot = (e2.get("observation") or {}).get("remainingOverageTime")
            if rot is not None:
                rots.append(float(rot))
        if len(rots) >= 2:
            ds = [rots[i] - rots[i + 1] for i in range(len(rots) - 1) if rots[i] >= rots[i + 1]]
            deltas += ds
            ep_consumed.append(rots[0] - rots[-1])
            bank_min = min(bank_min, min(rots))
        if row["team_internal"]:
            internal[0 if row["reward"] == 1 else 1] += 1
            continue
        # 対面分類(相手デッキ)
        opp_deck = decks[1 - mine]
        lineup = {}
        for cid, n in opp_deck.items():
            nm, isp = names.get(cid, ("?", False))
            if isp:
                lineup[nm] = lineup.get(nm, 0) + n
        label = next((lab for lab, keys in RULES if any(k in lineup for k in keys)), None)
        if label is None:
            top = sorted(lineup.items(), key=lambda kv: -kv[1])
            label = "Other:" + (top[0][0] if top else "?")
        tally[label][0 if row["reward"] == 1 else 1] += 1
        n_real += 1

    print(f"# probe autopsy sub={sub_id} (validation ep{validation} 除外)")
    print(f"実ラダー対外戦 N={n_real} / チーム内対戦 {internal[0]}W-{internal[1]}L / "
          f"statuses={dict(statuses)}")
    w_tot = sum(v[0] for v in tally.values())
    print(f"対外の素の勝率: {w_tot}/{n_real}")
    print(f"\n{'対面':<24}{'W-L':>8}{'n':>4}")
    cov_w = cov_n = 0
    for lab, (w, l) in sorted(tally.items(), key=lambda kv: -sum(kv[1])):
        print(f"{lab:<24}{f'{w}-{l}':>8}{w+l:>4}")
        if lab in covered:
            cov_w += w
            cov_n += w + l
    lo, hi = wilson(cov_w, cov_n)
    print(f"\n★覆域({sorted(covered)}): {cov_w}/{cov_n} = "
          f"{100*cov_w/max(1,cov_n):.1f}%  95%CI[{lo:.1f},{hi:.1f}]  H1={h1}")
    print(f"  N_cov={cov_n} (登録判定はN_cov>=20)  H1はCI{'内' if lo <= h1 <= hi else '外'}")
    if deltas:
        deltas.sort()
        n = len(deltas)
        print(f"\nタイミング: 決定間課金 n={n} 中央値={deltas[n//2]*1000:.0f}ms "
              f"p99={deltas[int(n*0.99)]*1000:.0f}ms 最大={deltas[-1]*1000:.0f}ms")
        pe = sorted(ep_consumed)
        print(f"エピソード消費: 中央値={pe[len(pe)//2]:.2f}s 最大={pe[-1]:.2f}s / 600s")
        print(f"バンク最小={bank_min:.1f}s (ガード閾値72sを{'下回った!' if bank_min < 72 else '大きく上回る=ガード不発火を機械確認'})")


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], float(sys.argv[3]),
         sys.argv[4] if len(sys.argv) > 4 else None,
         set(sys.argv[5].split(",")) if len(sys.argv) > 5 else None)

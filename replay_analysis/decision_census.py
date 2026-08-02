#!/usr/bin/env python3
"""「決定点」計数の監査(測定専用): 12,506 の正体の特定と、ACTIVE限定の正しい分母。

背景: review-request-fable5-full.md §4.5 の「12,506決定点(MAIN 6,240 / CARD 5,828 /
DAMAGE 163)」が、独立計数(自分ACTIVE=2,646)と約4.7倍乖離。INACTIVE再送の
二重計数疑い(D59/台帳#31と同型)。ここで (自分/相手/両方)×(ACTIVE/全status) の
全組合せを数え、どの組合せが公表値を再現するかを特定する。

併せて §6.1(Ignition 72回)と §6.4(DAMAGE文脈163件)を ACTIVE限定で再集計する。

★重要(2026-07-31発見): リプレイの `entry.action` は **同stepのselectへの答えではなく、
1つ前のstepのselectへの答え**(D11-3のoff-by-oneはビジュアライザだけでなく
replay.json のフィールド対応にも存在する)。証拠: (a)決定のあるACTIVE stepの
action が空 (b)自分のnopt範囲外・直前stepのnopt範囲内のactionが出現
(c)INACTIVEエントリがactionを運ぶ。よって本スクリプトの選択の読みは
「step s の select ↔ step s+1 の entry[me].action」で対応づける。

使い方:
  cd src/input/datasets/decks/starmie-aggro && \
  python3 ../../../../../replay_analysis/decision_census.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/input/datasets/decks/starmie-aggro"))
from cg.api import (AreaType, OptionType, SelectContext, SelectType,  # noqa: E402
                    to_observation_class)
import main as champ  # noqa: E402

CARDS, _ = champ._card_db()
TYPE = {int(s): s.name for s in SelectType}
DMG_CTX = {int(SelectContext.DAMAGE_COUNTER), int(SelectContext.DAMAGE_COUNTER_ANY),
           int(SelectContext.DAMAGE)}
OUR = "Yser"

grid = Counter()      # (side, status) -> n
bytype = Counter()    # (side, status, typename) -> n
dmgctx = Counter()    # (side, status) -> n
ign = Counter()
ign_basic_rescued = 0
dmg_active = Counter()
align = Counter()     # off-by-one補正後のaction整合性

for d in ["eps55058443", "eps55060473"]:
    for f in sorted((ROOT / "replay_analysis" / d).glob("*.json")):
        try:
            rep = json.loads(f.read_text())
        except Exception:
            continue
        nm = (rep.get("info") or {}).get("TeamNames") or []
        if OUR not in nm:
            continue
        me = nm.index(OUR)
        evolves_by_turn = defaultdict(list)   # turn -> [evolvesFrom名]
        basic_attaches = []                   # (turn, 貼り先カード名)
        steps = rep["steps"]
        for si, step in enumerate(steps):
            for pi, e in enumerate(step):
                obsd = e.get("observation") or {}
                sel = obsd.get("select")
                if not sel or not sel.get("option"):
                    continue
                side = "mine" if pi == me else "opp"
                status = "ACTIVE" if e.get("status") == "ACTIVE" else "INACTIVE"
                t = sel.get("type")
                ctx = sel.get("context")
                grid[(side, status)] += 1
                bytype[(side, status, TYPE.get(t, str(t)))] += 1
                if ctx in DMG_CTX:
                    dmgctx[(side, status)] += 1
                # ★シフト整合性の全数検証(自分・相手の全ACTIVE select、全SelectType)
                if status == "ACTIVE":
                    nxt = (steps[si + 1][pi].get("action")
                           if si + 1 < len(steps) and pi < len(steps[si + 1]) else None)
                    n_opt = len(sel["option"])
                    tn = TYPE.get(t, str(t))
                    if nxt is None:
                        align[(side, tn, "次step無し")] += 1
                    elif nxt == []:
                        ok = (sel.get("minCount") or 0) == 0
                        align[(side, tn, "空(minCount=0合法)" if ok else "空(不整合)")] += 1
                    elif (all(isinstance(x, int) and 0 <= x < n_opt for x in nxt)
                          and len(set(nxt)) == len(nxt)):
                        align[(side, tn, "整合")] += 1
                    else:
                        align[(side, tn, "範囲外/重複")] += 1
                if side != "mine" or status != "ACTIVE":
                    continue
                # --- ここから ACTIVE 自分のみ ---
                if ctx in DMG_CTX:
                    dmg_active["n"] += 1
                    if len(sel["option"]) >= 2:
                        dmg_active["n2"] += 1
                if t != int(SelectType.MAIN):
                    continue
                act = (steps[si + 1][me].get("action")
                       if si + 1 < len(steps) and me < len(steps[si + 1]) else None)
                if not act:
                    continue
                if not all(isinstance(x, int) and 0 <= x < len(sel["option"]) for x in act):
                    continue
                try:
                    obs = to_observation_class(obsd)
                except Exception:
                    continue
                if obs.select is None or obs.current is None:
                    continue
                st_ = obs.current
                my = st_.yourIndex if st_.yourIndex is not None else me
                turn = st_.turn or 0
                for oi in act:
                    o = obs.select.option[oi]
                    if o.type == OptionType.ATTACH:
                        try:
                            ecid = (st_.players[my].hand[o.index].id
                                    if o.area == AreaType.HAND else None)
                        except Exception:
                            ecid = None
                        if ecid == 17:
                            pk = champ._pokemon_at(st_, my, o.inPlayArea, o.inPlayIndex)
                            c = CARDS.get(pk.id) if pk else None
                            ev = bool(c and (getattr(c, "stage1", False)
                                             or getattr(c, "stage2", False)))
                            ign["total"] += 1
                            ign["進化体" if ev else "たね"] += 1
                            if not ev and c is not None:
                                basic_attaches.append((turn, c.name))
                    elif o.type == OptionType.EVOLVE:
                        cid = champ._card_id_of_option(obs, o)
                        cc = CARDS.get(cid) if cid else None
                        if cc is not None:
                            evolves_by_turn[turn].append(cc.evolvesFrom)
        for turn, tgt in basic_attaches:
            if any(ef == tgt for ef in evolves_by_turn.get(turn, [])):
                ign_basic_rescued += 1

print("## 決定点候補の全組合せ(select.option が非空のエントリ数)\n")
print("| 側 | status | n |")
for side in ("mine", "opp"):
    for status in ("ACTIVE", "INACTIVE"):
        print(f"| {side} | {status} | {grid[(side, status)]} |")
mine_all = grid[("mine", "ACTIVE")] + grid[("mine", "INACTIVE")]
opp_all = grid[("opp", "ACTIVE")] + grid[("opp", "INACTIVE")]
both_active = grid[("mine", "ACTIVE")] + grid[("opp", "ACTIVE")]
both_all = mine_all + opp_all
print(f"\n自分/全status = {mine_all}")
print(f"両者/ACTIVE   = {both_active}")
print(f"両者/全status = {both_all}   ← 12,506 との照合対象")

print("\n## SelectType別(公表値: MAIN 6,240 / CARD 5,828 との照合)\n")
for label, pred in [("両者/全status", lambda s, st: True),
                    ("自分/ACTIVE", lambda s, st: s == "mine" and st == "ACTIVE")]:
    c = Counter()
    for (s, st, tn), v in bytype.items():
        if pred(s, st):
            c[tn] += v
    print(f"{label}: " + ", ".join(f"{k}={v}" for k, v in c.most_common()))

print("\n## DAMAGE系context(公表値: 163 との照合)\n")
for side in ("mine", "opp"):
    for status in ("ACTIVE", "INACTIVE"):
        print(f"  {side}/{status}: {dmgctx[(side, status)]}")
print(f"  自分/ACTIVE(=正しい分母): {dmg_active['n']} / うち選択肢2+: {dmg_active['n2']}")

print("\n## action対応の整合性(シフト補正 select[s]↔action[s+1]、全ACTIVE・全SelectType)\n")
print("| 側 | SelectType | 判定 | n |")
for (side, tn, verdict), v in sorted(align.items()):
    print(f"| {side} | {tn} | {verdict} | {v} |")

print("\n## Ignition(17)の貼付(自分ACTIVE・シフト補正済み。公表値: 72 = 進化体49+たね23)\n")
print(f"  総数 {ign['total']} / 進化体 {ign['進化体']} / たね {ign['たね']}")
print(f"  たねのうち同ターンに進化(名前一致の上界) {ign_basic_rescued}")

#!/usr/bin/env python3
"""damage_accuracy の新旧ペアリングの差分診断(測定専用)。

背景: off-by-one補正で突合 186/240(77.5%)→240/240、一致 87.6%→90.4%になった。
しかし新規回収54件の誤りが0件なら、回収群は元の186件と系統的に異なる
(0.876^54 ≈ 0.08%)。「対応がずれていただけ」では説明にならない。

ここでは同一のATTACKログ列に事象番号を振り、新旧両方式で「どの事象が
突合できたか」をタグ付けして、回収群と元群の組成差(Full Metal Lab の有無・
対戦相手・ターン)を直接測る。

使い方:
  cd src/input/datasets/decks/starmie-aggro && \
  python3 ../../../../../replay_analysis/damage_pairing_diff.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "src/input/datasets/decks/starmie-aggro"
sys.path.insert(0, str(DECK))
import main as champ  # noqa: E402
from cg.api import to_observation_class  # noqa: E402

LOG_ATTACK, LOG_HP, LOG_TURN_END, LOG_TURN_START, LOG_COIN = 15, 16, 3, 2, 22
FML = 1244
OUR = "Yser"


def collect(rep, me, shift):
    """damage_accuracy.collect と同じpending消費方式。shift=Trueで
    select[s]↔action[s+1](補正済み)、Falseで同一entry(旧・誤り)。
    戻り値の各行に ev(そのepのATTACKログ通し番号)を付す。"""
    steps = rep["steps"]
    pending, rows = [], []
    ev_counter = [0]

    def drain(batch):
        for i, lg in enumerate(batch):
            if lg.get("type") != LOG_ATTACK or lg.get("playerIndex") != me:
                continue
            ev = ev_counter[0]
            ev_counter[0] += 1
            aid = lg.get("attackId")
            k = next((j for j, p in enumerate(pending) if p["attackId"] == aid), None)
            if k is None:
                continue
            p = pending.pop(k)
            del pending[:k]
            dealt, coin = defaultdict(int), False
            for lg2 in batch[i + 1:]:
                t = lg2.get("type")
                if t in (LOG_ATTACK, LOG_TURN_END, LOG_TURN_START):
                    break
                if t == LOG_COIN:
                    coin = True
                if t == LOG_HP and lg2.get("playerIndex") == 1 - me:
                    dealt[lg2.get("serial")] += abs(lg2.get("value") or 0)
            rows.append(dict(**p, ev=ev, actual=dealt.get(p["foe_serial"], 0),
                             coin=coin))

    for si, step in enumerate(steps):
        if me >= len(step):
            continue
        entry = step[me]
        if entry.get("status") != "ACTIVE":
            continue
        obs_dict = entry.get("observation") or {}
        drain(obs_dict.get("logs") or [])
        sel = obs_dict.get("select")
        if shift:
            action = (steps[si + 1][me].get("action")
                      if si + 1 < len(steps) and me < len(steps[si + 1]) else None)
        else:
            action = entry.get("action")
        if not sel or not sel.get("option") or not action:
            continue
        try:
            obs = to_observation_class(obs_dict)
        except Exception:
            continue
        if obs.select is None or obs.current is None:
            continue
        state = obs.current
        my_idx = state.yourIndex if state.yourIndex is not None else me
        for oi in action:
            if not isinstance(oi, int) or oi < 0 or oi >= len(obs.select.option):
                continue
            opt = obs.select.option[oi]
            aid = getattr(opt, "attackId", None)
            if aid is None:
                continue
            try:
                pred = champ._estimate_damage(aid, state, my_idx)
            except Exception:
                pred = None
            try:
                foe = state.players[1 - my_idx].active[0]
                foe_serial, foe_id, foe_hp = foe.serial, foe.id, foe.hp
                foe_tools = tuple(t.id for t in (foe.tools or []) if t)
            except (IndexError, TypeError, AttributeError):
                foe_serial = foe_id = foe_hp = None
                foe_tools = ()
            try:
                stadium = tuple(sorted(c.id for c in (state.stadium or []) if c))
            except (TypeError, AttributeError):
                stadium = ()
            rec = dict(attackId=aid, pred=pred, foe_serial=foe_serial,
                       foe_id=foe_id, foe_hp=foe_hp, stadium=stadium,
                       turn=state.turn or 0)
            if pending and pending[-1]["attackId"] == aid:
                pending[-1] = rec
            else:
                pending.append(rec)
    return rows


def main():
    cards = {c.cardId: c for c in champ._card_db()[0].values()} if False else None
    CARDS, _ = champ._card_db()
    groups = {"共有(旧でも突合)": [], "回収(新のみ)": [], "旧のみ(消失)": []}
    pred_diff = 0
    shared_pairs = 0
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
            old = {r["ev"]: r for r in collect(rep, me, shift=False)}
            new = {r["ev"]: r for r in collect(rep, me, shift=True)}
            for ev, r in new.items():
                if ev in old:
                    groups["共有(旧でも突合)"].append(r)
                    shared_pairs += 1
                    if old[ev]["pred"] != r["pred"]:
                        pred_diff += 1
                else:
                    groups["回収(新のみ)"].append(r)
            for ev, r in old.items():
                if ev not in new:
                    groups["旧のみ(消失)"].append(r)

    print("# 新旧ペアリングの事象単位の差分\n")
    print("| 群 | n | 誤り(pred≠actual) | FMLが場 | FML+相手{M} | 中央値turn |")
    print("|---|---:|---:|---:|---:|---:|")
    for gname, rows in groups.items():
        if not rows:
            print(f"| {gname} | 0 | - | - | - | - |")
            continue
        n = len(rows)
        err = sum(1 for r in rows if r["pred"] != r.get("actual"))
        fml = sum(1 for r in rows if FML in r["stadium"])
        fml_m = 0
        for r in rows:
            if FML in r["stadium"]:
                c = CARDS.get(r["foe_id"])
                if c is not None and c.energyType == 8:
                    fml_m += 1
        turns = sorted(r["turn"] for r in rows)
        print(f"| {gname} | {n} | {err} | {fml} | {fml_m} | {turns[len(turns)//2]} |")
    print(f"\n共有群の pred 新旧不一致: {pred_diff} / {shared_pairs}")

    for gname in ("共有(旧でも突合)", "回収(新のみ)"):
        rows = groups[gname]
        foes = Counter()
        for r in rows:
            c = CARDS.get(r["foe_id"])
            foes[c.name if c else r["foe_id"]] += 1
        print(f"\n## {gname} の相手バトル場の内訳(上位8)")
        for k, v in foes.most_common(8):
            print(f"  {k}: {v}")
        atks = Counter(r["attackId"] for r in rows)
        print(f"   ワザ内訳: {dict(atks)}")

    # --- C: ワザ × FML({M}防御側) の2×2 一致率(全240件=新ペアリング全体) ---
    allrows = groups["共有(旧でも突合)"] + groups["回収(新のみ)"]

    def fml_metal(r):
        if FML not in r["stadium"]:
            return False
        c = CARDS.get(r["foe_id"])
        return c is not None and c.energyType == 8

    print("\n## C: ワザ × FML({M}防御) 別の一致率(全240件)\n")
    print("| ワザ | 条件 | n | 一致 | 一致率 |")
    print("|---|---|---:|---:|---:|")
    for aid in (1487, 1488, 1486):
        for cond, label in ((True, "FML+{M}防御"), (False, "FML無し/非{M}")):
            sub = [r for r in allrows if r["attackId"] == aid and fml_metal(r) == cond]
            if not sub:
                print(f"| {aid} | {label} | 0 | - | - |")
                continue
            hit = sum(1 for r in sub if r["pred"] == r.get("actual"))
            print(f"| {aid} | {label} | {len(sub)} | {hit} | {100*hit/len(sub):.1f}% |")

    # --- D: KO署名 — 旧ペアリングが「その攻撃でActiveをKOした事象」を落とすか ---
    print("\n## D: ActiveをKOした攻撃の比率(actual >= 決定時の相手Active HP)\n")
    print("| 群 | n | KO | KO率 |")
    print("|---|---:|---:|---:|")
    for gname in ("共有(旧でも突合)", "回収(新のみ)"):
        rows = groups[gname]
        ko = sum(1 for r in rows
                 if r.get("foe_hp") is not None and (r.get("actual") or 0) >= r["foe_hp"])
        print(f"| {gname} | {len(rows)} | {ko} | {100*ko/max(1,len(rows)):.1f}% |")
    for aid in (1487, 1488):
        rows = [r for r in allrows if r["attackId"] == aid]
        ko = sum(1 for r in rows
                 if r.get("foe_hp") is not None and (r.get("actual") or 0) >= r["foe_hp"])
        print(f"| (参考)ワザ{aid}全体 | {len(rows)} | {ko} | {100*ko/max(1,len(rows)):.1f}% |")


if __name__ == "__main__":
    main()

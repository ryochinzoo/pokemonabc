#!/usr/bin/env python3
"""Alakazam 対面の敗因機構の記述解析 (2026-07-30、ref 55058443 の N=55 から)。

**なぜこの対面か**: 55058443検死(data.md 2026-07-29)で Alakazam は
  遭遇1位 30.9%(17/55) / 敗北1位 10敗 / **較正ゲージが存在しない**
= 我々の計器の最大の盲点。writeup §6 は「カバレッジ38%」を限界として開示しているが、
**なぜ負けるのかは一度も記述していない**。追加測定ゼロ(リプレイは既にDL済)。

**ラベルの約束(playbook §7 T6)**: これは事前登録のない**記述解析**であり、
出力は全て **探索的** ラベル。効果量の主張・介入の根拠には使わない。
比較対象として同じ検死内の Archaludon(4W-8L)と全体(25W-30L)を併記し、
「Alakazam固有か / 全対面共通か」を切り分ける形でのみ読む。

使い方: python3 alakazam_autopsy.py
"""
import csv
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/yujiinoue/Documents/products/pokemonabc"
EPS = os.path.join(HERE, "eps55058443")

# 王者デッキの主要カード
STARYU, MSTARMIE, IGNITION, WATER = 1030, 1031, 17, 3
NEBULA = 1488          # Nebula Beam (210)
JETTING = 1486         # Jetting Aqua (Staryu 側の低打点攻撃)
JUDGE = 1192           # Judge (手札リセット)

RULES = [
    ("Lucario", ["Mega Lucario ex"]), ("Archaludon", ["Archaludon ex"]),
    ("Abomasnow", ["Mega Abomasnow ex"]), ("Wall", ["Crustle"]),
    ("StarmieMirror", ["Mega Starmie ex"]), ("Alakazam", ["Alakazam"]),
    ("Grimmsnarl", ["Marnie's Grimmsnarl ex"]), ("Dragapult", ["Dragapult ex"]),
    ("TR Mewtwo", ["Team Rocket's Mewtwo ex"]), ("Kangaskhan", ["Mega Kangaskhan ex"]),
    ("Garchomp", ["Cynthia's Garchomp ex", "Garchomp ex"]),
]


def load_names():
    out = {}
    with open(os.path.join(REPO, "verification/data/EN_Card_Data.csv")) as f:
        for r in csv.DictReader(f):
            st = r["Stage (Pokémon)/Type (Energy and Trainer)"] or ""
            out[int(r["Card ID"])] = (r["Card Name"], "Pokémon" in st)
    return out


def classify(opp_deck, names):
    lineup = {}
    for cid, n in opp_deck.items():
        nm, isp = names.get(cid, ("?", False))
        if isp:
            lineup[nm] = lineup.get(nm, 0) + n
    for lab, keys in RULES:
        if any(k in lineup for k in keys):
            return lab
    return "Other"


def analyse(path, seat):
    """1試合を走査して機構指標を返す。seat = 我々の agents 配列内 index。"""
    d = json.load(open(path))
    steps = d["steps"]
    m = dict(my_turns=0, nebula=0, jetting=0, attacks=0, foe_attacks=0,
             multi_atk_turns=0, _atk=set(), _fatk=set(), _judge=set(),
             prize_me_end=6, prize_foe_end=6, deck_me_end=None,
             active_msta_turns=0, first=None, judge_played=0,
             hand_sizes=[], energy_on_active=[], turns=0)
    seen_turn = set()
    for st in steps:
        if len(st) <= seat:
            continue
        o = st[seat].get("observation")
        if not isinstance(o, dict):
            continue
        cur = o.get("current")
        if not isinstance(cur, dict) or not cur.get("players"):
            continue
        if m["first"] is None:
            m["first"] = (cur.get("firstPlayer") == cur.get("yourIndex"))
        t = cur.get("turn")
        if t is not None:
            m["turns"] = max(m["turns"], t)
        me = cur["players"][cur["yourIndex"]]
        foe = cur["players"][1 - cur["yourIndex"]]
        m["prize_me_end"] = len(me.get("prize") or [])
        m["prize_foe_end"] = len(foe.get("prize") or [])
        m["deck_me_end"] = me.get("deckCount")
        act = me.get("active") or []
        a0 = act[0] if act else None
        if t is not None and t not in seen_turn:
            seen_turn.add(t)
            m["hand_sizes"].append(me.get("handCount") or 0)
            if a0:
                m["energy_on_active"].append(len(a0.get("energyCards") or []))
                if a0.get("id") == MSTARMIE:
                    m["active_msta_turns"] += 1
        # ★ログは step 間で再送される(step2 と step3 が同一配列であることを実測)。
        # 素朴に加算すると2-3倍に膨らむ(初版は9ターンで17.7攻撃・与ダメ3362という不能値を出した)。
        # ポケモンTCGは「1ターンに1回だけ攻撃」なので (turn, attackId) の集合で数えると
        # 重複計上が原理的に起きない。ダメージ総量は同様に一意化できないため計測しない。
        for lg in (o.get("logs") or []):
            pi = lg.get("playerIndex")
            if lg.get("type") == 15 and t is not None:
                aid = lg.get("attackId")
                if pi == cur["yourIndex"]:
                    m["_atk"].add((t, aid))
                else:
                    m["_fatk"].add((t, aid))
            if lg.get("type") == 10 and lg.get("cardId") == JUDGE and pi == cur["yourIndex"] \
                    and t is not None:
                m["_judge"].add(t)
    m["attacks"] = len(m["_atk"])
    m["nebula"] = len({x for x in m["_atk"] if x[1] == NEBULA})
    m["jetting"] = len({x for x in m["_atk"] if x[1] == JETTING})
    m["foe_attacks"] = len(m["_fatk"])
    m["judge_played"] = len(m["_judge"])
    # 検算: 1ターンに2種の攻撃が記録されていたら1ターン1攻撃の前提が崩れている
    turns_with_atk = {x[0] for x in m["_atk"]}
    m["multi_atk_turns"] = len(m["_atk"]) - len(turns_with_atk)
    return m


def main():
    names = load_names()
    ours = Counter(int(l.strip().rstrip(",")) for l in
                   open(os.path.join(REPO, "src/input/datasets/decks/starmie-aggro/deck.csv"))
                   if l.strip())
    meta = []
    for part in open(os.path.join(EPS, "meta.txt")).read().strip().split(","):
        ep, seat, rew, opp = part.split(":")
        meta.append((int(ep), int(seat), int(rew), opp))

    rows = []
    for ep, seat, rew, opp in meta:
        if opp in ("NONE", "SELF"):
            continue
        p = os.path.join(EPS, f"ep{ep}.json")
        d = json.load(open(p))
        if len(d.get("steps", [])) < 2:
            continue
        decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
        if decks[seat] != ours or sum(decks[1 - seat].values()) != 60:
            continue
        lab = classify(decks[1 - seat], names)
        m = analyse(p, seat)
        m.update(ep=ep, arch=lab, win=(rew == 1))
        rows.append(m)

    def agg(sel, key):
        vals = [r[key] for r in sel if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else float("nan")

    def hand_mean(sel):
        allh = [h for r in sel for h in r["hand_sizes"]]
        return sum(allh) / len(allh) if allh else float("nan")

    groups = [("Alakazam", [r for r in rows if r["arch"] == "Alakazam"]),
              ("Archaludon", [r for r in rows if r["arch"] == "Archaludon"]),
              ("ALL", rows)]

    print(f"=== Alakazam 敗因機構の記述解析 (ref 55058443、分類済み {len(rows)} 戦) ===")
    print("**探索的ラベル**: 事前登録なしの記述解析。効果量・介入根拠には使わない。\n")
    hdr = (f"{'group':<14}{'n':>4}{'W':>4}{'勝率':>7}{'総T':>6}{'自攻撃':>7}"
           f"{'Nebula':>8}{'敵攻撃':>7}{'残サイド自':>10}{'残サイド敵':>10}"
           f"{'終盤山':>7}{'手札':>6}{'Judge':>6}")
    print(hdr)
    for name, sel in groups:
        if not sel:
            continue
        w = sum(1 for r in sel if r["win"])
        print(f"{name:<14}{len(sel):>4}{w:>4}{100*w/len(sel):>6.1f}%"
              f"{agg(sel,'turns'):>6.1f}{agg(sel,'attacks'):>7.1f}"
              f"{agg(sel,'nebula'):>8.2f}{agg(sel,'foe_attacks'):>7.1f}"
              f"{agg(sel,'prize_me_end'):>10.2f}{agg(sel,'prize_foe_end'):>10.2f}"
              f"{agg(sel,'deck_me_end'):>7.1f}{hand_mean(sel):>6.2f}{agg(sel,'judge_played'):>6.2f}")

    print("\n--- Alakazam: 勝ち試合 vs 負け試合 ---")
    ala = [r for r in rows if r["arch"] == "Alakazam"]
    for name, sel in [("Alakazam WIN", [r for r in ala if r["win"]]),
                      ("Alakazam LOSS", [r for r in ala if not r["win"]])]:
        if not sel:
            continue
        print(f"{name:<14}{len(sel):>4}{'':>4}{'':>7}"
              f"{agg(sel,'turns'):>6.1f}{agg(sel,'attacks'):>7.1f}"
              f"{agg(sel,'nebula'):>8.2f}{agg(sel,'foe_attacks'):>7.1f}"
              f"{agg(sel,'prize_me_end'):>10.2f}{agg(sel,'prize_foe_end'):>10.2f}"
              f"{agg(sel,'deck_me_end'):>7.1f}{hand_mean(sel):>6.2f}{agg(sel,'judge_played'):>6.2f}")

    print("\n--- 負け方の内訳(残サイドで読む) ---")
    for name, sel in groups[:2]:
        loss = [r for r in sel if not r["win"]]
        if not loss:
            continue
        blow = sum(1 for r in loss if r["prize_me_end"] >= 5)      # ほぼ何も取れず負け
        close = sum(1 for r in loss if r["prize_me_end"] <= 2)     # 1-2枚差の接戦負け
        deck0 = sum(1 for r in loss if (r["deck_me_end"] or 99) == 0)
        print(f"{name}: {len(loss)}敗 → 一方的(残サイド>=5) {blow} / "
              f"接戦(残サイド<=2) {close} / 山切れ {deck0}")

    bad = sum(r["multi_atk_turns"] for r in rows)
    print(f"\n[検算] 同一ターンに複数種の攻撃が記録された件数 = {bad} "
          f"(0なら1ターン1攻撃の前提が成立=数え方が妥当)")

    print("\n--- Nebula(210)に一度も到達できなかった試合の割合 ---")
    for name, sel in groups:
        if not sel:
            continue
        z = sum(1 for r in sel if r["nebula"] == 0)
        print(f"{name}: {z}/{len(sel)} = {100*z/len(sel):.0f}%"
              f"   (うち敗戦 {sum(1 for r in sel if r['nebula']==0 and not r['win'])})")

    print("\n--- 攻撃の内訳(Nebula 210 vs Jetting 低打点) ---")
    for name, sel in groups:
        if not sel:
            continue
        nb = sum(r["nebula"] for r in sel); jt = sum(r["jetting"] for r in sel)
        ot = sum(r["attacks"] for r in sel) - nb - jt
        tot = max(1, nb + jt + ot)
        print(f"{name}: Nebula {nb} ({100*nb/tot:.0f}%) / Jetting {jt} ({100*jt/tot:.0f}%) / "
              f"その他 {ot} ({100*ot/tot:.0f}%)")


if __name__ == "__main__":
    main()

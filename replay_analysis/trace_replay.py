#!/usr/bin/env python3
"""Kaggle cabt episode replay tracer.

Usage: python3 trace_replay.py replay.json [--quiet]
Prints a human-readable game narrative from agent 0's perspective,
plus a per-decision list of our selects/actions.
"""

import csv
import json
import sys
from pathlib import Path

CSV = Path(__file__).resolve().parent.parent / "verification" / "data" / "EN_Card_Data.csv"

AREA = {
    1: "DECK",
    2: "HAND",
    3: "DISCARD",
    4: "ACTIVE",
    5: "BENCH",
    6: "PRIZE",
    7: "STADIUM",
    8: "ENERGY",
    9: "TOOL",
    10: "PREEVO",
    11: "PLAYER",
    12: "LOOK",
}
LOG = {
    0: "SHUFFLE",
    1: "HAS_BASIC",
    2: "TURN_START",
    3: "TURN_END",
    4: "DRAW",
    5: "DRAW_REV",
    6: "MOVE",
    7: "MOVE_REV",
    8: "SWITCH",
    9: "CHANGE",
    10: "PLAY",
    11: "ATTACH",
    12: "EVOLVE",
    13: "DEVOLVE",
    14: "MOVE_ATT",
    15: "ATTACK",
    16: "HP",
    17: "POISON",
    18: "BURN",
    19: "ASLEEP",
    20: "PARALYZED",
    21: "CONFUSED",
    22: "COIN",
    23: "RESULT",
}
SELTYPE = {
    0: "MAIN",
    1: "CARD",
    2: "ATTACHED",
    3: "CARD/ATT",
    4: "ENERGY",
    5: "SKILL",
    6: "ATTACK",
    7: "EVOLVE",
    8: "COUNT",
    9: "YES_NO",
    10: "SPECIAL",
}
OPT = {
    0: "NUM",
    1: "YES",
    2: "NO",
    3: "CARD",
    4: "TOOL",
    5: "ENERGYCARD",
    6: "ENERGY",
    7: "PLAY",
    8: "ATTACH",
    9: "EVOLVE",
    10: "ABILITY",
    11: "DISCARD",
    12: "RETREAT",
    13: "ATTACK",
    14: "END",
    15: "SKILL",
}
RESULT_REASON = {1: "0 prizes", 2: "deck out", 3: "no active pokemon", 4: "card effect"}


def card_names():
    names = {}
    attacks = {}
    with open(CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        cols = r.fieldnames
        for row in r:
            try:
                cid = int(row.get("Card ID") or row.get("CardID") or row.get("id"))
            except (TypeError, ValueError):
                continue
            names.setdefault(cid, row.get("Card Name") or row.get("Name") or "?")
    return names


def opt_str(o, names):
    t = OPT.get(o.get("type"), f"?{o.get('type')}")
    parts = [t]
    if "area" in o:
        parts.append(AREA.get(o["area"], str(o["area"])))
    for k in ("index", "playerIndex", "attackId", "number", "energyIndex"):
        if k in o:
            parts.append(f"{k[0]}{o[k]}")
    return ":".join(str(p) for p in parts)


def main():
    path = sys.argv[1]
    d = json.load(open(path))
    names = card_names()
    info = d.get("info", {})
    teams = info.get("TeamNames", ["?", "?"])
    print(
        f"=== Episode {info.get('EpisodeId')} | {teams[0]} (agent0) vs {teams[1]} (agent1) | rewards={d.get('rewards')} ==="
    )
    n = lambda cid: names.get(cid, f"#{cid}")
    turn = 0
    prev = [None, None]
    for si, step in enumerate(d["steps"]):
        # merge fresh logs from both agents' views; keep own-player events from
        # each view (draws are only visible to the owner), RESULT/COIN from view 1
        logs = []
        for ai, ag in enumerate(step):
            alogs = (ag.get("observation") or {}).get("logs") or []
            if alogs == prev[ai]:
                continue
            prev[ai] = alogs
            for L in alogs:
                t = L.get("type")
                if L.get("playerIndex") == ai or (ai == 1 and t in (22, 23)):
                    logs.append(L)
        for L in logs:
            t = L.get("type")
            p = L.get("playerIndex")
            who = teams[p][:12] if p in (0, 1) else "?"
            tag = LOG.get(t, f"?{t}")
            if t == 2:
                turn += 1
                print(f"--- turn {turn} ({who}) ---")
            elif t == 4:
                print(f"  {who} draw {n(L['cardId'])}")
            elif t == 10:
                print(f"  {who} PLAY {n(L['cardId'])}")
            elif t == 11:
                print(f"  {who} attach {n(L['cardId'])} -> {n(L['cardIdTarget'])}")
            elif t == 12:
                print(f"  {who} EVOLVE {n(L['cardIdTarget'])} -> {n(L['cardId'])}")
            elif t == 15:
                print(f"  {who} ATTACK with {n(L['cardId'])} (attackId {L.get('attackId')})")
            elif t == 16:
                print(
                    f"  {who} {n(L['cardId'])} HP {L.get('value'):+d}{' (counter)' if L.get('putDamageCounter') else ''}"
                )
            elif t == 6:
                fa, ta = AREA.get(L.get("fromArea")), AREA.get(L.get("toArea"))
                cid = L.get("cardId")
                if (
                    (fa, ta) in (("ACTIVE", "DISCARD"), ("BENCH", "DISCARD"))
                    or ta in ("PRIZE",)
                    or fa in ("PRIZE",)
                ):
                    print(f"  {who} move {n(cid)} {fa}->{ta}")
            elif t == 8:
                print(f"  {who} switch: {n(L.get('cardIdBench'))} -> active")
            elif t == 22:
                print(f"  coin: {'HEAD' if L.get('head') else 'TAIL'}")
            elif t == 23:
                r = L.get("result")
                reason = L.get("reason")
                w = teams[r] if r in (0, 1) else "DRAW"
                print(f"*** RESULT: {w} wins ({RESULT_REASON.get(reason, reason)}) ***")
        # our decision at this step
        if "--decisions" in sys.argv:
            for ai, ag in enumerate(step):
                act = ag.get("action")
                obs = ag.get("observation") or {}
                sel = obs.get("select")
                if act and sel:
                    opts = sel.get("option") or []
                    chosen = [opt_str(opts[i], names) if i < len(opts) else f"!OOB{i}" for i in act]
                    print(
                        f"    [step{si} agent{ai} {SELTYPE.get(sel.get('type'))}/ctx{sel.get('context')}] {len(opts)} opts -> {chosen}"
                    )
    print()


if __name__ == "__main__":
    main()

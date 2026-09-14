#!/usr/bin/env python3
"""ミツルの思いやり(Wally's Compassion, 1229)の本番利用率 — 記事 §2「key cards utilized」用、対戦ゼロ.

数えるもの(事前に固定):
  uses            = 自分の MAIN 選択で PLAY(7) を選び、その手札位置(option.index)のカードが 1229 だった回数
  healed_damaged  = 続く HEAL(ctx 17) 選択で選んだ対象のダメージ(maxHp−hp)が >0 だった回数
  healed_undamaged= 同対象が無傷だった回数(無駄撃ち)
  energy_returned = 対象に付いていたエネルギー枚数の合計(手札に戻る枚数)
  order_violation = 同じターンに エネ貼り(ATTACH 8)→ミツル の順で選んだ回数(貼ったエネも手札に戻る)
  no_heal_select  = HEAL 選択が続かなかった回数(対象が自動確定など)。PLAY 時点の盤面で代用集計。

規約: 自席 = steps[1] の action と deck.csv の重なり最大 / 手番 = status=="ACTIVE" /
      選択肢 = steps[N].observation.select.option / 答え = steps[N+1].action /
      PLAY の option.index = 手札位置(CLAUDE.md 罠1: 正しい) → current.players[me].hand[index].id で札を同定 /
      HEAL の option = {area: 4=ACTIVE/5=BENCH, index, playerIndex} → その位置のポケモン。
使い方: python3 replay_analysis/wally_usage.py <epsDir> <deck.csv>
"""
import json
import sys
from collections import Counter
from pathlib import Path

WALLY = 1229
MEGA = 1031
OPT_PLAY, OPT_ATTACH = 7, 8
SEL_MAIN, SEL_CARD = 0, 1
CTX_HEAL = 17
AREA_ACTIVE, AREA_BENCH = 4, 5


def resolve(ps, o):
    """HEAL 選択肢 → 盤上のポケモン dict."""
    p = ps[o.get("playerIndex", 0)]
    zone = p.get("active") if o.get("area") == AREA_ACTIVE else p.get("bench") if o.get("area") == AREA_BENCH else None
    if zone is None:
        return None
    i = o.get("index")
    return zone[i] if isinstance(i, int) and 0 <= i < len(zone) else None


def dmg(pk):
    return (pk.get("maxHp") or 0) - (pk.get("hp") or 0)


def main():
    eps, deck_csv = Path(sys.argv[1]), Path(sys.argv[2])
    ours = Counter(int(x) for x in deck_csv.read_text().split())
    c = Counter()
    energy_back = 0
    dmg_healed = []
    games = 0
    for fp in sorted(eps.glob("ep*.json")):
        try:
            rep = json.loads(fp.read_text())
        except Exception:
            c["load_error"] += 1
            continue
        steps = rep.get("steps") or []
        if len(steps) < 2:
            continue
        decks = [Counter(a.get("action") or []) for a in steps[1]]
        ov = [sum((ours & x).values()) for x in decks]
        if ov[0] == ov[1]:
            continue
        me = 0 if ov[0] > ov[1] else 1
        games += 1
        pending = None          # (turn, our board at PLAY time)
        attached_turn = None
        for si in range(len(steps) - 1):
            ag = steps[si][me] or {}
            if ag.get("status") != "ACTIVE":
                continue
            obs = ag.get("observation") or {}
            sel = obs.get("select") or {}
            opts = sel.get("option") or []
            act = (steps[si + 1][me] or {}).get("action")
            if not opts or not act or act[0] >= len(opts):
                continue
            o = opts[act[0]]
            cur = obs.get("current") or {}
            turn = cur.get("turn")
            ps = cur.get("players") or []
            if len(ps) != 2:
                continue
            mine = ps[me]
            if sel.get("type") == SEL_MAIN:
                if o.get("type") == OPT_ATTACH:
                    attached_turn = turn
                if o.get("type") == OPT_PLAY:
                    hand = mine.get("hand") or []
                    idx = o.get("index")
                    cid = hand[idx].get("id") if isinstance(idx, int) and 0 <= idx < len(hand) else None
                    if cid == WALLY:
                        c["uses"] += 1
                        if attached_turn == turn:
                            c["order_violation_attach_before_wally"] += 1
                        board = [pk for z in ("active", "bench") for pk in (mine.get(z) or []) if pk]
                        pending = (turn, board)
                        continue
            if pending is not None and sel.get("type") == SEL_CARD and sel.get("context") == CTX_HEAL:
                target = resolve(ps, o)
                if target is None:
                    c["heal_target_unresolved"] += 1
                else:
                    d = dmg(target)
                    if d > 0:
                        c["healed_damaged"] += 1
                        dmg_healed.append(d)
                    else:
                        c["healed_undamaged"] += 1
                    energy_back += len(target.get("energyCards") or [])
                    if target.get("id") == MEGA:
                        c["target_mega"] += 1
                pending = None
            elif pending is not None and turn != pending[0]:
                b = pending[1]
                c["no_heal_select"] += 1
                if b:
                    t = max(b, key=dmg)
                    if dmg(t) > 0:
                        c["no_heal_select_but_damaged_board"] += 1
                pending = None
    print(f"games={games}")
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")
    print(f"  energy_returned_total: {energy_back}")
    if dmg_healed:
        s = sorted(dmg_healed)
        print(f"  healed damage: median {s[len(s)//2]} / mean {sum(s)/len(s):.0f} / n={len(s)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""P9全譜採掘 (sub 55236642, deckswap-tarountula, 54リプレイ全量)。

問い(依頼文 2026-08-05):
  Q1 Lucario 11敗の機構 — 我々を倒した攻撃の内訳(ex/メガ vs 非ex)、敗戦の速さ、
     我々の獲得サイド → 壁テック(exワザのみ無効)で防げた損害の上界。
  Q2 Alakazam 11勝の機構 — Repelling Veil の効果無効か速度勝ちか。
     Strange Hacking(338)/Powerful Hand(1072) の使用数、我々の状態異常・被ダメカン実測。
  Q3 Mirror 0-2 の中身。 Q4 Grimmsnarl/Wall/Archaludon 各機構。 Q5 我々の下手の観測。

流儀の継承(handover-2026-08-03 §3.1/§3.4):
  - 自側同定 = steps[1] action(60枚)とのデッキ重なり (mechanism_autopsy.our_index)。
    TeamNames は表示バグがあるため使わない。
  - logs は再送される → 各視点で logs==prev を読み飛ばす (mechanism_autopsy.per_turn_view)。
  - 片視点は終局付近のイベントを落とす → 両視点を per-turn max / serialユニオンでマージ。
  - サイド計数は observation.current の prize 長の減少(状態ベース、再送に免疫)。
    最終KOは observation に現れない → 勝者の残サイドで補完 (prize_race.analyze)。
  - action は1手ずれ(step s の select ↔ step s+1 の action)だが本スクリプトは
    action を読まない(logs と state のみ)。

使い方:
  nice -n 19 python3 replay_analysis/p9_mining.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK_DIR = ROOT / "src/input/datasets/decks/deckswap-tarountula"
sys.path.insert(0, str(DECK_DIR))
from cg.api import all_attack, all_card_data  # noqa: E402

EPS = ROOT / "replay_analysis/eps55236642"
LIST = ROOT / "replay_analysis/ladder_scout/lists/55236642_list.json"
OUR_SUB = 55236642

CARDS = {c.cardId: c for c in all_card_data()}
ATTACKS = {a.attackId: a for a in all_attack()}
OUR_DECK = Counter(int(l) for l in open(DECK_DIR / "deck.csv") if l.strip())
OUR_PKMN = {cid for cid in OUR_DECK if CARDS.get(cid) and CARDS[cid].cardType == 0
            or (CARDS.get(cid) and getattr(CARDS[cid], "basic", False))}
# cardType enum: POKEMON=0 想定が外れても basic/stage で拾う
OUR_PKMN = {cid for cid in OUR_DECK
            if CARDS.get(cid) and (CARDS[cid].basic or CARDS[cid].stage1 or CARDS[cid].stage2)}
OUR_ENERGY = {cid for cid in OUR_DECK if cid not in OUR_PKMN and
              "Energy" in (CARDS[cid].name if CARDS.get(cid) else "")}
MEWTWO = 431          # ex(2枚), それ以外の我々のポケモンは全て1枚
ARTICUNO = 414        # Repelling Veil持ち
BASIC_TR = {400, 414, 431, 432, 463}  # たねのTRポケモン(Veil保護対象)
PURE_EFFECT_ATKS = {338, 1072}  # Strange Hacking / Powerful Hand(dmg0, 効果のみ)

# 対面分類(probe_autopsy.RULES を継承、先勝ち)。ミラーは重なり>=45で先に判定
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


def prize_value(cid):
    c = CARDS.get(cid)
    if not c:
        return 1
    if c.megaEx:
        return 3
    if c.ex:
        return 2
    return 1


def klass(cid):
    c = CARDS.get(cid)
    if not c:
        return "?"
    if c.megaEx:
        return "megaEx"
    if c.ex:
        return "ex"
    return "nonex"


def cname(cid):
    c = CARDS.get(cid)
    return c.name if c else str(cid)


def aname(aid):
    a = ATTACKS.get(aid)
    return a.name if a else str(aid)


def our_index(d):
    decks = [Counter(a.get("action") or []) for a in d["steps"][1]]
    ov = [sum((OUR_DECK & x).values()) for x in decks]
    if ov[0] == ov[1]:
        return None, decks
    return (0 if ov[0] > ov[1] else 1), decks


def classify(opp_deck):
    overlap = sum((OUR_DECK & opp_deck).values())
    if overlap >= 45:
        return "Mirror(tarountula)"
    lineup = {}
    for cid, n in opp_deck.items():
        c = CARDS.get(cid)
        if c and (c.basic or c.stage1 or c.stage2):
            lineup[c.name] = lineup.get(c.name, 0) + n
    for lab, keys in RULES:
        if any(k in lineup for k in keys):
            return lab
    top = sorted(lineup.items(), key=lambda kv: -kv[1])
    return "Other:" + (top[0][0] if top else "?")


# ---------- ログ走査(1視点) ----------

def walk_view(d, view, mine):
    """1視点のdedup済みログ列を歩き、ターン別イベントを返す。

    返り値:
      turn_owner: {turn: playerIndex}
      percnt:     {turn: Counter}  スカラ統計(視点間で per-key max マージする)
      ko_events:  {serial: dict}   我々のポケモンの場→トラッシュ移動(=KO)
      opp_ko_events: {serial: dict} 相手のポケモンの場→トラッシュ移動
      atk_seq:    [(turn, side, cardId, attackId)]  攻撃の並び(重複判定は呼び出し側)
    """
    prev = None
    turn = 0
    turn_owner = {}
    percnt = defaultdict(Counter)
    ko_events, opp_ko_events = {}, {}
    atk_seq = []
    last_opp_atk = None     # (cardId, attackId) 現ターン内の相手の直近攻撃
    last_my_atk = None
    for step in d["steps"]:
        ag = step[view]
        logs = (ag.get("observation") or {}).get("logs") or []
        if logs == prev:
            continue
        prev = logs
        for L in logs:
            t, p = L.get("type"), L.get("playerIndex")
            if t == 2:  # TURN_START
                turn += 1
                turn_owner[turn] = p
                last_opp_atk = None
                last_my_atk = None
            elif t == 15:  # ATTACK
                cid, aid = L.get("cardId"), L.get("attackId")
                side = "us" if p == mine else "them"
                percnt[turn][("atk", side, cid, aid)] += 1
                atk_seq.append((turn, side, cid, aid))
                if p == mine:
                    last_my_atk = (cid, aid)
                else:
                    last_opp_atk = (cid, aid)
            elif t == 6:  # MOVE_CARD
                cid, fa, ta, ser = (L.get("cardId"), L.get("fromArea"),
                                    L.get("toArea"), L.get("serial"))
                c = CARDS.get(cid)
                is_pk = bool(c and (c.basic or c.stage1 or c.stage2))
                if fa in (4, 5) and ta == 3 and is_pk:
                    ev = dict(cardId=cid, turn=turn,
                              owner_turn=turn_owner.get(turn),
                              killer=(last_opp_atk if p == mine else last_my_atk))
                    (ko_events if p == mine else opp_ko_events)[ser] = ev
                if p == mine and ta == 3 and fa == 8 and cid in OUR_ENERGY:
                    percnt[turn][("edrop", cid)] += 1
                # 我々のたね→場(Articuno入場の追跡)
                if p == mine and ta in (4, 5) and cid == ARTICUNO:
                    percnt[turn][("articuno_in",)] += 1
            elif t == 11 and p == mine:  # ATTACH
                cid, tgt = L.get("cardId"), L.get("cardIdTarget")
                if cid in OUR_ENERGY:
                    percnt[turn][("attach", cid, tgt)] += 1
            elif t == 8:  # SWITCH
                side = "us" if p == mine else "them"
                percnt[turn][("switch", side)] += 1
            elif t == 16:  # HP_CHANGE
                if L.get("putDamageCounter"):
                    v = L.get("value") or 0
                    side = "us" if p == mine else "them"
                    if v < 0:
                        percnt[turn][("dcnt_on", side)] += -v
                        if p == mine:
                            percnt[turn][("dcnt_tgt", L.get("cardId"))] += -v
                    else:
                        percnt[turn][("dcnt_off", side)] += v
            elif t in (17, 18, 19, 20, 21):  # 状態異常
                if not L.get("isRecover"):
                    side = "us" if p == mine else "them"
                    percnt[turn][("cond", t, side)] += 1
            elif t == 23:  # RESULT
                percnt[turn][("result", L.get("result"), L.get("reason"))] += 1
    return dict(turn_owner=turn_owner, percnt=percnt, ko_events=ko_events,
                opp_ko_events=opp_ko_events, n_turns=turn)


def merge_views(va, vb):
    """視点マージ: スカラは per-turn per-key max、KOイベントは serial ユニオン
    (killer が付いている方を優先)。"""
    turns = max(va["n_turns"], vb["n_turns"])
    owner = dict(vb["turn_owner"])
    owner.update(va["turn_owner"])  # 同一turnは同値のはず(公開イベント)
    percnt = defaultdict(Counter)
    for t in range(0, turns + 1):
        ca, cb = va["percnt"].get(t, Counter()), vb["percnt"].get(t, Counter())
        for k in set(ca) | set(cb):
            percnt[t][k] = max(ca[k], cb[k])
    def uni(key):
        out = dict(vb[key])
        for ser, ev in va[key].items():
            if ser not in out or (ev.get("killer") and not out[ser].get("killer")):
                out[ser] = ev
        return out
    return dict(turn_owner=owner, percnt=percnt, n_turns=turns,
                ko_events=uni("ko_events"), opp_ko_events=uni("opp_ko_events"))


# ---------- 状態走査(prize_race流儀) ----------

def board_of(ps, pi):
    b = {}
    for zone in ("active", "bench"):
        for pk in ps[pi].get(zone) or []:
            if pk and pk.get("serial") is not None:
                b[pk["serial"]] = pk.get("id")
    return b


def active_of(ps, pi):
    out = []
    for pk in ps[pi].get("active") or []:
        if pk:
            out.append(pk.get("id"))
    return out


def state_walk(rep, me):
    states = []
    for step in rep["steps"]:
        for e in step:
            if e.get("status") == "ACTIVE":
                c = (e.get("observation") or {}).get("current")
                if c:
                    states.append(c)
                break
    if not states:
        return None
    turn_first, turn_order, turn_active = {}, [], {}
    drops = []
    prev = None
    setup_done = False
    for cur in states:
        ps = cur.get("players") or []
        if len(ps) < 2:
            continue
        pz = (len(ps[0].get("prize") or []), len(ps[1].get("prize") or []))
        t = cur.get("turn") or 0
        if t not in turn_first:
            turn_first[t] = [board_of(ps, 0), board_of(ps, 1)]
            turn_active[t] = [active_of(ps, 0), active_of(ps, 1)]
            turn_order.append(t)
        if not setup_done:
            if pz == (6, 6):
                setup_done = True
            prev = pz
        elif pz[0] > prev[0] or pz[1] > prev[1]:
            pass  # 陳腐化視点は読み飛ばし(prevは進めない)
        else:
            for pi in (0, 1):
                dl = prev[pi] - pz[pi]
                if dl > 0:
                    drops.append((t, pi, dl))
            prev = pz
    last = states[-1]
    ps = last.get("players") or []
    final_boards = [board_of(ps, 0), board_of(ps, 1)] if len(ps) == 2 else None

    merged = {}
    for t, pi, k in drops:
        merged[(t, pi)] = merged.get((t, pi), 0) + k
    kos = []
    for (t, pi), k in sorted(merged.items()):
        victim = 1 - pi
        b0 = turn_first.get(t, [None, None])[victim]
        nxt = [u for u in turn_order if u > t]
        b1 = (turn_first[nxt[0]][victim] if nxt
              else (final_boards[victim] if final_boards else None))
        gone = []
        if b0 is not None and b1 is not None:
            gone = [(klass(cid), cname(cid)) for s, cid in b0.items() if s not in b1]
        kos.append(dict(turn=t, taker=("us" if pi == me else "them"), k=k, gone=gone))

    res = last.get("result", -1)
    if res not in (0, 1):
        rw = rep.get("rewards") or []
        if len(rw) == 2 and rw[0] is not None and rw[1] is not None:
            res = 0 if rw[0] > rw[1] else (1 if rw[1] > rw[0] else -1)
    if res not in (0, 1):
        return None
    winner, loser = res, 1 - res
    loser_deck = ps[loser].get("deckCount") if len(ps) == 2 else None
    r_win = len(ps[winner].get("prize") or []) if len(ps) == 2 else None
    final_ko = None
    if loser_deck == 0:
        ending = "山札切れ"
    else:
        ending = "KO決着"
        victim = None
        if turn_order and final_boards:
            t_last = turn_order[-1]
            b0 = turn_first.get(t_last, [None, None])[loser]
            if b0 is not None:
                g = [(klass(cid), cname(cid)) for s, cid in b0.items()
                     if s not in final_boards[loser]]
                if len(g) == 1:
                    victim = g[0]
                elif g:
                    victim = ("複数", "+".join(x[1] for x in g))
        if r_win and r_win > 0:
            final_ko = dict(taker=("us" if winner == me else "them"), k=r_win,
                            victim=victim)
    us = sum(m["k"] for m in kos if m["taker"] == "us")
    them = sum(m["k"] for m in kos if m["taker"] == "them")
    if final_ko:
        if final_ko["taker"] == "us":
            us += final_ko["k"]
        else:
            them += final_ko["k"]
    # Articuno在場ターン数 / 我々のActiveがたねTRのターン数(視点=stateのturn)
    art_turns = sum(1 for t in turn_order if ARTICUNO in turn_first[t][me].values())
    basictr_active = sum(1 for t in turn_order
                         if turn_active[t][me] and all(c in BASIC_TR for c in turn_active[t][me]))
    my_final_board = len(final_boards[me]) if final_boards else None
    my_board_max = max((len(turn_first[t][me]) for t in turn_order), default=0)
    return dict(win=(res == me), us=us, them=them, kos=kos, ending=ending,
                final_ko=final_ko, loser_deck=loser_deck, n_state_turns=len(turn_order),
                art_turns=art_turns, basictr_active=basictr_active,
                my_final_board=my_final_board, my_board_max=my_board_max)


# ---------- メイン ----------

def main():
    lst = json.load(open(LIST))
    eps = [e for e in lst["episodes"] if e.get("state") == "COMPLETED"]
    eps.sort(key=lambda e: e["createTime"])
    validation = eps[0]["id"]
    meta = {}
    for e in eps:
        me_a = next(a for a in e["agents"] if a.get("submissionId") == OUR_SUB)
        op_a = next((a for a in e["agents"] if a is not me_a), {})
        meta[e["id"]] = dict(reward=me_a.get("reward"), opp_sub=op_a.get("submissionId"),
                             our_score=me_a.get("initialScore"),
                             opp_score=op_a.get("initialScore"),
                             create=e["createTime"])

    games = []
    for f in sorted(EPS.glob("ep*.json")):
        ep = int(f.stem[2:])
        if ep == validation:
            continue
        if ep not in meta:
            print(f"!! ep{ep}: 一覧に無い、除外", file=sys.stderr)
            continue
        d = json.loads(f.read_text())
        mine, decks = our_index(d)
        if mine is None:
            print(f"!! ep{ep}: 自側同定不能、除外", file=sys.stderr)
            continue
        opp_deck = decks[1 - mine]
        label = classify(opp_deck)
        va = walk_view(d, mine, mine)
        vb = walk_view(d, 1 - mine, mine)
        mg = merge_views(va, vb)
        st = state_walk(d, mine)
        first_player = mg["turn_owner"].get(1)
        g = dict(ep=ep, mine=mine, label=label, opp_deck=opp_deck,
                 reward=meta[ep]["reward"], opp_sub=meta[ep]["opp_sub"],
                 our_score=meta[ep]["our_score"], opp_score=meta[ep]["opp_score"],
                 first=("us" if first_player == mine else "them"),
                 merged=mg, st=st)
        games.append(g)
    out = dict(games=games, validation=validation)
    report(out)


def agg_percnt(mg):
    tot = Counter()
    for t, c in mg["percnt"].items():
        tot.update(c)
    return tot


def result_reason(g):
    """RESULTログ(type23)から終局理由を返す。無ければNone。
    reason: 1=サイド0 2=山札0 3=バトル場空 4=カード効果"""
    for k, v in agg_percnt(g["merged"]).items():
        if k[0] == "result":
            return k[1], k[2]
    return None, None


REASON_JA = {1: "サイド取り切り", 2: "山札切れ", 3: "バトル場空(盤面全滅)", 4: "カード効果"}


def ending_of(g):
    _, reason = result_reason(g)
    if reason is not None:
        return REASON_JA.get(reason, f"reason{reason}")
    return g["st"]["ending"] if g["st"] else "?"


def report(out):
    games = out["games"]
    print(f"# P9採掘 対外戦 N={len(games)} (検証ep{out['validation']}除外)")
    by = defaultdict(list)
    for g in games:
        by[g["label"]].append(g)
    print(f"\n{'対面':<22}{'W-L':>7}{'distinct相手':>12}")
    for lab, gs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        w = sum(1 for g in gs if g["reward"] == 1)
        l = len(gs) - w
        ds = len({g["opp_sub"] for g in gs})
        print(f"{lab:<22}{f'{w}-{l}':>7}{ds:>12}")

    # ---- Q1 Lucario ----
    print("\n\n=== Q1: Lucario ===")
    lus = by.get("Lucario", [])
    losses = [g for g in lus if g["reward"] != 1]
    wins = [g for g in lus if g["reward"] == 1]
    print(f"N={len(lus)} (W{len(wins)}-L{len(losses)}), distinct={len({g['opp_sub'] for g in lus})}")
    # 相手デッキの中身(頻度)
    dk = Counter()
    for g in lus:
        for cid, n in g["opp_deck"].items():
            c = CARDS.get(cid)
            if c and (c.basic or c.stage1 or c.stage2):
                dk[c.name] += 1
    print("相手デッキのポケモン(出現デッキ数):", dict(dk.most_common()))
    kill_cls = Counter()          # KO打点の attacker class
    kill_atk = Counter()          # (attacker, attack)
    prize_by_cls = Counter()      # 献上サイドの attacker class 別
    unattr = 0
    our_victims = Counter()
    for g in losses:
        for ser, ev in g["merged"]["ko_events"].items():
            our_victims[cname(ev["cardId"])] += 1
            pv = prize_value(ev["cardId"])
            if ev["killer"]:
                kcid, kaid = ev["killer"]
                kill_cls[klass(kcid)] += 1
                kill_atk[(cname(kcid), aname(kaid))] += 1
                prize_by_cls[klass(kcid)] += pv
            else:
                own = ev.get("owner_turn")
                lab = "self/effect(自ターン)" if own is not None and own == g["mine"] else "no-attack"
                kill_cls[lab] += 1
                prize_by_cls[lab] += pv
                unattr += 1
    print("\n敗戦11本の我々のKOされ(ログ可視分):")
    print("  犠牲者:", dict(our_victims.most_common()))
    print("  KO打点のattacker class:", dict(kill_cls.most_common()))
    print("  KO打点の(attacker, attack):", {f"{a}/{b}": v for (a, b), v in kill_atk.most_common()})
    print("  献上サイド(可視KOのみ)のclass別:", dict(prize_by_cls.most_common()))
    tot_pv = sum(prize_by_cls.values())
    exm = prize_by_cls.get("megaEx", 0) + prize_by_cls.get("ex", 0)
    if tot_pv:
        print(f"  ★壁テック上界: ex/メガ打点由来の献上 {exm}/{tot_pv} = {100*exm/tot_pv:.0f}%")
    print("\n敗戦の明細:")
    print("ep        先手 ターン 我々サイド:相手 終局   我々のKOされ(killer)")
    for g in sorted(losses, key=lambda x: x["ep"]):
        st = g["st"]
        kos = "; ".join(
            f"{cname(ev['cardId'])}<-{(cname(ev['killer'][0]) + '/' + aname(ev['killer'][1])) if ev['killer'] else 'no-atk'}"
            for ser, ev in sorted(g["merged"]["ko_events"].items(), key=lambda kv: kv[1]["turn"]))
        ua = sum(v for k, v in agg_percnt(g["merged"]).items() if k[0] == "atk" and k[1] == "us")
        print(f"ep{g['ep']} {g['first']:>4} {g['merged']['n_turns']:>4} "
              f"{st['us']}:{st['them']}  {ending_of(g)}  盤面終{st['my_final_board']}/最大{st['my_board_max']} "
              f"我々の攻撃{ua}回  {kos}")
    # 相手の攻撃の全量(KO打点だけでなく)
    atk_all = Counter()
    for g in losses:
        tot = agg_percnt(g["merged"])
        for k, v in tot.items():
            if k[0] == "atk" and k[1] == "them":
                atk_all[(cname(k[2]), aname(k[3]), klass(k[2]))] += v
    print("\n敗戦中の相手の攻撃全量:", {f"{a}/{b}[{c}]": v for (a, b, c), v in atk_all.most_common()})
    for g in wins:
        st = g["st"]
        tot = agg_percnt(g["merged"])
        ua = Counter()
        for k, v in tot.items():
            if k[0] == "atk" and k[1] == "us":
                ua[(cname(k[2]), aname(k[3]))] += v
        kw = "; ".join(f"{cname(ev['cardId'])}" for _, ev in g["merged"]["opp_ko_events"].items())
        print(f"\n勝ち: ep{g['ep']} 先手={g['first']} turns={g['merged']['n_turns']} "
              f"我々{st['us']}:{st['them']} {ending_of(g)} 我々の攻撃={dict((f'{a}/{b}', v) for (a, b), v in ua.most_common())} "
              f"相手のKOされ=[{kw}]")

    # ---- Q2 Alakazam ----
    print("\n\n=== Q2: Alakazam ===")
    als = by.get("Alakazam", [])
    print(f"N={len(als)}, distinct={len({g['opp_sub'] for g in als})}")
    variants = Counter()
    for g in als:
        has245 = 245 in g["opp_deck"]
        has743 = 743 in g["opp_deck"]
        variants[("245" if has245 else "") + ("+743" if has743 else "")] += 1
    print("相手のAlakazam変種(245=StrangeHacking / 743=PowerfulHand):", dict(variants))
    # ryotaゲージとの重なり
    ry = Counter(int(l) for l in open(ROOT / "verification/decks/ryota_alakazam_2026-07-05.csv")
                 if l.strip())
    ovl = [sum((ry & g["opp_deck"]).values()) for g in als]
    print(f"ryotaゲージデッキとの重なり(60中): min={min(ovl)} med={sorted(ovl)[len(ovl)//2]} max={max(ovl)}")
    for g in als:
        st = g["st"]
        tot = agg_percnt(g["merged"])
        eff = sum(v for k, v in tot.items() if k[0] == "atk" and k[1] == "them" and k[3] in PURE_EFFECT_ATKS)
        oth = sum(v for k, v in tot.items() if k[0] == "atk" and k[1] == "them" and k[3] not in PURE_EFFECT_ATKS)
        conf = sum(v for k, v in tot.items() if k[0] == "cond" and k[1] == 21 and k[2] == "us")
        dcn = sum(v for k, v in tot.items() if k[0] == "dcnt_on" and k[1] == "us")
        w = "W" if g["reward"] == 1 else "L"
        tgt = Counter()
        for k, v in tot.items():
            if k[0] == "dcnt_tgt":
                lab = "たねTR" if k[1] in BASIC_TR else cname(k[1])
                tgt[lab] += v // 10
        print(f"ep{g['ep']} {w} 先手={g['first']} turns={g['merged']['n_turns']} "
              f"我々{st['us']}:{st['them']} {ending_of(g)} | 相手効果ワザ{eff} 他ワザ{oth} "
              f"我々こんらん{conf} 被ダメカン{dcn//10}個(着弾先{dict(tgt)}) | "
              f"Articuno在場{st['art_turns']}/{st['n_state_turns']}T "
              f"ActiveたねTR率{st['basictr_active']}/{st['n_state_turns']}")
    atk_al = Counter()
    for g in als:
        tot = agg_percnt(g["merged"])
        for k, v in tot.items():
            if k[0] == "atk" and k[1] == "them":
                atk_al[(cname(k[2]), aname(k[3]))] += v
    print("相手の攻撃全量(12戦):", {f"{a}/{b}": v for (a, b), v in atk_al.most_common()})

    # ---- Q3 Mirror ----
    print("\n\n=== Q3: Mirror ===")
    mrs = [g for g in games if g["label"].startswith("Mirror")]
    for g in mrs:
        st = g["st"]
        diff_add = {cname(c): n for c, n in (g["opp_deck"] - OUR_DECK).items()}
        diff_del = {cname(c): n for c, n in (OUR_DECK - g["opp_deck"]).items()}
        print(f"\nep{g['ep']} {'W' if g['reward']==1 else 'L'} 先手={g['first']} "
              f"turns={g['merged']['n_turns']} 我々{st['us']}:{st['them']} {st['ending']} "
              f"opp_sub={g['opp_sub']} score {g['our_score']:.0f} vs {g['opp_score']:.0f}")
        print(f"  相手デッキとの差分: 相手のみ={diff_add} 我々のみ={diff_del}")
        tot = agg_percnt(g["merged"])
        for side in ("us", "them"):
            seq = Counter()
            for k, v in tot.items():
                if k[0] == "atk" and k[1] == side:
                    seq[(cname(k[2]), aname(k[3]))] += v
            print(f"  {side}の攻撃:", {f"{a}/{b}": v for (a, b), v in seq.most_common()})
        kos_l = "; ".join(f"{cname(ev['cardId'])}<-{(cname(ev['killer'][0])+'/'+aname(ev['killer'][1])) if ev['killer'] else 'no-atk'}"
                          for ser, ev in sorted(g["merged"]["ko_events"].items(), key=lambda kv: kv[1]["turn"]))
        kos_w = "; ".join(f"{cname(ev['cardId'])}<-{(cname(ev['killer'][0])+'/'+aname(ev['killer'][1])) if ev['killer'] else 'no-atk'}"
                          for ser, ev in sorted(g["merged"]["opp_ko_events"].items(), key=lambda kv: kv[1]["turn"]))
        print(f"  我々のKOされ: {kos_l}")
        print(f"  相手のKOされ: {kos_w}")

    # ---- Q4 その他対面 ----
    print("\n\n=== Q4: Grimmsnarl / Wall / Archaludon / その他 ===")
    for lab in sorted(by, key=lambda x: -len(by[x])):
        if lab in ("Lucario", "Alakazam") or lab.startswith("Mirror"):
            continue
        gs = by[lab]
        print(f"\n-- {lab} (N={len(gs)}, distinct={len({g['opp_sub'] for g in gs})}) --")
        for g in gs:
            st = g["st"]
            tot = agg_percnt(g["merged"])
            oatk, uatk = Counter(), Counter()
            for k, v in tot.items():
                if k[0] == "atk" and k[1] == "them":
                    oatk[(cname(k[2]), aname(k[3]))] += v
                elif k[0] == "atk" and k[1] == "us":
                    uatk[(cname(k[2]), aname(k[3]))] += v
            kos_l = "; ".join(f"{cname(ev['cardId'])}" for _, ev in g["merged"]["ko_events"].items())
            kos_w = "; ".join(f"{cname(ev['cardId'])}" for _, ev in g["merged"]["opp_ko_events"].items())
            print(f"ep{g['ep']} {'W' if g['reward']==1 else 'L'} 先手={g['first']} "
                  f"turns={g['merged']['n_turns']} 我々{st['us']}:{st['them']} {ending_of(g)} "
                  f"盤面終{st['my_final_board']}/最大{st['my_board_max']}")
            print(f"   相手の攻撃: {dict((f'{a}/{b}', v) for (a, b), v in oatk.most_common(4))}"
                  f"  我々の攻撃: {dict((f'{a}/{b}', v) for (a, b), v in uatk.most_common(4))}")
            print(f"   我々のKOされ: [{kos_l}]  相手のKOされ: [{kos_w}]")

    # ---- Q5 我々の下手 ----
    print("\n\n=== Q5: 我々の操縦の観測(全53戦) ===")
    attach_mx = Counter()
    our_atks = Counter()
    edrop_koturn = edrop_other = 0
    sw_our_turn = sw_their_turn = 0
    for g in games:
        mg = g["merged"]
        ko_turns = {ev["turn"] for ev in mg["ko_events"].values()}
        for t, c in mg["percnt"].items():
            for k, v in c.items():
                if k[0] == "attach":
                    attach_mx[(cname(k[1]), cname(k[2]))] += v
                elif k[0] == "atk" and k[1] == "us":
                    our_atks[(cname(k[2]), aname(k[3]))] += v
                elif k[0] == "edrop":
                    if t in ko_turns:
                        edrop_koturn += v
                    else:
                        edrop_other += v
                elif k[0] == "switch" and k[1] == "us":
                    own = mg["turn_owner"].get(t)
                    if own == g["mine"]:
                        sw_our_turn += v
                    else:
                        sw_their_turn += v
    print("我々の攻撃全量(53戦):", {f"{a}/{b}": v for (a, b), v in our_atks.most_common()})
    print("\nエネ貼りマトリクス(エネ, 貼り先) 全53戦:")
    for (e, tgt), v in attach_mx.most_common():
        print(f"  {e:<28} -> {tgt:<28} {v}")
    print(f"\nエネのトラッシュ落ち: KOターン内 {edrop_koturn} / KOターン外(退却コスト・効果) {edrop_other}")
    print(f"SWITCH(我々のポケモン): 自ターン(退却/入替) {sw_our_turn} / 相手ターン(呼び出され・昇格) {sw_their_turn}")
    # 全体の被KO集計(壁テックの全対面版)+ 犠牲者別(ex負債)
    kill_cls_all = Counter()
    prize_cls_all = Counter()
    victim_all = Counter()
    victim_prize = Counter()
    for g in games:
        for ser, ev in g["merged"]["ko_events"].items():
            pv = prize_value(ev["cardId"])
            victim_all[cname(ev["cardId"])] += 1
            victim_prize[cname(ev["cardId"])] += pv
            if ev["killer"]:
                kill_cls_all[klass(ev["killer"][0])] += 1
                prize_cls_all[klass(ev["killer"][0])] += pv
            else:
                kill_cls_all["no-atk"] += 1
                prize_cls_all["no-atk"] += pv
    print("\n(参考)全53戦の我々の被KO attacker class:", dict(kill_cls_all.most_common()),
          " 献上サイド:", dict(prize_cls_all.most_common()))
    tp = sum(victim_prize.values())
    print("犠牲者別(全53戦):", dict(victim_all.most_common()))
    print("犠牲者別の献上サイド:", dict(victim_prize.most_common()))
    mp = victim_prize.get("Team Rocket's Mewtwo ex", 0)
    print(f"  Mewtwo ex(2枚負債)経由 {mp}/{tp} = {100*mp/max(1,tp):.0f}%")
    # 終局理由の全数(RESULTログの有無も検証)
    endings = Counter()
    have_result = 0
    for g in games:
        _, reason = result_reason(g)
        if reason is not None:
            have_result += 1
        endings[("W" if g["reward"] == 1 else "L", ending_of(g))] += 1
    print(f"\n終局理由の全数(RESULTログ捕捉 {have_result}/{len(games)}):")
    for (wl, e), v in sorted(endings.items()):
        print(f"  {wl} {e}: {v}")
    # サイド収支のクロスチェック(状態ベース vs ログベース)
    mism = 0
    for g in games:
        st = g["st"]
        led = sum(prize_value(ev["cardId"]) for ev in g["merged"]["ko_events"].values())
        if st["ending"] == "KO決着" and abs(st["them"] - led) > (g["st"]["final_ko"]["k"] if g["st"]["final_ko"] and g["st"]["final_ko"]["taker"] == "them" else 0):
            mism += 1
    print(f"\n整合性: 状態ベース献上サイドとログ台帳の不一致(最終KO補完を超える差) {mism}/{len(games)}戦")


if __name__ == "__main__":
    main()

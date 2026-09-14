#!/usr/bin/env python3
"""最終エージェントの「初期状態依存」プロファイル(記事 §4 Model④ 用、対戦ゼロ・保存済み replay のみ).

問い(2026-09-09 材料の旅、事前に固定):
  1. 先攻/後攻で勝率はどれだけ違うか(firstPlayer は replay の observation.current にある)
  2. 本番のマリガン率(セットアップの SETUP_ACTIVE 選択回数−1 = 自分のマリガン数)と、マリガン数別の勝率
  3. 負けは「立ち上がり不成立」か: Mega Starmie ex(1031)の着地ターン・完封(自分のサイド取得0)を勝敗で比較
  4. (任意)相手の initialScore 帯別の勝率 — ladder_scout/lists の ListEpisodes 出力があれば結合

規約(CLAUDE.md の罠1〜3に従う): 自席 = steps[1] の action(60枚)と deck.csv の重なり最大 /
  手番 = status=="ACTIVE" / 選択肢 = steps[N].observation.select.option / 答え = steps[N+1].action /
  勝敗 = replay 冒頭の rewards[自席](1=勝, -1=負, 0=引分)。

使い方:
  python3 replay_analysis/first_player_split.py <epsDir> <deck.csv> [--list <ListEpisodes.json>] [--out <profile.json>]
出力: 標準出力に集計(Wilson 95%CI 付き)、--out に1試合1行の JSON(再集計用)。
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

MEGA_ID = 1031            # Mega Starmie ex
CTX_SETUP_ACTIVE = 1
CTX_DRAW_COUNT = 38
CTX_IS_FIRST = 41


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def fmt(k, n):
    if n == 0:
        return "n=0"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100*k/n:.1f}% [{100*lo:.1f}, {100*hi:.1f}]"


def board(p):
    out = []
    for zone in ("active", "bench"):
        for pk in p.get(zone) or []:
            if pk:
                out.append(pk)
    return out


def analyze(rep, ours):
    steps = rep.get("steps") or []
    if len(steps) < 2:
        return None
    decks = [Counter(a.get("action") or []) for a in steps[1]]
    ov = [sum((ours & x).values()) for x in decks]
    if ov[0] == ov[1]:
        return None                       # ミラーで判別不能 → 除外(件数を記録)
    me = 0 if ov[0] > ov[1] else 1
    rew = rep.get("rewards") or [0, 0]
    win = 1 if rew[me] == 1 else (0 if rew[me] == -1 else None)
    first = None
    my_setup = 0
    my_dc, opp_dc = None, None
    mega_turn = None
    turns = 0
    my_prize = opp_prize = None
    mull = [0, 0]            # HAS_BASIC_POKEMON=False の回数(自席の ACTIVE 観測の logs から。INACTIVE 観測は再送なので読まない)
    toss = None              # (誰がコイントスに勝って IS_FIRST を選んだか, 先攻を選んだか)
    for si, st in enumerate(steps):
        for pi, e in enumerate(st):
            if e.get("status") != "ACTIVE":
                continue
            obs = e.get("observation") or {}
            if pi == me:
                for lg in obs.get("logs") or []:
                    if lg.get("type") == 1 and lg.get("hasBasicPokemon") is False and lg.get("playerIndex") in (0, 1):
                        mull[lg["playerIndex"]] += 1
            sel0 = obs.get("select") or {}
            if sel0.get("context") == CTX_IS_FIRST and si + 1 < len(steps):
                ans = (steps[si + 1][pi] or {}).get("action") or []
                opts = sel0.get("option") or []
                if ans and ans[0] < len(opts):
                    toss = (pi == me, opts[ans[0]].get("type") == 1)   # type 1 = YES(先攻を取る)
            cur = obs.get("current") or {}
            if cur:
                fp = cur.get("firstPlayer")
                if first is None and fp in (0, 1):
                    first = fp
                t = cur.get("turn") or 0
                turns = max(turns, t)
                ps = cur.get("players") or []
                if len(ps) == 2:
                    my_prize = len(ps[me].get("prize") or [])
                    opp_prize = len(ps[1 - me].get("prize") or [])
                    if mega_turn is None and any((pk.get("id") == MEGA_ID) for pk in board(ps[me])):
                        mega_turn = t
            sel = obs.get("select") or {}
            if not sel or not sel.get("option"):
                continue
            ctx = sel.get("context")
            if pi == me and ctx == CTX_SETUP_ACTIVE:
                my_setup += 1
            if ctx == CTX_DRAW_COUNT:
                n_extra = len(sel["option"]) - 1
                if pi == me:
                    my_dc = n_extra          # 相手のマリガン数(自分が引ける追加枚数)
                else:
                    opp_dc = n_extra         # 自分のマリガン数(相手が引ける追加枚数)
    return dict(
        ep=rep.get("id"), me=me, win=win, first=(first == me) if first is not None else None,
        my_mull=mull[me], opp_mull=mull[1 - me], my_mull_x=opp_dc, opp_mull_x=my_dc,
        toss_mine=(toss[0] if toss else None), toss_took_first=(toss[1] if toss else None),
        mega_turn=mega_turn, turns=turns,
        my_prize_left=my_prize, opp_prize_left=opp_prize,
    )


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    eps, deck_csv = Path(args[0]), Path(args[1])
    list_path = Path(sys.argv[sys.argv.index("--list") + 1]) if "--list" in sys.argv else None
    out_path = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    ours = Counter(int(x) for x in deck_csv.read_text().split())
    rows, skipped, errors = [], 0, 0
    for fp in sorted(eps.glob("ep*.json")):
        try:
            rep = json.loads(fp.read_text())
        except Exception:
            errors += 1
            continue
        r = analyze(rep, ours)
        if r is None:
            skipped += 1
            continue
        r["ep"] = int(fp.stem[2:])          # ファイル名 ep<id>.json が episode id(replay 内の id は信用しない)
        rows.append(r)

    # 任意: 相手 initialScore の結合
    if list_path and list_path.exists():
        # 自分の agent は submissionId で同定する(list の agents 順は replay の席順と一致しない: 'index' が別にある)
        sub_id = int(sys.argv[sys.argv.index("--sub") + 1]) if "--sub" in sys.argv else int(list_path.stem.split("_")[0])
        d = json.loads(list_path.read_text())
        eplist = d.get("episodes") if isinstance(d, dict) else d
        score = {}
        for e in eplist or []:
            ags = e.get("agents") or []
            mine = [a for a in ags if a.get("submissionId") == sub_id]
            theirs = [a for a in ags if a.get("submissionId") != sub_id]
            if len(mine) == 1 and len(theirs) == 1:
                score[e.get("id")] = (mine[0].get("initialScore"), theirs[0].get("initialScore"), mine[0].get("reward"))
        for r in rows:
            s = score.get(r["ep"])
            if s:
                r["my_score"], r["opp_score"], r["list_reward"] = s
        mism = sum(1 for r in rows if r.get("list_reward") is not None and r["win"] is not None
                   and (1 if r["list_reward"] == 1 else 0 if r["list_reward"] == -1 else None) != r["win"])
        print(f"list 結合: {sum(1 for r in rows if 'opp_score' in r)}/{len(rows)} 譜、勝敗の不一致(席判定の検算) {mism}")

    decided = [r for r in rows if r["win"] is not None]
    W = sum(r["win"] for r in decided)
    print(f"games={len(rows)} (skipped mirror/undecidable={skipped}, load errors={errors}); decided={len(decided)} W={W} "
          f"draws={len(rows)-len(decided)}")
    print("\n## 先攻/後攻")
    for label, cond in (("先攻", True), ("後攻", False)):
        g = [r for r in decided if r["first"] is cond]
        print(f"  {label}: {fmt(sum(r['win'] for r in g), len(g))}")
    unk = [r for r in decided if r["first"] is None]
    print(f"  先後不明: {len(unk)}")

    print("\n## コイントス")
    tm = [r for r in decided if r["toss_mine"] is not None]
    mine_won = [r for r in tm if r["toss_mine"]]
    opp_won = [r for r in tm if not r["toss_mine"]]
    print(f"  トスに勝った: 自分 {len(mine_won)} / 相手 {len(opp_won)} (記録あり {len(tm)})")
    print(f"  自分がトスに勝って先攻を取った: {sum(1 for r in mine_won if r['toss_took_first'])}/{len(mine_won)}"
          f" / 相手がトスに勝って先攻を取った: {sum(1 for r in opp_won if r['toss_took_first'])}/{len(opp_won)}")
    print(f"  自分が先攻になった試合: {fmt(sum(1 for r in decided if r['first']), len(decided))}")

    print("\n## マリガン(engine logs の HAS_BASIC_POKEMON=False を自席の ACTIVE 観測から数える)")
    mc = Counter(r["my_mull"] for r in rows)
    print("  自分の分布:", dict(sorted(mc.items())))
    # 交差検証: 相手に提示された DrawCount の追加枚数 = max(0, 自分のマリガン − 相手のマリガン) のはず(差分規則)
    chk_ok = chk_ng = 0
    for r in rows:
        exp = max(0, r["my_mull"] - r["opp_mull"])
        got = r["my_mull_x"] if r["my_mull_x"] is not None else 0
        if exp == got:
            chk_ok += 1
        else:
            chk_ng += 1
    print(f"  交差検証(差分規則 vs 相手のDrawCount選択肢−1): 一致 {chk_ok} / 不一致 {chk_ng}")
    m1 = sum(1 for r in rows if r["my_mull"] >= 1)
    print(f"  マリガン率(≥1回): {fmt(m1, len(rows))}  (4たね/60枚の超幾何期待値 60.1%)")
    for k in sorted(mc):
        g = [r for r in decided if r["my_mull"] == k]
        print(f"  マリガン{k}回の勝率: {fmt(sum(r['win'] for r in g), len(g))}")
    g0 = [r for r in decided if r["my_mull"] == 0]
    g1 = [r for r in decided if r["my_mull"] >= 1]
    print(f"  マリガン0回 vs ≥1回: {fmt(sum(r['win'] for r in g0), len(g0))} vs {fmt(sum(r['win'] for r in g1), len(g1))}")
    oc = Counter(r["opp_mull"] for r in rows)
    print("  相手のマリガン分布:", dict(sorted(oc.items())),
          f"/ 相手≥1回 {sum(1 for r in rows if r['opp_mull'] >= 1)}/{len(rows)}")

    print("\n## 立ち上がり(Mega Starmie ex 着地ターン)と完封")
    for label, cond in (("勝ち", 1), ("負け", 0)):
        g = [r for r in decided if r["win"] == cond]
        mt = [r["mega_turn"] for r in g if r["mega_turn"] is not None]
        no = sum(1 for r in g if r["mega_turn"] is None)
        mt_s = sorted(mt)
        med = mt_s[len(mt_s) // 2] if mt_s else float("nan")
        by3 = sum(1 for t in mt if t <= 3)
        shut = sum(1 for r in g if r["my_prize_left"] == 6)
        tl = sorted(r["turns"] for r in g)
        print(f"  {label} n={len(g)}: 着地 中央値T{med} / T3以内 {fmt(by3, len(g))} / 着地せず {no} / "
              f"自分のサイド取得0(完封) {shut} / 試合長 中央値 {tl[len(tl)//2] if tl else 'nan'} ターン")

    if any("opp_score" in r for r in rows):
        print("\n## 相手 initialScore 帯別")
        bands = defaultdict(list)
        for r in decided:
            if "opp_score" in r and r["opp_score"] is not None:
                bands[int(r["opp_score"] // 100) * 100].append(r["win"])
        for b in sorted(bands):
            print(f"  {b}-{b+99}: {fmt(sum(bands[b]), len(bands[b]))}")
        sc = sorted(r["opp_score"] for r in rows if r.get("opp_score") is not None)
        if sc:
            print(f"  相手 initialScore 中央値 {sc[len(sc)//2]:.1f} / IQR {sc[len(sc)//4]:.1f}〜{sc[3*len(sc)//4]:.1f} / n={len(sc)}")

    if out_path:
        out_path.write_text(json.dumps(dict(eps_dir=str(eps), deck=str(deck_csv), games=rows,
                                            skipped=skipped, errors=errors), ensure_ascii=False))
        print(f"-> {out_path}")


if __name__ == "__main__":
    main()

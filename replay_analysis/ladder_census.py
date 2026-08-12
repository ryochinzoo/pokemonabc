#!/usr/bin/env python3
"""上位ラダーの悉皆調査 — leaderboard 起点で、当たったことのない相手のデッキを集める。

**なぜ必要か**: 我々は 678 帯にいる。マッチングはレートが近い者同士を当てるので、
1,100〜1,224 帯の構築は**原理的に我々のリプレイに写らない**。既存の ladder_scout は
`opponents.json`(＝自分のリプレイ由来の遭遇一覧)を種にしているため、この盲点を
構造的に埋められない。デッキ選択は我々の最大のレバーなのに、上位が何を使っているかを
見る手段が無かった。

    leaderboard → team_submissions → list_episodes → 先頭3MB → steps[1] の60枚

**設計の要**: 60枚は `agent(obs)` が `obs.select is None` のとき返す値、つまり
**提出物の一部で、その提出の全エピソードを通じて固定**。よって1提出につき1本読めば
デッキが確定する。全エピソードを舐める必要は無い。保険として2本読んで突き合わせ、
食い違ったら `deckVaries` を立てる(理論上デッキを乱択するエージェントがありうる)。

**ついでに拾えるもの(追加リクエストゼロ)**:
  - 勝敗と n: `list_episodes` の応答は全エピソード分の `reward` を含む
  - 対戦相手のデッキ: 先頭3MBには**両者の**60枚が入っている。相手側も1行書く
    (rank=None の「野良」行。上位N の集計からは外し、母集団としてだけ使う)

取得は全て kaggle_gate 経由(8秒間隔・429で4時間停止、playbook §8)。
`Cooldown` で落ちても種と既取得分は残り、再実行で差分だけ進む。

    python3 replay_analysis/ladder_census.py seed [topN]   # 種を作る(既定100)
    python3 replay_analysis/ladder_census.py mine [maxSubs] # 消化する(中断・再開可)
    python3 replay_analysis/ladder_census.py report [topN]  # 集計を出す
    python3 replay_analysis/ladder_census.py normalize     # deckVaries を未確認=null に揃える
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import kaggle_cli
import kaggle_gate
from band_meta_census import NAMES, band, classify_a, classify_b, top_pokemon
from ladder_scout import decks_from_text

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LAKE = HERE / "lake"
TARGETS = LAKE / "targets.json"
STORE = LAKE / "rival_decks.jsonl"

OUR_DECK = REPO / "src/input/datasets/decks/deckswap-tarountula-v2/deck.csv"
# デッキ確定に要るのは1本。2本目は「デッキを乱択するエージェント」検出の保険だったが、
# 1提出あたり1リクエスト(8秒 + 4MB転送)を丸ごと足すのに対し、
# 自チーム55308422の譜5本すべてでデッキが同一だったこと(2026-08-09実測)と、
# 60枚が `agent()` の返り値=提出物の一部という構造から、保険の価値は低いと判断。
# 疑わしい行が出たらその提出だけ EPS_PER_SUB=2 で取り直せばよい。
EPS_PER_SUB = 1
EPS_ATTEMPTS = 4         # 適応読みでも steps[1] に届かない譜がありうるので次の譜へ回す上限


# ---------------------------------------------------------------- 保存まわり

def _load_rows(dedupe=True):
    """JSONL を読む。既定では1提出1行に畳む。

    同じ提出が「順位つきの行」と「相手側として拾った野良の行」の両方で書かれうるので、
    情報量の多い順位つきを優先して残す(追記式なので古い行を消しには行かない)。
    """
    if not STORE.exists():
        return []
    out = []
    for line in STORE.open():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    if not dedupe:
        return out
    best = {}
    for r in out:
        cur = best.get(r["sub"])
        if cur is None or (cur.get("rank") is None and r.get("rank") is not None):
            best[r["sub"]] = r
    return list(best.values())


def _append(row):
    LAKE.mkdir(parents=True, exist_ok=True)
    with STORE.open("a") as f:
        f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- seed

def seed(top_n=100):
    """leaderboard 上位 top_n の稼働中提出を targets.json に並べる。

    1チーム1リクエスト。途中で落ちても既に引けた分は残り、再実行で続きから。
    """
    LAKE.mkdir(parents=True, exist_ok=True)
    targets = json.loads(TARGETS.read_text()) if TARGETS.exists() else []
    done_teams = {t["teamId"] for t in targets}

    teams = kaggle_cli.leaderboard(top_n)
    print(f"leaderboard 上位{len(teams)}チーム取得 "
          f"(既知{len(done_teams)}チーム / 目標{top_n})")

    for t in teams:
        if t["teamId"] in done_teams:
            continue
        try:
            subs = kaggle_cli.team_submissions(t["teamId"])
        except kaggle_gate.Cooldown as e:
            print(f"  中断: {e}\n  → targets.json に{len(targets)}件保存済み。再実行で続きから")
            TARGETS.write_text(json.dumps(targets, ensure_ascii=False, indent=1))
            return 1
        for s in subs:
            targets.append({"rank": t["rank"], "team": t["teamName"], "teamId": t["teamId"],
                            "teamScore": t["score"], "sub": s["sub"], "subScore": s["score"],
                            "dateSubmitted": s["dateSubmitted"]})
        done_teams.add(t["teamId"])
        TARGETS.write_text(json.dumps(targets, ensure_ascii=False, indent=1))
        print(f"  #{t['rank']:>3} {t['teamName'][:28]:<28} {t['score']:>7.1f} "
              f"→ 稼働提出{len(subs)}件", flush=True)

    print(f"seed 完了: {len(done_teams)}チーム / 提出{len(targets)}件 → {TARGETS}")
    return 0


# ---------------------------------------------------------------- mine

def _fetch_decks(ep_id):
    """steps[1] が読めた時点で接続を切る適応読み。

    3MB固定で切ると steps[0] が太い譜(対面によって膨らむ)を取りこぼす —
    ローカル48件で約20%。kaggle_gate.fetch_replay_prefix の docstring 参照。
    """
    box = {}

    def stop(txt):
        dk = decks_from_text(txt)
        if dk:
            box["dk"] = dk
            return True
        return False

    txt = kaggle_gate.fetch_replay_prefix(ep_id, stop_when=stop)
    return box.get("dk") or (decks_from_text(txt) if txt else None)


def _seat_of(agents, sub):
    """その提出がどちらの席かを返す。ListEpisodes にしか無い情報。"""
    for i, a in enumerate(agents):
        if a.get("submissionId") == sub:
            return i
    return None


def _tally(episodes, sub):
    """全エピソードから勝敗とスコア推移を集計する(追加リクエストゼロ)。"""
    won = lost = drew = 0
    scores = []
    for e in episodes:
        seat = _seat_of(e.get("agents", []), sub)
        if seat is None:
            continue
        a = e["agents"][seat]
        rw = a.get("reward")
        if rw == 1:
            won += 1
        elif rw == -1:
            lost += 1
        elif rw is not None:
            drew += 1
        for k in ("initialScore", "updatedScore"):
            if a.get(k) is not None:
                scores.append(a[k])
    return won, lost, drew, scores


def _row(tgt, sub, ep, seat, deck, extra):
    a = classify_a(deck)
    b = classify_b(deck)
    row = {"sub": sub, "ep": ep, "seat": seat,
           "archA": a, "archB": b, "agree": (a == b),
           "top": top_pokemon(deck), "deck": deck}
    row.update(extra)
    if tgt:
        row.update({"rank": tgt["rank"], "team": tgt["team"], "teamId": tgt["teamId"],
                    "score": tgt["subScore"] if tgt["subScore"] is not None else tgt["teamScore"]})
    row["band"] = band(row.get("score"))
    return row


def mine(max_subs=None):
    if not TARGETS.exists():
        print("targets.json が無い。先に `seed` を走らせること")
        return 1
    targets = json.loads(TARGETS.read_text())
    target_subs = {t["sub"] for t in targets}
    seen = {r["sub"] for r in _load_rows()}
    todo = [t for t in targets if t["sub"] not in seen]
    if max_subs:
        todo = todo[:max_subs]
    print(f"mine: 未取得{len(todo)}提出 (既取得{len(seen)}) / 1提出あたり最大{EPS_ATTEMPTS}本読む")

    for k, tgt in enumerate(todo, 1):
        sub = tgt["sub"]
        if sub in seen:
            continue          # ループ中に相手側として拾えた。二重行を書かない
        try:
            data = kaggle_gate.list_episodes(sub)
            eps = [e for e in data.get("episodes", [])
                   if e.get("state") == "COMPLETED" and len(e.get("agents", [])) == 2]
            eps.sort(key=lambda e: e["id"], reverse=True)          # 新しい順
            won, lost, drew, scores = _tally(data.get("episodes", []), sub)

            got = []          # [(ep, seat, our_deck, opp_sub, opp_deck)]
            for e in eps[:EPS_ATTEMPTS]:
                seat = _seat_of(e["agents"], sub)
                if seat is None:
                    continue
                dk = _fetch_decks(e["id"])
                if not dk:
                    continue
                got.append((e["id"], seat, dk[seat],
                            e["agents"][1 - seat].get("submissionId"), dk[1 - seat]))
                if len(got) >= EPS_PER_SUB:
                    break
        except kaggle_gate.Cooldown as e:
            print(f"  中断: {e}\n  → {len(seen)}提出まで保存済み。再実行で差分だけ進む")
            return 1

        if not got:
            print(f"  [{k}/{len(todo)}] sub{sub} デッキ抽出できず(全{len(eps)}戦) — skip",
                  flush=True)
            continue

        ep, seat, deck, _, _ = got[0]
        # 譜が1本しか無いなら「変わらないことを確認した」わけではない。
        # False(確認して同一)と null(未確認)を混ぜない — 後で読む人が誤解する。
        varies = (len({tuple(g[2]) for g in got}) > 1) if len(got) >= 2 else None
        row = _row(tgt, sub, ep, seat, deck,
                   {"deckVaries": varies, "nEps": len(eps),
                    "w": won, "l": lost, "d": drew,
                    "scoreMin": min(scores) if scores else None,
                    "scoreMax": max(scores) if scores else None})
        _append(row)
        seen.add(sub)

        # 追加リクエストゼロで拾える相手側のデッキ(rank なしの「野良」行)。
        # targets に居る提出は野良で埋めない — 後で順位つきの良い行として取るため。
        for _, _, _, osub, odeck in got:
            if osub and osub not in seen and osub not in target_subs:
                _append(_row(None, osub, ep, None, odeck,
                             {"deckVaries": False, "via": "opponent"}))
                seen.add(osub)

        wr = f"{100*won/(won+lost):.0f}%" if (won + lost) else "?"
        print(f"  [{k}/{len(todo)}] #{tgt['rank']:>3} {tgt['team'][:20]:<20} sub{sub} "
              f"{row['archA'] or row['top']:<14} {won}-{lost} ({wr}) "
              f"{'⚠デッキ可変' if varies is True else ''}", flush=True)

    print(f"mine 完了 / 累計 {len(seen)} 提出 → {STORE}")
    return 0


# ---------------------------------------------------------------- report

def _our_deck():
    if not OUR_DECK.exists():
        return None
    ids = [x.strip().rstrip(",").strip() for x in OUR_DECK.read_text().split("\n")]
    return [int(x) for x in ids if x][:60]


def _hist(rows, key):
    c = Counter((r.get(key) or "(未分類)") for r in rows)
    return c.most_common()


def report(top_n=100):
    rows = _load_rows()
    if not rows:
        print("rival_decks.jsonl が空。先に seed / mine を走らせること")
        return 1
    ranked = [r for r in rows if r.get("rank") is not None and r["rank"] <= top_n]
    wild = [r for r in rows if r.get("rank") is None]

    print(f"=== 上位{top_n}ラダーのデッキ悉皆調査 ===")
    print(f"順位つき提出 {len(ranked)} / 野良(対戦相手として観測) {len(wild)} / 総 {len(rows)}\n")
    if not ranked:
        print(f"順位つきの行がまだ無い(mine が上位{top_n}に到達していない)。")
        return 1

    print("--- アーキタイプ分布(分類器A: カード名ベース) ---")
    for a, n in _hist(ranked, "archA"):
        print(f"  {a:<18} {n:>3}  {100*n/len(ranked):5.1f}%")

    dis = [r for r in ranked if not r.get("agree")]
    print(f"\n--- 分類器A/Bの不一致 {len(dis)}件 (D59: 片方の取りこぼしを黙って飲まない) ---")
    for r in dis[:15]:
        print(f"  #{r['rank']:>3} {str(r.get('team'))[:20]:<20} A={r['archA']} B={r['archB']} "
              f"top={r['top']}")

    print("\n--- 帯別の構成 ---")
    by_band = defaultdict(list)
    for r in ranked:
        if r.get("band") is not None:
            by_band[r["band"]].append(r)
    for bd in sorted(by_band, reverse=True):
        c = Counter((x.get("archA") or "(未分類)") for x in by_band[bd])
        top3 = "  ".join(f"{a}:{n}" for a, n in c.most_common(3))
        print(f"  [{bd}-{bd+99}] N={len(by_band[bd]):>3}   {top3}")

    unc = [r for r in ranked if not r.get("archA") and not r.get("archB")]
    print(f"\n--- 両分類器とも未分類 {len(unc)}件 (新アーキタイプはここに居る) ---")
    for r in unc[:20]:
        print(f"  #{r['rank']:>3} {str(r.get('team'))[:22]:<22} {str(r.get('score')):>7}  "
              f"主力={r['top']}")

    ours = _our_deck()
    if ours:
        oc = Counter(ours)
        print(f"\n--- 我々のデッキ({OUR_DECK.name}) との差分 ---")
        inc = Counter()
        for r in ranked:
            for cid in set(r["deck"]):
                inc[cid] += 1
        miss = [(n, cid) for cid, n in inc.items() if cid not in oc]
        miss.sort(reverse=True)
        print(f"  上位{top_n}で広く使われ、我々が1枚も入れていないカード(採用提出数の多い順):")
        for n, cid in miss[:20]:
            nm = NAMES.get(cid, ("?", False))[0]
            print(f"    {n:>3}/{len(ranked)} 提出  {cid:>5}  {nm}")
        unique = [cid for cid in oc if inc.get(cid, 0) == 0]
        print(f"  逆に、上位{top_n}の誰も使っていない我々のカード {len(unique)}種:")
        for cid in unique[:20]:
            nm = NAMES.get(cid, ("?", False))[0]
            print(f"    x{oc[cid]}  {cid:>5}  {nm}")
    return 0


def normalize():
    """`deckVaries` を、情報を持つ値だけに揃える。

    経緯: 本走の途中で EPS_PER_SUB を 2→1 に落とした(1提出あたり8秒+4MBを節約するため)。
    譜が1本しか無ければ「デッキが変わらないことを確認した」わけではないのに、
    当時のコードは `False` を書いていた。**確認して同一(False)と未確認を混ぜてはいけない。**
    実際に食い違いを観測した `True` だけが情報を持つので、それ以外は null にする。

    追記式JSONLを書き換える唯一の操作。走行中に実行しないこと。
    """
    if not STORE.exists():
        print("rival_decks.jsonl が無い")
        return 1
    raw = [json.loads(x) for x in STORE.open() if x.strip()]
    bak = STORE.with_suffix(".jsonl.bak")
    bak.write_text(STORE.read_text())
    changed = 0
    for r in raw:
        if r.get("deckVaries") is not True and r.get("deckVaries") is not None:
            r["deckVaries"] = None
            changed += 1
    with STORE.open("w") as f:
        for r in raw:
            f.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"normalize: {len(raw)}行中 {changed}行の deckVaries を null(未確認)に。"
          f"退避 → {bak.name}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if cmd == "seed":
        sys.exit(seed(arg or 100))
    elif cmd == "mine":
        sys.exit(mine(arg))
    elif cmd == "report":
        sys.exit(report(arg or 100))
    elif cmd == "normalize":
        sys.exit(normalize())
    else:
        print(__doc__)

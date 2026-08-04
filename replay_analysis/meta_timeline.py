#!/usr/bin/env python3
"""時系列×個体×レーティングのパネルを作る(公開範囲で我々だけが持てる三点セット)。

SUMI(74,634戦)も myso1987 も公式日次データセット由来で **rating を持たない**。
我々は ListEpisodes API(公開POST、ログイン不要)経由なので、任意の submissionId の
**全対戦履歴に createTime と両者の initialScore/updatedScore が付く**。さらに応答の
`submissions[]` に **dateSubmitted(=そのエージェントの正確な参入日時)** が入る。

これで「現職(早期参入の distinct submissionId)のレーティングが、自アーキタイプの
シェア増加とともに下がるか」= 対抗適応 vs 構成効果の分離が初めて可能になる。

規律:
  - 保存するのは ListEpisodes の応答(1件 60〜700KB)だけ。**生リプレイは取らない**
    (引き継ぎ§3.4: 1本7〜24MB、Range無視)。
  - 取得は直列・sleep 0.35s。失敗は記録して続行。
  - アーキタイプは ladder_scout/decks.jsonl(3,359体の実デッキ)から付与。
    デッキ未知の相手は unknown として率を開示する。

使い方:
  python3 replay_analysis/meta_timeline.py plan          # 標本設計を作る(lists/_plan.json)
  python3 replay_analysis/meta_timeline.py fetch         # 計画分を取得(キャッシュ、再開可)
  python3 replay_analysis/meta_timeline.py panel         # panel.jsonl と submeta.json を構築
"""
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import band_meta_census as B  # noqa: E402

HERE = Path(__file__).resolve().parent
LS = HERE / "ladder_scout"
LISTS = LS / "lists"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# アーキタイプ別の標本目標(distinct submissionId)。
# tarountula は低シェア新顔の本丸なので全数。他は participation に比例+層化。
TARGETS = {
    "tarountula": 10_000,      # 全数
    "grimmsnarl": 90,
    "alakazam": 50,
    "crustle": 40,
    "lucario": 30,
    "archaludon": 30,
    "starmie": 20,
    "dragapult": 15,
    "garchomp": 15,
}


def parse_ts(s):
    if not s:
        return None
    d = s.partition(".")[0].rstrip("Z")
    try:
        return datetime.strptime(d, "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def arch_map():
    """decks.jsonl → {sub: arch}(側の初出デッキで分類。1体だけ複数デッキ=無視できる)"""
    m = {}
    for line in open(LS / "decks.jsonl"):
        r = json.loads(line)
        for s in r["s"]:
            if s["sub"] is None or s["sub"] in m:
                continue
            m[s["sub"]] = (B.classify_b(s["d"]) or B.classify_a(s["d"]) or "other")
    return m


def harvest_dates():
    """既存+取得済みの全 _list.json / lists/*.json から dateSubmitted を回収。"""
    subdate, teamid = {}, {}
    files = (sorted(LS.glob("sub*/_list.json")) + sorted(HERE.glob("eps*/_list.json"))
             + sorted(LISTS.glob("[0-9]*.json")))
    for f in files:
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for s in d.get("submissions", []):
            subdate[s["id"]] = parse_ts(s.get("dateSubmitted"))
            teamid[s["id"]] = s.get("teamId")
    return subdate, teamid


def cached_subs():
    have = {int(p.stem) for p in LISTS.glob("[0-9]*.json")}
    have |= {int(p.parent.name[3:]) for p in LS.glob("sub*/_list.json")}
    have |= {int(p.parent.name[3:]) for p in HERE.glob("eps*/_list.json")}
    return have


def plan():
    am = arch_map()
    subdate, _ = harvest_dates()
    have = cached_subs()
    by_arch = defaultdict(list)
    for sub, a in am.items():
        if sub in B.OUR_SUBS:
            continue
        by_arch[a].append(sub)
    chosen = []
    for a, target in TARGETS.items():
        subs = by_arch.get(a, [])
        dated = sorted([s for s in subs if subdate.get(s)], key=lambda s: subdate[s])
        undated = [s for s in subs if not subdate.get(s)]
        if len(subs) <= target:
            pick = subs                        # 全数
        else:
            # 参入日で層化(等間隔)。日付未知は残枠に頭から。
            k = min(target, len(dated))
            idx = [round(i * (len(dated) - 1) / max(1, k - 1)) for i in range(k)]
            pick = [dated[i] for i in sorted(set(idx))]
            pick += undated[: target - len(pick)]
        chosen += [(s, a) for s in pick]
    todo = [(s, a) for s, a in chosen if s not in have]
    LISTS.mkdir(exist_ok=True)
    (LISTS / "_plan.json").write_text(json.dumps(
        {"chosen": chosen, "todo": todo}, indent=0))
    print("計画(distinct submissionId):")
    per = defaultdict(lambda: [0, 0])
    for s, a in chosen:
        per[a][0] += 1
        per[a][1] += (s in have)
    for a in sorted(per, key=lambda x: -per[x][0]):
        print(f"  {a:<12} 選定{per[a][0]:>4}  取得済{per[a][1]:>3}  母集合{len(by_arch[a]):>4}")
    print(f"合計 選定{len(chosen)} / 未取得{len(todo)}")


def fetch():
    """レート制限(429等)には指数バックオフで対応。キャッシュ済みは飛ばすので再開可。"""
    import urllib.error
    LISTS.mkdir(exist_ok=True)
    todo = json.loads((LISTS / "_plan.json").read_text())["todo"]
    have = {int(p.stem) for p in LISTS.glob("[0-9]*.json")}
    todo = [(s, a) for s, a in todo if s not in have]
    print(f"取得対象 {len(todo)} 体(直列、基本間隔1.2s、429は指数バックオフ)", flush=True)
    fails = []
    for k, (sub, a) in enumerate(todo, 1):
        req = urllib.request.Request(
            "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
            data=json.dumps({"submissionId": sub}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": UA})
        ok = False
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                json.loads(data)                   # 壊れた応答を保存しない
                (LISTS / f"{sub}.json").write_bytes(data)
                n = len(json.loads(data).get("episodes", []))
                print(f"  [{k}/{len(todo)}] {a} sub{sub} eps={n}", flush=True)
                ok = True
                break
            except urllib.error.HTTPError as e:
                wait = min(5 * (2 ** attempt), 120)      # 5s→倍々→上限120s(合意仕様)
                print(f"  [{k}/{len(todo)}] {a} sub{sub} HTTP {e.code} → {wait}s 待機",
                      flush=True)
                time.sleep(wait)
            except Exception as e:
                print(f"  [{k}/{len(todo)}] {a} sub{sub} {type(e).__name__} → 10s", flush=True)
                time.sleep(10)
        if not ok:
            fails.append(sub)
        time.sleep(1.2)
    print(f"完了。失敗 {len(fails)} 件: {fails[:30]}")


def panel():
    """全キャッシュから panel.jsonl(1行=追跡subの1エピソード視点)と submeta.json を作る。"""
    am = arch_map()
    subdate, teamid = harvest_dates()
    rows = []
    tracked = set()
    src = {}
    for f in (sorted(LS.glob("sub*/_list.json")) + sorted(HERE.glob("eps*/_list.json"))
              + sorted(LISTS.glob("[0-9]*.json"))):
        sub = int(f.stem if f.name != "_list.json" else f.parent.name.lstrip("subeps"))
        src[sub] = f
    for sub, f in src.items():
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        eps = data.get("episodes", [])
        n_kept = 0
        for e in eps:
            if e.get("state") != "COMPLETED":
                continue
            ags = e.get("agents", [])
            if len(ags) != 2:
                continue
            mine = [a for a in ags if a.get("submissionId") == sub]
            other = [a for a in ags if a.get("submissionId") != sub]
            if len(mine) != 1 or len(other) != 1:
                continue                      # 自己対戦(検証エピソード)は除外
            me, op = mine[0], other[0]
            t = parse_ts(e.get("createTime"))
            if t is None:
                continue
            rows.append({
                "ep": e["id"], "t": t, "sub": sub,
                "sc": me.get("initialScore"), "su": me.get("updatedScore"),
                "rw": me.get("reward"),
                "osub": op.get("submissionId"), "osc": op.get("initialScore"),
                "orw": op.get("reward")})
            n_kept += 1
        tracked.add(sub)
    rows.sort(key=lambda r: (r["sub"], r["t"]))
    with open(LS / "panel.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    meta = {}
    all_subs = set(am) | tracked | {r["osub"] for r in rows if r["osub"]}
    for s in all_subs:
        meta[s] = {"arch": am.get(s), "date": subdate.get(s),
                   "team": teamid.get(s), "tracked": s in tracked,
                   "ours": s in B.OUR_SUBS}
    (LS / "submeta.json").write_text(json.dumps(meta))
    n_arch = sum(1 for s in tracked if am.get(s))
    ep_ids = {r["ep"] for r in rows}
    print(f"panel.jsonl: {len(rows)} 視点行 / distinct エピソード {len(ep_ids)} / "
          f"追跡 {len(tracked)} 体(うちアーキタイプ既知 {n_arch})")
    opp = [r["osub"] for r in rows]
    known = sum(1 for o in opp if am.get(o))
    print(f"相手アーキタイプ既知率: {known}/{len(opp)} ({100*known/max(1,len(opp)):.1f}%) "
          "(未知率は各分析で開示)")
    dated = sum(1 for s in tracked if subdate.get(s))
    print(f"追跡体の参入日既知: {dated}/{len(tracked)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    {"plan": plan, "fetch": fetch, "panel": panel}[cmd]()

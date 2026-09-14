#!/usr/bin/env python3
"""ラダー斥候 — 多数のチームの「デッキ×スコア×勝敗」を、生リプレイを溜めずに集める。

**なぜ必要か**(2026-08-03、band_meta_census.py の汚染検査で判明):
12体スカウトでは対面行列の Lucario 系セルが **distinct 5〜11体** にしか乗っておらず、
「デッキの勝率」ではなく「そのパイロットの勝率」を測っていた(台帳#11 / D9 と同型)。
デッキとして語るには **distinct 提出数の幅**が要る。

**設計上の制約**:
- リプレイ1本が 7〜24MB。12体=510戦で **12GB** に達した。50体に広げると破綻する
- `Range` ヘッダは**サーバが無視して全量を返す**(2026-08-03 実測)
  → **ストリームを先頭 PREFIX バイトで打ち切り**、デッキだけ取って本体は保存しない
- デッキは steps[1]、勝敗とスコアは ListEpisodes 側にあるので先頭だけで足りる

出力: `replay_analysis/ladder_scout/decks.jsonl`(1行=1エピソード、追記・重複排除)

    python3 replay_analysis/ladder_scout.py ingest          # 既存の生リプレイを取り込む
    python3 replay_analysis/ladder_scout.py expand 60 20    # 上位60体×各20戦まで広げる
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = HERE / "ladder_scout"
STORE = D / "decks.jsonl"
PREFIX = 3 << 20          # 先頭3MB読めば steps[0..1] は必ず入る(実測最大 1.6MB 地点)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

OUR_SUBS = {55169074, 55163442, 55070495, 55060473, 55058443, 54961048, 54858780,
            54832323, 55032182, 55004671, 54943911, 54831270, 54830797, 54815282,
            54788435, 54727395, 54435972, 54146595}

_DEC = json.JSONDecoder()


def decks_from_text(s):
    """先頭チャンクから steps[0..1] を部分デコードして両者の60枚を返す。"""
    try:
        i = s.index('"steps"')
        i = s.index("[", i) + 1
        while s[i] in " \t\r\n":
            i += 1
        _, j = _DEC.raw_decode(s, i)              # steps[0]
        j = s.index(",", j) + 1
        while s[j] in " \t\r\n":
            j += 1
        step1, _ = _DEC.raw_decode(s, j)          # steps[1] = デッキ提出
    except (ValueError, IndexError):
        return None
    out = [a.get("action") for a in step1]
    if len(out) == 2 and all(isinstance(x, list) and len(x) == 60 for x in out):
        return out
    return None


def list_episodes(sub):
    req = urllib.request.Request(
        "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
        data=json.dumps({"submissionId": sub}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fetch_decks(ep_id):
    """本体を保存せず、先頭 PREFIX バイトだけ読んで接続を切る。"""
    url = f"https://www.kaggle.com/competitions/episodes/{ep_id}/replay.json"
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
            chunk = r.read(PREFIX)
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return None
    return decks_from_text(chunk.decode("utf-8", "ignore"))


def load_seen():
    seen = set()
    if STORE.exists():
        for line in STORE.open():
            try:
                seen.add(json.loads(line)["ep"])
            except Exception:
                pass
    return seen


def write_rows(rows):
    with STORE.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")


def row_of(ep, agents, decks):
    return {"ep": ep,
            "s": [{"sub": a.get("submissionId"),
                   "sc": a.get("initialScore") or a.get("updatedScore"),
                   "rw": a.get("reward"),
                   "d": decks[i]} for i, a in enumerate(agents)]}


def ingest():
    """既にディスクにある生リプレイを decks.jsonl に取り込む(削除はしない)。"""
    seen = load_seen()
    total = 0
    for listf in sorted(D.glob("sub*/_list.json")) + sorted(HERE.glob("eps*/_list.json")):
        meta = {e["id"]: e["agents"] for e in json.loads(listf.read_text()).get("episodes", [])
                if len(e.get("agents", [])) == 2}
        rows = []
        for f in sorted(listf.parent.glob("ep*.json")):
            ep = int(f.stem[2:])
            if ep in seen or ep not in meta:
                continue
            with open(f) as fh:
                dk = decks_from_text(fh.read(PREFIX))
            if not dk:
                continue
            rows.append(row_of(ep, meta[ep], dk))
            seen.add(ep)
        write_rows(rows)
        total += len(rows)
        print(f"  {listf.parent.name}: +{len(rows)}", flush=True)
    print(f"ingest 完了: +{total} 行 / 累計 {len(seen)}")


def expand(n_agents, per_agent):
    """未スカウトの相手を上位から広げる。生リプレイは一切保存しない。"""
    seen = load_seen()
    opponents = json.load(open(D / "opponents.json"))          # [[sub, score], ...] 降順
    done_subs = {int(p.parent.name[3:]) for p in D.glob("sub*/_list.json")}
    todo = [(s, sc) for s, sc in opponents
            if s not in done_subs and s not in OUR_SUBS][:n_agents]
    print(f"新規スカウト対象 {len(todo)}体 (各最大{per_agent}戦)、生ファイルは保存しない")
    for k, (sub, sc) in enumerate(todo, 1):
        try:
            data = list_episodes(sub)
        except Exception as e:
            print(f"  [{k}/{len(todo)}] sub{sub} LIST失敗 {type(e).__name__}", flush=True)
            continue
        meta = {e["id"]: e["agents"] for e in data.get("episodes", [])
                if e.get("state") == "COMPLETED" and len(e.get("agents", [])) == 2}
        eps = sorted(meta, reverse=True)[:per_agent]           # 新しい順
        rows = []
        for ep in eps:
            if ep in seen:
                continue
            dk = fetch_decks(ep)
            if dk:
                rows.append(row_of(ep, meta[ep], dk))
                seen.add(ep)
            time.sleep(0.2)
        write_rows(rows)
        print(f"  [{k}/{len(todo)}] sub{sub} score={sc:.0f} 総{len(meta)}戦 → +{len(rows)}",
              flush=True)
    print(f"expand 完了 / 累計 {len(seen)} エピソード")


if __name__ == "__main__":
    D.mkdir(exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ingest"
    if cmd == "ingest":
        ingest()
    elif cmd == "expand":
        expand(int(sys.argv[2]) if len(sys.argv) > 2 else 40,
               int(sys.argv[3]) if len(sys.argv) > 3 else 20)
    else:
        print(__doc__)

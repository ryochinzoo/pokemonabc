#!/usr/bin/env python3
"""Kaggle 内部API(EpisodeService)の門番 — 429を構造的に再発不能にする。

2026-08-04の事故: 並列バースト(バックオフ無しで27/46失敗)+429後の再試行連打で、
**IP単位**の制限を踏み、ログイン済みWebUIの「ゲーム履歴」まで丸1日以上巻き込んだ。
教訓は「量を減らす」ではなく「行儀」: 必要量(~800リクエスト)は 8秒/件のトリクルで2時間弱。

規律(このモジュール以外から EpisodeService を叩くことを禁止する):
  1. 直列1本のみ。最小間隔 MIN_INTERVAL 秒(既定8)。
  2. 429を1回でも受けたら**再試行せず** COOLDOWN_H 時間(既定4)完全停止。状態は
     gate_state.json に永続化され、**別プロセスから起動しても停止が引き継がれる**。
  3. キャッシュ優先: 既取得の list/replay は再取得しない(force指定時を除く)。
  4. リプレイは必要バイトだけ(デッキ抽出なら先頭3MB)。自チーム提出の検死のみ全量可。

使い方:
  python3 replay_analysis/kaggle_gate.py probe                       # 1回だけ試す(状態を更新)
  python3 replay_analysis/kaggle_gate.py list <submissionId>        # 一覧をキャッシュへ
  python3 replay_analysis/kaggle_gate.py drain-replays <submissionId> <outDir> [maxN] [full|head]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / "ladder_scout" / "gate_state.json"
LISTS = HERE / "ladder_scout" / "lists"
MIN_INTERVAL = 8.0          # 秒/リクエスト
COOLDOWN_H = 4.0            # 429後の完全停止時間
HEAD_BYTES = 3 * 1024 * 1024


def _state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _save(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st))


def _gate():
    """呼び出し前の関門: クールダウン中なら残秒を返す(呼び出し側は中止)。"""
    st = _state()
    cd = st.get("cooldown_until", 0)
    if time.time() < cd:
        return cd - time.time()
    last = st.get("last_req", 0)
    wait = MIN_INTERVAL - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    return 0


def _mark(ok):
    st = _state()
    st["last_req"] = time.time()
    if not ok:
        st["cooldown_until"] = time.time() + COOLDOWN_H * 3600
        st["last_429"] = time.time()
    _save(st)


class Cooldown(Exception):
    pass


def list_episodes(sub_id, force=False):
    LISTS.mkdir(parents=True, exist_ok=True)
    out = LISTS / f"{sub_id}_list.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    rem = _gate()
    if rem > 0:
        raise Cooldown(f"cooldown 残り{rem/60:.0f}分")
    r = subprocess.run(["curl", "-s", "-X", "POST",
        "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"submissionId": int(sub_id)})],
        capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(r.stdout)
    except Exception:
        d = {}
    if "episodes" not in d:
        _mark(ok=False)
        raise Cooldown(f"429/異常応答: {r.stdout[:80]!r} → {COOLDOWN_H}h停止(永続)")
    _mark(ok=True)
    out.write_text(r.stdout)
    return d


def fetch_replay(ep_id, out_path, full=False):
    out_path = Path(out_path)
    if out_path.exists():
        return out_path
    rem = _gate()
    if rem > 0:
        raise Cooldown(f"cooldown 残り{rem/60:.0f}分")
    url = f"https://www.kaggle.com/competitions/episodes/{ep_id}/replay.json"
    if full:
        r = subprocess.run(["curl", "-s", url, "-o", str(out_path)],
                           capture_output=True, text=True, timeout=300)
        ok = out_path.exists() and out_path.stat().st_size > 1000
    else:
        # Rangeはサーバが無視して全量を返す(2026-08-03実測)ので、転送をバイト数で打ち切る
        r = subprocess.run(["curl", "-s", "--max-filesize", str(HEAD_BYTES * 4), url,
                           "-o", str(out_path)], capture_output=True, text=True, timeout=300)
        ok = out_path.exists() and out_path.stat().st_size > 1000
    if not ok:
        txt = out_path.read_text()[:80] if out_path.exists() else ""
        if "Too many requests" in txt or not ok:
            _mark(ok=False)
            out_path.unlink(missing_ok=True)
            raise Cooldown(f"replay取得失敗 ep{ep_id} → {COOLDOWN_H}h停止")
    _mark(ok=True)
    return out_path


def main():
    cmd = sys.argv[1]
    if cmd == "probe":
        try:
            d = list_episodes(int(sys.argv[2]) if len(sys.argv) > 2 else 55163442, force=True)
            print(f"OK episodes={len(d.get('episodes', []))}")
        except Cooldown as e:
            print(f"BLOCKED: {e}")
            sys.exit(1)
    elif cmd == "list":
        d = list_episodes(int(sys.argv[2]))
        print(f"OK episodes={len(d.get('episodes', []))}")
    elif cmd == "drain-replays":
        sub = int(sys.argv[2])
        out_dir = Path(sys.argv[3])
        max_n = int(sys.argv[4]) if len(sys.argv) > 4 else 200
        full = (len(sys.argv) > 5 and sys.argv[5] == "full")
        out_dir.mkdir(parents=True, exist_ok=True)
        d = list_episodes(sub)
        eps = [e for e in d.get("episodes", []) if e.get("state") == "COMPLETED"]
        got = 0
        for e in eps[:max_n]:
            p = out_dir / f"ep{e['id']}.json"
            if p.exists():
                continue
            fetch_replay(e["id"], p, full=full)
            got += 1
            print(f"  ep{e['id']} 取得 ({got})")
        print(f"DONE 新規{got}件 / 総{len(eps)}件")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

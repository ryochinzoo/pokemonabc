#!/usr/bin/env python3
"""Kaggle 公式CLI(`kaggle competitions ...`)の薄いラッパ — 門番の律速下に置く。

**なぜラッパが要るか**: 2026-08-04 の事故は **IP単位**のブロックで、ログイン済み
WebUIの試合履歴まで丸1日以上巻き込んだ。CLI は `api.kaggle.com`、生POSTは
`www.kaggle.com` と別ホストだが、**同一IPである以上ひとつの予算**として扱う。
よって kaggle_gate の `_gate()`/`_mark()`/`gate_state.json` をそのまま共有する
(playbook §8)。直に `kaggle` を叩かず、必ずここを通すこと。

**これで開く経路**(2026-08-09 実測):

    leaderboard          → teamId, teamName, submissionDate, score (全6,307チーム)
      └→ team_submissions(teamId) → 稼働中の提出ID + publicScore
          └→ kaggle_gate.list_episodes(subId) → epID + agents[].submissionId/score

既存の ladder_scout は「実際に当たった相手」しか辿れない(opponents.json が
自分のリプレイ由来)。マッチングはレートが近い者同士を当てるので、678帯にいる
我々のリプレイに1,200帯の構築は原理的に写らない。leaderboard 起点はその盲点を埋める。

**使わないコマンドと理由**(実測の上での判断):
  - `competitions episodes`: `agents` 配列が落ちる。submissionId / reward /
    initialScore / updatedScore / teamId が全部消えるので、どちらの席が相手かを
    決められない。`kaggle_gate.list_episodes`(生POST)が上位互換。
  - `competitions replay`: 全量(2〜24MB)を落とす。頭切り取りが効かないので
    `kaggle_gate.fetch_replay_prefix`(3MB)の方が 1/8 の転送で済む。

使い方:
    python3 replay_analysis/kaggle_cli.py leaderboard [topN]
    python3 replay_analysis/kaggle_cli.py team-submissions <teamId>
"""
import csv
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

from kaggle_gate import Cooldown, _gate, _mark

COMP = "pokemon-tcg-ai-battle"      # `...-challenge` は404になる(handover-2026-08-03)
KAGGLE = os.environ.get("KAGGLE_BIN") or shutil.which("kaggle") or "kaggle"

# CLI が律速に当たったときに出す文字列。
# **裸の "429" を入れてはいけない**(2026-08-09に踏んだ): 応答本文は8桁の提出IDだらけで、
# 例えば 553742**92** ならぬ 5537**429**2 のように部分一致する。正常な200応答が
# 4時間の停止を引き起こした。判定は曖昧さのない語句だけに限ること。
_RATE_MARKERS = ("Too many requests", "Too Many Requests", "RESOURCE_EXHAUSTED",
                 "429 Client Error", "rate limit")


def _run(args, timeout=180):
    """門番を通して `kaggle` を1回だけ叩き、stdout を返す。"""
    rem = _gate()
    if rem > 0:
        raise Cooldown(f"cooldown 残り{rem/60:.0f}分")
    try:
        r = subprocess.run([KAGGLE, *args], capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        _mark(ok=True)          # 我々側の失敗。相手を叩いていないので停止しない
        raise RuntimeError(f"kaggle CLI 実行失敗: {type(e).__name__}") from e
    blob = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        # 律速の判定は**失敗した時だけ**に掛ける。成功応答の本文まで走査すると
        # 提出IDへの部分一致で誤爆する(上の _RATE_MARKERS のコメント参照)。
        if any(m in blob for m in _RATE_MARKERS):
            _mark(ok=False)
            raise Cooldown(f"CLI が律速に当たった: {blob[:160]!r} → 4h停止(永続)")
        _mark(ok=True)
        raise RuntimeError(f"kaggle {' '.join(args)} が失敗: {blob[:200]!r}")
    if any(m in blob for m in _RATE_MARKERS):
        _mark(ok=False)          # rc=0 でも本文で律速を告げてくる場合の保険
        raise Cooldown(f"CLI が律速を告知: {blob[:160]!r} → 4h停止(永続)")
    _mark(ok=True)
    return r.stdout or ""


def _rows(stdout, header0):
    """CLI の CSV 出力を dict の列にする。

    実測の癖(ここを外すと静かに壊れる):
      - `leaderboard --show -v` は CSV ヘッダの**前**に `Next Page Token = ...` を吐く
        → ヘッダ行が見つかるまで読み飛ばす
      - description 等のフィールドは**改行とカンマを含む** → split(",") ではなく
        csv.reader に行全体を渡す(引用の継続行を正しく食わせるため)
      - `--format json` は末尾に人間向けヒント行を足し、ページングで複数のJSON配列が
        連結されて出る(json.load が落ちる)。よって CSV(-v)のみを使う。
    """
    lines = stdout.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(header0):
            body = "\n".join(lines[i:])
            break
    else:
        return []
    rd = csv.DictReader(io.StringIO(body))
    # 値は必ずしも str ではない: ヘッダより列が多い行では restkey に list が入るので、
    # そのまま .strip() すると落ちる。空行だけ落としたいので str() を噛ませる。
    return [r for r in rd if any(str(v or "").strip() for v in r.values())]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def leaderboard(top=100, comp=COMP):
    """上位 top チームを順位つきで返す。`--page-size` の上限は200なので1リクエスト。

    Returns: [{"rank", "teamId", "teamName", "score", "submissionDate"}, ...]
    """
    if top > 200:
        raise ValueError("--page-size の上限は200。それ以上要るなら --download を使うこと")
    out = _run(["competitions", "leaderboard", "-c", comp, "--show", "-v",
                "--page-size", str(min(200, max(1, top)))])
    rows = _rows(out, "teamId,")
    return [{"rank": i, "teamId": int(r["teamId"]), "teamName": r["teamName"],
             "score": _num(r["score"]), "submissionDate": r["submissionDate"]}
            for i, r in enumerate(rows[:top], 1)]


def leaderboard_download(out_dir="replay_analysis/lake/leaderboard", comp=COMP):
    """順位表**全件**を1リクエストで取る(`--download` は zip の CSV)。

    `leaderboard()` は `--page-size` 上限200で上位しか見えず、我々の帯(600〜700)は圏外。
    2026-09-02 追加(記事の「r位 / T チーム」用)。

    Returns: (csv_path, rows)  rows = [{"teamId","teamName","submissionDate","score"}, ...]
    """
    import zipfile
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    _run(["competitions", "leaderboard", "-c", comp, "--download", "-p", str(out)])
    zips = sorted(out.glob("*.zip"), key=lambda z: z.stat().st_mtime)
    if not zips:
        raise RuntimeError(f"順位表の zip が {out} に無い")
    with zipfile.ZipFile(zips[-1]) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"zip に CSV が無い: {zf.namelist()}")
        data = zf.read(names[0]).decode("utf-8", "replace")
    csv_path = out / (Path(names[0]).stem + "_" + zips[-1].stem + ".csv")
    csv_path.write_text(data)
    rows = []
    for r in csv.DictReader(io.StringIO(data)):
        k = {kk.strip().lower(): vv for kk, vv in r.items() if kk}
        rows.append({"teamId": k.get("teamid"), "teamName": k.get("teamname"),
                     "submissionDate": k.get("submissiondate"), "score": _num(k.get("score"))})
    return csv_path, rows


def rank_of(score, rows):
    """`rank = 1 + #{score > ours}`(同点は同順位)。Returns: (rank, n_teams)"""
    scored = [r["score"] for r in rows if r["score"] is not None]
    return 1 + sum(1 for x in scored if x > score), len(scored)


def team_submissions(team_id):
    """あるチームの**稼働中の**提出を返す(シミュレーション競技では現役の全提出)。

    Returns: [{"sub", "dateSubmitted", "score"}, ...]
    """
    out = _run(["competitions", "team-submissions", str(int(team_id)), "-v"])
    return [{"sub": int(r["id"]), "dateSubmitted": r["dateSubmitted"],
             "score": _num(r["publicScore"])}
            for r in _rows(out, "id,")]


def our_submissions(comp=COMP):
    """自チームの提出一覧。台帳(OUR_TEAM_SUBS)の陳腐化検出に使える。

    description は改行とカンマを含むので、必ず _rows(csv.DictReader)を通すこと。
    """
    out = _run(["competitions", "submissions", "-c", comp, "-v"])
    return [{"sub": int(r["ref"]), "file": r["fileName"], "date": r["date"],
             "status": r["status"], "score": _num(r["publicScore"]),
             "desc": (r.get("description") or "").strip()}
            for r in _rows(out, "ref,")]


def kernels_list(comp=COMP, sort_by="dateCreated", page=1, page_size=200):
    """公開ノートブック一覧(1リクエスト/ページ)。2026-09-09 新設: 8/3 以降に公開された Strategy 系ノートの偵察用。"""
    out = _run(["kernels", "list", "--competition", comp, "--sort-by", sort_by, "--page-size", str(page_size), "-p", str(page), "-v"])
    rows = _rows(out, "ref,")
    return [{"ref": r.get("ref"), "title": r.get("title"), "author": r.get("author"),
             "lastRunTime": r.get("lastRunTime"), "totalVotes": r.get("totalVotes")} for r in rows]


def agent_logs(ep_id, agent_index, out_dir):
    """1エピソードぶんの**エージェントログ**を落として、そのパスを返す。

    中身は1決定につき `{duration, stdout, stderr}` の配列。**3.9KB前後**しかないのに、
    ローカルでは原理的に得られないものが2つ入っている:
      - `duration`: 本番ランナーが計った実測の思考時間。今は replay.json(136〜232MB)の
        `remainingOverageTime` から**推定**している値を、直接測れる
      - `stderr`: 「絶対にクラッシュしない」要件に対する直接証拠

    **自チーム限定**。他人のエピソードは 403(GetEpisodeAgentLogs、2026-08-09実測)。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"episode-{ep_id}-agent-{agent_index}-logs.json"
    if dst.exists():
        return dst
    _run(["competitions", "logs", str(int(ep_id)), str(int(agent_index)),
          "-p", str(out_dir), "-q"])
    return dst if dst.exists() else None


def submit(tar_path, message, comp=COMP):
    """提出を1回だけ行う。**門番(`_run`)を通す**ので律速予算を他の経路と共有する。

    playbook §8: CLI も生POSTも同じIP単位の制限を踏むので、ひとつの予算として数える。
    提出は書き込み操作なので、**再試行はしない**(二重提出は枠を1つ無駄にする)。
    """
    tar = Path(tar_path).expanduser().resolve()
    if not tar.is_file():
        raise FileNotFoundError(f"提出ファイルが無い: {tar}")
    return _run(["competitions", "submit", "-c", comp,
                 "-f", str(tar), "-m", message], timeout=600)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "leaderboard":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        for t in leaderboard(n):
            print(f"{t['rank']:>4}  {t['score']:>7.1f}  team{t['teamId']}  {t['teamName']}")
    elif cmd == "leaderboard-download":
        # 使い方: kaggle_cli.py leaderboard-download [score]  → 全件CSV(1リクエスト)+順位
        path, rows = leaderboard_download()
        print(f"saved {path}  teams={len(rows)}")
        if len(sys.argv) > 2:
            rk, n = rank_of(float(sys.argv[2]), rows)
            print(f"score {sys.argv[2]} → rank {rk} / {n} (top {100*rk/n:.1f}%)")
    elif cmd == "rank-of":
        # 使い方: kaggle_cli.py rank-of <score> [csv]  → リクエストなし(保存済みCSVを読む)
        csvs = sorted(Path("replay_analysis/lake/leaderboard").glob("*.csv"), key=lambda z: z.stat().st_mtime)
        src = Path(sys.argv[3]) if len(sys.argv) > 3 else csvs[-1]
        rows = [{"score": _num((r.get("Score") or r.get("score")))} for r in csv.DictReader(open(src))]
        rk, n = rank_of(float(sys.argv[2]), rows)
        print(f"{src.name}: score {sys.argv[2]} → rank {rk} / {n} (top {100*rk/n:.1f}%)")
    elif cmd == "team-submissions":
        for s in team_submissions(int(sys.argv[2])):
            print(f"  sub{s['sub']}  {s['score']}  {s['dateSubmitted']}")
    elif cmd == "submit":
        # 使い方: kaggle_cli.py submit <tar> <message>
        print(submit(sys.argv[2], sys.argv[3]))
    elif cmd == "kernels":
        # 使い方: kaggle_cli.py kernels [page]  → 公開ノート一覧(dateRun 降順、100件/ページ、1リクエスト)
        pg = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        for k in kernels_list(page=pg):
            print(f"  {k['lastRunTime'][:10] if k['lastRunTime'] else '?':<10} {str(k['totalVotes']):>4}  {k['ref']:<60} {k['title']}")
    elif cmd == "our-submissions":
        for s in our_submissions():
            print(f"  sub{s['sub']}  {str(s['score']):>7}  {s['status']:<28} {s['file']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

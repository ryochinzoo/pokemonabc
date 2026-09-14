#!/usr/bin/env python3
"""本番テレメトリの回収 — 自チーム提出の「1決定ごとの思考時間とstderr」を集める。

**なぜこれが要るか**: 我々の最も硬い制約は「絶対にクラッシュせず、時間も切らさない」だが、
その2つは**ローカルでは原理的に測れない**。本番ランナーのCPU・本番の対面・本番の入力でしか
起きないからだ。今まではリプレイ(136〜232MB)の `remainingOverageTime` から**推定**していた。

`kaggle competitions logs <ep> <agentIdx>` は同じ情報源をもっと直接に、**3.9KB**で返す:

    [ [{"duration": 0.08759, "stdout": "", "stderr": ""}], ... ]   ← 1決定1要素

  - `duration` = 本番ランナーが計った実測の思考時間(秒)
  - `stderr`   = 例外が出れば**ここに出る**。クラッシュ非発生の直接証拠
  - サイズはリプレイの **1/1000〜1/5000**。全エピソード分を永久に持てる

**自チーム限定**(他人のエピソードは403、2026-08-09実測)。取得は kaggle_gate の律速下。

注意: 事前登録の2つの予測のうち、**p99は直接測れるが「bank(繰越時間)残量」は測れない**。
bank は `remainingOverageTime` にあり、それはリプレイ側。混同しないこと。

    python3 replay_analysis/agent_logs.py fetch <submissionId> [maxN]
    python3 replay_analysis/agent_logs.py report [submissionId]
"""
import json
import statistics as st
import sys
from pathlib import Path

import kaggle_cli
import kaggle_gate

HERE = Path(__file__).resolve().parent
LAKE = HERE / "lake"
RAW = LAKE / "agentlogs"
STORE = LAKE / "agentlogs.jsonl"


def _seat_of(agents, sub):
    for i, a in enumerate(agents):
        if a.get("submissionId") == sub:
            return i
    return None


def _distill(path, sub, ep, seat, opp, reward, score):
    """生のログ配列を1行に畳む。生ファイルは残すが、解析はこの行だけで足りる。"""
    d = json.loads(Path(path).read_text())
    durs, errs, outs = [], [], []
    for step in d:
        if not isinstance(step, list):
            continue
        for rec in step:
            if not isinstance(rec, dict):
                continue
            if rec.get("duration") is not None:
                durs.append(rec["duration"])
            if (rec.get("stderr") or "").strip():
                errs.append(rec["stderr"].strip()[:400])
            if (rec.get("stdout") or "").strip():
                outs.append(rec["stdout"].strip()[:200])
    if not durs:
        return None
    s = sorted(durs)
    q = lambda p: s[min(len(s) - 1, int(p * len(s)))]        # noqa: E731
    return {"sub": sub, "ep": ep, "seat": seat, "opp": opp, "reward": reward,
            "score": score, "n": len(durs),
            "p50": q(.50), "p90": q(.90), "p99": q(.99), "max": max(durs),
            "sum": sum(durs), "mean": st.mean(durs),
            "nStderr": len(errs), "nStdout": len(outs),
            "stderr": errs[:3], "stdout": outs[:3]}


def _seen():
    if not STORE.exists():
        return set()
    out = set()
    for line in STORE.open():
        try:
            r = json.loads(line)
            out.add((r["sub"], r["ep"]))
        except (ValueError, KeyError):
            pass
    return out


def fetch(sub, max_n=None):
    sub = int(sub)
    data = kaggle_gate.list_episodes(sub)                      # キャッシュ優先
    eps = [e for e in data.get("episodes", [])
           if e.get("state") == "COMPLETED" and len(e.get("agents", [])) == 2]
    eps.sort(key=lambda e: e["id"], reverse=True)
    if max_n:
        eps = eps[:max_n]
    seen = _seen()
    RAW.mkdir(parents=True, exist_ok=True)
    LAKE.mkdir(parents=True, exist_ok=True)
    print(f"sub{sub}: COMPLETED {len(eps)}戦 / 既取得 {sum(1 for e in eps if (sub, e['id']) in seen)}")

    got = 0
    for e in eps:
        if (sub, e["id"]) in seen:
            continue
        seat = _seat_of(e["agents"], sub)
        if seat is None:
            continue
        me, foe = e["agents"][seat], e["agents"][1 - seat]
        try:
            p = kaggle_cli.agent_logs(e["id"], seat, RAW / str(sub))
        except kaggle_gate.Cooldown as ex:
            print(f"  中断: {ex}\n  → {got}戦ぶん保存済み。再実行で差分だけ進む")
            return 1
        if not p:
            print(f"  ep{e['id']}: ログ取得できず")
            continue
        row = _distill(p, sub, e["id"], seat, foe.get("submissionId"),
                       me.get("reward"), me.get("initialScore"))
        if row:
            with STORE.open("a") as f:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
            got += 1
            flag = "  ⚠stderr" if row["nStderr"] else ""
            print(f"  ep{e['id']} seat{seat}  {row['n']:>3}決定  "
                  f"p99 {1000*row['p99']:6.1f}ms  max {1000*row['max']:6.1f}ms{flag}",
                  flush=True)
    print(f"fetch 完了: 新規{got}戦 → {STORE}")
    return 0


def report(sub=None):
    if not STORE.exists():
        print("agentlogs.jsonl が無い。先に fetch を走らせること")
        return 1
    rows = [json.loads(x) for x in STORE.open() if x.strip()]
    if sub:
        rows = [r for r in rows if r["sub"] == int(sub)]
    if not rows:
        print("該当なし")
        return 1

    for s in sorted({r["sub"] for r in rows}):
        rs = [r for r in rows if r["sub"] == s]
        alld = []
        for r in rs:
            alld.append(r["p99"])
        p99s = sorted(alld)
        worst = max(rs, key=lambda r: r["max"])
        errs = [r for r in rs if r["nStderr"]]
        w = sum(1 for r in rs if r.get("reward") == 1)
        ll = sum(1 for r in rs if r.get("reward") == -1)
        print(f"=== sub{s} ===  {len(rs)}戦  戦績 {w}-{ll}"
              f"  総決定 {sum(r['n'] for r in rs):,}")
        print(f"  1試合あたり決定数   中央 {st.median([r['n'] for r in rs]):.0f}"
              f"  最大 {max(r['n'] for r in rs)}")
        print(f"  試合内p99 の分布    中央 {1000*st.median(p99s):.0f}ms"
              f"  最悪 {1000*max(p99s):.0f}ms")
        print(f"  単発の最遅          {1000*worst['max']:.0f}ms  (ep{worst['ep']})")
        print(f"  1試合の総思考時間   中央 {st.median([r['sum'] for r in rs]):.1f}s"
              f"  最大 {max(r['sum'] for r in rs):.1f}s")
        print(f"  **stderr を出した試合: {len(errs)}/{len(rs)}**"
              + ("" if not errs else "  ← クラッシュ or 例外の証拠"))
        for r in errs[:5]:
            print(f"     ep{r['ep']}: {r['stderr'][:1]}")
        print(f"  stdout を出した試合: {sum(1 for r in rs if r['nStdout'])}/{len(rs)}")
        # 事前登録との突き合わせ
        over = [r for r in rs if r["p99"] > 0.9]
        print(f"  事前登録『p99 < 900ms』: 破った試合 {len(over)}/{len(rs)}"
              f"  → {'合格' if not over else '⚠違反あり'}")
        print("  ※『min bank > 400s』は remainingOverageTime 側の量で、"
              "エージェントログには入っていない(混同しないこと)")
        print()
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "fetch":
        sys.exit(fetch(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None))
    elif cmd == "report":
        sys.exit(report(sys.argv[2] if len(sys.argv) > 2 else None))
    else:
        print(__doc__)

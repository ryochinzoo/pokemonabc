#!/usr/bin/env python3
"""決定一致率 diff(対戦ゼロ): 2つの main.py を同じ本番観測に食わせ、v1層(探索OFF)の選択を比較する.

council-2026-08-17-external-review.md「救済測定」の永続化。当時の 4.13% は b9a7bd31 vs 783d91d6
(未提出候補)の値で、最終バイト b67466a9 では未再走だった(Plan 2026-09-02 §1.5)。

使い方:
  python3 verification/decision_agreement.py <deckDirA> <deckDirB> <epsDir> [<epsDir> ...] [--json OUT]
  例: python3 verification/decision_agreement.py <v1抽出dir> src/input/datasets/decks/starmie-aqua-bosslogic \
        replay_analysis/eps55468574 replay_analysis/eps55519487

規則: 選択肢= steps[N].observation.select.option / 答え= steps[N+1].action / 手番= status=="ACTIVE"。
自席= 各 dir の deck.csv との重なり最大側(両dirのデッキが同一である前提。異なれば警告)。
測るのは (a)実装の正しさ=例外0 と (c)非退行の面のみ。**勝率への効果は測っていない**。
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

RUNNER = r'''
import json, os, sys
from collections import Counter
sys.path.insert(0, ".")
os.environ["V2_NO_SEARCH"] = "1"
import main
deck_ids = Counter(int(x) for x in open("deck.csv").read().split())
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
with open(sys.argv[2], "w") as out:
    for fp in files:
        d = json.load(open(fp))
        steps = d.get("steps") or []
        if len(steps) < 2:
            continue
        decks = [Counter(a.get("action") or []) for a in steps[1]]
        ov = [sum((deck_ids & x).values()) for x in decks]
        mine = 0 if ov[0] >= ov[1] else 1
        for si in range(len(steps) - 1):
            ag = steps[si][mine] or {}
            if ag.get("status") != "ACTIVE":
                continue
            obs_d = ag.get("observation") or {}
            sel = obs_d.get("select")
            if not sel:
                continue
            try:
                obs = main.to_observation_class(obs_d)
                res = main._v1_decide(obs)
                rec = {"f": os.path.basename(fp), "si": si, "mine": mine, "t": sel.get("type"),
                       "ctx": sel.get("context"), "res": list(res), "exc": None}
            except Exception as e:
                rec = {"f": os.path.basename(fp), "si": si, "mine": mine, "t": sel.get("type"),
                       "ctx": sel.get("context"), "res": None, "exc": type(e).__name__}
            out.write(json.dumps(rec) + "\n")
'''

SELTYPE = {0: "MAIN", 1: "CARD", 2: "ATTACHED", 3: "CARD_OR_ATT", 4: "YES_NO", 5: "COUNT", 6: "ATTACK", 7: "EVOLVE"}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()[:8]


def run(deck_dir, files, scratch, tag):
    (scratch / f"runner_{tag}.py").write_text(RUNNER)
    lst = scratch / f"files_{tag}.txt"
    lst.write_text("\n".join(str(f) for f in files))
    out = scratch / f"out_{tag}.jsonl"
    r = subprocess.run([sys.executable, str(scratch / f"runner_{tag}.py"), str(lst), str(out)],
                       cwd=deck_dir, env=dict(os.environ, V2_NO_SEARCH="1"), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"runner {tag} failed:\n{r.stderr[-2000:]}")
    return [json.loads(l) for l in out.read_text().splitlines() if l.strip()]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]
        args = [a for a in args if a != out_json]
    a_dir, b_dir, eps_dirs = Path(args[0]), Path(args[1]), [Path(p) for p in args[2:]]
    files = sorted(f.resolve() for e in eps_dirs for f in e.resolve().glob("ep*.json"))  # runner の cwd は deck dir なので絶対パス
    if not files:
        sys.exit("リプレイが無い")
    ha, hb = md5(a_dir / "main.py"), md5(b_dir / "main.py")
    da, db = md5(a_dir / "deck.csv"), md5(b_dir / "deck.csv")
    if da != db:
        print(f"⚠ deck.csv が異なる: {da} vs {db}(自席判定がずれる可能性)")
    scratch = Path(tempfile.mkdtemp(prefix="decision_agreement_"))
    ra = run(a_dir, files, scratch, "A")
    rb = run(b_dir, files, scratch, "B")
    ka = {(r["f"], r["si"]): r for r in ra}
    kb = {(r["f"], r["si"]): r for r in rb}
    keys = sorted(set(ka) & set(kb))
    tot, mism, exc = Counter(), Counter(), Counter()
    examples = []
    for k in keys:
        x, y = ka[k], kb[k]
        t = SELTYPE.get(x["t"], str(x["t"]))
        tot[t] += 1
        if x["exc"]:
            exc["A"] += 1
        if y["exc"]:
            exc["B"] += 1
        if x["res"] != y["res"]:
            mism[t] += 1
            if len(examples) < 40:
                examples.append((k[0], k[1], t, x["ctx"], x["res"], y["res"]))
    n = sum(tot.values())
    m = sum(mism.values())
    print(f"A main={ha} deck={da}  B main={hb} deck={db}  games={len(files)}  decisions={n}")
    print(f"不一致 {m}/{n} = {100*m/max(n,1):.2f}%   例外 A={exc['A']} B={exc['B']}   "
          f"(A-only keys {len(set(ka)-set(kb))}, B-only {len(set(kb)-set(ka))})")
    for t in sorted(tot, key=lambda t: -tot[t]):
        print(f"  {t:12s} {mism[t]:5d}/{tot[t]:<6d} = {100*mism[t]/tot[t]:.2f}%")
    print("例(先頭):")
    for e in examples[:12]:
        print("  ", e)
    if out_json:
        Path(out_json).write_text(json.dumps({"A": {"dir": str(a_dir), "main": ha, "deck": da},
                                              "B": {"dir": str(b_dir), "main": hb, "deck": db},
                                              "games": len(files), "decisions": n, "mismatch": m,
                                              "by_type": {t: [mism[t], tot[t]] for t in tot},
                                              "exceptions": dict(exc), "examples": examples}, ensure_ascii=False, indent=1))
        print("saved", out_json)


if __name__ == "__main__":
    main()

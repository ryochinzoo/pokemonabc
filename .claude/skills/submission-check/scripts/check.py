#!/usr/bin/env python3
"""submission-check: Kaggle へ出す前のプリフライト検査。

壊れたパッケージで貴重な「1日5回」の提出枠を1つ無駄にしないための防衛線。
リポジトリのルートから実行する想定:
    python3 <skill_dir>/scripts/check.py

検査項目:
  1. deck.csv      … ちょうど60枚 / 全て整数 / 全て実在のCard ID / 同一ID5枚以上は警告
  2. imports       … main.py 等が標準ライブラリ + cg + 同梱モジュール 以外を import してないか
  3. tar 構造      … submission.tar.gz のルートに main.py と deck.csv があるか
  4. スモーク対戦  … main.agent を20戦走らせ「落ちない/常に合法手/時間内」を実測

すべて合格なら exit 0、1つでも FAIL があれば exit 1。
"""

import argparse
import ast
import csv
import os
import sys
import tarfile
import time

OK = "  OK  "
WARN = " WARN "
FAIL = " FAIL "


class Report:
    def __init__(self) -> None:
        self.failed = False

    def line(self, status: str, msg: str) -> None:
        print(f"[{status}] {msg}")
        if status == FAIL:
            self.failed = True


def check_deck(rep: Report, deck_path: str, valid_ids: set[int]) -> None:
    print("\n== 1. deck.csv ==")
    if not os.path.exists(deck_path):
        rep.line(FAIL, f"deck.csv が見つからない: {deck_path}")
        return
    with open(deck_path) as f:
        lines = [ln for ln in f.read().split("\n") if ln.strip()]
    if len(lines) != 60:
        rep.line(FAIL, f"60行でない（実際 {len(lines)}行）。デッキはちょうど60枚。")
    else:
        rep.line(OK, "60行ある。")
    ids: list[int] = []
    bad = []
    for ln in lines:
        try:
            ids.append(int(ln.strip()))
        except ValueError:
            bad.append(ln)
    if bad:
        rep.line(FAIL, f"整数として読めない行: {bad[:5]}")
    if valid_ids:
        missing = sorted({i for i in ids if i not in valid_ids})
        if missing:
            rep.line(FAIL, f"カードデータに存在しないID: {missing[:10]}")
        else:
            rep.line(OK, "全IDがカードデータに存在する。")
    counts: dict[int, int] = {}
    for i in ids:
        counts[i] = counts.get(i, 0) + 1
    over = {i: c for i, c in counts.items() if c >= 5}
    if over:
        rep.line(WARN, f"同一IDが5枚以上（基本エネルギー以外なら4枚制限に注意）: {over}")


def check_imports(rep: Report, submission_dir: str) -> None:
    print("\n== 2. imports（標準ライブラリのみか） ==")
    allowed = set(sys.stdlib_module_names) | {"cg"}
    # 同梱の自作モジュール（cg/ 配下を除くトップレベル .py）は許可
    local = {
        os.path.splitext(f)[0]
        for f in os.listdir(submission_dir)
        if f.endswith(".py")
    }
    allowed |= local
    offenders: dict[str, set[str]] = {}
    for fname in sorted(os.listdir(submission_dir)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(submission_dir, fname)
        try:
            tree = ast.parse(open(path).read(), filename=path)
        except SyntaxError as e:
            rep.line(FAIL, f"{fname}: 構文エラー {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            else:
                continue
            for m in mods:
                if m not in allowed:
                    offenders.setdefault(fname, set()).add(m)
    if offenders:
        for fname, mods in offenders.items():
            rep.line(FAIL, f"{fname}: 標準ライブラリ外の import {sorted(mods)}（サンドボックスに無い可能性）")
    else:
        rep.line(OK, "標準ライブラリ + cg + 同梱モジュール のみ。")


def check_tar(rep: Report, tar_path: str) -> None:
    print("\n== 3. submission.tar.gz の構造 ==")
    if not os.path.exists(tar_path):
        rep.line(WARN, f"{tar_path} が無い。提出前に作る（下のコマンド参照）。")
        return
    with tarfile.open(tar_path) as t:
        names = t.getnames()
    roots = {n.split("/")[0] for n in names}
    for required in ("main.py", "deck.csv"):
        if required in names:
            rep.line(OK, f"ルートに {required} がある。")
        else:
            rep.line(FAIL, f"ルートに {required} が無い（実在: {sorted(roots)[:8]}）。")
    if "cg" in roots:
        rep.line(OK, "cg/ 同梱を確認（前回の提出と同じ構成）。")


def check_smoke(rep: Report, submission_dir: str, games: int, time_warn_ms: float) -> None:
    print(f"\n== 4. スモーク対戦（{games}戦：落ちない/合法手/時間内） ==")
    cwd = os.getcwd()
    os.chdir(submission_dir)
    sys.path.insert(0, submission_dir)
    try:
        import selfplay
        import main as our_main
        from cg.api import to_observation_class

        stats = {"calls": 0, "max_ms": 0.0, "violations": 0}

        def checked(obs_dict: dict) -> list[int]:
            obs = to_observation_class(obs_dict)
            t = time.perf_counter()
            result = our_main.agent(obs_dict)
            ms = (time.perf_counter() - t) * 1000
            stats["calls"] += 1
            stats["max_ms"] = max(stats["max_ms"], ms)
            sel = obs.select
            if sel is not None:  # 自己対戦では select は常に非None
                n = len(sel.option)
                bad = (
                    not isinstance(result, list)
                    or not all(isinstance(x, int) for x in result)
                    or not (sel.minCount <= len(result) <= sel.maxCount)
                    or any(not (0 <= x < n) for x in result)
                    or len(set(result)) != len(result)
                )
                if bad:
                    stats["violations"] += 1
                    print(f"      契約違反: min={sel.minCount} max={sel.maxCount} "
                          f"n={n} -> returned {result}")
            return result

        deck = selfplay.load_deck()
        try:
            selfplay.run_series(games, deck, deck, checked, checked)
        except Exception as e:
            import traceback
            traceback.print_exc()
            rep.line(FAIL, f"対戦中に例外＝クラッシュ: {e}（『絶対に落ちない』要件に違反）")
            return

        if stats["violations"]:
            rep.line(FAIL, f"返り値が契約違反: {stats['violations']}件 / {stats['calls']}判断")
        else:
            rep.line(OK, f"{stats['calls']}回の判断すべてが合法（範囲内・重複なし・件数OK）。")
        if stats["max_ms"] > time_warn_ms:
            rep.line(WARN, f"最も遅い判断 {stats['max_ms']:.0f}ms。手番ごとの制限時間は要確認。")
        else:
            rep.line(OK, f"最も遅い判断 {stats['max_ms']:.0f}ms。")
    finally:
        os.chdir(cwd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", default="src/input/datasets/decks/mega-starmie-ex-deck")
    ap.add_argument("--carddata", default="verification/data/EN_Card_Data.csv")
    ap.add_argument("--tar", default="submission.tar.gz")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--time-warn-ms", type=float, default=2000.0)
    args = ap.parse_args()

    submission_dir = os.path.abspath(args.submission)
    carddata = os.path.abspath(args.carddata)
    tar_path = os.path.abspath(args.tar)

    valid_ids: set[int] = set()
    if os.path.exists(carddata):
        with open(carddata) as f:
            r = csv.reader(f)
            next(r, None)  # header
            for row in r:
                if row and row[0].strip().isdigit():
                    valid_ids.add(int(row[0]))

    rep = Report()
    check_deck(rep, os.path.join(submission_dir, "deck.csv"), valid_ids)
    check_imports(rep, submission_dir)
    check_tar(rep, tar_path)
    check_smoke(rep, submission_dir, args.games, args.time_warn_ms)

    print("\n== 結果 ==")
    if rep.failed:
        print("FAIL があります。提出しないこと。上の項目を直してから再実行する。")
        sys.exit(1)
    print("すべて合格。提出してよい。tar を作り直すなら:")
    print("  cd src/input/datasets/decks/mega-starmie-ex-deck && tar czf ../../submission.tar.gz main.py deck.csv cg")
    sys.exit(0)


if __name__ == "__main__":
    main()

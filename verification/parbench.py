#!/usr/bin/env python3
"""parbench: 並列ベンチ。D51の並列許可条件を「規則」ではなく「構造」として強制する。

bench.py と同じ測定を、プロセス並列で走らせる。ただし playbook §2(2026-07-25改訂)の
許可条件を**ツール側で機械的に検査**し、満たさなければ実行を拒否する:

  1. 相手エージェントが壁時計を読むなら並列を拒否する（現時点の該当= steel_agent.py）
  2. 我々のパイロットの壁時計予算（安全弁）への到達を全数計測し、必ず出力する
  3. 並列時最悪でも安全弁まで3倍以上の余裕がなければ VERDICT=UNSAFE を返す
  4. ワーカーごとの完了戦数を検算し、部分失敗を黙って合算しない

なぜツールに入れるか: 旧規定「時間予算制ベンチは並列禁止」は人間の警戒に依存して
2回破られた（D16、2026-07-22）。守るべき規則を、破れない構造にするのが本ツールの目的。

使い方（デッキディレクトリから実行、bench.py と同じ流儀）:
    cd src/input/datasets/decks/starmie-aggro
    python3 ../../../../../verification/parbench.py 3200 --workers 8 \
      --opponent ../../../../../verification/reference/official_lucario_agent.py \
      --opponent-deck ../../../../../verification/decks/official_lucario_2026-07-21.csv

終了コード: 0=正常 / 1=--baseline 未達 / 2=クラッシュ / 3=並列安全条件の不成立
"""

import argparse
import importlib.util
import math
import multiprocessing as mp
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# 壁時計を読むエージェントの検出パターン（D51: steel_agent.py が唯一の該当物）
#
# 呼び出し側の形で検出する。モジュール名に縛ると `import time as _time` →
# `_time.time()` を取り逃す（初版の実バグ。2026-07-25 に steel を並列で走らせてしまった）。
# **偽陽性は安全側**（直列に落ちるだけ）なので、`.time(` のような広いパターンを許容する。
# 既知の限界: 相手が別モジュールに壁時計を隠している場合は検出できない
# （現行の参照エージェントは全て単一ファイルなので実害なし）。
_WALLCLOCK_RE = re.compile(
    r"(?:monotonic|perf_counter|process_time)\s*\("   # _time.monotonic() / monotonic()
    r"|\.\s*time\s*\("                                 # time.time() / _time.time()
    r"|(?<![\w.])time\s*\(\s*\)"                       # from time import time → time()
    r"|datetime\s*\.\s*now\s*\("
    r"|\.\s*clock\s*\("
)

# パイロット側の壁時計予算として認識する定数名（新旧どちらでも拾う）
_BUDGET_NAMES = ("_SAFETY_VALVE_SEC", "_SEARCH_BUDGET_SEC")

# D51: 並列許可には安全弁まで3倍以上の余裕が要る
_REQUIRED_HEADROOM = 3.0


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """勝率の95% Wilson信頼区間（bench.py と同一実装）。"""
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def uses_wallclock(path: str) -> bool:
    """相手エージェントのソースが壁時計を読むかを静的に判定する。"""
    try:
        with open(path, "r") as f:
            return bool(_WALLCLOCK_RE.search(f.read()))
    except OSError:
        return True  # 読めないものは安全側に倒す


def split_even(n: int, k: int) -> list[int]:
    """N を k 個の**偶数**チャンクに割る。

    run_series は i%2 で席を入れ替えるため、奇数チャンクは先攻/後攻を偏らせる。
    偏っても数値は普通に出る（＝計器に映らない）ので、ここで構造的に防ぐ。
    """
    if n % 2:
        raise ValueError(f"N は偶数でなければならない（席交換の均衡のため）: N={n}")
    pairs = n // 2
    k = max(1, min(k, pairs))
    base, extra = divmod(pairs, k)
    return [2 * (base + (1 if i < extra else 0)) for i in range(k)]


def _worker(job: dict) -> dict:
    """1ワーカー = 1プロセス。エンジンはプロセスごとに独立ロードされる。

    Battle.battle_ptr がモジュールグローバル（＝1プロセス1試合）のため、
    スレッドではなくプロセスでなければならない。
    """
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.path.insert(0, job["cwd"])
    sys.path.insert(1, HERE)
    os.chdir(job["cwd"])

    import selfplay
    import main as our_main

    # --- 安全弁への到達を全数計測する（D51の許可条件②③） ---
    stats = {"calls": 0, "max_ms": 0.0, "hits": 0, "budget_sec": None, "fires": 0}
    budget = None
    for name in _BUDGET_NAMES:
        if hasattr(our_main, name):
            budget = float(getattr(our_main, name))
            stats["budget_sec"] = budget
            break

    # 計時計装は予算定数の有無と切り離す（「不在を証拠として扱う」の防止）
    if hasattr(our_main, "_search_decide"):
        _orig = our_main._search_decide

        def _timed(obs_dict, sel, v1, _o=_orig, _b=budget, _s=stats):
            t0 = time.monotonic()
            r = None
            try:
                r = _o(obs_dict, sel, v1)
                return r
            finally:
                dt = time.monotonic() - t0
                _s["calls"] += 1
                if r is not None:
                    _s["fires"] += 1
                if dt * 1000.0 > _s["max_ms"]:
                    _s["max_ms"] = dt * 1000.0
                if _b is not None and dt >= _b * 0.9:
                    _s["hits"] += 1

        our_main._search_decide = _timed

    # === アーム同一性を「測定値」にする（T7パネル M3） ===
    # `--label` は自由文字列なので、アームが実際に効いたことの証拠にならない。
    # 「全アームが現行設定のまま走った」出力は、事前登録済みのH0と観測上区別がつかない。
    import hashlib
    with open(os.path.join(job["cwd"], "main.py"), "rb") as _f:
        arm_sha = hashlib.sha256(_f.read()).hexdigest()[:12]
    arm = {
        "sha": arm_sha,
        "det": getattr(our_main, "_DETERMINIZATIONS", None),
        "margin": getattr(our_main, "_OVERRIDE_MARGIN", None),
        "env": ",".join(f"{k}={os.environ[k]}" for k in sorted(os.environ)
                        if k.startswith(("V2_", "V3_", "PROBE_", "ARM_"))) or "-",
    }

    deck = selfplay.load_deck(job["deck"]) if job["deck"] else selfplay.load_deck()
    if job["opponent"] == "random":
        opp_agent = selfplay.random_agent
    else:
        spec = importlib.util.spec_from_file_location(f"opp_{job['idx']}", job["opponent"])
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        opp_agent = mod.agent
    opp_deck = selfplay.load_deck(job["opponent_deck"]) if job["opponent_deck"] else deck

    t0 = time.time()
    try:
        res = selfplay.run_series(job["n"], deck, opp_deck, our_main.agent, opp_agent)
    except Exception as e:  # noqa: BLE001 — 部分失敗は黙って合算しないため必ず持ち帰る
        import traceback
        return {"idx": job["idx"], "ok": False, "n_req": job["n"],
                "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()}

    return {"idx": job["idx"], "ok": True, "n_req": job["n"], "arm": arm,
            "wins": res["agent0_wins"], "losses": res["agent1_wins"],
            "draws": res["draws"], "n_done": res["n"],
            "wall": time.time() - t0, **{f"stat_{k}": v for k, v in stats.items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, help="総対戦数（偶数）")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--deck", default=None)
    ap.add_argument("--opponent", default="random")
    ap.add_argument("--opponent-deck", default=None)
    ap.add_argument("--baseline", type=float, default=None)
    ap.add_argument("--label", default="", help="ログ用のアーム名（掃引時に使う）")
    ap.add_argument("--expect-arm", default=None,
                    help="アーム実体（sha/det/margin/env）に含まれるべき文字列。"
                         "不一致なら exit 3。掃引の取り違えを構造的に防ぐ")
    ap.add_argument("--allow-serial-fallback", action="store_true",
                    help="壁時計依存の相手が指定されたとき、拒否せず workers=1 に落とす")
    args = ap.parse_args()

    cwd = os.getcwd()

    # === D51 許可条件① 相手エージェントの壁時計依存を静的に検査する ===
    if args.opponent != "random" and args.workers > 1 and uses_wallclock(args.opponent):
        msg = (f"相手エージェント {args.opponent} は壁時計を読む。"
               f"playbook §2（D51）により並列測定は禁止。")
        if not args.allow_serial_fallback:
            print(f"PARALLEL=REFUSED  {msg}")
            print("VERDICT=UNSAFE")
            print("→ bench.py で直列に測るか、--allow-serial-fallback を付けること。")
            sys.exit(3)
        print(f"PARALLEL=DOWNGRADED  {msg} → workers=1 に落として続行。")
        args.workers = 1

    chunks = split_even(args.n, args.workers)
    jobs = [{"idx": i, "n": c, "cwd": cwd, "deck": args.deck,
             "opponent": args.opponent, "opponent_deck": args.opponent_deck}
            for i, c in enumerate(chunks)]

    t0 = time.time()
    ctx = mp.get_context("spawn")  # fork は ctypes ロード済みライブラリと相性が悪い
    with ctx.Pool(processes=len(jobs)) as pool:
        results = pool.map(_worker, jobs)
    wall = time.time() - t0

    # === D51 許可条件④ 部分失敗を黙って合算しない ===
    failed = [r for r in results if not r.get("ok")]
    if failed:
        for r in failed:
            print(f"WORKER {r['idx']} FAILED (n_req={r['n_req']}): {r.get('error')}")
            print(r.get("tb", ""))
        print("PARBENCH: ワーカーが落ちたため結果を合算しない。")
        print("CRASH=1")
        sys.exit(2)

    n_done = sum(r["n_done"] for r in results)
    n_req = sum(r["n_req"] for r in results)
    if n_done != n_req or n_req != args.n:
        print(f"PARBENCH: 戦数の検算に失敗（要求{args.n} / 割当{n_req} / 完了{n_done}）。")
        print("CRASH=1")
        sys.exit(2)

    wins = sum(r["wins"] for r in results)
    losses = sum(r["losses"] for r in results)
    draws = sum(r["draws"] for r in results)
    wr = wins / n_done
    lo, hi = wilson(wins, n_done)

    # === D51 許可条件②③ 安全弁への到達を必ず出力する ===
    calls = sum(r.get("stat_calls", 0) for r in results)
    hits = sum(r.get("stat_hits", 0) for r in results)
    max_ms = max((r.get("stat_max_ms", 0.0) for r in results), default=0.0)
    budget_sec = next((r.get("stat_budget_sec") for r in results
                       if r.get("stat_budget_sec")), None)

    fires = sum(r.get("stat_fires", 0) for r in results)

    # === アーム同一性の検算（T7パネル M3） ===
    arms = {repr(sorted(r["arm"].items())) for r in results}
    arm0 = results[0]["arm"]
    arm_str = f"sha={arm0['sha']} det={arm0['det']} margin={arm0['margin']} env={arm0['env']}"
    if len(arms) != 1:
        print("PARBENCH: ワーカー間でアームが一致しない（掃引の取り違え）。")
        for r in results:
            print(f"  worker{r['idx']}: {r['arm']}")
        print("CRASH=1")
        sys.exit(2)
    print(f"ARM={arm_str}")
    print(f"ARM_FIRES={fires}  (上書き発火の総数。OFF腕なら0でなければならない)")
    if args.expect_arm and args.expect_arm not in arm_str:
        print(f"PARBENCH: --expect-arm '{args.expect_arm}' がアーム実体に一致しない。")
        print("VERDICT=UNSAFE")
        sys.exit(3)

    label = f"[{args.label}] " if args.label else ""
    print(f"{label}並列={len(jobs)}  総戦数={n_done}  "
          f"({wall:.1f}秒, {n_done / max(wall, 1e-9):.2f}戦/秒)")
    print(f"チャンク: {[r['n_done'] for r in results]}  "
          f"各ワーカーwall: {[round(r['wall'], 1) for r in results]}")
    print(f"結果: {wins}勝 {losses}敗 {draws}分")
    print(f"勝率: {wr:.1%}  (95%信頼区間 {lo:.1%}〜{hi:.1%})")

    # === 安全性の判定を、機械可読の勝率より「先に」出す（T7パネル M3） ===
    # 初版は WINRATE を先に印字しており、汚染アームの勝率が駆動スクリプトに
    # 収穫されうる構造だった。
    safe = True
    if budget_sec is None:
        print("VALVE=NONE  (パイロットに壁時計予算が見つからない)")
        print(f"SEARCH_CALLS={calls}  MAX_MS={max_ms:.1f}")
    else:
        headroom = (budget_sec * 1000.0 / max_ms) if max_ms > 0 else float("inf")
        print(f"VALVE_SEC={budget_sec:.3f}  SEARCH_CALLS={calls}  "
              f"VALVE_HITS={hits}  MAX_MS={max_ms:.1f}  HEADROOM={headroom:.1f}x")
        safe = hits == 0 and headroom >= _REQUIRED_HEADROOM
        if not safe:
            print(f"VERDICT=UNSAFE  (到達{hits}件 / 余裕{headroom:.1f}x < {_REQUIRED_HEADROOM}x)")
            print("→ この数値は汚染の可能性がある。直列で測り直すか仕事量予算へ変換すること。")
            print("WINRATE=INVALID")   # キー自体を消すと呼び出し側が前回値を使い回す
            print("CI_LOW=INVALID")
            print("CI_HIGH=INVALID")
            print("CRASH=0")
            sys.exit(3)
    print("VERDICT=SAFE  (安全弁への到達0件、余裕3倍以上 = 負荷は判断に影響しえない)"
          if budget_sec is not None else "VERDICT=SAFE")
    print(f"WINRATE={wr:.4f}")
    print(f"CI_LOW={lo:.4f}")
    print(f"CI_HIGH={hi:.4f}")
    print("CRASH=0")

    if args.baseline is not None:
        if lo < args.baseline:
            print(f"GATE=FAIL  (信頼区間の下限 {lo:.3f} < baseline {args.baseline:.3f})")
            sys.exit(1)
        print(f"GATE=PASS  (信頼区間の下限 {lo:.3f} >= baseline {args.baseline:.3f})")
    sys.exit(0)


if __name__ == "__main__":
    main()

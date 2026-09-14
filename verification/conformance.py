#!/usr/bin/env python3
"""conformance.py — 本番ランナー(kaggle_environments envs/cabt)への適合検査。

なぜ必要か: `verification/selfplay.py` は `battle_start(deck0, deck1)` に deck.csv から
読んだデッキを直接渡すため、**agent() のデッキ返却分岐がローカルで一度も実行されない**。
本番の interpreter は違う:

    decks = [state[0].action, state[1].action]          # デッキは agent() の戻り値
    if len(decks[i]) != 60: state[i].status = "INVALID"  # → reward -1 = 即敗北
    _, start_data = battle_start(...)
    if start_data.errorPlayer >= 0: status = "INVALID"   # エンジンによるデッキ検証

(出典: Kaggle/kaggle-environments master, kaggle_environments/envs/cabt/cabt.py の
 interpreter() L110-144。2026-07-22 に実物を取得して確認)

つまりデッキ返却が壊れていると、ベンチも CEW も正常な数値を出したまま本番だけ全敗する。
この経路をローカルで実行する唯一の検査がこれ。デッキディレクトリから実行する:

    cd src/input/datasets/decks/starmie-aggro
    python3 ../../../../../verification/conformance.py
"""
import sys
import time

sys.path.insert(0, ".")

FAIL = []
WARN = []


def check(cond, msg):
    if not cond:
        FAIL.append(msg)
    return cond


def main() -> int:
    import main as agent_mod
    from cg.game import battle_finish, battle_start

    # --- 本番の interpreter が最初のステップで渡す観測 (cabt.py L111-119 と同一) ---
    deck_phase_obs = {
        "remainingOverageTime": 600,
        "select": None,
        "logs": [],
        "current": None,
        "search_begin_input": None,
    }

    print("=== 1. デッキ返却経路 (本番 interpreter L122-131) ===")
    t0 = time.perf_counter()
    try:
        deck = agent_mod.agent(dict(deck_phase_obs))
    except Exception as e:
        FAIL.append(f"agent() がデッキ要求で例外: {type(e).__name__}: {e}")
        print(f"  CRASH: {type(e).__name__}: {e}")
        return report()
    dt = (time.perf_counter() - t0) * 1000
    print(f"  agent() 応答 {dt:.1f}ms")

    check(isinstance(deck, list), f"戻り値が list でない: {type(deck).__name__}")
    if isinstance(deck, list):
        check(len(deck) == 60, f"**60枚でない: {len(deck)}枚 → 本番 INVALID = reward -1**")
        check(all(isinstance(c, int) and not isinstance(c, bool) for c in deck),
              "int でない要素がある(本番は c_int 配列に渡すため型エラー)")
        print(f"  枚数 {len(deck)} / 型 {'OK' if all(isinstance(c, int) for c in deck) else 'NG'}")

    print("\n=== 2. deck.csv との一致 ===")
    try:
        with open("deck.csv") as f:
            csv_deck = [int(line.strip()) for line in f if line.strip()]
        if isinstance(deck, list):
            if sorted(csv_deck) == sorted(deck):
                print("  deck.csv と一致 (60枚の多重集合として)")
            else:
                WARN.append("agent() の返すデッキが deck.csv と不一致"
                            "(意図的なら無視可。提出物の deck.csv は別途審査対象)")
                print(f"  不一致: csv={len(csv_deck)}枚 / agent={len(deck)}枚")
    except Exception as e:
        WARN.append(f"deck.csv 読めず: {e}")

    print("\n=== 3. 同名4枚制限 (エンジンは検査しない: CLAUDE.md) ===")
    if isinstance(deck, list):
        from collections import Counter
        over = {c: n for c, n in Counter(deck).items() if n > 4}
        # 基本エネルギーは制限外なので警告に留める
        if over:
            WARN.append(f"5枚以上の card ID: {over} (基本エネルギーなら正常)")
            print(f"  5枚以上: {over} ← 基本エネルギー以外なら違反")
        else:
            print("  全 card ID が4枚以下")

    print("\n=== 4. エンジンによるデッキ検証 (interpreter L133-137) ===")
    if isinstance(deck, list) and len(deck) == 60:
        try:
            obs, start = battle_start(list(deck), list(deck))
            ep, et = start.errorPlayer, start.errorType
            check(ep < 0, f"**start_data.errorPlayer={ep} (errorType={et}) → 本番 INVALID**")
            check(start.battlePtr not in (None, 0), "battlePtr が無効")
            print(f"  errorPlayer={ep} errorType={et} battlePtr={'OK' if start.battlePtr else 'NULL'}")
            battle_finish()
        except Exception as e:
            FAIL.append(f"battle_start が例外: {type(e).__name__}: {e}")
            print(f"  CRASH: {type(e).__name__}: {e}")

    return report()


def report() -> int:
    print("\n" + "=" * 56)
    for w in WARN:
        print(f"WARN: {w}")
    if FAIL:
        for f in FAIL:
            print(f"FAIL: {f}")
        print(f"\nCONFORMANCE=FAIL ({len(FAIL)} 件)")
        return 1
    print("CONFORMANCE=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

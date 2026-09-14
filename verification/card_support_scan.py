#!/usr/bin/env python3
"""card_support_scan.py — どのカードがエンジンに載っているかを1枚ずつ機械判定する。

**なぜ必要か**: Strategy側 discussion/712435 で Juan Ortega が
「623 Valid / 644 not valid cards against the CABT」と報告したまま **0コメント=未回答**。
デッキを組み替えるなら「そもそも使えるカードの集合」が前提になるが、
公開範囲にこれを確定した人はいない。我々は `battle_start` の
`errorPlayer` を持っているので、**カード単位で機械判定できる**。

方式(conformance.py の「エンジンによるデッキ検証」と同じ経路):
  試験デッキ = Staryu×4 + 基本水エネ×52 + 対象カード×4  (計60)
  対照デッキ = Staryu×4 + 基本水エネ×56              (計60、必ず有効であることを先に確認)
  `battle_start(test, control)` の errorPlayer が 0 を指したら **その対象カードが原因**。

注意: 「無効」の内訳は分離していない(未実装 / デッキ構築規則違反 / 進化元不在 など)。
本スキャンが答えるのは「**4枚積んだデッキがエンジンに受理されるか**」だけ。

デッキディレクトリから実行する:
    cd src/input/datasets/decks/starmie-aggro
    python3 ../../../../../verification/card_support_scan.py
"""
import csv
import json
import os
import sys

sys.path.insert(0, ".")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARYU, WATER = 1030, 3


def load_cards():
    rows = []
    with open(os.path.join(REPO, "verification/data/EN_Card_Data.csv")) as f:
        for r in csv.DictReader(f):
            rows.append((int(r["Card ID"]), r["Card Name"],
                         r["Stage (Pokémon)/Type (Energy and Trainer)"] or "?"))
    return rows


def main():
    from cg.game import battle_finish, battle_start

    control = [STARYU] * 4 + [WATER] * 56
    assert len(control) == 60

    # --- 対照: 素の基本デッキが受理されるか(これが落ちるなら方式ごと無効) ---
    obs, st = battle_start(list(control), list(control))
    if st.battlePtr:
        battle_finish()
    print(f"対照(Staryu×4 + 水エネ×56 の同型対戦): errorPlayer={st.errorPlayer} "
          f"errorType={st.errorType} → {'OK' if st.errorPlayer < 0 else '**方式が使えない**'}")
    if st.errorPlayer >= 0:
        return 1
    print("  → 基本エネは4枚制限の対象外、かつたね1種4枚で受理されることを確認\n")

    cards = load_cards()
    print(f"走査対象 {len(cards)} 枚(EN_Card_Data.csv 全件)\n")
    ok, ng, err = [], [], []
    for n, (cid, name, stage) in enumerate(cards, 1):
        if cid in (STARYU, WATER):
            ok.append((cid, name, stage))
            continue
        test = [STARYU] * 4 + [WATER] * 52 + [cid] * 4
        try:
            _, s = battle_start(test, list(control))
            ep = s.errorPlayer
            if s.battlePtr:
                battle_finish()
        except Exception as e:
            err.append((cid, name, stage, f"{type(e).__name__}: {e}"))
            continue
        (ok if ep < 0 else ng).append((cid, name, stage))
        if n % 250 == 0:
            print(f"  ...{n}/{len(cards)}  有効{len(ok)} 無効{len(ng)} 例外{len(err)}",
                  flush=True)

    print(f"\n=== 結果 ===")
    print(f"  受理(4枚積んで有効) : {len(ok)}")
    print(f"  不受理               : {len(ng)}")
    print(f"  例外                 : {len(err)}")
    print(f"  合計                 : {len(cards)}")

    from collections import Counter
    print("\n--- 受理されたカードの種別内訳 ---")
    for k, v in Counter(s for _, _, s in ok).most_common():
        print(f"  {k:<24}{v}")
    print("\n--- 不受理の種別内訳 ---")
    for k, v in Counter(s for _, _, s in ng).most_common():
        print(f"  {k:<24}{v}")

    out = os.path.join(REPO, "verification/data/card_support.json")
    with open(out, "w") as f:
        json.dump({"ok": [c for c, _, _ in ok], "ng": [c for c, _, _ in ng],
                   "err": [c for c, _, _, _ in err]}, f)
    print(f"\n書き出し: {out}")
    if err:
        print("\n例外を出したカード(先頭10):")
        for cid, name, stage, e in err[:10]:
            print(f"  {cid} {name} [{stage}] {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

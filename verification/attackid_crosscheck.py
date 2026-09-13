#!/usr/bin/env python3
"""ワザIDの通番導出の悉皆証明 (2026-08-13、deck_fit_audit の前提検査)。

**なぜ**: `deck_fit_audit.py` は**エンジンを import しない**(どこからでも走る・0.3秒・
dylib不要)。しかしパイロットのハードコード定数はカードIDとワザIDが**同じ名前空間に見えて
違う**ので、ワザIDをカードに解決できないと判定が全部ずれる。実測: `1072` はワザなら
Alakazam「Powerful Hand」だが**カードなら Snorlax**、`1488` はカードとして存在しない
(カードIDの最大は1267)。範囲で当て推量すると **ATTACK名前空間の定数が全滅する**。

そこで audit 側は `EN_Card_Data.csv` の**ワザ行の通番**からワザID→所有カードを導出する。
本スクリプトは、その導出が正しいことを**エンジンに突き合わせて悉皆で証明する**。
audit は4点の固定検査しか持たない(起動が速いことが要件)ので、
**ATTACK名前空間の判定を引用する前に、1回これを走らせる**のが手順。

**対戦は1戦も走らせない**(`all_attack()` / `all_card_data()` を1回ずつ叩くだけ、約1秒)。

**導出規則**: `Move Name` が空でも `n/a` でも `[Ability]…` でもなく、かつ `Cost != "n/a"`
である行を CSV の出現順に並べ、1始まりで番号を振る = そのカードのワザID。
(`Cost == "n/a"` の除外が `[Tera]` / `Tera` の標識行を落とす。)

使い方(デッキディレクトリから — `cg` が要るため):
    cd src/input/datasets/decks/starmie-aggro
    python3 ../../../../../verification/attackid_crosscheck.py

出力の読み方: `OWNER_MISMATCH=0` が必須条件。`NAME_MISMATCH` は表示名だけの差で、
既知の2件(カード979 Koraidon ex)はエンジン側の名前ずれ = 既知の想定内。
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.getcwd())

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "data", "EN_Card_Data.csv")

# エンジン側の既知の名前ずれ。カード979 Koraidon ex は CSV に3行
# ('Tera'(Cost n/a) / 'Orichalcum Fang'(dmg 50) / 'Impact Blow'(dmg 200))を持つが、
# エンジンは 1408='Tera'(dmg 50) / 1409='Orichalcum Fang'(dmg 200) と名前を1つずらして持つ。
# **打点とコストは CSV 側の行と完全一致する**ので、ずれているのはエンジンの名前欄。
# 所有カードは一致するため audit の判定には影響しない。
KNOWN_NAME_SHIFT = {1408, 1409}


def derive_from_csv(path: str):
    """CSV から (attackId -> (cardId, cardName, moveName, damage, cost)) を導出する。"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    aid = 0
    for r in rows:
        mv = (r.get("Move Name") or "").strip()
        cost = (r.get("Cost") or "").strip()
        if not mv or mv == "n/a" or mv.startswith("[Ability]") or cost == "n/a":
            continue
        aid += 1
        out[aid] = (int(r["Card ID"]), (r.get("Card Name") or "").strip(),
                    mv, (r.get("Damage") or "").strip(), cost)
    return out, len(rows)


def main() -> None:
    try:
        from cg.api import all_attack, all_card_data
    except ImportError:
        sys.exit("cg が import できない。デッキディレクトリから実行すること "
                 "(例: cd src/input/datasets/decks/starmie-aggro)")

    atks = all_attack()
    cards = all_card_data()

    engine_name = {a.attackId: (a.name or "").strip() for a in atks}
    owner = {}
    multi = []
    for c in cards:
        for aid in c.attacks:
            if aid in owner:
                multi.append(aid)
            owner[aid] = c

    derived, n_rows = derive_from_csv(CSV_PATH)

    ids = sorted(a.attackId for a in atks)
    contiguous = ids == list(range(1, len(ids) + 1))

    name_bad, owner_bad, missing = [], [], []
    for aid, (cid, cname, mv, dmg, cost) in derived.items():
        if aid not in engine_name:
            missing.append(aid)
            continue
        if engine_name[aid] != mv and aid not in KNOWN_NAME_SHIFT:
            name_bad.append((aid, mv, engine_name[aid]))
        o = owner.get(aid)
        if o is None or o.cardId != cid:
            owner_bad.append((aid, cid, cname, None if o is None else (o.cardId, o.name)))

    print("ワザID通番導出の悉皆突合 — 対戦0戦")
    print(f"  CSV: {os.path.relpath(CSV_PATH)}  行 {n_rows} / 導出ワザ {len(derived)}")
    print(f"  エンジン: ワザ {len(atks)} / カード {len(cards)}")
    print(f"  attackId は 1..{len(ids)} で連番: {contiguous}")
    print(f"  複数カードが所有するワザ: {len(set(multi))}   所有者不明のワザ: {len(atks) - len(owner)}")
    print()
    if owner_bad:
        print(f"  ★所有カードの不一致 {len(owner_bad)} 件(致命的 — 導出が壊れている):")
        for aid, cid, cname, got in owner_bad[:10]:
            print(f"    aid={aid} CSV={cid}({cname}) エンジン={got}")
    if name_bad:
        print(f"  表示名の不一致 {len(name_bad)} 件(既知の2件を除く):")
        for aid, mv, en in name_bad[:10]:
            print(f"    aid={aid} CSV={mv!r} エンジン={en!r}")
    if missing:
        print(f"  エンジンに存在しない導出ID {len(missing)} 件: {missing[:10]}")

    known = [(aid, derived[aid][2], engine_name.get(aid)) for aid in sorted(KNOWN_NAME_SHIFT)
             if aid in derived]
    print("  既知のエンジン側名前ずれ(カード979 Koraidon ex、打点/コストは CSV と一致):")
    for aid, mv, en in known:
        print(f"    aid={aid} CSV={mv!r} / エンジン={en!r}")

    ok = (not owner_bad) and (not name_bad) and (not missing) and contiguous \
        and len(derived) == len(atks)
    print()
    print(f"TOTAL_ATTACKS={len(atks)}")
    print(f"TOTAL_CARDS={len(cards)}")
    print(f"DERIVED={len(derived)}")
    print(f"OWNER_MISMATCH={len(owner_bad)}")
    print(f"NAME_MISMATCH={len(name_bad)}")
    print(f"KNOWN_NAME_SHIFT={len(known)}")
    print(f"VERDICT={'PASS' if ok else 'FAIL'}")
    print("CROSSCHECK_JSON=" + json.dumps({
        "attacks": len(atks), "cards": len(cards), "derived": len(derived),
        "contiguous": contiguous, "owner_mismatch": len(owner_bad),
        "name_mismatch": len(name_bad), "known_name_shift": sorted(KNOWN_NAME_SHIFT),
        "pass": ok,
    }, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

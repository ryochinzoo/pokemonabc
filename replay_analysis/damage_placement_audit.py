#!/usr/bin/env python3
"""ダメカン/ダメージ配置(main.py:464-478 HP昇順)のサイド枚数監査(測定専用)。

問い: megaEx=3枚が確定した今、HP昇順の配置が「サイド枚数最大化」と異なる選択を
実ラダーで何回したか。0件なら実装しない(事前固定)。

判定規則(実行前に固定):
  - 対象 = 自分ACTIVEの DAMAGE系context決定点(off-by-one補正済みactionで選択を読む)
  - 各選択肢の対象ポケモンに (サイド枚数[1/2/3=getPrizeCount基礎値], HP) を付す
  - CF1(保守的対案) = 「KO可能(HP<=50)な対象の中でサイド枚数最大(同数はHP昇順)。
    KO可能が無ければ現行と同じHP昇順」 ※50はJetting Blowのベンチ打点。DAMAGE文脈のみ適用
  - CF2(素朴対案) = 「常にサイド枚数最大(同数はHP昇順)」
  - 「異なる選択」 = 実際の選択(本番の挙動) != CF の選択

使い方:
  cd src/input/datasets/decks/starmie-aggro && \
  python3 ../../../../../replay_analysis/damage_placement_audit.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/input/datasets/decks/starmie-aggro"))
from cg.api import SelectContext, to_observation_class  # noqa: E402
import main as champ  # noqa: E402

CARDS, _ = champ._card_db()
OUR = "Yser"
DMG_CTX = {int(SelectContext.DAMAGE_COUNTER), int(SelectContext.DAMAGE_COUNTER_ANY),
           int(SelectContext.DAMAGE)}
JETTING_BENCH = 50


def prize_of(cid):
    c = CARDS.get(cid)
    if c is None:
        return 1
    if getattr(c, "megaEx", False):
        return 3
    if getattr(c, "ex", False):
        return 2
    return 1


def main():
    n_points = n_multi = n_mixed = 0
    diff_cf1 = diff_cf2 = 0
    n_multipick = 0
    examples = []
    ctx_count = Counter()
    for d in ["eps55058443", "eps55060473"]:
        for f in sorted((ROOT / "replay_analysis" / d).glob("*.json")):
            try:
                rep = json.loads(f.read_text())
            except Exception:
                continue
            nm = (rep.get("info") or {}).get("TeamNames") or []
            if OUR not in nm:
                continue
            me = nm.index(OUR)
            steps = rep["steps"]
            for si, step in enumerate(steps):
                if me >= len(step):
                    continue
                e = step[me]
                if e.get("status") != "ACTIVE":
                    continue
                obsd = e.get("observation") or {}
                sel = obsd.get("select")
                if not sel or not sel.get("option"):
                    continue
                if sel.get("context") not in DMG_CTX:
                    continue
                act = (steps[si + 1][me].get("action")
                       if si + 1 < len(steps) and me < len(steps[si + 1]) else None)
                if not act:
                    continue
                try:
                    obs = to_observation_class(obsd)
                except Exception:
                    continue
                if obs.select is None or obs.current is None:
                    continue
                st = obs.current
                n_points += 1
                ctx_count[sel.get("context")] += 1
                opts = obs.select.option
                if len(opts) < 2:
                    continue
                n_multi += 1
                # 各選択肢の (prize, hp)
                cand = []
                for i, o in enumerate(opts):
                    pk = champ._pokemon_at(st, o.playerIndex, o.area, o.index)
                    if pk is None:
                        cand.append((i, None, None))
                    else:
                        cand.append((i, prize_of(pk.id), pk.hp or 0))
                known = [c for c in cand if c[1] is not None]
                if len({c[1] for c in known}) >= 2:
                    n_mixed += 1
                else:
                    continue  # サイド枚数が全対象で同一なら規則差は発生しない
                if len(act) != 1:
                    n_multipick += 1
                    continue
                chosen = act[0]
                is_dmg = sel.get("context") == int(SelectContext.DAMAGE)
                # CF1: KO可能(hp<=50)の中で prize最大→HP昇順。無ければHP昇順
                koable = [c for c in known if is_dmg and c[2] <= JETTING_BENCH]
                if koable:
                    cf1 = min(koable, key=lambda c: (-c[1], c[2]))[0]
                else:
                    cf1 = min(known, key=lambda c: (c[2], ))[0]
                cf2 = min(known, key=lambda c: (-c[1], c[2]))[0]
                if chosen != cf1:
                    diff_cf1 += 1
                    if len(examples) < 10:
                        examples.append((f.stem, st.turn, "CF1",
                                         [(CARDS.get(champ._pokemon_at(st, o.playerIndex, o.area, o.index).id).name
                                           if champ._pokemon_at(st, o.playerIndex, o.area, o.index) else "?",
                                           c[1], c[2]) for o, c in zip(opts, cand)],
                                         chosen, cf1))
                if chosen != cf2:
                    diff_cf2 += 1

    print("# ダメカン/ダメージ配置のサイド枚数監査(56戦・シフト補正済み)\n")
    print(f"- DAMAGE系決定点(action有り): {n_points} (context内訳 {dict(ctx_count)})")
    print(f"- 選択肢2つ以上: {n_multi}")
    print(f"- **サイド枚数の異なる対象が混在: {n_mixed}**")
    print(f"- 複数同時選択(minCount>1)で除外: {n_multipick}")
    print(f"- **実選択 != CF1(KO可能内サイド最大): {diff_cf1}**")
    print(f"- 実選択 != CF2(常にサイド最大): {diff_cf2}")
    print("\n事前固定の判定: CF1差分が0件なら実装しない。")
    for ex in examples:
        print("  例:", ex)


if __name__ == "__main__":
    main()

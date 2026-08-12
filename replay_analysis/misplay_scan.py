#!/usr/bin/env python3
"""実リプレイから「機械的に判定できるミス」を**手元で数える**。

NotebookLM に数えさせないための道具。LLMは検索で上位k件しか引かないので
「何回あったか」には答えられないし、2026-08-10には**判定は当てたのに理由を取り違えた**
(Archer を「1枚も引けない」と説明したが、実際は手札を山に戻して5枚引く札だった)。
→ **どこを見るかはLLM、数えるのはここ。**

数えるもの:

1. **リーサル見逃し** — **そのターンが終わるまでに一度も攻撃しなかった**のに、
   ターン中に「基本打点 ≥ 相手アクティブ残HP」の ATTACK が合法だった回数。

   **決定点ごとに数えてはいけない**(2026-08-10に踏んだ): 1ターンの中で
   エージェントは「出す→出す→付ける→**攻撃**」と何度も MAIN 決定をする。
   攻撃はターンを終わらせるので、**攻撃前に手札を使い切るのは正しいプレイ**。
   決定点ごとに数えると、その正しい手順が全部「見逃し」に化ける。
   実際それで 98回 と出た(正しくは後述)。勝ち譜ほど数が増えるという
   **逆向きの異常**が出て気づいた。
2. **手札リセットの空撃ち** — 「手札を山に戻して N 枚引く」系のサポートを、
   手札が N 枚より多い状態で使い、**差引で手札を減らした**回数。

**どちらも過小に数える側に倒してある**(下の「数え方の限界」参照)。
出た数字は「少なくともこれだけある」であって上限ではない。

    cd src/input/datasets/decks/<deck> && \
      python3 ../../../../../replay_analysis/misplay_scan.py <epsDir> [maxN]
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path.cwd()))
from cg.api import all_attack  # noqa: E402

ATTACKS = {a.attackId: a for a in all_attack()}
OUR_TEAM = "Yser"

OPT_PLAY, OPT_ATTACK = 7, 13
SEL_MAIN = 0


def _hand_reset_supporters():
    """「手札を山に戻して N 枚引く」サポートを効果文から拾い、N を返す。

    Archer の教訓: **カード名や『ドロー系』という直感で判定しない。効果文を読む。**
    """
    out = {}
    with open(ROOT / "verification/data/EN_Card_Data.csv") as f:
        for r in csv.DictReader(f):
            eff = (r.get("Effect Explanation") or "").replace("’", "'")
            low = eff.lower()
            if "hand into" not in low or "deck" not in low:
                continue
            m = re.search(r"you draw (\d+) card", low)
            if m:
                out[int(r["Card ID"])] = (r["Card Name"], int(m.group(1)))
    return out


RESET = _hand_reset_supporters()


def _active_hp(player):
    a = (player or {}).get("active") or []
    c = a[0] if a else None
    return c.get("hp") if isinstance(c, dict) else None


def scan_episode(path):
    """1譜を走査して所見を返す。"""
    d = json.loads(Path(path).read_text())
    info = d.get("info") or {}
    names = info.get("TeamNames") or []
    rewards = d.get("rewards") or []
    found = []
    turns = {}          # (席, 手番) -> そのターンの要約
    steps = d.get("steps", [])
    for si, st in enumerate(steps):
        for ai, a in enumerate(st):
            # 手番でない側の観測は前の残骸(action=[])。status でしか判別できない。
            if a.get("status") != "ACTIVE":
                continue
            o = a.get("observation") or {}
            sel = o.get("select") or {}
            opts = sel.get("option") or []
            # **応答は次のstepに記録される**(2026-08-11確定、134譜4,593決定で99.9%)。
            # steps[si].action を使うと 29% しか当たらず、所見が丸ごと偽になる。
            act = (steps[si + 1][ai].get("action") if si + 1 < len(steps) else None)
            if not opts or not isinstance(act, list) or not act:
                continue
            cur = o.get("current") or {}
            players = cur.get("players") or []
            if len(players) != 2:
                continue
            me, foe = players[ai], players[1 - ai]
            chosen = [opts[i] for i in act if 0 <= i < len(opts)]

            # --- 1) リーサル見逃し（ターン単位で集計。判定はループの後） ---
            if sel.get("type") == SEL_MAIN:
                key = (ai, cur.get("turn"))
                t = turns.setdefault(key, {"lethal": 0, "attacked": False,
                                           "step": si, "foeHp": None, "aid": None})
                foe_hp = _active_hp(foe)
                for op in opts:
                    if op.get("type") == OPT_ATTACK and op.get("attackId") is not None:
                        atk = ATTACKS.get(op["attackId"])
                        dmg = (getattr(atk, "damage", 0) or 0) if atk else 0
                        if foe_hp is not None and dmg >= foe_hp > 0 and dmg > t["lethal"]:
                            t.update(lethal=dmg, foeHp=foe_hp, aid=op["attackId"], step=si)
                if any(c.get("type") == OPT_ATTACK for c in chosen):
                    t["attacked"] = True

            # --- 2) 手札リセットの空撃ち ---
            for c in chosen:
                if c.get("type") != OPT_PLAY:
                    continue
                idx, hand = c.get("index"), (me.get("hand") or [])
                if idx is None or not (0 <= idx < len(hand)):
                    continue
                cid = (hand[idx] or {}).get("id")
                if cid in RESET:
                    nm, draw = RESET[cid]
                    if len(hand) > draw:
                        found.append({"kind": "reset_waste", "seat": ai, "step": si,
                                      "turn": cur.get("turn"), "card": nm,
                                      "hand": len(hand), "draw": draw,
                                      "net": draw - len(hand)})
    # ターン単位で確定させる: リーサルがあったのに、そのターン一度も攻撃しなかった
    for (ai, turn), t in turns.items():
        if t["lethal"] and not t["attacked"]:
            found.append({"kind": "lethal_miss", "seat": ai, "turn": turn,
                          "step": t["step"], "dmg": t["lethal"],
                          "foeHp": t["foeHp"], "attackId": t["aid"]})
    return found, names, rewards


def main():
    eps_dir = Path(sys.argv[1])
    max_n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    files = sorted(eps_dir.glob("ep*.json"))
    if max_n:
        files = files[:max_n]
    print(f"走査: {len(files)}譜 / 手札リセット系サポート {len(RESET)}種を認識")
    print("  例: " + ", ".join(f"{n}(→{k}枚)" for n, k in list(RESET.values())[:4]))
    print()

    tot = Counter()
    per_game = []
    examples = []
    for f in files:
        found, names, rewards = scan_episode(f)
        # 我々の席(自己対戦の譜もあるので、両席とも我々なら両方数える)
        ours = [i for i, n in enumerate(names) if n == OUR_TEAM] or [0, 1]
        mine = [x for x in found if x["seat"] in ours]
        c = Counter(x["kind"] for x in mine)
        tot.update(c)
        won = rewards[ours[0]] == 1 if rewards and ours else None
        per_game.append((f.name, won, c["lethal_miss"], c["reset_waste"]))
        for x in mine[:2]:
            if len(examples) < 6:
                examples.append((f.name, x))

    n = len(files)
    print(f"=== 合計（{n}譜） ===")
    print(f"  リーサル見逃し        {tot['lethal_miss']:>4} 回"
          f"   （1譜あたり {tot['lethal_miss']/max(1,n):.2f}）")
    print(f"  手札リセットの空撃ち  {tot['reset_waste']:>4} 回"
          f"   （1譜あたり {tot['reset_waste']/max(1,n):.2f}）")
    print()
    lost = [g for g in per_game if g[1] is False]
    won = [g for g in per_game if g[1] is True]
    for lab, grp in (("負け譜", lost), ("勝ち譜", won)):
        if grp:
            print(f"  {lab} {len(grp):>3}本: リーサル見逃し {sum(g[2] for g in grp)/len(grp):.2f}/譜"
                  f"  空撃ち {sum(g[3] for g in grp)/len(grp):.2f}/譜")
    print()
    print("=== 実例 ===")
    for fn, x in examples:
        if x["kind"] == "lethal_miss":
            print(f"  {fn} 手番{x['turn']} step{x['step']}: "
                  f"打点{x['dmg']} ≥ 相手HP{x['foeHp']} なのに攻撃せず")
        else:
            print(f"  {fn} 手番{x['turn']} step{x['step']}: "
                  f"{x['card']} を手札{x['hand']}枚で使用 → {x['draw']}枚（差引{x['net']:+d}）")
    print()
    print("=== 数え方の限界（過小側に倒してある）===")
    print("  - 打点は**基本値のみ**。弱点/効果による増加は見ていない → 見逃しを取りこぼす")
    print("  - damage=0 の可変打点技（Rocket Rush 等）は0として扱う → 同上")
    print("  - 抵抗力/軽減効果は見ていない → 逆に**過大**に数える方向の誤差もありうる")
    print("  - 「攻撃すべきだった」とは限らない（壁を残す等の理由はありうる）")
    print("  → 出た数は『少なくともこれだけ』。採否は必ずローカル実測で。")


if __name__ == "__main__":
    main()

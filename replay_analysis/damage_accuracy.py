#!/usr/bin/env python3
"""_estimate_damage の予測精度を実リプレイで測定する（測定専用・実装は変更しない）。

原理:
  リプレイの observation.current が各決定点の State そのものなので、盤面復元器は不要。
  我々が ATTACK オプションを選んだ決定点で main._estimate_damage() を実行し、
  直後の HP_CHANGE(16).value（相手バトル場ぶん）と突き合わせる。

使い方:
  python3 replay_analysis/damage_accuracy.py [<エピソードdir> ...]
  既定は replay_analysis/eps55058443 と eps55060473。

出力:
  docs/memo/damage-accuracy.md
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "src/input/datasets/decks/starmie-aggro"
OUT = ROOT / "docs/memo/damage-accuracy.md"
OUR_TEAM = "Yser"

sys.path.insert(0, str(DECK))
import main as champ  # noqa: E402
from cg.api import all_attack, all_card_data, to_observation_class  # noqa: E402

ATTACKS = {a.attackId: a for a in all_attack()}
CARDS = {c.cardId: c for c in all_card_data()}

LOG_ATTACK, LOG_HP, LOG_TURN_END, LOG_TURN_START, LOG_COIN = 15, 16, 3, 2, 22


def our_index(rep):
    names = (rep.get("info") or {}).get("TeamNames") or []
    return names.index(OUR_TEAM) if OUR_TEAM in names else None


def collect(rep, me):
    """決定点と ATTACK ログを時系列で突き合わせ、対応づいた行のリストを返す。

    ペアリングは「順序＋attackId一致」ではなく **ログ到着順に pending を消費** する。
    ログ(observation.logs)は決定の *後* に次の観測で届くので、
    ATTACK(15) が現れた時点で、それ以前に選ばれた同 attackId の決定を1件消費する。
    同一 attackId が ATTACK ログを挟まずに連続選択された場合(MAIN→ATTACK の二段選択)は
    後勝ちで置き換え、1回の攻撃に2件を作らない。
    """
    pending, rows, stream = [], [], []

    def drain_logs(batch):
        """届いたログを順に処理し、ATTACK が出たら pending を1件解決する。"""
        for i, lg in enumerate(batch):
            if lg.get("type") != LOG_ATTACK or lg.get("playerIndex") != me:
                continue
            aid = lg.get("attackId")
            k = next((j for j, p in enumerate(pending) if p["attackId"] == aid), None)
            if k is None:
                continue
            p = pending.pop(k)
            del pending[:k]  # 解決されずに飛ばされた古い候補は捨てる
            dealt, coin = defaultdict(int), False
            for lg2 in batch[i + 1:]:
                t = lg2.get("type")
                if t in (LOG_ATTACK, LOG_TURN_END, LOG_TURN_START):
                    break
                if t == LOG_COIN:
                    coin = True
                if t == LOG_HP and lg2.get("playerIndex") == 1 - me:
                    dealt[lg2.get("serial")] += abs(lg2.get("value") or 0)
            rows.append(dict(**p, actual=dealt.get(p["foe_serial"], 0),
                             dealt_all=dict(dealt), coin=coin))

    for step in rep["steps"]:
        if me >= len(step):
            continue
        entry = step[me]
        if entry.get("status") != "ACTIVE":
            continue
        obs_dict = entry.get("observation") or {}
        batch = obs_dict.get("logs") or []
        stream.extend(batch)
        drain_logs(batch)

        sel = obs_dict.get("select")
        action = entry.get("action")
        if not sel or not sel.get("option") or not action:
            continue
        try:
            obs = to_observation_class(obs_dict)
        except Exception:
            continue
        if obs.select is None or obs.current is None:
            continue
        state = obs.current
        my_idx = state.yourIndex if state.yourIndex is not None else me
        for oi in action:
            if not isinstance(oi, int) or oi < 0 or oi >= len(obs.select.option):
                continue
            opt = obs.select.option[oi]
            aid = getattr(opt, "attackId", None)
            if aid is None:
                continue
            try:
                pred = champ._estimate_damage(aid, state, my_idx)
            except Exception as e:
                pred = None
                print(f"  ! _estimate_damage 失敗 attackId={aid}: {e}")
            try:
                foe = state.players[1 - my_idx].active[0]
                foe_serial, foe_id, foe_hp = foe.serial, foe.id, foe.hp
                foe_tools = tuple(sorted(t.id for t in (foe.tools or []) if t))
            except (IndexError, TypeError, AttributeError):
                foe_serial = foe_id = foe_hp = None
                foe_tools = ()
            try:
                stadium = tuple(sorted(c.id for c in (state.stadium or []) if c))
            except (TypeError, AttributeError):
                stadium = ()
            rec = dict(attackId=aid, pred=pred, foe_serial=foe_serial,
                       foe_id=foe_id, foe_hp=foe_hp, foe_tools=foe_tools,
                       stadium=stadium)
            if pending and pending[-1]["attackId"] == aid:
                pending[-1] = rec  # 二段選択の後勝ち
            else:
                pending.append(rec)

    n_atk = sum(1 for lg in stream
                if lg.get("type") == LOG_ATTACK and lg.get("playerIndex") == me)
    return rows, n_atk


# 「30 less damage」等をテキストに持つカード（DB全走査で抽出済み）
_REDUCERS = {}
for _c in CARDS.values():
    for _sk in _c.skills or []:
        if "less damage" in (_sk.text or "").lower():
            _REDUCERS[_c.cardId] = _c.name


def classify(pred, actual, aid, coin, stadium=(), foe_tools=(), foe_id=None):
    atk = ATTACKS.get(aid)
    base = (atk.damage if atk else 0) or 0
    text = (atk.text if atk else "") or ""
    if pred == actual:
        return "一致"
    if coin:
        return "コイン（未実装）"
    hit_stadium = [c for c in stadium if c in _REDUCERS]
    hit_tool = [c for c in foe_tools if c in _REDUCERS]
    if actual < pred:
        if hit_stadium:
            return f"スタジアム未読（{_REDUCERS[hit_stadium[0]]}）"
        if hit_tool:
            return f"道具未読（{_REDUCERS[hit_tool[0]]}）"
        if foe_id in _REDUCERS:
            return f"特性未読（{_REDUCERS[foe_id]}）"
        return "軽減・無効化（出所未特定）" if actual > 0 else "無効化（出所未特定）"
    if base == 0 and actual > 0:
        return "damage=0だが実打点あり"
    if actual > pred:
        return "効果文による加算" if text.strip() else "未分類（素点より大）"
    return "未分類"


def main(dirs):
    rows, files, skipped, total_attacks = [], 0, 0, 0
    for dpath in dirs:
        for f in sorted(Path(dpath).glob("*.json")):
            try:
                rep = json.loads(f.read_text())
            except Exception:
                skipped += 1
                continue
            me = our_index(rep)
            if me is None:
                skipped += 1
                continue
            files += 1
            got, n_atk = collect(rep, me)
            total_attacks += n_atk
            for r in got:
                rows.append(dict(ep=f.stem, **r,
                                 verdict=classify(r["pred"], r["actual"],
                                                  r["attackId"], r["coin"],
                                                  r.get("stadium", ()),
                                                  r.get("foe_tools", ()),
                                                  r.get("foe_id"))))
    return rows, files, skipped, total_attacks


def report(rows, files, skipped, total_attacks):
    n = len(rows)
    hit = sum(1 for r in rows if r["verdict"] == "一致")
    L = []
    L.append("# `_estimate_damage` の予測精度（実リプレイ測定）\n")
    L.append("> 測定専用。`main.py` は一切変更していない。")
    L.append("> 再実行: `cd src/input/datasets/decks/starmie-aggro && "
             "python3 ../../../../../replay_analysis/damage_accuracy.py`\n")
    L.append(f"- 対象: {files} 戦（読めなかった/自チーム不明: {skipped}）")
    L.append(f"- ログ上の自分の ATTACK イベント: **{total_attacks}** 件")
    L.append(f"- 決定点と突合できた攻撃: **{n}** 件"
             f"（突合率 {100*n/total_attacks:.1f}%）" if total_attacks else "")
    L.append(f"- 予測が実測と完全一致: **{hit} / {n} = {100*hit/n:.1f}%**\n" if n else "")
    L.append("## 不一致の原因別内訳\n")
    L.append("| 分類 | 件数 | 割合 |")
    L.append("|---|---:|---:|")
    for k, v in Counter(r["verdict"] for r in rows).most_common():
        L.append(f"| {k} | {v} | {100*v/n:.1f}% |")
    L.append("\n## 不一致の attackId 別頻度（上位20）\n")
    L.append("| attackId | ワザ名 | 件数 | 予測→実測(例) | damage欄 | 分類 |")
    L.append("|---|---|---:|---|---:|---|")
    bad = [r for r in rows if r["verdict"] != "一致"]
    for aid, cnt in Counter(r["attackId"] for r in bad).most_common(20):
        ex = next(r for r in bad if r["attackId"] == aid)
        atk = ATTACKS.get(aid)
        L.append(f"| {aid} | {atk.name if atk else '?'} | {cnt} | "
                 f"{ex['pred']} → {ex['actual']} | {(atk.damage if atk else 0)} | {ex['verdict']} |")
    L.append("\n## 不一致ワザの効果文\n")
    for aid, cnt in Counter(r["attackId"] for r in bad).most_common(10):
        atk = ATTACKS.get(aid)
        if atk:
            L.append(f"- **[{aid}] {atk.name}** (damage欄={atk.damage}, {cnt}件)\n"
                     f"  - `{(atk.text or '').strip()[:300]}`")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    ds = sys.argv[1:] or [str(ROOT / "replay_analysis/eps55058443"),
                          str(ROOT / "replay_analysis/eps55060473")]
    rows, files, skipped, total_attacks = main(ds)
    report(rows, files, skipped, total_attacks)

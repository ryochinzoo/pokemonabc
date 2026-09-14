#!/usr/bin/env python3
"""bosslogic 本番検死: 事前登録した行動予測(prereg-2026-08-16-bosslogic.md T1 + v3〜v9追記)を機械検証する.

使い方:
  python3 replay_analysis/bosslogic_autopsy.py <epsDir> [--deck-dir DIR] [--limit N] [--json OUT]
  既定 deck-dir = src/input/datasets/decks/starmie-aqua-bosslogic(最終バイト b67466a9 の main.py の
  ヘルパを V2_NO_SEARCH=1 で直接呼ぶ。対照 eps55552195 も**同じ規則**で採点する)。

プローブ(いずれも「本番で選ばれた手」を最終規則で再採点する。効果量は測らない):
  P0 CRASH/結果  : replay の statuses / rewards(自席が DONE でなければ CRASH 候補)
  P1 BOSS_TARGET : CARD/SWITCH で候補が全て相手側(ボスの指令系の対象選択)→ 選択が _dragout_value
                   の最大か(同点可)+ 内訳(KO可 / 進化前 / 縛り / 最弱)
  P2 BOSS_MISFIRE: MAIN で PLAY=ガスト系サポート → L8 条件(アクティブKO可 かつ ベンチ最良≤アクティブ
                   かつ 非コンボ)なら誤爆。v1 再実行で帰属(v1 由来 / 探索上書き)を分ける
  P3 ATTACK_SPLIT: ATTACK 選択で KO可能ワザ≥2 かつ ライダー技あり → ライダー技の選択率(L9)
  P4 ATTACK_RUSH : MAIN で ATTACK 選択 かつ ATTACH/PLAY/EVOLVE/ABILITY が合法 → v1 再実行で
                   L12 違反(v1 は無料行動)か v1 公認(v1 も ATTACK)か
  P5 END_STALL   : MAIN で END 選択 かつ ATTACK が合法(end_stall_count.py と同一定義)
対応規則(CLAUDE.md 罠1,2): 選択肢= steps[N].observation.select.option、答え= steps[N+1].action、
手番= status=="ACTIVE"。自席= deck.csv との重なりが大きい側。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DECK_DIR = REPO / "src/input/datasets/decks/starmie-aqua-bosslogic"

RUNNER = r'''
import json, os, sys
from collections import Counter
sys.path.insert(0, ".")
os.environ["V2_NO_SEARCH"] = "1"
import main
from cg.api import SelectType, SelectContext, OptionType

FREE = {int(OptionType.PLAY), int(OptionType.ATTACH), int(OptionType.EVOLVE), int(OptionType.ABILITY)}
deck_ids = Counter(int(x) for x in open("deck.csv").read().split())
gust_ids = main._gust_supporter_ids()


def affordable_damage(state, me):
    """今の貼りエネで**実際に撃てる**ワザの最大打点(J-C 指摘 2026-09-02: _my_active_damage は印字最大で
    エネを見ない)。pk.energies = エンジン計算の供給ユニット(EnergyType の列、Ignition on Mega=[0,0,0])。"""
    try:
        act = state.players[me].active[0]
    except Exception:
        return 0
    if act is None:
        return 0
    cards_db, attacks = main._card_db()
    c = cards_db.get(act.id)
    if c is None:
        return 0
    units = [int(x) for x in (act.energies or [])]
    best = 0
    for aid in c.attacks or []:
        a = attacks.get(aid)
        if a is None:
            continue
        need = [int(x) for x in (a.energies or [])]
        u = units[:]
        ok = True
        for t in [x for x in need if x != 0]:
            if t in u:
                u.remove(t)
            elif 10 in u:
                u.remove(10)
            else:
                ok = False
                break
        if ok and len(u) >= sum(1 for x in need if x == 0):
            best = max(best, a.damage or 0)
    return best


class _energy_aware:
    """with ブロック内だけ main._my_active_damage をエネ考慮版に差し替える(L8/L7 の再採点用)。"""
    def __init__(self, state, me):
        self.v = affordable_damage(state, me)
    def __enter__(self):
        self.orig = main._my_active_damage
        main._my_active_damage = lambda s, m, _v=self.v: _v
        return self.v
    def __exit__(self, *a):
        main._my_active_damage = self.orig


def l8_view(obs, me):
    """_choose_main の L8/L24 判定を同じヘルパで再計算する(誤爆= not combo and active KO可 and bench≤active)."""
    state = obs.current
    opp = 1 - me
    cards_db, _ = main._card_db()
    try:
        opp_active = state.players[opp].active[0]
    except Exception:
        opp_active = None
    dmg = main._my_active_damage(state, me)
    evn = main._opp_evolvable_names(state, me)

    def ko_key(pk):
        if pk is None or not (dmg > 0 and (pk.hp or 9999) <= dmg):
            return None
        c2 = cards_db.get(pk.id)
        ev = evn.get(c2.name, 0) if c2 is not None else 0
        return (main._prize_value(pk.id), ev)

    active_key = ko_key(opp_active)
    bench_keys = [k for k in (ko_key(b) for b in (state.players[opp].bench or [])) if k]
    best_bench = max(bench_keys) if bench_keys else None
    combo = False
    if opp_active is not None and best_bench is not None:
        try:
            my_act = state.players[me].active[0]
            splash = 0
            c_my = cards_db.get(my_act.id) if my_act is not None else None
            for aid2 in (c_my.attacks if c_my else None) or []:
                splash = max(splash, main._BENCH_SPLASH.get(aid2, 0))
            has_colored = bool(my_act is not None and any(
                e is not None and e.id != main._IGNITION_ID for e in (my_act.energyCards or [])))
            oc = cards_db.get(opp_active.id)
            blocked = opp_active.id in main._ex_wall_ids() or bool(oc is not None and getattr(oc, "tera", False))
            if splash > 0 and has_colored and not blocked and (opp_active.hp or 9999) <= splash:
                combo = True
        except Exception:
            combo = False
    misfire = (not combo) and active_key is not None and (best_bench is None or best_bench <= active_key)
    return misfire, {"active_key": active_key, "best_bench": best_bench, "combo": combo, "dmg": dmg}


def main_loop(list_path, out_path):
    files = [l.strip() for l in open(list_path) if l.strip()]
    with open(out_path, "w") as out:
        for fp in files:
            try:
                d = json.load(open(fp))
            except Exception as e:
                out.write(json.dumps({"file": os.path.basename(fp), "error": f"load:{e}"}) + "\n")
                continue
            steps = d.get("steps") or []
            if len(steps) < 2:
                out.write(json.dumps({"file": os.path.basename(fp), "error": "no steps"}) + "\n")
                continue
            decks = [Counter(a.get("action") or []) for a in steps[1]]
            ov = [sum((deck_ids & x).values()) for x in decks]
            mine = 0 if ov[0] >= ov[1] else 1
            g = {"file": os.path.basename(fp), "mine": mine, "overlap": ov,
                 "statuses": d.get("statuses"), "rewards": d.get("rewards"),
                 "n_steps": len(steps), "events": []}
            c = Counter()
            for si in range(len(steps) - 1):
                ag = steps[si][mine] or {}
                if ag.get("status") != "ACTIVE":
                    continue
                obs_d = ag.get("observation") or {}
                sel = obs_d.get("select")
                if not sel:
                    continue
                act = (steps[si + 1][mine] or {}).get("action")
                if not act:
                    continue
                opts = sel.get("option") or []
                if any(i >= len(opts) for i in act):
                    c["act_out_of_range"] += 1
                    continue
                stype, ctx = sel.get("type"), sel.get("context")
                c["decisions"] += 1
                try:
                    obs = main.to_observation_class(obs_d)
                except Exception:
                    c["parse_fail"] += 1
                    continue
                state = obs.current
                me = state.yourIndex
                if me != mine:
                    c["seat_mismatch"] += 1
                chosen_types = {opts[i].get("type") for i in act}
                avail = {o.get("type") for o in opts}
                # ---- MAIN ----
                if stype == int(SelectType.MAIN):
                    c["main"] += 1
                    if int(OptionType.END) in chosen_types and int(OptionType.ATTACK) in avail:
                        c["P5_end_stall"] += 1
                        g["events"].append([si, "P5_END_STALL", None])
                    if int(OptionType.ATTACK) in chosen_types and (avail & FREE):
                        c["P4_rush_raw"] += 1
                        try:
                            v1 = main._v1_decide(obs)
                            v1t = opts[v1[0]].get("type") if v1 else None
                        except Exception:
                            v1t = None
                        if v1t in FREE:
                            c["P4_L12_violation"] += 1
                            g["events"].append([si, "P4_ATTACK_RUSH_L12", {"v1_type": v1t, "avail": sorted(avail & FREE)}])
                        else:
                            c["P4_v1_approved"] += 1
                    for i in act:
                        o = opts[i]
                        if o.get("type") != int(OptionType.PLAY):
                            continue
                        try:
                            cid = state.players[me].hand[o.get("index")].id
                        except Exception:
                            cid = None
                        if cid in gust_ids:
                            c["P2_boss_played"] += 1
                            try:
                                misfire, det = l8_view(obs, me)
                            except Exception as e:
                                misfire, det = None, {"err": str(e)[:60]}
                            try:
                                v1 = main._v1_decide(obs)
                                v1_boss = bool(v1) and v1[0] == i
                            except Exception:
                                v1_boss = None
                            try:
                                with _energy_aware(state, me) as dmg_e:
                                    misfire_e, det_e = l8_view(obs, me)
                            except Exception:
                                misfire_e, det_e, dmg_e = None, {}, None
                            if misfire_e:
                                c["P2e_misfire"] += 1
                            elif misfire_e is not None:
                                c["P2e_boss_ok"] += 1
                            if misfire:
                                c["P2_misfire"] += 1
                                c["P2_misfire_v1" if v1_boss else "P2_misfire_search"] += 1
                                g["events"].append([si, "P2_BOSS_MISFIRE", {"v1_boss": v1_boss, "misfire_energy_aware": misfire_e, "dmg_e": dmg_e, **{k: (list(v) if isinstance(v, tuple) else v) for k, v in det.items()}}])
                            elif misfire is None:
                                c["P2_undecidable"] += 1
                            else:
                                c["P2_boss_ok"] += 1
                                c["P2_boss_ok_v1" if v1_boss else "P2_boss_ok_search"] += 1
                                if misfire_e:
                                    g["events"].append([si, "P2e_MISFIRE_ONLY_WHEN_ENERGY_COUNTED", {"dmg_rule": det.get("dmg"), "dmg_e": dmg_e, **{k: (list(v) if isinstance(v, tuple) else v) for k, v in det_e.items()}}])
                # ---- CARD / SWITCH (ボス対象) ----
                elif stype == int(SelectType.CARD) and ctx == int(SelectContext.SWITCH):
                    oo = obs.select.option
                    if oo and all(o.playerIndex is not None and o.playerIndex != me for o in oo):
                        c["P1_boss_target"] += 1
                        if len(oo) >= 2:
                            c["P1_denom_multi"] += 1
                        try:
                            keys = [main._dragout_value(obs, me, o) for o in oo]
                            best = max(keys)
                            k = keys[act[0]]
                            cat = "KO" if k[0] else ("EVOLVABLE" if k[2] > 0 else ("BIND" if k[3] > 0 else "WEAKEST"))
                            c[f"P1_cat_{cat}"] += 1
                            if k == best:
                                c["P1_conform"] += 1
                            else:
                                c["P1_nonconform"] += 1
                                g["events"].append([si, "P1_BOSS_TARGET_NONCONFORM", {"chosen": list(k), "best": list(best), "n": len(oo)}])
                            try:
                                with _energy_aware(state, me) as dmg_e:
                                    keys_e = [main._dragout_value(obs, me, o) for o in oo]
                                best_e = max(keys_e)
                                ke = keys_e[act[0]]
                                if ke == best_e:
                                    c["P1e_conform"] += 1
                                else:
                                    c["P1e_nonconform"] += 1
                                    g["events"].append([si, "P1e_NONCONFORM_WHEN_ENERGY_COUNTED", {"chosen": list(ke), "best": list(best_e), "dmg_e": dmg_e, "n": len(oo)}])
                                if bool(ke[0]) != bool(k[0]):
                                    c["P1_koable_flips_with_energy"] += 1
                            except Exception:
                                c["P1e_err"] += 1
                        except Exception as e:
                            c["P1_err"] += 1
                            g["events"].append([si, "P1_ERR", str(e)[:80]])
                # ---- ATTACK (使い分け L9) ----
                elif stype == int(SelectType.ATTACK):
                    c["attack_sel"] += 1
                    oo = obs.select.option
                    try:
                        oa = state.players[1 - me].active[0]
                        hp = oa.hp if oa is not None else None
                    except Exception:
                        hp = None
                    if hp and len(oo) >= 2:
                        dmgs = {}
                        for i2, o in enumerate(oo):
                            if o.attackId is None:
                                continue
                            try:
                                dmgs[i2] = main._estimate_damage(o.attackId, state, me)
                            except Exception:
                                pass
                        ko = [i2 for i2, dm in dmgs.items() if dm >= hp]
                        riders = [i2 for i2 in ko if main._attack_has_bench_rider(oo[i2].attackId)]
                        if len(ko) >= 2 and riders:
                            c["P3_denom"] += 1
                            if act[0] in riders:
                                c["P3_rider_chosen"] += 1
                            else:
                                c["P3_nonrider_chosen"] += 1
                                g["events"].append([si, "P3_NO_RIDER", {"ko": ko, "riders": riders, "chosen": act[0], "hp": hp, "dmgs": dmgs}])
            g["counts"] = dict(c)
            out.write(json.dumps(g) + "\n")
            out.flush()


main_loop(sys.argv[1], sys.argv[2])
'''

PRED = [  # (key, 予測, 分子キー, 分母キー, 合格条件)
    ("P0 CRASH",        "0",     "crash_games",       "games",            "k==0"),
    ("P5 END stall",    "0",     "P5_end_stall",      "main",             "k==0"),
    ("P2 Boss misfire", "0",     "P2_misfire",        "P2_boss_played",   "k==0"),
    ("P1 Boss target",  "100%",  "P1_conform",        "P1_boss_target",   "k==n"),
    ("P3 Rider split",  "100%",  "P3_rider_chosen",   "P3_denom",         "k==n"),
    ("P2e misfire(energy)", "0", "P2e_misfire",       "P2_boss_played",   "k==0"),
    ("P1e target(energy)", "100%", "P1e_conform",     "P1_boss_target",   "k==n"),
    ("P4 Attack rush",  "0",     "P4_L12_violation",  "main",             "k==0"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("eps_dir")
    ap.add_argument("--deck-dir", default=str(DEFAULT_DECK_DIR))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", default=None)
    ap.add_argument("--events", action="store_true", help="個別イベントを全て印字")
    a = ap.parse_args()
    eps_dir = Path(a.eps_dir).resolve()
    files = sorted(eps_dir.glob("ep*.json"))
    if a.limit:
        files = files[: a.limit]
    if not files:
        sys.exit(f"リプレイが無い: {eps_dir}")
    scratch = Path(tempfile.mkdtemp(prefix="bosslogic_autopsy_"))
    (scratch / "runner.py").write_text(RUNNER)
    (scratch / "files.txt").write_text("\n".join(str(f) for f in files))
    out_path = scratch / "out.jsonl"
    env = dict(os.environ, V2_NO_SEARCH="1")
    r = subprocess.run([sys.executable, str(scratch / "runner.py"), str(scratch / "files.txt"), str(out_path)],
                       cwd=a.deck_dir, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("runner failed:\n" + r.stderr[-2000:])
    games = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
    tot = Counter()
    events = []
    errs = [g for g in games if "error" in g]
    for g in games:
        if "error" in g:
            continue
        tot["games"] += 1
        st = (g.get("statuses") or [None, None])[g["mine"]]
        if st != "DONE":
            tot["crash_games"] += 1
            events.append((g["file"], -1, "P0_STATUS_" + str(st), None))
        rw = (g.get("rewards") or [None, None])[g["mine"]]
        tot["W" if rw == 1 else ("L" if rw == -1 else "D")] += 1
        for k, v in g["counts"].items():
            tot[k] += v
        for si, kind, det in g["events"]:
            events.append((g["file"], si, kind, det))
    print(f"eps={eps_dir.name} deck={Path(a.deck_dir).name} games={tot['games']} (load errors {len(errs)})  "
          f"W{tot['W']} L{tot['L']} D{tot['D']}  decisions={tot['decisions']} main={tot['main']} "
          f"seat_mismatch={tot['seat_mismatch']} parse_fail={tot['parse_fail']}")
    print(f"{'probe':18s} {'pred':>6s} {'k/n':>12s}  verdict")
    verdicts = {}
    for name, pred, kk, nn, cond in PRED:
        k, n = tot[kk], tot[nn]
        ok = eval(cond, {}, {"k": k, "n": n}) if n > 0 else None
        v = "PASS" if ok else ("n/a (分母0)" if ok is None else "FAIL")
        verdicts[name] = {"pred": pred, "k": k, "n": n, "verdict": v}
        print(f"{name:18s} {pred:>6s} {k:>5d}/{n:<6d}  {v}")
    extra = {k: tot[k] for k in sorted(tot) if k.startswith(("P1_cat", "P1_ko", "P1e", "P2_", "P2e", "P4_", "P3_"))}
    print("内訳:", json.dumps(extra, ensure_ascii=False))
    kinds = Counter(e[2] for e in events)
    print("イベント種別:", dict(kinds))
    if a.events:
        for e in events:
            print("  ", e)
    else:
        for e in events[:25]:
            print("  ", e)
        if len(events) > 25:
            print(f"   ... (+{len(events) - 25})")
    out = a.json or str(REPO / "replay_analysis" / f"{eps_dir.name}_autopsy.json")
    Path(out).write_text(json.dumps({"eps_dir": str(eps_dir), "deck_dir": a.deck_dir, "totals": dict(tot),
                                     "verdicts": verdicts, "events": events, "n_files": len(files),
                                     "load_errors": [g["file"] for g in errs]}, ensure_ascii=False, indent=1))
    print("saved", out)


if __name__ == "__main__":
    main()

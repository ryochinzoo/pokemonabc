#!/usr/bin/env python3
"""サイドレース収支の全数集計(測定専用・main.py は一切変更しない)。

方法(ログ再送問題への免疫):
  observation.logs は使わない。各 step の ACTIVE エントリの observation.current
  だけを時系列に採り、players[i].prize の長さの減少 = サイド取得として数える。
  状態は再送されても「同一値の連続」になるだけで、差分カウントは汚染されない。
  (turn, 取得側) でまとめて1「KOターン」とし、倒された側のポケモンは
  ターン頭の盤面(serial集合)と次ターン頭の盤面の差分で同定する。

既知の観測限界(2026-07-31 実測で確認):
  1) セットアップ前の状態は prize=(0,0)。(0,0)→(6,6) は増加でなく初期化。
  2) **勝敗を決める最後のKOは observation に現れない**(以後の決定点が無いため)。
     最終KOは「勝者の残りサイド枚数 R」から補完する(taker=勝者, k=R)。
     補完分は capped(サイド価値>Rでも R しか取れない)なので、
     「exが何枚か」の規則表には**可視イベントのみ**を使う。
  3) RESULT(23) ログはこれらのリプレイに存在しない(全ステップ走査で0件)。
     敗因は「敗者の山札残0 → 山札切れ / それ以外 → KO決着」で推定する。

事前固定の判定基準(2026-07-31、実行前に固定):
  サイド起因の敗北(相手が6枚に到達)のうち、相手の要したKOターン数の中央値が
  3以下なら「サイドレースの形は行動選択でなくデッキ構成の性質」ラベルを立てる。
  ※誠実性の注記: §6.3の集計値(相手2.17枚/KO)から中央値≦3はほぼ確実に予見される。
  本測定の新情報は敗北ごとの分布と機構の詳細であり、基準は準事前登録に留まる。

使い方:
  cd src/input/datasets/decks/starmie-aggro && \
  python3 ../../../../../replay_analysis/prize_race.py

出力: docs/memo/prize-race.md
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src/input/datasets/decks/starmie-aggro"))
from cg.api import all_card_data  # noqa: E402

CARDS = {c.cardId: c for c in all_card_data()}
OUR = "Yser"
OUT = ROOT / "docs/memo/prize-race.md"
REASON = {1: "サイド0", 2: "山札0", 3: "バトル場空", 4: "カード効果"}


def klass(cid):
    c = CARDS.get(cid)
    if not c:
        return "?"
    if getattr(c, "megaEx", False):
        return "megaEx"
    if getattr(c, "ex", False):
        return "ex"
    return "nonex"


def cname(cid):
    c = CARDS.get(cid)
    return c.name if c else str(cid)


def board_of(ps, pi):
    b = {}
    for zone in ("active", "bench"):
        for pk in ps[pi].get(zone) or []:
            if pk and pk.get("serial") is not None:
                b[pk["serial"]] = pk.get("id")
    return b


def analyze(rep, me):
    states = []
    for step in rep["steps"]:
        for e in step:
            if e.get("status") == "ACTIVE":
                c = (e.get("observation") or {}).get("current")
                if c:
                    states.append(c)
                break
    if not states:
        return None
    turn_first, turn_order = {}, []
    drops = []  # (turn, taker_pi, k)
    prev = None
    setup_done = False
    anomalies = Counter()
    for cur in states:
        ps = cur.get("players") or []
        if len(ps) < 2:
            continue
        pz = (len(ps[0].get("prize") or []), len(ps[1].get("prize") or []))
        t = cur.get("turn") or 0
        if t not in turn_first:
            turn_first[t] = [board_of(ps, 0), board_of(ps, 1)]
            turn_order.append(t)
        if not setup_done:
            # セットアップ: サイドは片方ずつ置かれ (0,0)→(0,6)→(6,6) 等と増える。
            # 両者6枚が見えるまでは差分を取らない。
            if pz == (6, 6):
                setup_done = True
            prev = pz
        elif pz[0] > prev[0] or pz[1] > prev[1]:
            # 陳腐化した視点(相手視点との到着順ずれで古い状態が後から来る)。
            # 読み飛ばし、prevは進めない(進めると同じ取得を二重計上する)。
            anomalies["陳腐state読み飛ばし"] += 1
        else:
            for pi in (0, 1):
                d = prev[pi] - pz[pi]
                if d > 0:
                    drops.append((t, pi, d))
            prev = pz
    last = states[-1]
    ps = last.get("players") or []
    final_boards = [board_of(ps, 0), board_of(ps, 1)] if len(ps) == 2 else None

    merged = {}
    for t, pi, k in drops:
        merged[(t, pi)] = merged.get((t, pi), 0) + k
    kos = []
    for (t, pi), k in sorted(merged.items()):
        victim = 1 - pi
        b0 = turn_first.get(t, [None, None])[victim]
        nxt = [u for u in turn_order if u > t]
        b1 = (turn_first[nxt[0]][victim] if nxt
              else (final_boards[victim] if final_boards else None))
        gone = []
        if b0 is not None and b1 is not None:
            gone = [(klass(cid), cname(cid)) for s, cid in b0.items() if s not in b1]
        kos.append(dict(turn=t, taker=("us" if pi == me else "them"), k=k, gone=gone))

    res = last.get("result", -1)
    if res not in (0, 1):
        rw = rep.get("rewards") or []
        if len(rw) == 2 and rw[0] is not None and rw[1] is not None:
            res = 0 if rw[0] > rw[1] else (1 if rw[1] > rw[0] else -1)
    if res not in (0, 1):
        return dict(win=False, unknown=True, us=0, them=0, kos=[],
                    ending="不明", final_ko=None, anomalies=anomalies)

    winner, loser = res, 1 - res
    try:
        loser_deck = ps[loser].get("deckCount")
    except (IndexError, AttributeError):
        loser_deck = None
    r_win = len(ps[winner].get("prize") or []) if len(ps) == 2 else None
    loser_board_n = len(final_boards[loser]) if final_boards else None

    final_ko = None
    if loser_deck == 0:
        ending = "山札切れ"
    else:
        ending = "KO決着"
        # 最終KOの犠牲者: 最終ターン頭の敗者盤面と最終盤面の差分(serial)。
        # 最終状態は敗者の昇格要求(取得前)なので active は空になっている。
        victim = None
        if turn_order and final_boards:
            t_last = turn_order[-1]
            b0 = turn_first.get(t_last, [None, None])[loser]
            if b0 is not None:
                g = [(klass(cid), cname(cid)) for s, cid in b0.items()
                     if s not in final_boards[loser]]
                if len(g) == 1:
                    victim = g[0]
                elif g:
                    victim = ("複数", "+".join(x[1] for x in g))
        if r_win and r_win > 0:
            final_ko = dict(taker=("us" if winner == me else "them"), k=r_win,
                            victim=victim, capped=True)
    us = sum(m["k"] for m in kos if m["taker"] == "us")
    them = sum(m["k"] for m in kos if m["taker"] == "them")
    if final_ko:
        if final_ko["taker"] == "us":
            us += final_ko["k"]
        else:
            them += final_ko["k"]
    return dict(win=(res == me), unknown=False, us=us, them=them, kos=kos,
                ending=ending, final_ko=final_ko, loser_deck=loser_deck,
                loser_board_n=loser_board_n, anomalies=anomalies)


def main():
    games = []
    for d in ["eps55058443", "eps55060473"]:
        for f in sorted((ROOT / "replay_analysis" / d).glob("*.json")):
            try:
                rep = json.loads(f.read_text())
            except Exception:
                continue
            nm = (rep.get("info") or {}).get("TeamNames") or []
            if OUR not in nm:
                continue
            g = analyze(rep, nm.index(OUR))
            if g:
                g["ep"] = f.stem
                games.append(g)

    n = len(games)
    wins = sum(1 for g in games if g["win"] and not g["unknown"])
    losses = [g for g in games if not g["win"] and not g["unknown"]]
    unknown = sum(1 for g in games if g["unknown"])
    anom = Counter()
    for g in games:
        anom.update(g["anomalies"])

    size = {"us": Counter(), "them": Counter()}  # 可視イベントのみ
    single = Counter()  # (taker, class, k) -> n  (goneが1体の可視KOターンのみ)
    ex_names = Counter()
    for g in games:
        for m in g["kos"]:
            size[m["taker"]][m["k"]] += 1
            if len(m["gone"]) == 1:
                kl, nm_ = m["gone"][0]
                single[(m["taker"], kl, m["k"])] += 1
                if kl == "ex":
                    ex_names[(nm_, m["k"])] += 1

    us_total = sum(g["us"] for g in games)      # 最終KO補完込み
    them_total = sum(g["them"] for g in games)
    us_events = sum(size["us"].values())
    them_events = sum(size["them"].values())

    def them_K(g):
        k = len([m for m in g["kos"] if m["taker"] == "them"])
        if g.get("final_ko") and g["final_ko"]["taker"] == "them":
            k += 1
        return k

    def us_K(g):
        k = len([m for m in g["kos"] if m["taker"] == "us"])
        if g.get("final_ko") and g["final_ko"]["taker"] == "us":
            k += 1
        return k

    ko_losses = [g for g in losses if g["ending"] == "KO決着"]
    deck_losses = [g for g in losses if g["ending"] == "山札切れ"]
    Ks = sorted(them_K(g) for g in ko_losses)
    medK = Ks[len(Ks) // 2] if Ks else None
    fire = medK is not None and medK <= 3
    ko_wins = [g for g in games if g["win"] and g["ending"] == "KO決着"]
    Kw = sorted(us_K(g) for g in ko_wins)
    medKw = Kw[len(Kw) // 2] if Kw else None

    L = []
    A = L.append
    A("# サイドレース収支(実リプレイ全数・状態遷移ベース)\n")
    A("> 測定専用。`main.py` 不変。ログ(observation.logs)不使用=再送問題に免疫。")
    A("> 再実行: `cd src/input/datasets/decks/starmie-aggro && "
      "python3 ../../../../../replay_analysis/prize_race.py`\n")
    A(f"- 対象 {n} 戦(勝 {wins} / 負 {len(losses)} / 不明 {unknown})、"
      f"状態異常検知 {dict(anom) or 'なし'}")
    A(f"- 総取得(最終KO補完込み): 我々 {us_total} 枚({us_total/n:.2f}/戦) / "
      f"相手 {them_total} 枚({them_total/n:.2f}/戦)")
    A(f"- 可視KOターン: 我々 {us_events} / 相手 {them_events} "
      f"(可視分の平均 {sum(k*v for k,v in size['us'].items())/max(1,us_events):.2f} / "
      f"{sum(k*v for k,v in size['them'].items())/max(1,them_events):.2f} 枚/KO)\n")
    A("## KOターンの取得枚数分布(可視イベントのみ・最終KO除く)\n")
    A("| 取得側 | 1枚 | 2枚 | 3枚 | 4枚+ |")
    A("|---|---:|---:|---:|---:|")
    for t in ("us", "them"):
        c = size[t]
        A(f"| {'我々' if t=='us' else '相手'} | {c[1]} | {c[2]} | {c[3]} | "
          f"{sum(v for k, v in c.items() if k >= 4)} |")
    A("\n## 倒された側が1体だけの可視KOターン(サイド枚数の規則の実測)\n")
    A("| 取得側 | 倒された種別 | 枚数 | n |")
    A("|---|---|---:|---:|")
    for (t, kl, k), v in sorted(single.items()):
        A(f"| {'我々' if t=='us' else '相手'} | {kl} | {k} | {v} |")
    A("\n通常ex の内訳(単体可視KOのみ): " +
      (", ".join(f"{nm_}={k}枚×{v}" for (nm_, k), v in sorted(ex_names.items()))
       or "観測なし"))
    A("\n## 勝敗の終局分類(推定規則は冒頭の注記3)\n")
    A(f"- 敗北 {len(losses)} = KO決着 **{len(ko_losses)}** + 山札切れ {len(deck_losses)}")
    A(f"- 勝利 {wins} = KO決着 {len(ko_wins)} + 山札切れ勝ち {wins - len(ko_wins)}")
    if Kw:
        A(f"- (参考)KO決着の勝利で我々が要したKOターン数: {Counter(Kw).most_common()} / "
          f"中央値 {medKw}")
    A("\n## 相手が勝ち切るのに要したKOターン数(KO決着の敗北・最終KO補完込み)\n")
    if Ks:
        A(f"- 分布: {Counter(Ks).most_common()} / **中央値 {medK}**")
    A(f"\n**事前固定基準(KO決着敗北の中央値≦3)の判定: {'発火' if fire else '非発火'}**\n")
    A("## 点差 — 僅差の積み上げか、構造の差か\n")
    lm = Counter(6 - g["us"] for g in losses)
    wm = Counter(6 - g["them"] for g in ko_wins)
    A("| あと何枚だったか | " + " | ".join(str(k) for k in range(0, 7)) + " |")
    A("|---|" + "---:|" * 7)
    A("| 敗北30戦(我々の残り必要枚数) | "
      + " | ".join(str(lm.get(k, 0)) for k in range(0, 7)) + " |")
    A("| 勝利26戦(相手の残り必要枚数) | "
      + " | ".join(str(wm.get(k, 0)) for k in range(0, 7)) + " |")
    close = sum(v for k, v in lm.items() if k <= 2)
    blow = sum(v for k, v in lm.items() if k >= 5)
    A(f"\n敗北30戦のうち 残り1-2枚の僅差 = **{close}** / 残り5-6枚の一方的 = **{blow}** "
      f"/ 中間(3-4枚) = {len(losses)-close-blow}\n")
    A("## 敗北30戦の明細\n")
    A("| ep | 終局 | 我々取得 | 相手取得 | 相手KOターン(補完込) | 相手の可視KOサイズ+最終 | 敗者山残 |")
    A("|---|---|---:|---:|---:|---|---:|")
    for g in losses:
        tk = [m for m in g["kos"] if m["taker"] == "them"]
        sizes = "+".join(str(m["k"]) for m in tk)
        if g.get("final_ko") and g["final_ko"]["taker"] == "them":
            v = g["final_ko"].get("victim")
            sizes += f"+[{g['final_ko']['k']}:{v[1] if v else '?'}]"
        A(f"| {g['ep']} | {g['ending']} | {g['us']} | {g['them']} | {them_K(g)} | "
          f"{sizes} | {g.get('loser_deck')} |")
    out = "\n".join(L) + "\n"
    OUT.write_text(out)
    print(out)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()

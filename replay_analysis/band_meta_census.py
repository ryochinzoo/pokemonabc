#!/usr/bin/env python3
"""帯別メタセンサス — レーティング付きの遭遇分布と対面行列。

**なぜ我々にしか作れないか**: SUMI(discussion/729926, 74,634戦)は公式日次データセットを
使ったため rating を持たない(本人が「ratings themselves are not in the replay JSONs」と明記)。
我々は ListEpisodes API 経由なので **全試合に相手の initialScore が付く**。
Oshbocker(37位)は「600-800はLucario/Abomasnowの群れ、800-1000はArchaludon、top100は別階層」
と証言しているが、**帯別の数字を出した人は公開範囲に存在しない**。

入力(いずれも取得済み・追加DLゼロ):
  1. replay_analysis/eps<sub>/       — 我々自身の提出の全譜(276戦)
  2. replay_analysis/ladder_scout/sub<sid>/ — 上位12体の譜(510戦、_list.json 付き)

分類器は2系統を **相互検証** する:
  A. 我々の RULES(カード名ベース、probe_autopsy.py / t1_verdict.py から継承)
  B. SUMI の SIGS(カードIDベース、discussion/729926 で公開)
不一致は明示的に出す(片方の取りこぼしを黙って飲まないため — D59の教訓)。

使い方: python3 replay_analysis/band_meta_census.py
"""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERE = REPO / "replay_analysis"

# 我々の全提出(自チーム対戦の除外に使う)
OUR_SUBS = {55169074, 55163442, 55070495, 55060473, 55058443, 54961048, 54858780,
            54832323, 55032182, 55004671, 54943911, 54831270, 54830797, 54815282,
            54788435, 54727395, 54435972, 54146595}

# --- 分類器A: カード名ベース(既存実装から継承。順序依存・先勝ち) ---
RULES = [
    ("Lucario", ["Mega Lucario ex"]),
    ("Archaludon", ["Archaludon ex"]),
    ("Abomasnow", ["Mega Abomasnow ex"]),
    ("Wall(Crustle/GreatTusk)", ["Crustle"]),
    ("StarmieMirror", ["Mega Starmie ex"]),
    ("Alakazam", ["Alakazam"]),
    ("Grimmsnarl", ["Marnie's Grimmsnarl ex"]),
    ("Dragapult", ["Dragapult ex"]),
    ("TR Mewtwo", ["Team Rocket's Mewtwo ex"]),
    ("Kangaskhan", ["Mega Kangaskhan ex"]),
    ("Garchomp", ["Cynthia's Garchomp ex", "Garchomp ex"]),
]

# --- 分類器B: SUMI 公開の署名カードID(discussion/729926、2026-07-28) ---
SIGS = {
    "alakazam": {743, 245}, "archaludon": {190, 170, 840}, "grimmsnarl": {648},
    "starmie": {1031, 361}, "trevenant": {879}, "dragapult": {121},
    "crustle": {345, 533}, "bellibolt": {269}, "abomasnow": {723, 419},
    "lucario": {678}, "dudunsparce": {306, 997, 66},
    "garchomp": {380, 381}, "gardevoir": {747}, "tarountula": {400, 401},
}
# A のラベルを B の語彙に寄せる対応(相互検証用)
A2B = {
    "Lucario": "lucario", "Archaludon": "archaludon", "Abomasnow": "abomasnow",
    "Wall(Crustle/GreatTusk)": "crustle", "StarmieMirror": "starmie",
    "Alakazam": "alakazam", "Grimmsnarl": "grimmsnarl", "Dragapult": "dragapult",
    "Garchomp": "garchomp",
}


def load_names():
    out = {}
    with open(REPO / "verification/data/EN_Card_Data.csv") as f:
        for r in csv.DictReader(f):
            st = r["Stage (Pokémon)/Type (Energy and Trainer)"] or ""
            out[int(r["Card ID"])] = (r["Card Name"], "Pokémon" in st)
    return out


NAMES = load_names()


def classify_a(deck_ids):
    """カード名ベース(我々の既存規則)。"""
    lineup = set()
    for cid in deck_ids:
        nm, isp = NAMES.get(cid, ("?", False))
        if isp:
            lineup.add(nm)
    for lab, keys in RULES:
        if any(k in lineup for k in keys):
            return A2B.get(lab, lab)
    return None


def classify_b(deck_ids):
    """SUMI 公開の署名カードID。"""
    s = set(deck_ids)
    return next((a for a, sig in SIGS.items() if sig & s), None)


def top_pokemon(deck_ids):
    c = Counter()
    for cid in deck_ids:
        nm, isp = NAMES.get(cid, ("?", False))
        if isp:
            c[nm] += 1
    return c.most_common(1)[0][0] if c else "?"


def band(score):
    if score is None:
        return None
    return 100 * int(score // 100)


def wilson(k, n):
    if n == 0:
        return (0.0, 100.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


_DEC = json.JSONDecoder()


def decks_of_file(path, _probe=(1 << 21)):
    """**先頭2ステップだけ**を部分デコードして60枚デッキを取り出す。

    リプレイ1本が20MB超あるため全体を json.loads すると 13GB の解析になる
    (2026-08-03、実測で実行不能)。デッキは steps[1] にあり、勝敗・スコアは
    `_list.json`(ListEpisodes API)側にあるので、本体は先頭だけ読めばよい。
    probe_autopsy.py と同じ「steps[1] の action が60要素」という取り方は不変。
    """
    size = path.stat().st_size
    n = min(_probe, size)
    while True:
        with open(path, "r") as f:
            s = f.read(n)
        try:
            i = s.index('"steps"')
            i = s.index("[", i) + 1
            # raw_decode は先頭の空白を飛ばさないので自前で送る
            while s[i] in " \t\r\n":
                i += 1
            step0, j = _DEC.raw_decode(s, i)          # steps[0]
            j = s.index(",", j) + 1
            while s[j] in " \t\r\n":
                j += 1
            step1, _ = _DEC.raw_decode(s, j)          # steps[1] = デッキ提出
        except (ValueError, IndexError):
            if n >= size:
                return None
            n = min(n * 4, size)                      # 足りなければ広げて再試行
            continue
        out = []
        for a in step1:
            act = a.get("action")
            if isinstance(act, list) and len(act) == 60:
                out.append(act)
        return out if len(out) == 2 else None


def collect():
    """(episode_id, sideA, sideB) を集める。side = dict(sub, score, deck, reward)

    一次ソースは `ladder_scout/decks.jsonl`(ladder_scout.py が作る抽出済み台帳)。
    生リプレイは1本20MB超で保存しない方針に変えたため、そこに無いものだけ
    ディスク上の生ファイルから拾う。
    """
    games = {}          # ep_id -> record(重複排除)
    store = HERE / "ladder_scout/decks.jsonl"
    if store.exists():
        for line in store.open():
            try:
                r = json.loads(line)
            except Exception:
                continue
            games[r["ep"]] = [dict(sub=s["sub"], score=s["sc"], reward=s["rw"],
                                   deck=s["d"]) for s in r["s"]]
    # --- 1. ladder_scout(_list.json に submissionId とスコアが入っている) ---
    for listf in sorted((HERE / "ladder_scout").glob("sub*/_list.json")):
        data = json.loads(listf.read_text())
        meta = {}
        for e in data.get("episodes", []):
            ags = e.get("agents", [])
            if len(ags) != 2:
                continue
            meta[e["id"]] = ags
        for f in sorted(listf.parent.glob("ep*.json")):
            ep = int(f.stem[2:])
            if ep in games or ep not in meta:
                continue
            dk = decks_of_file(f)
            if not dk:
                continue
            ags = meta[ep]
            # replay の step1 の並びと agents の並びは同一(Kaggle の仕様)
            sides = []
            for i, a in enumerate(ags):
                sides.append(dict(sub=a.get("submissionId"),
                                  score=a.get("initialScore") or a.get("updatedScore"),
                                  deck=dk[i], reward=a.get("reward")))
            games[ep] = sides
    # --- 2. 我々自身の譜(_list.json が無いので API 由来の対応表を作る) ---
    for epsdir in sorted(HERE.glob("eps*")):
        lf = epsdir / "_list.json"
        meta = {}
        if lf.exists():
            for e in json.loads(lf.read_text()).get("episodes", []):
                if len(e.get("agents", [])) == 2:
                    meta[e["id"]] = e["agents"]
        for f in sorted(epsdir.glob("ep*.json")):
            ep = int(f.stem[2:])
            if ep in games or ep not in meta:
                continue                  # _list.json に無い = 勝敗/スコア不明なので使わない
            dk = decks_of_file(f)
            if not dk:
                continue
            games[ep] = [dict(sub=a.get("submissionId"),
                              score=a.get("initialScore") or a.get("updatedScore"),
                              deck=dk[i], reward=a.get("reward"))
                         for i, a in enumerate(meta[ep])]
    return games


def main():
    games = collect()
    print(f"# 帯別メタセンサス — 総エピソード {len(games)}(重複排除済み)\n")

    # ---- 分類器の相互検証 ----
    agree = dis = only_a = only_b = neither = 0
    unknown_top = Counter()
    for sides in games.values():
        for s in sides:
            a, b = classify_a(s["deck"]), classify_b(s["deck"])
            s["arch"] = b or a          # B優先(公開・ID直接)、無ければA
            if a and b:
                agree += (a == b)
                dis += (a != b)
            elif a:
                only_a += 1
            elif b:
                only_b += 1
            else:
                neither += 1
                unknown_top[top_pokemon(s["deck"])] += 1
    tot = sum(len(v) for v in games.values())
    print("## 分類器の相互検証(名前ベース vs SUMI公開ID)")
    print(f"  両方が分類 {agree+dis}(一致 {agree} / **不一致 {dis}**) / "
          f"Aのみ {only_a} / Bのみ {only_b} / どちらも不能 {neither}  (全{tot}側)")
    if unknown_top:
        print("  未分類の最頻ポケモン: " +
              ", ".join(f"{k}×{v}" for k, v in unknown_top.most_common(8)))

    # ---- 帯別の遭遇分布(側単位) ----
    print("\n## 帯別アーキタイプ構成(側=エージェント出現数。**我々自身の提出は除外**)")
    print("   ※自分を数えると starmie が二重に乗る(我々の全譜が標本に入っているため)")
    per_band = defaultdict(Counter)
    band_n = Counter()
    for sides in games.values():
        for s in sides:
            bd = band(s["score"])
            if bd is None or s["sub"] in OUR_SUBS:
                continue
            per_band[bd][s["arch"] or "other"] += 1
            band_n[bd] += 1
    for bd in sorted(per_band):
        if band_n[bd] < 15:
            continue
        top = per_band[bd].most_common(8)
        print(f"\n  [{bd}-{bd+99}] n={band_n[bd]}")
        for a, c in top:
            print(f"     {a:<14} {100*c/band_n[bd]:5.1f}%  ({c})")

    # ---- 対面行列(帯を跨がない試合のみ = 同帯対戦) ----
    # **distinct 提出数を必ず併記する**。2026-08-03、これを出さずに
    # 「1100+帯は crustle 60.8%」と読み違えた(実体は crustle 4チーム vs grimmsnarl 67チーム)。
    # 少数エージェントに乗ったセルは「デッキの勝率」ではなく「そのパイロットの勝率」
    # (台帳#11 / D9 の deck×pilot 非分離)。
    print("\n## 対面行列(行が列に勝った率。両者が同一100点帯の試合のみ)")
    mat = defaultdict(lambda: [0, 0, set(), set()])
    for sides in games.values():
        a, b = sides
        if a["score"] is None or b["score"] is None:
            continue
        if band(a["score"]) != band(b["score"]):
            continue
        aa, bb = a["arch"], b["arch"]
        if not aa or not bb or aa == bb:
            continue
        win = a if a["reward"] == 1 else (b if b["reward"] == 1 else None)
        if win is None:
            continue
        lose = b if win is a else a
        for key, i in (((win["arch"], lose["arch"]), 0), ((lose["arch"], win["arch"]), 1)):
            mat[key][i] += 1
            mat[key][2].add(win["sub"] if i == 0 else lose["sub"])
            mat[key][3].add(lose["sub"] if i == 0 else win["sub"])
    pairs = sorted(mat.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
    print(f"  {'行 vs 列':<30}{'W-L':>9}{'勝率':>8}{'95%CI':>15}"
          f"{'行の提出数':>10}{'列':>5}  判定")
    for (x, y), (w, l, sx, sy) in pairs[:26]:
        n = w + l
        if n < 20:
            continue
        lo, hi = wilson(w, n)
        thin = min(len(sx), len(sy))
        tag = "**少数パイロット**" if thin <= 12 else ("やや薄い" if thin <= 25 else "デッキ級")
        print(f"  {x+' vs '+y:<30}{f'{w}-{l}':>9}{100*w/n:7.1f}%  [{lo:5.1f},{hi:5.1f}]"
              f"{len(sx):>9}{len(sy):>5}  {tag}")

    # ---- 我々の対面別成績(帯つき) ----
    print("\n## 我々(starmie)の対面別成績 — 帯別")
    ours = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for sides in games.values():
        for i, s in enumerate(sides):
            if s["sub"] not in OUR_SUBS:
                continue
            o = sides[1 - i]
            if o["sub"] in OUR_SUBS:
                continue          # 自チーム対戦は除外
            bd = band(s["score"])
            if bd is None:
                continue
            cell = ours[bd][o["arch"] or "other"]
            cell[0 if s["reward"] == 1 else 1] += 1
    for bd in sorted(ours):
        rows = sorted(ours[bd].items(), key=lambda kv: -sum(kv[1]))
        n = sum(sum(v) for v in ours[bd].values())
        w = sum(v[0] for v in ours[bd].values())
        print(f"\n  [自スコア {bd}-{bd+99}] N={n} 総合 {100*w/max(1,n):.1f}%")
        for a, (ww, ll) in rows:
            if ww + ll < 3:
                continue
            lo, hi = wilson(ww, ww + ll)
            print(f"     vs {a:<14} {ww}-{ll:<3} {100*ww/(ww+ll):5.1f}%  [{lo:5.1f},{hi:5.1f}]")


if __name__ == "__main__":
    main()

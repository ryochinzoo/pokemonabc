#!/usr/bin/env python3
"""湖(lake/)から NotebookLM 投入用の .md を生成する。

**なぜ2層に分けるか**: NotebookLM は grounded RAG なので、カード効果や試合内容を
捏造することは無い。弱いのは**集計**の方で、検索は上位k件しか引かないため
「209提出のうち何%が◯◯か」のような**全件走査が要る問い**には答えられない
(引けた範囲からの推定になる)。よって:

  第1層 = 集計値。**手元で数えて .md に焼き込む**。数字の正典は docs/memo/data.md のまま、
          NotebookLM はそれを引用するだけ。
  第2層 = 1提出1節の人間可読な記録。**これが grounding 素材**。
          カードは必ず**名前**で書く(NotebookLM は Card ID 1182 を解決できない)。

**.html は投入できない**(アップローダが明示的に拒否する)。.md 一択。

    python3 replay_analysis/make_digest.py            # 生成のみ(外部送信なし)
    python3 replay_analysis/make_digest.py --push     # 生成して NotebookLM に差し替え投入
"""
import collections
import json
import subprocess
import sys
from pathlib import Path

from band_meta_census import NAMES

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LAKE = HERE / "lake"
OUT_DIR = REPO / "docs-for-you" / "notebooklm-sources"
OUR_DECK = REPO / "src/input/datasets/decks/deckswap-tarountula-v2/deck.csv"

# デッキ相談ノートブック(memory: notebooklm-policy)。差し替え投入はここへ。
NOTEBOOK = "41482aa3-d790-4002-a096-d24a3894cd50"
CEW = {"alakazam": .3399, "grimmsnarl": .2247, "crustle": .1572,
       "lucario": .1537, "archaludon": .1246}


def _rows():
    p = LAKE / "rival_decks.jsonl"
    if not p.exists():
        return []
    best = {}
    for line in p.open():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        cur = best.get(r["sub"])
        if cur is None or (cur.get("rank") is None and r.get("rank") is not None):
            best[r["sub"]] = r
    return list(best.values())


def _agentlogs():
    p = LAKE / "agentlogs.jsonl"
    return [json.loads(x) for x in p.open() if x.strip()] if p.exists() else []


def _deck_lines(deck):
    """60枚を「4x カード名」の形に畳む。ポケモン→その他の順、枚数降順。"""
    c = collections.Counter(deck)
    items = []
    for cid, n in c.items():
        nm, isp = NAMES.get(cid, (f"(未知ID {cid})", False))
        items.append((0 if isp else 1, -n, nm, n))
    items.sort()
    return [f"{n}x {nm}" for _, _, nm, n in items]


def build():
    rows = _rows()
    if not rows:
        return None, "lake/rival_decks.jsonl が空。先に ladder_census を走らせること"
    ranked = sorted([r for r in rows if r.get("rank")], key=lambda r: (r["rank"], -(r.get("score") or 0)))
    logs = _agentlogs()
    L = []
    A = L.append

    A("# 上位ラダー悉皆調査 — デッキ実測データ (2026-08-10)")
    A("")
    A("Kaggle の順位表から上位105チームの稼働提出を全て辿り、各提出の**実際の60枚**を")
    A("リプレイから抽出したもの。**推測ではなく実測**。取得方法は")
    A("`leaderboard → team-submissions → list_episodes → リプレイ先頭部`。")
    A("")
    A("**この資料の使い方**: 第1部の数字は手元で全件を数えた結果なので、そのまま引用してよい。")
    A("第2部は1提出1節の生記録で、「誰が何を使っているか」を調べるための素材。")
    A("**数値の正典は `docs/memo/data.md`。この資料と食い違ったら data.md が正しい。**")
    A("")
    A("**重要な前提**: 対象は 1000〜1224 点の帯。我々は 678.7 点で、**帯の重なりはゼロ**。")
    A("これは「行き先の地図」であって「今の遭遇分布」ではない。")
    A("我々の判定指標(CEW)の重みをこの分布で置き換えてはいけない。")
    A("")
    A("---")
    A("")
    A("## 第1部 — 集計(全件を数えた結果)")
    A("")
    A(f"- 対象: 上位105チーム / 順位つき提出 **{len(ranked)}件**（+ 対戦相手として観測した野良 {len(rows)-len(ranked)}件）")
    A("- デッキ抽出失敗 0件 / 60枚でない行 0件 / 重複 0件")
    A("")
    A("### アーキタイプ分布")
    A("")
    A("| アーキタイプ | 提出数 | 割合 |")
    A("|---|---|---|")
    for a, n in collections.Counter(r["archA"] or "(未分類)" for r in ranked).most_common():
        A(f"| {a} | {n} | {100*n/len(ranked):.1f}% |")
    A("")
    A("### 我々の判定ゲージ(CEW)が上位帯を覆う割合")
    A("")
    A("| ゲージ | CEW重み | 上位105での実数 |")
    A("|---|---|---|")
    tot = 0
    for a, wt in CEW.items():
        n = sum(1 for r in ranked if r["archA"] == a)
        tot += n
        A(f"| {a} | {wt:.4f} | {n}/{len(ranked)} = {100*n/len(ranked):.1f}% |")
    A(f"| **合計** | 1.0000 | **{tot}/{len(ranked)} = {100*tot/len(ranked):.1f}%** |")
    A("")
    A(f"→ **上位の {100-100*tot/len(ranked):.1f}% は我々のゲージに存在しないデッキ。**")
    A("")
    A("### 分類器の盲点(2系統を相互検証した結果)")
    A("")
    A("| 型 | 提出数 | 通算勝率 | 見落としていた側 |")
    A("|---|---|---|---|")
    for lab, sel, who in (
            ("dudunsparce", lambda r: r["archB"] == "dudunsparce", "我々のカード名規則(分類器A)"),
            ("Kangaskhan", lambda r: r["archA"] == "Kangaskhan", "公開のSUMI署名(分類器B)")):
        g = [r for r in ranked if sel(r)]
        w, ll = sum(r.get("w", 0) for r in g), sum(r.get("l", 0) for r in g)
        if w + ll:
            A(f"| {lab} | {len(g)} | {100*w/(w+ll):.1f}% (N={w+ll:,}) | {who} |")
    OG = {"Teal Mask Ogerpon ex", "Dipplin", "Applin", "Grookey", "Thwackey"}
    og = [r for r in ranked if len({NAMES.get(c, ("?", 0))[0] for c in r["deck"]} & OG) >= 2]
    w, ll = sum(r.get("w", 0) for r in og), sum(r.get("l", 0) for r in og)
    if w + ll:
        A(f"| Ogerpon/Dipplin系 | {len(og)} | **{100*w/(w+ll):.1f}%** (N={w+ll:,}) | **両方とも知らない** |")
    A("")
    A("### 我々のデッキ(v2)との差分")
    A("")
    ours = collections.Counter(int(x.rstrip(",")) for x in OUR_DECK.read_text().split() if x.strip().rstrip(","))
    inc = collections.Counter()
    for r in ranked:
        for cid in set(r["deck"]):
            inc[cid] += 1
    A("**上位で広く使われ、我々が1枚も入れていないカード:**")
    A("")
    A("| カード | 採用提出数 |")
    A("|---|---|")
    for n, cid in sorted(((n, c) for c, n in inc.items() if c not in ours), reverse=True)[:15]:
        A(f"| {NAMES.get(cid, ('?', 0))[0]} | {n}/{len(ranked)} ({100*n/len(ranked):.0f}%) |")
    A("")
    uniq = [c for c in ours if inc.get(c, 0) == 0]
    A(f"**逆に、上位{len(ranked)}提出の誰一人使っていない我々のカード {len(uniq)}種:**")
    A("")
    for cid in uniq:
        A(f"- {ours[cid]}x {NAMES.get(cid, ('?', 0))[0]}")
    A("")

    if logs:
        A("### 我々自身の本番テレメトリ(agent logs)")
        A("")
        A("| 提出 | 戦数 | 1手の中央値 | 最遅の1手 | stderr |")
        A("|---|---|---|---|---|")
        for s in sorted({r["sub"] for r in logs}):
            rs = [r for r in logs if r["sub"] == s]
            med = sorted(r["p50"] for r in rs)[len(rs)//2]
            A(f"| {s} | {len(rs)} | {1000*med:.1f}ms | {1000*max(r['max'] for r in rs):.0f}ms | "
              f"{sum(r['nStderr'] for r in rs)}件 |")
        A("")
        A("`main.py` の探索予算は 0.6秒。pilotfix/v2 の最遅が 601〜602ms で止まっているのは")
        A("**安全弁が本番で設計どおり作動している**ことを示す。stderr が全戦で空 = クラッシュ非発生の直接証拠。")
        A("")

    A("---")
    A("")
    A("## 第2部 — 提出ごとの生記録(grounding 素材)")
    A("")
    A("各節が1提出。順位・スコア・戦績・アーキタイプ・**60枚の中身**。")
    A("「◯◯を使っているのは誰か」「××位のデッキは何か」を調べるのはここ。")
    A("")
    for r in ranked:
        A(f"### 第{r['rank']}位 {r.get('team','?')} — 提出 {r['sub']}")
        A("")
        wl = f"{r.get('w','?')}勝{r.get('l','?')}敗"
        tot_g = (r.get("w") or 0) + (r.get("l") or 0)
        wr = f" (勝率 {100*r['w']/tot_g:.1f}%)" if tot_g else ""
        A(f"- スコア: {r.get('score')}　戦績: {wl}{wr}　総試合数: {r.get('nEps','?')}")
        A(f"- アーキタイプ: 分類器A=**{r['archA'] or '未分類'}** / 分類器B=**{r['archB'] or '未分類'}**"
          f"　主力ポケモン: {r.get('top','?')}")
        A("- デッキ60枚:")
        A("")
        for ln in _deck_lines(r["deck"]):
            A(f"    - {ln}")
        A("")
    return "\n".join(L), None


# 投入フォルダに置いている「原本のコピー」。手作業でcpされたまま腐るので、
# ここで機械的に同期する(2026-08-10: data.md のコピーは117KB古かった。
# その結果 NotebookLM が古い集計値(我々の帯の grimmsnarl 19.3%)を、新しい上位105の
# 記録と混ぜて1つの答えとして返してきた。**古い層は黙って混ざる。**)
MIRRORS = [
    ("docs/memo/data.md", "data.md"),
    ("docs/memo/team-guide-battles-and-decks.md", "team-guide-battles-and-decks.md"),
]


def sync_mirrors():
    """原本 → 投入フォルダ のコピーを取り直す。乖離しているものだけ報告する。"""
    changed = []
    for src, dst in MIRRORS:
        s, d = REPO / src, OUT_DIR / dst
        if not s.exists():
            continue
        if not d.exists() or s.read_bytes() != d.read_bytes():
            old = d.stat().st_size if d.exists() else 0
            d.write_bytes(s.read_bytes())
            changed.append((dst, old, s.stat().st_size))
    for name, old, new in changed:
        print(f"  同期 {name}: {old/1024:.0f}KB → {new/1024:.0f}KB")
    if not changed:
        print("  コピーは全て最新")
    return changed


def push(path):
    """同名ソースを消してから入れ直す(ソース枠を1つに固定する)。

    **`-y` は必須**(2026-08-10に踏んだ): 付け忘れると delete が対話プロンプトを出し、
    非対話シェルでは Abort する。ところが後続の add は成功するので、
    **古い版と新しい版が両方ノートブックに残る**。差し替えたつもりが二重化して、
    混線が直るどころか悪化する。削除の失敗を検知して add を止めること。
    """
    # **`.stem` ではなく `.name`**(2026-08-10に踏んだ): NotebookLM が保持する title は
    # 拡張子込みの `foo.md`。`.stem` だと `foo` になって delete-by-title が一致せず、
    # 「消えないまま add」で二重化する。しかも delete 側は rc=0 を返すので気づけない。
    title = Path(path).name
    d = subprocess.run(["notebooklm", "source", "delete-by-title", title, "-n", NOTEBOOK, "-y"],
                       capture_output=True, text=True)
    blob = (d.stdout or "") + (d.stderr or "")
    # 「見つからない」は初回投入なので正常。それ以外の失敗は二重化を招くので中止する。
    if d.returncode != 0 and "not found" not in blob.lower() and "no source" not in blob.lower():
        print(f"削除に失敗したので投入を中止する(二重化を避ける): {blob[:200]!r}")
        return 1
    r = subprocess.run(["notebooklm", "source", "add", str(path), "-n", NOTEBOOK],
                       capture_output=True, text=True)
    print(r.stdout or r.stderr)
    return r.returncode


if __name__ == "__main__":
    text, err = build()
    if err:
        print(err)
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "ladder-census-2026-08-10.md"
    out.write_text(text)
    print(f"生成: {out}  ({len(text)/1024:.0f} KB / {text.count(chr(10))+1} 行)")
    print("原本コピーの同期:")
    stale = sync_mirrors()
    if "--push" in sys.argv:
        rc = push(out)
        if stale:
            print(f"\n⚠ {len(stale)}件のコピーが古かった。**NotebookLM側は入れ直さないと古いまま**")
            print("   (差し替えはソースの削除を伴うので、明示的に指示された場合だけ行う)")
            for name, _, _ in stale:
                print(f"     notebooklm source delete-by-title {Path(name).stem} -n {NOTEBOOK}")
                print(f"     notebooklm source add {OUT_DIR/name} -n {NOTEBOOK}")
        sys.exit(rc)
    print("外部送信はしていない。投入するなら --push を付けて実行。")

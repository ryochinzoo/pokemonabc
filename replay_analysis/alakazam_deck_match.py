#!/usr/bin/env python3
"""全候補Alakazamデッキ × 実ラダー遭遇デッキ の悉皆一致表 (2026-08-02、data.md同日節の根拠)。

問い: 我々のAlakazamゲージが使う `decks/alakazam_v0.csv` は、実ラダーで当たる本物と
どれだけ一致しているか。公開ノートブックのデッキと比べてどうか。

方法: 全 eps*/ep*.json から Alakazam(cardId 743)入りの60枚リストを悉皆抽出し、
多重集合の一致枚数を遭遇回数で加重平均する。追加測定ゼロ(リプレイはDL済)。

結果(2026-08-02): meta_alakazam 55.5 / jazivxt 51.6 / ryotasueyoshi 50.8 / **alakazam_v0 24.7**。
→ デッキ抽出は我々が正確だったが、**ゲージはその正確なデッキを使っていなかった**。

使い方: python3 replay_analysis/alakazam_deck_match.py
※ 公開デッキCSVは scratchpad 側にあるため、再実行時は CAND のパスを実在する場所へ向けること。
"""
import csv, glob, json, os
from collections import Counter
REPO="/Users/yujiinoue/Documents/products/pokemonabc"
SCR=os.path.dirname(os.path.abspath(__file__))
def load(p): return Counter(int(l.strip()) for l in open(p) if l.strip().isdigit())

CAND = {
 "公開ryotasueyoshi(5位)": load(f"{SCR}/alakazam/deck.csv"),
 "公開jazivxt(rising-tide)": load(f"{SCR}/nb/a-better-hand-alakazam-rising-tide-v21/deck.csv"),
 "我々meta_alakazam(7/14)": load(f"{REPO}/verification/decks/meta_alakazam_2026-07-14.csv"),
 "我々alakazam_v0(ゲージ)": load(f"{REPO}/verification/decks/alakazam_v0.csv"),
}
def ov(a,b): return sum((a&b).values())

# 実ラダーの全Alakazamデッキ(遭遇回数つき)
real={}
for f in sorted(glob.glob(f"{REPO}/replay_analysis/eps*/ep*.json")):
    try: d=json.load(open(f))
    except Exception: continue
    if len(d.get("steps",[]))<2: continue
    for ag in d["steps"][1]:
        deck=ag.get("action") or []
        if len(deck)!=60: continue
        c=Counter(deck)
        if c[743]==0: continue
        sig=tuple(sorted(deck))
        r=real.setdefault(sig,{"n":0,"c":c}); r["n"]+=1
ranked=sorted(real.values(), key=lambda v:-v["n"])
tot=sum(v["n"] for v in ranked)
print(f"実ラダーAlakazam: {len(ranked)}種 / 延べ{tot}回\n")
hdr = f"{'実物':>6} {'遭遇':>4} " + " ".join(f"{k:>24s}" for k in CAND)
print(hdr); print("-"*len(hdr))
score={k:0 for k in CAND}
for i,v in enumerate(ranked):
    cells=[]
    for k,dk in CAND.items():
        o=ov(v["c"],dk); score[k]+=o*v["n"]
        cells.append(f"{o:>2d}/60{'  ★完全' if o==60 else '      '}")
    print(f"  #{i:<3d} {v['n']:>4d} " + " ".join(f"{c:>24s}" for c in cells))
print()
print("=== 遭遇回数で重み付けした平均一致枚数(60点満点) ===")
for k in CAND:
    print(f"  {k:26s}: {score[k]/tot:5.1f} / 60")

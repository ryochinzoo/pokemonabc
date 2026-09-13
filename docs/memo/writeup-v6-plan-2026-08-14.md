# writeup v6 改稿案(2026-08-14、D78決定の記事側実装。ゆうじレビュー待ち)

方針(D78): 提出物 = starmie-aqua で凍結 → 記事の乖離は §4(旧リスト記述)と §2(退却物語の不在)の
2箇所だけ。**±0語では入らない**ので、v5保留分の L-a/L-b 追加(+85語)を**取り下げ**、
その枠を退却物語に振り替えることを提案する(理由: 主砲級 > 補強級。台帳行は残るので後日復活可能)。
数値はすべて台帳 #32〜#36 経由(2026-08-14 追加済み)。

## 1. §2 末尾に挿入(+155語) — #27「マージン120」物語の完結編

> Seven months later the margin defect stopped being archaeology and became a live failure.
> A teammate spotted, in a ladder replay, the agent retreating a fully-powered attacker rather
> than attacking a Mega Lucario it could not one-shot. Fed that exact observation, our production
> pilots chose RETREAT 12 times out of 12; the greedy layer alone answered ATTACK, and the search
> overrode it — the prize term (±10,000 per card) outscales the override margin (120) by 250×,
> so the margin gates nothing. We repaired the decision, reproduced 12/12 ATTACK, and the
> repaired bundle measured **+6.03pt (95% CI [+4.77, +7.28], N=6,400, pre-registered)** [#32].
> Then our pre-registered falsification sensor fired: the matchup where the retreat pathology
> is most frequent got *worse* (−1.37pt) [#33]. The bundle is adopted; the mechanism story is
> withheld. Proving the defect did not entitle us to the credit.

## 2. §4 の修正(2箇所、±ほぼ0語)

(a) 冒頭1文を差し替え(「final list = 水単」への追随):
> Our final list is a mono-water Mega Starmie ex aggro build, twelve cards from its ancestor,
> every step forced by measurement rather than theory [#32].

(b) 3つの定石失敗の直後に追加(+58語) — **凍結直前の1枚差し実験**:
> The freeze test was the sharpest. With the pilot byte-identical, we swapped exactly one card:
> in for Boss's Orders — the most-adopted card (96%) among the top-100 teams we crawled. It
> measured **−1.53pt (CI [−2.76, −0.30])**; the next most natural swap (Poké Pad, 82% adoption)
> measured −1.58pt. The deck refused the field's consensus twice, one card at a time [#34].

## 3. §5 の更新(+約40語)

- 効果量トリオ → カルテットに: Deck 64.7% [#4] / Search layer +13.62 [#26] / Pilot rule +2.50
  [#5] / **Value-layer bundle +6.03 [#32]**(帰属保留の注記つき)。
- 頑健性の行を更新: 「CRASH=0 across 60 games」→ **「0 stderr in {N} production games across
  our two final submissions, worst decision 573ms」**({N}は凍結後の実測で埋める。8/14時点 83)。
- 方向一致 [#35] は書くなら1文・探索的ラベルで(「CEWとラダーが同方向 n=1」)。

## 4. 語数会計(上限2,000)

| 項目 | 語数 |
|---|---|
| v5本文 | 1,998 |
| 圧縮 C1(§3自己監査3段目) | −55 |
| 圧縮 C3(§6辞書修理) / C4(§6 v3) / C5(§2冒頭) | −60 |
| §3 Half-one + §1 の追加圧縮(v5保留分に既記載の予備) | −35 |
| §2 挿入(退却物語) | +155 |
| §4 (b) 1枚差し | +58 |
| §5 更新 | +40 |
| **着地見込み** | **≈1,981** |

- L-a/L-b(サイド経済+二峰性、+85語)は**今回見送り**(台帳行は生存、9月に余語があれば復活)。

## 5. ゆうじの判断が要る点(3つ)

1. L-a/L-b の見送りに同意するか(退却物語との交換)。
2. §2挿入の "A teammate spotted" — ゆうじの発見をこう書いてよいか(匿名の形)。
3. タイトル据え置きでよいか(現: Measure Before You Believe…。水単化でも背骨は不変なので**据え置きを推奨**)。

承認が出たら writeup-v1-fulldraft.md に v6 として反映し、T6(台帳突合)を機械的に回す。

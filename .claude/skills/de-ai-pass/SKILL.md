---
name: de-ai-pass
description: Strategy記事(writeup-v1-fulldraft.md)の文体パス。公開スキル humanizer の35パターンを使うが、数値・CI・N・主張#・図番号・カード名は一字も変えず、段落ごとに変更前後を並べて提示し、パス後に t6_check.py を再走する。
---

# de-ai-pass — 記事の「AIっぽさ」を取る、ただし数値は触らない

対象: `docs/memo/writeup-v1-fulldraft.md` の本文(`## Measure Before` 〜 `---\n---` の手前)。
前提: `~/.claude/skills/humanizer/SKILL.md`(MIT、Wikipedia "Signs of AI writing" 由来の35パターン)を先に読む。
そのパターン検出と書き換えの手順はそちらに従い、本スキルは**この記事固有の不変条件**を上書きで課す。

## 不変条件(違反したら差し戻し)

1. **数値・単位・CI・N・σ・%・pt・k/n・日付・提出ID・カードID は一字も変えない。** 丸めも禁止。
2. **台帳タグ `[#N]` と `Fig. N` の位置と番号を動かさない**(段落を分割・統合するときはタグを元の主張の直後に残す)。
3. **カード名・ポケモン名・技名は原文どおり**(英語公式名、大文字小文字も)。
4. **ラベル規律を壊さない**: `claims-ledger.md` で「探索的」「弱確証」の主張を断定形に書き換えない。
   逆に「確証」を不必要にぼかさない(hedging の除去は humanizer のパターン24、ただし台帳の留保は残す)。
5. **背骨A/B の弾を段落から落とさない**(方法論の数値と、ドメインの具体例)。
6. 語数は公開版で **≤1,960**(`python3 docs/memo/t6_check.py`)。増やさない方向で。

## この記事に実際に多い癖(v6 実測。優先して取る)

- 太字の多用(1段落に3つ以上) → 主張の核1つだけ残す
- em-dash の連鎖(— … — …)→ コンマ・ピリオド・コロンに戻す
- 三連(rule of three: "Mechanism true, occurrence zero; occurrence real, effect zero; effect real, legitimacy absent.")→ 内容が本当に3つある場合のみ残す。装飾の三連は2つか1文に
- "not X, it is Y" / "not X but Y" の逆並列の反復 → 段落に1回まで
- 段落末の格言("Proving the defect did not entitle us to the credit.")→ 記事全体で2〜3回まで。それ以外は事実文で終える
- "The X was the sharpest" 型の定型見出し → 具体で始める
- 文長の均質化 → 短文と長文を混ぜる(humanizer パターン11)

## 手順

1. 段落単位で処理する。各段落について **変更前 / 変更後 / 触った数値ゼロの確認** の3点を並べて提示する。
2. 全段落を通したら `python3 docs/memo/t6_check.py` を実行し、`UNMATCHED=0 UNCITED=0`、語数 ≤1,960 を確認して結果を貼る。
3. ゆうじ自筆の段落(§2 退却の発見 / §5 最終夜 / §5 ボスの価値序列)は**文体パスの対象外**。文法の最小修正のみ、それも提示して承認を取る。
4. 採否はゆうじ。承認された段落だけを本文に書き戻す。

---
name: kaggle-coach
description: Authoritative rulebook for the Pokémon TCG AI Battle Challenge on Kaggle — the two tracks, submission limits and scoring, the hard "never crash" requirement, deadlines, and the submission format. Background knowledge for any decision about strategy, submitting, or what the competition rewards.
user-invocable: false
---

# kaggle-coach

このプロジェクトが戦っている大会「The Pokémon Company × 松尾研 cabt：Pokémon TCG AI
Battle Challenge」のルール集。戦略・提出・「何が評価されるか」を判断するときの土台。
**確認済みの事実だけ**を上に、未確認は下にまとめる。未確認を事実として扱わない。

## 2部門（最重要）

- **Simulation部門**（賞金なし）: 提出AI同士の自動対戦ラダー。スキルはガウス分布の
  レーティングで、勝てば上がり負ければ下がる。**最終順位は「直近2提出」のみ**で決まる。
  提出は**1日5回まで**。
- **Strategy部門**（賞金あり）: **対戦成績＋技術レポート**で審査。レポートは構築した
  システム/戦略を「分析・説明・文書化」するもの。**上位8チーム各 $30,000**、その後
  東京決勝。→ 賞金狙いはレポートが勝負の半分。`.memo/`を原稿として`/strategy-report`で育てる。

## ハード要件（違反＝失格・無効試合の原因）

- エージェントは**絶対にクラッシュしてはならない**。常に**合法手**（提示された
  `obs.select.option` 内のインデックス）を返す。
- **手番ごとの制限時間**を守る。
- 初手の特殊ステップ（`obs.select is None`）では**60枚デッキ**（Card IDのlist）を返す。
- → この要件のチェックは `/submission-check` と `@robustness-guard` が担当。

## 提出フォーマット

- 提出物 = `main.py` + `deck.csv` + `cg/`（前回スコア413.4が通った構成）を `tar.gz` 化。
- `deck.csv` は Card ID をちょうど60枚、1行1つ。本番では `/kaggle_simulations/agent/`
  から読まれる（`main.py` がフォールバック実装済み）。
- サンドボックスは**標準ライブラリのみ**。第三者パッケージ不可（`requirements.txt`なし）。
- 初回提出には**本人確認（電話＋顔認証）**が必要（経験済み）。

## 日程（複数ソース一致。公式で最終確認推奨）

- Sim エントリー/チーム合併: 2026-08-09
- Sim 最終提出: 2026-08-16
- Strategy 最終提出: 2026-09-13
- Strategy 審査: 2026-09-14 〜 2026-10-11
- チームは最大5人。

## エンジンAPIの要点

- `agent(obs_dict) -> list[int]`。詳細は `/agent-api` スキルと `cg/api.py`。
- カード照会は `/lookup-card`。enumは大会中に増えうる＝網羅前提にしない。
- cabt公式ドキュメント: https://matsuoinstitute.github.io/cabt/

## 要確認（未確認の数字。Kaggle公式ルールで裏取りするまで事実扱いしない）

- 提出サイズ上限 **197.7 MiB**（?）
- 技術レポートの語数制限 **2000語以内**（?）
- 評価配分：手法の根拠/独自性が **約70%**（?）

→ ユーザーが公式ルールページの該当箇所を確認・共有したら、この節を「確認済み」に昇格する。

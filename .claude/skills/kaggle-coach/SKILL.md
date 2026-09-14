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
- **Strategy部門**（賞金あり）: 別コンペとして開催
  （https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy）。
  Kaggle **Writeup**（≤2000語、超過はペナルティ対象）＋任意のMedia Galleryで提出。
  **Simulation部門への参加が必須**。**Finalist 8チーム各 $30,000（計$240,000）**＋
  東京での招待対戦（TBD）。審査員はMI（松尾研）データサイエンティスト2名＋ポケモン社3名。

### Strategy審査基準（原文確認済み 2026-07-14）

| カテゴリ | 中身 | 配点 |
|---|---|---|
| **Model Score** | ①アプローチの明確な説明と根拠 ②独自性と技術的健全性 ③反復対戦での安定性 ④特定の初期状態・マッチアップ・状況的優位に依存しない頑健性 ⑤Simulation部門でのパフォーマンス | **70%** |
| **Deck Score** | デッキコンセプトの明確さと戦略との整合 / キーカードの選択・活用がゲームプランを支えているか | **20%** |
| **Report Score** | レポートの論理構成・明瞭さ / 図表の効果的な使用 | **10%** |

公式Overviewの明言: 「LB上位は performance scoring で有利になりうるが Strategy での
好成績を保証しない。**中位〜下位でも深い分析・独自性・構成の良いレポートで高得点可能**」。

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

## 日程（公式Timeline確認済み 2026-07-14）

- Sim エントリー/チーム合併: 2026-08-09
- Sim 最終提出: 2026-08-16（以後 〜8/31頃まで対戦継続、収束後にLB確定）
- Strategy エントリー/チーム合併: 2026-09-06
- Strategy 最終提出: 2026-09-13（JST 9/14 8:59まで）
- Strategy 審査: 2026-09-14 〜 2026-10-11
- チームは最大5人。

## ホスト裁定・公式発表（Discussion確認済み 2026-07-14）

- **マルチデッキ禁止**（discussion/711741、ホストshige回答）: 1提出=1デッキを一貫使用。
  試合ごとのデッキ切替は「意図されたセットアップではない」。**Strategy部門では
  マルチデッキ提出は肯定的に評価されない**と明言。Sim側の機械的な強制手段は検討中
  （2026-07-06時点で未発表）。→ 相手判定→デッキ切替戦略は却下。
- **エンジンソース公式公開**（discussion/717141、Kaggleスタッフ、〜2026-07-02）:
  Dataページの `ptcg_engine.zip`。ローカルテスト・検証・訓練用。**派生・改変・
  コンパイル済みコードを提出物に含めることは明示的に許可**（コンペ内利用に限る）。
  実装バグの悪用は禁止・発見したらフォーラムに報告。
  既知バグ報告: ToolCountProc の変数シャドウでクラッシュしうる / ビジュアライザ
  リプレイの selected が1手ずれるoff-by-one（**リプレイ学習・replay_analysis に影響**）。
- **レーティングの分散問題**（discussion/712621、68票、ホスト回答なし）: 同一エージェント
  2連投で 150〜400点以上の差が観測されている。序盤エピソードの結果がほぼ運命を決める。
  コミュニティの実務解: **最終版は同一エージェントを2枠とも提出**して高い方を引く。
  ローカル評価のほうが情報量が多い。

## 要確認 → 確認済みに昇格（2026-07-14、公式ページで裏取り完了）

- 提出サイズ上限 **197.7 MiB** ✅（Sim公式FAQ。HDD 11.8GiB / RAM 12.2GiB / 2vCPU）
- 技術レポート語数 **2000語以内** ✅（超過は「ペナルティの対象になりうる」）
- 「独自性70%」→ 正しくは **Model Score が70%**で、独自性はその中の1項目
  （上の審査基準表が原文）。

## エンジンAPIの要点

- `agent(obs_dict) -> list[int]`。詳細は `/agent-api` スキルと `cg/api.py`。
- カード照会は `/lookup-card`。enumは大会中に増えうる＝網羅前提にしない。
- cabt公式ドキュメント: https://matsuoinstitute.github.io/cabt/

（要確認節は 2026-07-14 に全項目裏取り完了し「確認済み」へ昇格済み。上記参照。）

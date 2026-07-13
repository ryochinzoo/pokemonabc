# verification — 提出前にローカルで強さを測る道具箱

エンジンは約7〜12ms/戦。**300戦がタダ**なのに、Kaggleの提出枠は1日5回しかない。
「本番でA/Bテスト」をやめて、ここで測ってから提出するための道具一式。

## 前提

各ツールは **デッキディレクトリ**（`main.py` + `deck.csv` + `cg/` が揃った場所、
例: `src/input/datasets/decks/mega-starmie-ex-deck/`）から実行する。
`cg/` のバイナリ（libcg.dylib 等）は gitignore なので、無い場合は
Kaggle の sample_submission からコピーすること。

## 使い方（デッキディレクトリで実行）

```bash
cd src/input/datasets/decks/mega-starmie-ex-deck

# 1) 対ランダム勝率（95%信頼区間つき）
python3 ../../../../../verification/bench.py 300

# 2) メタ再現ゲージ（上位型2種 + 実ラダー由来アグロ）
python3 ../../../../../verification/bench.py 300 \
  --opponent ../../../../../verification/gauges/alakazam_agent.py \
  --opponent-deck ../../../../../verification/decks/alakazam_v0.csv
python3 ../../../../../verification/bench.py 300 \
  --opponent ../../../../../verification/gauges/grimmsnarl_agent.py \
  --opponent-deck ../../../../../verification/decks/grimmsnarl_v0.csv
python3 ../../../../../verification/bench.py 300 \
  --opponent main.py \
  --opponent-deck ../../../../../verification/decks/lunasol_v0.csv

# 3) 早期敗北率（ドンク＝序盤即死の割合。実ラダーの負け8戦中5戦がこれだった）
python3 ../../../../../verification/donk_meter.py 400 deck.csv \
  main.py ../../../../../verification/decks/lunasol_v0.csv

# 4) 自陣デッキだけ差し替えて測る
python3 ../../../../../verification/bench.py 300 --deck ../../../../../verification/decks/starmie_v1.csv
```

## 提出前ゲート（チーム協定・案）

1. 対ランダム + 3ゲージすべてで現行提出版と同等以上
2. donk_meter の早期敗北率が悪化していない
3. CRASH=0（bench が exit 2 なら提出禁止）
4. デッキは**同名カード合計4枚以下**（エンジンは検査しない！5枚でも通ってしまう）
5. 最終順位は「直近2提出」＝**直近2枠は常にベスト2本**を維持する

## 中身

| パス | 何 |
|---|---|
| `selfplay.py` | 対戦ハーネス（席入替つき、`run_match`/`run_series`） |
| `bench.py` | 勝率+信頼区間。`--deck` `--opponent` `--opponent-deck` `--baseline` |
| `donk_meter.py` | 5ターン以内の早期敗北率 |
| `gauges/` | Alakazam型 / Grimmsnarl型の専用スクリプトAI |
| `decks/` | ゲージ用・実験用デッキ（lunasol_v0 = 実ラダーで2ターン負けした相手の完コピ） |
| `reference/steel_agent.py` | 公開コード「Pokemon steel」(Apache2.0, 820点)。**検証専用・提出禁止**（Strategy部門は独自性審査） |
| `data/` | カードDB（EN/JP CSV、replay_analysis からも参照） |

## 関連

- `../replay_analysis/` — Kaggle実対戦リプレイの取得・解析（負け方の一次情報）
  - リプレイJSON: `https://www.kaggle.com/competitions/episodes/{episodeId}/replay.json`（認証不要）
- `../docs/memo/` — 意思決定ログ・実測データ・引き継ぎ（Strategyレポートの素材）

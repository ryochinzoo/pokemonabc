---
name: bench
description: Measure how strong our agent is by running self-play games against a baseline and reporting win-rate with a 95% confidence interval. Use to check whether a change to main.py's agent() actually made it stronger, to get a before/after number on a heuristic change, or whenever asked how strong the agent is.
argument-hint: "[games] (default 200)"
allowed-tools: Bash(cd *) Bash(python3 *)
---

# bench

我々のエージェント（`main.py` の `agent()`）の強さを、自己対戦の**勝率**で測る。
「強くなった気がする」を**数字＋信頼区間**に変えるのがこのスキルの目的（= ベスト
プラクティス「Claudeに検証手段を与える」の実体）。

## 実行方法

必ず提出物ディレクトリから実行する（`import main / selfplay / cg` がそこでしか解決
しないため）。`$ARGUMENTS` は対戦数（省略時200）。

```
cd src/input/datasets/decks/mega-starmie-ex-deck && python3 "$(git rev-parse --show-toplevel)/verification/bench.py" $ARGUMENTS
```

引数なしのときは `200` で実行する。

## 結果の読み方

- **勝率と95%信頼区間** が主役。区間が広い（例 200戦で ±7%）なら、その差はノイズかも
  しれない。差を確実に言いたいときは対戦数を増やす（例 `/bench 500`）。
- `WINRATE=` / `CI_LOW=` の行は機械可読。
- 出力に `CRASH=1` が出たら、エージェントが落ちている＝**大会の「絶対に落ちない」要件
  に違反**。最優先で直す。`@robustness-guard` サブエージェントに原因究明を頼むとよい。

## 測れること・測れないこと

- 測れる: **判断ロジックの良し悪し**。両者まったく同じデッキ（`deck.csv`）で戦わせ、
  デッキ差を消して `agent()` の差だけを見る。
- デッキ込みの強さを測りたいときは `--opponent-deck` を使う（下記）。

## メタ再現モード（標準仮想敵）

LB上位で観測された Alakazam + Dudunsparce 型を、スクリプトAI＋専用デッキとして
提出物ディレクトリに常備してある（2026-07-07 に cabt 実機でキーカード挙動を検証済み）:

```
python3 "$(git rev-parse --show-toplevel)/verification/bench.py" 200 \
  --opponent alakazam_agent.py --opponent-deck decks/alakazam_v0.csv
```

第2ゲージ（Grimmsnarl型、2026-07-08 追加）:

```
python3 "$(git rev-parse --show-toplevel)/verification/bench.py" 200 \
  --opponent grimmsnarl_agent.py --opponent-deck decks/grimmsnarl_v0.csv
```

- ランダム相手の勝率が飽和したら、**2ゲージの平均を標準の強さ指標にする**。
  「環境上位アーキタイプに何%勝てるか」が Kaggle レーティングの代理変数。
  基準（v1+サンプルデッキ, 2026-07-08）: 対Alakazam 63.0% / 対Grimmsnarl 75.3%。
- 関連ファイル: `alakazam_agent.py` / `grimmsnarl_agent.py`（貪欲スクリプトAI）,
  `decks/*.csv`（60枚リスト）, `verify_alakazam.py`（挙動検証の再実行用）,
  `deck_tournament.py`（同一パイロットのデッキ総当たり）。
  いずれも**提出 tar.gz には含めない**こと。

## 補足

- 既定の相手はランダムAI（`selfplay.random_agent`）。現状の `main.py` もほぼランダム
  なので、初期は勝率〜50%が正常。
- 過去バージョンとの直接対決は `--opponent <path>.py` で可能。`/try-heuristic` が
  新旧比較に使う。

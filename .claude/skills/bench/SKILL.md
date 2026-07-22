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

**既定は現行の王者デッキ `starmie-aggro`**（D34で確定）。別のデッキを測るときは
呼び出し側がディレクトリを明示する。`decks/mega-starmie-ex-deck/` は**チームメイトの
デッキ**なので、ここを既定にしてはいけない（測定対象の取り違えは無言で通る）。

```
cd src/input/datasets/decks/starmie-aggro && python3 "$(git rev-parse --show-toplevel)/verification/bench.py" $ARGUMENTS
```

**どのデッキディレクトリで測ったかを必ず報告の1行目に書く。**

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

## ゲージと採否判定（D27/D29/D35 で改訂済み — ここが最重要）

**このスキルの生の勝率で採否を決めてはいけない。** 自前パイロットが相手デッキを操縦する
「族内ゲージ」（`verification/gauges/` の Alakazam型・Grimmsnarl型）は、相手操縦者との
実力差に比例して勝率を **+8〜+62pt 過大評価する**（D27で実測）。族内ゲージは
**スクリーニング用途のみ**。

**採否の主指標は CEW**（較正済み族外ゲージ4種の遭遇加重合成、基準線41.5%、
N=800/セル、閾値+2pt）。計算は `verification/cew.py`、手順は
`verification/README.md` の提出前ゲート。族外ゲージ（公式サンプル / tomato系譜）は
`verification/reference/` にあり、**検証専用・提出禁止**。

族内ゲージをスクリーニングで回すとき（パスは deck ディレクトリからの相対）:

```
python3 "$(git rev-parse --show-toplevel)/verification/bench.py" 200 \
  --opponent "$(git rev-parse --show-toplevel)/verification/gauges/alakazam_agent.py" \
  --opponent-deck "$(git rev-parse --show-toplevel)/verification/decks/alakazam_v0.csv"
```

`grimmsnarl_agent.py` / `grimmsnarl_v0.csv` も同様。いずれのゲージ資材も
**提出 tar.gz には含めない**こと。

## 補足

- 既定の相手はランダムAI（`selfplay.random_agent`）。これは**強さの指標ではなく
  正当性の検査**（提出前ゲート: vs random ≥96%）。現行の王者は95〜99%帯にいるので、
  ここが落ちていたら効果ではなく事故を疑う。
- 過去バージョンとの直接対決は `--opponent <path>.py` で可能。`/try-heuristic` が
  新旧比較に使う。

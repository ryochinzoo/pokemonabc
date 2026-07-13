---
name: try-heuristic
description: Try a change to the agent's decision logic and keep it only if self-play proves it stronger than the previous version. Use when improving main.py's agent(), testing a heuristic idea, or when asked to make the agent stronger. This is the explore -> implement -> verify -> record loop, in one command.
argument-hint: "[hypothesis, e.g. 'attack when it knocks out the active Pokémon']"
allowed-tools: Bash(cd *) Bash(python3 *) Bash(cp *) Bash(mkdir *) Bash(ruff *)
---

# try-heuristic

1つのヒューリスティック仮説を、**勝率で証明できたときだけ採用する**ワークフロー。
ベストプラクティス（検証手段を与える／小さく可逆な一歩／レポート素材を貯める）を
このプロジェクト用に1コマンドへ凝縮したもの。

仮説 = `$ARGUMENTS`。空なら、まず何を試したいか1行で確認してから進める。

作業ディレクトリは `src/input/datasets/decks/mega-starmie-ex-deck/`。各ステップは順に実行する。

## 手順（このとおりに実行する）

1. **仮説を1行で宣言する。** 「何を、なぜ、どの選択局面（SelectContext）で変えるか」。
   不明なら `@agent-api` スキルでAPIを確認してから。

2. **現行をスナップショット＝退行の基準にする。**
   ```
   mkdir -p .bench && cp main.py .bench/main_prev.py
   ```

3. **最小の変更を `main.py` の `agent()` に入れる。** 大きく作り替えない。enum を直接
   分岐するときは必ず未知値の fallback を用意（落ちたら即不採用）。保存後 `ruff format`
   は自動で走る。

4. **新旧の直接対決で検証する（決定論ゲート）。**
   ```
   python3 "$(git rev-parse --show-toplevel)/verification/bench.py" 300 --opponent .bench/main_prev.py --baseline 0.50
   ```
   - `CRASH=1` / 終了コード2 → **即・不採用**（大会の「絶対に落ちない」要件違反）。手順6へ。
   - `GATE=FAIL`（信頼区間の下限 < 0.50, 終了コード1）→ 退行の疑い。**不採用**。手順6へ。
   - `GATE=PASS` かつ `WINRATE > 0.50` → 統計的に勝ち越し。**採用**。手順5へ。
   - 判断に迷う僅差なら対戦数を 500〜1000 に増やして再測定する（信頼区間が狭まる）。

5. **採用した場合：記録する（レポート素材になる）。** `.memo/decisions.md` に追記:
   - 日付 / 仮説 / 変更点の要約 / 旧→新の勝率（信頼区間つき）/ 対戦数 / 採用理由。
   結果データ（数値）は `.memo/data.md` にも残す。これが後の技術レポート(`/strategy-report`)
   の根拠になる。

6. **不採用の場合：必ず元に戻す。**
   ```
   cp .bench/main_prev.py main.py
   ```
   そのうえで `.memo/journal.md` に「○○を試したが勝率↑せず（数値）→ 戻した」と1行残す
   （失敗の記録もレポートの「検討したが採らなかった案」として価値がある）。

7. **結果を証拠つきで報告する。** 「採用/不採用」「旧→新の勝率と信頼区間」「対戦数」を提示。
   主張ではなく数字で。

## ノート

- 同じデッキ同士の対決なので、ここで測っているのは**判断ロジックの改善**のみ。
- 連続で複数の仮説を試すときは、採用するたびに手順2のスナップショットを取り直す
  （`main_prev.py` が常に「直前の採用版」になるように）。
- 裏で並行実行したいときは、このスキルの前に `/fork` を付けて起動するか、起動側で
  バックグラウンド実行を指定する。常時バックグラウンド化したくなったらフロントマターに
  `context: fork` を足す（会話履歴を引き継ぐ点に注意）。

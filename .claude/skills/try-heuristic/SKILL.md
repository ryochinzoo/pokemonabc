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

作業ディレクトリは **`src/input/datasets/decks/starmie-aggro/`**（現行の王者デッキ、D34）。
別デッキを対象にするときは呼び出し側が明示すること。
**`decks/mega-starmie-ex-deck/` はりょーちん(ryochinzoo)のデッキなので絶対に編集しない**
（D35「りょーちんのブランチへの変更はしない」）。ローカルのあれは `origin/mega-starmie-ex-deck`
から取った**作業コピーのスナップショット**であり、我々のブランチでは未追跡。
編集しても `git diff` に出ず、彼の成果物のコピーに我々の変更が混ざる。
各ステップは順に実行する。

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

4. **検証する（D29/D35 の判定規則。新旧直接対決を採用ゲートにしてはいけない）。**

   a. **安全ゲート**（正当性の検査であって効果量ではない）:
      ```
      python3 "$(git rev-parse --show-toplevel)/verification/bench.py" 300
      ```
      `CRASH=1` / 終了コード2 → **即・不採用**（「絶対に落ちない」要件違反）。手順6へ。
      vs random が **96%未満** → 不採用。手順6へ。

   b. **効果量の判定 = CEW**（較正済み族外ゲージ4種の遭遇加重合成）。
      基準線 **41.5%**、**N=800/セル**、閾値 **+2pt**。計算は `verification/cew.py`、
      手順は `verification/README.md` の提出前ゲート。
      **族内ゲージ（自パイロットが相手を操縦）や新旧直接対決の勝率は、相手操縦者との
      実力差ぶん過大評価する（D27: +8〜+62pt）ので採否には使わない**——
      スクリーニングで方向性を見るまで。
      閾値未満 → 不採用。手順6へ。

   c. 効果量の測定に入る前に、可能なら**行動デルタ**（狙った局面で実際に手が変わったか）
      を先行ゲートとして確認する。手が変わっていない変更に N=800 を払わない。

5. **採用した場合：記録する（レポート素材になる）。** `docs/memo/decisions.md` に追記:
   - 日付 / 仮説 / 変更点の要約 / CEW（基準比・N・CI）/ 安全ゲートの結果 / 採用理由。
   結果データ（数値）は `docs/memo/data.md` にも残す。
   **writeup で使う数値は `docs/memo/claims-ledger.md` に行を足してから**（playbook §7 T6）。

6. **不採用の場合：必ず元に戻す。**
   ```
   cp .bench/main_prev.py main.py
   ```
   そのうえで `docs/memo/journal.md` に「○○を試したが勝率↑せず（数値）→ 戻した」と1行残す
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

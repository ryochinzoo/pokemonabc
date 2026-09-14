---
name: submission-check
description: Pre-flight checks before submitting to Kaggle, so a broken package does not waste one of the 5 daily submissions. Validates deck.csv, that only the standard library is imported, the tar.gz layout, and runs a crash / legal-move / timing smoke test. Run manually before every real submission.
disable-model-invocation: true
allowed-tools: Bash(cd *) Bash(python3 *) Bash(tar *) Bash(ls *)
---

# submission-check

Kaggle へ提出する**前**に必ず通す検査。提出は1日5回まで・最終順位は直近2提出のみで
決まるので、壊れた提出で枠を1つ溶かすのは大きな損。それを防ぐ。
（手動専用＝Claudeが勝手に走らせない設計。提出直前に人間が `/submission-check` する。）

## 実行

リポジトリのルートから、**提出するデッキディレクトリを必ず指定して**実行する:

```
python3 "${CLAUDE_SKILL_DIR}/scripts/check.py" --submission src/input/datasets/decks/starmie-aggro
```

`--submission` は必須(既定値なし)。2人チームで別々のデッキを持つため、どちらかを
既定値にすると「検査した対象と違うデッキを提出する」事故になるため
(2026-07-21の運用監査で、既定値が旧デッキを指したまま放置されていた)。

## 検査内容

1. **deck.csv** — ちょうど60枚 / 全て整数 / 全て実在のCard ID（`verification/data/EN_Card_Data.csv`照合）。
   同一IDが5枚以上なら警告（基本エネルギー以外は4枚制限）。
2. **imports** — `main.py` 等が**標準ライブラリ + cg + 同梱モジュール**以外を import
   していないか（サンドボックスに第三者パッケージは無い）。
3. **tar 構造** — `submission.tar.gz` のルートに `main.py` と `deck.csv` があるか。
   `cg/` 同梱も確認（前回スコア413.4が通った構成）。
4. **スモーク対戦** — `main.agent` を20戦走らせ、大会の**ハード要件**を実測で確認:
   - 一度も**クラッシュしない**
   - 常に**合法手**を返す（範囲内・重複なし・min/maxCount内）
   - 各判断が**時間内**。※D37で確定: **1手ごとの制限時間は存在しない**
     (`cabt.json`: `actTimeout: 0`)。実体は**エピソード単位600のバンク**
     (`observation.remainingOverageTime`)。現行は1戦約325msで約1800倍の余裕。
5. **本番ランナー適合** — `verification/conformance.py`（D37で新設）。**これは他の4項目では
   絶対に検出できない経路を見る**:
   ```
   cd <デッキディレクトリ> && python3 ../../../../../verification/conformance.py
   ```
   本番の interpreter は**デッキを `agent()` の戻り値から取る**(`decks = [state[i].action]`)
   が、`verification/selfplay.py` は `deck.csv` から読んで `battle_start` に直接渡すため、
   **デッキ返却分岐はベンチでも CEW でも一度も実行されない**。壊れていても全ての数値は
   正常に出て、本番だけ全敗する。検査するのは:
   - `agent({"select": None, ...})` が**ちょうど60枚**の int リストを返す
     （60枚でなければ本番は `INVALID` → reward -1 = 即敗北）
   - `deck.csv` との一致 / 同名4枚制限
   - `battle_start` の **`errorPlayer < 0`**（エンジン自身のデッキ検証。
     4枚制限は見ないが**別種のデッキエラーは見る**）

## 結果の扱い

- `FAIL` が1つでもあれば**提出しない**。表示された項目を直して再実行。
- 全部合格したら、表示される `tar czf ...` コマンドで提出物を作り直してから提出する。
- スモークで `クラッシュ` や `契約違反` が出たら、`@robustness-guard` に原因と最小修正を
  調べさせると速い。

## 注意（未確認のルール）

提出サイズ上限（197.7 MiB?）は**未確認**。Kaggle公式ルールで要確認。大きく超えそうな
ときだけ気にすればよい（現構成は十分小さい）。

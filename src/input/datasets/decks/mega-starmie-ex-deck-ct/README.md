# PTCG AI 監査駆動・自動改善ループ README

## 0. 目的

このREADMEは、監査結果を基準に、AIが自律的に

```text
調査
→ 仮説
→ failing test
→ 最小実装
→ test
→ 自己監査
→ 差分判定
→ 次のIssue
```

を繰り返すための作業契約です。

目的は、監査資料を要約することではありません。

> **現在確認されている不自然な行動を、汎用的なFactとPolicy責務の修正によって減らすこと。**

各Issueは一つずつ処理し、実装後に必ず自己監査してください。

---

## 1. 読み込む資料

### 必須

```text
README.md
ISSUE_ROADMAP.md
ptcg_68_replay_research_audit.md
src/input/datasets/decks/mega-starmie-ex-deck-ct/main.py
src/input/datasets/decks/mega-starmie-ex-deck-ct/test_immediate_outcome.py
```

### 補助資料

存在する場合は参照してください。

```text
ptcg_68_sensitivity_summary.csv
ptcg_68_dominance_audit_cases.csv
v7_4_regression_guard_cases.csv
```

補助資料と監査MDが食い違う場合は、監査MDの後半にある訂正・総論を優先してください。

---

## 2. 作業上の役割

このループでは、AIは同時に次の役割を持ちます。

### 実装者

- 現行コードを読む
- 最小変更でIssueを修正する
- unit testを追加する
- 既存testを維持する

### 監査者

- 実装前の仮説を疑う
- 実Outcomeと推測Factを分離する
- 二重計上を探す
- カード名専用補正を探す
- 無関係な順位変化を警戒する
- 変更後のコードを、実装者とは反対の立場から再読する

### 記録者

- 何を変更したか
- なぜ必要だったか
- どのtestで証明したか
- 何がまだ不明か
- 次のIssueへ進めるか

を明示します。

---

## 3. 正本と判断基準

優先順位は次です。

1. 現在の実コード
2. 現在のtest
3. `ptcg_68_replay_research_audit.md`
4. 補助CSV
5. 過去の説明や推測

監査MDにある事実・Policy判断・推測を混ぜないでください。

### 区別するもの

```text
Replay上で確認された事実
コード上で確認された事実
Policyとして望ましい判断
反実仮想
未確認
```

不明なものは、不明のまま残してください。

---

## 4. 自動ループの基本単位

一回のループで扱うIssueは一つだけです。

### Step 1: Issueを選ぶ

優先順位の最上位にある未完了Issueを一つ選びます。

### Step 2: 現行責務を読む

最低限、次を確認します。

- Factを作る場所
- Policyへ渡す場所
- ActionScoreへ反映する場所
- 並び替えを行う場所
- 既存helper
- 既存test
- 関連する正常Guard

### Step 3: 仮説を書く

実装前に次を記録します。

```markdown
## 仮説

- 現象:
- 原因候補:
- コード上の根拠:
- 変更予定責務:
- 変更しない責務:
- 反証条件:
```

原因が確認できない場合、実装へ進まず調査を継続してください。

### Step 4: failing testを作る

先に、現在の不自然な判断を再現する最小testを追加します。

testはカード名を固定するだけでなく、問題構造を表現してください。

悪い例:

```text
Mega Froslassなら高得点
```

良い例:

```text
Active Attachによって新規Attackが合法化し、
そのAttackが同TurnのKO／Winへ到達する
```

### Step 5: 最小実装

- 一つの責務だけ変更
- 既存helperを再利用
- 新しい定数を増やす前にFact不足を疑う
- 大規模整理をしない
- 別Issueへ触れない

### Step 6: test実行

最低限:

```bash
python -m pytest \
  src/input/datasets/decks/mega-starmie-ex-deck-ct/test_immediate_outcome.py \
  -q
```

関連testが別にある場合は追加実行してください。

全体testが現実的なら実行して構いません。

```bash
python -m pytest -q
```

### Step 7: 反対側から自己監査

変更後、次を必ず確認します。

- 未実行結果を実Outcomeへ書いていないか
- 同じ価値を複数fieldへ二重計上していないか
- 直接Attackと準備Actionの優先関係が壊れていないか
- Bench育成を一括で壊していないか
- カード名専用条件がないか
- 閾値変更で広範囲を誤魔化していないか
- `_result_key()`変更が本当に必要か
- 他Issueを混ぜていないか
- testが実装詳細に依存しすぎていないか
- testを弱めて通していないか

### Step 8: 採否判定

次の三つから選びます。

```text
ACCEPT
REWORK
BLOCKED
```

#### ACCEPT

- Target testが通る
- Guard testが通る
- 最小責務として説明できる
- 無関係な挙動を壊していない
- 二重計上がない

#### REWORK

- Targetは通るが設計が過剰
- 無関係な順位へ影響する
- 固定加点へ逃げている
- testが不足
- 別Issueを混ぜている

#### BLOCKED

- 必要なFactを現行APIから取得できない
- カード効果が不明
- 原因関数を特定できない
- test環境で再現不能
- 仕様判断が必要

### Step 9: 報告

指定形式で記録し、ACCEPTの場合だけ次のIssueへ進みます。

---

## 5. Issue優先順位

## P0: Active Attach後の即時KO／Win reachability

現在の最優先です。

問題構造:

```text
ActiveへEnergy Attach
→ 新しいAttackが合法化
→ damage
→ KO
→ Prize
→ Win
```

現行コードでは、Attach前後の支払い可能Attack差分として、

```text
enables_attack
enabled_attack_ids
```

までは計算されています。

一方、Attach後に新しく合法化されるAttackの

```text
予測damage
到達可能KO
到達可能Prize
到達可能Win
```

が、Attach候補の評価へ十分に伝わっていません。

### P0の設計原則

- Attach自体の実Outcomeへ未実行KOを書かない
- 新しく合法化されたAttackだけを見る
- 現在のActiveへのAttachだけを見る
- blocked AttackをKO扱いしない
- 複数Attackを比較できるようにする
- Froslass／Water専用分岐にしない
- 固定大加点で逆転させない
- 直接KO／Win Attackを準備Actionが不当に追い越さない

### P0で最初に確認するもの

```text
ImmediateOutcome
enables_knockout
evaluate_attach()
evaluate_attack()
score_attach()
action_score()
_result_key()
attack_damage_for_card()
wall判定
energy payment helper
```

### P0必須test

1. Active Attachが新しいAttackを合法化する
2. 新規合法AttackがKO可能
3. Prize取得でWinへ到達可能
4. blocked Attackはreachable KO／Winにならない
5. Bench Attachを即時Attackとして扱わない
6. Attackを新規合法化しないAttachは昇格しない
7. すでに合法なAttack価値をAttachへ重複計上しない
8. Froslass／Water以外でも同じ構造が動く
9. 複数の新規Attackを比較できる
10. Attachの実Outcomeには未実行KO／Prize／Winを記録しない
11. 直接KO／Win Attackの優先を維持する

---

## P1: Composite access

P0がACCEPTになった後だけ着手します。

対象:

```text
Bench Attach → Retreat → Attack
Bench Attach → Surfing Beach → Attack
Retreat → Ready attacker → Attack
```

必要責務:

```text
現在のActionから
同Turn中にどのActiveへ到達でき
どのAttackまで実行できるか
```

P0のActive Attach専用処理へ無理に混ぜないでください。

---

## P2: Attach → paid RetreatによるEnergy浪費

対象構造:

```text
ActiveへEnergy Attach
→ 同Turnに有償Retreat
→ 付けたEnergyを失う
→ Attackなし
→ 明確な利益なし
```

Attach単体やRetreat単体を罰しないでください。

sequence全体で、

- Energy損失
- Attack不成立
- 状態解除なし
- KO回避なし
- free-retreatでない

ことを確認します。

---

## P3: 0 damage Attack

二つのIssueを混ぜないでください。

### P3-A

評価器も0 damageと認識しているのに、準備行動より優先する。

### P3-B

実際は0 damageだが、評価器がdamage／KOありと誤認する。

P3-AはTier／Policy問題、P3-BはOutcome model問題です。

別test・別差分にしてください。

---

## P4: Active進化の残存穴

既存修正後にも残る、Active進化による即時damage改善の取りこぼしを扱います。

閾値変更だけで直す場合も、変更nodeが狭いことをtestで示してください。

他の進化、Bench育成、直接Attackを壊さないでください。

---

## P5: Opponent Threat vs Development

公開盤面から、

- 相手が次Turn攻撃可能か
- 自ActiveがKOされるか
- 現在処理可能か
- Prize取得と被KOの交換

を評価する責務です。

特定カード名専用補正にしないでください。

P0〜P4が安定する前に着手しないでください。

---

## 6. 共通の禁止事項

- デッキ変更
- カード枚数変更
- カード名専用の救済
- Replay ID／Turn番号による分岐
- 未実行結果を実Outcomeとして記録
- 同じ価値の二重計上
- 複数Issueの同時実装
- 大規模リファクタリング
- 無根拠な`_result_key()`変更
- test削除
- 期待値の弱体化
- 不明なカード効果の推測
- 「testが通ったから勝率が上がる」という断定
- ACCEPT前に次Issueへ進むこと

---

## 7. 共通Guard

修正時は、少なくとも次を壊さないでください。

- 直接KO Attack
- 直接Win Attack
- 正常なAttach → Attack
- 正常なBench育成
- CinderaceのEnergy加速
- free-retreat
- Surfing Beachの正常利用
- Active進化後Attack
- Wally後Attack
- EX wallで無効になるAttackの認識
- 同じ構造を持つ別カード

勝利例であることだけを理由に、Turn全体を正常Guardへしないでください。

Guardは、保護するActionと責務を明示してください。

---

## 8. 変更の粒度

望ましい変更:

```text
Fact追加
helper追加
既存Factの意味修正
ActionScoreへの限定反映
targeted unit test
```

避ける変更:

```text
多数の定数を同時調整
Tier全体の再設計
全Actionのscore再配分
GameSimulatorの全面改修
デッキ固有カードの特例追加
```

一つのIssueに対し、最小の責務差分で進めてください。

---

## 9. テスト方針

testは次の三層に分けます。

### Fact test

- helperが正しいFactを返す
- 実Outcomeとreachable Factが分離される
- blocked、KO、Prize、Winが正しい

### Policy test

- FactがActionScoreへ期待どおり反映される
- 直接Attackと準備Actionの優先関係が正しい
- 無関係な育成Actionを壊さない

### Guard test

- 既存の正常な判断が維持される
- 別カードでも同型構造が動く
- 別Issueへ影響しない

test名は、カード名だけでなく、守る責務が分かる名前にしてください。

---

## 10. ループ停止条件

次の場合は自動ループを停止してください。

- BLOCKEDになった
- 仕様判断が必要
- 既存test失敗の原因がP0〜P5と無関係
- 変更が複数Issueへ広がる
- 大規模設計変更が必要
- カード効果を確認できない
- 直接Attackと準備Actionの優先規則を決められない
- 同じ修正を二回REWORKしてもGuardを通せない
- すべての優先IssueがACCEPTになった

停止時は、不明点と必要な判断だけを報告してください。

---

## 11. 各Issueの報告形式

```markdown
# Issue実装・監査報告

## 1. Issue
- ID:
- 状態: ACCEPT / REWORK / BLOCKED

## 2. 現象
- ...

## 3. 原因
- コード上確認できた事実:
- 推測:
- 不明:

## 4. 変更ファイル
- ...

## 5. 設計
- 追加／変更したFact:
- 実Outcomeとの分離:
- Policyへの反映:
- 二重計上防止:
- 変更しなかった責務:

## 6. 追加したtest
### Fact
- ...

### Policy
- ...

### Guard
- ...

## 7. test結果
### 変更前
- command:
- passed:
- failed:

### 変更後
- command:
- passed:
- failed:

## 8. 自己監査
- カード名専用条件:
- 二重計上:
- 直接Attackの保護:
- Bench育成の保護:
- 別Issue混入:
- _result_key変更:
- 大規模差分:

## 9. git diff概要
- diff stat:
- 主な変更:

## 10. 残る不明点
- ...

## 11. 次の判断
- 次Issueへ進む / REWORK / 停止
```

---

## 12. 最終報告

すべてのループ終了後、次をまとめてください。

```markdown
# 監査駆動・自動改善ループ 最終報告

## 1. 完了Issue
- ...

## 2. 未完了Issue
- ...

## 3. 変更ファイル
- ...

## 4. 追加test
- ...

## 5. test結果
- ...

## 6. 修正できた不自然行動
- ...

## 7. 修正できなかった行動
- ...

## 8. 自己監査で差し戻した変更
- ...

## 9. 現在の不明点
- ...

## 10. git diff
- ...

## 11. 次に人間が確認すべき点
- ...
```

---

## 13. 成功条件

このループの成功は、変更量やIssue消化数では決まりません。

成功条件は次です。

> **監査で確認された不自然な判断を、個別カードへの過適合ではなく、汎用的なFact・Policy責務として修正し、Target testとGuard testの両方で維持できること。**

修正が広すぎる場合は、Issueを消化するよりREWORKまたは停止を選んでください。

P0から開始してください。

---

## 14. 文書の役割とIssue選択

問題一覧と解決経路は、`ISSUE_ROADMAP.md`を正とします。

| 文書 | 使用目的 |
|---|---|
| `README.md` | 調査・実装・test・自己監査・採否判定の進め方 |
| `ISSUE_ROADMAP.md` | 現在存在する問題、依存順、解決手順、完了条件 |
| `ptcg_68_replay_research_audit.md` | 各問題の証拠、数値、正常例、反例、訂正 |
| `main.py`／test | 現在のコード上の事実 |

自動ループ開始時は、次の順に行ってください。

1. `ISSUE_ROADMAP.md`で最上位の`READY` Issueを選ぶ
2. そのIssueの問題、原因、目標状態、必須test、完了条件を読む
3. 監査MDで証拠と正常Guardを確認する
4. READMEのループ手順に従って実装・自己監査する
5. `ACCEPT`の場合だけ次Issueへ進む

監査MDの見出し順や、観測件数の多さだけで新しいIssueを作らないでください。

`ISSUE_ROADMAP.md`にない問題を発見した場合は、既存Issueの派生か新規Issueかを報告し、現在のIssueへ混ぜずに停止または保留してください。


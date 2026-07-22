# GameSimulator関連棚卸し

対象ファイル: `main.py.backup`

方針:

- コードは変更しない。
- 新しいGameSimulatorは実装しない。
- 現行実装を肯定的に解釈せず、実際にコードが行っている処理だけを書く。
- 行番号は `main.py.backup` 基準。

## 1. GameSimulator本体

### `GameSimulator.__init__` line 4284

- 入力: `board: BoardState`
- 出力: なし
- 保持するもの: `self.board = board`
- 参照するBoardState情報: なし
- 実際に計算している内容: なし
- 暗黙に仮定している情報: 渡されたBoardStateがdeepcopy可能であること
- 非公開情報を推測しているか: しない
- 他の評価関数との重複: なし
- 呼び出し元: 各Actionの `evaluate()`

### `GameSimulator.evaluate_after_action` line 4287-4290

```text
virtual = copy.deepcopy(self.board)
action.apply(virtual)
return BoardEvaluator(virtual).evaluate()
```

- 入力: `action: GameAction`
- 出力: `float`
- 参照するBoardState情報:
  - `copy.deepcopy(self.board)` でBoardState全体
  - `action.apply(virtual)` が読む/書く仮想状態
  - `BoardEvaluator(virtual).evaluate()` が読む盤面評価
- 実際に計算している内容:
  - 自分の現在選択候補を1回だけ仮想盤面へ適用
  - 適用後の盤面を `BoardEvaluator` で静的評価
- 自分の行動を何回適用するか:
  - 1回だけ
- 相手の行動を実際に適用しているか:
  - していない
- 自分の次の行動を実際に適用しているか:
  - していない
- 合法Option集合を再生成しているか:
  - していない
- 相手の手札、山札、進化、サポート、入れ替えをどう扱うか:
  - GameSimulator本体では扱わない
  - `BoardEvaluator` 側の静的評価で相手最大打点等を見るだけ
- 何をもって「相手最大応答」としているか:
  - GameSimulator内には存在しない
  - 近いものは `TempoEvaluator.evaluate()` line 3795 の `calculate_max_damage(self.board.opp_active, next_turn=True)` だが、これは相手行動適用ではなく静的な最大打点評価
- 何をもって「自分最大応答」としているか:
  - GameSimulator内には存在しない
  - 近いものは `FutureBoardEvaluator.evaluate()` line 3809 のベンチ `can_attack_next_turn` と line 3810 の `high_impact_attack_progress`
- 非公開情報を推測しているか:
  - GameSimulator本体は推測しない
  - 周辺評価は、次ターン攻撃可能性や最大打点を静的に推測する
- 他の評価関数との重複:
  - `BoardEvaluator` が `PrizeRaceEvaluator` / `TempoEvaluator` / `FutureBoardEvaluator` を呼び、Action内の個別評価と同じ概念を再評価する
- 呼び出し元:
  - `AttackAction.evaluate` line 4738
  - `EvolveAction.evaluate` line 4878
  - `RetreatAction.evaluate` line 5149
  - `PlayCardAction.evaluate` line 5239
  - `AttachEnergyAction.evaluate` line 5353 / 5437 / 5512

結論:

- 現行GameSimulatorの実質探索深度は「自分の現在行動1手」。
- 相手応答も自分の次手も適用していない。
- 2手先探索ではない。

## 2. 仮想盤面

GameSimulatorまたは `action.apply()` のために存在する状態。

### 仮想バトル場/ベンチ

- 定義場所:
  - `_my_active` line 317
  - `_opp_active` line 318
  - `_my_bench_slots` line 319
  - `_opp_bench_slots` line 320
- 更新するメソッド:
  - `switch_with_bench` line 2850-2858
  - `resolve_knockout` line 2908-2933
  - `RetreatAction.apply` line 5151-5160
  - `PlayCardAction.apply` のボス処理 line 5245-5251
- 読み取るメソッド:
  - `active` line 474-476
  - `opp_active` line 478-480
  - `bench_slots` line 482-484
  - `opp_bench_slots` line 486-488
  - `bench` line 490-492
  - `opp_bench` line 494-496
  - `all_my_pokemon` line 498-504
  - `all_opp_pokemon` line 506-512
- GameSimulator削除時に必要か:
  - 通常選択処理では不要。Observationの実体を読めばよい。
- 通常の選択処理でも必要か:
  - 通常処理では現在盤面参照のみ必要。仮想更新は不要。
- 正確に再現できているか:
  - 交代先を入れ替えるだけなら一部正確。
  - KO後の後続選択は自動選択なので不正確。
- API実体との不整合リスク:
  - 正式にはKO後の後続はプレイヤーが選ぶ。`_choose_replacement_index` は勝手に選ぶ。

### 仮想サイド

- 定義場所:
  - `_my_prizes` line 321
  - `_opp_prizes` line 322
- 更新するメソッド:
  - `take_prizes` line 2867-2871
  - `resolve_knockout` line 2908-2933
- 読み取るメソッド:
  - `my_remaining_prizes` line 530-532
  - `opp_remaining_prizes` line 534-536
  - `PrizeRaceEvaluator.evaluate` line 3784-3785
  - `BoardEvaluator.evaluate` line 3823-3826
- GameSimulator削除時に必要か:
  - 仮想サイドは不要。
  - 実サイド参照は必要。
- 通常の選択処理でも必要か:
  - 実サイド枚数は必要。
- 正確に再現できているか:
  - KOした場合のサイド枚数だけは近い。
  - レガシーエネルギー等のサイド軽減は `calculate_prize_value` に依存。
- API実体との不整合リスク:
  - KO後の追加効果、複数同時KO、特殊なサイド処理は弱い。

### 仮想スタジアム

- 定義場所:
  - `_stadium_id` line 323-325
- 更新するメソッド:
  - `set_stadium` line 561-562
  - `PlayCardAction.apply` line 5242-5244
- 読み取るメソッド:
  - `stadium_id` line 538-540
  - `has_foreign_stadium` line 542-544
  - スタジアム評価各所
- GameSimulator削除時に必要か:
  - 仮想スタジアムは不要。
  - 現在スタジアム参照は必要。
- 通常の選択処理でも必要か:
  - 必要。
- 正確に再現できているか:
  - スタジアムIDの差し替えだけ。
  - スタジアムの継続効果は各評価関数に散在。
- API実体との不整合リスク:
  - スタジアムの使用済み状態、相手ターン効果、強制効果は再現していない。

### 仮想HP

- 定義場所:
  - `_hp` line 327
- 更新するメソッド:
  - `set_hp` line 554-556
  - `AttackAction.apply` line 4746
  - `DamageAction.apply` line 5672-5673
- 読み取るメソッド:
  - `current_hp` line 549-552
  - `BoardEvaluator` / 各評価関数
- GameSimulator削除時に必要か:
  - 仮想HPは不要。
  - 実HP参照は必要。
- 通常の選択処理でも必要か:
  - 実HPは必要。
- 正確に再現できているか:
  - 単純ダメージは一部再現。
  - ダメージ追加効果、弱点抵抗、効果無視、ベンチダメージは `effective_attack_damage` と個別処理次第。
- API実体との不整合リスク:
  - 攻撃の追加効果、複数対象、特殊状態、ダメカンとダメージの区別が不完全。

### 仮想カードID

- 定義場所:
  - `_card_ids` line 328
- 更新するメソッド:
  - `set_card_id` line 558-559
  - `evolve_target` line 2860-2865
  - `EvolveAction.apply` line 4920-4924
- 読み取るメソッド:
  - `card_id` line 546-547
  - `get_attacks` line 572-578
  - 評価関数全般
- GameSimulator削除時に必要か:
  - 仮想進化を見ないなら不要。
- 通常の選択処理でも必要か:
  - 不要。実Pokemon.idを読むだけでよい。
- 正確に再現できているか:
  - 進化先IDだけ変える。
  - HP最大値、受けているダメージ量、進化元、特性、道具、状態は完全には更新しない。
- API実体との不整合リスク:
  - line 2863 のコメント通り「最大HP未公開のため、受けているダメージ量の正確な維持は行わない」。

### 仮想エネルギー

- 定義場所:
  - `_extra_energy` line 329
- 更新するメソッド:
  - `add_virtual_energy` line 906-909
  - `add_virtual_energy_card` line 911-914
  - `AttachEnergyAction.apply` line 5514-5522
- 読み取るメソッド:
  - `attached_energy_tokens` line 599-615
  - `count_energy` line 631-644
  - `can_use_attack` line 919-944
  - `attack_energy_shortfall` line 946-970
  - `FutureBoardEvaluator.evaluate` line 3806 / 3809 / 3810
- GameSimulator削除時に必要か:
  - 仮想エネルギーは不要。
  - 実エネルギー参照は必要。
- 通常の選択処理でも必要か:
  - 実エネと「このOptionを選んだ後に攻撃できるか」の一手先には小さく必要。
- 正確に再現できているか:
  - 手貼りによるエネルギー追加だけ一部再現。
  - イグニッションは `AttachEnergyAction.apply` line 5518-5519 で仮想追加しない。
- API実体との不整合リスク:
  - エネルギー付替え、アカマツ、エースバーンのワザ加速、特殊エネのターン終了処理は完全ではない。

### 消費済みエネルギーserial

- 定義場所:
  - `_spent_energy_serials` line 330
- 更新するメソッド:
  - `discard_attached_energy` line 802-811
  - `DiscardEnergyAction.apply` line 5655-5657
- 読み取るメソッド:
  - `attached_energy_cards` line 617-624
  - `attached_energy_card_ids` line 626-629
- GameSimulator削除時に必要か:
  - 仮想トラッシュをしないなら不要。
- 通常の選択処理でも必要か:
  - エネルギー選択の評価には実カードserial参照は有用。
  - 仮想消費集合は不要。
- 正確に再現できているか:
  - 1枚の添付エネルギーを見えなくするだけ。
- API実体との不整合リスク:
  - トラッシュ置き場へ移動させない。カード移動ログや以後の回収可能性は再現しない。

### ダメカン残数

- 定義場所:
  - `_damage_counter_steps_used` line 331
  - `_remaining_damage_counter` line 332
- 更新するメソッド:
  - この抽出範囲では明確な更新は見えない。DamageCounterEngine周辺で読むための状態。
- 読み取るメソッド:
  - `remain_damage_counter` line 374-376
- GameSimulator削除時に必要か:
  - GameSimulator専用ではない。
- 通常の選択処理でも必要か:
  - ダメカン選択時には必要。
- 正確に再現できているか:
  - APIの `remainDamageCounter` を保持するだけなら正確。
  - 仮想探索全体での合法Option更新は不正確。
- API実体との不整合リスク:
  - ダメカンを置いた後の次Option集合を再生成しない。

### 回復上限

- 定義場所:
  - `_healing_ceiling` line 333
- 更新するメソッド:
  - この抽出範囲では主要更新なし。
- 読み取るメソッド:
  - 検索上、限定的。現行GameSimulator本体からは直接使わない。
- GameSimulator削除時に必要か:
  - GameSimulator専用なら不要。
- 通常の選択処理でも必要か:
  - 実HPから回復対象を評価するだけなら不要。
- 正確に再現できているか:
  - 不明。主要applyには見えない。
- API実体との不整合リスク:
  - 回復でエネルギーを手札に戻す等のカード効果を正確には再現しない。

## 3. `action.apply()`

### `GameAction.apply` line 4312-4313

- 仮想盤面へ反映する内容: 何もしない
- 反映していないカード効果: 全て
- 正確性: 名前だけ
- GameSimulator専用か: はい
- 一手先評価へ再利用可能か: 不要
- 削除候補: 完全削除

### `AttackAction.apply` line 4740-4749

- 仮想盤面へ反映する内容:
  - `effective_attack_damage(attacker, attack)` を相手バトル場HPから引く
  - HPが0なら `resolve_knockout(defender, target_is_mine=False)`
- 反映していないカード効果:
  - ベンチダメージ
  - 特殊状態
  - エネルギートラッシュ
  - 山札サーチ
  - 複数対象
  - ワザ追加効果の多く
  - 攻撃後のターン終了や状態変化
- 正確性:
  - 単純な相手バトル場ダメージだけ一部再現
- GameSimulator専用か:
  - applyはGameSimulator専用
- 一手先評価へ再利用可能か:
  - 小さく作り直せば、単純ダメージ/KO/即時勝利判定には使える
- 削除候補:
  - 現行実装は削除。仕様だけ救出。

### `EvolveAction.apply` line 4920-4924

- 仮想盤面へ反映する内容:
  - Option対象ポケモンの仮想カードIDを進化先IDへ変更
- 反映していないカード効果:
  - 最大HP更新
  - 現HP/ダメージ維持の正確処理
  - 進化元情報
  - 特性発生
  - 進化時制限
- 正確性:
  - 低い。カードIDだけ。
  - `evolve_target` line 2863 に「最大HP未公開のため、受けているダメージ量の正確な維持は行わない」と明記。
- GameSimulator専用か:
  - はい
- 一手先評価へ再利用可能か:
  - 現行コードは不可。進化後攻撃可否などの小仕様だけ作り直す。
- 削除候補:
  - 現行applyは削除。

### `RetreatAction.apply` line 5151-5160

- 仮想盤面へ反映する内容:
  - Optionがベンチを指していればそのベンチと交代
  - そうでなければ `_best_retreat_target` で選んだベンチと交代
- 反映していないカード効果:
  - 逃げエネルギー消費
  - `retreated` フラグ
  - 特殊状態による逃げ不可
  - 逃げコスト支払い選択
- 正確性:
  - 交代だけ一部再現
  - 逃げエネルギー消費をしないため重要局面で不正確
- GameSimulator専用か:
  - はい
- 一手先評価へ再利用可能か:
  - 交代候補比較の仕様は参考可。ただしエネルギー消費込みで作り直し。
- 削除候補:
  - 現行applyは削除。

### `PlayCardAction.apply` line 5241-5253

- 仮想盤面へ反映する内容:
  - 自分のスタジアムなら `set_stadium`
  - ボスの司令なら対象相手ベンチと相手バトル場を交代
- 反映していないカード効果:
  - ポフィン
  - ハイパーボール
  - ポケギア
  - ポケパッド
  - メガシグナル
  - 夜のタンカ
  - トウコ
  - アカマツ
  - セイジ
  - ミツルの思いやり
  - Tool Scrapper
  - ヒーローマント装着
  - サポート使用済み/スタジアム使用済み更新
  - 手札/山札/トラッシュ移動
- 正確性:
  - スタジアムID変更とボス交代だけ一部再現
  - 大半のカードは未反映
- GameSimulator専用か:
  - はい
- 一手先評価へ再利用可能か:
  - ボス交代、スタジアム置換の仕様だけ救出可
- 削除候補:
  - 現行applyは削除。

### `EndAction`

- `apply()` を持たない。`GameAction.apply` の何もしない処理になる。
- 仮想盤面へ反映する内容:
  - なし
- 反映していないカード効果:
  - ターン終了処理
  - イグニッション破棄
  - ポケモンチェック
  - 毒/やけど/眠り等
  - 相手ターン移行
- 正確性:
  - 名前だけで実質未実装
- GameSimulator専用か:
  - なし
- 一手先評価へ再利用可能か:
  - 不要
- 削除候補:
  - apply不要

### `AbilityAction`

- `apply()` を持たない。
- 仮想盤面へ反映する内容:
  - なし
- 反映していないカード効果:
  - エースバーンのセットアップ特性
  - マシマシラ
  - ユキメノコ
  - シェイミ
  - その他特性
- 正確性:
  - 名前だけ
- GameSimulator専用か:
  - なし
- 一手先評価へ再利用可能か:
  - 不可
- 削除候補:
  - apply不要

### `CountAction`

- `apply()` を持たない。
- 仮想盤面へ反映する内容:
  - なし
- 正確性:
  - カウント選択評価だけ。盤面更新なし。
- 削除候補:
  - GameSimulatorとは無関係

### `AttachEnergyAction.apply` line 5514-5522

- 仮想盤面へ反映する内容:
  - 基本水/悪など `ENERGY_CARD_TO_TYPE` にあるカードを `_extra_energy` として対象へ追加
  - イグニッションは line 5518-5519 で何も追加しない
- 反映していないカード効果:
  - 手札からカードを取り除く
  - 手貼り済みフラグ
  - 特殊エネルギーのターン終了破棄
  - アカマツ/エースバーン等の複数エネルギー加速
- 正確性:
  - 通常エネルギー1枚追加だけ一部再現
  - イグニッションは評価と仮想盤面がズレる
- GameSimulator専用か:
  - はい
- 一手先評価へ再利用可能か:
  - 「エネルギー付与後の攻撃可否」仕様だけ救出可
- 削除候補:
  - 現行applyは削除。

### `EnergySelectionAction`

- `apply()` を持たない。
- 仮想盤面へ反映する内容:
  - なし
- 反映していないカード効果:
  - 選択したエネルギーの手札移動/デッキ戻し/付け替え
- 正確性:
  - 評価のみ。盤面更新なし。
- GameSimulator専用か:
  - なし
- 一手先評価へ再利用可能か:
  - 選択評価だけなら参考可
- 削除候補:
  - GameSimulator用途では削除。

### `DiscardEnergyAction.apply` line 5655-5657

- 仮想盤面へ反映する内容:
  - `discard_attached_energy` で対象ポケモンのエネルギーserialを `_spent_energy_serials` に追加
- 反映していないカード効果:
  - トラッシュへのカード移動
  - トラッシュ後の回収可能性
  - 複数エネルギー選択
- 正確性:
  - 対象のエネルギーを以後カウントしない点だけ一部再現
- GameSimulator専用か:
  - はい
- 一手先評価へ再利用可能か:
  - 逃げる際のエネルギー消費評価として小さく作り直し可
- 削除候補:
  - 現行applyは削除。

### `DamageAction.apply` line 5669-5676

- 仮想盤面へ反映する内容:
  - `selected_damage_amount()` の値を対象HPから引く
  - HP0なら `resolve_knockout`
- 反映していないカード効果:
  - ダメカン個数の残数更新
  - 複数回選択後の合法Option再生成
  - マシマシラの「自分1匹から相手1匹へ移す」制約
  - ユキメノコ等の自動ダメカン処理
- 正確性:
  - Jetting Blowの50ダメージ等、単純な追加ダメージだけ一部再現
- GameSimulator専用か:
  - はい
- 一手先評価へ再利用可能か:
  - ダメカン/追加ダメージ後のKO判定として小さく作り直し可
- 削除候補:
  - 現行applyは削除。

### `YesNoAction`

- `apply()` を持たない。
- 仮想盤面へ反映する内容:
  - なし
- 正確性:
  - 評価のみ
- 削除候補:
  - GameSimulatorとは無関係

## 4. BoardEvaluatorとの重複

### 相手の最大打点

- `TempoEvaluator.evaluate` line 3795:
  - `calculate_max_damage(self.board.opp_active, next_turn=True) * 2.5` を減点
- `BoardState.opp_active_max_damage` line 1988:
  - 多数のAction評価で使用
- `RetreatAction.evaluate` line 4959-4961:
  - active dangerやtarget比較に使用
- `AttackAction.evaluate` line 4592-4601:
  - 回復前攻撃判断に使用

重複経路:

```text
AttackAction.evaluate
→ 個別に active_will_be_knocked_out / opp_active_max_damage を見る
→ GameSimulator.evaluate_after_action * 0.05
→ BoardEvaluator
→ TempoEvaluatorで相手最大打点を再度減点
```

### 自分の最大打点

- `TempoEvaluator.evaluate` line 3794:
  - `best_attack_damage(active) * 3.0`
- `AttackAction.evaluate` line 4441以降:
  - 攻撃ダメージを直接評価
- `RetreatAction.evaluate` line 4960-4964:
  - active_damageとtarget_damageを比較
- `TargetResolver.score_target` line 4248:
  - 自分対象選択でも最大打点を評価

重複経路:

```text
AttackAction.evaluate
→ attack.damage / effective_attack_damageで攻撃価値加点
→ GameSimulator.evaluate_after_action
→ BoardEvaluator
→ TempoEvaluatorで自分最大打点を再加点
```

### KO可能性

- `AttackAction.evaluate` line 4452:
  - `can_knock_out`
- `AttackAction.apply` line 4747-4748:
  - HP0なら `resolve_knockout`
- `BoardState.can_take_prize` line 2482
- `MasterEvaluator.evaluate_target_priority` line 3929
- `BossOrdersStrategy` line 3014以降

重複経路:

```text
AttackAction.evaluate
→ can_knock_outでサイド/勝利価値を加点
→ GameSimulator.applyでKOして仮想サイド更新
→ BoardEvaluator
→ PrizeRaceEvaluatorでサイド差を再評価
```

### サイド価値

- `PrizeRaceEvaluator.evaluate` line 3784-3785
- `BoardEvaluator.evaluate` line 3823-3826
- `calculate_prize_value` line 1969
- `AttackAction.evaluate` line 4468 / 4490-4495
- `MasterEvaluator.evaluate_target_priority` line 3929
- `BossOrdersStrategy` line 3014以降

同じKOがAction内と仮想盤面評価で二重に加点される。

### 逃げるコスト

- `effective_retreat_cost` line 730-737
- `retreat_would_spend_water` line 903-904
- `RetreatAction.evaluate` line 4952以降
- `EndAction.evaluate` line 5283-5284

`RetreatAction.apply` line 5151-5160 は逃げエネルギーを消費しないため、評価と仮想盤面が一致しない。

### ベンチアタッカー

- `FutureBoardEvaluator.evaluate` line 3809:
  - ベンチの `can_attack_next_turn` を加点
- `RetreatAction._best_retreat_target` line 4928以降
- `_choose_replacement_index` line 2873-2906

ベンチアタッカー価値が、未来評価、退却先、自動後続選択で重複する。

### 次ターン攻撃可能性

- `can_attack_next_turn` line 1643
- `calculate_max_damage(next_turn=True)` line 1633
- `FutureBoardEvaluator.evaluate` line 3809
- `RetreatAction` / `EvolveAction` で多数使用

ただし合法Option集合は再生成しないため、「次ターン攻撃可能性」は静的推定。

### エネルギー進捗

- `FutureBoardEvaluator.evaluate` line 3806 / 3810
- `high_impact_attack_progress` line 1001
- `AttachEnergyAction.evaluate` line 5427-5436 / 5498-5508
- `BoardState.attack_energy_shortfall` line 946

エネルギー進捗はAttachEnergyAction内で直接評価し、さらにGameSimulator後のFutureBoardEvaluatorでも再評価される。

### 残りHP

- `FutureBoardEvaluator.evaluate` line 3807-3808
- `current_hp` line 549
- `AttackAction.evaluate`
- `RetreatAction.evaluate`
- `DamageAction.apply`

攻撃・回復・退却判断の各所で重複する。

### 特性価値

- `AbilityAction.evaluate` line 5304-5305 は0点固定
- 特性価値は実質Strategyや個別カード評価に散在
- GameSimulator/BoardEvaluatorでは特性使用済みや自動特性を扱わない

### 勝敗

- `BoardEvaluator.evaluate` line 3823-3826:
  - サイド0で±1,000,000
- `AttackAction.evaluate` line 4468:
  - `wins_now`
- `can_win_by_active_attack` line 2523
- `can_win_by_killing_bench_pokemon` 周辺

即勝利は複数経路で評価される。

## 5. 呼び出し箇所

| 呼び出し元 | 行 | 対象行動 | 係数 | 合成方法 | 削除で失われる判断 | 重複 |
|---|---:|---|---:|---|---|---|
| `AttackAction.evaluate` | 4738 | 攻撃 | 0.05 | `action_score +=` | 攻撃後HP/KO/サイド差の静的評価 | 攻撃ダメージ、KO、サイド価値と重複 |
| `EvolveAction.evaluate` | 4878 | 進化 | 0.05 | `action_score = 2500 + ...` | 進化後カードIDでの静的盤面評価 | 進化先価値、エネ進捗と重複 |
| `RetreatAction.evaluate` | 5149 | 退却 | 0.05 | `action_score +=` | 交代後の静的盤面評価 | 退却先評価と重複 |
| `PlayCardAction.evaluate` | 5239 | カード使用 | 0.03 | `action_score = 500 + ...` | スタジアム/ボスだけ静的評価 | カードStrategyと重複 |
| `AttachEnergyAction.evaluate` | 5353 | 非エネルギー/道具系 | 0.03 | `action_score +=` | ほぼなし | 道具評価と重複 |
| `AttachEnergyAction.evaluate` | 5437 | 水エネルギー | 0.05 | `action_score +=` | 仮想水エネ追加後の攻撃可否 | エネ進捗評価と重複 |
| `AttachEnergyAction.evaluate` | 5512 | その他エネルギー | 0.05 | `action_score +=` | 仮想エネ追加後の攻撃可否 | エネ進捗評価と重複 |

Simulator削除で失われる主なもの:

- 攻撃後の相手バトル場HP減少をBoardEvaluatorへ見せること
- KO後の仮想サイド差
- 仮想エネルギー追加後の攻撃可能性
- ボス/退却/スタジアム後の静的盤面評価

ただし、いずれも個別評価と重複しており、合法Option再生成や相手応答は失われない。もともと存在しないため。

## 6. 本当に再現できている行動

| 処理 | 分類 | 根拠 |
|---|---|---|
| 単純ダメージ | 一部のみ再現 | `AttackAction.apply` line 4746、`DamageAction.apply` line 5672 |
| KO | 一部のみ再現 | `resolve_knockout` line 2908。単一対象のみ |
| サイド取得 | 一部のみ再現 | `take_prizes` line 2867。特殊処理は弱い |
| ボスによる交代 | 正確に近い | `PlayCardAction.apply` line 5245-5251。ただし手札/サポ使用は未反映 |
| 逃げる | 一部のみ再現 | `RetreatAction.apply` line 5151。エネ消費なし |
| エネルギー付与 | 一部のみ再現 | `AttachEnergyAction.apply` line 5514。基本エネだけ |
| エネルギートラッシュ | 一部のみ再現 | `DiscardEnergyAction.apply` line 5655。serialを除外するだけ |
| 進化 | ほぼ再現できていない | `EvolveAction.apply` line 4920。カードIDだけ |
| スタジアム | 一部のみ再現 | `PlayCardAction.apply` line 5242。ID変更だけ |
| ツール | ほぼ再現できていない | Hero Cape等の装着applyなし |
| ダメカン移動 | ほぼ再現できていない | `DamageAction.apply` は単純HP減少のみ |
| サーチ | 名前だけで実質未実装 | `PlayCardAction.apply` line 5252 コメント通り非公開山札/手札効果は未反映 |
| 手札操作 | 名前だけで実質未実装 | 手札配列を更新しない |
| 特性 | 名前だけで実質未実装 | `AbilityAction.evaluate` は0、applyなし |
| 特殊状態 | 名前だけで実質未実装 | applyなし |
| ワザの追加効果 | ほぼ再現できていない | ベンチダメージ、眠り、サーチ等なし |

## 7. 誤推定

### 逃げられない/逃げコストを払えないのに交代後盤面として評価する

- 発生元:
  - `RetreatAction.apply` line 5151-5160
- 理由:
  - 逃げエネルギーを消費しない。
  - 特殊状態や逃げ不可状態を見ない。

### KO後の後続ポケモンを勝手に選ぶ

- 発生元:
  - `_choose_replacement_index` line 2873-2906
  - `resolve_knockout` line 2908-2933
- 理由:
  - 正式にはプレイヤー選択だが、仮想盤面では最大火力等で自動選択。

### 進化後HPが不正確

- 発生元:
  - `evolve_target` line 2860-2865
- 理由:
  - カードIDだけ変更。
  - line 2863で最大HP/ダメージ維持不正確をコメントしている。

### サーチカードを使った未来が盤面に反映されない

- 発生元:
  - `PlayCardAction.apply` line 5252
- 理由:
  - ポフィン、ハイパーボール、ポケギア、ポケパッド、メガシグナル、夜のタンカ等は手札/山札/場へ反映しない。

### ミツルの思いやり等の回復が反映されない

- 発生元:
  - `PlayCardAction.apply` line 5241-5253
- 理由:
  - 回復、エネルギー手札戻し、サポート使用済みを反映しない。

### Tool ScrapperやHero Capeが反映されない

- 発生元:
  - `PlayCardAction.apply` line 5241-5253
  - `AttachEnergyAction.apply` line 5514-5522
- 理由:
  - ツール除去/装着の仮想状態を持たない。

### イグニッションエネルギーの未来がズレる

- 発生元:
  - `AttachEnergyAction.apply` line 5518-5519
- 理由:
  - イグニッションは仮想盤面に追加しない。
  - 評価ではイグニッションによる本命技起動を見る箇所があるが、BoardEvaluatorには反映されない。

### 同一ターンに不可能な行動を組み合わせた評価になる

- 発生元:
  - `GameSimulator.evaluate_after_action` line 4287-4290
  - `BoardEvaluator` line 3819-3827
- 理由:
  - 1行動適用後の静的盤面を「次ターン攻撃可能性」等で評価するが、サポート使用済み、エネルギー手貼り済み、合法Option再生成を扱わない。

### 相手がベンチアタッカーで攻撃できるように見える

- 発生元:
  - `FutureBoardEvaluator.evaluate` line 3809
  - `calculate_max_damage(next_turn=True)` line 1633
- 理由:
  - 逃げ、入れ替え札、特殊状態、エネルギー付与可否を完全には扱わない。

### 相手の進化・手札・サポート・入れ替えを静的評価に混ぜる

- 発生元:
  - GameSimulator本体ではなく、BoardStateの対面評価や `calculate_max_damage(next_turn=True)` 系
- 理由:
  - GameSimulatorは合法Optionを再生成しないため、実際に相手が実行可能かは検証しない。

## 8. 削除範囲

### 完全削除可能

GameSimulatorのためだけに存在するもの。

- `GameSimulator` class line 4283-4290
- `GameSimulator.evaluate_after_action` 呼び出し全箇所 line 4738 / 4878 / 5149 / 5239 / 5353 / 5437 / 5512
- `GameAction.apply` line 4312-4313
- `AttackAction.apply` line 4740-4749
- `EvolveAction.apply` line 4920-4924
- `RetreatAction.apply` line 5151-5160
- `PlayCardAction.apply` line 5241-5253
- `AttachEnergyAction.apply` line 5514-5522
- `DiscardEnergyAction.apply` line 5655-5657
- `DamageAction.apply` line 5669-5676
- `_hp` 仮想HP line 327
- `_card_ids` 仮想カードID line 328
- `_extra_energy` 仮想エネルギー line 329
- `_spent_energy_serials` 仮想消費エネルギー line 330
- `_my_active` / `_opp_active` / `_my_bench_slots` / `_opp_bench_slots` の仮想差し替え用途 line 317-320
- `_my_prizes` / `_opp_prizes` の仮想更新用途 line 321-322
- `_stadium_id` の仮想更新用途 line 323-325
- `switch_with_bench` line 2850-2858
- `evolve_target` line 2860-2865
- `take_prizes` line 2867-2871
- `_choose_replacement_index` line 2873-2906
- `resolve_knockout` line 2908-2933
- `add_virtual_energy` line 906-909
- `add_virtual_energy_card` line 911-914

### 別用途で残す

通常のルール処理、攻撃判定、カード選択にも必要。

- APIアクセスFacadeとしてのBoardState/BoardView思想
- `get_card_data` line 564
- `get_attack` line 567
- `get_attacks` line 572
- `attached_energy_cards` line 617
- `attached_energy_card_ids` line 626
- `count_energy` line 631
- `can_use_attack` line 919
- `attack_energy_shortfall` line 946
- `effective_attack_damage` line 1524
- `best_attack_damage` line 1615
- `calculate_max_damage` line 1633。ただし `next_turn=True` の扱いは要縮小
- `calculate_prize_value` line 1969
- `my_active_remaining_hp` line 1984
- `my_active_can_attack` line 2479
- `can_take_prize` line 2482
- `damage_target_value` line 2485
- `get_option_target` line 2826
- `option_points_to_me` line 2814

### 小さく作り直す

知識は必要だが、現行実装を移植すべきではないもの。

- `BoardEvaluator` line 3815-3827
- `PrizeRaceEvaluator` line 3780-3785
- `TempoEvaluator` line 3788-3798
- `FutureBoardEvaluator` line 3801-3812
- `high_impact_attack_progress` line 1001
- `calculate_max_damage(next_turn=True)` line 1633
- `RetreatAction._best_retreat_target` line 4928
- `selected_damage_amount` line 431
- `DamageAction.apply` の追加ダメージ仕様 line 5669-5676
- `Tool Scrapper` / `Hero Cape` 周辺のHP変化仕様

## 9. 一手先評価へ残せる仕様

現在の合法Optionを1回適用した直後の確定結果に限定して残せるもの。

### 残してよい

- 攻撃ダメージ:
  - `effective_attack_damage` line 1524
  - ただし追加効果は別仕様として限定実装
- ダメージ無効判定:
  - `crustle_blocks_ex_attack` 等の知識は残せるが、現行コードは移植せず再定義
- KO:
  - `current_hp - damage <= 0` の即時判定
- サイド取得:
  - `calculate_prize_value` line 1969 の仕様は救出可
- ボスによる交代:
  - `PlayCardAction.apply` line 5245-5251 の仕様だけ救出可
- 逃げる際のエネルギー消費:
  - 現行applyは消費しないため移植不可
  - `effective_retreat_cost` line 730 の仕様を小さく再利用
- エネルギー付与後の攻撃可否:
  - `can_use_attack` line 919
  - `attack_energy_shortfall` line 946
- ダメカン配置・移動後のKO:
  - `DamageAction.apply` line 5669-5676 の単純HP減少だけ参考
  - マシマシラ等は新規仕様化
- Tool Scrapper後のHP変化:
  - `hp_after_tool_scrapper` line 675
  - 現行applyにはないため新規実装が必要
- 即時勝利判定:
  - `my_remaining_prizes == 0` line 3823
  - `can_win_by_active_attack` line 2523

### 残してはいけない

- 相手の非公開手札の推測
- 次のドローの推測
- 相手の進化推測
- 相手のサポート使用推測
- 好きなエネルギーを付けられる前提
- 自分のさらに次ターンの最大応答
- 完全な2手先を装う静的スコア
- `_choose_replacement_index` の自動後続選択
- `calculate_max_damage(next_turn=True)` を相手応答として使うこと
- `FutureBoardEvaluator` の静的未来評価を探索結果として扱うこと

## 10. 最終結論

- 現行GameSimulatorの実質的な探索深度:
  - 自分の現在行動1手だけ。
  - 相手応答0手。
  - 自分次手0手。
- 本格的なゲームシミュレーターと呼べるか:
  - 呼べない。
  - `deepcopy -> action.apply -> 静的BoardEvaluator` であり、合法Option再生成も相手ターンもない。
- コード量に対して得られている価値:
  - 低い。
  - GameSimulator本体は4行だが、それを支える仮想盤面状態とapply群が肥大化している。
- 現行実装を移植すべきか:
  - 移植すべきではない。
  - とくに `action.apply` 群、仮想HP、仮想カードID、仮想エネルギー、KO後自動後続選択は移植禁止。
- 一手先評価へ救出すべき機能:
  - 単純攻撃ダメージ
  - KO/サイド取得
  - ボス交代
  - エネルギー付与後の攻撃可否
  - 逃げコスト支払い
  - ダメカン配置後KO
  - Tool Scrapper後HP
  - 即時勝利判定
- GameSimulator削除により削減できる周辺構造:
  - `GameSimulator`
  - 全Actionの `apply`
  - 仮想盤面差分 `_hp`, `_card_ids`, `_extra_energy`, `_spent_energy_serials`
  - 仮想入れ替え/KO/サイド/後続選択関数
  - `BoardEvaluator` への混合係数
- フルスクラッチ初版へ入れない方がよい理由:
  - 2手先を見ているように見えるが見ていない。
  - 退却、進化、サーチ、回復、ツール、特性、特殊状態の再現が不足。
  - 個別評価とBoardEvaluatorが同じ概念を重複評価し、点数衝突の原因になる。
  - 非合法な未来や不完全な未来を作り、行動選択を濁らせる。

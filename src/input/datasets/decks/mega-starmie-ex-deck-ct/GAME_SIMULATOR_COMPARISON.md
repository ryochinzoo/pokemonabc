# v7初版とbackup比較: GameSimulator由来構造

対象:

- フルスクラッチ初版: `main.py` 1344行
- バックアップ: `main.py.backup` 6249行

この文書はコードを変更せず、GameSimulator導入と、その後の補正で増えた構造を分類する。

## 0. 全体差分

`main.py` は以下の薄い構造になっている。

- `BoardView` `main.py:297`
- `Policy` `main.py:653`
- `choose_indices` `main.py:1318`
- `agent` `main.py:1336`
- `MATCHUP_PLANS` `main.py:133`
- `FORBIDDEN_PATTERNS` `main.py:205`

`main.py.backup` は以下の多層構造になっている。

- `BoardState` `main.py.backup:308`
- `CardStrategy` 群 `main.py.backup:3069`
- `PrizeRaceEvaluator` `main.py.backup:3780`
- `TempoEvaluator` `main.py.backup:3788`
- `FutureBoardEvaluator` `main.py.backup:3801`
- `BoardEvaluator` `main.py.backup:3815`
- `MasterEvaluator` `main.py.backup:3830`
- `SearchResolver` `main.py.backup:3934`
- `TargetResolver` `main.py.backup:4231`
- `GameSimulator` `main.py.backup:4283`
- `GameAction` 階層 `main.py.backup:4296`
- `SelectionResolver` `main.py.backup:5705`
- `DecisionGovernor` `main.py.backup:5824`
- `ActionFactory` `main.py.backup:6128`

結論として、backupは「カード知識」「行動評価」「仮想盤面」「後付け禁止・補正」が重なり、同じ判断が複数経路で加減点される。

## 1. 初版にはなく、GameSimulatorのために追加されたもの

### GameSimulator本体

- `GameSimulator` `main.py.backup:4283`
- `evaluate_after_action` `main.py.backup:4287`

実処理は `copy.deepcopy(board)` し、`action.apply(virtual_board)` を1回呼び、`BoardEvaluator(virtual_board).evaluate()` を返すだけ。

現行 `main.py` には実装なし。コメント上の方針として「No GameSimulator」としている。

### 仮想盤面状態

`BoardState` 内でAPI実体とは別に保持する仮想状態。

- `_my_active` `main.py.backup:317`
- `_opp_active` `main.py.backup:318`
- `_my_bench_slots` `main.py.backup:319`
- `_opp_bench_slots` `main.py.backup:320`
- `_my_prizes` `main.py.backup:321`
- `_opp_prizes` `main.py.backup:322`
- `_stadium_id` `main.py.backup:323`
- `_hp` `main.py.backup:327`
- `_card_ids` `main.py.backup:328`
- `_extra_energy` `main.py.backup:329`
- `_spent_energy_serials` `main.py.backup:330`
- `_damage_counter_steps_used` `main.py.backup:331`
- `_remaining_damage_counter` `main.py.backup:332`
- `_healing_ceiling` `main.py.backup:333`

現行 `BoardView` は観測値の読み取り中心で、これらの仮想状態を持たない。

### 仮想盤面更新メソッド

- `discard_attached_energy` `main.py.backup:802`
- `add_virtual_energy` `main.py.backup:906`
- `add_virtual_energy_card` `main.py.backup:911`
- `switch_with_bench` `main.py.backup:2850`
- `evolve_target` `main.py.backup:2860`
- `take_prizes` `main.py.backup:2867`
- `_choose_replacement_index` `main.py.backup:2873`
- `resolve_knockout` `main.py.backup:2908`

これらはGameSimulatorの `apply()` が盤面を進めたように見せるための構造。現行初版にはない。

### apply系

- `GameAction.apply` `main.py.backup:4312`
- `AttackAction.apply` `main.py.backup:4740`
- `EvolveAction.apply` `main.py.backup:4920`
- `RetreatAction.apply` `main.py.backup:5151`
- `PlayCardAction.apply` `main.py.backup:5241`
- `AttachEnergyAction.apply` `main.py.backup:5514`
- `DiscardEnergyAction.apply` `main.py.backup:5655`
- `DamageAction.apply` `main.py.backup:5669`

現行初版は `Policy.score_*` で現在の合法Optionを採点するだけで、仮想盤面へ反映しない。

### Simulator係数

GameSimulatorの戻り値を行動スコアへ混ぜている箇所。

- `AttackAction.evaluate` `main.py.backup:4738` 係数 `0.05`
- `EvolveAction.evaluate` `main.py.backup:4878` 係数 `0.05`
- `RetreatAction.evaluate` `main.py.backup:5149` 係数 `0.05`
- `PlayCardAction.evaluate` `main.py.backup:5239` 係数 `0.03`
- `AttachEnergyAction.evaluate` `main.py.backup:5353` 係数 `0.03`
- `AttachEnergyAction.evaluate` `main.py.backup:5437` 係数 `0.05`
- `AttachEnergyAction.evaluate` `main.py.backup:5512` 係数 `0.05`

## 2. GameSimulatorとは無関係に追加されたカード・対面知識

以下はGameSimulatorそのものではなく、カード知識・対面知識として追加されたもの。

### Strategy群

- `BossOrdersStrategy` `main.py.backup:3090`
- `SurfingBeachStrategy` `main.py.backup:3139`
- `ShayminStrategy` `main.py.backup:3159`
- `CinderaceStrategy` `main.py.backup:3198`
- `DarknessEnergyStrategy` `main.py.backup:3228`
- `WaterEnergyStrategy` `main.py.backup:3313`
- `IgnitionEnergyStrategy` `main.py.backup:3318`
- `StaryuStrategy` `main.py.backup:3405`
- `MegaStarmieStrategy` `main.py.backup:3420`
- `SnoruntStrategy` `main.py.backup:3435`
- `YveltalStrategy` `main.py.backup:3447`
- `EnergySwitchStrategy` `main.py.backup:3475`
- `ToolScrapperStrategy` `main.py.backup:3486`
- `PokePadStrategy` `main.py.backup:3509`
- `PokegearStrategy` `main.py.backup:3526`
- `PofinStrategy` `main.py.backup:3547`
- `TankerStrategy` `main.py.backup:3564`
- `HyperballStrategy` `main.py.backup:3585`
- `BallonStrategy` `main.py.backup:3644`
- `HeroCapeStrategy` `main.py.backup:3654`
- `MegaSignalStrategy` `main.py.backup:3680`
- `WallyCompassionStrategy` `main.py.backup:3691`
- `SalvatoreStrategy` `main.py.backup:3696`
- `LillieDeterminationStrategy` `main.py.backup:3709`
- `ToukoStrategy` `main.py.backup:3745`
- `AkamatsuStrategy` `main.py.backup:3759`

これらはGameSimulatorなしでも知識としては使える。ただし、Strategyクラス群として移植すると、現行初版の単一Policy設計を壊す。

### 現行初版に既にある知識

- 対面プラン表 `MATCHUP_PLANS` `main.py:133`
- 無効化・禁止知識 `FORBIDDEN_PATTERNS` `main.py:205`
- 相手プロフィール判定 `BoardView.opponent_profile` `main.py:570`
- 攻撃評価 `Policy.score_attack` `main.py:730`
- プレイ評価 `Policy.score_play` `main.py:840`
- サーチ選択評価 `Policy.score_card_selection` `main.py:1066`
- 捨て札評価 `Policy.score_discard` `main.py:1231`

## 3. 初版のPolicyだけへ移植可能な知識

移植する場合は、旧クラスを移植せず、`Policy` 内の単純な知識として移す。

### 移植可能

- ボスの司令の対象優先  
  旧: `BossOrdersStrategy` `main.py.backup:3090`、`MasterEvaluator.evaluate_target_priority` `main.py.backup:3886`  
  新: `Policy.score_boss` `main.py:928`、`Policy.score_target_or_card` `main.py:1151`

- サーチ対象優先  
  旧: `SearchResolver` `main.py.backup:3934`  
  新: `Policy.score_card_selection` `main.py:1066`

- 対象選択優先  
  旧: `TargetResolver` `main.py.backup:4231`  
  新: `Policy.score_target_or_card` `main.py:1151`

- トラッシュ保護  
  旧: `evaluate_trash_cost_priority` `main.py.backup:2954`、`MasterEvaluator.evaluate_trash_target` `main.py.backup:3877`  
  新: `Policy.score_discard` `main.py:1231`

- エネルギー付与先の優先  
  旧: `WaterEnergyStrategy` `main.py.backup:3313`、`DarknessEnergyStrategy` `main.py.backup:3228`、`IgnitionEnergyStrategy` `main.py.backup:3318`  
  新: `Policy.score_attach` `main.py:963`、`Policy.score_water_attach` `main.py:985`、`Policy.score_dark_attach` `main.py:1002`

- セイジ、リーリエ、ゼイユ、タンカ、ハイボ、ポフィンなどの使用価値  
  旧: 各Strategy `main.py.backup:3547` から `main.py.backup:3745`  
  新: `Policy.score_play` `main.py:840`、`Policy.score_card_selection` `main.py:1066`

### 移植時の制限

`forbidden` と `protected/last_resort` を分けること。

- 完全除外: 攻撃Optionがある攻撃フェーズでのEND、確定無効攻撃、目的のないエネルギー0メガ退却
- 強い減点止まり: 水エネ、主軸ポケモン、Tool Scrapper、エネルギー付き主軸の退却

## 4. 一手先評価として後付けする価値がある処理

GameSimulator全体は移植しない。一手先の確定結果だけなら価値がある。

### 残す価値あり

- 攻撃ダメージ、KO、サイド取得  
  旧: `AttackAction.apply` `main.py.backup:4740`、`resolve_knockout` `main.py.backup:2908`、`take_prizes` `main.py.backup:2867`  
  新候補: `Policy.score_attack` `main.py:730` の補助として純関数化

- ボスによる即時交代と次の攻撃対象  
  旧: `PlayCardAction.apply` `main.py.backup:5241`  
  新候補: `Policy.score_boss` `main.py:928` の補助

- エネルギー付与後の攻撃可否  
  旧: `AttachEnergyAction.apply` `main.py.backup:5514`、`can_use_attack` `main.py.backup:919`、`attack_energy_shortfall` `main.py.backup:946`  
  新候補: `Policy.score_attach` `main.py:963`

- ダメカン配置・移動後のKO  
  旧: `DamageAction.apply` `main.py.backup:5669`  
  新候補: `Policy.score_damage_target` `main.py:1187`

- Tool Scrapper後のHP変化  
  旧: `hp_after_tool_scrapper` `main.py.backup:675`、`tool_scrapper_target_value` `main.py.backup:683`  
  新候補: `Policy.score_target_or_card` `main.py:1151`

- 公開情報だけの次ターン致死判定  
  新: `BoardView.public_lethal_next_turn` `main.py:562`

### 残さない

- 相手の非公開手札推測
- 次ドロー推測
- 相手の進化推測
- 相手サポート使用推測
- 好きなエネルギーを貼れる前提
- 自分のさらに次ターン最大応答
- 完全な2手先を装う静的スコア

## 5. 現行GameSimulatorと一緒に削除すべき処理

### 完全削除候補

- `GameSimulator` `main.py.backup:4283`
- `BoardEvaluator` `main.py.backup:3815`
- `PrizeRaceEvaluator` `main.py.backup:3780`
- `TempoEvaluator` `main.py.backup:3788`
- `FutureBoardEvaluator` `main.py.backup:3801`
- `GameAction.apply` `main.py.backup:4312`
- 各Actionの `apply()` `main.py.backup:4740`、`4920`、`5151`、`5241`、`5514`、`5655`、`5669`
- GameSimulator係数混入箇所 `main.py.backup:4738`、`4878`、`5149`、`5239`、`5353`、`5437`、`5512`
- 仮想盤面状態 `_my_active` から `_healing_ceiling` まで `main.py.backup:317`
- 仮想盤面更新メソッド `main.py.backup:802`、`906`、`911`、`2850`、`2860`、`2867`、`2873`、`2908`

### 削除寄り

- `DecisionGovernor` `main.py.backup:5824`

これはGameSimulator本体ではないが、多層評価で発生した矛盾を最後に補正するための後付け層になっている。現行初版では `Policy` の採点前提・禁止前提へ統合すべきで、独立クラスとして戻すべきではない。

- `SearchResolver` `main.py.backup:3934`
- `TargetResolver` `main.py.backup:4231`
- `SelectionResolver` `main.py.backup:5705`
- `ActionFactory` `main.py.backup:6128`

これらはAction階層を使う設計に依存している。現行初版では `Policy.score_card_selection` `main.py:1066`、`Policy.score_target_or_card` `main.py:1151`、`choose_indices` `main.py:1318` へ集約する。

## 6. 初版の設計思想を壊した変更

### 二重評価

backupでは、同じ概念が複数箇所で評価される。

例:

```text
AttackAction.evaluate main.py.backup:4354
→ GameSimulator.evaluate_after_action main.py.backup:4287
→ BoardEvaluator.evaluate main.py.backup:3818
→ TempoEvaluator / FutureBoardEvaluator main.py.backup:3788 / 3801
→ DecisionGovernor.apply main.py.backup:5830
```

現行初版は `Policy.score_attack` `main.py:730` のように、選択フェーズごとの採点を1箇所へ寄せている。

### 仮想盤面の過信

backupの `RetreatAction.apply` `main.py.backup:5151` はベンチ交代だけを反映し、逃げエネルギー消費を反映しない。  
`EvolveAction.apply` `main.py.backup:4920` はカードIDだけ変更し、進化後HPなどを正確に再現しない。  
`PlayCardAction.apply` `main.py.backup:5241` はスタジアムとボス以外のカード効果をほぼ反映しない。

この状態で `BoardEvaluator` に渡すため、実際の未来ではなく、部分的に書き換えた現在盤面を高精度な未来のように扱っている。

### 後付け補正の肥大化

`DecisionGovernor` `main.py.backup:5824` は、行動評価後に「これはやめろ」「これは上げろ」をさらに重ねる。  
これは初版の「禁止、保護、優先をPolicyで明示する」思想と相性が悪い。

### 2手先思想の形骸化

backupの `GameSimulator.evaluate_after_action` `main.py.backup:4287` は、実際には現在の行動を1回だけ `apply()` する。  
相手の合法Option集合再生成、自分の次行動、相手手札、相手進化、相手サポート、相手入れ替えは適用していない。

つまり「2手先を見る」構造ではなく、「現在行動後の静的盤面をBoardEvaluatorで再採点する」構造になっている。

## 7. 初版へ最小限追加する場合の必要機能

追加するなら、旧GameSimulatorではなく、現在の `Policy` へ小さな一手先評価を足す。

### 必要最小限

- 攻撃Optionの即時結果  
  参照元: `Policy.score_attack` `main.py:730`

- 攻撃フェーズで有効攻撃があるときEND禁止  
  参照元: `BoardView.is_attack_choice_phase` `main.py:526`、`Policy.score_end` `main.py:783`

- 確定無効攻撃の除外  
  参照元: `FORBIDDEN_PATTERNS` `main.py:205`

- 公開情報だけの次ターン致死判定  
  参照元: `BoardView.public_lethal_next_turn` `main.py:562`

- エネルギー付与後の攻撃到達  
  参照元: `Policy.score_attach` `main.py:963`

- サーチ先の主軸完成優先  
  参照元: `Policy.score_card_selection` `main.py:1066`

- 捨て札の protected / last_resort 分離  
  参照元: `Policy.score_discard` `main.py:1231`

- 目的のない退却と横滑りの禁止  
  参照元: `Policy.score_retreat` `main.py:795`、`Policy.score_switch_target` `main.py:1175`

### 入れないもの

- `GameSimulator`
- `BoardEvaluator`
- `TempoEvaluator`
- `FutureBoardEvaluator`
- `GameAction` 階層
- `ActionFactory`
- `DecisionGovernor`
- 仮想盤面状態
- 非公開情報込みの2手先風スコア

## 最終結論

backupで増えた大きな構造は、GameSimulatorのための仮想盤面、Action.apply、BoardEvaluator、そしてそれらの矛盾を押さえるDecisionGovernorである。

現行初版へ救う価値があるのは、カード知識と対面知識、そして「現在の合法Optionを1回選んだ直後に確定する結果」だけ。

GameSimulator本体、仮想BoardState、Action階層、BoardEvaluator群は移植しない方がよい。これらはコード量を増やす一方で、相手ターンや自分の次行動を実際には展開しておらず、初版の単純な `BoardView + Policy` 設計を壊す。

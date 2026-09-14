# ImmediateOutcomeEvaluator 詳細設計

対象: `main.py` フルスクラッチ初版 v7  
目的: GameSimulatorを復活させず、現在提示されている合法Optionを1つ選んだ直後の確定結果だけを公開情報から返す。

コードはこの段階では変更しない。

## 1. 現状分析

### 現行構造

現行 `main.py` は以下の構造。

- `BoardView` `main.py:297`
- `Policy` `main.py:653`
- `choose_indices` `main.py:1318`
- `agent` `main.py:1336`
- 対面知識 `MATCHUP_PLANS` `main.py:133`
- hard guard知識 `FORBIDDEN_PATTERNS` `main.py:205`

旧 `GameSimulator`、`copy.deepcopy`、`Action.apply`、`BoardEvaluator`、`DecisionGovernor` は存在しない。この方針は維持する。

### 再利用できるBoardViewメソッド

- `BoardView.option_card` `main.py:330`  
  OptionからカードIDを取る。

- `BoardView.option_target` `main.py:365`  
  Optionから対象ポケモンを取る。

- `BoardView.iter_options` `main.py:371`  
  現在提示されている合法Optionを走査する。

- `BoardView.data` `main.py:324`  
  `CardData` 参照。

- `BoardView.attack` `main.py:327`  
  `Attack` 参照。

- `BoardView.energies` `main.py:450`  
  対象ポケモンに付いているエネルギーカードID列を取る。

- `BoardView.energy_tokens` `main.py:461`  
  エネルギーカードIDを攻撃支払い用トークンへ変換する。

- `BoardView.can_pay_attack` `main.py:474`  
  現在のエネルギーでワザを使えるか判定する。

- `BoardView.attack_damage` `main.py:504`  
  公開情報で計算できる特殊火力を処理する。

- `BoardView.legal_attack_options` `main.py:513`  
  現在提示されている攻撃OptionのAttackを取る。

- `BoardView.is_attack_choice_phase` `main.py:526`  
  攻撃選択フェーズ判定。

- `BoardView.prize_value` `main.py:538`  
  KO時のサイド枚数判定。

- `BoardView.public_lethal_next_turn` `main.py:562`  
  公開情報だけの次ターン致死判定。

- `BoardView.opponent_profile` `main.py:570`  
  対面プラン判定。

- `BoardView.plan_*` `main.py:583` から `main.py:599`  
  対面ごとの圧力対象、ボス対象、本命攻撃を返す。

### 修正が必要なBoardViewメソッド

- `BoardView.can_pay_attack` `main.py:474`  
  現状は typed energy 要求に対して `EnergyType.COLORLESS` を代替として許している `main.py:487`。  
  公式ルールとして無色エネルギーは水や悪の代替にはならない。ImmediateOutcomeでエネルギー到達を扱うなら、ここは正確化が必要。

- `BoardView.energy_tokens` `main.py:461`  
  イグニッションエネルギーを無色3個として扱う `main.py:468`。これはNebula Beamのような無色要求には有効。  
  ただし「攻撃しないと番の終わりにトラッシュされる」制約はこの関数では扱わず、Outcomeの `reasons` とPolicy接続で扱う。

- `BoardView.attack_damage` `main.py:504`  
  `RESENTFUL_REFRAIN`、`CRUEL_ARROW` 以外は `attack.damage` のみ `main.py:507` から `main.py:511`。  
  効果無視、ベンチ攻撃、追加効果、眠りなどは未表現。初回ImmediateOutcomeでは、対象が相手バトル場である攻撃のダメージと壁突破判定に限定する。

- `BoardView.my_prizes_left` `main.py:535`  
  `card is not None or True` により常にリスト長を返す `main.py:536`。  
  非公開サイドは `None` で表現されるため、残り枚数としては実質 `len(self.me.prize)` でよいが、意図が読みづらい。ImmediateOutcomeでは別の純関数 `prizes_left(player_state)` を使う方が安全。

- `BoardView.active_can_ko` `main.py:548`  
  壁による攻撃無効を考慮していない。ImmediateOutcome導入後は、KO判定はOutcome側の責務へ移す。

### 二重評価になっている既存箇所

- `Policy.score_attack` `main.py:730`  
  ダメージ、KO、サイド、本命技、壁対面補正、イグニッション消費価値まで直接加点している。

- `Policy.score_boss` `main.py:928`  
  ボス後のKO可能性を `BoardView.active_can_ko` で直接加点している `main.py:935`。壁無効や効果無視を考慮しない。

- `Policy.score_attach` `main.py:963`  
  イグニッション、基本水、基本悪の価値を直接評価している。付与後に新しく使えるワザを構造化していない。

- `Policy.score_retreat` `main.py:795`  
  退却コスト、失うエネルギー、交代先の攻撃可否がOutcomeとして分離されていない。

- `Policy.score_switch_target` `main.py:1175`  
  交代先の火力だけで評価し、退却やスタジアム効果との責務境界が曖昧。

- `Policy.score_damage_target` `main.py:1187`  
  ダメカン・ダメージ選択のKO圏内判定を簡易に持つ。将来Outcomeへ移す候補。

## 2. 責務分担

### ImmediateOutcomeEvaluatorの責務

現在の合法Optionを1つ選んだ直後に、公開情報だけで確定できる結果を返す。

担当する判断:

- 攻撃の実効ダメージ
- 攻撃が壁で確定無効か
- 効果無視ワザで壁を突破できるか
- KOするか
- 取るサイド枚数
- 即時勝利か
- エネルギー付与後に新しく使えるワザ
- イグニッション付与後に即時攻撃が成立するか
- ボスで呼ぶ相手ベンチ
- ボス後に現在アタッカーがKOできるか
- Tool Scrapperでヒーローマントを剥がした後にKO圏内か
- 退却に必要な実効コスト
- 退却で失う可能性のある重要エネルギー数
- 交代先が攻撃可能か
- エネルギー0メガを前に出す事故か

担当しない判断:

- 相手の非公開手札
- 次ドロー
- 相手の次ターン進化
- 相手のサポート使用
- 好きなエネルギーを次ターン貼れる前提
- 自分のさらに次ターン最大応答
- 合計スコア算出

### Policyに残す責務

- 対面プラン適用
- hard guard
- protected / last_resort 判定
- 手札を使うべきか、攻撃へ行くべきかの優先順
- サーチ先、トラッシュ対象、対象選択の通常優先度
- 小さなタイブレーク
- Outcomeを使った意思決定の順序制御

PolicyはOutcomeを固定係数で混ぜない。  
`score += outcome_value * 0.05` のような合成は禁止。

## 3. データ構造

### ImmediateOutcome

```python
@dataclass(frozen=True)
class ImmediateOutcome:
    legal: bool
    blocked: bool
    damage: int
    knockout: bool
    prizes_taken: int
    wins_game: bool
    enables_attack: bool
    enabled_attack_ids: tuple[int, ...]
    retreat_energy_cost: int
    important_energy_loss: int
    removes_wall: bool
    removes_tool: bool
    target_id: int | None
    target_serial: int | None
    reasons: tuple[str, ...]
```

### フィールド意味

- `legal`  
  現在のOptionとして合法。基本的には提示されたOptionなので `True`。対象欠落など解析不能なら `False`。

- `blocked`  
  公開情報で効果が確定無効。例: EXワザ無効壁へ、効果無視でないEX攻撃。

- `damage`  
  公開情報で確定する相手バトル場への実効ダメージ。無効なら0。

- `knockout`  
  `damage >= hp_left(target)`。

- `prizes_taken`  
  KO時に取れるサイド。`BoardView.prize_value` `main.py:538` 相当。

- `wins_game`  
  `prizes_taken >= prizes_left`。

- `enables_attack`  
  エネルギー付与などで、付与前は使えなかったワザが付与後に使える。

- `enabled_attack_ids`  
  新しく使えるようになった攻撃ID。

- `retreat_energy_cost`  
  退却Optionで必要なエネルギー数。正式なエネルギー選択は行わない。

- `important_energy_loss`  
  退却時に失う可能性がある水、イグニッション、主軸に必要なエネルギー数。

- `removes_wall`  
  ボスやTool Scrapper等で、現在の壁状況を回避・解除できる。

- `removes_tool`  
  Tool Scrapperで道具を剥がす。

- `target_id` / `target_serial`  
  解析対象のポケモンIDとserial。盤面を書き換えず、対象識別だけ保持する。

- `reasons`  
  `("wins_game", "ko", "blocked_ex_wall", "enables_nebula_beam")` のような説明用タグ。

### Evaluator構造

```python
class ImmediateOutcomeEvaluator:
    def __init__(self, board: BoardView):
        self.b = board

    def evaluate(self, option: Any) -> ImmediateOutcome:
        ...
```

スコアは返さない。  
`BoardView` を変更しない。  
`Pokemon` も変更しない。  
`copy.deepcopy` は使わない。

## 4. 各Option種別の判定仕様

### 4.1 攻撃Option

対象:

- `OptionType.ATTACK`
- または `option.attackId is not None`

参照:

- `BoardView.attack` `main.py:327`
- `BoardView.attack_damage` `main.py:504`
- `BoardView.opp_active` `main.py:313`
- `hp_left` `main.py:286`
- `BoardView.prize_value` `main.py:538`

判定:

1. `attack = board.attack(option.attackId)`
2. `attacker = board.active`
3. `target = board.opp_active`
4. 攻撃ID、攻撃者、対象が欠けるなら `legal=False`
5. `is_blocked_attack(attacker, attack, target)` を判定
6. blockedなら `damage=0`, `blocked=True`
7. blockedでないなら `damage = effective_attack_damage(attacker, attack, target, board)`
8. `knockout = damage >= hp_left(target)`
9. `prizes_taken = prize_value(target)` if KO else 0
10. `wins_game = prizes_taken >= prizes_left(board.me)`

壁判定:

- 対象IDが `EX_ATTACK_WALLS` `main.py:93`
- 攻撃者がEXまたはMegaEX
- 攻撃が効果無視ワザではない
- 初回の効果無視ワザは `NEBULA_BEAM` `main.py:80`

注意:

- ベンチ攻撃、複数対象、眠り等は初回Outcomeでは `reasons` に記録するだけ。
- 相手の特性が非公開なら扱わない。場に見えているポケモンIDだけを見る。

### 4.2 エネルギー付与Option

対象:

- `OptionType.ATTACH`

参照:

- `BoardView.option_card` `main.py:330`
- `BoardView.option_target` `main.py:365`
- `BoardView.energy_tokens` `main.py:461`
- `BoardView.can_pay_attack` `main.py:474`
- `BoardView.data` `main.py:324`
- `BoardView.attack` `main.py:327`

判定:

1. 付与カードIDと対象を取る。
2. 対象の現在エネルギートークンを読む。
3. `with_extra_energy_tokens(tokens, cid)` で一時トークンを作る。
4. 対象ポケモンの全ワザを取得する。
5. 付与前に使えるワザID集合を計算。
6. 付与後に使えるワザID集合を計算。
7. 差分を `enabled_attack_ids` に入れる。
8. 差分が空でなければ `enables_attack=True`。
9. `NEBULA_BEAM` が新規到達なら `reasons += ("enables_nebula_beam",)`。
10. `IGNITION_ENERGY` が付与され、対象がactiveで、付与後に有効攻撃があるなら `reasons += ("ignition_immediate_attack",)`。

水、悪、イグニッションの扱い:

- 水エネルギー: `EnergyType.WATER`
- 悪エネルギー: `EnergyType.DARKNESS`
- イグニッション: `EnergyType.COLORLESS` 3個

重要:

- BoardViewやPokemonへ実際に追加しない。
- イグニッションのターン終了トラッシュは盤面に反映しない。
- 「次ターン貼れば」は扱わない。

### 4.3 ボスの司令

対象:

- `OptionType.PLAY` でカードIDが `BEFEHL_VON_BOSS` `main.py:66`
- または選択フェーズで effect/contextCard がボスの司令

参照:

- `BoardView.opp_bench` `main.py:315`
- `BoardView.active` `main.py:312`
- `BoardView.legal_attack_options` `main.py:513`
- `BoardView.attack_damage` `main.py:504`
- `BoardView.prize_value` `main.py:538`
- `BoardView.plan_boss_targets` `main.py:592`
- `Policy.target_value` `main.py:1256`

判定:

1. Play段階では「このカードを使う価値」として、相手ベンチ全体を評価する。
2. 対象選択段階では、提示された対象1体を評価する。
3. 現在activeが、呼び出した対象を現在合法攻撃でKOできるか判定。
4. KOできるなら `knockout=True`, `prizes_taken` を返す。
5. 対象が `EX_ATTACK_WALLS` や `CRUSTLE_LINE` の壁本体なら `removes_wall=True`。
6. 対象が `plan_boss_targets` に入るなら `reasons += ("breaks_engine",)`。

やらないこと:

- 相手ベンチ配列を変更しない。
- サポート使用済み状態を変更しない。
- ボス後の攻撃Option再生成はしない。現在activeの既知ワザと現在エネルギーだけで攻撃可否を計算する。

### 4.4 Tool Scrapper

対象:

- `TOOL_SCRAPPER` `main.py:63`
- Tool Scrapperの対象選択フェーズ

参照:

- 相手ポケモンの `tools`
- `hp_left` `main.py:286`
- `damage_on` `main.py:280`
- `BoardView.legal_attack_options` `main.py:513`
- `BoardView.attack_damage` `main.py:504`

判定:

1. 対象ポケモンまたは対象道具を取る。
2. 対象がヒーローマントを持つか確認。
3. ヒーローマント除去後の実効HPを計算する。
4. 現在activeの合法攻撃でKO圏内に入るか判定。
5. KO圏内なら `reasons += ("tool_scrapper_enables_ko",)`。
6. 対象が主軸、強敵、壁なら `reasons += ("removes_key_tool",)`。

注意:

- HPを実際に減らさない。
- Toolを実際に外さない。
- ヒーローマント以外の道具は、初回は `removes_tool=True` と価値タグだけ返す。

### 4.5 退却Option

対象:

- `OptionType.RETREAT`

参照:

- `BoardView.active` `main.py:312`
- `BoardView.bench` `main.py:314`
- `BoardView.energy_count` `main.py:455`
- `BoardView.best_damage` `main.py:493`
- `Policy.best_retreat_target` `main.py:827`

判定:

1. activeがいなければ `legal=False`
2. 実効逃げコストを `retreat_cost(active, board)` で計算。
3. 波乗りビーチ等の公開スタジアム軽減を適用。
4. ふうせん等の公開Tool軽減を適用。
5. 必要なエネルギー数を `retreat_energy_cost` に入れる。
6. 正式なエネルギー選択Optionは推測しない。
7. activeに付いている水・イグニッション等の重要エネ数を `important_energy_loss` に入れる。
8. 交代候補のうち、現在攻撃可能な最大火力を確認。
9. 交代先がエネルギー0メガで攻撃不能なら `reasons += ("zero_energy_mega_wall",)`。
10. 火力改善がないなら `reasons += ("no_damage_improvement",)`。
11. activeが攻撃可能で、退却しても火力改善や生存価値がないならPolicy側で禁止候補にする。

重要:

- エネルギーは勝手に消費しない。
- ベンチとactiveを入れ替えない。
- 退却後のOption集合は生成しない。

## 5. Policyとの接続方法

### 接続点

- `Policy.__init__` `main.py:653`  
  `self.outcome = ImmediateOutcomeEvaluator(board)` を持つ。

- `Policy.score_attack` `main.py:730`  
  ダメージ、KO、サイド、壁無効はOutcomeを唯一の根拠にする。  
  Policy側は対面プランとタイブレークだけを足す。

- `Policy.score_end` `main.py:783`  
  攻撃フェーズで `blocked=False` の有効攻撃があるならEND禁止。

- `Policy.score_boss` `main.py:928`  
  ボス後KO、壁回避、エンジン破壊はOutcomeを使う。

- `Policy.score_attach` `main.py:963`  
  付与後に新しく使えるワザ、本命技到達、イグニッション即時攻撃はOutcomeを使う。

- `Policy.score_retreat` `main.py:795`  
  逃げコスト、重要エネルギー損失、火力改善、エネルギー0メガ事故はOutcomeを使う。

- `Policy.score_target_or_card` `main.py:1151`  
  ボス、Tool Scrapper、セイジ等の対象選択でOutcomeを補助に使う。

### 優先順

PolicyはOutcomeを以下の順で使う。

1. `wins_game`
2. 敗北回避に必要な確定行動
3. `knockout` / `prizes_taken`
4. `blocked=False` の有効攻撃
5. `enables_attack`
6. `MATCHUP_PLANS`
7. 小さな通常タイブレーク

### 二重評価防止

唯一責任者を以下に分ける。

- ダメージ計算: `ImmediateOutcomeEvaluator`
- 壁無効判定: `ImmediateOutcomeEvaluator`
- KO判定: `ImmediateOutcomeEvaluator`
- サイド取得: `ImmediateOutcomeEvaluator`
- 即時勝利: `ImmediateOutcomeEvaluator`
- 対面プラン補正: `Policy`
- カード使用価値: `Policy`
- protected / last_resort: `Policy`
- 複数候補の最終順位付け: `Policy`

## 6. 変更対象一覧

設計上の追加対象。

- `ImmediateOutcome` dataclass
- `ImmediateOutcomeEvaluator`
- 純関数 `energy_tokens_with_extra`
- 純関数 `can_pay_attack_with_tokens`
- 純関数 `effective_attack_damage`
- 純関数 `is_effect_ignoring_attack`
- 純関数 `is_ex_attack_wall`
- 純関数 `is_blocked_attack`
- 純関数 `prizes_left`
- 純関数 `retreat_cost`
- 純関数 `important_energy_loss`
- 純関数 `tool_removed_effective_hp`

既存の接続修正対象。

- `Policy.__init__` `main.py:653`
- `Policy.score_attack` `main.py:730`
- `Policy.score_end` `main.py:783`
- `Policy.score_retreat` `main.py:795`
- `Policy.score_play` `main.py:840`
- `Policy.score_boss` `main.py:928`
- `Policy.score_attach` `main.py:963`
- `Policy.score_target_or_card` `main.py:1151`
- `Policy.score_switch_target` `main.py:1175`

BoardView修正候補。

- `BoardView.can_pay_attack` `main.py:474`
- `BoardView.active_can_ko` `main.py:548`
- `BoardView.my_prizes_left` `main.py:535`

## 7. 禁止対象一覧

以下は実装・復活禁止。

- `GameSimulator`
- `copy.deepcopy`
- 仮想BoardState
- BoardState内の仮想HP
- 仮想カードID
- 仮想バトル場
- 仮想ベンチ
- 仮想サイド
- 仮想スタジアム
- `Action.apply`
- `GameAction` 階層
- `ActionFactory`
- `BoardEvaluator`
- `PrizeRaceEvaluator`
- `TempoEvaluator`
- `FutureBoardEvaluator`
- `DecisionGovernor`
- 相手の非公開手札推測
- 次ドロー推測
- 相手の進化推測
- 相手のサポート使用推測
- 好きなエネルギーを次ターン貼れる前提
- 2手先風の静的スコア
- Outcomeを固定係数で混ぜること
- KO、サイド、打点をPolicyとOutcomeの両方で独立加点すること

## 8. テストケース一覧

### 1. 有効攻撃がある攻撃フェーズでENDを選ばない

条件:

- `BoardView.is_attack_choice_phase` がTrue
- `OptionType.ATTACK` と `OptionType.END` が両方提示
- 攻撃Outcomeが `blocked=False`

期待:

- `Policy.score_end` は `SCORE_FORBIDDEN`
- 攻撃Optionが選ばれる

### 2. イグニッション付与後に本命技を選ぶ

条件:

- activeが `MEGA_STARMIE_EX`
- `IGNITION_ENERGY` attach Optionあり
- 付与後に `NEBULA_BEAM` が使える

期待:

- attach Outcome `enables_attack=True`
- `enabled_attack_ids` に `NEBULA_BEAM`
- `reasons` に `ignition_immediate_attack`

### 3. EX無効壁へ無効なEXワザを選ばない

条件:

- 相手activeが `EX_ATTACK_WALLS`
- 自分activeがEXまたはMegaEX
- 攻撃が効果無視ではない

期待:

- 攻撃Outcome `blocked=True`
- Policyはその攻撃を禁止または最下位にする

### 4. Nebula Beamで壁を突破できる場合は候補に残す

条件:

- 相手activeが `EX_ATTACK_WALLS`
- 攻撃Optionに `NEBULA_BEAM`

期待:

- Outcome `blocked=False`
- `removes_wall=True`
- 攻撃候補に残る

### 5. KOで最終サイドを取れる攻撃を最優先する

条件:

- 攻撃でKO可能
- `prizes_taken >= prizes_left`

期待:

- Outcome `wins_game=True`
- Policyは最優先する

### 6. ボスで呼べば勝てる対象を認識する

条件:

- 相手ベンチに低HPのEXまたはMegaEX
- 現在activeの合法攻撃でKO可能
- ボス使用または対象選択Option

期待:

- Outcome `knockout=True`
- `prizes_taken` が対象に応じる
- `wins_game` も判定する

### 7. Tool Scrapperでマントを剥がすとKOできるケース

条件:

- 相手activeまたはベンチにヒーローマント付き
- 除去後の実効HPが現在攻撃のダメージ以下

期待:

- Outcome `removes_tool=True`
- `reasons` に `tool_scrapper_enables_ko`

### 8. 退却すると水エネルギーを失い、火力も改善しないケース

条件:

- activeに水エネルギーあり
- activeが攻撃可能
- ベンチ候補の火力がactive以下

期待:

- Outcome `important_energy_loss > 0`
- `reasons` に `no_damage_improvement`
- Policyは退却を禁止またはlast_resortへ落とす

### 9. エネルギー付与後に新しくNebula Beamが使えるケース

条件:

- 対象が `MEGA_STARMIE_EX`
- 付与前は `NEBULA_BEAM` 不可
- 付与後は可

期待:

- Outcome `enables_attack=True`
- `enabled_attack_ids` に `NEBULA_BEAM`

### 10. Aの修正後もBが再発しない対立ケース

対立例:

- A: 攻撃可能ならEND禁止
- B: ただし壁で確定無効の攻撃しかない場合、END以外の展開Optionを優先

期待:

- 有効攻撃がある場合だけEND禁止
- `blocked=True` 攻撃しかない場合は、攻撃強制で自滅しない

別対立例:

- A: イグニッション付与後は攻撃へ行く
- B: イグニッション付与先がactiveでなく即時攻撃不能なら高評価しない

期待:

- `ignition_immediate_attack` がある場合のみ強く押す

## 9. 想定追加行数

概算:

- `ImmediateOutcome` dataclass: 20から30行
- `ImmediateOutcomeEvaluator`: 180から260行
- 純関数群: 80から140行
- Policy接続修正: 80から140行
- テスト補助・回帰シナリオ: 150から250行

本体追加はおおよそ 300から500行。  
旧GameSimulator系のようなAction階層、仮想盤面、BoardEvaluatorは作らないため、1000行単位にはしない。

## 10. 実装順序

1. `ImmediateOutcome` dataclassを追加する。
2. エネルギー支払い純関数を作る。先に `can_pay_attack` の typed/colorless 問題を正す。
3. 攻撃Outcomeを実装する。
4. `Policy.score_attack` をOutcome責務へ接続し、打点・KO・サイドの二重評価を消す。
5. `Policy.score_end` を「blockedではない有効攻撃がある場合だけEND禁止」に変える。
6. エネルギー付与Outcomeを実装する。
7. `Policy.score_attach` を `enables_attack` / `enabled_attack_ids` へ接続する。
8. ボスOutcomeを実装する。
9. `Policy.score_boss` とボス対象選択をOutcomeへ接続する。
10. Tool Scrapper Outcomeを実装する。
11. 退却Outcomeを実装する。
12. `Policy.score_retreat` と `Policy.score_switch_target` をOutcomeへ接続する。
13. 回帰ケースを順に検証する。
14. 旧GameSimulator的な構造が増えていないことを `rg` で確認する。

## 公開情報だけで計算できる根拠

この設計で使う情報は以下に限定する。

- 現在提示されている `obs.select.option`
- 自分のactive/bench/hand/discard
- 相手のactive/bench/discard
- 場に見えているポケモンID、HP、付いているエネルギー、道具
- `CardData` と `Attack` の公開定義
- `MATCHUP_PLANS` の静的対面知識
- `FORBIDDEN_PATTERNS` の静的禁止知識

使わない情報:

- 相手の手札内容
- 相手の山札内容
- 次のドロー
- 相手が次に貼るエネルギー
- 相手が持っている進化札
- 相手が持っているサポート
- 相手の次ターンの合法Option

これにより、ImmediateOutcomeEvaluatorは「一手先探索」ではなく「現在Optionの即時確定結果解析」に限定される。

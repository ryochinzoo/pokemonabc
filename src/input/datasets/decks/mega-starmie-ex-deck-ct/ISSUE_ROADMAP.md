# PTCG AI Issue Roadmap

## 0. この文書の役割

この文書は、監査で確認された問題を、**何が起きているか／どの責務が欠けているか／どう直すか／どこまで直れば完了か**の順に整理した実装ロードマップです。

文書の役割は次のように分けます。

| 文書 | 役割 |
|---|---|
| `README.md` | AIがどう調査・実装・自己監査するかという作業契約 |
| `ISSUE_ROADMAP.md` | 何を、どの順序で、どの完了条件まで直すか |
| `ptcg_68_replay_research_audit.md` | 問題を特定した証拠、数値、反例、訂正、総論 |
| `main.py` | 現在の実装上の事実 |
| `test_immediate_outcome.py` | 現在保証されている挙動と追加すべき回帰test |

AIは、監査MDを頭から順に実装Issueへ変換してはいけません。監査には、原因未確定の観測、正常例、相性分析、将来の検討事項も含まれます。

**実装対象と順序はこのロードマップを正とします。**

---

## 1. 現在の全体問題

現デッキには勝ち筋があります。しかしPolicyは、一手ずつの静的な価値は比較できても、同Turn内の短い行動列を十分に接続できません。

現在の中心問題は次です。

```text
盤面上では勝てる経路が存在する
↓
必要なActionを一つずつ見ると、それぞれは準備行動に見える
↓
後続Attackのdamage／KO／Prize／Winが前段Actionへ伝わらない
↓
ResourceやDevelopmentが優先される
↓
攻撃可能なTurnをENDする、別対象へ投資する、Energyを浪費する
```

つまり、単純に「Attackの点数が低い」「Froslassの点数が低い」という問題ではありません。

> **Fact不足、same-turn reachability不足、sequence cost不足が別々のAction間に存在すること**

が主要因です。

修正の基本方針:

1. 大域係数を先に動かさない
2. 欠けているFactを特定する
3. 実Outcomeと未実行の到達可能価値を分ける
4. 一つのIssueにつき一つの責務だけ直す
5. failing testと正常Guardの両方を持つ
6. カード名専用条件ではなく汎用構造として直す

---

## 2. Issue一覧と依存関係

### 状態

| 状態 | 意味 |
|---|---|
| `READY` | 現在着手してよい |
| `WAITING` | 前提Issueの完了待ち |
| `REWORK` | 実装したが設計またはGuardに問題がある |
| `BLOCKED` | 仕様・カード効果・責務が確定できず停止 |
| `ACCEPT` | TargetとGuardを満たし完了 |

### 優先順

| 順序 | ID | 問題 | 初期状態 | 主な依存 |
|---:|---|---|---|---|
| 1 | P0 | Active Attach後の即時KO／Win価値が伝わらない | `READY` | なし |
| 2 | P1 | Bench／交代を含むsame-turn Attack経路を接続できない | `WAITING` | P0 |
| 3 | P2 | AttachしたEnergyを有償Retreatで即座に失う | `WAITING` | P1 |
| 4 | P3-A | 0 damageと認識済みのAttackが準備行動を打ち切る | `WAITING` | P0〜P2 |
| 5 | P3-B | 実際は0 damageなのにdamage／KOありと誤認する | `WAITING` | P3-A |
| 6 | P4 | Active進化による即時damage改善の残存見逃し | `WAITING` | P3 |
| 7 | P5 | 相手の公開ThreatよりDevelopmentを優先する | `WAITING` | P0〜P4 |

依存イメージ:

```text
P0 Active Attach reachability
  ↓
P1 Composite access
  ↓
P2 Sequence resource loss
  ↓
P3-A Recognized zero damage priority
  ↓
P3-B Damage model mismatch
  ↓
P4 Residual active evolution
  ↓
P5 Opponent threat
```

P4は技術的には独立修正できる可能性がありますが、自動ループでは問題を混ぜないため、この順番を維持してください。

## 2.1 監査項目と実装Issueの対応

監査MDの研究項目と、このロードマップのIssueは一対一対応ではありません。

```text
11の研究項目
↓
コード上の根本原因と責務へ再編
↓
7つの実装Issue（P0、P1、P2、P3-A、P3-B、P4、P5）
```

理由:

- 複数の監査項目が、同じ根本原因を別角度から裏づけている
- 一つの監査項目に、実装責務が異なる複数問題が含まれる
- 因果未確定の観測や正常Guardは、独立Issueにしない
- 相性・使用率・勝率だけをカード専用補正へ変換しない

### 対応表

| 監査項目 | 主に接続するIssue | 扱い |
|---|---|---|
| 1. 勝ちの質＋回避可能敗戦 | P0、P1、P2、P4、P5 | Issue優先度とfailure caseの横断証拠。独立Issueにはしない |
| 2. ActionScore順位・field差 | P0、P3-A、P4 | 欠けたFactと最初に順位差が生じるfieldの原因分析 |
| 3. 複合行動経路 | P0、P1、P2 | Active Attach一段、交代を含む到達経路、sequence資源損失へ分割 |
| 4. カード利用状況 | 共通Guard、P5補助 | カード削除・専用補正を防ぐ材料。単独実装Issueにはしない |
| 5. Attacker速度・効率 | P0、P1 | Froslassのready化以前停止、Starmieへの到達、Cinderaceの役割を補強 |
| 6. Active／Bench資源配分 | P1、P2 | Active accessとAttach後Retreat浪費へ接続 |
| 7. 先攻後攻・初手 | 実装Issueなし | 因果未確定。現時点ではPolicy修正へ変換しない |
| 8. 相手デッキ別の敗戦形状 | P5、共通Guard | Opponent Threatの根拠。ただし対面・カード名専用補正にしない |
| 9. 感度分析 | P0、P3-A、P4、共通制約 | 固定加点や大域閾値変更の危険性、狭い変更候補の範囲を示す |
| 10. 支配関係違反 | P0、P1、共通Guard | Target根拠と、直接Actionを準備Actionより保護する規則へ接続 |
| 11. 未来情報混入監査 | 全Issue、特にP5 | 公開情報のみを使うという共通設計制約 |
| 追加研究: 相手デッキ × 攻撃軸／軸未達 | P0、P1、デッキ変更保留 | 軸未達の構造と、デッキ変更を先行しない根拠 |

### 監査項目3を三つへ分ける理由

```text
P0:
Active Attach
→ Attack合法化
→ KO／Prize／Win
```

P0は、現在のActiveへのAttach直後に起きる一段のreachabilityです。

```text
P1:
Bench Attach
→ Retreat／Surfing Beach
→ Active交代
→ Attack
```

P1は、仮想盤面遷移と短いsame-turn探索が必要です。

```text
P2:
Active Attach
→ paid Retreat
→ Energy消失
→ Attackなし
```

P2は、到達可能性ではなくsequence全体のresource costです。

三つは症状が近くても、Fact責務・必要なstate・完了条件が異なるため、同時実装しません。

### 0 damageを二つへ分ける理由

```text
P3-A:
評価器もdamage 0と認識
→ それでもAttack Tierが準備行動を打ち切る
```

これはPolicy／Tier側の問題です。

```text
P3-B:
実エンジンではdamage 0
→ 評価器はdamage／KOありと誤認
```

これはOutcome model側の問題であり、Tier調整では直りません。

### 実装Issueにしない監査結果

次は重要な観測ですが、現段階では独立Issueへ変換しません。

- 先攻52.5％、後攻29.6％
- Alakazam系2勝8敗
- Lucario系5勝8敗
- Boss合法162 Turn、使用2
- Froslassの使用率
- CinderaceのPrize効率
- Active E0＋Ready Bench＋END
- デッキ変更

これらは、因果未確定、正常例混在、またはP1／P5の汎用責務へ吸収されるためです。

AIは、監査項目を上から順番に一件ずつコード変更へ変換してはいけません。実装対象と順序は、P0〜P5のロードマップを正としてください。

---

# P0: Active Attach後の即時KO／Win reachability

## P0-1. 現在起きている問題

ActiveへEnergyをAttachすると新しいAttackが合法になり、そのAttackで同TurnにKOまたはWinへ到達できる盤面でも、Attachが通常の育成行動としてしか評価されません。

監査では同系統を8 Turn確認しています。そのうち1 Turnは、その場の勝利まで公開情報だけで確定しています。

現在確認されているコード構造:

```text
evaluate_attach()
  └─ enables_attack
  └─ enabled_attack_ids
```

一方、Attach後に新しく合法化されるAttackの次の価値が、Attach候補へ届いていません。

```text
damage
knockout
prizes_taken
wins_game
```

## P0-2. 根本原因

確認済み:

- Attach前後で使用可能Attack IDが増えたことは分かる
- そのAttackが何damageを出すかはAttach評価で計算されない
- KO／Prize／Win価値がActionScoreの強いfieldへ届かない

未確定:

- 既存`enables_knockout`を同じ意味で再利用できるか
- reachable Prize／WinをどのFactに保存するか
- `score_attach()`と`action_score()`のどちらが責務上適切か

## P0-3. 目標状態

次を汎用的に評価できること。

```text
現在のActiveへAttach
→ Attach前は支払い不能だったAttackが合法化
→ そのAttackの予測結果を計算
→ blockedでなければdamage／KO／Prize／Win到達価値を保持
→ Policyが通常の育成Attachと区別できる
```

ただし、Attachそのものの実Outcomeへ未実行KOを記録しません。

## P0-4. 解決手順

1. `enables_knockout`の定義・設定箇所・使用箇所を確認する
2. Attach前後で新規合法化されたAttack IDだけを抽出する
3. Attach先が現在のActiveであることを確認する
4. 既存damage／wall／Prize helperを再利用して各Attackを評価する
5. 実Outcomeとは別のreachable Factへ保存する
6. 複数Attackがある場合の代表値選択を定義する
7. ActionScoreへ限定的に反映する
8. 直接KO／Win Attackを準備Attachが追い越さないGuardを入れる
9. カード名専用条件がないことを自己監査する

## P0-5. 必須test

### Target

- Active Attachで新しいAttackが合法化する
- 新規AttackがKO可能
- Prize取得でWin到達可能
- blocked AttackはKO／Win到達にならない
- 複数の新規Attackから妥当な候補を選べる
- Froslass／Water以外の同型構造でも動く

### Negative

- Bench Attachを即時Active Attackとして扱わない
- Attackを新規合法化しないAttachは昇格しない
- すでに合法なAttack価値をAttachへ重複計上しない
- Attachの`knockout`／`prizes_taken`／`wins_game`を実発生扱いにしない

### Guard

- 現在合法な直接KO Attackを維持
- 現在合法な直接Win Attackを維持
- 通常のBench育成を壊さない
- Cinderace加速、free-retreat、Active進化を壊さない

## P0-6. 完了条件

- Target testが通る
- Negative testが通る
- Guard testが通る
- 実Outcomeとreachable Factの二重計上がない
- カード名専用条件がない
- `_result_key()`を変更した場合、他の方法では不可能だった理由を説明できる
- P1以降を同時変更していない

---

# P1: Composite access

## P1-1. 現在起きている問題

盤面上では同TurnにAttackへ到達できるのに、最初の準備Actionが単独評価で負けます。

正常に成立した経路は多数あります。

```text
Attach → Attack
Attach → Retreat → Attack
Attach → Surfing Beach → Attack
Energy Switch → Attack
Wally → 再Attach／交代 → Attack
進化 → Attach → Attack
```

一方、監査では未選択の複合経路を13 node・9 Replay、Ready Benchへ到達できずENDするdeadlockを13 Turn・4 Replay確認しています。

## P1-2. 根本原因

Action単体のImmediateOutcomeとscoreだけでは、次を表現できません。

```text
このAction後に残る合法Action
現在のActive
BenchからActiveへ移る方法
once-per-turn flag
Retreat cost
最終的に到達するAttack
```

P0はActive Attach直後の一段だけです。P1では、交代Actionを含む短い経路が必要です。

## P1-3. 目標状態

現在のActionから、同Turn内の限定された行動列を評価できること。

```text
candidate action
→ resulting public board state
→ legal switch／retreat／stadium action
→ reachable active attacker
→ reachable attack outcome
```

完全なゲーム木探索は不要です。自Turn内でAttackまたはENDまでの、短く決定的な経路に限定します。

## P1-4. 解決手順

1. P0のreachable Factを再利用可能な形にする
2. Board stateを破壊しない仮想遷移方法を確認する
3. Active／Benchをserial単位で追跡する
4. Retreat、free-retreat、Surfing Beachを区別する
5. 使用済みflagとEnergy costを仮想状態へ反映する
6. 最大深度を明示したsame-turn探索を実装する
7. Attackに到達した経路だけを高い価値として扱う
8. 到達しない育成価値と即時Attack価値を分ける
9. ループ経路、同じ交代の往復、状態重複を防ぐ

## P1-5. 必須test

- Bench Attach → paid Retreat → Attack
- Bench Attach → free-retreat → Attack
- Bench Attach → Surfing Beach → Attack
- Retreat → Ready attacker → Attack
- 交代後もAttack不能なら昇格しない
- 使用済みSurfing Beachを再利用しない
- Retreat済み状態で二度目のRetreatをしない
- Energy costを払えない経路を生成しない
- Active／Benchの同名カードをserialで混同しない
- 直接Attackがある場合に不要な複合経路を優先しない

## P1-6. 完了条件

- Target経路を構造として再現できる
- 到達不能経路を生成しない
- 状態遷移が元Boardを汚染しない
- 探索深度と停止条件が明示される
- P2の資源浪費を同時に場当たり修正していない

---

# P2: Attach → paid RetreatによるEnergy浪費

## P2-1. 現在起きている問題

監査では次のsequenceを14件確認しています。

```text
ActiveへEnergy Attach
→ 同Turnに有償Retreat
→ 付けたEnergyをRetreat Costとして失う
→ Attackなし
```

勝利・敗戦の両方に存在するため、勝利testだけでは検出できません。

## P2-2. 根本原因

AttachとRetreatを別々に採点すると、sequence全体で起きる資源損失が見えません。

ただし、次は正常です。

- 状態異常解除
- 被KO回避
- Attackへ接続
- free-retreat
- 価値の高いActive交代

よって「Attach後にRetreatしたら罰する」では広すぎます。

## P2-3. 目標状態

経路全体について、次を比較できること。

```text
投入Energy
Retreatで失うEnergy
重要Energyの損失
Attack到達
KO回避
状態解除
free-retreat
最終Activeの価値
```

具体的利益がない純損失経路だけを下げます。

## P2-4. 解決手順

1. P1で生成した経路にresource deltaを持たせる
2. AttachしたEnergy card serialを追跡する
3. Retreat paymentで失われたEnergyを特定する
4. Attack、状態解除、survival、free-retreatの利益を別Factで確認する
5. 純損失経路にだけriskまたはresource penaltyを付ける
6. Attach単体またはRetreat単体へ一律penaltyを入れない

## P2-5. 必須test

- AttachしたEnergyを同TurnRetreatで失いENDする経路を下げる
- 同じ経路でもAttackへ接続すれば下げない
- 状態異常解除なら一律禁止しない
- free-retreatならEnergy損失扱いしない
- 付けたEnergy以外を支払った場合を区別する
- 重要Energyと余剰Energyを区別する既存責務を壊さない

## P2-6. 完了条件

- sequence-levelの損失として表現される
- 正常Retreatを壊さない
- Attach／Retreat単体へのカード名・固定penaltyがない
- P1の到達経路と整合する

---

# P3-A: 認識済み0 damage Attackの優先度

## P3-A-1. 現在起きている問題

評価器自身がdamage 0と認識しているAttackでも、Attackであること自体によりTierが高くなり、有用な準備行動を打ち切る場合があります。

確認済み例は`87632037 T7/T9`です。

## P3-A-2. 根本原因

「Attackを実行する」ことと「盤面を改善する」ことが同一視されています。

ただし0 damage Attackでも、効果、状態異常、Energy操作、Bench damageなどの価値を持つ場合があります。damage 0だけで一律降格できません。

## P3-A-3. 目標状態

次のAttackだけを限定的に下げます。

```text
damage = 0
KOなし
Prizeなし
Winなし
有用なAttack effectなし
盤面改善なし
```

## P3-A-4. 解決手順

1. Attackの非damage効果を現在どこまでFact化しているか確認する
2. 「0 damage」ではなく「有効Outcomeなし」を定義する
3. 直接の有用効果がないAttackだけTierまたはimmediateを下げる
4. Attack effect未対応の場合は、誤って無価値判定せずBLOCKEDにする

## P3-A-5. 必須test

- 完全に無効な0 damage Attackを有用prepより下げる
- 状態異常を与える0 damage Attackを保護する
- Bench damageを与えるAttackを保護する
- Energy操作やswitch効果を持つAttackを保護する
- KO／Prize／Win Attackを保護する

## P3-A-6. 完了条件

- damageだけでなくAttack全効果を考慮する
- 無効Attackだけを限定的に下げる
- 有用な0 damage Attackを壊さない

---

# P3-B: damage／KOの誤認

## P3-B-1. 現在起きている問題

実エンジン上はdamage 0なのに、評価器が50 damageおよびKOとして認識したケースが`87638484`で8回確認されています。

これはTier調整では直りません。Outcome modelが実際のカード効果・継続効果・防御条件を欠いています。

## P3-B-2. 根本原因

候補:

- 攻撃側のdamage helperが継続効果を見ていない
- 防御側のwall／effectを見ていない
- engine上の特殊条件がCARD_TABLE／ATTACK_TABLEへ表現されていない

原因は実コードとカード効果を確認して確定してください。

## P3-B-3. 目標状態

同じ公開盤面から、Policy evaluatorと実エンジンが同じdamage可否を判定すること。

## P3-B-4. 解決手順

1. 誤認Attackと防御側効果を特定する
2. engine側の正しい判定責務を確認する
3. 既存wall／effect Factへ統合できるか確認する
4. カード名専用分岐ではなく、効果カテゴリとして実装する
5. `evaluate_attack()`とP0/P1 reachable Attackの両方で同じhelperを使う
6. damage、KO、Prize、Winを同時に再計算する

## P3-B-5. 必須test

- 該当防御効果下でdamage 0
- KO／Prize／WinもFalse
- 効果がない相手には通常damage
- bypass条件があるAttackは正しく通る
- P0/P1の仮想Attackでも同じ結果

## P3-B-6. 完了条件

- evaluatorとengineの判定責務が一致する
- 同じeffectを複数箇所へ重複実装しない
- カード名だけでなく効果カテゴリとして説明できる

---

# P4: Active進化の残存穴

## P4-1. 現在起きている問題

既存修正によりActive進化見逃しは大幅に減りましたが、damage改善量が現在の閾値に届かないケースが残っています。

確認済み:

- v7.3: 13 node
- v7.4: 2 node
- 残存例: `87644371 T4/T6`
- damage改善閾値50に対し、改善量20

感度分析では閾値20で変化したのは3 node・2 Turn、正常Guard変化0でした。

## P4-2. 根本原因

現在のActive進化価値が、固定damage改善閾値でTier昇格する設計に依存しています。

閾値を下げれば狭く直る可能性がありますが、意味上の根拠が必要です。

## P4-3. 目標状態

Active進化により同TurnAttackの価値が明確に改善する場合、改善量20でも合理的に選べること。

ただし、Bench進化、将来育成、直接KO Attackを壊しません。

## P4-4. 解決手順

1. 残存ケースを最小盤面testで再現する
2. 進化前後のAttack結果差分をFactとして確認する
3. 閾値20が意味的に妥当か、別の構造条件が必要か比較する
4. 最小変更を選ぶ
5. 進化しない方が良い正常ケースをGuard化する

## P4-5. 必須test

- damage +20のActive進化が有用な場合に選ばれる
- damage改善なしの進化を昇格しない
- 直接KO／Win Attackを進化が追い越さない
- Bench進化全体を同じTierへ上げない
- 進化後Attackがblockedなら昇格しない

## P4-6. 完了条件

- 残存ケースの構造をtestで再現
- 変更範囲が狭い
- 閾値変更の場合、なぜ20なのか説明できる
- 別進化や直接AttackのGuardを維持

---

# P5: Opponent Threat vs Development

## P5-1. 現在起きている問題

相手の公開盤面から次Turnの高damageや自ActiveのKOが見える状況でも、相手Threatの除去よりBench育成や手札展開を優先する場合があります。

Alakazam系では、公開handCountにより次Attack damageが上昇し、即時攻撃準備またはBossによる処理可能性があるのにDevelopmentを優先した場面を確認しています。

全体発生件数と全カードの次Turn damage再現は未確認です。

## P5-2. 根本原因

Policyに次の汎用Factが不足している可能性があります。

```text
相手が次Turn攻撃可能か
予測damage
自ActiveがKOされるか
相手AttackerのPrize価値
現在そのThreatを処理可能か
Threat除去と現在Prize取得の交換
```

P0〜P4が未修正だと、自分側のAttack到達不能とOpponent Threat不足が混ざります。

## P5-3. 目標状態

公開情報だけを用いて、次の比較ができること。

```text
現在のDevelopment価値
vs
相手次Turnの被KOリスク
vs
現在のThreat除去可能性
vs
現在取れるPrize
```

## P5-4. 解決手順

1. opponent attack legality helperを確認する
2. 公開情報から次Turnの予測damageを計算する
3. handCount依存など公開countを使うdamageを扱う
4. 相手Active／Bench Threatをserial単位で評価する
5. Boss、Attack、switchなど現在の除去経路と接続する
6. Prize tradeをFactとして比較する
7. 特定カード名ではなく汎用Threat scoreへ落とす
8. 隠れた手札内容、山札順、未来drawを使わない

## P5-5. 必須test

- 公開情報だけで次Turn自Active KOを予測
- Threatを現在KOできる場合にDevelopmentより優先
- Threat除去不能なら無意味なBossを過大評価しない
- 現在の2〜3 Prize KOを捨てて低価値Threatを追わない
- handCount依存damageを公開枚数だけで計算
- 相手の非公開手札内容を参照しない
- Threatが低い正常Developmentを維持

## P5-6. 完了条件

- P0〜P4がACCEPT
- 公開情報だけで計算
- opponent damage modelが自分側と整合
- Threat専用カード名分岐がない
- Prize tradeとDevelopment Guardを持つ

---

## 3. 現時点で実装Issueにしない監査結果

次は重要な観測ですが、単独では即実装しません。

| 観測 | 現在の扱い |
|---|---|
| 先攻52.5%、後攻29.6% | 因果未確定。Policy修正Issueにしない |
| Alakazam系2勝8敗 | 既知Policy欠陥が混在。相性専用補正にしない |
| Lucario系5勝8敗 | v7.4で4勝2敗。構造的不利と断定しない |
| Boss合法162 Turn、使用2 | 攻撃不能時の遅延価値など未確定。P5で汎用評価 |
| Froslass使用率が低い | ready化以前で止まることが主因。カード削除根拠にしない |
| CinderaceのPrize効率が低い | 加速・free-retreat・非ex役割がある。削除根拠にしない |
| Active E0＋Ready Bench＋END | 正常例も含む。P1の到達可能性で分離 |
| デッキ変更 | P0〜P5より先に行わない |

---

## 4. Issue間で共通する設計ルール

### FactとPolicyを分ける

Fact層は、盤面から計算可能な事実を返します。

```text
合法か
何damageか
blockedか
KOか
Prizeはいくつか
Winか
Energyはいくつ失うか
どのAttackへ到達できるか
```

Policy層は、そのFactをどう比較するかを決めます。

カード名への好き嫌いをFactへ混ぜないでください。

### 実OutcomeとReachabilityを分ける

```text
実Outcome:
  現在のActionを実行した直後に発生する結果

Reachability:
  そのAction後、同Turn中の合法な後続Actionで到達可能な結果
```

同じKO／Prize／Winを両方へ加点しないでください。

### 直接Actionを保護する

同じ最終結果へ到達するなら、原則として準備Actionより直接Attackを優先します。

準備Actionが上になるのは、直接Actionがまだ合法でない場合、または直接Actionより明確に高い最終結果へ到達する場合だけです。

### 状態をserial単位で追う

同名カードが複数存在するため、Active／Bench／Energy／Toolの対象をcard IDだけで追わないでください。

### 無関係な大域調整を避ける

感度分析では、prep閾値や固定Attach加点は多数nodeを変更しました。

先にFact責務を直してください。

---

## 5. 自動ループでのロードマップ使用方法

1. 状態が`READY`の最上位Issueを選ぶ
2. この文書の「現在の問題」「根本原因」「目標状態」を読む
3. 監査MDで該当箇所の証拠と正常例を確認する
4. 実コードで原因を再確認する
5. failing testを作る
6. 最小実装する
7. Target／Negative／Guard testを実行する
8. READMEの自己監査を行う
9. `ACCEPT / REWORK / BLOCKED`を判定する
10. ACCEPTの場合だけ次Issueを`READY`として扱う

ロードマップの説明と実コードが食い違う場合、実コードを確認した結果を報告し、推測で進めないでください。

---

## 6. 全体完了条件

次を満たしたとき、この改善ロードマップを完了とします。

- P0〜P5がすべて`ACCEPT`
- 各IssueにTarget／Negative／Guard testがある
- 実OutcomeとReachabilityが分離されている
- same-turn経路の状態遷移が一箇所の責務にまとまっている
- damage／wall判定を直接Attackと仮想Attackで共有している
- Energy損失をsequenceとして評価できる
- 無効0 damage Attackと有用0 damage Attackを区別できる
- opponent Threatを公開情報だけで評価できる
- カード名専用救済がない
- P0〜P5以外の変更が混入していない

完了後に初めて、残る不自然行動を再監査し、次のIssue群またはデッキ変更を検討してください。

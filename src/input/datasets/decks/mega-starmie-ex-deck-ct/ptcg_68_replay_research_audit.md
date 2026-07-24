# PTCG AI Replay Research Audit

## 監査原則

- 対象: 提供済み68 Replay（v7.3敗戦20、v7.3勝利18、v7.4敗戦18、v7.4勝利12）。
- 各研究項目は独立して実施し、完了した内容だけを本ファイルへ追記する。
- Replayで確認できる事実、監査上の判定、推測、コード未確認事項を分離する。
- 判断時点で非公開だった未来情報を、Policyの正誤判定には使用しない。
- 根拠不足は「不明」「判定不能」と記載し、補完しない。
- 既存レポートの結論を無条件に転記せず、必要箇所は生Replayから再確認する。
- v7.3とv7.4、勝利と敗戦、self-playと対外戦を混同しない。

## 研究進行

1. 勝ちの質と回避可能敗戦の分類 — **完了**
2. ActionScoreの順位差・field差 — **完了**
3. 複合行動経路 — **完了**
4. カード別利用価値 — 未着手
5. Attacker別の起動速度と効率 — 未着手
6. BenchとActiveの資源分配 — 未着手
7. 先攻・後攻、初手、事故率 — 未着手
8. 対戦相手別の負け方 — 未着手
9. 評価関数の感度分析 — 未着手
10. 支配関係違反の検出 — 未着手
11. 未来情報混入監査 — 未着手

---

## 1. 勝ちの質と回避可能敗戦の分類

### 状態

研究項目1を完了。以下は確定した結果のみ。

### 1.1 判定方法

この項目では、勝敗そのものとPolicyの正常性を分離した。

- **勝利経路**はReplay終端の公開状態で `Prize / Board-out / Deck-out` に分類した。
- **攻撃終結**は、最後の勝利確定行動がAttackであり、Prize取り切りまたは相手盤面消滅に至ったもの。
- **確定損失**は、合法Option・公開盤面・実結果まで確認できたものだけを数えた。
- `W1` の「確定損失を検出せず」は、最善手だったことを意味しない。
- `L4` の「確定欠陥なし」は、不可避の敗戦だったことを意味しない。
- 勝敗反転を証明するには、代替行動がその場でゲーム終了まで到達する場合だけを `L1` とした。単なるKO・資源改善・停止回避は勝敗反転を保証しないため、`L2/L3` に留めた。
- Board-outを相手事故とは分類しない。相手がBasicを引けなかったのか、合法展開を見送ったのか、こちらの圧力で盤面が消えたのかは、相手側Policyを別監査しない限り不明。

### 1.2 勝利の質

#### 集計

| 区分 | 件数 | 意味 |
|---|---:|---|
| W0 self-play | 1 | Yser同士。対外勝率・相性評価から除外 |
| W1 攻撃終結・確定損失を検出せず | 17 | 対外戦でPrize/Board-outをAttackにより完了。既知の確定損失なし |
| W2 攻撃終結・確定損失あり | 9 | 攻撃で勝ったが、その前に確定した損失行動あり |
| W3 Deck-out終結・確定損失あり | 3 | 相手山札切れで勝利。3件すべてに確定損失あり |

- 全30勝の終結条件は **Prize 22、Board-out 5、Deck-out 3**。
- self-playを除く対外29勝では、**26/29がAttack終結**、3/29がDeck-out終結。
- 対外29勝のうち **12/29に確定損失**があった。
- Attack終結26勝だけを見ても、**9/26は確定損失を含んだまま勝っている**。
- したがって、現デッキには相手Deck-outだけに依存しない攻撃的な勝ち筋がある。一方で、勝利ラベルはPolicy欠陥をかなり隠している。

#### バージョン別

| Version | W0 | W1 | W2 | W3 |
|---|---:|---:|---:|---:|
| v7.3 | 1 | 9 | 7 | 1 |
| v7.4 | 0 | 8 | 2 | 2 |

v7.4で確定損失を含む勝利が少なく見えるが、母数が12戦と小さく、相手分布も異なる。これだけでPolicy全体が改善したとは断定しない。

#### Replay別

| Episode | Ver | 終結 | 自Turn数 | 相手残Prize | 分類 | 確定損失 |
|---:|---|---|---:|---:|---|---|
| 87480598 | v7.3 | Prize | 8 | 4 | W0 self-play（対外評価から除外） | なし（最善性を保証しない） |
| 87480740 | v7.3 | Prize | 7 | 6 | W2 攻撃終結・確定損失あり | T1 Attach→有償RetreatでEnergy喪失 |
| 87481258 | v7.3 | Prize | 9 | 6 | W2 攻撃終結・確定損失あり | T3/T5 Active進化見逃し |
| 87482904 | v7.3 | Prize | 8 | 1 | W2 攻撃終結・確定損失あり | T11/T13 Composite accessによる同Turn KO見逃し |
| 87483996 | v7.3 | Prize | 6 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87485083 | v7.3 | Prize | 8 | 5 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87488887 | v7.3 | Prize | 9 | 2 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87491060 | v7.3 | Deck-out | 11 | 1 | W3 Deck-out終結・確定損失あり | T1 Retreat浪費、T5/T7 Access deadlock、T9 Composite KO見逃し |
| 87491590 | v7.3 | Prize | 21 | 5 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87492128 | v7.3 | Prize | 17 | 6 | W2 攻撃終結・確定損失あり | T3 Active進化見逃し、T15 合法Attackを残してEND |
| 87493190 | v7.3 | Prize | 7 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87494261 | v7.3 | Board-out | 3 | 6 | W2 攻撃終結・確定損失あり | T1 Attach→有償RetreatでEnergy喪失 |
| 87494795 | v7.3 | Board-out | 5 | 4 | W2 攻撃終結・確定損失あり | T1 Attach→有償RetreatでEnergy喪失 |
| 87497826 | v7.3 | Board-out | 9 | 6 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87510420 | v7.3 | Prize | 9 | 2 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87533017 | v7.3 | Prize | 12 | 1 | W2 攻撃終結・確定損失あり | T3 Active進化見逃し |
| 87543559 | v7.3 | Prize | 13 | 2 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87555944 | v7.3 | Prize | 10 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87631518 | v7.4 | Prize | 9 | 5 | W2 攻撃終結・確定損失あり | T2 Attach→有償RetreatでEnergy喪失 |
| 87633136 | v7.4 | Prize | 9 | 6 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87634201 | v7.4 | Board-out | 4 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87635272 | v7.4 | Prize | 22 | 5 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87636337 | v7.4 | Prize | 6 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87636873 | v7.4 | Prize | 7 | 6 | W2 攻撃終結・確定損失あり | T1 Attach→有償RetreatでEnergy喪失 |
| 87638484 | v7.4 | Deck-out | 10 | 6 | W3 Deck-out終結・確定損失あり | T6–T20 実damage 0 Attackを8回反復 |
| 87640634 | v7.4 | Prize | 8 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87641694 | v7.4 | Board-out | 6 | 2 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87642240 | v7.4 | Deck-out | 11 | 6 | W3 Deck-out終結・確定損失あり | T1 Retreat浪費、T7/T9 Access deadlock |
| 87643838 | v7.4 | Prize | 7 | 6 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |
| 87644912 | v7.4 | Prize | 8 | 3 | W1 攻撃終結・確定損失を検出せず | なし（最善性を保証しない） |

### 1.3 回避可能敗戦

#### 集計

| 区分 | 件数 | 判定可能なこと |
|---|---:|---|
| L1 即時勝利の見逃しを証明 | 1 | 合法な代替行動でそのTurnに勝利できた |
| L2 強い確定損失 | 8 | 即時KO見逃し、複数Turn deadlock、0 damage Attackによる準備打切り。勝敗反転までは未証明 |
| L3 局所的な確定損失 | 10 | 進化見逃し、無利益Retreat浪費。損失は確定、勝敗影響は不明 |
| L4 確定欠陥なし／回避可能性不明 | 19 | 既知の狭い条件では欠陥を確定できない。不可避とは判定しない |

38敗中、**19敗には少なくとも1件の確定損失行動**がある。ただし、その19敗が修正後すべて勝利へ変わるという意味ではない。

#### 直接反転を証明できた1件

`87639549 T12`のみ、Replay上で即時勝利まで証明できた。

- 自分の残りPrize: 1
- Active: Mega Froslass ex、W Energyなし
- 相手Active: Alakazam HP140
- 相手公開handCount: 19
- ActiveへのBasic {W} Energy Attachが合法
- Resentful Refrainは公開情報上 `19 × 50 = 950 damage`
- 同じカードの成功ReplayからAlakazam KOが1 Prizeであることを確認済み
- 実際はBench側を育成し、Alakazamを倒さず敗戦

この1件は「より良かったかもしれない」ではなく、合法な代替経路でそのTurnにゲーム終了条件を満たす。

#### バージョン別

| Version | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|
| v7.3 | 0 | 4 | 7 | 9 |
| v7.4 | 1 | 4 | 3 | 10 |

v7.3からv7.4でActive進化見逃し中心の `L3` は7件から3件へ減った。一方、即時KO見逃し・deadlock・0 damage preemptionを含む `L1+L2` は4件から5件へ増えている。したがってIssue5の改善だけでは、強い敗着候補の総量は減っていない。

#### Replay別

| Episode | Ver | 敗北終結 | 自Turn数 | 自残Prize | 分類 | 根拠 |
|---:|---|---|---:|---:|---|---|
| 87481810 | v7.3 | Opponent Prize | 7 | 3 | L4 確定欠陥なし／回避可能性不明 | Turbo FlareのEnergy集中を観測したが、後に利用されており損失確定不可 |
| 87482358 | v7.3 | Opponent Prize | 6 | 2 | L4 確定欠陥なし／回避可能性不明 | Attach→即時KO成功など正常経路あり。明確な欠陥を特定せず |
| 87483452 | v7.3 | Opponent Prize | 5 | 5 | L4 確定欠陥なし／回避可能性不明 | Active進化→Attach→Attackが成立。明確な欠陥を特定せず |
| 87484539 | v7.3 | Opponent Prize | 5 | 4 | L4 確定欠陥なし／回避可能性不明 | 序盤の壁setupはあるが合理性を排除できず |
| 87485611 | v7.3 | Opponent Prize | 7 | 5 | L3 局所的な確定損失（勝敗影響不明） | T3/T13 Active進化見逃し |
| 87486157 | v7.3 | Opponent Prize | 8 | 3 | L3 局所的な確定損失（勝敗影響不明） | T4 Active進化見逃し |
| 87486700 | v7.3 | Own Board-out | 2 | 6 | L3 局所的な確定損失（勝敗影響不明） | T3 Active進化見逃し |
| 87487251 | v7.3 | Opponent Prize | 4 | 6 | L3 局所的な確定損失（勝敗影響不明） | T1 Attach→有償RetreatでEnergy喪失 |
| 87487796 | v7.3 | Opponent Prize | 9 | 2 | L2 強い確定損失（勝敗反転は未証明） | T3/T5/T7: powered BenchがあるのにActiveから攻撃・RetreatできずENDするAccess deadlock |
| 87488357 | v7.3 | Opponent Prize | 11 | 2 | L2 強い確定損失（勝敗反転は未証明） | T1 Retreat浪費、T3/T5/T7 Access deadlock、T15/T17 Active FroslassへのW Attachで即時KO可能だが見逃し |
| 87489956 | v7.3 | Opponent Prize | 10 | 1 | L4 確定欠陥なし／回避可能性不明 | Prize進行は概ね成立。Yveltal低打点の代替価値は確定不可 |
| 87490505 | v7.3 | Opponent Prize | 7 | 4 | L3 局所的な確定損失（勝敗影響不明） | T12 Active進化見逃し |
| 87492654 | v7.3 | Opponent Prize | 6 | 4 | L4 確定欠陥なし／回避可能性不明 | Productive RetreatとAttack接続あり。相手速度優位が大きいが不可避とは断定しない |
| 87493732 | v7.3 | Opponent Prize | 9 | 3 | L3 局所的な確定損失（勝敗影響不明） | T3 Active進化見逃し |
| 87495339 | v7.3 | Opponent Prize | 6 | 3 | L4 確定欠陥なし／回避可能性不明 | Froslassなら高damageの候補はあるが非KOで、最善手を確定できず |
| 87495871 | v7.3 | Opponent Prize | 8 | 6 | L2 強い確定損失（勝敗反転は未証明） | T14/T16 Active FroslassへのW AttachでMega Starmie exを即時KO可能だが見逃し（T6進化見逃しも併存） |
| 87501720 | v7.3 | Opponent Prize | 14 | 2 | L3 局所的な確定損失（勝敗影響不明） | T20 Active進化見逃し |
| 87509907 | v7.3 | Opponent Prize | 7 | 6 | L4 確定欠陥なし／回避可能性不明 | Active access/Wally候補はあるが、確定Issue化できず |
| 87517866 | v7.3 | Opponent Prize | 6 | 6 | L4 確定欠陥なし／回避可能性不明 | W Energy取得が遅い。Energy starvationが大きいが、敗戦の不可避性は不明 |
| 87521331 | v7.3 | Opponent Prize | 12 | 5 | L2 強い確定損失（勝敗反転は未証明） | T12/T14/T16/T18/T20: powered Starmieへアクセスできず5 Turn停止（T4進化見逃しも併存） |
| 87630981 | v7.4 | Opponent Prize | 9 | 4 | L2 強い確定損失（勝敗反転は未証明） | T17 Active FroslassへのW AttachでAlakazam HP40を即時KO可能だが見逃し（T1 Retreat浪費も併存） |
| 87632037 | v7.4 | Opponent Prize | 7 | 4 | L2 強い確定損失（勝敗反転は未証明） | T7/T9 実damage 0 Attackが有用Attachを打ち切る（T1 Retreat浪費も併存） |
| 87632586 | v7.4 | Opponent Prize | 7 | 5 | L4 確定欠陥なし／回避可能性不明 | Attack前Attach/Cape候補あり。ただし最善手・勝敗影響は未確定 |
| 87633660 | v7.4 | Opponent Prize | 6 | 6 | L4 確定欠陥なし／回避可能性不明 | Attach・Ultra Ball合法でEND。保持の合理性を排除できず原因未確定 |
| 87634734 | v7.4 | Opponent Prize | 7 | 3 | L4 確定欠陥なし／回避可能性不明 | Attack前準備遅延候補あり。後続損失は見えるが、狭い確定条件に未到達 |
| 87637402 | v7.4 | Opponent Prize | 17 | 2 | L3 局所的な確定損失（勝敗影響不明） | T1 Attach→有償RetreatでEnergy喪失 |
| 87637949 | v7.4 | Own Board-out | 5 | 4 | L4 確定欠陥なし／回避可能性不明 | 明確なAI異常を特定せず |
| 87639017 | v7.4 | Opponent Prize | 6 | 4 | L4 確定欠陥なし／回避可能性不明 | Crispinによる即時攻撃解禁疑い。効果再現前は未確定 |
| 87639549 | v7.4 | Opponent Prize | 6 | 1 | L1 即時勝利の見逃しを証明 | T12: Active Mega Froslass exへW AttachでAlakazam HP140を950 damage相当でKO可能。自分の残りPrizeは1枚で、通常Pokémon KOの1 Prizeにより即時勝利が成立。 |
| 87640085 | v7.4 | Opponent Prize | 10 | 2 | L4 確定欠陥なし／回避可能性不明 | Attack前Attach未使用が多いが、生件数だけでは異常判定不可 |
| 87642752 | v7.4 | Opponent Prize | 6 | 3 | L3 局所的な確定損失（勝敗影響不明） | T1 Attach→有償RetreatでEnergy喪失 |
| 87643286 | v7.4 | Opponent Prize | 5 | 5 | L2 強い確定損失（勝敗反転は未証明） | T10 Active FroslassへのW AttachでArchaludon ex HP100を200 damageで即時KO可能だが見逃し |
| 87643350 | v7.4 | Opponent Prize | 8 | 3 | L4 確定欠陥なし／回避可能性不明 | Cape・Attach未使用候補。生存価値をコード再現前は未確定 |
| 87644371 | v7.4 | Opponent Prize | 8 | 6 | L2 強い確定損失（勝敗反転は未証明） | T10 Active FroslassへのW AttachでTeal Mask Ogerpon ex HP160を200 damageで即時KO可能だが見逃し（T4/T6進化残存穴も併存） |
| 87645438 | v7.4 | Own Board-out | 9 | 3 | L3 局所的な確定損失（勝敗影響不明） | T1 Attach→有償RetreatでEnergy喪失 |
| 87646047 | v7.4 | Opponent Prize | 10 | 6 | L4 確定欠陥なし／回避可能性不明 | 低HPでWally未使用候補。相手の次Turn damage再現前は未確定 |
| 87650661 | v7.4 | Opponent Prize | 6 | 5 | L4 確定欠陥なし／回避可能性不明 | Attack前Attach未使用候補。勝敗直結度は未確定 |
| 87665056 | v7.4 | Own Board-out | 1 | 6 | L4 確定欠陥なし／回避可能性不明 | 自Turnが実質1回の短期Board-out。判断材料が少なく、明確な欠陥を特定せず |

### 1.4 観測勝率へ変換できる範囲

- self-playを除く観測成績は **29勝38敗、43.3%**。
- `L1`の1敗だけをReplay上で直接反転可能と扱うと、同じ67戦を仮に置き換えた算術値は **30勝37敗、44.8%**。これは将来勝率の推定ではなく、確認済み1試合だけを反転した計算。
- `L1+L2`の9敗すべてが勝利へ変わると仮定した56.7%は、反実仮想を証明していないため**上限シナリオにすら近い参考値**であり、予測として使用しない。
- 確定損失を含む19敗をすべて勝利換算することは不正。局所損失の修正が勝敗を変えない試合も当然含まれる。

### 1.5 この項目から確定できること

1. 現デッキには実際の攻撃勝ち筋がある。対外29勝中26勝はPrizeまたはBoard-outをAttackで完了している。
2. 勝利の41.4%（12/29）にも確定損失があるため、勝利Replayを正常系として一括保護してはいけない。
3. 敗戦38件中19件には確定損失があるが、勝敗反転まで証明できるのは現時点で1件のみ。
4. v7.4ではIssue5対象の局所進化ミスは減ったが、より強い即時KO・access・ineffective attack問題は残っている。
5. 「現デッキを変えるべき」という証拠はこの項目からは出ていない。むしろ、攻撃終結型の勝利が多数あるため、Policy修正前にデッキを変更すると原因分離を失う。

### 1.6 不明として残す事項

- Board-out勝利における相手事故・相手Policyミスの寄与。
- `L2/L3`を修正した場合に実際に何敗が勝利へ変わるか。
- `L4`の19敗が、ドロー事故・構築相性・未発見Policy欠陥のどれに属するか。
- 相手強度とマッチング分布がv7.3/v7.4で同等か。

### 状態

**研究項目1 完了。**

---

## 2. ActionScoreの順位差・field差

### 状態

研究項目2を完了。ReplayにActionScoreそのものは保存されていないため、ここでは**Replayの公開状態と提供済みソーススナップショットからスコアを再構成**した。Replay事実と再構成値を混同しない。

### 2.1 監査方法と証拠限界

使用した順位キーは、提供ソース内の `_result_key()` に記載された辞書式比較である。

```text
Tier
→ Immediate
→ Pressure
→ Development
→ Resource
→ -Risk
→ Outcome supported
→ Win
→ KO
→ Prizes
→ not Blocked
→ Enables KO
→ Enables Attack
→ Improves Damage
→ Damage
→ Energy loss / Retreat cost
→ Legacy
→ -Option index
```

この順序では、**上位fieldで差が付いた時点で、それより下位の数値は順位を覆せない**。例えばTier30の候補は、Resourceがどれほど低くてもTier20より上に並ぶ。

再構成の検証結果は次のとおり。

| 対象 | rank可能Main node | 再構成top1＝実選択 | 一致率 |
|---|---:|---:|---:|
| v7.3 | 890 | 878 | 98.7% |
| v7.4 | 649 | 626 | 96.5% |
| 合計 | **1,539** | **1,504** | **97.7%** |

- 全1,540 Main nodeのうち、`87491060`の終端1 nodeは次frameに選択記録がなく、順位との照合不能。
- 不一致35 nodeは、以下の精密な数値診断から除外した。
- 提供ソースが提出時コードとbyte単位で同一かは確認不能。
- 相手カードの一部metadataはReplayから復元している。したがって、再構成一致率は高いが、**submission実行時の内部ActionScoreを直接取得した証拠ではない**。
- 以下の個別確定表は、再構成top1が実選択と一致したnodeだけを使用した。

### 2.2 top1とtop2を最初に分けたfield

比較可能だった1,404 nodeについて、top1とtop2の `_result_key()` を先頭から比較した。

| 最初に差が付いたfield | node | 割合 |
|---|---:|---:|
| Tier | 630 | 44.9% |
| Resource | 446 | 31.8% |
| Option indexのみ | 169 | 12.0% |
| Development | 61 | 4.3% |
| Legacy | 44 | 3.1% |
| Outcome supported | 32 | 2.3% |
| Pressure | 21 | 1.5% |
| Enables Attack | 1 | 0.1% |
| **合計** | **1,404** | **100.0%** |

主要な事実は次の三点。

1. **44.9%はTierだけで決着**している。
2. 同Tier内ではResourceが最大の決定要因で、全体の31.8%を占める。
3. 169 nodeは全スコアfieldが同値で、最終的にOption indexだけで決まった。

Top2が同Tierだったのは、v7.3で461/819、v7.4で313/585、合計774/1,404（55.1%）。つまりTier支配は強いが、過半数では同Tier内比較も発生している。

field差の中央値は、Tier差10、Resource差56,000、Development差15,000、Legacy差15,900だった。field間の数値単位は異なるため、これらを横断して大小比較してはいけない。

#### top1のTier分布

| Version | Tier20 | Tier30 | Tier40 | Tier60 | Tier70 | 合計 |
|---|---:|---:|---:|---:|---:|---:|
| v7.3 | 498 | 153 | 151 | 65 | 11 | 878 |
| v7.4 | 373 | 125 | 97 | 29 | 2 | 626 |

対戦盤面の母集団が異なるため、この分布差だけからIssue5の効果や劣化を推定しない。

### 2.3 Attachで即時KO／Win攻撃が解禁される8 node

Replay監査で確認済みの8件について、Active Mega Froslass exへの水Attachと、実際に選ばれたAttachを比較した。

全8件で、Active Attach候補は以下の同一構造だった。

```text
Tier20
Immediate 0
Pressure 0
Development 0
Damage 0
KO false
Prizes 0
Win false
Enables Attack true（attack #1240）
```

つまり、攻撃が解禁されること自体は認識しているが、**解禁後のdamage・KO・Prize・WinはAttach候補へ伝播していない**。

| Episode | Turn / Frame | 実選択 | 実選択Resource | Active Froslass Attach rank | Active Attach Resource | Resource差 |
|---|---|---|---:|---:|---:|---:|
| 87488357 | T15 / F108 | ATTACH Basic {W} Energy -> Mega Starmie ex#7 | 230,000 | 2 | 140,000 | 90,000 |
| 87488357 | T17 / F119 | ATTACH Basic {W} Energy -> Mega Starmie ex#7 | 365,000 | 2 | 140,000 | 225,000 |
| 87495871 | T14 / F66 | ATTACH Basic {W} Energy -> Mega Starmie ex#66 | 365,000 | 3 | 140,000 | 225,000 |
| 87495871 | T16 / F84 | ATTACH Basic {W} Energy -> Mega Starmie ex#66 | 230,000 | 3 | 140,000 | 90,000 |
| 87630981 | T17 / F123 | ATTACH Basic {W} Energy -> Mega Starmie ex#6 | 230,000 | 3 | 160,000 | 70,000 |
| 87639549 | T12 / F107 | ATTACH Basic {W} Energy -> Mega Starmie ex#67 | 365,000 | 2 | 160,000 | 205,000 |
| 87643286 | T10 / F57 | ATTACH Basic {W} Energy -> Staryu#64 | 175,000 | 2 | 140,000 | 35,000 |
| 87644371 | T10 / F62 | ATTACH Basic {W} Energy -> Mega Starmie ex#66 | 365,000 | 2 | 140,000 | 225,000 |

- 8件すべて同じTier20で、最初に差が付いたfieldは**Resource**。
- Resource差は35,000～225,000、中央値147,500。
- `87639549 T12`は残りPrize 1であり、Active Attach後の攻撃が即時勝利へつながる盤面だったが、Attach評価上はWin falseのまま。
- rankはOption単位。水Energyや同対象の重複Optionがあるnodeでは、同じ概念候補が複数順位を占める。

この8件については「Attach一般の価値が低い」のではなく、**Attach後に合法化されるAttack Outcomeが早いfieldへ載っていないため、同TierのBench育成Resourceに負けた**と特定できる。

### 2.4 実damage 0 Attackの二種類

Replay上の実damage 0 Attackは10 nodeだった。スコア再構成により、同じ見た目でも内部原因が二種類に分かれた。

| Episode | Turn / Frame | Attack再構成値 | 最上位の非Attack候補 | Replayとの関係 |
|---|---|---|---|---|
| 87632037 | T7 / F49 | Tier30 / damage 0 / pressure 0 | ATTACH Basic {W} Energy -> Mega Starmie ex#6（rank 2、Tier20） | Replay実damage 0と再構成評価が一致 |
| 87632037 | T9 / F56 | Tier30 / damage 0 / pressure 0 | ATTACH Basic {W} Energy -> Mega Starmie ex#6（rank 2、Tier20） | Replay実damage 0と再構成評価が一致 |
| 87638484 | T6 / F36 | Tier60 / damage 50 / KO=True | ATTACH Ignition Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T8 / F50 | Tier60 / damage 50 / KO=True | ATTACH Ignition Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T10 / F56 | Tier60 / damage 50 / KO=True | ATTACH Ignition Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T12 / F62 | Tier60 / damage 50 / KO=True | ATTACH Ignition Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T14 / F69 | Tier60 / damage 50 / KO=True | ATTACH Ignition Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T16 / F74 | Tier60 / damage 50 / KO=True | ATTACH Basic {D} Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T18 / F79 | Tier60 / damage 50 / KO=True | ATTACH Basic {D} Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |
| 87638484 | T20 / F84 | Tier60 / damage 50 / KO=True | ATTACH Basic {D} Energy -> Mega Starmie ex#67（rank 2、Tier20） | Replay実damage 0だが再構成評価は50 damage KO |

#### A. `87632037 T7/T9`

- Replay実damage 0。
- 再構成側もdamage 0、Pressure 0、Tier30。
- Mega Starmie exへの水AttachはNebula Beamを解禁するがTier20。
- 最初の差はTierなので、AttachのResource 365,000は比較まで到達しない。

これは、**効果のない通常AttackがTier30であるため、攻撃準備Tier20を辞書式に打ち切る**問題として再構成できた。

#### B. `87638484 T6～T20`の8回

- Replayでは、相手Active Comfeyに対して8回連続で`HpChange value=0`。
- しかし提供ソースによる再構成は、各回を50 damage・KO・1 Prize・Tier60と評価した。
- そのため、これは単なる「0 damage AttackにもTier30を与えた」問題ではない。
- **評価器が実エンジンで0になる相互作用を認識せず、KOと誤認していた**ことが順位を固定している。

Comfeyが0 damageになった正確なカード効果・継続効果の起点は、Replay JSONと提供ソースだけでは確定できないため不明とする。GenericなAttack Tierだけを下げても、この8件は評価器上Tier60のままであり、根本修正にならない。

### 2.5 Issue5の同一盤面counterfactual

提供されたv7.3ソースにIssue5差分だけを適用し、v7.3の890 rank可能Main nodeを同じ盤面のまま再評価した。

- top1が変化したのは**7 node**。
- 7 nodeは4 Turnに属する。
  - `87485611 T13`
  - `87486157 T4`
  - `87490505 T12`（同Turn内4 node）
  - `87493732 T3`
- 新しいtop1は7 nodeすべてActive進化。
- 変化内訳はAttack→Evolve 2、Play→Evolve 3、Bench Evolve→Active Evolve 2。
- この再構成では、上記以外のv7.3 nodeでtop1変更を検出しなかった。

したがって、Issue5差分の直接的な影響半径は**狭く、意図したActive進化へ限定されていた**。ただし提出時コードとのbyte同一性が未確認なので、これは提供ソース上のcounterfactualであり、Kaggle実行そのものの完全再現ではない。

#### 残存範囲

v7.3で既に監査済みのActive進化見逃し13 Turnのうち、同一盤面counterfactualでtop1が変わったのは4 Turn。残る9 Turnは変化しなかった。

理由を再構成できた代表例は次のとおり。

- Staryuの現Attack 10 → Mega Starmie ex進化後50：増加40。
- Issue5の昇格条件はdamage増加50以上、またはKO／Win／blocked解消。
- 増加40でKOしない盤面は条件を満たさず、Active進化はTier20のまま。
- `87644371 T4/T6`ではSnoruntの30 → Mega Froslass exの50で増加20。これも条件未達で、v7.4残存nodeを説明できる。

この結果から、Issue5は「Active進化全般」を直したのではなく、**明確なKOまたは50以上のdamage改善だけをTier40へ上げる限定修正**だったと確認できる。

### 2.6 完全同点とOption index依存

Top1とTop2がOption index以外すべて同値だった169 nodeの内訳は次のとおり。

| 組み合わせ | node |
|---|---:|
| Attach vs Attach | 100 |
| Play vs Play | 40 |
| Evolve vs Evolve | 29 |

多くは、同名カードを同種の複数個体へ使う重複候補だった。異なるtarget serial同士の同点は76 nodeあったが、serialが異なるだけで同種・同役割の候補も多く、76件をそのまま誤選択とは扱わない。

明確にtarget種が異なるHero’s Cape同点は2件あった。

- `87488357 T15`: Mega Froslass ex vs Mega Starmie ex
- `87640085 T5`: Mega Froslass ex vs Mega Starmie ex

どちらもTier20、Resource 90,000で、再構成ImmediateOutcomeはunsupported。どちらへ付けるべきかは次Turnの生存計算を行わない限り確定できないため、ここでは**target差を評価していない事実だけ**を記録し、誤選択とは判定しない。

### 2.7 この項目から確定できること

1. 現行順位はTierの影響が最大で、同Tier内ではResourceが最大の決定要因。
2. Attach即時KO／Win見逃し8件は、攻撃解禁自体は検知しているが、その先のOutcomeがAttach候補へ伝播せず、Resource比較で敗れている。
3. 実damage 0 Attackは一種類ではない。2件はTier30による準備打ち切り、8件は実エンジンとのOutcome認識不一致。
4. Issue5差分は提供ソース上で7/890 nodeだけを変え、変更先はすべてActive進化だった。
5. Issue5の閾値により、damage改善40以下のActive進化は依然Tier20に残る。
6. 169 nodeは意味的評価ではなくOption indexで決着しているが、その大半を異常とは断定できない。

### 2.8 修正時の監査条件

- Attach即時KO修正では、Attach自体を「既にKOした」と誤表示せず、**同Turnに実行可能な後続Attackへの到達価値**として表現する必要がある。
- 現在実行可能なKO／Win Attackを、準備Attachが逆転してはならない。
- 0 damage対策は、`87632037`型と`87638484`型を分ける。後者はOutcomeモデルの不足を直さない限りTier調整では解消しない。
- Issue5の追加調整では、40 damage改善を一律昇格すると正常nodeも動く可能性があるため、全Corpus順位差分が必要。
- Option index同点を解消する場合、serial順を別の固定順へ置換するだけでは意味改善にならない。生存・Energy・accessなどの差を上位fieldへ載せる必要がある。

### 2.9 不明として残す事項

- 提供ソースと各提出物の完全なsource hash一致。
- 再構成不一致35 nodeの個別原因。
- `87638484`でComfeyへのdamageが0になった正確なルール／継続効果。
- Hero’s Cape同点2件で、どちらのtargetが実際に優位だったか。
- Issue5閾値を40へ下げた場合の全1,540 nodeへの影響。これは研究項目9の感度分析で扱う。

### 状態

**研究項目2 完了。**

---

## 3. 複合行動経路

### 状態

研究項目3を完了。ここでは、同一Turn内で複数のMain行動を経てAttackへ到達する経路を監査した。

### 3.1 判定方法と限界

- 1 Turn内のMain選択を実行順に並べ、最初のAttackまでに選ばれた行動をprefixとして記録した。
- `AttackがTurn開始時には合法でなく、途中から合法になった`ことは、各Main nodeの合法Optionで判定した。
- **直接unlock行動**は、次のMain nodeでAttackが初めて合法になった直前の実行行動と定義した。
- prefix長は実際に選ばれた行動数であり、最短経路ではない。Search・Draw・盤面展開など、Attack解禁に不要だった可能性のある行動も含む。
- 未選択経路は、公開盤面、合法Option、既知のカード効果、同一Replay内の成功例で到達可能性を確認できたものだけを「確定」とした。
- Replayに存在しない分岐を、最終結果から逆算して補完していない。

### 3.2 実際に実行されたAttack経路

561自Turn中、Attackを実行したTurnは407だった。

| Attack前のMain行動数 | Attack Turn数 |
|---:|---:|
| 0 | 185 |
| 1 | 88 |
| 2 | 56 |
| 3 | 38 |
| 4 | 20 |
| 5 | 17 |
| 6 | 2 |
| 7 | 1 |
| **合計** | **407** |

- **222/407 Attack（54.5%）**は、Attack前に1行動以上を実行していた。
- **115/407 Attack（28.3%）**は、Turn開始時にAttackが合法でなく、同Turn内の行動によってAttackへ到達した。
- 115件は全561自Turnの20.5%に相当する。
- Attack前に3行動以上あったものは78件、4行動以上は40件。

したがって、このデッキにおける複合経路は例外ではない。ただし、長いprefixの全行動が攻撃に必要だったとは限らない。

### 3.3 Attackを直接合法化した行動

Turn開始時にAttackが存在しなかった115件について、Attackが初めて合法になった直前の行動を集計した。

| 直接unlock行動 | 件数 |
|---|---:|
| Basic {W} Energy Attach | 64 |
| Retreat | 27 |
| Surfing Beach Ability | 14 |
| Basic {D} Energy Attach | 4 |
| Ignition Energy Attach | 3 |
| Energy Switch | 2 |
| Crispin | 1 |
| **合計** | **115** |

まとめると、

- Energy Attach系: **71件**
- Retreat／Surfing Beachによる交代: **41件**
- Energy Switch: 2件
- Crispin: 1件

だった。

これは「Attach価値」と「Active access価値」が独立した周辺要素ではなく、実際の攻撃成立に直接使われていることを示す。

### 3.4 Productive switch経路

Attack前に自分のActiveが交代した実経路は43件あった。

| 交代手段 | 実経路数 | Turn開始時Attackなし | 交代が直接unlock | 実damage > 0 | Prize取得 |
|---|---:|---:|---:|---:|---:|
| Retreat | 28 | 27 | 27 | 28 | 12 |
| Surfing Beach | 15 | 15 | 14 | 15 | 11 |
| **合計** | **43** | **42** | **41** | **43** | **23** |

- 43件すべてで実damageが発生した。
- 23/43件でPrizeを取得した。
- Surfing Beachを使った1件は、交代後の別行動が最終的なAttack unlockになったため、`Turn開始時Attackなし=15`に対して`直接unlock=14`となる。
- Retreatの1件はTurn開始時からAttackが合法だったが、交代後に別attackerで攻撃した。

したがって、RetreatやSurfing Beachを一律に下げる修正は正常な勝ち筋を壊す。

#### 代表的な正常経路

| Replay | Turn | 実経路 | 実結果 |
|---:|---:|---|---|
| 87482904 | T15 | W Attach to Mega Froslass → Retreat → Resentful Refrain | 350 damage、3 Prize、勝利終結 |
| 87483996 | T2 | Staryu展開 → Salvatore → W Attach → Retreat → Jetting Blow | 170 damage、1 Prize |
| 87488357 | T19 | Energy Switch → Resentful Refrain | 350 damage、1 Prize |
| 87634201 | T8 | Salvatore → W Attach → Retreat → Jetting Blow | 120 damage、3 Prize、勝利終結 |
| 87637402 | T13 | W Attach → Boss’s Orders → Jetting Blow | 120 damage、1 Prize |
| 87640085 | T13 | Attach・進化・Wally・Surfing Beachを経てJetting Blow | 170 damage、3 Prize |

### 3.5 Active進化を含む実経路

Active進化後に同TurnでAttackした経路は11件あった。

- 11件中7件はTurn開始時にAttackが合法でなかった。
- 11件中6件でPrizeを取得した。
- Active進化そのものが直接unlockだったとは限らない。進化後のAttachが直接unlockとなる経路や、Basic時点でも低打点Attackは合法だった経路が含まれる。

このため、Active進化は単純なDevelopment行動ではなく、同Turnのattacker・damage・Prize経路の一部として評価する必要がある。

### 3.6 確定した未選択の複合経路

同一Turn内に合法な改善経路があったのに、終端Attackまたは別行動で打ち切ったものとして、**13 node・9 Replay**を確定できた。

| 経路型 | node | Replay | 内容 |
|---|---:|---:|---|
| Active FroslassへW Attach → Attack | 8 | 6 | 即時KOまたはWin攻撃を解禁するが、別Attach／Developmentを選択 |
| Bench StarmieへW Attach → Surfing Beach → Attack | 2 | 1 | 0 damage Froslass Attackを選び、同TurnのStarmie攻撃経路を打ち切る |
| Bench FroslassへW Attach → Retreat → Attack | 2 | 1 | 20 damage Water Gunを選び、Froslassによる即時KOを逃す |
| Retreat → powered Froslass → Attack | 1 | 1 | Yveltal 40 damageを選び、Froslassによる即時KOを逃す |
| **合計** | **13** | **9** |  |

#### `87482904 T11/T13`

T11:

- Active: Yveltal
- Bench: Mega Froslass ex E0、Staryu E0
- 相手Active: Mega Abomasnow ex HP130
- 相手公開handCount: 9
- W AttachとRetreatが合法
- 実際はStaryuへW Attach → Retreat → Water Gun 20
- FroslassへW Attach → Retreat → Resentful Refrainなら、公開情報上450 damageでKO可能

T13:

- 相手Active: Mega Abomasnow ex HP110
- 相手公開handCount: 7
- 実際は別StaryuへW Attach → Retreat → Water Gun 20
- Froslass経路なら350 damageでKO可能

同ReplayのT15では、実際に`FroslassへW Attach → Retreat → Resentful Refrain`を実行し、350 damage・3 Prizeで勝利した。したがってT11/T13の経路は、カード効果を推測しただけではなく、同一Replay内の実成功経路でも確認できる。

#### `87491060 T9`

- Active: Yveltal、Basic {D} Energy付き
- Bench: Mega Froslass ex、Basic {W} Energy付き
- 相手Active: Alakazam HP140
- 相手公開handCount: 12
- Retreatが合法
- 実際はYveltal Attack 40
- Retreat → Froslass → Resentful Refrainなら、公開情報上600 damageでKO可能

T11では実際にFroslassへ交代し、Resentful Refrain 650 damageでPrizeを取得している。

#### `87632037 T7/T9`

- Active FroslassのResentful Refrainは相手handCount 0により実damage 0。
- Bench Mega Starmie exへのW Attach、Surfing Beach Ability、Retreatが合法。
- 実際は未使用Attachを残して0 damage Attackを選び、Turnを終了した。
- T7/T9とも、少なくとも`Bench StarmieへW Attach → Surfing Beach → StarmieのAttack`という同Turn経路が存在した。

正確な最善Attackと最終勝敗への影響は不明だが、0 damageでTurnを終えるより攻撃可能なStarmieへ到達する経路が存在したことは確定できる。

### 3.7 有害な複合経路: Attach → 有償Retreat → 攻撃なし

同TurnにActiveへEnergyをAttachし、そのEnergyをRetreat Costとして失い、後続Attackもなかった経路は14件あった。

| Version | 件数 |
|---|---:|
| v7.3 | 6 |
| v7.4 | 8 |
| **合計** | **14** |

- 勝利Replay: 7件
- 敗戦Replay: 7件

勝利側にも半数存在するため、勝敗ラベルだけでは検出できない資源損失である。

対象Replay／Turn:

```text
87480740 T1
87487251 T1
87488357 T1
87491060 T1
87494261 T1
87494795 T1
87630981 T1
87631518 T2
87632037 T1
87636873 T1
87637402 T1
87642240 T1
87642752 T1
87645438 T1
```

一方、43件のproductive switch→Attack経路が存在するため、修正対象はRetreat自体ではなく、

> 同Turnに付けたEnergyを実際に失い、Attack・KO・access改善・生存改善の確認可能な利益がない経路

に限定する必要がある。

### 3.8 Reachable missとHard deadlockの分離

複合経路問題は二種類ある。

#### A. Reachable miss

そのTurnに合法な複合経路が存在するが、途中の行動順位または終端Attackにより選ばれない。

- Active Froslass Attach → Attack
- Attach Bench attacker → Surfing Beach／Retreat → Attack
- Retreat → powered attacker → Attack

本項目で確定した13 nodeはこちらに属する。

#### B. Hard access deadlock

powered attackerがBenchにいても、Attack・Retreat・Surfing Beachの合法経路が存在せず、そのTurnの順位調整だけでは攻撃へ到達できない。

既存の全件手動監査で確定済みの強いclusterは、次の15 Turn・5 Replay。

```text
87487796 T3/T5/T7
87488357 T3/T5/T7
87491060 T5/T7
87521331 T12/T14/T16/T18/T20
87642240 T7/T9
```

この型は、dead TurnでRetreat点を上げても修正できない。以前のTurnで、Active側の交代Energy、Surfing Beach条件、Wally、またはattacker配置を維持する必要がある。

### 3.9 設計上の結論

1. 現デッキは複合経路への依存が高い。407 Attack中222件に前処理があり、115件は前処理なしではAttack自体が合法にならなかった。
2. 現在の重要欠陥は単一Actionの価値不足だけではなく、`Action AがAction Bを可能にし、BがAttackを可能にする`連鎖の未評価。
3. 確定missには、1準備行動の経路と2準備行動の経路がある。
   - Attach → Attack
   - Retreat → Attack
   - Attach → Retreat／Surfing Beach → Attack
4. したがって、Attach・Retreatへ固定bonusを加えるだけでは不十分。到達可能な後続Attack、damage、KO、Prize、Winまで経路として評価する必要がある。
5. ただし、準備行動を「既にdamageを与えた」と扱ってはならない。将来到達価値と現在の実Outcomeを分離する必要がある。
6. Hard deadlockは現在nodeのActionScoreだけでなく、前Turnの資源分配・access維持を監査対象にする必要がある。

### 3.10 修正後の回帰Guard

最低限、以下を別々に保護する。

#### 変更されるべき経路

- 8件のActive Froslass W Attach → 即時KO／Win Attack
- `87482904 T11/T13`のFroslass Attach → Retreat → KO
- `87491060 T9`のRetreat → Froslass → KO
- `87632037 T7/T9`の0 damage Attackより先に行うStarmie Attach → Surfing Beach → Attack
- 14件のAttach直後有償Retreat浪費

#### 維持されるべき経路

- 28件のRetreat → positive damage Attack
- 15件のSurfing Beach → positive damage Attack
- 11件のActive進化 → Attack
- `87637402 T13`のAttach → Boss’s Orders → Prize Attack
- `87488357 T19`のEnergy Switch → Prize Attack
- `87482904 T15`のAttach → Retreat → 3 Prize Attack

テストは最初のActionだけで終了せず、

```text
初期合法Option
→ 選択Action
→ 中間盤面
→ 次の合法Option
→ 最終Attack
→ damage / KO / Prize / Win
```

まで確認する必要がある。

### 3.11 不明として残す事項

- 222件のprefixについて、どの前処理が最短経路に必須だったか。
- 確定13 node以外に存在する未発見のcounterfactual経路数。
- Hard deadlockを防ぐ最適な前Turn行動。複数の合法な予防経路があり得る。
- 複合経路を汎用探索で扱うべきか、Attach／Switchなど限定helperで扱うべきか。これはコード複雑度と実行時間を含めた設計判断になる。

### 状態

**研究項目3 完了。**

---

## 4. カード別の実利用価値

### 4.1 対象と測定定義

対象は既存の68 Replay、561自Turn、1,540 Main node、407 Attackである。68 ReplayすべてでYser側のデッキ60枚は同一だった。

本項目では、Replayから直接確認できる利用実績を集計した。用語は次のとおり。

- **Hand-observed copies**: Replay state上で一度以上手札に存在した、Episode内serial単位の異なるカード枚数。
- **Distinct used/deployed copies**: setup配置、Play、Attach、Evolveのいずれかで実際に使用された、Episode内serial単位の異なるカード枚数。
- **Used/legal turns**: そのカードのMain行動を少なくとも1回選んだTurn数／そのカードを使う合法Optionが少なくとも1回存在したTurn数。
- **Pre-attack / Pre-prize sequence**: そのカードを使用した後、同Turn中にAttack／Prize取得Attackへ進んだ行動回数。
- **Final-hand copies**: 終局時の手札に残っていた枚数。
- **All-copies prized games**: 初期Prizeにデッキ内の全コピーが入っていた試合数。

`Pre-attack`は同一Turn内の順序関係であり、カード使用がAttackを因果的に可能にしたことまでは意味しない。初期Prizeの中身はReplay後の観測情報であり、Policy判断時には利用できない。

### 4.2 Pokémonとattackerの実利用

| Card             |   Copies |   Hand-observed copies |   Distinct deployed copies | Setup/Main uses   |   Final-hand copies |   Attacks |   Positive attacks |   Damage |   Prizes |
|:-----------------|---------:|-----------------------:|---------------------------:|:------------------|--------------------:|----------:|-------------------:|---------:|---------:|
| Cinderace        |        3 |                    101 |                         28 | 28/0              |                  52 |        71 |                 71 |     4150 |       23 |
| Staryu           |        3 |                    115 |                        109 | 34/80             |                   4 |        58 |                 58 |     1180 |        2 |
| Snorunt          |        4 |                    128 |                         69 | 39/31             |                  30 |        18 |                 17 |      170 |        0 |
| Mega Starmie ex  |        2 |                     80 |                         63 | 0/63              |                   8 |       210 |                202 |    35630 |      171 |
| Mega Froslass ex |        2 |                     74 |                         29 | 0/29              |                  17 |        36 |                 33 |    12850 |       33 |
| Yveltal          |        1 |                     32 |                         14 | 10/4              |                  10 |        12 |                 12 |      320 |        2 |
| Shaymin          |        1 |                     36 |                         15 | 9/6               |                  11 |         2 |                  2 |       90 |        0 |

#### 確認できる事実

1. **Mega Starmie exが主力attackerである。**
   - 210 Attack
   - positive damage 202回
   - 合計35,630 damage
   - 171 Prize
   - 1 Attack当たり平均169.7 damage、0.814 Prize

2. **Mega Froslass exは使用回数が少ない一方、1回当たりの実績が高い。**
   - 36 Attack
   - positive damage 33回
   - 合計12,850 damage
   - 33 Prize
   - 1 Attack当たり平均356.9 damage、0.917 Prize

   したがって、FroslassはReplay上で「機能していないカード」ではない。起動・Attach・Active accessを通せた場合の出力は高い。

3. **Cinderaceはsetup依存の役割になっている。**
   - setup配置28回
   - Main中のPlay合法TurnおよびPlay選択は0
   - 71 Attack、23 Prize
   - Hand-observed 101枚のうち52枚が終局時手札に残った

   Replayから確認できるのは、Cinderaceが初期配置された場合には攻撃・中継役として機能する一方、試合開始後に手札から展開された例がないことまでである。カードルール上の制約か、全該当盤面で別条件が不足したのかは未確認。

4. **Staryuは展開カードとして高頻度に消費されるが、Basic AttackのPrize寄与は小さい。**
   - 異なる109枚が配置・使用
   - 58 Attack、2 Prize
   - 終局時残存は4枚

5. **Snoruntは配置数に対して進化・攻撃接続が弱い。**
   - 異なる69枚が配置・使用
   - 18 Attack、0 Prize
   - 終局時30枚残存

   ただし、Snorunt自体を減らせるかは、Froslassの起動率・初手Basic率を別項目で確認しないと判断できない。

6. YveltalとShayminは採用1枚で、実際の配置はそれぞれ14枚、15枚。攻撃PrizeはYveltal 2、Shaymin 0だった。壁・初手・補助価値はこのAttack集計だけでは測れない。

### 4.3 Trainer・Energy・Stadiumの利用

| Card                   |   Copies |   Hand-observed copies |   Distinct used copies | Used/legal turns          |   Pre-attack seq |   Pre-prize seq |   Final-hand copies |   All-copies prized games |
|:-----------------------|---------:|-----------------------:|-----------------------:|:--------------------------|-----------------:|----------------:|--------------------:|--------------------------:|
| Basic {W} Energy       |        8 |                    264 |                    155 | 166/372                   |               91 |              35 |                  79 |                         0 |
| Basic {D} Energy       |        2 |                     57 |                     23 | 23/120                    |                7 |               1 |                  21 |                         0 |
| Ignition Energy        |        1 |                     34 |                     11 | 11/74                     |                7 |               5 |                  11 |                         8 |
| Salvatore              |        2 |                     70 |                     53 | 53/74                     |               33 |              14 |                   9 |                         1 |
| Lillie's Determination |        4 |                    132 |                     63 | 63/172                    |               45 |               7 |                  36 |                         0 |
| Crispin                |        2 |                     69 |                     32 | 32/134                    |               22 |               7 |                  15 |                         1 |
| Hilda                  |        1 |                     30 |                     18 | 18/37                     |               15 |               2 |                   2 |                         3 |
| Boss’s Orders          |        2 |                     63 |                      2 | 2/162                     |                1 |               1 |                  22 |                         1 |
| Wally's Compassion     |        2 |                     58 |                     11 | 11/77                     |                2 |               1 |                  25 |                         2 |
| Ultra Ball             |        3 |                    103 |                     67 | 64/152                    |               38 |               4 |                  25 |                         0 |
| Buddy-Buddy Poffin     |        3 |                     80 |                     50 | 47/137                    |               19 |               2 |                  19 |                         0 |
| Pokégear 3.0           |        3 |                     94 |                     45 | 40/171                    |                6 |               4 |                  32 |                         0 |
| Night Stretcher        |        2 |                     61 |                     37 | 37/90                     |               21 |               1 |                  16 |                         1 |
| Poké Pad               |        2 |                     57 |                     30 | 28/104                    |               11 |               0 |                  13 |                         1 |
| Tool Scrapper          |        2 |                     63 |                     12 | 11/37                     |                4 |               1 |                  30 |                         0 |
| Energy Switch          |        1 |                     24 |                      6 | 6/39                      |                2 |               1 |                   7 |                        10 |
| Mega Signal            |        1 |                     27 |                     11 | 11/68                     |                4 |               1 |                  10 |                         7 |
| Surfing Beach          |        2 |                     58 |                     19 | 19/91 play; 34/71 ability |               21 |              16 |                  18 |                         1 |
| Hero’s Cape            |        1 |                     37 |                     12 | 12/139                    |                3 |               2 |                  15 |                         4 |

`Used/legal turns`は同一Turn中に同名カードを複数回使った場合でも使用Turnを1としている。`Distinct used copies`はserial単位であり、回収した同じEnergyを再Attachした場合は1枚として数える。

#### 利用傾向

1. **Basic Water Energyが行動連結の中心である。**
   - 166 Attach
   - 91回が同Turn Attack前
   - 35回が同Turn Prize Attack前
   - 一方で79枚が終局時手札に残った

   ただし、既知のAttach即時KO欠落とAttach→有償Retreat浪費が含まれるため、Attach回数の多さをそのまま適正利用とは扱えない。

2. **Salvatoreは最も高い使用転換率を持つ主要Supporterである。**
   - 74合法Turn中53使用Turn
   - 33回が同Turn Attack前
   - 14回が同Turn Prize Attack前

3. **Surfing Beachは配置後のabilityが実際に勝ち筋へ接続している。**
   - Stadium Play 19回
   - ability Switch 34回
   - ability使用後の同Turn Attack 21回
   - 同Turn Prize Attack 16回

   既知のActive access問題があるため、Surfing Beachは不要カードではなく、使える盤面と使えない盤面の差が重要である。

4. **Boss’s Ordersは極端に利用が少ない。**
   - 162合法Turn中2使用Turn
   - Hand-observed 63枚
   - 終局時22枚、20 Replayで残存
   - 2使用のうち1回は同Turn Prize Attackへ接続

   これはUnderuse調査候補である。ただし、合法であっても相手Benchを呼ぶ利益がない盤面を多数含むため、2/162だけでPolicy欠陥またはデッキ不要とは断定できない。

5. **Wally's CompassionとHero’s Capeは低頻度だが、利用価値がゼロとは言えない。**
   - Wally: 11使用、全11回で回復、合計1,950 HP回復
   - Wally使用後、次の自Turnまでに対象がdamageを受けて生存した例: 7
   - Cape: 12使用
   - Cape対象が次の自Turnまでにdamageを受けて生存した例: 2

   これらは「使用後に生存した」観測であり、使用しなければきぜつしたというcounterfactualは証明していない。

6. **Tool Scrapper、Energy Switch、Mega Signalは使用率が低く、終局時残存も多い。**
   - Tool Scrapper: 11/37使用Turn、終局時30枚
   - Energy Switch: 6/39使用Turn、終局時7枚
   - Mega Signal: 11/68使用Turn、終局時10枚

   ただし、Tool Scrapperは相手Tool、Energy Switchは盤面Energy、Mega Signalは進化先不足に依存するため、単純な使用率比較ではカード性能を判定できない。

### 4.4 直接確認できた効果解決

| Card                  |   Uses | Observed direct resolution                   | Same-turn attack/prize   |
|:----------------------|-------:|:---------------------------------------------|:-------------------------|
| Salvatore             |     53 | 49 Evolve logs; 4 without Evolve log         | 33 / 14                  |
| Crispin               |     32 | 22 Attach; 8 hand-only; 2 no energy movement | 22 / 7                   |
| Boss’s Orders         |      2 | 2 Switch logs                                | 1 / 1                    |
| Energy Switch         |      6 | 6 MoveAttached logs                          | 2 / 1                    |
| Wally's Compassion    |     11 | 11 heals; total +1950 HP                     | 2 / 1                    |
| Hero’s Cape           |     12 | 12 Attach logs                               | 3 / 2                    |
| Surfing Beach ability |     34 | 34 Switch logs                               | 21 / 16                  |
| Hilda                 |     18 | 36 deck→hand MoveCard logs                   | 15 / 2                   |
| Mega Signal           |     11 | 11 deck→hand moves (Starmie 7, Froslass 4)   | 4 / 1                    |
| Night Stretcher       |     37 | 37 discard→hand moves                        | 21 / 1                   |

#### 効果が完全には解決されなかった使用

Salvatoreは53使用中49回でEvolve logが発生し、次の4回ではEvolve logがなかった。

```text
87480598 T4
87491060 T15
87497826 T15
87639549 T6
```

Crispinは32使用中22回でAttach、8回でWater Energyを手札へ移動しただけ、2回ではEnergyのMoveCardもAttachも発生しなかった。

```text
87501720 T24
87501720 T28
```

これらはReplay上の効果結果である。対象不在、山札内対象不足、選択処理、またはPolicy上の空打ちのどれが原因かは、Replayだけでは確定していない。

### 4.5 初期Prize lock

全コピーが初期Prizeに入った回数が多いカードは次のとおり。

| Card | Copies in deck | All-copies prized games |
|---|---:|---:|
| Energy Switch | 1 | 10 |
| Yveltal | 1 | 10 |
| Ignition Energy | 1 | 8 |
| Mega Signal | 1 | 7 |
| Hero’s Cape | 1 | 4 |
| Shaymin | 1 | 4 |
| Hilda | 1 | 3 |
| Wally's Compassion | 2 | 2 |

これは実際の初期Prize配置であり、Policyが知り得た情報ではない。

既知のHard access deadlock 5 Replayと照合すると、

- `87491060`: Wally's Compassion 2枚がすべて初期Prize
- `87642240`: Surfing Beach 2枚中1枚が初期Prize
- `87487796`, `87488357`, `87521331`: access関連カードの全コピーlockは確認されない

したがって、Prize lockは一部Replayの制約にはなり得るが、Hard deadlock全体の一般原因ではない。`87491060`でも、WallyがPrizeでなければ必ずdeadlockを防げたかは不明である。

### 4.6 カード別監査からの結論

1. **現デッキの主力勝ち筋は実在する。**
   Mega Starmie exとMega Froslass exだけで204 Prizeを取得している。デッキ全体が出力不足という証拠ではない。

2. **Froslassは削除候補ではなく、到達失敗の影響を受けている高出力カードである。**
   Attach即時KO欠落とComposite access missを直す価値が、カード実績からも裏付けられる。

3. **Cinderace 3枚は構築上の調査候補である。**
   setup時の役割と71 Attackは確認できる一方、Mainからの展開例がなく52枚が終局時手札に残った。これは明確な手札占有事実だが、3枚採用を減らした場合の初手安定性低下はまだ測定していない。

4. **Boss’s OrdersはPolicy underuseと構築枠の両方を疑う対象である。**
   ただし、どちらが原因かは現段階で分離できない。まず合法時の相手Bench価値とAttack差分を監査する必要がある。

5. **低使用率カードをそのまま抜く判断はできない。**
   Wally、Cape、Tool Scrapper、Energy Switchは盤面依存が強く、使用頻度だけでは価値を決められない。実際、WallyとCapeには使用後の生存例、Energy SwitchにはPrize Attack接続例がある。

6. **カード利用の悪さとカード自体の悪さを分離する必要がある。**
   現在のPolicyはAttach、Active access、複合経路を落としているため、カード使用率はPolicy欠陥によって歪んでいる。P0～P2修正前にデッキを変更すると、構築とPolicyの原因が混ざる。

### 4.7 不明として残す事項

- 同Turn Attack前に使われた各カードが、そのAttackを因果的に可能にしたか。
- 終局時手札のカードが、使えなかったのか、使う必要がなかったのか。
- CinderaceにMain Play Optionが一度も出なかった正確なルール上・盤面上の理由。
- Salvatore 4回とCrispin 2回の不発原因。
- Wally／Capeがなければ実際にきぜつしていたか。
- 初期Prize lockが各試合の勝敗へ与えた影響。
- 採用枚数を変更したcounterfactual勝率。

### 状態

**研究項目4 完了。研究項目5は未着手。**

---

## 5. Attacker別の起動速度と効率

### 5.1 対象と測定定義

この項目では、主力候補である **Mega Starmie ex、Mega Froslass ex、Cinderace** を個体serial単位で追跡した。

- 起動・生存・勝敗比較は、mirror self-play `87480598`を除いた対外67 Replayを主対象とした。
- Item 4の全68 Replay集計との差を明示する必要がある箇所だけ、self-play込みの値も併記する。
- `deploy`は、その最終形態のserialがActiveまたはBenchへ初めて現れた時点とする。進化前Basicの配置時点へ遡らない。
- CinderaceはMain中のPlayが一度もなく、確認できた個体はsetup配置である。自分の最初のTurnを起動計測の基準Turn 1とした。
- 起動遅延は自分のTurn数で数える。同じTurnに進化・準備してAttackした場合は0 Turn。
- `Energy-ready`はカードテキストを外部補完せず、実際のAttack時に確認できた最小Energy状態から判定した。
  - Mega Starmie ex: Energy 1枚以上。Basic Water 1枚およびIgnition Energy 1枚のみでのAttack実績がある。
  - Mega Froslass ex: Basic Water Energy 1枚以上。今回確認した全AttackにBasic Waterが含まれていた。
  - Cinderace: Energy 1枚以上。Basic WaterまたはBasic Darkness 1枚でのAttack実績がある。
- この`Energy-ready`はEnergy条件だけの実証的近似であり、状態異常、相手効果、Attack固有制約まで含む「完全な合法Attack保証」ではない。
- `access route`は、Readyになった後の同Turn中に合法Optionとして観測できたRetreat、Surfing Beach ability、Wally's Compassionを数えた。未来のドローや、Replay上にOptionが出ていない経路は補完しない。

### 5.2 deployからEnergy-ready、Attackまで

| Attacker | Deployed個体 | Energy-ready到達 | Attackした個体 | 起動率 | 同Turn起動 | deploy→Attack中央値 | deploy→Ready中央値 | Ready→Attack中央値 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mega Starmie ex | 96 | 84 | 73 | 76.0% | 28 | 1 Turn | 0 Turn | 0 Turn |
| Mega Froslass ex | 44 | 15 | 13 | 29.5% | 5 | 1 Turn | 0 Turn | 0 Turn |
| Cinderace | 27 | 23 | 21 | 77.8% | 6 | 2 Turn | 0 Turn | 1 Turn |

`同Turn起動`は、最終形態が現れた同じ自Turnに初Attackまで到達した個体数である。

#### Mega Starmie ex

- 96個体中84個体、87.5%がEnergy-readyへ到達した。
- Ready個体84のうち73個体、86.9%が実際にAttackした。
- 初Attackまでの中央値はdeploy後1 Turn、75パーセンタイルは3 Turn。
- 28個体は進化・準備した同じTurnにAttackした。

Starmieは三者の中で最も再現性高く主力化している。ただし、Energy-readyなのに一度もAttackしなかった個体が11あり、10個体は終局時まで盤面に残っていた。これはカード自体の起動不足だけではなく、Active accessまたは別Attacker優先の問題を含む。

#### Mega Froslass ex

- 44個体中Energy-readyへ到達したのは15個体、34.1%だけだった。
- ただしReady個体15のうち13個体、86.7%はAttackした。
- deployから初Attackまでの中央値は1 Turnだが、7～8 Turnを要した個体も各1あった。
- 29個体は、最終形態として盤面へ出た後、一度もBasic Waterを持つ状態が観測されなかった。

したがって、Froslassの主なボトルネックは「Ready後にAttackを選ばないこと」より、**最終形態へBasic Waterを配分してEnergy-readyへ到達させること**にある。既知のAttach即時KO欠落はReady到達直前の選択を落とす問題であり、この低起動率と整合する。

#### Cinderace

- 27個体中23個体、85.2%がEnergy-readyへ到達し、21個体がAttackした。
- Ready個体からのAttack転換率は91.3%だった。
- deployから初Attackまでの中央値は2 Turn、Ready後でも中央値1 Turnを要した。
- 最長は`87635272`の14 Turnだったが、そのReplayは勝利している。長い待機時間だけを自動的に誤りとは判定できない。

Cinderaceはsetupから常に主力化するカードではなく、壁への攻撃、Active中継、Turbo FlareによるBench加速という役割を持つ。初Attackの遅さだけでは価値を測れない。

### 5.3 Attack出力とEnergy投資

以下はself-playを除いた対外67 Replayの値である。Item 4の全68 ReplayではMega Froslass exが36 Attack・12,850 damage・33 Prizeだったが、そのうち4 Attack・1,900 damage・6 Prizeはmirror self-playである。

| Attacker | Attack | Positive damage | 実damage合計 | Prize | Damage/Attack | Prize/Attack | Energy投資単位 | Prize/Energy投資 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mega Starmie ex | 210 | 202 | 35,630 | 171 | 169.7 | 0.814 | 183 | 0.934 |
| Mega Froslass ex | 32 | 29 | 10,950 | 27 | 342.2 | 0.844 | 30 | 0.900 |
| Cinderace | 71 | 71 | 4,150 | 23 | 58.5 | 0.324 | 23 | 1.000 |

`Energy投資単位`は、各最終形態個体に一度でも付いていた異なるEnergy serialの合計である。同じEnergyが別個体へ移動した場合は各受け手で1回ずつ数え、同じ個体で再観測しただけなら重複させない。Attackしなかった個体へのEnergyも分母に含む。

この比率には次の限界がある。

- 一度付けたEnergyで複数回Attackした価値はPrize側へ累積する。
- Energy Switchなどで同じEnergyが複数Attackerへ移れば、複数の投資単位として数える。
- CinderaceのTurbo FlareによるBench加速価値は、Cinderace自身のPrizeへ入らない。
- Starmieの210 Attackには`87638484`の実damage 0 Attack 8回が含まれる。これは既知の評価器誤認を含むため、平均34.0 damageとなったComfey／Yveltal対面をStarmie本来の出力とは扱えない。

### 5.4 初Attack後の生存

初Attackを行った個体について、次の自Turn開始時に同じserialがActiveまたはBenchへ残っているかを確認した。

| Attacker | 初Attack個体 | 次の自Turnまで盤面生存 | 次の自Turn前にDiscard移動 | 試合終了で判定不能 | 判定可能分の盤面生存率 |
|---|---:|---:|---:|---:|---:|
| Mega Starmie ex | 73 | 62 | 2 | 9 | 96.9% |
| Mega Froslass ex | 13 | 10 | 2 | 1 | 83.3% |
| Cinderace | 21 | 11 | 8 | 2 | 57.9% |

ここで確認したのはMoveCardと次Turn盤面であり、Discard移動の原因をすべて「相手Attackによるきぜつ」とは補完していない。

Starmieは初Attackまで到達すれば、次の自Turnまで盤面へ残る割合が高い。一方、Cinderaceは初Attack後にDiscardへ移る割合が相対的に高く、前線・中継役として消費されやすい。ただしHP、相手damage、Attack対象の違いを揃えた比較ではないため、カード耐久力の因果比較とはしない。

### 5.5 一度もAttackしなかった最終形態

| Attacker | Attackなし個体 | 終局時盤面残存 | 初Attack前にDiscard移動 | その他・不明 |
|---|---:|---:|---:|---:|
| Mega Starmie ex | 23 | 18 | 5 | 0 |
| Mega Froslass ex | 31 | 23 | 8 | 0 |
| Cinderace | 6 | 5 | 1 | 0 |

Mega Froslass exの「初Attack前にDiscard移動」8個体は、すべて敗戦Replayだった。

- `87481810`
- `87484539`
- `87495871`
- `87630981`
- `87639017`
- `87639549`
- `87643286`
- `87644371`

これは関連を示す観測であり、「FroslassがAttackすれば必ず勝った」というcounterfactualは証明しない。ただし8件のうち`87639549`には、その場で勝てるWater Attach見逃しが別途証明されている。

### 5.6 Energy-ready BenchからActiveへの到達

各自Turnの途中で、Energy条件上Readyな主力がBenchへ存在したinstance-turnを数えた。同じTurnにReadyなStarmieが2体いれば2 instance-turnとなる。

| Attacker | Ready Bench instance-turn | 同Turnにその個体でAttack | Accessあり・未Attack | 観測Accessなし | 観測AccessなしのうちTurn中Attack自体なし |
|---|---:|---:|---:|---:|---:|
| Mega Starmie ex | 165 | 26 | 74 | 65 | 58 |
| Mega Froslass ex | 16 | 4 | 9 | 3 | 3 |
| Cinderace | 83 | 1 | 41 | 41 | 37 |

`観測Accessなし`は、Readyを確認した後にRetreat、Surfing Beach、Wally's Compassionの合法Optionが一度も出なかったものを指す。

- Starmieの65 instance-turnは59 Replay-turn・23 Replayに分布し、そのうち52 Replay-turnではTurn中Attack自体がなかった。
- Froslassの3件は3 Replay・3 Turnで、すべてTurn中Attackなしだった。
- Cinderaceの41件は41 Replay-turn・15 Replayに分布し、37 TurnでAttack自体がなかった。

一方、`Accessあり・未Attack`をそのまま誤りとは扱えない。

- Starmieの74件中27件では、別のAttackerが同TurnにPrizeを取った。
- Cinderaceの41件中16件でも、別のAttackerが同TurnにPrizeを取った。
- Ready Benchを使わなかったことが合理的なTurnと、到達経路を誤って捨てたTurnが混在している。

より強い異常候補は、**Ready Benchがあり、観測Accessがなく、Turn中Attackもない**52 Starmie Replay-turn、3 Froslass Turn、37 Cinderace Turnである。これには項目3で確定したHard access deadlockが含まれる。

代表例:

- `87521331`: Starmie #66は最終形態deployから初Attackまで9自Turn、#67は6自Turn。T12～T20にはReady Starmieが2体Benchにいるのに5自Turn連続でAttack不能。
- `87642240`: Starmie #67はdeployから初Attackまで8自Turn。勝利ReplayだがT7/T9の連続ENDを含む。
- `87488357`: Froslass #12はdeployから初Attackまで8自Turn。
- `87635272`: Cinderaceはsetupから14自Turn後に初Attackしたが勝利。長期待機が常に欠陥ではない対照例。

### 5.7 相手デッキ別の実出力

サンプル数が2 Attack以上ある主な対面を示す。これは相手構築、盤面、Attack対象を統制した比較ではない。

#### Mega Starmie ex

| 相手系統 | Attack | 平均実damage | Prize/Attack |
|---|---:|---:|---:|
| Mega Lucario ex系 | 41 | 167.6 | 0.780 |
| Mega Starmie ex／Cinderace | 21 | 166.2 | 0.714 |
| Mega Abomasnow ex系 | 18 | 173.3 | 0.944 |
| Archaludon ex系 | 17 | 178.8 | 0.471 |
| Alakazam系 | 14 | 190.0 | 1.000 |
| Dragapult ex系 | 14 | 175.0 | 0.929 |
| Comfey／Yveltal control | 10 | 34.0 | 0.200 |

Starmieは広い対面で160～190前後の実damageを出している。Archaludon対面はdamage自体よりPrize変換が低い。Comfey／Yveltal対面は既知の0 damage誤認8回を含むため、通常対面と同列には扱えない。

#### Mega Froslass ex

| 相手系統 | Attack | 平均実damage | Prize/Attack |
|---|---:|---:|---:|
| Alakazam系 | 12 | 575.0 | 1.000 |
| Mega Abomasnow ex系 | 4 | 275.0 | 1.000 |
| Mega Lucario ex系 | 6 | 125.0 | 0.667 |
| Sylveon系 | 5 | 70.0 | 0.600 |

FroslassはAlakazam対面で突出した実damageを記録している。これは相手手札枚数に応じるAttack特性とReplay事実が一致する。ただし、Alakazamへの勝敗はFroslassを起動できたかだけでは決まらず、v7.4では即時KO見逃しを含む敗戦が残る。

#### Cinderace

| 相手系統 | Attack | 平均実damage | Prize/Attack |
|---|---:|---:|---:|
| Sylveon系 | 9 | 61.1 | 0.444 |
| Crustle系 | 8 | 62.5 | 0.375 |
| Teal Mask Ogerpon ex草系 | 8 | 75.0 | 0.625 |
| Alakazam系 | 8 | 50.0 | 0.250 |
| Mega Lucario ex系 | 4 | 50.0 | 0.750 |

Cinderaceの直接damageは低いが、CrustleなどStarmie側の攻撃条件と噛み合わない相手への打点、Turbo FlareのEnergy加速を兼ねる。直接Prize効率だけで不要とは判定できない。

### 5.8 勝敗・versionとの関係

個体起動率は次の通りだった。

| Attacker | v7.3勝 | v7.3敗 | v7.4勝 | v7.4敗 |
|---|---:|---:|---:|---:|
| Mega Starmie ex | 20/25 = 80.0% | 20/28 = 71.4% | 14/18 = 77.8% | 19/25 = 76.0% |
| Mega Froslass ex | 4/10 = 40.0% | 5/15 = 33.3% | 1/5 = 20.0% | 3/14 = 21.4% |
| Cinderace | 6/8 = 75.0% | 8/8 = 100.0% | 3/6 = 50.0% | 4/5 = 80.0% |

また、Replay内で最初にそのAttackerがAttackした自Turnの中央値は、Starmieでv7.3勝5・敗5、v7.4勝2・敗5だった。

v7.4だけを見ると勝利側のStarmie初動が早いが、v7.3では差がない。FroslassとCinderaceは使用Replay数がさらに少なく、Cinderaceは敗戦側の起動率が高い。したがって、今回のCorpusだけから「特定Attackerを早く起動すれば勝率が何ポイント上がる」とは言えない。

### 5.9 この項目から確定できること

1. **Mega Starmie exは現デッキの再現性ある主力である。**
   deploy個体の76.0%がAttackし、210 Attackで171 Prizeを取得している。初Attack後の判定可能個体では96.9%が次の自Turnまで盤面に残った。

2. **Mega Froslass exは出力不足ではなく起動不足である。**
   対外戦で1 Attack平均342.2 damageを出す一方、44 deploy個体のうちEnergy-readyは15だけだった。Readyになった後は13/15がAttackしているため、主な不足はWater配分とそこへ至るPolicyである。

3. **Cinderaceは主力closerではなく、中継・加速・壁処理役として観測される。**
   直接Prize/Attackは0.324だが、71 Attackすべてでpositive damageがあり、Turbo FlareのBench加速価値はこの数値へ含まれない。

4. **Active accessはAttacker共通の実害候補である。**
   Energy-readyなBenchがいるのに観測Accessがなく、Turn中Attackもない場面がStarmie52 Replay-turn、Froslass3、Cinderace37あった。全件を誤りとは断定しないが、既知のHard deadlockがこの集合へ含まれる。

5. **現時点でデッキ変更を先行させる根拠はない。**
   三者は異なる役割で実績を持つ。特にFroslassの低使用率はカード価値の低さより、Energy配分と到達Policyに強く歪められている。

### 5.10 不明として残す事項

- 各個体がEnergy-readyになった時点で、カード効果・状態異常を含め本当に全Attackが合法だったか。
- Ready Benchを使わなかった各Turnで、別Attackerを優先した判断が最善だったか。
- Discardへ移動した個体すべての正確な除去原因。
- Energy投資単位のうち、どのEnergyが本来別Attackerへ付くべきだったか。
- Froslassを早期起動したcounterfactualで、8件の初Attack前Discard敗戦が何件反転したか。
- Attacker初動と勝利の因果関係。現在確認できるのは相関と個別の確定ミスだけである。

### 状態

**研究項目5 完了。研究項目6「BenchとActiveの資源分配」は未着手。**

---

## 6. BenchとActiveの資源分配

### 6.1 対象と測定定義

本項目では、mirror self-play `87480598` を除いた対外67 Replay、552自Turnを対象に、EnergyがActiveとBenchのどちらへ配分されていたかを調べた。

Turn終端の盤面は、結果ログではなく、最後に選択したMain行動の入力状態を使用した。

- `ATTACK`を選んだTurn: Attack実行直前の盤面
- `END`を選んだTurn: END実行直前の盤面
- 対外552 Turnの終端行動:
  - ATTACK: 403
  - END: 149

この方法を使った理由は、Attackなどの結果ログが次の自Turnの最初のframeへ遅れて現れるReplayがあるためである。結果ログの表示Turnをそのまま行動Turnとして扱っていない。

`Energy-ready`は項目5と同じ実証的近似を使用した。

- Mega Starmie ex: Energy 1枚以上
- Mega Froslass ex: Basic Water Energy 1枚以上
- Cinderace: Energy 1枚以上

これはEnergy条件だけの近似であり、状態異常、相手効果、Attack固有条件を含む完全な合法性判定ではない。

本項目で使用する用語:

- **all-active**: EnergyがActiveにだけ存在
- **split**: ActiveとBenchの両方にEnergyが存在
- **all-bench**: ActiveはEnergy 0で、BenchにだけEnergyが存在
- **Active-starved END**: ActiveがEnergy 0、Energy-readyなBench attackerが1体以上存在し、最終行動がEND
- **追加集中**: Energy-readyなBench attackerに、さらにEnergyを付けること

`Active-starved END`や`追加集中`は調査条件であり、その条件だけで誤りとは判定しない。壁役をActiveへ残す判断、次Turn向けの育成、交代手段の不在などが含まれ得る。

### 6.2 Turn終端時のEnergy配置

| Corpus | all-active | split | all-bench | Energyなし | 合計 |
|---|---:|---:|---:|---:|---:|
| v7.3敗戦 | 73 | 37 | 27 | 12 | 149 |
| v7.3勝利（self-play除外） | 68 | 65 | 23 | 7 | 163 |
| v7.4敗戦 | 65 | 20 | 28 | 20 | 133 |
| v7.4勝利 | 55 | 33 | 13 | 6 | 107 |
| **合計** | **261** | **155** | **91** | **45** | **552** |

全体比率:

- all-active: 261/552 = 47.3%
- split: 155/552 = 28.1%
- all-bench: 91/552 = 16.5%
- Energyなし: 45/552 = 8.2%

BenchへEnergyがあること自体は異常ではない。v7.3勝利ではsplit状態が65 Turnあり、敗戦側の37 Turnより多い。試合数・試合長・相手構築を統制した比較ではないため、split状態が勝利原因とは言えないが、**Bench投資への一律減点が不適切**であることは確認できる。

### 6.3 Active-starved END

Turn終端でActiveがEnergy 0、Energy-readyなBench attackerが存在し、ATTACKではなくENDした場面は80 Turn・32 Replayだった。

| Corpus | Active-starved END | Bench Energy 2枚以上かつEND | Ready Benchに観測最小値を超えるEnergyがありEND |
|---|---:|---:|---:|
| v7.3敗戦 | 23 | 16 | 13 |
| v7.3勝利 | 20 | 12 | 6 |
| v7.4敗戦 | 25 | 9 | 7 |
| v7.4勝利 | 12 | 6 | 4 |
| **合計** | **80** | **43** | **30** |

80 TurnすべてをPolicy欠陥とはしない。

- 交代Optionが存在しない場合、現在のTurnだけではAttackへ到達できない。
- Activeを壁として維持し、次Turn用にBenchを育てることが合理的な場合がある。
- 勝利Replayにも32 Turn存在するため、勝敗ラベルだけでは異常判定できない。

一方、既知のHard access deadlockはこの集合に含まれる。

- `87487796 T3/T5/T7`
- `87488357 T3/T5/T7`
- `87521331 T12/T14/T16/T18/T20`
- `87642240 T7/T9`

したがって、この80 Turnは一括修正対象ではなく、**到達経路の有無を調べる母集合**として扱う。

### 6.4 手札からのEnergy Attach先

Main行動として選択されたEnergy Attachを、Energy card IDと選択Optionから直接復元した。対外67 Replayでは199回だった。

- Basic Water Energy: 165
- Basic Darkness Energy: 23
- Ignition Energy: 11

Hero's CapeなどEnergy以外のAttach Optionは除外した。

| Attach先 | Attach回数 | その対象lineが同TurnにAttack | 同Turnに何らかのAttack | Attach前から対象がEnergy-ready |
|---|---:|---:|---:|---:|
| Active | 119 | 73 | 77 | 9 |
| Bench | 80 | 22 | 27 | 29 |
| **合計** | **199** | **95** | **104** | **38** |

確認できる事実:

1. 199 Attach中95回、47.7%で、付けた対象lineが同TurnにAttackした。
2. Active Attachでは73/119、61.3%が同Turnの対象line Attackへ接続した。
3. Bench Attachでも22/80、27.5%がRetreat、Surfing Beach、Wallyなどを経由して同Turnの対象line Attackへ接続した。
4. Bench Attach 80回中29回は、対象がAttach前から既にEnergy-readyだった。

Bench Attachの同Turn接続率がActive Attachより低いことだけで、Bench Attachを低価値とは判定できない。Bench Attachには将来Turnの育成が含まれ、実際に22回は同TurnAttackへ接続している。

### 6.5 Active Attach後のEnergy所在

ActiveへEnergyを付けた119回について、Turn終端時にそのEnergy serialが盤面上のどこに存在したかを追跡した。

| 終端結果 | 回数 |
|---|---:|
| 同TurnにAttackを選択 | 77 |
| ENDし、EnergyがActiveに残存 | 8 |
| ENDし、EnergyがBenchに残存 | 20 |
| END時にEnergyが盤面から消失 | 14 |
| **合計** | **119** |

`ENDし、EnergyがBenchに残存`には、Energyを失わないCinderaceの交代などが含まれる。この20回を損失とは扱わない。

一方、END時に付けたEnergyが盤面から消失した14回は、これまでの全件監査で確認した、

> ActiveへAttach → 同Turnに有償Retreat → そのEnergyをRetreat Costとして失う → Attackなし

の14件と一致した。

- v7.3勝利: `87480740 T1`, `87491060 T1`, `87494261 T1`, `87494795 T1`
- v7.3敗戦: `87487251 T1`, `87488357 T1`
- v7.4勝利: `87631518 T2`, `87636873 T1`, `87642240 T1`
- v7.4敗戦: `87630981 T1`, `87632037 T1`, `87637402 T1`, `87642752 T1`, `87645438 T1`

したがって、修正条件はActive AttachやRetreat全体ではなく、**付けたEnergyが同Turnに実際に失われ、Attackや別の具体的利益へ接続しない経路**である。

### 6.6 Activeを飢餓状態に残した追加Bench投資

次の三条件を同時に満たす、より狭いパターンを抽出した。

1. Attach選択時のActiveがEnergy 0
2. Attach先が、既にEnergy-readyなBench attacker
3. 同Turnの最終行動がEND

該当は23 Turn・15 Replayだった。

| Corpus | 該当Turn |
|---|---:|
| v7.3敗戦 | 12 |
| v7.3勝利 | 6 |
| v7.4敗戦 | 4 |
| v7.4勝利 | 1 |
| **合計** | **23** |

Attach先:

- Starmie line: 22
- Froslass line: 1

勝敗別:

- 敗戦: 16
- 勝利: 7

この23件も、条件だけで全件を誤りとはしない。ただし、広い`Active-starved END`より、実際の選択責任を狭く捉えている。

既存監査で別途欠陥が確認済みの代表例:

- `87488357 T5/T7`: powered Starmieへさらに投資し、Active Staryuから到達できない状態を継続
- `87488357 T15/T17`: Active FroslassへWaterを付ければ即時KO可能だが、既にReadyなBench Starmieへ追加投資
- `87521331 T14/T16/T18/T20`: Ready Starmieが2体Benchにいる一方、Active Staryu E0から複数Turn停止
- `87495871 T16`: Active Froslassの即時KO経路を逃してBench Starmieへ追加投資
- `87630981 T17`: Active FroslassへのWater Attachでその場のKOが可能だがBench StarmieへAttach
- `87642240 T5`: 既に複数Energyを持つBench Starmieへ追加Attachし、その後T7/T9で連続END。試合自体は勝利

この集合の22/23がStarmie lineであることは、StarmieへのEnergy集中が強いというReplay事実を示す。ただし、Starmieの追加EnergyにAttack、Retreat、次Turn以降の価値がないとは確認していないため、**過剰Energy一般を無価値とは扱わない。**

### 6.7 v7.3とv7.4の比較

狭い「Active E0のまま、既にReadyなBenchへ追加AttachしてEND」は、

- v7.3: 18回
- v7.4: 5回

へ減っている。

一方、広い`Active-starved END`は、

- v7.3: 43/312 Turn = 13.8%
- v7.4: 37/240 Turn = 15.4%

で、消えていない。

これは次の分離を支持する。

- **追加Bench Attachの選択症状**はv7.4で減少している
- **Ready Benchへ到達できずENDする問題全体**は残っている

ただし、version間で対戦相手、試合長、初手、盤面分布が異なる。Issue5や特定変更がこの差を直接生んだとは断定しない。

### 6.8 正常Guard

資源分配修正で維持すべき正常系:

1. **Active Attachから即時Attack**
   - 対外67 Replayで73回、Attach対象lineが同TurnにAttack
   - 即時KO・Prize・Winを含むため最優先で保護する

2. **Bench Attachから交代してAttack**
   - 対外67 Replayで22回、Attach対象lineが同TurnにAttack
   - Bench Attach全体を下げる修正は禁止

3. **Energyを失わない交代**
   - Active Attach後、EnergyがBenchへ残ったENDが20回
   - Cinderaceのfree-retreatなどを、有償Retreat浪費と混同しない

4. **勝利試合でのsplit育成**
   - v7.3勝利だけでも65 TurnでActive・Bench双方にEnergyが存在
   - Activeへ全Energyを集中させるPolicyは、正常な次Attacker育成を壊す

### 6.9 設計上の含意

Replay事実から、Energy配置を次の一軸だけで評価するのは不十分である。

```text
その個体にEnergyを付ける価値
```

必要なのは少なくとも次の分離である。

```text
対象がAttack-readyになるか
+
そのTurnにActiveへ到達できるか
+
現在ActiveのAttack / Retreat不能を解消するか
+
同Turnまたは次Turnの具体的Attackへ接続するか
-
同TurnにRetreat Costとして失われるか
```

特に、Bench側のEnergy総量や既存Energy数だけでResource値を上げると、

```text
ReadyなBench Starmieへ追加投資
↓
Active E0を維持
↓
交代不能
↓
END
```

という経路を防げない。

ただし、未実行Attackのdamage、KO、Prize、Winを実際に発生したOutcomeとして記録してはならない。項目3と同様に、**到達可能な将来価値と実Outcomeを別fieldで保持する必要がある。**

### 6.10 この項目から確定できること

1. **Bench投資そのものは正常かつ必要である。**
   split状態は155 Turn、Bench Attachから同TurnAttackへ接続した例は22回ある。

2. **Active accessを無視したBench集中は実在する。**
   Active E0のまま、既にReadyなBenchへ追加AttachしてENDした例が23 Turnある。

3. **その集中先はほぼStarmie lineである。**
   23例中22例。現在のResource評価がStarmieの既存Energyを強く評価している可能性はあるが、原因関数は未確認である。

4. **Attach→有償Retreat浪費は盤面Energy serialでも14件再確認できる。**
   free-retreatやEnergy保持型の交代とは分離できる。

5. **Active-starved END全体はv7.4でも残る。**
   狭い追加Attach症状は減ったが、到達不能によるENDは解消していない。

### 6.11 不明として残す事項

- 80件のActive-starved ENDのうち、何件が最善手としての壁維持だったか。
- Starmieに観測最小値を超えて付いたEnergyの正確な将来価値。
- Attach時点では見えていない次Turnのドローを含めたcounterfactual。
- Ready Benchへ到達できなかった原因が、Retreat Cost、Surfing Beach条件、Wally不足、状態異常のどれだったかという全件内訳。
- 23件の追加集中をすべて修正した場合の勝敗反転数。
- Crispin、Turbo Flare、Energy Switchによる効果内Energy配分。本節の199回はMainの手札Energy Attachだけであり、効果による全Energy移動を含まない。
- Starmieへの集中がResource field、Pressure、legacy、または効果内target選択のどこで生じるか。コード未確認。

### 状態

**研究項目6 完了。研究項目7「先攻・後攻、初手、事故率」は未着手。**

保留研究として、ユーザー指定の **「相手デッキ別の勝敗 × その試合で選択された攻撃軸／軸へ到達できなかった試合」** を記録した。本項目では未着手。

---

## 7. 先攻・後攻、初手、事故率

### 7.1 対象と定義

本項目は、mirror self-play `87480598` を除いた対外67 Replayを対象とした。

初期状態はReplayのsetupログから次のように復元した。

- **先攻／後攻**: `firstPlayer`とYserのplayer indexを比較
- **Mulligan**: `HasBasicPokemon=False` の回数
- **最終opening hand**: Mulligan終了後、`HasBasicPokemon=True`が記録された時点の7枚
- **初期Active／Bench**: 両者のsetupとPrize配置が完了し、最初のTurnが開始した時点
- **自Turn番号**: Yserの`TurnStart`を1から数えた序数
- **最初のEnergy Attach／Evolve／Attack／Prize**: 各Replayで最初に実行された自Turn番号

本項目における「事故」はルールエンジンの正式分類ではない。以下の観測可能なproxyへ分解した。

- 自分のMulligan
- opening handにEnergyがない
- opening handにBasic Water Energyがない
- Energy Attach、Evolve、Attack、最初のPrizeが遅い
- 主力進化カードの全コピーが初期Prizeに入る

初期Prizeの中身はReplay後に確認できる未来情報であり、Policy判断時には利用できない。ここではデッキ安定性の結果分析にのみ使用した。

### 7.2 先攻／後攻と観測勝率

| Version | 手番 | 試合 | 勝 | 敗 | 観測勝率 |
|---|---|---:|---:|---:|---:|
| v7.3 | 先攻 | 22 | 13 | 9 | 59.1% |
| v7.3 | 後攻 | 15 | 4 | 11 | 26.7% |
| v7.4 | 先攻 | 18 | 8 | 10 | 44.4% |
| v7.4 | 後攻 | 12 | 4 | 8 | 33.3% |
| **合計** | **先攻** | **40** | **21** | **19** | **52.5%** |
| **合計** | **後攻** | **27** | **8** | **19** | **29.6%** |

このCorpusでは、先攻の観測勝率が後攻より22.9ポイント高かった。v7.3、v7.4の両方で同じ方向だった。

ただし、先攻・後攻ごとに対戦相手、初期Active、opening hand、version内の対戦分布を揃えた比較ではない。したがって、**先攻が22.9ポイントの因果効果を持つとは断定しない。**

### 7.3 Mulligan

自分のMulliganは8/67試合、11.9%だった。8試合はすべて1回で、2回以上の自分Mulliganはなかった。

| 自分のMulligan | 試合 | 勝 | 敗 | 観測勝率 |
|---|---:|---:|---:|---:|
| なし | 59 | 24 | 35 | 40.7% |
| あり | 8 | 5 | 3 | 62.5% |

相手は14/67試合で1回以上Mulliganし、合計26回だった。

| 相手のMulligan | 試合 | 勝 | 敗 | 観測勝率 |
|---|---:|---:|---:|---:|
| なし | 53 | 20 | 33 | 37.7% |
| あり | 14 | 9 | 5 | 64.3% |

自分Mulliganありの方が観測勝率は高く、Mulliganを単純な敗因とは扱えない。相手Mulligan時の追加draw選択、対戦相手構成、手番を統制していないため、両表とも因果効果は不明である。

### 7.4 Opening handのBasicとEnergy

最終opening handには、Mulligan後なので全67試合でBasic Pokémonが1枚以上存在した。

| opening Basic枚数 | 試合 | 勝 | 敗 | 観測勝率 |
|---:|---:|---:|---:|---:|
| 1 | 30 | 14 | 16 | 46.7% |
| 2 | 28 | 12 | 16 | 42.9% |
| 3 | 5 | 2 | 3 | 40.0% |
| 4 | 4 | 1 | 3 | 25.0% |

Basic枚数が多いほど勝率が上がる単調関係は、この67試合では確認できなかった。Basicの種類、手番、Energy、進化札が異なるため、枚数だけでは初手の質を表せない。

Energy枚数は次のとおりだった。

| opening Energy枚数 | 試合 | 勝 | 敗 | 観測勝率 |
|---:|---:|---:|---:|---:|
| 0 | 16 | 6 | 10 | 37.5% |
| 1 | 32 | 13 | 19 | 40.6% |
| 2 | 13 | 6 | 7 | 46.2% |
| 3 | 4 | 3 | 1 | 75.0% |
| 4 | 2 | 1 | 1 | 50.0% |

- opening handにEnergyなし: 16/67試合、23.9%
- opening handにBasic Water Energyなし: 23/67試合、34.3%
- 最初のEnergy Attachは全67試合で確認
- 自Turn1に最初のEnergy Attach: 61/67試合、91.0%
- Energyなし16試合のうち、自Turn1にEnergy Attachできた試合: 11/16、68.8%

opening EnergyなしでAttachが自Turn2以降になったのは5試合だった。

| Episode | Version／結果 | 初期Active | 最初のEnergy Attach |
|---|---|---|---:|
| 87485611 | v7.3敗戦 | Staryu | 自Turn2 |
| 87517866 | v7.3敗戦 | Staryu | 自Turn5 |
| 87646047 | v7.4敗戦 | Cinderace | 自Turn9 |
| 87485083 | v7.3勝利 | Cinderace | 自Turn3 |
| 87644912 | v7.4勝利 | Cinderace | 自Turn2 |

opening Energyを2枚持っていたが、最初のAttachが自Turn2だった例も1試合ある。

- `87491590`、v7.3勝利、初期Active Cinderace

したがって、Attach遅延はopening Energy欠如だけでは説明できない。一方、`87646047`は自Turn9までEnergy AttachもAttackもなく、結果としてPrizeを取らず敗戦した。遅延の原因がdraw、search選択、Energy使用Policyのどれかは、本項目だけでは確定しない。

### 7.5 初期Active

| 初期Active | 試合 | 勝 | 敗 | 観測勝率 | 最初のAttack中央値 | Prizeなし |
|---|---:|---:|---:|---:|---:|---:|
| Cinderace | 27 | 14 | 13 | 51.9% | 自Turn2 | 2 |
| Staryu | 25 | 10 | 15 | 40.0% | 自Turn2 | 4 |
| Snorunt | 13 | 5 | 8 | 38.5% | 自Turn2 | 2 |
| Shaymin | 1 | 0 | 1 | 0.0% | 自Turn3 | 1 |
| Yveltal | 1 | 0 | 1 | 0.0% | 自Turn1 | 0 |

Cinderace初期Activeの観測勝率が最も高かった。ただしsetup選択の最善性、手番、相手デッキを揃えていない。ShayminとYveltalは各1試合だけなので比較材料にならない。

初期Active別の数字は、カード自体の優劣ではなく、**そのカードが初期Activeになった試合全体の結果**である。

### 7.6 初動速度

| 指標 | 勝利29試合 | 敗戦38試合 |
|---|---|---|
| 最初のEnergy Attach | 中央値 自Turn1、欠測0 | 中央値 自Turn1、欠測0 |
| 最初のEvolve | 中央値 自Turn2、欠測0 | 中央値 自Turn2、欠測2 |
| 最初のAttack | 中央値 自Turn2、欠測0 | 中央値 自Turn2、欠測1 |
| 最初のPrize | 中央値 自Turn4、欠測0 | 中央値 自Turn4、欠測9 |

Attackを行った66試合では、最初のAttackと最初のpositive damageは同じ自Turnだった。最初から0 damageだった試合はない。既知の0 damage Attack問題は試合途中に発生したものである。

一度もAttackしなかった試合:

- `87487251`、v7.3敗戦、4自Turn

一度もPrizeを取らなかった試合は9件で、すべて敗戦だった。

Turn orderを混ぜないため、最も早くAttackが観測されたtimingを次のように置いた。

- 先攻: 自Turn2。先攻の自Turn1 Attackは67試合中0件
- 後攻: 自Turn1

| 手番 | 最早timingでAttack | 試合 | 勝 | 敗 | 観測勝率 |
|---|---|---:|---:|---:|---:|
| 先攻 | あり | 22 | 14 | 8 | 63.6% |
| 先攻 | なし | 18 | 7 | 11 | 38.9% |
| 後攻 | あり | 23 | 7 | 16 | 30.4% |
| 後攻 | なし | 4 | 1 | 3 | 25.0% |

全体では45/67試合、67.2%が最早timingでAttackした。ただし、後攻群では最早Attackの有無で観測勝率の差が小さく、**早くAttackすることだけで勝敗は説明できない。** Attackのdamage、相手Active、選択した軸が異なるためである。

最初のPrizeを自Turn4までに取った試合は33件だった。

| 自Turn4までの最初のPrize | 試合 | 勝 | 敗 | 観測勝率 |
|---|---:|---:|---:|---:|
| あり | 33 | 17 | 16 | 51.5% |
| なし | 34 | 12 | 22 | 35.3% |

これは観測上の関連であり、早期Prizeが勝利を因果的に生んだとまでは言えない。

version別の最初のPrize中央値は次のとおりだった。

| Version／結果 | Prize取得試合 | Prizeなし | 最初のPrize中央値 |
|---|---:|---:|---:|
| v7.3敗戦 | 15 | 5 | 自Turn5 |
| v7.3勝利 | 17 | 0 | 自Turn4 |
| v7.4敗戦 | 14 | 4 | 自Turn3 |
| v7.4勝利 | 12 | 0 | 自Turn2.5 |

v7.4は勝利・敗戦の両方でv7.3より早く最初のPrizeを取っていた。それでも提供Corpusのraw win rateはv7.4の方が低い。したがって、**最初のPrize速度だけではv7.4の勝率低下を説明できない。** 手番構成、対戦相手、取得後のPrize race、既知Policy欠陥を含めた比較が必要である。

### 7.7 初期Prizeによる主力封鎖

初期Prizeに入った主力進化カードは次のとおりだった。

| 状態 | 試合 |
|---|---:|
| Mega Starmie ex 0枚Prize | 53 |
| Mega Starmie ex 1枚Prize | 14 |
| Mega Starmie ex 2枚ともPrize | 0 |
| Mega Froslass ex 0枚Prize | 54 |
| Mega Froslass ex 1枚Prize | 13 |
| Mega Froslass ex 2枚ともPrize | 0 |

主力進化の全コピーPrize落ちは67試合で一度もなかった。

その他の全コピーPrize落ち:

- Wally's Compassion 2枚ともPrize: 2試合
  - `87483452` v7.3敗戦
  - `87491060` v7.3勝利
- Surfing Beach 2枚ともPrize: 1試合
  - `87483452` v7.3敗戦

`87483452`はWallyとSurfing Beachがともに全コピーPrizeだった。ただし、それが敗戦を決定したcounterfactualは確認していない。`87491060`はWally全コピーPrizeでも勝利している。

### 7.8 この項目から確定できること

1. **このCorpusでは先攻側の観測勝率が高い。**
   先攻52.5%、後攻29.6%。両versionで同方向だが、因果効果の大きさは不明。

2. **Mulliganは主要敗因として観測されていない。**
   自分Mulliganは8試合だけで、そのうち5勝。少なくとも「Mulliganした試合はほぼ負ける」という状態ではない。

3. **opening Energyなしは珍しくないが、多くは自Turn1に解消される。**
   16試合中11試合は自Turn1にEnergy Attachできた。opening handだけから実際の初動停止を判定してはいけない。

4. **明確な長期Energy停止は存在する。**
   `87646047`は自Turn9までEnergy AttachもAttackもなく、Prizeなしで敗戦した。ただし原因関数は未確認。

5. **主力進化の全コピーPrize落ちは観測されていない。**
   現在の67対外戦では、Mega Starmie exまたはMega Froslass exが2枚ともPrizeに入った試合は0。

6. **勝敗を分けるのは単純な初動中央値だけではない。**
   勝利・敗戦とも最初のAttach中央値は1、EvolveとAttackは2、最初のPrizeは4だった。

7. **v7.4の低いraw win rateを、初動の遅さだけでは説明できない。**
   最初のPrizeはv7.4の方が早い。取得後の軸選択、access、資源損失、対戦相手別の進行を別に見る必要がある。

### 7.9 不明として残す事項

- 先攻／後攻の因果効果。matchup、初期Active、opening handを統制していない。
- setup時に選択されたActive／Bench配置が最善だったか。
- opening Energyなし16試合で、自Turn1 Attachを可能にしたdrawまたはsearchの内訳。
- Attach遅延6試合で、Energyが存在したのに使わなかった判断の正否。
- 初期Prizeの特定カードが勝敗へ与えたcounterfactual。
- 最初のAttackやPrizeが早くても、そのdamage量、相手Prize pace、次Attacker準備が適切だったか。
- 67試合を独立同分布の無作為標本とみなした理論的事故率。
- デッキ別の勝敗と、その試合で実際に選ばれた攻撃軸／軸未達の関係。本項目では未着手。

### 状態

**研究項目7 完了。研究項目8「対戦相手別の負け方」は未着手。**

ユーザー指定の保留研究 **「対戦相手デッキ別の勝敗 × 選択された攻撃軸／軸未達」** も未着手のまま保持する。

---

## 8. 対戦相手別の負け方

### 8.1 対象と分離方針

本項目では、mirror self-play `87480598` を除いた対外67 Replayを、相手デッキfamily別に集計した。

- 対外成績: 29勝38敗
- 相手family: 18分類
- 敗戦を含むfamily: 11分類

分類名は、初期デッキデータに含まれる60枚と主軸ポケモンから付けた監査用名称であり、公式アーキタイプ名ではない。

本項目で扱うのは次の範囲に限定する。

1. family別の観測勝敗
2. 敗戦終結方法
3. 敗戦時に自分が取ったPrize数
4. 既存監査で確定済みの損失行動が、どのfamily戦に含まれていたか
5. version別の観測差

ユーザー指定の保留研究、

> 相手デッキ別の勝敗 × その試合で実際に選ばれた攻撃軸／軸へ到達できなかった試合

は、本項目へ混ぜていない。Attacker軸の選択・未達分類は未着手のまま保持する。

用語:

- **0 Prize敗戦**: 自分がPrizeを1枚も取らずに敗戦
- **接戦敗戦**: 敗戦時の自分の残りPrizeが1～2枚
- **確定損失あり**: 項目1でL1、L2、L3に分類済み
- **強い確定損失**: 項目1でL1またはL2に分類済み

「確定損失あり」は、その行動を直せば必ず勝ったという意味ではない。勝敗反転をReplay上で証明できたのは、既出の`87639549`だけである。

### 8.2 全familyの観測勝敗

| 相手family | 試合 | 勝 | 敗 | 観測勝率 |
|---|---:|---:|---:|---:|
| Mega Lucario ex系 | 13 | 5 | 8 | 38.5% |
| Alakazam系 | 10 | 2 | 8 | 20.0% |
| Mega Abomasnow ex系 | 7 | 3 | 4 | 42.9% |
| Mega Starmie ex／Cinderace | 5 | 2 | 3 | 40.0% |
| Teal Mask Ogerpon ex草系 | 5 | 2 | 3 | 40.0% |
| Archaludon ex系 | 4 | 1 | 3 | 25.0% |
| Dragapult ex系 | 4 | 1 | 3 | 25.0% |
| Hop系 | 3 | 2 | 1 | 66.7% |
| Mega Kangaskhan ex／Crustle | 3 | 1 | 2 | 33.3% |
| Crustle系 | 2 | 2 | 0 | 100.0% |
| Cynthia's Garchomp ex系 | 2 | 1 | 1 | 50.0% |
| Marnie's Grimmsnarl ex系 | 2 | 0 | 2 | 0.0% |
| Sylveon系 | 2 | 2 | 0 | 100.0% |
| Comfey／Yveltal コントロール | 1 | 1 | 0 | 100.0% |
| Mega Kangaskhan ex系 | 1 | 1 | 0 | 100.0% |
| Mega Manectric ex | 1 | 1 | 0 | 100.0% |
| Raging Bolt ex／Teal Mask Ogerpon ex | 1 | 1 | 0 | 100.0% |
| Walrein系 | 1 | 1 | 0 | 100.0% |

0敗のfamilyはいずれも1～2試合しかない。したがって、観測勝率100%を有利相性とは判定しない。

同様に、Marnie's Grimmsnarl ex系の0勝2敗も、2試合だけなので不利相性とは断定しない。

### 8.3 family別の敗戦形状

自分の取得Prize数は、敗戦時の残りPrizeを6から引いて算出した。

| 相手family | 敗 | Opponent Prize | Own Board-out | 敗戦自Turn中央値 | 取得Prize中央値 | 0 Prize敗戦 | 接戦敗戦 | 確定損失あり | 強い確定損失 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Alakazam系 | 8 | 7 | 1 | 6 | 2 | 1 | 2 | 4 | 2 |
| Mega Lucario ex系 | 8 | 7 | 1 | 6 | 1.5 | 3 | 0 | 2 | 1 |
| Mega Abomasnow ex系 | 4 | 3 | 1 | 8 | 3 | 1 | 0 | 2 | 0 |
| Archaludon ex系 | 3 | 3 | 0 | 6 | 1 | 0 | 0 | 1 | 1 |
| Dragapult ex系 | 3 | 3 | 0 | 9 | 4 | 0 | 2 | 2 | 1 |
| Mega Starmie ex／Cinderace | 3 | 3 | 0 | 8 | 3 | 1 | 1 | 2 | 1 |
| Teal Mask Ogerpon ex草系 | 3 | 2 | 1 | 8 | 0 | 2 | 0 | 2 | 2 |
| Marnie's Grimmsnarl ex系 | 2 | 2 | 0 | 7.5 | 2.5 | 0 | 0 | 1 | 0 |
| Mega Kangaskhan ex／Crustle | 2 | 2 | 0 | 12 | 2 | 1 | 1 | 1 | 0 |
| Cynthia's Garchomp ex系 | 1 | 1 | 0 | 11 | 4 | 0 | 1 | 1 | 1 |
| Hop系 | 1 | 1 | 0 | 14 | 4 | 0 | 1 | 1 | 0 |

敗戦終結は38敗中34件がOpponent Prize、4件がOwn Board-outだった。

Own Board-out:

- `87486700` — Mega Lucario ex系
- `87637949` — Alakazam系
- `87645438` — Mega Abomasnow ex系
- `87665056` — Teal Mask Ogerpon ex草系

Deck-outによる敗戦は、この38敗にはない。

### 8.4 family別に含まれた確定損失

以下は、項目1～7ですでに確定済みの損失をfamily単位で再集計したもの。1 Replayに複数種類が併存するため、横方向の合計は敗戦数と一致しない。

| 相手family | 即時KO／Win見逃し | Access deadlock | Active進化見逃し | Attach→有償Retreat浪費 | 0 damage Attack | Energy停止候補・未確定 |
|---|---:|---:|---:|---:|---:|---:|
| Alakazam系 | 2 | 0 | 1 | 2 | 0 | 0 |
| Mega Lucario ex系 | 0 | 0 | 1 | 1 | 1 | 2 |
| Mega Abomasnow ex系 | 0 | 0 | 1 | 1 | 0 | 0 |
| Archaludon ex系 | 1 | 0 | 0 | 0 | 0 | 0 |
| Dragapult ex系 | 0 | 1 | 0 | 1 | 0 | 0 |
| Mega Starmie ex／Cinderace | 1 | 0 | 2 | 0 | 0 | 0 |
| Teal Mask Ogerpon ex草系 | 1 | 1 | 2 | 0 | 0 | 0 |
| Marnie's Grimmsnarl ex系 | 0 | 0 | 1 | 0 | 0 | 0 |
| Mega Kangaskhan ex／Crustle | 0 | 0 | 0 | 1 | 0 | 0 |
| Cynthia's Garchomp ex系 | 1 | 1 | 0 | 1 | 0 | 0 |
| Hop系 | 0 | 0 | 1 | 0 | 0 | 0 |

`Energy停止候補・未確定`は確定Issueではない。

- `87517866` — Mega Lucario ex系。Water Energy取得が遅く、Energy starvationが大きい
- `87646047` — Mega Lucario ex系。自Turn9までEnergy AttachもAttackもない

draw、search、使用Policyのどれが直接原因かは未確認である。

### 8.5 Alakazam系

観測成績:

- 全体: 2勝8敗
- v7.3: 2勝4敗
- v7.4: 0勝4敗

敗戦形状:

- Opponent Prize: 7
- Own Board-out: 1
- 取得Prize中央値: 2
- 0 Prize敗戦: 1
- 接戦敗戦: 2
- 確定損失あり: 4/8
- 強い確定損失: 2/8

確定損失:

- `87485611`: Active進化見逃し
- `87487251`: Attach→有償Retreat浪費
- `87630981`: Attach→有償Retreat浪費、およびActive FroslassへのWater Attachによる即時KO見逃し
- `87639549`: Active FroslassへのWater Attachによる即時勝利見逃し

Alakazam系8敗の半数には確定損失がある。したがって、20.0%というraw win rateをそのまま純粋なデッキ相性とは解釈できない。

一方、残る4敗では狭い確定Issueを特定できていない。Alakazam系への2勝も存在するため、現デッキで勝利不能な相手ではない。

v7.4で0勝4敗へ悪化しているが、試合数、相手構築、初手が異なるため、version変更による因果とは断定しない。

### 8.6 Mega Lucario ex系

観測成績:

- 全体: 5勝8敗
- v7.3: 1勝6敗
- v7.4: 4勝2敗

敗戦形状:

- Opponent Prize: 7
- Own Board-out: 1
- 取得Prize中央値: 1.5
- 0 Prize敗戦: 3
- 接戦敗戦: 0
- 確定損失あり: 2/8
- 強い確定損失: 1/8

確定損失:

- `87486700`: Active進化見逃し。Own Board-out
- `87632037`: Attach→有償Retreat浪費、および実damage 0 Attackによる準備行動の打切り

未確定のEnergy停止候補:

- `87517866`
- `87646047`

8敗中6敗は、現在の狭い確定Issueでは説明できていない。また、0 Prize敗戦が3件あり、接戦敗戦は0件だった。

ただし、v7.4では4勝2敗であるため、現デッキがMega Lucario ex系へ構造的に勝てないとは言えない。v7.3の1勝6敗からの変化が、Policy改善、相手構築差、初手差、標本変動のどれによるかは不明。

このfamilyは、既知欠陥だけでなく、相手のPrize速度やこちらの軸成立条件を別途調べる価値が高い。ただし攻撃軸研究は本項目では実施していない。

### 8.7 Mega Abomasnow ex系

観測成績:

- 全体: 3勝4敗
- v7.3: 2勝1敗
- v7.4: 1勝3敗

敗戦形状:

- Opponent Prize: 3
- Own Board-out: 1
- 取得Prize中央値: 3
- 0 Prize敗戦: 1
- 接戦敗戦: 0
- 確定損失あり: 2/4
- 強い確定損失: 0/4

確定損失:

- `87493732`: Active進化見逃し
- `87645438`: Attach→有償Retreat浪費

残る2敗は候補行動があるものの、保持判断の不合理性や勝敗影響を確定していない。

4敗の取得Prize中央値は3で、LucarioやArchaludonほど一貫して低くない。単一の負け方は、この4試合からは確定できない。

### 8.8 Teal Mask Ogerpon ex草系

観測成績:

- 全体: 2勝3敗
- v7.3: 0勝1敗
- v7.4: 2勝2敗

敗戦形状:

- Opponent Prize: 2
- Own Board-out: 1
- 取得Prize中央値: 0
- 0 Prize敗戦: 2
- 接戦敗戦: 0
- 確定損失あり: 2/3
- 強い確定損失: 2/3

内訳:

- `87521331`: powered Starmieへアクセスできず5自Turn停止。Active進化見逃しも併存
- `87644371`: Active FroslassへのWater AttachでTeal Mask Ogerpon exを即時KO可能だが見逃し。Active進化残存穴も併存
- `87665056`: 自Turnが実質1回の短期Own Board-out。明確なAI異常は特定せず

rawでは取得Prize中央値0だが、3敗のうち2敗に強い確定損失があり、残る1敗は自Turn1回の短期試合である。したがって、この数字から草系へのデッキ相性不利を判断することはできない。

### 8.9 Archaludon ex系

観測成績:

- 全体: 1勝3敗
- v7.3: 1勝0敗
- v7.4: 0勝3敗

3敗はいずれもOpponent Prizeで、自分の残りPrizeはすべて5枚だった。つまり、3敗とも自分が取ったPrizeは1枚である。

- `87632586`: Attack前Attach／Cape候補。最善手と勝敗影響は未確定
- `87643286`: Active FroslassへのWater AttachでArchaludon exを即時KO可能だが見逃し
- `87650661`: Attack前Attach未使用候補。勝敗直結度は未確定

3試合すべてで低いPrize出力が共通している。ただし、1試合には即時KO見逃しがあり、他2試合の最善行動は未確定である。

4試合だけなので、耐久相性や速度差のどちらが主因かは不明。攻撃軸とdamage経路を分ける後続研究が必要である。

### 8.10 Dragapult ex系

観測成績:

- 全体: 1勝3敗
- v7.3: 0勝2敗
- v7.4: 1勝1敗

敗戦形状:

- 3敗すべてOpponent Prize
- 取得Prize中央値: 4
- 接戦敗戦: 2
- 0 Prize敗戦: 0
- 確定損失あり: 2/3
- 強い確定損失: 1/3

内訳:

- `87487796`: powered BenchがあるのにActiveから到達できないAccess deadlock
- `87489956`: 自分の残りPrize1。狭い確定Issueは特定せず
- `87642752`: Attach→有償Retreat浪費

観測勝率は25.0%だが、3敗中2敗は自分の残りPrizeが1～2枚だった。今回のCorpusでは、Dragapult ex系は「一方的に何もできず負ける」より、Prizeを進めた後に負ける形が多い。

Bench damage管理が主因だったかは、本項目では確認していない。

### 8.11 Mega Starmie ex／Cinderace mirror

観測成績:

- 全体: 2勝3敗
- v7.3: 1勝2敗
- v7.4: 1勝1敗

敗戦形状:

- 3敗すべてOpponent Prize
- 取得Prize中央値: 3
- 0 Prize敗戦: 1
- 接戦敗戦: 1
- 確定損失あり: 2/3
- 強い確定損失: 1/3

確定損失:

- `87486157`: Active進化見逃し
- `87495871`: Active進化見逃し、およびActive FroslassへのWater Attachで相手Mega Starmie exを即時KOできる経路の見逃し

`87640085`は自分の残りPrize2まで進んでいるが、Attack前Attach未使用候補の正否は未確定。

mirrorでも0 Prize敗戦と接戦敗戦が混在し、単一の負け方は確認できない。

### 8.12 その他のfamily

#### Mega Kangaskhan ex／Crustle

- 1勝2敗
- `87509907`: 0 Prize敗戦。Active access／Wally候補はあるが未確定
- `87637402`: 自分の残りPrize2、17自Turnの接戦敗戦。Attach→有償Retreat浪費あり

2敗の形が大きく異なるため、現段階で共通原因は置かない。

#### Marnie's Grimmsnarl ex系

- 0勝2敗
- `87490505`: Active進化見逃し
- `87643350`: Cape／Attach未使用候補。生存価値は未確定

2試合のみであり、相性判定は不能。

#### Cynthia's Garchomp ex系

- 1勝1敗
- 唯一の敗戦`87488357`は、自分の残りPrize2の接戦
- Attach→有償Retreat浪費、Access deadlock、Active Froslassの即時KO見逃しが同一Replayに併存

敗戦が既知欠陥で強く汚染されているため、デッキ相性の証拠として使えない。

#### Hop系

- 2勝1敗
- 唯一の敗戦`87501720`は、自分の残りPrize2、14自Turn
- Active進化見逃しあり

3試合では不利傾向を確認しない。

### 8.13 version別の主要family成績

3試合以上あるfamilyのみ記載する。

| 相手family | v7.3勝 | v7.3敗 | v7.4勝 | v7.4敗 |
|---|---:|---:|---:|---:|
| Mega Lucario ex系 | 1 | 6 | 4 | 2 |
| Alakazam系 | 2 | 4 | 0 | 4 |
| Mega Abomasnow ex系 | 2 | 1 | 1 | 3 |
| Mega Starmie ex／Cinderace | 1 | 2 | 1 | 1 |
| Teal Mask Ogerpon ex草系 | 0 | 1 | 2 | 2 |
| Archaludon ex系 | 1 | 0 | 0 | 3 |
| Dragapult ex系 | 0 | 2 | 1 | 1 |
| Hop系 | 2 | 1 | 0 | 0 |
| Mega Kangaskhan ex／Crustle | 1 | 1 | 0 | 1 |

大きく方向が異なるもの:

- Mega Lucario ex系: v7.3の1勝6敗から、v7.4の4勝2敗
- Alakazam系: v7.3の2勝4敗から、v7.4の0勝4敗
- Archaludon ex系: v7.3の1勝0敗から、v7.4の0勝3敗

ただし、versionごとに相手、seed、初手、構築内訳が異なる。これらをコード変更の効果または回帰とは断定しない。

### 8.14 この項目から確定できること

1. **Alakazam系のraw成績は最も低いが、8敗中4敗に確定損失がある。**
   raw 2勝8敗を、そのまま純粋な相性差とは扱えない。

2. **Mega Lucario ex系は既知欠陥で説明できない敗戦が多い。**
   8敗中、確定損失ありは2敗だけ。0 Prize敗戦3件、接戦敗戦0件。ただしv7.4では4勝2敗であり、構造的に勝てない相手ではない。

3. **Teal Mask Ogerpon ex草系の低Prize敗戦は、強い既知欠陥と短期Board-outで汚染されている。**
   現時点で草系不利とは判定できない。

4. **Archaludon ex系の3敗は、すべて自分が1 Prizeしか取れていない。**
   今回のfamily別集計で最も一貫した低出力形状。ただし3敗中1敗には即時KO見逃しがあり、残り2敗の最善手は不明。

5. **Dragapult ex系は、raw勝率より敗戦内容が接近している。**
   3敗中2敗が残りPrize1～2。少なくとも今回のCorpusでは、常に一方的な敗戦ではない。

6. **0敗familyを有利相性とは呼べない。**
   いずれも1～2試合だけである。

7. **family別raw勝率と、Policy修正優先度は一致しない。**
   raw勝率が低くても既知欠陥で汚染されたfamilyがあり、逆にLucario系のように既知欠陥だけでは説明しにくいfamilyもある。

### 8.15 不明として残す事項

- 各family戦で、Starmie、Froslass、Cinderaceのどれを主軸として選んだか。
- 選んだ軸へ到達できたか、別軸へ切り替えたか、軸未達のまま終わったか。
- 相手の個別Attack、Ability、Bench damage、耐久効果のどれが敗戦へ直接寄与したか。
- family内の構築差。例: Alakazam単独型とDragapult混成型を同一family集計へ含めている。
- 先攻／後攻、初期Active、opening handを統制したfamily別勝率。
- 既知欠陥をすべて修正した場合のfamily別counterfactual勝率。
- 1～4試合しかないfamilyの真の相性。
- Kaggle全体の対戦分布に対して、提供67試合が代表的かどうか。

### 状態

**研究項目8 完了。研究項目9「評価関数の感度分析」は未着手。**

ユーザー指定の保留研究 **「相手デッキ別の勝敗 × 選択された攻撃軸／軸未達」** は、本項目へ混ぜず未着手のまま保持する。

---

## 9. 評価関数の感度分析

### 9.1 対象・方法・証拠限界

本項目では、修正候補となる定数・閾値を**一つずつ**変更し、同一Replay状態でtop1 Optionが何件変わるかを調べた。複数の変更は組み合わせていない。

対象は、順位照合可能な1,539 Main nodeである。将来の修正へ現在のPolicyを適用する目的から、感度比較の基準には**v7.4相当Policyを全1,539 nodeへ適用した再構成結果**を使用した。

感度分析用に、項目2とは別のparameterized evaluatorを作成した。相手カードmetadataの推定範囲を増やしたため、歴史的な各versionのPolicyを使ったtop1一致は次の値になった。

| 対象 | node | 再構成top1＝実選択 |
|---|---:|---:|
| v7.3 | 890 | 887 |
| v7.4 | 649 | 643 |
| **合計** | **1,539** | **1,530（99.4%）** |

これは項目2の再構成値を上書きするものではない。項目2の結果はそのまま保持し、本項目のcounterfactualは本項目用再構成器の中だけで比較した。

制約:

- Replayには提出時のActionScoreが保存されていない。以下は提供ソースとReplay公開状態からの再構成counterfactualである。
- top1変更後の行動を実際に実行し、その後の盤面を再simulationしてはいない。
- top1変更数は、勝敗変更数でも勝率上昇幅でもない。
- 同一Turn内で複数回Main選択があれば、nodeは複数件になる。
- 「正常Guard turnに変更あり」は保護対象のTurnへ変更が入ったという警告であり、即座にGuard破壊を証明するものではない。
- `87638484`のComfey戦のように評価器と実エンジンのdamage認識が異なるnodeは、係数だけでは正しくならない。
- 提供ソースと実提出物のsource hash完全一致は未確認である。

### 9.2 Active進化damage改善閾値

現行値:

```text
ACTIVE_EVOLVE_CLEAR_DAMAGE_GAIN = 50
```

閾値だけを変更した結果:

| 閾値 | top1変更node | 変更Turn | 正常Guard turnに変更 |
|---:|---:|---:|---:|
| 60 | 0 | 0 | 0 |
| 50 | 0 | 0 | 0 |
| 40 | 0 | 0 | 0 |
| 30 | 0 | 0 | 0 |
| 20 | 3 | 2 | 0 |
| 10 | 3 | 2 | 0 |
| 0 | 3 | 2 | 0 |

閾値20で変わったのは、すべて既知の残存例`87644371`だった。

- T4: `PLAY Buddy-Buddy Poffin` → Active SnoruntをMega Froslass exへ進化
- T4: `ATTACK Chilly` → Active SnoruntをMega Froslass exへ進化
- T6: Bench Snorunt進化 → Active Snorunt進化

この盤面では、再構成上のdamage改善が30→50の20である。閾値40へ下げても何も変わらず、20で初めて変化した。

したがって、今回のCorpusでは次を確認できる。

1. 50→40は影響0で、既知残存例も直さない。
2. 20まで下げると、影響半径は3 node・2 Turnに限定された。
3. この3 nodeでは正常Guard turnを触っていない。

ただし、閾値20を採用すれば勝率が上がるとは証明していない。別Replay状態や新規対戦での影響は不明である。

### 9.3 Attack Pressure

#### Pressure全体の一様倍率

`attack_pressure_value()`の最終値全体を正の倍率で変更した。

| 倍率 | top1変更node |
|---:|---:|
| 0.5倍 | 0 |
| 2倍 | 0 |
| 10倍 | 0 |

これは現行の辞書式順位では自然な結果である。

- Non-KO AttackはTier30
- Pressureは同Tier内で比較される
- 全AttackのPressureを同じ正の倍率で掛けても大小関係は保存される
- 異なるTierを越えることもない

したがって、Pressure全体の倍率調整は、今回の既知問題に対して実質的な調整ノブになっていない。

#### 次Turn Pressure discount

現行値:

```text
NEXT_TURN_PRESSURE_DISCOUNT = 0.35
```

| Discount | top1変更node | 変更内容 |
|---:|---:|---|
| 0.0 | 0 | なし |
| 0.175 | 0 | なし |
| 0.35 | 0 | 基準 |
| 0.7 | 1 | Nebula Beam → Jetting Blow |
| 1.0 | 2 | Nebula Beam → Jetting Blow |

変更node:

- `87521331 T24`
- `87637402 T31`（1.0のみ）

両nodeともReplay実選択はNebula Beamだった。Discountを大きくすると、Jetting BlowのBench pressureと次Turnpressureが強くなり、Activeへの210 damageより120 damage＋Bench pressureが上へ出た。

今回のCorpusからは、

- Discountを下げても既知問題は直らない
- 0.7以上へ上げると別Attackへ反転する
- 現行0.35を動かす積極的根拠はない

と判断する。

### 9.4 High-value prep昇格閾値

現行では、現在Non-KO Attackが存在するとき、一定以上の`legacy_score`を持つPlay／Bench進化をTier40へ昇格する。基準値は50,000である。

| 閾値 | top1変更node | 変更Turn | 正常Guard turnに変更 | 主な方向 |
|---:|---:|---:|---:|---|
| 0 | 184 | 184 | 6 | Attack → Play 184 |
| 25,000 | 133 | 133 | 5 | Attack → Play 133 |
| 50,000 | 0 | 0 | 0 | 基準 |
| 75,000 | 148 | 102 | 3 | Play → Attack 146、Evolve → Attack 2 |
| 100,000 | 186 | 115 | 4 | Play → Attack 184、Evolve → Attack 2 |
| 150,000 | 188 | 115 | 4 | Play → Attack 186、Evolve → Attack 2 |
| 200,000 | 188 | 115 | 4 | Play → Attack 186、Evolve → Attack 2 |

25,000下げただけで133 node、25,000上げただけで148 nodeが変わった。

つまりこの閾値は、

> 局所的な一つの不具合を直すための微調整値ではなく、AttackとDevelopmentの関係を広範囲に反転させる境界

である。

既知のAttach即時KO、0 damage Attack、Active access問題をこの閾値でまとめて直そうとすると、正常な準備行動または正常なAttackを大量に動かす。現段階でglobal変更を行う根拠はない。

### 9.5 Tier40 Resource cap

現行のTier40候補では、`resource`を最大200,000へ制限している。

試したcap:

```text
50,000
100,000
150,000
200,000
250,000
300,000
uncapped
```

**すべてtop1変更0 node**だった。

今回のCorpusでは、Tier40候補同士の順位はResource capより前のDevelopment、またはResource以外の差で決着していた。したがってcap調整は、少なくとも保存済み1,539 nodeでは無効である。

これは「capが一般に不要」という意味ではない。今回の状態分布ではtop1へ影響しなかった、という範囲に限定する。

### 9.6 StarmieへのWater Attach Resource

現行式の一部:

```text
140,000 + 残りEnergy枠 × 45,000
```

45,000部分だけを変更した。

| 1枠当たり加点 | top1変更node | 既知Attach即時KO 8件の改善 | 変更種別 |
|---:|---:|---:|---|
| 0 | 14 | 2 | 全件Attach target変更 |
| 22,500 | 2 | 0 | Attach target変更 |
| 45,000 | 0 | 0 | 基準 |
| 67,500 | 2 | 0 | Attach target変更 |
| 90,000 | 2 | 0 | Attach target変更 |
| 135,000 | 2 | 0 | Attach target変更 |

変更はすべてAttach同士のtarget入替で、Action classは変わっていない。

45,000を0へ下げると、既知8件のうち2件はActive Froslass Attachへ変わった。しかし、

- 残り6件は直らない
- 別の12 nodeもtargetが変わる
- あるnodeではStarmieからStaryuへ移るだけで、即時KO経路にはならない

したがって、Starmie係数を下げることは根本修正にならない。

### 9.7 Active Froslass Water Attachへの固定加点

即時KO見逃し8件をResourceだけで逆転させる実験として、Active Mega Froslass exへのBasic Water Attachへ固定加点した。

| 固定加点 | top1変更node | 既知8件の改善 |
|---:|---:|---:|
| +25,000 | 0 | 0 |
| +50,000 | 6 | 1 |
| +75,000 | 8 | 2 |
| +100,000 | 11 | 4 |
| +150,000 | 11 | 4 |
| +200,000 | 12 | 4 |
| +225,000 | 20 | 8 |
| +250,000 | 20 | 8 |

全8件を逆転するには、今回の試行では+225,000が必要だった。しかしその場合、合計20 nodeが変化し、既知8件以外にも12 nodeへ影響した。

12件の追加変更のうち、少なくとも次の3 nodeは「即時KOを解禁するAttach」ではなかった。

- 新しいAttackを解禁していないAttach
- follow-up damageがKOへ届かないAttach 2件

したがって固定加点は、

> KO／Winへ到達する価値

ではなく、

> Active Froslassへ水を付けたというカード・target属性

を評価してしまう。Resource bonusだけでP0を直す方法は過剰適用を避けられない。

### 9.8 認識済み0 damage AttackのTier

評価器自身が`damage=0`と認識しているNon-KO Attackだけを、Tier30からTier20またはTier10へ下げた。

| 新Tier | top1変更node | 認識済み既知2件の改善 | 誤認識8件の改善 | 正常Guard turnに変更 |
|---:|---:|---:|---:|---:|
| 20 | 3 | 2 | 0 | 0 |
| 10 | 3 | 2 | 0 | 0 |

変更内容:

- `87632037 T7`: Attack → StarmieへのWater Attach
- `87632037 T9`: Attack → StarmieへのWater Attach
- `87632037 T5`: Attack → Ability

Tier20とTier10の結果は同じだった。Tier20へ下げた時点で、Resourceを持つ準備行動が上へ出る。

一方、`87638484`の8回は変化しなかった。評価器上は50 damage・KO・Tier60と誤認しているためである。

したがって0 damage問題は、次の二修正へ分離する必要がある。

1. **評価器も0 damageと認識しているAttack**: Tier30の扱いを変更する
2. **実エンジンでは0だが評価器はKOと認識するAttack**: カード効果・継続効果をOutcome modelへ追加する

一つの係数では両方を直せない。

### 9.9 構造条件との比較実験

固定加点との比較用に、次の条件だけを持つ仮想fieldを試した。

```text
ActiveへのAttach
→ 新しいAttackを解禁
→ そのAttackが同TurnにKO可能
```

この条件をTier40／50／60へ置いた結果:

| 仮想Tier | top1変更node | 変更Turn | 既知8件の改善 | 正常Guard turnに変更 |
|---:|---:|---:|---:|---:|
| 40 | 43 | 32 | 8 | 1 |
| 50 | 51 | 33 | 8 | 1 |
| 60 | 51 | 33 | 8 | 1 |

固定+225,000より変更数は多いが、変更対象は少なくとも「KOへ到達できるAttach」という意味条件で限定される。変更が多い理由には、同じTurn内でKO経路へ到達する前の複数Main nodeが含まれる。

ただし、この仮想実装もそのまま採用できない。

- `87636337 T8`の既存productive sequenceへ変更が入った
- Attach後のAttackをまだ実行していないため、実OutcomeのKO／Prize／Winとして記録してはいけない
- Tier40と50のどちらが妥当かは、現在のKO Attack、Win Attack、他の複合経路との比較が必要
- AttachだけでなくRetreat／Surfing Beachを含む経路は別に扱う必要がある

この実験から確定できるのは、**固定Resource加点より、後続Attackへの到達可能性を別fieldで表す方が意味的に正しい**という範囲である。

### 9.10 感度分析からの分類

#### 影響半径が狭かった変更

- Active進化閾値50→20: 3 node・2 Turn
- 認識済み0 damage AttackをTier20へ降格: 3 node・3 Turn
- Pressure discountを下げる: 変更0
- Tier40 Resource cap: 変更0

このうち、前二つは別Issueなので同時変更せず、それぞれ独立した修正・Guard監査が必要である。

#### 影響半径が広かった変更

- High-value prep閾値: 25,000動かすだけで133～148 node
- Active Froslass Water Attach固定加点: 全8件を直す値で20 node
- KO reachabilityを一般AttachへTier昇格: 43～51 node

#### 既知問題へ効かなかった変更

- Pressure全体の一様倍率
- Tier40 Resource cap
- Starmie Water marginalの小幅変更
- Pressure discountの引下げ
- 認識済み0 damage Tier変更による、Comfey戦8件の修正

### 9.11 修正順序への含意

感度分析上、次の順序が最も混線しにくい。

1. **Attach後の即時KO／Win到達価値**
   - 固定Resource bonusではなく、後続Attack reachabilityとして実装
   - 実Outcomeとは別fieldにする
   - 既知8件と、正常なAttach→Attack／Win Attack Guardを比較

2. **認識済み0 damage Attack**
   - `outcome.damage <= 0`かつNon-KOの場合だけを狭く扱う
   - `87638484`型は別Issueとして残す

3. **Active進化残存穴**
   - 閾値20の独立修正候補
   - 3 nodeだけが変わることを再確認
   - 既存のActive進化→Attack Guardを保持

High-value prep閾値、Pressure係数、Starmie係数を先に全体調整する根拠はない。

### 9.12 不明として残す事項

- 各counterfactual top1を実行した後の完全なゲーム経路と勝敗。
- 新しいReplay分布で同じ影響半径になるか。
- `87638484`の実damage 0を生んだ正確なカード効果・継続効果。
- Attach reachability fieldの最適Tier・field順序。
- Win reachableとKO reachableを同Tierに置くべきか。
- Retreat／Surfing Beachを含む2手以上のreachabilityを、Attach単独と同じ比較器へ入れるべきか。
- High-value prep閾値50,000が全体最適かどうか。本分析は局所変更の危険性を示しただけで、最適化はしていない。
- 複数パラメータを同時変更した場合の相互作用。
- Kaggle実戦での勝率変化。

### 状態

**研究項目9 完了。研究項目10「支配関係違反の検出」は未着手。**

---


## 10. 支配関係違反の検出

### 10.1 判定基準

本項目では、68 Replay・1,540 Main nodeについて、実選択が別候補に支配されていないかを調べた。

ただし、Replayには未選択行動後の完全な将来盤面が存在しない。そのため、次の三段階を分離した。

1. **ゲーム終端までの厳密な支配**
   - 代替経路を選べば同Turnに勝利し、実選択では勝利しない。
   - 以後の将来価値を比較する必要がない。

2. **同Turn内の戦術的支配**
   - 代替経路が同TurnのKO、Prize、またはpositive Attackへ到達し、実選択はそれより低い結果でTurnを終える。
   - 同Turnの結果は優るが、KO後を含む将来盤面全体のPareto支配までは断定しない。

3. **局所改善候補**
   - damage、Energy損失、Active accessなど一部の軸で明確に改善する。
   - ほかの将来価値が未観測なので「支配確定」には昇格しない。

「候補AのActionScoreが候補Bより高い」というPolicy内部順位は、事実上の支配判定には使っていない。評価関数自体が欠落している可能性があるためである。

### 10.2 確定した同Turn支配

項目3で確定済みの13 nodeを、支配の強さで再分類した。

| 分類 | node | Replay | 判定 |
|---|---:|---:|---|
| 同Turnの即時勝利 | 1 | 1 | ゲーム終端まで厳密に支配 |
| 同TurnのKO経路 | 10 | 7 | 同Turn戦術的支配 |
| positive Attack経路 vs 実damage 0 | 2 | 1 | 同Turn戦術的支配 |
| **合計** | **13** | **9** |  |

厳密な1件は`87639549 T12`。

- 残りPrize 1
- Active Mega Froslass exへBasic Water Energyを付けるOptionが合法
- 相手Active AlakazamはHP40、公開handCount 26
- Attach後のResentful RefrainでそのTurnに勝利可能
- 実際はBench Mega Starmie exへAttachし、攻撃せず敗戦

この1件は、代替経路の後にゲームが終了するため、将来のBench育成価値を持ち出して実選択を正当化できない。

残る12件は同Turnの出力では明確に上回るが、KO後の盤面・手札・次Turnまで含む完全なゲーム木を再実行していない。そのため「ゲーム全体の厳密なPareto支配」とは書かない。

### 10.3 13 nodeの内訳

| 経路 | node | 内容 |
|---|---:|---|
| Active FroslassへWater Attach → Attack | 8 | 7 KO、1即時勝利 |
| Bench FroslassへWater Attach → Retreat → Attack | 2 | Water Gun 20ではなく同TurnKOへ到達 |
| Retreat → powered Froslass → Attack | 1 | Yveltal 40ではなく同TurnKOへ到達 |
| Bench StarmieへWater Attach → Surfing Beach → Attack | 2 | 実damage 0 Attackではなくpositive Attackへ到達 |

これは新たに13件を追加発見したという意味ではない。項目3で確定した経路を、支配関係の強さに従って再監査した結果である。

### 10.4 複数のAttackが合法だったnode

Main nodeで複数のAttack Optionが同時に合法だったのは74 node。

| Active | node | 実選択・結果 |
|---|---:|---|
| Mega Starmie ex | 70 | Nebula BeamでKO 42、Nebula Beam非KO 12、Jetting Blow非KO 1、非終端のPlay／Evolve 15 |
| Mega Froslass ex | 4 | 4件すべてResentful RefrainでKO |

Mega Starmie exの非終端Play／Evolve 15 nodeは、**全15件で同Turn中に後続Attackを実行**した。したがって、Attackが合法な状態で準備行動を挟んだこと自体は支配違反ではない。

唯一Jetting Blowを選んで非KOだった`87487796 T11`では、相手Active HP270に対してJetting Blow 120、Nebula Beam 210であり、どちらもその場のKOには届かない。Jetting BlowにはBench pressureがあるため、Nebula Beamが全軸で支配しているとは言えない。

Nebula Beam非KOの12 nodeでも、Jetting BlowはActive damageが低い一方でBench damageを持つ。damageの配分先が異なるため、単一の数値比較だけでは支配関係にならない。

Froslassで2種類のAttackが合法だった4 nodeは、すべてResentful Refrainで実KOしていた。Attack選択の支配違反は確認しなかった。

### 10.5 Attackが合法なのにAttackしなかったTurn

一度はAttack Optionが合法だったが、そのTurnにAttackを選ばなかった例は6 Turnだった。

```text
87492128 T15
87555944 T12
87637402 T5/T15/T17/T19
```

6件すべて、合法だったのはMega Evolution exから既知のEX wallへ向ける、効果で止められるAttackだった。

- Jetting Blow → wall
- Resentful Refrain → wall

そのうち、Turn終端時点でもAttack Optionが残ったままENDしたのは2 node。どちらもJetting Blowがwallで止まる盤面だった。

したがって、

> Attack Optionが合法なのにENDした

という形だけでは異常ではない。**positive damage、KO、Prize、または具体的なattack effectが得られるか**まで確認する必要がある。

今回の保守的な全件走査では、直接Attackメニューに既に存在する確実なKO Attackを捨てて、非KO AttackまたはENDを選んだ新規例は見つからなかった。

### 10.6 Active進化15 nodeの扱い

Active進化を選ばず、同じBasicの低打点AttackまたはBench進化を優先した既知例は15 node。

- v7.3敗戦: 9
- v7.3勝利: 4
- v7.4敗戦: 2
- v7.4勝利: 0

Active進化後も同TurnAttackへ進め、damageが改善することは確認済みである。しかし、進化カードをActiveに使うかBenchに使うかで将来盤面が変わる。

そのため本項目では、

> **同Turnの局所支配候補ではあるが、将来を含む完全なPareto支配は未証明**

と固定した。

Issue5後に15 nodeから2 nodeへ減ったことは症状改善と整合するが、残存2件`87644371 T4/T6`は独立して修正対象になる。

### 10.7 Attach→有償Retreat 14件は支配確定にしない

同TurnにActiveへEnergyを付け、そのEnergyをRetreat Costとして失い、Attackしなかった経路は14件ある。

Energy損失は事実だが、次は未証明である。

- AttachしなければRetreat自体が合法だったか
- 交代先を変えずに同じ終端盤面へ到達できたか
- 交代による次Turnの生存・配置価値がなかったか

したがって、14件は引き続き**確定した資源損失**として保持するが、「別経路が全項目で支配していた」とは書かない。

### 10.8 Hard access deadlockは支配違反ではない

既知のHard access deadlockは15 Turn・5 Replayある。

これらは、そのTurnにpowered Benchへ到達する合法経路が存在しない。現在nodeで選べるAとBの比較ではなく、前Turn以前の資源配分・Active配置が原因となる。

したがって、支配関係検出で現在Turnの誤選択へ数えない。

### 10.9 この項目から確定できること

1. **ゲーム終端まで厳密に支配された実選択は1 node。**
   `87639549 T12`の即時勝利見逃し。

2. **同Turn戦術で支配された経路は、上記を含め13 node。**
   ただし12 nodeは将来盤面全体のPareto支配までは証明していない。

3. **複数Attack間の新しい支配違反は確認しなかった。**
   74 nodeを調べ、差はKO、Active damage、Bench damage、status、準備行動継続のいずれかで説明できた。

4. **合法Attackを使わなかった6 Turnは、すべてwallで止まるAttackだった。**
   Attack合法だけを根拠に異常判定してはいけない。

5. **Active進化15 nodeは局所改善だが、完全なPareto支配とは分ける。**

6. **Attach→有償RetreatとHard deadlockは、支配違反とは別カテゴリである。**
   前者はsequence resource loss、後者は前Turnのaccess設計問題。

7. **本項目から新しいIssue categoryは増えていない。**
   新規に見つかった直接Attack選択の支配違反は0。既知のComposite reachability、Active evolution、Retreat wasteの境界が明確になった。

### 10.10 修正後の監査条件

支配関係を回帰テストへ使う場合、少なくとも次を分ける。

#### 必ず反転させる

- `87639549 T12`: 即時勝利経路
- 残る7件のActive Froslass Attach→KO
- `87482904 T11/T13`: Attach→Retreat→KO
- `87491060 T9`: Retreat→KO
- `87632037 T7/T9`: 0 damage Attackよりpositive Attack経路

#### 必ず維持する

- 複数Attack合法時にNebula BeamでKOした42 node
- FroslassのResentful Refrain KO 4 node
- 非終端Play／Evolve後に同TurnAttackした15 node
- wallに対して無効Attackを選ばず終えた6 Turn
- `87487796 T11`: Jetting BlowとNebula Beamがともに非KOで、Bench pressureとのtrade-offがある場面

#### 一律反転してはいけない

- Active進化15 nodeを、将来盤面を無視してすべて強制
- Attach→有償Retreat14件を、Retreatの必要性を見ずに禁止
- Attack合法なら必ずAttack
- Active damageだけでJetting Blow／Nebula Beamを比較

### 10.11 不明として残す事項

- 同Turn戦術支配12件を修正した後の完全な勝敗反転数。
- Active進化15件について、将来Bench価値まで含む最適行動。
- Attack target選択、Boss target、Tool Scrapper targetなどMain後の選択context全体に対する汎用Pareto走査。
- 相手の未公開手札や次のdrawを含む期待値。
- 未選択経路を実ゲームエンジンで再実行した場合の、状態異常・弱点・抵抗・継続効果の全相互作用。
- 新規Replayで同じ13 node型がどの頻度で再発するか。

### 状態

**研究項目10 完了。研究項目11「未来情報の混入監査」は未着手。**

ユーザー指定の保留研究 **「相手デッキ別の勝敗 × 選択された攻撃軸／軸未達」** は、本項目へ混ぜず未着手のまま保持する。

---


## 11. 未来情報の混入監査

### 11.1 監査対象と情報境界

本項目では、次の三種類を分離した。

1. **判断時点情報**
   - そのMain promptの`observation.current`、`select`、そこまでの`logs`
   - 公開盤面、公開discard、Stadium、状態異常、Energy、残りPrize枚数
   - 自分のhand、相手のhandCount／deckCount
   - 既知のカードルールと自分の固定デッキリスト

2. **事後情報**
   - 最終勝敗、終結条件、終局時手札
   - 初期Prizeの中身
   - 相手の完全な60枚構築
   - その判断より後のdraw、行動、damage、KO、生存

3. **counterfactual情報**
   - 未選択行動後の仮想盤面
   - 同Turn内に確定的に到達できるAttack／KO／Win
   - 次Turn以降の期待値

事後情報は、結果の分類やカード利用実績の記述には使える。しかし、**判断時点のPolicyが知っていた情報として扱うことはできない。**

対象は、順位照合可能だった**1,539 Main decision prompt**である。全1,540 Main nodeのうち、次frameの選択記録がない終端1 nodeは、判断入力の全件集計から除いた。

mirror self-play `87480598`は、これまでのCorpusと同じく勝利側Yserだけを1 Replayとして数えた。

### 11.2 Main promptで実際に見えていた情報

| 情報 | 1,539 Main promptでの状態 |
|---|---:|
| 自分のhand fieldがlist | 1,539 |
| 自分のhandにcard identityあり | 1,538 |
| 相手handCountあり | 1,539 |
| 相手hand identityあり | **0** |
| 自分の`current.deck` identityあり | **0** |
| 相手の`current.deck` identityあり | **0** |
| `select.deck` identityあり | **0** |
| 自分のPrize identityあり | **0** |
| 相手のPrize identityあり | **0** |
| terminal resultが見えていた | **0** |
| `current.looking`が非null | **0** |
| prompt時点のlogsあり | 1,539 |

Main promptでは、相手の手札内容、双方の山札内容、Prize内容、最終勝敗は見えていなかった。

Prizeはカードidentityではなく`None` placeholderの配列として渡されるため、残り枚数だけは判断時点で利用できる。相手handもidentityは`None`だが、`handCount`は公開されている。

自分のhand identityがない1 promptは`87631518`のhandCount 0状態であり、隠蔽ではなく空手札だった。

### 11.3 Search contextのdeck view

監査対象側の全active selection promptは2,958件だった。そのうち`select.deck`にcard identityが入ったものは456件。

- 456件すべてMainではなく、deck search／card selection側の`select.type=1`
- 456件すべて、cardの`playerIndex`は現在の自分側
- Main 1,539 promptでは`select.deck`は0件

したがって、提供ソースの`BoardView.deck_view = self.select.deck or []`は、**合法なsearch contextで現在見えている自分の山札view**を読む構造であり、Main判断時に未来のdraw順や相手deckを取得してはいない。

ただし、Replayファイル全体には両agentのobservationが保存される。分析者が相手agent側のsearch viewを後から読むと、Yserがその時点で知らなかった相手deck情報を得られる。相手デッキfamily分類はこの種の**分析者側事後情報**であり、Policy入力ではない。

### 11.4 提供ソースの入力監査

提供済みソーススナップショットで、主要評価が参照する情報を確認した。

- 自分のhand: `self.me.hand`
- 自分／相手の公開discard、Active、Bench、Energy
- 相手handの**枚数**: `self.opp.handCount`
- 残りPrize枚数: `len(self.me.prize)`
- 相手ActiveのPrize価値: 公開card metadataの`ex / megaEx`
- 山札: `self.select.deck`が合法に開かれたselection contextだけ
- 過去Attack: 現promptの`obs.logs`を後方走査

提供ソースがReplay全体の`steps`、top-level `rewards`、top-level `statuses`を参照する箇所は検出しなかった。

- raw token `steps`参照: False
- raw token `reward/rewards`参照: False
- raw token `statuses`参照: False

`_recent_my_attack_id()`は現在の`obs.logs`から過去の自分のAttackを探す。これは履歴参照であり、後続stepの参照ではない。

以上から、**提供ソースそのものが最終勝敗、未来draw、相手hand identity、相手deck identityを直接読む証拠は確認しなかった。**

これはコード全体に未来予測の誤差がないという意味ではない。公開盤面から相手の最大damageや進化可能性を推定する処理はあるが、それはstatic card knowledgeを使った推定であり、隠れた実手札を読んでいるわけではない。

### 11.5 研究項目1～10の情報由来

| 項目 | 事後／未来情報の使用 | 使用目的 | Policy正誤への使用可否 |
|---|---|---|---|
| 1 勝ちの質・敗戦分類 | 最終勝敗、終結条件 | 勝利経路と敗戦群の分類 | 分類には可。勝ったから正しい／負けたから誤り、は不可 |
| 2 ActionScore差 | 判断時点snapshot＋提供ソース | 同一nodeの順位再構成 | 可。未来drawは不使用 |
| 3 複合経路 | 実行済み後続行動、同Replay後半の成功例 | 実経路の記述、static mechanicsの確認 | 実行済み経路の記述には可。後の成功を当時の知識としては不可 |
| 4 カード利用価値 | 終局時hand、後続Attack／Prize | 実利用頻度の記述 | 構築候補抽出には可。未使用＝不要、とは断定不可 |
| 5 Attacker起動 | 後の初Attack、生存、discard移動 | 観測起動率・待機時間 | 記述には可。耐久・最適軸の因果断定は不可 |
| 6 資源分配 | Turn終端、後続Retreat／Attack | 実sequenceの分類 | sequence損失には可。初手Attach単独の最善性へ直接変換不可 |
| 7 初手・事故 | 最終勝敗、初期Prize identity | 結果との観測関係、deck安定性 | 事後分析のみ。Prize内容をPolicy入力にしてはならない |
| 8 相手family別 | 相手の完全deck、最終勝敗 | matchup stratification | 事後集計のみ。初期の軸判断へfull deck labelを与えるのは禁止 |
| 9 感度分析 | 既知failure／guard label | 係数変更の影響半径 | regression研究には可。独立性能評価ではない |
| 10 支配関係 | 判断時点公開状態＋同Turn deterministic route | 即時Win／KOの局所比較 | 即時終端1件は可。次Turn以降の完全支配は未証明 |

### 11.6 強い結論の再監査

#### A. `87639549 T12`の即時勝利

この判定に必要な情報は、すべてT12のMain promptで公開されていた。

- 自分の残りPrize 1: Prize placeholderの長さ
- Active Mega Froslass ex、Energy 0
- 相手Active Alakazam HP140
- 相手handCount 19
- Basic Water Energyが自分のhandにある
- ActiveへのAttach Optionが合法
- 公開handCountを使うResentful Refrain: 950 damage
- Alakazamは公開card metadata上、1 Prizeの通常Pokémon

この経路は同Turnにゲーム終了まで到達するため、未来drawや相手responseを必要としない。**未来情報混入なしで維持できる唯一の勝敗反転証明**である。

#### B. 残る12件の同Turn戦術支配

後の勝敗は証明していない。公開盤面とstatic ruleから、同Turn中のpositive Attack／KOへ到達できる範囲だけを認定している。

同Replayの後半で同じ経路が成功した事実は、card mechanicsの照合には使えるが、当時のPolicy入力ではない。今後の記述では、次の順に証拠を置く。

1. そのnodeの公開盤面
2. そのnodeの合法Option
3. static card rule
4. 同Replay後半の成功例は補助確認

#### C. 次Turn生存・勝敗因果

Wally、Hero's Cape、Attacker生存、初期Active別勝率などは、後の結果を使った観測値である。既存項目は「使わなければ倒れた」「初期Activeが勝因」とは書いていないため、因果判定への未来混入は確認しなかった。

#### D. Attach→有償Retreat 14件

Attach判断時点から見れば、後でそのEnergyをRetreat Costとして失うことはまだ実行前である。本監査で確定しているのは、**実際に選ばれたsequence全体がEnergyを失い、Attackへ接続しなかった**こと。

したがって、14件を「Attach単独が必ず誤り」として学習labelにしてはならない。sequence-level regression caseとして扱う必要がある。

### 11.7 確認された混入リスク

#### 1. 相手full deck labelの逆流

項目8のfamily labelは事後情報である。今後の「デッキ別の勝敗 × 選択軸／軸未達」研究では、full deck familyを集計軸に使ってよいが、各TurnのPolicy評価には次を記録する必要がある。

- 軸を決めた時点で公開されていた相手card
- その時点でfamilyが未判明／推定可能／ほぼ確定のどれだったか
- 後から判明した60枚情報を、当時の判断材料へ混ぜていないか

相手familyが後から判明しただけなら、序盤の軸選択を「読み違い」とは判定できない。

#### 2. 初期Prize identityの逆流

項目7で集計したPrize内容はpost-game情報である。

- `主力2枚がPrizeだった`
- `Wally 2枚がPrizeだった`

という結果はdeck安定性の研究には使える。しかし、その試合中にPolicyが特定cardのPrize落ちを知っていたとは扱えない。

Policyが利用できるのは、公開済みのhand、discard、盤面と固定deck枚数から計算する**残存可能性**までである。

#### 3. 同じ68 Replayによる発見・調整・評価

項目9では、同じ68 Replayを使ってfailureを発見し、閾値や仮想fieldの感度も測定した。

これはゲーム内の未来情報混入ではないが、**corpus leakage／過適合リスク**である。

現在の68 Replayは、今後次の用途に限定する。

- 既知failureの再現
- normal guardの保護
- rank-diffと影響半径
- regression corpus

同じ68 Replay上の改善数を、未知試合での勝率上昇証拠にしてはならない。

新しい修正の実戦性能は、修正前に件数と評価条件を固定した新規Replay群で測る必要がある。その新規群を見て再調整した時点で、その群もdevelopment corpusとなり、さらに別の未見群が必要になる。

### 11.8 既存記録の訂正

未来情報混入とは別件だが、項目間照合で1箇所の過剰認定を確認した。

項目1の`87492128`には、

```text
T3 Active進化見逃し、T15 合法Attackを残してEND
```

と記録している。

項目10の全件照合により、`87492128 T15`で残っていたAttackはEX wallに止められるAttackだった。したがって、**T15を確定損失として扱う記述は撤回する。**

- `87492128`のW2分類は、T3 Active進化見逃しがあるため変更なし
- W1／W2の件数変更なし
- 訂正対象はT15の追加理由だけ

append-only監査のため、過去行を上書きせず、本項目を正式な訂正記録とする。

### 11.9 この項目から確定できること

1. **1,539 Main promptに、相手hand identity、deck identity、Prize identity、terminal resultは入っていなかった。**
2. **提供ソースがReplay全体の未来stepや最終rewardを読む証拠は確認しなかった。**
3. **`87639549 T12`の即時勝利証明は、判断時点の公開情報だけで成立する。**
4. **相手deck family、初期Prize identity、終局時hand、生存結果は事後分析専用である。**
5. **同Turn後続行動を使った研究は、実sequenceの記述には有効だが、最初のAction単独の知識へ逆流させてはならない。**
6. **現在の68 Replayは既にdevelopment／regression corpusであり、独立した勝率検証setではない。**
7. **項目1の`87492128 T15`は確定損失から撤回するが、集計値は変わらない。**

### 11.10 不明として残す事項

- Kaggle engine内部で、agentへ渡す前のstate生成にhidden field leakがないか。今回確認したのは保存Replayのobservationと提供ソース。
- 提供ソーススナップショットが、各submissionで実行されたコードとbyte単位で同一か。
- 未選択の複合経路を実engineで再実行した場合の全相互作用。
- 相手familyが各Turnでどの時点まで公開cardだけで識別可能だったか。これは保留中の軸研究で個別に記録する。
- 新規holdout ReplayでのIssue発生率と勝率。

### 状態

**研究項目11「未来情報の混入監査」完了。最初に列挙した研究項目はここまで完了。**

ユーザー指定の保留研究 **「相手デッキ別の勝敗 × 選択された攻撃軸／軸未達」** は、本項目へ混ぜず未着手のまま保持する。

---

## 12. 相手デッキ別の勝敗 × 選択された攻撃軸／軸未達

### 12.1 目的と定義

本項目は、項目8で保留した次の研究を独立して実施した。

> 相手デッキ別の勝敗を、その試合で実際に到達した攻撃軸、最初に完成した軸、完成したが攻撃へ到達しなかった軸へ分ける。

対象はmirror self-play `87480598` を除く対外67 Replay。

相手familyは試合終了後に判明した60枚構築による監査用分類であり、試合中のPolicyがそのfamilyを知っていたとは扱わない。

本項目では意図を推測せず、Replay上で直接観測できる事実だけを使う。

- **最初に完成したMega**: Mega Starmie ex／Mega Froslass exのうち、盤面へ先に現れたもの
- **攻撃到達**: `visualize.logs`に、そのcardをattackerとする`Attack` logが1回以上存在
- **実到達ルート**: Mega attackerが実際に攻撃した順序
- **完成軸未到達**: 完成Megaが盤面へ現れたが、そのMegaは一度も攻撃しなかった
- **Ready未攻撃**: 項目5と同じ近似Energy条件を満たした状態を観測したが、一度も攻撃しなかった
- **Cinderace**: Mega軸とは分け、bridge／sub-attackerとして別記録

Energy-ready近似:

- Mega Starmie ex: Energy 1枚以上
- Mega Froslass ex: Basic Water Energy 1枚以上
- Cinderace: Energy 1枚以上

これはEnergy条件だけの近似であり、状態異常、相手効果、Attack固有条件を完全再現していない。

個別表の記号:

- `A(n)`: Attackへ到達、括弧内はAttack回数
- `R`: Energy-readyを観測したがAttackなし
- `E`: 完成体は出たがreadyを観測せずAttackなし
- `B`: Basicだけ盤面へ出た
- `—`: 盤面出現を確認せず

### 12.2 全体の軸到達

対外67 Replayで、主なattackerのAttack回数は次のとおり。

| Attacker | Attack回数 | AttackしたReplay |
|---|---:|---:|
| Mega Starmie ex | 210 | 58 |
| Mega Froslass ex | 32 | 13 |
| Cinderace | 71 | 21 |

最初に完成したMega:

| 最初に完成したMega   |   試合 |   勝 |   敗 |   Starmie攻撃到達 |   Froslass攻撃到達 | 最初の完成軸が未到達   |
|:---------------------|-------:|-----:|-----:|------------------:|-------------------:|:-----------------------|
| Starmie先            |     44 |   22 |   22 |                42 |                  1 | 2                      |
| Froslass先           |     14 |    6 |    8 |                 9 |                  9 | 5                      |
| 同一Turnで双方       |      7 |    1 |    6 |                 7 |                  3 | 0                      |
| Mega完成なし         |      2 |    0 |    2 |                 0 |                  0 | —                      |

実際にAttackへ到達したMegaルート:

| 実到達ルート     |   試合 |   勝 |   敗 | 観測勝率   |
|:-----------------|-------:|-----:|-----:|:-----------|
| Starmieのみ      |     49 |   22 |   27 | 44.9%      |
| Froslassのみ     |      4 |    1 |    3 | 25.0%      |
| Froslass→Starmie |      7 |    3 |    4 | 42.9%      |
| Starmie→Froslass |      2 |    1 |    1 | 50.0%      |
| Mega攻撃なし     |      5 |    2 |    3 | 40.0%      |

確認できる事実:

1. 67試合中62試合で、StarmieまたはFroslassのMega攻撃へ到達した。
2. Starmieのみで攻撃した試合が49で、全体の73.1%。
3. Froslassが一度でも攻撃した試合は13。
4. Mega攻撃なしは5試合。
   - 3敗は主attackerのAttack自体が0
   - 2勝はCinderaceだけで攻撃して勝利
5. Cinderaceは21試合で攻撃し、15試合では最初の主attackerだった。
6. Cinderaceだけで勝った試合が2件あるため、Mega攻撃なしを自動的に軸失敗とは扱えない。

### 12.3 最初に完成した軸と実到達のずれ

最初に完成したMegaが、そのままAttackへ到達した割合は軸ごとに異なる。

- Starmie先完成: 44試合中42試合でStarmieがAttack
- Froslass先完成: 14試合中9試合でFroslassがAttack
- 同一Turnに双方完成: 7試合すべてで少なくとも一方がAttack
- Mega完成なし: 2試合、いずれも敗戦

最初に完成した軸そのものが未到達だったのは7 Replay。

- Starmie先完成だがStarmie未攻撃: 2
- Froslass先完成だがFroslass未攻撃: 5
- 勝敗: 4勝3敗

したがって、**最初に完成した軸が未到達だったという事実だけでは誤りとは言えない。**
別軸またはCinderaceで勝った正常例が4試合ある。

一方、完成したが一度も攻撃しなかったMegaは、軸instance単位で25件。

- Froslass: 21件
  - `R`: 2
  - `E`: 19
- Starmie: 4件
  - `R`: 2
  - `E`: 2

重複を除くと24 Replay。大半はreadyになる前の未到達であり、access failureと同一視できない。

### 12.4 3試合以上ある相手family × 実到達軸

`Froslass関与`は、Froslassのみ／Froslass→Starmie／Starmie→Froslassを合算したもの。

| 相手family                  | 全体   | Starmieのみ   | Froslass関与   | Mega攻撃なし   |   完成軸未到達 |   完成したが未攻撃 |
|:----------------------------|:-------|:--------------|:---------------|:---------------|---------------:|-------------------:|
| Mega Lucario ex系           | 5勝8敗 | 5勝5敗 / 10   | 0勝2敗 / 2     | 0勝1敗 / 1     |              0 |                  2 |
| Alakazam系                  | 2勝8敗 | 0勝5敗 / 5    | 2勝2敗 / 4     | 0勝1敗 / 1     |              2 |                  5 |
| Mega Abomasnow ex系         | 3勝4敗 | 1勝3敗 / 4    | 2勝1敗 / 3     | 0勝0敗 / 0     |              0 |                  0 |
| Mega Starmie ex／Cinderace  | 2勝3敗 | 2勝3敗 / 5    | 0勝0敗 / 0     | 0勝0敗 / 0     |              0 |                  3 |
| Teal Mask Ogerpon ex草系    | 2勝3敗 | 1勝2敗 / 3    | 0勝0敗 / 0     | 1勝1敗 / 2     |              2 |                  4 |
| Archaludon ex系             | 1勝3敗 | 1勝2敗 / 3    | 0勝1敗 / 1     | 0勝0敗 / 0     |              0 |                  1 |
| Dragapult ex系              | 1勝3敗 | 1勝3敗 / 4    | 0勝0敗 / 0     | 0勝0敗 / 0     |              0 |                  1 |
| Hop系                       | 2勝1敗 | 2勝0敗 / 2    | 0勝1敗 / 1     | 0勝0敗 / 0     |              1 |                  2 |
| Mega Kangaskhan ex／Crustle | 1勝2敗 | 1勝2敗 / 3    | 0勝0敗 / 0     | 0勝0敗 / 0     |              0 |                  0 |

この表は観測結果であり、軸の因果効果を示さない。対戦相手、初手、先後、version、既知Policy欠陥を統制していない。

### 12.5 family別に確認できる特徴

#### Alakazam系

- 全体: 2勝8敗
- Starmieのみ: 0勝5敗
- Froslass関与: 2勝2敗
- Mega攻撃なし: 0勝1敗
- 完成したが未攻撃のMegaあり: 5/10

この10試合では、2勝ともFroslassが実際に攻撃している。
ただしFroslass同Turn到達見逃しが3 Turn・3 Replayあり、うち2 Replayは敗戦。
したがって、

> Froslass関与時の観測成績が相対的に高い

ことは言えるが、

> AlakazamにはFroslassを選べば勝てる

とは言えない。

#### Mega Lucario ex系

- 全体: 5勝8敗
- Starmieのみ: 5勝5敗
- Froslass関与: 0勝2敗
- Mega攻撃なし: 0勝1敗

13試合中10試合がStarmieのみで、唯一まとまった勝利群もStarmieのみ。
ただしFroslass関与は2試合しかなく、Froslass不適合の証拠としては弱い。

#### Mega Abomasnow ex系

- 全体: 3勝4敗
- Starmieのみ: 1勝3敗
- Froslass関与: 2勝1敗

Froslass関与3試合の観測成績はStarmieのみ4試合より高い。
その一方、勝利`87482904`にはFroslass同TurnKO経路を2回見逃した後、後のTurnで同型経路に到達した事実がある。
軸の選択より、**Froslassへ到達するtiming**が問題になっている。

#### Teal Mask Ogerpon ex草系

- 全体: 2勝3敗
- Starmieのみ: 1勝2敗
- Froslass関与: 0試合
- Mega攻撃なし: 1勝1敗
- 完成したが未攻撃のMegaあり: 4/5
- 最初の完成軸未到達: 2/5

5試合でFroslass Attackは0。
`87644371`ではFroslassが先に完成したがAttackへ到達せず、同TurnKO経路の見逃しも確定している。
一方、`87635272`はFroslass完成・Starmie readyのまま、Cinderaceだけで勝っている。

よって「Froslass未達」には、敗戦上の問題例と、別軸で完遂した正常例が混在する。

#### Archaludon ex系

- 全体: 1勝3敗
- Starmieのみ: 1勝2敗
- Froslass関与: 0勝1敗

Froslass関与は`87643286`の1敗だけで、その試合にはActive FroslassへのWater Attachによる同TurnKO見逃しがある。
1試合のため軸相性は判断できない。

#### Dragapult ex系

- 全4試合がStarmieのみ
- 成績: 1勝3敗
- Froslass到達sample: 0

このCorpusではStarmie routeしか観測していないため、StarmieとFroslassの比較は不能。
`87487796`にはReady Bench access deadlockがある。

#### Mega Starmie ex／Cinderace mirror

- 全5試合がStarmieのみ
- 成績: 2勝3敗
- 3試合でFroslassが完成したが未攻撃

Froslassが選択肢として盤面へ出る例はあるが、実攻撃軸は全件Starmieだった。
`87495871`ではFroslass同TurnKO経路を2回見逃しているため、全件Starmie routeという結果の一部はPolicy欠陥で汚染されている。

### 12.6 Mega攻撃へ一度も到達しなかった5 Replay

|   Replay | ver   | 勝敗   | 相手family               | 実攻撃                  | Starmie   | Froslass   | Cinderace   | 既存監査との接続         |
|---------:|:------|:-------|:-------------------------|:------------------------|:----------|:-----------|:------------|:-------------------------|
| 87486700 | v7.3  | 敗     | Mega Lucario ex系        | No main attacker attack | B         | —          | —           | Active進化見逃し         |
| 87487251 | v7.3  | 敗     | Alakazam系               | No main attacker attack | E         | —          | —           | Attach→有償Retreat浪費   |
| 87665056 | v7.4  | 敗     | Teal Mask Ogerpon ex草系 | No main attacker attack | B         | —          | —           | 自Turn1回の短期Board-out |
| 87635272 | v7.4  | 勝     | Teal Mask Ogerpon ex草系 | Cinderace               | R         | E          | A(8)        | —                        |
| 87497826 | v7.3  | 勝     | Crustle系                | Cinderace               | R         | —          | A(8)        | —                        |

分類:

- **軸未成立の敗戦**
  - `87486700`: Staryu Basicのみ。Active進化見逃しあり
  - `87487251`: Mega Starmie完成、Energy-ready未観測、Attackなし
  - `87665056`: Staryu Basicのみ、自Turn1回でBoard-out
- **Cinderace完遂の勝利**
  - `87635272`
  - `87497826`

したがって、「Mega攻撃なし」という同じ表面結果でも、敗戦3件と勝利2件は分けて扱う必要がある。

### 12.7 最初の完成軸が未到達だった7 Replay

|   Replay | ver   | 勝敗   | 相手family               | 最初の完成   | 実到達ルート   | Starmie   | Froslass   | Cinderace   | 既存監査との接続                           |
|---------:|:------|:-------|:-------------------------|:-------------|:---------------|:----------|:-----------|:------------|:-------------------------------------------|
| 87481810 | v7.3  | 敗     | Alakazam系               | Froslass先   | Starmieのみ    | A(1)      | E          | A(5)        | —                                          |
| 87487251 | v7.3  | 敗     | Alakazam系               | Starmie先    | Mega攻撃なし   | E         | —          | —           | Attach→有償Retreat浪費                     |
| 87644371 | v7.4  | 敗     | Teal Mask Ogerpon ex草系 | Froslass先   | Starmieのみ    | A(1)      | E          | —           | Froslass同Turn到達見逃し; Active進化見逃し |
| 87635272 | v7.4  | 勝     | Teal Mask Ogerpon ex草系 | Froslass先   | Mega攻撃なし   | R         | E          | A(8)        | —                                          |
| 87491590 | v7.3  | 勝     | Walrein系                | Froslass先   | Starmieのみ    | A(6)      | R          | R           | —                                          |
| 87497826 | v7.3  | 勝     | Crustle系                | Starmie先    | Mega攻撃なし   | R         | —          | A(8)        | —                                          |
| 87510420 | v7.3  | 勝     | Hop系                    | Froslass先   | Starmieのみ    | A(6)      | E          | —           | —                                          |

7件中4件は勝利。
完成軸未到達を一律に減点すると、Cinderaceまたは別Megaで勝った正常経路を壊す。

### 12.8 確定済みの軸到達失敗／遅延

| 区分                        |   Turn |   Replay |   勝利Replay |   敗戦Replay | 内容                                                                     |
|:----------------------------|-------:|---------:|-------------:|-------------:|:-------------------------------------------------------------------------|
| Froslass同Turn到達見逃し    |     11 |        8 |            2 |            6 | Active/Bench Froslassへ到達可能だったが、同TurnのKO経路を選ばなかった    |
| Starmie同Turn到達見逃し     |      2 |        1 |            0 |            1 | 実damage 0のFroslass攻撃より、Starmieへ到達してpositive attack可能だった |
| Ready Bench access deadlock |     13 |        4 |            1 |            3 | ReadyなBench attackerがいるがActiveから到達できずENDを継続               |
| Active進化見逃し            |     15 |       12 |            4 |            8 | Active進化で同Turn damage改善できる局所経路を選ばなかった                |

重要な分離:

- **Replay単位の到達結果**
  - 最終的にその軸がAttackしたか
- **Turn単位の到達品質**
  - 到達可能だったTurnに、即時KO／positive attackへ進んだか

最終的にFroslassがAttackしたReplayでも、早いTurnのFroslass KO経路を見逃している例がある。
そのため、`軸到達済み`をそのまま正常Guardにはできない。

family別の確定same-turn route miss:

| issue                    | family                     |   turns |   replays |   wins |   losses |
|:-------------------------|:---------------------------|--------:|----------:|-------:|---------:|
| Froslass同Turn到達見逃し | Alakazam系                 |       3 |         3 |      1 |        2 |
| Froslass同Turn到達見逃し | Archaludon ex系            |       1 |         1 |      0 |        1 |
| Froslass同Turn到達見逃し | Cynthia's Garchomp ex系    |       2 |         1 |      0 |        1 |
| Froslass同Turn到達見逃し | Mega Abomasnow ex系        |       2 |         1 |      1 |        0 |
| Froslass同Turn到達見逃し | Mega Starmie ex／Cinderace |       2 |         1 |      0 |        1 |
| Froslass同Turn到達見逃し | Teal Mask Ogerpon ex草系   |       1 |         1 |      0 |        1 |
| Starmie同Turn到達見逃し  | Mega Lucario ex系          |       2 |         1 |      0 |        1 |

### 12.9 設計上の含意

Replay事実から、軸評価には少なくとも次の状態分離が必要。

```text
未配置
↓
Basic配置
↓
Mega完成
↓
Energy-ready
↓
Activeへ到達可能
↓
Attack
↓
positive damage / KO / Prize / Win
```

現在の集計で特に重要なのは、次の二つが別物であること。

1. **軸を作らなかった／完成しなかった**
2. **軸は完成・readyだがActiveへ到達できなかった**

また、完成したFroslassが未攻撃だった21件のうち、ready未攻撃は2件だけ。
したがって、Froslass未使用の主因をすべてActive accessへ置くことはできない。
多くはWater Energyを含むready化以前で止まっている。

一方、同Turn Froslass到達見逃しは11 Turn確認済みであり、ready化・accessが可能な局面でもPolicyがroute価値を拾えていない。

必要な評価は固定の軸bonusではなく、

```text
この行動で軸がどの段階からどの段階へ進むか
+
そのTurn中にAttack／KOへ到達できるか
+
現在の相手Active／公開Threatに対して、その到達が具体的価値を持つか
```

である。

### 12.10 この項目から確定できること

1. **Starmieが実戦の主軸。**
   58/67 ReplayでAttackし、Starmieのみrouteは49試合。

2. **Froslassは限定的だが実在する第二軸。**
   13 ReplayでAttackし、Alakazam系とAbomasnow系の勝利に実績がある。

3. **Froslass先完成は、Starmie先完成より未到達が多い。**
   - Starmie先: 2/44未到達
   - Froslass先: 5/14未到達

4. **完成軸未到達は、単独では欠陥ではない。**
   7件中4件は別軸で勝利。

5. **Mega攻撃なしの5件は二種類。**
   3敗は主attackerへ到達せず、2勝はCinderaceだけで完遂。

6. **Alakazam系ではFroslass関与2勝2敗、Starmieのみ0勝5敗。**
   ただし確定したFroslass到達見逃しが含まれ、因果相性とは断定できない。

7. **Mega Abomasnow ex系ではFroslass関与2勝1敗、Starmieのみ1勝3敗。**
   ただしsampleは3対4で小さい。

8. **Dragapult ex系とmirrorは、実到達軸が全件Starmie。**
   Froslassとの比較sampleがない。

9. **Froslass未攻撃21件の大半はready以前。**
   ready未攻撃は2件で、単純な交代access問題だけでは説明できない。

10. **軸到達済みでもtiming欠陥は残る。**
    Froslass同Turn到達見逃し11 Turn、Starmie同Turn到達見逃し2 Turnを確認済み。

### 12.11 不明として残す事項

- 相手familyを、各軸選択時点の公開cardだけでどこまで識別できたか。
- first completionがPolicy上の意図的な主軸選択だったか、単なる合法進化消化だったか。
- Froslass完成後にWater Energyが付かなかった各試合の直接原因。
- 完成軸未到達7件で、未到達軸を使う方が勝敗上優れていたか。
- family別の真の最適軸。試合数が少なく、初手・先後・version・既知欠陥を統制していない。
- 軸変更を実engineでcounterfactual再生した場合の勝敗。
- 新規holdout Replayで同じfamily×axis傾向が再現するか。

### 12.12 全67 Replay個別記録

|   Replay | ver   | 勝敗   | 相手family                           | 最初の完成Mega   | 実到達ルート     | S     | F    | C    | 監査注記                                                                      |
|---------:|:------|:-------|:-------------------------------------|:-----------------|:-----------------|:------|:-----|:-----|:------------------------------------------------------------------------------|
| 87481810 | v7.3  | 敗     | Alakazam系                           | Froslass先       | Starmieのみ      | A(1)  | E    | A(5) | —                                                                             |
| 87482358 | v7.3  | 敗     | Alakazam系                           | Froslass先       | Froslass→Starmie | A(2)  | A(2) | A(1) | —                                                                             |
| 87485083 | v7.3  | 勝     | Alakazam系                           | Froslass先       | Froslassのみ     | —     | A(6) | E    | —                                                                             |
| 87485611 | v7.3  | 敗     | Alakazam系                           | Starmie先        | Starmieのみ      | A(1)  | B    | —    | Active進化見逃し                                                              |
| 87487251 | v7.3  | 敗     | Alakazam系                           | Starmie先        | Mega攻撃なし     | E     | —    | —    | Attach→有償Retreat浪費                                                        |
| 87491060 | v7.3  | 勝     | Alakazam系                           | 同一Turnで双方   | Froslass→Starmie | A(2)  | A(2) | —    | Froslass同Turn到達見逃し; Attach→有償Retreat浪費                              |
| 87630981 | v7.4  | 敗     | Alakazam系                           | Starmie先        | Starmieのみ      | A(2)  | E    | —    | Froslass同Turn到達見逃し; Attach→有償Retreat浪費                              |
| 87637949 | v7.4  | 敗     | Alakazam系                           | Froslass先       | Froslassのみ     | —     | A(2) | A(1) | —                                                                             |
| 87639017 | v7.4  | 敗     | Alakazam系                           | 同一Turnで双方   | Starmieのみ      | A(2)  | E    | A(1) | —                                                                             |
| 87639549 | v7.4  | 敗     | Alakazam系                           | Starmie先        | Starmieのみ      | A(4)  | E    | —    | Froslass同Turn到達見逃し                                                      |
| 87533017 | v7.3  | 勝     | Archaludon ex系                      | Starmie先        | Starmieのみ      | A(8)  | B    | A(2) | Active進化見逃し                                                              |
| 87632586 | v7.4  | 敗     | Archaludon ex系                      | Starmie先        | Starmieのみ      | A(4)  | B    | —    | —                                                                             |
| 87643286 | v7.4  | 敗     | Archaludon ex系                      | Starmie先        | Starmieのみ      | A(3)  | E    | —    | Froslass同Turn到達見逃し                                                      |
| 87650661 | v7.4  | 敗     | Archaludon ex系                      | 同一Turnで双方   | Froslass→Starmie | A(2)  | A(1) | —    | —                                                                             |
| 87638484 | v7.4  | 勝     | Comfey／Yveltal コントロール         | Starmie先        | Starmieのみ      | A(10) | —    | —    | —                                                                             |
| 87481258 | v7.3  | 勝     | Crustle系                            | Starmie先        | Starmieのみ      | A(6)  | —    | —    | Active進化見逃し                                                              |
| 87497826 | v7.3  | 勝     | Crustle系                            | Starmie先        | Mega攻撃なし     | R     | —    | A(8) | —                                                                             |
| 87488357 | v7.3  | 敗     | Cynthia's Garchomp ex系              | 同一Turnで双方   | Starmie→Froslass | A(3)  | A(2) | —    | Froslass同Turn到達見逃し; Attach→有償Retreat浪費; Ready Bench access deadlock |
| 87644912 | v7.4  | 勝     | Cynthia's Garchomp ex系              | Starmie先        | Starmieのみ      | A(6)  | E    | A(1) | —                                                                             |
| 87487796 | v7.3  | 敗     | Dragapult ex系                       | Starmie先        | Starmieのみ      | A(4)  | B    | A(1) | Ready Bench access deadlock                                                   |
| 87489956 | v7.3  | 敗     | Dragapult ex系                       | Starmie先        | Starmieのみ      | A(2)  | E    | —    | —                                                                             |
| 87642240 | v7.4  | 勝     | Dragapult ex系                       | Starmie先        | Starmieのみ      | A(4)  | —    | —    | Attach→有償Retreat浪費; Ready Bench access deadlock                           |
| 87642752 | v7.4  | 敗     | Dragapult ex系                       | Starmie先        | Starmieのみ      | A(4)  | B    | —    | Attach→有償Retreat浪費                                                        |
| 87493190 | v7.3  | 勝     | Hop系                                | Starmie先        | Starmieのみ      | A(5)  | B    | —    | —                                                                             |
| 87501720 | v7.3  | 敗     | Hop系                                | Froslass先       | Froslassのみ     | E     | A(2) | A(7) | Active進化見逃し                                                              |
| 87510420 | v7.3  | 勝     | Hop系                                | Froslass先       | Starmieのみ      | A(6)  | E    | —    | —                                                                             |
| 87490505 | v7.3  | 敗     | Marnie's Grimmsnarl ex系             | Starmie先        | Starmieのみ      | A(3)  | R    | A(3) | Active進化見逃し                                                              |
| 87643350 | v7.4  | 敗     | Marnie's Grimmsnarl ex系             | Starmie先        | Starmieのみ      | A(2)  | —    | A(4) | —                                                                             |
| 87482904 | v7.3  | 勝     | Mega Abomasnow ex系                  | Starmie先        | Starmie→Froslass | A(4)  | A(1) | —    | Froslass同Turn到達見逃し                                                      |
| 87493732 | v7.3  | 敗     | Mega Abomasnow ex系                  | Froslass先       | Froslass→Starmie | A(2)  | A(1) | A(1) | Active進化見逃し                                                              |
| 87494795 | v7.3  | 勝     | Mega Abomasnow ex系                  | Starmie先        | Starmieのみ      | A(1)  | B    | —    | Attach→有償Retreat浪費                                                        |
| 87633660 | v7.4  | 敗     | Mega Abomasnow ex系                  | Starmie先        | Starmieのみ      | A(1)  | —    | A(1) | —                                                                             |
| 87634734 | v7.4  | 敗     | Mega Abomasnow ex系                  | Starmie先        | Starmieのみ      | A(4)  | B    | —    | —                                                                             |
| 87641694 | v7.4  | 勝     | Mega Abomasnow ex系                  | Froslass先       | Froslass→Starmie | A(2)  | A(2) | —    | —                                                                             |
| 87645438 | v7.4  | 敗     | Mega Abomasnow ex系                  | Starmie先        | Starmieのみ      | A(4)  | B    | —    | Attach→有償Retreat浪費                                                        |
| 87488887 | v7.3  | 勝     | Mega Kangaskhan ex系                 | Starmie先        | Starmieのみ      | A(3)  | —    | A(6) | —                                                                             |
| 87509907 | v7.3  | 敗     | Mega Kangaskhan ex／Crustle          | Starmie先        | Starmieのみ      | A(2)  | B    | —    | —                                                                             |
| 87543559 | v7.3  | 勝     | Mega Kangaskhan ex／Crustle          | Starmie先        | Starmieのみ      | A(5)  | B    | A(7) | —                                                                             |
| 87637402 | v7.4  | 敗     | Mega Kangaskhan ex／Crustle          | Starmie先        | Starmieのみ      | A(5)  | B    | —    | Attach→有償Retreat浪費                                                        |
| 87483452 | v7.3  | 敗     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(2)  | B    | —    | —                                                                             |
| 87483996 | v7.3  | 勝     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(4)  | —    | A(2) | —                                                                             |
| 87484539 | v7.3  | 敗     | Mega Lucario ex系                    | 同一Turnで双方   | Starmieのみ      | A(3)  | E    | —    | —                                                                             |
| 87486700 | v7.3  | 敗     | Mega Lucario ex系                    | Mega完成なし     | Mega攻撃なし     | B     | —    | —    | Active進化見逃し                                                              |
| 87492654 | v7.3  | 敗     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(2)  | —    | A(1) | —                                                                             |
| 87495339 | v7.3  | 敗     | Mega Lucario ex系                    | Froslass先       | Froslassのみ     | B     | A(2) | A(1) | —                                                                             |
| 87517866 | v7.3  | 敗     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(2)  | B    | —    | Energy停止候補（未確定）                                                      |
| 87632037 | v7.4  | 敗     | Mega Lucario ex系                    | Froslass先       | Froslass→Starmie | A(2)  | A(4) | —    | Starmie同Turn到達見逃し; Attach→有償Retreat浪費                               |
| 87633136 | v7.4  | 勝     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(6)  | B    | R    | —                                                                             |
| 87636337 | v7.4  | 勝     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(6)  | —    | E    | —                                                                             |
| 87636873 | v7.4  | 勝     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(6)  | —    | —    | Attach→有償Retreat浪費                                                        |
| 87643838 | v7.4  | 勝     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(6)  | B    | —    | —                                                                             |
| 87646047 | v7.4  | 敗     | Mega Lucario ex系                    | Starmie先        | Starmieのみ      | A(2)  | E    | E    | Energy停止候補（未確定）                                                      |
| 87634201 | v7.4  | 勝     | Mega Manectric ex                    | Starmie先        | Starmieのみ      | A(3)  | —    | E    | —                                                                             |
| 87486157 | v7.3  | 敗     | Mega Starmie ex／Cinderace           | Starmie先        | Starmieのみ      | A(3)  | B    | —    | Active進化見逃し                                                              |
| 87494261 | v7.3  | 勝     | Mega Starmie ex／Cinderace           | Starmie先        | Starmieのみ      | A(2)  | —    | —    | Attach→有償Retreat浪費                                                        |
| 87495871 | v7.3  | 敗     | Mega Starmie ex／Cinderace           | 同一Turnで双方   | Starmieのみ      | A(3)  | E    | —    | Froslass同Turn到達見逃し; Active進化見逃し                                    |
| 87640085 | v7.4  | 敗     | Mega Starmie ex／Cinderace           | 同一Turnで双方   | Starmieのみ      | A(8)  | E    | —    | —                                                                             |
| 87640634 | v7.4  | 勝     | Mega Starmie ex／Cinderace           | Starmie先        | Starmieのみ      | A(5)  | E    | A(1) | —                                                                             |
| 87480740 | v7.3  | 勝     | Raging Bolt ex／Teal Mask Ogerpon ex | Starmie先        | Starmieのみ      | A(6)  | E    | —    | Attach→有償Retreat浪費                                                        |
| 87492128 | v7.3  | 勝     | Sylveon系                            | Starmie先        | Starmieのみ      | A(2)  | E    | A(9) | Active進化見逃し                                                              |
| 87555944 | v7.3  | 勝     | Sylveon系                            | Froslass先       | Froslass→Starmie | A(3)  | A(5) | —    | —                                                                             |
| 87521331 | v7.3  | 敗     | Teal Mask Ogerpon ex草系             | Starmie先        | Starmieのみ      | A(2)  | E    | —    | Active進化見逃し; Ready Bench access deadlock                                 |
| 87631518 | v7.4  | 勝     | Teal Mask Ogerpon ex草系             | Starmie先        | Starmieのみ      | A(6)  | E    | —    | Attach→有償Retreat浪費                                                        |
| 87635272 | v7.4  | 勝     | Teal Mask Ogerpon ex草系             | Froslass先       | Mega攻撃なし     | R     | E    | A(8) | —                                                                             |
| 87644371 | v7.4  | 敗     | Teal Mask Ogerpon ex草系             | Froslass先       | Starmieのみ      | A(1)  | E    | —    | Froslass同Turn到達見逃し; Active進化見逃し                                    |
| 87665056 | v7.4  | 敗     | Teal Mask Ogerpon ex草系             | Mega完成なし     | Mega攻撃なし     | B     | —    | —    | 自Turn1回の短期Board-out                                                      |
| 87491590 | v7.3  | 勝     | Walrein系                            | Froslass先       | Starmieのみ      | A(6)  | R    | R    | —                                                                             |

### 状態

**保留研究「相手デッキ別の勝敗 × 選択された攻撃軸／軸未達」完了。**

本項目で、最初に依頼された研究項目と、その後に指定された保留研究はすべて完了した。

---

## 総論

### 構成上の注記

当初提示した12研究項目のうち、

1. 勝ちの質
2. 回避可能敗戦／不可避敗戦

を、項目1「勝ちの質と回避可能敗戦の分類」として統合して実施した。そのため、元の項目番号と本MDの項目番号には1項目分のずれがある。

研究内容そのものの欠落は確認していない。その後に追加された「相手デッキ別の勝敗 × 選択された攻撃軸／軸未達」を本MDの項目12として収録した。

以後、項目の統合、分割、順序変更が必要になった場合は、実施前または実施報告時に明示する。

---

### 1. 監査全体の対象

監査対象は68 Replayである。

- v7.3: 38 Replay
- v7.4: 30 Replay
- self-play: 1 Replay
- 対外戦: 67 Replay
- 対外成績: **29勝38敗、観測勝率43.3%**
- 順位照合可能なMain decision prompt: **1,539**
- 対外戦の自Turn: **552**
- 対外戦で確認したAttack終端Turn: **403**

この67戦は、相手、seed、先攻後攻、初手、versionが統制された実験ではない。したがって、観測勝率やversion間の差を、そのまま修正効果や真のデッキ性能とは扱わない。

また、この68 Replayはすでに問題発見、係数感度、Guard選定へ使用した。今後は**development／regression corpus**であり、未知試合に対する独立評価setではない。

---

### 2. 最終結論

今回のReplay群から最も強く支持される結論は、次である。

> **現デッキには再現可能な攻撃勝ち筋がある。現在の主要な制約は、デッキそのものよりも、複数行動の到達可能性、Activeへのアクセス、即時KO価値の伝播を扱えないPolicy側にある。**

対外29勝中26勝は、AttackによってPrize取り切りまたはBoard-outへ到達している。相手のDeck-outだけで勝っているデッキではない。

一方、対外29勝中12勝には、勝利前に確定した損失行動が含まれていた。勝てたReplayにも欠陥が隠れており、勝利ログを一括で正常Guardにすることはできない。

38敗中19敗には少なくとも1件の確定損失がある。ただし、修正すれば勝利へ変わることまでReplay上で証明できたのは、`87639549 T12`の1敗だけである。

したがって、

- 「Policyを直せば少なくとも一部の取りこぼしは減る」は事実
- 「19敗すべて救える」は事実ではない
- 「修正後に勝率が何ポイント上がる」は不明
- 「現在のデッキでは上位へ行けない」とする証拠もない

という位置づけになる。

---

### 3. 現デッキの役割分担

#### Mega Starmie ex

対外67戦中58戦で攻撃し、210回Attackした。最も頻繁に実戦投入されている主力であり、試合を完了させる中心軸である。

実到達ルートがStarmieのみだった試合は49戦で、22勝27敗。母数が最も大きく、Mega Lucario ex系に対してもStarmieのみで5勝5敗を記録している。

Starmieへの投資自体は問題ではない。Bench AttachからSurfing BeachやRetreatを経由し、同Turnに攻撃した正常例も存在する。

問題は、すでにReadyなStarmieへ追加投資する一方、ActiveがEnergy 0のまま停止する場面があること。

- Active E0
- すでにReadyなBenchへ追加Attach
- 同TurnEND

という狭い条件は23 Turnあり、22 TurnのAttach先がStarmie lineだった。

これはStarmieが悪いのではなく、**既存Energy量と実際のActive到達可能性を分離できていない評価**の問題である可能性が高い。原因関数は未確認である。

#### Mega Froslass ex

対外67戦中13戦で攻撃し、32回Attackした。

攻撃回数はStarmieより少ないが、攻撃時の出力は高い。Alakazam系では、Starmieのみが0勝5敗だった一方、Froslassが攻撃した試合は2勝2敗だった。

ただし、これを純粋な相性差とは断定できない。Alakazam系敗戦には、FroslassへのWater Attachから即時KOまたは即時勝利へ到達できた見逃しが含まれている。

完成したが一度も攻撃しなかったFroslassは21個体。

- Energy-readyまで到達していた: 2
- Energy-ready以前で停止: 19

したがって、Froslassの主要問題は、完成後のAttack選択よりも、

> **Basic Water Energyを付け、実際に攻撃可能な状態へ到達させるまで**

にある。

Froslassを抜く根拠は出ていない。むしろ、Policyが現在十分に利用できていない高出力軸と見る方がReplay事実に合う。

#### Cinderace

対外67戦中21戦で攻撃し、71回Attackした。

直接Prize効率はStarmieやFroslassより低いが、

- 非ex attacker
- Energy加速
- free-retreat bridge
- Mega攻撃なしで試合を完遂した勝利2件

が確認されている。

したがって、Cinderaceを単純に「Prize効率が低いカード」として評価することはできない。

一方、終局時手札へ残る例や、Main中にPlayされない構造も多い。採用枚数の調整候補にはなり得るが、初手安定性、setup配置、Policyの利用能力を分離していないため、現時点ではデッキ変更根拠にしない。

---

### 4. 最も重要なPolicy欠陥

#### P0: Attach後の即時KO／Win到達価値が伝播しない

Active FroslassへのWater Attachから、そのTurnにKOへ到達できるのに見逃した例を8件確認した。

そのうち`87639549 T12`は、

- 自分の残りPrize 1
- 相手Active Alakazam HP140
- 相手公開handCount 19
- Active FroslassへのWater Attachが合法
- Resentful Refrainで950 damage相当

であり、その場で勝利できたことを公開情報だけで証明できる。

コード再構成では、AttachによってAttack IDが解禁されることは認識していても、後続Attackのdamage、KO、Prize、WinがAttach側へ伝播していない。

ただし、Attachした時点ではまだKOしていない。修正時は、

- 実際に発生したOutcome
- 同Turnに到達可能な後続Attack価値

を別fieldにしなければならない。

固定Resource加点で代用すると、既知8件をすべて逆転するために大きな加点が必要となり、即時KOではないAttachまで逆転した。構造条件として扱う必要がある。

#### P1: 複合行動経路とActiveアクセス

Attackの前に準備行動を必要としたAttackは多数存在する。

対外403 Attack終端Turnのうち、少なくとも115件はTurn開始時にAttackが合法でなく、同Turnの準備によってAttackへ到達していた。

実際に正常動作した経路:

```text
Attach → Attack
Attach → Retreat → Attack
Attach → Surfing Beach → Attack
Energy Switch → Attack
Wally → 再Attach／交代 → Attack
進化 → Attach → Attack
```

一方、未選択だった同Turn複合経路は13 node・9 Replayで確認した。

- Active FroslassへAttach → KO／Win: 8
- Bench FroslassへAttach → Retreat → Attack: 2
- Retreat → powered Froslass → Attack: 1
- Bench StarmieへAttach → Surfing Beach → Attack: 2

Ready Benchへ到達できずENDした既知deadlockは13 Turn・4 Replay。

この問題は、Attach、Retreat、Surfing Beachを個別に少し加点するだけでは解決しない。必要なのは、

> **現在の行動から、そのTurn内にどのAttackerへ到達し、どのAttackまで実行できるか**

というreachability評価である。

#### P2: AttachしたEnergyを同Turnの有償Retreatで失う

次のsequenceを14件確認した。

```text
ActiveへEnergy Attach
→ 同Turnに有償Retreat
→ 付けたEnergyをRetreat Costとして失う
→ Attackなし
```

勝利7件、敗戦7件に存在した。勝利ログでも欠陥が隠れる代表例である。

ただし、

- Energyを保持したままBenchへ移る交代
- free-retreat
- 状態異常解除
- 攻撃やKOへ接続するRetreat

と混同してはならない。

AttachまたはRetreat単体を罰するのではなく、**sequence全体で資源を失い、具体的利益へ接続しなかった場合**を評価する必要がある。

#### P3: 0 damage Attackは二つの別問題

確認した0 damage問題は、同じ修正で扱えない。

1. 評価器も0 damageと認識しているAttack
   - `87632037 T7/T9`
   - Tier30 Attackが有用な準備行動を打ち切った

2. 実エンジンでは0 damageだが、評価器は50 damage・KOと認識
   - `87638484`で8回
   - Tier調整では直らず、カード効果または継続効果をOutcome modelへ追加する必要がある

したがって、

- Non-KOかつ認識済み0 damage Attackの優先度
- damage modelの誤認

を別Issueとして修正する必要がある。

#### P4: Active進化の残存穴

Issue5により、Active進化見逃し症状は大きく減った。

- v7.3: 13 node
- v7.4: 2 node

これは明確な改善である。

残る`87644371 T4/T6`は、damage改善閾値50に対し、再構成上の改善量が20であるため昇格しない。

感度分析では、閾値を20へ下げた場合に変化したのは3 node・2 Turnだけで、正常Guard Turnへの変化は0だった。

ただし、同じ閾値が新規Replayでも安全とは限らない。独立修正として全Corpus rank-diffを行う必要がある。

#### P5: Opponent Threatと即時除去

Alakazam戦などで、

- 相手の公開handCountから次Attack damageが増える
- 次TurnにこちらがKOされる
- Bossまたは即時攻撃準備でThreatを処理できる可能性がある
- それよりDevelopmentを優先する

場面が確認されている。

ただし、全Corpusで相手次Turnの完全なAttack damageを再現した監査は未実施である。現段階では、特定Turnの事実と汎用Issue候補までは示せるが、全体発生件数や修正効果は不明。

カード名専用補正ではなく、公開盤面から、

- 相手が次Turn攻撃可能か
- 自ActiveがKOされるか
- 相手Threatを現在処理可能か
- 現在のPrize取得と将来の被害の交換

を評価する責務として設計する必要がある。

---

### 5. ActionScore監査から分かったこと

順位照合可能1,539 Main nodeの再構成では、実選択との一致率は高かった。したがって、Replay上の不自然行動の多くは、実行部分ではなく、現在の評価順序をPolicyが意図どおり選んだ結果である。

top1とtop2を最初に分ける主なfieldは、

- Tier
- Resource
- Option index

だった。

特にAttach即時KO見逃しでは、Attachと別の準備行動が同Tierに置かれ、後続KO価値が存在しないためResourceで負けていた。

これは「係数が少し足りない」より、

> **必要な事実がActionScoreへ載っていない**

問題である。

感度分析でも、

- High-value prep閾値の変更: 133～148 node変化
- Froslass Attach固定加点: 既知8件を直す値で20 node変化
- 一般的なKO reachability昇格: 43～51 node変化

となり、大域的な係数変更は影響範囲が広い。

一方、

- Active進化閾値20: 3 node・2 Turn
- 認識済み0 damage Attackの狭い降格: 3 node・3 Turn

は影響範囲が狭かった。

したがって、今後の基本方針は、

> **大域係数を動かす前に、欠けているFactと限定条件を追加する**

である。

---

### 6. 勝敗と相手デッキの解釈

family別の観測成績は、相性の確定値ではない。既知Policy欠陥、先攻後攻、初手、version、相手構築差が混在している。

#### Alakazam系

- 2勝8敗
- Starmieのみ: 0勝5敗
- Froslass関与: 2勝2敗
- 8敗中4敗に確定損失

Froslassが有力な対抗軸である可能性はある。ただし、Froslassへの即時Attachを見逃した敗戦が含まれるため、現行raw勝率から純粋な相性を推定できない。

#### Mega Lucario ex系

- 5勝8敗
- v7.3: 1勝6敗
- v7.4: 4勝2敗
- Starmieのみ: 5勝5敗

既知欠陥だけでは説明できない敗戦が多い一方、v7.4とStarmie軸にはまとまった勝利実績がある。構造的な絶望対面とは言えない。

#### Archaludon ex系

- 1勝3敗
- 3敗すべて自分の取得Prizeは1枚

低出力形状が最も一貫している。ただし1敗にFroslass即時KO見逃しがあり、残る2敗の最善手は不明。耐久相性、速度差、軸選択のどれが主因かはまだ確定できない。

#### Dragapult ex系

- 1勝3敗
- 3敗中2敗は自分の残りPrize1～2

raw勝率ほど一方的な試合内容ではない。Bench damage管理が主因だったかは未確認。

#### Teal Mask Ogerpon ex草系

- 2勝3敗
- Froslass攻撃到達: 0/5

ただし敗戦には、

- Froslass即時KO見逃し
- Ready Bench access deadlock
- 自Turn1回の短期Board-out

が含まれる。草系への構築不利とは判定できない。

---

### 7. 先攻後攻と初動

対外67戦の観測値:

- 先攻: 21勝19敗、52.5%
- 後攻: 8勝19敗、29.6%

両versionで先攻側の観測勝率が高かった。

ただし、相手、初手、versionを統制した比較ではないため、先攻の因果効果とは断定しない。

初動中央値は勝敗で大きく変わらなかった。

- 最初のEnergy Attach: 自Turn1
- 最初のEvolve: 自Turn2
- 最初のAttack: 自Turn2
- 最初のPrize: 自Turn4

v7.4はv7.3より最初のPrizeが早いにもかかわらず、raw win rateは低かった。したがって、序盤速度だけではv7.4の成績を説明できない。

明確な長期Energy停止例は`87646047`だが、draw、search、Energy使用Policyのどれが直接原因かは不明。

---

### 8. デッキ変更について

現段階では、先にデッキを変更しない方がよい。

理由:

1. 対外29勝中26勝がAttack終結で、現デッキには明確な勝ち筋がある
2. Starmie、Froslass、Cinderaceの三役に実戦上の異なる役割がある
3. FroslassやSurfing Beachなど、低使用に見えても具体的なKO／Prize接続例がある
4. Boss’s Orders、Cinderaceなどは、カードが弱いのかPolicyが使えていないのか未分離
5. Policy修正前に構築を変えると、既知欠陥の再現条件と原因分離を失う

デッキ変更を再検討する条件は、少なくとも次である。

- P0～P4を独立修正
- 既存68 Replayでtarget caseと正常Guardを通過
- 新規未見Replayを固定条件で取得
- その新規群で軸未達、カード滞留、対面別不足が再現
- Policy問題では説明できない構築上の欠損を確認

その段階で初めて、

- Cinderace採用枚数
- Boss’s Ordersの枚数または役割
- Energy配分
- Froslass到達支援
- 特定対面へのカード

を比較する。

---

### 9. 修正と検証の推奨順序

#### 第1段階: Active Attachからの即時KO／Win reachability

対象:

- 既知8件
- `87639549 T12`の即時勝利
- 正常なAttach→Attack
- 現在合法なKO／Win Attackをそのまま選ぶGuard

禁止:

- Attachへ実発生していないKO／Prize／Winを記録
- FroslassまたはWater Energyへの固定大加点
- 他のResource係数を同時変更

#### 第2段階: Composite access

対象:

```text
Attach → Retreat／Surfing Beach → Attack
Retreat → Ready attacker → Attack
```

必要:

- same-turn reachability
- paid／free retreatの分離
- ActiveとBenchのserial単位追跡
- Attackまで到達しない未来価値と、実Outcomeの分離

#### 第3段階: Attach→有償Retreat浪費

対象は14件のsequence-level case。

Attach単独、Retreat単独ではなく、

- 付けたEnergyの消失
- Attackなし
- 状態解除、KO回避、free-retreatなどの具体的利益なし

を条件にする。

#### 第4段階: 0 damage問題を二分

- 認識済み0 damage AttackのTier
- damage model誤認

を別Issue、別テスト、別差分にする。

#### 第5段階: Active進化残存穴

閾値20候補を独立適用し、既知3 nodeと正常進化Guardだけでまず検証する。

#### 第6段階: Opponent Threat

前段の即時KO、access、damage modelを直した後に扱う。そうしないと、Threat問題と「そもそも自分の攻撃経路を評価できない問題」が混ざる。

---

### 10. 各修正で必須の監査

修正ごとに、次を固定する。

1. 修正前の全1,539 Main node順位
2. 対象failure case
3. 正常Guard case
4. 全node rank-diff
5. top1変更件数
6. 変更した最初のfield
7. 既知の別Issueへの影響
8. 変更後の実Replay
9. 新規未見Replay群での発生率

採用条件:

- 対象caseが直る
- 正常Guardが維持される
- 無関係nodeの逆転理由を説明できる
- 係数ではなくFact責務が適切
- 実Outcomeと到達可能価値を混同しない

同じ68 Replayで改善しただけでは、実戦勝率改善とは判定しない。

---

### 11. 事実として言える範囲

#### 言える

- 現デッキには複数の実勝利軸がある
- Policyはその軸を十分に起動・接続できていない
- 即時KO、Composite access、Retreat浪費、0 damageの確定問題がある
- Issue5はActive進化症状を減らした
- 勝利Replayにも欠陥が存在する
- 係数全体調整より狭い構造条件の方が安全
- 68 ReplayのMain判断入力に相手手札内容、山札内容、Prize内容、最終勝敗の混入は確認されなかった

#### 言えない

- 既知19敗を直せば19勝増える
- v7.4のraw win rate低下がIssue5のせい
- Alakazam、Archaludon、草系が確定不利対面
- CinderaceやBoss’s Ordersが不要
- 閾値20が未知環境でも安全
- 修正すればレート1200へ到達する
- 現在の67戦がKaggle全体の相手分布を代表する

---

### 12. 総合判定

現状は、

> **デッキが弱くて勝てない状態というより、勝てる盤面と勝てる軸をPolicyが最後まで接続できず、勝ちを盤面上へ残している状態**

と判断するのが最も妥当である。

特に深刻なのは、単に評価値が低いことではなく、

- Attach後にKOできる
- Benchに攻撃可能個体がいる
- Surfing BeachやRetreatで到達できる
- Active進化で即時打点が上がる

という事実が、別々のAction間で切断されていること。

現デッキは、Starmieの即応性、Froslassの高出力、Cinderaceの加速と橋渡しを組み合わせる構造である。そのため、一手ごとの静的評価よりも、同Turn内の短い行動列を評価できるかどうかが、デッキ性能を引き出す鍵になる。

最優先はデッキ改造ではなく、

1. 即時KO／Win reachability
2. Active accessと複合経路
3. Retreat資源損失
4. 0 damage認識
5. Active進化残存穴

を分離して直し、既存Corpusで回帰を防いだうえで、新規Replayで実戦差を測ることである。

現時点で証明できる勝敗反転は1試合だけであり、期待勝率や最終レートは不明である。しかし、局所的な珍しいミスだけではなく、複数Replayと勝敗双方に共通する構造欠陥が確認されているため、**修正を続ける技術的根拠は十分にある。**

### 状態

**全研究項目および追加軸研究の総論完了。**

---

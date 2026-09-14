# デッキ表現力の解析 — 「我々のデッキは下手なのではなく語ることが少ない」の厳密化

- 担当: 解析B-metric(Fable 5)/ 2026-08-04(依頼は 2026-08-03 の引き継ぎ §5.5-B)
- 対戦ゼロ。使ったのは (a) 静的解析(api.py / main.py / EN_Card_Data.csv / deck.csv)、
  (b) **保存済み実リプレイ 276試合のパース**(`replay_analysis/eps*`、新規取得なし)のみ。
- 本文書の全数値に再現コマンドを付す(§7)。

---

## 0. 結論先出し

1. **前任者の「255項目中128未参照(50%)」は、前任者自身の方式の下では正確**(ツール再実行で
   保存出力と diff 完全一致)。ただし方式(クラス非修飾の名前grep)には**同名衝突による偽✓が24件**あり、
   意味的な未参照は **152/255(59.6%)**。偽✗(見落とし)は0件。
2. **未参照152項目の分類: A(デッキ由来)30 / B(操縦者由来)67 / C(冗長)45 / 判定不能10。**
   - 最大バケットは **B=操縦者が読んでいない**(67)。「デッキのせい」だけにはできない。
   - ただし **A=30項目は実測で裏づけ**: 現行デッキ235試合・10,604選択で発生0、同じ文脈が
     相手側(実ラダーのメタデッキ)では ACTIVATE 365 / ATTACH_FROM 762 / REMOVE_DAMAGE_COUNTER_COUNT 104 …と常時発生。
   - さらに B の内数 **13項目(EnergyType×12・SPECIAL_ENERGY)は「デッキが貧しいから読まなくても
     罰されない」**(単色エネ+特エネ1種をID定数で代替)。デッキを替えた瞬間に実害化する。
3. **表現力指標 DEX(静的・対戦ゼロ)で、我々のデッキは12本中最下位の40。**
   メタ11本の中央値68、最小値52(dudunsparce)。**フィールドの同型デッキ(meta starmie=65)にも −25**。
   「語ることが少ない」は数字になった。
4. **問い5(強いデッキに変える vs 語れるデッキを選ぶ、は同じか)への基礎回答: 違う。**
   実測4点で、**表現力最大(grimmsnarl DEX93)=勝率最下位(30.8%)**、**勝率最大(crustle 71.5%)は
   表現力9位(62)**。ただし**両立解が実在する**(tarountula: DEX 82 で3位、勝率68.8%で2位)。
   分水嶺は表現力の「能動成分」(選択を要求する機構)で、これは現操縦者の下では負債になる
   (D63の機構仮説と同一原理が指標の内部でも見える)。

---

## 1. 前任者の枠「128項目・50%未参照」の検算

### 1.1 元データの特定

- **生成器**: `verification/api_surface_audit.py`(2026-08-02、D62項目⓪)
- **生出力**: `docs/memo/api-surface-2026-08-02.txt`
- **正典の記述**: `docs/memo/data.md` 2026-08-02「API面の数え上げ監査」節(L3510)
- prior-art-audit-2026-08-02.md 側には数え上げ本体は無い(APIの言及1箇所のみ)。

### 1.2 数え方(何を1項目としたか)

`cg/api.py` の **IntEnum の全メンバ + dataclass の全フィールド = 各1項目**。
21クラス・255項目(Enum 8クラス137メンバ + dataclass 13クラス118フィールド)。
判定は **`\b名前\b` の単語grep**を、`#` コメントを行内除去した main.py 全文
(docstring・文字列は残る)に当てる。**クラス非修飾**(どのクラスの同名かを区別しない)。

### 1.3 検算結果

- 手計算での合計: 総255・未参照128・参照127 — **加算は正しい**。
- **ツール再実行**(starmie-aggro ディレクトリ): 出力は保存された
  api-surface-2026-08-02.txt と **diff 完全一致**(21クラス/255項目/127参照/128未参照)。
- **方式の限界は前任者自身が脚注で明記**(「識別子のgrepであり意味的な使用を保証しない。
  人が1件ずつ見て判断する」)。本文書がその「1件ずつ」である。

### 1.4 厳密再判定 — 未参照は128ではなく152

厳密基準: Enumメンバは **`クラス名.メンバ` の修飾参照**(コメント除去後のコードのみ)。
dataclassフィールドは **属性アクセス `.field` / 辞書キー `["field"]`・`get("field")` /
`getattr(x,"field")`** を全出現行つきで抽出し、同名フィールドは受け手の型で1件ずつ帰属
(帰属表は §7 のスクリプトが出力する証跡と対応)。

**結果: 意味的参照 103 / 未参照 152(59.6%)。前任者比 +24 は全て「偽✓→✗」で、偽✗は0件。**

| 偽✓の型 | 件数 | 項目 |
|---|---|---|
| ログ系が丸ごと未読なのに同名衝突で✓ | 10 | LogType.{SWITCH,PLAY,ATTACH,EVOLVE,ATTACK} / Log.{type,playerIndex,cardId,attackId,result}(`obs.logs` は一度も読まれない) |
| Enumの同名メンバ衝突 | 6 | AreaType.{STADIUM,TOOL}(実体はCardType側)/ SelectContext.{MAIN,ATTACK,EVOLVE} / SelectType.EVOLVE(実体はSelectType/OptionType側) |
| OptionTypeの暗黙処理を✓扱い | 2 | OptionType.{CARD,DISCARD}(修飾参照なし。CARDは型内で暗黙処理=C、DISCARDは全576側で提示実測0) |
| ローカル変数・別クラス属性との衝突 | 6 | Option.count(変数`count`×10)/ Option.cardId / Card.playerIndex / Skill.name / Attack.{name,text} |

> 教訓(§3.1系列の5例目): この24件も「計器は堂々と数字を出していた」型。
> 単位の罠は「チーム/遭遇」だけでなく**「名前/意味」**にもある。

### 1.5 クラス別ブリッジ表(前任者→厳密)

| クラス | 項目数 | 前任者✓ | 厳密✓ | 厳密未参照 |
|---|---:|---:|---:|---:|
| AreaType | 12 | 9 | 7 | 5 |
| EnergyType | 12 | 0 | 0 | 12 |
| CardType | 7 | 6 | 6 | 1 |
| SpecialConditionType | 5 | 0 | 0 | 5 |
| SelectType | 11 | 8 | 7 | 4 |
| SelectContext | 49 | 19 | 16 | 33 |
| OptionType | 17 | 10 | 8 | 9 |
| LogType | 24 | 5 | 0 | 24 |
| Card | 3 | 2 | 1 | 2 |
| Pokemon | 9 | 7 | 7 | 2 |
| PlayerState | 13 | 7 | 7 | 6 |
| State | 12 | 5 | 5 | 7 |
| Option | 14 | 10 | 8 | 6 |
| SelectData | 10 | 6 | 6 | 4 |
| Log | 24 | 5 | 0 | 24 |
| Observation | 4 | 3 | 3 | 1 |
| SearchState | 2 | 2 | 2 | 0 |
| ApiResult | 2 | 2 | 2 | 0 |
| Skill | 2 | 2 | 1 | 1 |
| CardData | 18 | 14 | 14 | 4 |
| Attack | 5 | 5 | 3 | 2 |
| **計** | **255** | **127** | **103** | **152** |

---

## 2. 分類の判定基準(分類前に固定)

対象 = 意味的未参照152項目。以下を**この順**で判定し、最初に該当した箱に入れる。

- **C(どのデッキでも不要/冗長)**: その項目の情報が、**既に参照している項目から構造的に
  導出できる**(例: SelectContext.MAIN は参照済み SelectType.MAIN と1:1)。各Cに導出元を明記。
- **A(デッキ由来 — 我々のデッキに機構が無いから活性化しない)**:
  (i) その項目が非自明になる引き金が**自デッキのカード機構**であり、
  (ii) starmie-aggro の60枚(15種、効果全文を精査)にその機構が0枚、
  (iii) **相手起因で我々に提示される経路が無い**(TCG慣例: 効果のコントローラが選ぶ)、かつ
  (iv) **実測で裏づく**(現行デッキ側=cur 239側/235試合・10,604選択で発生0)。
- **B(操縦者由来)**: 現デッキのままでも値が変わる/選択が提示される/情報が得られるのに読んでいない。
  実測発生があるものは件数を付す。
- **判定不能**: エンジン実行なしに A/B を確定できない(発火経路が特定できない等)。

**証拠源**
1. **実リプレイ・センサス**(本解析で新設、§7): ローカル保存済みの実ラダー276試合を、
   **TeamNames ではなく steps[1] の60枚実体**で side 同定(cur=現行デッキと完全一致239側 /
   oldY=旧我々14側 / meta=実ラダー相手299側)。ACTIVE エントリの select のみ計数。
2. **カードDB**: 我々の15種+比較11デッキの全効果テキスト。
3. **api.py の仕様コメント**とホスト裁定(ABILITY=能動 / SKILL=常在)。

**センサス計器の検証(2不変量)**: SETUP_ACTIVE_POKEMON = **239 = cur側の総数と完全一致**
(1試合側あたり厳密に1回)/ IS_FIRST = **130 ≈ 総側数の半分**(コイン勝者のみ)。
二重計上があれば 478 / 260 になるはずで、なっていない。

**開示(自分が踏みかけた罠2件)**
- センサス v1 は `TeamNames.index("Yser")` で side を決めており、**自己対戦エピソード
  (両側 'Yser')で帰属が全壊**していた(§3.1「数える単位」と同型)。v2 でデッキ実体照合に修正。
  v1 の数字は本文書に一切使っていない。
- 赤チームDの指摘どおり **`action_vocabulary.py` は両視点合算で約2倍に膨れる欠陥**がある。
  本文書は同計器の絶対値(25.1枚/戦 等)を**一切使わない**。data.md の行動語彙からは
  distinct数と順位のみ参照する(それらは合算の影響を受けない)。本センサスは select を
  決定側 ACTIVE エントリでのみ数えるため、この欠陥の構造を持たない(上記不変量で確認)。

---

## 3. 未参照152項目の全内訳表

記法: ●n = 現行デッキ(cur)側での実測発生 n 件 / meta n = 相手側での実測 n 件 / 0 = 全576側で0。

### 3.1 A: デッキ由来 — 30項目(未参照の20%、全項目の12%)

| 項目 | 根拠(我々の60枚に機構0 + 実測) |
|---|---|
| SelectContext.ACTIVATE | 「When…you may」型の誘発が0枚。cur 0 / **meta 365**(Punk Up・Psychic Draw等) |
| SelectData.contextCard | ACTIVATE 時のみ送られる(api注釈)。同上 |
| SelectContext.ATTACH_FROM | エネ加速0枚。cur 0 / **meta 762**(Turbo Flare・Charging Up等) |
| SelectContext.ATTACH_TO | 同上。cur 0 / **meta 409** |
| SelectContext.DETACH_FROM | エネ剥がし0枚。0 |
| SelectContext.SWITCH_ENERGY_CARD | エネ移動0枚。cur 0 / meta 4 |
| SelectContext.SWITCH_ENERGY | 同上。cur 0 / meta 5 |
| SelectContext.TO_HAND_ENERGY | Wally's は「全部戻す」=選択なし。0 |
| SelectContext.TO_DECK_ENERGY | 該当機構0枚。0 |
| SelectContext.EVOLVE(型もA) | 効果進化(ふしぎなアメ系)0枚。cur 0 / **meta 65** |
| SelectType.EVOLVE | 同上(この型の選択は _fallback 行き) |
| SelectContext.DAMAGE_COUNTER_COUNT | ダメカン配分機構0枚。0 |
| SelectContext.REMOVE_DAMAGE_COUNTER_COUNT | 回復配分機構0枚。cur 0 / **meta 104**(Grimmsnarl系) |
| SelectData.remainDamageCounter | 配分系の残数。cur 0 |
| SelectContext.COIN_HEAD | コイン表裏を選ぶカード0枚(そもそもフリップするカードも0)。0 |
| SelectContext.MORE_DEVOLVE / SelectContext.DEVOLVE | 退化カード0枚(12デッキ中どこにも無し)。0(2項目) |
| SelectContext.AFFECT_SPECIAL_CONDITION / RECOVER_SPECIAL_CONDITION | 状態異常の付与/治療カード0枚。0(2項目) |
| SelectType.SPECIAL_CONDITION / OptionType.SPECIAL_CONDITION / Option.specialConditionType | 同上(3項目)。0 |
| SpecialConditionType.{POISON,BURN,SLEEP,PARALYZE,CONFUSE} | 同上(5項目)。このメンバが要るのは条件系の選択payloadのみで、自分の被状態異常は PlayerState 旗(B)で読める |
| OptionType.TOOL_CARD / Option.toolIndex | 道具「を選ぶ」機構0枚(Bomb は貼るだけ・剥がすのは相手の Tool Scrapper=相手の選択)。cur 0 / meta 4(2項目) |
| OptionType.ENERGY_CARD | エネカード単位の選択はコスト/効果由来のみ。cur 0 / meta 52。退却は ENERGY(単位)型で来ることを実測 |

### 3.2 B: 操縦者由来 — 67項目

**B-1: 現行デッキで実測発生しているのに読んでいない(操作的実害の候補)**

| 項目 | 実測と含意 |
|---|---|
| SelectType.ENERGY | **●159**(退却コストのエネ選択)。`_v1_decide` は _fallback(先頭k)で応答。**発見: `_COST_CONTEXTS` に DISCARD_ENERGY を入れてあるが、ENERGY型は `_choose_cards` に到達しない=死に地図** |
| SelectContext.DISCARD_ENERGY相当のpayload: OptionType.ENERGY / Option.energyIndex / Option.count / SelectData.remainEnergyCost | ●(オプション245件)。どのエネから捨てるかを価値づけできない(4項目) |
| SelectType.SKILL / OptionType.SKILL / Option.cardId | **●10選択/20オプション**。全て**相手の Froslass**(Freezing Shroud)起因=デッキ非依存で来る。cardId=0は状態異常処理(api注釈)(3項目) |
| SelectContext.SKILL_ORDER | 同上 ●10 |
| SelectContext.IS_FIRST | **●130**。常にYES(=常に先攻選択)を文脈も読まずに返す。**Carmine「If you go first, you may use this card during your first turn.」を3枚積んでいるのに、先攻後攻を読まない** |
| SelectContext.DRAW_COUNT | **●30**。引く枚数選択が現デッキで起こる(COUNT型は最大値方針で処理、文脈は未読) |
| SelectContext.TO_HAND | **●1,985**。サーチの主戦場。汎用 `_gain_value` で処理、文脈固有の戦略なし |
| SelectContext.TO_BENCH | **●185**(Poffin) |
| SelectContext.SETUP_BENCH_POKEMON | **●57**(毎試合級のベンチ初期配置) |
| SelectContext.EVOLVES_FROM / EVOLVES_TO | **●各1**。機構を特定: **相手の Grand Tree スタジアム**起因(effectフィールドで確認)=相手起因で現デッキでも来る(2項目) |
| State.stadium | **相手のスタジアムは現実に我々の試合にある**: cur側の MAIN に ABILITY オプション200件、**全てスタジアム由来**(Spikemuth Gym 195 / Surfing Beach 3 / Grand Tree 2)。どの盤面かも読まずに `main.py:335` が盲打ちする(Spikemuth Gym は「Marnie's ポケモンをサーチ」= **我々には無意味どころか、使えば山を1回シャッフルするだけ**) |
| OptionType.NO | ●130(YES/NO対)。常時YES方針の裏面。MULLIGAN/ACTIVATE等でNOが正解の局面はデッキ非依存 |

**B-2: 現デッキで値が動く/読めば効く状態・データ系**

| 項目 | 根拠 |
|---|---|
| PlayerState.{poisoned,burned,asleep,paralyzed,confused} | 相手起因で自分に付く(メタに Munkidori「Mind Bend: …is now Confused.」等)。眠り/麻痺中の入替判断・攻撃期待値に直結(5項目) |
| PlayerState.benchMax | 相手の Area Zero Underdepths は上限を8に変える。Poffin展開判断に効く |
| State.turnActionCount / State.firstPlayer / State.supporterPlayed / State.energyAttached / State.retreated | ターン内計画の基本旗(5項目)。firstPlayer は Carmine と直結 |
| CardData.retreatCost | **退却ロジック(5.5節)を持ちながら退却コストを読まない**。D62で読み変種(starmie-retreatcost)を作った経緯があり、操縦者側課題として確定済み |
| CardData.tera | **相手の Tera はベンチで被ダメ0**(api注釈)。我々は **Jetting Blow のベンチ狙撃を●654回**実測でやっている=**テラのベンチに50点を空撃ちしうる**、読めば直る具体的実害 |
| CardData.aceSpec | 自デッキに Deluxe Bomb(ACE SPEC)実在。自他のACE SPEC識別はデッキ非依存 |
| CardType.SPECIAL_ENERGY | 自デッキに Ignition×4 実在。**操縦者は `_IGNITION_ID=17` のハードコードで代替** — 読まずに済んでいるのはデッキが特エネ1種だから |
| EnergyType×12 | 同型: **単色デッキだから色を読まなくても正しい**(コスト充足を len() で数える色盲設計)。多色デッキに載せ替えた瞬間に誤る。相手の攻撃可否推定にも要る(12項目) |
| Attack.text | ワザ効果の解析。現状は `_SCALING_DAMAGE` / `_EFFECT_IGNORING_ATTACKS` のハードコード表で代替(=デッキ・ゲージ特化の症状) |
| Pokemon.appearThisTurn | 出したターンの進化不可等。合法手はエンジンが絞るが、次ターン計画に要る |
| SelectData.effect | この選択を起こしたカード。退却では null を実測、効果起因では因果の同定に使える |
| Observation.logs | 相手の隠れ行動の唯一の証跡(下記B-3の入口) |
| AreaType.STADIUM / AreaType.TOOL / AreaType.ENERGY | 場のスタジアム/付属道具/付属エネを指す領域定数。相手スタジアム・自分のBomb・退却エネ選択で現デッキでも流れる(3項目) |

**B-3: ログ系のうち、状態差分から復元できない情報(9項目)**

Log を読む価値はデッキ非依存(相手の隠れ行動)。復元不能な情報を運ぶもののみB、残りはC(§3.3)。

| 項目 | 復元不能な理由 |
|---|---|
| LogType.MOVE_CARD / MOVE_CARD_REVERSE / SHUFFLE | 相手の山→手札等、非公開領域の移動とサーチの証跡(3項目)。※DRAW/DRAW_REVERSE は手札・handCount 差分で復元可能なのでC側 |
| LogType.ATTACK / Log.attackId | 相手が**どの技を**使ったかはダメージからの逆算では曖昧(2項目) |
| LogType.COIN / Log.head | コイン結果は状態に現れない(2項目) |
| LogType.HAS_BASIC_POKEMON / Log.hasBasicPokemon | 相手のマリガン回数は状態から不可視(2項目) |
| Log.type / Log.playerIndex / Log.cardId / Log.fromArea / Log.toArea / Log.putDamageCounter | ログを読む最低限+移動の中身+「乗せ」か「打撃」かの区別(6項目) |

(B-3小計: LogType 6 + Log 9 = 15 … 集計は下の総括表で)

### 3.3 C: どのデッキでも冗長 — 45項目(導出元つき)

| 項目群 | 導出元 |
|---|---|
| SelectContext.MAIN / SelectContext.ATTACK | 参照済み SelectType.MAIN / SelectType.ATTACK と1:1(ATTACKは DISABLE_ATTACK との区別に使えるが、現ハンドラの最大打点選択は両読みで同型) |
| SelectContext.LOOK | 全576側で発生0。「Look at」を持つカードは我々含む多数(Pokégear/Dusk Ball/Bug Catching Set…)にあるのに一度も出ない=**エンジンは looking 状態(参照済み State.looking / AreaType.LOOKING)で表現**。死蔵疑い |
| OptionType.NUMBER / OptionType.CARD | 参照済み SelectType.COUNT+Option.number / SelectType.CARD 内で型は自明 |
| LogType 18項目(TURN_START, TURN_END, DRAW, DRAW_REVERSE, PLAY, ATTACH, EVOLVE, DEVOLVE, SWITCH, CHANGE, MOVE_ATTACHED, HP_CHANGE, POISONED, BURNED, ASLEEP, PARALYZED, CONFUSED, RESULT) | 主内容が参照済み状態(盤面・hp・旗・State.turn/result)の前後差分から復元可能。HP_CHANGE の「乗せ」区別だけは Log.putDamageCounter(B)側 |
| Log 15項目(serial系6, cardIdActive/Bench/Before/After/Target 5, value, isRecover, reason, serial) | 盤面差分・旗・終局状態から復元可能。serial系は「同名個体の追跡」にのみ固有価値(註記) |
| Card.serial / Pokemon.serial / Option.serial | 同上の serial 論(3項目) |
| Card.playerIndex | アクセス経路(players[i] 経由)で所有者は常に自明 |
| Skill.name / Attack.name | 意思決定は text / attackId で足りる。名前は表示用 |
| CardData.basic | 参照済み stage1/stage2 の否定から導出可能 |

### 3.4 判定不能 — 10項目

| 項目 | 理由 |
|---|---|
| SelectContext.TO_FIELD / NOT_MOVE / EFFECT_TARGET / FIRST_EFFECT / DISABLE_ATTACK | 全576側で発生0、発火カードを静的に特定できず(5項目) |
| SelectContext.MULLIGAN | cur 0 / meta 7。仕様(「引き直すか」が誰にいつ出るか)が実測から確定できない |
| OptionType.DISCARD | MAIN の「場のカードを捨てる」— 全576側で提示0、経路未特定 |
| AreaType.PRE_EVOLUTION / AreaType.PLAYER | オプション領域としての発火経路未特定(2項目) |
| State.stadiumPlayed | api注釈「a stadium has already been **used**」が「プレイ済み」か「効果使用済み」か二義的。前者なら自デッキ0枚で恒偽=A、後者なら相手スタジアム経由でB |

### 3.5 集計

| 判定 | 件数 | 内訳の要点 |
|---|---:|---|
| **A(デッキ由来)** | **30** | 全て選択系(SelectContext 16 / SelectType 2 / OptionType 3 / Option 2 / SelectData 2 / SpecialConditionType 5)。**相手側実測(meta 365/762/409/104/65…)が「デッキを替えれば現れる」ことの直接証拠** |
| **B(操縦者由来)** | **67** | うち実測発生あり19項目(●159/●130/●10…)。**うち13項目(EnergyType12+SPECIAL_ENERGY)は「デッキ形状に守られたB」**=読まない罰を現デッキが免除している |
| **C(冗長)** | **45** | ログの復元可能分33項目が主。設計上の余剰であり「読んでいない罪」ではない |
| **判定不能** | **10** | 全576側で発生0の死蔵疑いを含む |
| 計 | 152 | |

**読み方(主砲候補Bへの含意)**: 「語ることが少ない」をAだけで立てると30項目(20%)で、
**最大バケットB(44%)を無視した盛った主張になる**。正しい形は三段:
(1) デッキが構造的に発火させられない選択が30項目ぶん実在し(相手側では常時発生)、
(2) 操縦者が読んでいない67項目のうち13項目は**デッキが単純だから読まずに済んでいる**
(=デッキの貧しさが操縦者の貧しさを免罪している)、
(3) その帰結が §4 の表現力最下位。

### 3.6 副産物(分類中に確定した個別の発見)

1. **`main.py:335` の盲打ち特性コードは、自デッキでは一度も自分のカードで発火しない**
   (我々の15種に [Ability] 行は0)。cur側で提示された ABILITY 選択肢200件は**全て相手の
   スタジアム**(Spikemuth Gym 195 = 「Marnie's ポケモンをサーチ」……我々の山に1枚も無い)。
   デッキ入替スクリーニングで grimmsnarl が35%に沈んだ機構(D63)は、王者の実戦ログ側からも裏が取れた。
2. **死に地図**: `_COST_CONTEXTS` の `DISCARD_ENERGY` は到達不能(ENERGY型は `_choose_cards` に来ない)。
   実際の退却エネ選択159件は _fallback(先頭k)が答えていた。
3. **tera×ベンチ狙撃の潜在実害**: 我々は DAMAGE 選択を654回実測(最低HP優先)。相手の
   Tera(dragapult / Ogerpon等)はベンチで被ダメ0なのに、`CardData.tera` を読んでいない。
4. **マリガン率の設計負債**: 現デッキのたねは Staryu×4 のみ。7枚初手にたねが無い確率は
   C(56,7)/C(60,7) = **60.1%**(引き直しは自動でセンサスの選択には出ない)。
   これはAPI外だがデッキ表現力と同根の「60枚の設計」問題として記録する。

---

## 4. 表現力指標 DEX — 設計と12デッキのランキング

### 4.1 定義(静的・対戦ゼロ・action_vocabulary 非依存)

**DEX(deck) = N_api + N_vocab**

- **N_api** = 255項目のうち、**そのデッキが活性化できるAPI項目数**。
  機構ゲート(下表)ごとに「デッキがその機構を持つか」をカードDBの効果テキストで判定し、
  持てばそのゲートの項目数を加点。項目の重複割当なし。どんな合法デッキでも活性化する
  ベースライン項目(id/hp/hand/MAIN…)は全デッキ共通の定数なので加点対象から除外
  (順位に影響しない)。
- **N_vocab** = 静的行動語彙 = distinctカード名 + distinctワザ名 + distinct特性名。

**ゲート表(機構 → 活性化する項目、判定述語の要点)**

| ゲート(項目数) | 判定述語(効果テキスト) | 検証 |
|---|---|---|
| stadium(4) | Category=Stadium | — |
| tool(6) | Category=Pokémon Tool | — |
| special_energy(1) | Category=Special Energy | — |
| ability(4) | [Ability] 行あり | — |
| opt_trigger(2) | 「[Ww]hen …(110字内)… you may」誘発 | meta ACTIVATE 365と整合 |
| conditions(16) | Poisoned/Burned/Asleep/Paralyzed/Confused | — |
| coin(3) | flip a coin / flip N coins | — |
| dmg_counter(5) | move…damage counter / put…counters…(any way・as you like・1 of) | cur 0・meta 258+106と整合 |
| heal(3) | Heal / remove…damage counter | cur HEAL 161と整合 |
| energy_manip(7) | 動詞attach(状態語attachedを除外)/ switch・move Energy / Energy from your opponent | cur 0・meta 762+409と整合 |
| energy_discard_cost(2) | discard…Energy from this/your(非opponent) | — |
| fx_evolution(4) | 「to evolve it」(ふしぎなアメ/Ascension/Salvatore型) | cur 0・meta 65と整合 |
| bench_damage(1) | damage to N of…opponent/Benched(ワザ本文) | cur DAMAGE 654と整合 |
| bench_put(1) | put … onto your/their Bench | cur TO_BENCH 185と整合 |
| to_deck_select(2) | 数量つきの山戻し(全手札シャッフルは除外) | cur TO_DECK 0と整合 |
| ex/megaEx/tera/aceSpec(各1) | Rule欄+[Tera]行 | — |
| evolution(7) | Previous stage あり | — |
| multicolor(12) | ワザコストに2色以上 | — |

**開示①(v1→v2の監査修正)**: 初版ゲートは (a) Deluxe Bomb の固定対象配置を dmg_counter に、
(b) Hilda/Wally's の「attached/Energy…into hand」を energy_manip に、(c) Lillie's の
「サイド枚数**条件**」を prize 系に誤検知し、energy_manip は12/12全デッキ✓の無弁別だった。
**全ゲートを cur センサス実測(発生0/発生あり)と突合して修正**した(§7 のv1・v2両スクリプトを保存)。
**開示②(除外ゲート)**: look / prize / attack_fx / disable_attack / devolve / choose_one は
「全576側で発生0かつ静的述語を確証できない」ため**全デッキ一律で加点対象外**(死蔵扱い。
順位に影響しない)。
**開示③(粒度の限界)**: ゲートはテキスト述語なので、選択粒度の偽陽性が残りうる
(例: Recon Directive の「bottom of your deck」は選択を生まない)。cur デッキについてのみ
センサスで全ゲートを検証済み。他11本は述語ベース。

### 4.2 ランキング(N=12、2026-08-04計算)

| 順位 | デッキ | N_api | N_vocab | **DEX** | (種/ワザ/特性) |
|---:|---|---:|---:|---:|---|
| 1 | dragapult | 61 | 35 | **96** | 22/9/4 |
| 2 | grimmsnarl | 65 | 28 | **93** | 19/6/3 |
| 3 | tarountula | 48 | 34 | **82** | 23/8/3 |
| 4 | Kangaskhan | 39 | 41 | **80** | 24/11/6 |
| 5 | archaludon | 47 | 24 | **71** | 16/5/3 |
| 6 | garchomp | 39 | 29 | **68** | 20/7/2 |
| 7 | alakazam | 33 | 34 | **67** | 22/8/4 |
| 8 | starmie(実ラダー版) | 42 | 23 | **65** | 18/4/1 |
| 9 | crustle | 36 | 26 | **62** | 19/4/3 |
| 10 | lucario | 26 | 27 | **53** | 17/8/2 |
| 11 | dudunsparce | 25 | 27 | **52** | 17/8/2 |
| **12** | **starmie-aggro(我々)** | **22** | **18** | **40** | **15/3/0** |

- メタ11本: 中央値 **68**、最小 **52**。**我々はその最小をさらに12下回る唯一の外れ値**。
- **最も痛い1行**: 実ラダーの同型 starmie(Mega Starmie + Ignition 核は同じ)は **65**。
  差分は Cinderace(特性)+Crushing Hammer(コイン+相手エネ破壊)+Boss's Orders(呼び出し)+
  Salvatore(効果進化)等 — **同じ骨格でも「語れる」構成にできることの実在証明**。
- ゲート×デッキ行列と各ゲートのマッチ根拠(カード名+本文60字)はスクリプト出力に全掲。

---

## 5. 問い5への基礎回答 — 表現力と強さは同じか

手持ちの勝率(3ゲージ掃引・フィールド加重、main.py同一 md5 725ef4c9、各N=200×3、data.md 2026-08-03)
と DEX の突合。**n=4 なので相関の主張はしない**。事実判定のみ。

| デッキ | DEX(順位/12) | フィールド加重勝率 |
|---|---:|---:|
| grimmsnarl | 93(2位) | **30.8%(最下位)** |
| tarountula | 82(3位) | 68.8%(2位) |
| crustle | 62(9位) | **71.5%(最大)** |
| starmie-aggro(我々) | 40(12位) | 48.7%(3位) |

(garchomp は対Alakazamのみ51.5%・N=200で、加重比較から除外)

**事実判定: 「表現力最大のデッキ」と「勝率最大のデッキ」は別物。**
測った範囲で表現力最上位(grimmsnarl)が勝率最下位、勝率最大(crustle)は表現力下位1/3。

**両立可能性の議論(機構つき)**:
- DEX を「能動成分」(選択を要求するゲート: opt_trigger+dmg_counter+energy_manip+
  fx_evolution+to_deck_select+energy_discard_cost+multicolor)に絞ると:
  **grimmsnarl 30 / tarountula 24 / crustle 4 / 我々 0**。
  勝率上位2本(crustle・tarountula)の**動力源は常在**(Mysterious Rock Inn/Repelling Veil)で、
  能動機構は補助(tarountula の Charging Up は「使えれば得」)。grimmsnarl は**動力源そのものが
  能動**(Adrena-Brain の移動元・先・個数、Punk Up の配分)で、`main.py:335` の盲打ちが直撃する。
  → **D63 の機構仮説(常在=満額/能動=劣化)が、指標の内部構造としても再現された。**
- したがって「強いデッキに変える」と「語れる要素が多いデッキを選ぶ」は**同じ操作ではない**。
  ただし**矛盾もしない**: tarountula(DEX 82・勝率68.8%)が両立解として実在する。
  条件は「**常在動力 + 高DEX**」— 表現力は語りの資産、能動要求は(現操縦者の下では)操縦の負債。
- 含意: デッキ選定は「DEX最大化」でも「勝率最大化」でもなく、
  **DEX高 × 能動成分が動力源でない × フィールド相性**の同時解を探すこと。
  能動成分を資産に変える唯一の道は操縦者側の改修(= B67項目の解消、例: `deckswap-grimmsnarl-abilityfix` 系)。

---

## 6. deckcrafting への具体材料 — 移行先ごとに「語れるようになるトピック」3件

運営の名指し(handover §0: gameplay / **deckcrafting** / strategic decisions)に対し、
各デッキで**記事に書ける具体トピック**をカードDBの本文引用つきで3件ずつ。
(引用は EN_Card_Data.csv 原文。長文は省略記号)

**dragapult(DEX 96)**
1. ダメカン幾何学: Phantom Dive「Put 6 damage counters on your opponent's Benched Pokémon in any way you like.」— 6個の配分最適化はAPIの DAMAGE_COUNTER_ANY/remainDamageCounter をフル活用する題材。
2. テラのベンチ無敵: Dragapult ex[Tera]「As long as this Pokémon is on your Bench, prevent all damage done to this Pokémon by attacks」— ベンチ配置自体が防御になる。
3. コイン妨害とリセット: Crushing Hammer「Flip a coin. If heads, discard an Energy from 1 of your opponent's Pokémon.」+ Unfair Stamp(被KOターン後の手札リセット)。

**grimmsnarl(DEX 93)**
1. ダメカン移動の資源管理: Adrena-Brain「…move up to 3 damage counters from 1 of your Pokémon to 1 of your opponent's Pokémon.」— 回復と打点を同時に動かす、能動表現力の極点。
2. 一括加速の配分: Punk Up「…search your deck for up to 5 Basic {D} Energy cards and attach them…」— 5枚をどこに撒くかが ATTACH_TO 選択の教科書。
3. 特性メタの自傷設計: Freezing Shroud「During Pokémon Checkup, put 1 damage counter on each Pokémon that has an Ability (both yours and your opponent's)」— 自分の特性持ちにも刺さる採用判断。

**tarountula(DEX 82)**
1. 常在ロック: Repelling Veil「Prevent all effects of attacks … done to your Basic Team Rocket's Pokémon. (… Damage is not an effect.)」— Alakazam 94.5% の機構そのもの。
2. 攻撃権の条件化: Power Saver「This Pokémon can't attack unless you have 4 or more Team Rocket's Pokémon in play.」— 盤面数が攻撃許可になる設計。
3. 名前シナジーのエンジン: Transceiver「Search your deck for a Supporter card that has "Team Rocket" in its name」+ Factory(TRサポート使用ターンに2ドロー)— 「名前」参照のデッキ構築論。

**Kangaskhan(DEX 80)**
1. たねのみ×メガ: Mega Kangaskhan ex は Basic の Mega(進化ゲートなしでサイド3枚)+ Run Errand(場で毎ターン2ドロー)。
2. ベンチ上限の改変: Area Zero Underdepths「Each player who has any Tera Pokémon in play can have up to 8 Pokémon on their Bench.」— benchMax が動く唯一級の実例。
3. コイン打点の分散: Rapid-Fire Combo「Flip a coin until you get tails. This attack does 50 more damage for each heads.」

**archaludon(DEX 71)**
1. 進化誘発の加速: Assemble Alloy「When you play this Pokémon from your hand to evolve … attach up to 2 Basic {M} Energy cards from your discard pile … in any way you like.」
2. 全体軽減スタジアム: Full Metal Lab「{M} Pokémon … take 30 less damage from attacks」— 盤面全体のダメージ計算が変わる。
3. 条件つき回復: Jumbo Ice Cream「Heal 80 damage from your Active Pokémon that has 3 or more Energy attached.」

**garchomp(DEX 68)**
1. 常在バフ: Cheer On to Glory「Attacks used by your Cynthia's Pokémon do 30 more damage…」— 名前シナジーの常在打点。
2. 効果無効の特エネ: Rock Fighting Energy「…Prevent all effects of attacks … done to the {F} Pokémon this card is attached to.」— エネ自体が防御表現。
3. ベンチ依存の逆転打: Raging Curse「This attack does 10 damage for each damage counter on all of your Benched Cynthia's Pokémon.」

**alakazam(DEX 67)**
1. 進化=ドローの誘発連鎖: Psychic Draw(Kadabra/Alakazam)「…when you play this Pokémon from your hand to evolve … Draw 2/3 cards.」— ACTIVATE 365件(メタ側実測)の主要源。
2. 手札スケール打点: Powerful Hand「Place 2 damage counters on your opponent's Active Pokémon for each card in your hand.」— 打点が「手札枚数」という別リソースに乗る。
3. 貼るだけ展開の特エネ: Telepath Psychic Energy「When you attach this card … search your deck for up to 2 Basic {P} Pokémon and put them onto your Bench.」

**starmie 実ラダー版(DEX 65)— 我々の骨格のまま +25**
1. 同骨格比較そのもの: 我々と同じ Mega Starmie + Ignition に、Cinderace「Turbo Flare: Search your deck for up to 3 Basic Energy cards and attach them to your Benched Pokémon in any way you like.」を足すと加速と配分の語りが生まれる。
2. 呼び出し: Boss's Orders「Switch in 1 of your opponent's Benched Pokémon to the Active Spot.」— 我々に1枚も無い「相手盤面への干渉」の最小実装。
3. 効果進化: Salvatore「Search your deck for a card that has no Abilities and evolves from 1 of your Pokémon, and put it onto that Pokémon to evolve it.」— EVOLVE 型選択(我々は _fallback 行き)を自分の武器にする。

**crustle(DEX 62)**
1. 常在壁: Mysterious Rock Inn「Prevent all damage done to this Pokémon by attacks from your opponent's Pokémon {ex}.」— 勝率首位の動力源が「選択ゼロ」であることが問い5の核。
2. 特エネ三種盛り: Mist(効果無効)/ Spiky(触れたら2個)/ Grow Grass(+20HP)— エネ枠が全部テキストを持つ。
3. 手札破壊: Xerosic's Machinations「Your opponent discards cards from their hand until they have 3 cards in their hand.」

**lucario(DEX 53)**
1. 進化誘発の呼び出し: Heave-Ho Catcher「…when you play this Pokémon from your hand to evolve … Switch in 1 of your opponent's Benched Pokémon to the Active Spot.」— ポケモンでBoss'sを内蔵。
2. 二体シナジーのドロー: Lunar Cycle「…if you have Solrock in play, you may discard a Basic {F} Energy card from your hand … Draw 3 cards.」
3. HP環境操作: Gravity Mountain「Each Stage 2 Pokémon in play (both yours and your opponent's) gets -30 HP.」— 相手依存で効く両刃スタジアム。

**dudunsparce(DEX 52)**
1. 自己バウンスのドロー機関: Run Away Draw「…draw 3 cards. If you drew any cards in this way, shuffle this Pokémon and all attached cards into your deck.」— 盤面を溶かしてでも引く設計。
2. 退却コスト操作: Air Balloon「The Retreat Cost of the Pokémon this card is attached to is {C}{C} less.」— retreatCost(B項目)を自分の武器にする。
3. 初ターン特化サーチ: Fan Call「Once during your first turn, you may search … up to 3 {C} Pokémon with 100 HP or less」— 先攻後攻(IS_FIRST/firstPlayer)を読む動機がデッキ側に生まれる。

---

## 7. 再現コマンド

```bash
# 1) 前任者の枠の検算(diff 完全一致を確認)
cd src/input/datasets/decks/starmie-aggro
python3 ../../../../../verification/api_surface_audit.py | diff - ../../../../../docs/memo/api-surface-2026-08-02.txt

# 2) 厳密再判定(Enum修飾参照 + フィールド全出現行の証跡ダンプ)
nice -n 19 python3 <scratch>/recount.py          # 21クラス255項目 / 厳密103参照・152未参照

# 3) 実リプレイ選択センサス v2(side=デッキ実体同定、対戦ゼロ)
nice -n 19 python3 <scratch>/ctx_census2.py      # cur 239側 / meta 299側 / 全(型,文脈)頻度と不発生一覧

# 4) 表現力指標 DEX v2(12デッキ)
nice -n 19 python3 <scratch>/dex_metric2.py      # ランキング表とゲート×デッキ行列
```

`<scratch>` = 本セッションの scratchpad
(`/private/tmp/claude-501/-Users-yujiinoue-Documents-products-pokemonabc/3b6371be-60d8-47f7-912b-caf9b28d8112/scratchpad/`)。
リポジトリへ移す場合は `verification/` 配下に `api_surface_semantic.py` / `ctx_census.py` /
`deck_expressiveness.py` として収載するのが自然(未実施 — 承認事項ではないが、ファイル追加は
親エージェントの判断に委ねる)。

## 8. 本解析の限界(必ず併記)

- センサスの「発生0」は **N=235試合(cur側10,604選択)での上界**であり非存在の証明ではない。
  A判定は「機構0枚(全文精査)+実測0+相手起因経路なし」の三重根拠だが、判定不能10件を残した。
- DEX のゲートは効果テキスト述語で、選択粒度の偽陽性が残りうる(curのみセンサス検証済み)。
- N_api と N_vocab の合算は単位の異なる計数の和(いずれも「distinct な表現要素の数」)。
  成分は常に併記した。合算の重み依存を排した頑健な事実は: **我々は N_api 単独(22 < メタ最小25)でも
  N_vocab 単独(18 < メタ最小23)でも最下位**。上位の順序は成分の重みで入れ替わる(例: N_api 単独なら
  grimmsnarl 65 > dragapult 61)ため、1〜4位の序列は解釈に使わないこと。
- 勝率との突合は n=4。相関係数は計算しない(主張しない)。
- 行動語彙計器(action_vocabulary.py)の既知欠陥(両視点合算で約2倍)により、同計器の
  絶対値は本文書で不使用。distinct数・順位のみ参照。

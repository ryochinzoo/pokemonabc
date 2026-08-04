# 人間メタ × AIメタ 突き合わせ — 主砲D「人間が選ぶデッキと、AIが選ぶデッキは別のゲーム」の実体化

- 担当: 解析C-cross(Fable 5)/ 実施 2026-08-03〜04
- 対戦を伴う測定: **ゼロ**(規律4遵守)。全数値は手元データ+カードDB+WebFetch 3回のみ。
- 数値の正典: この文書内の AI 側数値は `band_meta_census.py` / `field_ev.py` /
  `ladder_scout/decks.jsonl` から本日再計算した一次出力(§11 に再現コマンド)。

---

## 0. 結論(先出し)

**主砲Dは成立する。ただし正確な形は「別のカードプールで別のゲームをしている」ではなく、
「同一プール・ほぼ同一のトレーナー骨格の上で、"何をデッキの主役にするか" だけが分岐した」である。**
この精密化は攻撃への耐性を上げる(§6 の収束データを自分から先に出すため)。

1. **カードプール整合は検証で確定**(§2)。人間側16本は全960スロットが競技DBに解決し、
   エンジン規則で16/16合法。Mega Evolution(MEG)のカードを122枚使っている。
2. **AI最大勢力 Alakazam は人間側に0本**(§4-④)。潰すつもりで名前3種+SUMI署名ID+960スロット
   全数+外部の実大会結果サンプルまで当てたが、1枚も出なかった。前任者の見立ては生存。
3. **AI上位6勢力(シェア≥3.2%)のうち、人間 top-cut 16 と共有されるのは grimmsnarl と lucario の2つだけ**。
   crustle壁 / alakazam / archaludon / tarountula は人間16に不在(tarountula のみ外部サンプルに1勝例 → §4-③で降格処理)。
4. **人間16本のうち AI 確立勢力(distinct 52体以上)は6本、AIメジャー(シェア≥10%)は2本**。
   引き継ぎ文書の「3〜4本のみ」は **6本に訂正**(閾値の取り方で2〜6本。§4-③)。
5. **反直感の収束**: トレーナー骨格は両世界でほぼ同じ(Night Stretcher 人間16/16 vs AI 81%、
   Boss's Orders 15/16 vs 92%)。共有アーキタイプは60枚中52枚まで一致する。**分岐はポケモン層に局在**。
6. **AIメタの実体は「コピーメタ」**: 800-1099帯の distinct 2,560体のうち、
   **912体(35.6%)がわずか2種類の完全同一60枚リスト**(alakazam 407体 / grimmsnarl 505体)を提出している。
   人間の大会でリストがバイト単位で一致する率とは比較にならない(§7)。
7. **逆向きの問い(任務4)**: 人間側にあってAIに無いデッキの中で、我々の操縦者
   (常在=満額 / 能動=劣化、data.md 4110-4174)に合う候補は
   **#1 Honchkrow(TRバレット)**: 人間16本中唯一の**能動特性0**デッキ。動力源は我々の実測最良デッキ
   (tarountula 94.5%)と同一カードの常在 Repelling Veil。**#2 Slowking/Latias**(能動3・受動4、外部で実勝利例)。
   いずれも**探索的・未測定**(§9)。

---

## 1. 何を1と数えたか(全表共通の単位宣言)

**この節を飛ばした読みは全部誤読になる**(引き継ぎ §3.1: 同型の誤りを前任者は1日4回踏んだ)。

| 側 | 「1」の単位 | N | 出所 |
|---|---|---|---|
| 人間 | **デッキリスト1本**(=1アーキタイプの代表構築1本。大会シェアでは**ない**) | **16本**(960スロット) | yu0307 データセット(§2) |
| 人間(外部) | **優勝行1行**(City League 1大会の優勝アーキタイプ名) | **約26行**(49頁中1頁のみ。**全数走査は未達**) | limitlesstcg.com/tournaments/jp(§10) |
| AI(遭遇) | **側1つ**(1エピソードに2側。同一エージェントが試合数だけ重複して乗る) | **6,341側** | 我々の census、800-1099帯、自チーム18提出は除外 |
| AI(実体) | **distinct 提出1体**(submissionId で重複排除) | **2,560体** | 同上 |

- 人間16本は「シェア0%」を意味しない: yu0307 は**アーキタイプごとに代表1本**を収載した編集物であり、
  頻度情報を持たない。人間側の頻度主張には limitless サンプルだけを使い、検定力を明記する(§4-④)。
- AI側は必ず**両単位を併記**する。側単位と distinct 単位で順位が入れ替わる勢力が実在する
  (lucario: 側13.2%だが**96体**しかいない — garchomp の100体より少ない)。
- 落とした標本: AI側で分類不能(両分類器Noneかつ主役判定も不能)の111側は「other」に含めて開示。
  distinct 1体(sub 54856636)が試合によって alakazam / crustle の両方に分類された(全2,560体中1体、
  デッキ抽出の揺れ)。crustle の distinct は 253〜254 と表記が揺れるのはこのため。

---

## 2. 第一関門: カードプール整合の検証(規律5)

**判定: 通過(カード単位で完全整合)。ただし「同一大会期間」は著者申告どまり — 射程を下に明記。**

検証した事実(全て本日実測、§11 コマンド1):

| 検査 | 結果 |
|---|---|
| 16本×60枚=960スロットのカードIDが競技DB(EN/JP_Card_Data.csv、distinct 1,267 ID)に解決するか | **960/960 解決** |
| エンジン規則(60枚・同名≤4・ACE SPEC≤1・たね≥1)で合法か | **16/16 合法**(conformance と同じ規則で静的検査) |
| Mega Evolution 環境のカードを実際に使っているか | **MEG 122枚**を9本以上が使用(Mega Lucario/Starmie/Venusaur/Sharpedo/Kangaskhan/Lopunny ex 等) |
| AI固有勢力のコアカードが人間側からも「選べた」か | AIコアの出典セット **MEG/TWM/TEF/DRI/ASC の5セット全てのカードが人間16本の中にも登場**(例: 人間側は TEF 50枚・DRI 100枚を使用)→「人間はそのセットに触れていなかった」という逃げ道は塞がった |

射程の限定(ここを曖昧にしない):

- yu0307 の申告は「**この競技のカードプールとおおむね同じスタンダード期間**の City League 1位/2位」。
  **大会名・日付・順位のメタデータは付いていない**(著者自身が明記)。
- 外部照合: limitlesstcg の JP City League 実結果(**2026年5月2〜26日**、シーズン最終月)に
  Lucario-Mega / Starmie-Mega / Ogerpon+Arboliva / Slowking+Latias / Garchomp+Roserade /
  Dragapult 各種 — **yu0307 の16本と同じ語彙**が並ぶ。Mega 級が優勝している以上、
  この窓は Mega 環境であり、競技プールと同世代。**個々の16本がどの大会かは特定不能のまま**。
- よって本文書の主張は全て「**この競技のプールで合法かつ同世代の、人間の実大会上位構築16本**」を
  人間側代表とする、という形に限定する。

---

## 3. アーキタイプ写像規則(対応表)

写像は**アーキタイプの動力源カード**(分類器がキーにする実カード名)で取る。曖昧なものは対応不能と明記。
検証として、**16本の人間デッキを我々のAI分類器2系統に実際に通した**(A=カード名規則 / B=SUMI公開ID)。

| 人間側ファイル名 | 日本語名(yu0307) | 中身の主役(実物で確認) | AI分類器A | AI分類器B | 写像判定 |
|---|---|---|---|---|---|
| Grafaiai | オーロンゲ | **Marnie's Grimmsnarl ex** ×2 + Munkidori ×4 | grimmsnarl | grimmsnarl | **↔ AI grimmsnarl**(注1) |
| MegaLucario | メガルカリオ | Mega Lucario ex ×3 | lucario | lucario | **↔ AI lucario** |
| Dragapult | ドラパルト | Dragapult ex ×3 + Dusknoir線 | dragapult | dragapult | **↔ AI dragapult** |
| DragapultBlaziken | ドラパバシャーモ | Dragapult ex ×2 + Blaziken ex ×2 | dragapult | dragapult | **↔ AI dragapult**(混成) |
| MegaStarmie | メガスターミー | Mega Starmie ex ×3 + Dusknoir線 | starmie | starmie | **↔ AI starmie**(注2) |
| Garchomp | ガブリアス | Cynthia's Garchomp ex ×3 | garchomp | garchomp | **↔ AI garchomp** |
| ClefairyOgerpon | ピッピオーガポン | Lillie's Clefairy ex ×3 + Ogerpon ×3 | Kangaskhan(**誤分類**) | None | **対応不能**(注3) |
| RagingBolt | タケルライコ | Raging Bolt ex ×3 + Ogerpon ×4 | Kangaskhan(**誤分類**) | None | 対応不能 |
| TerastalBox | 宝石バレッド | Noctowl ×3 + テラス群 | Kangaskhan(**誤分類**) | None | 対応不能 |
| Arboliva | オリーヴァ | Arboliva ex ×2 + Ogerpon ×4 | None | None | 対応不能 |
| FestivalLead | おまつり | Dipplin ×4 + Thwackey ×4 | None | None | 対応不能(注4) |
| Honchkrow | ドンカラス | TR Honchkrow ×3 + TR Articuno ×2 | None | None | 対応不能(注5) |
| MegaSharpedo | メガサメハダー | Mega Sharpedo ex ×3 | None | None | 対応不能(痕跡: Carvanha 5側/5体) |
| MegaVenusaur | メガフシギバナ | Mega Venusaur ex ×2 | None | None | 対応不能 |
| Slowking | ヤドキング | Slowking ×3 + Latias ex ×2 | None | None | 対応不能 |
| Zoroark | ゾロアーク | N's Zoroark ex ×4 | None | None | 対応不能(痕跡: 11側/9体) |

- 注1: ファイル名 Grafaiai(タギングル)は**誤解を招く**が、実物にタギングルは0枚。JP名対応表の
  「オーロンゲ」が正しい。中身で判定した。
- 注2: AI側 starmie(52体)のモーダル構築は Cinderace ×4 / Crushing Hammer ×4 入りで、人間 MegaStarmie
  との一致は 31/60 に落ちる(共有型の中で最遠)。
- 注3: 分類器Aの「Kangaskhan」規則は Mega Kangaskhan ex 1枚で発火する。人間側はこのカードを
  **汎用ドロー(Run Errand)の1〜2枚挿し**として使うため誤発火する。AIメタ専用に作った分類器は
  人間メタでは壊れる — **分類器の語彙自体がメタの形を映す**という副次的発見。
- 注4: FestivalLead は分類不能だが、AI側 800-1099 の「other」の中に **Dipplin+Grookey 線を全部含む
  55側/最大28体**が実在する(§4-③の痕跡層)。myso1987(第三者)の分類器には "Festival Lead" 規則がある。
- 注5: Honchkrow(TRバレット)は AI側 tarountula(TRバレットの別主役)と**部分重なり**:
  同じ常在シールド TR Articuno ×2 を積むが、主役が違う(人間=Honchkrow、AI=Spidops/Mimikyu/Mewtwo)。
  アーキタイプとしては別物と判定。

**第三者分類器との整合**: myso1987(スコア帯別メタの公開ノートブック)の規則25本は、AI側実勢
(Great Tusk/Crustle, Crustle Wall, Alakazam, Mega Kangaskhan…)と人間型(Festival Lead, N's Zoroark,
Mega Sharpedo…)の**両方の語彙を必要としている**。AIラダーを記述するには人間メタに無い語彙が要る —
これ自体が主砲Dの独立傍証。

---

## 4. 突き合わせ本体

### ① 人間 top-cut 16 の構成(単位=デッキ本数、頻度情報なし)

16本 = §3 の表の通り。内訳: Mega系 4本 / Dragapult系 2本 / ex主役 12本 / 非ex主役 4本
(FestivalLead, Honchkrow, Slowking, TerastalBox※Noctowl核)。16/16 が固有の60枚(同一リストなし)。

### ② AI 800-1099帯の構成(両単位併記。我々自身の18提出は除外)

| アーキタイプ | 側(6,341) | 側シェア | **distinct 提出(2,560)** | distinctシェア | 人間16に主役カードが |
|---|---|---|---|---|---|
| alakazam | 1,853 | 29.2% | **773** | 30.2% | **0本** |
| grimmsnarl | 1,225 | 19.3% | **723** | 28.2% | 1本(Grafaiai) |
| crustle | 855 | 13.5% | **254** | 9.9% | **0本**(Crustle/Dwebble 0枚) |
| lucario | 834 | 13.2% | **96** | 3.8% | 1本(MegaLucario) |
| archaludon | 678 | 10.7% | **231** | 9.0% | **0本**(Archaludon/Duraludon 0枚) |
| tarountula | 205 | 3.2% | **101** | 3.9% | 0本(ただし TR Articuno は Honchkrow に2枚) |
| other | 184 | 2.9% | 94 | 3.7% | (§③の痕跡層) |
| starmie | 132 | 2.1% | 52 | 2.0% | 1本(MegaStarmie) |
| dragapult | 132 | 2.1% | 88 | 3.4% | 2本 |
| garchomp | 122 | 1.9% | 100 | 3.9% | 1本 |
| dudunsparce | 86 | 1.4% | 24 | 0.9% | **0本**(Dunsparce線 0枚) |
| bellibolt / Kangaskhan / trevenant / gardevoir | 14/11/5/5 | 各≤0.2% | 4/11/5/5 | — | 0本(Mega Kangaskhan ex のみ3本が1〜2枚挿し) |

- **単位で順位が動く実例**: lucario は側で4位(13.2%)だが distinct では **7位(96体)**。
  少数の常連が大量に対戦している。crustle も側13.5%に対し distinct 9.9%。
  逆に grimmsnarl は distinct で 28.2% に**上がり**、alakazam とほぼ並ぶ。
- **打ち切りゼロの表であることの宣言**: この表は `band_meta_census.py` の**表示ロジックを経由していない**
  (同スクリプトには表示上の静かな打ち切りが4種残存 — 赤チームD指摘、§10-10)。
  `collect()` で得た 800-1099 の全側を閾値なしで全数集計し、n=5側の勢力まで全行表示している。

### ③ 3リスト(両方に居る / 人間のみ / AIのみ)

**(a) 両方に居る — 6本/16、AI側5アーキタイプ**(AI distinct 52〜723体):
grimmsnarl(723体)・lucario(96体)・dragapult(88体、人間2本)・garchomp(100体)・starmie(52体)。
**AIメジャー(シェア≥10%)との共有はこのうち grimmsnarl / lucario の2つだけ。**
引き継ぎ文書の「人間16本のうちAIに定着は3〜4本」は、distinct≥52体を「定着」と読むなら **6本に訂正**、
シェア≥10%と読むなら **2本**。以後この2閾値を併記する。

**(b) 人間のみ(AI側は痕跡以下)** — 10本。AI側の痕跡量(800-1099帯)を正直に併記:

| 人間デッキ | AI側の痕跡(側 / distinct) | 判定 |
|---|---|---|
| FestivalLead | 55側 / ≤28体(otherの中、全側が Dipplin+Grookey線持ち) | 痕跡あり(≈1.1%) |
| Zoroark | 11側 / 9体 | 痕跡あり |
| MegaSharpedo | 5側 / 5体(Carvanha主役) | 痕跡あり |
| RagingBolt | 3側 / 2体 | 痕跡あり |
| Honchkrow | 8側 / 6体(TR Murkrow主役。ただし Honchkrow 核かは未確認) | 痕跡あり |
| ClefairyOgerpon / TerastalBox | Ogerpon主役 10側/9体 が該当しうる(判別不能) | 曖昧 |
| Slowking | **0**(Slowking というカード自体は AI側に出現あり※種類数え。主役例なし) | 実質不在 |
| Arboliva | **0側**(Arboliva ex/Smoliv/Dolliv は**カードとして2,560体に1枚も無い**) | **完全不在** |
| MegaVenusaur | **0側**(Bulbasaur/Ivysaur/Mega Venusaur ex 同上) | **完全不在** |

カード次元の完全不在リスト(人間が使い、AI 2,560体の誰も1枚も入れていない15種):
Arboliva ex, Smoliv, Dolliv, Bulbasaur, Ivysaur, Mega Venusaur ex, Hoothoot, **Noctowl**(人間メタ屈指の
サーチエンジン), Iron Leaves ex, Raging Bolt(非ex), Haxorus, Zeraora, Binding Mochi, Lillie's Pearl,
Sparkling Crystal。**15/182種(8%)** — 人間の道具箱の大半(92%)はAIラダーのどこかに存在する。

**(c) AIのみ(人間16に主役ゼロ)** — AI distinct 順:

| AI勢力 | AI規模(側 / distinct) | 人間側の存在 |
|---|---|---|
| **alakazam**(Abra/Kadabra/Alakazam+Dunsparce線、非ex) | 1,853 / **773** | **0**(§④) |
| **crustle壁**(Dwebble/Crustle+Mega Kangaskhan) | 855 / **254** | 0(コアカード0枚。limitless 26行にも無し) |
| **archaludon** | 678 / **231** | 0(同上) |
| dudunsparce 単 | 86 / 24 | 0(Dunsparce線は人間16に0枚。ただし limitless に「Dragapult/Dudunsparce」優勝が複数 → **カードとしては人間も使う**。単主役型のみAI固有) |
| Cubchoo ハンマーロック(Crushing/Enhanced Hammer×4+TR Petrel。ポケモンは Cubchoo 4枚のみ) | 42 / **9** | 0(limitless サンプルにも無し) |
| ライブラリアウト(crustle亜種: Great Tusk+Terrakion) | (crustle 254体の内数) | 0(Great Tusk は人間16に0枚) |
| **tarountula(TRバレット)** | 205 / 101 | **⚠ 降格: 人間 City League 実結果に「Spidops/Mewtwo」優勝1行を発見**(limitless、北海道)。「AIのみ」ではなく「人間側で希少(サンプル26行中1行)、AI側で確立(3.2%/101体)」に修正 |

### ④ 「AI最大勢力 Alakazam は人間側に何本か」の確定

**0本。** 潰しにいった手続きを含めて記録する:

1. カード名 3種(Alakazam / Abra / Kadabra を含む名前)で 960スロット全数照合 → **0枚**
2. SUMI 署名ID(743, 245)で直接照合 → **0枚**
3. AI側の実体確認: モーダル構築は Abra×4/Kadabra×4/Alakazam×4/Dunsparce×3/Dudunsparce×2 —
   **非ex・1賞・2進化のドロー機関デッキ**(Psychic Draw で展開し、手札枚数×2個のダメカンを置く
   Powerful Hand で殴る)。Alakazam(id 743)は **MEG 収録 = 競技プール最新世代**であり、
   人間側もこのカードを「選べた」(§2 の入手可能性検査)。
4. 外部の実大会結果(limitless、2026年5月の優勝行 約26行サンプル)→ **Alakazam 0行**。
   検定力: 仮に Alakazam が人間優勝の10%を占めるなら26行で0の確率は 0.9^26 ≈ **6%**。
   よって「人間側の主要アーキタイプではない」は約94%水準で言える。
   **「痕跡すら無い」は言えない**(全49頁を走査していない。§10)。

**結論: 「AIラダーの30%(distinct 773体)を占める王者デッキは、人間の同格メタで主要勢力ではなく、
検証した範囲では1本も観測されない。」** — 前任者の見立ては、殺しにいった上で生存した。

### ⑤ AIのみ勢力が人間側に無い理由(**仮説。以下は未検証**)

| 仮説 | 中身 | 支持する断片 | 反証されうる点 |
|---|---|---|---|
| H1 時計の非対称 | 人間の City League は BO1+25分制限。壁/ロック/LO はターン数を極大化する戦略で、**人間は両負け・時間切れリスクを払う**。エンジンにはこの費用が無い(打ち切りはstep上限のみ) | crustle の行動語彙: 自ターン18.1回/戦=最長(data.md 2026-08-03)。LO設計者 soutasakurai 本人が「**Great Tusk does not really attack**」と明記 | 人間の対戦時間の一次データを持っていない。JP大会規定の確認も未実施 |
| H2 相手方策の脆さを狩る種 | Crustle「Mysterious Rock Inn」は**ex からのダメージだけ**を常在で無効化。ex 主砲一本のボットは対処選択肢を持たず詰む。**カードが強いのではなく、相手集団(ボット)の方策が脆い**からニッチが開いた | AIメタの主砲は ex 集中(grimmsnarl/lucario/archaludon…)。人間16本は非ex攻撃線を4本が持ち、テック挿しも自在 | 我々自身の crustle 対面成績(64%で勝てている)と整合するが、上位帯ボットの「詰み方」のログ実証は未実施 |
| H3 模倣可能性による播種(主砲Aと接続) | AIメタの上位は「強いデッキ」ではなく「**公開された教師データ・スケルトンが多いデッキ**」。Alakazam は公開ノートブックの定番ベースライン。人間メタにはこの選択圧が無い | _inbox に「why-alakazam-is-a-good-baseline-for-ai」(heiseimikiko)が実在。未取得22件に「ptcg-1070-9-**alakazam-rule-based-skeleton**」。8位 Jake 証言(Marnie's はデータが多いから作りやすい)。**§7 の集中度(帯の36%が2リストの完全コピー)** | コピー元ノートブックと帯のモーダルリストの60枚一致照合は未実施(斥候Bの `agent()` 実行審査と接続すべき) |
| H4 賞トレード経済の読み違い耐性 | Alakazam型(1賞×2進化)は、ボット相手だと「進化前を狩られ切る前に成立する」。人間相手では Boss's 等で進化線を的確に折られる。人間が選ばないのは**人間の対面では成立しないから** | 人間16本の15本が Boss's Orders 採用(=進化線折りの標準装備) | 完全に推論。AI上位帯でも Boss's 採用は92%あり、「使えるのに折れていない」の説明が要る(操縦の質の差、という補助仮説が必要) |

---

## 5. (欠番 — §4-⑤に統合)

## 6. 反直感の収束面 — 「同じゲーム」の部分を自分から出す

主砲Dを記事にする時、審査員(ポケモン社3名)は必ず「本当に別のゲームか?」と突いてくる。
**先にこちらから収束データを出す**:

### トレーナー骨格は両世界でほぼ同一

| カード | 人間(16本中) | AI(distinct 2,560体中) |
|---|---|---|
| Boss's Orders | 15 | 92% |
| Night Stretcher | **16(全デッキ)** | 81% |
| Poké Pad | 14 | 90% |
| Lillie's Determination | 14 | 71% |
| Buddy-Buddy Poffin | 8 | 83% |

### だが第2層で分岐する

| カード | 人間 | AI | 読み |
|---|---|---|---|
| Ultra Ball | **13/16** | 21% | 人間の標準サーチをAIは捨てている |
| Rare Candy | 3/16 | **61%** | AIは2進化(Alakazam/Dusknoir)偏重 |
| Dawn / Xerosic's / Hilda / Pokégear | 各1〜3/16 | 45〜60% | AI側の定型(公開スケルトン由来?) |
| Dunsparce+Dudunsparce | **0/16** | **34%** | AIラダー最大の「見えない標準装備」 |

### 共有アーキタイプは60枚中52枚まで同じ

Grafaiai(人間) vs AI モーダル grimmsnarl: **52/60一致**。差分は人間側=テック8枚
(Yveltal/Tatsugiri/Psyduck/Shaymin/Budew/Fez/Air Balloon/Boss's増)、AI側=コア増量+定型
(Poffin/Pokégear/Dawn/Spikemuth Gym)。Garchomp も 52/60。MegaLucario 45/60、Dragapult 44/60、
MegaStarmie のみ 31/60。

**解釈(仮説)**: この収束は独立発見ではなく、**AI側が人間リストを公開データセット経由で輸入した**
可能性が高い(citerne「from 30k decks」、yu0307 自身が「drop-in deck.csv」として16本を配布)。
つまり主砲Dの正確な言い方は:
**「AIメタは人間のデッキを輸入して始まったのに、淘汰の末に人間メタとは別の頂点(Alakazam/壁/ロック)へ
漂流した。残った共有部分すら、テックを削ってコピー耐性を上げる方向に変形している」**。

---

## 7. AIメタは「コピーメタ」— 標準化の定量(単位=distinct 提出)

同一アーキタイプ内で、**完全同一の60枚リスト**を提出している distinct 提出の割合:

| アーキタイプ | distinct | 最頻リストの提出数 | 集中度 |
|---|---|---|---|
| grimmsnarl | 723 | 505 | **69.8%** |
| garchomp | 100 | 59 | 59.0% |
| **alakazam** | **773** | **407** | **52.7%** |
| lucario | 96 | 36 | 37.5% |
| archaludon | 231 | 78 | 33.8% |
| crustle | 253 | 73 | 28.9% |
| starmie | 52 | 11 | 21.2% |
| dudunsparce | 24 | 5 | 20.8% |
| dragapult | 88 | 16 | 18.2% |
| tarountula | 101 | 17 | 16.8% |

**帯全体の35.6%(912/2,560体)が、たった2種類の60枚リストのどちらかをそのまま出している。**
人間16本は16/16が固有(当然だが、人間大会で60枚がバイト一致するのは同チーム内共有程度)。
grimmsnarl 69.8% は handover §2.6 の「723体中505体(70%)」の独立再計算に一致。

---

## 8. 記事用の候補主張(5本。各: 主張1文+根拠+弱点)

**D-1. 「AIラダーの王者デッキ(distinct 30%)は、人間の大会に1本も存在しない」**
- 根拠: AI alakazam 1,853側(29.2%)/773体 vs 人間 0/16本・0/960スロット・外部優勝行 0/26。
  カードは MEG 収録で人間も選べた(§2)。
- 弱点: 人間側は編集物16本+1頁サンプル。「主要でない」(≈94%水準)までで、「皆無」は過大主張。
  全49頁走査か複数ソース(公式イベント結果)で塞げる。

**D-2. 「両者は同じ道具箱を持ち、トレーナー骨格は81〜92%一致する。分岐は『何を主役にするか』に局在する」**
- 根拠: §6 の骨格表 + 共有型52/60一致 + 人間カード182種中AI皆無は15種(8%)のみ、全部ポケモン層。
- 弱点: 「輸入による収束」(§6解釈)と区別できていない。独立収束と言うと攻撃される。
  むしろ輸入説を採ってD-3に繋げる方が防御的。

**D-3. 「AIメタの順位は強さではなくコピー可能性の順位 — 帯の36%が2種類の完全同一リスト」**
- 根拠: §7 集中度(alakazam 52.7% / grimmsnarl 69.8%)+ Alakazam の EV は 46.9% で平均以下
  (field_ev、シェア1位なのに)+ heiseimikiko/mechi22 の公開スケルトン実在 + Jake 証言 + SUMI 飽和則。
- 弱点: モーダルリストと公開ノートブックの60枚照合が未実施(斥候Bの実行審査で埋まる)。
  これが埋まると「教師データの系譜」まで言えて最強になる。

**D-4. 「AI固有の生態: 壁・ハンマーロック・ライブラリアウトは、ボットの脆さが開けたニッチ」**
- 根拠: crustle 壁 254体(9.9%)+Cubchoo ロック9体+LO(soutasakurai Elo1208、
  「Great Tusk does not really attack」と設計者本人が書く)がAI側に実在し、人間側2ソースに0。
  Rock Inn の効果文(ex のダメージだけ無効)と AI メタの ex 偏重の噛み合わせ(§4-⑤ H2)。
- 弱点: 理由は全部仮説(H1〜H4未検証)。tarountula の前例(人間1勝)が示す通り
  「人間に無い」は程度問題で、悉皆調査ではない。

**D-5. 「審査員への一言型: 『あなたたちのゲームの5月のシティリーグと、Kaggle の8月のラダーは、
同じ2,022枚から別の答えを出した』」**
- 根拠: D-1〜D-4 の合成。両側の一次データを両方持っているのは公開範囲で我々だけ(291件監査で前例ゼロ)。
- 弱点: 「別の答え」の魅せ方が数字の羅列になると弱い。§9 の逆輸入実験(人間デッキを我々の操縦者に
  載せる)が1本でも走れば、「違いを実測した」に格上げできる — ただし対戦が要るので本文書では提案止まり。

---

## 9. 逆向きの問い(任務4): 人間側にあってAIに無いデッキで、我々の操縦者に向くもの

**前提(機構仮説、data.md 4110-4174)**: 我々の操縦者は特性を「最初のABILITY選択肢を盲打ち」する
(`main.py:335`)。動力源が**常在(エンジン上は選択肢に出ない)**なら操縦不要で満額
(tarountula 94.5%)、**能動選択**なら20pt級で劣化(grimmsnarl 35.0%)。

16本全ての特性コピー数を効果文から機械判定した(能動=「Once during your turn」等 /
受動=常在効果。単位=60枚中のコピー数、§11 コマンド5):

| 人間デッキ(AIに無い10本) | 能動 | 受動 | 操縦適性の読み |
|---|---|---|---|
| **Honchkrow** | **0** | **2** | ◎ 唯一の能動ゼロ |
| Slowking | 3 | 4 | ○ |
| FestivalLead | 4 | 9 | △(受動最多だが条件付き) |
| Arboliva | 7 | 2 | × |
| Zoroark | 7 | 0 | ×(grimmsnarl型) |
| MegaSharpedo | 8 | 0 | × |
| MegaVenusaur | 8 | 2 | ×(Solar Transfer は無限選択の危険) |
| RagingBolt | 9+2trg | 3 | × |
| ClefairyOgerpon | 9+2trg | 6 | × |
| TerastalBox | 10+1trg | 5 | × |

(参考: AI側モーダル alakazam は能動11 — **AIラダーの王者はむしろ特性選択が最重のデッキ**であり、
それを回せるのは模倣学習された専用操縦者だから。我々の汎用操縦者とは別問題。混同しないこと)

### 候補 #1: Honchkrow(TRバレット)— **探索的・未測定**

- **動力源が我々の実測最良デッキと同一カード**: TR Articuno「Repelling Veil」×2(常在)。
  tarountula デッキ(94.5%)と同じ盾を、別の攻撃陣で使う人間構築。
- 攻撃陣は全て素直: Murkrow「Deceit」(サポーターサーチ)、Honchkrow「Hammer In」素点100、
  Porygon2「R Command」(捨て札のTRサポーター×20 — **デッキにTRサポーターが20枚**入っており自然に育つ)。
  非ex中心=1賞交換。
- 懸念(正直に): (a) Honchkrow は1進化で **Repelling Veil の保護対象外**(たねTR限定)
  (b)「Rocket Feathers」は攻撃中の任意捨て札選択があり盲打ちの質が不明
  (c) **Team Rocket's Factory ×4(スタジアム)— 我々の操縦者のスタジアム挙動は一度も観測されていない**
  (現行デッキに0枚のため。行動語彙で Stadium 0% はこの意味)
  (d) 特殊エネ8枚(TR Energy/Ignition)の付け先選択。

### 候補 #2: Slowking/Latias — **探索的・未測定**

- 能動3(Meowth×2/Fez×1 — いずれも「使えなくても死なない」おまけ系)、受動4
  (Latias「Skyliner」=たね全員にげ0、Kyurem「Plasma Bane」条件付き)。
- 主勝ち筋が**攻撃そのもの**(Super Psy Bolt 素点120)で、特性依存が最小。たね中心+にげ0で
  盤面選択の失敗コストが低い。**limitless の実大会で「Slowking/Latias」優勝行を確認**(人間の実在保証)。
- 懸念: 「Seek Inspiration」(山札トップ捨てコピー)と Kyurem「Trifrost」(3体選択)に
  攻撃中選択があり、盲打ち時の挙動は未知。

次点: FestivalLead(受動9は16本中最多だが、動力源「Festival Lead」は **Festival Grounds
(スタジアム)が場にある時だけ**の条件付き常在。スタジアムを置けるかが未検証の我々には賭けが二重)。

**この節はデッキ転換の提案ではない**(承認事項)。測るなら: ①robustness-guard ②vs random 120戦
③Alakazam/Lucario/Archaludon ゲージ掃引、の既存ゲート順で、ゆうじのGO後に。

---

## 10. 落とした標本・限界・未達(全部開示)

1. **人間16本に頻度が無い**: シェア主張は全て limitless サンプル(26行)頼み。
   **limitless の全49頁走査は未達**(WebFetch 3回で打ち切り。SPAではなく取得可能なので、
   続きは機械的に可能 — ただし1頁ずつ)。
2. **limitless の数字は小型モデル経由の抽出**で、行の取りこぼしがありうる。頻度の主張には使わず、
   存在/不在の傍証と「主要ではない」の検定力計算のみに使った。
3. AI側 census の「どちらの分類器でも不能」111側は other に含む。other の主役内訳(§4-③)には
   Comfey 38側/15体という**未同定の塊**が残っている(中身未読)。
4. sub 54856636 が2アーキタイプに分類される(2,560体中1体)。デッキ抽出の揺れ。crustle の
   distinct 253/254 の揺れはこれ。
5. myso1987 / takusid / busyaprime のノートブックは**出力セルが空**(ソースのみ保存)。
   彼らの数字は使えず、語彙と方法論だけを傍証に使った。SUMI の数字は data.md 経由の引用。
6. yu0307 の16本が「どの大会・何位・いつ」かは**原理的に特定不能**(著者が明記)。
   「1位/2位」「同世代」は著者申告+カードプール検証(§2)による間接確認。
7. 人間側の「シティリーグ以外」(CL/JCS 等の大型大会)は未調査。top-cut 16 の代表性はシティ水準。
8. AI側は **800-1099帯のみ**。1100+帯(crustle 60.6%側 — ただし前日の監査で distinct は
   **わずか4体**と判明済みの帯)では突き合わせの絵が変わる可能性がある。
9. §9 の操縦適性は**効果文の静的判定のみ**。エンジン上で当該特性が ABILITY 選択肢として
   出るか(=ホスト裁定 ABILITY/SKILL の区別)との突合は、対戦なしでは完全にはできない。
10. **計器の残存打ち切りと、本文書の引用セルへの影響**(赤チームD指摘の中継を受けて開示):
    `band_meta_census.py` には表示上の静かな打ち切りが4種残る(①帯 n<15 非表示 ②対面セル n<20
    非表示 ③対面行列は上位26ペアで切断 ④n<3 の切り捨て)。本文書での影響範囲:
    - **§4-② の帯構成表: 影響なし**(打ち切りゼロの自前全数集計。上記宣言の通り)。
    - **§7 の集中度・§6 の浸透率・§4-③④の全数照合: 影響なし**(いずれも decks.jsonl 直接集計)。
    - **影響あり①**: D-3 で引用した「alakazam の EV 46.9%」(`field_ev.py`)は、シェア≥3%の
      6アーキタイプ(覆域89.1%)への再正規化+セル N≥10 の産物。かつ alakazam 行の
      vs lucario / vs tarountula セルは片側 distinct <15(† 表示)に乗る。EV の序列
      (シェア1位なのに平均以下)は維持されるが、絶対値は±数pt動きうる。
    - **影響あり②**: §4-⑤ H2 で触れた「我々は crustle に 64%」は N=11 の小標本セル
      (95%CIはおよそ[35,85]級)。仮説の傍証以上に使ってはいけない。

## 11. 再現コマンド(全て対戦ゼロ)

```bash
# 1. 人間16本の取得と整合検証(kaggle CLI 認証済み環境)
kaggle datasets download -d yu0307/deck-csv -p <dir> --unzip
# → リポジトリ保全済み: verification/reference/_inbox/yu0307~16-real-city-league-top-cut-decks-deck-csv/data/
# 検証スクリプトの要点: EN_Card_Data.csv を Card ID で引き、60枚/同名≤4/ACE≤1/たね≥1 を判定

# 2. AI側の帯構成(側+distinct)・対面行列
python3 replay_analysis/band_meta_census.py
python3 replay_analysis/field_ev.py 800

# 3. 突き合わせ(本文書の②③④⑦の数値):
#    band_meta_census を import し、decks.jsonl の 800-1099 側を
#    classify_b or classify_a で分類 → sub 単位で dedup(本文書の表の生成過程は git log 参照)

# 4. limitless(人間側の外部照合。SPAではない):
#    https://limitlesstcg.com/tournaments/jp?show=100   ← 2026年5月シーズン最終月・49頁

# 5. 特性の常在/能動判定: EN_Card_Data.csv の Move Name が '[Ability]' で始まる行の
#    Effect Explanation に 'Once during your turn' 等を照合(§9 の表)
```

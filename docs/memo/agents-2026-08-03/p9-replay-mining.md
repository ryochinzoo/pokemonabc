# P9全譜採掘 — tarountulaプローブ54リプレイの機構検死 (2026-08-05)

対象: sub **55236642**(deckswap-tarountula、操縦者=王者 main.py md5 **725ef4c9** で同一)。
`replay_analysis/eps55236642/` の54本全量。検証ep89907692(自己対戦)を除外した**対外戦 N=53、
相手は53体すべて distinct**(同一相手との再戦ゼロ)。

再現: `nice -n 19 python3 replay_analysis/p9_mining.py`(対戦ゼロ。ログ再送はlogs==prevで排除、
両視点をper-turn max/serialユニオンでマージ、サイドは状態ベース+最終KO補完=prize_race流儀)。

**計器の限界(先に開示)**: ①RESULTログ(type23)は53戦全てに存在せず、終局理由は
「敗者山札0→山札切れ/それ以外→KO決着」の推定+盤面終0の検出で補正 ②最終KOはログに現れない
ことがあり、KO帰属はLucario敗戦で可視61/66サイド(92%)をカバー ③状態ベースとログ台帳の
不一致は1/53戦のみ ④3ターン敗北の「0:6」は補完の産物で、実体は盤面全滅(サイドを取られ切っていない)。

## 結論先出し — 実行可能な含意トップ3

1. **Lucario対策に「壁テック」を張る前に、上界82%と2つの漏れを直視せよ。**
   敗戦11本で我々を倒した打点の**82.0%**(サイド加重 50/61 [70.5, 89.6])はMega Lucario exのワザ
   (Aura Jab 26KO / Mega Brave 12KO)で、壁(ex/メガのワザのみ無効)の守備範囲。だが
   (a) 非ex打点(Hariyama Wild Press 210=5KO、Solrock Cosmic Beam 70=4KO)が既に**13デッキ中12〜13**に
   常備され、Crustle型の壁は**壁自身しか守らない**うえHariyamaのHeave-Ho Catcher(進化時ベンチ
   引きずり出し)で剥がされる。(b) そもそも敗戦の我々の攻撃回数は**中央値2回/戦**(相手6回)で、
   壁が守っても攻撃が立たない。壁テックの検証は較正済みmakthanithinゲージでのローカル測定が先。
2. **Alakazam 91.7%の機構は「Repelling Veil の効果無効」が主で「速度」が従。失点源は
   Articuno着地前の窓に限局する。** 12戦の被ダメカン534個のうち**Spidops(Stage1=Veil対象外)が480個
   (89.9%)、たねTRへの54個は全てArticuno不在ターン**(ターンレベルで確認)。こんらん受けは
   **0回/12戦**。完全無効(被ダメカン0)が3戦。→ 伸びしろは①Articuno最速着地②**Rocket Mirror
   (Wobbuffet、ベンチTR1体のダメカンを丸ごと相手Activeへ返す)がほぼ未使用**(53戦で3回。
   見積り0のため優先されない。`_SCALING_DAMAGE`類の1行で発火する)。被ダメカンが1戦平均44.5個
   積まれる対面での返し刃。
3. **このデッキの失点は構造的に2本柱: Mewtwo ex負債とたね密度。** 全53戦で献上した190サイドの
   **33.7%**(64枚 [27.3, 40.7])がMewtwo ex(32KO×2枚)経由、Lucario敗戦に限れば**45.9%**(28/61)。
   さらに**盤面全滅負け4本**(4/27敗=たね1枚スタートのままT3-4で轢かれた)はデッキのたね11枚構成の
   事故率そのもの。次のデッキ差し替え評価軸に「ex枚数×被KO率」「たね密度(事故率)」を足すべき。

検死(data.md 2026-08-05)との照合: Lucario 2-11 / Alakazam 11-1 / Grimmsnarl 3-2 / Wall 4-0 /
Archaludon 0-3 は**完全一致**。ただし**「Mirror 0-2」の正体はtarountulaミラーではない**(→Q3)。

対面全表(N=53、全て distinct 相手):

| 対面 | W-L | distinct | | 対面 | W-L | distinct |
|---|---|---|---|---|---|---|
| Lucario | 2-11 | 13 | | StarmieMirror | 0-2 | 2 |
| Alakazam | 11-1 | 12 | | **Mirror(tarountula)** | **1-1** | 2 |
| Grimmsnarl | 3-2 | 5 | | Mega Lopunny | 0-2 | 2 |
| Wall(Crustle/Tusk) | 4-0 | 4 | | Iono's Voltorb | 0-1 | 1 |
| Dragapult | 2-1 | 3 | | Abomasnow | 0-1 | 1 |
| Archaludon | 0-3 | 3 | | Mega Gardevoir | 1-0 | 1 |
| Ogerpon | 1-2 | 3 | | Great Tusk(単独) | 1-0 | 1 |

先手番効果(参考): 先手 18W-14L(56.2% [39.3, 71.8])/ 後手 8W-13L(38.1% [20.8, 59.1])。CIは重なる。

---

## Q1. Lucario 2-11(13 distinct)— 敗戦11本の機構

**相手の構成**: 13デッキ全てに Mega Lucario ex / Riolu / Solrock / Lunatone、12デッキに Makuhita/Hariyama。

**我々を倒した打点(可視KO 47件、敗戦11本)**:

| attacker | KO数 | サイド |
|---|---|---|
| Mega Lucario ex / Aura Jab (130) | 26 | — |
| Mega Lucario ex / Mega Brave (270) | 12 | — |
| **megaEx小計** | **38 (81%)** | **50/61 (82.0% [70.5, 89.6])** |
| Hariyama / Wild Press (210) | 5 | — |
| Solrock / Cosmic Beam (70) | 4 | — |
| **非ex小計** | **9 (19%)** | **11/61 (18%)** |

Riolu/LunatoneによるKOは0(Riolu攻撃2回、Lunatone 0回)。相手の攻撃全量66回のうちmegaEx 51回(77%)。

**壁テックで防げた損害の上界 = サイド加重82%**。ただし上界であって期待値ではない:
壁(Mysterious Rock Inn型)は壁自身への打点しか止めず、相手は非壁に狙いを変えられる。
非ex代替(Wild Press 210=壁ごと一撃圏、Cosmic Beam 70)は12/13デッキに既装備。
Heave-Ho Catcher(特性、壁で止まらない)が壁をどかす。

**敗戦の速さと形**: ターン数 3,10,13,13,14,14,14,15,15,15,25(中央値14)。
我々の獲得サイド: 0枚×3 / 1枚×5 / 2枚×1 / 3枚×1 / 4枚×1 → **完封〜準完封(0-1枚)が8/11**。
競り負け(3-4枚)は2本のみ。1本(ep89926099)は**たね1枚スタートのまま盤面全滅**(T3、
サイドレースですらない)。**我々の攻撃回数: 0,0,1,1,1,2,2,2,3,5,7(中央値2)vs 相手6回/戦** —
負け試合の我々はほぼ観客だった。

**なぜ速いか**: Aura Jab 130が Spidops 130 / Articuno 120 / Murkrow 80 / Tarountula 50 を全て一撃
(Spidopsはぴったり)。可視47KOの内訳: Spidops 22 / Mewtwo ex 14 / Articuno 5 / Murkrow 3 /
Tarountula 3。**Mewtwo ex 14KO=28サイド=献上の45.9%** [34.0, 58.3] — 2枚積みのexが相手の
サイド収入の半分を配った。さらにAura Jabのおまけ(トラッシュからエネ3枚をベンチへ配給)で
次のアタッカーが即立つため、KOの合間の息継ぎが無い。

**勝った2本の形**(ep89912192 / ep89924755): どちらも**先手**、15ターン、6:1。
Rocket Rush 3〜5回が立ち、**Mega Lucario ex本体をKO(3枚取り)**+Solrock/Hariyama狩りで6枚。
Lucario 13戦の先手内訳: 先手6(2W)/後手7(0W)。

## Q2. Alakazam 11-1(12 distinct)— 勝ちの機構は「効果無効」が主、「速度」が従

**相手は12/12全てPowerful Hand型**(Alakazam 743、手札×2ダメカン、dmg0の純効果ワザ)。
Strange Hacking型(245)は**0体**、こんらん付与も**0回/12戦**。ryotaゲージのデッキとの一致は
中央値51/60(min46、**max60=1体は完全一致**)— ゲージは実ラダーAlakazamの忠実な代表だった
(94.5%ローカル→91.7%実ラダーの高転移の説明)。

**Repelling Veil の実測**(Veil=たねTRポケモンへの「ワザの効果」全無効。ダメージは効果でない):

- 相手の攻撃全量: Powerful Hand **73** / Teleportation Attack 16 / Super Psy Bolt 10 / Trading Places 1。
- 我々への被ダメカン合計 **534個/12戦**。着弾先: **Spidops(Stage1=Veil対象外)480個(89.9%)/
  たねTR 54個(10.1%)**。
- **たねTRに乗った54個は全てArticuno不在の窓**(ターンレベル検証: ep89929196の44個はT4/T6=
  Articuno着地前。着地後28ターンは0個)。Articuno在場中のたねTRへの被害は素点ダメージ
  (Super Psy Bolt 30等)のみ=仕様どおり「ダメージは通り、効果は通らない」。
- **完全無効の試合が3/12**(被ダメカン0個。PH計11発が全部不発。うちep89919699は被HP減総量0)。
- 対照実証(機構の裏取り): Grimmsnarl戦では**Munkidoriのダメカン移動(=特性でありワザでない)が
  我々のたねTRに乗っている**(例 ep89916541: Articuno12+Mewtwo9+Murkrow16個)。Veilが無効化するのは
  「ワザの効果」だけ、という区別がリプレイ上で対称に確認できた。

**勝ち方の内訳**: KO決着8 + **相手の山札切れ3**。山札切れ勝ちでは我々2-5枚 vs 相手0-2枚 —
相手はVeilを崩せず、ドローエンジン(Poffin/Poké Pad/Hilda)が先に尽きた。
唯一の敗北 ep89930458 は36ターンのグラインドの末に**我々が**山札切れ(4:3まで競って燃料切れ)。

**速度の寄与**: Alakazam 140HPはRocket Rush(30×TRポケモン、盤面6で180)の一撃圏。KO決着8本は
これで押し切った。**未使用の返し刃: Rocket Mirror(Wobbuffet、ベンチTR1体のダメカン全部を相手
バトル場へ移動)** — 被ダメカン534個/12戦の環境で53戦計3回しか出ていない(パイロットの
見積りがdmg=0のため優先度最下位)。ベンチのSpidopsに積まれた分(1体最大12個=120点)を
Alakazam 140HPへ返す設計が眠っている。

**ゲージとの挙動差**: 実ラダー勢はゲージ(ryota)とデッキも技構成もほぼ同型で、明確な挙動差は
検出されず。差があったのは「グラインドで我々を山札切れに追い込める個体がいた」こと(L1本+4:4まで
粘られたW1本)。

## Q3. 「Mirror 0-2」の正体 — tarountulaミラーではなかった

検死の"Mirror 0-2"は **StarmieMirror = Mega Starmie ex 使い**(我々が8/3に捨てた旧王者デッキの
アーキタイプ)。旧王者デッキのコピーではない(一致<40/60、2体とも)。
- ep89913411 L 0:6(14T): Jetting Blow×5+Nebula Beam×1で6体全滅。**旧デッキ系統に新デッキが轢かれた。**
- ep90036519 L(3T): たね1枚スタートのまま盤面全滅(開局事故、対面依存でない)。

**真のtarountulaミラーは1-1(2 distinct)**:
- W ep89914611(6:5、後手、58/60同型): 我々のRocket Rush 6回 vs 相手3回。開発勝ち。
- L ep90108175(3:6、後手): 相手は**改良変種**(TR Mimikyu×3 / Maximum Belt / Ultra Ball入り、
  P energy・Wobbuffet・Murkrow抜き)。我々の攻撃3回(全部Erasure Ball)vs 相手8回、
  **我々のRocket Rush 0回** — Spidopsが立つ前に轢かれた。
- 両方後手なので先手番では説明できない。**同型戦の分水嶺は「Spidopsが先に立つか」**(≒サーチ・
  展開の速さ)で、相手変種はUltra Ball増で立ち上がりを買っている。操縦者は同一(こちらは王者
  main.py、相手も類似ロジックとみられるが未確認)なので、**この1敗はデッキ構築の差**が最有力。

## Q4. Grimmsnarl 3-2 / Wall 4-0 / Archaludon 0-3(各1段落)

**Grimmsnarl 3-2(5 distinct)**: 純粋なサイドレース。勝ち3本は Grimmsnarl ex(320HP)を
Rocket Rush で割って**ex 2枚取り**を2-3回通した(6:3, 6:5。KO帰属で確認: Grimmsnarl ex 5KOは
全てRocket Rush)か、相手が**15ターン一度も攻撃しない**事故個体(ep89916541、Erasure Ball 6発で
小物6体狩り)。負け2本は Shadow Bullet 180+30ベンチ狙撃に先行され0:6 / 2:6(うち1本は盤面最大2の
立ち上がり事故)。注意: **MunkidoriのダメカンはVeilを素通りする**(特性でありワザでないため。
実測: 被ダメカン41-60個/戦、たねTRにも着弾)— Veilはこの対面では守りにならず、勝敗は素の
展開速度で決まっている。

**Wall 4-0(4 distinct)**: **Mysterious Rock Inn は「exのワザのダメージ」しか止めず、我々の主砲
Spidops(非ex)Rocket Rush が素通し** — KO帰属で確認: Crustle 9KO(Rocket Rush 8+Rocket Mirror 1)、
Great Tusk 6KO(全てRocket Rush)。Q1の壁テック検討の裏面のライブ実証=壁は非ex打点に無力。
Great Tusk型2体はほぼ無抵抗(攻撃計2回)で6:0×2、Crustle攻撃型2体(Superb Scissors 120×6-8発)
にも6:3×2。4戦で我々の被ダメカン0個。ローカルsoutasakuraiゲージ94.5%と整合。

**Archaludon 0-3(3 distinct)**: 構造的完敗。Archaludon ex は**300HP**でRocket Rush最大180の
2発圏外+Metal Defender 220が我々全員を一撃圏に置き、Assemble Alloy(進化時エネ加速)で
息継ぎなく連射(6-7発/戦)。我々の獲得0,0,2枚。1本(ep89911527)はたね1枚スタートのT4盤面全滅。
ローカルゲージ9.0%と整合 — **このプローブ最大の自動負け対面**(帯に10.7%いる)。

## Q5. 我々の下手の観測(53戦、53 distinct)

**攻撃語彙(53戦)**: Rocket Rush 107(2.0/戦)/ Erasure Ball 69 / Torment 26 / Headbutt Bounce 15 /
Deceit 10 / Take Down 5 / **Rocket Mirror 3** / **Dark Frost 0**。

既知の穴の発現状況:

1. **Ignition誤貼り: 発現せず**(この山にIgnitionは無い)。ただし**同型の穴=型盲目エネ配分**が
   全面発現: P energy 126回の貼りのうちP需要者(Mewtwo/Wobbuffet)へは33回(26%)のみ。
   **攻撃0回のArticunoに91回**(G42+P22+TR27、1.7回/戦)を吸わせ、万能通貨TR Energyの26%を
   壁に眠らせた。原因はコードで特定済み: `_max_attack_cost(Articuno)=3` が「飢え」判定を出し
   続け、エネ種を見ないキーが埋めにいく(main.py:377-409)。
2. **退却暴発**: 自ターンSWITCH **167回(3.2/戦)**+KOターン外のエネのトラッシュ落ち134枚
   (2.5/戦。退却コストとErasure Ball自己破棄の混合、ログからは分離不能)。構造原因は
   Rocket Rushの見積りが**0**(`_SCALING_DAMAGE`未登録)のため攻撃段(dmg>0要求)を素通りし
   退却チェックが先に走ること — リーサル検出もRocket Rushでは永久に発火しない。
3. **サイド負債無視**: Mewtwo ex 32KO=**64/190枚(33.7%)**が全対面の献上サイドの1/3
   (Lucario敗戦では45.9%)。Power Saver(TR4体必要)で立たないターンもex 2枚負債は場に残る。
4. **追加観測(デッキ側)**: 盤面全滅負け4本(4/27敗=14.8% [5.9, 32.5]、全て盤面最大1-2)。
   Bug Catching Set 3枚では初手たね1枚の穴を塞げていない。

**修理束(エネ配分)が入っていたら変わったと思われる場面(探索的)**:
- **Ogerpon 2敗(0:6, 0:6)は「エネ配分がそのまま失点」の最鮮明な例**: Myriad Leaf Shower は
  **両バトル場のエネ×30**で伸びる。エネを吸ったArticuno/Mewtwoが前に立つほど相手の打点を
  自給した。型を見る配分ならこの2敗の形は変わった可能性がある。
- Alakazamグラインド4本(山札切れW3+自山切れL1): TR/Pを攻撃者に集約できれば攻撃回数が増え、
  36ターン4:3の敗北は押し切れた可能性がある。
- **Lucario 11敗は修理束では動かない見込み**: エネ以前に「主砲が2発以内に死ぬ」速度の壁
  (我々の攻撃中央値2回)。ここはテック/構築の領分で、操縦の修理では埋まらない。

---

### 数字の出所と再現

- 本文の全数値: `nice -n 19 python3 replay_analysis/p9_mining.py`(スクリプト内に流儀の継承元を明記)。
- ターンレベルのVeil検証(ep89929196ほか4戦)は同スクリプトの手法でのワンオフ(本文§Q2)。
- 先手番集計・Starmie相手の旧デッキ照合もワンオフ(本文中に数値記載)。
- 相手ID・勝敗は `replay_analysis/ladder_scout/lists/55236642_list.json`(検証ep除外)。

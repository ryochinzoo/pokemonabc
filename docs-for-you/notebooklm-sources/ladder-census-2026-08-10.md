# 上位ラダー悉皆調査 — デッキ実測データ (2026-08-10)

Kaggle の順位表から上位105チームの稼働提出を全て辿り、各提出の**実際の60枚**を
リプレイから抽出したもの。**推測ではなく実測**。取得方法は
`leaderboard → team-submissions → list_episodes → リプレイ先頭部`。

**この資料の使い方**: 第1部の数字は手元で全件を数えた結果なので、そのまま引用してよい。
第2部は1提出1節の生記録で、「誰が何を使っているか」を調べるための素材。
**数値の正典は `docs/memo/data.md`。この資料と食い違ったら data.md が正しい。**

**重要な前提**: 対象は 1000〜1224 点の帯。我々は 678.7 点で、**帯の重なりはゼロ**。
これは「行き先の地図」であって「今の遭遇分布」ではない。
我々の判定指標(CEW)の重みをこの分布で置き換えてはいけない。

---

## 第1部 — 集計(全件を数えた結果)

- 対象: 上位105チーム / 順位つき提出 **209件**（+ 対戦相手として観測した野良 102件）
- デッキ抽出失敗 0件 / 60枚でない行 0件 / 重複 0件

### アーキタイプ分布

| アーキタイプ | 提出数 | 割合 |
|---|---|---|
| grimmsnarl | 57 | 27.3% |
| (未分類) | 50 | 23.9% |
| alakazam | 41 | 19.6% |
| crustle | 18 | 8.6% |
| dragapult | 16 | 7.7% |
| lucario | 11 | 5.3% |
| Kangaskhan | 10 | 4.8% |
| garchomp | 5 | 2.4% |
| archaludon | 1 | 0.5% |

### 我々の判定ゲージ(CEW)が上位帯を覆う割合

| ゲージ | CEW重み | 上位105での実数 |
|---|---|---|
| alakazam | 0.3399 | 41/209 = 19.6% |
| grimmsnarl | 0.2247 | 57/209 = 27.3% |
| crustle | 0.1572 | 18/209 = 8.6% |
| lucario | 0.1537 | 11/209 = 5.3% |
| archaludon | 0.1246 | 1/209 = 0.5% |
| **合計** | 1.0000 | **128/209 = 61.2%** |

→ **上位の 38.8% は我々のゲージに存在しないデッキ。**

### 分類器の盲点(2系統を相互検証した結果)

| 型 | 提出数 | 通算勝率 | 見落としていた側 |
|---|---|---|---|
| dudunsparce | 19 | 62.1% (N=1,988) | 我々のカード名規則(分類器A) |
| Kangaskhan | 10 | 61.2% (N=1,214) | 公開のSUMI署名(分類器B) |
| Ogerpon/Dipplin系 | 9 | **67.2%** (N=716) | **両方とも知らない** |

### 我々のデッキ(v2)との差分

**上位で広く使われ、我々が1枚も入れていないカード:**

| カード | 採用提出数 |
|---|---|
| Boss’s Orders | 201/209 (96%) |
| Buddy-Buddy Poffin | 164/209 (78%) |
| Dawn | 113/209 (54%) |
| Pokégear 3.0 | 109/209 (52%) |
| Rare Candy | 98/209 (47%) |
| Hilda | 93/209 (44%) |
| Unfair Stamp | 89/209 (43%) |
| Basic {D} Energy | 75/209 (36%) |
| Snorunt | 74/209 (35%) |
| Munkidori | 74/209 (35%) |
| Xerosic’s Machinations | 72/209 (34%) |
| Fezandipiti ex | 71/209 (34%) |
| Dudunsparce | 66/209 (32%) |
| Basic {P} Energy | 66/209 (32%) |
| Dunsparce | 62/209 (30%) |

**逆に、上位209提出の誰一人使っていない我々のカード 10種:**

- 4x Team Rocket's Energy
- 4x Team Rocket's Tarountula
- 4x Team Rocket's Spidops
- 1x Team Rocket's Wobbuffet
- 2x Team Rocket's Murkrow
- 4x Team Rocket's Transceiver
- 4x Team Rocket's Ariana
- 1x Team Rocket's Archer
- 3x Team Rocket's Giovanni
- 4x Team Rocket's Proton

### 我々自身の本番テレメトリ(agent logs)

| 提出 | 戦数 | 1手の中央値 | 最遅の1手 | stderr |
|---|---|---|---|---|
| 55308422 | 20 | 38.8ms | 602ms | 0件 |
| 55376467 | 12 | 39.2ms | 601ms | 0件 |
| 55379036 | 27 | 2.8ms | 1403ms | 0件 |

`main.py` の探索予算は 0.6秒。pilotfix/v2 の最遅が 601〜602ms で止まっているのは
**安全弁が本番で設計どおり作動している**ことを示す。stderr が全戦で空 = クラッシュ非発生の直接証拠。

---

## 第2部 — 提出ごとの生記録(grounding 素材)

各節が1提出。順位・スコア・戦績・アーキタイプ・**60枚の中身**。
「◯◯を使っているのは誰か」「××位のデッキは何か」を調べるのはここ。

### 第1位 Majkel1337 — 提出 55333348

- スコア: 1224.6　戦績: 117勝87敗 (勝率 57.4%)　総試合数: 204
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第1位 Majkel1337 — 提出 55337430

- スコア: 968.8　戦績: 69勝30敗 (勝率 69.7%)　総試合数: 99
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Slowpoke
- デッキ60枚:

    - 4x Slowking
    - 4x Slowpoke
    - 3x Mega Kangaskhan ex
    - 2x Kyurem
    - 2x Latias ex
    - 2x Smoochum
    - 1x Annihilape
    - 1x Conkeldurr
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Academy at Night
    - 4x Basic {P} Energy
    - 4x Ciphermaniac’s Codebreaking
    - 4x Lillie's Determination
    - 4x Night Stretcher
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 4x Ultra Ball
    - 3x Wondrous Patch
    - 1x Colress’s Tenacity
    - 1x Hilda
    - 1x Prime Catcher
    - 1x Switch

### 第2位 AlphaStarmie — 提出 55350342

- スコア: 1048.9　戦績: 48勝27敗 (勝率 64.0%)　総試合数: 75
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第3位 palsystem — 提出 55337492

- スコア: 966.2　戦績: 65勝37敗 (勝率 63.7%)　総試合数: 102
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Chikorita
    - 2x Dipplin
    - 2x Hydrapple ex
    - 2x Meganium
    - 2x Meowth ex
    - 1x Applin
    - 1x Applin
    - 1x Bayleef
    - 1x Bayleef
    - 1x Fezandipiti ex
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 4x Lillie's Determination
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 1x Ciphermaniac’s Codebreaking
    - 1x Dawn
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Poké Pad
    - 1x Unfair Stamp

### 第4位 James Cox & Henry Chao — 提出 55278240

- スコア: 1162.5　戦績: 163勝100敗 (勝率 62.0%)　総試合数: 263
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 3x Mega Kangaskhan ex
    - 3x Meowth ex
    - 3x Teal Mask Ogerpon ex
    - 2x Latias ex
    - 2x Raging Bolt ex
    - 1x Fezandipiti ex
    - 1x Lillie’s Clefairy ex
    - 1x Passimian
    - 1x Wellspring Mask Ogerpon ex
    - 9x Basic {G} Energy
    - 4x Area Zero Underdepths
    - 4x Crispin
    - 4x Energy Switch
    - 4x Ultra Ball
    - 2x Basic {F} Energy
    - 2x Basic {L} Energy
    - 2x Basic {P} Energy
    - 2x Boss’s Orders
    - 2x Cyrano
    - 2x Glass Trumpet
    - 2x Night Stretcher
    - 2x Xerosic’s Machinations
    - 1x Basic {W} Energy
    - 1x Prime Catcher

### 第4位 James Cox & Henry Chao — 提出 55328864

- スコア: 1124.2　戦績: 84勝46敗 (勝率 64.6%)　総試合数: 130
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 3x Mega Kangaskhan ex
    - 3x Meowth ex
    - 3x Teal Mask Ogerpon ex
    - 2x Latias ex
    - 2x Raging Bolt ex
    - 1x Fezandipiti ex
    - 1x Lillie’s Clefairy ex
    - 1x Passimian
    - 1x Wellspring Mask Ogerpon ex
    - 9x Basic {G} Energy
    - 4x Area Zero Underdepths
    - 4x Crispin
    - 4x Energy Switch
    - 4x Ultra Ball
    - 2x Basic {F} Energy
    - 2x Basic {L} Energy
    - 2x Basic {P} Energy
    - 2x Boss’s Orders
    - 2x Cyrano
    - 2x Glass Trumpet
    - 2x Night Stretcher
    - 2x Xerosic’s Machinations
    - 1x Basic {W} Energy
    - 1x Prime Catcher

### 第5位 MissingNo. — 提出 55331941

- スコア: 1157.2　戦績: 91勝38敗 (勝率 70.5%)　総試合数: 129
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 3x Hilda
    - 2x Buddy-Buddy Poffin
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Cook
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Xerosic’s Machinations

### 第5位 MissingNo. — 提出 55332194

- スコア: 1083.1　戦績: 81勝45敗 (勝率 64.3%)　総試合数: 126
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 3x Hilda
    - 2x Buddy-Buddy Poffin
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Cook
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Xerosic’s Machinations

### 第6位 flg — 提出 55290684

- スコア: 1133.2　戦績: 137勝77敗 (勝率 64.0%)　総試合数: 214
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Pokégear 3.0
    - 1x Unfair Stamp

### 第6位 flg — 提出 55290732

- スコア: 1107.5　戦績: 107勝47敗 (勝率 69.5%)　総試合数: 154
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Applin
    - 2x Bayleef
    - 2x Chikorita
    - 2x Dipplin
    - 2x Hydrapple ex
    - 2x Meganium
    - 2x Meowth ex
    - 2x Tapu Bulu
    - 1x Fezandipiti ex
    - 13x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 4x Lillie's Determination
    - 4x Ultra Ball
    - 3x Poké Pad
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Lana’s Aid
    - 1x Unfair Stamp

### 第7位 Raihan Ramadistra — 提出 55202823

- スコア: 1129.5　戦績: 307勝193敗 (勝率 61.4%)　総試合数: 500
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第8位 da da — 提出 55379796

- スコア: 1128.2　戦績: 16勝6敗 (勝率 72.7%)　総試合数: 22
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Crustle
    - 4x Dwebble
    - 4x Mega Kangaskhan ex
    - 1x Hero’s Cape
    - 4x Buddy-Buddy Poffin
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 2x Hand Trimmer
    - 1x Basic {G} Energy

### 第8位 Thai — 提出 55340443

- スコア: 1127.2　戦績: 67勝37敗 (勝率 64.4%)　総試合数: 105
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Slowpoke
- デッキ60枚:

    - 4x Slowking
    - 4x Slowpoke
    - 3x Mega Kangaskhan ex
    - 2x Kyurem
    - 2x Latias ex
    - 2x Smoochum
    - 1x Annihilape
    - 1x Conkeldurr
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Academy at Night
    - 4x Basic {P} Energy
    - 4x Ciphermaniac’s Codebreaking
    - 4x Lillie's Determination
    - 4x Night Stretcher
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 4x Ultra Ball
    - 3x Wondrous Patch
    - 1x Colress’s Tenacity
    - 1x Hilda
    - 1x Prime Catcher
    - 1x Switch

### 第8位 Thai — 提出 55350156

- スコア: 1097.3　戦績: 62勝20敗 (勝率 75.6%)　総試合数: 82
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Slowpoke
- デッキ60枚:

    - 4x Slowking
    - 4x Slowpoke
    - 3x Mega Kangaskhan ex
    - 2x Kyurem
    - 2x Latias ex
    - 2x Smoochum
    - 1x Annihilape
    - 1x Conkeldurr
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Academy at Night
    - 4x Basic {P} Energy
    - 4x Ciphermaniac’s Codebreaking
    - 4x Lillie's Determination
    - 4x Night Stretcher
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 4x Ultra Ball
    - 3x Wondrous Patch
    - 1x Colress’s Tenacity
    - 1x Hilda
    - 1x Prime Catcher
    - 1x Switch

### 第8位 da da — 提出 55367658

- スコア: 751.2　戦績: 23勝17敗 (勝率 57.5%)　総試合数: 40
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第9位 sadwat — 提出 55333279

- スコア: 1121.8　戦績: 79勝43敗 (勝率 64.8%)　総試合数: 122
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第9位 sadwat — 提出 55333284

- スコア: 1105.5　戦績: 86勝34敗 (勝率 71.7%)　総試合数: 120
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 4x Mega Kangaskhan ex
    - 3x Crustle
    - 3x Dwebble
    - 1x Hero’s Cape
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 1x Basic {G} Energy

### 第10位 LiamK — 提出 55248965

- スコア: 1120.6　戦績: 242勝170敗 (勝率 58.7%)　総試合数: 413
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第10位 LiamK — 提出 55248957

- スコア: 1055.4　戦績: 129勝70敗 (勝率 64.8%)　総試合数: 199
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第12位 vvs — 提出 55337712

- スコア: 1106.3　戦績: 62勝33敗 (勝率 65.3%)　総試合数: 95
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第12位 vvs — 提出 55349216

- スコア: 956.5　戦績: 46勝28敗 (勝率 62.2%)　総試合数: 74
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第13位 wwwwwwwwwwwwwwwwwwwwwwwwwwwwww — 提出 55379748

- スコア: 1103.3　戦績: 20勝4敗 (勝率 83.3%)　総試合数: 24
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Pokégear 3.0
    - 1x Unfair Stamp

### 第13位 @kdcyberdude — 提出 55362230

- スコア: 1101.7　戦績: 45勝19敗 (勝率 70.3%)　総試合数: 64
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第13位 @kdcyberdude — 提出 55331428

- スコア: 940.9　戦績: 61勝52敗 (勝率 54.0%)　総試合数: 113
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 4x Mega Kangaskhan ex
    - 3x Crustle
    - 3x Dwebble
    - 1x Air Balloon
    - 1x Fezandipiti ex
    - 1x Mega Lopunny ex
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Switch
    - 3x Battle Cage
    - 3x Hilda
    - 3x Lillie's Determination
    - 3x Pokégear 3.0
    - 3x Spiky Energy
    - 3x Xerosic’s Machinations
    - 2x Mist Energy
    - 1x Basic {D} Energy
    - 1x Basic {G} Energy
    - 1x Boss’s Orders
    - 1x Enriching Energy
    - 1x Night Stretcher
    - 1x Prism Energy
    - 1x Telepath Psychic Energy

### 第13位 wwwwwwwwwwwwwwwwwwwwwwwwwwwwww — 提出 55379838

- スコア: 730.1　戦績: 10勝13敗 (勝率 43.5%)　総試合数: 23
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 3x Mega Kangaskhan ex
    - 3x Meowth ex
    - 3x Teal Mask Ogerpon ex
    - 2x Latias ex
    - 2x Raging Bolt ex
    - 1x Fezandipiti ex
    - 1x Lillie’s Clefairy ex
    - 1x Passimian
    - 1x Wellspring Mask Ogerpon ex
    - 9x Basic {G} Energy
    - 4x Area Zero Underdepths
    - 4x Crispin
    - 4x Energy Switch
    - 4x Ultra Ball
    - 2x Basic {F} Energy
    - 2x Basic {L} Energy
    - 2x Basic {P} Energy
    - 2x Boss’s Orders
    - 2x Cyrano
    - 2x Glass Trumpet
    - 2x Night Stretcher
    - 2x Xerosic’s Machinations
    - 1x Basic {W} Energy
    - 1x Prime Catcher

### 第14位 Dipam Chakraborty — 提出 55379056

- スコア: 1100.0　戦績: 25勝7敗 (勝率 78.1%)　総試合数: 32
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 3x Night Stretcher
    - 2x Basic {D} Energy
    - 2x Crushing Hammer
    - 2x Jamming Tower
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第14位 Dipam Chakraborty — 提出 55370960

- スコア: 1072.4　戦績: 41勝12敗 (勝率 77.4%)　総試合数: 53
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 3x Night Stretcher
    - 2x Basic {D} Energy
    - 2x Crushing Hammer
    - 2x Jamming Tower
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第15位 Pokemon Siuuuu — 提出 55302165

- スコア: 1098.3　戦績: 95勝52敗 (勝率 64.6%)　総試合数: 147
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第15位 Pokemon Siuuuu — 提出 55351925

- スコア: 1054.0　戦績: 52勝28敗 (勝率 65.0%)　総試合数: 80
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第16位 Sixth Sense — 提出 55356795

- スコア: 1098.0　戦績: 58勝29敗 (勝率 66.7%)　総試合数: 87
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Grookey
- デッキ60枚:

    - 4x Applin
    - 4x Dipplin
    - 4x Grookey
    - 4x Thwackey
    - 2x Air Balloon
    - 2x Brave Bangle
    - 1x Goldeen
    - 1x Seaking
    - 7x Basic {G} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Bug Catching Set
    - 4x Festival Grounds
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 2x Ultra Ball
    - 1x Black Belt’s Training
    - 1x Kieran
    - 1x Pokégear 3.0
    - 1x Sacred Ash
    - 1x Unfair Stamp

### 第16位 Sixth Sense — 提出 55354892

- スコア: 1085.0　戦績: 63勝28敗 (勝率 69.2%)　総試合数: 91
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Grookey
- デッキ60枚:

    - 4x Applin
    - 4x Dipplin
    - 4x Grookey
    - 4x Thwackey
    - 2x Air Balloon
    - 2x Brave Bangle
    - 1x Goldeen
    - 1x Seaking
    - 7x Basic {G} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Bug Catching Set
    - 4x Festival Grounds
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 2x Ultra Ball
    - 1x Black Belt’s Training
    - 1x Kieran
    - 1x Pokégear 3.0
    - 1x Sacred Ash
    - 1x Unfair Stamp

### 第17位 M Sato — 提出 55367699

- スコア: 1097.4　戦績: 38勝24敗 (勝率 61.3%)　総試合数: 62
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第17位 M Sato — 提出 55367704

- スコア: 970.4　戦績: 34勝19敗 (勝率 64.2%)　総試合数: 53
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第18位 Team Rot-Weiß — 提出 55373361

- スコア: 1096.2　戦績: 39勝15敗 (勝率 72.2%)　総試合数: 54
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第18位 Team Rot-Weiß — 提出 55373917

- スコア: 982.4　戦績: 32勝18敗 (勝率 64.0%)　総試合数: 50
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第19位 tttzof351 — 提出 55380015

- スコア: 1088.0　戦績: 13勝4敗 (勝率 76.5%)　総試合数: 17
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Kadabra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第19位 Luca — 提出 55362302

- スコア: 1085.4　戦績: 43勝25敗 (勝率 63.2%)　総試合数: 68
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 1x Tapu Bulu
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Crushing Hammer
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第19位 Luca — 提出 55362304

- スコア: 977.7　戦績: 43勝25敗 (勝率 63.2%)　総試合数: 68
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Dunsparce
    - 4x Kadabra
    - 3x Dudunsparce
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Rare Candy
    - 4x Telepath Psychic Energy
    - 3x Basic {P} Energy
    - 3x Night Stretcher
    - 2x Boss’s Orders
    - 2x Xerosic’s Machinations
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Sacred Ash

### 第19位 tttzof351 — 提出 55361121

- スコア: 706.8　戦績: 26勝23敗 (勝率 53.1%)　総試合数: 49
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第20位 matsurih — 提出 55358165

- スコア: 1084.6　戦績: 50勝31敗 (勝率 61.7%)　総試合数: 81
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第20位 matsurih — 提出 55363831

- スコア: 981.2　戦績: 43勝15敗 (勝率 74.1%)　総試合数: 58
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第21位 대답해드리는게인지상정 — 提出 55378792

- スコア: 1076.3　戦績: 27勝13敗 (勝率 67.5%)　総試合数: 40
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第21位 대답해드리는게인지상정 — 提出 55379844

- スコア: 671.2　戦績: 14勝10敗 (勝率 58.3%)　総試合数: 24
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第22位 ---below this line is gay---- — 提出 55379960

- スコア: 1042.7　戦績: 16勝8敗 (勝率 66.7%)　総試合数: 24
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第22位 ---below this line is gay---- — 提出 55374880

- スコア: 833.9　戦績: 26勝15敗 (勝率 63.4%)　総試合数: 41
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第23位 THIRD PTCG Club — 提出 55377700

- スコア: 1071.0　戦績: 31勝14敗 (勝率 68.9%)　総試合数: 45
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Rare Candy
    - 4x Telepath Psychic Energy
    - 3x Battle Cage
    - 2x Basic {P} Energy
    - 2x Boss’s Orders
    - 2x Xerosic’s Machinations
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第23位 THIRD PTCG Club — 提出 55354638

- スコア: 1069.6　戦績: 57勝29敗 (勝率 66.3%)　総試合数: 86
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Munkidori
    - 1x Budew
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Jamming Tower
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Basic {D} Energy
    - 3x Boss’s Orders
    - 3x Crispin
    - 3x Night Stretcher
    - 2x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第25位 DavidFreelan — 提出 55374895

- スコア: 1069.4　戦績: 34勝16敗 (勝率 68.0%)　総試合数: 50
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Riolu
- デッキ60枚:

    - 4x Mega Lucario ex
    - 4x Riolu
    - 3x Solrock
    - 2x Lunatone
    - 1x Hero’s Cape
    - 11x Basic {F} Energy
    - 4x Dusk Ball
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Rock Fighting Energy
    - 4x Wally's Compassion
    - 3x Carmine
    - 2x Switch
    - 2x Xerosic’s Machinations

### 第25位 DavidFreelan — 提出 55374292

- スコア: 1014.4　戦績: 37勝12敗 (勝率 75.5%)　総試合数: 49
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第26位 213tubo — 提出 55363080

- スコア: 1069.3　戦績: 47勝19敗 (勝率 71.2%)　総試合数: 66
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第26位 213tubo — 提出 55353913

- スコア: 1043.8　戦績: 55勝24敗 (勝率 69.6%)　総試合数: 79
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第27位 ONE PIECE — 提出 55370915

- スコア: 1064.3　戦績: 35勝18敗 (勝率 66.0%)　総試合数: 53
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第27位 ONE PIECE — 提出 55370887

- スコア: 1000.8　戦績: 36勝16敗 (勝率 69.2%)　総試合数: 52
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第28位 Octavi Grau — 提出 55374897

- スコア: 1059.9　戦績: 37勝14敗 (勝率 72.5%)　総試合数: 51
- アーキタイプ: 分類器A=**garchomp** / 分類器B=**garchomp**　主力ポケモン: Cynthia's Roselia
- デッキ60枚:

    - 4x Cynthia's Gabite
    - 4x Cynthia's Gible
    - 4x Cynthia's Roselia
    - 3x Cynthia's Garchomp ex
    - 3x Cynthia's Power Weight
    - 3x Cynthia's Roserade
    - 2x Cynthia's Spiritomb
    - 5x Basic {F} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Rock Fighting Energy
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Forest of Vitality
    - 2x Night Stretcher
    - 1x Surfer
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第28位 Octavi Grau — 提出 55374888

- スコア: 798.8　戦績: 23勝15敗 (勝率 60.5%)　総試合数: 38
- アーキタイプ: 分類器A=**garchomp** / 分類器B=**garchomp**　主力ポケモン: Cynthia's Roselia
- デッキ60枚:

    - 4x Cynthia's Gabite
    - 4x Cynthia's Gible
    - 4x Cynthia's Roselia
    - 3x Cynthia's Garchomp ex
    - 3x Cynthia's Power Weight
    - 3x Cynthia's Roserade
    - 2x Cynthia's Spiritomb
    - 5x Basic {F} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Rock Fighting Energy
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Forest of Vitality
    - 2x Night Stretcher
    - 1x Surfer
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第29位 S4nkurero — 提出 55361685

- スコア: 1059.8　戦績: 43勝24敗 (勝率 64.2%)　総試合数: 67
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第29位 S4nkurero — 提出 55367213

- スコア: 911.2　戦績: 33勝17敗 (勝率 66.0%)　総試合数: 50
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第30位 齐乐 — 提出 55247479

- スコア: 1059.7　戦績: 117勝90敗 (勝率 56.5%)　総試合数: 207
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第30位 齐乐 — 提出 55247218

- スコア: 1042.1　戦績: 120勝97敗 (勝率 55.3%)　総試合数: 217
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第31位 yumizu — 提出 55380494

- スコア: 1059.4　戦績: 21勝12敗 (勝率 63.6%)　総試合数: 33
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第31位 Bart, Edwyn — 提出 55378371

- スコア: 1058.6　戦績: 26勝12敗 (勝率 68.4%)　総試合数: 39
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Kadabra
    - 3x Alakazam
    - 3x Dudunsparce
    - 3x Dunsparce
    - 1x Fezandipiti ex
    - 4x Battle Cage
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Rare Candy
    - 4x Telepath Psychic Energy
    - 3x Night Stretcher
    - 2x Basic {P} Energy
    - 2x Boss’s Orders
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Sacred Ash

### 第31位 Bart, Edwyn — 提出 55380079

- スコア: 919.5　戦績: 13勝7敗 (勝率 65.0%)　総試合数: 20
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Kadabra
    - 3x Alakazam
    - 3x Dudunsparce
    - 3x Dunsparce
    - 1x Fezandipiti ex
    - 4x Battle Cage
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Rare Candy
    - 4x Telepath Psychic Energy
    - 3x Night Stretcher
    - 2x Basic {P} Energy
    - 2x Boss’s Orders
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Sacred Ash

### 第31位 yumizu — 提出 55376221

- スコア: 902.3　戦績: 26勝15敗 (勝率 63.4%)　総試合数: 41
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第32位 e-toppo + kurupical — 提出 55357507

- スコア: 1057.3　戦績: 55勝26敗 (勝率 67.9%)　総試合数: 81
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 3x Night Stretcher
    - 2x Basic {D} Energy
    - 2x Crushing Hammer
    - 2x Jamming Tower
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第32位 e-toppo + kurupical — 提出 55365737

- スコア: 958.7　戦績: 37勝20敗 (勝率 64.9%)　総試合数: 57
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Dudunsparce
    - 2x Dunsparce
    - 2x Munkidori
    - 1x Budew
    - 1x Dudunsparce ex
    - 1x Fezandipiti ex
    - 1x Hero’s Cape
    - 1x Meowth ex
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Basic {D} Energy
    - 3x Basic {P} Energy
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Judge
    - 2x Night Stretcher
    - 2x Risky Ruins

### 第33位 masspeaks — 提出 55371277

- スコア: 1056.4　戦績: 34勝18敗 (勝率 65.4%)　総試合数: 52
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第33位 masspeaks — 提出 55378169

- スコア: 983.5　戦績: 28勝11敗 (勝率 71.8%)　総試合数: 39
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第34位 Pokopia — 提出 55367659

- スコア: 1055.0　戦績: 42勝20敗 (勝率 67.7%)　総試合数: 62
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第34位 Pokopia — 提出 55373213

- スコア: 830.5　戦績: 28勝14敗 (勝率 66.7%)　総試合数: 42
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第35位 NIWATORI — 提出 55291808

- スコア: 1054.2　戦績: 100勝47敗 (勝率 68.0%)　総試合数: 147
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第35位 NIWATORI — 提出 55291801

- スコア: 1008.5　戦績: 92勝62敗 (勝率 59.7%)　総試合数: 154
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 1x Sacred Charm
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Team Rocket's Petrel
    - 3x Spiky Energy
    - 3x Ultra Ball
    - 2x Buddy-Buddy Poffin
    - 2x Colress’s Tenacity
    - 2x Hilda
    - 2x Rock Fighting Energy
    - 1x Basic {G} Energy
    - 1x Community Center
    - 1x Morty’s Conviction
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Xerosic’s Machinations

### 第36位 fishcat — 提出 55299032

- スコア: 1054.2　戦績: 87勝53敗 (勝率 62.1%)　総試合数: 140
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第36位 fishcat — 提出 55273229

- スコア: 961.4　戦績: 89勝76敗 (勝率 53.9%)　総試合数: 165
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第37位 Yaroslav — 提出 55292349

- スコア: 1054.1　戦績: 82勝63敗 (勝率 56.6%)　総試合数: 145
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第37位 Yaroslav — 提出 55377439

- スコア: 932.3　戦績: 28勝16敗 (勝率 63.6%)　総試合数: 44
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第38位 hatry — 提出 55352278

- スコア: 1053.3　戦績: 58勝20敗 (勝率 74.4%)　総試合数: 78
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第38位 hatry — 提出 55361977

- スコア: 948.6　戦績: 44勝15敗 (勝率 74.6%)　総試合数: 59
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第39位 Jonathan Coletti — 提出 55373704

- スコア: 1052.9　戦績: 39勝18敗 (勝率 68.4%)　総試合数: 57
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第39位 Jonathan Coletti — 提出 55369300

- スコア: 916.5　戦績: 34勝15敗 (勝率 69.4%)　総試合数: 49
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第40位 PP kawada — 提出 55364861

- スコア: 1058.4　戦績: 46勝20敗 (勝率 69.7%)　総試合数: 66
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Applin
- デッキ60枚:

    - 4x Dipplin
    - 4x Grookey
    - 4x Thwackey
    - 3x Applin
    - 3x Volbeat
    - 1x Applin
    - 1x Brave Bangle
    - 1x Shaymin
    - 8x Basic {G} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Bug Catching Set
    - 4x Festival Grounds
    - 4x Hilda
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 1x Brock’s Scouting
    - 1x Sacred Ash
    - 1x Unfair Stamp

### 第40位 PP kawada — 提出 55366775

- スコア: 959.5　戦績: 31勝24敗 (勝率 56.4%)　総試合数: 56
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Applin
- デッキ60枚:

    - 4x Dipplin
    - 4x Grookey
    - 4x Thwackey
    - 3x Applin
    - 3x Volbeat
    - 1x Applin
    - 1x Brave Bangle
    - 8x Basic {G} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Bug Catching Set
    - 4x Festival Grounds
    - 4x Hilda
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 1x Black Belt’s Training
    - 1x Brock’s Scouting
    - 1x Sacred Ash
    - 1x Unfair Stamp

### 第41位 Kosmostars — 提出 55306986

- スコア: 1051.6　戦績: 88勝52敗 (勝率 62.9%)　総試合数: 140
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第41位 Kosmostars — 提出 55317687

- スコア: 980.0　戦績: 69勝53敗 (勝率 56.6%)　総試合数: 122
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第42位 __Taichicchi__ — 提出 55362193

- スコア: 1049.6　戦績: 43勝24敗 (勝率 64.2%)　総試合数: 67
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 3x Chikorita
    - 2x Applin
    - 2x Bayleef
    - 2x Dipplin
    - 2x Hydrapple ex
    - 2x Meganium
    - 1x Celebi
    - 1x Fezandipiti ex
    - 1x Mega Meganium ex
    - 1x Meowth ex
    - 14x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 3x Lillie's Determination
    - 3x Ultra Ball
    - 2x Boss’s Orders
    - 2x Dawn
    - 2x Night Stretcher
    - 2x Poké Pad
    - 1x Judge
    - 1x Lana’s Aid
    - 1x Unfair Stamp

### 第42位 __Taichicchi__ — 提出 55362209

- スコア: 933.2　戦績: 41勝23敗 (勝率 64.1%)　総試合数: 64
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第43位 JB Bryant — 提出 55267977

- スコア: 1048.0　戦績: 124勝89敗 (勝率 58.2%)　総試合数: 213
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第43位 JB Bryant — 提出 55308390

- スコア: 1007.6　戦績: 87勝52敗 (勝率 62.6%)　総試合数: 139
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第44位 Confusion — 提出 55294158

- スコア: 1047.4　戦績: 87勝52敗 (勝率 62.6%)　総試合数: 139
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 15x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Judge
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Lillie's Determination
    - 3x Lively Stadium
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Harlequin
    - 1x Energy Retrieval
    - 1x N's Plan

### 第44位 Confusion — 提出 55305274

- スコア: 944.3　戦績: 80勝48敗 (勝率 62.5%)　総試合数: 128
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 15x Basic {G} Energy
    - 4x Boss’s Orders
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Judge
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Lillie's Determination
    - 3x Lively Stadium
    - 2x Energy Search
    - 2x Pokégear 3.0
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第45位 你好哇 — 提出 55335975

- スコア: 1047.0　戦績: 66勝40敗 (勝率 62.3%)　総試合数: 106
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第45位 你好哇 — 提出 55334183

- スコア: 1001.6　戦績: 68勝45敗 (勝率 60.2%)　総試合数: 113
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第46位 wennan cao — 提出 55380465

- スコア: 1013.1　戦績: 11勝14敗 (勝率 44.0%)　総試合数: 25
- アーキタイプ: 分類器A=**archaludon** / 分類器B=**archaludon**　主力ポケモン: Duraludon
- デッキ60枚:

    - 4x Archaludon ex
    - 4x Cinderace
    - 4x Duraludon
    - 1x Hero’s Cape
    - 1x Relicanth
    - 11x Basic {M} Energy
    - 4x Explorer’s Guidance
    - 4x Full Metal Lab
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Pokégear 3.0
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Night Stretcher
    - 1x Judge

### 第46位 wennan cao — 提出 55381110

- スコア: 674.3　戦績: 11勝5敗 (勝率 68.8%)　総試合数: 16
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Dunsparce
    - 4x Kadabra
    - 3x Dudunsparce
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Rare Candy
    - 4x Telepath Psychic Energy
    - 3x Basic {P} Energy
    - 3x Boss’s Orders
    - 3x Night Stretcher
    - 1x Battle Cage
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Sacred Ash

### 第47位 Jack — 提出 55286357

- スコア: 1045.8　戦績: 96勝66敗 (勝率 59.3%)　総試合数: 162
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第47位 Jack — 提出 55325950

- スコア: 797.5　戦績: 46勝44敗 (勝率 51.1%)　総試合数: 90
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 2x Basic {G} Energy
    - 2x Buddy-Buddy Poffin
    - 2x Colress’s Tenacity
    - 2x Hilda
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Battle Cage
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Tool Scrapper
    - 1x Xerosic’s Machinations

### 第48位 kwa — 提出 55365227

- スコア: 1043.9　戦績: 45勝16敗 (勝率 73.8%)　総試合数: 61
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第48位 kwa — 提出 55379214

- スコア: 884.6　戦績: 23勝12敗 (勝率 65.7%)　総試合数: 35
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Grimmsnarl ex
    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 2x Froslass
    - 2x Marnie's Morgrem
    - 2x Snorunt
    - 11x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Rare Candy
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第49位 ANDPAD kaggler team — 提出 55379578

- スコア: 1057.8　戦績: 20勝11敗 (勝率 64.5%)　総試合数: 31
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第49位 ANDPAD kaggler team — 提出 55379553

- スコア: 855.8　戦績: 23勝10敗 (勝率 69.7%)　総試合数: 33
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第50位 Magist — 提出 55365909

- スコア: 1043.1　戦績: 39勝23敗 (勝率 62.9%)　総試合数: 62
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 11x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第50位 Magist — 提出 55370794

- スコア: 981.3　戦績: 33勝17敗 (勝率 66.0%)　総試合数: 50
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 11x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第51位 RtoABC — 提出 55356411

- スコア: 1042.7　戦績: 54勝28敗 (勝率 65.9%)　総試合数: 82
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Munkidori
    - 1x Budew
    - 1x Dudunsparce
    - 1x Dudunsparce ex
    - 1x Dunsparce
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Basic {D} Energy
    - 3x Basic {R} Energy
    - 3x Crispin
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 1x Jamming Tower
    - 1x Judge
    - 1x Risky Ruins
    - 1x Unfair Stamp

### 第51位 RtoABC — 提出 55356674

- スコア: 967.1　戦績: 53勝25敗 (勝率 67.9%)　総試合数: 78
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Munkidori
    - 1x Budew
    - 1x Dudunsparce
    - 1x Dudunsparce ex
    - 1x Dunsparce
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Basic {D} Energy
    - 3x Basic {R} Energy
    - 3x Crispin
    - 2x Boss’s Orders
    - 2x Night Stretcher
    - 1x Jamming Tower
    - 1x Judge
    - 1x Risky Ruins
    - 1x Unfair Stamp

### 第52位 haggle — 提出 55372617

- スコア: 1040.1　戦績: 35勝16敗 (勝率 68.6%)　総試合数: 51
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第52位 haggle — 提出 55367315

- スコア: 977.6　戦績: 34勝19敗 (勝率 64.2%)　総試合数: 53
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Judge
    - 1x Unfair Stamp

### 第53位 YumeNeko — 提出 55354380

- スコア: 1039.7　戦績: 55勝29敗 (勝率 65.5%)　総試合数: 84
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第53位 YumeNeko — 提出 55354311

- スコア: 1031.8　戦績: 54勝30敗 (勝率 64.3%)　総試合数: 84
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第54位 Canon — 提出 55362619

- スコア: 1038.5　戦績: 42勝25敗 (勝率 62.7%)　総試合数: 67
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Buddy-Buddy Poffin
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Energy Switch
    - 2x Judge
    - 1x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第54位 Canon — 提出 55362735

- スコア: 958.3　戦績: 34勝23敗 (勝率 59.6%)　総試合数: 57
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Buddy-Buddy Poffin
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Energy Switch
    - 2x Judge
    - 1x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第55位 Evgeniy Zdoronok — 提出 55242459

- スコア: 1038.4　戦績: 130勝89敗 (勝率 59.4%)　総試合数: 219
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dudunsparce
    - 3x Dunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Battle Cage
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 2x Basic {P} Energy
    - 2x Enhanced Hammer
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash
    - 1x Wondrous Patch
    - 1x Xerosic’s Machinations

### 第55位 Evgeniy Zdoronok — 提出 55095721

- スコア: 885.6　戦績: 188勝174敗 (勝率 51.9%)　総試合数: 362
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Crustle
    - 4x Dwebble
    - 4x Mega Kangaskhan ex
    - 1x Hero’s Cape
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 1x Basic {G} Energy
    - 1x Hand Trimmer

### 第56位 Oshbocker — 提出 55280123

- スコア: 1038.0　戦績: 102勝73敗 (勝率 58.3%)　総試合数: 175
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第56位 Oshbocker — 提出 55280132

- スコア: 1017.1　戦績: 100勝70敗 (勝率 58.8%)　総試合数: 170
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第57位 MtN — 提出 55363551

- スコア: 1037.6　戦績: 42勝20敗 (勝率 67.7%)　総試合数: 62
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第57位 MtN — 提出 55361039

- スコア: 973.3　戦績: 43勝28敗 (勝率 60.6%)　総試合数: 71
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第58位 Yopta — 提出 55359125

- スコア: 1035.1　戦績: 51勝30敗 (勝率 63.0%)　総試合数: 81
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第58位 Yopta — 提出 55380187

- スコア: 684.4　戦績: 18勝11敗 (勝率 62.1%)　総試合数: 29
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第59位 Team — 提出 55291360

- スコア: 1034.5　戦績: 107勝55敗 (勝率 66.0%)　総試合数: 162
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第59位 Team — 提出 55313824

- スコア: 974.0　戦績: 83勝47敗 (勝率 63.8%)　総試合数: 130
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第60位 Lunariz — 提出 55365307

- スコア: 1031.5　戦績: 43勝21敗 (勝率 67.2%)　総試合数: 64
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 1x Battle Cage
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Nighttime Mine
    - 1x Sacred Ash

### 第60位 Lunariz — 提出 55379313

- スコア: 590.6　戦績: 13勝13敗 (勝率 50.0%)　総試合数: 26
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 18x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Energy Search
    - 4x Judge
    - 4x Lillie's Determination
    - 3x Boss’s Orders
    - 3x Pokégear 3.0
    - 2x Energy Retrieval
    - 2x Grow Grass Energy
    - 2x Harlequin
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Tera Orb
    - 1x Briar
    - 1x N's Plan
    - 1x Tool Scrapper

### 第61位 Brahim — 提出 55324471

- スコア: 1031.3　戦績: 73勝52敗 (勝率 58.4%)　総試合数: 125
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Buneary
- デッキ60枚:

    - 4x Air Balloon
    - 4x Buneary
    - 4x Dudunsparce
    - 4x Dunsparce
    - 3x Mega Lopunny ex
    - 1x Fan Rotom
    - 4x Boss’s Orders
    - 4x Buddy-Buddy Poffin
    - 4x Hilda
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Pokégear 3.0
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Spiky Energy
    - 1x Enriching Energy

### 第61位 Brahim — 提出 55324462

- スコア: 978.7　戦績: 74勝36敗 (勝率 67.3%)　総試合数: 110
- アーキタイプ: 分類器A=**garchomp** / 分類器B=**garchomp**　主力ポケモン: Cynthia's Gabite
- デッキ60枚:

    - 4x Cynthia's Gabite
    - 4x Cynthia's Gible
    - 4x Cynthia's Roselia
    - 3x Cynthia's Garchomp ex
    - 3x Cynthia's Power Weight
    - 3x Cynthia's Roserade
    - 2x Cynthia's Spiritomb
    - 5x Basic {F} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Rock Fighting Energy
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Forest of Vitality
    - 2x Night Stretcher
    - 1x Surfer
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第62位 Ars Noveau — 提出 55364634

- スコア: 1031.1　戦績: 43勝23敗 (勝率 65.2%)　総試合数: 66
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第62位 Ars Noveau — 提出 55341379

- スコア: 1006.1　戦績: 60勝37敗 (勝率 61.9%)　総試合数: 97
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第63位 I4Kaggle — 提出 55247294

- スコア: 1030.2　戦績: 128勝92敗 (勝率 58.2%)　総試合数: 220
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第63位 I4Kaggle — 提出 55305454

- スコア: 981.6　戦績: 82勝62敗 (勝率 56.9%)　総試合数: 144
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第64位 ☕ Psyduck Needs Coffee — 提出 55328414

- スコア: 1023.7　戦績: 64勝46敗 (勝率 58.2%)　総試合数: 110
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第64位 ☕ Psyduck Needs Coffee — 提出 55300907

- スコア: 1020.7　戦績: 94勝68敗 (勝率 58.0%)　総試合数: 162
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第65位 wkonishi — 提出 55369238

- スコア: 1026.5　戦績: 38勝22敗 (勝率 63.3%)　総試合数: 60
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第65位 wkonishi — 提出 55363209

- スコア: 990.5　戦績: 37勝23敗 (勝率 61.7%)　総試合数: 60
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第66位 Battle Data Base — 提出 55348017

- スコア: 1022.0　戦績: 54勝39敗 (勝率 58.1%)　総試合数: 93
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Team Rocket's Articuno
    - 1x Buneary
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 1x Mega Lopunny ex
    - 1x Okidogi
    - 1x Team Rocket's Kangaskhan ex
    - 12x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Lillie's Determination
    - 4x Prism Energy
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Judge
    - 3x Pokégear 3.0
    - 3x Tera Orb
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Poké Pad
    - 1x Lt. Surge's Bargain
    - 1x Tool Scrapper

### 第66位 Battle Data Base — 提出 55348020

- スコア: 999.5　戦績: 55勝37敗 (勝率 59.8%)　総試合数: 92
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Team Rocket's Articuno
    - 1x Buneary
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 1x Mega Lopunny ex
    - 1x Okidogi
    - 1x Team Rocket's Kangaskhan ex
    - 12x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Lillie's Determination
    - 4x Prism Energy
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Judge
    - 3x Pokégear 3.0
    - 3x Tera Orb
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Poké Pad
    - 1x Lt. Surge's Bargain
    - 1x Tool Scrapper

### 第67位 爆爆盛焼脂油麺 — 提出 55345154

- スコア: 1021.2　戦績: 57勝42敗 (勝率 57.6%)　総試合数: 99
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Alakazam
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第67位 爆爆盛焼脂油麺 — 提出 55364823

- スコア: 933.5　戦績: 34勝22敗 (勝率 60.7%)　総試合数: 56
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Alakazam
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第68位 Mega Regigigas Ex Vmax — 提出 55369511

- スコア: 1019.4　戦績: 40勝20敗 (勝率 66.7%)　総試合数: 60
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第68位 Mega Regigigas Ex Vmax — 提出 55378870

- スコア: 931.3　戦績: 25勝14敗 (勝率 64.1%)　総試合数: 39
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Unfair Stamp

### 第69位 Ghleii — 提出 54866812

- スコア: 1019.2　戦績: 509勝487敗 (勝率 51.1%)　総試合数: 996
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第69位 Ghleii — 提出 54948127

- スコア: 909.1　戦績: 319勝288敗 (勝率 52.6%)　総試合数: 608
- アーキタイプ: 分類器A=**garchomp** / 分類器B=**garchomp**　主力ポケモン: Cynthia's Roselia
- デッキ60枚:

    - 4x Cynthia's Gabite
    - 4x Cynthia's Gible
    - 4x Cynthia's Roselia
    - 3x Cynthia's Garchomp ex
    - 3x Cynthia's Power Weight
    - 3x Cynthia's Roserade
    - 2x Cynthia's Spiritomb
    - 5x Basic {F} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Rock Fighting Energy
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Forest of Vitality
    - 2x Night Stretcher
    - 1x Surfer
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第70位 想要成为kaggle大师 — 提出 55355189

- スコア: 1018.5　戦績: 52勝24敗 (勝率 68.4%)　総試合数: 76
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第70位 想要成为kaggle大师 — 提出 55365545

- スコア: 973.6　戦績: 41勝23敗 (勝率 64.1%)　総試合数: 65
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: N’s Zorua
- デッキ60枚:

    - 4x N’s Zoroark ex
    - 4x N’s Zorua
    - 2x Munkidori
    - 2x N's Zekrom
    - 2x N’s Reshiram
    - 2x Punk Helmet
    - 1x Budew
    - 9x Basic {D} Energy
    - 4x Boss’s Orders
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x N’s PP Up
    - 3x Cyrano
    - 3x N’s Castle
    - 3x Poké Pad
    - 3x Ultra Ball
    - 2x Night Stretcher
    - 1x Ciphermaniac’s Codebreaking
    - 1x Janine’s Secret Art
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第71位 Nghia Tran + ketchum alt — 提出 55282766

- スコア: 1018.4　戦績: 89勝77敗 (勝率 53.6%)　総試合数: 166
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第71位 Nghia Tran + ketchum alt — 提出 55282758

- スコア: 936.9　戦績: 94勝67敗 (勝率 58.4%)　総試合数: 161
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第71位 Nghia Tran + ketchum alt — 提出 55366610

- スコア: 791.5　戦績: 26勝19敗 (勝率 57.8%)　総試合数: 45
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 18x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Lively Stadium
    - 3x Boss’s Orders
    - 3x Pokégear 3.0
    - 2x Energy Retrieval
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Harlequin
    - 2x Jumbo Ice Cream
    - 2x Tera Orb
    - 1x Briar
    - 1x N's Plan
    - 1x Tool Scrapper

### 第71位 Nghia Tran + ketchum alt — 提出 55364362

- スコア: 750.6　戦績: 28勝21敗 (勝率 57.1%)　総試合数: 49
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Dudunsparce
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Dudunsparce
    - 4x Kadabra
    - 2x Dunsparce
    - 2x Fezandipiti ex
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Rare Candy
    - 4x Telepath Psychic Energy
    - 4x Xerosic’s Machinations
    - 3x Basic {P} Energy
    - 3x Boss’s Orders
    - 2x Night Stretcher
    - 2x Poké Pad
    - 1x Lana’s Aid
    - 1x Neutralization Zone

### 第72位 PokeMiniMax — 提出 55374131

- スコア: 1018.2　戦績: 43勝10敗 (勝率 81.1%)　総試合数: 53
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Grookey
- デッキ60枚:

    - 4x Applin
    - 4x Dipplin
    - 4x Goldeen
    - 4x Grookey
    - 4x Seaking
    - 4x Thwackey
    - 2x Air Balloon
    - 2x Brave Bangle
    - 6x Basic {G} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Bug Catching Set
    - 4x Festival Grounds
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 2x Boss’s Orders
    - 1x Black Belt’s Training
    - 1x Kieran
    - 1x Switch
    - 1x Unfair Stamp

### 第72位 PokeMiniMax — 提出 55374132

- スコア: 755.8　戦績: 25勝16敗 (勝率 61.0%)　総試合数: 41
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Riolu
- デッキ60枚:

    - 3x Dunsparce
    - 3x Mega Lucario ex
    - 3x Riolu
    - 2x Air Balloon
    - 2x Dudunsparce
    - 2x Lunatone
    - 2x Solrock
    - 1x Dudunsparce ex
    - 1x Genesect
    - 1x Hero’s Cape
    - 1x Riolu
    - 9x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 3x Boss’s Orders
    - 2x Buddy-Buddy Poffin
    - 2x Gravity Mountain
    - 2x Hilda
    - 2x Ultra Ball
    - 2x Wally's Compassion
    - 1x Judge

### 第73位 tktkyamyam — 提出 55296227

- スコア: 1017.0　戦績: 91勝61敗 (勝率 59.9%)　総試合数: 152
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 18x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Energy Search
    - 4x Judge
    - 4x Lillie's Determination
    - 3x Boss’s Orders
    - 3x Pokégear 3.0
    - 2x Energy Retrieval
    - 2x Grow Grass Energy
    - 2x Harlequin
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Tera Orb
    - 1x Briar
    - 1x N's Plan
    - 1x Tool Scrapper

### 第73位 tktkyamyam — 提出 55283348

- スコア: 996.0　戦績: 97勝64敗 (勝率 60.2%)　総試合数: 161
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 18x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Energy Search
    - 4x Judge
    - 4x Lillie's Determination
    - 3x Boss’s Orders
    - 3x Pokégear 3.0
    - 2x Energy Retrieval
    - 2x Grow Grass Energy
    - 2x Harlequin
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Tera Orb
    - 1x Briar
    - 1x N's Plan
    - 1x Tool Scrapper

### 第74位 Juyong — 提出 55335476

- スコア: 1016.9　戦績: 62勝34敗 (勝率 64.6%)　総試合数: 96
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第74位 Juyong — 提出 55335480

- スコア: 996.1　戦績: 65勝38敗 (勝率 63.1%)　総試合数: 103
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第75位 cyrus — 提出 55371207

- スコア: 1016.1　戦績: 41勝15敗 (勝率 73.2%)　総試合数: 56
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第75位 cyrus — 提出 55364276

- スコア: 918.1　戦績: 34勝25敗 (勝率 57.6%)　総試合数: 60
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Munkidori
    - 1x Budew
    - 1x Dudunsparce
    - 1x Dunsparce
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Basic {P} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Basic {D} Energy
    - 3x Basic {R} Energy
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Night Stretcher
    - 2x Risky Ruins
    - 1x Judge
    - 1x Unfair Stamp

### 第76位 MarineYY — 提出 55369472

- スコア: 1015.5　戦績: 38勝17敗 (勝率 69.1%)　総試合数: 55
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Crustle
    - 4x Dwebble
    - 4x Mega Kangaskhan ex
    - 1x Hero’s Cape
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 1x Basic {G} Energy
    - 1x Hand Trimmer

### 第76位 MarineYY — 提出 55352798

- スコア: 972.8　戦績: 60勝31敗 (勝率 65.9%)　総試合数: 92
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Crustle
    - 4x Dwebble
    - 4x Mega Kangaskhan ex
    - 1x Hero’s Cape
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 1x Basic {G} Energy
    - 1x Hand Trimmer

### 第77位 cununn — 提出 55373892

- スコア: 1014.4　戦績: 31勝18敗 (勝率 63.3%)　総試合数: 49
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第77位 cununn — 提出 55373886

- スコア: 952.0　戦績: 27勝19敗 (勝率 58.7%)　総試合数: 46
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第78位 goonew — 提出 55362161

- スコア: 1013.6　戦績: 44勝20敗 (勝率 68.8%)　総試合数: 64
- アーキタイプ: 分類器A=**garchomp** / 分類器B=**garchomp**　主力ポケモン: Cynthia's Roselia
- デッキ60枚:

    - 4x Cynthia's Gabite
    - 4x Cynthia's Gible
    - 4x Cynthia's Roselia
    - 3x Cynthia's Garchomp ex
    - 3x Cynthia's Power Weight
    - 3x Cynthia's Roserade
    - 2x Cynthia's Spiritomb
    - 4x Basic {F} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Fighting Gong
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Rock Fighting Energy
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Forest of Vitality
    - 2x Night Stretcher
    - 2x Xerosic’s Machinations
    - 1x Pokégear 3.0
    - 1x Unfair Stamp

### 第78位 goonew — 提出 55370073

- スコア: 1001.5　戦績: 37勝17敗 (勝率 68.5%)　総試合数: 54
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Arboliva ex
    - 2x Chikorita
    - 2x Dolliv
    - 2x Meganium
    - 2x Meowth ex
    - 2x Smoliv
    - 1x Bayleef
    - 1x Bayleef
    - 1x Budew
    - 1x Fezandipiti ex
    - 13x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 4x Lillie's Determination
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Dawn
    - 2x Poké Pad
    - 1x Energy Switch
    - 1x Judge
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Unfair Stamp

### 第79位 Boss's Orders Are All You Need — 提出 55361202

- スコア: 1013.7　戦績: 47勝21敗 (勝率 69.1%)　総試合数: 69
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Slowpoke
- デッキ60枚:

    - 4x Slowking
    - 4x Slowpoke
    - 3x Mega Kangaskhan ex
    - 2x Kyurem
    - 2x Latias ex
    - 2x Smoochum
    - 1x Annihilape
    - 1x Conkeldurr
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Academy at Night
    - 4x Basic {P} Energy
    - 4x Ciphermaniac’s Codebreaking
    - 4x Lillie's Determination
    - 4x Night Stretcher
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 4x Ultra Ball
    - 3x Wondrous Patch
    - 1x Colress’s Tenacity
    - 1x Hilda
    - 1x Prime Catcher
    - 1x Switch

### 第79位 Boss's Orders Are All You Need — 提出 55379333

- スコア: 725.0　戦績: 22勝10敗 (勝率 68.8%)　総試合数: 32
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Slowpoke
- デッキ60枚:

    - 4x Slowking
    - 4x Slowpoke
    - 3x Mega Kangaskhan ex
    - 2x Kyurem
    - 2x Latias ex
    - 2x Smoochum
    - 1x Annihilape
    - 1x Conkeldurr
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Academy at Night
    - 4x Basic {P} Energy
    - 4x Ciphermaniac’s Codebreaking
    - 4x Lillie's Determination
    - 4x Night Stretcher
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 4x Ultra Ball
    - 3x Wondrous Patch
    - 1x Colress’s Tenacity
    - 1x Hilda
    - 1x Prime Catcher
    - 1x Switch

### 第80位 GuerillaMoon — 提出 55367101

- スコア: 1011.4　戦績: 32勝25敗 (勝率 56.1%)　総試合数: 57
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第80位 GuerillaMoon — 提出 55358292

- スコア: 943.3　戦績: 55勝21敗 (勝率 72.4%)　総試合数: 76
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第81位 takayosi — 提出 55299922

- スコア: 1015.0　戦績: 80勝67敗 (勝率 54.4%)　総試合数: 147
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 18x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Energy Search
    - 4x Judge
    - 4x Lillie's Determination
    - 3x Boss’s Orders
    - 3x Pokégear 3.0
    - 2x Energy Retrieval
    - 2x Grow Grass Energy
    - 2x Harlequin
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Tera Orb
    - 1x Briar
    - 1x N's Plan
    - 1x Tool Scrapper

### 第81位 takayosi — 提出 55377180

- スコア: 909.3　戦績: 25勝15敗 (勝率 62.5%)　総試合数: 40
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 18x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Energy Search
    - 4x Judge
    - 4x Lillie's Determination
    - 3x Boss’s Orders
    - 3x Pokégear 3.0
    - 2x Energy Retrieval
    - 2x Grow Grass Energy
    - 2x Harlequin
    - 2x Jumbo Ice Cream
    - 2x Lively Stadium
    - 2x Tera Orb
    - 1x Briar
    - 1x N's Plan
    - 1x Tool Scrapper

### 第82位 Where is my orbit — 提出 54957625

- スコア: 1010.8　戦績: 531勝466敗 (勝率 53.3%)　総試合数: 1000
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 4x Mega Kangaskhan ex
    - 3x Crustle
    - 3x Dwebble
    - 1x Hero’s Cape
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 1x Basic {G} Energy

### 第82位 Where is my orbit — 提出 54959248

- スコア: 952.8　戦績: 528勝472敗 (勝率 52.8%)　総試合数: 1000
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 4x Mega Kangaskhan ex
    - 3x Crustle
    - 3x Dwebble
    - 1x Hero’s Cape
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Grow Grass Energy
    - 4x Hilda
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Switch
    - 4x Xerosic’s Machinations
    - 2x Battle Cage
    - 2x Boss’s Orders
    - 1x Basic {G} Energy

### 第83位 szlachetny snieg — 提出 55341389

- スコア: 1010.3　戦績: 68勝35敗 (勝率 66.0%)　総試合数: 103
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第83位 szlachetny snieg — 提出 55368707

- スコア: 973.4　戦績: 36勝15敗 (勝率 70.6%)　総試合数: 51
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第84位 KouFu — 提出 55328142

- スコア: 1010.2　戦績: 70勝45敗 (勝率 60.9%)　総試合数: 115
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Crushing Hammer
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第84位 KouFu — 提出 55367223

- スコア: 553.6　戦績: 17勝17敗 (勝率 50.0%)　総試合数: 34
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Slowpoke
- デッキ60枚:

    - 4x Slowking
    - 4x Slowpoke
    - 3x Mega Kangaskhan ex
    - 2x Kyurem
    - 2x Latias ex
    - 2x Smoochum
    - 1x Annihilape
    - 1x Conkeldurr
    - 1x Fezandipiti ex
    - 1x Meowth ex
    - 4x Academy at Night
    - 4x Basic {P} Energy
    - 4x Ciphermaniac’s Codebreaking
    - 4x Lillie's Determination
    - 4x Night Stretcher
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 4x Ultra Ball
    - 3x Wondrous Patch
    - 1x Colress’s Tenacity
    - 1x Hilda
    - 1x Prime Catcher
    - 1x Switch

### 第85位 BC+ — 提出 55370560

- スコア: 1008.9　戦績: 39勝14敗 (勝率 73.6%)　総試合数: 53
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第85位 BC+ — 提出 55370572

- スコア: 824.1　戦績: 28勝14敗 (勝率 66.7%)　総試合数: 42
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第86位 cm391 — 提出 55345024

- スコア: 1008.6　戦績: 55勝47敗 (勝率 53.9%)　総試合数: 102
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第86位 cm391 — 提出 55345031

- スコア: 948.7　戦績: 51勝30敗 (勝率 63.0%)　総試合数: 81
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Handheld Fan
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Pokégear 3.0
    - 1x Unfair Stamp

### 第87位 Boseiju — 提出 55359464

- スコア: 1007.9　戦績: 41勝35敗 (勝率 53.9%)　総試合数: 76
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第87位 Boseiju — 提出 55373424

- スコア: 965.3　戦績: 27勝19敗 (勝率 58.7%)　総試合数: 46
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第88位 【共逐荣光】Timmy Juicehouse — 提出 55377210

- スコア: 1007.7　戦績: 24勝19敗 (勝率 55.8%)　総試合数: 43
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第88位 【共逐荣光】Timmy Juicehouse — 提出 55380837

- スコア: 834.9　戦績: 20勝8敗 (勝率 71.4%)　総試合数: 28
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第89位 miya — 提出 55365521

- スコア: 1007.2　戦績: 38勝20敗 (勝率 65.5%)　総試合数: 58
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第89位 miya — 提出 55351478

- スコア: 990.8　戦績: 51勝35敗 (勝率 59.3%)　総試合数: 86
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第90位 Byer Script — 提出 55299971

- スコア: 1006.9　戦績: 91勝71敗 (勝率 56.2%)　総試合数: 162
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第90位 Byer Script — 提出 55294562

- スコア: 949.3　戦績: 84勝63敗 (勝率 57.1%)　総試合数: 147
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第91位 ei1333 — 提出 55296170

- スコア: 1005.9　戦績: 91勝53敗 (勝率 63.2%)　総試合数: 144
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第91位 ei1333 — 提出 55238370

- スコア: 823.4　戦績: 99勝74敗 (勝率 57.2%)　総試合数: 173
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第92位 あなまか — 提出 55276449

- スコア: 1004.1　戦績: 97勝84敗 (勝率 53.6%)　総試合数: 181
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 2x Basic {G} Energy
    - 2x Buddy-Buddy Poffin
    - 2x Colress’s Tenacity
    - 2x Hilda
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Battle Cage
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Tool Scrapper
    - 1x Xerosic’s Machinations

### 第92位 あなまか — 提出 55366038

- スコア: 567.3　戦績: 19勝17敗 (勝率 52.8%)　総試合数: 36
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第93位 llkarill — 提出 55217790

- スコア: 1003.6　戦績: 147勝135敗 (勝率 52.1%)　総試合数: 282
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Arboliva ex
    - 2x Bayleef
    - 2x Chikorita
    - 2x Dolliv
    - 2x Meganium
    - 2x Meowth ex
    - 2x Smoliv
    - 1x Budew
    - 1x Fezandipiti ex
    - 1x Tapu Bulu
    - 12x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 4x Lillie's Determination
    - 4x Ultra Ball
    - 3x Dawn
    - 2x Boss’s Orders
    - 1x Energy Switch
    - 1x Judge
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Poké Pad
    - 1x Unfair Stamp

### 第93位 llkarill — 提出 55354960

- スコア: 807.3　戦績: 40勝20敗 (勝率 66.7%)　総試合数: 60
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 2x Arboliva ex
    - 2x Bayleef
    - 2x Chikorita
    - 2x Dolliv
    - 2x Meganium
    - 2x Meowth ex
    - 2x Smoliv
    - 1x Budew
    - 1x Fezandipiti ex
    - 1x Tapu Bulu
    - 12x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 4x Lillie's Determination
    - 4x Ultra Ball
    - 3x Dawn
    - 2x Boss’s Orders
    - 1x Energy Switch
    - 1x Judge
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Poké Pad
    - 1x Unfair Stamp

### 第94位 Klein Houmani — 提出 55367728

- スコア: 1005.4　戦績: 37勝20敗 (勝率 64.9%)　総試合数: 57
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 4x Mega Kangaskhan ex
    - 3x Crustle
    - 3x Dwebble
    - 1x Hero’s Cape
    - 1x Team Rocket's Articuno
    - 1x Team Rocket's Kangaskhan ex
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 3x Pokégear 3.0
    - 2x Buddy-Buddy Poffin
    - 2x Hilda
    - 1x Basic {G} Energy
    - 1x Basic {W} Energy
    - 1x Bianca’s Devotion
    - 1x Brock’s Scouting
    - 1x Cook
    - 1x Eri
    - 1x Lumiose Galette
    - 1x Night Stretcher
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Ultra Ball
    - 1x Xerosic’s Machinations

### 第94位 haruto — 提出 55380478

- スコア: 997.0　戦績: 22勝11敗 (勝率 66.7%)　総試合数: 33
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第94位 Klein Houmani — 提出 55362187

- スコア: 932.4　戦績: 39勝20敗 (勝率 66.1%)　総試合数: 59
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Mega Kangaskhan ex
- デッキ60枚:

    - 4x Mega Kangaskhan ex
    - 3x Crustle
    - 3x Dwebble
    - 1x Hero’s Cape
    - 1x Team Rocket's Articuno
    - 1x Team Rocket's Kangaskhan ex
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 3x Pokégear 3.0
    - 2x Buddy-Buddy Poffin
    - 2x Hilda
    - 1x Basic {G} Energy
    - 1x Basic {W} Energy
    - 1x Bianca’s Devotion
    - 1x Brock’s Scouting
    - 1x Cook
    - 1x Eri
    - 1x Lumiose Galette
    - 1x Night Stretcher
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Ultra Ball
    - 1x Xerosic’s Machinations

### 第94位 haruto — 提出 55380469

- スコア: 847.7　戦績: 20勝12敗 (勝率 62.5%)　総試合数: 32
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第95位 宝糕手 — 提出 55360284

- スコア: 1002.8　戦績: 45勝30敗 (勝率 60.0%)　総試合数: 75
- アーキタイプ: 分類器A=**alakazam** / 分類器B=**alakazam**　主力ポケモン: Abra
- デッキ60枚:

    - 4x Abra
    - 4x Alakazam
    - 4x Kadabra
    - 3x Dunsparce
    - 2x Dudunsparce
    - 1x Fezandipiti ex
    - 1x Shaymin
    - 4x Buddy-Buddy Poffin
    - 4x Dawn
    - 4x Enhanced Hammer
    - 4x Hilda
    - 4x Poké Pad
    - 4x Telepath Psychic Energy
    - 3x Boss’s Orders
    - 3x Rare Candy
    - 3x Xerosic’s Machinations
    - 2x Basic {P} Energy
    - 2x Nighttime Mine
    - 1x Enriching Energy
    - 1x Lana’s Aid
    - 1x Night Stretcher
    - 1x Sacred Ash

### 第95位 宝糕手 — 提出 55366789

- スコア: 663.3　戦績: 27勝15敗 (勝率 64.3%)　総試合数: 42
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Drakloak
- デッキ60枚:

    - 4x Drakloak
    - 4x Dreepy
    - 3x Dragapult ex
    - 2x Budew
    - 2x Meowth ex
    - 2x Munkidori
    - 1x Fezandipiti ex
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crushing Hammer
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Ultra Ball
    - 3x Boss’s Orders
    - 3x Crispin
    - 2x Basic {D} Energy
    - 2x Jamming Tower
    - 2x Night Stretcher
    - 1x Dawn
    - 1x Unfair Stamp

### 第96位 李秉叡（ntumlnoob） — 提出 55365892

- スコア: 1006.9　戦績: 45勝15敗 (勝率 75.0%)　総試合数: 61
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第96位 李秉叡（ntumlnoob） — 提出 55366513

- スコア: 940.7　戦績: 38勝15敗 (勝率 71.7%)　総試合数: 53
- アーキタイプ: 分類器A=**lucario** / 分類器B=**lucario**　主力ポケモン: Mega Lucario ex
- デッキ60枚:

    - 4x Mega Lucario ex
    - 3x Riolu
    - 3x Solrock
    - 2x Hariyama
    - 2x Lunatone
    - 2x Makuhita
    - 1x Hero’s Cape
    - 13x Basic {F} Energy
    - 4x Fighting Gong
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Premium Power Pro
    - 4x Ultra Ball
    - 2x Boss’s Orders
    - 2x Switch
    - 2x Wally's Compassion

### 第97位 S. B. — 提出 55344264

- スコア: 1003.1　戦績: 64勝28敗 (勝率 69.6%)　総試合数: 92
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第97位 loIzpo + emonga — 提出 55374852

- スコア: 1001.4　戦績: 37勝15敗 (勝率 71.2%)　総試合数: 52
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Buneary
    - 3x Dudunsparce
    - 3x Mega Lopunny ex
    - 2x Lillie’s Clefairy ex
    - 1x Fan Rotom
    - 1x Latias ex
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Wally's Compassion
    - 3x Battle Cage
    - 3x Hilda
    - 3x Poké Pad
    - 3x Telepath Psychic Energy
    - 3x Ultra Ball
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 2x Xerosic’s Machinations
    - 1x Enriching Energy
    - 1x Hand Trimmer
    - 1x Night Stretcher

### 第97位 S. B. — 提出 55218119

- スコア: 968.3　戦績: 133勝128敗 (勝率 51.0%)　総試合数: 261
- アーキタイプ: 分類器A=**grimmsnarl** / 分類器B=**grimmsnarl**　主力ポケモン: Munkidori
- デッキ60枚:

    - 4x Marnie's Impidimp
    - 4x Munkidori
    - 3x Marnie's Grimmsnarl ex
    - 3x Marnie's Morgrem
    - 2x Froslass
    - 2x Snorunt
    - 10x Basic {D} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Spikemuth Gym
    - 4x Team Rocket's Petrel
    - 3x Night Stretcher
    - 3x Rare Candy
    - 2x Boss’s Orders
    - 1x Dawn
    - 1x Pokégear 3.0
    - 1x Tool Scrapper
    - 1x Unfair Stamp

### 第97位 loIzpo + emonga — 提出 55374744

- スコア: 880.1　戦績: 25勝16敗 (勝率 61.0%)　総試合数: 41
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Grookey
- デッキ60枚:

    - 4x Applin
    - 4x Dipplin
    - 4x Grookey
    - 4x Thwackey
    - 3x Brave Bangle
    - 1x Fezandipiti ex
    - 7x Basic {G} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Bug Catching Set
    - 4x Festival Grounds
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 4x Pokégear 3.0
    - 3x Night Stretcher
    - 2x Dawn
    - 1x Sacred Ash
    - 1x Tool Scrapper
    - 1x Unfair Stamp
    - 1x Xerosic’s Machinations

### 第98位 ykhnkf — 提出 55380812

- スコア: 926.1　戦績: 18勝14敗 (勝率 56.2%)　総試合数: 32
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 2x Basic {G} Energy
    - 2x Buddy-Buddy Poffin
    - 2x Colress’s Tenacity
    - 2x Hilda
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Battle Cage
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Tool Scrapper
    - 1x Xerosic’s Machinations

### 第98位 ykhnkf — 提出 55380823

- スコア: 833.7　戦績: 21勝11敗 (勝率 65.6%)　総試合数: 32
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 2x Basic {G} Energy
    - 2x Buddy-Buddy Poffin
    - 2x Colress’s Tenacity
    - 2x Hilda
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Battle Cage
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Tool Scrapper
    - 1x Xerosic’s Machinations

### 第99位 typeIIIfairy — 提出 55324935

- スコア: 1000.8　戦績: 67勝54敗 (勝率 55.4%)　総試合数: 121
- アーキタイプ: 分類器A=**未分類** / 分類器B=**dudunsparce**　主力ポケモン: Dunsparce
- デッキ60枚:

    - 4x Dunsparce
    - 3x Air Balloon
    - 3x Dudunsparce
    - 2x Buneary
    - 2x Mega Froslass ex
    - 2x Mega Lopunny ex
    - 2x Snorunt
    - 1x Fan Rotom
    - 4x Buddy-Buddy Poffin
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Poké Pad
    - 4x Ultra Ball
    - 4x Wally's Compassion
    - 3x Basic {W} Energy
    - 3x Battle Cage
    - 3x Hand Trimmer
    - 3x Hilda
    - 2x Boss’s Orders
    - 2x Pokégear 3.0
    - 1x Enriching Energy

### 第99位 Yan — 提出 55235071

- スコア: 1000.3　戦績: 124勝100敗 (勝率 55.4%)　総試合数: 224
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 1x Tapu Bulu
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Crushing Hammer
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第99位 Yan — 提出 55256480

- スコア: 870.4　戦績: 89勝59敗 (勝率 60.1%)　総試合数: 148
- アーキタイプ: 分類器A=**未分類** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 1x Hero’s Cape
    - 1x Tapu Bulu
    - 17x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Judge
    - 4x Lillie's Determination
    - 4x Tera Orb
    - 3x Crushing Hammer
    - 3x Jumbo Ice Cream
    - 3x Pokégear 3.0
    - 2x Boss’s Orders
    - 2x Energy Search
    - 2x Grow Grass Energy
    - 2x Lively Stadium
    - 1x Briar
    - 1x Energy Retrieval
    - 1x Harlequin
    - 1x N's Plan

### 第99位 typeIIIfairy — 提出 55324819

- スコア: 649.3　戦績: 31勝32敗 (勝率 49.2%)　総試合数: 63
- アーキタイプ: 分類器A=**crustle** / 分類器B=**crustle**　主力ポケモン: Dwebble
- デッキ60枚:

    - 4x Dwebble
    - 3x Crustle
    - 2x Mega Kangaskhan ex
    - 1x Cornerstone Mask Ogerpon ex
    - 1x Hero’s Cape
    - 4x Boss’s Orders
    - 4x Grow Grass Energy
    - 4x Jumbo Ice Cream
    - 4x Lillie's Determination
    - 4x Mist Energy
    - 4x Pokégear 3.0
    - 4x Spiky Energy
    - 4x Team Rocket's Petrel
    - 2x Basic {G} Energy
    - 2x Buddy-Buddy Poffin
    - 2x Colress’s Tenacity
    - 2x Hilda
    - 2x Rock Fighting Energy
    - 2x Ultra Ball
    - 1x Battle Cage
    - 1x Switch
    - 1x Team Rocket's Factory
    - 1x Tool Scrapper
    - 1x Xerosic’s Machinations

### 第100位 tonakaiiii — 提出 55185728

- スコア: 1000.1　戦績: 202勝177敗 (勝率 53.3%)　総試合数: 379
- アーキタイプ: 分類器A=**Kangaskhan** / 分類器B=**未分類**　主力ポケモン: Teal Mask Ogerpon ex
- デッキ60枚:

    - 4x Teal Mask Ogerpon ex
    - 3x Chikorita
    - 2x Bayleef
    - 2x Bulbasaur
    - 2x Ivysaur
    - 2x Mega Kangaskhan ex
    - 2x Mega Venusaur ex
    - 2x Meganium
    - 11x Basic {G} Energy
    - 4x Bug Catching Set
    - 4x Forest of Vitality
    - 4x Wally's Compassion
    - 3x Hilda
    - 2x Colress’s Tenacity
    - 2x Dawn
    - 2x Mega Signal
    - 2x Poké Pad
    - 2x Pokégear 3.0
    - 1x Boss’s Orders
    - 1x Energy Retrieval
    - 1x Enriching Energy
    - 1x Switch
    - 1x Xerosic’s Machinations

### 第100位 tonakaiiii — 提出 55381423

- スコア: 569.5　戦績: 16勝8敗 (勝率 66.7%)　総試合数: 24
- アーキタイプ: 分類器A=**dragapult** / 分類器B=**dragapult**　主力ポケモン: Dreepy
- デッキ60枚:

    - 4x Dragapult ex
    - 4x Drakloak
    - 4x Dreepy
    - 4x Dunsparce
    - 3x Munkidori
    - 2x Dudunsparce
    - 1x Dudunsparce ex
    - 1x Hero’s Cape
    - 4x Basic {P} Energy
    - 4x Basic {R} Energy
    - 4x Buddy-Buddy Poffin
    - 4x Crispin
    - 4x Lillie's Determination
    - 4x Poké Pad
    - 3x Basic {D} Energy
    - 3x Dusk Ball
    - 3x Risky Ruins
    - 2x Dawn
    - 1x Boss’s Orders
    - 1x Night Stretcher

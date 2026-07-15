# 実データ（Data）

参照用の生データ。提出スコアとローカル勝率を時系列で残す。

## Kaggle 提出履歴（Simulation部門）

| # | 日付 | ref | 中身 | status | publicScore | メモ |
|---|---|---|---|---|---|---|
| 1 | 2026-06-28 | 54146595 | ランダム(サンプル) + サンプルデッキ | COMPLETE | **413.4**→381.1 | 配管確認の初提出＝基準点 |
| 2 | 2026-07-08 | 54435972 | **v1(貪欲+評価)** + サンプルデッキ | COMPLETE | **600.0**(初期値) | 較正提出(D10)。推移を観察 |

参考: 初提出時のリーダーボード上位 … 1位 1427.4 / 2位 1343.7 / 3位 1342.4 / 中位帯 〜1225。

## ローカル自己対戦ベンチマーク

測り方: `cd sample_submission/sample_submission && python3 selfplay.py <戦数>`（席を入れ替えて先後の有利を均す）。

| 日付 | 対戦 | 結果(agent0–agent1–引分) | 速度 | メモ |
|---|---|---|---|---|
| 2026-06-28 | random vs random (50戦) | 30–20–0 | ~9ms/戦 | ハーネス動作確認（強さ比較ではない） |
| 2026-07-07 | main.py(random) vs **Alakazam型ゲージ** (200戦) | 51–149–0 = **25.5%** (CI 20.0〜32.0%) | ~9ms/戦 | メタ再現モード初回＝改善の基準点 |
| 2026-07-07 | **main.py v1(貪欲+評価)** vs random (300戦) | 273–27–0 = **91.0%** (CI 87.2〜93.7%) | ~7ms/戦 | D8採用ゲート PASS |
| 2026-07-07 | **main.py v1** vs Alakazam型ゲージ (300戦) | 189–111–0 = **63.0%** (CI 57.4〜68.3%) | ~11ms/戦 | 25.5%→63.0%。デッキはサンプルのまま（メガユキノオーex+水エネ35） |

| 2026-07-08 | main.py v1 vs **Grimmsnarl型ゲージ** (300戦) | 226–74–0 = **75.3%** | ~10ms/戦 | 第2ゲージ初回。2ゲージ平均=69.2% |

> 今後ここに「v1(ヒューリスティック) vs random の勝率」などを積む。目標は各版で random 比の勝率を上げること。
> メタ再現モード: `python3 .claude/skills/bench/scripts/bench.py N --opponent alakazam_agent.py --opponent-deck decks/alakazam_v0.csv`
> 第2ゲージ: `--opponent grimmsnarl_agent.py --opponent-deck decks/grimmsnarl_v0.csv`

## デッキ総当たり（2026-07-08, deck_tournament.py, 同一パイロット=v1, 300戦/ペア）

| | vs sample | vs alakazam | vs archaludon | vs grimmsnarl | 総合 |
|---|---|---|---|---|---|
| sample(メガユキノオー) | – | 68.0% | 45.0% | 84.3% | **65.8%** |
| archaludon_v0 | 55.0% | 54.7% | – | 53.3% | 54.3% |
| grimmsnarl_v0 | 15.7% | 57.7% | 46.7% | – | 40.0% |
| alakazam_v0 | 32.0% | – | 45.3% | 42.3% | 39.9% |

- 専用AIゲージとの対戦: Archaludon(v1操縦) vs Alakazamゲージ **40.0%** / vs Grimmsnarlゲージ **53.0%**（サンプルはそれぞれ63.0% / 75.3%）→ D9の根拠。
- 2強ゲージ直接対決（専用AI同士300戦）: Grimmsnarl側 **50.3%** ≒ 五分。
- Grimmsnarlゲージの下界確認: vs ランダム+サンプル 69.5%（Alakazamゲージの74.5%よりやや弱い）。

## cabt実機検証（2026-07-07, verify_alakazam.py, 10戦）

| 仮説 | 結果 |
|---|---|
| Psychic Draw = 進化時にKadabra 2枚/Alakazam 3枚ドロー | 成立（22回発動） |
| Powerful Hand = 手札×20のダメカン乗せ（弱点・抵抗・軽減を通らない） | **15/15回で完全一致**。実戦手札14〜21枚→280〜420ダメ |
| Run Away Draw = 3ドロー＋本体山戻り | 成立（16回、山戻り100%） |
| ふしぎなアメ = Abra→Alakazam直進化 | 6/6成立 |

- カードプール正本: CSVユニークID 1267種 ＝ エンジン`all_card_data()` 1267種（完全一致、差分ゼロ）。
- 基本超エネのCard ID = **5**（基本エネはID 1〜8がタイプ順）。

## 環境
- Python 3.14.6 / macOS arm64。エンジン `cg/libcg.dylib`。
- カードデータ: `all_card_data()`=1267種、`all_attack()`=1556種。CSV は `EN/JP_Card_Data.csv`（行数2102=複数ワザでカードが複数行になるため）。

## 監査セッション(2026-07-08): Kaggle実対戦リプレイ解析

取得方法は新設 `replay_analysis/`(trace_replay.py 等)と memory の kaggle-replay-pipeline を参照。

### v1提出(54435972)の実対戦15戦(提出後最初の1時間)
- 7勝8敗、レーティング 600→底325→**424(15戦時点・上昇中)**。提出直後の「428.6下降中」は収束前の瞬間値であり誤読だった。
- クラッシュ/時間切れ 0(remainingOverageTime 最小588.9/600秒)。
- **負け8戦中5戦が相手の2〜4ターン目で終了する即死**。全て「basic1枚スタート→初撃で盤面全滅」。
- 24ターン負け(ep84676947): Kyogreが壁Meowth exに**ダメージ0の攻撃を10ターン連続**→Dragapult ex×3完成→一撃200で敗北。0ダメ攻撃・リトリート不在・相手を見ない、が実敗因として観測された。
- サンプルデッキのマリガン率46%・basic1枚スタート率74%(超幾何、basic6枚)。
- 同サンプルデッキ同士で相手(Shu Kato)に3ターン負けした試合あり=下位帯はサンプル提出者の海。

### 上位帯(1000〜1180)のメタ観測(TOP1の直近10試合=20デッキ)
- Alakazam/Dudunsparce 11、Mega Kangaskhan ex 4、Crustle/Munkidori 2、Mega Starmie ex 1、他。
- **全デッキ共通: Buddy-Buddy Poffin 3-4 / basic 10枚以上 / ドロー・サーチサポ10枚超**。
- リーダーボード実勢: 4,524チーム、TOP 1171.5、中位帯520前後(レーティング分布は初提出時から圧縮された模様)。

### エンジン検査(§7-7回収)
- **同名カード(ID違い)を合計6枚入れたデッキをbattle_startが受理した** → エンジンは同名4枚制限を強制しない。ルール違反回避のため、デッキ構築では「エンジンが通す=合法」とせず同名合計≤4を自前で守ること。

### Starmieデッキ探索(2026-07-08, v1パイロット固定, 300-400戦/セル)
デッキ: decks/starmie_v0/v1/v2.csv(v0=basic4枚, v1=+Dunsparce4で basic8枚, v2=v1+Dudunsparce2−Wally's2)

| 指標 | sample | starmie_v0 | starmie_v1 | starmie_v2 |
|---|---|---|---|---|
| vs random+sample | 88.3% | 99.0% | 94.7% | 86.3% |
| vs Alakazamゲージ | 56.7% | 80.7% | 73.3% | 73.3%(donk計では67.8/73.2%帯) |
| vs Grimmsnarlゲージ | 74.0% | 80.3% | 70.7% | 69.7% |
| vs lunasolアグロ(v1操縦) | 59.7% | 71.7% | 71.3% | 59.5% |
| vs sample(v1操縦) | – | 56.3% | 43.3% | 51.3% |
| **早期敗北率(≤5ターン) vs lunasol** | 16.8% | 12.2% | **6.5%** | 19.2% |
| 早期敗北率 vs Alakazamゲージ | 10.0% | 3.5% | **1.8%** | 11.8% |
| マリガン率(計算値) | 46% | 60% | 35% | 33% |

- 新ゲージ: decks/lunasol_v0.csv = 実ラダーで我々を2ターンで倒したLeonArdoVの闘デッキ(Mega Lucario/Solrock)をリプレイから抽出。
- 新計測器: donk_meter.py(早期敗北率)。**ローカルゲージは序盤圧が無く「事故らない価値」を過小評価する**——basic増量は全勝率ゲージで悪化に見えるが早期敗北率は半減する。
- v2の教訓: v1パイロットは能力常時YESのため**Run Away Drawが盤面自壊ループになる**(D9のPowerful Hand自壊と同型)。Dudunsparceはパイロット改修後まで凍結。
- bench.py に `--deck` フラグ追加(自陣デッキ差し替え)。

## 外部公開コード「Pokemon steel」(plamen06) の実測評価(2026-07-08)

出典: kaggle.com/code/plamen06/pokemon-steel (公開・Apache2.0・Public 820.6 / Best 958.4)。
中身: Archaludon ex + Cinderace メタル・テンポ専用の1300行ヒューリスティック + Kaggle安全なビームサーチ(search_begin/search_step を try/except で包みセグフォ回避、時間予算2.0s)。
特徴: 相手アーキタイプ判定(crustle/hop/starmie/lucario/alakazam/generic)＋相手の最大打点推定(Alakazam Powerful Handの床/天井まで実装)＋マッチ別override。パイロットはArchaludonデッキ専用に密結合(＝汎用パイロットではない)。

実測(steelのデッキ+パイロットを我々側に置き、各200戦):

| 相手 | steel勝率 | 参考: 我々starmie_v1(v1操縦) |
|---|---|---|
| ランダム | 98.0% | 94.7% |
| Alakazamゲージ | 93.5% | 73.3% |
| Grimmsnarlゲージ | 97.5% | 70.7% |
| lunasolアグロ(v1操縦) | 90.5% | 71.3% |
| **我々のstarmie_v1(v1操縦)と直接対決** | **89.5%** | (=10.5%) |

- **steelは我々の現状最高デッキ+パイロットに直接対決で89.5%勝つ**。ゲージ非依存の決定的な差。Kaggle 820 vs 420 とも整合。クラッシュ0(約1000戦)。
- **前セッションD9「Archaludon却下(対Alakazam 40%)」は誤りと確定**。同じArchaludonデッキがパイロット次第で対Alakazam 93.5%。デッキではなくパイロットが問題だった、という監査結論を第三者コードが裏付け。
- steel_agent.py / decks/steel_archaludon.csv として保存(検証専用・提出tarには入れない)。

## メタ再観測 (2026-07-14, 184エピソード, LB上位15チーム+rank50/100/200/400/800の直近10戦)

7/8観測(TOP1の20デッキ)の検証。取得: LeaderboardService/GetLeaderboard → ListEpisodes → replay.json×184。

### サンプルチーム本人のデッキ(rank順)
1,2,5,14,15,50位=Alakazam / 3,8,11,13位=Kangaskhan+Crustle / 4,12,800位=Grimmsnarl / 6位=Dragapult / 7位=TR Mewtwo(Spidops) / **9位=Mega Starmie+Dusknoir(1130.9)** / 10位=Crustle+Cinderace / 100位=Garchomp / 200位=GreatTusk / 400位=Lucario

### 対戦相手アーキタイプ分布
| アーキタイプ | top15帯(n=147) | mid帯50-200(n=30) | low帯400-800(n=20) |
|---|---|---|---|
| Alakazam/Dudunsparce | **42.2%** | 26.7% | 20.0% |
| Grimmsnarl/Munkidori | **16.3%** | 13.3% | 10.0% |
| Kangaskhan ex(+Crustle) | 11.6% | – | – |
| TR Mewtwo(Spidops) | 7.5% | 3.3% | 5.0% |
| Archaludon | 0.7% | **23.3%** | **25.0%** |
| Lucario / Dragapult / Starmie / Garchomp | 各4-5% | 各3-10% | 各10-15% |

### 7/8観測の訂正
- Alakazam支配は正しい(42%)。Kangaskhan+Crustleも上位柱で正しい(2位グループ)。
- **見落とし: Grimmsnarl/Munkidoriが相手シェア2位(16%)**。7/8のN=20では2件しか出ず過小評価していた。
- **帯で別のゲーム**: 我々が実際に戦う600-900帯はArchaludonが最多勢力(23-25%)でAlakazamと二強。頑健性マトリクスはtop15メタとmid/low帯メタの両方で測る必要がある。
- Mega Starmieは上位で実在(9位)。メンバーのデッキ線は「一旦」としては妥当な筋。

### ゲージ用に実リスト保存(verification/decks/)
meta_alakazam / meta_kangaskhan_crustle / meta_grimmsnarl_munkidori / meta_starmie_dusknoir / meta_tr_mewtwo (各_2026-07-14.csv、最頻出の実60枚)

## メンバーagent弱点マップ (2026-07-15, mega-starmie-ex-deck@origin, 200戦/セル)

環境: verification/bench.py。エンジンは旧リポジトリからコピー。**全セルCRASH=0**。速度 ~925ms/戦（v1の~9msの100倍、要調査）。

| セル | 相手 | 勝率 | 95%CI | 読み方 |
|---|---|---|---|---|
| A | random | 95.5% | 91.7〜97.6 | 健全 |
| B | Alakazamゲージ(専用AI+v0) | 63.5% | 56.6〜69.9 | v1の63.0%と同等 |
| C | Grimmsnarlゲージ(専用AI+v0) | 65.5% | 58.7〜71.7 | v1の75.3%より低い |
| D | 実メタAlakazam(ミラー操縦) | 94.0% | 89.8〜96.5 | 過大評価(操縦者の壁) |
| E | 実メタKangaskhan+Crustle(ミラー) | **82.5%** | 76.6〜87.1 | ミラー4セル中の最低=**相対的に苦手** |
| F | 実メタGrimmsnarl(ミラー) | 94.5% | 90.4〜96.9 | 過大評価 |
| G | 実メタTR Mewtwo(ミラー) | 98.0% | 95.0〜99.2 | 過大評価 |
| H | **実メタStarmie/Dusknoir(rank9型・ミラー)** | **36.5%** | 30.1〜43.4 | **同一パイロット=公平なデッキ比較。負け越し** |

### H（同型対決）の含意 — デッキ差分（メンバー型 vs rank9型）
- メンバー型: Starmie+**Mega Froslass ex/Munkidori 悪スプラッシュ**（悪エネ3・Risky Ruins4・Boss's Orders3）= アタッカー2本立て
- rank9型: **水単Starmie厚積み**(Staryu4/Starmie4?)+Dusknoirライン+Ignition Energy4+ドローサポ厚(Wally's Compassion3/Hilda2/Judge3/Carmine1)+Pokégear/Ultra Ball
- 同じagentで36.5% vs 63.5% → **60枚の差だけで27pt**。rank9型は「1本目を太く+徹底したドロー一貫性」、メンバー型は2本目に枠を割いて主線が細い。
- 次アクション候補: メンバー型を段階的にrank9型へ寄せてA/B（①ドローサポ入替のみ ②Froslass線→Dusknoir線 ③全量）。

### その他の観測
- E(82.5%)がミラー系で突出して低い → Kangaskhan ex(HP300 basic)+Mist/Spiky Energyは実弱点の可能性。専用ゲージ化して確認する価値あり。
- 残る疑問: 925ms/戦の重さ。手番制限時間との余裕を/submission-check系で確認要。

## エンジン同梱探索API PoC (2026-07-15, 穴A可否検証)

エンジンには**エージェント用探索APIが公式に組み込み済み**（Export.cpp/Search.h/Api.h、ソースはKaggle Dataページ ptcg_engine、ライセンス=大会期間内利用限定のためリポジトリ非同梱・scratchpad保管）。

- 仕組み: 毎観測に `obs["search_begin_input"]`（相手非公開情報を消去したシリアライズ盤面base64）が**本番・ローカル共に既に入っている**（kaggle-environments cabt.py L187で確認）。`AgentStart()`→`SearchBegin(盤面, 自分の山札/サイド・相手の山札/サイド/手札の推定=決定化, enemyActive, manualCoin)`→`SearchStep(searchId, 選択)`で分岐状態を無限に展開。`shuffle`で再決定化、`SearchRelease/SearchEnd`で解放。**両プレイヤーの手を自分で選んで進められる**＝MCTS/expectimaxの土台そのもの。
- PoC実測（member機、ターン2起点、決定化1本）: **23,666 SearchSteps/秒**（JSON往復込み）。ランダムプレイアウトは約200step/本→**約100プレイアウト/秒**。手番600秒のovergage予算に対し余裕が桁で違う。
- 検証スクリプト: scratchpad/poc_search.py（determinize: 自分の未見カード→山札+サイドに分割 / 相手の60枚仮定→サイド+手札+山札に分割）。
- 含意: 相手デッキの推定（アーキタイプ判定→60枚仮定）が探索の入力になる → メタ観測(7/14)の実リスト5種がそのまま推定辞書になる。

## エンジンのデッキ検証の訂正 (2026-07-15)

7/8の「エンジンは同名4枚制限を強制しない(6枚受理)」は**誤り**。現バイナリで再検証: 同名7枚デッキは battle_start が **errorType=2 で拒否**。ソース(Api.h ApiBattleStart)も同名≤4(基本エネ除く)・ACE SPEC≤1・basic≥1体を強制している。7/8のテストは「同名と思った2枚のIDが実は別名だった」可能性が高い。→ CLAUDE.mdの「デッキ合法性は自前で守る」は維持しつつ、エンジンも防波堤になることを確認。

## v2探索パイロット 初回計測 (2026-07-15, src/input/datasets/decks/v2-search, サンプルデッキ)

構成: v1ヒューリスティック + 探索層（決定化2本 × 候補手全展開(重複群約) × **v1誘導ロールアウト**(相手の返し=turn+2まで) × 静的評価。**v1の選択を評価マージン120以上で上回るときだけ上書き**。予算0.6s/手、実測 平均7.6ms・最大49ms/手）。

| 相手 | v1 | **v2** | 差 |
|---|---|---|---|
| random (100戦) | 91.0% | **94.0%** (CI 87.5〜97.2) | +3.0 |
| **v1直接対決 (200戦)** | 50% | **58.5%** (CI 51.6〜65.1) | **+8.5、CI下限51.6%で有意** |
| Alakazamゲージ (200戦) | 63.0% | 62.5% | ±0 |
| Grimmsnarlゲージ (200戦) | 75.3% | 75.5% | ±0 |

全セルCRASH=0。教訓: 深さ1+静的評価は失敗した（vs random 25%、評価がフラット+手札項の歪みで先頭手を機械選択）。**ロールアウトで相手の返しまで見る+「v1に対する明確な改善時のみ上書き」構造**にした途端に有意な改善。ゲージ戦が横ばいなのは、上書きが効く局面がスクリプト相手だと勝敗に直結しにくいためとみられる（要深掘り: 上書き発生率のログ取り）。

### v2 提出前ゲート (2026-07-15, 対戦相手条件を揃えた最終比較)

| 項目 | v1 | v2 | 判定 |
|---|---|---|---|
| vs random (100-300戦) | 91.0% | 94.0% | ✓ |
| Alakazamゲージ (200-300戦) | 63.0% | 62.5% | ✓ 同等 |
| Grimmsnarlゲージ (200-300戦) | 75.3% | 75.5% | ✓ |
| vs v1操縦lunasol (300-400戦) | 59.7% (bench) / 58.5% (donk計) | 57.7% (bench) / **65.8%** (donk計) | ✓ 同等以上 |
| donk_meter 早期敗北率 (400戦, 相手=v1lunasol) | 14.8% | 15.5% | ✓ 悪化なし(CI内) |
| CRASH | 0 | 0 | ✓ |
| デッキ合法性 | – | サンプルデッキ無変更・同名≤4 | ✓ |

**ゲート判定: PASS**。注意: 当初のlunasol比較(53.7% vs 59.7%)は相手操縦者が違い(v2操縦lunasol vs v1操縦lunasol)非対称だった。条件を揃えると同等以上。v1直接対決58.5-61.0%と合わせ、v2は提出可の状態。

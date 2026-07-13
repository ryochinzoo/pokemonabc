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

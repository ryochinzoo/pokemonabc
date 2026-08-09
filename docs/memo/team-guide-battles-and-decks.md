# チーム案内 — 外部の実物と戦わせる方法・デッキ全一覧・資料の場所(2026-08-09更新、りょーちん向け)

> 目的: ①セルフ対戦ではない「他チームの実物」との対戦のやり方をコピペで動く形で共有
> ②リポジトリにあるデッキ全部の「なんでこれがあるの?」に答える ③見つけた記事・データの場所の地図
> ④NotebookLMに入れて「デッキ相談AI」として使う手順。

---

## 1. セルフ対戦ではない相手と戦わせる方法

### 大原則(実測で確定した罠)

- **自分のパイロット同士のセルフ対戦で勝率を測ると、本物の相手より+8〜+62pt甘く出る。**
  勝率の判定は必ず下の「外部実物ゲージ」か本番ラダーで。セルフ対戦は動作確認用。
  ここで言う「セルフ対戦」は**自分のパイロットが相手のデッキも動かすこと**を指す。
  相手のデッキリストを60枚完璧にコピーしても、動かすのが我々のコードなら同じ罠にかかる
  (D61の三段分解: 自作P×自作D 96.0% → 自作P×実物D 89.0% → **本物P×実物D 57.3%**。
  **デッキ差7.0pt / 操縦者差31.7pt = 操縦者が4.5倍効く**)。
- **族内ゲージの数値を採否判定に混ぜない。** 2026-08-08に実際に事故った —
  合成の重みに族内オーロンゲを19.3%混ぜていたため「デッキ差分は実質ゼロ(+0.04pt)」が
  族外のみの再計算で**−2.70pt(符号反転)**になった。
- **ベンチは同時に1本だけ**(並列で走らせると数字が汚れるのに、エラーは出ない=気づけない)。
- 安全ゲート: **vs random ≥96%** を先に確認(攻撃的な相手は自滅バグを隠す)。
- N=200で誤差±3.5pt程度。**3pt差をN=200で語らない**。本番レートは同一エージェントでも±150〜400ぶれる。
- **`env $vars cmd` と書かない。** zsh はクォートしない `$var` を単語分割しないので
  **先頭のトグルしか適用されないのに数値は正常に見える**。`env A=1 B=1 cmd` と直書きする。

### やり方(コピペ用)

自分のデッキのディレクトリ(main.py+deck.csv+cg/がある場所)に入って bench.py を呼ぶ:

```bash
cd src/input/datasets/decks/mega-starmie-ex-deck   # ←自分のデッキdirに変える
REPO=/Users/yujiinoue/Documents/products/pokemonabc

# まず安全ゲート(vs random 120戦)
python3 $REPO/verification/bench.py 120

# 外部実物との対戦(例: フーディンゲージ、200戦)
python3 $REPO/verification/bench.py 200 \
  --opponent $REPO/verification/reference/alakazam_ryota_agent.py \
  --opponent-deck $REPO/verification/decks/ryota_alakazam_2026-07-05.csv
```

### 使える外部実物ゲージ一覧(すべて検証専用・提出禁止)

**2026-08-09 更新**: オーロンゲの族外ゲージを新設し、CEWの重みを再較正した(覆域 66.6%→85.9%)。
下表の「CEW重み」は現在の800-1099帯の実遭遇シェア。正典は `verification/cew.py`。

| 相手 | agent | デッキcsv | CEW重み | 信頼度 |
|---|---|---|---|---|
| フーディン | `reference/alakazam_ryota_agent.py` | `decks/ryota_alakazam_2026-07-05.csv` | **0.3399** | **較正済み**(本番実測と差5.6pt) |
| オーロンゲ | `reference/tetsutani_grimmsnarl_agent.py` | `reference/tetsutani_grimmsnarl/deck.csv` | **0.2247** | **2026-08-09新設**。公開notebookに base64 で畳まれていた実装を展開 |
| イワパレス | `reference/soutasakurai_crustle_agent.py` | `decks/soutasakurai_crustle_2026-08-04.csv` | **0.1572** | 公開強豪の実装 |
| メガルカリオ | `reference/makthanithin_lucario_agent.py` | `decks/makthanithin_lucario_2026-08-05.csv` | **0.1537** | **較正済み**(本番のルカリオ勢2勝11敗=15.4%を14.0%で再現) |
| ブリジュラス | `reference/tomato_archaludon_agent.py` | `decks/tomato_archaludon_2026-07-22.csv` | **0.1246** | 実ラダー系譜(60/60一致×2) |
| ブリジュラス(副) | `reference/steel_agent.py` | `decks/steel_archaludon.csv` | — | 実時間依存のため**直列必須**。CEWからは外れた |
| ドラパルト | `reference/official_dragapult_agent.py` | `decks/official_dragapult_2026-07-22.csv` | — | 運営サンプル。**CEWから外れた**(現在の帯シェア2.1%) |
| ユキノオー | `reference/official_abomasnow_agent.py` | `decks/official_abomasnow_2026-07-21.csv` | — | 運営サンプル。**CEWから外れた**(帯のcensusに出現しない) |
| ~~メガルカリオ(旧)~~ | `reference/official_lucario_agent.py` | — | — | **勝率判定に使用禁止**(本物より+45pt甘いと実証済み。動作確認のみ可) |
| ~~オーロンゲ(族内)~~ | `reference/grimmsnarl_infamily_agent.py` | `decks/meta_grimmsnarl_800_2026-08-03.csv` | — | **族内=スクリーニング専用**。採否判定に混ぜない(2026-08-08に混入事故あり) |

- 相手のデッキも自由に差し替え可: `verification/decks/meta_*_800_2026-08-03.csv` に実ラダー最頻出デッキ11本
  (全部エンジン受理確認済み。中身の日本語一覧は `docs-for-you/notebooklm-sources/deck-catalog-2026-08-06.md`)。
- 提出前は `/submission-check`(check.py)と conformance.py を必ず通す(壊れた提出で枠を溶かさない)。

---

## 2. デッキディレクトリ全一覧 — 「なんでこのデッキがあるの?」

場所: `src/input/datasets/decks/`(**30ディレクトリ**、2026-08-09時点)。
**王者(starmie-aggro)と凍結物(deckswap-tarountula / -pilotfix)は直接触らない**(実験は複製ディレクトリで)。

> **なぜこんなに多いのか**: `md5 -q */main.py | sort | uniq -c` で数えると 30本が **16グループ**になる。
> **`main.py` がバイト同一のコピーが 12本(王者)+4本(pilotfix)**。これは散らかりではなく実験設計で、
> **デッキ実験は `main.py` を1バイトも変えずに `deck.csv` だけ差し替え、パイロット実験はその逆**をやる
> (＝変数を1個だけ動かす)。残り14本が固有ロジック。
> **デッキdirに `*.jsonl` やログを置かないこと** — ここは提出時にそのまま tar される。

| ディレクトリ | 何者か | 状態 |
|---|---|---|
| **starmie-aggro** | **現王者**。メガスターミー、確定レート783/793.9 | 使用中・**変更禁止** |
| **mega-starmie-ex-deck** | **りょーちんのデッキ**(`src/`で我々が書いていない唯一のもの) | りょーちん管理 |
| **deckswap-tarountula-pilotfix** | **いまラダーに載っている腕**(ref 55308422)。P9とdeck.csvバイト同一・操縦者だけ修理版 | 稼働中・**凍結** |
| **deckswap-tarountula** | **P9プローブ提出物**(タマンチュラ、本番で53戦実測済み) | 提出済み・**凍結** |
| deckswap-tarountula-sweep | ↑のバイト同一コピー(凍結物を触らず測定するため) | 測定用 |
| deckswap-tarountula-toolfix | pilotfix + どうぐ専用の貼り先分岐 | 実験済み |
| **deckswap-tarountula-v2** | **現役の作業場**。3修理(costfix / I1 / VETO、各独立トグル)実装済み・**掃引は未実行** | 作業中 |
| deckswap-v2-control | ↑の対照(変更前 `ce8aef63` を復元)。介入なしの腕 | 作業中 |
| **deckcand-{alakazam, archaludon, lucario}** | **実ラダー最頻出デッキを「我々が持つ」側に置いた候補**(2026-08-09新設)。操縦者はpilotfixとバイト同一＝デッキ軸だけを見る | 作業中 |
| deckswap-grimmsnarl | デッキ入替実験の腕(オーロンゲ、パイロット無修理=35%) | 実験済み・対照として保持 |
| deckswap-grimmsnarl-abilityfix | **パイロット修理実験**(エネ配分修理で35→55%、+13〜20pt実証) | 実験済み・修理束の原本 |
| deckswap-crustle | デッキ入替実験の腕(イワパレス) | 実験済み |
| deckswap-crustle-probe | イワパレス敗因解剖用の計装コピー(負け21戦全部=自分の山札切れ、と特定) | 解剖済み |
| deckswap-garchomp | デッキ入替実験の腕(ガブリアス、51.5% vs フーディンゲージ) | 実験済み |
| deckswap-honchkrow | **人間の大会デッキ輸入テスト**(ドンカラス。vs random 52.5%で即死→原因特定済み: 打点がテキストにしか無くパイロットが0点評価) | 失敗記録として保持 |
| deckswap-honchkrow-probe | ↑の観測用コピー(トレーサ入り) | 解剖済み |
| starmie-clockguard | P1プローブ提出物(時間切れガード版) | 提出済み・実績あり |
| starmie-widthprobe | P2プローブ提出物(探索幅の実験版) | 提出済み |
| starmie-belt-e1 / starmie-boss-e2 | 過去のカード実験(E1ベルト/E2ボス指令) | 実験終了 |
| starmie-retreatcost / starmie-aggro-evalablate | 過去のパイロット実験(リトリート規則/評価関数の分解) | 実験終了 |
| starmie-aggro-metadecks | 相手デッキ推定辞書の実験 | 実験終了 |
| alakazam-e3 | E3実験(フーディンの山切れ修理→安全ゲートで棄却) | 棄却記録として保持 |
| lucario-calib / dragapult-calib | 較正用の提出物(公式デッキ×王者パイロット。練習相手の信頼度を本番で検証するため) | 提出済み |
| v2-search / v3-mcts | 旧世代パイロット(v3は棄却。研究比較用) | アーカイブ |
| *.log / *.sh / *.done | 掃引の実行ドライバと記録(自動測定の痕跡) | 消してもよい類 |

---

## 3. 見つけた記事・データの場所(地図)

| 場所 | 中身 |
|---|---|
| `docs/memo/handover-*.md`(**日付が最新のもの**) | **いまの現在地**。ここから読むのが一番速い |
| `docs/directory-guide.html` | **リポジトリ全体の構造ガイド**(どのファイルが何をしているか/対戦の呼び出し連鎖/なぜセルフ対戦をやめたか) |
| `docs/memo/data.md` | **数値の正典**。全実測がN・CI付きで日付順に(5,400行超) |
| `docs/memo/decisions.md` | 意思決定ログ D1〜(何を・なぜ決めたか)。冒頭に「最小読了セット」のナビあり |
| `verification/cew.py` | **採否判定の重みの正典**(2026-08-09 T3再較正。README.mdより新しい) |
| `docs/memo/team-report-2026-08-05.md` / `.html` | **りょーちん向け総括**(背景/外部調査/デッキ選定の経緯/本番53戦の中身/相談事項) |
| `docs/memo/agents-2026-08-03/` | 一次調査9本: 公開ノートブック291件の実行分類(corpus-B)/ Kaggle外部偵察(scout-A)/ 人間大会×AIメタ(cross-human-ai)/ メタ=コピー可視性の検証(ood-imitability)/ デッキ表現力(deck-expressiveness)/ 本番53戦の解剖(p9-replay-mining)/ Discord偵察 / 検証の赤チーム(red-team-D)/ 根拠の再検証 |
| `docs/memo/prior-art-audit-2026-08-02.md` | 公開ノートブック291件の精読監査 |
| `docs/memo/external-ingestion-audit-2026-08-02.md` | 掲示板(Sim/Strategy)の一次情報監査 |
| `docs/memo/playbook.md` | チームの運用規範(測定規律・バイアス対策) |
| `verification/decks/meta_*_800_2026-08-03.csv` | 実ラダー最頻出デッキ11本(本番の実物) |
| `verification/reference/` | 外部実物ゲージ本体+`_inbox/`(公開ノートブック291件の生体) |
| `replay_analysis/` | 計器群+`ladder_scout/`(本番全譜のデータ湖)+`eps55236642/`(P9の54試合全譜) |
| `docs-for-you/notebooklm-sources/` | **NotebookLM投入用の厳選セット**(下記) |

---

## 4. NotebookLMを「デッキ相談AI」にする手順

### 入れる素材(`docs-for-you/notebooklm-sources/` に集約済み)

1. `deck-catalog-2026-08-06.md` — 我々の2本+メタ11本の**全60枚を日本語カード名で**一覧化
2. `team-report-2026-08-05.md` — 総括(メタ分析・本番53戦の中身・弱点分析)
3. `p9-replay-mining.md` — 本番53戦の詳細解剖(どのカードで負けたか)
4. `cross-human-ai.md` — 人間の大会デッキとAIメタの比較
5. `ood-imitability.md` — 「メタはコピーで決まる」の検証データ
6. `discord-recon-2026-08-05.md` — コミュニティの議論
7. `team-guide-battles-and-decks.md` — 本ファイル(デッキ一覧と測定方法)
8. (任意・重い) `data.md` — 数値の正典。根拠を深掘りしたい時用

### 状態(2026-08-06): **稼働中**

- NotebookLMは **Gemini Notebook** に改名された(notebook.google.com)。CLIは対応版 v0.8.0 に更新済み・認証済み。
- **デッキ相談ノートブックは投入済みで使える**:
  https://notebook.google.com/notebook/41482aa3-d790-4002-a096-d24a3894cd50
  (上記8ファイル+ゆうじが入れた競技ページ2件=10ソース、全てインデックス済み)
- 追加の資料を入れる時: `notebooklm use 41482aa3` してから `notebooklm source add <ファイル>`。
  Web UIへのドラッグ&ドロップでも同じ。

### 質問の例(この用途のために素材を組んである)

- 「我々のタマンチュラデッキ(デッキカタログ参照)で、**外していいカード**はどれ? 本番53戦の解剖結果を根拠に」
- 「メガルカリオ系に2勝11敗の弱点を、**デッキ側の入れ替えで**改善する案は? メタデッキのカタログと比較して」
- 「ロケット団のミュウツーexを削る場合のリスクは? 代わりに入れる候補は?」
- 「人間の大会で使われていてAIラダーにいないカードで、我々のデッキに合いそうなものは?」

**注意**: NotebookLMの答えは入れた資料の範囲でのアイデア出し。**採用判断は必ず較正済みゲージでの実測**(§1)を通す。数値の真偽は `data.md` が正典。

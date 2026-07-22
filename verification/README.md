# verification — 提出前にローカルで強さを測る道具箱

エンジンは約7〜12ms/戦。**300戦がタダ**なのに、Kaggleの提出枠は1日5回しかない。
「本番でA/Bテスト」をやめて、ここで測ってから提出するための道具一式。

## 前提

各ツールは **デッキディレクトリ**（`main.py` + `deck.csv` + `cg/` が揃った場所）から
実行する。**現行の王者＝`src/input/datasets/decks/starmie-aggro/`**（D34）。
`decks/mega-starmie-ex-deck/` は**チームメイトのデッキ**なので、自分の測定対象として
`cd` しないこと（取り違えても数値は普通に出るので無言で通る。D35: りょーちんの
ディレクトリは変更もしない）。
`cg/` のバイナリ（libcg.dylib 等）は gitignore なので、無い場合は
Kaggle の sample_submission からコピーすること。

## 使い方（デッキディレクトリで実行）

```bash
cd src/input/datasets/decks/starmie-aggro

# 1) 対ランダム勝率（95%信頼区間つき）
python3 ../../../../../verification/bench.py 300

# 2) メタ再現ゲージ（上位型2種 + 実ラダー由来アグロ）
python3 ../../../../../verification/bench.py 300 \
  --opponent ../../../../../verification/gauges/alakazam_agent.py \
  --opponent-deck ../../../../../verification/decks/alakazam_v0.csv
python3 ../../../../../verification/bench.py 300 \
  --opponent ../../../../../verification/gauges/grimmsnarl_agent.py \
  --opponent-deck ../../../../../verification/decks/grimmsnarl_v0.csv
python3 ../../../../../verification/bench.py 300 \
  --opponent main.py \
  --opponent-deck ../../../../../verification/decks/lunasol_v0.csv

# 3) 早期敗北率（ドンク＝序盤即死の割合。実ラダーの負け8戦中5戦がこれだった）
python3 ../../../../../verification/donk_meter.py 400 deck.csv \
  main.py ../../../../../verification/decks/lunasol_v0.csv

# 4) 自陣デッキだけ差し替えて測る
python3 ../../../../../verification/bench.py 300 --deck ../../../../../verification/decks/starmie_v1.csv
```

## 提出前ゲート（2026-07-21改訂、decisions.md D29準拠）

**重要な前提（D27）**: 自前パイロットが相手デッキを操縦する「族内ゲージ」は、相手操縦者と
我々の操縦者の実力差に比例して勝率を+8〜+62pt過大評価する（steel相手+62pt / 公式Lucario
相手+41pt / りょーちんagent相手+8pt、実測）。**採否の判定は必ず較正済みの族外ゲージで行う。**

1. **効果量の判定 = 較正済み遭遇加重合成指標（CEW）**（D29、D35改訂）。族外ゲージ4種
   (Lucario49.0/Archaludon35.3/Dragapult9.8/Abomasnow5.9%)を実ラダー遭遇率で加重した1指標。
   **基準線41.03%**(D38、4反復×Neyman計3,200戦、プールSE 0.82pt)、
   **測定はNeyman配分 合計N=3,200 (Lucario1712/Archaludon1024/Dragapult272/Abomasnow192)**、
   閾値+2pt。この構成の実効=誤採用率4.2%/真+2.5ptへの検出力67%（D38検定力計算。
   一様800/セルは同戦数で誤採用6.4%に劣る）。CIは `cew_stats.py`。計算は `cew.py` で行う。族内ゲージ（Alakazam/
   Grimmsnarl型・自パイロット操縦）は**スクリーニング用途のみ**で採否の主指標にしない。
   ※CEWの重みは現在の帯の実遭遇分布に紐づく。帯が変われば再計算する（playbook §2/§7 T3）。
2. **正当性の検査**（効果量ではない、独立に残す）: CRASH=0 / vs random ≥96% / `check.py`。
   ※donk_meterやゲージ勝率を独立ゲートとして課さない（D29: 独立4条件で真に効果ゼロでも
   65.1%が「退行」と誤検出され良い変更を捨てる）。
3. デッキは**同名カード合計4枚以下**（エンジンは**4枚制限は**検査しない！5枚でも通る）。
   ただし D37 で判明: エンジンは**別種のデッキエラーは検査する**
   (`battle_start` の `start_data.errorPlayer >= 0` → 本番 `INVALID` = 即敗北)。
   「エンジンは何も見ない」と一般化しないこと。
4. **本番ランナー適合検査** = `conformance.py`（D37新設）。**agent() のデッキ返却経路は
   他のどのツールでも実行されない**（selfplay.py は deck.csv から直接 `battle_start` に
   渡すため）。壊れていても全数値は正常に出て本番だけ全敗するので、提出前に必ず通す:
   ```
   cd src/input/datasets/decks/starmie-aggro
   python3 ../../../../../verification/conformance.py     # → CONFORMANCE=PASS
   ```
5. 最終順位は「直近2提出」＝**直近2枠は常にベスト2本**を維持する

## 中身

| パス | 何 |
|---|---|
| `selfplay.py` | 対戦ハーネス（席入替つき、`run_match`/`run_series`） |
| `bench.py` | 勝率+信頼区間。`--deck` `--opponent` `--opponent-deck` `--baseline` |
| `donk_meter.py` | 5ターン以内の早期敗北率 |
| `gauges/` | Alakazam型 / Grimmsnarl型の専用スクリプトAI |
| `decks/` | ゲージ用・実験用デッキ（lunasol_v0 = 実ラダーで2ターン負けした相手の完コピ） |
| `reference/steel_agent.py` | 公開コード「Pokemon steel」(Apache2.0, 820点)。**検証専用・提出禁止**（Strategy部門は独自性審査） |
| `reference/official_lucario_agent.py` + `decks/official_lucario_2026-07-21.csv` | ホスト公式サンプル(kiyotah)。**実ラダーの相手と60/60枚一致=実環境の再現**。CEWの主ゲージ。**検証専用・提出禁止** |
| `reference/official_abomasnow_agent.py` + `decks/official_abomasnow_2026-07-21.csv` | ホスト公式サンプル(kiyotah)。CEW成分。**検証専用・提出禁止** |
| `reference/tomato_archaludon_agent.py` + `decks/tomato_archaludon_2026-07-22.csv` | 公開notebook(TOMATOMATO)。**実ラダーArchaludonの正体=この系譜**(60/60一致×2、D34)。CEWのArchaludon成分の優先参照。ライセンス未確認=再配布・派生禁止。**検証専用・提出禁止** |
| `reference/official_dragapult_agent.py` + `decks/official_dragapult_2026-07-22.csv` | ホスト公式サンプル(kiyotah)。CEW第4成分(D35)。**検証専用・提出禁止** |
| `data/` | カードDB（EN/JP CSV、replay_analysis からも参照） |

## 関連

- `../replay_analysis/` — Kaggle実対戦リプレイの取得・解析（負け方の一次情報）
  - リプレイJSON: `https://www.kaggle.com/competitions/episodes/{episodeId}/replay.json`（認証不要）
- `../docs/memo/` — 意思決定ログ・実測データ・引き継ぎ（Strategyレポートの素材）

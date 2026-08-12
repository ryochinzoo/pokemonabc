# 道具の早見表（逆引き）

**目的**: 「何が知りたいか」から1手でコマンドに辿り着く。探索させないための索引。
道具は全部で60本以上あるが、**常設で使うのは20本弱**。残りは使い捨ての検死で、
走らせるものではなく**読むもの**（下の §5）。

最終更新 2026-08-11。罠と規律は `CLAUDE.md` の「External data」節を先に読むこと。

---

## 1. 早見表 — 知りたいこと → コマンド

### 我々の現在地

| 知りたいこと | コマンド | 返るもの |
|---|---|---|
| **今のチャンピオンはどれ** | `python3 replay_analysis/kaggle_cli.py our-submissions` | 自チーム全提出のID・スコア・日時。**セッション開始時に必ず1回** |
| 順位表の上位 | `python3 replay_analysis/kaggle_cli.py leaderboard 50` | 順位・チームID・スコア |
| 特定チームの稼働提出 | `python3 replay_analysis/kaggle_cli.py team-submissions <teamId>` | 提出IDとスコア |

### 本番（Kaggleのラダー）で何が起きたか

| 知りたいこと | コマンド | 返るもの |
|---|---|---|
| **提出が本番で落ちてないか / 遅くないか** | `agent_logs.py fetch <提出ID>` → `agent_logs.py report` | 1決定ごとの思考時間、stderr。**1試合3.9KB**。自チーム限定 |
| 提出の検死（予測と実測のズレ） | `probe_autopsy.py <提出ID> <epsDir> <H1予測%>` | T1判定・タイミング・CRASH検査 |
| 誰と当たって勝ったか | `kaggle_gate.py list <提出ID>` | 対面の提出ID・報酬・レート増減 |
| 1試合を人が読む形で | `battle_report.py <replay.json> --seat 0 --out x.md` | 各決定点の盤面＋**選べた手の全列挙**＋選んだ手 |
| 1試合の出来事を時系列で | `trace_replay.py <replay.json>` | ドロー/プレイ/攻撃の物語 |
| ミスを数える | `misplay_scan.py <epsDir>`（デッキdirから） | リーサル見逃し・手札リセットの空撃ち |

### 相手・メタ

| 知りたいこと | コマンド | 返るもの |
|---|---|---|
| **上位ラダーは何のデッキか** | `ladder_census.py seed 100` → `mine` → `report` | 上位105チームの60枚・アーキタイプ・勝率。**~75分** |
| 帯別の遭遇分布・対面行列 | `band_meta_census.py` | 自スコア帯ごとの相手構成と勝率（追加DLなし） |
| 遭遇した相手を広く浅く | `ladder_scout.py expand 60 20` | デッキ×スコア×勝敗（生リプレイを溜めない） |
| デッキがどのアーキタイプか | `band_meta_census.classify_a/classify_b` を import | 2系統で相互検証。不一致は不一致として出す |

### 我々のAIの強さ（ローカル）

| 知りたいこと | コマンド | 返るもの |
|---|---|---|
| **採否の判定** | `cew.py --alakazam .. --grimmsnarl .. --crustle .. --lucario .. --archaludon ..` | 合成指標1本。**判定はこれだけで行う** |
| 上に信頼区間を付ける | `cew_stats.py --reps "勝/戦,..."` | CEW ± CI、過分散χ² |
| 1対面の勝率 | `bench.py N --opponent <agent.py> --opponent-deck <deck.csv>` | 勝率＋95%CI＋CRASH数 |
| 同上を並列で | `parbench.py N --workers 8 ...` | 同上。**安全条件を満たさないと自動で拒否** |
| 早期敗北率 | `donk_meter.py N our_deck.csv opp.py opp_deck.csv` | 5ターン以内に負けた率 |
| 変更が無影響か（純関数層） | `equiv_probe.py` | 勝率でなく**決定の一致率**。数分で済む |

### 提出前

| 知りたいこと | コマンド |
|---|---|
| 本番ランナーに適合するか | `conformance.py`（デッキdirから） |
| デッキが合法か | `conformance.py` が `battle_start().errorType` を見る。`2`=枚数違反 / `3`=たね無し / `4`=ACE SPEC違反 |
| 提出物の総点検 | `/submission-check` スキル |

### 資料をNotebookLMへ

| 知りたいこと | コマンド |
|---|---|
| 湖 → .md → 投入 | `make_digest.py --push`（差し替え式・冪等） |
| 生成だけ（外部送信しない） | `make_digest.py` |

---

## 2. ローカルでバトルを回す正しいやり方

**必ずデッキディレクトリから実行する。** `cg/`(エンジン) と `main.py` は
そこにしか無く、`bench.py` は `sys.path` に cwd を入れて解決している。

```bash
cd src/input/datasets/decks/<デッキ名>
python3 ../../../../../verification/bench.py 200 \
  --opponent      ../../../../../verification/reference/alakazam_ryota_agent.py \
  --opponent-deck ../../../../../verification/decks/ryota_alakazam_2026-07-05.csv
```

守るべき3点:

1. **族外ゲージで測る。** 自前パイロットに相手デッキを操縦させる「族内ゲージ」は
   **+8〜+62pt 過大評価**する（D27）。族内は篩い分け専用で、**引用禁止**。
2. **CPUは直列。** 我々の `main.py` 自身が壁時計に依存するので、ゲージ側が非依存でも
   測定は直列（D51）。並列は `parbench.py` が安全条件を検査して許可した時だけ。
3. **判定指標は1本。** CEW だけで判断する。4条件を並べると、真に効果ゼロの変更でも
   **65.1%の確率でどれかが「退行」と誤検出**され、良い変更を系統的に捨てる（D29）。

**対戦ログを残したいとき**（既定オフ）:

```python
import os
from cg.api import LogType
OUT = os.path.expanduser("~/Documents/products/pokemonabc-runs/mylogs/run.jsonl")
selfplay.run_series(200, deck, deck, our_agent, opp_agent, record=OUT,
                    record_types={LogType.ATTACK, LogType.HP_CHANGE, LogType.RESULT})
```

- **デッキdir配下には書けない**（提出tarに混入するので `ValueError` で拒否される）
- **`record_types` で必ず絞る**。全種別だと 81KB/戦＝12,048戦で **1.00GB**

---

## 3. 現行のCEW（正典は `verification/cew.py`）

| ゲージ | 重み | agent |
|---|---|---|
| alakazam | 0.3399 | `reference/alakazam_ryota_agent.py` |
| grimmsnarl | 0.2247 | `reference/tetsutani_grimmsnarl_agent.py` |
| crustle | 0.1572 | `reference/soutasakurai_crustle_agent.py` |
| lucario | 0.1537 | `reference/makthanithin_lucario_agent.py` |
| archaludon | 0.1246 | `reference/tomato_archaludon_agent.py` |

覆域 **85.9%** / 基準線 **59.70**（実ラダーに載っている腕）。

> ⚠️ **`verification/README.md` の重み表は古い**（4ゲージ・覆域66.6%・基準線66.75）。
> 2026-08-09 の T3再較正でオーロンゲが加わって5ゲージになった。**`cew.py` が正典。**
> 手計算しないこと（重み1つの付け忘れで採否が反転する）。

`reference/official_lucario_agent.py` は **+45pt 甘いので使わない**（D61）。

---

## 4. データはどこに溜まっているか

| 場所 | 中身 | git |
|---|---|---|
| `replay_analysis/lake/rival_decks.jsonl` | 上位105チーム 311提出の60枚 | 追跡 |
| `replay_analysis/lake/agentlogs.jsonl` | 本番の思考時間・stderr | 追跡 |
| `replay_analysis/eps<提出ID>/` | 生リプレイ（1本2〜24MB） | **除外**（9.5GB） |
| `replay_analysis/ladder_scout/` | 斥候の成果（decks.jsonl / panel.jsonl） | **除外** |
| `verification/data/EN_Card_Data.csv` | カードDB 2,022枚 | 追跡 |
| `../pokemonabc-runs/` | 掃引のログ・ローカル対戦記録 | リポジトリ外 |

---

## 5. 使い捨て（走らせない。**手口を読む**ためのもの）

特定の仮説のために書かれ、役目を終えたスクリプト。似た調査をするとき
**書き方の手本**として読む。そのまま走らせても意味のある結果は出ない。

`autopsy_2026-07-29.py` / `autopsy_54961048.py` / `calib_verdict_54943911.py` /
`alakazam_autopsy.py` / `alakazam_deck_match.py` / `floor_autopsy.py` / `p9_mining.py` /
`mechanism_autopsy.py` / `shutout_anatomy.py` / `prize_race.py` / `semantic_check.py` /
`damage_pairing_diff.py` / `damage_placement_audit.py` / `decision_census.py` /
`ev_crosscheck.py` / `incumbency.py` / `novelty_decay.py` / `notebook_exposure.py` /
`episode_arrival.py` / `t1_verdict.py` / `classify_replays.py` / `extract_decks.py` /
`extract_meta_decks.py` / `action_vocabulary.py` / `field_ev.py` /
`verification/` 側の `*_probe.py` 各種・`*_aggregate.py` 各種

**`*_aggregate.py` は例外**: 対応する事前登録の掃引を回したときだけ使う
（`v2final_aggregate.py` / `mastercontrol_aggregate.py` / `aqua_aggregate.py`）。

---

## 6. 外部APIを叩くときの絶対規則

**`kaggle_gate.py` / `kaggle_cli.py` 以外から Kaggle を叩かない。**
直書き `curl` も、直の `kaggle` コマンドも禁止。8秒間隔・429で4時間停止を共有している。

2026-08-04 に並列取得で **IP単位のブロック**を踏み、ログイン済みWebUIの試合履歴まで
丸1日以上巻き込んだ。詳細は playbook §8。

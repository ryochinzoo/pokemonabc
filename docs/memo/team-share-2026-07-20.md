# チーム共有 2026-07-20 — 現状と「自分のデッキを10分で測る」クイックスタート

りょーちん向けの共有。詳細な経緯は `decisions.md`(D1〜D21)、数値は `data.md`、
運用の型は `playbook.md` に全部ある。ここは入口だけ。

## いまの提出状態(7/20時点)

- アクティブ2枠: **starmie-aggro**(新・ドスクラインout変種×探索パイロットv2.1c) + v2.1c×旧Starmie
- 今日の大きい発見: **ドスクライン(攻撃不能の6枠)はAI操縦だと死荷重**。抜いて
  Mega Starmie 4枚目+水2+Dawn3にしただけで全8対面改善・加重+15.7pt(data.md 7/20節)。
  Starmie本家のりょーちんの見解を聞きたい。
- パイロットの中身: v1ヒューリスティック(貪欲+文脈別選択) + エンジン内蔵探索API
  (SearchBegin/SearchStep)による「対標本比較・保守的上書き」の2層。凝ったMCTSは
  作って測って**棄却した**(理由はD18-19、レポートの柱の一つ)。

## 自分のデッキ/エージェントを10分で測る

デッキディレクトリ(main.py+deck.csv+cg/)の中から:

```bash
# 1) 対ランダム勝率(必須ゲート。自滅系バグの検出器 — これで2回大事故を未然に防いだ)
python3 ../../../../../verification/bench.py 300

# 2) メタ再現(相手デッキ+ゲージAI。--deck で自分側のデッキ差し替えも可)
python3 ../../../../../verification/bench.py 200 \
  --opponent ../../../../../verification/gauges/alakazam_agent.py \
  --opponent-deck ../../../../../verification/decks/alakazam_v0.csv

# 3) 族外較正(公開steelエージェント。自前同士のベンチは近親交配になる — data.md 7/20参照)
python3 ../../../../../verification/bench.py 200 \
  --opponent ../../../../../verification/reference/steel_agent.py \
  --opponent-deck ../../../../../verification/decks/steel_archaludon.csv

# 4) 早期敗北率
python3 ../../../../../verification/donk_meter.py 400 deck.csv main.py \
  ../../../../../verification/decks/lunasol_v0.csv
```

提出前は必ず: 上のゲート + `python3 .claude/skills/submission-check/scripts/check.py
--submission <デッキdir>`(リポジトリルートから、PYTHONPATH=verification)。

## ハマりどころ(実体験)

- **ctypesのNULL**: エンジン戻り値を`string_at`する前にNoneチェック。しないと
  try/exceptで捕まらないセグフォルト=対局没収(提出済み版で見つけて修正した)。
- **vs randomを飛ばさない**: 攻撃的な相手だけで測ると自滅系バグ(山札切れ・エネ詰み)が
  隠れる。
- **ベンチはCPU直列**: 時間予算制の探索が入ると並列ベンチは数字が壊れる。
- **N=200で3pt差を語らない**(SE≈3.5pt)。5pt差を見たいならN≈800。

## 提案(今度話したい)

最終ランキングは**直近2提出のみ**。8月中旬以降の枠運用をチームで決めておきたい:
最終2枠=検証済みベスト2本、提出前ゲートを互いに通す、締切前の凍結日を決める、など。

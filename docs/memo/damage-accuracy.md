# `_estimate_damage` の予測精度（実リプレイ測定）

> 測定専用。`main.py` は一切変更していない。
> 再実行: `cd src/input/datasets/decks/starmie-aggro && python3 ../../../../../replay_analysis/damage_accuracy.py`

- 対象: 56 戦（読めなかった/自チーム不明: 0）
- ログ上の自分の ATTACK イベント: **240** 件
- 決定点と突合できた攻撃: **186** 件（突合率 77.5%）
- 予測が実測と完全一致: **163 / 186 = 87.6%**

## 不一致の原因別内訳

| 分類 | 件数 | 割合 |
|---|---:|---:|
| 一致 | 163 | 87.6% |
| スタジアム未読（Full Metal Lab） | 21 | 11.3% |
| 無効化（出所未特定） | 2 | 1.1% |

## 不一致の attackId 別頻度（上位20）

| attackId | ワザ名 | 件数 | 予測→実測(例) | damage欄 | 分類 |
|---|---|---:|---|---:|---|
| 1487 | Jetting Blow | 23 | 120 → 0 | 120 | 無効化（出所未特定） |

## 不一致ワザの効果文

- **[1487] Jetting Blow** (damage欄=120, 23件)
  - `This attack also does 50 damage to 1 of your opponent’s Benched Pokémon. (Don’t apply Weakness and Resistance for Benched Pokémon.)`

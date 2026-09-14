"""オーロンゲ(Marnie's Grimmsnarl ex)対面の**族外**ゲージ — 2026-08-09 新設。

## これは何か

公開Kaggleノートブック `tetsutani~grimmsnarl-ex-damage-transfer-control` に
**base64 で埋め込まれていた**方策バンドルを展開したもの。実体は
`reference/tetsutani_grimmsnarl/` に置き、本ファイルは bench.py 用の薄いラッパー。

- `main.py` / `strategic_policy.py` / `policy_features.py` + 380本の木のアンサンブル
- import は標準ライブラリと `cg` のみ(numpy/sklearn なし)
- **実時間依存なし**(`time.`/`perf_counter`/`monotonic`/`deadline` の参照ゼロ)
  → ゲージ側は壁時計非依存。直列が要るのは**我々の**パイロットが実時間予算制だから。
- 同梱 pickle は `pickletools` で検査済み: 3,937 opcode 中
  **GLOBAL / REDUCE / INST / BUILD が0** = 純データ。任意コード実行の経路はない。

## ★D64 の訂正

D64(2026-08-04)は「公開ノートブック291件を実際に実行して Grimmsnarl 操縦者0件」を根拠に
**「Grimmsnarlゲージは公開コードから構築不能」で正式クローズ**していた。これは誤りだった。
分類器は `def agent` / `%%writefile` を探しており、**base64 に畳まれた実装は静的にも実行的にも
見えなかった**。D64 自身が記録した「静的解析の偽陽性率100%」と同型の盲点である。

意味: 800-1099帯で **19.3%** を占める対面に、初めて族外ゲージが立つ。
CEW の覆域は **66.6% → 85.9%**。族内ゲージ `grimmsnarl_infamily_agent.py`
(我々の操縦者が相手を回す=+8〜+62pt甘い、D27)を判定から追い出せる。

## 取り扱い(重要)

**ライセンス表記がノートブックに無い。** `tomato_archaludon_agent.py` と同じ扱いとする:
**検証専用 — 対戦相手としてのみ使用。再配布・派生・提出はすべて禁止。**
Strategy部門は独創性を見るので、この実装を写した提出は行わない(CLAUDE.md)。

使い方(他のゲージと同じ):
    cd src/input/datasets/decks/<deckdir>
    python3 ../../../../../verification/bench.py 300 \
      --opponent      ../../../../../verification/reference/tetsutani_grimmsnarl_agent.py \
      --opponent-deck ../../../../../verification/reference/tetsutani_grimmsnarl/deck.csv
"""
import importlib.util
import sys
from pathlib import Path

_BUNDLE = Path(__file__).resolve().parent / "tetsutani_grimmsnarl"

# D61 の手順: cwd 依存を絶対パス化する。
# 原版のままだと policy_features が `BASE/EN_Card_Data.csv` を探しに行くが、
# BASE は __file__ 基準なので、カードDBをバンドル側に置いておけば cwd に依存しない
# (これを怠ると**相手が我々の山札を自分の山と誤読する** = D59/台帳#31 と同型の汚染)。
if str(_BUNDLE) not in sys.path:
    sys.path.insert(0, str(_BUNDLE))


def _load():
    spec = importlib.util.spec_from_file_location("_tetsutani_grimmsnarl_main",
                                                  _BUNDLE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_MOD = _load()
DECK_CSV = _BUNDLE / "deck.csv"


def agent(obs_dict):
    return _MOD.agent(obs_dict)

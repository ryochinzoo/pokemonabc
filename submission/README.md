# 最終提出物(凍結バイト)

Kaggle「The Pokémon Company - PTCG AI Battle Challenge」に **Team Yser** が最後に出した 2 本のエージェントを、試作デッキ群(`src/input/datasets/decks/`、41 本)から分離して置いています。
中身は提出時のバイトそのもので、`SHA256SUMS` で照合できます。エンジン本体(`cg/*.so`, `*.dylib`, `*.dll`)は運営配布物なので含めていません(Kaggle の sample_submission から `cg/` にコピーすると動きます)。

| ディレクトリ | 提出 | 最終レート | デッキ / 操縦者 | 作業コピー |
|---|---|---|---|---|
| `aggro-yuji-55558557/` | Simulation 提出 **55558557**(2026-08-17、ゆうじ) | **656.7**(2,898 / 6,807 位) | 水単 Mega Starmie ex(Boss's Orders ×3)/ 貪欲規則 14 本 + 門付きエンジン先読み 0.6 s | `src/input/datasets/decks/starmie-aqua-bosslogic/`(main.py md5 b67466a9、deck.csv d2fd11c0) |
| `srhp-ryochin-55554191/` | Simulation 提出 **55554191**(2026-08-17、りょーちん) | **533.7** | Mega Starmie ex 核 + 防御・位置取り分岐 / 公開情報に限った短期計画(SRHP) | `src/input/datasets/decks/mega-starmie-ex-deck-final/`(origin/main 077445c を複製。提出 ID との対応はりょーちん確認) |

- Strategy 部門の Writeup(提出済み 2026-09-13): "Aggro or Abstain? When Exact Reasoning Meets Tempo in Pokémon TCG" — https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy/writeups/new-writeup-1788949252000
- 提出用 tar の作り方: `cd submission/<dir> && cp <sample_submission>/cg/*.{so,dylib,dll} cg/ && tar czf ../../submission.tar.gz main.py deck.csv cg`
- 各エージェントの中身と測定の経緯: `docs/memo/decisions.md`、`docs/memo/writeup-v1-fulldraft.md`(Aggro 側の記事草稿 v8.4)

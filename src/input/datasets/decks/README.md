# 試したデッキ・操縦者の作業ディレクトリ(実験場)

**最終提出物はここではなく `submission/` にあります**(2026-09-15、マージ時に分離)。
このディレクトリは開発中に試した 41 本のデッキ×操縦者の作業コピーで、各ディレクトリが `main.py` + `deck.csv` + `cg/`(エンジンの Python ラッパ。バイナリは gitignore)を持ちます。
どれを何のために試し、何が測れたかは `docs/memo/decisions.md`(D1〜D88)と `docs/memo/data.md` に日付順で残っています。
`*_driver.sh` / `*.log` / `*.done` は掃引(スイープ)の実行スクリプトと記録です。

| ディレクトリ | 初回コミット | 最終コミット | 中身 | 備考 |
|---|---|---|---|---|
| `alakazam-e3` | 2026-07-24 | 2026-07-24 | main.py deck.csv |  |
| `deckcand-alakazam` | 2026-08-09 | 2026-08-13 | main.py deck.csv |  |
| `deckcand-archaludon` | 2026-08-09 | 2026-08-13 | main.py deck.csv |  |
| `deckcand-lucario` | 2026-08-09 | 2026-08-13 | main.py deck.csv |  |
| `deckcand-v2deck` | 2026-08-09 | 2026-08-09 | main.py deck.csv |  |
| `deckswap-crustle` | 2026-08-03 | 2026-08-03 | main.py deck.csv |  |
| `deckswap-crustle-probe` | 2026-08-04 | 2026-08-04 | main.py deck.csv |  |
| `deckswap-garchomp` | 2026-08-03 | 2026-08-03 | main.py deck.csv |  |
| `deckswap-grimmsnarl` | 2026-08-03 | 2026-08-03 | main.py deck.csv |  |
| `deckswap-grimmsnarl-abilityfix` | 2026-08-04 | 2026-08-04 | main.py deck.csv |  |
| `deckswap-honchkrow` | 2026-08-04 | 2026-08-04 | main.py deck.csv |  |
| `deckswap-honchkrow-probe` | 2026-08-04 | 2026-08-04 | main.py deck.csv |  |
| `deckswap-tarountula` | 2026-08-03 | 2026-08-03 | main.py deck.csv |  |
| `deckswap-tarountula-pilotfix` | 2026-08-06 | 2026-08-09 | main.py deck.csv |  |
| `deckswap-tarountula-sweep` | 2026-08-04 | 2026-08-04 | main.py deck.csv |  |
| `deckswap-tarountula-toolfix` | 2026-08-09 | 2026-08-13 | main.py deck.csv |  |
| `deckswap-tarountula-v2` | 2026-08-06 | 2026-08-09 | main.py deck.csv |  |
| `deckswap-v2-control` | 2026-08-09 | 2026-08-13 | main.py deck.csv |  |
| `dragapult-calib` | 2026-07-29 | 2026-07-29 | main.py deck.csv |  |
| `lucario-calib` | 2026-07-24 | 2026-07-24 | main.py deck.csv |  |
| `mega-starmie-ex-deck` | 2026-08-02 | 2026-08-02 | main.py deck.csv |  |
| `mega-starmie-ex-deck-ct` | 2026-07-22 | 2026-08-04 | main.py deck.csv |  |
| `mega-starmie-ex-deck-final` | 2026-08-05 | 2026-08-10 | main.py deck.csv | **最終提出(SRHP, りょーちん)の作業コピー** → `submission/srhp-ryochin-55554191/` |
| `starmie-aggro` | 2026-07-19 | 2026-07-24 | main.py deck.csv |  |
| `starmie-aggro-evalablate` | 2026-08-02 | 2026-08-02 | main.py deck.csv |  |
| `starmie-aggro-metadecks` | 2026-07-29 | 2026-07-29 | main.py deck.csv |  |
| `starmie-aqua` | 2026-08-13 | 2026-08-13 | main.py deck.csv |  |
| `starmie-aqua-boss` | 2026-09-14 | 2026-09-14 | main.py deck.csv |  |
| `starmie-aqua-bosslogic` | 2026-09-14 | 2026-09-14 | main.py deck.csv | **最終提出(Aggro, 55558557)の作業コピー** → `submission/aggro-yuji-55558557/` |
| `starmie-aqua-bosslogic-efix` | 2026-09-14 | 2026-09-14 | main.py deck.csv |  |
| `starmie-aqua-endguard` | 2026-09-14 | 2026-09-14 | main.py deck.csv |  |
| `starmie-aqua-endguard-boss3` | 2026-09-14 | 2026-09-14 | main.py deck.csv |  |
| `starmie-aqua-pad` | 2026-09-14 | 2026-09-14 | main.py deck.csv |  |
| `starmie-belt-e1` | 2026-07-23 | 2026-07-24 | main.py deck.csv |  |
| `starmie-boss-e2` | 2026-07-24 | 2026-07-24 | main.py deck.csv |  |
| `starmie-clockguard` | 2026-08-02 | 2026-08-02 | main.py deck.csv |  |
| `starmie-mastercontrol` | 2026-08-13 | 2026-08-13 | main.py deck.csv |  |
| `starmie-retreatcost` | 2026-08-02 | 2026-08-02 | main.py deck.csv |  |
| `starmie-widthprobe` | 2026-08-02 | 2026-08-02 | main.py deck.csv |  |
| `v2-search` | 2026-07-15 | 2026-07-19 | main.py deck.csv |  |
| `v3-mcts` | 2026-07-19 | 2026-07-21 | main.py deck.csv |  |

# 斥候B(コーパス) — 公開ノートブック291件の `agent()` 実行掃引 (2026-08-03深夜〜08-04)

> 任務: 前任者の静的解析C4(「Grimmsnarl 操縦者は291件中0件」)を**実行で**決定的に検証する。
> 方針は「確認しにいくな、潰すつもりで探せ」。
> データ正典: `verification/data/corpus_exec_2026-08-03.jsonl`(291行、1ノートブック=1行)。
> 対戦ゼロ(エンジンの battle 系APIは構造的に遮断して実行した。§5.1)。

---

## 0. 結論(先出し)

**C4 は生き残った — ただし文言を強くした形で置き換える。**

> **「291件の公開ノートブックの `agent()` を全件実行した範囲で、Grimmsnarl を自デッキとして
> 返した操縦者は 0件**(実行成功135件中0件)。**それどころか、実行で得た135本の60枚デッキに
> Grimmsnarl 系カード(ID 646 Impidimp / 647 Morgrem / 648 Marnie's Grimmsnarl ex)は
> 1枚も入っていない**(135×60=8,100枚中0枚)。」

- 静的には **grimmsnarl の60枚リストを含むノートブックが16件**あったが、**実行すると16件全部が
  alakazam(14)または crustle(2)を返した** = 全部が相手モデル/決定化テンプレの辞書。
  **§3.2 の罠(`_GRIMM_IDS` 事件)は孤立事故ではなく、公開コーパスの標準的な書き方**だった(§3)。
- 検出力の対照2本つき: 実ラダー抽出の grimmsnarl デッキを両分類器が正しく grimmsnarl と判定し、
  我々自身の main.py を同一ハーネスに通すと starmie と判定される(§2.3)。**「0件」は盲目ではない。**
- **ただし全称命題にはできない**: 取得不能の21ref(§6.3)のうち17refが恒久欠測で、その中に
  **`prvsiyan/ptcg-rmy-grimmsnarl-replay-hybrid-v1`** という「Grimmsnarl リプレイ模倣」を名乗る
  ノートブックが含まれる(404=削除済み、再取得を今回も試して失敗)。
  したがって正確な主張は **「公開で現存する範囲に Grimmsnarl 操縦者は0件」** まで。
- **Crustle 操縦者は22件**(distinct デッキ8種)おり、最高 LB 1208(soutasakurai)を含む。
  ゲージ候補は §4。

**含意(主砲Aへの接続)**: 実ラダー800-1099帯で Grimmsnarl はシェア19.3%(2位)なのに、
公開ノートブックの操縦者は0件。**「模倣可能性がメタを決める」仮説の教師データ側は、
少なくとも公開ノートブック経路では供給されていない**。供給源はリプレイ模倣(削除された
prvsiyan の1本が示唆)か非公開コードのはず — 8位 Jake の証言「データが大量にあるから
Grimmsnarl が一番作りやすい」の「データ」は**リプレイであってコードではない**、と絞り込める。

---

## 1. アーキタイプ分布 — 「公開コーパスが操縦できるデッキの集合」

実行成功 135件(distinct notebook)。分類は B(SUMI公開ID署名)優先、無ければ A(カード名規則)。

| アーキタイプ | distinct notebooks | distinct 60枚デッキ | 備考 |
|---|---|---|---|
| lucario | 31 | 6 | 最大勢力。romanrozen 950系のコピー網 |
| alakazam | 25 | 6 | prvsiyan/llccqq624/jazivxt 系列 |
| **crustle** | **22** | **8** | **soutasakurai 1208 の同一60枚を8ノートブックが共有** |
| archaludon | 7 | 4 | |
| abomasnow | 6 | 3 | |
| dudunsparce | 6 | 3 | naoto714 の実験系 |
| dragapult | 4 | 3 | |
| garchomp | 2 | 2 | |
| Kangaskhan | 2 | 1 | A のみ検出(B に署名なし) |
| TR Mewtwo | 2 | 1 | 同上 |
| gardevoir | 1 | 1 | パス書換で救済(yashjakhar99) |
| **grimmsnarl** | **0** | **0** | **カード単位でも0枚** |
| tarountula | 0 | 0 | **P9(deckswap-tarountula)に公開の先行操縦者は無い** |
| starmie | 0 | 0 | 我々の型の公開操縦者も0(対照実験では検出可能を確認済み) |
| 未分類 | 27 | 15 | 大半が naoto714 の実験デッキ(下記) |
| **計** | **135** | **53** | |

- 未分類27の内訳(先頭ポケモン): Archen×4, Bulbasaur(Mega Venusaur)×3, Zacian ex×2, Piplup(Empoleon)×2,
  Eevee(Glaceon)×2, Cinderace(Ogerpon)×2, Iron Thorns ex×2, Magcargo ex×2, Gastly(Mega Gengar)×2,
  Slowpoke(Slowking)×2, TR Kangaskhan ex×2, Wiglett(Wugtrio)×2。
- **naoto714 一人で ok 135件中46件**。distinct デッキ53種のうち相当数が彼の1人実験室
  (「デッキ多様性の公開供給源」はほぼ1人)。
- 分類器の相互検証: 両方判定97件で**不一致0**、Aのみ4(Kangaskhan/TR Mewtwo)、Bのみ7(dudunsparce系)、
  両方不能27。census(B優先)の方針をそのまま踏襲して問題なし。
  副産物: **A(RULES)には tarountula 規則が無く**、実ラダー tarountula デッキを TR Mewtwo と誤答する
  (B が正答するので census 出力は無事。`band_meta_census.py` の RULES に将来1行追加推奨)。
- おまけの発見: 実行135本中、**静的に違法なデッキが2本**あった。
  `manderson240/pokemon-tcg-steel-aggro-20260625-1923` = **ACE SPEC 15枚**(errorType 4 で即 INVALID 級)、
  `sohansuriyal/the-pokemon-company` = **Mega Lucario ex 60枚**。公開コードの品質はこの程度に散っている。

---

## 2. 方法(再現可能性)

### 2.1 実行の形

- 対象: `verification/reference/_inbox/` の MANIFEST 291件全件(ipynb 282 / py 8 / irnb 1)。
- 各ノートブックを **subprocess + 全体35s(内部27s)+ セル毎 SIGALRM 10s + 専用一時cwd**
  (scratchpad 配下、§3.3 の cwd 汚染対策で deck.csv は絶対に置かない)で実行。
- `%%writefile` はハーネスが直接ファイル化(Kaggle と同一の成果物)。行頭 `!`/`%` は除去。
  セル例外はセル単位で握って続行(セル5のベンチが死んでもセル3の agent 定義は生きる)。
- agent 解決はファイル優先(main.py > その他 .py)→ ノートブック名前空間。
  **実行成功135件は全件 file 解決**(= Kaggle 提出物と同じ main.py を実行した)。
- 呼び出しは本番 interpreter と同一の deck-phase obs(`conformance.py` L42-48 の
  `{"remainingOverageTime":600, "select":None, "logs":[], "current":None, "search_begin_input":None}`)。
- **Kaggle パス写像**: `/kaggle/working` と `/kaggle_simulations/agent` を一時cwdへ書換
  (どちらも「そのノートブック自身が作るファイルの置き場」なので忠実なエミュレーション。
  発火は notes に記録、これで4件救済)。`/kaggle/input`(外部データセット)は**写像しない**
  (無いものは無いままエラーとして開示)。
- 環境: venv(numpy/pandas/matplotlib/ipython 入り、Kaggleノートブック環境に寄せた)。
  総実行壁時計 32.7秒 ×(むしろ大半が fail-fast)、nice -n 19 直列1ワーカー。

### 2.2 遮断(規律4対応)

- **エンジン**: 偽 `cg.sim` を各一時cwdに配置。`lib` は属性アクセスで即 RuntimeError
  ("ENGINE_BLOCKED")。**例外は AllCard/AllAttack のみ**、実エンジンから事前キャッシュした
  実データ JSON を返す(= EN_Card_Data.csv と同内容の静的ダンプ。battle 起動ではない。
  これが無いと import 時にカードDBを引く多数の agent が全部死ぬ)。
  さらに `ctypes.CDLL`/`PyDLL` 自体をブロック(バイナリも一時cwdに存在しない)。
  実際に `samrishb/unified-ptcg-framework-v2` が BattleStart を呼ぼうとして遮断された(記録済み)。
- **ネットワーク**: `socket.*` を全てブロック。**サブプロセス**: `subprocess.*`/`os.system`/`os.popen`
  をブロック(pip/kaggle CLI 経由の抜け道も塞ぐ)。該当は失敗として理由つき記録(10件、§6.2)。

### 2.3 検出力の対照(この掃引自体の較正)

| 対照 | 結果 |
|---|---|
| **陽性対照(grimmsnarl 検出力)**: 実ラダー抽出 `verification/decks/meta_grimmsnarl_800_2026-08-03.csv` を両分類器へ | **A=grimmsnarl / B=grimmsnarl** — 0件は分類器の盲目ではない |
| **端到端対照(ハーネス)**: 我々の starmie-aggro main.py + deck.csv を合成ノートブック化して同一ハーネスに通す | **status=ok / file:main.py / A=B=starmie / 60枚が deck.csv と多重集合一致** |

再現:
```bash
# 掃引本体(冪等・途中再開可): scratchpad/corpus_exec/{driver,runner}.py
nice -n 19 <venv>/python scratchpad/corpus_exec/driver.py   # → verification/data/corpus_exec_2026-08-03.jsonl
# 集計はこの文書の各表のインラインスクリプト(JSONLを読むだけ)
```

---

## 3. §3.2 の罠の実証 — 静的解析と実行が食い違った16件

前任者は変数名検索で6件の「Grimmsnarl?」に当たり、全部ハズレと手作業で判定した。
実行掃引は同じ現象を**網羅的に**示した:

**ソース内に grimmsnarl の完全な60枚リストを持つ16件、実行すると全部が別デッキを返す。**

| notebook | 静的候補に含まれるアーキタイプ | 実行結果 |
|---|---|---|
| prvsiyan/ptcg-ai-battle-visible-**grim-belief**-alakazam-v18/20/21/22/23 (5件) | alakazam+**grimmsnarl** | **alakazam** |
| prvsiyan/ptcg-ai-battle-visible-templates-alakazam-v19 | alakazam+crustle+**grimmsnarl** | **alakazam** |
| llccqq624/ptcg-alakazam-**marniebelief**-0723-a/-b (2件) | alakazam+**grimmsnarl** | **alakazam** |
| jazivxt/a-better-hand-alakazam-rising-tide-v21 | alakazam+crustle+**grimmsnarl** | **alakazam** |
| jazivxt/codex-sol-eclipse-alakazam ※ | alakazam+crustle+**grimmsnarl** | **alakazam** |
| ravi123a321at/codex-sol-eclipse-alakazam-20a31c ※ | 同上 | **alakazam** |
| pllinas/ptcg-alakazam-rising-tide-v21-improved | alakazam+crustle+**grimmsnarl** | **alakazam** |
| farhanabidtech786/pokemon-battle-simulation, /pokemon-company-ai-battle-challenge-simulation (2件) | alakazam+crustle+**grimmsnarl** | **alakazam** |
| raunakdey07/pok-mon-tcg-advanced-heuristic-agent | alakazam+crustle+**grimmsnarl** | **alakazam** |
| jazivxt/crustle-counter-al220-v29-agents-only | **13アーキタイプ全部入り**(相手テンプレ辞書) | **crustle** |

※ codex-sol-eclipse 2件は当初 no-agent(/kaggle/working 依存)。パス写像の救済で実行に到達した。

**教訓を規則化すると**: 公開コーパスでは「60枚リストの所持」は自デッキの証拠として
**偽陽性率が高すぎて使えない**(16/16=100%が相手モデル)。belief / template / counter / router
という語が近くにあれば、ほぼ確実に相手辞書。**自デッキは `select is None` の返り値だけが真実。**

逆向きの食い違い(静的0件なのに実行で出る)も12件あった(deck.csv 同梱型や動的構築型:
makthanithin/ptcg-mega-lucario-ex-v62、prvsiyan/ptcg-tusk-crustle-library-out-public など)。
静的解析は**両方向に**漏れる。

---

## 4. ゲージ候補ランキング

> **ライセンス注意**: 全候補とも Kaggle 既定 Apache 2.0 の**推定**であり個別表示は未確認。
> `_inbox/README.md` の規約どおり、`reference/` へ昇格させる際は出典・票数・公開日・改変点を
> ファイル冒頭に明記(雛形 `alakazam_ryota_agent.py`)。**学習・ゲージ用途に限定、提出流用は禁止**
> (steel_agent と同じ扱い)。

### ① Grimmsnarl 操縦者 — **該当0件。この枠は公開コーパスからは埋められない。**

代替案(順推奨): (a) 我々の main.py に `verification/decks/meta_grimmsnarl_800_2026-08-03.csv`
(723体中505体が完全一致の標準形)を持たせた「弱Grimmsnarlゲージ」をまず立てる — ただし
D63 の実測どおり我々の操縦では 35% 級の下手さになる点を明記して使う。
(b) リプレイ模倣で Grimmsnarl 操縦者を自作(prvsiyan が消した路線。全譜は手元にある)。

### ② Crustle 操縦者(22件から上位3件)

| 順位 | ファイル | LB根拠 | 自己完結性 / cwd依存 |
|---|---|---|---|
| 1 | `_inbox/soutasakurai~max-elo-1208-libraryout-w-crustle-great-tusk/` → 抽出済み main.py 1,256行 | **Elo 1208**(タイトル+本人注記「former submission」。現物がその強さの保証は無い — 監査 §3.1) | stdlib+cg のみ。deck.csv 読込は**相対パスだが notebook が deck.csv を書く**ので tar 抽出で完結。GreatTusk×4/Dwebble×4/Crustle×4/Terrakion。library-out 型 |
| 2 | `_inbox/prvsiyan~ptcg-844-4-observable-meta-router-visuals/` → observable_v3_submission/main.py 1,301行 | **844.4**(タイトル) | stdlib+cg のみ。**デッキ埋め込み**(deck.csv 不要)。60枚は 1208 と同一(コピー) |
| 3 | `_inbox/map1e114514~iwapalace-resource-balance-1000-fixed-agent/` → submission_files/{main,agent}.py 計1,984行 | 1000(タイトル、確度低) | stdlib+cg のみ2ファイル。**デッキ埋め込み**。60枚は独自変種(dupdeck=1) |

- 次点: `jazivxt~crustle-counter-al220-v29-agents-only`(独自60枚だが5ファイル+JSON重み2本で最も重装)。
- 注: 22件中8件は soutasakurai と**同一60枚**(コピー網)。「crustle が回せる公開操縦者」の実体は
  実質 soutasakurai 系 + naoto714 系 + map1e114514 の3系統。

### ③ LB高スコア操縦者(アーキタイプ不問、上位3件)

| 順位 | ファイル | LB根拠 | アーキタイプ | 自己完結性 |
|---|---|---|---|---|
| 1 | (②-1 と同一)soutasakurai 1208 | 1208 | crustle | 上記 |
| 2 | `_inbox/makthanithin~pokemon-tcg-ai-battle-1084-5-baseline/` → main.py 596行 | **1084.5**(タイトル) | **lucario** | stdlib+cg。deck.csv は notebook が書く |
| 3 | `_inbox/borealis27~elo-1050-rule-based-agent-matchup-tests/` → main.py 546行 | **1050**(タイトル) | **lucario** | 同上 |

- 次点: `romanrozen~strong-start-baseline-agent-v10-lb-950`(main.py 541行 = 監査 §3.1 の
  「探索が壊れていて誰も気づいていない」個体そのもの。**壊れた探索の対照ゲージ**として別価値)。
- 抽出済み実体はすべて `scratchpad/corpus_exec/work/<user~slug>/` にあり(main.py+deck.csv)。
  scratchpad はセッション揮発なので、採用決定時は `_inbox/` から再抽出するか早めに退避のこと。

---

## 5. 失敗全件開示(291 = ok 135 / no-agent 139 / error 17 / timeout 0)

### 5.1 no-agent 139件

- **104件 = ソースに `def agent(` が無い**。解析・可視化・ライター系ノートブック
  (citerne の2本、busyaprime の分析群、リプレイビューア、メタスナップショット等)。設計どおり対象外。
- **35件 = `def agent(` はあるが実行で agent に到達できず**。全件の内訳(重複理由でグループ化):
  - **サンプルフォーク族(deck.csv が添付データセット側で notebook 内に無い)9件**:
    kiyotah×4(dragapult/iono/abomasnow/lucario と**名前で**デッキは分かるが実行不能)、
    itsuki9180/japanese-language-ex、kityugin/version-8-mega-lucario-ex、mktdev/fork-sample-rule-based-mega-lucario-ex、
    mossarimossari/a-sample-rule-based-agent-dragapult-ex-deck、res1235/rule-based-agent-mega-lucario-ex-deck-very-simple
    (パス写像後も deck.csv の実体が無いため FileNotFoundError)
  - **メタスナップショット族(cell0 が subprocess でリプレイ取得→後続全滅)6件**:
    biohack44/pok-mon-tcg-ai-battle-meta-snapshot-07-july、liangwanyiudavid/同、makthanithin/同-06-29、
    kaiwalyaatulraut、rahuljiwane/pokemon-tcg-rahul-jiwane、aristophanivan/one-of-snapshot-versions
  - **/kaggle/input(他人のデータセット)必須 7件**: dedquoc、junkonno、teisnestech、ferozahmedds、
    makimakiai/ptcg-tiny-rl-to-submission-baseline-guide、samrishb/unified-ptcg-framework-v2(+BattleStart遮断)、
    faheemgurkani/dragapult-ucb1-search-baseline-establishment
  - **cg実物必須(エンジン探索して exit)3件**: arnabkarmakar/ptcg-evo-opt-v2(SystemExit)、
    jazivxt/archaludon-metal-gpu-v28-agents-only、jazivxt/rising-tide-fixed-metal-v15-reproducible-agent
    (v28/v15 は module 実行が `AttributeError: NoneType.__dict__` — cg 実物ロード前提の構造)
  - **torch 必須 1件**: siddharajkulkarni/ptgc-game(Kaggle 本番コンテナにも torch は無い — citerne)
  - **その他 9件**: busyaprime/test-your-agent-a-local-matchup-harness(パス解決 None)、
    kokinnwakashuu/ptcg-diary-day2/day4(battle_start 前提のセル構造)、
    returnofsputnik/battle-simulator...(cell3 IndentationError + deck{1,2}.py IndexError)、
    pcxxxxxx/explainable...(def agent は **markdown セル内**の説明文のみ)、
    rauffauzanrambe×2(.irnb、セルは走るが agent 未定義)、torusuke(ビューア、文字列内のみ)、
    yoikoarmor(gen0-lstm、成果物欠如 AssertionError)

### 5.2 error 17件

| 型 | 件数 | 対象 |
|---|---|---|
| **60枚契約違反: len=64** | 7 | daizen11/notebook00ad1c3e1e、inokoudai/notebookd1999b930f、sakiroki/notebooklast、shinpeinishimura×2、sotatata、zawawa1830(同一コードのコピー網。deck.csv 読めない時のフォールバック埋め込みリストが64枚。静的分類は lucario。**この main.py がそのまま提出されていれば全戦 INVALID 級**) |
| len=61 / len=0 | 3 | nursrijan(61)、godhand/en-submission-sanity-checker-0(0)、kazutamizuta(0) |
| deck.csv 外部依存(agent-call 時) | 4 | avikdas567、lucifer19/battlecore-compact-agent、ravi123a321at/battlecore-compact-agent、yakitori55(agent は動くがデッキが添付データセット。**lucifer19 のデッキだけは監査価値が残るが実行では取れない**) |
| 環境前提(NameError) | 2 | busyaprime/getting-started(find_file)、koki1231(DECK) |
| 明示的な雛形 | 1 | jaafarbk(NotImplementedError: "illustrative only") |

### 5.3 取得不能 21ref(_failed.txt) — 再取得を今回も試行、全滅

2026-08-04 に `kaggle kernels pull` を21件全部へ再試行 → **403(非公開化)13件 / 404(削除)8件**。
うち**4件は同一スラッグのミラーが取得済みで実行 ok**:
seokjeongeum/max-elo-1208-... = soutasakurai版(crustle)、.../strong-start-baseline-agent-v10-lb-950 = romanrozen版(lucario)、
.../pure-dragapult-ex-deck = stealthtechnologies版、.../mega-pokemon-reinforcement-ai-battle = rauffauzanrambe版(no-agent)。

**恒久欠測 17ref**(C4 の残余リスク、LB級を含む):
`prvsiyan/ptcg-rmy-grimmsnarl-replay-hybrid-v1`(404。**唯一の Grimmsnarl 操縦者候補だった可能性**)、
`mechi22/ptcg-1070-9-alakazam-rule-based-skeleton`(403、LB 1070.9)、
`seokjeongeum/strong-start-psychic-anti-meta-v8-lb-1100`(403、LB 1100)、
`romanrozen/strong-start-crustle-lucario-agent-v7-lb-960`(404、LB 960)、
`kokinnwakashuu/ptcg-public-915-lucario-search-baseline`(404)、
alycemiki/lucario-deck-v2、fishcat37/ptcg-v9-attention、kacchanwriting/crustle-aware-mega-lucario-ex-anti-wall、
llccqq624/ptcg-meta-a-crustle-attackfix-v1、maulikgajera、nursrijan/…advanced-heuristic-planning-agent、
pilkwang×2、prvsiyan/ptcg-ai-battle-field-audited-alakazam-v8、prvsiyan/ptcg-observable-meta-router-v1、
rahuljiwane/pokemon-tcg-rahul-jiwane7、yaminh/the-pokemon-company-ai-challenge。

### 5.4 ハーネス側の既知バイアス(正直な限界)

- venv に torch なし(Kaggle 本番コンテナ相当)。RL 系は不利に落ちるが本番でも同様。
- `%%bash` セルはスキップ(untar 等がそこにある notebook は不利)— 該当で ok を逃した形跡は cell_errors 上なし。
- `__name__ = "__corpus_nb__"` で実行(main ブロック不発)。agent 定義には影響しない設計。
- 静的スキャンは「60整数ちょうど」のみ拾う(59/61枚のリストは対象外)。

---

## 6. C4 への最終判定文(claims-ledger 用の推敲済み文言)

> **「公開ノートブック(取得できた291件)の `agent()` を全件実行した結果、Grimmsnarl を
> 自デッキとして返す操縦者は0件(実行成功135件、うち Grimmsnarl 系カードを1枚でも含むデッキも0件)。
> 静的に Grimmsnarl の60枚を持つ16件は全て相手モデル辞書で、実行では alakazam/crustle を返した。
> 検出力は陽性対照2本で較正済み。ただし公開後に削除された17refは検証不能であり、うち1件
> (prvsiyan/ptcg-rmy-grimmsnarl-replay-hybrid-v1)は名前から Grimmsnarl 操縦者だった可能性を
> 否定できない。よって主張は『現存する公開コードの範囲で0件』に限定する。」**

前任者の C4 原文(「291件中0件」)との差分: ①静的→実行に根拠を格上げ ②「カード1枚も無い」を追加
③検出力対照を追加 ④恒久欠測17refの留保を明文化(特に rmy-grimmsnarl-replay-hybrid)。

---

*斥候B / 2026-08-04 未明。実行環境と抽出済み main.py 群は
`/private/tmp/claude-501/.../scratchpad/corpus_exec/`(揮発)、データ正典は
`verification/data/corpus_exec_2026-08-03.jsonl`(永続、291行)。*

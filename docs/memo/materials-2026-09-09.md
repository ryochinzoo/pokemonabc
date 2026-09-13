# 材料の旅(2026-09-09) — 審査員・運営回答・未使用材料の棚卸しと採否

依頼(ゆうじ): 「材料を探しに旅に出よう。シミュレーション結果ほかの材料を探し、心理学をアクセントに混ぜるか、審査員を確認・理解した上で、
視野を外に広げて良いアプローチを探す」。計画 = `~/.claude/plans/simulations-strategy-wild-beaver.md`(承認済み)。
本文書は**旅の収穫の正典**。数値は data.md 2026-09-09 節と台帳 #53〜#59 に転記済み。記事側の適用は v8.2 → v8.4(writeup-v1-fulldraft.md 変更履歴、評議会 = plan-2026-09-10-council-writeup.md)。

## 1. 審査員(Kaggle Strategy 部門 Overview、9/9 実読。8/3・9/2 から変更なし)

| 審査員 | 確認できた事実 | 含意 |
|---|---|---|
| **shige** | Kaggle `shimishige`。Data Scientist at **MI**(松尾研究所)、名古屋。Competitions **Expert**(44 コンペ、順位 3,157 / 217,603)。Welcome 投稿(708588): 「thinking and experimentation」「creative approaches, interesting findings, and lessons learned」「reinforcement learning, game AI, and decision-making when dealing with unknown elements」 | Kaggler。実測・負の結果・再現性を読む。ルールベースでも「強く堅牢で設計と説明が明確」なら競争力ありと明言済み(724094) |
| **choya** | Kaggle `chome0910`。Data Scientist at MI、東京。Competitions **Master**(順位 1,797、最高 1,054)。bio「Merging from strong Kagglers is very welcome!」 | 本職の競技 Kaggler。効果量・CI・アブレーション・リーダーボードの現実を読む |
| The Pokémon Company 01/02/03 | 匿名。TPC 社内 | 実盤面・カード相互作用・デッキの意図。「ポケモンの記事か、計測学の記事か」を見る(8/17 評議会の落第条件) |

配点原文(変更なし): Model 70%(①明確さ・根拠 ②独自性・技術的健全性 ③反復安定性 ④初期状態/対面/状況的優位への非依存 ⑤成績)/ Deck 20% / Report 10%。
Overview の一文: 「Participants in middle or lower tiers of the competition can still achieve high overall scores through deep analysis, originality, and well-structured reporting.」
規模: **14,277 Entrants / 766 Participants / 695 Teams / 699 Submissions**(8/3 の 289 から倍増)。判定期間 9/14〜10/11(提出数次第で変更あり)。

## 2. 運営回答(Addison Howard = Kaggle staff、Strategy 議論板。台帳の「未確認」3件が解消)

| # | スレッド | 回答(要旨、原文は英語) | 記事への適用 |
|---|---|---|---|
| 738657 | How should we present decklists?(9/2) | **図・表の中の文字は 2,000 語に数えない**。デッキリストは画像・表・CSV 添付でよく、語数回避とはみなさない。「in-person TCG players が共有するやり方でよい」。**公式ビジュアライザのカード絵を含むスクリーンショットは使用可**。改変・新キャラ作成・所有権主張は不可 | 冒頭の対応表・§4 対面表を表に。デッキ CSV を添付。T10 盤面のスクリーンショットを Fig.12 候補に |
| 735679 | Questions on 2000 word limit(8/27) | **Media Gallery は語数外**。引用文献は Gallery に置いてよい | 出典(Kahneman & Klein / Nosek / Hearthstone AI Comp / PTCG-Bench)は Fig.1/5/9 のキャプションへ |
| 738324 | multi-word card names(9/1) | 「空白区切りの標準的な数え方」 | `wc -w` が正しい代理。全文 ≤2,000・地の文 ≤1,900 に改定 |
| 735656 | scope relative to the Aug 17 submission(8/25) | **締切後の改善・知見は記事に含めてよい**(「findings after the fact」)。性能点だけは最終提出の実績で評価。資格の下限なし | D86 の A/B/C(−3.29 / −2.42 / −2.78)は運営方針どおり §3・§6 に残す |
| 738058 | Strategy-only team(8/29〜9/5) | Sim 未参加でも提出はできるが「very very very low」。Sim 成績の重みは大きい | 我々は Sim 参加済み(Yser、2,898 位)。問題なし |
| 738925 | Team Merge Deadline(shige、9/3) | **チーム構成は Sim と同一必須**、期限 9/7、以後訂正不可 | ゆうじ確認済み(9/9): 参加済み・同一チーム |
| 739855 | [Bug?] submission overwritten(9/7、未回答) | 提出済み Writeup が空のドラフトで上書きされたとの報告 | 9/11 に器を作って一度 submit → 9/12 最終 → **9/13 に残存確認**の三段構え |
| 738911 | Where should I post writeup(9/2) | 「gold 圏外でも成功は排除されない」「多くが Strategy 用に温存している」 | 他チームの記事は締切まで読めない(変更なし) |

## 3. 他チームの校正点(読めた Writeup 5本。Strategy 一覧は非公開だが、ノートとして公開している人がいる)
`kaggle_cli.py kernels`(9/9 新設、1 リクエスト)で 8/3 以降の公開ノート 200 本を見て、Writeup 型の4本を `kernels pull` した(転記 = `external-writeups-2026-09-09/`、コード・画像は省略)。

| 出典 | 中身 | 我々との差 |
|---|---|---|
| Team Magist(Sim 229 位、公開 Writeup、37 票) | Waltheri 型パターン DB + Transformer 方策/価値 + ヒューリスティック変種 + GA デッキ探索 + 隠れ情報のモンテカルロ | **勝率・N・対面表・効果量なし** |
| **pokeso「Rule-Based Dragapult ex Agent — Solution Write-up」**(8/17、2,199 語、日英併記、表3、コード抜粋付き) | 完全ルールベース: 固定点数帯の score ladder(監査可能)、リーサル全列挙(ばら撒き 31 通り)、ダメカン配分、確率モデルは「二値ルールが実測で間違う所だけ」(自己対戦 30 試合・5,477 局面で頻度×判断反転率を測って上位のみ)、相手アーキタイプ照合+決定化探索の悲観マージン(+12/+60)、リプレイ回帰テスト約 40 本、**毎回 1,000 戦の A/B(50% 割れで停止)**、「n=100 の SE は ±5%、1,000 戦未満で結論するな」「レートの上振れを実力と混同するな、head-to-head を信じろ」 | **最も強い競合サンプル**。ただし**計測は全て自己対戦**(6.4 試合/秒)。我々の「自己対戦は +8〜+62pt 甘い/較正計器/前向き4/4/最終エージェントの負の結果」はこれと正面から対照になる。構成の明快さ・日英併記・コード抜粋は見習う点 |
| busyaprime「Last submission Aug 16. The top is still rising」(9/6、1,381 語) | 凍結後 14 日間のラダー分析: **上位の平均レートは最後のコード提出後に +67.5**、上位と中央値の差は 13.9% 拡大、日次ダンプの episode 数は「20 GiB ÷ 1譜の大きさ」でしかない(参加度ではない)、リーダーボード中央値とダンプ中央値は 476 点違う(母集団が違う) | Fig.10(9/1 スナップショット=凍結後の最終状態)の読みに整合。「凍結後の動きはマッチメイキングと分散」は我々の #47(582〜742)の解釈と同じ |
| Team Pokesonic「361st Rule-based Grimmsnarl Agent」(9/6、418 語、921.2) | デッキリスト画像+コード。分析なし | 参考のみ |
| hosikusa「Optimization of deck and agent scores using a genetic algorithm」(8/17、309 語) | GA でデッキ枚数と評価点を同時最適化(概要のみ) | 参考のみ |

→ 明日の `/council` には pokeso の転記を「強い競合サンプル」として渡し、審査員ペルソナに**並べて採点**させる。

## 4. 先行研究・心理学(一次情報で確認した引用候補と採否)

| 出典 | 確認した中身 | 採否 |
|---|---|---|
| Kahneman, D. & Klein, G. (2009). Conditions for intuitive expertise: a failure to disagree. *American Psychologist* 64(6):515–526 | 専門家直感が信頼できる条件 = (a) 規則性のある環境 (b) 素早く明確なフィードバックでの長い学習。どちらか欠けると自信ある直感は系統誤差になる | **採用**: §2 末尾に1文、Fig.9 キャプションに完全表記。ドスクライン除去の専門家予測 −5〜−10 が実測 +14.7(#7)の原理的説明 |
| Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *PNAS* 115(11):2600–2606 | 事前登録 = 予測(prediction)と事後説明(postdiction)の区別。Gelman & Loken の「forking paths」を引く | **採用**: §5 に1文、Fig.5 キャプションに完全表記 |
| PTCG-Bench (Hua et al., arXiv:2605.29653, 2026-05) | 本作(フル PTCG、5 デッキ固定)で LLM 10 種を評価。Glicko-2 で 1237〜1854。ハーネス除去で −33/−118/−115 点。「harness design has a substantial effect」 | **採用(キャプションのみ)**: Fig.1 に「LLM agents remain harness-sensitive」 |
| Hearthstone AI Competition (IEEE CIG/CoG 2018–2020; Świechowski et al. 2018 MCTS+SL、GP 評価関数+MCTS 等) | ヒューリスティック+探索のハイブリッドが上位常連。デッキ別の特化エージェント | **採用(キャプションのみ)**: Fig.1 に位置取り1文 |
| Kowalski & Miernik (2023). Summarizing Strategy Card Game AI Competition (LoCM). *IEEE CoG* | **本文を arXiv の LaTeX ソース(e-print)から読了**(9/9 追記)。「Search-based agents were the most common and won all competitions running version 1.2. All of them employed move pruning ... most of them implemented lethal move detection」。優勝 Coac = 深さ3のミニマックス+αβ+ヒューリスティック枝刈り(CEC 2019 勝率 94.22%)。相手の手札を予測した ProphetCoac は**探索時間が減って勝率が下がった**。v1.5(2022)は深層RL(ByteRL 84.41%)が席巻。組織者向けの教訓「Taming the randomness」: 同一シードを全ペアに、シードを複数回、**先後両方の席順で走らせる**(「most games are asymmetrical, giving one of the players a visible advantage」) | **採用(キャプション)**: Fig.1 の位置取り文を正確化、Fig.11 に先攻優位の注記 |
| Vieira, Tavares & Chaimowicz (2024). A Taxonomy of CCGs from a Game-Playing AI Perspective | **本文を e-print から読了**。10次元の分類。Pokémon TCG への言及は「prizes zone」と「サイドを取り切った方が勝つ」の2箇所のみ。deck-building と battling を「ordered な2部分」と定義 | 見送り(記事に足す内容なし) |
| McGrath et al. (2022). Acquisition of chess knowledge in AlphaZero. *PNAS* | 駒の価値は人間の 1-3-3-5-9 に収束し、機動力などの文脈項が後から加わる | 見送り(「価値は文脈依存」の補強にはなるが、収束の方が主結果で記事の主張と噛み合わない) |
| Sezer, Gino & Norton (2018) humblebragging | D85 で構成裁定に使用済み | 記事本文には入れない(引用すること自体が humblebrag) |

## 5. リポジトリ棚卸し — 未使用材料の採否(Explore 3本の報告を統合)

採用の原則: 最終エージェントの実測 > 対戦ゼロで今日計算できるもの > 旧デッキ/旧操縦者の値(見送り)。層S(引用禁止)は「計数」として台帳行を立ててから。

| 材料 | 出典 | 採否 | 行き先 |
|---|---|---|---|
| 先攻/後攻別勝率 57.7 / 40.1、先攻率 64.9% | **新計測** first_player_split.py | 採用 | #53、§4、Fig.11 |
| 本番マリガン率 59.9%(超幾何 60.1%)、マリガンの代償 4〜5pt | 新計測 | 採用 | #54、§2、Fig.11 |
| Mega 着地 T3 以内 勝 67.2 / 負 46.1、着地せず 1/86、完封負け 123/482 | 新計測 | 採用 | #55、§4、Fig.11 |
| 相手 initialScore 帯別勝率(中央値 651.6) | 新計測(list 結合) | 採用 | #56、§4、Fig.11 |
| ミツル 755/755 ダメージ付き Mega、エネ戻し 774 | 新計測 wally_usage.py | 採用 | #57、§2 |
| 12枚系譜(親→aqua→最終) | deck.csv 3本 | 採用 | #58、§2、Fig.9 |
| 6,807 チームのレート分布(中央値 621.5) | lake/leaderboard CSV | 採用 | #59、§1、Fig.10 |
| 専門家予測 −5〜−10 の符号逆(5件中3的中) | data.md:430-441、#7 | 採用 | §2、Fig.9 |
| 決定一致率 196/4,575 = 4.28%、例外0 | #42(未引用だった) | 採用 | §4 |
| 時間バンク最小 587 s | data.md 7396、#38 追記 | 採用 | §4 |
| 対照 55552195 の L12 違反 11/554 → 0/24,429 | #39 内 | 見送り(Fig.7 改修の時間なし。#39 に数値あり) | — |
| 帯別メタセンサス 3,333 譜 / 上位105チームの採用率 | data.md 3863-, 6195- | 見送り(旧デッキ時点) | — |
| 評価器アブレーション Δ_prize +12.25 / Δ_board +4.22 | plan-2026-07-31-evalablation | 見送り(7月王者) | — |
| 自己不整合 6.31%(探索幅で平坦) | data.md 2490- | 見送り(7月王者・語数) | — |
| サイドレース収支(L-a)・完封解剖(L-b) | prize-race.md、v5 保留分 | 見送り(55058443 時代。最終譜では #55 が代替) | — |
| coaching-canon crosscheck(「手順は有段者、抑制は空白」) | coaching-canon-crosscheck-2026-08-17.md | 見送り(語数。評議会で復活候補) | — |
| 早期収束 vs サンクコスト(council-deck-negative) | agents-2026-08-03 | 不採用(手続きの内省 = D85 で落とす側) | — |
| 支出明細図・レート推移図 | fig_rating_expenditure / timeline | 不採用(D85 裁定維持) | — |

## 6. ゆうじの回答(9/9)と工程
参加済み・同一チーム / 仮提出の器は未作成(9/11 に作成して一度 submit)/ 自筆は A のみ / 心理学は本文2箇所+キャプション出典 / りょーちん実名 OK(ryoheihara)。
工程: 9/9 v8.2(本書)→ 9/10 自筆A反映 + de-AI パス + /council 審査員ペルソナ → 9/11 反映・最終 T6・凍結・コミット・器作成 → 9/12 最終貼付 submit → 9/13 残存確認。

## 7. 未解決 → 9/9 夜に回収した分
- **Fig.12 取得済み**: `replay_analysis/visualizer_shot.py`(新設)= 手元の replay から Kaggle と同じ payload を作って公式ビジュアライザに POST → 返る HTML を `<base>` 付きで保存 → headless Chrome を CDP(標準ライブラリの WebSocket)で駆動して `#slideindex` を 98 に合わせて撮影。拡張のサイト権限は不要。`figures/png/fig_board_t10.png`、CAPTIONS 12、本文 §3 に (Fig. 12)。
- **Kaggle ログイン後の実物確認(9/9)**: Strategy のチーム = Ryohei Hara(リーダー)+ 井上祐志 の2名で Sim と同一 ✓ / Writeup は未作成(「You haven't created a writeup yet」、締切表示 Sep 14 8:59 AM GMT+9)✓。
- **Kaggle Writeup エディタの実物確認(9/9 夜、ゆうじが器を作成 → 私が編集画面を読んだ)**: 器 = `…/writeups/new-writeup-1788949252000`(DRAFT、著者 = Ryohei Hara + 井上祐志)。
  - 提出チェックリスト4件: Title(≤**80文字**、いま "New Writeup")/ Subtitle(≤**140文字**、未入力)/ Submission Track(単一トラック、自動選択済み)/ Project Description(未入力)。4件揃うまで Submit ボタンは無効。
  - Project Description は **Markdown エディタ**(ツールバー: 見出し・太字・斜体・取消線・リンク・引用・コードブロック・番号/箇条書き・**Insert Table**・**Insert Image**・YouTube・絵文字・「Markdown documentation」リンク)。**表は使える。画像も本文中に挿入できる**(Gallery だけでなく、参照箇所の直下に置ける)。語数カウンタは無い。
  - Media Gallery(画像/動画、動画は YouTube のみ)、Attachments = Project links(Add a link)+ **Files(Upload Files、100MB まで)** → デッキ CSV はここに添付。DOI opt-in チェックボックスあり。
  - 現行タイトル "What a Card Is Worth When an AI Plays It: A Mega Starmie ex Agent, Measured Against the Real Ladder" は **80 文字超過** → Title = "What a Card Is Worth When an AI Plays It"(40字)、Subtitle = "A Mega Starmie ex agent measured against the real ladder: deck, pilot and field, every number with its N and interval."(118字)の案。貼り付け時は本文先頭の "## …" タイトル行を外す。
  - 何も入力せず Cancel で閉じた(9/9 夕)。**9/9 夜に下書きを完成させた**(ゆうじ「今日中にドラフトまで」): Title "What a Card Is Worth When an AI Plays It" / Subtitle 118 字 / 本文 = v8.2 の貼り付け版(タイトル行を除く。SHA-1 `a4528ddf…` で一致を検算)+ **本文中に図 12 枚をインライン挿入**(参照段落の直下、`![Fig. N](URL)` + `*Fig. N*` ラベル)+ 末尾に「Figure captions」表(出典付き完全版、表なので語数外)/ Media Gallery に 12 枚(順序 Fig.1→12、タイトルは **255 字上限**なので短縮版)/ Files に `decklist_final_55558557.csv` 添付。状態 = **DRAFT(Ready to Submit、未提出)**。
  - 画像の入れ方(拡張は native のファイル選択を扱えない): `HTMLElement.prototype.click` を差し替えて `<input type=file>` を捕捉・DOM に残し、`file_upload` で渡す。Insert Image は 1 入力 = 1 回限り(Kaggle 側が使い捨て)なので、画像ごとに「Insert Image → Upload image from computer」を JS で押して新しい入力を捕捉した。Gallery は「Add videos or photos」→ 各スロットの Upload Image → crop ドロワーの `input type=file` に直接渡す。
  - 図の URL(googleapis の inbox 直リンク)は表示ページの `<img src>` から再取得できる(sessionStorage `figUrls` にも保存)。再貼付の手順: 本文を form_input で差し替え → 同じ JS でアンカー段落の直後に `![Fig. N](URL)` を挿入 → 末尾に captions 表 → Save Draft → 「Just checking」モーダルで **Save Draft**(Submit ではない)。挿入アンカー: Fig.1/10 = §1 段落1末、Fig.2/9 = §2 段落1末、Fig.12 = §3 段落1末、Fig.7 = §3 末、Fig.3 = §4 対面表の直後、Fig.11 = §4 開始依存段落末、Fig.4/5/6 = §5 段落1/2/3 末、Fig.8 = §6 末。
  - 9/10 未明に **v8.3 で再貼付・保存済み**(Gallery は Fig.12 を先頭 = 表紙、main.py 添付、再読み込みで検証)。残り: v8.4 の再貼付 → 9/10 りょーちんと読む → 9/11 一度 Submit → 9/12 最終 → 9/13 残存確認。
- (旧記述の訂正 9/10)Fig.12 は上記のとおり取得済み。りょーちんの表記は Kaggle byline と同じ **"Ryohei Hara"**(本文・Fig.8、本人承諾済み)。
- **9/10 未明: 下書きを v8.3 に再貼付 → 評議会 3 報告(J-MI / J-TPC / 赤チーム)→ v8.4**(`plan-2026-09-10-council-writeup.md`、D88)。v8.4 = 計器欠陥の訂正(Mega 着地は自分の2ターン目まで 92.0/74.3)、T10 に Hero's Cape と返しの Aura Jab、自己対戦の例外明記、専門家予測 → 自前の事前予測、たね実験 screening N=300、1エネ設計段落、対面の算術(#60)、先攻基準線 58.5%、§4 整合性の表、§6 最終枠の理由。t6: publish 2,157 / 地の文 1,897 / 151-0-0。
  図の再出力 = Fig.2, 4, 6, 7, 8, 9, 11。キャプション表 734 語(`CAPTIONS`)、Gallery タイトル ≤255 字(`GALLERY_TITLES`、paste ファイル末尾にも出力)。**Kaggle への v8.4 再貼付は 9/10 朝に完了**(本文 + 図 7 枚を Insert Image で再アップロード → 新 URL で本文を再組立、Gallery は該当スロットを Delete → Add Image → crop drawer → 並べ替え、タイトルは `GALLERY_TITLES`)。再読み込みで検証: Ready to Submit(未提出)、v8.4 の文言、旧文言なし、インライン 11 枚の順序、captions 表、main.py + CSV。

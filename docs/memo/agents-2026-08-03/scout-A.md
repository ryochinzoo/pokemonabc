# 斥候A(外部)報告 — Kaggle未読偵察・競争相手のwriteupの姿

観測: 2026-08-03 深夜〜08-04 未明(JST)、claude-in-chrome 実ブラウザ。読み取り専用(投稿・リアクション・ログイン操作ゼロ)。
既読前提: handover-2026-08-03-for-fable5.md §3.5 / external-ingestion-audit-2026-08-02.md §8-9。

---

## 0. 結論(3行)

1. **提出済みwriteup(289件)は1件も読めない。** 全件「Viewable at Hackathon close」で本文・タイトル・票まで完全非公開、カードは「Team 1..N」に匿名化。スタッフが公式回答で確認済み(本人以外は締切まで不可視、締切後に全公開)。**「品質の天井」は原理的に観測不能 = 全チームが盲目で書いている。**
2. **Second Round(決勝)は Strategy 部門の上位8チームだけが進む**(shige公式、732331)。Sim LB順位は「考慮要素」どまり。デッキ構築・独自性・レポート品質での選抜が明文化された。**D63のデッキ転換路線を運営が事後的に正当化した形。**
3. 監査が見落としていた大物2本を回収: **726690(運営がマッチメイキング仕様を数値で全開示)**と**724362(73票・思考時間で上位の実装を推定、「場の約半分はルールベース」)**。SUMIスレ返信には「デッキを隠すため1日で取り下げる」証言(112位)。

---

## 1. 任務1: Strategy部門 提出済みwriteupの偵察(最優先)

### 1.1 読めるか? → **読めない(これが回答)**

- https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy/writeups (2026-08-03観測)
- 全カードが `SUBMITTED / Project submitted / visibility_off / Viewable at Hackathon close`。チーム名は「Team 1」〜「Team 20」の匿名表示(ページ毎に同じラベル)。タイトル・票数・サムネイル・本文、一切なし。ページネーションは10ページ+次矢印。
- **公式裏付け**: Strategy discussion/710978「Project visibility」(anthony mbadiwe ikeme、約1ヶ月前) への Kaggle スタッフ Addison Howard の回答:
  > "Your writeup will be available to you and only you until the end of the competition, at which point all writeups will be made publicly available. You can submit your writeup, unsubmit it and continue to edit it, and resubmit it until the deadline."
- 含意:
  - **競合のwriteupから品質の天井を測る手段は存在しない**。逆に我々のも凍結まで誰にも読まれない(コピーされない)。
  - unsubmit→編集→再submitが自由 = **早く出して更新し続けるのが正解**(出し遅れリスクだけが残る)。

### 1.2 規模(公式 Participation パネル、2026-08-03)

- **11,292 Entrants / 297 Participants / 289 Teams / 289 Submissions**(8/2監査時の「約200」から289へ増加)。Sim側は6,214チーム(LBの行数合計)。
- 期限: 提出 2026-09-14 08:59 JST。Judging 9/14〜10/11。Main Track $240,000 = **8 Finalists × $30,000**+東京での対面トーナメント招待。
- 審査員: shige(MI)・choya(MI)・The Pokémon Company ×3。

### 1.3 評価ルーブリック全文(overview/evaluation、レポート設計の照準)

- **Model Score 70%**: 手法の明確さ/根拠の説明、**独自性と技術的健全性**、**繰り返し対戦・安定条件下での一貫した性能**、**特定の初期状態・マッチアップ・状況優位への過度依存の回避**、競技トラック内での性能。
- **Deck Score 20%**: デッキコンセプトの明確さと戦略との整合、**キーカードの選択と活用がゲームプランを支えているか**。
- **Report Score 10%**: 論理構成、**図表・チャート・表・視覚要素の効果的な使用**。
- Writeup ≤2000語 + Media Gallery(任意)。「You must select a Track for your Writeup in order to submit.」
- 補足: 709452「Question on Writeup Format?」(Tim Inzitari、3票) = LaTeX PDF可否の質問に**回答ゼロ(2ヶ月放置)** → Kaggle Writeup システムで書くのが安全。

---

## 2. 任務2: 8/2監査以降の新着・未読 discussion

### 2.1 Sim側の最重要: 732331「Second Round Information」(shige、8/2投稿、17票、8コメント)

https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/732331 (全文取得済み)

- **「The teams advancing to Second Round will be determined based on the results of the Strategy Category in First Round.」Strategy上位8チームが Second Round(東京・対面)でチャンピオンを決める。**辞退時は次点繰り上げ。
- 選抜は「Sim順位は考慮するが、**deck construction / originality of the proposed approach / quality of the explanations in the report** を含めて総合評価」。
- **Second Round 環境**:
  - **BO3**。マッチ内は同一デッキ・同一コード固定。**逐次対局でGame1のログをGame2で、G1+G2のログをG3で参照可能**(ゲーム間適応が公式に許される)。
  - 計算資源: **AWS p5.4xlarge 相当 = H100 80GB / 256GiB RAM / 16 vCPU**。
  - **持ち時間: 1ゲームあたり合計30分**(ゲーム間繰越なし、時間切れ=そのゲーム敗北)。
  - カード: First Round全カード+**追加カード**(Sim最終順位確定後に発表)。
  - 公式イベントサイト: https://ptcg-abc.pokemon.co.jp/
- shige返信(12h前): ①**Strategy結果はSim最終LBに影響しない** ②**Second RoundはFirst Round提出と別のデッキ・別のコードで良い**、追加制約なし ③Expanded旧カードは入れない・競技専用オリジナルカードも作らない。
- コメント欄の顔ぶれ(バッジ=当時順位): Raihan Ramadistra 2位、c-number 5位、tomo0608 5位、Jack 93位、greySnow 922位(「originality等の不定形要因で決まるのは signed off した内容と違う」と不満表明)。

**含意**: 賞金・決勝進出の全経路が writeup を通る。さらに Second Round 環境(H100・30分/ゲーム・BO3ログ参照)は**探索・適応型のルールベース/サーチ操縦者が最も価値を持つ場**。「エンジン同梱可」の公式裁定(§2.5)と合わせ、探索路線の将来価値が上がった。

### 2.2 728935「Public Notebook Sharing Deadline: August 2」(Addison Howard、19票)

- **公開ノートブック共有は 8/2 23:59 UTC で締切済み** = **291件の公開プールはこれで凍結**(以後、競技終了まで新規公開は不可)。「作業自体は妨げない。公開だけ不可」。
- Addison: 「**Bo1→Bo3への変更は今回はしない。締切後にエピソード頻度を上げる予定**」(Mikael Kerimov 23位の質問への回答)。
- razilyrazi(238位): **リプレイAPIのレート制限**で meta 分析が困難、公式データセット化の要望(myso1987 のスコア帯メタ・ノートブックを例示)。→ 732502(3h前、"Too many requests"でreplay取得も提出確認も不能)、732469(公式ビューア ptcgvis.heroz.jp が8/3 07:08 UTC頃ダウン→6h後復旧報告)と併せ、**replay.json 大量取得は現在絞られている**。replay_analysis はスロットリング前提で設計すること。

### 2.3 726690「Large systematic disparity in episode rates」(kurikuri54、18日前、10票) — **監査が完全に見落とした運営仕様開示**

https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/726690

Addison Howard(スタッフ)がマッチメイキングの内部仕様を数値付きで開示:

- **マッチメイカーは約4分毎に実行**。「必要度」= sigma(不確実性)+最終対戦からの経過時間、**これがレーティングでスケールされる**(初期600に対する相対値の乗数、**乗数だけで約8倍差**)。
- **対戦相手選択 = 自分のスコアを中心としたガウス窓上の加重ランダムサンプリング**(近いレートほど選ばれやすい)⇒ **我々の「帯」構造の生成機構が公式に確定**。
- 6/30以降、抽選の10%はランダム対戦相手。
- **エピソードに参加した全提出(相手側も)のレーティング・sigmaが更新される**。
- 全提出の最低保証は48エピソード/日(kurikuri54の実測では20-29/日の日もあり、未解決の反論あり)。
- **最終評価: レーティング・sigmaのリセットは行わない。最終評価対象は直近2提出。締切後約2週間の追加対戦で確定**(Addison、10日前)。
- kurikuri54 の統計的批判(そのまま記事の方法論素材になる質): 早期勝利→高レート→8倍のスケジューリング→速い収束、という**経路依存フィードバックループ**。「改善したエージェントが序盤の分散で沈むと、回復機会自体が減る」「参加者は『本当に弱い』『評価経路が不運』『初期帯メタに刺さっただけ』を区別できない」。
- Santiago J.(143位): **上位ほどリプレイ(=学習データ)を多く得る構造**で格差が拡大、「新しい試みを躊躇する」。

### 2.4 724362「Top players' methods, revealed by 30,000 games」(Abhyuday、101位、24日前、**73票**) — チーム未読だった高票分析

https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/724362

- 手法: **思考時間のサイドチャネル分析**(起動時間×手番毎思考時間の散布図)。手書きボット=即答/NN=起動重い+一定速度/探索=局面が複雑なほど長考。
- 主張: **「場の大半はルールベース。約半分は手書きか公開サンプルのコピー」**。大半は1手0.03秒即答、数秒考える小集団があり中間は薄い。**1位だけ異質: 重いモデル+時間フル活用 = RL+bounded search と推定。1位以外のトップは探索を使っていないように見える**。
- コメント: **李秉叡(ntumlnoob、現3位)「rule-based/searchに分類されたもののかなりの数は実際はRL/RL+search」**/ Aji Samudra(1389位)RL 1.7Mパラメータ・ロード8秒 / Belati(761位)5Mパラメータ・起動40秒・ピーク1032 / Aliy Elbekov(75位)700kモデル+不確実時のみヒューリスティック探索 / Abhyuday自身「**探索はvalue headが正確でないと効かない。不完全情報+高不確実性で難しい**」。
- 含意: ①「思考時間による実装推定」は既出(我々の行動語彙計器の新規性主張はこの先行と差別化必須) ②敵環境の実像: ルールベース多数+上位にRL、探索は希少。

### 2.5 717141「Game Engine Source Code」のコメント群(スレ本文は既知、コメントに新情報)

- **pao(24位)の質問に Addison が公式裁定: 「Code derived from, adapted from, or compiled from ptcg_engine.zip is permitted」**(submission.tar.gz への同梱可。用途は競技限定・商用不可・受賞時ライセンス供与の条件付き)⇒ **エンジンを積んだ先読み/合法手検証エージェントが合法**。SpeedSci「RLに極めて重要」。
- KawattaTaido(266位): **EffectProc.h 1149-1179 の変数シャドウイングバグ**(Team Rocket専用エネルギーの廃棄処理で内側ループの `i` が player index を隠し、`MoveCard` が activePlayerIndex を使う)→ 相手の盤面のエネルギーを誤廃棄/範囲外インデックスで**クラッシュを故意に誘発可能**(負けそうな側の暴発戦術)。ホスト未返答。
- Prema Ananda(1442位): **ローカルvisualizer出力の `selected` が1ステップ後ろにずれる off-by-one**(Export.cpp の GetBattleData が state 前進後に直列化するため。entry[0].selected は常に null、実際の選択は entry[i+1].selected)。**オフラインBC/ログ解析をする場合は必ず補正**。Kaggle 本番 replay.json に同じずれがあるかは未検証 → **我々の replay_analysis の検算項目に追加すべき**。
- **James Jean(3114位、2日前): エンジンAPIに乱数シード注入・状態export/importが無い**。アプリ側 random_seed では初期シャッフルを再現できず、**300組のA/Bペアで初期状態指紋の一致 0/300** → 彼はA/B実験を中止してホストに機構提供を要請(8/3期限指定)。ホスト未返答。⇒ **「ペアドシードA/B」はこのエンジンでは組めない**。我々のbench設計の前提と一致するが、明文の外部証拠として引用可能。

### 2.6 その他の新着(Sim)

- 731933「matching frequency in score band segmentation」(junlee789、96位): 800-1000帯はマッチ頻度が薄く、1100+は頻繁 — 体感報告。Santiago J. が 726690 を参照先として提示。
- 731739「Why is there so much grimmsnarl」(282位): 「対戦の80%がgrimmsnarl」。MioValentine(295位)「**Grimmは今のKaggle環境に適し、600-900点帯を効果的に処理でき、他デッキより安定**」⇒ 我々の帯別メタ実測(800-1099でgrimmsnarl 19.3%)と整合する定性証言。
- 731397「How do we build our decks?」(JB Bryant、105位): **105位が「既存メタの再現でなく新デッキを発見する自動デッキ探索パイプライン」を構築中と公言**(課題: 新デッキ評価の分散が大きすぎる・デッキ毎fine-tuningが高コスト)。hengck23(150位)が **FORMATION理論**を回答: 「攻撃直前の盤面配置=FORMATIONと呼び、ダメージ/HP/相手に与えるカード等でスコア化、構築に要するターン数=セットアップコストを計算。デッキとは『強く・速く・ドロー乱数に頑健な』FORMATIONを得る手段。**探索空間は思うより小さい**」。さらに **CEDEC 2026 DeNA「Pokémon TCG Pocketのバトルを支える強化学習AI技術」の一次資料URLを開示**: https://cedil.cesa.or.jp/cedil_sessions/view/3296 (+Googleスライド PDF、x.com/InvenGlobal/status/2080559209888858439)。監査で「未確認・未入手」だった文献の入手経路が判明。
- 731298「my plan on how to do RL training」(hengck23、7票): 本文図 = **「Agent swamp」構想: 公開LBのreplay.json+デッキ → LLM(chatgpt等)をPTCG戦略家として「どのカード/攻撃スタイル/勝敗理由」を抽出 → LLMをコーダーとして勝敗アクションを複製するルールベース/IL(行動クローン)エージェントを量産**し、RLの対戦相手プールにする。コメント画像には「Exact replay policy(記録された行動列を再現する相手)」「Strategy-preserving perturbed opponent(意図と優先順位を抽出し、デッキ構成・初手・ドロー順・サイド配置・先後などを摂動)」の3段システムと、Grimmsnarl実リプレイのLLM解析例。**「まだスコアには寄与していない」と本人明言**。ntumlnoob(3位)が別質問に「**3年前の4090一枚で参加可能**」と回答。
- 732502 / 732469: リプレイ取得の "Too many requests" とビューア一時停止(§2.2に統合)。
- 708588(Strategy Welcome)の新着コメント(18h前)は挨拶のみ。情報ゼロ。

### 2.7 Strategy側 全スレッド一覧(15件、ID確定)と新規読解分

708588 Welcome(既読・挨拶のみ) / 708494 Important Information(既知: deckcrafting名指し) / 708491 How to Get Started+Discord / 730338 Simulators??(6d前、0票、API文書所在の質問・回答なし) / 730277 teamup疑義 / 725195 Beginner Guide(1票、宣伝) / 724831 Rule 3.5.d / 724094 ML必須か(既読) / 722920 rules question / 717046 未成年(不読) / 716196 Marília Prata(13票、京都のポケモンショップ写真の雑談・情報ゼロ) / 712435 Cards data / 710978 Project visibility(§1) / 709452 Writeup Format(§1) / 709223 US未成年(不読)。

- **730277「Is it a bug in strategy teamup?」(hengck23、4票)**: 「Sim側で別チームだったメンバー同士がStrategy側で1チームに合流できてしまう。禁止規則が無い?」。Zhenyu Zhang「LBではチーム済みなのにHackathonページではチーム表示されない。LBとHackathonで別チームを組める?」**運営回答なし(5日経過)**。722920 では Addison が「Strategy チームは Sim チームと同一である必要」を前提に「削除済みユーザーの残留はこのケースでは不問」と回答しており、**規則上は同一チーム要件・実装上は合成できる穴**の疑いが残る。我々(枠5、現2名)には直接影響なしだが、外部専門家を入れるなら期限(9/6 merger deadline)前にSim側でチーム化が必要という理解を維持。
- **724831「Rule 3.5.d fairness」(Taichi Akiyama、4コメント)全文取得**: Addison「ポケカ一般論の会話はOK。**リプレイを見て『エージェント改善を意図した競技特化の助言』を私的に与えるなら、その人は正式にチーム加入が必要**。リプレイが公開されていることは私的助言の免罪符にならない」「懸念があるならチームに入れるのがベストプラクティス」。Russell Kirk の「計算資源はよくて助言はだめなのか(金で買う助言と計算資源の等価性)」への正面回答はなし。→ handover §3.5.d の理解を公式に再確認。
- **712435「Problems with Cards data / CABT supported cards」(Juan Ortega、0票・回答なし)**: 「CABTに対して623枚valid/644枚not valid」と主張し، カード名の誤記("Telepath Psychic Energy"→正しくは"Telepathic Psychic Energy")を指摘。分母1,267は我々の2,022枚プールと合わない(外部カードリストとの突合とみられる)。**C5(全数使用可)の反証にはならない**が、「効果が実装されているか」は別問題という C5 への注意書きと同種の疑義が外部にもある、という記録。

---

## 3. 任務3: mechi22/ptcg-1070-9-alakazam-rule-based-skeleton(LB1070.9級)

**結論: 消滅(非公開化または削除)。回収不能。**

- https://www.kaggle.com/code/mechi22/ptcg-1070-9-alakazam-rule-based-skeleton → 「We can't find that page.」(2026-08-03観測)
- https://www.kaggle.com/mechi22/code → **公開ノートブック0件**(ユーザー「めめっち」、1ヶ月前参加、**昨日もアクティブ**)。意図的な取り下げ(going dark)と整合。
- 競技Codeタブで "skeleton" 検索 → 該当0件(公開フォークも残っていない)。Wayback Machine は 429 Too Many Requests ×2 で照会不能(時間を置けば照会の余地あり)。

### 3.1 副産物: 取得失敗22件の全数生死判定(curl の title タグ + リダイレクト追跡)

**13件消滅**(title が「Kaggle: Your Home for Data Science」= 404):
alycemiki/lucario-deck-v2-play-like-a-bot、fishcat37/ptcg-v9-attention-all3d-end-to-end、kacchanwriting/crustle-aware-mega-lucario-ex-anti-wall、llccqq624/ptcg-meta-a-crustle-attackfix-v1、maulikgajera/the-pok-mon-ptcg-ai-battle-agent、**mechi22/ptcg-1070-9-alakazam-rule-based-skeleton**、nursrijan/pok-mon-tcg-advanced-heuristic-planning-agent、rahuljiwane/pokemon-tcg-rahul-jiwane7、**seokjeongeum の5本全部**(max-elo-1208-libraryout-w-crustle-great-tusk / mega-pokemon-reinforcement-ai-battle / pure-dragapult-ex-deck / strong-start-baseline-agent-v10-lb-950 / strong-start-psychic-anti-meta-v8-lb-1100)。

**8件は改名して現存**(curl -sL で最終URLに解決。**取得失敗の正体はリダイレクト**):
- kokinnwakashuu/ptcg-public-915-lucario-search-baseline → **ptcg-lucario-public-lab-anti-crustle-log**(「PTCG Lucario Public Lab: Anti-Crustle & Log」)
- pilkwang/pok-mon-tcg-ai-battle-meta-snapshot-08-july および pilkwang/pokemon-tcg-lucario-alakazam → **pok-mon-tcg-ai-battle-meta-snapshot-18-july**(176票・5,230views・Public 748.5 / Best 981.3 V28)
- prvsiyan/ptcg-ai-battle-field-audited-alakazam-v8 → **ptcg-alakazam-2-304-game-audit-12-visuals**(「2,304-Game Audit | 12 Visuals」)
- prvsiyan/ptcg-observable-meta-router-v1 → **ptcg-844-4-observable-meta-router-visuals**
- prvsiyan/ptcg-rmy-grimmsnarl-replay-hybrid-v1 → **ptcg-rmy-surface-souta-1208-loader-v1**(「Rmy Surface Souta 1208 Loader」= LB1208級 Rmy 系エージェントのローダーを名乗る。**要取込**)
- romanrozen/strong-start-crustle-lucario-agent-v7-lb-960 → **strong-start-baseline-agent-v10-lb-950**
- yaminh/the-pokemon-company-ai-challenge → **the-pokemon-company-ai-challenge-v3**

→ 後続タスク: 現存8件(実質7件)を _inbox に取込む(公開共有は8/2で凍結済みなので、この7件が最後の未収穫)。

---

## 4. 任務4: 公式Discord(discord.gg/kaggle)

**未達(ログイン壁)。** https://discord.com/channels/@me はログインフォーム(「おかえりなさい！」)を表示。規律により認証操作はせず撤退。招待リンクの承諾もサーバー参加という状態変更のため実施せず。

- 期待値の補正材料: Strategy discussion/708491 で Kaggle スタッフが明言 — 「**Discord の競技チャンネルはスタッフ・ホスト非監視。重要な質問・知見は Kaggle フォーラムに置くこと**」「競技のtipsをX等の非公開チャネルだけで共有するのは規則違反になりうる」。→ 運営発言・重要メタ情報が Discord だけに存在する可能性は低い。優先度を下げてよい。

---

## 5. 任務5: SUMI スレッド(Sim discussion/729926)の図表・返信

52票(監査時から増)。本文の数表・再現コード・返信14件を全文取得。前任者の要約(Archaludonバブル・adoption lags ~3日)に対する**追加分**:

### 5.1 本文の詳細(前任要約に無かった数値)

- **対戦マトリクス(7/17-26プール、行が列に勝つ、括弧はN)**:
  - grimmsnarl: vs alakazam **57%**(3,703)/ vs tarountula 57%(1,237)/ vs garchomp **41%**(993)/ vs crustle 50%(830)
  - alakazam: vs tarountula **28%**(1,038)/ vs garchomp **64%**(916)/ vs crustle 60%(978)
  - tarountula: vs alakazam **72%** / vs garchomp 44%(316)/ vs crustle 57%(237)
  - garchomp: vs grimmsnarl **59%** / vs alakazam 36% / vs tarountula 56% / vs crustle 57%(233)
  - SUMIの読み: **Grimmsnarl > Alakazam > Garchomp > Grimmsnarl の3すくみ**。Tarountula は「専業アラカザム狩り(72%!)」で他に負ける。**「Garchomp が現在の実フィールド構成に対する最高EVデッキ=次のバブル候補」**。
  - **⇒ 我々の tarountula 94.5(対Alakazamゲージ)に、N=1,038 の実ラダー独立裏付け(72%)が付いた。**
- 時系列: Grimmsnarl 台頭 7/17→7/26 で 17→31→39→**51.3%**、**#1チームと現トップ25の大半が使用**、非ミラー勝率は50.3%に収束(自分が作った場と均衡)。6月下旬は2-29%シェアで61-67%勝ちだった。Alakazamは7/14に46%でピーク。Mega Lucarioは28%→絶滅(7/26に1チーム、0.03%)。
- トップ帯は回転扉: 3,057チーム中、14スナップショット皆勤は0、2回以上出現も1,492のみ。隣接スナップショット間の生存率15-92%(7月後半は56-71%)。
- 手法・再現コード全文公開(シグネチャカードID: alakazam{743,245} archaludon{190,170,840} grimmsnarl{648} starmie{1031,361} trevenant{879} dragapult{121} crustle{345,533} bellibolt{269} abomasnow{723,419} lucario{678} dudunsparce{306,997,66} garchomp{380,381} gardevoir{747} tarountula{400,401}。デッキは steps[0] の visualize[].action 内の60枚リスト×2)。sankey_data.json 添付、74,634行の census CSV 共有の申し出あり。
- 図(Sankey): 14列(6/17→7/26、列下は日次ゲーム数 約7.8k→4.5k)、リボン=チームのデッキ乗換。本文数値と整合、追加情報なし。

### 5.2 返信14件(前任者未読の部分)の重要証言

- **Zhenyu Zhang(112位)**: 「**最終戦略を1日だけ提出して翌日デッキを替える競合がいる。LBに置いておくと研究・対策されるからだ**。分かる人には分かるはず」⇒ Oshbocker の going dark と同型の**デッキ秘匿行動が複数チームで進行中**という直接証言。**凍結直前まで見えるLBメタは意図的に汚染されている**前提を強化。
- **Tony Li(139位)**: 「ゲーム数が最終スコアと順位に効くように見える。**理想は、強い開始位置+十分な消化試合数+『他人に研究されていない』新しいモデルとデッキで最終2週間に入ること**。未証明のモデル・デッキをいきなり出すのはリスクが高すぎる」⇒ 競合の凍結戦略の定式化。我々の「直近2提出=ベスト2本」規律と同じ盤面を見ている。
- hengck23(148位)「締切直前に魔法の勝ちデッキへ乗り換えるチームが出るのでは」/ SUMI「乗換が増えるほどLB動態は予測不能になる」。
- SUMI(4333位=分析専業)は「**関連分析をシリーズで出す予定**」。スケジュール実行ノートブック化はデータロードが重く断念。
- 726690 とこのスレの相互参照から、**「帯メタを狙い撃つ counter-deck 戦略」は 732105 の junlee789 コメントでも独立に証言**(「ランキング境界に分布する特定デッキ構造を倒す戦略を作っている人々がいる」)。

---

## 6. 統合: 「超えるべき品質の天井」と「誰も書いていない空白」

writeup 本体が読めない以上、天井は**公開 discussion 分析の最高水準**から推定するしかない:

| 公開分析の最高峰 | 票 | 中身 |
|---|---|---|
| 724362 Abhyuday(101位) | 73 | 思考時間サイドチャネルで実装分類。散布図。しかし**N=30,000の観察であって因果・CI なし** |
| 729926 SUMI | 52 | 74,634戦・全数分類・Sankey・マトリクス・再現コード付き。**最も論文に近い**。ただし相関記述で、介入実験ゼロ |
| 726690 kurikuri54 | 10 | 実測エピソードレート+運営仕様を引き出した統計的批判。CI なし |

**空白(=我々の差別化)、今日の観測で裏が取れたもの**:
1. **介入実験**: 公開物は全て観察研究。**操縦者固定・デッキ可変(60pt)のような統制実験は皆無**。JB Bryant(105位)がデッキ自動探索を目指すも「評価の分散とコスト」で詰まっている — まさに我々のCEW/ゲージ方法論が解いた問題。
2. **CI・検定力を明示した測定**: どの公開分析にも無い。kurikuri54 の批判(区別できない3仮説)への回答形式で書ける。
3. **Media Gallery**: 言及ゼロのまま(291走査+今回の新着でも)。図表10%の配点を Gallery で取りに行くのは依然ブルーオーシャン。
4. **失敗の方法論(数える単位・静かな打ち切り)**: 募集文(708588)が「試行錯誤・教訓の共有」を明示要求。公開スレで方法論の失敗を体系的に書いた者はいない。
5. **評価ルーブリックとの直接照合**: 「繰り返し対戦での一貫性」「特定マッチアップへの過度依存回避」は、我々のフィールドEV・帯別メタ・OOFゲージがそのまま証拠になる。counter-deck 分散戦略(732105でc-numberが批判した行動)の**対極**として自陣を位置づけられる。

**競合の実名と着手(敵情の要約)**: 1位 Majkel1337 1259.2(RL+探索と推定/724362)、2位 Raihan Ramadistra 1163.7、3位 ntumlnoob 1186.4(RL、4090一枚)、5位帯に c-number/tomo0608、12位 James Cox & Henry Chao 1101.8(ルールベースと目される元ポケカ勢)、22位 Oshbocker、44位 Rmy。hengck23(148-153位)= LLM×リプレイ克隆の agent swamp(未寄与と本人談)。JB Bryant(105位)= デッキ自動探索(未完)。※順位は 2026-08-03 深夜のLB。

---

## 7. 我々の主張・計器への波及(handover §4 の C1-C5 対応)

- **C1/C2(デッキ60pt・機構仮説)**: SUMI マトリクスが tarountula>alakazam 72%(N=1,038)で方向を裏付け。一方で**実ラダーではgrimmsnarlがトップ帯51.3%・#1チーム使用** — 我々のゲージでの grimmsnarl 35.0 は「操縦者が特性を盲打ちしている」せいである可能性が濃くなった(=**C2の反証テスト`main.py:335`修正の優先度が上がる**)。garchomp{380,381} は SUMI 曰く対フィールド最高EV — **ゲージ掃引の追加腕候補**。
- **C4(公開操縦者にGrimmsnarl 0件)**: mechi22 消滅と seokjeongeum 5本消滅により、**「公開プールの棚卸しは 8/2 時点のスナップショットとしてしか語れない」**ことが確定(消えた13件は再検証不能)。現存の改名7件は未取込のまま残っている。
- **C5(2,022枚全数受理)**: 712435 の「623/644」は外部リスト由来で反証にならず。ただし「受理≠効果実装」の疑義は外部にも存在。
- **bench/A-B設計**: エンジンに**シード注入・状態復元は無い**(James Jean、0/300)。ペアドシード設計は不可能 — 我々のN設計(CI前提)の正当化材料。
- **replay_analysis**: ①レート制限が始まっている(732502、razilyrazi)②ローカルvisualizer出力の `selected` off-by-one(Prema Ananda)— **Kaggle replay.json 側に同じずれがあるか要検算**(我々の行動語彙・意思決定タイミング解析の妥当性に直結)。
- **タイミング計器の新規性**: 724362 が先行。引用した上で「彼は観察、我々は統制実験」と差別化する。

---

## 8. 未達・積み残し

- Discord(ログイン壁、§4)。ゆうじのログイン済みブラウザがあれば再訪価値は低〜中(708491の非監視宣言のため)。
- mechi22 の Wayback 照会(429×2)。時間を置いて `archive.org/wayback/available?url=kaggle.com/code/mechi22/...` を再試行の余地。
- 改名7件の取込(§3.1)。特に prvsiyan/ptcg-rmy-surface-souta-1208-loader-v1。
- CEDEC 資料(cedil.cesa.or.jp/cedil_sessions/view/3296)の入手(CEDiL は無料会員登録が要る可能性 — 登録操作はしていない)。
- 708586(エンジン差分スレ)のコメントは 7/31 以降増えていない(last comment 3d ago by S)ため再読せず。

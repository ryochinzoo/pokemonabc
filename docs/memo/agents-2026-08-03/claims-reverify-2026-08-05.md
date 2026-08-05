# 根拠再検証 2026-08-05 — 今セッション依拠主張6件を各1回の新鮮プローブで確認

> 方式: 全量再実行ではなく**各主張1プローブ**。「以前そうだったから」は根拠にせず、
> 今日返ってきた実物だけを貼る。EpisodeService は不使用(全プローブが公式 kaggle CLI の
> 公開エンドポイント。playbook §8 の門番対象外)。**Kaggle APIリクエスト計4**(提出一覧1・
> LB全量DL1・kernels list 1・kernels pull 1)。対戦ゼロ(エンジンは AllCard/AllAttack の
> DB読取と、取得カーネルの agent(select=None) 純関数呼び出しのみ)。

## 総括表

| # | 主張(出所) | 試した1手 | 判定 |
|---|---|---|---|
| 1 | makthanithin は LB1084.5級(corpus-B §4③、タイトル自己申告) | `kaggle competitions leaderboard --download` → CSV検索 | **崩れた(「級」の部分)** — 実在は立つが現在 **750.0・1499位**。1084.5の裏取りは今回も不能。※ゲージ昇格の実質根拠(P9セル一致)は別系統で無傷 |
| 2 | 公開ノートブックのプールは8/2で凍結済み(D61/scout-A §2.2) | `kaggle kernels list --sort-by dateCreated` | **立つ** — 最新作成は 8/2 18:22 UTC。8/3以降の新規作成ゼロ |
| 3 | Grimmsnarl操縦者は公開コード0件(corpus-B C4) | 残余候補の後継 `prvsiyan/ptcg-rmy-surface-souta-1208-loader-v1` を pull → agent(select=None) 実行 | **立つ(強化)** — 返り値は **Mega Lopunny ex/Dudunsparce** 60枚。Grimmsnarl系カード(646/647/648)ゼロ |
| 4 | Team Rocket's Energy の仕様(Honchkrow検死、本文途中省略のまま使用) | `cg/api.py all_card_data()` で全文取得 | **立つ** — 省略部は「付いている限り {P}{D} 任意組合せで**2エネ供給**」。検死の機構説明と矛盾なし。DB由来主張3点も全一致 |
| 5 | SUMI の tarountula>alakazam 72% (N=1,038)(scout-A §5.1) | 我々のローカル湖で同セルを直接計算(field_ev/band_meta_census 系) | **立つ(方向)** — 我々の独立標本で **86.7%**(52W-8L, N=60, distinct 31×35)。方向一致、水準は帯・期間差の範囲で我々が高め |
| 6 | 王者系列の確定スコアは 783/793.9(team-share-2026-08-05) | `kaggle competitions submissions` | **立つ** — 54832323=**783.0** / 55058443=**793.9**(現在値) |

**崩れたのは1件のみ**: #1の「1084.5級」という形容。ほか5件は実物で裏が取れた。

---

## 1. makthanithin は LB1084.5級か

- **主張**: data.md 2026-08-05「実ラダー上位級の公開Lucario操縦者(makthanithin 1084.5、corpus-B選定)」。
  出所は notebook タイトル `pokemon-tcg-ai-battle-1084-5-baseline` の自己申告のみ(corpus-B §4③も「(タイトル)」と明記)。
- **試した1手**: `kaggle competitions leaderboard -c pokemon-tcg-ai-battle --download` → 全量CSV(2026-08-05T09:43:56 スナップショット、6,307行)を検索。
- **実物**:
  ```
  1499,16378270,"Nithin maktha","2026-08-03 19:01:25",750.0,2,makthanithin
  3646,16405138,Yser,"2026-08-05 08:51:34",596.0,2,"inoueyuji,ryoheihara"
  ```
- **判定: 崩れた(「1084.5級」の部分)/ 実在は立つ**。
  - チームは実在(Nithin maktha、単独)。ただし現在スコア **750.0(1499位/6307)**。「上位級」ではない。
  - LBは直近2提出の現在値(最終提出 8/3)であり、**過去ピーク1084.5の反証にはならない**が、
    自己申告を裏付ける独立証拠は今回も得られなかった。現在走っている提出がノートブックの
    agent と同一かも不明。
  - **ゲージへの波及は限定的**: 新ゲージの較正計器昇格は「P9実ラダーセル 15.4%(13体)≈ ゲージ14.0%」
    の一致による(data.md 2026-08-05 T1較正監査)。この根拠は本判定の影響を受けない。
    ただし文書中の「実ラダー上位級の操縦者」という形容は**「LB1084.5自己申告(現在750)の公開
    Lucario操縦者」に弱めるべき**。writeup に「上位級ゲージ」と書くのは不可。
  - ついで(依頼分): 我々= **Yser 3646位 596.0**。LastSubmissionDate 08:51:34 が proto5
    (55264776、8/5 08:51:34)と一致=本人確認。直近2=proto窓(596.0/591.2)で王者2本は窓外(D50想定どおり)。

## 2. 公開ノートブックのプールは8/2で凍結済みか

- **主張**: D61・scout-A §2.2(728935「Public Notebook Sharing Deadline: August 2」= 8/2 23:59 UTC 締切)。
- **試した1手**: `kaggle kernels list --competition pokemon-tcg-ai-battle --sort-by dateCreated --page-size 25 -v`(作成日降順)。
- **実物**(先頭3行。列は ref,title,author,**lastRunTime**,totalVotes):
  ```
  toshikomiyake/rl-mcts-text-embedding-model4,...,2026-08-02 18:22:08
  keidroid/ptcg-ai-battle-rating-and-matchmaking-analysis,...,2026-08-02 16:47:45
  samoilovmikhail/eda-the-anatomy-of-a-winning-turn,...,2026-08-02 00:06:56
  ```
- **判定: 立つ**。作成日降順の先頭要素の lastRun=8/2 18:22(作成≤lastRun)なので、
  **全公開カーネルの作成日 ≤ 8/2 18:22 UTC = 8/3以降の新規作成ゼロ**(本日8/5時点)。
  - 留保: このプローブは「旧作を後から公開に切替」(flip-to-public)を検出できない。
    検出には現在の全量リスト vs 8/2 MANIFEST(291件)の差分が要る(必要になったら
    page-size 200×2リクエストで可能)。
  - 副産物: 対象カーネル prvsiyan/ptcg-rmy-surface-souta-1208-loader-v1 がこの一覧に
    現存することも同時に確認(#3の前提)。

## 3. Grimmsnarl操縦者は公開コード0件か

- **主張**: corpus-B C4「現存する公開コードの範囲で Grimmsnarl 操縦者0件」。残余リスクとして
  「prvsiyan/ptcg-rmy-grimmsnarl-replay-hybrid-v1(404)が唯一の候補だった可能性」を明記していた。
  scout-A §3.1 がその後、**同カーネルは削除ではなく改名して現存**(→ ptcg-rmy-surface-souta-1208-loader-v1)と特定。
- **試した1手**: `kaggle kernels pull prvsiyan/ptcg-rmy-surface-souta-1208-loader-v1 -p rmy -m` →
  埋め込みpayload(base64+SHA束縛)をデコード → SHA256 一致確認 → **agent(select=None) を実行**
  (conformance.py と同一の deck-phase obs、cg は実DB読取のみ・対戦ゼロ)→ 60枚を両分類器で分類。
- **実物**:
  ```
  main.py sha256 95c0764e...bbe69b3 MATCH / deck.csv sha256 7fc17fc6...ed1d6c MATCH
  returned type: list len: 60
  classify_a (RULES/name): None
  classify_b (SUMI SIGS): dudunsparce
  top_pokemon: Dudunsparce
  grimmsnarl-family cards (646/647/648) in deck: NONE
  60枚 = Mist Energy4 / Enriching1 / Spiky3 / Dudunsparce4 / Fan Rotom1 / Dunsparce4 /
         Buneary4 / Mega Lopunny ex3 / Buddy-Buddy Poffin4 / Ultra Ball4 / Pokégear4 /
         Poké Pad4 / Air Balloon4 / Boss's Orders3 / Xerosic1 / Hilda4 / Lillie4 / Wally4
  ```
- **判定: 立つ(強化)**。唯一の残余候補の**現存後継は Grimmsnarl 操縦者ではない**
  (Mega Lopunny ex/Dudunsparce のクリーンルーム実装。main.py 冒頭に「60枚は公開リプレイ
  89276670 から転記」と自己申告)。C4 の残余リスク文言は「削除された v1 の中身のみ検証不能」
  まで縮む。corpus-B §5.3 の「404・再取得失敗」は**改名リダイレクトの見逃し**だった(scout-A の
  読みが正しかった)。
  - **副次発見**: タイトル「Rmy Surface Souta 1208 Loader」は中身と無関係(Rmy でも Souta の
    crustle でもない)。**タイトル自己申告の不信頼の2例目**(1例目=#1 makthanithin)。
    公開プールのタイトル由来情報は全て要実行確認、を規則化してよい。

## 4. Team Rocket's Energy の仕様は検死と矛盾しないか

- **主張**: Honchkrow検死(data.md 2026-08-04)の機構説明。カード本文はCSV引用時に
  改行で途切れ、前半(TR限定・違反時破棄)しか見ていなかった。
- **試した1手**: `cg.api.all_card_data()` / `all_attack()` から全文取得(エンジンDB直読、対戦ゼロ)。
- **実物**(card 15 の skill text 全文):
  ```
  This card can only be attached to a Team Rocket's Pokémon. If this card is attached to
  anything other than a Team Rocket's Pokémon, discard this card.

  As long as this card is attached to a Pokémon, it provides 2 in any combination of
  {P} Energy and {D} Energy.
  ```
  併せて検死のDB由来主張を検算:
  ```
  Rocket Feathers: damage=0, text「手札からTRサポーターを任意枚数捨て、1枚につき60」 → 検死と一致
  Hammer In:       damage=100(素点100) → 一致
  R Command:       damage=0, text「捨て札のTRサポーター×20」 → 一致
  ```
- **判定: 立つ**。省略されていた後半は**エネ供給条項(2個分の{P}/{D})**で、検死の機構説明
  (①テキスト内打点の盲点 ②コスト最小化=打点無力化 ③エネ機関が操縦者側で死ぬ)と矛盾しない。
  なお honchkrow デッキのポケモンは**全員 Team Rocket's**(Articuno/Murkrow/Porygon/Porygon2/
  Honchkrow)なので付着制限はデッキ内では発動しえず、「エネ機関非互換」は**カード側でなく
  操縦者側(供給2の非理解・付け先選択)の問題**という検死の読みをむしろ支持する。

## 5. SUMI の tarountula>alakazam 72% は我々の計器と整合するか

- **主張**: scout-A §5.1 の読取「alakazam vs tarountula 28%(N=1,038)⇔ tarountula 72%」
  (7/17-26 全ラダープール)。
- **試した1手**: 我々のローカル湖(ladder_scout/decks.jsonl+ep群、ネットワーク不使用)で
  同セルを直接計算。分類は band_meta_census の B(SUMI署名)優先+A、自チーム戦は除外。
  併せて `field_ev.py` 既定実行(800-1099帯)の行列も採取。
- **実物**:
  ```
  tarountula vs alakazam (全帯、自チーム除外): 52W-8L = 86.7%  N=60  wilson95 [75.8, 93.1]
    distinct tarountula subs=31, distinct alakazam subs=35
  band 800-1099 両側: 39W-6L = 86.7%  N=45
  field_ev(800-1099): tarountula行 alaka 85† / alakazam行 tarou 15†(†=distinct<25側あり)
  ```
- **判定: 立つ(方向・優劣は完全一致)**。独立標本(我々の湖、distinct 31×35)で
  tarountula が alakazam を大差で狩る方向を再確認。水準は我々 86.7% [75.8, 93.1] > SUMI 72% で
  CI下端が SUMI 値を僅かに上回る = 同一母集団ではない(SUMI=7/17-26全帯・N=1,038、
  我々=直近サンプル・800-1099帯中心)。「専業アラカザム狩り」という結論の使用に支障なし。

## 6. 王者系列の確定スコアは 783/793.9 か

- **主張**: team-share-2026-08-05「王者starmie: 確定レート783/793.9で最強」。
- **試した1手**: `kaggle competitions submissions -c pokemon-tcg-ai-battle -v`(現在値を1回取得)。
- **実物**:
  ```
  54832323 | 2026-07-19 | v2.1c x starmie-aggro          | COMPLETE | public: 783.0
  55058443 | 2026-07-28 | Champion re-submission #3      | COMPLETE | public: 793.9
  (参考: 54961048=747.0 / 54858780=765.0 / 55236642 P9=709.3)
  ```
- **判定: 立つ**。783.0 / 793.9 とも現在値で一致。王者系列レンジ「747-794」(data.md)も
  54961048=747.0 で整合(旧記録747.1から0.1のドリフト、許容内)。

---

## 波及メモ(記録のみ、判断は主セッションで)

1. **#1**: data.md 2026-08-05 の「実ラダー上位級の公開Lucario操縦者」という形容は弱める
   (「LB1084.5**自己申告**・現在750」)。ゲージの計器としての地位は P9 セル一致由来で不変。
2. **#3**: corpus-B §5.3 の恒久欠測17refのうち prvsiyan/rmy-grimmsnarl-replay-hybrid は
   「改名現存・後継は非Grimmsnarl(Lopunny)」に更新可。C4 残余リスクは縮小。
3. タイトル自己申告の不信頼が同日2例(1084.5 / Souta 1208 Loader)。公開物のタイトル数値は
   引用前に必ず実行 or LB で裏取り、を運用規則に。
4. 取得物の置き場: LB CSV・提出一覧・pull した rmy カーネルと抽出済み main.py/deck.csv は
   scratchpad `reverify/`(揮発)。必要なら _inbox へ正式取込を別途。

*根拠再検証係 / 2026-08-05。プローブはすべて単発・直列、429ゼロ。*

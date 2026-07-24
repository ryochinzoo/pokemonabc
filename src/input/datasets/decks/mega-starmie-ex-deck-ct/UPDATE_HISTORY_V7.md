# UPDATE_HISTORY_V7

このファイルは、v7以降の変更履歴を記録する。

旧 `UPDATE_HISTORY.md` は過去履歴として残し、v7の実戦改善・設計修正はこのファイルへ追記する。

記録単位は原則として `1 Issue = 1 Fix` とする。
各ブロックは、必ず「問題」「原因分析」「修正案」を分けて記載する。

---

## 記録フォーマット

### YYYY-MM-DD / Issue名

**問題**

- 実戦ログ、テスト、提出エラーなどで確認した事実を書く。
- 推測は書かない。

**原因分析**

- 現行 `main.py`、`deck.csv`、`CARD_TABLE`、`ATTACK_TABLE`、`cg/api.py`、現行テストから確認できた原因を書く。
- 旧実装、過去バックアップ、Notebook由来コードは根拠にしない。

**修正案**

- 最小修正の方針を書く。
- 変更対象、追加テスト、回帰確認を書く。
- 実装しなかった案がある場合は、その理由を書く。

---

## 2026-07-19 / セイジを使えるのに弱攻撃を選ぶ

**問題**

- 参考ログ `いやいや、セイジつかえよ.json` で、手札に `Salvatore` があり、合法Optionにも出ているのに、ユキワラシの弱攻撃 `Chilly` を選んでいた。
- 該当局面では `salvatore_live=True`、`needs_mega_yuki=True`。
- 修正前スコアは `Salvatore = 125000`、`Chilly = 701000`。
- そのため、攻撃前に進化展開できる局面でも、弱攻撃が優先されていた。

**原因分析**

- `Salvatore` のカードIDは `1189`。
- `deck.csv` / `DECK` 上、`Salvatore` は2枚存在する。
- `CARD_TABLE[1189]` は `Salvatore` として存在し、効果は「自分の場のポケモンから進化する、特性なしの進化先を山札から選び進化させる」。
- カード認識ミス、デッキ未投入、APIフィールド誤解ではなかった。
- 原因は `Policy.score_play(SALVATORE)` が低く、`Policy.score_attack()` の有効攻撃基礎点 `SCORE_PREFERRED` に乗った弱攻撃を上回れないこと。
- `Chilly` は非KO弱攻撃として減点されていたが、それでも `701000` 残っていた。

**修正案**

- `score_play(SALVATORE)` を、`salvatore_live=True` のとき `SCORE_PREFERRED + 125000` から評価開始する。
- これにより、弱攻撃よりセイジを優先する。
- 即時勝利攻撃やKO攻撃は従来どおり攻撃側の強い評価が残るため、セイジが勝ち確行動を潰さない。
- 回帰テストとして、ユキワラシが `Chilly` を撃てるが `Salvatore` も使用可能な局面で、`Salvatore` のスコアが `Chilly` を上回ることを追加する。
- 実ログ再採点では、該当局面が `Salvatore = 1125000`、`Chilly = 701000` になり、セイジが最上位になることを確認する。

---

## 2026-07-19 / Turbo Flare後のエネルギー配布が補助役へ流れる

**問題**

- 参考ログ `ヒトデマンいるのにシェイミにエネわたすな.json` で、`Cinderace` の `Turbo Flare` 後に、ベンチの `Staryu` ではなく `Shaymin` へ水エネルギーが複数枚配られていた。
- 通常の手貼り評価では `Shaymin` への水エネルギーは `SCORE_FORBIDDEN` になっており、問題は通常ATTACHでは再現しなかった。
- 実ログ上の対象選択フェーズは `SelectContext.ATTACH_FROM`、`effect_id() == CINDERACE`。

**原因分析**

- `Turbo Flare` 後の対象選択は、現行コードでは `score_target_or_card()` へ入り、専用処理がない場合は `target_value()` へフォールバックしていた。
- `target_value()` は相手への攻撃対象評価に近く、`Shaymin` 加点やエネルギー付き対象加点を持つ。
- そのため、味方へのエネルギー配布なのに、攻撃対象用の汎用評価で `Shaymin` が `Staryu` を上回る可能性があった。
- これは `Shaymin` 固有ではなく、`Turbo Flare` 後の味方エネルギー配布全体の評価経路の問題。

**修正案**

- `effect_id() == CINDERACE` かつ `SelectContext.ATTACH_FROM / ATTACH_TO` の場合だけ、`target_value()` へ落とさず `score_turbo_flare_attach_target()` を使う。
- `Mega Starmie ex`、`Staryu`、必要局面の `Mega Froslass ex` / `Snorunt` を優先する。
- `Shaymin`、`Cinderace`、`Yveltal` など補助役はTurbo Flareの加速先として低評価にする。
- 問題ログ再採点では、該当step 29-36がすべて `Staryu = 230000`、`Shaymin = -50000` へ反転したことを確認する。

---

## 2026-07-19 / テスト上のTurbo Flareダメージ定義が実データとズレている

**問題**

- 実戦観察で `Cinderace` の `Turbo Flare` のダメージが50ではなく100付近に見える疑いがあった。
- 現行 `ATTACK_TABLE[965]` では `Turbo Flare` の `damage=50` と確認できた。
- 参考ログの攻撃ログには `attackId=965` は出るが、ダメージ値そのものは記録されていなかった。
- 現行テストの `FakeBoard` だけ、`TURBO_FLARE` を `damage=80` として定義していた。

**原因分析**

- 実コード本体の `ATTACK_TABLE` は正しく50を参照しているため、実装本体が100ダメージとして扱っている根拠は確認できなかった。
- ただし、テスト用FakeDataが実データとズレており、今後のレビューや回帰テストで誤った期待値を作るリスクがあった。

**修正案**

- `test_immediate_outcome.py` の `FakeBoard` 内 `TURBO_FLARE` 定義を、実データに合わせて `damage=50` へ修正する。
- 本体ロジック、Policy点数、AttackOutcome、Turbo Flare評価は変更しない。
- `AST OK`、`IMPORT OK 50`、`immediate outcome tests OK` を確認する。

---

## 2026-07-19 / Turbo Flareが強制評価すぎて展開札やボスを潰す

**問題**

- 参考ログ `イグニッションエネルギーの使い方おかしいし、エースバーンの攻撃１００とかハイパーボール使わないとか動きが意味不明.json` で、`Turbo Flare` が非常に高く評価され続けていた。
- 現行再採点でも、修正前は `Turbo Flare = 500300000`、`Ultra Ball = 85000`、`Boss's Orders = 1305000` となり、ほぼすべての展開札・干渉札を押し潰していた。

**原因分析**

- `Policy.score_attack()` で `Turbo Flare` が `SCORE_FORCED // 2 + 300000` を返していた。
- `Turbo Flare` は有用な加速ワザだが、即時勝利やKOと同じ強制行動ではない。
- このため、エネルギー加速が必要な局面を超えて、ボスによる勝ち筋やハイパーボールによる展開判断まで常時上回るリスクがあった。

**修正案**

- `Turbo Flare` を強い優先攻撃として残しつつ、`SCORE_FORCED` 系の評価から外す。
- ベンチに加速先がある場合は `SCORE_PREFERRED` 基準で評価する。
- メガ未完成なら追加評価し、手札に `Ultra Ball` / `Salvatore` / `Mega Starmie ex` がない場合はさらに少し上げる。
- 代表ログ再採点では、`Turbo Flare` が `500300000` から `1220000` 前後に低下し、`Boss's Orders = 1305000` の局面ではボスが上回ることを確認する。
- `Ultra Ball` よりはTurbo Flareが上に残るため、明確な加速局面のテンポは維持する。

---

## 2026-07-19 / Water Gun・Chillyが展開札より高すぎる

**問題**

- 参考ログで、`Staryu` の `Water Gun` や `Snorunt` の `Chilly` が非KOなのに70万点台になり、`Crispin`、`Pokegear 3.0`、`Mega Signal`、`Boss's Orders` などの展開・干渉札を上回る局面が複数あった。
- 例として、`Water Gun = 702000`、`Crispin = 72000`、`Pokegear 3.0 = 52000` のような評価が確認された。
- その結果、メガ進化やエネルギー準備より、10〜30ダメージの弱い基本ワザを優先するリスクがあった。

**原因分析**

- `Policy.score_attack()` は有効攻撃を `SCORE_PREFERRED + damage * 100` から評価している。
- 既に `Water Gun` / `Chilly` と、`Staryu` / `Snorunt` の非KO攻撃には減点があったが、起点が高すぎるため減点後も展開札を大きく上回っていた。
- KOできる場合は攻撃すべきなので、弱ワザそのものを常時禁止するのではなく、非KOかつ実展開札が存在する局面だけ評価を落とす必要があった。

**修正案**

- `Policy.score_attack()` で、`Water Gun` / `Chilly` が非KOかつ `has_real_development_option()` が真の場合、通常候補レベルへ早期returnする。
- KOできる `Water Gun` / `Chilly` は従来どおり高評価に残す。
- 回帰テストで、非KOの `Water Gun` より `Crispin` を優先し、KOできる `Water Gun` は `Crispin` より優先することを確認する。

---

## 2026-07-19 / ハイパーボール等のコストで水エネ・主軸札を雑に捨てる

**問題**

- 参考ログ `動きが最悪.json` の `Ultra Ball` コスト選択で、水エネルギーや重要札が捨て候補に混ざっていた。
- 現行再採点でも、修正前は該当stepで `Water Energy` と `Crispin` が選ばれる経路が残っていた。
- このデッキは水エネルギー、`Staryu`、`Mega Starmie ex`、ライブ状態の `Salvatore` を失うと、その後の完成速度と攻撃継続が落ちる。

**原因分析**

- `Policy.score_discard()` は `IMPORTANT_CARDS` を一律 `SCORE_LAST_RESORT` にしていた。
- 複数枚コストでは、重要カード同士がほぼ横並びになり、どれを泣く泣く捨てるかの序列が粗かった。
- 特に、水エネルギー、`Salvatore`、`Hero Cape`、`Mega Signal` の状況別価値を区別できていなかった。

**修正案**

- `score_discard()` 内だけで、現行デッキの重要札に状況別の保護順位を付ける。
- `Mega Starmie ex`、`Staryu`、水エネルギー、ライブ状態の `Salvatore` を強く保護する。
- `Hero Cape` は貼り先のメガがいる場合に強く保護し、貼り先がない場合は中保護にする。
- `Mega Signal` は進化元がいる場合だけ保護し、進化元がいない場合はコスト候補に寄せる。
- 問題ログ再採点では、該当stepが `Water Energy + Crispin` から `Crispin + Mega Signal` へ変わり、水エネルギーを残すことを確認する。

---

## 2026-07-19 / 改善なしの有料退却で横滑りする

**問題**

- 参考ログで、交代先選択フェーズに入った後、全候補が `retreat_no_damage_improvement` かつ退却コストありの低評価になっている局面があった。
- 一度退却フェーズへ入ると、API上は提示された交代先から選ぶしかない。
- そのため、根本対策は交代先選択ではなく、退却開始Optionを押す前に止める必要がある。

**原因分析**

- `Policy.score_retreat()` は `retreat_energy_cost` を減点していたが、火力改善・攻撃可能化・KO・生存退却・役割交代のない有料退却を完全には止めていなかった。
- 結果として、退却開始後に「どれを選んでも悪い」交代先選択へ入る可能性が残っていた。

**修正案**

- `score_retreat()` に、以下がすべてない有料退却を `SCORE_FORBIDDEN` にするガードを追加する。
- 対象は `switch_enables_win`、`enables_knockout`、`enables_attack`、`improves_damage`、`survival_retreat`、`role_handoff` のいずれもない退却。
- 生存退却、勝ち筋退却、攻撃可能化、Cinderaceから主軸への役割交代は従来どおり残す。
- 回帰テストで、改善なし有料退却は禁止され、既存の有効退却は維持されることを確認する。

---

## 2026-07-19 / Budewのグッズ封じを圧力対象として扱えていない

**問題**

- 最新参考ログで、相手が `Budew` をバトル場に置き、`Itchy Pollen` でItem使用を止めながら、後ろで `Dreepy` / `Drakloak` / `Dragapult ex` を育てる流れが確認された。
- 現行コードは `Dreepy` / `Drakloak` / `Dragapult ex` を `BENCH_DAMAGE` 対面の圧力対象にしていたが、`Budew` は対象外だった。
- 非KOの `Water Gun` / `Chilly` は弱ワザ抑制により通常候補まで落ちるため、Budewを削る価値が低くなりやすかった。

**原因分析**

- `Budew` は自分のDECKには存在しないが、現行 `CARD_TABLE` に `cardId=235` として存在する相手カード。
- `Budew` の `Itchy Pollen` は `attackId=323`、0エネ10ダメージで、次の相手ターンにItemを使えなくする。
- これはドラパルト系の完成を支える妨害壁として機能するが、対面知識に入っていなかった。

**修正案**

- `BUDEW = 235` を相手カード知識として定数化する。
- `BENCH_DAMAGE` 対面の `must_pressure` と `boss_targets` に `BUDEW` を追加する。
- `target_value()` でBudewを圧力対象として加点する。
- `Water Gun` / `Chilly` が非KOでも対象がBudewなら、通常の弱ワザ抑制まで落とさず、Budewを削る評価を残す。
- KOできるBudew攻撃は既存の攻撃Outcomeで従来どおり最優先になる。

## 2026-07-19 / BENCH_DAMAGE対面でShayminをベンチ保護役として固定できていない

### 問題

- `Dragapult ex` などのベンチ攻撃対面では、`Shaymin` の `Flower Curtain` によるベンチ保護が重要。
- 現行コードは `BENCH_DAMAGE` 対面で `Shaymin` を出す価値は持っていたが、サーチ・捨て札・交代先評価まで一貫して保護役として扱えていなかった。
- そのため、`Shaymin` を拾える局面で優先が足りない、場に出る前に捨てる、またはベンチ固定したい局面でバトル場へ出す余地があった。

### 原因分析

- `score_pokemon_play()` の `Shaymin` 評価は `BENCH_DAMAGE` 対面でも中程度で、主軸展開や一部サーチ評価に埋もれる可能性があった。
- `card_need_score()` に `Shaymin` のベンチ保護需要がなく、山札・探索系の対象として十分に上がらなかった。
- `score_discard()` は `BENCH_DAMAGE` でない場合だけ `Shaymin` を低保護にしており、必要対面での捨て札保護が抜けていた。
- `score_switch_target()` では `Shaymin` を補助役として扱うだけで、ベンチ固定したい対面で前に出すことを明確に抑制していなかった。

### 修正案

- `BENCH_DAMAGE` 対面かつ場に `Shaymin` がいない場合、`Shaymin` のプレイ価値と探索需要を上げる。
- `BENCH_DAMAGE` 対面では、場に出る前の `Shaymin` を捨て札候補から強く保護する。
- `BENCH_DAMAGE` 対面での `Shaymin` 交代先選択は、`survival_retreat` など生存退却の理由がない限り禁止する。
- `Shaymin` は攻撃役ではなくベンチ保護役として扱い、ベンチに維持する方針に寄せる。

## 2026-07-19 / Shaymin保護判定がDragapult・Marnie系に寄りすぎている

### 問題

- `Shaymin` の `Flower Curtain` は、特定デッキ専用ではなく、相手ワザから自分ベンチへのダメージを防ぐ役割。
- 前回修正では `BENCH_DAMAGE` 対面名を条件にしていたため、`Mega Starmie ex` の `Jetting Blow` など、他のベンチダメージワザに対して保護役として扱い切れない可能性があった。
- `Dragapult ex` だけ、または `Marnie` 系だけに寄せると、同じ性質の別デッキに対して再発する。

### 原因分析

- `opponent_profile() == "BENCH_DAMAGE"` は、現行コード上 `DREEPY_LINE` / `Dragapult ex` / `MARIE_LINE` の公開IDに依存していた。
- しかし現行 `ATTACK_TABLE` には、`Jetting Blow` や `Shadow Bullet` のように、テキスト上で相手ベンチへダメージを与えるワザが複数存在する。
- `Shaymin` の保護需要は対面名ではなく、公開されている相手ポケモンがベンチダメージワザを持つか、という事実から判断すべきだった。

### 修正案

- `attack_can_damage_opponent_bench()` を追加し、現行 `ATTACK_TABLE` のワザ本文から相手ベンチへのダメージ・ダメカン影響を判定する。
- `BoardView.opponent_has_bench_damage_threat()` で、公開相手ポケモンのワザだけを確認する。
- `BoardView.needs_shaymin_bench_guard()` を追加し、`Shaymin` のプレイ・サーチ・捨て札保護・交代先抑制をこの事実判定へ接続する。
- `Do the Wave` のような「相手ベンチ数を参照するだけで、相手ベンチへダメージを与えないワザ」は誤検出しない。

## 2026-07-19 / 進化後ベンチ攻撃へのShaymin事前準備が遅れる

### 問題

- 公開されている相手ポケモン自身がまだベンチ攻撃ワザを持っていない場合、進化後にベンチ攻撃ワザを得る相手への `Shaymin` 準備が後追いになる。
- 例として、相手の `Staryu` が見えている時点では、現行ワザだけを見ると `Mega Starmie ex` の `Jetting Blow` を警戒できなかった。
- 進化後に即攻撃されてから `Shaymin` を探すのでは遅い。

### 原因分析

- `opponent_has_bench_damage_threat()` は、公開中の相手ポケモンが現在持つワザだけを見ていた。
- 進化ラインの公開カード知識として `CardData.evolvesFrom` は存在するが、`Shaymin` 保護判定では使っていなかった。
- `DREEPY_LINE` / `MARIE_LINE` は固定集合で事前警戒できていたが、それ以外の進化ラインには一般化されていなかった。

### 修正案

- `card_or_evolution_has_bench_damage_threat()` を追加し、公開中の相手ポケモン自身または現行 `CARD_TABLE` 上の進化先がベンチダメージワザを持つか確認する。
- `opponent_has_bench_damage_threat()` は、現在ワザだけでなく進化先ワザも含めて判定する。
- 非公開手札や次ターン進化の推測は行わず、公開相手ポケモンと `CARD_TABLE` の進化ライン知識に限定する。

## 2026-07-19 / 展開札が合法にあるのにENDを候補へ残す

### 問題

- 参考ログ直下の複数局面で、手札に `Buddy-Buddy Poffin`、`Pokégear 3.0`、`Crispin`、`Lillie's Determination` などが見える状態でENDしていた。
- 現行再採点では、多くの該当局面は既に展開札がENDを上回っていた。
- ただし `score_end()` は、`has_real_development_option()` が真でも `-500000` を返すだけで、候補から完全には除外していなかった。

### 原因分析

- `has_real_development_option()` は、現行Policyが `score_main(option) > 3000` と評価した合法な展開Optionが存在することを表す。
- つまり、Policy自身が「使う価値がある」と認めた合法Optionがある局面では、ENDを通常候補に残す必要がない。
- 有効攻撃が壁で無効な場合など、他に有効な行動がない局面ではENDを禁止しない既存ルールは維持する必要がある。

### 修正案

- `score_end()` で `has_real_development_option()` が真の場合は `SCORE_FORBIDDEN` を返す。
- blocked攻撃しかない局面では、END禁止ガードが誤発火しないことを回帰で確認する。
- `Buddy-Buddy Poffin` など正の展開Optionが合法にある場合は、`choose_indices()` がENDではなく展開Optionを選ぶことを確認する。

## 2026-07-19 / PokégearでSalvatoreを取れる局面の再発防止

### 問題

- 参考ログ `そのポケギア、セイジにつかえよ.json` などで、`Pokégear 3.0` 使用後の選択が疑われていた。
- ログ上の旧選択では `Salvatore` を取るべき局面で別サポートを選ぶ可能性があった。
- ただし現行コードで再採点すると、`Salvatore` が候補にあり `salvatore_live()` が真の局面では `Salvatore = 160000` で最上位になっていた。

### 原因分析

- 現行 `score_card_selection()` の `POKEGEAR` 分岐は、`Salvatore` がライブなら `160000` を返す。
- `Crispin` は `starmie_needs_energy()` が真でも `110000` なので、`Salvatore` が必要な局面では現行評価で上回る。
- そのため本体ロジックの追加修正ではなく、再発防止の回帰テストを追加するのが最小対応。

### 修正案

- `Pokégear 3.0` の `TO_HAND` 選択で、候補に `Salvatore`、`Crispin`、`Lillie's Determination` があり、`salvatore_live()` が真の場合に `Salvatore` を選ぶ回帰テストを追加する。
- 本体のPolicy点数は変更しない。

## 2026-07-19 / 主軸未完成時にLillie's Determinationを軽視する

### 問題

- 参考ログ直下の再採点で、`Staryu` と `Snorunt` が場にいる一方、`Mega Starmie ex` / `Mega Froslass ex` へ触る札が手札にない局面でも、`Lillie's Determination` が通常候補の `8000` に留まっていた。
- この局面では `Crispin` が高評価になり、エネルギーだけ整えて進化先へ到達できない可能性がある。

### 原因分析

- `Policy.score_play()` の `Lillie's Determination` 評価は、少手札または種不足だけを高評価にしていた。
- 主軸が未完成かつ、手札に進化先・`Salvatore`・`Mega Signal`・`Ultra Ball` がない場合でも、山札を回す価値を評価できていなかった。
- 一方で、手札に有効な進化ルートや水エネルギーがある場合は、既存の温存判断を残す必要がある。

### 修正案

- `Lillie's Determination` の評価に、主軸進化ルートが手札にない場合の高評価を追加する。
- `Mega Starmie ex` / `Mega Froslass ex` / `Salvatore` / `Mega Signal` / `Ultra Ball` が手札にない場合だけ、進化先探索として `Lillie's Determination` を優先する。
- 水エネルギーやエネルギー解決札がない場合の補助評価も追加する。
- 既に `Salvatore` や水エネルギーなどの重要札が手札にある場合の温存判断は維持する。

## 2026-07-19 / 加速先なしのTurbo Flareが手札処理より上に残る

### 問題

- 参考ログ直下の再採点で、`Cinderace` がバトル場にいてベンチが空の局面でも、`Turbo Flare` が `8000` で `Pokégear 3.0` の `6000` を上回っていた。
- `Turbo Flare` はエネルギー加速が主目的のワザだが、加速先がない場合は展開札を押しのける価値が薄い。
- 問題は `Pokégear 3.0` 固有ではなく、加速先がない攻撃が攻撃前の手札処理を邪魔すること。

### 原因分析

- `Policy.score_attack()` の `Turbo Flare` 分岐は、`has_bench_energy_receiver()` が真の場合だけ加速ワザとして高評価していた。
- しかし偽の場合でも固定で `8000` を返していたため、低めの展開札より上に残る可能性があった。
- ワザ自体は合法Optionなので完全禁止にはせず、他に実用的な展開Optionがある場合だけ低くする必要がある。

### 修正案

- `Turbo Flare` に加速先がない場合は `0` へ下げる。
- 加速先がある場合の高評価は維持する。
- 加速先がなくても攻撃Optionとしては残すため、他に何もなければENDよりは上に残る。
- `Pokégear 3.0` 以外の低めの手札処理も、加速先なし `Turbo Flare` より優先できるようにする。

## 2026-07-19 / ベンチ空で非KO弱攻撃を基本ポケモン展開より優先する

### 問題

- 参考ログ直下の再採点で、`Staryu` がバトル場、ベンチ空、手札に `Snorunt` / `Yveltal` がある局面でも、非KOの `Water Gun` が基本ポケモンを置く行動より上に残っていた。
- ベンチ空のまま弱攻撃を続けると、後続を作れず、主軸完成前に押し切られる。

### 原因分析

- `Policy.score_attack()` は、`Water Gun` / `Chilly` が非KOかつ展開Optionありの場合でも、通常は `30000 + damage * 100` を返していた。
- この値は `Snorunt` や `Yveltal` のベンチ展開評価を上回るため、ベンチが空でも弱攻撃が残った。
- ただし相手 `Budew` への圧力は別Issueで重要と判断済みなので、そこは例外として維持する必要がある。

### 修正案

- `Water Gun` / `Chilly` が非KOで、展開Optionがあり、相手が `Budew` ではなく、こちらのベンチが空の場合は弱攻撃評価をさらに下げる。
- `Budew` への圧力評価は維持する。
- ベンチが既にある局面の弱攻撃抑制は従来どおり維持する。

## 2026-07-19 / 補助役activeの非KO弱攻撃が手札処理より上に残る

### 問題

- 参考ログ直下の再採点で、`Shaymin` がバトル場にいる局面でも、非KOの `Smash Kick` が `Lillie's Determination` や `Pokégear 3.0` を上回っていた。
- `Shaymin` はベンチ保護役であり、30ダメージを撃つために手札処理を止める役割ではない。

### 原因分析

- `Policy.score_attack()` は、基本的に有効攻撃へ `SCORE_PREFERRED + damage * 100` を与える。
- `Water Gun` / `Chilly` や `Turbo Flare` には個別抑制が入っていたが、`Shaymin` など補助役の非KO弱攻撃には同じ抑制がなかった。
- KO攻撃まで下げると取り切れる局面を逃すため、非KOかつ手札処理がある場合だけ抑制する必要がある。

### 修正案

- activeが `Shaymin` または通常 `Froslass` で、攻撃が非KOかつ `has_real_development_option()` が真の場合、攻撃評価を低くする。
- KOできる攻撃は従来どおり攻撃優先に残す。
- `Cinderace`、`Yveltal`、主軸メガの攻撃評価には触れない。

## 2026-07-19 / Cinderaceへの基本エネ手貼りが主軸ベンチを上回る

### 問題

- 参考ログ直下の再採点で、`Cinderace` がバトル場、ベンチに `Staryu` がいる局面でも、基本エネルギーの手貼り先として `Cinderace` が `Staryu` を上回っていた。
- `Cinderace` は加速役だが、このデッキの主軸は `Staryu` / `Mega Starmie ex` なので、主軸ベンチがいるなら基本エネルギーはそちらを優先したい。

### 原因分析

- `score_water_attach()` は、`Cinderace` が0エネかつベンチにエネルギー受け先がある場合 `98000` を返していた。
- さらに `ImmediateOutcome` の `enables_attack` 加点が乗り、`Cinderace` への水エネルギーが `Staryu` への水エネルギーを上回る局面があった。
- `score_dark_attach()` でも `Cinderace` の0エネ起動評価が高く、基本悪エネルギーも補助役へ流れやすかった。
- `Ignition Energy` は即時 `Turbo Flare` 起動の別問題になり得るため、今回は基本水・基本悪だけを対象にする。

### 修正案

- `Cinderace` への基本水エネルギー初回評価を下げ、主軸ベンチへの水エネルギーを上回らないようにする。
- `Cinderace` への基本悪エネルギー初回評価も下げ、主軸ベンチより優先しないようにする。
- `Cinderace` の加速役としての価値自体は残し、`Ignition Energy` や `Turbo Flare` 評価には触れない。

## 2026-07-19 / CinderaceへのIgnition Energy即Turboが展開札を潰す

### 問題

- 参考ログ直下の再採点で、`Cinderace` へ `Ignition Energy` を付けて即 `Turbo Flare` へ向かう評価が `1220000` になり、`Buddy-Buddy Poffin`、`Ultra Ball`、`Pokégear 3.0` などの展開札を大きく上回っていた。
- `Turbo Flare` は有用だが、主軸が未完成のまま加速だけ先行すると、攻撃前の手札処理を飛ばす問題が再発する。

### 原因分析

- `score_attach()` は、`Ignition Energy` によって現在activeが即時有効攻撃へ到達すると、`SCORE_PREFERRED + 220000` を返していた。
- これは主軸メガが本命技へ到達する局面では有効だが、`Cinderace` の即 `Turbo Flare` でも同じ強評価になっていた。
- 手札に展開札がある場合、`Cinderace` への即時起動より、先に主軸を探す・置く・進化へ触る方が重要な局面がある。

### 修正案

- `Ignition Energy` の対象が `Cinderace` で、手札に `Buddy-Buddy Poffin` / `Ultra Ball` / `Salvatore` / `Mega Signal` / `Pokégear 3.0` / `Mega Starmie ex` がある場合は、即時攻撃評価を下げる。
- 主軸メガへの `Ignition Energy` 即時攻撃評価は維持する。
- `Turbo Flare` や通常の主軸攻撃スコアには触れない。

## 2026-07-19 / Mega Froslass exをサブアタッカーとして育てにくい

### 問題

- `Mega Froslass ex` はサブアタッカーとして使う方針だが、現行評価では `Snorunt` / `Mega Froslass ex` の育成価値が `Alakazam` 対面に寄りすぎていた。
- `Staryu` / `Mega Starmie ex` を主軸にする方針は維持しつつ、サブアタッカーとして最低限育てる価値を持たせる必要がある。

### 原因分析

- `score_water_attach()` では、`Snorunt` への水エネルギーが `Alakazam` 以外で低めだった。
- `Mega Froslass ex` への水エネルギーも、`Alakazam` / `BENCH_DAMAGE` 以外ではかなり低く、育成対象として残りにくかった。
- `card_need_score()` と `score_evolve()` でも、`Mega Froslass ex` は汎用サブアタッカーとしては軽く扱われていた。

### 修正案

- `Snorunt` への水エネルギー評価を汎用的に引き上げる。ただし `Staryu` への水エネルギーよりは下に置く。
- `Mega Froslass ex` への水エネルギー、進化、サーチ需要を引き上げる。
- `Alakazam` 対面では従来どおり高めに維持し、その他対面でもサブアタッカーとして切り捨てない。

## 2026-07-19 / Ignition Energyを非メインへ使いすぎる

### 問題

- `Ignition Energy` は1枚しかないため、`Cinderace` や補助役へ雑に使うと、`Mega Starmie ex` / `Mega Froslass ex` の本命技到達が遅れる。
- 方針としては、`Mega Starmie ex` が主軸、`Mega Froslass ex` がサブアタッカー、`Alakazam` 対面では `Mega Froslass ex` がメイン寄り。
- `Shaymin`、`Yveltal`、`Cinderace` など非メインへ流れるのは避けたい。

### 原因分析

- `score_attach()` は、`Ignition Energy` で新しく攻撃可能になる場合に一律 `70000` を返していた。
- そのため、`Mega Starmie ex`、`Mega Froslass ex`、`Cinderace` が同じ評価になる局面があった。
- `Cinderace` は加速役だが、`Ignition Energy` を使ってまで起動するより、メガに温存して本命技を速める方が基本方針に合う。

### 修正案

- `Ignition Energy` の対象順位を明確にする。
- `Mega Starmie ex` への本命技到達を最優先にする。
- `Mega Froslass ex` への本命技到達をサブアタッカーとして次点にする。
- `Cinderace` への `Ignition Energy` は大きく下げ、非メイン扱いにする。
- `Shaymin` / `Yveltal` など攻撃到達しない補助役は従来どおり低評価にする。

## 2026-07-19 / ベンチ空の主軸メガが非KO攻撃で再建を後回しにする

### 問題

- 参考ログ直下の再採点で、`Mega Starmie ex` がバトル場、ベンチ空、手札に `Buddy-Buddy Poffin` / `Night Stretcher` などがある局面でも、非KOの `Jetting Blow` が再建札を大きく上回っていた。
- 主軸メガの攻撃は重要だが、ベンチ空のまま非KO攻撃を続けると、倒された後の後続がなくなる。

### 原因分析

- `Policy.score_attack()` は主軸メガの有効攻撃に高い基礎点を与えている。
- KOや即時勝利なら正しいが、ベンチ空かつ再建札が手札にある場合でも同じ強さで攻撃が残っていた。
- 主軸攻撃を雑に下げると勝ち筋を失うため、条件をベンチ空・非KO・再建札ありに限定する必要がある。

### 修正案

- activeが `Mega Starmie ex` / `Mega Froslass ex`、攻撃が非KO、ベンチ空、手札に `Buddy-Buddy Poffin` / `Night Stretcher` / `Ultra Ball` / `Pokégear 3.0` / `Lillie's Determination` がある場合だけ、攻撃評価を下げる。
- KO攻撃と即時勝利攻撃は従来どおり攻撃優先に残す。
- ベンチがある局面の主軸攻撃には触れない。

## 2026-07-19 / Turbo Flareが攻撃前の主軸展開札を飛ばす

### 問題

- 参考ログ直下の再採点で、`Cinderace` がバトル場、ベンチにエネルギー受け先がある局面でも、`Turbo Flare` が `Ultra Ball` などの主軸展開札を上回っていた。
- `Turbo Flare` は加速役として必要だが、攻撃を選ぶとそのターンの手札処理が終わるため、先に使える展開札を飛ばすと主軸完成が遅れる。

### 原因分析

- `Policy.score_attack()` の `Turbo Flare` 分岐は、ベンチにエネルギー受け先があると `SCORE_PREFERRED` 帯で評価していた。
- 加速先がない場合の抑制はあったが、加速先がある場合でも手札に `Buddy-Buddy Poffin` / `Ultra Ball` / `Pokégear 3.0` / `Salvatore` などがある局面を区別していなかった。
- そのため、攻撃前に使うべき手札があるのに、先に攻撃してターンを閉じる評価になっていた。

### 修正案

- `Turbo Flare` が使用可能で、ベンチにエネルギー受け先がある場合でも、手札に主軸展開札があるなら攻撃評価を下げる。
- 対象カードは `Buddy-Buddy Poffin` / `Ultra Ball` / `Pokégear 3.0` / `Salvatore` / `Mega Signal` / `Lillie's Determination` / `Crispin` / `Night Stretcher` に限定する。
- 手札に展開札がない場合の `Turbo Flare` 評価は残し、加速役としての役割は維持する。

## 2026-07-19 / Yveltal単騎でDark Energyより主軸探索を優先する

### 問題

- `動きが最悪.json` / `86712972.json` の候補分析で、active `Yveltal`、ベンチ空、手札に `Ultra Ball` / `Crispin` / `Salvatore` がある局面でも、`Basic {D} Energy` 手貼りが `Ultra Ball` を上回る疑いがあった。
- `Yveltal` は妨害・壁役として使えるが、単騎のまま悪エネルギーを貼って攻撃に寄せると、主軸である `Staryu` / `Mega Starmie ex` の展開が遅れる。

### 原因分析

- `score_dark_attach()` は `Yveltal` への基本悪エネルギーを常に `36000` としていた。
- さらに `ImmediateOutcome` の `enables_attack` 加点 `70000` が乗るため、単騎でも合計 `106000` となり、`Ultra Ball = 85000` を上回る局面があった。
- ベンチがある局面や、手札に展開札がない局面まで下げると `Yveltal` の役割を失うため、条件を単騎・active・主軸展開札ありに限定する必要がある。

### 修正案

- `Yveltal` がactive、ベンチ空、手札に `Buddy-Buddy Poffin` / `Ultra Ball` / `Pokégear 3.0` / `Salvatore` / `Mega Signal` / `Lillie's Determination` / `Crispin` がある場合だけ、基本悪エネルギー手貼りの基礎点を下げる。
- `enables_attack` 加点は残すが、合計が `Ultra Ball` を上回らないようにする。
- ベンチがある場合や展開札がない場合の `Yveltal` 運用には触れない。

## 2026-07-19 / Cinderace単騎でIgnition Energyを消費する

### 問題

- 地下闘技場の提出前1戦回帰で、active `Cinderace`、ベンチ空、手札に `Pokégear 3.0` がある局面でも、`Ignition Energy -> Cinderace` が `Pokégear 3.0` を上回っていた。
- `Ignition Energy` は1枚しかなく、ベンチに加速先がない `Cinderace` へ使うと、主軸メガの本命技到達が遅れる。

### 原因分析

- `score_attach()` は `Ignition Energy` の対象が `Cinderace` の場合、ベンチにエネルギー受け先がなくても `12000` を返していた。
- `Cinderace` の `Turbo Flare` はベンチへのエネルギー加速が主目的なので、ベンチなしでは `Ignition Energy` を消費する価値が低い。

### 修正案

- `Ignition Energy` の対象が `Cinderace` で、`has_bench_energy_receiver()` が偽なら `-40000` にする。
- ベンチに主軸エネルギー受け先がある場合の `Cinderace` 起動評価は残す。
- 主軸メガへの `Ignition Energy` 評価には触れない。

---

## 今後の追記方針

今後のKaggleリプレイ改善は、次の形でこのファイルへ追記する。

1. 事実として確認できた問題だけを書く。
2. 原因分析は現行正本だけを根拠にする。
3. 修正案は最小差分に限定する。
4. 修正後は、実ログ再採点または地下闘技場シナリオで再発確認する。
5. 旧実装や過去バックアップから仕様を持ち込まない。

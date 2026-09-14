# ゆうじ自筆パック v2 — v8 構成版(2026-09-02 夕方に差し替え。執筆予定 9/7、約5h)

v1(v7 構成向け)は D85 の裁定で無効。**主役が最終エージェントに変わった**ので、自筆する3箇所も変わる。
共通ルール: 数値は「残す事実」から一字も変えず、増やさない(台帳に無い数値は書けない)。長さは目安 ±20%。
日本語で書けば私が英訳(その段落の英語は Claude の語選択に戻る)。**英語で直接書けば最小修正のみ**。
構成・順序・一人称は自由。現行文は器であって手本ではない。台帳タグ [#N] は後で私が付け直す。

---

## 箇所A: §3 冒頭 — 実局面と、ボスの指令の価値序列(現行 約230語 → 目安 200〜260語)★最重要

**現行英文(2段落)**:
> Turn ten of a ladder game against Mega Lucario ex. Our Mega Starmie ex sits at 60 HP with one Water attached;
> the opponent's Mega Lucario ex is at 90 of 440, two prizes from winning against our four. Jetting Blow for 120
> knocks it out for three prizes. The agent played Boss's Orders instead, dragged an 80-HP Makuhita forward, took
> one prize, and lost to the reply on the next turn.
>
> The value ordering it should have used is the one a player uses, and it is in the code: knock out what you can
> knock out now, most prizes first; failing that, drag out the piece that will evolve into a threat, Riolu before it
> becomes Mega Lucario; failing that, the piece that cannot retreat, so the opponent's energy attachment is held
> hostage. Over the last 1,000 games the agent's 809 Boss's Orders went to knock-outs 577 times, to evolving threats
> 184 times, to bound targets 16 and to the weakest piece 32. The turn above is not a failure of the ordering.
> The greedy layer proposed something else; the engine lookahead overrode it into Boss's Orders, and the gates let
> it, because every gate protects the greedy choice from the lookahead and none stops the lookahead from reaching
> for Boss's Orders on its own (Fig. 1).

**日本語逆訳**: メガルカリオ戦の第10ターン。こちらのメガスターミーexは残りHP60、水1個。相手のメガルカリオexは
残り90(最大440)。相手はあと2枚、こちらはあと4枚。ジェットブロー120で倒せば3枚。AIはボスの指令を使って
HP80のマクノシタを引きずり出し、1枚取って、返しのターンに負けた。/ 使うべきだった序列はプレイヤーが使うもので、
コードにも入っている: 今倒せるものを倒す(枚数の多い順)→ 脅威に育つ前の駒を引き出す(リオルがメガルカリオに
なる前)→ 逃げられない駒を前に縛る(相手の手貼りを人質に)。直近1,000譜で809回のボスは、KO 577・進化前 184・
縛り 16・最弱 32。第10ターンの失敗は序列の失敗ではない — 貪欲層は別の手を出し、探索がボスに上書きし、門は
それを止めなかった(門は貪欲層の選択を探索から守るだけで、探索が勝手にボスへ手を伸ばすのは止めない)。

**残す事実**: 60/330・エネ1 / 相手 90/440 / サイド 自4・相手2 / ジェットブロー120で3枚 / マクノシタ80 / 809回の内訳 577・184・16・32 / 「序列の失敗ではなく探索の上書き」[#39]。
**ここはゆうじのパターン(yuji-card-patterns)そのもの。** 「なぜこの順序か」をプレイヤーの言葉で。リオル/メガルカリオ/マクノシタ/ソルロックは実局面にある名前なので出してよい。

---

## 箇所B: §3 第3段落 — 7月の退却病理(現行 約150語 → 目安 120〜170語)

**現行英文**:
> That unguarded direction is a family trait. In July a replay showed the agent retreating a fully-powered attacker
> rather than attacking a Mega Lucario it could not one-shot; fed that board, the production pilot chose RETREAT 12
> of 12 times while the greedy layer said ATTACK. The cause was an override margin of 120 against a prize term of
> ±10,000: the margin gated nothing. We repaired the decision, reproduced ATTACK 12 of 12, and the repaired bundle
> measured +6.03pt (N=6,400, pre-registered); then the pre-registered falsification sensor fired, the matchup where
> the retreat is most frequent getting worse by 1.37pt. The bundle stayed; the mechanism story was withdrawn.

**日本語逆訳**: 守られていない方向は家系的な癖だ。7月、リプレイで、エネ満タンのアタッカーが一撃で倒せない
メガルカリオを前に攻撃せず退却するのを見つけた。その盤面を食わせると本番パイロットは12回中12回退却、貪欲層は
攻撃。原因は上書きマージン120に対しサイド項が±10,000で、マージンは何も堰き止めていなかった。修理して12/12攻撃、
束で+6.03pt。ところが事前登録した反証センサーが鳴った — 退却が最も多い対面が1.37pt悪化。採用は残し、
「修理が効いた」という物語は撤回した。

**残す事実**: 12/12 → 12/12 [#33] / 120 vs ±10,000 [#27] / +6.03(N=6,400、事前登録)[#32] / −1.37 [#33]。
**発見者はゆうじ本人**。一人称で書いてよい(「私が見つけた」)。

---

## 箇所C: §2 冒頭 — デッキの勝ち筋をプレイヤーの言葉で(現行 約110語 → 目安 90〜130語)

**現行英文**:
> The list (Fig. 2) runs 4 Staryu, 4 Mega Starmie ex, 12 Water and 4 Ignition Energy, nineteen Supporters, fourteen
> Items, two Surfing Beach and a Deluxe Bomb. The plan is a race: Mega Starmie ex takes three prizes from an
> opposing Mega ex, or two and one with the 50-damage bench splash, and Wally's Compassion heals it and returns the
> energy for a second run. In the last 1,000 ladder games the one-energy Jetting Blow (120, plus 50 to the bench)
> was 71.4% of all attacks; the three-energy Nebula Beam (210) was the finisher at 18.5%. The paper plan was a
> 210-damage deck; the play plan is a 120-plus-50 deck, and only the replays told us which we had.

**日本語逆訳**: リストは ヒトデマン4・メガスターミーex4・水12・イグニッション4、サポート19・グッズ14、
なみのりビーチ2、デラックスボム1。プランはレース: メガスターミーexが相手のメガexから3枚、または本体2枚+
ベンチ50で1枚。ミツルの思いやりで全回復してエネを手札に戻し、もう一走り。直近1,000譜では1エネのジェットブロー
(120+ベンチ50)が全攻撃の71.4%、3エネのネビュラビーム(210)は締めで18.5%。紙の上では210のデッキ、
実戦では120+50のデッキだった — リプレイを読むまで分からなかった。

**残す事実**: 60枚の内訳(上記)/ 3枚 or 2+1 / ミツル=回復+エネ回収 / 71.4% と 18.5% [#46] / 紙vs実戦 [#30]。
ポケカ勢に「このデッキはこう勝つ」と一文で伝わる書き方を。

---

## 進め方(変更なし)
1. 9/7 にゆうじが書く(日本語 or 英語)。このファイルへの追記でも別ファイルでも。
2. 私が英訳(or 最小修正)→ 台帳タグ → `t6_check.py` → 差分提示。語数の余白は 102 語(公開版 1,858 / 1,960)。
3. 溢れたら削るのは私の地の文。あなたの文は削らない。

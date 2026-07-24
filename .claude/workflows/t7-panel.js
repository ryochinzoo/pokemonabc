export const meta = {
  name: 't7-panel',
  description: 'T7設計レビューのパネル型v2 — 斥候→4レンズ発見→dedup→異モデル検証→編集長裁定',
  whenToUse: 'パイロット側実験や複雑な事前登録を起動する前(playbook §7 T7)。デッキ1行差分などの単純登録は単独T7で足りる',
  phases: [
    { title: 'Scout', detail: '一次資料を抽出して共有コンテキストパックを作る' },
    { title: 'Find', detail: '統計/ドメイン/実装/前提挑戦の4レンズが独立に指摘を出す' },
    { title: 'Verify', detail: '別モデルが独立再導出できるかで confirmed を判定' },
    { title: 'Adjudicate', detail: '編集長が「実験の結果を変えるか」で採否を裁定' },
  ],
}

// args = { target: '<レビュー対象の記述+ファイルパス>', sources: ['path', ...] }
const TARGET = args?.target || '(未指定)'
const SOURCES = args?.sources || []

const RULES = `
## このレビューの規則(playbook §7 T7)
- **既存決定・主席エージェントの推奨への遠慮を明示的に禁止する。** 反対意見は歓迎される。
- **bench.py / selfplay.py / 実測スクリプトの実行は禁止**(CPUは測定用に予約されている)。
  Read/Grep/Globでのコード・ドキュメントの精読は必須。
- **要約を信用しない。** 主張の裏は必ず一次資料(コード本体・data.md・decisions.md)で当たる。
- 指摘には必ず「根拠のファイル:行」と「これが正しければ実験結果がどう変わるか」を付ける。
  根拠を示せない直感は出さない。
`

const CONTEXT_FILES = SOURCES.map(s => `- ${s}`).join('\n')

phase('Scout')
const pack = await agent(
  `あなたはT7レビューパネルの斥候。レビュー対象は次のとおり:

${TARGET}

${RULES}

次の一次資料を実際に読み、**発見レンズ4人が共有するコンテキストパック**を作れ:
${CONTEXT_FILES}

パックに含めるもの:
1. レビュー対象の事前登録の全文要点(改変せず、決定的な数値・閾値・格子・N・判定規則を漏らさない)
2. 関連する既存決定の該当箇所(ファイル:行つき)。特に D18/D19(v3棄却の機構)、D29(判定規則)、
   D38(Neyman/検定力)、D42(先行ゲート=存在と発生率)、D44(本番適合)、D48(パネルv1の欠陥)、
   D49(E3のkill)、D51(今回の運用変更)
3. 該当コードの構造(starmie-aggro/main.py の探索まわり、verification/ の計器)を、
   行番号つきで。特に壁時計を読む箇所・上書き判定の条件・run_series の席交換
4. 直近の実測値(data.md「★計器監査」節)の数値表
5. **レビュワーが自分で検算すべき箇所のリスト**(数値・統計・機構の主張ごとに)

出力はそのまま4人に配れる形の構造化テキスト。憶測を混ぜず、読んだ事実だけを書け。`,
  { label: 'scout', phase: 'Scout', model: 'sonnet' }
)

const LENSES = [
  {
    key: 'stats',
    title: '統計・実験計画レンズ',
    brief: `検定力・多重比較・推定量・判定規則の妥当性を見る。特に:
- 傾向(傾き)検定の設計は正しいか。加重最小二乗の重みは何であるべきか。アーム間の分散不均一は?
- 「検出可能な傾き±0.88pt/倍化」の算出は正しいか。**自分で再計算せよ**(SE 1.85pt/アーム、
  log2(det)の6点、SD(x)=1.708 という前提を含めて検算する)。
- CEW-lite(2成分84.3%を58.1:41.9で再正規化)はCEWの不偏な代理か。落とした2成分が
  アームによって非対称に効く可能性は? 基準線41.03はCEW-liteには使えないはずだが登録はどう扱っているか。
- N=600/アームのNeyman的配分(349/251)は最適か。
- Phase A→Phase B の勝者の呪いの扱いは十分か。傾き有意でargmaxを選ぶ手続きの選択バイアスは?
- H0のときの結論の書き方(上界としての記録)は主張として正当か。`,
  },
  {
    key: 'domain',
    title: 'ドメイン(PTCG+エンジン機構)レンズ',
    brief: `ゲーム機構とエンジンAPIの側から見る。特に:
- determinizationを増やすと本当に最大化バイアスは減るか。_determinize の隠れ情報の作り方
  (_infer_enemy_deck のメタ辞書被覆率、未知アーキタイプ時のフォールバック)に系統誤差はないか。
  **相手デッキ推定が間違っていれば、detを増やしても間違った分布に収束するだけではないか。**
- _evaluate の裾(エンジン拒否手の-1e6、終局評価)がdetの増加でどう振る舞うか。
  「候補内SD中央値14.5 / p90 4587」という実測はこの設計にとって何を意味するか。
- ロールアウトが root_turn+2 で止まる設計、_ROLLOUT_MAX_STEPS=60、_MAX_CANDIDATES=24 は
  detを上げたときにボトルネックにならないか。**detより先に上げるべき軸はないか。**
- CEWゲージ4種の対面特性から見て、CEW-liteに残す2成分の選択は妥当か。
- 本番バンク600秒に対する安全弁5.0秒の設定は、実対戦の判断回数分布から見て安全か。`,
  },
  {
    key: 'impl',
    title: '実装・堅牢性レンズ',
    brief: `コードとハーネスの側から見る。特に:
- G0-1の差分テスト(random.getstate/setstate による対比較)は**本当に成立するか**。
  _search_decide は SearchBegin/SearchStep/SearchEnd を呼ぶ。同一意思決定で2回呼ぶと
  エンジン側の状態(_agent_ptr、searchId、内部RNG)が汚染されないか。**main.py を実読して判定せよ。**
  成立しないなら代替の等価性証明を提案せよ。
- 安全弁を0.6→5.0秒にすることの提出時リスク。agent()の契約違反・タイムアウト・
  遅い相手との相互作用。_env_int 型の外出しはimport時例外を確実に避けているか。
- 並列ハーネスの設計欠陥: Battle.battle_ptr のグローバル性、run_series の i%2 席交換と
  チャンク分割、ワーカー部分失敗、__pycache__ 競合、cg バイナリ共有。
- 変種dirの作り方(王者を汚さない保証)。ライブ・りょーちんdirへの誤爆経路。
- 「並列時最悪でも安全弁の1/3以下」を**どうやって全数で保証するか**(サンプリングでは不十分)。`,
  },
  {
    key: 'premise',
    title: '前提挑戦レンズ(D48-追記で新設)',
    brief: `**この実験を今やるべきかそのものを疑う。** 他の3人が設計の中身を見るのに対し、
あなたはフレームを疑うのが仕事。特に:
- 目的関数はStrategy部門(Model 70%/Deck 20%/Report 10%、LB順位は配点の約14%)。
  **残り期間(実験終了8/8・凍結8/13・レポート9/12、本日7/25)で、E4はこの目的関数に対して
  最善の資源配分か。** 対抗する使い道(穴D、writeupの肉付け、りょーちん統合、ベスト2本復帰)と
  比較して論じよ。
- 「本番予算の0.2%しか使っていない」は本当に**行動可能な**余地か。それとも
  「探索の設計上、それ以上使う先がない」だけか。detを上げても同じ分布を厚くサンプルするだけで
  情報が増えない可能性を検討せよ。
- D18/D19でv3が棄却された論拠は「決定化MCTSは教科書で差別化不可、197本中に同型多数」。
  **E4が成功しても独自性の主砲になるのか**、それとも既存の背骨(較正法則・三部作)を薄めるだけか。
- D51は「実験フェーズ終了(D49)を撤回」している。**この撤回は正当か。**
  サンクコストや「何かしていたい」バイアスが働いていないか。
- **E4をやらない場合の最善手**を1つ、具体的に対案として出せ。`,
  },
]

const FINDING_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string', description: '指摘の一文要約' },
          severity: { type: 'string', enum: ['致命', '重大', '中', '軽微'] },
          evidence: { type: 'string', description: '根拠のファイル:行と、実際に読んだ内容' },
          impact: { type: 'string', description: 'これが正しければ実験結果がどう変わるか' },
          fix: { type: 'string', description: '具体的な修正案' },
        },
        required: ['title', 'severity', 'evidence', 'impact', 'fix'],
      },
    },
    verdict: { type: 'string', enum: ['このまま起動可', '修正してから', '設計やり直し'] },
  },
  required: ['findings', 'verdict'],
}

phase('Find')
const found = await parallel(LENSES.map(L => () =>
  agent(
    `あなたはT7レビューパネルの**${L.title}**。レビュー対象:

${TARGET}

${RULES}

## 斥候が用意した共有コンテキストパック
${pack}

## あなたのレンズ
${L.brief}

パックは出発点にすぎない。**必ず自分で一次資料(コード・data.md・decisions.md)を開いて検算せよ。**
他のレンズの担当領域には踏み込まなくてよい。指摘がない項目は無理に作らない
(D48-追記の欠陥④「22/22採用のラチェット」を避けるため、**確信の持てない指摘は出さない**)。`,
    { label: `find:${L.key}`, phase: 'Find', schema: FINDING_SCHEMA }
  ).then(r => ({ lens: L.key, ...r }))
))

const alive = found.filter(Boolean)
const allFindings = alive.flatMap(r => (r.findings || []).map(f => ({ ...f, lens: r.lens })))

// --- dedup(コードで行う。エージェントを使わない) ---
const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9ぁ-んァ-ヶ一-龠]/g, '').slice(0, 60)
const seen = new Map()
for (const f of allFindings) {
  const k = norm(f.title)
  if (seen.has(k)) {
    const prev = seen.get(k)
    prev.lens = `${prev.lens}+${f.lens}`
    prev.evidence = `${prev.evidence}\n[別レンズ] ${f.evidence}`
  } else {
    seen.set(k, { ...f })
  }
}
const deduped = [...seen.values()]
log(`発見 ${allFindings.length}件 → dedup後 ${deduped.length}件 / レンズ判定: ${alive.map(r => `${r.lens}=${r.verdict}`).join(', ')}`)

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          status: { type: 'string', enum: ['confirmed', 'refuted', 'overstated'] },
          rederivation: { type: 'string', description: '自分で独立に再導出した過程と結論' },
          correction: { type: 'string', description: '指摘側の誇張・数値誤りがあれば具体的に訂正' },
        },
        required: ['title', 'status', 'rederivation', 'correction'],
      },
    },
  },
  required: ['results'],
}

// 4バッチに分けて検証(発見層とは異なるモデル = D48-追記の多様性装置)
const BATCHES = [[], [], [], []]
deduped.forEach((f, i) => BATCHES[i % 4].push(f))

phase('Verify')
const verified = await parallel(BATCHES.map((batch, i) => () => {
  if (!batch.length) return Promise.resolve({ results: [] })
  return agent(
    `あなたはT7パネルの**検証層**。発見層とは別のモデルで動いており、役割は
「指摘を独立に再導出できるか」を確かめることだ。

${RULES}

## 判定基準(D48-追記でv1から強化)
- **自分で一次資料から独立に同じ結論に到達できた → confirmed**
- 到達できず、かつ指摘が誤りだと示せた → refuted
- 核は正しいが数値・強度が誇張されている → overstated(**必ず正しい数値に訂正して書く**)
- 「反証できなかったから confirmed」は**禁止**。立証責任は再導出の側にある。

## 共有コンテキストパック
${pack}

## 検証対象(${batch.length}件)
${batch.map((f, j) => `### ${j + 1}. [${f.severity}] ${f.title}
- 根拠(指摘側): ${f.evidence}
- 影響(指摘側): ${f.impact}
- 修正案(指摘側): ${f.fix}`).join('\n\n')}

各件について、必ず自分でファイルを開いて再導出せよ。`,
    { label: `verify:batch${i + 1}`, phase: 'Verify', schema: VERIFY_SCHEMA, model: 'sonnet' }
  )
}))

// --- 検証結果の突合 ---
// 初版のバグ: タイトル文字列で突合していたが、検証層はプロンプト中の見出し
// 「### 3. [致命] ...」をそのまま title に echo するため一致せず、**38件全部が
// verify=null → refuted 扱いで消えた**（編集長に指摘本体が1件も届かなかった）。
// 位置による突合を主、正規化タイトルを従にする。§6の失敗パターン#4「部分失敗の黙殺」を
// 自分でやっていた実例。
const vmap = new Map()
for (const v of verified.filter(Boolean)) {
  for (const r of (v.results || [])) {
    // 「1. [致命] 」のような接頭辞を落としてから正規化する
    const stripped = (r.title || '').replace(/^\s*\d+\s*[.．)]\s*(\[[^\]]*\]\s*)?/, '')
    vmap.set(norm(stripped), r)
  }
}
const merged = []
BATCHES.forEach((batch, bi) => {
  const res = (verified[bi] && verified[bi].results) || []
  batch.forEach((f, j) => {
    // 主: 同一バッチ内の位置で対応づける（件数が一致するときだけ信頼する）
    let v = res.length === batch.length ? res[j] : null
    if (!v) v = vmap.get(norm(f.title)) || null
    merged.push({ ...f, verify: v })
  })
})
const unmatched = merged.filter(f => !f.verify).length
if (unmatched) log(`⚠ 検証結果と突合できなかった指摘が ${unmatched}件ある（集計バグの疑い）`)
const survivors = merged.filter(f => f.verify && f.verify.status !== 'refuted')
const killed = merged.filter(f => f.verify && f.verify.status === 'refuted')
log(`検証: confirmed/overstated ${survivors.length}件、refuted ${killed.length}件、突合不能 ${unmatched}件`)

phase('Adjudicate')
const verdict = await agent(
  `あなたはT7パネルの**編集長**。裁定基準はただ一つ:
**「この指摘を採用すると、実験の結果や結論が変わるか」**。

D48-追記が特定したv1の欠陥⑤「重要度の裁定者がおらず22/22採用のラチェットになった」を
直すのがあなたの役割だ。**全件採用は失敗**とみなす。採る・落とす・保留を必ず振り分けよ。

${RULES}

## レビュー対象
${TARGET}

## 共有コンテキストパック
${pack}

## 検証を通った指摘(${survivors.length}件)
${survivors.map((f, i) => `### ${i + 1}. [${f.severity}] ${f.title} (lens=${f.lens}, ${f.verify.status})
- 根拠: ${f.evidence}
- 影響: ${f.impact}
- 修正案: ${f.fix}
- 検証層の再導出: ${f.verify.rederivation}
- 検証層の訂正: ${f.verify.correction}`).join('\n\n')}

## 検証層が棄却した指摘(${killed.length}件) — 棄却の当否もあなたが裁定する
D48-追記の欠陥⑦対策: 検証層が落とした指摘を編集長に見せないと、パネルは単独T7以下になる。
**棄却理由が弱いと判断したものは復活させてよい。**
${killed.map((f, i) => `### R${i + 1}. [${f.severity}] ${f.title} (lens=${f.lens})
- 指摘の根拠: ${f.evidence}
- 検証層の棄却理由: ${f.verify.rederivation}
- 検証層の訂正: ${f.verify.correction}`).join('\n\n') || '(なし)'}

## 各レンズの総合判定
${alive.map(r => `- ${r.lens}: ${r.verdict}`).join('\n')}

## 著者からの申し送り(パネル走行中に判明した層S実測 — v2の凍結規約の欠落による)
パネル起動後、著者が追加の層S測定を行い、次の3点が判明している。**これらを踏まえて裁定せよ。**
1. **G0-1は実測で棄却**: 同一関数を2回呼びRNGを巻き戻しても自己不一致 6.31%(N=2,788組)。
   非決定性の源はエンジン内部PRNG(2回目の例外は0件=再入汚染ではない)。ビット一致証明は不可能。
2. **二次エンドポイント案(安定性 vs det)も測って棄却**: det 2/8/16 で 5.34/5.63/5.05% と完全に平坦。
3. **推定量軸が det 軸を上回った**: 発火率が mean/k=2 の16.4% に対し、
   det を4倍(k=8)にして14.1%、**推定量を min に変えるだけ(計算量同一)で12.9%**。
なお著者はコードを実読し、main.py:714/716 終局±1e9・:721 サイド±10,000/枚に対し
:605 _OVERRIDE_MARGIN=120.0 である**スケール階層**を確認済み。

出力(この順で、簡潔に):
1. **総合判定**: このまま起動可 / 修正してから / 設計やり直し
2. **必須修正**(実験結果を変えるもの。番号+一文で、修正後の具体的な文言・数値まで)
3. **任意修正**(質は上がるが結果は変わらない)
4. **却下**(採らない指摘と、その理由)
5. **前提挑戦レンズへの応答**: E4を今やるべきかの結論と、対案を採るなら何を
6. **パネルが見落とした可能性がある領域**(自己批判。1〜2点)`,
  { label: 'editor', phase: 'Adjudicate' }
)

return {
  lensVerdicts: alive.map(r => ({ lens: r.lens, verdict: r.verdict })),
  raw: allFindings.length,
  deduped: deduped.length,
  refuted: merged.length - survivors.length,
  survivors: survivors.map(f => ({ lens: f.lens, severity: f.severity, title: f.title, status: f.verify.status })),
  editor: verdict,
}

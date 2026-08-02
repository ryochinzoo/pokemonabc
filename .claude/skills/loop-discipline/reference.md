# reference — 出典記事の要約(2026-07-31取得、一次と食い違うときは一次を当たること)

## 1. Sonar: Loop Engineering Without Verification Is Just Automation
https://www.sonarsource.com/blog/loop-engineering-without-verification-is-just-automation/

- **検証は耐荷重部品**: 「硬い客観的な停止条件が無いループは、大声で失敗せず、静かに失敗する」。
  検証ゲート無しの自律ループは未完成の成果物を出荷するリスクを持つ。
- **二層検証**: LLM検証サブエージェント(意図・意味論)+決定的なコード検証(規則ベース)。
  「ループが停止する根拠となるゲートは決定的な検査に置く」。
- **コスト制御**: 信頼できるゲートが開放的で高価なループを閉じたループに変える(収束を可能にする)。
- 本プロジェクトへの写像: 決定的ゲート = 台帳(T6)・事前登録の判定規則・CEW・robustness-guard。
  ゲートは**採択判定**にかかるのであって、**測定の実行**にはかからない。

## 2. Claude blog: Building verification loops in Claude Code with skills
https://claude.com/blog/building-verification-loops-in-claude-code-with-skills

- 検証ループ = エージェントが「自分の仕事をチェックし、失敗を直してから進む」反復過程。
- 「毎回同じ小さな修正を繰り返しているなら、そのステップをスキルに変換する時期」
  — 手動チェックを `.claude/skills/` のmarkdownとして体系化する。
- 実行パターンはスタンドアロン/組み込み/チェーン/PR自動実行の4種、頻度と成熟度で選ぶ。
- 本プロジェクトへの写像: 本スキル自体がその適用(「見送りの3条件」を毎回口頭で
  再発明せず、規律として固定した)。

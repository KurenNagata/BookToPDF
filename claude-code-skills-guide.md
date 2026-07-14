# Claude Code スキル導入ガイド

Anthropic公式リポジトリ [anthropics/skills](https://github.com/anthropics/skills) から有用な15スキルを選定したパッケージ。
スキルは「SKILL.md + スクリプト/参考資料」のフォルダで、Claude Codeが作業内容に応じて自動で読み込み、特定タスクの品質を大きく向上させる。

---

## インストール方法

### 方法A: プラグインマーケットプレイス経由(推奨・更新が楽)

Claude Code内で以下を実行:

```
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```

- `document-skills` … docx / pptx / xlsx / pdf
- `example-skills` … その他(mcp-builder, frontend-design など)
- 更新は `/plugin update` で可能

### 方法B: 手動コピー(同梱のzipを使用)

`claude-skills-pack.zip` を展開し、中身を `~/.claude/skills/` に配置:

```bash
mkdir -p ~/.claude/skills
unzip claude-skills-pack.zip
cp -r skills-pack/* ~/.claude/skills/
```

- 全プロジェクト共通: `~/.claude/skills/`
- 特定リポジトリのみ: プロジェクト内の `.claude/skills/`
- 削除はフォルダを消すだけ

### 使い方の基本

インストール後は特別な操作は不要。タスクを普通に依頼すればClaudeが自動で該当スキルを読み込む。明示的に使いたい場合はスキル名を指示に含める(例:「pptxスキルを使ってスライドを作って」)。

---

## 収録スキル一覧

### 📄 資料作成系

| スキル名 | 用途 |
|---|---|
| **pptx** | PowerPointの作成・編集・読み取り。ピッチデッキやポスター資料に |
| **docx** | Word文書の作成・編集。目次・見出し・変更履歴・テンプレート対応 |
| **xlsx** | Excelの作成・編集・数式・データ整形。CSV/TSV変換も対応 |
| **pdf** | PDFの結合・分割・フォーム記入・テキスト抽出・OCR |
| **doc-coauthoring** | 技術仕様書・提案書などを対話的に共同執筆するワークフロー |
| **theme-factory** | スライドやHTML・レポートに統一テーマ(配色・タイポグラフィ)を適用。10種のプリセット付き |

**使用例**
- 「このMVP要件からピッチデッキを10枚で作って」(pptx)
- 「ESの下書きをWordファイルにして」(docx)
- 「APIエンドポイント一覧をExcelにまとめて」(xlsx)
- 「theme-factoryのテーマでポスターの配色を統一して」

### 💻 開発・コーディング系

| スキル名 | 用途 |
|---|---|
| **mcp-builder** | 高品質なMCPサーバーの設計・実装ガイド。外部サービス連携ツールの開発に |
| **webapp-testing** | Playwrightでローカルwebアプリを操作・テスト。フロントの動作確認やUIデバッグ |
| **claude-api** | Claude API / Anthropic SDKのリファレンス。モデルID・料金・ツール使用・ストリーミング等を正確に参照 |
| **skill-creator** | 自作スキルの作成・改善・評価。チーム独自のワークフローをスキル化できる |

**使用例**
- 「SlackのカスタムメンションBotをMCPサーバーとして設計して」(mcp-builder)
- 「localhost:3000のログインフローをテストして」(webapp-testing)
- 「Go向けにAnthropic SDKでツール呼び出しを実装して」(claude-api)
- 「チームのAPIレビュー手順をスキルにして」(skill-creator)

### 🎨 デザイン・Web系

| スキル名 | 用途 |
|---|---|
| **frontend-design** | テンプレ感のない、意図のあるUIデザイン指針。タイポグラフィ・美的方向性の質が向上 |
| **web-artifacts-builder** | React + Tailwind + shadcn/uiで複数コンポーネントの本格的なHTMLアーティファクトを構築 |
| **canvas-design** | デザイン理論に基づくポスター・ビジュアルアート(.png/.pdf)の作成 |
| **algorithmic-art** | p5.jsによるジェネラティブアート。シード付きランダムネスとパラメータ探索 |
| **slack-gif-creator** | Slack最適化されたアニメーションGIFの作成(サイズ制約・検証ツール込み) |

**使用例**
- 「アプリのランディングページをモダンなデザインで作って」(frontend-design + web-artifacts-builder)
- 「発表会用のポスターをzine風の質感で作って」(canvas-design)
- 「チームSlack用のリアクションGIFを作って」(slack-gif-creator)

---

## 収録を見送ったスキル

| スキル名 | 理由 |
|---|---|
| brand-guidelines | Anthropic社の公式ブランド適用専用のため |
| internal-comms | Anthropic社内の文書フォーマット前提のため(skill-creatorで自チーム版を作る方が有用) |

---

## 運用のヒント

- **入れすぎ注意**: スキルの説明文は全てコンテキストに読み込まれるため、多すぎるとマッチ精度が下がる。日常的に使うものに絞るのが良い
- **プロジェクト共有**: チームで共有したいスキルはリポジトリの `.claude/skills/` にコミットすれば、クローンした全員が使える
- **自作スキル**: `SKILL.md`(YAMLフロントマター + 指示)を置くだけで作れる。skill-creatorスキルが作成から評価まで支援してくれる
- **確認方法**: Claude Codeで「今使えるスキルを教えて」と聞くと一覧が返る

参考: [Claude Code Skills公式ドキュメント](https://code.claude.com/docs/en/skills) / [anthropics/skills](https://github.com/anthropics/skills)

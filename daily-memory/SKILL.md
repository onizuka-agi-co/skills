---
name: daily-memory
description: "Add daily reports to VitePress repository. Use when: (1) adding daily reports, (2) saving work logs, (3) creating date-based documents."
---

# daily-memory

日報をVitePressリポジトリに追加するスキル。

## Description

日々の作業記録を `onizuka-agi-co/memory` リポジトリに追加する。日付フォルダを作成し、index.mdとトピック別ファイルを生成、config.tsのサイドバーを更新してcommit & pushする。

## Usage

### 新しい日報を追加

```
日報を追加して
今日の作業は：
- タスクA完了
- タスクB進行中
```

### トピックを指定して追加

```
日報を追加して
トピック: X API開発
内容: OAuth認証を実装した
```

### 既存の日報にトピックを追加

```
2026-02-25にトピック追加
トピック: テスト
内容: テストコードを書いた
```

## Commands

```bash
# 新しい日報を追加
uv run scripts/daily_memory.py add \
  --completed "タスクA,タスクB" \
  --in-progress "タスクC" \
  --notes "気づき" \
  --tags "#AGI #開発" \
  --continue  # 前回リンクを自動追加

# トピックを追加
uv run scripts/daily_memory.py add-topic "トピック名" \
  --content "内容" \
  --date "2026-03-01"

# 目次を更新
uv run scripts/daily_memory.py update-toc

# タグで検索
uv run scripts/daily_memory.py search-tags "#AGI"

# コミット＆プッシュ
uv run scripts/daily_memory.py commit
```

| コマンド | 説明 |
|---------|------|
| `add` | 新しい日報を追加 |
| `add-topic` | 既存の日報にトピックを追加 |
| `update-toc` | 目次を更新 |
| `search-tags` | タグで検索 |
| `commit` | 変更をcommit & push |

## Repository

- URL: https://github.com/onizuka-agi-co/memory
- Local: `~/.openclaw/workspace/memory`

## Structure

```
docs/2026/02/25/
├── index.md           ← 日報サマリー
├── topic-a.md         ← トピック別詳細
└── topic-b.md
```

## Notes

- 日付は自動取得（Asia/Tokyo）
- トピック名はファイル名に変換（英数字・ハイフンのみ）
- index.mdの「詳細」セクションにリンクを自動追加

## ⚠️ VitePressビルド検証（必須）

**commit前に必ずビルド検証を行うこと:**

```bash
cd ~/.openclaw/workspace/memory && npm run docs:build
```

**よくあるエラーと対策:**

| エラー | 原因 | 対策 |
|--------|------|------|
| `Element is missing end tag` | `<name>` などがHTMLタグと誤認 | `` `<name>` `` とバッククォートで囲む |
| `dead link` | ローカルパスへのリンク | `https://docs.openclaw.ai/...` などURLを使用 |
| `SyntaxError` | Markdown内のHTML構文エラー | コードブロック内の `<...>` を確認 |

**注意事項:**
- コードブロック内でも `<...>` は危険
- 特にFlask等のルート定義（`<name>`, `<int:id>` など）に注意
- ローカルパス（`/usr/lib/...`）はdead linkになる

**検証フロー:**
1. ファイル作成/編集
2. `npm run docs:build` で検証
3. エラーがあれば修正
4. ビルド成功後に commit & push

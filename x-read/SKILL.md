---
name: x-read
description: "X (Twitter) API READ operations. Use when: (1) getting user info, (2) reading timeline/mentions, (3) searching tweets, (4) fetching tweet details. NO posting/writing."
---

# X Read - 読み込み専用

X APIからのデータ取得のみ。投稿・書き込みは `x-write` スキルを使用。

## Quick Start

```bash
uv run scripts/x_read.py <command> [args...]
```

## Commands

### ユーザー情報

```bash
# 自分の情報
uv run scripts/x_read.py me

# ユーザー名で検索
uv run scripts/x_read.py user <username>

# IDで検索
uv run scripts/x_read.py userid <user_id>
```

### ツイート取得

```bash
# ツイート詳細
uv run scripts/x_read.py tweet <tweet_id>

# 自分のツイート一覧
uv run scripts/x_read.py tweets [max]

# タイムライン
uv run scripts/x_read.py timeline [max]

# メンション
uv run scripts/x_read.py mentions [max]
```

### 検索

```bash
uv run scripts/x_read.py search "<query>" [max]

# 例
uv run scripts/x_read.py search "from:Onizuka_Renji" 20
uv run scripts/x_read.py search "#OpenClaw" 10
```

### トークン更新

```bash
uv run scripts/x_read.py refresh
```

## 出力形式

全てJSON形式で返される：

```json
{
  "data": {
    "id": "...",
    "name": "...",
    "username": "..."
  }
}
```

## 必要なファイル

- `x-tokens.json` - アクセストークン
- `x-client-credentials.json` - クライアント認証情報

## Rate Limits

| 操作 | 制限 |
|------|------|
| ユーザー検索 | 75 / 15分 |
| タイムライン | 180 / 15分 |
| 検索 | 180 / 15分 |

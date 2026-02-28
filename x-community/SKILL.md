---
name: x-community
description: "X (Twitter) Community post operations. Use when: (1) posting to a specific community, (2) community-only posts vs shared posts. Requires OAuth2 token with tweet.write scope."
---

# X Community - コミュニティ投稿専用

Xのコミュニティ機能への投稿に特化したスキル。

## Quick Start

```bash
uv run skills/x-community/scripts/x_community.py post "投稿テキスト"
```

## Commands

### 投稿

```bash
# コミュニティへ投稿（フォロワーにも表示 - デフォルト）
uv run skills/x-community/scripts/x_community.py post "投稿テキスト"

# コミュニティのみ（フォロワーには表示しない）
uv run skills/x-community/scripts/x_community.py post "投稿テキスト" --no-share

# 引用リツイートをコミュニティに投稿（URLを含める形式）
uv run skills/x-community/scripts/x_community.py post "解説テキスト https://x.com/user/status/123"
```

**注意:** X API v2では、コミュニティ投稿と`quote_tweet_id`パラメータの併用が制限されています。引用リツイートしたい場合は、URLをテキストに含める形で投稿してください。

### 設定

```bash
# デフォルトコミュニティIDを設定
uv run skills/x-community/scripts/x_community.py set-community <community_id>

# 現在の設定を確認
uv run skills/x-community/scripts/x_community.py config
```

## 設定ファイル

- `x-community-config.json` - デフォルトコミュニティIDなど

## 出力形式

**投稿成功:**
```json
{
  "data": {
    "id": "2025980911364579673",
    "text": "投稿テキスト",
    "edit_history_tweet_ids": ["2025980911364579673"]
  }
}
```

## Agentからの呼び出し方

```
コミュニティに投稿して: [テキスト]
```

または明示的に：

```
x-community skillでコミュニティに投稿: [テキスト]
```

## パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `--no-share` | false | フォロワーには表示しない（コミュニティのみ） |

## 必要なファイル

- `x-tokens.json` - アクセストークン（workspace直下）
- `x-client-credentials.json` - クライアント認証情報（workspace直下）
- `x-community-config.json` - コミュニティ設定（自動生成）

## Rate Limits

通常のツイートと同じ: 200 / 15分

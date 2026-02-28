---
name: x-write
description: "X (Twitter) API WRITE operations. Use when: (1) posting tweets, (2) deleting tweets, (3) liking/retweeting, (4) following/unfollowing. NO reading operations."
---

# X Write - 書き込み専用

X APIへの書き込みのみ。読み込みは `x-read` スキルを使用。

## Quick Start

```bash
uv run scripts/x_write.py <command> [args...]
```

## Commands

### 投稿

```bash
# ツイート投稿
uv run scripts/x_write.py post "投稿テキスト"

# 引用リツイート
uv run scripts/x_write.py quote <tweet_id> "引用コメント"

# コミュニティへ投稿
uv run scripts/x_write.py community <community_id> "投稿テキスト"

# コミュニティへ投稿（フォロワーにも共有）
uv run scripts/x_write.py community <community_id> "投稿テキスト" --share

# ツイート削除
uv run scripts/x_write.py delete <tweet_id>
```

### いいね・リツイート

```bash
# いいね（user省略時は自分）
uv run scripts/x_write.py like <tweet_id> [user_id|me]

# いいね解除
uv run scripts/x_write.py unlike <tweet_id> [user_id|me]

# リツイート
uv run scripts/x_write.py retweet <tweet_id> [user_id|me]

# リツイート解除
uv run scripts/x_write.py unretweet <tweet_id> [user_id|me]
```

### フォロー

```bash
# フォロー
uv run scripts/x_write.py follow <target_user_id> [source_user_id|me]

# フォロー解除
uv run scripts/x_write.py unfollow <target_user_id> [source_user_id|me]
```

### トークン更新

```bash
uv run scripts/x_write.py refresh
```

## 出力形式

全てJSON形式で返される：

**投稿成功:**
```json
{
  "data": {
    "id": "2025924754197434423",
    "text": "投稿テキスト",
    "edit_history_tweet_ids": ["2025924754197434423"]
  }
}
```

## 必要なファイル

- `x-tokens.json` - アクセストークン
- `x-client-credentials.json` - クライアント認証情報

## Rate Limits

| 操作 | 制限 |
|------|------|
| 投稿 | 200 / 15分 |
| 削除 | 50 / 15分 |
| いいね | 500 / 15分 |
| リツイート | 300 / 15分 |

## トークン自動更新

アクセストークンは2時間で期限切れ。
期限切れの場合、自動的にリフレッシュトークンで更新。

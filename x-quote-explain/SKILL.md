---
name: x-quote-explain
description: "通常の解説投稿を行い、その自分の投稿へのリプライに元ツイートURLを付ける。コミュニティ投稿なし。Use when: (1) ツイートに解説を付けて投稿, (2) 元ツイートURLはリプライに分離, (3) コミュニティ投稿は不要。"
---

# X Quote Explain - 解説投稿 + 元ツイートURLリプライ

指定されたツイートに解説を付けて通常投稿し、その自分の投稿へのリプライに元ツイートURLを付ける。コミュニティ投稿はしない。

## Quick Start

```bash
# 解説投稿（解説指定）
uv run skills/x-quote-explain/scripts/quote_explain.py <ツイートURL> "解説テキスト"

# AI解説生成
uv run skills/x-quote-explain/scripts/quote_explain.py <ツイートURL> --ai

# JSON only
uv run skills/x-quote-explain/scripts/quote_explain.py <ツイートURL> --ai --json
```

## 機能

- **通常投稿 + 元ツイートURLリプライ**
- `--ai` はフラグとして解釈される。文字列 `--ai` をそのまま投稿しない
- JSON出力対応
- OAuth 2.0認証

```json
{
  "success": true,
  "tweet_id": "123456789",
  "tweet_url": "https://x.com/i/status/123456789",
  "reply_tweet_id": "123456790",
  "reply_tweet_url": "https://x.com/i/status/123456790",
  "method": "post_with_reply"
}
```

## 必要なファイル

- `data/x/x-tokens.json` - アクセストークン
- `data/x/x-client-credentials.json` - クライアント認証

## トークン期限切れ時の対応

トークンは自動リフレッシュを試行する。失敗した場合は再認証が必要。

### 再認証方法

```bash
# x-writeスキルで認証
uv run skills/x-write/scripts/x_write.py auth

# または認証専用スクリプト
uv run skills/x-write/scripts/x_auth.py
```

### コールバックURI設定

X Developer Portalで以下を登録済みであること：
```
http://localhost:8080/callback
```

詳細は `x-write` スキルのSKILL.mdを参照。

## ハッシュタグルール

投稿時は **`$ONIAGI`** を使う。

## 出力形式

```json
{
  "success": true,
  "tweet_id": "123456789",
  "tweet_url": "https://x.com/i/status/123456789",
  "reply_tweet_id": "123456790",
  "reply_tweet_url": "https://x.com/i/status/123456790",
  "method": "post_with_reply"
}
```

# X Filtered Stream Skill

X（Twitter）のFiltered Stream APIを使って、リアルタイムにツイートを監視・受信するスキル。

## 機能

- **リアルタイム監視**: 特定ユーザーやキーワードの新規投稿を検知
- **ルール管理**: Filtered Streamのルールを追加・削除・確認
- **OpenClaw統合**: 受信したツイートを自動通知

## 必要なもの

### Bearer Token（App-only認証）

このスキルには**Bearer Token**が必要です。OAuth 2.0ユーザートークンとは異なります。

**取得方法:**
1. [X Developer Portal](https://developer.x.com/en/portal/dashboard)にアクセス
2. プロジェクト → アプリ → 「Keys and tokens」タブ
3. 「Bearer Token」セクションで「Generate」または「Regenerate」

**設定方法:**

方法1: ファイル作成
```bash
# data/x/x-bearer-token.json
{
  "bearer_token": "YOUR_BEARER_TOKEN_HERE"
}
```

方法2: 環境変数
```bash
export X_BEARER_TOKEN="your_bearer_token_here"
```

## 使い方

### 1. 設定確認

```bash
uv run skills/x-stream/scripts/x_filtered_stream.py test
```

### 2. ルール設定

```bash
# デフォルトルール（hAru_mAki_chの新規投稿）を設定
uv run skills/x-stream/scripts/x_filtered_stream.py setup

# カスタムルールを追加
uv run skills/x-stream/scripts/x_filtered_stream.py add "from:username -is:retweet -is:reply" "tag_name"

# 現在のルールを確認
uv run skills/x-stream/scripts/x_filtered_stream.py rules

# 全ルールを削除
uv run skills/x-stream/scripts/x_filtered_stream.py clear
```

### 3. ストリーム開始

```bash
uv run skills/x-stream/scripts/x_filtered_stream.py stream
```

## ルールの例

### 特定ユーザーの新規投稿のみ（リポスト・返信除外）
```
from:hAru_mAki_ch -is:retweet -is:reply
```

### 引用ポストも除外
```
from:hAru_mAki_ch -is:retweet -is:reply -is:quote
```

### 複数ユーザーを監視
```
from:user1 OR from:user2 OR from:user3
```

### キーワード監視
```
AGI OR "Artificial General Intelligence" -is:retweet
```

## 設定ファイル

### x-stream-config.json（オプション）

```json
{
  "rules": [
    {
      "value": "from:hAru_mAki_ch -is:retweet -is:reply",
      "tag": "haru_maki_new_posts"
    }
  ],
  "tweet_fields": ["created_at", "author_id", "public_metrics", "entities", "attachments"]
}
```

### 利用可能なtweet_fields

- `created_at` - 投稿日時
- `author_id` - 投稿者ID
- `public_metrics` - いいね、リポスト数など
- `entities` - URL、メンション、ハッシュタグ
- `attachments` - 添付メディア情報
- `context_annotations` - 文脈注釈
- `conversation_id` - 会話ID

## OpenClawでの活用

### バックグラウンド実行

```bash
# バックグラウンドでストリームを開始
exec uv run skills/x-stream/scripts/x_filtered_stream.py stream &
```

### Cronでの定期チェック

リアルタイムストリームの代わりに、定期的に検索APIを叩く方式も可能（実装予定）

## 注意事項

- **レート制限**: Filtered Streamは接続数に制限あり（最大5接続）
- **ルール数**: 最大25個のルールを設定可能
- **遅延**: P99で約6-7秒の遅延あり
- **切断対策**: ネットワーク切断時は再接続処理が必要

## トラブルシューティング

### 403 Forbidden
- Bearer Tokenが正しいか確認
- アプリの権限設定を確認（Filtered Stream権限が必要）

### No rules matched
- ルールが正しく設定されているか確認: `python x_filtered_stream.py rules`

### 接続が切れる
- ネットワーク安定性を確認
- 自動再接続処理を実装するか、cronで定期実行

## APIエンドポイント

- `GET /2/tweets/search/stream/rules` - ルール一覧
- `POST /2/tweets/search/stream/rules` - ルール追加・削除
- `GET /2/tweets/search/stream` - ストリーム接続

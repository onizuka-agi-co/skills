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

# 画像付きツイート投稿
uv run scripts/x_write.py post-image <image_path> "投稿テキスト"

# 図解画像付きツイート投稿（自動生成）
uv run scripts/x_write.py post-with-diagram "AGIに関する重要な発表" [--style abstract|minimalist|tech|artistic]

# 引用リツイート
uv run scripts/x_write.py quote <tweet_id> "引用コメント"

# コミュニティへ投稿
uv run scripts/x_write.py community <community_id> "投稿テキスト"

# コミュニティへ投稿（フォロワーにも共有）
uv run scripts/x_write.py community <community_id> "投稿テキスト" --share

# ツイート削除
uv run scripts/x_write.py delete <tweet_id>
```

### 図解自動生成機能

`post-with-diagram` コマンドは、ツイートテキストから図解画像を自動生成して投稿する。

**スタイルオプション:**
- `abstract` - 抽象的な幾何学模様（デフォルト）
- `minimalist` - シンプルでミニマル
- `tech` - 技術的な回路パターン
- `artistic` - アーティスティックで鮮やか

**使用例:**
```bash
# AGI関連ツイートに図解を追加
uv run scripts/x_write.py post-with-diagram "新しいAGI論文が発表されました" --style tech

# シンプルな図解で投稿
uv run scripts/x_write.py post-with-diagram "機械学習モデルのトレーニングが完了" --style minimalist
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

## 初回認証・再認証

### 自動認証（推奨）

```bash
# ローカルサーバーを起動して自動認証
uv run scripts/x_write.py auth

# または認証専用スクリプト
uv run scripts/x_auth.py
```

**手順:**
1. ブラウザが自動で開く
2. Twitterでアプリを認証
3. 自動でコールバックを受け取りトークン保存

### 手動認証（自動が失敗する場合）

```bash
# 1. 認証URLを生成
uv run scripts/x_auth.py --url

# 2. ブラウザでURLを開いて認証

# 3. コールバックURLのcodeパラメータを指定
uv run scripts/x_auth.py --code <code>
```

### コールバックURI設定

X Developer Portalで以下のコールバックURIを登録済みであること：
```
http://localhost:8080/callback
```

### トークン状態確認

```bash
uv run scripts/x_auth.py --status
```

## 必要なファイル

| ファイル | 説明 |
|---------|------|
| `x-tokens.json` | アクセストークン（自動生成） |
| `x-client-credentials.json` | クライアント認証情報（要手動配置） |

### x-client-credentials.json 形式

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
```

## ハッシュタグルール

投稿時のハッシュタグは **#ONIZUKA_AGI** のみ使用する。

## 投稿スケジューラー

投稿キューを管理し、指定時刻に自動投稿するシステム。

```bash
# キューに追加（時刻指定）
uv run scripts/x_scheduler.py add "投稿テキスト" --at "2026-05-09T18:00:00+09:00"

# キューに追加（タグ付き）
uv run scripts/x_scheduler.py add "投稿テキスト" --tags paper AGI --priority 3

# キュー一覧
uv run scripts/x_scheduler.py list

# 投稿を削除
uv run scripts/x_scheduler.py remove Q0509074702

# 予定時刻の投稿を実行
uv run scripts/x_scheduler.py process

# 最適投稿時間の提案
uv run scripts/x_scheduler.py suggest

# 統計情報
uv run scripts/x_scheduler.py stats
```

**機能:**
- 投稿キューの管理（追加・一覧・削除）
- 指定時刻の自動投稿（`process`をcron実行）
- 投稿間隔の最小保証（15分）
- 投稿履歴の統合管理
- 最適投稿時間の提案

**定期実行の設定:**

schedule-tasks.yamlに以下を追加：

```yaml
- name: "X投稿スケジューラー処理"
  schedule: "*/15 * * * *"  # 15分ごと
  prompt: " Scheduler: uv run skills/x-write/scripts/x_scheduler.py process"
  enabled: true
```

## トラブルシューティング

| エラー | 原因 | 対処 |
|--------|------|------|
| 401 Unauthorized | トークン期限切れ | `auth`コマンドで再認証 |
| Token refresh failed | リフレッシュトークン無効 | `auth`コマンドで再認証 |
| Callback not received | ポート8080が使用中 | 他のプロセスを停止 |
| Invalid redirect_uri | コールバックURI未登録 | X Developer Portalで設定 |

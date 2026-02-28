---
name: sunwood-community
description: "Sunwood AI OSS Hub (https://x.com/i/communities/2010195061309587967) への投稿専用スキル。引用リツイート投稿や解説付き投稿に使用。"
---

# Sunwood Community - Sunwood AI OSS Hub 投稿スキル

Sunwood AI OSS Hub コミュニティへの投稿専用。

**コミュニティ:** https://x.com/i/communities/2010195061309587967

## Quick Start

```bash
# 引用リツイート（解説付き）
uv run skills/sunwood-community/scripts/quote_to_community.py <ポストURL> "解説文"

# 例
uv run skills/sunwood-community/scripts/quote_to_community.py https://x.com/user/status/123 "これは面白い記事です！"
```

## ログ保存

投稿するたびに自動でログを保存します。

**保存場所:** `skills/sunwood-community/logs/YYYY-MM-DD/`

**ファイル名:** `HH-MM-SS_<元ツイートID>.json`

**ログ内容:**
```json
{
  "timestamp": "2026-02-24T04:30:00+00:00",
  "original_tweet": {
    "id": "123456789",
    "text": "元のツイート本文",
    "url": "https://x.com/i/status/123456789"
  },
  "community_post": {
    "id": "987654321",
    "text": "投稿したテキスト",
    "url": "https://x.com/i/status/987654321"
  }
}
```

## 🔔 投稿前のログ確認フロー

**重要:** 新しい投稿をする前に、必ず過去のログを確認し、流れを理解した内容にすること。

### 確認手順

1. **ログディレクトリを確認**
   ```bash
   ls skills/sunwood-community/logs/
   ```

2. **最新のログファイルを読む**
   ```bash
   cat skills/sunwood-community/logs/YYYY-MM-DD/*.json
   ```

3. **シリーズものの場合**
   - 同じ作者の連続投稿（例: FUTODAMA AGI準備①②③...）を把握
   - 前回の内容を踏まえた解説を作成
   - 「前回の続き」「シリーズ第N弾」など文脈を反映

### Agentがやるべきこと

```
1. ユーザーからポストURLを受け取る
2. logs/ 内の最新ログを確認（同じ作者・シリーズがあれば）
3. 文脈を理解した解説文を作成
4. 投稿実行
5. ログ保存
```

### 例

過去ログ:
- ① サンドボックス環境構築
- ② GitHub Pagesデプロイ
- ③ GitHub Apps連携 ← 今回

解説例:
```
🔍 FUTODAMA AGI準備シリーズ第③弾

前回のGitHub Pagesデプロイに続き、今回はGitHub Apps連携を完了。

🎯 これまでの流れ:
① サンドボックス環境構築
② GitHub Pagesデプロイ
③ GitHub Apps連携 ← NEW

💡 AGIの自律実行環境が着々と整備中
```

## スクリプト一覧

### quote_to_community.py - 引用リツイート投稿

```bash
uv run skills/sunwood-community/scripts/quote_to_community.py <ポストURL> "解説文"
```

シンプル版。引数2つだけ：
1. ポストURL（またはツイートID）
2. 解説文

### x_community.py - 汎用コミュニティ投稿

```bash
# 通常投稿
uv run skills/sunwood-community/scripts/x_community.py post "投稿テキスト"

# 引用リツイート
uv run skills/sunwood-community/scripts/x_community.py quote <URL> "解説"
```

### x_community_quote.py - テンプレート付き引用投稿

```bash
# テンプレート使用
uv run skills/sunwood-community/scripts/x_community_quote.py quote <URL> "解説" --template notable

# プレビュー
uv run skills/sunwood-community/scripts/x_community_quote.py preview <URL> "解説"
```

**テンプレート:**
| 名前 | フォーマット |
|------|-------------|
| `notable` | 🔍 注目ポスト解説 |
| `news` | 📰 ニュース紹介 |
| `tip` | 💡 Tips・豆知識 |

## 設定

コミュニティID固定: `2010195061309587967` (Sunwood AI OSS Hub)

## 必要なファイル

- `x-tokens.json` - アクセストークン（workspace直下）
- `x-client-credentials.json` - クライアント認証情報

## 注意点

- `community_id` + `quote_tweet_id` の併用は403エラー（API制限）
- URLをテキストに含める形式で投稿（引用カードとして表示）

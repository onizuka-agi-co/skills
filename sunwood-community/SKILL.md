---
name: sunwood-community
description: "Sunwood AI OSS Hub (https://x.com/i/communities/2010195061309587967) への投稿専用スキル。引用リツイート投稿や解説付き投稿に使用。AIによる自動解説生成、文脈理解機能を搭載。"
---

# Sunwood Community - Sunwood AI OSS Hub 投稿スキル

Sunwood AI OSS Hub コミュニティへの投稿専用。

**コミュニティ:** https://x.com/i/communities/2010195061309587967
**X投稿アカウント:** `@Onizuka_Renji` を基準に運用する。

## Quick Start

```bash
# 引用リツイート（解説付き）
uv run skills/sunwood-community/scripts/quote_to_community.py <ポストURL> "解説文"

# AI解説生成（文脈理解付き）
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL>

# 可視化画像付き投稿（NEW）
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL> --visual

# 本体+画像+複数リプライを一括投稿（推奨）
uv run skills/sunwood-community/scripts/post_thread.py --payload-file payload.json

# プレビューのみ
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL> --preview
```

## GitHub Event Playbook

GitHub release / repository event を扱う場合は、通常の X ポストとは別ルールで処理する。

### 基本ルール

1. 投稿アカウントは `@Onizuka_Renji` を使う
2. 解説本文と URL を同じ投稿に混ぜない
3. 先に解説ポストを投稿し、その**リプライ欄**に GitHub の URL を貼る
4. GitHub event の URL は **元のXポストURLではなく、GitHubの release / repository URL** を使う
5. ハッシュタグは使わず **`$ONIAGI`** を本文に入れる

### 結果報告で必ず返すもの

- 解説ポストURL
- リプライURL
- 解説のポイントまとめ

### 参照テンプレート

GitHub event 用の依頼文テンプレート:

`prompts/github_event_quote.md`

Bookmark 用の依頼文テンプレート:

`prompts/bookmark_quote.md`

共通ルール断片:

- `prompts/shared_posting_rules.md`
- `prompts/shared_explainer_requirements.md`
- `prompts/shared_result_requirements.md`

## 新機能：可視化画像添付 (--visual)

`--visual`フラグを使用すると、`memory/docs/public/Onizuka_2k_delpmaspu.png` を参照画像として使い、nano-banana-2 edit ベースでポスト内容を可視化した図解画像を自動生成・添付します。

`--visual` 指定時は画像添付が必須です。画像生成またはアップロードに失敗した場合は、テキストのみで続行せずエラーにします。
図解内の見出し、ラベル、短い説明文は文字化け回避のため英語で生成します。

```bash
# 可視化画像付きで投稿
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL> --visual

# テンプレート指定 + 可視化画像
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL> --visual --template insight

# プレビュー（画像生成プロンプトを確認）
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL> --visual --preview
```

**必要な環境変数:**
- `FAL_KEY` - fal.ai APIキー（または`fal-key.txt`をworkspace直下に配置）
- `SUNWOOD_VISUAL_REFERENCE_IMAGE` - 参照画像を差し替える場合のみ指定。未指定時は `Onizuka_2k_delpmaspu.png` を使う。

**処理フロー:**
1. ポスト内容を取得
2. 文脈を分析して解説を生成（元ポストの引用を含む）
3. nano-banana-2 edit で参照画像ベースの図解を生成
4. 画像をXにアップロード
5. media_ids付きでコミュニティに投稿

## 投稿フォーマット

デフォルトで元ポストの内容を引用として含めます：

```
🔍 **作者名の注目ポスト解説**

[要約]

📝 元ポスト:
[元ポストのテキスト]

https://x.com/i/status/...
```

`--no-quote`で引用を省略可能：
```bash
uv run skills/sunwood-community/scripts/ai_quote_generator.py <ポストURL> --no-quote
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

### post_thread.py - 本体+画像+複数リプライの一括投稿

```bash
uv run skills/sunwood-community/scripts/post_thread.py --payload-file payload.json
uv run skills/sunwood-community/scripts/post_thread.py --payload-file payload.json --dry-run
```

推奨の投稿経路。`payload JSON` に本体、画像、複数リプライをまとめて渡し、1回の実行で投稿する。

- 本体投稿には画像が必須
- 本文に URL があるとエラー
- 1リプライに複数 URL があるとエラー
- `reply_to` で `main` または先行リプライを指定可能
- 途中で失敗したら既に投稿したポストをロールバック削除

最小 payload 例:

```json
{
  "main_post": {
    "text": "🔍 例の解説本文\n\n$ONIAGI",
    "image_path": "memory/docs/public/example.png"
  },
  "replies": [
    {
      "id": "source",
      "reply_to": "main",
      "text": "📎 元ポスト\n論点確認用のリンクです。\nhttps://x.com/i/status/123"
    },
    {
      "id": "docs",
      "reply_to": "main",
      "text": "🔗 公式情報\n仕様を確認したい場合はこちらです。\nhttps://example.com"
    }
  ]
}
```

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

- `data/x/x-tokens.json` - `@Onizuka_Renji` 用アクセストークン
- `data/x/x-client-credentials.json` - クライアント認証情報

## 注意点

- `community_id` + `quote_tweet_id` の併用は403エラー（API制限）
- URLをテキストに含める形式で投稿（引用カードとして表示）

## ハッシュタグルール

投稿時の銘柄タグは **`$ONIAGI`** を使用する。

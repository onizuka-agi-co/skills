#!/usr/bin/env python3
"""
引用リツイート投稿スクリプト - Sunwood AI OSS Hub専用

Usage:
    uv run quote_to_community.py <ポストURL> "解説文"
    uv run quote_to_community.py <ポストURL> "解説文" --ai  # AI解説生成
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

# 設定
COMMUNITY_ID = "2010195061309587967"  # Sunwood AI OSS Hub
TOKEN_FILE = Path(__file__).parent.parent.parent.parent / "x-tokens.json"
LOGS_DIR = Path(__file__).parent.parent / "logs"


def load_token() -> str:
    """アクセストークンを読み込む"""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"Token file not found: {TOKEN_FILE}")

    with open(TOKEN_FILE) as f:
        data = json.load(f)
    return data.get("access_token", "")


def extract_tweet_id(url_or_id: str) -> str:
    """URLまたはIDからツイートIDを抽出"""
    if url_or_id.isdigit():
        return url_or_id

    # URLからIDを抽出
    # https://x.com/user/status/123456789
    # https://twitter.com/user/status/123456789
    parts = urlparse(url_or_id).path.split("/")
    for i, part in enumerate(parts):
        if part == "status" and i + 1 < len(parts):
            return parts[i + 1]

    raise ValueError(f"Invalid tweet URL or ID: {url_or_id}")


def get_tweet(tweet_id: str, token: str) -> dict:
    """ツイート情報を取得"""
    url = f"https://api.x.com/2/tweets/{tweet_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"tweet.fields": "created_at,author_id,text"}

    with httpx.Client() as client:
        resp = client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


def post_community_tweet(text: str, token: str) -> dict:
    """コミュニティに投稿"""
    url = "https://api.x.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text, "community_id": COMMUNITY_ID}

    with httpx.Client() as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def save_log(original_tweet: dict, community_post: dict, quote_text: str):
    """投稿ログを保存"""
    now = datetime.now(timezone.utc)
    date_dir = LOGS_DIR / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    tweet_id = original_tweet.get("id", "unknown")
    log_file = date_dir / f"{now.strftime('%H-%M-%S')}_{tweet_id}.json"

    log_data = {
        "timestamp": now.isoformat(),
        "original_tweet": {
            "id": tweet_id,
            "text": original_tweet.get("text", ""),
            "url": f"https://x.com/i/status/{tweet_id}",
        },
        "community_post": {
            "id": community_post.get("data", {}).get("id", ""),
            "text": quote_text,
            "url": f"https://x.com/i/status/{community_post.get('data', {}).get('id', '')}",
        },
    }

    with open(log_file, "w") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"📝 ログ保存: {log_file}")


def generate_ai_summary(tweet_text: str) -> str:
    """AIによる解説生成（プレースホルダー）"""
    # 注: 実際のAI生成は外部APIを呼び出す必要がある
    # ここではテンプレートベースの生成を行う

    if "AGI" in tweet_text or "agi" in tweet_text.lower():
        return "🔍 AGI関連の注目ポストです"
    elif "AI" in tweet_text or "ai" in tweet_text.lower():
        return "🔍 AI技術に関する情報です"
    else:
        return "🔍 注目のポストです"


def build_quote_text(tweet_url: str, summary: str, template: str = "notable") -> str:
    """引用投稿テキストを構築"""
    templates = {
        "notable": f"🔍 注目ポスト解説\n\n{summary}\n\n{tweet_url}",
        "news": f"📰 ニュース紹介\n\n{summary}\n\n{tweet_url}",
        "tip": f"💡 Tips・豆知識\n\n{summary}\n\n{tweet_url}",
        "simple": f"{summary}\n\n{tweet_url}",
    }
    return templates.get(template, templates["notable"])


def main():
    parser = argparse.ArgumentParser(description="引用リツイート投稿")
    parser.add_argument("tweet_url", help="引用するツイートのURLまたはID")
    parser.add_argument("summary", help="解説文")
    parser.add_argument("--ai", action="store_true", help="AIによる解説生成")
    parser.add_argument(
        "--template",
        choices=["notable", "news", "tip", "simple"],
        default="notable",
        help="テンプレート選択",
    )
    parser.add_argument("--dry-run", action="store_true", help="投稿せずプレビューのみ")

    args = parser.parse_args()

    try:
        # トークン読み込み
        token = load_token()
        if not token:
            print("❌ アクセストークンが見つかりません")
            sys.exit(1)

        # ツイートID抽出
        tweet_id = extract_tweet_id(args.tweet_url)
        print(f"📌 ツイートID: {tweet_id}")

        # ツイート取得
        tweet_data = get_tweet(tweet_id, token)
        tweet = tweet_data.get("data", {})
        tweet_text = tweet.get("text", "")
        print(f"📝 元ツイート: {tweet_text[:100]}...")

        # 解説文決定
        if args.ai:
            summary = generate_ai_summary(tweet_text)
            print(f"🤖 AI生成解説: {summary}")
        else:
            summary = args.summary

        # 投稿テキスト構築
        tweet_url = f"https://x.com/i/status/{tweet_id}"
        quote_text = build_quote_text(tweet_url, summary, args.template)

        # プレビュー
        print("\n" + "=" * 40)
        print("📤 投稿内容:")
        print("=" * 40)
        print(quote_text)
        print("=" * 40 + "\n")

        if args.dry_run:
            print("🔍 ドライランモード: 投稿しません")
            return

        # 投稿実行
        result = post_community_tweet(quote_text, token)
        post_id = result.get("data", {}).get("id", "")
        print(f"✅ 投稿成功: https://x.com/i/status/{post_id}")

        # ログ保存
        save_log(tweet, result, quote_text)

    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

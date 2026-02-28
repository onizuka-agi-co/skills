#!/usr/bin/env python3
"""
AI解説生成スクリプト - 過去ログを活用した文脈理解

Usage:
    uv run ai_quote_generator.py <ポストURL>
    uv run ai_quote_generator.py <ポストURL> --preview
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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

    from urllib.parse import urlparse

    parts = urlparse(url_or_id).path.split("/")
    for i, part in enumerate(parts):
        if part == "status" and i + 1 < len(parts):
            return parts[i + 1]

    raise ValueError(f"Invalid tweet URL or ID: {url_or_id}")


def get_tweet(tweet_id: str, token: str) -> dict:
    """ツイート情報を取得"""
    url = f"https://api.x.com/2/tweets/{tweet_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"tweet.fields": "created_at,author_id,text", "expansions": "author_id", "user.fields": "name,username"}

    with httpx.Client() as client:
        resp = client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


def get_recent_logs(days: int = 7) -> list[dict]:
    """最近のログを取得"""
    logs = []
    now = datetime.now(timezone.utc)

    for i in range(days):
        date = now - __import__("datetime").timedelta(days=i)
        date_dir = LOGS_DIR / date.strftime("%Y-%m-%d")
        if date_dir.exists():
            for log_file in sorted(date_dir.glob("*.json"), reverse=True):
                with open(log_file) as f:
                    logs.append(json.load(f))

    return logs[:20]  # 最大20件


def analyze_context(tweet_text: str, author_name: str, recent_logs: list[dict]) -> dict:
    """過去ログから文脈を分析"""
    context = {
        "is_series": False,
        "series_count": 0,
        "related_topics": [],
        "previous_summaries": [],
    }

    # 同じ作者の投稿を探す
    author_posts = []
    for log in recent_logs:
        log_text = log.get("community_post", {}).get("text", "")
        if author_name.lower() in log_text.lower():
            author_posts.append(log)

    if author_posts:
        context["is_series"] = True
        context["series_count"] = len(author_posts)
        context["previous_summaries"] = [p.get("community_post", {}).get("text", "")[:100] for p in author_posts[:3]]

    # トピック抽出
    keywords = ["AGI", "AI", "LLM", "GPT", "Claude", "Gemini", "OpenAI", "Anthropic", "FUTODAMA", "OpenClaw", "スキル", "エージェント"]
    for kw in keywords:
        if kw.lower() in tweet_text.lower():
            context["related_topics"].append(kw)

    return context


def generate_smart_summary(tweet_text: str, author_name: str, context: dict) -> str:
    """文脈を考慮したスマートな解説を生成"""

    # トピックに基づく分類
    topics = context.get("related_topics", [])
    is_series = context.get("is_series", False)
    series_count = context.get("series_count", 0)

    # トピック別の絵文字とプレフィックス
    topic_emoji = {
        "AGI": "🔮",
        "AI": "🤖",
        "LLM": "🧠",
        "GPT": "💬",
        "Claude": "🔮",
        "Gemini": "💎",
        "OpenAI": "🌐",
        "Anthropic": "🔮",
        "FUTODAMA": "🏠",
        "OpenClaw": "🦞",
        "スキル": "🎭",
        "エージェント": "🤖",
    }

    # メイントピックを決定
    main_topic = topics[0] if topics else "AI"
    emoji = topic_emoji.get(main_topic, "🔍")

    # シリーズものの場合
    if is_series:
        prefix = f"{emoji} {author_name}シリーズ第{series_count + 1}弾"
    else:
        prefix = f"{emoji} 注目ポスト"

    # 内容の要約（簡易版）
    if len(tweet_text) > 200:
        summary = tweet_text[:200] + "..."
    else:
        summary = tweet_text

    return f"{prefix}\n\n{summary}"


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


def main():
    parser = argparse.ArgumentParser(description="AI解説生成付き引用リツイート")
    parser.add_argument("tweet_url", help="引用するツイートのURLまたはID")
    parser.add_argument("--preview", action="store_true", help="プレビューのみ")
    parser.add_argument("--days", type=int, default=7, help="過去ログ参照日数")

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
        author = tweet_data.get("includes", {}).get("users", [{}])[0]
        author_name = author.get("name", "Unknown")
        print(f"👤 作者: {author_name}")
        print(f"📝 元ツイート: {tweet_text[:100]}...")

        # 過去ログ取得・分析
        recent_logs = get_recent_logs(args.days)
        print(f"📚 過去ログ: {len(recent_logs)}件")

        context = analyze_context(tweet_text, author_name, recent_logs)
        print(f"🔍 文脈分析: シリーズ={context['is_series']}, トピック={context['related_topics']}")

        # スマート解説生成
        summary = generate_smart_summary(tweet_text, author_name, context)

        # 投稿テキスト構築
        tweet_url = f"https://x.com/i/status/{tweet_id}"
        quote_text = f"{summary}\n\n{tweet_url}"

        # プレビュー
        print("\n" + "=" * 40)
        print("📤 投稿内容:")
        print("=" * 40)
        print(quote_text)
        print("=" * 40 + "\n")

        if args.preview:
            print("🔍 プレビューモード: 投稿しません")
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

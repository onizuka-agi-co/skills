#!/usr/bin/env python3
"""
AI解説生成スクリプト - 過去ログを活用した文脈理解

Usage:
    uv run ai_quote_generator.py <ポストURL>
    uv run ai_quote_generator.py <ポストURL> --preview
    uv run ai_quote_generator.py <ポストURL> --template notable
    uv run ai_quote_generator.py <ポストURL> --visual  # 可視化画像を添付
"""

import argparse
import base64
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import httpx

# 設定
COMMUNITY_ID = "2010195061309587967"  # Sunwood AI OSS Hub
TOKEN_FILE = Path(__file__).parent.parent.parent.parent / "x-tokens.json"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# テンプレート定義
TEMPLATES = {
    "notable": {
        "prefix": "🔍",
        "title": "注目ポスト解説",
        "format": "{emoji} **{title}**\n\n{summary}\n\n{context}",
    },
    "news": {
        "prefix": "📰",
        "title": "ニュース紹介",
        "format": "{emoji} **{title}**\n\n{summary}\n\n{hashtags}",
    },
    "tip": {
        "prefix": "💡",
        "title": "Tips・豆知識",
        "format": "{emoji} **{title}**\n\n{summary}\n\n{hashtags}",
    },
    "series": {
        "prefix": "📚",
        "title": "シリーズ連載",
        "format": "{emoji} **{title} 第{num}弾**\n\n{summary}\n\n{context}\n\n{hashtags}",
    },
    "release": {
        "prefix": "🚀",
        "title": "リリース情報",
        "format": "{emoji} **{title}**\n\n{summary}\n\n{hashtags}",
    },
    "insight": {
        "prefix": "🔮",
        "title": "技術解説",
        "format": "{emoji} **{title}**\n\n{summary}\n\n{context}\n\n{hashtags}",
    },
}

# fal.ai API endpoint for nano-banana-2
FAL_API_URL = "https://fal.run/fal-ai/nano-banana-2"

# API key file locations for fal.ai
FAL_KEY_FILES = [
    Path(__file__).parent.parent.parent.parent / "fal-key.txt",
    Path.home() / ".fal-key.txt",
]


def get_fal_key() -> Optional[str]:
    """Get fal.ai API key from file or environment."""
    key = os.environ.get("FAL_KEY")
    if key:
        return key
    
    for key_file in FAL_KEY_FILES:
        if key_file.exists():
            return key_file.read_text().strip()
    
    return None


def generate_visual_image(prompt: str) -> str:
    """Generate image using fal.ai nano-banana-2 API. Returns image URL."""
    api_key = get_fal_key()
    if not api_key:
        raise ValueError(
            "FAL_KEY not found. Set FAL_KEY environment variable "
            "or create fal-key.txt in workspace root."
        )
    
    # 日本語プロンプトを英語に変換するヒントを追加
    enhanced_prompt = f"Create a visually appealing explanation image for: {prompt}. Style: modern, clean, infographic-like with soft colors."
    
    payload = {
        "prompt": enhanced_prompt,
        "num_images": 1,
        "aspect_ratio": "16:9",
        "resolution": "1K",
        "output_format": "png",
    }
    
    request = Request(
        FAL_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            images = result.get("images", [])
            if images:
                return images[0].get("url")
            raise ValueError("No image generated")
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"FAL API error: {e.code} - {error_body}")


def download_image(url: str) -> bytes:
    """Download image from URL and return bytes."""
    request = Request(url, headers={"User-Agent": "ONIZUKA-AGI/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def upload_media_to_x(image_url: str, token: str) -> str:
    """Upload image to X and return media_id."""
    # Download image
    image_data = download_image(image_url)
    
    # Upload to X using v1.1 media/upload
    url = "https://api.x.com/1.1/media/upload.json"
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Prepare multipart form data
    boundary = "----ONIZUKA_AGI_BOUNDARY"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="visual.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8")
    body += image_data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    
    with httpx.Client() as client:
        resp = client.post(url, headers=headers, content=body)
        resp.raise_for_status()
        result = resp.json()
        return result.get("media_id_string")


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


def generate_smart_summary(
    tweet_text: str, author_name: str, context: dict, template: str = "notable", include_quote: bool = True
) -> str:
    """文脈を考慮したスマートな解説を生成"""

    # トピックに基づく分類
    topics = context.get("related_topics", [])
    is_series = context.get("is_series", False)
    series_count = context.get("series_count", 0)

    # トピック別の絵文字
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

    # テンプレート自動選択
    if is_series:
        template = "series"
    elif main_topic in ["AGI", "LLM", "Claude", "Gemini", "GPT"]:
        template = "insight"
    elif "リリース" in tweet_text or "Release" in tweet_text or "release" in tweet_text:
        template = "release"
    elif "Tips" in tweet_text or "tips" in tweet_text or "豆知識" in tweet_text:
        template = "tip"

    tmpl = TEMPLATES.get(template, TEMPLATES["notable"])

    # 内容の要約（短縮）
    if len(tweet_text) > 150:
        summary = tweet_text[:150] + "..."
    else:
        summary = tweet_text

    # 文脈情報
    context_text = ""
    if is_series and context.get("previous_summaries"):
        context_text = "📌 これまでの流れ:\n" + "\n".join(
            f"• {s[:50]}..." for s in context["previous_summaries"][:3]
        )

    # ハッシュタグ
    hashtags = "#ONIZUKA_AGI"

    # タイトル生成
    title = f"{author_name}の{tmpl['title']}"

    # 元ツイートの引用を含める
    quote_block = ""
    if include_quote:
        # ツイートテキストを整形（長い場合は短縮）
        quoted_text = tweet_text if len(tweet_text) <= 200 else tweet_text[:200] + "..."
        quote_block = f"\n\n📝 元ポスト:\n{quoted_text}"

    # フォーマット適用
    result = tmpl["format"].format(
        emoji=emoji,
        title=title,
        num=series_count + 1,
        summary=summary,
        context=context_text,
        hashtags=hashtags,
    )
    
    # 引用ブロックを追加
    result += quote_block

    return result


def post_community_tweet(text: str, token: str, media_ids: Optional[list[str]] = None) -> dict:
    """コミュニティに投稿（オプションで画像添付）"""
    url = "https://api.x.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text, "community_id": COMMUNITY_ID}
    
    if media_ids:
        payload["media"] = {"media_ids": media_ids}

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
    parser.add_argument(
        "--template",
        "-t",
        choices=list(TEMPLATES.keys()),
        default="notable",
        help="テンプレート選択",
    )
    parser.add_argument(
        "--visual",
        "-v",
        action="store_true",
        help="可視化画像を生成して添付",
    )
    parser.add_argument(
        "--no-quote",
        action="store_true",
        help="元ポストの引用を含めない",
    )

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
        include_quote = not args.no_quote
        summary = generate_smart_summary(tweet_text, author_name, context, args.template, include_quote)

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
            if args.visual:
                print("🎨 可視化画像プロンプト:")
                print(f"   {tweet_text[:100]}")
            return

        # 画像生成とアップロード
        media_ids = None
        if args.visual:
            print("🎨 可視化画像を生成中...")
            try:
                image_url = generate_visual_image(tweet_text)
                print(f"✅ 画像生成完了: {image_url}")
                
                print("📤 画像をXにアップロード中...")
                media_id = upload_media_to_x(image_url, token)
                media_ids = [media_id]
                print(f"✅ アップロード完了: media_id={media_id}")
            except Exception as e:
                print(f"⚠️ 画像処理エラー: {e}")
                print("📝 テキストのみで投稿します...")

        # 投稿実行
        result = post_community_tweet(quote_text, token, media_ids)
        post_id = result.get("data", {}).get("id", "")
        print(f"✅ 投稿成功: https://x.com/i/status/{post_id}")

        # ログ保存
        save_log(tweet, result, quote_text)

    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

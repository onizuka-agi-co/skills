#!/usr/bin/env python3
"""
引用リツイート投稿スクリプト - Sunwood AI OSS Hub専用

Usage:
    uv run quote_to_community.py <ポストURL> "解説文"
    uv run quote_to_community.py <ポストURL> "解説文" --ai  # AI解説生成
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

# 設定
COMMUNITY_ID = "2010195061309587967"  # Sunwood AI OSS Hub
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
DATA_X_DIR = WORKSPACE_ROOT / "data" / "x"
TOKEN_FILE = Path(os.environ.get("SUNWOOD_COMMUNITY_TOKEN_FILE", str(DATA_X_DIR / "x-tokens.json")))
LOGS_DIR = Path(__file__).parent.parent / "logs"
ONIAGI_TAG = "$ONIAGI"
LEGACY_TAGS = ("#ONIZUKA_AGI",)
URL_LINE_RE = re.compile(r"^https?://\S+$")
URL_RE = re.compile(r"https?://\S+")
ESCAPED_CONTROL_SEQUENCE_RE = re.compile(r"\\[nrt]")


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


def extract_urls(text: str) -> list[str]:
    """Extract raw URLs from text."""
    return URL_RE.findall(text or "")


def validate_no_literal_escape_sequences(text: str) -> None:
    """Reject raw escaped control sequences like \\n in user-facing text."""
    matches = sorted(set(ESCAPED_CONTROL_SEQUENCE_RE.findall(text or "")))
    if matches:
        raise ValueError(
            "Post text must not contain raw escaped control sequences. "
            f"Found: {', '.join(matches)}"
        )


def validate_main_post_text(text: str) -> None:
    """Main post bodies must not contain URLs."""
    validate_no_literal_escape_sequences(text)
    urls = extract_urls(text)
    if urls:
        raise ValueError(
            "Main post text must not contain URLs. "
            f"Found {len(urls)} URL(s): {', '.join(urls)}"
        )


def validate_reply_text(text: str) -> None:
    """Each reply may contain at most one URL."""
    validate_no_literal_escape_sequences(text)
    urls = extract_urls(text)
    if len(urls) > 1:
        raise ValueError(
            "Reply text must not contain multiple URLs. "
            f"Found {len(urls)} URL(s): {', '.join(urls)}"
        )


def build_source_reply_text(label: str, url: str, note: str) -> str:
    """Build a single-link reply with a short explanation."""
    reply_text = f"{label}\n{note.strip()}\n{url.strip()}"
    validate_reply_text(reply_text)
    return reply_text


def post_community_tweet(text: str, token: str, *, reply_to_tweet_id: str | None = None, include_community: bool = True) -> dict:
    """コミュニティに投稿、またはその投稿に返信"""
    if reply_to_tweet_id:
        validate_reply_text(text)
    else:
        validate_main_post_text(text)

    url = "https://api.x.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"text": text}
    if include_community:
        payload["community_id"] = COMMUNITY_ID
    if reply_to_tweet_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}

    with httpx.Client() as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def save_log(original_tweet: dict, community_post: dict, quote_text: str, reply_post: dict | None = None, reply_text: str = ""):
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
    if reply_post:
        log_data["reply_post"] = {
            "id": reply_post.get("data", {}).get("id", ""),
            "text": reply_text,
            "url": f"https://x.com/i/status/{reply_post.get('data', {}).get('id', '')}",
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


def ensure_oniagi_tag(text: str) -> str:
    """Normalize legacy tags and guarantee that $ONIAGI is present."""
    normalized = (text or "").strip()
    for legacy_tag in LEGACY_TAGS:
        normalized = normalized.replace(legacy_tag, ONIAGI_TAG)

    if ONIAGI_TAG not in normalized:
        lines = normalized.splitlines() if normalized else []
        if lines and URL_LINE_RE.match(lines[-1].strip()):
            url_line = lines.pop().strip()
            lines.extend(["", ONIAGI_TAG, "", url_line])
            normalized = "\n".join(lines)
        else:
            normalized = f"{normalized}\n\n{ONIAGI_TAG}" if normalized else ONIAGI_TAG

    return normalized


def build_quote_text(summary: str, template: str = "notable") -> str:
    """本文用の投稿テキストを構築"""
    templates = {
        "notable": f"🔍 注目ポスト解説\n\n{summary}",
        "news": f"📰 ニュース紹介\n\n{summary}",
        "tip": f"💡 Tips・豆知識\n\n{summary}",
        "simple": summary,
    }
    return ensure_oniagi_tag(templates.get(template, templates["notable"]))


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
        quote_text = build_quote_text(summary, args.template)
        reply_text = build_source_reply_text(
            "📎 元ポスト",
            tweet_url,
            "元の投稿はここから確認できます。論点や温度感を直接たどるための参照リンクです。",
        )
        validate_main_post_text(quote_text)
        validate_reply_text(reply_text)

        # プレビュー
        print("\n" + "=" * 40)
        print("📤 投稿内容:")
        print("=" * 40)
        print(quote_text)
        print("\n↳ リプライ:")
        print(reply_text)
        print("=" * 40 + "\n")

        if args.dry_run:
            print("🔍 ドライランモード: 投稿しません")
            return

        # 投稿実行
        result = post_community_tweet(quote_text, token)
        post_id = result.get("data", {}).get("id", "")
        print(f"✅ 投稿成功: https://x.com/i/status/{post_id}")

        reply_result = post_community_tweet(
            reply_text,
            token,
            reply_to_tweet_id=post_id,
        )
        reply_id = reply_result.get("data", {}).get("id", "")
        print(f"✅ 返信投稿: https://x.com/i/status/{reply_id}")

        # ログ保存
        save_log(tweet, result, quote_text, reply_result, reply_text)

    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

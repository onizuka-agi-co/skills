#!/usr/bin/env python3
"""
X explain post script.
Posts a normal explanation tweet, then replies with the source tweet URL.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

CURRENT_DIR = Path(__file__).resolve().parent
SUNWOOD_SCRIPTS_DIR = CURRENT_DIR.parent.parent / "sunwood-community" / "scripts"
if str(SUNWOOD_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SUNWOOD_SCRIPTS_DIR))

from sunwood_token_auth import load_token_context, request_httpx


ONIAGI_TAG = "$ONIAGI"
LEGACY_TAGS = ("#ONIZUKA_AGI",)
URL_LINE_RE = re.compile(r"^https?://\S+$")
URL_RE = re.compile(r"https?://\S+")
ESCAPED_CONTROL_SEQUENCE_RE = re.compile(r"\\[nrt]")


def extract_tweet_id(url_or_id: str) -> str:
    if url_or_id.isdigit():
        return url_or_id

    parts = urlparse(url_or_id).path.split("/")
    for index, part in enumerate(parts):
        if part == "status" and index + 1 < len(parts):
            return parts[index + 1].split("?")[0]

    raise ValueError(f"Invalid tweet URL or ID: {url_or_id}")


def get_tweet(tweet_id: str, token_context: dict) -> dict:
    url = f"https://api.x.com/2/tweets/{tweet_id}"
    params = {
        "tweet.fields": "created_at,author_id,text",
        "expansions": "author_id",
        "user.fields": "name,username",
    }
    response = request_httpx("GET", url, token_context, params=params)
    return response.json()


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def remove_urls(text: str) -> str:
    without_urls = URL_RE.sub("", text or "")
    return re.sub(r"\n{3,}", "\n\n", without_urls).strip()


def validate_no_literal_escape_sequences(text: str) -> None:
    matches = sorted(set(ESCAPED_CONTROL_SEQUENCE_RE.findall(text or "")))
    if matches:
        raise ValueError(
            "Post text must not contain raw escaped control sequences. "
            f"Found: {', '.join(matches)}"
        )


def validate_main_post_text(text: str) -> None:
    validate_no_literal_escape_sequences(text)
    urls = extract_urls(text)
    if urls:
        raise ValueError(
            "Main post text must not contain URLs. "
            f"Found {len(urls)} URL(s): {', '.join(urls)}"
        )


def validate_reply_text(text: str) -> None:
    validate_no_literal_escape_sequences(text)
    urls = extract_urls(text)
    if len(urls) > 1:
        raise ValueError(
            "Reply text must not contain multiple URLs. "
            f"Found {len(urls)} URL(s): {', '.join(urls)}"
        )


def ensure_oniagi_tag(text: str) -> str:
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


def generate_ai_explanation(tweet_text: str, author_name: str) -> str:
    cleaned = remove_urls(tweet_text)
    if len(cleaned) > 180:
        cleaned = cleaned[:180] + "..."

    if not cleaned:
        cleaned = "元ポストの内容を確認し、要点を短く整理します。"

    body = (
        f"🔍 {author_name}の注目ポスト解説\n\n"
        f"{cleaned}\n\n"
        "重要な論点を短く整理しつつ、元ポストはリプライ側で参照できるようにします。"
    )
    return ensure_oniagi_tag(body)


def build_source_reply_text(original_url: str) -> str:
    reply_text = (
        "📎 元ポスト\n"
        "元の投稿はこちらです。論点と文脈を直接確認したい場合に参照してください。\n"
        f"{original_url}"
    )
    validate_reply_text(reply_text)
    return reply_text


def post_tweet(text: str, token_context: dict, *, reply_to_tweet_id: str | None = None) -> dict:
    if reply_to_tweet_id:
        validate_reply_text(text)
    else:
        validate_main_post_text(text)

    payload = {"text": text}
    if reply_to_tweet_id:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}

    response = request_httpx(
        "POST",
        "https://api.x.com/2/tweets",
        token_context,
        headers={"Content-Type": "application/json"},
        json=payload,
    )
    return response.json()


def emit_result(result: dict, *, json_only: bool) -> None:
    if json_only:
        print(json.dumps(result, ensure_ascii=False))
        return

    if result.get("success"):
        print(f"✅ Explanation posted: {result['tweet_url']}")
        if result.get("reply_tweet_url"):
            print(f"✅ Source reply posted: {result['reply_tweet_url']}")
    else:
        print(f"❌ Failed: {result.get('error')}")

    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Post an explanation tweet and reply with the source URL.")
    parser.add_argument("tweet_url", help="Target tweet URL or ID")
    parser.add_argument("explanation", nargs="?", help="Explanation text for the main post")
    parser.add_argument("--ai", action="store_true", help="Generate the explanation body automatically")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--dry-run", action="store_true", help="Validate only. Do not post.")
    args = parser.parse_args()

    if args.ai and args.explanation:
        raise SystemExit("Do not pass explanation text together with --ai.")
    if not args.ai and not args.explanation:
        raise SystemExit("Explanation text is required unless --ai is specified.")

    token_context = load_token_context()
    tweet_id = extract_tweet_id(args.tweet_url)
    tweet_data = get_tweet(tweet_id, token_context)
    tweet = tweet_data.get("data", {})
    author = tweet_data.get("includes", {}).get("users", [{}])[0]
    author_name = author.get("name", "Unknown")
    original_url = f"https://x.com/i/status/{tweet_id}"

    explanation = generate_ai_explanation(tweet.get("text", ""), author_name) if args.ai else ensure_oniagi_tag(args.explanation or "")
    validate_main_post_text(explanation)
    reply_text = build_source_reply_text(original_url)

    if args.dry_run:
        emit_result(
            {
                "success": True,
                "method": "dry_run",
                "tweet_id": None,
                "tweet_url": None,
                "reply_tweet_id": None,
                "reply_tweet_url": None,
                "explanation": explanation,
                "reply_text": reply_text,
            },
            json_only=args.json,
        )
        return

    main_result = post_tweet(explanation, token_context)
    main_tweet_id = main_result.get("data", {}).get("id", "")
    if not main_tweet_id:
        raise RuntimeError(f"Failed to create main tweet: {main_result}")

    reply_result = post_tweet(reply_text, token_context, reply_to_tweet_id=main_tweet_id)
    reply_tweet_id = reply_result.get("data", {}).get("id", "")
    if not reply_tweet_id:
        raise RuntimeError(f"Failed to create reply tweet: {reply_result}")

    emit_result(
        {
            "success": True,
            "method": "post_with_reply",
            "tweet_id": main_tweet_id,
            "tweet_url": f"https://x.com/i/status/{main_tweet_id}",
            "reply_tweet_id": reply_tweet_id,
            "reply_tweet_url": f"https://x.com/i/status/{reply_tweet_id}",
        },
        json_only=args.json,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error = {"success": False, "error": str(exc)}
        print(json.dumps(error, ensure_ascii=False))
        sys.exit(1)

#!/usr/bin/env python3
"""
X (Twitter) Filtered Stream Client

Monitor tweets in real-time using X's Filtered Stream API.

Usage:
    python x_filtered_stream.py test           # Test configuration
    python x_filtered_stream.py setup          # Setup default rules
    python x_filtered_stream.py rules          # List current rules
    python x_filtered_stream.py add <rule> <tag>  # Add custom rule
    python x_filtered_stream.py clear          # Delete all rules
    python x_filtered_stream.py stream         # Start streaming
    python x_filtered_stream.py test-webhook   # Test webhook notification
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Configuration
SCRIPT_DIR = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent.parent
DATA_DIR = WORKSPACE_DIR / "data" / "x"

# API Endpoints
BASE_URL = "https://api.twitter.com/2"
STREAM_URL = f"{BASE_URL}/tweets/search/stream"
RULES_URL = f"{BASE_URL}/tweets/search/stream/rules"

# Default configuration
DEFAULT_RULES = [
    {
        "value": "from:hAru_mAki_ch -is:retweet -is:reply",
        "tag": "haru_maki_new_posts"
    }
]

DEFAULT_TWEET_FIELDS = [
    "created_at",
    "author_id",
    "public_metrics",
    "entities",
    "attachments"
]


def load_bearer_token() -> str:
    """Load Bearer Token from file or environment."""
    # Try file first
    token_file = DATA_DIR / "x-bearer-token.json"
    if token_file.exists():
        with open(token_file) as f:
            data = json.load(f)
            return data.get("bearer_token", "")

    # Try environment variable
    token = os.environ.get("X_BEARER_TOKEN", "")
    if token:
        return token

    raise ValueError(
        "Bearer Token not found. Set X_BEARER_TOKEN environment variable "
        "or create data/x/x-bearer-token.json"
    )


def load_webhook_url() -> str | None:
    """Load Discord Webhook URL from file."""
    webhook_file = DATA_DIR / "x-discord-webhook.json"
    if webhook_file.exists():
        with open(webhook_file) as f:
            data = json.load(f)
            return data.get("webhook_url", "")
    return None


def get_headers(token: str) -> dict[str, str]:
    """Get authorization headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def test_config(token: str) -> bool:
    """Test API configuration."""
    print("🔧 Testing X Filtered Stream configuration...")

    # Test Bearer Token
    try:
        headers = get_headers(token)
        response = requests.get(RULES_URL, headers=headers)

        if response.status_code == 200:
            print("✅ Bearer Token is valid")
            return True
        elif response.status_code == 403:
            print("❌ 403 Forbidden - Check your app permissions")
            print("   Filtered Stream access required")
            return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def get_rules(token: str) -> dict[str, Any]:
    """Get current stream rules."""
    headers = get_headers(token)
    response = requests.get(RULES_URL, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting rules: {response.status_code}")
        print(response.text)
        return {"data": [], "meta": {"result_count": 0}}


def list_rules(token: str) -> None:
    """List current stream rules."""
    print("📋 Current Filtered Stream rules:")
    result = get_rules(token)

    data = result.get("data", [])
    if not data:
        print("   No rules configured")
        return

    for i, rule in enumerate(data, 1):
        print(f"   {i}. [{rule.get('tag', 'no-tag')}]")
        print(f"      {rule.get('value', 'no-value')}")
        print(f"      ID: {rule.get('id', 'unknown')}")
    print(f"\n   Total: {len(data)} rules")


def setup_rules(token: str) -> None:
    """Setup default stream rules."""
    print("🔧 Setting up default rules...")

    # First, clear existing rules
    result = get_rules(token)
    data = result.get("data", [])

    if data:
        ids = [rule["id"] for rule in data]
        delete_payload = {"delete": {"ids": ids}}
        headers = get_headers(token)
        response = requests.post(RULES_URL, headers=headers, json=delete_payload)

        if response.status_code == 200:
            print(f"   Deleted {len(ids)} existing rules")
        else:
            print(f"   Error deleting rules: {response.status_code}")

    # Add default rules
    payload = {"add": DEFAULT_RULES}
    headers = get_headers(token)
    response = requests.post(RULES_URL, headers=headers, json=payload)

    if response.status_code == 201:
        print("✅ Default rules added:")
        for rule in DEFAULT_RULES:
            print(f"   - {rule['tag']}: {rule['value']}")
    else:
        print(f"❌ Error adding rules: {response.status_code}")
        print(response.text)


def add_rule(token: str, value: str, tag: str) -> None:
    """Add a custom stream rule."""
    print(f"🔧 Adding rule: [{tag}] {value}")

    payload = {"add": [{"value": value, "tag": tag}]}
    headers = get_headers(token)
    response = requests.post(RULES_URL, headers=headers, json=payload)

    if response.status_code == 201:
        print("✅ Rule added successfully")
    else:
        print(f"❌ Error adding rule: {response.status_code}")
        print(response.text)


def clear_rules(token: str) -> None:
    """Delete all stream rules."""
    print("🗑️ Clearing all rules...")

    result = get_rules(token)
    data = result.get("data", [])

    if not data:
        print("   No rules to delete")
        return

    ids = [rule["id"] for rule in data]
    payload = {"delete": {"ids": ids}}
    headers = get_headers(token)
    response = requests.post(RULES_URL, headers=headers, json=payload)

    if response.status_code == 200:
        print(f"✅ Deleted {len(ids)} rules")
    else:
        print(f"❌ Error deleting rules: {response.status_code}")
        print(response.text)


def send_webhook(tweet: dict[str, Any]) -> bool:
    """Send tweet to Discord webhook."""
    webhook_url = load_webhook_url()
    if not webhook_url:
        print("⚠️ No webhook URL configured")
        return False

    # Format tweet data
    tweet_id = tweet.get("id", "unknown")
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "unknown")
    created_at = tweet.get("created_at", "")

    # Build tweet URL (we need username, but we only have author_id)
    tweet_url = f"https://twitter.com/user/status/{tweet_id}"

    # Create Discord embed
    embed = {
        "title": "🐦 New Tweet Detected",
        "description": text,
        "url": tweet_url,
        "color": 0x1DA1F2,  # Twitter blue
        "fields": [
            {"name": "Author ID", "value": author_id, "inline": True},
            {"name": "Tweet ID", "value": tweet_id, "inline": True},
        ],
        "timestamp": created_at,
        "footer": {"text": "X Filtered Stream"}
    }

    payload = {
        "content": "<@&1475432244725288973> 新しいツイートを検知しました！タスクを実行してください",
        "embeds": [embed],
        "allowed_mentions": {"roles": ["1475432244725288973"]}
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print(f"✅ Webhook sent for tweet {tweet_id}")
            return True
        else:
            print(f"❌ Webhook error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False


def test_webhook(token: str) -> None:
    """Test webhook notification with a fake tweet."""
    print("🧪 Testing webhook notification...")

    fake_tweet = {
        "id": "test_tweet_123",
        "text": "This is a test tweet from X Filtered Stream",
        "author_id": "test_author",
        "created_at": "2026-03-18T00:00:00.000Z"
    }

    if send_webhook(fake_tweet):
        print("✅ Webhook test successful")
    else:
        print("❌ Webhook test failed")


def stream_tweets(token: str) -> None:
    """Start streaming tweets."""
    print("🚀 Starting Filtered Stream...")
    print("   Press Ctrl+C to stop\n")

    headers = get_headers(token)
    params = {
        "tweet.fields": ",".join(DEFAULT_TWEET_FIELDS)
    }

    try:
        with requests.get(
            STREAM_URL,
            headers=headers,
            params=params,
            stream=True,
            timeout=(10, None)  # Connection timeout, no read timeout
        ) as response:
            if response.status_code != 200:
                print(f"❌ Stream error: {response.status_code}")
                print(response.text)
                return

            print("✅ Connected to stream")
            print("   Waiting for tweets...\n")

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Keep-alive signals
                    if "data" not in data:
                        continue

                    tweet = data["data"]
                    print(f"\n🐦 New tweet: {tweet.get('id', 'unknown')}")
                    print(f"   {tweet.get('text', '')[:100]}...")

                    # Send to webhook
                    send_webhook(tweet)

                    # Save state
                    save_state(tweet)

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing tweet: {e}")

    except KeyboardInterrupt:
        print("\n\n⏹️ Stream stopped by user")
    except Exception as e:
        print(f"\n❌ Stream error: {e}")


def save_state(tweet: dict[str, Any]) -> None:
    """Save last tweet state."""
    state_file = DATA_DIR / "x-stream-state.json"

    state = {
        "last_tweet_id": tweet.get("id", ""),
        "last_tweet_at": tweet.get("created_at", "")
    }

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="X (Twitter) Filtered Stream Client"
    )
    parser.add_argument(
        "command",
        choices=["test", "setup", "rules", "add", "clear", "stream", "test-webhook"],
        help="Command to execute"
    )
    parser.add_argument("args", nargs="*", help="Additional arguments")

    args = parser.parse_args()

    # Load token
    try:
        token = load_bearer_token()
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Execute command
    if args.command == "test":
        success = test_config(token)
        sys.exit(0 if success else 1)

    elif args.command == "setup":
        setup_rules(token)

    elif args.command == "rules":
        list_rules(token)

    elif args.command == "add":
        if len(args.args) < 2:
            print("Usage: python x_filtered_stream.py add <rule> <tag>")
            sys.exit(1)
        add_rule(token, args.args[0], args.args[1])

    elif args.command == "clear":
        clear_rules(token)

    elif args.command == "stream":
        stream_tweets(token)

    elif args.command == "test-webhook":
        test_webhook(token)


if __name__ == "__main__":
    main()

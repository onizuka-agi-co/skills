#!/usr/bin/env python3
"""X Filtered Stream client with Discord Webhook notifications."""

import argparse
import json
import signal
import sys
import time
from pathlib import Path

import requests

# --- Config paths ---
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
BEARER_FILE = DATA_DIR / "x-bearer-token.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"
STATE_FILE = DATA_DIR / "x-stream-state.json"

STREAM_URL = "https://api.x.com/2/tweets/search/stream"
RULES_URL = "https://api.x.com/2/tweets/search/stream/rules"

# Default rule
DEFAULT_RULE = "from:hAru_mAki_ch -is:retweet -is:reply"
DEFAULT_TAG = "haru_maki_posts"


def get_bearer_token() -> str:
    if BEARER_FILE.exists():
        return json.loads(BEARER_FILE.read_text())["bearer_token"]
    raise SystemExit(f"Bearer token not found: {BEARER_FILE}")


def get_webhook_url() -> str:
    if WEBHOOK_FILE.exists():
        return json.loads(WEBHOOK_FILE.read_text())["webhook_url"]
    raise SystemExit(f"Webhook URL not found: {WEBHOOK_FILE}")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- Rule management ---
def list_rules(token: str):
    r = requests.get(RULES_URL, headers=auth_headers(token))
    r.raise_for_status()
    data = r.json()
    rules = data.get("data", [])
    if not rules:
        print("No rules configured.")
        return
    for rule in rules:
        print(f"  [{rule['id']}] {rule['value']}  tag={rule.get('tag', '-')}")


def clear_rules(token: str):
    r = requests.get(RULES_URL, headers=auth_headers(token))
    r.raise_for_status()
    rules = r.json().get("data", [])
    if not rules:
        print("No rules to clear.")
        return
    ids = {"delete": {"ids": [r["id"] for r in rules]}}
    r = requests.post(RULES_URL, headers=auth_headers(token), json=ids)
    r.raise_for_status()
    print(f"Cleared {len(rules)} rules.")


def add_rule(token: str, value: str, tag: str):
    payload = {"add": [{"value": value, "tag": tag}]}
    r = requests.post(RULES_URL, headers=auth_headers(token), json=payload)
    r.raise_for_status()
    print(f"Added rule: {value} (tag={tag})")


def setup_default_rules(token: str):
    """Clear existing and add default rule."""
    clear_rules(token)
    add_rule(token, DEFAULT_RULE, DEFAULT_TAG)
    print("Default rules set up.")


# --- State ---
def save_state(tweet_id: str, tweet_at: str):
    state = {"last_tweet_id": tweet_id, "last_tweet_at": tweet_at}
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


# --- Discord notification ---
def send_webhook(webhook_url: str, tweet_text: str, tweet_id: str, author: str = "hAru_mAki_ch"):
    tweet_url = f"https://x.com/{author}/status/{tweet_id}"
    embed = {
        "title": f"🐦 新規投稿: @{author}",
        "description": tweet_text[:2048] if tweet_text else "(no text)",
        "url": tweet_url,
        "color": 0x1DA1F2,
        "fields": [
            {"name": "Link", "value": tweet_url, "inline": False}
        ],
        "footer": {"text": "X Filtered Stream"},
    }
    payload = {
        "username": "朱燈烏 🔔",
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }
    r = requests.post(webhook_url, json=payload, timeout=10,
                       headers={"User-Agent": "ONIZUKA-FilteredStream/1.0"})
    r.raise_for_status()
    print(f"  Notified Discord: {tweet_id}")


def send_test_webhook(webhook_url: str):
    embed = {
        "title": "🧪 テスト通知",
        "description": "X Filtered Stream 接続テスト",
        "color": 0x4CAF50,
        "footer": {"text": "X Filtered Stream"},
    }
    payload = {
        "username": "朱燈烏 🔔",
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }
    r = requests.post(webhook_url, json=payload, timeout=10,
                       headers={"User-Agent": "ONIZUKA-FilteredStream/1.0"})
    r.raise_for_status()
    print("Test notification sent ✓")


# --- Stream ---
def stream(token: str, webhook_url: str):
    """Connect to filtered stream and forward tweets to Discord."""
    print("Connecting to filtered stream...")
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        print("\nDisconnecting...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running:
        try:
            params = {
                "tweet.fields": "created_at,author_id,public_metrics,entities,attachments",
                "expansions": "author_id",
                "user.fields": "username",
            }
            r = requests.get(STREAM_URL, headers=auth_headers(token),
                              params=params, stream=True, timeout=90)
            r.raise_for_status()

            print(f"Stream connected (status {r.status_code})")
            for line in r.iter_lines(decode_unicode=True):
                if not running:
                    break
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Check for errors
                if "errors" in data:
                    print(f"Stream error: {data['errors']}")
                    continue

                tweet = data.get("data")
                if not tweet:
                    continue

                tweet_id = tweet["id"]
                tweet_text = tweet.get("text", "")
                created_at = tweet.get("created_at", "")

                # Get author username from includes
                username = "unknown"
                includes = data.get("includes", {})
                users = includes.get("users", [])
                if users:
                    username = users[0].get("username", "unknown")

                print(f"Tweet: [{username}] {tweet_text[:80]}...")
                send_webhook(webhook_url, tweet_text, tweet_id, username)
                save_state(tweet_id, created_at)

        except requests.exceptions.Timeout:
            print("Stream timeout, reconnecting...")
            continue
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}")
            print("Reconnecting in 10s...")
            time.sleep(10)
            continue
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            if r.status_code == 429:
                print("Rate limited, waiting 60s...")
                time.sleep(60)
            elif r.status_code >= 500:
                print("Server error, reconnecting in 30s...")
                time.sleep(30)
            else:
                print(f"Fatal HTTP error ({r.status_code}), stopping.")
                break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(10)

    print("Stream stopped.")


# --- Test connection ---
def test_connection(token: str):
    """Verify bearer token works by listing rules."""
    print("Testing connection...")
    r = requests.get(RULES_URL, headers=auth_headers(token))
    if r.status_code == 200:
        print("✓ Connection OK")
        list_rules(token)
    else:
        print(f"✗ Connection failed: {r.status_code} {r.text}")


# --- CLI ---
def main():
    parser = argparse.ArgumentParser(description="X Filtered Stream")
    parser.add_argument("command", choices=[
        "test", "rules", "setup", "add", "clear", "stream", "test-webhook"
    ])
    parser.add_argument("--value", help="Rule value for 'add'")
    parser.add_argument("--tag", help="Rule tag for 'add'", default="custom")
    args = parser.parse_args()

    token = get_bearer_token()

    if args.command == "test":
        test_connection(token)
    elif args.command == "rules":
        list_rules(token)
    elif args.command == "setup":
        setup_default_rules(token)
    elif args.command == "add":
        if not args.value:
            print("--value is required for 'add'")
            sys.exit(1)
        add_rule(token, args.value, args.tag)
    elif args.command == "clear":
        clear_rules(token)
    elif args.command == "test-webhook":
        webhook_url = get_webhook_url()
        send_test_webhook(webhook_url)
    elif args.command == "stream":
        webhook_url = get_webhook_url()
        stream(token, webhook_url)


if __name__ == "__main__":
    main()

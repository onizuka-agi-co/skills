#!/usr/bin/env python3
"""
X Filtered Stream - Twitter/X Filtered Stream API Client

Real-time tweet monitoring with Discord webhook notifications.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library required. Run: pip install requests")
    sys.exit(1)

# Configuration paths
WORKSPACE = Path(__file__).parent.parent.parent.parent
BEARER_TOKEN_FILE = WORKSPACE / "data" / "x" / "x-bearer-token.json"
WEBHOOK_FILE = WORKSPACE / "data" / "x" / "x-discord-webhook.json"
STATE_FILE = WORKSPACE / "data" / "x" / "x-stream-state.json"

# X API endpoints
BASE_URL = "https://api.x.com/2"
STREAM_URL = f"{BASE_URL}/tweets/search/stream"
RULES_URL = f"{BASE_URL}/tweets/search/stream/rules"

# Default rule for hAru_mAki_ch
DEFAULT_RULE = "from:hAru_mAki_ch -is:retweet -is:reply"
DEFAULT_TAG = "haru_maki_new_posts"


def get_bearer_token() -> str:
    """Get bearer token from file or environment."""
    # Try environment variable first
    token = os.environ.get("X_BEARER_TOKEN")
    if token:
        return token
    
    # Try file
    if BEARER_TOKEN_FILE.exists():
        with open(BEARER_TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("bearer_token", "")
    
    raise ValueError("Bearer token not found. Set X_BEARER_TOKEN or create data/x/x-bearer-token.json")


def get_webhook_url() -> Optional[str]:
    """Get Discord webhook URL from file."""
    if WEBHOOK_FILE.exists():
        with open(WEBHOOK_FILE) as f:
            data = json.load(f)
            return data.get("webhook_url")
    return None


def get_headers(token: str) -> dict:
    """Get API headers with bearer token."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def test_connection(token: str) -> bool:
    """Test API connection and credentials."""
    print("Testing X API connection...")
    
    headers = get_headers(token)
    
    # Test getting rules (validates credentials)
    response = requests.get(RULES_URL, headers=headers)
    
    if response.status_code == 200:
        print("✓ API connection successful")
        data = response.json()
        print(f"✓ Current rules: {len(data.get('data', []))}")
        return True
    elif response.status_code == 403:
        print("✗ 403 Forbidden - Check Bearer Token and app permissions")
        return False
    else:
        print(f"✗ Error: {response.status_code} - {response.text}")
        return False


def get_rules(token: str) -> list:
    """Get current stream rules."""
    headers = get_headers(token)
    response = requests.get(RULES_URL, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])
    return []


def list_rules(token: str):
    """List current rules."""
    rules = get_rules(token)
    
    if not rules:
        print("No rules configured")
        return
    
    print(f"Current rules ({len(rules)}):")
    for rule in rules:
        print(f"  - [{rule.get('id')}] {rule.get('value')}")
        if rule.get('tag'):
            print(f"    Tag: {rule.get('tag')}")


def clear_rules(token: str):
    """Clear all rules."""
    rules = get_rules(token)
    
    if not rules:
        print("No rules to clear")
        return
    
    headers = get_headers(token)
    ids = [r["id"] for r in rules]
    
    payload = {"delete": {"ids": ids}}
    response = requests.post(RULES_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print(f"✓ Cleared {len(ids)} rules")
    else:
        print(f"✗ Error clearing rules: {response.status_code} - {response.text}")


def add_rule(token: str, value: str, tag: Optional[str] = None):
    """Add a new rule."""
    headers = get_headers(token)
    
    rule = {"value": value}
    if tag:
        rule["tag"] = tag
    
    payload = {"add": [rule]}
    response = requests.post(RULES_URL, headers=headers, json=payload)
    
    if response.status_code == 201:
        data = response.json()
        print(f"✓ Rule added: {value}")
        if data.get("data"):
            for r in data["data"]:
                print(f"  ID: {r.get('id')}")
    else:
        print(f"✗ Error adding rule: {response.status_code} - {response.text}")


def setup_default_rules(token: str):
    """Setup default rules for hAru_mAki_ch."""
    print(f"Setting up default rule: {DEFAULT_RULE}")
    
    # Clear existing rules first
    clear_rules(token)
    time.sleep(0.5)
    
    # Add default rule
    add_rule(token, DEFAULT_RULE, DEFAULT_TAG)


def save_state(tweet_id: str, tweet_data: dict):
    """Save last tweet state."""
    state = {
        "last_tweet_id": tweet_id,
        "last_tweet_at": tweet_data.get("created_at", ""),
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_discord_notification(webhook_url: str, tweet: dict):
    """Send Discord notification for a tweet."""
    tweet_id = tweet.get("id", "")
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")
    created_at = tweet.get("created_at", "")
    
    # Build tweet URL
    tweet_url = f"https://x.com/user/status/{tweet_id}"
    
    # Build embed
    embed = {
        "title": "🆕 New Tweet Detected",
        "description": text[:500] + ("..." if len(text) > 500 else ""),
        "url": tweet_url,
        "color": 0x1DA1F2,  # Twitter blue
        "fields": [
            {"name": "Tweet ID", "value": tweet_id, "inline": True},
            {"name": "Author ID", "value": author_id, "inline": True},
        ],
        "timestamp": created_at,
        "footer": {"text": "X Filtered Stream"}
    }
    
    payload = {
        "content": "<@&1475432244725288973> 新しいツイートを検知しました",
        "embeds": [embed]
    }
    
    response = requests.post(webhook_url, json=payload)
    
    if response.status_code == 204:
        print(f"✓ Discord notification sent for tweet {tweet_id}")
    else:
        print(f"✗ Discord notification failed: {response.status_code}")


def test_webhook(token: str):
    """Test Discord webhook notification."""
    webhook_url = get_webhook_url()
    
    if not webhook_url:
        print("✗ Webhook URL not found in data/x/x-discord-webhook.json")
        return
    
    # Send test notification
    test_tweet = {
        "id": "test_123456",
        "text": "This is a test notification from X Filtered Stream",
        "author_id": "test_user",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    print("Sending test notification...")
    send_discord_notification(webhook_url, test_tweet)


def stream(token: str):
    """Start streaming tweets."""
    webhook_url = get_webhook_url()
    
    if not webhook_url:
        print("Warning: No webhook URL configured. Tweets will be logged only.")
    
    headers = get_headers(token)
    
    # Tweet fields to retrieve
    params = {
        "tweet.fields": "created_at,author_id,public_metrics,entities,attachments"
    }
    
    print("Starting X Filtered Stream...")
    print(f"Monitoring rules: {DEFAULT_RULE}")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            response = requests.get(
                STREAM_URL,
                headers=headers,
                params=params,
                stream=True,
                timeout=90
            )
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                print("Retrying in 10 seconds...")
                time.sleep(10)
                continue
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Check for errors
                    if "errors" in data:
                        print(f"Error: {data['errors']}")
                        continue
                    
                    # Process tweet
                    if "data" in data:
                        tweet = data["data"]
                        tweet_id = tweet.get("id")
                        text = tweet.get("text", "")
                        
                        print(f"\n{'='*60}")
                        print(f"Tweet ID: {tweet_id}")
                        print(f"Text: {text[:100]}...")
                        print(f"{'='*60}")
                        
                        # Save state
                        save_state(tweet_id, tweet)
                        
                        # Send notification
                        if webhook_url:
                            send_discord_notification(webhook_url, tweet)
                
                except json.JSONDecodeError:
                    continue
        
        except requests.exceptions.Timeout:
            print("Connection timeout, reconnecting...")
            continue
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            print("Reconnecting in 10 seconds...")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\nStream stopped by user")
            break


def main():
    parser = argparse.ArgumentParser(description="X Filtered Stream Client")
    parser.add_argument("command", choices=[
        "test", "setup", "rules", "clear", "add", "stream", "test-webhook"
    ], help="Command to execute")
    parser.add_argument("value", nargs="?", help="Rule value (for 'add')")
    parser.add_argument("--tag", help="Rule tag (for 'add')")
    
    args = parser.parse_args()
    
    try:
        token = get_bearer_token()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    if args.command == "test":
        test_connection(token)
    elif args.command == "setup":
        setup_default_rules(token)
    elif args.command == "rules":
        list_rules(token)
    elif args.command == "clear":
        clear_rules(token)
    elif args.command == "add":
        if not args.value:
            print("Error: Rule value required for 'add' command")
            sys.exit(1)
        add_rule(token, args.value, args.tag)
    elif args.command == "stream":
        stream(token)
    elif args.command == "test-webhook":
        test_webhook(token)


if __name__ == "__main__":
    main()

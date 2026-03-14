#!/usr/bin/env python3
"""
X (Twitter) Filtered Stream Client

Monitor tweets in real-time using Twitter's Filtered Stream API.

Usage:
    uv run x_filtered_stream.py test           # Test configuration
    uv run x_filtered_stream.py setup          # Setup default rules
    uv run x_filtered_stream.py rules          # List current rules
    uv run x_filtered_stream.py add <rule> [tag]  # Add a rule
    uv run x_filtered_stream.py clear          # Clear all rules
    uv run x_filtered_stream.py stream         # Start streaming
    uv run x_filtered_stream.py test-webhook   # Test Discord webhook
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Paths
SCRIPT_DIR = Path(__file__).parent
WORKSPACE = SCRIPT_DIR.parent.parent.parent
DATA_DIR = WORKSPACE / "data" / "x"
BEARER_TOKEN_FILE = DATA_DIR / "x-bearer-token.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"
STATE_FILE = DATA_DIR / "x-stream-state.json"

# Twitter API endpoints
STREAM_URL = "https://api.twitter.com/2/tweets/search/stream"
RULES_URL = "https://api.twitter.com/2/tweets/search/stream/rules"

# Tweet fields to request
TWEET_FIELDS = "created_at,author_id,public_metrics,entities,attachments"


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


def get_webhook_url() -> str | None:
    """Get Discord webhook URL from file."""
    if WEBHOOK_FILE.exists():
        with open(WEBHOOK_FILE) as f:
            data = json.load(f)
            return data.get("webhook_url")
    return None


def load_state() -> dict:
    """Load stream state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """Save stream state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def twitter_request(url: str, method: str = "GET", data: dict | None = None) -> dict:
    """Make authenticated request to Twitter API."""
    token = get_bearer_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    body = json.dumps(data).encode() if data else None
    
    req = Request(url, method=method, headers=headers, data=body)
    
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {error_body}", file=sys.stderr)
        raise


def send_discord_notification(tweet: dict, webhook_url: str | None = None):
    """Send tweet notification to Discord."""
    webhook_url = webhook_url or get_webhook_url()
    if not webhook_url:
        print("No Discord webhook configured", file=sys.stderr)
        return False
    
    tweet_id = tweet.get("id", "")
    tweet_text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")
    created_at = tweet.get("created_at", "")
    
    # Build tweet URL
    tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
    
    # Build embed
    embed = {
        "title": "🐦 New Tweet Detected",
        "description": tweet_text[:500] + ("..." if len(tweet_text) > 500 else ""),
        "url": tweet_url,
        "color": 0x1DA1F2,  # Twitter blue
        "fields": [
            {"name": "Tweet ID", "value": tweet_id, "inline": True},
            {"name": "Author ID", "value": author_id, "inline": True},
        ],
        "timestamp": created_at,
    }
    
    payload = {
        "content": "<@&1475432244725288973> 新しいツイートを検知しました",
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }
    
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload).encode()
    
    req = Request(webhook_url, method="POST", headers=headers, data=body)
    
    try:
        with urlopen(req, timeout=10) as response:
            return response.status == 204
    except Exception as e:
        print(f"Discord webhook error: {e}", file=sys.stderr)
        return False


def cmd_test(args):
    """Test configuration."""
    print("📋 Testing X Filtered Stream configuration...")
    
    # Test bearer token
    try:
        token = get_bearer_token()
        print(f"✅ Bearer token found: {token[:20]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    
    # Test API access
    try:
        result = twitter_request(RULES_URL)
        print(f"✅ API access OK - {len(result.get('data', []))} rules configured")
    except Exception as e:
        print(f"❌ API access failed: {e}")
        return 1
    
    # Test webhook
    webhook = get_webhook_url()
    if webhook:
        print(f"✅ Discord webhook configured: {webhook[:50]}...")
    else:
        print("⚠️ No Discord webhook configured")
    
    print("\n✅ Configuration test passed!")
    return 0


def cmd_rules(args):
    """List current rules."""
    print("📋 Current Filtered Stream rules:")
    
    try:
        result = twitter_request(RULES_URL)
        rules = result.get("data", [])
        
        if not rules:
            print("  No rules configured")
            return 0
        
        for i, rule in enumerate(rules, 1):
            rule_id = rule.get("id", "?")
            value = rule.get("value", "?")
            tag = rule.get("tag", "")
            print(f"  {i}. [{rule_id}] {value}")
            if tag:
                print(f"     Tag: {tag}")
        
        print(f"\nTotal: {len(rules)} rules")
    except Exception as e:
        print(f"❌ Failed to get rules: {e}")
        return 1
    
    return 0


def cmd_setup(args):
    """Setup default rules."""
    print("🔧 Setting up default rules...")
    
    # Default rule: monitor hAru_mAki_ch
    default_rules = [
        {
            "value": "from:hAru_mAki_ch -is:retweet -is:reply",
            "tag": "haru_maki_new_posts"
        }
    ]
    
    # Clear existing rules first
    try:
        result = twitter_request(RULES_URL)
        existing = result.get("data", [])
        if existing:
            ids = [r["id"] for r in existing]
            twitter_request(RULES_URL, "POST", {"delete": {"ids": ids}})
            print(f"  Cleared {len(ids)} existing rules")
    except Exception as e:
        print(f"  Warning: Could not clear existing rules: {e}")
    
    # Add default rules
    try:
        result = twitter_request(RULES_URL, "POST", {"add": default_rules})
        added = result.get("data", [])
        print(f"✅ Added {len(added)} rules:")
        for rule in added:
            print(f"  - {rule.get('value')}")
    except Exception as e:
        print(f"❌ Failed to add rules: {e}")
        return 1
    
    return 0


def cmd_add(args):
    """Add a custom rule."""
    if not args.rule:
        print("❌ Rule value required")
        return 1
    
    rule_data = {"value": args.rule}
    if args.tag:
        rule_data["tag"] = args.tag
    
    print(f"➕ Adding rule: {args.rule}")
    
    try:
        result = twitter_request(RULES_URL, "POST", {"add": [rule_data]})
        added = result.get("data", [])
        if added:
            print(f"✅ Rule added with ID: {added[0].get('id')}")
        else:
            print("⚠️ Rule may not have been added")
    except Exception as e:
        print(f"❌ Failed to add rule: {e}")
        return 1
    
    return 0


def cmd_clear(args):
    """Clear all rules."""
    print("🗑️ Clearing all rules...")
    
    try:
        result = twitter_request(RULES_URL)
        existing = result.get("data", [])
        
        if not existing:
            print("  No rules to clear")
            return 0
        
        ids = [r["id"] for r in existing]
        twitter_request(RULES_URL, "POST", {"delete": {"ids": ids}})
        print(f"✅ Cleared {len(ids)} rules")
    except Exception as e:
        print(f"❌ Failed to clear rules: {e}")
        return 1
    
    return 0


def cmd_stream(args):
    """Start streaming tweets."""
    print("🐦 Starting X Filtered Stream...")
    print("Press Ctrl+C to stop\n")
    
    token = get_bearer_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    url = f"{STREAM_URL}?tweet.fields={TWEET_FIELDS}"
    
    try:
        req = Request(url, headers=headers)
        
        with urlopen(req, timeout=None) as response:
            print("✅ Connected to stream\n")
            
            for line in response:
                line = line.decode().strip()
                
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Check for errors
                    if "errors" in data:
                        print(f"⚠️ Error: {data['errors']}", file=sys.stderr)
                        continue
                    
                    # Process tweet
                    if "data" in data:
                        tweet = data["data"]
                        tweet_id = tweet.get("id", "")
                        tweet_text = tweet.get("text", "")
                        
                        print(f"🐦 Tweet: {tweet_id}")
                        print(f"   {tweet_text[:100]}...")
                        
                        # Save state
                        save_state({
                            "last_tweet_id": tweet_id,
                            "last_tweet_at": tweet.get("created_at", ""),
                        })
                        
                        # Send notification
                        webhook_url = get_webhook_url()
                        if webhook_url:
                            if send_discord_notification(tweet, webhook_url):
                                print("   ✅ Discord notification sent")
                            else:
                                print("   ⚠️ Discord notification failed")
                        
                        print()
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠️ Error processing tweet: {e}", file=sys.stderr)
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Stream stopped by user")
    except Exception as e:
        print(f"❌ Stream error: {e}", file=sys.stderr)
        return 1
    
    return 0


def cmd_test_webhook(args):
    """Test Discord webhook."""
    print("🔔 Testing Discord webhook...")
    
    webhook_url = get_webhook_url()
    if not webhook_url:
        print("❌ No webhook URL configured")
        return 1
    
    # Create test tweet
    test_tweet = {
        "id": "test_123456789",
        "text": "This is a test tweet from X Filtered Stream",
        "author_id": "test_author",
        "created_at": "2026-01-01T00:00:00.000Z",
    }
    
    if send_discord_notification(test_tweet, webhook_url):
        print("✅ Webhook test successful!")
        return 0
    else:
        print("❌ Webhook test failed")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="X Filtered Stream Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # test
    subparsers.add_parser("test", help="Test configuration")
    
    # setup
    subparsers.add_parser("setup", help="Setup default rules")
    
    # rules
    subparsers.add_parser("rules", help="List current rules")
    
    # add
    add_parser = subparsers.add_parser("add", help="Add a custom rule")
    add_parser.add_argument("rule", help="Rule value (e.g., 'from:user -is:retweet')")
    add_parser.add_argument("tag", nargs="?", help="Optional tag for the rule")
    
    # clear
    subparsers.add_parser("clear", help="Clear all rules")
    
    # stream
    subparsers.add_parser("stream", help="Start streaming tweets")
    
    # test-webhook
    subparsers.add_parser("test-webhook", help="Test Discord webhook")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        "test": cmd_test,
        "setup": cmd_setup,
        "rules": cmd_rules,
        "add": cmd_add,
        "clear": cmd_clear,
        "stream": cmd_stream,
        "test-webhook": cmd_test_webhook,
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

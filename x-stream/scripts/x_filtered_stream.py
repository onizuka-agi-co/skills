#!/usr/bin/env python3
"""
X Filtered Stream Client

Monitor X (Twitter) in real-time using Filtered Stream API
and send notifications to Discord webhook.

Usage:
    python x_filtered_stream.py test        - Test configuration
    python x_filtered_stream.py setup       - Setup default rules
    python x_filtered_stream.py add <rule> <tag> - Add a rule
    python x_filtered_stream.py rules       - List current rules
    python x_filtered_stream.py clear       - Clear all rules
    python x_filtered_stream.py stream      - Start streaming
"""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Configuration
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
BEARER_TOKEN_FILE = WORKSPACE_ROOT / "data" / "x" / "x-bearer-token.json"
WEBHOOK_FILE = WORKSPACE_ROOT / "data" / "x" / "x-discord-webhook.json"
STATE_FILE = WORKSPACE_ROOT / "data" / "x" / "x-stream-state.json"

BASE_URL = "https://api.x.com/2"

DEFAULT_RULE = {
    "value": "from:hAru_mAki_ch -is:retweet -is:reply",
    "tag": "haru_maki_new_posts"
}

TWEET_FIELDS = "created_at,author_id,public_metrics,entities,attachments"


def get_bearer_token():
    """Get bearer token from file or environment."""
    # Try file first
    if BEARER_TOKEN_FILE.exists():
        with open(BEARER_TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("bearer_token")
    
    # Try environment
    return os.environ.get("X_BEARER_TOKEN")


def get_webhook_url():
    """Get Discord webhook URL from file."""
    if WEBHOOK_FILE.exists():
        with open(WEBHOOK_FILE) as f:
            data = json.load(f)
            return data.get("webhook_url")
    return None


def get_headers():
    """Get API headers with bearer token."""
    token = get_bearer_token()
    if not token:
        raise ValueError("Bearer token not found. Set X_BEARER_TOKEN or create data/x/x-bearer-token.json")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def api_request(method, endpoint, data=None):
    """Make API request to X API."""
    url = f"{BASE_URL}{endpoint}"
    headers = get_headers()
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return response


def get_rules():
    """Get current stream rules."""
    response = api_request("GET", "/tweets/search/stream/rules")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting rules: {response.status_code}")
        print(response.text)
        return None


def add_rule(value, tag):
    """Add a stream rule."""
    data = {
        "add": [{"value": value, "tag": tag}]
    }
    response = api_request("POST", "/tweets/search/stream/rules", data)
    if response.status_code == 200:
        print(f"✅ Rule added: {tag}")
        return response.json()
    else:
        print(f"❌ Error adding rule: {response.status_code}")
        print(response.text)
        return None


def delete_all_rules():
    """Delete all stream rules."""
    rules = get_rules()
    if not rules or "data" not in rules:
        print("No rules to delete")
        return
    
    ids = [rule["id"] for rule in rules.get("data", [])]
    if not ids:
        print("No rules to delete")
        return
    
    data = {"delete": {"ids": ids}}
    response = api_request("POST", "/tweets/search/stream/rules", data)
    if response.status_code == 200:
        print(f"✅ Deleted {len(ids)} rules")
    else:
        print(f"❌ Error deleting rules: {response.status_code}")
        print(response.text)


def setup_default_rules():
    """Setup default monitoring rules."""
    print("🔧 Setting up default rules...")
    
    # Clear existing rules first
    delete_all_rules()
    time.sleep(1)
    
    # Add default rule
    result = add_rule(DEFAULT_RULE["value"], DEFAULT_RULE["tag"])
    if result:
        print(f"✅ Default rule configured: {DEFAULT_RULE['value']}")
    
    return result


def send_to_discord(tweet_data):
    """Send tweet notification to Discord webhook."""
    webhook_url = get_webhook_url()
    if not webhook_url:
        print("⚠️ Discord webhook URL not found")
        return False
    
    tweet = tweet_data.get("data", {})
    includes = tweet_data.get("includes", {})
    users = {u["id"]: u for u in includes.get("users", [])}
    
    author_id = tweet.get("author_id")
    author = users.get(author_id, {})
    username = author.get("username", "unknown")
    name = author.get("name", "Unknown")
    
    tweet_id = tweet.get("id")
    text = tweet.get("text", "")
    created_at = tweet.get("created_at", "")
    
    tweet_url = f"https://x.com/{username}/status/{tweet_id}"
    
    # Create Discord embed
    embed = {
        "title": f"🐦 新規投稿: @{username}",
        "description": text[:500] + ("..." if len(text) > 500 else ""),
        "url": tweet_url,
        "color": 0x1DA1F2,  # Twitter blue
        "author": {
            "name": name,
            "url": f"https://x.com/{username}",
            "icon_url": author.get("profile_image_url", "")
        },
        "fields": [
            {
                "name": "投稿時刻",
                "value": created_at,
                "inline": True
            },
            {
                "name": "リンク",
                "value": f"[ツイートを開く]({tweet_url})",
                "inline": True
            }
        ],
        "footer": {
            "text": "X Filtered Stream"
        },
        "timestamp": created_at
    }
    
    # Add metrics if available
    metrics = tweet.get("public_metrics", {})
    if metrics:
        metrics_text = f"❤️ {metrics.get('like_count', 0)} | 🔄 {metrics.get('retweet_count', 0)} | 💬 {metrics.get('reply_count', 0)}"
        embed["fields"].append({
            "name": "エンゲージメント",
            "value": metrics_text,
            "inline": False
        })
    
    payload = {
        "username": "X Stream Bot",
        "avatar_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
        "embeds": [embed],
        "content": "<@&1475432244725288973> 新規投稿を検知しました"  # Mention role
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print(f"✅ Discord notification sent: @{username}")
            return True
        else:
            print(f"❌ Discord error: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Discord error: {e}")
        return False


def save_state(last_tweet_id, last_tweet_at):
    """Save stream state."""
    state = {
        "last_tweet_id": last_tweet_id,
        "last_tweet_at": last_tweet_at
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def stream_tweets():
    """Stream tweets in real-time."""
    print("🚀 Starting X Filtered Stream...")
    
    # Check configuration
    token = get_bearer_token()
    if not token:
        print("❌ Bearer token not found")
        return
    
    webhook_url = get_webhook_url()
    if not webhook_url:
        print("⚠️ Warning: Discord webhook not configured")
    
    # Check rules
    rules = get_rules()
    if not rules or not rules.get("data"):
        print("⚠️ No rules configured. Run 'setup' first.")
        return
    
    print(f"📋 Active rules: {len(rules.get('data', []))}")
    for rule in rules.get("data", []):
        print(f"   - {rule.get('tag')}: {rule.get('value')}")
    
    print("\n👂 Listening for tweets... (Press Ctrl+C to stop)\n")
    
    # Stream endpoint with parameters
    params = {
        "tweet.fields": TWEET_FIELDS,
        "expansions": "author_id",
        "user.fields": "name,username,profile_image_url"
    }
    
    url = f"{BASE_URL}/tweets/search/stream"
    headers = get_headers()
    
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            response = requests.get(url, headers=headers, params=params, stream=True, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Stream error: {response.status_code}")
                print(response.text)
                retry_count += 1
                time.sleep(5 * retry_count)  # Exponential backoff
                continue
            
            retry_count = 0  # Reset on successful connection
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Skip keep-alive messages
                    if not data:
                        continue
                    
                    # Handle errors
                    if "errors" in data:
                        print(f"⚠️ Error: {data['errors']}")
                        continue
                    
                    # Process tweet
                    if "data" in data:
                        tweet = data["data"]
                        tweet_id = tweet.get("id")
                        created_at = tweet.get("created_at", datetime.utcnow().isoformat())
                        
                        print(f"\n📝 Tweet detected: {tweet_id}")
                        print(f"   Text: {tweet.get('text', '')[:100]}...")
                        
                        # Send to Discord
                        send_to_discord(data)
                        
                        # Save state
                        save_state(tweet_id, created_at)
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠️ Error processing tweet: {e}")
                    continue
                    
        except requests.exceptions.Timeout:
            print("⚠️ Connection timeout, reconnecting...")
            retry_count += 1
            continue
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Connection error: {e}")
            retry_count += 1
            time.sleep(5)
            continue
        except KeyboardInterrupt:
            print("\n👋 Stream stopped by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            retry_count += 1
            time.sleep(5)
            continue
    
    if retry_count >= max_retries:
        print("❌ Max retries reached. Stopping.")


def test_configuration():
    """Test configuration and connections."""
    print("🧪 Testing X Filtered Stream configuration...\n")
    
    # Test bearer token
    print("1️⃣ Bearer Token:")
    token = get_bearer_token()
    if token:
        print(f"   ✅ Found: {token[:20]}...")
    else:
        print("   ❌ Not found")
        return False
    
    # Test API access
    print("\n2️⃣ API Access:")
    try:
        rules = get_rules()
        if rules:
            print("   ✅ API accessible")
            print(f"   📋 Current rules: {len(rules.get('data', []))}")
        else:
            print("   ⚠️ API accessible but no rules")
    except Exception as e:
        print(f"   ❌ API error: {e}")
        return False
    
    # Test Discord webhook
    print("\n3️⃣ Discord Webhook:")
    webhook_url = get_webhook_url()
    if webhook_url:
        print(f"   ✅ Found: {webhook_url[:50]}...")
    else:
        print("   ⚠️ Not configured (notifications will be skipped)")
    
    print("\n✅ Configuration test complete!")
    return True


def cmd_rules():
    """List current rules."""
    print("📋 Current Stream Rules:\n")
    rules = get_rules()
    
    if not rules:
        print("   No rules or error fetching rules")
        return
    
    data = rules.get("data", [])
    if not data:
        print("   No rules configured")
        return
    
    for i, rule in enumerate(data, 1):
        print(f"   {i}. [{rule.get('tag', 'no-tag')}]")
        print(f"      {rule.get('value')}")
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "test":
        test_configuration()
    
    elif command == "setup":
        setup_default_rules()
    
    elif command == "add":
        if len(sys.argv) < 4:
            print("Usage: python x_filtered_stream.py add <rule> <tag>")
            sys.exit(1)
        value = sys.argv[2]
        tag = sys.argv[3]
        add_rule(value, tag)
    
    elif command == "rules":
        cmd_rules()
    
    elif command == "clear":
        delete_all_rules()
    
    elif command == "stream":
        stream_tweets()
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

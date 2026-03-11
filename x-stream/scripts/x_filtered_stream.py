#!/usr/bin/env python3
"""
X (Twitter) Filtered Stream Client
Monitors tweets in real-time and sends notifications to Discord.

Usage:
    python x_filtered_stream.py test          # Test webhook connection
    python x_filtered_stream.py setup         # Setup default rules
    python x_filtered_stream.py rules         # List current rules
    python x_filtered_stream.py clear         # Delete all rules
    python x_filtered_stream.py add <rule> <tag>  # Add custom rule
    python x_filtered_stream.py stream        # Start streaming
"""

import json
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "x"
BEARER_TOKEN_FILE = DATA_DIR / "x-bearer-token.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"
STATE_FILE = DATA_DIR / "x-stream-state.json"

# API URLs
STREAM_URL = "https://api.twitter.com/2/tweets/search/stream"
RULES_URL = "https://api.twitter.com/2/tweets/search/stream/rules"

# Tweet fields to request
TWEET_FIELDS = "created_at,author_id,public_metrics,entities,attachments,conversation_id"


def load_bearer_token() -> str:
    """Load Bearer Token from file."""
    if not BEARER_TOKEN_FILE.exists():
        raise FileNotFoundError(f"Bearer token file not found: {BEARER_TOKEN_FILE}")
    
    with open(BEARER_TOKEN_FILE) as f:
        data = json.load(f)
        return data.get("bearer_token", "")


def load_webhook_url() -> str:
    """Load Discord webhook URL from file."""
    if not WEBHOOK_FILE.exists():
        raise FileNotFoundError(f"Webhook file not found: {WEBHOOK_FILE}")
    
    with open(WEBHOOK_FILE) as f:
        data = json.load(f)
        return data.get("webhook_url", "")


def load_state() -> dict:
    """Load stream state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """Save stream state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_headers() -> dict:
    """Get API headers with Bearer Token."""
    token = load_bearer_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_rules() -> dict:
    """Get current stream rules."""
    response = requests.get(RULES_URL, headers=get_headers())
    return response.json()


def delete_all_rules():
    """Delete all stream rules."""
    rules = get_rules()
    if "data" not in rules:
        print("No rules to delete")
        return
    
    ids = [rule["id"] for rule in rules["data"]]
    payload = {"delete": {"ids": ids}}
    response = requests.post(RULES_URL, headers=get_headers(), json=payload)
    print(f"Deleted {len(ids)} rules")
    return response.json()


def add_rule(value: str, tag: str) -> dict:
    """Add a new stream rule."""
    payload = {"add": [{"value": value, "tag": tag}]}
    response = requests.post(RULES_URL, headers=get_headers(), json=payload)
    return response.json()


def setup_default_rules():
    """Setup default monitoring rules."""
    print("Clearing existing rules...")
    delete_all_rules()
    
    print("Adding default rules...")
    rules = [
        {"value": "from:hAru_mAki_ch -is:retweet -is:reply", "tag": "haru_maki_new_posts"},
    ]
    
    payload = {"add": rules}
    response = requests.post(RULES_URL, headers=get_headers(), json=payload)
    
    if "errors" in response.json():
        print(f"Error: {response.json()['errors']}")
    else:
        print(f"Added {len(rules)} rules")
        print(json.dumps(response.json(), indent=2))


def send_discord_notification(tweet: dict):
    """Send tweet notification to Discord via webhook."""
    webhook_url = load_webhook_url()
    
    tweet_id = tweet.get("id", "")
    tweet_text = tweet.get("text", "")
    created_at = tweet.get("created_at", "")
    author_id = tweet.get("author_id", "")
    
    # Parse timestamp
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            time_str = created_at
    else:
        time_str = "Unknown"
    
    # Build embed
    embed = {
        "title": "🐦 New Tweet Detected",
        "description": tweet_text[:500] + ("..." if len(tweet_text) > 500 else ""),
        "color": 0x1DA1F2,  # Twitter blue
        "fields": [
            {"name": "Author ID", "value": author_id, "inline": True},
            {"name": "Time", "value": time_str, "inline": True},
        ],
        "url": f"https://twitter.com/i/web/status/{tweet_id}",
        "footer": {"text": f"Tweet ID: {tweet_id}"}
    }
    
    # Add metrics if available
    metrics = tweet.get("public_metrics", {})
    if metrics:
        metrics_text = f"❤️ {metrics.get('like_count', 0)} | 🔄 {metrics.get('retweet_count', 0)} | 💬 {metrics.get('reply_count', 0)}"
        embed["fields"].append({"name": "Metrics", "value": metrics_text, "inline": False})
    
    payload = {
        "content": "<@&1475432244725288973> 新しいツイートを検知しました！",
        "embeds": [embed],
        "allowed_mentions": {"parse": ["roles"]}
    }
    
    response = requests.post(webhook_url, json=payload)
    
    if response.status_code == 204:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Notification sent successfully")
        # Save state
        save_state({
            "last_tweet_id": tweet_id,
            "last_tweet_at": created_at
        })
    else:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Failed to send notification: {response.status_code}")
        print(response.text)


def test_webhook():
    """Test Discord webhook connection."""
    print("Testing Discord webhook...")
    webhook_url = load_webhook_url()
    
    payload = {
        "content": "🎋 X Filtered Stream Test - Connection OK",
        "embeds": [{
            "title": "Test Notification",
            "description": "This is a test message from X Filtered Stream.",
            "color": 0x4CAF50,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    
    response = requests.post(webhook_url, json=payload)
    
    if response.status_code == 204:
        print("✅ Webhook test successful!")
    else:
        print(f"❌ Webhook test failed: {response.status_code}")
        print(response.text)


def stream_tweets():
    """Start streaming tweets."""
    print("Starting X Filtered Stream...")
    print("Press Ctrl+C to stop")
    
    # Build stream URL with parameters
    stream_url = f"{STREAM_URL}?tweet.fields={TWEET_FIELDS}"
    
    try:
        response = requests.get(
            stream_url,
            headers=get_headers(),
            stream=True,
            timeout=(10, 90)
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return
        
        print(f"Connected! Status: {response.status_code}")
        
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                if "data" in data:
                    tweet = data["data"]
                    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Tweet received: {tweet.get('id')}")
                    send_discord_notification(tweet)
                    
            except json.JSONDecodeError:
                # Keep-alive signal, ignore
                pass
            except Exception as e:
                print(f"Error processing tweet: {e}")
                
    except requests.exceptions.Timeout:
        print("Connection timeout, reconnecting...")
        time.sleep(5)
        stream_tweets()
    except KeyboardInterrupt:
        print("\nStream stopped by user")
    except Exception as e:
        print(f"Stream error: {e}")
        time.sleep(10)
        stream_tweets()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        test_webhook()
    elif command == "setup":
        setup_default_rules()
    elif command == "rules":
        rules = get_rules()
        print(json.dumps(rules, indent=2))
    elif command == "clear":
        delete_all_rules()
    elif command == "add":
        if len(sys.argv) < 4:
            print("Usage: python x_filtered_stream.py add <rule> <tag>")
            sys.exit(1)
        value = sys.argv[2]
        tag = sys.argv[3]
        result = add_rule(value, tag)
        print(json.dumps(result, indent=2))
    elif command == "stream":
        stream_tweets()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

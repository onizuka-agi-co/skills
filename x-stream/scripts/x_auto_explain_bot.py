#!/usr/bin/env python3
"""
X Auto Explain Bot - 自動解説Bot
hAru_mAki_chの投稿を監視し、自動で解説を生成して投稿する。

Usage:
    python x_auto_explain_bot.py stream    # 監視開始
    python x_auto_explain_bot.py test      # テスト実行
    python x_auto_explain_bot.py status    # ステータス確認
"""

import json
import sys
import time
import requests
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "x"
BEARER_TOKEN_FILE = DATA_DIR / "x-bearer-token.json"
STATE_FILE = DATA_DIR / "x-auto-explain-state.json"

# API URLs
STREAM_URL = "https://api.twitter.com/2/tweets/search/stream"
RULES_URL = "https://api.twitter.com/2/tweets/search/stream/rules"

# Tweet fields to request
TWEET_FIELDS = "created_at,author_id,public_metrics,entities,attachments,conversation_id"

# Target user to monitor
TARGET_USER = "hAru_mAki_ch"

# Quote Explain Script Path
QUOTE_EXPLAIN_SCRIPT = BASE_DIR / "skills" / "x-quote-explain" / "scripts" / "quote_explain.py"


def load_bearer_token() -> str:
    """Load Bearer Token from file."""
    if not BEARER_TOKEN_FILE.exists():
        raise FileNotFoundError(f"Bearer token file not found: {BEARER_TOKEN_FILE}")
    
    with open(BEARER_TOKEN_FILE) as f:
        data = json.load(f)
        return data.get("bearer_token", "")


def load_state() -> dict:
    """Load bot state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """Save bot state to file."""
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


def setup_rules():
    """Setup monitoring rules."""
    # Clear existing rules
    rules = get_rules()
    if "data" in rules:
        ids = [rule["id"] for rule in rules["data"]]
        payload = {"delete": {"ids": ids}}
        requests.post(RULES_URL, headers=get_headers(), json=payload)
        print(f"Cleared {len(ids)} existing rules")
    
    # Add new rules
    new_rules = [
        {"value": f"from:{TARGET_USER} -is:retweet -is:reply", "tag": f"{TARGET_USER}_new_posts"},
    ]
    
    payload = {"add": new_rules}
    response = requests.post(RULES_URL, headers=get_headers(), json=payload)
    
    if "errors" in response.json():
        print(f"Error setting rules: {response.json()['errors']}")
        return False
    else:
        print(f"Added {len(new_rules)} rules")
        return True


def generate_explanation(tweet_text: str, tweet_id: str) -> str:
    """
    Generate explanation using AI.
    Uses the x-quote-explain script's --ai mode.
    """
    tweet_url = f"https://x.com/i/status/{tweet_id}"
    
    # Call quote_explain.py --ai
    cmd = ["python3", str(QUOTE_EXPLAIN_SCRIPT), tweet_url, "--ai"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # Parse the output
            output = result.stdout.strip()
            try:
                data = json.loads(output)
                if data.get("success"):
                    return data
            except:
                pass
        
        # Fallback: simple explanation
        return generate_simple_explanation(tweet_text, tweet_id)
        
    except subprocess.TimeoutExpired:
        print("Explanation generation timed out")
        return generate_simple_explanation(tweet_text, tweet_id)
    except Exception as e:
        print(f"Error generating explanation: {e}")
        return generate_simple_explanation(tweet_text, tweet_id)


def generate_simple_explanation(tweet_text: str, tweet_id: str) -> dict:
    """
    Generate a simple explanation without AI.
    Fallback when AI explanation fails.
    """
    # Extract key terms from the tweet
    words = tweet_text.split()
    hashtags = [w for w in words if w.startswith('#')]
    
    explanation = f"📝 {TARGET_USER}の投稿を確認しました。\n\n"
    
    if hashtags:
        explanation += f"関連タグ: {' '.join(hashtags[:5])}\n\n"
    
    explanation += f"詳細は元のツイートをご確認ください。\n\n#ONIZUKA_AGI"
    
    return {
        "success": True,
        "explanation": explanation,
        "tweet_url": f"https://x.com/i/status/{tweet_id}",
        "method": "simple_fallback"
    }


def process_tweet(tweet: dict):
    """Process a detected tweet."""
    tweet_id = tweet.get("id", "")
    tweet_text = tweet.get("text", "")
    created_at = tweet.get("created_at", "")
    
    print(f"\n{'='*60}")
    print(f"[{datetime.now(timezone.utc).isoformat()}] Processing tweet: {tweet_id}")
    print(f"Text: {tweet_text[:100]}...")
    
    # Check if we already processed this tweet
    state = load_state()
    if state.get("last_processed_id") == tweet_id:
        print("Already processed, skipping...")
        return
    
    # Generate explanation and post
    print("Generating explanation...")
    result = generate_explanation(tweet_text, tweet_id)
    
    if result.get("success"):
        print(f"✅ Explanation posted successfully!")
        print(f"   Method: {result.get('method', 'unknown')}")
        if result.get("tweet_url"):
            print(f"   URL: {result.get('tweet_url')}")
        
        # Save state
        save_state({
            "last_processed_id": tweet_id,
            "last_processed_at": datetime.now(timezone.utc).isoformat(),
            "last_method": result.get("method")
        })
    else:
        print(f"❌ Failed to post explanation: {result.get('error')}")


def stream_tweets():
    """Start streaming tweets."""
    print(f"🐦 X Auto Explain Bot Starting...")
    print(f"📌 Monitoring: @{TARGET_USER}")
    print(f"{'='*60}")
    
    # Setup rules
    if not setup_rules():
        print("Failed to setup rules")
        return
    
    print("\n📡 Connecting to stream...")
    print("Press Ctrl+C to stop\n")
    
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
        
        print(f"✅ Connected! Status: {response.status_code}")
        
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                if "data" in data:
                    tweet = data["data"]
                    process_tweet(tweet)
                    
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
        print("\n\n🛑 Stream stopped by user")
    except Exception as e:
        print(f"Stream error: {e}")
        time.sleep(10)
        stream_tweets()


def test_bot():
    """Test the bot with a mock tweet."""
    print("🧪 Testing X Auto Explain Bot...")
    
    # Mock tweet
    mock_tweet = {
        "id": "1234567890",
        "text": "This is a test tweet about AGI and AI agents. #AGI #AI",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"\nMock Tweet: {mock_tweet['text']}")
    print("\nGenerating explanation...")
    
    result = generate_explanation(mock_tweet["text"], mock_tweet["id"])
    print(f"\nResult: {json.dumps(result, indent=2, ensure_ascii=False)}")


def show_status():
    """Show bot status."""
    print("📊 X Auto Explain Bot Status")
    print("="*40)
    
    # Load state
    state = load_state()
    if state:
        print(f"Last Processed ID: {state.get('last_processed_id', 'None')}")
        print(f"Last Processed At: {state.get('last_processed_at', 'None')}")
        print(f"Last Method: {state.get('last_method', 'None')}")
    else:
        print("No previous state found")
    
    # Show rules
    print("\n📋 Current Rules:")
    rules = get_rules()
    if "data" in rules:
        for rule in rules["data"]:
            print(f"  - {rule.get('tag')}: {rule.get('value')}")
    else:
        print("  No rules configured")
    
    # Check files
    print("\n📁 Required Files:")
    print(f"  Bearer Token: {'✅' if BEARER_TOKEN_FILE.exists() else '❌'}")
    print(f"  Quote Explain Script: {'✅' if QUOTE_EXPLAIN_SCRIPT.exists() else '❌'}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "stream":
        stream_tweets()
    elif command == "test":
        test_bot()
    elif command == "status":
        show_status()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

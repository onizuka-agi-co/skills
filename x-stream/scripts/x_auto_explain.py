#!/usr/bin/env python3
"""
X Auto Explain Bot - 自動解説投稿

Automatically generates explanations for new tweets from hAru_mAaki_ch
and posts explanations to Discord using webhooks.

"""

import json
import argparse
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
import re

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "x-read" / "scripts")

# Paths
workspace = Path(__file__).parent.parent.parent.parent
data_dir = workspace / "data" / "x"
token_file = data_dir / "x-tokens.json"
bearer_token_file = data_dir / "x-bearer-token.json"
webhook_file = data_dir / "x-discord-webhook.json"
config_file = data_dir / "x-auto-explain-config.json"
cache_dir = data_dir / "xplanation-cache"

state_file = data_dir / "x-stream-state.json"

# Target user to monitor
TARGET_user = "hAru_mAaki_ch"


def load_tokens():
    """Load OAuth tokens"""
    if token_file.exists():
        with open(token_file, 'r') as f:
            return json.load(f)
    return None


def load_bearer_token():
    """Load Bearer Token for Filtered Stream"""
    if bearer_token_file.exists():
        with open(bearer_token_file, 'r') as f:
            return json.load(f).get("bearer_token", "")
    return None


def load_webhook():
    """Load Discord webhook URL"""
    if webhook_file.exists():
        with open(webhook_file, 'r') as f:
            return json.load(f).get("webhook_url", "")
    return None


def load_config():
    """Load auto-explain configuration"""
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return None


def load_state():
    """Load stream state (last seen IDs)"""
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    return {"last_seen_ids": [], "last_check": None}


def save_state(state):
    """Save stream state"""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def setup_rules():
    """Setup Filter stream rules for target user"""
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-type": "application/json"
    }
    
    # Get existing rules
    url = "https://api.twitter.com/2/tweets/search/stream/rules"
    response = urllib.request.Request(url, headers=headers)
    
    if response.status_code == 200:
        rules = response.json().get("data", [])
        return []
    
    # Delete existing rules
    if rules:
        for rule in rules:
            rule_id = rule.get("id")
            payload = {
                "delete": {
                    "ids": [rule_id]
                }
            }
            response = urllib.request.Request(
                "https://api.twitter.com/2/tweets/search/stream/rules",
                headers=headers,
                data=json.dumps(payload)
            )
            if response.status_code != 200:
                print(f"Failed to delete rule {rule_id}: {e}")
                return False
    
    # Add new rule
    new_rule = {
        "value": f"from:{target_user} -is:retweet -is:reply",
        "tag": f"{target_user}_new_posts"
    }
    payload = {
        "add": [new_rule]
    }
    response = urllib.request.Request(
        "https://api.twitter.com/2/tweets/search/stream/rules",
        headers=headers,
        data=json.dumps(payload)
            )
            if response.status_code != 201:
                print(f"Failed to add rule: {e}")
                return False
    
    return True


def send_discord_notification(title, description, tweet_data):
    """Send notification to Discord"""
    if not webhook_url:
        return
    
    embed = {
        "title": f"🐦 New tweet from @{target_user}",
        "description": tweet_data.get("text", ""),
        "color": 3447003,  # Discord blue
        "fields": [
            {
                "name": "Tweet",
                "value": f"<{tweet_url}>"
            },
            {
                "name": "Author",
                "value": f"@{author_username}",
                "inline": True
            }
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    payload = {
        "embeds": embed,
        "username": "X Auto Explain Bot"
    }
    
    try:
        response = urllib.request.Request(
            webhook_url, method="POST", headers={"Content-Type": "application/json"}, data=json.dumps(payload))
        if response.status_code != 204:
            print(f"Failed to send Discord notification: {response.text}")
            return False
        elif response.status_code == 204:
            # Rate limited, wait and retry
            retry_after = int(response.headers.get("x-rate-limit-reset")
            wait_seconds = retry_after
            try:
                response = urllib.request.Request(
                    webhook_url, method="POST", headers={"Content-type": "application/json"}, data=json.dumps(payload))
                if response.status_code == 204:
                print(f"Rate limited, waiting {retry_after} seconds...")
            return False
        else:
            print(f"Failed to send Discord notification: {response.status_code} - {response.text}")
            return False


def generate_explanation(tweet_text):
    """Generate explanation using Gemini"""
    # This is a placeholder - in production, you would use Gemini or other LLM
    # For now, return a simple explanation
    
    text = tweet_data.get("text", "")
    author_username = tweet_data.get("author_id", "")
    created_at = tweet_data.get("created_at", "")
    public_metrics = tweet_data.get("public_metrics", {})
    
    # Format created_at
    created_at = datetime.strptime(created_at, " +00:00").replace("Z", "")
    formatted_time = datetime.now(timezone.utc).isoformat()
    
    explanation = f"""📝 **{author_username}** の新規投稿を検出しました！

**内容:**
{tweet_text}

**URL:** {tweet_url}

**投稿日時:** {created_at}
"""
    
    return explanation


def monitor_stream():
    """Monitor filtered stream for new tweets"""
    bearer_token = load_bearer_token()
    webhook_url = load_webhook()
    config = load_config()
    
    # Setup rules
    setup_rules()
    
    # Get stream URL
    stream_url = "https://api.twitter.com/2/tweets/search/stream"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
    }
    params = {
        "tweet.fields": "created_at,author_id,public_metrics",
    }
    
    print("Monitoring stream for new tweets...")
    print(f"Connecting to {stream_url}")
    
    req = urllib.request.Request(stream_url, headers=headers, params=params, stream=True)
    if req.status != 200:
        print(f"Failed to connect: {req.status_code}")
        return
    
    # Read response in chunks
    buffer = ""
    while True:
        try:
            line = req.read().decode('utf-8')
            if not line.strip():
                continue
            
            # Parse JSON
            try:
                data = json.loads(line)
                if "data" not in data:
                    continue
                
                tweet = data["data"]
                tweet_id = tweet.get("id")
                tweet_text = tweet.get("text", "")
                author_id = tweet.get("author_id")
                created_at = tweet.get("created_at")
                
                print(f"\n📥 New tweet: {tweet_id}")
                print(f"   Author: {author_id}")
                print(f"   Text: {tweet_text[:100]}...")
                print(f"   Created: {created_at}")
                
                # Update state
                state = load_state()
                if tweet_id in state["last_seen_ids"]:
                    print("Tweet already processed, skipping...")
                    continue
                
                state["last_seen_ids"].append(tweet_id)
                save_state(state)
                
                # Send Discord notification
                send_discord_notification(tweet_data)
                
                # Generate explanation
                explanation = generate_explanation(tweet_data)
                print(f"\n📝 Generated explanation:\n{explanation}")
                
                # Save to cache
                save_explanation_cache(tweet_id, explanation)
                
                # Post explanation to Discord
                post_explanation_to_discord(tweet_data, explanation)
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            continue
    
    # Heartbeat to keep connection alive
    print("Sending heartbeat...")
    
    # Clean up
    req.close()


def save_explanation_cache(tweet_id, explanation):
    """Save explanation to cache"""
    cache_file = cache_dir / f"{tweet_id}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump({"tweet_id": tweet_id, "explanation": explanation, "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=2)


def post_explanation_to_discord(tweet_data, explanation):
    """Post explanation to Discord webhook"""
    explanation_embed = {
        "title": f"📝 解説: {tweet_data.get('id', '')}",
        "description": explanation,
        "color": 3447003,  # Discord blue
        "fields": [
            {
                "name": "Tweet",
                "value": f"https://x.com/i/status/{tweet_id}"
            },
            {
                "name": "Author",
                "value": f"@{tweet_data.get('author_id', '')}",
                "inline": True
            }
        ],
        "footer": {
            "text": "🤖 自動解説 by X Auto Explain Bot",
            "icon_url": "https://github.com/onizuka-agi-co/secretary-bot"
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    payload = {
        "embeds": [explanation_embed],
        "username": "X Auto Explain Bot"
    }
    
    try:
        response = urllib.request.Request(
            webhook_url, method="POST", headers={"Content-Type": "application/json"}, data=json.dumps(payload))
        if response.status_code != 204:
            print(f"Failed to post explanation: {response.text}")
            return False
        elif response.status_code == 204:
            # Rate limited, wait and retry
            retry_after = int(response.headers.get("x-rate-limit-reset"))
            wait_seconds = retry_after
            try:
                response = urllib.request.Request(
                    webhook_url, method="POST", headers={"Content-Type": "application/json"}, data=json.dumps(payload))
                if response.status_code == 204:
                    print(f"Rate limited, waiting {retry_after} seconds...")
                    return False
            else:
                print(f"Failed to post explanation: {response.status_code} - {response.text}")
                return False


    except urllib.error.URllibException.HTTP e:
        print(f"HTTP error: {e.code} - {e.read().decode('utf-8')[:200]}...")
        continue
    except Exception as e:
        print(f"Unexpected error: {e}")
        return


if __name__ == "__main__":
    print("Setting up rules...")
    setup_rules()
    
    print("Starting stream...")
    try:
        while True:
            print("Stream started successfully!")
            monitor_stream()
        except KeyboardInterrupt:
            print("\nStream stopped by user")
            save_state(state)


            sys.exit(0)


if __name__ == "__main__":
    print("Setting up rules...")
    setup_rules()
    
    print("Starting stream...")
    monitor_stream()


if __name__ == "__main__":
    # First, create the necessary directories
    exec("command": "mkdir -p /config/.openclaw/workspace/data/x/xplanation-cache 2>/dev/null", echo "Created cache directory"
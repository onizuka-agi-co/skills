#!/usr/bin/env python3
"""
X Bookmark Monitor for OpenClaw
Monitors bookmarks and detects new ones for notification
"""

import json
import sys
import os
import urllib.request
import urllib.parse
import urllib.error
import base64
from datetime import datetime, timezone
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "x-read" / "scripts"))

# Paths
WORKSPACE = Path(__file__).parent.parent.parent.parent
DATA_DIR = WORKSPACE / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials.json"
STATE_FILE = DATA_DIR / "bookmark-state.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"


def load_tokens():
    """Load OAuth tokens"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None


def load_credentials():
    """Load client credentials"""
    if CLIENT_CREDENTIALS_FILE.exists():
        with open(CLIENT_CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return None


def load_state():
    """Load bookmark state (last seen IDs)"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_seen_ids": [], "last_check": None}


def save_state(state):
    """Save bookmark state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def refresh_token_if_needed(tokens, credentials):
    """Refresh access token if expired"""
    if not tokens or not credentials:
        raise Exception("Missing tokens or credentials")
    
    # Check if token needs refresh (simple check - could be improved)
    # For now, always use the current token
    return tokens.get('access_token')


def get_bookmarks(access_token, max_results=50):
    """Fetch bookmarks from X API"""
    # First get user ID
    req = urllib.request.Request(
        "https://api.x.com/2/users/me",
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            me_data = json.loads(resp.read().decode())
            user_id = me_data['data']['id']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"error": f"Failed to get user info: {e.code}", "details": error_body}
    
    # Get bookmarks
    params = {
        'max_results': max_results,
        'tweet.fields': 'created_at,public_metrics,author_id,text,entities',
        'expansions': 'author_id',
        'user.fields': 'name,username,profile_image_url'
    }
    
    url = f"https://api.x.com/2/users/{user_id}/bookmarks?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"error": f"Failed to get bookmarks: {e.code}", "details": error_body}


def format_bookmark(tweet, users_map):
    """Format a bookmark for notification"""
    author_id = tweet.get('author_id')
    author = users_map.get(author_id, {})
    username = author.get('username', 'unknown')
    name = author.get('name', 'Unknown')
    
    text = tweet.get('text', '')
    created_at = tweet.get('created_at', '')
    tweet_id = tweet.get('id', '')
    
    # Format metrics
    metrics = tweet.get('public_metrics', {})
    likes = metrics.get('like_count', 0)
    reposts = metrics.get('retweet_count', 0)
    
    return {
        'id': tweet_id,
        'url': f"https://x.com/{username}/status/{tweet_id}",
        'author': f"{name} (@{username})",
        'text': text,
        'created_at': created_at,
        'likes': likes,
        'reposts': reposts
    }


def send_discord_notification(webhook_url, bookmarks):
    """Send notification to Discord"""
    if not bookmarks:
        return
    
    embeds = []
    for bm in bookmarks[:5]:  # Max 5 embeds
        embed = {
            "title": f"🔖 New Bookmark",
            "description": bm['text'][:500] + ("..." if len(bm['text']) > 500 else ""),
            "url": bm['url'],
            "author": {
                "name": bm['author']
            },
            "footer": {
                "text": f"❤️ {bm['likes']} 🔄 {bm['reposts']}"
            },
            "color": 1972006,  # #1E1F22 (dark)
            "timestamp": bm['created_at']
        }
        embeds.append(embed)
    
    payload = {
        "embeds": embeds
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def main():
    if len(sys.argv) < 2:
        print("X Bookmark Monitor")
        print("\nUsage:")
        print("  python x_bookmark_monitor.py check       - Check for new bookmarks")
        print("  python x_bookmark_monitor.py test        - Test bookmark fetch")
        print("  python x_bookmark_monitor.py status      - Show state")
        print("  python x_bookmark_monitor.py clear       - Clear state")
        sys.exit(1)
    
    command = sys.argv[1]
    
    tokens = load_tokens()
    credentials = load_credentials()
    state = load_state()
    
    if command == "status":
        print("Bookmark Monitor State:")
        print(f"  Last check: {state.get('last_check', 'Never')}")
        print(f"  Tracked IDs: {len(state.get('last_seen_ids', []))}")
        if state.get('last_seen_ids'):
            print(f"  Latest ID: {state['last_seen_ids'][0]}")
        sys.exit(0)
    
    if command == "clear":
        save_state({"last_seen_ids": [], "last_check": None})
        print("State cleared.")
        sys.exit(0)
    
    if command == "test":
        access_token = refresh_token_if_needed(tokens, credentials)
        result = get_bookmarks(access_token, max_results=5)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)
    
    if command == "check":
        access_token = refresh_token_if_needed(tokens, credentials)
        result = get_bookmarks(access_token)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            if 'details' in result:
                print(f"Details: {result['details']}")
            sys.exit(1)
        
        if 'data' not in result:
            print("No bookmarks found.")
            sys.exit(0)
        
        # Build users map
        users_map = {}
        if 'includes' in result and 'users' in result['includes']:
            for user in result['includes']['users']:
                users_map[user['id']] = user
        
        # Get current bookmark IDs
        current_ids = [t['id'] for t in result['data']]
        last_seen = set(state.get('last_seen_ids', []))
        
        # Find new bookmarks
        new_bookmarks = []
        for tweet in result['data']:
            if tweet['id'] not in last_seen:
                new_bookmarks.append(format_bookmark(tweet, users_map))
        
        # Update state
        new_state = {
            "last_seen_ids": current_ids[:100],  # Keep last 100 IDs
            "last_check": datetime.now(timezone.utc).isoformat()
        }
        save_state(new_state)
        
        if new_bookmarks:
            print(f"Found {len(new_bookmarks)} new bookmark(s)!")
            
            # Send notification
            webhook_data = None
            if WEBHOOK_FILE.exists():
                with open(WEBHOOK_FILE, 'r') as f:
                    webhook_data = json.load(f)
            
            webhook_url = webhook_data.get('webhook_url') if webhook_data else None
            
            if webhook_url:
                send_discord_notification(webhook_url, new_bookmarks)
                print("Notification sent to Discord.")
            else:
                print("No webhook configured. New bookmarks:")
                for bm in new_bookmarks:
                    print(f"\n  📌 {bm['author']}")
                    print(f"     {bm['text'][:100]}...")
                    print(f"     {bm['url']}")
        else:
            print("No new bookmarks.")
        
        sys.exit(0)
    
    print(f"Unknown command: {command}")
    sys.exit(1)


if __name__ == "__main__":
    main()

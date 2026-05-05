#!/usr/bin/env python3
"""
Poll new tweets from hAru_mAki_ch and notify Discord for auto-explanation.
Designed to run as a cron job (e.g. every 30 minutes).

Usage:
    uv run skills/x-stream/scripts/poll_new_tweets.py
    uv run skills/x-stream/scripts/poll_new_tweets.py --test
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_FILE = DATA_DIR / "x-client-credentials.json"
BEARER_FILE = DATA_DIR / "x-bearer-token.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"
STATE_FILE = DATA_DIR / "x-auto-explain-state.json"

TARGET_USER_ID = "1468159538558009346"  # hAru_mAki_ch
AGENT_ID = "1475431819565469706"

MAX_RESULTS = 10


def load_tokens():
    tokens = json.loads(TOKEN_FILE.read_text())
    creds = json.loads(CLIENT_FILE.read_text())
    return tokens["access_token"], creds["client_id"], creds["client_secret"]


def refresh_token():
    tokens = json.loads(TOKEN_FILE.read_text())
    creds = json.loads(CLIENT_FILE.read_text())
    data = json.dumps({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": creds["client_id"],
    }).encode()
    req = urllib.request.Request(
        "https://api.x.com/2/oauth2/token",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    tokens["access_token"] = result["access_token"]
    tokens["refresh_token"] = result["refresh_token"]
    tokens["expires_in"] = result["expires_in"]
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    return result["access_token"]


def get_user_tweets(access_token: str, user_id: str, since_id: str | None = None):
    """Fetch recent tweets from a user using OAuth2 user context."""
    url = f"https://api.x.com/2/users/{user_id}/tweets?max_results={MAX_RESULTS}&tweet.fields=created_at,text&exclude=replies,retweets"
    if since_id:
        url += f"&since_id={since_id}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"Token expired, refreshing...")
            new_token = refresh_token()
            req2 = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {new_token}"},
            )
            with urllib.request.urlopen(req2) as resp:
                return json.loads(resp.read())
        raise


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_ids": [], "last_tweet_id": None, "last_check": None}


def save_state(state: dict):
    state["processed_ids"] = state["processed_ids"][-500:]
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def notify_discord(webhook_url: str, tweet_id: str, tweet_text: str):
    tweet_url = f"https://x.com/hAru_mAki_ch/status/{tweet_id}"
    payload = {
        "username": "朱燈烏 🔔",
        "content": f"<@{AGENT_ID}> 🐦 新規投稿を検知しました。解説をお願いします。\n{tweet_url}",
        "embeds": [{
            "title": "🐦 新規投稿検知: @hAru_mAki_ch",
            "description": tweet_text[:2048],
            "url": tweet_url,
            "color": 0x1DA1F2,
        }],
        "allowed_mentions": {"parse": []},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ONIZUKA-Poll/1.0"},
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    test_mode = "--test" in sys.argv

    state = load_state()
    access_token, _, _ = load_tokens()

    webhook_url = None
    if WEBHOOK_FILE.exists():
        webhook_url = json.loads(WEBHOOK_FILE.read_text())["webhook_url"]

    # Fetch tweets since last seen
    since_id = state.get("last_tweet_id")
    print(f"Polling tweets since: {since_id or 'beginning'}")

    result = get_user_tweets(access_token, TARGET_USER_ID, since_id)
    tweets = result.get("data", [])
    print(f"Found {len(tweets)} tweets")

    if not tweets:
        print("No new tweets")
        save_state(state)
        return

    new_ids = []
    for tweet in reversed(tweets):  # Oldest first
        tid = tweet["id"]
        if tid in state.get("processed_ids", []):
            continue
        if tid == since_id:
            continue

        new_ids.append(tid)
        state.setdefault("processed_ids", []).append(tid)
        print(f"New tweet: {tid} — {tweet['text'][:80]}")

        if test_mode:
            print(f"  [TEST] Would notify Discord for {tid}")
        elif webhook_url:
            try:
                notify_discord(webhook_url, tid, tweet["text"])
                print(f"  Notified Discord ✓")
            except Exception as e:
                print(f"  Discord notification failed: {e}")

    # Update last seen tweet ID (newest)
    state["last_tweet_id"] = tweets[0]["id"]
    save_state(state)
    print(f"Updated state: {len(new_ids)} new tweets processed")


if __name__ == "__main__":
    main()

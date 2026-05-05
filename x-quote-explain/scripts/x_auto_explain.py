#!/usr/bin/env python3
"""
X Auto Explain Pipeline
Monitors specific users' tweets and auto-generates explanation posts.

Usage:
    uv run scripts/x_auto_explain.py [--dry-run] [--user USERNAME] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = WORKSPACE / "data" / "x" / "x-auto-explain-state.json"
X_READ_SCRIPT = WORKSPACE / "skills" / "x-read" / "scripts" / "x_read.py"
X_EXPLAIN_SCRIPT = WORKSPACE / "skills" / "x-quote-explain" / "scripts" / "quote_explain.py"

# Default users to monitor
DEFAULT_MONITOR_USERS = ["hAru_mAki_ch"]

# Skip reply/retweet/quote tweets by default
DEFAULT_SKIP_REPLY = True
DEFAULT_SKIP_RETWEET = True


def load_state() -> dict:
    """Load pipeline state (last processed tweet IDs per user)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"users": {}, "last_run": None}


def save_state(state: dict):
    """Save pipeline state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def get_user_tweets(username: str, limit: int = 5) -> list[dict]:
    """Fetch recent tweets from a user using x-read skill."""
    cmd = [
        sys.executable, "-m", "x_read",
        "user-timeline", "--username", username,
        "--limit", str(limit), "--json",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
        cwd=str(X_READ_SCRIPT.parent),
        env={**os.environ, "PYTHONPATH": str(X_READ_SCRIPT.parent)},
    )
    if result.returncode != 0:
        print(f"[ERROR] x_read failed for {username}: {result.stderr}", file=sys.stderr)
        return []
    try:
        data = json.loads(result.stdout)
        return data.get("tweets", [])
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse x_read output for {username}", file=sys.stderr)
        return []


def get_user_id(username: str) -> str | None:
    """Get user ID from username."""
    cmd = ["uv", "run", str(X_READ_SCRIPT), "user", username]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return data.get("data", {}).get("id")
    except (json.JSONDecodeError, KeyError):
        return None


def run_x_read_cli(username: str, limit: int = 5) -> list[dict]:
    """Fetch recent tweets via CLI. Uses search API first, falls back to timeline approach."""
    # Method 1: Search API (may not work on Basic tier)
    cmd = ["uv", "run", str(X_READ_SCRIPT), "search",
           f"from:{username}", str(limit)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            tweets = data.get("data", [])
            if tweets:
                return tweets
        except json.JSONDecodeError:
            pass

    # Method 2: Direct API call via _api_request with user ID
    # x_read doesn't expose user-timeline directly, so we note the limitation
    print(f"[WARN] Could not fetch tweets for @{username} via search API", file=sys.stderr)
    print(f"[INFO] Consider upgrading X API tier or using x-stream skill for monitoring", file=sys.stderr)
    return []


def filter_tweets(tweets: list[dict], state: dict, username: str,
                  skip_reply: bool = True, skip_retweet: bool = True) -> list[dict]:
    """Filter out already-processed tweets, replies, and retweets."""
    last_id = state.get("users", {}).get(username, {}).get("last_tweet_id")
    filtered = []
    for tw in tweets:
        tid = tw.get("id") or tw.get("tweet_id", "")
        # Skip already processed
        if last_id and tid <= str(last_id):
            continue
        # Skip replies
        if skip_reply and (tw.get("in_reply_to_user_id") or tw.get("referenced_tweets")):
            ref = tw.get("referenced_tweets", [])
            if any(r.get("type") == "replied_to" for r in ref):
                continue
        # Skip retweets
        if skip_retweet:
            ref = tw.get("referenced_tweets", [])
            if any(r.get("type") == "retweeted" for r in ref):
                continue
        filtered.append(tw)
    return filtered


def generate_explanation(tweet: dict) -> str | None:
    """Generate explanation text for a tweet using AI (web_search or internal)."""
    text = tweet.get("text", "")
    if not text:
        return None
    
    # Simple explanation template - in production, this would call an LLM
    # For now, we'll use the --ai flag of quote_explain.py
    return "ai"  # Signal to use AI generation


def post_explanation(tweet_url: str, explanation: str, dry_run: bool = False) -> dict:
    """Post explanation using x-quote-explain skill."""
    if dry_run:
        return {"success": True, "dry_run": True, "url": tweet_url}
    
    cmd = ["uv", "run", str(X_EXPLAIN_SCRIPT), tweet_url, "--ai"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
    
    if result.returncode != 0:
        return {"success": False, "error": result.stderr, "url": tweet_url}
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": True, "raw": result.stdout, "url": tweet_url}


def main():
    parser = argparse.ArgumentParser(description="X Auto Explain Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Don't post, just show what would be done")
    parser.add_argument("--user", action="append", help="Username to monitor (can repeat)")
    parser.add_argument("--limit", type=int, default=5, help="Max tweets to fetch per user")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    users = args.user or DEFAULT_MONITOR_USERS
    state = load_state()
    results = []

    for username in users:
        print(f"[INFO] Checking @{username}...")
        tweets = run_x_read_cli(username, args.limit)
        new_tweets = filter_tweets(tweets, state, username)

        if not new_tweets:
            print(f"[INFO] No new tweets from @{username}")
            results.append({"user": username, "new_tweets": 0, "processed": 0})
            continue

        print(f"[INFO] Found {len(new_tweets)} new tweet(s) from @{username}")
        processed = 0

        for tw in new_tweets:
            tid = tw.get("id") or tw.get("tweet_id", "")
            text = (tw.get("text", ""))[:80]
            print(f"[INFO] Processing tweet {tid}: {text}...")

            tweet_url = f"https://x.com/{username}/status/{tid}"
            result = post_explanation(tweet_url, "ai", dry_run=args.dry_run)
            result["tweet_id"] = tid
            result["user"] = username
            result["text_preview"] = text
            results.append(result)

            if result.get("success"):
                processed += 1
                # Update state
                if username not in state.get("users", {}):
                    state.setdefault("users", {})[username] = {}
                state["users"][username]["last_tweet_id"] = tid

        results.append({"user": username, "new_tweets": len(new_tweets), "processed": processed})

    save_state(state)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n[SUMMARY] Processed {len(results)} items")

    return 0


if __name__ == "__main__":
    sys.exit(main())

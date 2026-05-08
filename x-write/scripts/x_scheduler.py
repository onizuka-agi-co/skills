#!/usr/bin/env python3
"""
X Post Scheduler - 投稿スケジューラー
X（Twitter）の投稿をスケジュール管理するシステム

機能:
- 投稿キューの管理（追加・一覧・削除）
- 指定時刻の自動投稿
- 投稿間隔の最適化
- 投稿履歴との統合
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

# Timezone
JST = timezone(timedelta(hours=9))

# Paths
WORKSPACE = Path.home() / ".openclaw" / "workspace"
TOKEN_FILE = WORKSPACE / "x-tokens.json"
CLIENT_CRED_FILE = WORKSPACE / "x-client-credentials.json"
QUEUE_FILE = WORKSPACE / "data" / "x" / "post-queue.json"
HISTORY_FILE = WORKSPACE / "data" / "x" / "post-history.json"

# X API endpoints
POST_URL = "https://api.x.com/2/tweets"
REFRESH_URL = "https://api.x.com/2/oauth2/token"

# Rate limits
MIN_POST_INTERVAL_MIN = 15  # 投稿間の最小間隔（分）


def load_json(path: Path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or {}


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_tokens():
    """Load and optionally refresh X OAuth2 tokens"""
    tokens = load_json(TOKEN_FILE)
    if not tokens:
        print(json.dumps({"error": "Token file not found"}))
        sys.exit(1)

    # Check expiry
    expires_at = tokens.get("expires_at")
    if expires_at:
        exp = datetime.fromisoformat(expires_at)
        if datetime.now(JST) >= exp - timedelta(minutes=5):
            tokens = refresh_tokens(tokens)
            if tokens:
                save_json(TOKEN_FILE, tokens)

    return tokens


def refresh_tokens(tokens):
    """Refresh OAuth2 tokens"""
    creds = load_json(CLIENT_CRED_FILE)
    if not creds:
        return None

    resp = httpx.post(REFRESH_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": tokens.get("refresh_token", ""),
    }, auth=(creds["client_id"], creds["client_secret"]))

    if resp.status_code == 200:
        data = resp.json()
        new_tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", tokens.get("refresh_token")),
            "token_type": data.get("token_type", "bearer"),
            "expires_at": (datetime.now(JST) + timedelta(seconds=data.get("expires_in", 7200))).isoformat(),
        }
        save_json(TOKEN_FILE, new_tokens)
        return new_tokens
    return None


def load_queue():
    """Load post queue"""
    queue = load_json(QUEUE_FILE, {"pending": [], "completed": []})
    if "pending" not in queue:
        queue["pending"] = []
    if "completed" not in queue:
        queue["completed"] = []
    return queue


def save_queue(queue):
    """Save post queue"""
    save_json(QUEUE_FILE, queue)


def load_history():
    """Load post history"""
    return load_json(HISTORY_FILE, {"posts": [], "stats": {}})


def save_history(history):
    """Save post history"""
    save_json(HISTORY_FILE, history)


def add_to_queue(text: str, scheduled_at: Optional[str] = None,
                 image_path: Optional[str] = None, tags: Optional[list] = None,
                 priority: int = 5):
    """Add a post to the queue"""
    queue = load_queue()

    # Validate no overlap within MIN_POST_INTERVAL
    if scheduled_at:
        scheduled_time = datetime.fromisoformat(scheduled_at)
        for item in queue["pending"]:
            item_time = datetime.fromisoformat(item["scheduled_at"])
            if abs((scheduled_time - item_time).total_seconds()) < MIN_POST_INTERVAL_MIN * 60:
                print(json.dumps({
                    "error": f"Too close to existing post: {item['scheduled_at']}",
                    "min_interval_min": MIN_POST_INTERVAL_MIN
                }))
                sys.exit(1)

    entry = {
        "id": datetime.now(JST).strftime("Q%m%d%H%M%S"),
        "text": text,
        "scheduled_at": scheduled_at or datetime.now(JST).isoformat(),
        "image_path": image_path,
        "tags": tags or [],
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now(JST).isoformat(),
    }

    queue["pending"].append(entry)
    # Sort by scheduled_at
    queue["pending"].sort(key=lambda x: x["scheduled_at"])
    save_queue(queue)

    print(json.dumps({"success": True, "queue_id": entry["id"], "scheduled_at": entry["scheduled_at"]}))


def list_queue(status_filter: Optional[str] = None):
    """List posts in the queue"""
    queue = load_queue()

    items = []
    for item in queue["pending"]:
        if status_filter and item.get("status") != status_filter:
            continue
        items.append(item)

    result = {
        "pending_count": len([i for i in queue["pending"] if i["status"] == "pending"]),
        "total_pending": len(queue["pending"]),
        "total_completed": len(queue["completed"]),
        "items": items[:20],  # Show latest 20
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


def remove_from_queue(queue_id: str):
    """Remove a post from the queue"""
    queue = load_queue()
    queue["pending"] = [i for i in queue["pending"] if i["id"] != queue_id]
    save_queue(queue)
    print(json.dumps({"success": True, "removed": queue_id}))


def process_queue():
    """Process due posts in the queue"""
    queue = load_queue()
    tokens = load_tokens()
    now = datetime.now(JST)

    processed = []
    failed = []

    for item in queue["pending"]:
        if item["status"] != "pending":
            continue

        scheduled_time = datetime.fromisoformat(item["scheduled_at"])
        if scheduled_time > now:
            continue

        # Post the tweet
        result = post_tweet(tokens["access_token"], item["text"], item.get("image_path"))

        if result.get("success"):
            item["status"] = "completed"
            item["posted_at"] = now.isoformat()
            item["tweet_id"] = result.get("tweet_id")
            queue["completed"].append(item)
            processed.append(item)
        else:
            item["status"] = "failed"
            item["error"] = result.get("error", "Unknown error")
            failed.append(item)

    # Remove completed/failed from pending
    queue["pending"] = [i for i in queue["pending"] if i["status"] == "pending"]
    save_queue(queue)

    # Update history
    if processed:
        history = load_history()
        for item in processed:
            history["posts"].append({
                "tweet_id": item["tweet_id"],
                "text": item["text"],
                "posted_at": item["posted_at"],
                "scheduled_at": item["scheduled_at"],
                "tags": item.get("tags", []),
                "queue_id": item["id"],
            })
        history["stats"]["last_processed"] = now.isoformat()
        history["stats"]["total_posts"] = len(history["posts"])
        save_history(history)

    print(json.dumps({
        "processed": len(processed),
        "failed": len(failed),
        "remaining": len(queue["pending"]),
        "details": {
            "processed": [{"id": i["id"], "tweet_id": i.get("tweet_id")} for i in processed],
            "failed": [{"id": i["id"], "error": i.get("error")} for i in failed],
        }
    }, indent=2, ensure_ascii=False))


def post_tweet(access_token: str, text: str, image_path: Optional[str] = None) -> dict:
    """Post a tweet"""
    payload = {"text": text}

    resp = httpx.post(
        POST_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        tweet_id = data.get("data", {}).get("id")
        return {"success": True, "tweet_id": tweet_id}
    else:
        return {"success": False, "error": f"{resp.status_code}: {resp.text}"}


def suggest_times():
    """Suggest optimal posting times based on history"""
    history = load_history()
    posts = history.get("posts", [])

    if len(posts) < 5:
        # Default suggestions based on general best practices
        suggestions = [
            {"time": "08:00", "reason": "朝の通勤時間帯"},
            {"time": "12:00", "reason": "昼休み"},
            {"time": "18:00", "reason": "帰宅時間帯"},
            {"time": "21:00", "reason": "夜のリラックスタイム"},
        ]
    else:
        # Analyze posting history for patterns
        from collections import Counter
        hour_counts = Counter()
        for post in posts[-30:]:  # Last 30 posts
            posted_at = post.get("posted_at", "")
            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at)
                    hour_counts[dt.hour] += 1
                except:
                    pass

        suggestions = []
        for hour, count in hour_counts.most_common(4):
            suggestions.append({
                "time": f"{hour:02d}:00",
                "reason": f"過去{count}回投稿",
            })

    print(json.dumps({"suggestions": suggestions}, indent=2, ensure_ascii=False))


def stats():
    """Show posting statistics"""
    queue = load_queue()
    history = load_history()
    posts = history.get("posts", [])

    # Today's posts
    today = datetime.now(JST).strftime("%Y-%m-%d")
    today_posts = [p for p in posts if p.get("posted_at", "").startswith(today)]

    # This week's posts
    week_ago = (datetime.now(JST) - timedelta(days=7)).isoformat()
    week_posts = [p for p in posts if p.get("posted_at", "") >= week_ago]

    result = {
        "queue": {
            "pending": len([i for i in queue["pending"] if i["status"] == "pending"]),
            "next_post": min(
                (i["scheduled_at"] for i in queue["pending"] if i["status"] == "pending"),
                default=None,
            ),
        },
        "history": {
            "total_posts": len(posts),
            "today": len(today_posts),
            "this_week": len(week_posts),
            "last_post": posts[-1]["posted_at"] if posts else None,
        },
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="X Post Scheduler")
    sub = parser.add_subparsers(dest="command")

    # add
    add_p = sub.add_parser("add", help="Add post to queue")
    add_p.add_argument("text", help="Post text")
    add_p.add_argument("--at", help="Scheduled time (ISO format)", default=None)
    add_p.add_argument("--image", help="Image path", default=None)
    add_p.add_argument("--tags", nargs="*", help="Tags", default=[])
    add_p.add_argument("--priority", type=int, default=5, help="Priority (1-10)")

    # list
    list_p = sub.add_parser("list", help="List queue")
    list_p.add_argument("--status", default=None, help="Filter by status")

    # remove
    rm_p = sub.add_parser("remove", help="Remove from queue")
    rm_p.add_argument("queue_id", help="Queue ID to remove")

    # process
    sub.add_parser("process", help="Process due posts")

    # suggest
    sub.add_parser("suggest", help="Suggest optimal posting times")

    # stats
    sub.add_parser("stats", help="Show posting statistics")

    args = parser.parse_args()

    if args.command == "add":
        add_to_queue(args.text, args.at, args.image, args.tags, args.priority)
    elif args.command == "list":
        list_queue(args.status)
    elif args.command == "remove":
        remove_from_queue(args.queue_id)
    elif args.command == "process":
        process_queue()
    elif args.command == "suggest":
        suggest_times()
    elif args.command == "stats":
        stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

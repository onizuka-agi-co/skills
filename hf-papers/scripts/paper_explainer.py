#!/usr/bin/env python3
"""
AGI Paper Explainer Bot

HuggingFace Daily Papersから注目論文を自動ピックアップし、
日本語解説＋図解画像をXにスレッド投稿するBot。

Usage:
    uv run skills/hf-papers/scripts/paper_explainer.py run [--limit 3] [--min-upvotes 10]
    uv run skills/hf-papers/scripts/paper_explainer.py test [--limit 1]
    uv run skills/hf-papers/scripts/paper_explainer.py history
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Paths
WORKSPACE = Path(__file__).parent.parent.parent.parent
DATA_DIR = WORKSPACE / "data" / "paper-explainer"
HF_CACHE = WORKSPACE / "data" / "hf-papers"

# Gemini API
GEMINI_API_KEY_FILE = WORKSPACE / "gemini-api-key.txt"

# X tokens
X_TOKENS_FILE = WORKSPACE / "x-tokens.json"

# Fal key
FAL_KEY_FILE = WORKSPACE / "fal-key.txt"

# Discord webhook
DISCORD_WEBHOOK_FILE = WORKSPACE / "discord-webhooks.json"

JST = timezone(timedelta(hours=9))


def get_gemini_key() -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    if GEMINI_API_KEY_FILE.exists():
        content = GEMINI_API_KEY_FILE.read_text().strip()
        # Handle GEMINI_API_KEY=prefix format
        if content.startswith("GEMINI_API_KEY="):
            content = content.split("=", 1)[1]
        return content
    return None


def get_x_tokens() -> Optional[dict]:
    if not X_TOKENS_FILE.exists():
        return None
    with open(X_TOKENS_FILE) as f:
        return json.load(f)


def get_discord_webhook() -> Optional[str]:
    if not DISCORD_WEBHOOK_FILE.exists():
        return None
    with open(DISCORD_WEBHOOK_FILE) as f:
        hooks = json.load(f)
    return hooks.get("paper_explainer") or hooks.get("default")


def fetch_hf_papers(limit: int = 20) -> list[dict]:
    """Fetch today's HuggingFace Daily Papers."""
    url = "https://huggingface.co/api/daily_papers"
    req = Request(url, headers={"User-Agent": "ONIZUKA-Paper-Explainer/1.0"})

    cache_file = HF_CACHE / "daily_papers.json"
    if cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < 3600:
            with open(cache_file) as f:
                papers = json.load(f)
                return papers[:limit]

    try:
        with urlopen(req, timeout=30) as resp:
            papers = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError) as e:
        print(f"Error fetching papers: {e}", file=sys.stderr)
        if cache_file.exists():
            with open(cache_file) as f:
                papers = json.load(f)
        else:
            return []

    HF_CACHE.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(papers, f, ensure_ascii=False)

    return papers[:limit]


def filter_papers(papers: list[dict], min_upvotes: int = 10, posted_ids: set = None) -> list[dict]:
    """Filter papers by upvotes and exclude already posted."""
    posted_ids = posted_ids or set()
    result = []
    for p in papers:
        pid = p.get("paper", {}).get("id", "")
        upvotes = p.get("paper", {}).get("upvotes", 0)
        if pid not in posted_ids and upvotes >= min_upvotes:
            result.append(p)
    # Sort by upvotes descending
    result.sort(key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True)
    return result


def load_posted_ids() -> set:
    """Load already posted paper IDs."""
    history_file = DATA_DIR / "history.json"
    if not history_file.exists():
        return set()
    with open(history_file) as f:
        history = json.load(f)
    return {item["paper_id"] for item in history}


def save_to_history(entry: dict):
    """Save a posted entry to history."""
    history_file = DATA_DIR / "history.json"
    history = []
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
    history.append(entry)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(history_file, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def generate_explanation(paper: dict, gemini_key: str) -> Optional[dict]:
    """Generate Japanese explanation using Gemini API."""
    title = paper.get("paper", {}).get("title", "Unknown")
    abstract = paper.get("paper", {}).get("summary", "")
    authors = paper.get("paper", {}).get("authors", [])
    author_names = ", ".join(a.get("name", "") for a in authors[:5])
    if len(authors) > 5:
        author_names += " et al."

    prompt = f"""以下のAGI/AI研究論文について、日本語でわかりやすい解説を作成してください。

タイトル: {title}
著者: {author_names}
アブストラクト: {abstract}

以下の形式で出力してください：

1. **一言でいうと**（15文字以内）
2. **概要**（3〜4文、専門用語にも簡単な説明を付ける）
3. **なぜ重要か**（2〜3文）
4. **キーワード**（5個以内、カンマ区切り）
5. **図解プロンプト**（この論文のキーアイデアを可視化する、nano-banana-2用の英語プロンプト、1文）

JSON形式で出力:
{{
  "one_liner": "...",
  "summary": "...",
  "importance": "...",
  "keywords": ["...", "..."],
  "image_prompt": "..."
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
    }

    req = Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "ONIZUKA-Paper-Explainer/1.0")

    try:
        data = json.dumps(payload).encode("utf-8")
        with urlopen(req, data, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            # Extract JSON from markdown code block if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
    except Exception as e:
        print(f"Error generating explanation: {e}", file=sys.stderr)
        return None


def generate_image(prompt: str) -> Optional[str]:
    """Generate image using nano-banana-2 via fal.ai."""
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key and FAL_KEY_FILE.exists():
        fal_key = FAL_KEY_FILE.read_text().strip()
    if not fal_key:
        print("FAL_KEY not found", file=sys.stderr)
        return None

    try:
        import fal_client

        result = fal_client.submit(
            "fal-ai/nano-banana-2",
            arguments={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "resolution": "1K",
                "output_format": "png",
                "num_images": 1,
            },
            api_key=fal_key,
        )
        output = result.get()
        if output and output.get("images"):
            return output["images"][0]["url"]
    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
    return None


def post_x_thread(paper: dict, explanation: dict, image_url: Optional[str] = None) -> Optional[list[str]]:
    """Post explanation as X thread."""
    tokens = get_x_tokens()
    if not tokens:
        print("X tokens not found", file=sys.stderr)
        return None

    access_token = tokens.get("access_token")
    if not access_token:
        print("No access token", file=sys.stderr)
        return None

    title = paper.get("paper", {}).get("title", "")
    pid = paper.get("paper", {}).get("id", "")
    arxiv_url = f"https://arxiv.org/abs/{pid}" if pid else ""
    upvotes = paper.get("paper", {}).get("upvotes", 0)

    # First tweet
    tweet1 = f"""📜 {explanation.get('one_liner', '')}

{explanation.get('summary', '')}

#{' #'.join(['ONIZUKA_AGI'] + explanation.get('keywords', [])[:3])}"""

    # Post first tweet
    tweet_ids = []
    payload = {"text": tweet1[:280]}

    req = Request(
        "https://api.x.com/2/tweets",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("User-Agent", "ONIZUKA-Paper-Explainer/1.0")

    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            tweet_id = result["data"]["id"]
            tweet_ids.append(tweet_id)
            print(f"Posted tweet 1: {tweet_id}")
    except Exception as e:
        print(f"Error posting tweet 1: {e}", file=sys.stderr)
        return None

    time.sleep(2)

    # Second tweet (importance + link)
    tweet2 = f"""💡 なぜ重要か
{explanation.get('importance', '')}

📄 {title}
🔗 {arxiv_url}
⬆️ {upvotes} upvotes"""

    payload2 = {
        "text": tweet2[:280],
        "reply": {"in_reply_to_tweet_id": tweet_id}
    }

    req2 = Request(
        "https://api.x.com/2/tweets",
        method="POST",
        data=json.dumps(payload2).encode("utf-8"),
    )
    req2.add_header("Content-Type", "application/json")
    req2.add_header("Authorization", f"Bearer {access_token}")
    req2.add_header("User-Agent", "ONIZUKA-Paper-Explainer/1.0")

    try:
        with urlopen(req2, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            tweet2_id = result["data"]["id"]
            tweet_ids.append(tweet2_id)
            print(f"Posted tweet 2: {tweet2_id}")
    except Exception as e:
        print(f"Error posting tweet 2: {e}", file=sys.stderr)

    return tweet_ids


def notify_discord(paper: dict, explanation: dict, tweet_ids: list[str] = None, image_url: str = None):
    """Send Discord notification."""
    webhook_url = get_discord_webhook()
    if not webhook_url:
        return

    title = paper.get("paper", {}).get("title", "")
    pid = paper.get("paper", {}).get("id", "")
    tweet_url = f"https://x.com/i/status/{tweet_ids[0]}" if tweet_ids else ""

    embed = {
        "title": f"📜 {explanation.get('one_liner', '')}",
        "description": explanation.get("summary", "")[:500],
        "color": 0xC41E3A,
        "fields": [
            {"name": "📄 論文", "value": f"[{title}](https://arxiv.org/abs/{pid})", "inline": False},
            {"name": "💡 重要性", "value": explanation.get("importance", ""), "inline": False},
        ],
        "footer": {"text": "🎋 AGI Paper Explainer Bot"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if tweet_url:
        embed["fields"].append({"name": "🐦 投稿", "value": tweet_url, "inline": False})

    payload = {
        "username": "🎋 Paper Explainer",
        "embeds": [embed],
        "allowed_mentions": {"parse": []}
    }

    if image_url:
        embed["image"] = {"url": image_url}

    req = Request(webhook_url, method="POST", data=json.dumps(payload).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "ONIZUKA-Paper-Explainer/1.0")

    try:
        with urlopen(req, timeout=30) as resp:
            print("Discord notification sent")
    except Exception as e:
        print(f"Error sending Discord notification: {e}", file=sys.stderr)


def run(limit: int = 3, min_upvotes: int = 10, dry_run: bool = False):
    """Main execution."""
    print(f"=== AGI Paper Explainer Bot ===")
    print(f"Time: {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
    print(f"Limit: {limit}, Min upvotes: {min_upvotes}, Dry run: {dry_run}")

    # Check API keys
    gemini_key = get_gemini_key()
    if not gemini_key:
        print("ERROR: Gemini API key not found", file=sys.stderr)
        sys.exit(1)

    # Fetch papers
    print("\n📥 Fetching HuggingFace Daily Papers...")
    papers = fetch_hf_papers(limit=50)
    if not papers:
        print("No papers found")
        return

    # Filter
    posted_ids = load_posted_ids()
    filtered = filter_papers(papers, min_upvotes=min_upvotes, posted_ids=posted_ids)
    to_process = filtered[:limit]
    print(f"Found {len(filtered)} papers with >={min_upvotes} upvotes (already posted: {len(posted_ids)})")
    print(f"Processing {len(to_process)} papers\n")

    for i, paper in enumerate(to_process, 1):
        pid = paper.get("paper", {}).get("id", "")
        title = paper.get("paper", {}).get("title", "")
        upvotes = paper.get("paper", {}).get("upvotes", 0)
        print(f"--- Paper {i}/{len(to_process)} ---")
        print(f"Title: {title}")
        print(f"ID: {pid} | Upvotes: {upvotes}")

        # Generate explanation
        print("🧠 Generating explanation...")
        explanation = generate_explanation(paper, gemini_key)
        if not explanation:
            print("Failed to generate explanation, skipping")
            continue

        print(f"One-liner: {explanation.get('one_liner', '')}")

        if dry_run:
            print("DRY RUN - skipping posting")
            print(f"Summary: {explanation.get('summary', '')[:100]}...")
            print(f"Image prompt: {explanation.get('image_prompt', '')}")
            save_to_history({
                "paper_id": pid,
                "title": title,
                "upvotes": upvotes,
                "explanation": explanation,
                "posted_at": datetime.now(JST).isoformat(),
                "dry_run": True,
            })
            continue

        # Generate image
        image_url = None
        img_prompt = explanation.get("image_prompt", "")
        if img_prompt:
            print(f"🎨 Generating image: {img_prompt[:80]}...")
            image_url = generate_image(img_prompt)
            if image_url:
                print(f"Image: {image_url}")

        # Post to X
        print("🐦 Posting to X...")
        tweet_ids = post_x_thread(paper, explanation, image_url)

        # Notify Discord
        notify_discord(paper, explanation, tweet_ids, image_url)

        # Save to history
        save_to_history({
            "paper_id": pid,
            "title": title,
            "upvotes": upvotes,
            "explanation": explanation,
            "tweet_ids": tweet_ids,
            "image_url": image_url,
            "posted_at": datetime.now(JST).isoformat(),
        })

        print(f"✅ Done: {title[:50]}\n")
        if i < len(to_process):
            time.sleep(5)

    print(f"=== Complete: {len(to_process)} papers processed ===")


def show_history(limit: int = 10):
    """Show posting history."""
    history_file = DATA_DIR / "history.json"
    if not history_file.exists():
        print("No history found")
        return

    with open(history_file) as f:
        history = json.load(f)

    print(f"=== Paper Explainer History ({len(history)} total) ===\n")
    for item in history[-limit:]:
        status = "DRY RUN" if item.get("dry_run") else "POSTED"
        print(f"[{status}] {item['title'][:60]}")
        print(f"  ID: {item['paper_id']} | Upvotes: {item['upvotes']}")
        print(f"  Posted: {item.get('posted_at', 'N/A')}")
        if item.get('tweet_ids'):
            print(f"  Tweets: {', '.join(item['tweet_ids'])}")
        print()


def main():
    parser = argparse.ArgumentParser(description="AGI Paper Explainer Bot")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the explainer")
    run_parser.add_argument("--limit", type=int, default=3, help="Max papers to process")
    run_parser.add_argument("--min-upvotes", type=int, default=10, help="Minimum upvotes")

    test_parser = subparsers.add_parser("test", help="Dry run")
    test_parser.add_argument("--limit", type=int, default=1, help="Max papers to process")
    test_parser.add_argument("--min-upvotes", type=int, default=5, help="Minimum upvotes")

    subparsers.add_parser("history", help="Show posting history")

    args = parser.parse_args()

    if args.command == "run":
        run(limit=args.limit, min_upvotes=args.min_upvotes)
    elif args.command == "test":
        run(limit=args.limit, min_upvotes=args.min_upvotes, dry_run=True)
    elif args.command == "history":
        show_history()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

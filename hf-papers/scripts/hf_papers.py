#!/usr/bin/env python3
"""
HF Papers - HuggingFace Daily Papers Fetcher

Fetches daily papers from HuggingFace and provides utilities for processing them.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# API endpoint
HF_DAILY_PAPERS_API = "https://huggingface.co/api/daily_papers"

# Cache directory
CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "hf-papers"
CACHE_EXPIRY_HOURS = 1  # Cache expires after 1 hour


def fetch_papers(limit: Optional[int] = None, use_cache: bool = True) -> list[dict]:
    """Fetch daily papers from HuggingFace API."""
    
    # Check cache
    cache_file = CACHE_DIR / "daily_papers.json"
    if use_cache and cache_file.exists():
        cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if cache_age < CACHE_EXPIRY_HOURS * 3600:
            with open(cache_file, "r") as f:
                papers = json.load(f)
                if limit:
                    return papers[:limit]
                return papers
    
    # Fetch from API
    request = Request(
        HF_DAILY_PAPERS_API,
        headers={"User-Agent": "ONIZUKA-AGI-HF-Papers/1.0"}
    )
    
    try:
        with urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
            papers = json.loads(data)
    except (HTTPError, URLError) as e:
        print(f"Error fetching papers: {e}", file=sys.stderr)
        # Fall back to cache if available
        if cache_file.exists():
            with open(cache_file, "r") as f:
                papers = json.load(f)
        else:
            return []
    
    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(papers, f, indent=2)
    
    if limit:
        return papers[:limit]
    return papers


def get_paper_by_id(paper_id: str) -> Optional[dict]:
    """Get a specific paper by arXiv ID."""
    papers = fetch_papers(use_cache=False)
    
    for item in papers:
        paper = item.get("paper", item)
        if paper.get("id") == paper_id:
            return item
    
    return None


def format_paper(paper_data: dict, brief: bool = False) -> str:
    """Format paper data for display."""
    paper = paper_data.get("paper", paper_data)
    
    if brief:
        return f"[{paper.get('id')}] {paper.get('title')}"
    
    lines = [
        f"**{paper.get('title')}**",
        f"arXiv: {paper.get('id')}",
        "",
        f"**Summary:** {paper.get('ai_summary', paper.get('summary', 'N/A')[:200] + '...')}",
        "",
        f"**Keywords:** {', '.join(paper.get('ai_keywords', []))}",
        "",
        f"**Upvotes:** {paper.get('upvotes', 0)}",
    ]
    
    if paper.get('githubRepo'):
        lines.append(f"**GitHub:** {paper.get('githubRepo')}")
    
    return "\n".join(lines)


def cmd_fetch(args):
    """Fetch and display papers."""
    papers = fetch_papers(limit=args.limit)
    
    print(f"Found {len(papers)} papers\n")
    
    for i, paper_data in enumerate(papers, 1):
        paper = paper_data.get("paper", paper_data)
        print(f"{i}. {format_paper(paper_data, brief=True)}")
        print(f"   Upvotes: {paper.get('upvotes', 0)}")
        print()


def cmd_get(args):
    """Get a specific paper."""
    paper = get_paper_by_id(args.paper_id)
    
    if not paper:
        print(f"Paper {args.paper_id} not found", file=sys.stderr)
        sys.exit(1)
    
    print(format_paper(paper))


def cmd_top(args):
    """Get top papers by upvotes."""
    papers = fetch_papers()
    
    # Sort by upvotes
    sorted_papers = sorted(
        papers,
        key=lambda x: x.get("paper", x).get("upvotes", 0),
        reverse=True
    )
    
    limit = args.limit or 10
    for i, paper_data in enumerate(sorted_papers[:limit], 1):
        paper = paper_data.get("paper", paper_data)
        print(f"{i}. [{paper.get('id')}] {paper.get('title')}")
        print(f"   Upvotes: {paper.get('upvotes', 0)}")
        print()


def cmd_explain(args):
    """Generate visual explanation for a paper."""
    paper = get_paper_by_id(args.paper_id)
    
    if not paper:
        print(f"Paper {args.paper_id} not found", file=sys.stderr)
        sys.exit(1)
    
    paper_info = paper.get("paper", paper)
    
    # Generate explanation prompt
    title = paper_info.get("title", "")
    summary = paper_info.get("ai_summary", paper_info.get("summary", ""))
    keywords = paper_info.get("ai_keywords", [])
    
    prompt = f"""Create a visual explanation diagram for the following AI research paper:

Title: {title}

Summary: {summary}

Keywords: {', '.join(keywords)}

Style: Modern, clean infographic with Japanese labels, suitable for social media posting."""

    print("=== Image Generation Prompt ===")
    print(prompt)
    print()
    print("To generate the image, use:")
    print(f"  uv run skills/nano-banana-2/scripts/generate.py --prompt \"{prompt[:100]}...\"")


def main():
    parser = argparse.ArgumentParser(
        description="HF Papers - HuggingFace Daily Papers Fetcher"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch daily papers")
    fetch_parser.add_argument("--limit", type=int, help="Limit number of papers")
    fetch_parser.set_defaults(func=cmd_fetch)
    
    # get command
    get_parser = subparsers.add_parser("get", help="Get a specific paper")
    get_parser.add_argument("paper_id", help="arXiv paper ID (e.g., 2603.02138)")
    get_parser.set_defaults(func=cmd_get)
    
    # top command
    top_parser = subparsers.add_parser("top", help="Get top papers by upvotes")
    top_parser.add_argument("--limit", type=int, default=10, help="Number of papers")
    top_parser.set_defaults(func=cmd_top)
    
    # explain command
    explain_parser = subparsers.add_parser("explain", help="Generate visual explanation")
    explain_parser.add_argument("paper_id", help="arXiv paper ID")
    explain_parser.set_defaults(func=cmd_explain)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()

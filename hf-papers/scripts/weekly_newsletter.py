#!/usr/bin/env python3
"""
AGI Weekly Newsletter Generator

Generates a weekly newsletter summarizing AGI research papers from HuggingFace Daily Papers
and related content from the knowledge base.

Usage:
    uv run scripts/weekly_newsletter.py generate [--week YYYY-MM-DD] [--limit 10] [--output DIR]
    uv run scripts/weekly_newsletter.py post-discord [--channel-id ID] [--webhook-url URL]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx

# Workspace root
WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
HF_DATA_DIR = WORKSPACE / "data" / "hf-papers"
DAILY_PAPERS_FILE = HF_DATA_DIR / "daily_papers.json"


def get_week_range(reference_date: datetime | None = None) -> tuple[datetime, datetime]:
    """Get Monday-Sunday range for the week containing reference_date."""
    ref = reference_date or datetime.now()
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def fetch_papers_for_week(monday: datetime, sunday: datetime, limit: int = 20) -> list[dict]:
    """Fetch papers from HuggingFace Daily Papers API for a date range."""
    papers = []
    url = "https://huggingface.co/api/daily_papers"
    
    current = monday
    while current <= sunday:
        try:
            resp = httpx.get(url, params={"date": current.strftime("%Y-%m-%d")}, timeout=30)
            if resp.status_code == 200:
                day_papers = resp.json()
                for p in day_papers:
                    paper = p.get("paper", p)
                    published = paper.get("publishedAt", "")
                    papers.append({
                        "id": paper.get("id", ""),
                        "title": paper.get("title", ""),
                        "authors": [a.get("name", "") for a in paper.get("authors", [])],
                        "summary": paper.get("summary", "")[:500],
                        "upvotes": p.get("paper", {}).get("upvotes", 0) if isinstance(p.get("paper"), dict) else 0,
                        "url": f"https://huggingface.co/papers/{paper.get('id', '')}",
                        "publishedAt": published,
                        "date": current.strftime("%Y-%m-%d"),
                    })
        except Exception as e:
            print(f"Error fetching papers for {current}: {e}", file=sys.stderr)
        current += timedelta(days=1)
    
    # Sort by upvotes descending
    papers.sort(key=lambda x: x.get("upvotes", 0), reverse=True)
    return papers[:limit]


def load_local_papers() -> list[dict]:
    """Load papers from local cache if available."""
    if DAILY_PAPERS_FILE.exists():
        with open(DAILY_PAPERS_FILE) as f:
            return json.load(f)
    return []


def generate_newsletter(papers: list[dict], monday: datetime, sunday: datetime) -> str:
    """Generate newsletter markdown content."""
    week_label = f"{monday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}"
    
    lines = [
        f"# 📰 AGI Weekly Newsletter",
        f"",
        f"**{week_label}**",
        f"",
        f"ONIZUKA AGI Co. がお届けする、今週のAGI研究動向まとめ。",
        f"",
        f"---",
        f"",
    ]
    
    if not papers:
        lines.append("*今週は新しい論文が見つかりませんでした。*")
    else:
        lines.append(f"## 📊 今週のハイライト ({len(papers)} papers)")
        lines.append("")
        
        # Top 3 highlights
        for i, paper in enumerate(papers[:3], 1):
            title = paper.get("title", "Unknown")
            paper_id = paper.get("id", "")
            url = paper.get("url", f"https://huggingface.co/papers/{paper_id}")
            summary = paper.get("summary", "")
            upvotes = paper.get("upvotes", 0)
            authors = paper.get("authors", [])
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += f" et al. ({len(authors)} authors)"
            
            lines.append(f"### {i}. {title}")
            lines.append(f"")
            lines.append(f"**Authors:** {author_str}")
            lines.append(f"**👍 {upvotes} upvotes** | [Paper]({url}) | [arXiv](https://arxiv.org/abs/{paper_id})")
            lines.append(f"")
            if summary:
                lines.append(f"> {summary[:300]}...")
                lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        
        # Remaining papers as list
        if len(papers) > 3:
            lines.append(f"## 📋 その他の論文 ({len(papers) - 3} papers)")
            lines.append("")
            for paper in papers[3:]:
                title = paper.get("title", "Unknown")
                paper_id = paper.get("id", "")
                url = paper.get("url", f"https://huggingface.co/papers/{paper_id}")
                upvotes = paper.get("upvotes", 0)
                lines.append(f"- [{title}]({url}) ({upvotes}👍)")
            lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("*Generated by ONIZUKA AGI Co. | #ONIZUKA_AGI*")
    lines.append("")
    
    return "\n".join(lines)


def generate_discord_embed(papers: list[dict], monday: datetime, sunday: datetime) -> dict:
    """Generate Discord embed payload for the newsletter."""
    week_label = f"{monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')}"
    
    top3 = papers[:3]
    description_parts = []
    for i, p in enumerate(top3, 1):
        title = p.get("title", "Unknown")[:80]
        upvotes = p.get("upvotes", 0)
        description_parts.append(f"**{i}. {title}** ({upvotes}👍)")
    
    remaining = len(papers) - 3 if len(papers) > 3 else 0
    if remaining > 0:
        description_parts.append(f"\n...and {remaining} more papers")
    
    return {
        "embeds": [{
            "title": f"📰 AGI Weekly Newsletter ({week_label})",
            "description": "\n".join(description_parts),
            "color": 0xFFD700,
            "footer": {"text": "ONIZUKA AGI Co. | #ONIZUKA_AGI"},
            "timestamp": datetime.now().isoformat(),
        }]
    }


def post_to_discord(embed: dict, webhook_url: str | None = None):
    """Post newsletter to Discord via webhook."""
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        # Try loading from config
        webhook_file = WORKSPACE / "data" / "x" / "x-discord-webhook.json"
        if webhook_file.exists():
            with open(webhook_file) as f:
                url = json.load(f).get("webhook_url")
    
    if not url:
        print("Error: No Discord webhook URL provided", file=sys.stderr)
        sys.exit(1)
    
    resp = httpx.post(url, json=embed, timeout=30)
    if resp.status_code in (200, 204):
        print("Newsletter posted to Discord!")
    else:
        print(f"Error posting to Discord: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AGI Weekly Newsletter Generator")
    subparsers = parser.add_subparsers(dest="command")
    
    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate newsletter")
    gen_parser.add_argument("--week", help="Reference date for the week (YYYY-MM-DD)")
    gen_parser.add_argument("--limit", type=int, default=15, help="Max papers to include")
    gen_parser.add_argument("--output", help="Output directory")
    
    # post-discord
    discord_parser = subparsers.add_parser("post-discord", help="Post to Discord")
    discord_parser.add_argument("--webhook-url", help="Discord webhook URL")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Determine week
    ref_date = datetime.strptime(args.week, "%Y-%m-%d") if hasattr(args, "week") and args.week else None
    monday, sunday = get_week_range(ref_date)
    
    print(f"Fetching papers for week: {monday.date()} ~ {sunday.date()}")
    
    # Fetch papers
    limit = getattr(args, "limit", 15)
    papers = fetch_papers_for_week(monday, sunday, limit=limit)
    
    if not papers:
        print("No papers found, trying local cache...")
        papers = load_local_papers()[:limit]
    
    print(f"Found {len(papers)} papers")
    
    if args.command == "generate":
        newsletter = generate_newsletter(papers, monday, sunday)
        
        if hasattr(args, "output") and args.output:
            out_dir = Path(args.output)
        else:
            out_dir = WORKSPACE / "data" / "newsletters"
        
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"newsletter-{monday.strftime('%Y%m%d')}.md"
        out_file.write_text(newsletter)
        print(f"Newsletter saved to: {out_file}")
        
        # Save to VitePress weekly section
        vp_dir = WORKSPACE / "memory" / "docs" / "weekly" / monday.strftime("%Y") / f"W{monday.strftime('%V')}"
        vp_dir.mkdir(parents=True, exist_ok=True)
        vp_file = vp_dir / "index.md"
        # Add frontmatter for VitePress
        vp_content = f"""---
title: "AGI Weekly Newsletter - W{monday.strftime('%V')} {monday.strftime('%Y')}"
date: {monday.strftime('%Y-%m-%d')}
---

{newsletter}
"""
        vp_file.write_text(vp_content)
        print(f"VitePress page saved to: {vp_file}")
        
        # Also print to stdout
        print("\n" + "=" * 60)
        print(newsletter)
    
    elif args.command == "post-discord":
        embed = generate_discord_embed(papers, monday, sunday)
        post_to_discord(embed, getattr(args, "webhook_url", None))


if __name__ == "__main__":
    main()

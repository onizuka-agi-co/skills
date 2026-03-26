#!/usr/bin/env python3
"""
AGI Paper Watcher - Weekly AGI paper curator

Selects 1-2 AGI-related papers weekly, generates explanations with visual diagrams.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from hf_papers import fetch_papers, get_paper_by_id, CACHE_DIR

# AGI-related keywords for filtering
AGI_KEYWORDS = [
    "agi",
    "artificial general intelligence",
    "reasoning",
    "world model",
    "planning",
    "autonomous agent",
    "multi-agent",
    "chain of thought",
    "self-improvement",
    "meta-learning",
    "few-shot",
    "in-context learning",
    "emergence",
    "scaling law",
    "foundation model",
    "large language model",
    "llm",
    "transformer",
    "gpt",
    "claude",
    "gemini",
    "reinforcement learning from human feedback",
    "rlhf",
    "constitutional ai",
    "tool use",
    "function calling",
    "code generation",
    "mathematical reasoning",
]

# Categories for paper classification
CATEGORIES = {
    "agi-core": ["agi", "artificial general intelligence", "reasoning", "planning"],
    "llm": ["llm", "large language model", "transformer", "gpt", "claude", "gemini"],
    "reasoning": ["chain of thought", "mathematical reasoning", "logical reasoning"],
    "agents": ["autonomous agent", "multi-agent", "tool use", "function calling"],
    "learning": ["meta-learning", "few-shot", "in-context learning", "rlhf"],
    "architecture": ["world model", "foundation model", "scaling law"],
}


def calculate_agi_score(paper_data: dict) -> tuple[float, list[str]]:
    """Calculate AGI relevance score for a paper."""
    paper = paper_data.get("paper", paper_data)
    
    title = paper.get("title", "").lower()
    summary = paper.get("ai_summary", paper.get("summary", "")).lower()
    keywords = [k.lower() for k in paper.get("ai_keywords", [])]
    
    all_text = f"{title} {summary} {' '.join(keywords)}"
    
    matched_keywords = []
    score = 0.0
    
    for keyword in AGI_KEYWORDS:
        if keyword in all_text:
            matched_keywords.append(keyword)
            # Weight by importance
            if keyword in ["agi", "artificial general intelligence", "reasoning"]:
                score += 2.0
            elif keyword in ["world model", "planning", "autonomous agent"]:
                score += 1.5
            else:
                score += 1.0
    
    # Bonus for upvotes (normalized)
    upvotes = paper.get("upvotes", 0)
    if upvotes > 100:
        score += 1.0
    elif upvotes > 50:
        score += 0.5
    
    return score, matched_keywords


def categorize_paper(paper_data: dict) -> str:
    """Categorize paper based on keywords."""
    paper = paper_data.get("paper", paper_data)
    
    title = paper.get("title", "").lower()
    summary = paper.get("ai_summary", paper.get("summary", "")).lower()
    all_text = f"{title} {summary}"
    
    category_scores = {}
    for category, cat_keywords in CATEGORIES.items():
        score = sum(1 for kw in cat_keywords if kw in all_text)
        category_scores[category] = score
    
    if not category_scores or max(category_scores.values()) == 0:
        return "general"
    
    return max(category_scores, key=category_scores.get)


def filter_agi_papers(papers: list[dict], min_score: float = 1.0) -> list[tuple[dict, float, list[str]]]:
    """Filter papers by AGI relevance."""
    scored_papers = []
    
    for paper_data in papers:
        score, keywords = calculate_agi_score(paper_data)
        if score >= min_score:
            scored_papers.append((paper_data, score, keywords))
    
    # Sort by score descending
    scored_papers.sort(key=lambda x: x[1], reverse=True)
    
    return scored_papers


def select_weekly_papers(papers: list[dict], count: int = 2) -> list[dict]:
    """Select 1-2 papers for weekly watch."""
    # Filter AGI-relevant papers
    agi_papers = filter_agi_papers(papers, min_score=1.0)
    
    if not agi_papers:
        print("⚠️ No AGI-relevant papers found, selecting top upvoted papers...")
        # Fall back to top upvoted papers
        sorted_papers = sorted(
            papers,
            key=lambda x: x.get("paper", x).get("upvotes", 0),
            reverse=True
        )
        return sorted_papers[:count]
    
    # Select top N papers
    selected = []
    for paper_data, score, keywords in agi_papers[:count]:
        paper = paper_data.get("paper", paper_data)
        paper["_agi_score"] = score
        paper["_agi_keywords"] = keywords
        paper["_category"] = categorize_paper(paper_data)
        selected.append(paper)
    
    return selected


def format_paper_report(paper: dict) -> str:
    """Format paper for weekly report."""
    title = paper.get("title", "")
    arxiv_id = paper.get("id", "")
    summary = paper.get("ai_summary", paper.get("summary", ""))
    keywords = paper.get("ai_keywords", [])
    agi_keywords = paper.get("_agi_keywords", [])
    agi_score = paper.get("_agi_score", 0)
    category = paper.get("_category", "general")
    upvotes = paper.get("upvotes", 0)
    github = paper.get("githubRepo", "")
    
    report = f"""## 📄 {title}

**カテゴリ:** {category}
**AGI関連度:** {agi_score:.1f}
**アップボート:** {upvotes}

### 要約

{summary}

### 関連キーワード

{', '.join(f'#{k}' for k in agi_keywords[:5])}

### リンク

- [arXiv](https://arxiv.org/abs/{arxiv_id})
- [HuggingFace Papers](https://huggingface.co/papers/{arxiv_id})
"""
    
    if github:
        report += f"- [GitHub]({github})\n"
    
    return report


def generate_weekly_report(papers: list[dict]) -> str:
    """Generate weekly AGI paper watch report."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    report = f"""---
title: 🔬 AGI論文ウォッチャー - {date_str}
---

# 🔬 AGI論文ウォッチャー

**{date_str}** 週次レポート

今週のAGI関連注目論文 {len(papers)} 本をピックアップ。

---

"""
    
    for i, paper in enumerate(papers, 1):
        report += f"### {i}. {paper.get('title', '')}\n\n"
        report += format_paper_report(paper)
        report += "\n---\n\n"
    
    report += """## 📌 まとめ

今週は上記の論文を要約・解説記事として公開予定です。

---

*このレポートは AGI論文ウォッチャー により自動生成されています。*

#AGI #ONIZUKA_AGI
"""
    
    return report


def cmd_select(args):
    """Select and display weekly AGI papers."""
    papers = fetch_papers(limit=args.limit or 50)
    
    selected = select_weekly_papers(papers, count=args.count)
    
    print(f"🎋 Selected {len(selected)} AGI-relevant papers:\n")
    
    for i, paper in enumerate(selected, 1):
        print(f"{i}. [{paper.get('id')}] {paper.get('title')}")
        print(f"   Score: {paper.get('_agi_score', 0):.1f}")
        print(f"   Category: {paper.get('_category', 'general')}")
        print(f"   Keywords: {', '.join(paper.get('_agi_keywords', [])[:5])}")
        print()


def cmd_report(args):
    """Generate weekly report."""
    papers = fetch_papers(limit=args.limit or 50)
    
    selected = select_weekly_papers(papers, count=args.count)
    
    report = generate_weekly_report(selected)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"✅ Report saved to: {output_path}")
    else:
        print(report)


def cmd_filter(args):
    """Filter and list AGI-relevant papers."""
    papers = fetch_papers(limit=args.limit or 50)
    
    filtered = filter_agi_papers(papers, min_score=args.min_score)
    
    print(f"Found {len(filtered)} AGI-relevant papers:\n")
    
    for paper_data, score, keywords in filtered[:args.count]:
        paper = paper_data.get("paper", paper_data)
        print(f"[{score:.1f}] [{paper.get('id')}] {paper.get('title')}")
        print(f"       Keywords: {', '.join(keywords[:5])}")
        print()


def send_discord_notification(papers: list[dict], report_path: Path) -> bool:
    """Send Discord notification about new papers."""
    import urllib.request
    import urllib.error
    
    # Load webhook URL
    workspace_root = Path(__file__).parent.parent.parent.parent
    webhook_file = workspace_root / "data" / "x" / "x-discord-webhook.json"
    
    if not webhook_file.exists():
        print("   ⚠️ Discord webhook not found, skipping notification")
        return False
    
    with open(webhook_file) as f:
        webhook_data = json.load(f)
        webhook_url = webhook_data.get("webhook_url")
    
    if not webhook_url:
        print("   ⚠️ Invalid webhook URL, skipping notification")
        return False
    
    # Build embed
    paper_list = []
    for i, paper in enumerate(papers[:3], 1):
        title = paper.get("title", "Unknown")[:100]
        paper_id = paper.get("id", "")
        score = paper.get("_agi_score", 0)
        keywords = paper.get("_agi_keywords", [])[:3]
        
        paper_list.append(f"**{i}. {title}**\n`{paper_id}` | AGI Score: {score:.1f}\nKeywords: {', '.join(keywords)}")
    
    description = "\n\n".join(paper_list)
    if len(papers) > 3:
        description += f"\n\n... and {len(papers) - 3} more papers"
    
    embed = {
        "title": "📄 AGI Paper Watcher",
        "description": description,
        "color": 0x9C27B0,  # Purple
        "footer": {
            "text": f"ONIZUKA AGI Co. | {datetime.now().strftime('%Y-%m-%d')}"
        }
    }
    
    payload = {
        "username": "AGI Paper Watcher 📄",
        "embeds": [embed]
    }
    
    # Send to Discord
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "AGI-Paper-Watcher/1.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 204:
                print("   ✅ Discord notification sent")
                return True
            else:
                print(f"   ⚠️ Discord returned status {response.status}")
                return False
    except urllib.error.URLError as e:
        print(f"   ⚠️ Discord notification failed: {e}")
        return False


def cmd_auto(args):
    """Automated weekly workflow."""
    print(f"🎋 AGI Paper Watcher - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # Step 1: Fetch papers
    print("\n📋 Step 1: Fetching papers...")
    papers = fetch_papers(limit=50)
    print(f"   Fetched {len(papers)} papers")
    
    # Step 2: Select AGI papers
    print("\n🎯 Step 2: Selecting AGI-relevant papers...")
    selected = select_weekly_papers(papers, count=args.count)
    print(f"   Selected {len(selected)} papers")
    
    for i, paper in enumerate(selected, 1):
        print(f"   {i}. [{paper.get('id')}] {paper.get('title')[:50]}...")
    
    # Step 3: Generate report
    print("\n📝 Step 3: Generating weekly report...")
    report = generate_weekly_report(selected)
    
    # Save report
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path(args.output_dir) / "agi-watcher"
    report_path = report_dir / f"{date_str}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"   Report saved: {report_path}")
    
    # Step 4: Generate images (optional)
    if not args.skip_images:
        print("\n🎨 Step 4: Generating visual explanations...")
        import subprocess
        
        gen_script = Path(__file__).parent.parent.parent / "nano-banana-2" / "scripts" / "generate.py"
        
        for i, paper in enumerate(selected, 1):
            title = paper.get("title", "")
            keywords = paper.get("_agi_keywords", [])
            
            prompt = f"""Infographic diagram explaining: {title}

Key concepts: {', '.join(keywords[:5])}

Style: Clean, modern, minimalist infographic with Japanese labels, suitable for social media, professional look, high contrast, easy to understand"""
            
            print(f"   [{i}/{len(selected)}] Generating for: {title[:40]}...")
            
            cmd = [
                sys.executable,
                str(gen_script),
                "--prompt", prompt,
                "--aspect-ratio", "16:9",
                "--resolution", "1K",
                "--save",
                "--output-dir", str(report_dir / "images"),
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                print(f"   ✅ Generated")
            except subprocess.CalledProcessError as e:
                print(f"   ⚠️ Failed: {e.stderr[:100]}")
    else:
        print("\n🎨 Step 4: Skipped (--skip-images)")
    
    # Step 5: Discord notification
    print("\n🔔 Step 5: Sending Discord notification...")
    if selected:
        send_discord_notification(selected, report_path)
    else:
        print("   No papers selected, skipping notification")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ AGI Paper Watcher Complete!")
    print(f"\n📄 Report: {report_path}")
    print(f"📊 Papers: {len(selected)}")


def main():
    parser = argparse.ArgumentParser(
        description="AGI Paper Watcher - Weekly AGI paper curator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # select command
    select_parser = subparsers.add_parser("select", help="Select weekly AGI papers")
    select_parser.add_argument("--count", "-n", type=int, default=2, help="Number of papers to select")
    select_parser.add_argument("--limit", "-l", type=int, default=50, help="Total papers to analyze")
    select_parser.set_defaults(func=cmd_select)
    
    # report command
    report_parser = subparsers.add_parser("report", help="Generate weekly report")
    report_parser.add_argument("--count", "-n", type=int, default=2, help="Number of papers")
    report_parser.add_argument("--limit", "-l", type=int, default=50, help="Total papers to analyze")
    report_parser.add_argument("--output", "-o", help="Output file path")
    report_parser.set_defaults(func=cmd_report)
    
    # filter command
    filter_parser = subparsers.add_parser("filter", help="Filter AGI-relevant papers")
    filter_parser.add_argument("--min-score", "-m", type=float, default=1.0, help="Minimum AGI score")
    filter_parser.add_argument("--count", "-n", type=int, default=10, help="Number of papers to show")
    filter_parser.add_argument("--limit", "-l", type=int, default=50, help="Total papers to analyze")
    filter_parser.set_defaults(func=cmd_filter)
    
    # auto command - automated workflow
    auto_parser = subparsers.add_parser("auto", help="Automated weekly workflow")
    auto_parser.add_argument("--count", "-n", type=int, default=2, help="Number of papers to select")
    auto_parser.add_argument("--output-dir", "-o", 
                            default="/config/.openclaw/workspace/memory/docs/papers",
                            help="Output directory")
    auto_parser.add_argument("--skip-images", action="store_true", help="Skip image generation")
    auto_parser.set_defaults(func=cmd_auto)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()

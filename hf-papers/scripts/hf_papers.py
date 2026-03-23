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


def cmd_generate(args):
    """Generate visual explanation image for a paper."""
    import subprocess
    
    paper = get_paper_by_id(args.paper_id)
    
    if not paper:
        print(f"Paper {args.paper_id} not found", file=sys.stderr)
        sys.exit(1)
    
    paper_info = paper.get("paper", paper)
    
    title = paper_info.get("title", "")
    summary = paper_info.get("ai_summary", paper_info.get("summary", ""))[:300]
    keywords = paper_info.get("ai_keywords", [])
    
    # Create image prompt
    prompt = f"""Infographic diagram explaining: {title}

Key concepts: {', '.join(keywords[:5])}

Style: Clean, modern, minimalist infographic with Japanese labels, suitable for social media, professional look, high contrast, easy to understand"""

    print(f"Generating image for: {title}")
    print(f"Prompt: {prompt[:100]}...")
    
    # Call nano-banana-2 generate script
    script_path = Path(__file__).parent.parent.parent / "nano-banana-2" / "scripts" / "generate.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--prompt", prompt,
        "--aspect-ratio", args.aspect_ratio,
        "--resolution", args.resolution,
    ]
    
    if args.save:
        cmd.extend(["--save", "--output-dir", args.output_dir])
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_post(args):
    """Generate formatted post content for Discord/X."""
    paper = get_paper_by_id(args.paper_id)
    
    if not paper:
        # If no paper_id, get top paper
        papers = fetch_papers(limit=1)
        if papers:
            paper = papers[0]
            paper_info = paper.get("paper", paper)
            args.paper_id = paper_info.get("id")
        else:
            print("No papers found", file=sys.stderr)
            sys.exit(1)
    
    paper_info = paper.get("paper", paper)
    
    title = paper_info.get("title", "")
    summary = paper_info.get("ai_summary", paper_info.get("summary", ""))
    keywords = paper_info.get("ai_keywords", [])
    upvotes = paper_info.get("upvotes", 0)
    arxiv_id = paper_info.get("id", "")
    github = paper_info.get("githubRepo", "")
    
    # Generate formatted post
    output = {
        "title": title,
        "arxiv_id": arxiv_id,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
        "hf_url": f"https://huggingface.co/papers/{arxiv_id}",
        "summary": summary,
        "keywords": keywords,
        "upvotes": upvotes,
        "github": github,
        "discord_message": f"""📜 **{title}**

{summary[:200]}...

🏷️ {', '.join(f'#{k}' for k in keywords[:5])}
⬆️ {upvotes} upvotes

🔗 https://huggingface.co/papers/{arxiv_id}""",
        "x_post": f"""{title}

{summary[:150]}...

🔗 huggingface.co/papers/{arxiv_id}

#AI #MachineLearning #{' '.join('#' + k for k in keywords[:3])}"""
    }
    
    if args.format == "json":
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(output["discord_message"])


def cmd_save(args):
    """Save paper(s) to Knowledge Base (memory/docs/papers/)."""
    papers_dir = Path(args.output_dir)
    papers_dir.mkdir(parents=True, exist_ok=True)
    
    if args.paper_id:
        # Save specific paper
        paper = get_paper_by_id(args.paper_id)
        if not paper:
            print(f"Paper {args.paper_id} not found", file=sys.stderr)
            sys.exit(1)
        papers_to_save = [paper]
    else:
        # Save top N papers
        papers_to_save = fetch_papers(limit=args.limit or 5)
    
    # Load template
    template_file = Path(__file__).parent.parent.parent.parent / "memory" / "docs" / "papers" / "paper-template.md"
    if template_file.exists():
        template = template_file.read_text()
        # Remove bibtex section with braces that cause format errors
        import re
        template = re.sub(
            r'## 📌 引用.*?---',
            '',
            template,
            flags=re.DOTALL
        )
    else:
        # Minimal template
        template = """---
title: 📄 {title}
---

# 📄 {title}

## メタデータ

| 項目 | 値 |
|------|-----|
| **arXiv ID** | {arxiv_id} |
| **タグ** | {tags} |

## リンク

- [arXiv](https://arxiv.org/abs/{arxiv_id})
- [HuggingFace Papers](https://huggingface.co/papers/{arxiv_id})

---

## 📝 要約

{summary}

---

## タグ

{tags_list}
"""
    
    saved_count = 0
    for paper_data in papers_to_save:
        paper = paper_data.get("paper", paper_data)
        arxiv_id = paper.get("id", "")
        title = paper.get("title", "")
        summary = paper.get("ai_summary", paper.get("summary", ""))
        keywords = paper.get("ai_keywords", [])
        authors = paper.get("authors", [])
        upvotes = paper.get("upvotes", 0)
        
        # Determine category folder
        if args.category:
            category = args.category
        else:
            # Auto-categorize based on keywords
            category = "general"
            keyword_str = " ".join(keywords).lower()
            if any(k in keyword_str for k in ["agi", "artificial general", "reasoning"]):
                category = "agi"
            elif any(k in keyword_str for k in ["llm", "language model", "gpt", "transformer"]):
                category = "llm"
            elif any(k in keyword_str for k in ["vision", "image", "multimodal"]):
                category = "vision"
            elif any(k in keyword_str for k in ["rl", "reinforcement", "agent"]):
                category = "rl"
        
        # Create category folder
        category_dir = papers_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50]
        filename = f"{arxiv_id}.md"
        filepath = category_dir / filename
        
        # Fill template
        content = template.format(
            title=title,
            arxiv_id=arxiv_id,
            published_date=paper.get("published", "N/A"),
            categories=category,
            tags=", ".join(keywords[:5]),
            summary=summary,
            background="",
            contributions="",
            technical_details="",
            significance="",
            related_papers="",
            authors=", ".join(a.get("name", str(a)) for a in authors) if authors else "N/A",
            year=arxiv_id[:2] if arxiv_id else "26",
            tags_list=" ".join(f"#{k}" for k in keywords[:5])
        )
        
        # Write file
        filepath.write_text(content)
        saved_count += 1
        print(f"✅ Saved: {category}/{filename}")
        print(f"   {title}")
    
    # Update index
    index_file = papers_dir / "index.md"
    if args.update_index:
        update_papers_index(papers_dir)
        print(f"\n📚 Updated index: {index_file}")
    
    print(f"\n✅ Saved {saved_count} papers to {papers_dir}")


def update_papers_index(papers_dir: Path):
    """Update the papers index with all saved papers."""
    index_content = """---
layout: doc
---

# 📚 Papers Knowledge Base

AGI関連論文の図解・解説を蓄積するナレッジベース。

## カテゴリ

"""
    
    categories = {}
    for category_dir in papers_dir.iterdir():
        if category_dir.is_dir() and category_dir.name not in ["images", "category"]:
            papers = list(category_dir.glob("*.md"))
            if papers:
                categories[category_dir.name] = papers
    
    for category, papers in sorted(categories.items()):
        index_content += f"### {category.upper()}\n\n"
        for paper_file in papers:
            # Read title from file
            content = paper_file.read_text()
            title = ""
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].replace("📄 ", "")
                    break
            
            index_content += f"- [{title or paper_file.stem}](/{category}/{paper_file.stem})\n"
        index_content += "\n"
    
    index_content += """---

## 統計

- 総論文数: {total}
- カテゴリ数: {categories}

---

*このナレッジベースは自動的に更新されます。*
""".format(total=sum(len(p) for p in categories.values()), categories=len(categories))
    
    (papers_dir / "index.md").write_text(index_content)


def cmd_auto_post(args):
    """Automated workflow: fetch top paper, generate image, post to X/Discord."""
    import subprocess
    
    print("🎋 HF Papers Auto-Post Workflow")
    print("=" * 40)
    
    # Step 1: Get top paper
    print("\n📋 Step 1: Fetching top paper...")
    papers = fetch_papers(limit=1)
    if not papers:
        print("❌ No papers found", file=sys.stderr)
        sys.exit(1)
    
    paper = papers[0]
    paper_info = paper.get("paper", paper)
    arxiv_id = paper_info.get("id", "")
    title = paper_info.get("title", "")
    
    print(f"✅ Selected: [{arxiv_id}] {title}")
    
    # Step 2: Generate image
    if not args.skip_image:
        print("\n🎨 Step 2: Generating visual explanation...")
        gen_script = Path(__file__).parent.parent.parent / "nano-banana-2" / "scripts" / "generate.py"
        
        keywords = paper_info.get("ai_keywords", [])
        prompt = f"""Infographic diagram explaining: {title}

Key concepts: {', '.join(keywords[:5])}

Style: Clean, modern, minimalist infographic with Japanese labels, suitable for social media, professional look, high contrast, easy to understand"""
        
        gen_cmd = [
            sys.executable,
            str(gen_script),
            "--prompt", prompt,
            "--aspect-ratio", args.aspect_ratio,
            "--resolution", args.resolution,
            "--save",
            "--output-dir", args.output_dir,
        ]
        
        try:
            result = subprocess.run(gen_cmd, capture_output=True, text=True, check=True)
            print("✅ Image generated")
            # Extract image URL from output
            for line in result.stdout.split("\n"):
                if "http" in line:
                    print(f"   URL: {line.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Image generation failed: {e.stderr}")
            if not args.continue_on_error:
                sys.exit(1)
    else:
        print("\n🎨 Step 2: Skipped ( --skip-image )")
    
    # Step 3: Generate post content
    print("\n📝 Step 3: Generating post content...")
    summary = paper_info.get("ai_summary", paper_info.get("summary", ""))
    keywords = paper_info.get("ai_keywords", [])
    upvotes = paper_info.get("upvotes", 0)
    
    x_post = f"""{title}

{summary[:150]}...

🔗 huggingface.co/papers/{arxiv_id}

#ONIZUKA_AGI #AI #MachineLearning"""
    
    discord_message = f"""📜 **{title}**

{summary[:200]}...

🏷️ {', '.join(f'#{k}' for k in keywords[:5])}
⬆️ {upvotes} upvotes

🔗 https://huggingface.co/papers/{arxiv_id}"""
    
    print("✅ Content generated")
    
    # Step 4: Post to X
    if args.post_x:
        print("\n🐦 Step 4: Posting to X...")
        x_script = Path(__file__).parent.parent.parent / "x-write" / "scripts" / "x_write.py"
        
        x_cmd = [sys.executable, str(x_script), "post", x_post]
        
        try:
            result = subprocess.run(x_cmd, capture_output=True, text=True, check=True)
            print("✅ Posted to X")
            print(f"   {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ X post failed: {e.stderr}")
            if not args.continue_on_error:
                sys.exit(1)
    else:
        print("\n🐦 Step 4: Skipped ( use --post-x to enable )")
    
    # Step 5: Post to Discord
    if args.post_discord:
        print("\n💬 Step 5: Posting to Discord...")
        # Discord posting via webhook
        webhook_file = Path(__file__).parent.parent.parent.parent / "data" / "x" / "x-discord-webhook.json"
        
        if webhook_file.exists():
            with open(webhook_file) as f:
                webhook_data = json.load(f)
            webhook_url = webhook_data.get("webhook_url", "")
            
            if webhook_url:
                import urllib.request
                import urllib.parse
                
                payload = {
                    "content": discord_message,
                    "username": "ONIZUKA AGI 🎋"
                }
                
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "ONIZUKA-AGI-Paper-Watcher/1.0"
                    }
                )
                
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        print("✅ Posted to Discord")
                except Exception as e:
                    print(f"⚠️ Discord post failed: {e}")
                    if not args.continue_on_error:
                        sys.exit(1)
            else:
                print("⚠️ Webhook URL not found in config")
        else:
            print(f"⚠️ Webhook config not found: {webhook_file}")
    else:
        print("\n💬 Step 5: Skipped ( use --post-discord to enable )")
    
    # Summary
    print("\n" + "=" * 40)
    print("✅ Auto-Post Workflow Complete!")
    print(f"\nPaper: {title}")
    print(f"arXiv: {arxiv_id}")
    print(f"\n--- X Post ---\n{x_post}")
    print(f"\n--- Discord Message ---\n{discord_message}")


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
    
    # generate command - actually generate image
    gen_parser = subparsers.add_parser("generate", help="Generate visual explanation image")
    gen_parser.add_argument("paper_id", help="arXiv paper ID")
    gen_parser.add_argument("--aspect-ratio", "-a", default="16:9",
                           choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"])
    gen_parser.add_argument("--resolution", "-r", default="1K",
                           choices=["0.5K", "1K", "2K", "4K"])
    gen_parser.add_argument("--save", action="store_true", help="Save images locally")
    gen_parser.add_argument("--output-dir", "-o", default="output/hf-papers")
    gen_parser.set_defaults(func=cmd_generate)
    
    # post command - generate formatted post content
    post_parser = subparsers.add_parser("post", help="Generate formatted post content")
    post_parser.add_argument("paper_id", nargs="?", help="arXiv paper ID (default: top paper)")
    post_parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    post_parser.set_defaults(func=cmd_post)
    
    # auto-post command - automated workflow
    auto_parser = subparsers.add_parser("auto-post", help="Auto-post workflow: fetch, generate, post")
    auto_parser.add_argument("--aspect-ratio", "-a", default="16:9",
                            choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"])
    auto_parser.add_argument("--resolution", "-r", default="1K",
                            choices=["0.5K", "1K", "2K", "4K"])
    auto_parser.add_argument("--output-dir", "-o", default="output/hf-papers")
    auto_parser.add_argument("--skip-image", action="store_true", help="Skip image generation")
    auto_parser.add_argument("--post-x", action="store_true", help="Post to X/Twitter")
    auto_parser.add_argument("--post-discord", action="store_true", help="Post to Discord")
    auto_parser.add_argument("--continue-on-error", action="store_true", help="Continue even if a step fails")
    auto_parser.set_defaults(func=cmd_auto_post)
    
    # save command - save papers to Knowledge Base
    save_parser = subparsers.add_parser("save", help="Save papers to Knowledge Base")
    save_parser.add_argument("paper_id", nargs="?", help="arXiv paper ID (default: save top papers)")
    save_parser.add_argument("--limit", "-n", type=int, default=5, help="Number of papers to save")
    save_parser.add_argument("--output-dir", "-o", 
                            default="/config/.openclaw/workspace/memory/docs/papers",
                            help="Output directory")
    save_parser.add_argument("--category", "-c", help="Force category (agi, llm, vision, rl, general)")
    save_parser.add_argument("--update-index", action="store_true", help="Update papers index")
    save_parser.set_defaults(func=cmd_save)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()

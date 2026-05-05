#!/usr/bin/env python3
"""
arXiv Papers - Fetch AI/ML papers from arXiv API

Provides utilities for fetching and processing papers from arXiv.
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# arXiv API endpoint
ARXIV_API = "http://export.arxiv.org/api/query"

# Cache directory
CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "arxiv-papers"
CACHE_EXPIRY_HOURS = 6  # Cache expires after 6 hours

# XML namespaces
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_arxiv_papers(
    query: str = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL",
    start: int = 0,
    max_results: int = 10,
    use_cache: bool = True,
) -> list[dict]:
    """Fetch papers from arXiv API."""
    
    # Check cache
    cache_file = CACHE_DIR / f"papers_{hash(query)}_{start}_{max_results}.json"
    if use_cache and cache_file.exists():
        cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if cache_age < CACHE_EXPIRY_HOURS * 3600:
            with open(cache_file, "r") as f:
                return json.load(f)
    
    # Build URL (properly encoded)
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urlencode(params)}"
    
    request = Request(
        url,
        headers={"User-Agent": "ONIZUKA-AGI-arXiv-Papers/1.0"}
    )
    
    try:
        with urlopen(request, timeout=60) as response:
            data = response.read().decode("utf-8")
    except (HTTPError, URLError) as e:
        print(f"Error fetching arXiv papers: {e}", file=sys.stderr)
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        return []
    
    # Parse XML
    papers = parse_arxiv_response(data)
    
    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(papers, f, indent=2)
    
    return papers


def parse_arxiv_response(xml_data: str) -> list[dict]:
    """Parse arXiv API XML response."""
    papers = []
    root = ET.fromstring(xml_data)
    
    for entry in root.findall("atom:entry", NS):
        paper = {
            "id": entry.find("atom:id", NS).text.split("/")[-1],
            "title": entry.find("atom:title", NS).text.strip().replace("\n", " "),
            "summary": entry.find("atom:summary", NS).text.strip().replace("\n", " "),
            "authors": [a.find("atom:name", NS).text for a in entry.findall("atom:author", NS)],
            "published": entry.find("atom:published", NS).text,
            "updated": entry.find("atom:updated", NS).text,
            "link": entry.find("atom:id", NS).text,
            "pdf_link": None,
            "categories": [],
        }
        
        # Get PDF link
        for link in entry.findall("atom:link", NS):
            if link.get("title") == "pdf":
                paper["pdf_link"] = link.get("href")
        
        # Get categories
        for cat in entry.findall("atom:category", NS):
            paper["categories"].append(cat.get("term"))
        
        papers.append(paper)
    
    return papers


def format_paper(paper: dict, brief: bool = False) -> str:
    """Format paper for display."""
    if brief:
        return f"[{paper['id']}] {paper['title'][:60]}..."
    
    lines = [
        f"**{paper['title']}**",
        f"arXiv: {paper['id']}",
        f"Published: {paper['published'][:10]}",
        "",
        f"**Authors:** {', '.join(paper['authors'][:5])}{'...' if len(paper['authors']) > 5 else ''}",
        "",
        f"**Abstract:** {paper['summary'][:300]}...",
        "",
        f"**Categories:** {', '.join(paper['categories'])}",
        "",
        f"**Links:**",
        f"- arXiv: {paper['link']}",
    ]
    
    if paper.get("pdf_link"):
        lines.append(f"- PDF: {paper['pdf_link']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="arXiv Papers Fetcher")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch latest papers")
    fetch_parser.add_argument("--query", "-q", default="cat:cs.AI OR cat:cs.LG", help="Search query")
    fetch_parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    fetch_parser.add_argument("--brief", "-b", action="store_true", help="Brief output")
    fetch_parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    
    # get command
    get_parser = subparsers.add_parser("get", help="Get paper by ID")
    get_parser.add_argument("id", help="arXiv paper ID (e.g., 2301.07065)")
    get_parser.add_argument("--brief", "-b", action="store_true", help="Brief output")
    
    args = parser.parse_args()
    
    if args.command == "fetch":
        papers = fetch_arxiv_papers(query=args.query, max_results=args.limit)
        
        if args.json:
            print(json.dumps(papers, indent=2))
        else:
            for paper in papers:
                print(format_paper(paper, brief=args.brief))
                print("\n" + "-" * 40 + "\n")
        
        print(f"Fetched {len(papers)} papers")
    
    elif args.command == "get":
        papers = fetch_arxiv_papers(query=f"id:{args.id}", max_results=1)
        
        if papers:
            print(format_paper(papers[0], brief=args.brief))
        else:
            print(f"Paper not found: {args.id}", file=sys.stderr)
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

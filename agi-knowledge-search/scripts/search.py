#!/usr/bin/env python3
"""
AGI Knowledge Search - Full-text and semantic search across knowledge base.

Usage:
    python search.py "query" [--type TYPE] [--date-after DATE] [--limit N] [--semantic]
"""

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Knowledge base paths
MEMORY_DOCS = Path("/config/.openclaw/workspace/memory/docs")
DATA_PAPERS = Path("/config/.openclaw/workspace/data/papers")
DATA_X = Path("/config/.openclaw/workspace/data/x")
CACHE_DIR = Path("/config/.openclaw/workspace/data/embeddings-cache")


def get_gemini_api_key() -> Optional[str]:
    """Get Gemini API key from environment or file."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    key_file = Path("/config/.openclaw/workspace/gemini-api-key.txt")
    if key_file.exists():
        content = key_file.read_text().strip()
        if content.startswith("GEMINI_API_KEY="):
            return content.split("=", 1)[1]
        return content
    return None


def get_embedding(text: str, api_key: str) -> Optional[list[float]]:
    """Get embedding for text using Gemini API."""
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:max_chars]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text}]
        }
    }

    try:
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("embedding", {}).get("values", [])
    except HTTPError as e:
        print(f"⚠️ Embedding API error: {e.code} - {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return None


def get_query_embedding(query: str, api_key: str) -> Optional[list[float]]:
    """Get embedding for search query."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": query}]
        }
    }

    try:
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("embedding", {}).get("values", [])
    except HTTPError as e:
        print(f"⚠️ Query embedding API error: {e.code} - {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"⚠️ Query embedding error: {e}")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def get_cached_embedding(file_path: Path, content_hash: str) -> Optional[list[float]]:
    """Get cached embedding if available."""
    cache_file = CACHE_DIR / f"{file_path.stem}_{content_hash[:8]}.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            return data.get("embedding")
        except Exception:
            pass
    return None


def save_cached_embedding(file_path: Path, content_hash: str, embedding: list[float]):
    """Save embedding to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{file_path.stem}_{content_hash[:8]}.json"
    cache_file.write_text(json.dumps({"embedding": embedding, "hash": content_hash}))


def find_markdown_files(base_path: Path) -> list[Path]:
    """Find all markdown files in a directory, excluding node_modules."""
    if not base_path.exists():
        return []
    files = []
    for f in base_path.rglob("*.md"):
        if "node_modules" in str(f) or ".vitepress/dist" in str(f) or ".vitepress/cache" in str(f):
            continue
        files.append(f)
    return files


def extract_metadata(content: str) -> dict:
    """Extract frontmatter metadata from markdown."""
    metadata = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
    return metadata


def extract_text(content: str) -> str:
    """Extract plain text from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"`[^`]+`", "", content)
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
    content = re.sub(r"^#+\s*", "", content, flags=re.MULTILINE)
    content = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", content)
    content = " ".join(content.split())

    return content


def get_file_type(file_path: Path) -> str:
    """Determine the type of file based on path."""
    path_str = str(file_path)
    if "memory/docs" in path_str:
        return "report"
    elif "data/papers" in path_str:
        return "paper"
    elif "data/x" in path_str:
        return "post"
    return "other"


def extract_snippet(text: str, query: str, context_chars: int = 100) -> str:
    """Extract a snippet around the query match."""
    query_lower = query.lower()
    text_lower = text.lower()

    pos = text_lower.find(query_lower)
    if pos == -1:
        return text[:context_chars * 2] + "..." if len(text) > context_chars * 2 else text

    start = max(0, pos - context_chars)
    end = min(len(text), pos + len(query) + context_chars)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def search_in_file(file_path: Path, query: str, args: argparse.Namespace) -> Optional[dict]:
    """Search for query in a single file (full-text)."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    metadata = extract_metadata(content)
    plain_text = extract_text(content)

    # Check date filter
    if args.date_after:
        try:
            filter_date = datetime.strptime(args.date_after, "%Y-%m-%d")
            date_str = metadata.get("date", metadata.get("title", ""))
            if date_str:
                match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
                if match:
                    file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                    if file_date < filter_date:
                        return None
        except ValueError:
            pass

    # Check type filter
    if args.type:
        file_type = get_file_type(file_path)
        if file_type != args.type:
            return None

    # Search in content (case-insensitive)
    query_lower = query.lower()
    if query_lower not in plain_text.lower():
        return None

    score = plain_text.lower().count(query_lower)
    snippet = extract_snippet(plain_text, query)

    return {
        "title": metadata.get("title", file_path.stem),
        "source": get_file_type(file_path),
        "date": metadata.get("date", ""),
        "path": str(file_path.relative_to(Path("/config/.openclaw/workspace"))),
        "snippet": snippet,
        "score": score,
    }


def semantic_search(query: str, all_files: list[Path], args: argparse.Namespace, api_key: str) -> list[dict]:
    """Perform semantic search using embeddings."""
    query_embedding = get_query_embedding(query, api_key)
    if not query_embedding:
        print("⚠️ Failed to get query embedding")
        return []

    print(f"🧠 Performing semantic search...")
    results = []

    for file_path in all_files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        metadata = extract_metadata(content)
        plain_text = extract_text(content)

        # Check type filter
        if args.type:
            file_type = get_file_type(file_path)
            if file_type != args.type:
                continue

        # Check date filter
        if args.date_after:
            try:
                filter_date = datetime.strptime(args.date_after, "%Y-%m-%d")
                date_str = metadata.get("date", metadata.get("title", ""))
                if date_str:
                    match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
                    if match:
                        file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                        if file_date < filter_date:
                            continue
            except ValueError:
                pass

        # Get or create embedding
        content_hash = hashlib.md5(plain_text.encode()).hexdigest()
        embedding = get_cached_embedding(file_path, content_hash)

        if not embedding:
            embedding = get_embedding(plain_text[:2000], api_key)
            if embedding:
                save_cached_embedding(file_path, content_hash, embedding)

        if embedding:
            similarity = cosine_similarity(query_embedding, embedding)
            if similarity > 0.3:
                snippet = extract_snippet(plain_text, query)
                results.append({
                    "title": metadata.get("title", file_path.stem),
                    "source": get_file_type(file_path),
                    "date": metadata.get("date", ""),
                    "path": str(file_path.relative_to(Path("/config/.openclaw/workspace"))),
                    "snippet": snippet,
                    "score": round(similarity * 100, 1),
                    "semantic": True,
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def main():
    parser = argparse.ArgumentParser(description="AGI Knowledge Search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--type", choices=["paper", "report", "post"], help="Filter by type")
    parser.add_argument("--date-after", help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=10, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--semantic", action="store_true", help="Use semantic search with embeddings")

    args = parser.parse_args()

    # Collect all markdown files
    all_files = []
    all_files.extend(find_markdown_files(MEMORY_DOCS))
    all_files.extend(find_markdown_files(DATA_PAPERS))
    all_files.extend(find_markdown_files(DATA_X))

    # Search
    if args.semantic:
        api_key = get_gemini_api_key()
        if not api_key:
            print("⚠️ No Gemini API key found, falling back to full-text search")
            results = []
        else:
            results = semantic_search(args.query, all_files, args, api_key)

        if not results:
            print("ℹ️ Falling back to full-text search...")
            for file_path in all_files:
                result = search_in_file(file_path, args.query, args)
                if result:
                    results.append(result)
            results.sort(key=lambda x: x["score"], reverse=True)
    else:
        results = []
        for file_path in all_files:
            result = search_in_file(file_path, args.query, args)
            if result:
                results.append(result)
        results.sort(key=lambda x: x["score"], reverse=True)

    # Limit results
    results = results[: args.limit]

    # Output
    if args.json:
        output = {"query": args.query, "total": len(results), "results": results}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        mode = "🧠 Semantic" if args.semantic else "🔍"
        print(f"\n{mode} Search: \"{args.query}\"")
        print(f"📊 Found: {len(results)} results\n")
        for i, r in enumerate(results, 1):
            semantic_mark = " 🧠" if r.get("semantic") else ""
            print(f"### {i}. {r['title']}{semantic_mark}")
            print(f"   Type: {r['source']} | Score: {r['score']}")
            print(f"   Path: {r['path']}")
            print(f"   {r['snippet']}\n")


if __name__ == "__main__":
    main()

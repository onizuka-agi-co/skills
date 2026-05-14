#!/usr/bin/env python3
"""
AGI Knowledge Search - Index Builder

Build FAISS index from markdown files for fast semantic search.

Usage:
    python index.py [--rebuild]

Options:
    --rebuild    Force rebuild all embeddings
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Paths
WORKSPACE = Path("/config/.openclaw/workspace")
MEMORY_DOCS = WORKSPACE / "memory/docs"
DATA_PAPERS = WORKSPACE / "data/papers"
DATA_X = WORKSPACE / "data/x"
CACHE_DIR = WORKSPACE / "data/embeddings"
INDEX_DIR = WORKSPACE / "data/index"

# Files to track indexed content
METADATA_FILE = INDEX_DIR / "metadata.json"
FAISS_INDEX_FILE = INDEX_DIR / "knowledge.faiss"


def get_gemini_api_key() -> Optional[str]:
    """Get Gemini API key from environment or file."""
    # Try environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key

    # Try file
    key_file = WORKSPACE / "gemini-api-key.txt"
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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
    payload = {
        "model": "models/gemini-embedding-001",
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
        if e.code == 429:
            return "rate_limited"
        print(f"⚠️ API error: {e.code} - {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return None


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
    import re
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
    import re
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


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index for AGI knowledge base")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild all embeddings")
    args = parser.parse_args()

    api_key = get_gemini_api_key()
    if not api_key:
        print("❌ No Gemini API key found")
        print("   Set GEMINI_API_KEY environment variable or create gemini-api-key.txt")
        sys.exit(1)

    # Create directories
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all markdown files
    all_files = []
    all_files.extend(find_markdown_files(MEMORY_DOCS))
    all_files.extend(find_markdown_files(DATA_PAPERS))
    all_files.extend(find_markdown_files(DATA_X))

    print(f"📚 Found {len(all_files)} markdown files")

    # Load existing metadata
    metadata = {}
    if METADATA_FILE.exists() and not args.rebuild:
        try:
            metadata = json.loads(METADATA_FILE.read_text())
        except Exception:
            pass

    # Process files
    embeddings = []
    ids = []
    file_metadata = []

    for i, file_path in enumerate(all_files):
        print(f"📄 [{i+1}/{len(all_files)}] Processing {file_path.name}...", end=" ")

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Read error: {e}")
            continue

        file_meta = extract_metadata(content)
        plain_text = extract_text(content)
        content_hash = hashlib.md5(plain_text.encode()).hexdigest()

        # Check if embedding exists and content hasn't changed
        file_key = str(file_path.relative_to(WORKSPACE))
        cached = metadata.get(file_key, {})

        if not args.rebuild and cached.get("hash") == content_hash and cached.get("embedding"):
            print("✓ (cached)")
            embedding = cached["embedding"]
        else:
            # Generate new embedding with retry
            for attempt in range(3):
                embedding = get_embedding(plain_text[:2000], api_key)
                if embedding == "rate_limited":
                    wait = 60 * (attempt + 1)
                    print(f"⏳ Rate limited, waiting {wait}s... (attempt {attempt+1}/3)")
                    time.sleep(wait)
                    continue
                if embedding:
                    break
            if not embedding or embedding == "rate_limited":
                print("❌ Embedding failed (rate limit)")
                continue
            print("✓ (new)")

        # Store embedding and metadata
        embeddings.append(embedding)
        ids.append(i)
        file_metadata.append({
            "id": i,
            "path": file_key,
            "title": file_meta.get("title", file_path.stem),
            "type": get_file_type(file_path),
            "date": file_meta.get("date", ""),
            "hash": content_hash,
            "embedding": embedding,
        })

        # Update metadata
        metadata[file_key] = {
            "hash": content_hash,
            "embedding": embedding,
            "title": file_meta.get("title", file_path.stem),
            "type": get_file_type(file_path),
            "date": file_meta.get("date", ""),
        }

    if not embeddings:
        print("❌ No embeddings generated")
        sys.exit(1)

    # Build FAISS index
    print(f"\n🔨 Building FAISS index with {len(embeddings)} vectors...")

    try:
        import faiss
        import numpy as np

        # Convert to numpy array
        dim = len(embeddings[0])
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Create index
        index = faiss.IndexFlatIP(dim)  # Inner product for cosine similarity (after normalization)

        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings_array)

        # Add vectors to index
        index.add(embeddings_array)

        # Save index
        faiss.write_index(index, str(FAISS_INDEX_FILE))
        print(f"✅ Saved index to {FAISS_INDEX_FILE}")

        # Save metadata
        # Remove embeddings from metadata to save space (they're in FAISS)
        for key in list(metadata.keys()):
            val = metadata[key]
            if isinstance(val, dict) and "embedding" in val:
                del val["embedding"]

        METADATA_FILE.write_text(json.dumps({
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "total_documents": len(file_metadata),
            "dimension": dim,
            "files": metadata,
        }, indent=2, ensure_ascii=False))
        print(f"✅ Saved metadata to {METADATA_FILE}")

        print(f"\n📊 Index Statistics:")
        print(f"   Documents: {len(file_metadata)}")
        print(f"   Dimension: {dim}")
        print(f"   Index size: {FAISS_INDEX_FILE.stat().st_size / 1024:.1f} KB")

    except ImportError:
        print("⚠️ FAISS not installed, saving embeddings to JSON instead")
        # Save as JSON fallback
        INDEX_DIR.joinpath("embeddings.json").write_text(json.dumps({
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "documents": file_metadata,
        }, indent=2, ensure_ascii=False))
        print(f"✅ Saved embeddings to {INDEX_DIR}/embeddings.json")


if __name__ == "__main__":
    main()

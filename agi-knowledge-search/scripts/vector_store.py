#!/usr/bin/env python3
"""
AGI Knowledge Vector Store Manager

Manage the FAISS vector store: rebuild, stats, search, add, remove.

Usage:
    python vector_store.py stats
    python vector_store.py search "query text" [--top-k 5]
    python vector_store.py rebuild [--full]
    python vector_store.py add <file_path>
    python vector_store.py remove <file_path>
    python vector_store.py export [--format json|csv]
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import faiss
import numpy as np

WORKSPACE = Path("/config/.openclaw/workspace")
MEMORY_DOCS = WORKSPACE / "memory/docs"
DATA_PAPERS = WORKSPACE / "data/papers"
DATA_X = WORKSPACE / "data/x"
INDEX_DIR = WORKSPACE / "data/index"
FAISS_INDEX_FILE = INDEX_DIR / "knowledge.faiss"
METADATA_FILE = INDEX_DIR / "metadata.json"
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072


def get_api_key() -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key
    key_file = WORKSPACE / "gemini-api-key.txt"
    if key_file.exists():
        content = key_file.read_text().strip()
        if content.startswith("GEMINI_API_KEY="):
            return content.split("=", 1)[1]
        return content
    return None


def get_embedding(text: str, api_key: str) -> Optional[list[float]]:
    if len(text) > 8000:
        text = text[:8000]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={api_key}"
    payload = {"model": EMBEDDING_MODEL, "content": {"parts": [{"text": text}]}}
    try:
        req = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode()).get("embedding", {}).get("values", [])
    except HTTPError as e:
        if e.code == 429:
            return "rate_limited"
        print(f"⚠️ API error: {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️ Error: {e}", file=sys.stderr)
        return None


def extract_text(content: str) -> str:
    import re
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
    content = re.sub(r"^#+\s*", "", content, flags=re.MULTILINE)
    return " ".join(content.split())


def load_store():
    """Load existing FAISS index and metadata."""
    if not FAISS_INDEX_FILE.exists() or not METADATA_FILE.exists():
        return None, None
    index = faiss.read_index(str(FAISS_INDEX_FILE))
    meta = json.loads(METADATA_FILE.read_text())
    return index, meta


def save_store(index, meta):
    """Save FAISS index and metadata."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX_FILE))
    # Strip embeddings from metadata before saving
    clean_meta = {"version": meta.get("version", "2.0")}
    for k, v in meta.items():
        if k in ("version",):
            continue
        if isinstance(v, dict):
            clean_meta[k] = {kk: vv for kk, vv in v.items() if kk != "embedding"}
        else:
            clean_meta[k] = v
    clean_meta["total_documents"] = index.ntotal
    clean_meta["dimension"] = index.d
    clean_meta["updated"] = datetime.now().isoformat()
    METADATA_FILE.write_text(json.dumps(clean_meta, indent=2, ensure_ascii=False))


def cmd_stats(args):
    index, meta = load_store()
    if index is None:
        print("❌ No vector store found. Run `rebuild` first.")
        return
    files_meta = meta.get("files", {})
    types = {}
    for v in files_meta.values():
        if isinstance(v, dict):
            t = v.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
    print(f"📊 Vector Store Statistics")
    print(f"   Documents: {index.ntotal}")
    print(f"   Dimension: {index.d}")
    print(f"   Index size: {FAISS_INDEX_FILE.stat().st_size / 1024:.1f} KB")
    print(f"   Updated: {meta.get('updated', 'unknown')}")
    print(f"   By type: {types}")


def cmd_search(args):
    api_key = get_api_key()
    if not api_key:
        print("❌ No API key"); return
    index, meta = load_store()
    if index is None:
        print("❌ No vector store"); return

    query_embedding = get_embedding(args.query, api_key)
    if not query_embedding or query_embedding == "rate_limited":
        print("❌ Failed to get embedding"); return

    q = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(q)
    scores, ids = index.search(q, args.top_k)

    files_meta = meta.get("files", {})
    file_list = list(files_meta.items())

    print(f"\n🔍 Results for: \"{args.query}\"\n")
    for i, (score, idx) in enumerate(zip(scores[0], ids[0])):
        if idx < 0 or idx >= len(file_list):
            continue
        path, info = file_list[idx]
        print(f"  {i+1}. [{info.get('type','?')}] {info.get('title', path)} (score: {score:.4f})")
        print(f"     {path}\n")


def cmd_rebuild(args):
    from pathlib import Path
    api_key = get_api_key()
    if not api_key:
        print("❌ No API key"); return

    all_files = []
    for base in [MEMORY_DOCS, DATA_PAPERS, DATA_X]:
        if base.exists():
            for f in base.rglob("*.md"):
                if "node_modules" in str(f) or ".vitepress/dist" in str(f) or ".vitepress/cache" in str(f):
                    continue
                all_files.append(f)

    print(f"📚 Processing {len(all_files)} files...")
    embeddings = []
    meta = {"version": "2.0", "files": {}}

    for i, fp in enumerate(all_files):
        print(f"  [{i+1}/{len(all_files)}] {fp.name}...", end=" ")
        try:
            text = extract_text(fp.read_text(encoding="utf-8"))
        except:
            print("skip"); continue

        for attempt in range(3):
            emb = get_embedding(text[:2000], api_key)
            if emb == "rate_limited":
                time.sleep(60 * (attempt + 1)); continue
            break

        if not emb or emb == "rate_limited":
            print("❌"); continue
        print("✓")

        embeddings.append(emb)
        file_key = str(fp.relative_to(WORKSPACE))
        meta["files"][file_key] = {
            "title": fp.stem,
            "type": "report" if "memory/docs" in str(fp) else "paper" if "data/papers" in str(fp) else "post",
            "hash": hashlib.md5(text.encode()).hexdigest(),
            "index": len(embeddings) - 1,
        }

    if not embeddings:
        print("❌ No embeddings"); return

    arr = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(arr)
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(arr)
    save_store(index, meta)
    print(f"\n✅ Rebuilt: {index.ntotal} vectors")


def cmd_export(args):
    index, meta = load_store()
    if index is None:
        print("❌ No store"); return
    fmt = args.format or "json"
    if fmt == "json":
        print(json.dumps(meta, indent=2, ensure_ascii=False))
    elif fmt == "csv":
        print("path,title,type,hash")
        for path, info in meta.get("files", {}).items():
            print(f"{path},{info.get('title','')},{info.get('type','')},{info.get('hash','')}")


def main():
    parser = argparse.ArgumentParser(description="AGI Knowledge Vector Store Manager")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats")
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--top-k", type=int, default=5)
    sub.add_parser("rebuild")
    e = sub.add_parser("export"); e.add_argument("--format", choices=["json", "csv"], default="json")

    args = parser.parse_args()
    if args.command == "stats": cmd_stats(args)
    elif args.command == "search": cmd_search(args)
    elif args.command == "rebuild": cmd_rebuild(args)
    elif args.command == "export": cmd_export(args)
    else: parser.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AGI Knowledge Search API - Lightweight HTTP server.

Provides REST API for searching the AGI knowledge base.

Usage:
    python api.py [--port 8420] [--host 0.0.0.0]

Endpoints:
    GET  /search?q=QUERY&type=TYPE&limit=N&semantic=0|1
    GET  /status
    GET  /stats
"""

import argparse
import json
import os
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add scripts dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from search import (
    find_markdown_files, search_in_file, semantic_search,
    MEMORY_DOCS, DATA_PAPERS, DATA_X
)

WORKSPACE = Path("/config/.openclaw/workspace")


class SearchHandler(BaseHTTPRequestHandler):
    """HTTP request handler for search API."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys.stderr.write(f"[{ts}] {args[0]}\n")

    def _send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _send_error(self, message, status=400):
        """Send error response."""
        self._send_json({"error": message}, status)

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/search":
            self._handle_search(params)
        elif parsed.path == "/status":
            self._handle_status()
        elif parsed.path == "/stats":
            self._handle_stats()
        else:
            self._send_error("Not found", 404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle_search(self, params):
        """Handle search requests."""
        query = params.get("q", [None])[0]
        if not query:
            self._send_error("Missing query parameter 'q'")
            return

        limit = int(params.get("limit", ["10"])[0])
        search_type = params.get("type", [None])[0]
        use_semantic = params.get("semantic", ["0"])[0] == "1"

        # Collect files
        all_files = []
        all_files.extend(find_markdown_files(MEMORY_DOCS))
        all_files.extend(find_markdown_files(DATA_PAPERS))
        all_files.extend(find_markdown_files(DATA_X))

        # Build args namespace
        import argparse
        args = argparse.Namespace(
            type=search_type,
            date_after=None,
            limit=limit,
        )

        if use_semantic:
            from search import get_gemini_api_key
            api_key = get_gemini_api_key()
            if api_key:
                results = semantic_search(query, all_files, args, api_key)
            else:
                results = []
        else:
            results = []
            for f in all_files:
                r = search_in_file(f, query, args)
                if r:
                    results.append(r)
            results.sort(key=lambda x: x["score"], reverse=True)

        results = results[:limit]

        self._send_json({
            "query": query,
            "total": len(results),
            "semantic": use_semantic,
            "results": results,
        })

    def _handle_status(self):
        """Handle status requests."""
        self._send_json({
            "status": "ok",
            "service": "agi-knowledge-search-api",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        })

    def _handle_stats(self):
        """Handle stats requests."""
        docs_files = find_markdown_files(MEMORY_DOCS)
        papers_files = find_markdown_files(DATA_PAPERS)
        x_files = find_markdown_files(DATA_X)

        index_dir = WORKSPACE / "data/index"
        faiss_file = index_dir / "knowledge.faiss"
        metadata_file = index_dir / "metadata.json"

        index_info = {}
        if metadata_file.exists():
            try:
                meta = json.loads(metadata_file.read_text())
                index_info = {
                    "total_documents": meta.get("total_documents", 0),
                    "dimension": meta.get("dimension", 0),
                    "created": meta.get("created", ""),
                }
            except Exception:
                pass

        self._send_json({
            "documents": {
                "reports": len(docs_files),
                "papers": len(papers_files),
                "posts": len(x_files),
                "total": len(docs_files) + len(papers_files) + len(x_files),
            },
            "index": index_info,
            "faiss_exists": faiss_file.exists(),
        })


def main():
    parser = argparse.ArgumentParser(description="AGI Knowledge Search API")
    parser.add_argument("--port", type=int, default=8420, help="Port (default: 8420)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), SearchHandler)
    print(f"🎋 AGI Knowledge Search API")
    print(f"   Listening on http://{args.host}:{args.port}")
    print(f"   Endpoints: /search, /status, /stats")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🎋 Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()

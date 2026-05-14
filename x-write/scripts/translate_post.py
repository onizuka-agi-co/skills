#!/usr/bin/env python3
"""
AGI Knowledge Hub — 自動英訳パイプライン

日本語コンテンツを英語に翻訳し、X（Twitter）へ英語投稿する。
Usage:
    uv run scripts/translate_post.py translate <japanese_text> [--dry-run]
    uv run scripts/translate_post.py post-translated <japanese_text>
    uv run scripts/translate_post.py batch <file_or_directory> [--dry-run]
"""

import argparse
import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

# Token paths
TOKEN_FILE = Path(__file__).parent.parent.parent.parent / "x-tokens.json"

def translate_to_english(text: str) -> str:
    """Translate Japanese text to English using a simple prompt-based approach.
    
    In production, this would call GLM-5 or Claude for high-quality translation.
    For now, we output a structured prompt that OpenClaw agents can use.
    """
    # This is a placeholder — the actual translation will be handled by
    # the agent's LLM capabilities when invoked via OpenClaw
    prompt = f"""Translate the following Japanese AGI/ML research content to natural, 
professional English suitable for a technical Twitter/X post. Keep hashtags as-is. 
Maintain technical accuracy. Use the #ONIZUKA_AGI hashtag.

Japanese:
{text}

English translation:"""
    return prompt


def format_english_tweet(japanese_text: str, english_text: str) -> str:
    """Format the translated text as an X post."""
    # Truncate to 280 chars if needed
    if len(english_text) > 280:
        english_text = english_text[:277] + "..."
    
    # Ensure hashtag
    if "#ONIZUKA_AGI" not in english_text:
        english_text = english_text.rstrip() + " #ONIZUKA_AGI"
    
    return english_text


def main():
    parser = argparse.ArgumentParser(description="AGI Knowledge Hub — 自動英訳パイプライン")
    sub = parser.add_subparsers(dest="command")

    # translate
    p_translate = sub.add_parser("translate", help="Translate Japanese text to English")
    p_translate.add_argument("text", help="Japanese text to translate")
    p_translate.add_argument("--dry-run", action="store_true", help="Print without posting")

    # post-translated
    p_post = sub.add_parser("post-translated", help="Translate and post to X")
    p_post.add_argument("text", help="Japanese text to translate and post")

    # batch
    p_batch = sub.add_parser("batch", help="Translate file(s)")
    p_batch.add_argument("path", help="File or directory path")
    p_batch.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "translate":
        prompt = translate_to_english(args.text)
        print(f"[Translation Prompt]\n{prompt}")
        if args.dry_run:
            print("\n[dry-run] Would translate and format for X posting")

    elif args.command == "post-translated":
        print(f"[INFO] Translating and posting: {args.text[:50]}...")
        # In production: call LLM for translation, then x_write.py post
        prompt = translate_to_english(args.text)
        print(f"[Translation Prompt]\n{prompt}")
        print("[INFO] Agent should translate via LLM, then post via x-write skill")

    elif args.command == "batch":
        path = Path(args.path)
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(path.glob("*.md"))
        else:
            print(f"Path not found: {path}", file=sys.stderr)
            sys.exit(1)

        for f in files:
            content = f.read_text(encoding="utf-8")
            print(f"\n{'='*60}")
            print(f"File: {f.name}")
            print(f"{'='*60}")
            prompt = translate_to_english(content[:500])
            print(prompt[:300])
            if args.dry_run:
                print("[dry-run] Skipping actual translation")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

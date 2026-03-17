#!/usr/bin/env python3
"""
X Visual - Tweet Visual Explanation Generator

Generate visual explanations for X (Twitter) posts using AI image generation.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Add paths for imports
SCRIPT_DIR = Path(__file__).parent
SKILLS_DIR = SCRIPT_DIR.parent.parent
X_READ_DIR = SKILLS_DIR / "x-read" / "scripts"
NANO_BANANA_DIR = SKILLS_DIR / "nano-banana-2" / "scripts"

sys.path.insert(0, str(X_READ_DIR))
sys.path.insert(0, str(NANO_BANANA_DIR))

# Import from x-read
try:
    from x_read import XReadClient
except ImportError:
    XReadClient = None

# Import from nano-banana-2
try:
    from generate import generate_image, get_api_key
except ImportError:
    generate_image = None
    get_api_key = None

# fal.ai API endpoint
FAL_API_URL = "https://fal.run/fal-ai/nano-banana-2"

# Output directory
OUTPUT_DIR = SKILLS_DIR.parent / "data" / "x-visual"


def get_tweet(tweet_id: str) -> dict:
    """Fetch tweet by ID using x-read client."""
    if XReadClient is None:
        raise ImportError("x-read client not available")
    
    client = XReadClient()
    return client.get_tweet(tweet_id)


def analyze_tweet(tweet_data: dict) -> dict:
    """Analyze tweet content and extract key elements."""
    tweet = tweet_data.get("data", tweet_data)
    
    text = tweet.get("text", "")
    
    # Extract hashtags
    hashtags = []
    for entity in tweet.get("entities", {}).get("hashtags", []):
        hashtags.append(entity.get("tag", ""))
    
    # Extract mentions
    mentions = []
    for entity in tweet.get("entities", {}).get("mentions", []):
        mentions.append(entity.get("username", ""))
    
    # Extract URLs
    urls = []
    for entity in tweet.get("entities", {}).get("urls", []):
        urls.append(entity.get("expanded_url", entity.get("url", "")))
    
    # Simple keyword extraction (first few significant words)
    words = text.split()
    keywords = [w for w in words if len(w) > 3 and not w.startswith(("@", "#", "http"))][:5]
    
    return {
        "text": text,
        "hashtags": hashtags,
        "mentions": mentions,
        "urls": urls,
        "keywords": keywords,
        "author_id": tweet.get("author_id"),
        "created_at": tweet.get("created_at"),
    }


def generate_visual_prompt(analysis: dict) -> str:
    """Generate image prompt from tweet analysis."""
    text = analysis.get("text", "")
    keywords = analysis.get("keywords", [])
    hashtags = analysis.get("hashtags", [])
    
    # Build prompt
    prompt_parts = []
    
    # Add main content (first 100 chars)
    if text:
        prompt_parts.append(f"A visual illustration of: {text[:100]}")
    
    # Add keywords
    if keywords:
        prompt_parts.append(f"Key elements: {', '.join(keywords[:3])}")
    
    # Add style hints
    prompt_parts.append("Style: modern, clean, professional infographic style")
    prompt_parts.append("Format: suitable for social media sharing")
    
    return ". ".join(prompt_parts)


def generate_explanation(analysis: dict) -> str:
    """Generate explanation text for the tweet."""
    text = analysis.get("text", "")
    keywords = analysis.get("keywords", [])
    hashtags = analysis.get("hashtags", [])
    
    lines = []
    
    # Title
    lines.append("📊 ツイート図解")
    lines.append("")
    
    # Summary
    if len(text) > 50:
        lines.append(f"**要約:** {text[:100]}...")
    else:
        lines.append(f"**内容:** {text}")
    
    lines.append("")
    
    # Keywords
    if keywords:
        lines.append(f"**キーワード:** {', '.join(keywords)}")
    
    # Hashtags
    if hashtags:
        lines.append(f"**ハッシュタグ:** {', '.join(['#' + t for t in hashtags])}")
    
    lines.append("")
    lines.append("#ONIZUKA_AGI #図解")
    
    return "\n".join(lines)


def cmd_explain(args):
    """Generate visual explanation for a tweet."""
    print(f"Fetching tweet {args.tweet_id}...")
    
    # Fetch tweet
    try:
        tweet_data = get_tweet(args.tweet_id)
    except Exception as e:
        print(f"Error fetching tweet: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Analyze tweet
    analysis = analyze_tweet(tweet_data)
    print(f"\n📝 Tweet analyzed:")
    print(f"  Text: {analysis['text'][:80]}...")
    print(f"  Keywords: {analysis['keywords']}")
    
    # Generate prompt
    prompt = generate_visual_prompt(analysis)
    if args.custom_prompt:
        prompt = args.custom_prompt
    
    print(f"\n🎨 Generating image...")
    print(f"  Prompt: {prompt[:100]}...")
    
    # Generate image
    try:
        if generate_image is None:
            raise ImportError("nano-banana-2 not available")
        
        result = generate_image(
            prompt=prompt,
            num_images=1,
            aspect_ratio=args.aspect_ratio,
            resolution=args.resolution,
            output_format=args.format,
        )
    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)
    
    images = result.get("images", [])
    if not images:
        print("No images generated", file=sys.stderr)
        sys.exit(1)
    
    image_url = images[0].get("url")
    print(f"\n✅ Image generated: {image_url}")
    
    # Generate explanation
    explanation = generate_explanation(analysis)
    
    print(f"\n📝 Explanation:")
    print(explanation)
    
    # Save if requested
    if args.save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save image
        if image_url:
            ext = args.format.lower()
            image_path = OUTPUT_DIR / f"{args.tweet_id}.{ext}"
            
            request = Request(image_url, headers={"User-Agent": "ONIZUKA-AGI/1.0"})
            with urlopen(request, timeout=60) as response:
                image_path.write_bytes(response.read())
            
            print(f"\n💾 Image saved: {image_path}")
        
        # Save explanation
        explanation_path = OUTPUT_DIR / f"{args.tweet_id}_explanation.txt"
        explanation_path.write_text(explanation, encoding="utf-8")
        print(f"💾 Explanation saved: {explanation_path}")
    
    # Output JSON if requested
    if args.json:
        output = {
            "tweet_id": args.tweet_id,
            "analysis": analysis,
            "image_url": image_url,
            "explanation": explanation,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_preview(args):
    """Preview prompt without generating."""
    print(f"Fetching tweet {args.tweet_id}...")
    
    try:
        tweet_data = get_tweet(args.tweet_id)
    except Exception as e:
        print(f"Error fetching tweet: {e}", file=sys.stderr)
        sys.exit(1)
    
    analysis = analyze_tweet(tweet_data)
    prompt = generate_visual_prompt(analysis)
    
    print(f"\n📝 Tweet Analysis:")
    print(f"  Text: {analysis['text']}")
    print(f"  Keywords: {analysis['keywords']}")
    print(f"  Hashtags: {analysis['hashtags']}")
    
    print(f"\n🎨 Generated Prompt:")
    print(f"  {prompt}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate visual explanations for X posts"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # explain command
    explain_parser = subparsers.add_parser("explain", help="Generate visual explanation")
    explain_parser.add_argument("tweet_id", help="Tweet ID")
    explain_parser.add_argument("--prompt", dest="custom_prompt", help="Custom prompt")
    explain_parser.add_argument("--aspect-ratio", "-a", default="16:9",
                               choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
                               help="Aspect ratio")
    explain_parser.add_argument("--resolution", "-r", default="1K",
                               choices=["0.5K", "1K", "2K", "4K"],
                               help="Resolution")
    explain_parser.add_argument("--format", "-f", default="png",
                               choices=["jpeg", "png", "webp"],
                               help="Output format")
    explain_parser.add_argument("--save", "-s", action="store_true", help="Save locally")
    explain_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    # preview command
    preview_parser = subparsers.add_parser("preview", help="Preview prompt without generating")
    preview_parser.add_argument("tweet_id", help="Tweet ID")
    
    args = parser.parse_args()
    
    if args.command == "explain":
        cmd_explain(args)
    elif args.command == "preview":
        cmd_preview(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

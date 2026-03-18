#!/usr/bin/env python3
"""
Visual Quote Pipeline for X Community

1. Fetch source tweet
2. Generate visualization image
3. Upload image to X
4. Post to community with image and quoted content
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request

# Add parent paths for imports
SCRIPT_DIR = Path(__file__).parent
X_READ_SCRIPT = SCRIPT_DIR.parent.parent / "x-read" / "scripts" / "x_read.py"
NANO_BANANA_SCRIPT = SCRIPT_DIR.parent.parent / "nano-banana-2" / "scripts" / "generate.py"

# fal.ai API
FAL_API_URL = "https://fal.run/fal-ai/nano-banana-2"

# API key file locations
API_KEY_FILES = [
    Path(__file__).parent.parent.parent.parent / "fal-key.txt",
    Path.home() / ".fal-key.txt",
]


def get_api_key() -> str:
    """Get fal.ai API key from file or environment."""
    key = os.environ.get("FAL_KEY")
    if key:
        return key
    
    for key_file in API_KEY_FILES:
        if key_file.exists():
            return key_file.read_text().strip()
    
    raise ValueError("FAL_KEY not found. Set FAL_KEY environment variable or create fal-key.txt")


def extract_tweet_id(url_or_id: str) -> str:
    """Extract tweet ID from URL or return as-is."""
    if url_or_id.isdigit():
        return url_or_id
    
    match = re.search(r'(?:x\.com|twitter\.com)/\w+/status/(\d+)', url_or_id)
    if match:
        return match.group(1)
    return None


def fetch_tweet(tweet_id: str) -> dict:
    """Fetch tweet content using x-read client."""
    # Import and use XReadClient directly
    sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "x-read" / "scripts"))
    from x_read import XReadClient
    
    client = XReadClient()
    result = client.get_tweet_with_media(tweet_id)
    return result


def generate_visualization(tweet_text: str, author_name: str) -> tuple:
    """Generate visualization image for tweet content."""
    api_key = get_api_key()
    
    # Create prompt for visualization
    prompt = f"""Create an artistic visualization representing this concept:
"{tweet_text[:200]}"

Style: Modern, clean, abstract but meaningful, suitable for social media.
No text in the image. Focus on visual metaphors and symbolic representation."""
    
    payload = {
        "prompt": prompt,
        "num_images": 1,
        "aspect_ratio": "16:9",
        "resolution": "1K",
        "output_format": "png",
    }
    
    request = Request(
        FAL_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    with urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    
    images = result.get("images", [])
    if not images:
        raise ValueError("No images generated")
    
    return images[0].get("url"), images[0].get("seed")


def download_image(url: str, save_path: Path) -> Path:
    """Download image from URL."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    request = Request(url, headers={"User-Agent": "ONIZUKA-AGI/1.0"})
    
    with urlopen(request, timeout=60) as response:
        save_path.write_bytes(response.read())
    
    return save_path


def post_visual_quote(tweet_url: str, comment: str = None, no_share: bool = False):
    """Main pipeline: fetch tweet, generate image, post to community."""
    
    # 1. Extract tweet ID
    tweet_id = extract_tweet_id(tweet_url)
    if not tweet_id:
        raise ValueError(f"Invalid tweet URL or ID: {tweet_url}")
    
    print(f"📌 Fetching tweet: {tweet_id}")
    
    # 2. Fetch tweet content
    tweet_data = fetch_tweet(tweet_id)
    
    if "data" not in tweet_data:
        raise ValueError(f"Tweet not found: {tweet_id}")
    
    tweet = tweet_data["data"]
    tweet_text = tweet.get("text", "")
    
    # Get author info
    author_username = "unknown"
    author_name = "Unknown"
    if "includes" in tweet_data and "users" in tweet_data["includes"]:
        author = tweet_data["includes"]["users"][0]
        author_username = author.get("username", "unknown")
        author_name = author.get("name", "Unknown")
    
    print(f"📝 Tweet by @{author_username}: {tweet_text[:100]}...")
    
    # 3. Generate visualization image
    print("🎨 Generating visualization...")
    image_url, seed = generate_visualization(tweet_text, author_name)
    print(f"   Image URL: {image_url}")
    print(f"   Seed: {seed}")
    
    # 4. Download image
    temp_dir = Path(tempfile.mkdtemp())
    image_path = temp_dir / f"visual_{tweet_id}.png"
    download_image(image_url, image_path)
    print(f"📥 Downloaded: {image_path}")
    
    # 5. Upload to X
    print("📤 Uploading image to X...")
    sys.path.insert(0, str(SCRIPT_DIR))
    from x_community import XCommunityClient
    
    client = XCommunityClient()
    media_id = client.upload_media(image_path)
    print(f"   Media ID: {media_id}")
    
    # 6. Build post text
    # Format: comment + quoted content
    post_parts = []
    
    if comment:
        post_parts.append(comment)
        post_parts.append("")  # Empty line
    
    post_parts.append("---")
    post_parts.append(f"📝 引用元:")
    post_parts.append(f"@{author_username}: {tweet_text}")
    post_parts.append("")
    post_parts.append("#ONIZUKA_AGI")
    
    post_text = "\n".join(post_parts)
    
    # 7. Post to community
    print("📮 Posting to community...")
    result = client.post_to_community(
        text=post_text,
        share_with_followers=not no_share,
        media_ids=[media_id]
    )
    
    # Cleanup temp file
    image_path.unlink(missing_ok=True)
    temp_dir.rmdir()
    
    return {
        "success": True,
        "tweet_id": tweet_id,
        "source_author": author_username,
        "image_url": image_url,
        "media_id": media_id,
        "post_result": result
    }


def main():
    parser = argparse.ArgumentParser(
        description="Visual Quote Pipeline - Generate visual explanation and post to community"
    )
    
    parser.add_argument("tweet_url", help="Tweet URL or ID to quote")
    parser.add_argument("--comment", "-c", default="", help="Commentary text")
    parser.add_argument("--no-share", action="store_true",
                       help="Don't share with followers (community only)")
    
    args = parser.parse_args()
    
    try:
        result = post_visual_quote(
            tweet_url=args.tweet_url,
            comment=args.comment,
            no_share=args.no_share
        )
        
        print("\n✅ Success!")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

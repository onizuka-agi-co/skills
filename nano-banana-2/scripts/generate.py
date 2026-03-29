#!/usr/bin/env python3
"""
nano-banana-2 Image Generator
Generate images from text prompts using fal.ai's nano-banana-2 model.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
import urllib.request


def get_api_key() -> Optional[str]:
    """Get FAL API key from environment or file."""
    # Try environment variable first
    api_key = os.environ.get("FAL_KEY")
    if api_key:
        return api_key

    # Try file in workspace
    key_file = Path(__file__).parent.parent.parent.parent / "fal-key.txt"
    if key_file.exists():
        return key_file.read_text().strip()

    return None


def generate_image(
    prompt: str,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    seed: Optional[int] = None,
    enable_web_search: bool = False,
    api_key: str = None,
) -> dict:
    """Generate image using fal.ai nano-banana-2 API."""
    if not api_key:
        api_key = get_api_key()
        if not api_key:
            return {"error": "FAL_KEY not found. Set environment variable or create fal-key.txt"}

    try:
        import fal_client

        # Build request payload
        payload = {
            "prompt": prompt,
            "num_images": num_images,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "output_format": output_format,
        }

        if seed is not None:
            payload["seed"] = seed

        if enable_web_search:
            payload["enable_web_search"] = True

        # Set API key
        os.environ["FAL_KEY"] = api_key

        # Subscribe to the model (handles queue + result)
        result = fal_client.subscribe(
            "fal-ai/nano-banana-2",
            arguments=payload,
            with_logs=True,
        )

        return {
            "images": [
                {
                    "url": img.get("url"),
                    "content_type": img.get("content_type"),
                    "file_name": img.get("file_name"),
                    "width": img.get("width"),
                    "height": img.get("height"),
                }
                for img in result.get("images", [])
            ],
            "description": result.get("description", ""),
            "request_id": result.get("request_id"),
        }

    except Exception as e:
        return {"error": str(e)}


def download_image(url: str, output_path: Path) -> bool:
    """Download image from URL to file."""
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"Failed to download image: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate images from text prompts using fal.ai nano-banana-2"
    )
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument("--num-images", type=int, default=1, help="Number of images to generate")
    parser.add_argument(
        "--aspect-ratio",
        choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16", "4:1", "1:4", "8:1", "1:8"],
        default="auto",
        help="Aspect ratio of generated image",
    )
    parser.add_argument(
        "--resolution",
        choices=["0.5K", "1K", "2K", "4K"],
        default="1K",
        help="Resolution of generated image",
    )
    parser.add_argument(
        "--output-format",
        choices=["jpeg", "png", "webp"],
        default="png",
        help="Output format of generated image",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument(
        "--enable-web-search",
        action="store_true",
        help="Enable web search for up-to-date information",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory to save generated images",
    )
    parser.add_argument("--save", action="store_true", help="Download and save images locally")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Generate image
    result = generate_image(
        prompt=args.prompt,
        num_images=args.num_images,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        output_format=args.output_format,
        seed=args.seed,
        enable_web_search=args.enable_web_search,
    )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    # Download images if requested
    if args.save and result["images"]:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for i, img in enumerate(result["images"]):
            ext = args.output_format
            filename = f"generated_{i+1}.{ext}"
            output_path = args.output_dir / filename
            if download_image(img["url"], output_path):
                img["local_path"] = str(output_path)

    # Output result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n🎋 Generated {len(result['images'])} image(s):")
        for i, img in enumerate(result["images"]):
            print(f"  Image {i+1}: {img['url']}")
            print(f"    Size: {img.get('width', 'N/A')}x{img.get('height', 'N/A')}")
            print(f"    Format: {img.get('content_type', 'N/A')}")
            if img.get("local_path"):
                print(f"    Saved: {img['local_path']}")

        print(f"\nDescription: {result.get('description', 'N/A')}")
        print(f"Request ID: {result.get('request_id', 'N/A')}")


if __name__ == "__main__":
    main()

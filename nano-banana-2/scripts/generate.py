#!/usr/bin/env python3
"""
Generate images using fal.ai's nano-banana-2 model.

Usage:
    uv run generate.py --prompt "A serene mountain landscape"
    uv run generate.py --prompt "A cyberpunk city" --aspect-ratio 16:9 --resolution 2K
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.run(["uv", "pip", "install", "requests"], check=True)
    import requests


# API endpoint
FAL_API_URL = "https://queue.fal.run/fal-ai/nano-banana-2"

# Valid options
ASPECT_RATIOS = ["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"]
RESOLUTIONS = ["0.5K", "1K", "2K", "4K"]
OUTPUT_FORMATS = ["jpeg", "png", "webp"]


def get_api_key() -> str:
    """Get FAL API key from environment or file."""
    # Try environment variable first
    api_key = os.environ.get("FAL_KEY")
    if api_key:
        return api_key

    # Try workspace file
    key_file = Path(__file__).parent.parent.parent / "fal-key.txt"
    if key_file.exists():
        return key_file.read_text().strip()

    # Try home directory
    home_key = Path.home() / "fal-key.txt"
    if home_key.exists():
        return home_key.read_text().strip()

    raise ValueError(
        "FAL API key not found. Set FAL_KEY environment variable or create fal-key.txt"
    )


def submit_request(
    api_key: str,
    prompt: str,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    seed: Optional[int] = None,
    enable_web_search: bool = False,
) -> dict:
    """Submit image generation request to fal.ai."""
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "num_images": num_images,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
        "limit_generations": True,
    }

    if seed is not None:
        payload["seed"] = seed

    if enable_web_search:
        payload["enable_web_search"] = True

    response = requests.post(
        FAL_API_URL,
        headers=headers,
        json=payload,
    )

    if response.status_code != 200:
        raise Exception(f"API request failed: {response.status_code} - {response.text}")

    return response.json()


def get_result(api_key: str, request_id: str) -> dict:
    """Get the result of a submitted request."""
    headers = {
        "Authorization": f"Key {api_key}",
    }

    result_url = f"https://queue.fal.run/fal-ai/nano-banana-2/requests/{request_id}/status"

    response = requests.get(result_url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to get status: {response.status_code} - {response.text}")

    return response.json()


def download_image(url: str, output_path: Path) -> None:
    """Download image from URL to local file."""
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download image: {response.status_code}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    print(f"Downloaded: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using fal.ai's nano-banana-2 model"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text prompt for image generation"
    )
    parser.add_argument(
        "--num-images", "-n",
        type=int,
        default=1,
        help="Number of images to generate (default: 1)"
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        choices=ASPECT_RATIOS,
        default="auto",
        help="Aspect ratio (default: auto)"
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=RESOLUTIONS,
        default="1K",
        help="Resolution (default: 1K)"
    )
    parser.add_argument(
        "--output-format", "-f",
        choices=OUTPUT_FORMATS,
        default="png",
        help="Output format (default: png)"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--enable-web-search",
        action="store_true",
        help="Enable web search for up-to-date information"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("generated"),
        help="Output directory for downloaded images (default: generated)"
    )
    parser.add_argument(
        "--download", "-d",
        action="store_true",
        help="Download generated images locally"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response"
    )

    args = parser.parse_args()

    try:
        api_key = get_api_key()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Generating {args.num_images} image(s)...")
    print(f"Prompt: {args.prompt}")
    print(f"Aspect ratio: {args.aspect_ratio}")
    print(f"Resolution: {args.resolution}")
    print(f"Output format: {args.output_format}")
    print()

    try:
        # Submit request
        result = submit_request(
            api_key=api_key,
            prompt=args.prompt,
            num_images=args.num_images,
            aspect_ratio=args.aspect_ratio,
            resolution=args.resolution,
            output_format=args.output_format,
            seed=args.seed,
            enable_web_search=args.enable_web_search,
        )

        if args.json:
            print(json.dumps(result, indent=2))
            return

        # Display results
        images = result.get("images", [])
        description = result.get("description", "")

        print(f"Generated {len(images)} image(s):")
        print()

        for i, image in enumerate(images, 1):
            url = image.get("url", "")
            width = image.get("width", "?")
            height = image.get("height", "?")
            content_type = image.get("content_type", "?")

            print(f"Image {i}:")
            print(f"  URL: {url}")
            print(f"  Size: {width}x{height}")
            print(f"  Type: {content_type}")
            print()

            if args.download and url:
                ext = content_type.split("/")[-1] if "/" in content_type else args.output_format
                output_path = args.output_dir / f"nano-banana-2-{i}.{ext}"
                download_image(url, output_path)

        if description:
            print(f"Description: {description}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

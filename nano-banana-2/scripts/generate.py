#!/usr/bin/env python3
"""
nano-banana-2 Image Generator

Generate images from text prompts using fal.ai's nano-banana-2 model.
Uses HTTP requests directly (no fal-client dependency).

Usage:
    python3 generate.py --prompt "A serene mountain landscape"
    python3 generate.py --prompt "cyberpunk city" --aspect-ratio 16:9 --resolution 2K
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


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
        "FAL API key not found. Set FAL_KEY environment variable "
        "or create ~/fal-key.txt"
    )


def fal_request(
    endpoint: str,
    api_key: str,
    data: dict,
    method: str = "POST"
) -> dict:
    """Make request to fal.ai API."""
    url = f"https://queue.fal.run/{endpoint}"

    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"API error {e.code}: {error_body}")


def fal_status(endpoint: str, api_key: str, request_id: str) -> dict:
    """Check status of async request."""
    url = f"https://queue.fal.run/{endpoint}/requests/{request_id}/status"

    headers = {
        "Authorization": f"Key {api_key}",
    }

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fal_result(endpoint: str, api_key: str, request_id: str) -> dict:
    """Get result of completed request."""
    url = f"https://queue.fal.run/{endpoint}/requests/{request_id}"

    headers = {
        "Authorization": f"Key {api_key}",
    }

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def generate_image(
    prompt: str,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    seed: Optional[int] = None,
    enable_web_search: bool = False,
) -> dict:
    """Generate image(s) from text prompt."""
    api_key = get_api_key()
    endpoint = "fal-ai/nano-banana-2"

    # Build input
    input_data = {
        "prompt": prompt,
        "num_images": num_images,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
        "limit_generations": True,
    }

    if seed is not None:
        input_data["seed"] = seed
    if enable_web_search:
        input_data["enable_web_search"] = True

    # Submit request
    print(f"🎨 Generating image: {prompt[:50]}...")

    # Submit and wait for result
    submit_response = fal_request(endpoint, api_key, input_data)
    request_id = submit_response.get("request_id")

    if not request_id:
        raise RuntimeError(f"No request_id in response: {submit_response}")

    # Poll for completion
    print(f"⏳ Request ID: {request_id}")
    max_wait = 300  # 5 minutes max
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status = fal_status(endpoint, api_key, request_id)
        status_code = status.get("status")

        if status_code == "COMPLETED":
            return fal_result(endpoint, api_key, request_id)
        elif status_code == "FAILED":
            raise RuntimeError(f"Generation failed: {status}")

        time.sleep(2)

    raise RuntimeError("Timeout waiting for generation")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using nano-banana-2"
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
        choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
        default="auto",
        help="Aspect ratio (default: auto)"
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["0.5K", "1K", "2K", "4K"],
        default="1K",
        help="Resolution (default: 1K)"
    )
    parser.add_argument(
        "--output-format", "-f",
        choices=["jpeg", "png", "webp"],
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
        "--output", "-o",
        help="Output directory for downloaded images"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )

    args = parser.parse_args()

    # Run generation
    result = generate_image(
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
    else:
        images = result.get("images", [])
        print(f"\n✅ Generated {len(images)} image(s):")
        for img in images:
            print(f"  📷 {img.get('url', 'N/A')}")

        if args.output and images:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)

            for i, img in enumerate(images, 1):
                url = img.get("url")
                if url:
                    ext = args.output_format
                    filename = output_dir / f"nano-banana-2-{i}.{ext}"
                    urllib.request.urlretrieve(url, filename)
                    print(f"  💾 Saved: {filename}")


if __name__ == "__main__":
    main()

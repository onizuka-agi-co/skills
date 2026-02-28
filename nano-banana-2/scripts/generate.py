#!/usr/bin/env python3
"""
nano-banana-2 Image Generator

Generate images from text prompts using fal.ai's nano-banana-2 model.

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
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: uv add httpx")
    sys.exit(1)


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
        "FAL_KEY not found. Set FAL_KEY environment variable or create ~/fal-key.txt"
    )


def generate_image(
    prompt: str,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    seed: Optional[int] = None,
    enable_web_search: bool = False,
    api_key: Optional[str] = None,
) -> dict:
    """
    Generate image(s) using fal.ai nano-banana-2 API.

    Args:
        prompt: Text description of the image
        num_images: Number of images to generate (1-4)
        aspect_ratio: Aspect ratio (auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16)
        resolution: Resolution (0.5K, 1K, 2K, 4K)
        output_format: Output format (jpeg, png, webp)
        seed: Random seed for reproducibility
        enable_web_search: Enable web search for up-to-date information
        api_key: FAL API key (optional, will be fetched if not provided)

    Returns:
        API response with generated image URLs
    """
    if api_key is None:
        api_key = get_api_key()

    url = "https://queue.fal.run/fal-ai/nano-banana-2"

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

    # Submit request
    with httpx.Client(timeout=60.0) as client:
        # Submit job
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Get request ID
        request_id = result.get("request_id")
        if not request_id:
            return result

        # Poll for result
        status_url = f"https://queue.fal.run/fal-ai/nano-banana-2/requests/{request_id}/status"
        result_url = f"https://queue.fal.run/fal-ai/nano-banana-2/requests/{request_id}"

        import time

        while True:
            status_response = client.get(status_url, headers=headers)
            status_response.raise_for_status()
            status = status_response.json()

            if status.get("status") == "COMPLETED":
                break
            elif status.get("status") == "FAILED":
                raise Exception(f"Image generation failed: {status}")

            time.sleep(2)

        # Get final result
        result_response = client.get(result_url, headers=headers)
        result_response.raise_for_status()
        return result_response.json()


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using fal.ai nano-banana-2"
    )
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt for image generation")
    parser.add_argument("--num-images", "-n", type=int, default=1, help="Number of images to generate")
    parser.add_argument(
        "--aspect-ratio", "-a",
        default="auto",
        choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
        help="Aspect ratio",
    )
    parser.add_argument(
        "--resolution", "-r",
        default="1K",
        choices=["0.5K", "1K", "2K", "4K"],
        help="Image resolution",
    )
    parser.add_argument(
        "--output-format", "-f",
        default="png",
        choices=["jpeg", "png", "webp"],
        help="Output format",
    )
    parser.add_argument("--seed", "-s", type=int, help="Random seed")
    parser.add_argument("--web-search", "-w", action="store_true", help="Enable web search")
    parser.add_argument("--output", "-o", help="Output directory for downloaded images")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        result = generate_image(
            prompt=args.prompt,
            num_images=args.num_images,
            aspect_ratio=args.aspect_ratio,
            resolution=args.resolution,
            output_format=args.output_format,
            seed=args.seed,
            enable_web_search=args.web_search,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            images = result.get("images", [])
            if images:
                print(f"✅ Generated {len(images)} image(s):")
                for i, img in enumerate(images, 1):
                    url = img.get("url", "")
                    print(f"  {i}. {url}")

                if args.output:
                    output_dir = Path(args.output)
                    output_dir.mkdir(parents=True, exist_ok=True)

                    for i, img in enumerate(images, 1):
                        url = img.get("url", "")
                        if url:
                            # Download image
                            ext = args.output_format
                            filename = f"nano-banana-2-{i}.{ext}"
                            filepath = output_dir / filename

                            with httpx.Client() as client:
                                img_response = client.get(url)
                                img_response.raise_for_status()
                                filepath.write_bytes(img_response.content)

                            print(f"  💾 Saved: {filepath}")
            else:
                print("❌ No images generated")
                print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

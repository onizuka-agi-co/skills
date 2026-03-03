#!/usr/bin/env python3
"""
Nano Banana 2 - Image Generation with fal.ai

Generate images from text prompts using fal.ai's nano-banana-2 model.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# fal.ai API endpoint
FAL_API_URL = "https://fal.run/fal-ai/nano-banana-2"

# API key file locations
API_KEY_FILES = [
    Path(__file__).parent.parent.parent.parent / "fal-key.txt",
    Path.home() / ".fal-key.txt",
]


def get_api_key() -> Optional[str]:
    """Get fal.ai API key from file or environment."""
    # Check environment variable
    key = os.environ.get("FAL_KEY")
    if key:
        return key
    
    # Check key files
    for key_file in API_KEY_FILES:
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
) -> dict:
    """Generate image using fal.ai nano-banana-2 API."""
    
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "FAL_KEY not found. Set FAL_KEY environment variable "
            "or create fal-key.txt in workspace root."
        )
    
    payload = {
        "prompt": prompt,
        "num_images": num_images,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
        "enable_web_search": enable_web_search,
    }
    
    if seed is not None:
        payload["seed"] = seed
    
    request = Request(
        FAL_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
    )
    
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"API error: {e.code} - {error_body}")


def save_image(url: str, output_dir: Path, filename: str) -> Path:
    """Download and save image from URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    
    request = Request(url, headers={"User-Agent": "ONIZUKA-AGI/1.0"})
    
    with urlopen(request, timeout=60) as response:
        output_path.write_bytes(response.read())
    
    return output_path


def cmd_generate(args):
    """Generate images from prompt."""
    print(f"Generating {args.num_images} image(s)...")
    print(f"Prompt: {args.prompt}")
    
    result = generate_image(
        prompt=args.prompt,
        num_images=args.num_images,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        output_format=args.output_format,
        seed=args.seed,
        enable_web_search=args.web_search,
    )
    
    images = result.get("images", [])
    print(f"\nGenerated {len(images)} image(s):")
    
    output_dir = Path(args.output_dir)
    
    for i, image in enumerate(images):
        url = image.get("url")
        if url:
            print(f"\nImage {i + 1}:")
            print(f"  URL: {url}")
            
            if args.save:
                ext = args.output_format.lower()
                filename = f"generated_{i + 1}.{ext}"
                saved_path = save_image(url, output_dir, filename)
                print(f"  Saved: {saved_path}")
            
            if args.seed is None:
                print(f"  Seed: {image.get('seed', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images with fal.ai nano-banana-2"
    )
    
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--num-images", "-n", type=int, default=1, help="Number of images")
    parser.add_argument("--aspect-ratio", "-a", default="auto",
                       choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
                       help="Aspect ratio")
    parser.add_argument("--resolution", "-r", default="1K",
                       choices=["0.5K", "1K", "2K", "4K"],
                       help="Resolution")
    parser.add_argument("--output-format", "-f", default="png",
                       choices=["jpeg", "png", "webp"],
                       help="Output format")
    parser.add_argument("--seed", "-s", type=int, help="Random seed")
    parser.add_argument("--web-search", "-w", action="store_true",
                       help="Enable web search for up-to-date info")
    parser.add_argument("--save", action="store_true", help="Save images locally")
    parser.add_argument("--output-dir", "-o", default="output",
                       help="Output directory for saved images")
    
    args = parser.parse_args()
    
    try:
        cmd_generate(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

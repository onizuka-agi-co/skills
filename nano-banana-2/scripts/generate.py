#!/usr/bin/env python3
"""
nano-banana-2 Image Generator

Generate images from text prompts using fal.ai's nano-banana-2 model.

Usage:
    uv run generate.py --prompt "A serene mountain landscape"
    uv run generate.py --prompt "cyberpunk city" --aspect-ratio 16:9 --resolution 2K
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
    print("Error: httpx is required. Install with: uv pip install httpx")
    sys.exit(1)


# fal.ai API endpoints
FAL_API_URL = "https://fal.run/fal-ai/nano-banana-2"

# Default settings
DEFAULT_ASPECT_RATIO = "auto"
DEFAULT_RESOLUTION = "1K"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_NUM_IMAGES = 1
DEFAULT_SAFETY_TOLERANCE = "4"


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


def generate_image(
    prompt: str,
    num_images: int = DEFAULT_NUM_IMAGES,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    resolution: str = DEFAULT_RESOLUTION,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    seed: Optional[int] = None,
    enable_web_search: bool = False,
    api_key: Optional[str] = None,
) -> dict:
    """
    Generate image(s) from a text prompt using sync mode.
    
    Args:
        prompt: Text description of the image
        num_images: Number of images to generate (1-4)
        aspect_ratio: Aspect ratio (auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16)
        resolution: Resolution (0.5K, 1K, 2K, 4K)
        output_format: Output format (jpeg, png, webp)
        seed: Random seed for reproducibility
        enable_web_search: Enable web search for up-to-date info
        api_key: FAL API key
    
    Returns:
        API response with image URLs
    """
    if api_key is None:
        api_key = get_api_key()
    
    # Build request payload
    payload = {
        "prompt": prompt,
        "num_images": num_images,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
        "safety_tolerance": DEFAULT_SAFETY_TOLERANCE,
        "limit_generations": True,
        "sync_mode": True,  # Use sync mode for immediate response
    }
    
    if seed is not None:
        payload["seed"] = seed
    
    if enable_web_search:
        payload["enable_web_search"] = True
    
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }
    
    # Submit request
    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            FAL_API_URL,
            headers=headers,
            json=payload,
        )
        
        if response.status_code == 401:
            raise ValueError("Invalid FAL API key")
        
        if response.status_code == 402:
            raise ValueError("FAL API quota exceeded")
        
        if response.status_code != 200:
            error_detail = response.text
            raise RuntimeError(f"API error {response.status_code}: {error_detail}")
        
        result = response.json()
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using fal.ai nano-banana-2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --prompt "A serene mountain landscape at sunset"
  %(prog)s --prompt "cyberpunk city" --aspect-ratio 16:9 --resolution 2K
  %(prog)s --prompt "portrait" --num-images 4 --output-format jpeg
        """
    )
    
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text prompt for image generation"
    )
    
    parser.add_argument(
        "--num-images", "-n",
        type=int,
        default=DEFAULT_NUM_IMAGES,
        choices=range(1, 5),
        help=f"Number of images to generate (default: {DEFAULT_NUM_IMAGES})"
    )
    
    parser.add_argument(
        "--aspect-ratio", "-a",
        default=DEFAULT_ASPECT_RATIO,
        choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
        help=f"Aspect ratio (default: {DEFAULT_ASPECT_RATIO})"
    )
    
    parser.add_argument(
        "--resolution", "-r",
        default=DEFAULT_RESOLUTION,
        choices=["0.5K", "1K", "2K", "4K"],
        help=f"Resolution (default: {DEFAULT_RESOLUTION})"
    )
    
    parser.add_argument(
        "--output-format", "-f",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["jpeg", "png", "webp"],
        help=f"Output format (default: {DEFAULT_OUTPUT_FORMAT})"
    )
    
    parser.add_argument(
        "--seed", "-s",
        type=int,
        help="Random seed for reproducibility"
    )
    
    parser.add_argument(
        "--enable-web-search",
        action="store_true",
        help="Enable web search for up-to-date info"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response"
    )
    
    parser.add_argument(
        "--download", "-d",
        metavar="DIR",
        help="Download images to directory"
    )
    
    args = parser.parse_args()
    
    try:
        print(f"🎨 Generating image: {args.prompt[:50]}...")
        
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
            return
        
        images = result.get("images", [])
        
        if not images:
            print("⚠️ No images generated")
            return
        
        print(f"✅ Generated {len(images)} image(s):\n")
        
        for i, img in enumerate(images, 1):
            url = img.get("url", "")
            width = img.get("width", "?")
            height = img.get("height", "?")
            print(f"  [{i}] {url}")
            print(f"      Size: {width}x{height}\n")
        
        # Download if requested
        if args.download:
            download_dir = Path(args.download)
            download_dir.mkdir(parents=True, exist_ok=True)
            
            with httpx.Client() as client:
                for i, img in enumerate(images, 1):
                    url = img.get("url")
                    if not url:
                        continue
                    
                    ext = args.output_format
                    filename = download_dir / f"nano-banana-2-{i}.{ext}"
                    
                    response = client.get(url)
                    filename.write_bytes(response.content)
                    print(f"  📥 Downloaded: {filename}")
    
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

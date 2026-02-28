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

try:
    from fal_client import client
except ImportError:
    print("Installing fal-client...")
    os.system("pip install fal-client")
    from fal_client import client


def load_api_key() -> str:
    """Load FAL API key from environment or file."""
    # Try environment variable first
    api_key = os.environ.get("FAL_KEY")
    if api_key:
        return api_key

    # Try workspace file
    key_file = Path(__file__).parent.parent.parent / "fal-key.txt"
    if key_file.exists():
        return key_file.read_text().strip()

    # Try home directory
    key_file = Path.home() / "fal-key.txt"
    if key_file.exists():
        return key_file.read_text().strip()

    raise ValueError(
        "FAL_KEY not found. Set FAL_KEY environment variable or create fal-key.txt"
    )


def generate_image(
    prompt: str,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    seed: Optional[int] = None,
    enable_web_search: bool = False,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Generate images using nano-banana-2 model.

    Args:
        prompt: Text description of the image
        num_images: Number of images to generate (1-4)
        aspect_ratio: Aspect ratio (auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16)
        resolution: Resolution (0.5K, 1K, 2K, 4K)
        output_format: Output format (jpeg, png, webp)
        seed: Random seed for reproducibility
        enable_web_search: Enable web search for up-to-date info
        output_dir: Directory to save images

    Returns:
        API response with image URLs
    """
    # Set API key
    os.environ["FAL_KEY"] = load_api_key()

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

    # Call API
    print(f"Generating {num_images} image(s)...")
    print(f"Prompt: {prompt}")
    print(f"Resolution: {resolution}, Aspect: {aspect_ratio}")

    result = client.subscribe(
        "fal-ai/nano-banana-2",
        input=input_data,
        logs=True,
    )

    # Download images if output_dir specified
    if output_dir and result.get("images"):
        import urllib.request

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(result["images"]):
            url = img["url"]
            ext = output_format.lower()
            filename = f"generated_{i+1}.{ext}"
            filepath = output_path / filename

            print(f"Downloading to {filepath}...")
            urllib.request.urlretrieve(url, filepath)
            img["local_path"] = str(filepath)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using nano-banana-2"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text description of the image"
    )
    parser.add_argument(
        "--num-images", "-n",
        type=int,
        default=1,
        help="Number of images to generate (default: 1)"
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        default="auto",
        choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
        help="Aspect ratio (default: auto)"
    )
    parser.add_argument(
        "--resolution", "-r",
        default="1K",
        choices=["0.5K", "1K", "2K", "4K"],
        help="Resolution (default: 1K)"
    )
    parser.add_argument(
        "--output-format", "-f",
        default="png",
        choices=["jpeg", "png", "webp"],
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
        help="Enable web search for up-to-date info"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Directory to save images"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    result = generate_image(
        prompt=args.prompt,
        num_images=args.num_images,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        output_format=args.output_format,
        seed=args.seed,
        enable_web_search=args.enable_web_search,
        output_dir=args.output_dir,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n✅ Generation complete!")
        for i, img in enumerate(result.get("images", [])):
            print(f"  Image {i+1}: {img.get('url', 'N/A')}")
            if img.get("local_path"):
                print(f"    Saved to: {img['local_path']}")


if __name__ == "__main__":
    main()

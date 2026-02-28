#!/usr/bin/env python3
"""
Nano Banana 2 - Image Generation Script

Usage:
    uv run generate.py --prompt "A serene mountain landscape"
    uv run generate.py --prompt "..." --aspect-ratio 16:9 --resolution 2K
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from fal_client import client
except ImportError:
    print("Installing fal-client...")
    import subprocess
    subprocess.run(["uv", "pip", "install", "fal-client"], check=True)
    from fal_client import client

# 設定
TOKEN_FILE = Path(__file__).parent.parent.parent.parent / "fal-key.txt"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def load_api_key() -> str:
    """API Keyを読み込む"""
    # 環境変数から取得
    import os
    key = os.environ.get("FAL_KEY")
    if key:
        return key
    
    # ファイルから取得
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    
    raise ValueError("FAL_KEY not found. Set FAL_KEY environment variable or create ~/fal-key.txt")


def generate_image(
    prompt: str,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    seed: int = None,
    enable_web_search: bool = False,
) -> dict:
    """画像を生成"""
    
    api_key = load_api_key()
    
    # 入力パラメータ構築
    input_data = {
        "prompt": prompt,
        "num_images": num_images,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
    }
    
    if seed is not None:
        input_data["seed"] = seed
    if enable_web_search:
        input_data["enable_web_search"] = True
    
    print(f"🎨 Generating image...")
    print(f"   Prompt: {prompt[:100]}...")
    print(f"   Aspect: {aspect_ratio}, Resolution: {resolution}")
    
    # API呼び出し
    result = client.subscribe(
        "fal-ai/nano-banana-2",
        input=input_data,
        logs=True,
    )
    
    return result


def save_images(result: dict, output_dir: Path = OUTPUT_DIR):
    """画像を保存"""
    import httpx
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    images = result.get("images", [])
    saved_paths = []
    
    for i, img in enumerate(images):
        url = img.get("url")
        if not url:
            continue
        
        # 画像をダウンロード
        with httpx.Client() as client:
            resp = client.get(url)
            resp.raise_for_status()
        
        # ファイル名生成
        content_type = img.get("content_type", "image/png")
        ext = content_type.split("/")[-1]
        filename = f"nano-banana-2-{i+1}.{ext}"
        filepath = output_dir / filename
        
        # 保存
        with open(filepath, "wb") as f:
            f.write(resp.content)
        
        saved_paths.append(filepath)
        print(f"💾 Saved: {filepath}")
    
    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="Generate images with nano-banana-2")
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument("--num-images", type=int, default=1, help="Number of images to generate")
    parser.add_argument(
        "--aspect-ratio",
        choices=["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
        default="auto",
        help="Aspect ratio",
    )
    parser.add_argument(
        "--resolution",
        choices=["0.5K", "1K", "2K", "4K"],
        default="1K",
        help="Resolution",
    )
    parser.add_argument(
        "--output-format",
        choices=["jpeg", "png", "webp"],
        default="png",
        help="Output format",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--web-search", action="store_true", help="Enable web search")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--url-only", action="store_true", help="Print URLs only, don't download")
    
    args = parser.parse_args()
    
    try:
        # 画像生成
        result = generate_image(
            prompt=args.prompt,
            num_images=args.num_images,
            aspect_ratio=args.aspect_ratio,
            resolution=args.resolution,
            output_format=args.output_format,
            seed=args.seed,
            enable_web_search=args.web_search,
        )
        
        # 結果表示
        images = result.get("images", [])
        description = result.get("description", "")
        
        print(f"\n✅ Generated {len(images)} image(s)")
        if description:
            print(f"   Description: {description}")
        
        # URL表示
        for i, img in enumerate(images):
            url = img.get("url")
            if url:
                print(f"   Image {i+1}: {url}")
        
        # 画像保存
        if not args.url_only:
            saved = save_images(result, args.output_dir)
            print(f"\n📁 Saved to: {args.output_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

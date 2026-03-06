#!/usr/bin/env python3
"""Gemini Vision - Analyze images and videos using Google Gemini API"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Dependencies: google-genai, pillow (auto-resolved by uv)

def get_api_key() -> str:
    """Get Gemini API key from environment or file"""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    
    # Try to read from file
    key_file = Path(__file__).parent.parent.parent.parent / "gemini-api-key.txt"
    if key_file.exists():
        content = key_file.read_text().strip()
        if content.startswith("GEMINI_API_KEY="):
            return content.split("=", 1)[1]
        return content
    
    raise ValueError("GEMINI_API_KEY not found. Set environment variable or create gemini-api-key.txt")


def analyze_image(image_paths: list[str], prompt: str, model: str = "gemini-2.0-flash", json_output: bool = False) -> str:
    """Analyze one or more images using Gemini"""
    from google import genai
    from google.genai import types
    from PIL import Image
    
    client = genai.Client(api_key=get_api_key())
    
    # Load images
    contents = []
    for path in image_paths:
        if path.startswith("http"):
            # URL - download first
            import urllib.request
            with tempfile.NamedTemporaryFile(suffix=Path(path).suffix, delete=False) as tmp:
                urllib.request.urlretrieve(path, tmp.name)
                img = Image.open(tmp.name)
                os.unlink(tmp.name)
        else:
            img = Image.open(path)
        contents.append(img)
    
    contents.append(prompt)
    
    response = client.models.generate_content(
        model=model,
        contents=contents
    )
    
    if json_output:
        return json.dumps({"result": response.text}, ensure_ascii=False, indent=2)
    return response.text


def extract_frames(video_path: str, max_frames: int = 10, fps: float = 1.0) -> list[Path]:
    """Extract frames from video using ffmpeg"""
    frames = []
    with tempfile.TemporaryDirectory() as tmpdir:
        output_pattern = Path(tmpdir) / "frame_%04d.jpg"
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps={fps}",
            "-vframes", str(max_frames),
            "-y", str(output_pattern)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        # Collect frames
        for frame in sorted(Path(tmpdir).glob("frame_*.jpg")):
            frames.append(frame)
        
        # Need to copy frames before tempdir is deleted
        result = []
        for frame in frames:
            dest = Path(tempfile.mktemp(suffix=".jpg"))
            dest.write_bytes(frame.read_bytes())
            result.append(dest)
        
        return result


def analyze_video(video_path: str, prompt: str, model: str = "gemini-2.0-flash", 
                  max_frames: int = 10, fps: float = 1.0, json_output: bool = False) -> str:
    """Analyze video by extracting frames and analyzing with Gemini"""
    from google import genai
    from google.genai import types
    from PIL import Image
    
    # Check ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("ffmpeg not found. Install with: apt install ffmpeg")
    
    client = genai.Client(api_key=get_api_key())
    
    # Extract frames
    frames = extract_frames(video_path, max_frames, fps)
    if not frames:
        raise ValueError("No frames extracted from video")
    
    # Load frames
    contents = []
    for frame_path in frames:
        img = Image.open(frame_path)
        contents.append(img)
    
    contents.append(prompt)
    
    response = client.models.generate_content(
        model=model,
        contents=contents
    )
    
    # Cleanup temp frames
    for frame in frames:
        try:
            frame.unlink()
        except:
            pass
    
    if json_output:
        return json.dumps({"result": response.text}, ensure_ascii=False, indent=2)
    return response.text


def main():
    parser = argparse.ArgumentParser(description="Gemini Vision - Analyze images and videos")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Image command
    image_parser = subparsers.add_parser("image", help="Analyze images")
    image_parser.add_argument("images", nargs="+", help="Image paths or URLs")
    image_parser.add_argument("prompt", help="Analysis prompt")
    image_parser.add_argument("--model", "-m", default="gemini-2.0-flash", help="Model name")
    image_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    # Video command
    video_parser = subparsers.add_parser("video", help="Analyze videos")
    video_parser.add_argument("video", help="Video path")
    video_parser.add_argument("prompt", help="Analysis prompt")
    video_parser.add_argument("--model", "-m", default="gemini-2.0-flash", help="Model name")
    video_parser.add_argument("--max-frames", "-f", type=int, default=10, help="Max frames to extract")
    video_parser.add_argument("--fps", type=float, default=1.0, help="Frame extraction rate")
    video_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    try:
        if args.command == "image":
            result = analyze_image(args.images, args.prompt, args.model, args.json)
        elif args.command == "video":
            result = analyze_video(args.video, args.prompt, args.model, 
                                   args.max_frames, args.fps, args.json)
        
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

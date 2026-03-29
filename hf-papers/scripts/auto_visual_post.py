#!/usr/bin/env python3
"""
HuggingFace Papers Auto Visual Post

HF Papers のトップ論文を図解して X/Discord に自動投稿するスクリプト
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# スキルのパス
SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

# hf_papers モジュールを直接インポート
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from hf_papers import fetch_papers as hf_fetch_papers
except ImportError as e:
    print(f"Warning: Could not import hf_papers: {e}")
    hf_fetch_papers = None


def fetch_top_paper(limit: int = 1) -> list[dict]:
    """HuggingFace Papers からトップ論文を取得"""
    if hf_fetch_papers is None:
        print("Error: hf_fetch_papers not available")
        return []

    try:
        papers = hf_fetch_papers(limit=limit)
        return papers
    except Exception as e:
        print(f"Error fetching papers: {e}")
        return []


def generate_visual_explanation(paper: dict) -> dict:
    """論文の図解画像を生成"""
    generate_script = SKILL_DIR.parent / "nano-banana-2" / "scripts" / "generate.py"

    if not generate_script.exists():
        print(f"Warning: generate.py not found at {generate_script}")
        return {"image_url": None, "prompt": None}

    # 論文の内容から画像生成プロンプトを作成
    title = paper.get("title", "")
    summary = paper.get("ai_summary", paper.get("summary", ""))
    keywords = paper.get("ai_keywords", [])

    # 図解画像用のプロンプト
    prompt = f"Scientific illustration explaining {title}. Key concepts: {', '.join(keywords[:5]) if keywords else 'AI research'}. Style: Clean modern infographic academic visualization. Neural network diagrams data flow. Professional colors."

    try:
        # subprocess で generate.py を実行
        result = subprocess.run(
            [
                "python3", str(generate_script),
                "--prompt", prompt,
                "--aspect-ratio", "16:9",
                "--resolution", "1K",
                "--num-images", "1",
                "--output-format", "png",
                "--save",
                "--output-dir", "memory/images/papers",
                "--json"
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(SKILL_DIR.parent.parent)
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data and "images" in data and len(data["images"]) > 0:
                return {
                    "image_url": data["images"][0].get("url"),
                    "local_path": data["images"][0].get("local_path"),
                    "prompt": prompt,
                }
        else:
            print(f"Warning: Image generation failed: {result.stderr}")
    except Exception as e:
        print(f"Warning: Error generating image: {e}")

    return {"image_url": None, "prompt": prompt}


def generate_explanation_text(paper: dict) -> str:
    """論文の解説文を生成"""
    title = paper.get("title", "")
    summary = paper.get("ai_summary", paper.get("summary", ""))
    keywords = paper.get("ai_keywords", [])
    authors = paper.get("authors", [])
    arxiv_id = paper.get("id", "")

    # 解説文を構築
    text = f"""📜 **{title}**

{summary}

🏷️ キーワード: {', '.join(f'#{k}' for k in keywords) if keywords else '#AI #研究'}

👥 著者: {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}

🔗 arXiv: https://arxiv.org/abs/{arxiv_id}

#ONIZUKA_AGI #論文解説
"""

    return text


def post_to_x(text: str, image_path: str | None = None) -> bool:
    """X (Twitter) に投稿"""
    # x-write スキルを使用
    x_write_script = SKILL_DIR.parent / "x-write" / "scripts" / "x_write.py"

    if not x_write_script.exists():
        print("Warning: x_write.py not found, skipping X post")
        return False

    import subprocess

    cmd = ["python3", str(x_write_script), "tweet", "--text", text]
    if image_path:
        cmd.extend(["--media", image_path])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Posted to X successfully")
            return True
        else:
            print(f"❌ Failed to post to X: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error posting to X: {e}")
        return False


def post_to_discord(text: str, image_url: str | None, channel: str = "論文解説") -> bool:
    """Discord に投稿"""
    # message tool を使用（OpenClaw 経由）
    # この関数は OpenClaw 環境から呼ばれるため、
    # 実際の投稿は OpenClaw の message tool に委譲

    print(f"📢 Discord post to #{channel}:")
    print(f"  Text: {text[:100]}...")
    if image_url:
        print(f"  Image: {image_url}")

    # 実際の投稿は外部から行う
    return True


def main():
    parser = argparse.ArgumentParser(description="HF Papers Auto Visual Post")
    parser.add_argument("--paper-limit", type=int, default=1, help="Number of papers to process")
    parser.add_argument("--discord-channel", default="論文解説", help="Discord channel to post")
    parser.add_argument("--x-hashtag", default="#ONIZUKA_AGI", help="X hashtag")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without posting")

    args = parser.parse_args()

    print(f"🚀 Starting HF Papers Auto Visual Post...")
    print(f"  Paper limit: {args.paper_limit}")
    print(f"  Discord channel: #{args.discord_channel}")
    print(f"  X hashtag: {args.x_hashtag}")
    print(f"  Dry run: {args.dry_run}")

    # 1. トップ論文を取得
    print("\n📥 Fetching top papers from HuggingFace...")
    papers = fetch_top_paper(limit=args.paper_limit)

    if not papers:
        print("❌ No papers found")
        return 1

    print(f"✅ Found {len(papers)} paper(s)")

    # 各論文を処理
    for i, paper in enumerate(papers, 1):
        print(f"\n{'='*60}")
        print(f"📄 Processing paper {i}/{len(papers)}: {paper.get('title', 'Unknown')}")
        print(f"{'='*60}")

        # 2. 図解画像を生成
        print("\n🎨 Generating visual explanation...")
        visual = generate_visual_explanation(paper)

        if visual.get("image_url"):
            print(f"✅ Image generated: {visual['image_url']}")
        else:
            print("⚠️ Image generation failed or not available")

        # 3. 解説文を生成
        print("\n📝 Generating explanation text...")
        explanation = generate_explanation_text(paper)
        print(f"✅ Explanation generated ({len(explanation)} chars)")

        # 4. 投稿（dry-runでない場合）
        if not args.dry_run:
            # X に投稿
            print("\n🐦 Posting to X...")
            post_to_x(explanation, visual.get("local_path"))

            # Discord に投稿
            print("\n💬 Posting to Discord...")
            post_to_discord(explanation, visual.get("image_url"), args.discord_channel)
        else:
            print("\n🔍 Dry run - skipping posts")
            print(f"\n--- Explanation ---\n{explanation}\n--- End ---")

    print("\n✅ HF Papers Auto Visual Post completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

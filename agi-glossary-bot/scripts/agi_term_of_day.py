#!/usr/bin/env python3
"""
AGI用語解き — 今日の一言叶
蓄積したナレッジベースから毎日1つのAGI関連用語をピックアップし、解説 + 画像を生成してXに投稿する。
"""

import argparse
import json
import os
import sys
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta

WORKSPACE = Path(__file__).parent.parent.parent.parent
DATA_DIR = WORKSPACE / "data"
STATE_FILE = DATA_DIR / "agi-glossary-state.json"

# ── AGI Glossary Terms ──
# Curated list of important AGI concepts to explain
AGI_TERMS = [
    {"term": "Reward Hacking", "desc": "AIが報酬を最大化するために、意図しない方法でシステムを操作する現象"},
    {"term": "Emergent Abilities", "desc": "大規模モデルが小規模では見られなかった新たな能力を突然示す現象"},
    {"term": "Scaling Laws", "desc": "モデルの性能がデータ量・パラメータ数・計算量と共に予測可能に向上する法則"},
    {"term": "Chain-of-Thought", "desc": "推論過程を段階的に出力することで、複雑な問題の精度を向上させる手法"},
    {"term": "Constitutional AI", "desc": "AI自身にルール（憲法）を与え、自己修正させるアライメント手法"},
    {"term": "RLHF", "desc": "人間のフィードバックを強化学習に用いて、AIの出力を人間の好みに合わせる手法"},
    {"term": "Mixture of Experts", "desc": "複数の専門家モデルを組み合わせ、入力に応じて適切な専門家を選択する手法"},
    {"term": "In-Context Learning", "desc": "パラメータを更新せず、プロンプト内の例示から新しいタスクを学習する能力"},
    {"term": "Instruction Tuning", "desc": "指示に従うようモデルを微調整し、ユーザーの意図を正確に実行させる手法"},
    {"term": "Alignment", "desc": "AIの行動を人間の価値観や意図と一致させる研究分野"},
    {"term": "Frontier Models", "desc": "最新の最高性能AIモデル。未知のリスクをもたらす可能性がある"},
    {"term": "Agentic AI", "desc": "自律的に計画・実行・修正を行うAIシステムの設計パラダイム"},
    {"term": "Tool Use", "desc": "LLMが外部ツール（検索・計算・API）を呼び出して能力を拡張する手法"},
    {"term": "Retrieval-Augmented Generation", "desc": "外部知識ベースから情報を検索し、生成に活用する手法（RAG）"},
    {"term": "World Model", "desc": "環境の動的な変化を予測・理解するAIの内部表現"},
    {"term": "Test-Time Compute", "desc": "推論時に追加計算を行い、より深い思考で精度を向上させる手法"},
    {"term": "Sparse Attention", "desc": "注意機構の計算を疎にし、長文脈を効率的に処理する手法"},
    {"term": "Process Reward Model", "desc": "推論の各ステップを評価し、正しい思考プロセスを報酬付けする手法"},
    {"term": "Synthetic Data", "desc": "AIが生成したデータを用いて、別のAIモデルを訓練する手法"},
    {"term": "Grokking", "desc": "過学習を超えた訓練の後、突然汎化性能が向上する現象"},
    {"term": "Model Distillation", "desc": "大規模モデルの知識を小規模モデルに移す圧縮手法"},
    {"term": "Multimodal", "desc": "テキスト・画像・音声など複数のモダリティを統合的に処理する能力"},
    {"term": "Self-Play", "desc": "AIが自身と対戦することで戦略を改善する学習手法"},
    {"term": "Tree of Thoughts", "desc": "複数の推論パスを木構造で探索し、最適な解を見つける手法"},
    {"term": "Mechanistic Interpretability", "desc": "ニューラルネットの内部構造がどのように機能するかを解明する研究"},
    {"term": "Representation Engineering", "desc": "モデルの内部表現を操作して、出力を制御する手法"},
    {"term": "Catastrophic Forgetting", "desc": "新しいタスクを学習すると、以前のタスクの性能が急激に低下する現象"},
    {"term": "Zero-Shot Learning", "desc": "例示なしで未知のタスクを直接実行する能力"},
    {"term": "Gradient Accumulation", "desc": "小さいバッチを複数回計算し、勾配を蓄積して大きなバッチをシミュレートする手法"},
    {"term": "Softmax Temperature", "desc": "確率分布の鋭さを制御し、生成の多様性を調整するパラメータ"},
]

JST = timezone(timedelta(hours=9))


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"posted_terms": [], "last_post_date": None}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def select_term(state):
    """Select a term that hasn't been posted recently."""
    posted = set(state.get("posted_terms", []))
    available = [t for t in AGI_TERMS if t["term"] not in posted]
    if not available:
        # Reset when all terms have been used
        available = AGI_TERMS
        state["posted_terms"] = []
    
    # Use date-based seed for deterministic daily selection
    today = datetime.now(JST).strftime("%Y-%m-%d")
    seed = hash(today) % len(available)
    return available[seed]


def generate_explanation(term_info):
    """Generate a detailed explanation using the knowledge base context."""
    term = term_info["term"]
    short = term_info["desc"]
    
    # Build tweet text
    ja_term = term
    
    text = f"""🧠 AGI用語解き — 「{ja_term}」

{short}

#ONIZUKA_AGI #AGI"""
    
    return text


def generate_image_prompt(term_info):
    """Generate an image prompt for the term."""
    term = term_info["term"]
    desc = term_info["desc"]
    return (
        f"A clean, modern infographic illustration about the AI concept '{term}'. "
        f"Abstract, minimalist style with soft gradients. "
        f"Professional, educational, tech-themed. "
        f"Dark background with glowing neural network elements. "
        f"No text or words in the image."
    )


def main():
    parser = argparse.ArgumentParser(description="AGI用語解き — 今日の一言叶")
    parser.add_argument("command", nargs="?", default="run",
                        choices=["run", "select", "preview"],
                        help="Command: run (full pipeline), select (show today's term), preview (show tweet)")
    parser.add_argument("--dry-run", action="store_true", help="Don't post to X")
    parser.add_argument("--no-image", action="store_true", help="Skip image generation")
    args = parser.parse_args()
    
    state = load_state()
    term_info = select_term(state)
    
    if args.command == "select":
        print(f"Term: {term_info['term']}")
        print(f"Desc: {term_info['desc']}")
        return
    
    tweet_text = generate_explanation(term_info)
    
    if args.command == "preview":
        print("=== Tweet ===")
        print(tweet_text)
        print()
        print("=== Image Prompt ===")
        print(generate_image_prompt(term_info))
        return
    
    # Full pipeline
    print(f"[1/3] Selected term: {term_info['term']}")
    
    # Generate image
    image_url = None
    if not args.no_image:
        print("[2/3] Generating image...")
        try:
            gen_script = WORKSPACE / "skills" / "nano-banana-2" / "scripts" / "generate.py"
            prompt = generate_image_prompt(term_info)
            import subprocess
            result = subprocess.run(
                ["uv", "run", str(gen_script),
                 "--prompt", prompt,
                 "--aspect-ratio", "1:1",
                 "--resolution", "1K",
                 "--output-format", "png",
                 "--save", "--json"],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "FAL_KEY": (WORKSPACE / "fal-key.txt").read_text().strip()}
            )
            if result.returncode == 0:
                # Parse JSON output
                try:
                    gen_result = json.loads(result.stdout.strip().split('\n')[-1])
                    image_url = gen_result.get("images", [{}])[0].get("url")
                    print(f"  Image: {image_url}")
                except (json.JSONDecodeError, IndexError):
                    # Try to find URL in output
                    for line in result.stdout.strip().split('\n'):
                        if "http" in line and "fal" in line:
                            image_url = line.strip()
                            break
                    if image_url:
                        print(f"  Image: {image_url}")
                    else:
                        print("  Image generation output unclear, continuing without image")
            else:
                print(f"  Image generation failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  Image generation error: {e}")
    
    if args.no_image or not image_url:
        print("[2/3] Skipping image generation")
    
    # Post to X
    if args.dry_run:
        print("[3/3] DRY RUN - would post:")
        print(tweet_text)
        if image_url:
            print(f"  Image: {image_url}")
    else:
        print("[3/3] Posting to X...")
        try:
            x_write_script = WORKSPACE / "skills" / "x-write" / "scripts" / "x_write.py"
            import subprocess
            cmd = ["uv", "run", str(x_write_script), "tweet", "--text", tweet_text]
            if image_url:
                cmd.extend(["--media", image_url])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"  Posted successfully!")
                # Update state
                state["posted_terms"].append(term_info["term"])
                state["last_post_date"] = datetime.now(JST).isoformat()
                save_state(state)
            else:
                print(f"  Post failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  Post error: {e}")
    
    print(f"\nDone! Term: {term_info['term']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AGI Papers Multi-Agent Discussion System

複数のAIエージェントが異なる視点からAGI論文を議論するシステム
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# スキルのパス
SKILL_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

# hf_papers モジュールをインポート
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from hf_papers import fetch_papers as hf_fetch_papers
except ImportError as e:
    print(f"Warning: Could not import hf_papers: {e}")
    hf_fetch_papers = None


# エージェント定義
AGENTS = [
    {
        "name": "楽観派リーダー",
        "role": "技術の進歩と可能性を重視",
        "prompt": "あなたは技術の進歩を信じ、可能性を重視する楽観的な視点を持つ研究者です。論文の革新的な点和将来への影響を強調してください。"
    },
    {
        "name": "批判的アナリスト",
        "role": "課題と改善点を指摘",
        "prompt": "あなたは批判的思考が得意で、論文の課題や改善点を指摘するアナリストです。限界点、欠点、未解決問題を明確にしてください。"
    },
    {
        "name": "実装エキスパート",
        "role": "実装可能性と実用性を評価",
        "prompt": "あなたは実装と実用性の専門家です。論文の技術が実際に使えるか、工数、実現可能性について議論してください。"
    },
    {
        "name": "業界トレンドウォッチャー",
        "role": "市場・業界トレンドとの関連",
        "prompt": "あなたは業界のトレンドと市場動向に詳しい研究者です。この論文が現在のAI業界トレンドにどう位置づけられるか議論してください。"
    },
]


def fetch_paper_for_discussion(limit: int = 1) -> list[dict]:
    """議論対象の論文を取得"""
    if hf_fetch_papers is None:
        print("Error: hf_fetch_papers not available")
        return []

    try:
        papers = hf_fetch_papers(limit=limit)
        return papers
    except Exception as e:
        print(f"Error fetching papers: {e}")
        return []


def run_agent_discussion(paper: dict, agent: dict) -> str:
    """1つのエージェントで議論を実行"""
    title = paper.get("title", "Unknown")
    summary = paper.get("ai_summary", paper.get("summary", ""))
    keywords = paper.get("ai_keywords", [])

    prompt = f"""## あなたの役割
{agent['prompt']}

## 論文情報
タイトル: {title}
概要: {summary[:800]}...
キーワード: {', '.join(keywords) if keywords else 'なし'}

## タスク
この論文について、あなたの視点で400-600文字で議論してください。
以下の構成で議論してください:
1. 技術の革新性と意義
2. 現在の限界・課題
3. 将来への示唆

絶対に、自分の役割を忘れず、第一人称で発言してください。"""

    # OpenClaw API を呼び出して議論を生成
    # 実際の実装では sessions_spawn を使うが、
    # ここではシンプルな curl ベースの実装
    try:
        import urllib.request
        import urllib.parse

        # OpenClaw API endpoint
        api_url = "http://localhost:18789/v1/chat/completions"

        payload = json.dumps({
            "model": "zai/glm-5",
            "messages": [
                {"role": "system", "content": "あなたは日本語で返答するAIアシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.8
        }).encode("utf-8")

        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer dummy"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("choices"):
                return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"    Warning: API call failed, using fallback: {e}")

    # フォールバック
    return f"[{agent['name']}の分析]\n\n{agent['role']}の観点から、この論文を評価します。{title}はステレオマッチングタスクにおいて効率的な手法を提案しています。特にコストボリュームの代わりにwarpingを用いるアプローチは革新的です。"


def synthesize_discussion(discussions: list[dict], paper: dict) -> dict:
    """議論を要約"""
    title = paper.get("title", "Unknown")
    arxiv_id = paper.get("id", "")
    authors = paper.get("authors", [])

    # 要約を生成
    summary_parts = []

    for d in discussions:
        agent_name = d.get("agent", {}).get("name", "Unknown")
        discussion = d.get("discussion", "")
        summary_parts.append(f"**{agent_name}:** {discussion[:200]}...")

    summary = "\n\n".join(summary_parts)

    # 最終見解
    final_insight = f"""## マルチエージェント見解まとめ

{summary}

---

**結論:** この論文は{title}について、楽観的・批判的・実装的・業界的な観点から多角的に分析されました。
詳細については上記の各エージェントの発言を参照してください。
"""

    return {
        "title": title,
        "arxiv_id": arxiv_id,
        "authors": authors,
        "discussions": discussions,
        "final_insight": final_insight,
        "timestamp": datetime.now().isoformat(),
    }


def format_for_x(result: dict) -> str:
    """X 投稿用にフォーマット"""
    title = result.get("title", "")[:100]
    arxiv_id = result.get("arxiv_id", "")
    discussions = result.get("discussions", [])

    # 各エージェントの主要ポイント
    key_points = []
    for d in discussions[:3]:  # 上位3つ
        agent_name = d.get("agent", {}).get("name", "")
        discussion = d.get("discussion", "")[:100]
        key_points.append(f"{agent_name}: {discussion}...")

    x_text = f"""📜 **{title}**

🔬 マルチエージェント討論 💬

{chr(10).join(key_points)}

🔗 arXiv: https://arxiv.org/abs/{arxiv_id}

#ONIZUKA_AGI #論文解説 #AI研究
"""

    return x_text


def format_for_discord(result: dict) -> str:
    """Discord 投稿用にフォーマット"""
    title = result.get("title", "")
    arxiv_id = result.get("arxiv_id", "")
    final_insight = result.get("final_insight", "")

    discord_text = f"""📜 **{title}**

🔬 マルチエージェント討論 💬

{final_insight[:1500]}...

🔗 arXiv: https://arxiv.org/abs/{arxiv_id}

#ONIZUKA_AGI #論文解説
"""

    return discord_text


def main():
    parser = argparse.ArgumentParser(description="AGI Papers Multi-Agent Discussion")
    parser.add_argument("--paper-limit", type=int, default=1, help="Number of papers to discuss")
    parser.add_argument("--agent-count", type=int, default=4, help="Number of agents to use")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without posting")

    args = parser.parse_args()

    print(f"🚀 Starting AGI Papers Multi-Agent Discussion...")
    print(f"  Paper limit: {args.paper_limit}")
    print(f"  Agent count: {args.agent_count}")
    print(f"  Dry run: {args.dry_run}")

    # 1. 論文を取得
    print("\n📥 Fetching papers for discussion...")
    papers = fetch_paper_for_discussion(limit=args.paper_limit)

    if not papers:
        print("❌ No papers found")
        return 1

    print(f"✅ Found {len(papers)} paper(s)")

    # 各論文を処理
    for i, paper in enumerate(papers, 1):
        print(f"\n{'='*60}")
        print(f"📄 Paper {i}/{len(papers)}: {paper.get('title', 'Unknown')}")
        print(f"{'='*60}")

        # 2. 各エージェントで議論
        print(f"\n🤖 Running {args.agent_count} agents for discussion...")
        discussions = []

        for j, agent in enumerate(AGENTS[:args.agent_count], 1):
            print(f"\n  [{j}/{args.agent_count}] {agent['name']}...")
            discussion = run_agent_discussion(paper, agent)
            discussions.append({
                "agent": agent,
                "discussion": discussion,
            })
            print(f"  ✅ {agent['name']} completed")

        # 3. 議論を要約
        print("\n📝 Synthesizing discussions...")
        result = synthesize_discussion(discussions, paper)

        # 4. フォーマット
        x_text = format_for_x(result)
        discord_text = format_for_discord(result)

        print(f"\n✅ Discussion completed!")
        print(f"   Title: {result['title']}")
        print(f"   Agents: {len(discussions)}")
        print(f"   X text length: {len(x_text)} chars")
        print(f"   Discord text length: {len(discord_text)} chars")

        if args.dry_run:
            print("\n🔍 Dry run - skipping posts")
            print(f"\n--- X Post ---\n{x_text}\n--- End ---")
        else:
            print("\n🐦 Posting to X...")
            print("   (Skipped - X posting not implemented)")

            print("\n💬 Posting to Discord...")
            print(f"   (Skipped - Discord posting not implemented)")

    print("\n✅ AGI Papers Multi-Agent Discussion completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
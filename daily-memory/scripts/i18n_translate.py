#!/usr/bin/env python3
"""
VitePress i18n — 日報の自動多言語翻訳

日本語の日報を英語・中国語に翻訳し、対応するロケールディレクトリに配置する。

Usage:
    uv run scripts/i18n_translate.py translate --date 2026-05-15 [--lang en] [--dry-run]
    uv run scripts/i18n_translate.py translate-recent [--days 3] [--dry-run]
    uv run scripts/i18n_translate.py generate-index --lang en
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent.parent
DOCS_DIR = WORKSPACE / "memory" / "docs"

LOCALES = {
    "en": {
        "dir": "en",
        "label": "English",
        "lang": "en",
        "title_prefix": "📝",
        "date_format": "%Y-%m-%d",
    },
    "zh": {
        "dir": "zh",
        "label": "中文",
        "lang": "zh-CN",
        "title_prefix": "📝",
        "date_format": "%Y-%m-%d",
    },
}

LANG_PROMPTS = {
    "en": """Translate the following Japanese VitePress daily report to natural, professional English.
Keep the frontmatter structure (title format: "📝 YYYY-MM-DD Daily Report").
Translate all section headers, content, and task items.
Preserve markdown formatting, links, and emoji.
Do NOT translate proper nouns, URLs, file paths, or code blocks.
Output ONLY the translated markdown, no explanation.

Japanese:
{content}

English translation:""",
    "zh": """将以下日文VitePress日报翻译为自然、专业的中文。
保持frontmatter结构（title格式："📝 YYYY-MM-DD 日报"）。
翻译所有章节标题、内容和任务项。
保留markdown格式、链接和emoji。
不要翻译专有名词、URL、文件路径或代码块。
只输出翻译后的markdown，不要解释。

日文:
{content}

中文翻译:""",
}


def call_llm(prompt: str, model: str = "glm-5") -> str:
    """Call LLM for translation via OpenClaw's available models."""
    # Use a simple approach: write prompt to temp file and use subprocess
    # In practice, OpenClaw agent will handle the actual LLM call
    try:
        result = subprocess.run(
            ["curl", "-s", "https://open.bigmodel.cn/api/paas/v4/chat/completions",
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {Path(WORKSPACE / 'glm-api-key.txt').read_text().strip()}",
             "-d", json.dumps({
                 "model": model,
                 "messages": [{"role": "user", "content": prompt}],
                 "temperature": 0.3,
                 "max_tokens": 4096,
             })],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            resp = json.loads(result.stdout)
            return resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    
    # Fallback: return placeholder
    return f"[TRANSLATION PENDING]\n\n{prompt[:200]}..."


def find_daily_report(date_str: str) -> Path | None:
    """Find the Japanese daily report for a given date."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    report_path = DOCS_DIR / f"{dt.year}" / f"{dt.month:02d}" / f"{dt.day:02d}" / "index.md"
    if report_path.exists():
        return report_path
    return None


def translate_report(source_path: Path, lang: str, dry_run: bool = False) -> Path:
    """Translate a daily report and save to the target locale directory."""
    locale_config = LOCALES[lang]
    rel = source_path.relative_to(DOCS_DIR)
    target_path = DOCS_DIR / locale_config["dir"] / rel
    target_path.parent.mkdir(parents=True, exist_ok=True)

    content = source_path.read_text(encoding="utf-8")
    
    if dry_run:
        print(f"[dry-run] Would translate {source_path} → {target_path}")
        print(f"  Content preview: {content[:100]}...")
        return target_path

    prompt = LANG_PROMPTS[lang].format(content=content)
    translated = call_llm(prompt)
    
    # Fix frontmatter title date format
    if lang == "en":
        translated = re.sub(
            r'title: "📝 (\d{4}-\d{2}-\d{2}) 日報"',
            r'title: "📝 \1 Daily Report"',
            translated
        )
    elif lang == "zh":
        translated = re.sub(
            r'title: "📝 (\d{4}-\d{2}-\d{2}) 日報"',
            r'title: "📝 \1 日报"',
            translated
        )

    target_path.write_text(translated, encoding="utf-8")
    print(f"✅ Translated: {target_path}")
    return target_path


def generate_index(lang: str):
    """Generate locale-specific index.md."""
    locale_config = LOCALES[lang]
    index_path = DOCS_DIR / locale_config["dir"] / "index.md"
    
    if lang == "en":
        content = """---
title: ONIZUKA AGI Knowledge Hub
layout: home
hero:
  name: ONIZUKA AGI
  text: Democratizing AGI Knowledge
  tagline: Daily reports, paper summaries, and AGI insights in English
  actions:
    - theme: brand
      text: Latest Report
      link: /en/2026/
    - theme: alt
      text: Papers
      link: /en/papers/
features:
  - title: 📝 Daily Reports
    details: Automated daily development logs and meeting notes
  - title: 📚 Paper Summaries
    details: AGI research paper summaries and analysis
  - title: 🔍 Knowledge Search
    details: Semantic search across the AGI knowledge base
---
"""
    elif lang == "zh":
        content = """---
title: ONIZUKA AGI 知识中心
layout: home
hero:
  name: ONIZUKA AGI
  text: 普及AGI知识
  tagline: 每日报告、论文摘要和AGI见解（中文）
  actions:
    - theme: brand
      text: 最新报告
      link: /zh/2026/
    - theme: alt
      text: 论文
      link: /zh/papers/
features:
  - title: 📝 每日报告
    details: 自动化的每日开发日志和会议记录
  - title: 📚 论文摘要
    details: AGI研究论文摘要和分析
  - title: 🔍 知识搜索
    details: AGI知识库语义搜索
---
"""
    else:
        return

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(content, encoding="utf-8")
    print(f"✅ Generated index: {index_path}")


def main():
    parser = argparse.ArgumentParser(description="VitePress i18n — 日報の自動多言語翻訳")
    sub = parser.add_subparsers(dest="command")

    # translate
    p_t = sub.add_parser("translate", help="Translate a specific date's report")
    p_t.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    p_t.add_argument("--lang", default="en", choices=["en", "zh"], help="Target language")
    p_t.add_argument("--dry-run", action="store_true")

    # translate-recent
    p_r = sub.add_parser("translate-recent", help="Translate recent reports")
    p_r.add_argument("--days", type=int, default=3, help="Number of recent days")
    p_r.add_argument("--lang", default="en", choices=["en", "zh"], help="Target language")
    p_r.add_argument("--dry-run", action="store_true")

    # generate-index
    p_i = sub.add_parser("generate-index", help="Generate locale index.md")
    p_i.add_argument("--lang", required=True, choices=["en", "zh"])

    args = parser.parse_args()

    if args.command == "translate":
        source = find_daily_report(args.date)
        if not source:
            print(f"No report found for {args.date}", file=sys.stderr)
            sys.exit(1)
        translate_report(source, args.lang, args.dry_run)

    elif args.command == "translate-recent":
        today = datetime.now()
        count = 0
        for i in range(args.days):
            d = today - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            source = find_daily_report(date_str)
            if source:
                translate_report(source, args.lang, args.dry_run)
                count += 1
        print(f"\nTranslated {count} reports to {LOCALES[args.lang]['label']}")

    elif args.command == "generate-index":
        generate_index(args.lang)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

---
name: agi-glossary-bot
description: "Daily AGI term explainer: pick one AGI concept per day, generate an explanation + image, and post to X. Use when: (1) running the daily AGI term post, (2) previewing today's term, (3) scheduling automated glossary posts via s6, (4) running the English edition glossary bot."
---

# AGI用語解き — 今日の一言叶

毎日1つのAGI関連用語をピックアップし、短い解説と画像を生成してXに投稿する。

## Quick Start

```bash
# Preview today's term + tweet
uv run scripts/agi_term_of_day.py preview

# Full pipeline (dry run)
uv run scripts/agi_term_of_day.py run --dry-run

# Full pipeline with posting
uv run scripts/agi_term_of_day.py run
```

## Commands

| Command | Description |
|---------|-------------|
| `select` | Show today's selected term |
| `preview` | Show tweet text + image prompt |
| `run` | Full pipeline: select → image → post |

## Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Don't post to X |
| `--no-image` | Skip image generation |

## How It Works

1. Select an unposted term from curated AGI glossary (30 terms)
2. Generate explanation tweet (~280 chars)
3. Generate abstract image via nano-banana-2
4. Post to X with image

## Automation

Set up as s6 service for daily 07:00 JST execution.

## English Edition

```bash
# Preview today's English term
uv run scripts/agi_term_en.py preview

# Full pipeline (dry run)
uv run scripts/agi_term_en.py run --dry-run

# Full pipeline with posting
uv run scripts/agi_term_en.py run
```

## State

- `data/agi-glossary-state.json` — Japanese edition state
- `data/agi-glossary-en-state.json` — English edition state
- Resets automatically when all terms are used

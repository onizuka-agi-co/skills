---
name: hf-papers
description: "Fetch HuggingFace Daily Papers and generate visual explanations with AI-generated images. Use when: (1) getting latest AI/ML research papers from HuggingFace, (2) creating visual summaries of papers, (3) posting paper explanations to social media or Discord."
---

# HF Papers - HuggingFace Daily Papers Fetcher

Fetch daily papers from HuggingFace and generate visual explanations.

## Quick Start

```bash
# Fetch today's papers
uv run scripts/hf_papers.py fetch

# Fetch with limit
uv run scripts/hf_papers.py fetch --limit 5

# Get specific paper by arXiv ID
uv run scripts/hf_papers.py get 2603.02138

# Generate visual explanation (requires nano-banana-2 skill)
uv run scripts/hf_papers.py explain 2603.02138
```

## Commands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch latest daily papers |
| `get <id>` | Get specific paper by arXiv ID |
| `explain <id>` | Generate visual explanation for a paper |
| `top` | Get top papers by upvotes |

## Output Format

Papers are returned as JSON with:
- `id`: arXiv paper ID
- `title`: Paper title
- `summary`: Full abstract
- `ai_summary`: AI-generated short summary
- `ai_keywords`: Extracted keywords
- `upvotes`: Number of upvotes
- `authors`: List of authors
- `thumbnail`: Preview image URL
- `githubRepo`: GitHub repository URL (if available)

## API Endpoint

```
https://huggingface.co/api/daily_papers
```

## Integration

This skill integrates with:
- **nano-banana-2**: Generate visual explanations
- **x-write**: Post to X/Twitter
- **sunwood-community**: Post to X Community

## Resources

### scripts/
- `hf_papers.py` - Main script for fetching and processing papers

### references/
- `api.md` - API documentation and response format

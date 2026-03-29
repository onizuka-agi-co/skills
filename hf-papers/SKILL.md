---
name: hf-papers
description: "Fetch HuggingFace Daily Papers and arXiv papers, generate visual explanations with AI-generated images. Use when: (1) getting latest AI/ML research papers from HuggingFace or arXiv, (2) creating visual summaries of papers, (3) posting paper explanations to social media or Discord."
---

# HF Papers - AI/ML Papers Fetcher

Fetch daily papers from HuggingFace and arXiv, generate visual explanations.

## Quick Start

### HuggingFace Papers

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

### arXiv Papers

```bash
# Fetch latest AI papers
uv run scripts/arxiv_papers.py fetch

# Fetch with custom query
uv run scripts/arxiv_papers.py fetch --query "cat:cs.AI OR cat:cs.LG" --limit 10

# Get specific paper
uv run scripts/arxiv_papers.py get 2301.07065

# JSON output
uv run scripts/arxiv_papers.py fetch --json
```

## Commands

### HuggingFace (hf_papers.py)

| Command | Description |
|---------|-------------|
| `fetch` | Fetch latest daily papers |
| `get <id>` | Get specific paper by arXiv ID |
| `explain <id>` | Generate visual explanation for a paper |
| `top` | Get top papers by upvotes |

### arXiv (arxiv_papers.py)

| Command | Description |
|---------|-------------|
| `fetch` | Fetch latest papers by query |
| `get <id>` | Get specific paper by arXiv ID |

## Query Examples (arXiv)

```bash
# AI papers
uv run scripts/arxiv_papers.py fetch --query "cat:cs.AI"

# Machine Learning
uv run scripts/arxiv_papers.py fetch --query "cat:cs.LG"

# Computer Vision
uv run scripts/arxiv_papers.py fetch --query "cat:cs.CV"

# NLP
uv run scripts/arxiv_papers.py fetch --query "cat:cs.CL"

# Combined
uv run scripts/arxiv_papers.py fetch --query "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"
```

## Output Format

### HuggingFace Papers

- `id`: arXiv paper ID
- `title`: Paper title
- `summary`: Full abstract
- `ai_summary`: AI-generated short summary
- `ai_keywords`: Extracted keywords
- `upvotes`: Number of upvotes
- `authors`: List of authors
- `thumbnail`: Preview image URL
- `githubRepo`: GitHub repository URL (if available)

### arXiv Papers

- `id`: arXiv paper ID
- `title`: Paper title
- `summary`: Full abstract
- `authors`: List of authors
- `published`: Publication date
- `categories`: arXiv categories
- `link`: arXiv URL
- `pdf_link`: PDF download URL

## API Endpoints

- HuggingFace: `https://huggingface.co/api/daily_papers`
- arXiv: `http://export.arxiv.org/api/query`

## Integration

This skill integrates with:
- **nano-banana-2**: Generate visual explanations
- **x-write**: Post to X/Twitter
- **sunwood-community**: Post to X Community

## AGI Paper Watcher

Weekly AGI paper curation system.

### Commands

```bash
# Select AGI-relevant papers
uv run scripts/agi_watcher.py select --count 2

# Generate weekly report
uv run scripts/agi_watcher.py report --output memory/docs/papers/agi-watcher/YYYY-MM-DD.md

# Filter AGI papers by score
uv run scripts/agi_watcher.py filter --min-score 2.0

# Automated workflow (fetch + select + report)
uv run scripts/agi_watcher.py auto --count 2 --output-dir memory/docs/papers
```

### AGI Keywords

Papers are scored based on these AGI-related keywords:
- Core: AGI, reasoning, planning, world model
- Agents: autonomous agent, multi-agent, tool use
- Learning: meta-learning, few-shot, RLHF
- Architecture: foundation model, scaling law, LLM

### s6 Service

Auto-runs weekly on Monday 09:00:
```
/config/s6-services/agi-paper-watcher/
├── config.env  # Configuration
└── run         # Service script
```

## Resources

### scripts/
- `hf_papers.py` - HuggingFace Daily Papers fetcher
- `arxiv_papers.py` - arXiv API integration
- `agi_watcher.py` - AGI Paper Watcher

### references/
- `api.md` - API documentation

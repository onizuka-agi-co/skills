---
name: agi-knowledge-search
description: "Search and retrieve knowledge from accumulated papers, posts, and daily reports. Use when: (1) searching for specific AGI-related information, (2) finding related papers or discussions, (3) querying the knowledge base for context, (4) discovering connections between topics. Supports semantic search across memory/docs, papers, and X posts."
---

# AGI Knowledge Search

Search and retrieve knowledge from the accumulated AGI knowledge base.

## Quick Start

```bash
# Basic search
uv run skills/agi-knowledge-search/scripts/search.py "transformer architecture"

# Search with filters
uv run skills/agi-knowledge-search/scripts/search.py "AGI reasoning" --type paper --date-after 2026-01-01

# Find related documents
uv run skills/agi-knowledge-search/scripts/search.py "attention mechanism" --related
```

## Data Sources

| Source | Path | Content |
|--------|------|---------|
| Daily Reports | `memory/docs/` | Meeting notes, progress, decisions |
| Papers | `data/papers/` | Paper summaries, analyses |
| X Posts | `data/x/` | Tweet archives, analyses |

## Features

### 1. Full-Text Search
- Search across all markdown files
- Support for Japanese and English
- Date range filtering

### 2. Semantic Search
- Embedding-based similarity search
- Find conceptually related content
- Cross-reference between sources

### 3. Metadata Filtering
- Filter by date, type, tags
- Filter by source (paper/post/report)
- Filter by author/creator

### 4. Related Recommendations
- Suggest related documents
- Topic clustering
- Knowledge graph connections

## Architecture

```
agi-knowledge-search/
├── scripts/
│   ├── search.py         # Main search CLI
│   ├── index.py          # Index builder
│   └── embeddings.py     # Embedding generation
├── references/
│   ├── schema.md         # Data schema
│   └── api.md            # Search API docs
└── SKILL.md
```

## Setup

```bash
# Install dependencies
uv pip install meilisearch-python openai

# Start Meilisearch (if using)
docker run -d -p 7700:7700 getmeili/meilisearch:latest

# Build index
uv run skills/agi-knowledge-search/scripts/index.py
```

## Search Examples

### Find papers about reasoning
```bash
uv run scripts/search.py "reasoning capabilities" --type paper
```

### Find recent discussions about transformers
```bash
uv run scripts/search.py "transformer" --type report --date-after 2026-03-01
```

### Find all mentions of a specific topic
```bash
uv run scripts/search.py "RLHF" --all-sources
```

## Output Format

```json
{
  "query": "transformer architecture",
  "results": [
    {
      "title": "Attention Is All You Need Analysis",
      "source": "paper",
      "date": "2026-03-15",
      "snippet": "...",
      "score": 0.95,
      "path": "data/papers/attention-analysis.md"
    }
  ],
  "total": 5,
  "time_ms": 120
}
```

## Integration

### Discord Bot
Search results can be posted to Discord channels.

### VitePress
Search API can be integrated with VitePress docs.

### OpenClaw
Used by the agent for context retrieval during conversations.

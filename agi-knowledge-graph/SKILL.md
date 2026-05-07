---
name: agi-knowledge-graph
description: "Build and query a local knowledge graph from accumulated AGI papers, posts, and research. Use when: (1) visualizing relationships between papers/authors/concepts, (2) finding connected research topics, (3) exploring citation or thematic links across the knowledge base, (4) generating graph-based insights from collected papers."
---

# AGI Knowledge Graph

Build a local knowledge graph from accumulated AGI research papers and generate interactive visualizations.

## Quick Start

```bash
# Build/update the knowledge graph from collected papers
uv run skills/agi-knowledge-graph/scripts/build_graph.py

# Query the graph
uv run skills/agi-knowledge-graph/scripts/query_graph.py --concept "attention mechanism"

# Generate interactive visualization
uv run skills/agi-knowledge-graph/scripts/visualize.py --output data/graph/index.html
```

## Architecture

```
Papers (memory/docs/papers/)
  ↓ build_graph.py
Graph Data (data/graph/)
  ├── papers.jsonl       # Paper nodes
  ├── entities.jsonl     # Author/Concept/Method nodes
  ├── edges.jsonl        # Relationships
  └── index.html         # Interactive visualization
```

## Entity Types

| Type | Examples | Source |
|------|----------|--------|
| Paper | arXiv papers, HF Daily Papers | `collected-*.json`, `papers/*.md` |
| Author | Researcher names | Paper metadata |
| Concept | "transformer", "reinforcement learning" | Tags, categories, extracted keywords |
| Method | "fine-tuning", "distillation" | Paper summaries |
| Category | cs.AI, cs.CL, cs.CV | arXiv categories |

## Relationship Types

| Edge | Description |
|------|-------------|
| `authored_by` | Paper → Author |
| `uses_method` | Paper → Method |
| `related_concept` | Paper ↔ Concept |
| `categorized_as` | Paper → Category |
| `similar_to` | Paper ↔ Paper (topic similarity) |

## Graph Building Pipeline

1. **Parse papers** from `memory/docs/papers/collected-*.json`
2. **Extract entities** - authors, concepts, methods from metadata and tags
3. **Build edges** - connect papers to entities
4. **Compute similarity** - link related papers via shared concepts
5. **Export** - JSONL for data, HTML for visualization

## Visualization

Generates an interactive HTML page with:
- Force-directed graph layout (D3.js)
- Click nodes to see details
- Filter by category, date, author
- Color-coded by category

## Data Sources

- `memory/docs/papers/collected-*.json` - Paper metadata from HuggingFace/arXiv
- `memory/docs/papers/agi/`, `general/`, `vision/` etc. - Paper summaries
- `data/x/cache/` - X post analysis data

## Resources

### scripts/
- `build_graph.py` - Build/update graph from paper data
- `query_graph.py` - Query graph for connections
- `visualize.py` - Generate interactive HTML visualization

### references/
- `schema.md` - Graph data schema definition

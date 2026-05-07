#!/usr/bin/env python3
"""Build AGI Knowledge Graph from collected papers."""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

# Paths
WORKSPACE = Path(__file__).parent.parent.parent.parent
PAPERS_DIR = WORKSPACE / "memory" / "docs" / "papers"
OUTPUT_DIR = WORKSPACE / "data" / "graph"


def load_collected_papers() -> list[dict]:
    """Load all collected-*.json files."""
    papers = []
    for f in sorted(PAPERS_DIR.glob("collected-*.json")):
        with open(f) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                papers.extend(data)
            else:
                papers.append(data)
    return papers


def normalize_name(name: str) -> str:
    """Normalize entity name to snake_case id."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")


def extract_concepts_from_tags(paper: dict) -> list[str]:
    """Extract concepts from tags and summary keywords."""
    concepts = set()
    tags = paper.get("tags", [])
    for tag in tags:
        concepts.add(tag.strip().lower())
    
    # Extract from categories
    for cat in paper.get("categories", []):
        concepts.add(cat.lower())
    
    return list(concepts)


def build_graph(papers: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build nodes and edges from paper data."""
    nodes = []
    edges = []
    
    paper_ids = set()
    author_ids = set()
    concept_ids = set()
    
    # Track concept frequency
    concept_freq = defaultdict(int)
    
    for paper in papers:
        pid = paper.get("id", paper.get("arxiv_id", ""))
        if not pid:
            continue
        
        paper_node_id = f"paper:{pid}"
        paper_ids.add(paper_node_id)
        
        # Paper node
        nodes.append({
            "id": paper_node_id,
            "type": "paper",
            "title": paper.get("title", ""),
            "arxiv_id": pid,
            "published": paper.get("published", ""),
            "source": paper.get("source", ""),
            "agi_score": paper.get("agi_score", 0),
            "categories": paper.get("categories", []),
            "link": paper.get("link", f"https://arxiv.org/abs/{pid}"),
        })
        
        # Authors
        for author in paper.get("authors", []):
            author_name = author.strip()
            if not author_name:
                continue
            aid = f"author:{normalize_name(author_name)}"
            if aid not in author_ids:
                author_ids.add(aid)
                nodes.append({
                    "id": aid,
                    "type": "author",
                    "name": author_name,
                })
            edges.append({
                "source": paper_node_id,
                "target": aid,
                "type": "authored_by",
            })
        
        # Categories
        for cat in paper.get("categories", []):
            cid = f"category:{normalize_name(cat)}"
            edges.append({
                "source": paper_node_id,
                "target": cid,
                "type": "categorized_as",
            })
        
        # Concepts from tags
        for concept in extract_concepts_from_tags(paper):
            cid = f"concept:{normalize_name(concept)}"
            concept_freq[cid] += 1
            if cid not in concept_ids:
                concept_ids.add(cid)
                nodes.append({
                    "id": cid,
                    "type": "concept",
                    "name": concept,
                    "frequency": 0,  # Updated later
                })
            edges.append({
                "source": paper_node_id,
                "target": cid,
                "type": "related_concept",
                "weight": 1.0,
            })
    
    # Update concept frequencies
    for node in nodes:
        if node["type"] == "concept":
            node["frequency"] = concept_freq.get(node["id"], 0)
    
    # Compute paper similarity (shared concepts)
    paper_concepts = defaultdict(set)
    for edge in edges:
        if edge["type"] == "related_concept":
            paper_concepts[edge["source"]].add(edge["target"])
    
    paper_list = list(paper_concepts.keys())
    for i in range(len(paper_list)):
        for j in range(i + 1, len(paper_list)):
            shared = paper_concepts[paper_list[i]] & paper_concepts[paper_list[j]]
            if len(shared) >= 2:
                edges.append({
                    "source": paper_list[i],
                    "target": paper_list[j],
                    "type": "similar_to",
                    "weight": round(len(shared) / max(len(paper_concepts[paper_list[i]]), len(paper_concepts[paper_list[j]]), 1), 2),
                    "shared_concepts": len(shared),
                })
    
    # Add category nodes
    cat_ids = set()
    for edge in edges:
        if edge["type"] == "categorized_as":
            cat_ids.add(edge["target"])
    for cid in cat_ids:
        cat_name = cid.replace("category:", "")
        nodes.append({
            "id": cid,
            "type": "category",
            "name": cat_name,
        })
    
    return nodes, edges


def write_jsonl(data: list[dict], path: Path):
    """Write data as JSONL."""
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_stats(nodes: list[dict], edges: list[dict]):
    """Write graph statistics."""
    stats = defaultdict(int)
    for n in nodes:
        stats[f"{n['type']}_nodes"] += 1
    for e in edges:
        stats[f"{e['type']}_edges"] += 1
    
    stats_path = OUTPUT_DIR / "stats.json"
    with open(stats_path, "w") as f:
        json.dump(dict(stats), f, indent=2, ensure_ascii=False)
    
    return dict(stats)


def main():
    print("📚 Loading collected papers...")
    papers = load_collected_papers()
    print(f"   Found {len(papers)} papers")
    
    print("🔧 Building knowledge graph...")
    nodes, edges = build_graph(papers)
    
    # Deduplicate nodes
    seen = set()
    unique_nodes = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique_nodes.append(n)
    nodes = unique_nodes
    
    print(f"   Nodes: {len(nodes)}")
    print(f"   Edges: {len(edges)}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    write_jsonl(nodes, OUTPUT_DIR / "nodes.jsonl")
    write_jsonl(edges, OUTPUT_DIR / "edges.jsonl")
    
    stats = write_stats(nodes, edges)
    print(f"📊 Stats: {json.dumps(stats, ensure_ascii=False)}")
    
    print("✅ Knowledge graph built successfully!")
    print(f"   Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Query the AGI Knowledge Graph."""

import json
import sys
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(__file__).parent.parent.parent.parent
GRAPH_DIR = WORKSPACE / "data" / "graph"


def load_graph():
    """Load nodes and edges from JSONL files."""
    nodes = {}
    edges = []
    
    nodes_file = GRAPH_DIR / "nodes.jsonl"
    if nodes_file.exists():
        with open(nodes_file) as f:
            for line in f:
                node = json.loads(line)
                nodes[node["id"]] = node
    
    edges_file = GRAPH_DIR / "edges.jsonl"
    if edges_file.exists():
        with open(edges_file) as f:
            for line in f:
                edges.append(json.loads(line))
    
    return nodes, edges


def query_concept(query: str, nodes: dict, edges: list[dict]) -> list[dict]:
    """Find papers and entities related to a concept."""
    query_lower = query.lower()
    results = []
    
    # Find matching concept nodes
    matching_nodes = []
    for nid, node in nodes.items():
        if node["type"] == "concept" and query_lower in node.get("name", "").lower():
            matching_nodes.append(nid)
        elif node["type"] == "paper" and query_lower in node.get("title", "").lower():
            results.append({
                "type": "paper",
                "title": node["title"],
                "id": node["arxiv_id"],
                "score": 1.0,
            })
    
    # Find papers connected to matching concepts
    for edge in edges:
        if edge["type"] == "related_concept":
            if edge["target"] in matching_nodes:
                paper = nodes.get(edge["source"])
                if paper and paper["type"] == "paper":
                    results.append({
                        "type": "paper",
                        "title": paper["title"],
                        "id": paper["arxiv_id"],
                        "score": edge.get("weight", 1.0),
                    })
    
    # Deduplicate and sort by score
    seen = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    
    return sorted(unique, key=lambda x: x["score"], reverse=True)


def get_neighbors(node_id: str, nodes: dict, edges: list[dict]) -> dict:
    """Get all neighbors of a node."""
    neighbors = {"incoming": [], "outgoing": []}
    
    for edge in edges:
        if edge["source"] == node_id:
            target = nodes.get(edge["target"])
            if target:
                neighbors["outgoing"].append({
                    "node": target,
                    "edge_type": edge["type"],
                    "weight": edge.get("weight"),
                })
        elif edge["target"] == node_id:
            source = nodes.get(edge["source"])
            if source:
                neighbors["incoming"].append({
                    "node": source,
                    "edge_type": edge["type"],
                    "weight": edge.get("weight"),
                })
    
    return neighbors


def print_stats(nodes: dict, edges: list[dict]):
    """Print graph statistics."""
    type_counts = defaultdict(int)
    for n in nodes.values():
        type_counts[n["type"]] += 1
    
    edge_counts = defaultdict(int)
    for e in edges:
        edge_counts[e["type"]] += 1
    
    print("📊 Knowledge Graph Statistics")
    print(f"   Total nodes: {len(nodes)}")
    for t, c in sorted(type_counts.items()):
        print(f"   - {t}: {c}")
    print(f"   Total edges: {len(edges)}")
    for t, c in sorted(edge_counts.items()):
        print(f"   - {t}: {c}")


def main():
    nodes, edges = load_graph()
    
    if not nodes:
        print("❌ No graph data found. Run build_graph.py first.")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print_stats(nodes, edges)
        return
    
    command = sys.argv[1]
    
    if command == "--concept" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        results = query_concept(query, nodes, edges)
        print(f"🔍 Results for '{query}':")
        for r in results[:20]:
            print(f"   [{r['score']:.2f}] {r['title']}")
            print(f"          {r['id']}")
    
    elif command == "--neighbors" and len(sys.argv) >= 3:
        node_id = sys.argv[2]
        neighbors = get_neighbors(node_id, nodes, edges)
        print(f"🔗 Neighbors of {node_id}:")
        print(f"   Incoming ({len(neighbors['incoming'])}):")
        for n in neighbors["incoming"][:10]:
            print(f"     ← [{n['edge_type']}] {n['node'].get('title', n['node'].get('name', n['node']['id']))}")
        print(f"   Outgoing ({len(neighbors['outgoing'])}):")
        for n in neighbors["outgoing"][:10]:
            print(f"     → [{n['edge_type']}] {n['node'].get('title', n['node'].get('name', n['node']['id']))}")
    
    elif command == "--stats":
        print_stats(nodes, edges)
    
    else:
        print("Usage:")
        print("  query_graph.py --concept <query>")
        print("  query_graph.py --neighbors <node_id>")
        print("  query_graph.py --stats")


if __name__ == "__main__":
    main()

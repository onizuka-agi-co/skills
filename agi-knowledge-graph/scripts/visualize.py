#!/usr/bin/env python3
"""Generate interactive HTML visualization of the AGI Knowledge Graph."""

import json
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent.parent
GRAPH_DIR = WORKSPACE / "data" / "graph"


def load_graph():
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


def generate_html(nodes: dict, edges: list[dict]) -> str:
    # Prepare data for D3
    node_data = []
    for nid, n in nodes.items():
        node_data.append({
            "id": nid,
            "type": n["type"],
            "label": n.get("title", n.get("name", nid))[:60],
            "fullTitle": n.get("title", n.get("name", nid)),
            "link": n.get("link", ""),
        })
    
    edge_data = []
    for e in edges:
        if e["source"] in nodes and e["target"] in nodes:
            edge_data.append({
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "weight": e.get("weight", 1),
            })
    
    # Category colors
    type_colors = {
        "paper": "#C41E3A",
        "author": "#4CAF50",
        "concept": "#2196F3",
        "category": "#FFD700",
        "method": "#9C27B0",
    }
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎋 AGI Knowledge Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; }}
  #header {{ padding: 16px 24px; background: #161b22; border-bottom: 1px solid #30363d; }}
  #header h1 {{ font-size: 20px; color: #58a6ff; }}
  #header .stats {{ font-size: 13px; color: #8b949e; margin-top: 4px; }}
  #controls {{ padding: 12px 24px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; gap: 12px; align-items: center; }}
  #controls label {{ font-size: 13px; color: #8b949e; }}
  #controls select, #controls input {{ background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 4px 8px; border-radius: 4px; font-size: 13px; }}
  #controls button {{ background: #238636; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  #controls button:hover {{ background: #2ea043; }}
  .legend {{ display: flex; gap: 16px; margin-left: auto; }}
  .legend-item {{ display: flex; align-items: center; gap: 4px; font-size: 12px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  #graph {{ width: 100%; height: calc(100vh - 120px); }}
  .tooltip {{ position: absolute; background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-size: 13px; max-width: 400px; pointer-events: none; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
  .tooltip h3 {{ color: #58a6ff; margin-bottom: 4px; }}
  .tooltip .type {{ color: #8b949e; text-transform: uppercase; font-size: 11px; }}
  .tooltip a {{ color: #58a6ff; text-decoration: none; }}
</style>
</head>
<body>
<div id="header">
  <h1>🎋 AGI Knowledge Graph</h1>
  <div class="stats">{len(node_data)} nodes · {len(edge_data)} edges</div>
</div>
<div id="controls">
  <label>Filter:</label>
  <select id="typeFilter">
    <option value="all">All types</option>
    <option value="paper">Papers</option>
    <option value="author">Authors</option>
    <option value="concept">Concepts</option>
    <option value="category">Categories</option>
  </select>
  <input type="text" id="searchBox" placeholder="Search nodes..." size="30">
  <button onclick="resetZoom()">Reset</button>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#C41E3A"></div>Paper</div>
    <div class="legend-item"><div class="legend-dot" style="background:#4CAF50"></div>Author</div>
    <div class="legend-item"><div class="legend-dot" style="background:#2196F3"></div>Concept</div>
    <div class="legend-item"><div class="legend-dot" style="background:#FFD700"></div>Category</div>
  </div>
</div>
<div id="graph"></div>
<div class="tooltip" id="tooltip" style="display:none"></div>
<script>
const typeColors = {json.dumps(type_colors)};
const nodeData = {json.dumps(node_data)};
const edgeData = {json.dumps(edge_data)};

const width = document.getElementById('graph').clientWidth;
const height = document.getElementById('graph').clientHeight;

const svg = d3.select('#graph').append('svg')
  .attr('width', width).attr('height', height);

const g = svg.append('g');

svg.call(d3.zoom().scaleExtent([0.1, 8]).on('zoom', (e) => g.attr('transform', e.transform)));

const simulation = d3.forceSimulation(nodeData)
  .force('link', d3.forceLink(edgeData).id(d => d.id).distance(80))
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(width/2, height/2))
  .force('collision', d3.forceCollide().radius(20));

const link = g.append('g').selectAll('line')
  .data(edgeData).join('line')
  .attr('stroke', '#30363d').attr('stroke-width', 1).attr('stroke-opacity', 0.6);

const node = g.append('g').selectAll('circle')
  .data(nodeData).join('circle')
  .attr('r', d => d.type === 'paper' ? 8 : d.type === 'author' ? 4 : 6)
  .attr('fill', d => typeColors[d.type] || '#8b949e')
  .call(d3.drag().on('start', dragStart).on('drag', dragging).on('end', dragEnd))
  .on('mouseover', showTooltip)
  .on('mouseout', hideTooltip);

const tooltip = document.getElementById('tooltip');

function showTooltip(event, d) {{
  tooltip.style.display = 'block';
  tooltip.innerHTML = `<div class="type">${{d.type}}</div><h3>${{d.fullTitle}}</h3>${{d.link ? `<a href="${{d.link}}" target="_blank">${{d.link}}</a>` : ''}}`;
  tooltip.style.left = (event.pageX + 12) + 'px';
  tooltip.style.top = (event.pageY - 12) + 'px';
}}
function hideTooltip() {{ tooltip.style.display = 'none'; }}

simulation.on('tick', () => {{
  link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  node.attr('cx', d => d.x).attr('cy', d => d.y);
}});

function dragStart(event, d) {{ if(!event.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }}
function dragging(event, d) {{ d.fx=event.x; d.fy=event.y; }}
function dragEnd(event, d) {{ if(!event.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }}
function resetZoom() {{ svg.transition().duration(500).call(d3.zoom().transform, d3.zoomIdentity); }}

// Filter
document.getElementById('typeFilter').addEventListener('change', (e) => {{
  const t = e.target.value;
  node.attr('opacity', d => t === 'all' || d.type === t ? 1 : 0.1);
  link.attr('stroke-opacity', d => t === 'all' || d.source.type === t || d.target.type === t ? 0.6 : 0.02);
}});

// Search
document.getElementById('searchBox').addEventListener('input', (e) => {{
  const q = e.target.value.toLowerCase();
  if (!q) {{ node.attr('opacity', 1); link.attr('stroke-opacity', 0.6); return; }}
  const match = new Set(nodeData.filter(d => d.fullTitle.toLowerCase().includes(q)).map(d => d.id));
  node.attr('opacity', d => match.has(d.id) ? 1 : 0.1);
  link.attr('stroke-opacity', d => match.has(d.source.id) || match.has(d.target.id) ? 0.6 : 0.02);
}});
</script>
</body>
</html>"""
    return html


def main():
    nodes, edges = load_graph()
    if not nodes:
        print("❌ No graph data. Run build_graph.py first.")
        return
    
    html = generate_html(nodes, edges)
    output = GRAPH_DIR / "index.html"
    with open(output, "w") as f:
        f.write(html)
    
    print(f"✅ Visualization generated: {output}")
    print(f"   {len(nodes)} nodes, {len(edges)} edges")


if __name__ == "__main__":
    main()

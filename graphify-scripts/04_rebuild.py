import json
import re
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json

GRAPH_JSON = Path("graphify-out/graph.json")
ROOT = "/tmp/pathfinder-md"

graph_json = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
detection = {"total_files": 1, "total_words": 1403621}

extraction = {
    "nodes": [
        {
            "id": n["id"],
            "label": n["label"],
            "file_type": n.get("file_type", "concept"),
            "source_file": n.get("source_file", ""),
            "source_location": n.get("source_location"),
            "source_url": None,
            "captured_at": None,
            "author": None,
            "contributor": None,
        }
        for n in graph_json["nodes"]
    ],
    "edges": [
        {
            "source": l["source"],
            "target": l["target"],
            "relation": l.get("relation", "references"),
            "confidence": l.get("confidence", "EXTRACTED"),
            "confidence_score": l.get("confidence_score", 1.0),
            "source_file": l.get("source_file", ""),
            "source_location": l.get("source_location"),
            "weight": l.get("weight", 1.0),
        }
        for l in graph_json["links"]
    ],
    "hyperedges": graph_json.get("hyperedges", []),
    "input_tokens": 0,
    "output_tokens": 0,
}

G = build_from_json(extraction, root=ROOT, directed=False)
if G.number_of_nodes() == 0:
    raise RuntimeError("Empty graph")

communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: f"Community {cid}" for cid in communities}
questions = suggest_questions(G, communities, labels)

wrote = to_json(G, communities, "graphify-out/graph.json")
if not wrote:
    raise RuntimeError("Export refused to shrink graph")

report = generate(
    G,
    communities,
    cohesion,
    labels,
    gods,
    surprises,
    detection,
    {"input": 0, "output": 0},
    ROOT,
    suggested_questions=questions,
)
Path("graphify-out/GRAPH_REPORT.md").write_text(report, encoding="utf-8")

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities")
print("Top god nodes:")
for g in gods[:8]:
    print(f"  {g['label']}: {g['degree']}°")

import re
import json
from pathlib import Path

SOURCE = Path("/tmp/pathfinder-md/Manuale di Gioco.md")
GRAPH = Path("graphify-out/graph.json")

text = SOURCE.read_text(encoding="utf-8")
lines = text.split("\n")

g = json.loads(GRAPH.read_text(encoding="utf-8"))
node_by_id = {n["id"]: n for n in g["nodes"]}

talent_level_ids = {}
for n in g["nodes"]:
    m = re.match(r"Talento di (\d+)° Livello", n["label"])
    if m:
        talent_level_ids[n["id"]] = int(m.group(1))

stirpe_talent_level_ids = {}
for n in g["nodes"]:
    m = re.match(r"Talento di Stirpe di (\d+)° Livello", n["label"])
    if m:
        stirpe_talent_level_ids[n["id"]] = int(m.group(1))

all_talent_level_ids = {**talent_level_ids, **stirpe_talent_level_ids}

talento_p = re.compile(
    r"\*\*([^*]{3,70})\*\*\s*(?:\[[^\]]*\]\s*\*\*)?\s*TALENTO\s+(\d+)",
    re.IGNORECASE,
)
talento_p2 = re.compile(
    r"\*\*([^*]{3,70})\*\*\s*\[[^\]]*\]\s*\*\*\s*TALENTO\s+(\d+)",
    re.IGNORECASE,
)

talent_levels = {}
for line in lines:
    for pat in (talento_p, talento_p2):
        for m in pat.finditer(line):
            name = m.group(1).strip()
            level = int(m.group(2))
            if len(name) < 3 or len(name) > 80:
                continue
            s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
            nid = f"tmp_pathfinder_md_manuale_di_gioco_{s}"
            if nid in node_by_id:
                talent_levels[nid] = level

level_to_id = {}
for tid, tl in all_talent_level_ids.items():
    level_to_id[tl] = tid

new_edges = []
for tid, tl in talent_levels.items():
    if tl in level_to_id:
        new_edges.append(
            {
                "source": tid,
                "target": level_to_id[tl],
                "relation": "has_talent_level",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": str(SOURCE),
                "source_location": None,
                "weight": 1.0,
            }
        )

g["links"].extend(new_edges)
GRAPH.write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Added {len(new_edges)} has_talent_level edges")
print(f"Total: {len(g['nodes'])} nodes, {len(g['links'])} links")

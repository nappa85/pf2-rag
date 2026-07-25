import re
import json
from pathlib import Path

SOURCE = Path("/tmp/pathfinder-md/Manuale di Gioco.md")
SOURCE_FILE = "/tmp/pathfinder-md/Manuale di Gioco.md"
STEM = "tmp_pathfinder_md_manuale_di_gioco"

text = SOURCE.read_text(encoding="utf-8")
lines = text.split("\n")

# Load existing graph
graph = json.loads(Path("/home/marco/temp/pathfinder/graphify-out/graph.json").read_text(encoding="utf-8"))

# Build lookup of existing node IDs by label (case-insensitive)
existing_nodes = {}
for n in graph["nodes"]:
    existing_nodes[n["label"].lower().strip()] = n

new_edges = []
new_nodes = []
new_node_ids = set(n["id"] for n in graph["nodes"])

SCHOOL_MAP = {
    "amm": "Ammaliamento", "abi": "Abiurazione", "evo": "Evocazione",
    "inv": "Invocazione", "nec": "Necromanzia", "tra": "Trasmutazione",
    "div": "Divinazione", "ill": "Illusione",
}

TRAD_CLASS_MAP = {
    "Arcani": ["Mago", "Bardo", "Stregone"],
    "Divini": ["Chierico", "Campione"],
    "Occulti": ["Bardo", "Stregone"],
    "Primevi": ["Druido", "Ranger"],
}

def make_id(label):
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return f"{STEM}_{s}"

def add_node(label, file_type="concept", extra=None):
    nid = make_id(label)
    if nid in new_node_ids:
        return nid
    node = {
        "id": nid,
        "label": label,
        "file_type": file_type,
        "source_file": SOURCE_FILE,
        "source_location": None,
        "source_url": None,
        "captured_at": None,
        "author": None,
        "contributor": None,
    }
    if extra:
        node.update(extra)
    new_nodes.append(node)
    new_node_ids.add(nid)
    existing_nodes[label.lower().strip()] = node
    return nid

def add_edge(src, tgt, relation, confidence="EXTRACTED", confidence_score=1.0):
    # Deduplicate edges
    key = (src, tgt, relation)
    for e in new_edges:
        if (e["source"], e["target"], e["relation"]) == key:
            return
    new_edges.append({
        "source": src,
        "target": tgt,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "source_file": SOURCE_FILE,
        "source_location": None,
        "weight": 1.0,
    })

# Ensure school nodes exist
school_ids = {}
for code, name in SCHOOL_MAP.items():
    sid = add_node(f"Scuola: {name}", "concept")
    school_ids[code] = sid

# Ensure tradition nodes exist
trad_ids = {}
for trad in ["Arcano", "Divino", "Occulto", "Primevo"]:
    tid = add_node(f"Tradizione: {trad}", "concept")
    trad_ids[trad] = tid

# Ensure spell-level nodes exist
level_ids = {}
for lv in range(1, 11):
    lid = add_node(f"Incantesimo di {lv}° Livello", "concept")
    level_ids[lv] = lid

# Ensure class nodes exist (from existing graph)
class_node_ids = {}
for cls in ["Mago", "Bardo", "Stregone", "Chierico", "Campione", "Druido", "Ranger"]:
    cls_lower = cls.lower()
    if cls_lower in existing_nodes:
        class_node_ids[cls] = existing_nodes[cls_lower]["id"]

# Parse spell lists
# Pattern for section headers: #### TRUCCHETTI ARCANI / #### Incantesimi Arcani di N° Livello / #### INCANTESIMI ARCANI DI 1° LIVELLO
section_pattern = re.compile(
    r'^####\s+(?:TRUCCHETTI|Incantesimi|INCANTESIMI)\s+(Arcani|Divini|Occulti|Primevi|ARCANI|DIVINI|OCCULTI|PRIMEVI)'
    r'(?:\s+di\s+(\d+)°\s+Livello)?',
    re.IGNORECASE
)

# Pattern for spell entries: SpellName (school)
spell_pattern = re.compile(
    r'^[\*\#\s]*([A-ZÀÈÉÌÒÙ][a-zA-ZÀàÈèÉéÌìÒòÙù\s\'\.]+?)\s*(?:[INR]\s*)?\((amm|evo|inv|nec|tra|div|abi|ill)\)'
)

current_tradition = None
current_level = 0
spells_linked = 0
spells_total = 0

# Find spell list sections start
spell_section_start = 21640  # TRUCCHETTI ARCANI line

for i in range(spell_section_start, len(lines)):
    line = lines[i].strip()
    
    # Check for section header
    m = section_pattern.match(line)
    if m:
        trad_raw = m.group(1)
        current_tradition = trad_raw.capitalize()
        if current_tradition == "Arcani": current_tradition = "Arcano"
        elif current_tradition == "Divini": current_tradition = "Divino"
        elif current_tradition == "Occulti": current_tradition = "Occulto"
        elif current_tradition == "Primevi": current_tradition = "Primevo"
        
        if m.group(2):
            current_level = int(m.group(2))
        else:
            # TRUCCHETTI = level 0
            current_level = 0
        continue
    
    # Check for spell entry
    # Remove leading formatting
    clean_line = re.sub(r'^[\*\#\-\s]+', '', line).strip()
    sm = spell_pattern.match(clean_line)
    if not sm:
        continue
    
    spell_name = sm.group(1).strip()
    school_code = sm.group(2)
    
    # Clean up name
    spell_name = re.sub(r"['']+$", '', spell_name)
    spell_name = re.sub(r"[iINR]$", '', spell_name)
    spell_name = spell_name.strip()
    
    if len(spell_name) < 3:
        continue
    
    spells_total += 1
    spell_lower = spell_name.lower()
    
    # Find or create the spell node
    if spell_lower in existing_nodes:
        spell_node = existing_nodes[spell_lower]
        spell_id = spell_node["id"]
    else:
        spell_id = add_node(spell_name, "concept", extra={"category": "incantesimo", "school": school_code})
    
    # Link to tradition
    if current_tradition and current_tradition in trad_ids:
        add_edge(spell_id, trad_ids[current_tradition], "references", "EXTRACTED", 1.0)
    
    # Link to school
    if school_code in school_ids:
        add_edge(spell_id, school_ids[school_code], "references", "EXTRACTED", 1.0)
    
    # Link to level
    if current_level > 0 and current_level in level_ids:
        add_edge(spell_id, level_ids[current_level], "references", "EXTRACTED", 1.0)
    
    # Link to classes that use this tradition
    if current_tradition:
        trad_key = current_tradition.replace("o", "i")  # Arcano -> Arcani
        if trad_key in TRAD_CLASS_MAP:
            for cls in TRAD_CLASS_MAP[trad_key]:
                if cls in class_node_ids:
                    add_edge(spell_id, class_node_ids[cls], "references", "INFERRED", 0.85)
    
    spells_linked += 1

# Also link class-tradition edges
CLASS_TRADITION = [
    ("Mago", "Arcano"), ("Bardo", "Occulto"), ("Bardo", "Arcano"),
    ("Stregone", "Occulto"), ("Stregone", "Arcano"),
    ("Chierico", "Divino"), ("Campione", "Divino"),
    ("Druido", "Primevo"), ("Ranger", "Primevo"),
]
for cls, trad in CLASS_TRADITION:
    if cls in class_node_ids and trad in trad_ids:
        add_edge(class_node_ids[cls], trad_ids[trad], "references", "EXTRACTED", 1.0)

# Also link schools to the Tradizioni Magiche section
scuole_section = add_node("Scuole di Magia", "document")
for code, sid in school_ids.items():
    add_edge(sid, scuole_section, "conceptually_related_to", "EXTRACTED", 1.0)

# Also add focused spell section links
incantesimi_focus_id = add_node("Incantesimi Focalizzati", "concept")

# Parse class-specific spell lists (each class has its own spell section)
# These are in the class chapters - let me scan for focus spell patterns
focus_pattern = re.compile(r'^[\*\#\s]*([A-ZÀÈÉÌÒÙ][a-zA-ZÀàÈèÉéÌìÒòÙù\s\'\.]+?)\s*(?:[INR]\s*)?\((amm|evo|inv|nec|tra|div|abi|ill)\).*focus|focalizz', re.IGNORECASE)

print(f"Spells processed: {spells_total}, linked: {spells_linked}")
print(f"New nodes: {len(new_nodes)}, new edges: {len(new_edges)}")

# Add to graph
graph["nodes"].extend(new_nodes)
graph["links"].extend(new_edges)

# Update community count estimate
out_path = Path("/home/marco/temp/pathfinder/graphify-out/graph.json")
out_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Updated graph: {len(graph['nodes'])} nodes, {len(graph['links'])} links")

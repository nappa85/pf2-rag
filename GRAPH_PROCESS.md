# Pathfinder 2e IT — Graphify Knowledge Graph

## Overview

A traversable, queryable knowledge graph of abilities, talents, spells, classes, and stirpi from the Italian Pathfinder 2nd Edition rulebooks, built with [graphify](https://pypi.org/project/graphify/).

**Current coverage:** Manuale di Gioco (core rulebook).  
**Graph stats:** 1625 nodes, 5736 edges, 73 communities.

## Directory Layout

```
pathfinder/
├── graphify-out/                  # Generated graph outputs
│   ├── graph.json                 # The knowledge graph (nodes + links)
│   ├── graph.html                 # Interactive force-directed visualization
│   ├── query.html                 # Self-contained class/level selector UI
│   ├── GRAPH_REPORT.md            # Audit report with god nodes & communities
│   ├── .graphify_python           # Path to graphify's Python interpreter
│   └── .graphify_root             # Root directory for graphify
├── graphify-scripts/              # Build pipeline scripts
│   ├── 01_extract_graph.py        # Initial extraction from markdown
│   ├── 02_deepen_spells.py        # Spell → tradition/school/level/class edges
│   ├── 03_deepen_levels.py        # Character level, talent level, privileges
│   ├── 04_rebuild.py              # Rebuild graph with community detection
│   └── query_template.html        # query.html before graph.json embedding
├── data/markdown/                 # Root-owned markdown (from Docker)
├── /tmp/pathfinder-md/            # Writable copy of markdown files
└── rag/                           # Separate RAG system (FAISS + BM25 + Ollama)
```

## Source Files

| File | Lines | Content |
|------|-------|---------|
| Manuale di Gioco.md | ~51K | Core rulebook: 12 classes, 6 stirpi, 702 spells, 150 focus spells, 741 talents |
| Guida del Giocatore.md | ~20K | 4 new classes, 5 new stirpi, 26 archetypes, new spells |
| Guida del Game Master.md | — | GM rules (not yet extracted) |
| Bestiario.md | — | Monsters (not yet extracted) |
| Bestiario 2.md | — | Monsters (not yet extracted) |
| Bestiario 3.md | — | Monsters (not yet extracted) |
| Scheda di Riferimento.md | — | Quick reference (not yet extracted) |

## Build Pipeline

### Prerequisites

```bash
# graphify Python (path stored in graphify-out/.graphify_python)
pip install graphify networkx python-louvain

# Markdown source files (must exist in /tmp/pathfinder-md/)
# Copied from root-owned data/markdown/ via:
cp -r data/markdown/* /tmp/pathfinder-md/
```

### Step 1: Initial Extraction

```bash
python graphify-scripts/01_extract_graph.py
```

Extracts from `Manuale di Gioco.md`:
- 6 stirpi (Nano, Elfo, Gnomo, Goblin, Halfling, Umano)
- 12 classi with key characteristics and traditions
- 18 abilità
- ~741 talenti (with level metadata, linked to class/stirpe by line ranges)
- ~702 incantesimi (from spell chapter, lines 21137+)
- ~150 incantesimi focalizzati (from spell chapter, pattern `**NAME FOCALIZZATO N**`)
- Condizioni, Azioni, Tratti
- Subclass concepts (barbarian instincts, druid orders, bard muses, etc.)
- Prerequisite cross-references (talento → abilità/classe/stirpe)
- Stirpe-class typical associations

Output: `graphify-out/.graphify_chunk_01.json`

Then build the graph:
```bash
graphify build --root /tmp/pathfinder-md
graphify cluster
graphify export json
```

### Step 2: Deepen Spell Connections

```bash
python graphify-scripts/02_deepen_spells.py
```

Adds to the existing `graph.json`:
- 8 magic school nodes (Scuola: Ammaliamento, Abiurazione, etc.)
- 4 tradition nodes (Tradizione: Arcano, Divino, Occulto, Primevo)
- 10 spell level nodes (Incantesimo di 1°-10° Livello)
- Spell → tradition edges (from spell list section headers)
- Spell → school edges (from spell school codes in parentheses)
- Spell → spell level edges (from section headers like "Incantesimi Arcani di 3° Livello")
- Spell → class edges (via tradition→class mapping: Arcano→Mago/Bardo/Stregone, etc.)
- Class → tradition edges

Key patterns parsed:
- Section headers: `#### TRUCCHETTI ARCANI` / `#### Incantesimi Arcani di N° Livello`
- Spell entries: `SpellName (school_code)` where codes are amm/abi/evo/inv/nec/tra/div/ill

Tradition→Class mapping:
```
Arcano → Mago, Bardo, Stregone
Divino → Chierico, Campione
Occulto → Bardo, Stregone
Primevo → Druido, Ranger
```

### Step 3: Deepen Level & Progression

```bash
python graphify-scripts/03_deepen_levels.py
```

Adds:
- 20 character level nodes (Livello 1–20)
- Spell level unlock progression per class type
- 11 talent level nodes (Talento di 1°/2°/4°/6°/8°/10°/12°/14°/16°/18°/20° Livello)
- 5 stirpe talent level nodes (Talento di Stirpe di 1°/5°/9°/13°/17° Livello)
- Talent → talent level edges (has_talent_level)
- Talent level → character level edges (requires_character_level)
- Class privilege nodes (from progression tables) with gains_at_level/unlocked_at edges
- Skill rank progression (Grado: Senza Addestrato → Leggendario)

Spell unlock by class type:
```
Full casters (Mago, Stregone, Chierico, Druido, Bardo):
  Char Lv 1→spell 1°, Lv 3→2°, Lv 5→3°, Lv 7→4°, Lv 9→5°,
  Lv 11→6°, Lv 13→7°, Lv 15→8°, Lv 17→9°, Lv 19→10°

Ranger (half caster):
  Char Lv 1→spell 1°, Lv 5→2°, Lv 9→3°, Lv 13→4°, Lv 17→5°

Campione (half caster):
  Char Lv 1→spell 1°, Lv 7→2°, Lv 13→3°, Lv 19→4°
```

After this step, rebuild the graph:
```bash
# Using graphify's Python directly
$(cat graphify-out/.graphify_python) -c "
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_json
# ... (see 04_rebuild.py for full script)
"
graphify export html
```

### Step 4: Talent Level Patch

The `level` attribute on talent nodes is lost during graph rebuild. Run this
inline snippet after step 3 to restore talent→level edges:

```python
import re, json
from pathlib import Path
text = Path('/tmp/pathfinder-md/Manuale di Gioco.md').read_text(encoding='utf-8')
lines = text.split('\n')
g = json.loads(Path('graphify-out/graph.json').read_text(encoding='utf-8'))
node_by_id = {n['id']: n for n in g['nodes']}

talent_level_ids = {}
for n in g['nodes']:
    m = re.match(r'Talento di (\d+)° Livello', n['label'])
    if m: talent_level_ids[n['id']] = int(m.group(1))

talento_p = re.compile(r'\*\*([^*]{3,70})\*\*\s*(?:\[[^\]]*\]\s*\*\*)?\s*TALENTO\s+(\d+)', re.IGNORECASE)
talent_levels = {}
for line in lines:
    for m in talento_p.finditer(line):
        name = m.group(1).strip()
        level = int(m.group(2))
        s = re.sub(r'[^a-z0-9]+', '_', name.lower().strip()).strip('_')
        nid = f'tmp_pathfinder_md_manuale_di_gioco_{s}'
        if nid in node_by_id:
            talent_levels[nid] = level

new_edges = []
for tid, tl in talent_levels.items():
    if tl in {v: k for k, v in talent_level_ids.items()}:
        target_id = [k for k, v in talent_level_ids.items() if v == tl][0]
        new_edges.append({'source': tid, 'target': target_id,
            'relation': 'has_talent_level', 'confidence': 'EXTRACTED',
            'confidence_score': 1.0, 'source_file': '/tmp/pathfinder-md/Manuale di Gioco.md',
            'source_location': None, 'weight': 1.0})

g['links'].extend(new_edges)
Path('graphify-out/graph.json').write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding='utf-8')
```

### Step 5: Build Query UI

```bash
python graphify-scripts/04_build_query_html.py  # (or inline, see below)
graphify export html
```

The query UI (`graphify-out/query.html`) is self-contained — graph JSON is
embedded inline as a JS constant, so it works with `file://` with zero CORS
issues. To rebuild it from the template:

```python
import json
from pathlib import Path
graph_json = Path('graphify-out/graph.json').read_text(encoding='utf-8')
html = Path('graphify-scripts/query_template.html').read_text(encoding='utf-8')
html = html.replace(
    "async function init() {\n  const resp = await fetch('graph.json');\n  graphData = await resp.json();",
    "function init() {\n  graphData = GRAPH_DATA;"
)
html = html.replace('<script>', '<script>const GRAPH_DATA = ' + graph_json + ';</script>\n<script>', 1)
Path('graphify-out/query.html').write_text(html, encoding='utf-8')
```

## Query Examples

### What spells does a 2nd-level Stregone have access to?

```
Select: Stregone, Level 2
→ 49 first-level spells (Allarme, Anatema, Arma Magica, ...)
```

### What talents does a 3rd-level Barbaro have?

```
Select: Barbaro, Level 3
→ 3 lv1 talents (CARICA IMPROVVISA, INCANTESIMI CON PORTATA, MOMENTO DI LUCIDITÀ)
→ 3 lv2 talents (AFFONDO FURIOSO, NESSUNA FUGA, SCROLLARSI DI DOSSO)
```

### Programmatic query (Python)

```python
import json, re
from pathlib import Path

g = json.loads(Path('graphify-out/graph.json').read_text(encoding='utf-8'))
nbi = {n['id']: n for n in g['nodes']}
nbl = {n['label']: n for n in g['nodes']}

SPELL_UNLOCK_FULL = {1:1,2:1,3:2,4:2,5:3,6:3,7:4,8:4,9:5,10:5,
                     11:6,12:6,13:7,14:7,15:8,16:8,17:9,18:9,19:10,20:10}

def query_spells(class_name, char_level):
    cls_id = nbl[class_name]['id']
    max_spl = SPELL_UNLOCK_FULL[char_level]
    spl_ids = {}
    for n in g['nodes']:
        m = re.match(r'Incantesimo di (\d+)\xb0 Livello', n['label'])
        if m: spl_ids[n['id']] = int(m.group(1))
    s2l = {}
    for e in g['links']:
        if e['target'] in spl_ids and e['relation'] == 'references':
            s2l[e['source']] = spl_ids[e['target']]
    result = [(nbi[e['source']]['label'], s2l[e['source']])
              for e in g['links']
              if e['target'] == cls_id and e['relation'] == 'references'
              and s2l.get(e['source'], 0) > 0 and s2l[e['source']] <= max_spl]
    result.sort(key=lambda x: (x[1], x[0]))
    return result
```

## Graph Schema

### Node Types

| file_type | Examples | Count |
|-----------|----------|-------|
| concept | Stregone, Palla di Fuoco, Furia, Livello 5 | ~900 |
| document | Incantesimi, Classi, Stirpi e Background | ~30 |

### Edge Relations

| Relation | Meaning | Direction |
|----------|---------|----------|
| references | Direct reference/dependency | source → target |
| conceptually_related_to | Thematic grouping | item → section |
| has_talent_level | Talent's level tier | talento → livello talento |
| requires_character_level | Level prerequisite | talento livello → livello personaggio |
| unlocks_spell_level | Spell tier available at char level | livello → incantesimo livello |
| gains_at_level | Class gains feature at level | classe → privilegio |
| unlocked_at | Feature unlocks at char level | privilegio → livello |
| upgrades_to | Skill rank progression | rank → next rank |

### Key Structural Nodes

- **Livello 1–20** — character levels, linked consecutively
- **Incantesimo di N° Livello** — spell tiers (1°–10°)
- **Talento di N° Livello** — talent tiers (1/2/4/6/8/10/12/14/16/18/20)
- **Scuola: N** — 8 magic schools
- **Tradizione: N** — 4 magic traditions
- **Grado: N** — 5 skill ranks

### Node ID Format

```
tmp_pathfinder_md_manuale_di_gioco_{normalized_label}
```
where `normalized_label` is lowercase, non-alphanumeric replaced with `_`, stripped.

## Known Issues

- **Focus spells** — 150 focus spells are now extracted from the spell chapter (pattern `**NAME FOCALIZZATO N**`). They are linked to their class and tradition, and to the `Incantesimi Focalizzati` hub node. However, school extraction from focus spell entries is partial (only when the school code appears on the same line).
- **Spell level communities** — Spell level nodes (1°-10°) were initially scattered across 8+ communities. Bidirectional `conceptually_related_to` edges between consecutive levels and to the `Incantesimi` hub now keep them in 2 communities (0 and 32).
- **Bardo class range** — The PDF extraction places Bardo class content at lines 5699-6438 (between Barbaro and Campione), while the `# Bardo` heading at line 15553 is the archetype multiclass section. The `class_ranges` must use 5699-6438 for Bardo, not 15553-16412.
- **Talent pattern3** — Many talents use `**NAME TALENTO N**` (name and TALENTO inside same bold markers), not `**NAME** TALENTO N`. Pattern3 (`\*\*([^*]{3,70}?)\s+TALENTO\s+(\d+)\*\*`) was added to catch 584 previously missed talents.
- **Spell names** have stray characters from PDF extraction: trailing `'`, superscript markers (`i`, `N`, `R`). Partially cleaned in step 2.
- **Bardo/Stregone** share both Arcano and Occulto traditions; the graph links them to spells from both.
- **Alchimista** is not a spellcaster but gets linked to level 1 (for class features).
- **`data/markdown/`** is root-owned (from Docker); must use `/tmp/pathfinder-md/` copy.
- **Parallel subagent dispatch** doesn't work with the current API key; files must be processed sequentially.
- **Graph rebuild** loses the `level` and `category` attributes on nodes; these must be re-injected from the source markdown.

## Next Steps

1. **Guida del Giocatore** — 4 new classes (Fattucchiere, Investigatore, Oracolo, Spadaccino), 5 new stirpi (Coboldo, Felinide, Orco, Rattoide, Tengu), 26 archetypes, new spells
2. **Bestiaries** — monster nodes, traits, habitat
3. **GM Guide** — rules, hazards, environments
4. **Merge** all extractions into unified graph
5. **Focus spells** per class (currently only common spell lists are linked)
6. **Class-specific spell lists** (e.g., Cleric domain spells, Druid order spells)
7. **Equipment/items** extraction
8. **Feat prerequisite chains** (full DAG, not just class/stirpe references)

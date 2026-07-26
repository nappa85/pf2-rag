# Pathfinder 2e IT — Graphify Knowledge Graph

## Overview

A traversable, queryable knowledge graph of abilities, talents, spells, classes, and stirpi from the Italian Pathfinder 2nd Edition rulebooks, built with [graphify](https://pypi.org/project/graphify/).

**Current coverage:** Manuale di Gioco (core rulebook).
**Graph stats:** 1810 nodes, 7746 links, 107 communities.

## Directory Layout

```
pathfinder/
├── graphify-out/                  # Generated graph outputs
│   ├── graph.json                 # The knowledge graph (nodes + links)
│   ├── graph.html                 # Interactive force-directed visualization
│   ├── query.html                 # Self-contained class/level selector UI (2.9MB, embedded graph)
│   ├── GRAPH_REPORT.md            # Audit report with god nodes & communities
│   ├── .graphify_python           # Path to graphify's Python interpreter
│   └── .graphify_root             # Root directory for graphify
├── graphify-scripts/              # Build pipeline scripts
│   ├── 01_extract_graph.py        # Initial extraction from markdown
│   ├── 02_deepen_spells.py        # Spell + focus spell edges (tradition/school/level/class)
│   ├── 03_deepen_levels.py        # Character levels, class-specific talent levels, reweighting
│   ├── 04_rebuild.py              # Rebuild graph with community detection
│   ├── 05_build_query_html.py     # Embeds graph.json into query.html
│   ├── 06_deepen_talents.py       # Skill/general talents, descriptions, conditions
│   ├── patch_graph_html.py        # Patches graph.html to show descriptions in info panel
│   └── query_template.html        # query.html source (before embedding)
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
- ~741 talenti (all 3 patterns, linked to class/stirpe by line ranges, archetype range excluded)
- ~702 incantesimi (from spell chapter, lines 21137+)
- ~150 incantesimi focalizzati (from spell chapter, pattern `**NAME FOCALIZZATO N**`)
- Condizioni, Azioni, Tratti
- Subclass concepts (barbarian instincts, druid orders, bard muses, etc.)
- Prerequisite cross-references (talento → abilità/classe/stirpe)
- Stirpe-class typical associations

Key details:
- **Archetype exclusion**: Lines 15369-16412 contain archetype talents and are skipped (not linked to classes)
- **Stregone range**: 14071-15369 (before archetype section, not 15553)
- **Bardo range**: 5699-6438 (between Barbaro and Campione; `# Bardo` at line 15553 is the archetype section)
- **Three talent patterns**: p1=`**NAME** TALENTO N`, p2=`**NAME** [action] **TALENTO N**`, p3=`**NAME TALENTO N**`

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
- Spell → spell level edges (from section headers like "Incantesimi Arcani di N° Livello")
- Spell → class edges (via tradition→class mapping)
- Class → tradition edges
- **Focus spell extraction** with pattern `**NAME FOCALIZZATO N**`
- Focus spell → class edges (from `**NON COMUNE ... CLASS_NAME ...**` trait lines)
- Focus spell → school edges (from trait lines containing Italian school names)
- Focus spell → spell level edges
- Focus spell → Incantesimi Focalizzati hub

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
- 11 generic talent level nodes (Talento di 1°/2°/.../20° Livello)
- 5 stirpe talent level nodes (Talento di Stirpe di 1°/5°/9°/13°/17° Livello)
- **162 class-specific talent level nodes** (e.g. `Talento di 6° Livello (Guerriero)`) — prevents cross-class talent clustering
- Talent → class-specific talent level edges (replaces generic has_talent_level)
- Talent level → character level edges (requires_character_level)
- Class privilege nodes with gains_at_level/unlocked_at edges
- Skill rank progression (Grado: Senza Addestrato → Leggendario)
- **Spell level cohesion edges** (consecutive levels + hub links)
- **Edge reweighting**: spell→level/school at weight 3.0; spell→class/tradition at 0.5

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
python graphify-scripts/04_rebuild.py
graphify export html
```

### Step 3b: Extract Skill/General Talents & Descriptions

```bash
python graphify-scripts/06_deepen_talents.py
```

Adds:
- **117 skill/general talents** from the Abilità chapter (lines 16412–19331)
- **Talent type classification** (`classe`, `stirpe`, `abilità`, `generico`) on all talent nodes
- **Short descriptions** (first sentence) for ~504 nodes (talents, spells, classes, stirpi)
- **Stirpe prerequisite links** (talento → abilità) from prerequisite text
- **Skill feat level hubs** (`Talento di Abilità di N° Livello`) for levels 2,4,6,...,20
- **General feat level hubs** (`Talento Generico di N° Livello`) for levels 3,7,11,15,19
- Re-injects `level` and `talent_type` attributes lost during graph rebuild

Talent classification logic:
- **Classe**: linked to a class via `conceptually_related_to`
- **Stirpe**: linked to a stirpe via `conceptually_related_to`
- **Abilità**: has `ABILITÀ` trait in the Abilità chapter (98 talents)
- **Generico**: has only `GENERICO` trait, no `ABILITÀ` (19 talents)

Note: In PF2e, all skill feats also have the `GENERICO` trait. The `abilità` type takes
precedence over `generico` when both traits are present.

### Step 4: Build Query UI

```bash
python graphify-scripts/05_build_query_html.py
graphify export html
```

The query UI (`graphify-out/query.html`) is self-contained — graph JSON is
embedded inline as a JS constant, so it works with `file://` with zero CORS
issues. 4 tabs: Incantesimi per Livello, Incantesimi per Scuola, Talenti, Progressione.

Features:
- **Stirpe selector** — optional ancestry filter; shows stirpe talents when selected
- **Talent categories** — Talenti tab shows 4 sections: Classe, Stirpe, Abilità, Generici
- **Descriptions on hover** — tooltip with first-sentence description + level on all chips
- **Talent progression table** — shows when each talent type is gained per level
- Non-casting classes show "non è un incantatore" instead of spell progression tables

### Step 5: Patch graph.html for Descriptions

```bash
python graphify-scripts/patch_graph_html.py
```

Post-processes `graphify-out/graph.html` to:

- Inject `description`, `talent_type`, `level` attributes from `graph.json` into the HTML's `RAW_NODES` JS array
- Patch the `nodesDS` mapping so these fields are available in the vis.js DataSet
- Patch the `showInfo` panel to display description (styled box), talent type (as "Tipo"), and level (as "Livello")
- Set hover tooltip to show short description (≤150 chars) instead of just the label

Must run after `graphify export html`. This is the final step of the pipeline.

## Graph Schema

### Node Types

| file_type | Examples | Count |
|-----------|----------|-------|
| concept | Stregone, Palla di Fuoco, Furia, Livello 5 | ~1750 |
| document | Incantesimi, Classi, Stirpi e Background | ~30 |

### Edge Relations

| Relation | Meaning | Direction |
|----------|---------|----------|
| references | Direct reference/dependency | source → target |
| conceptually_related_to | Thematic grouping | item → section |
| has_talent_level | Talent's level tier (class-specific) | talento → livello talento |
| requires_character_level | Level prerequisite | talento livello → livello personaggio |
| unlocks_spell_level | Spell tier available at char level | livello → incantesimo livello |
| gains_at_level | Class gains feature at level | classe → privilegio |
| unlocked_at | Feature unlocks at char level | privilegio → livello |
| upgrades_to | Skill rank progression | rank → next rank |
| has_talent_level | Talent's skill/general level tier | talento → livello talento abilità/generico |
| inflicts | Spell/ability inflicts a condition | incantesimo → condizione |

### Key Structural Nodes

- **Livello 1–20** — character levels, linked consecutively
- **Incantesimo di N° Livello** — spell tiers (1°–10°), linked consecutively and to Incantesimi hub
- **Talento di N° Livello (CLASS)** — 162 class-specific talent tier nodes
- **Talento di Stirpe di N° Livello (STIRPE)** — stirpe talent tier nodes
- **Scuola: N** — 8 magic schools
- **Tradizione: N** — 4 magic traditions
- **Grado: N** — 5 skill ranks
- **Incantesimi Focalizzati** — hub for focus spells

### Node ID Format

```
tmp_pathfinder_md_manuale_di_gioco_{normalized_label}
```
where `normalized_label` is lowercase, non-alphanumeric replaced with `_`, stripped.

### Edge Weights

| Edge type | Weight | Rationale |
|-----------|--------|-----------|
| spell → level | 3.0 | Keeps spell communities cohesive |
| spell → school | 3.0 | Keeps spell communities cohesive |
| spell → class | 0.5 | Prevents class over-clustering |
| spell → tradition | 0.5 | Prevents tradition over-clustering |
| class-specific talent level → class | 2.0 | Strong class affiliation |
| default | 1.0 | Standard |

## Known Issues

- **Focus spell schools** — ~60 of 150 focus spells still lack school info (trait line too far from spell header or missing entirely)
- **Graph rebuild** loses the `level`, `category`, `talent_type` attributes on nodes; `04_rebuild.py` preserves them via `node_extras`, and `patch_graph_html.py` re-injects them into the HTML
- **Spell names** have stray characters from PDF extraction: trailing `'`, superscript markers (`i`, `N`, `R`). Partially cleaned in step 2.
- **Bardo/Stregone** share both Arcano and Occulto traditions; the graph links them to spells from both.
- **Alchimista** is not a spellcaster but gets linked to level 1 (for class features).
- **`data/markdown/`** is root-owned (from Docker); must use `/tmp/pathfinder-md/` copy.
- **Parallel subagent dispatch** doesn't work with the current API key; files must be processed sequentially.
- **Community count** (107) is higher than ideal — some small communities could be merged with tuned weights.

## Next Steps

1. **Guida del Giocatore** — 4 new classes (Fattucchiere, Investigatore, Oracolo, Spadaccino), 5 new stirpi (Coboldo, Felinide, Orco, Rattoide, Tengu), 26 archetypes, new spells
2. **Bestiaries** — monster nodes, traits, habitat
3. **GM Guide** — rules, hazards, environments
4. **Merge** all extractions into unified graph
5. **Fill remaining focus spell schools** (~60 without school info)
6. **Class-specific spell lists** (e.g., Cleric domain spells, Druid order spells)
7. **Equipment/items** extraction
8. **Feat prerequisite chains** (full DAG, not just class/stirpe references)

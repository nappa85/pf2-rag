import re
import json
from pathlib import Path

SOURCE_FILE = "/tmp/pathfinder-md/Manuale di Gioco.md"
STEM = "tmp_pathfinder_md_manuale_di_gioco"

graph = json.loads(Path("/home/marco/temp/pathfinder/graphify-out/graph.json").read_text(encoding="utf-8"))

existing_by_label = {}
for n in graph["nodes"]:
    existing_by_label[n["label"].lower().strip()] = n
existing_by_id = {n["id"]: n for n in graph["nodes"]}

new_edges = []
new_nodes = []
new_node_ids = set(n["id"] for n in graph["nodes"])

def make_id(label):
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return f"{STEM}_{s}"

def ensure_node(label, extra=None):
    lid = label.lower().strip()
    if lid in existing_by_label:
        return existing_by_label[lid]["id"]
    nid = make_id(label)
    if nid in new_node_ids:
        return nid
    node = {
        "id": nid, "label": label, "file_type": "concept",
        "source_file": SOURCE_FILE, "source_location": None,
        "source_url": None, "captured_at": None, "author": None, "contributor": None,
    }
    if extra:
        node.update(extra)
    new_nodes.append(node)
    new_node_ids.add(nid)
    existing_by_label[lid] = node
    return nid

def add_edge(src, tgt, relation, confidence="EXTRACTED", confidence_score=1.0):
    for e in new_edges:
        if e["source"] == src and e["target"] == tgt and e["relation"] == relation:
            return
    new_edges.append({
        "source": src, "target": tgt, "relation": relation,
        "confidence": confidence, "confidence_score": confidence_score,
        "source_file": SOURCE_FILE, "source_location": None, "weight": 1.0,
    })

# =================================================================
# 1. CHARACTER LEVEL NODES (Livello 1-20)
# =================================================================
level_ids = {}
for lv in range(1, 21):
    lid = ensure_node(f"Livello {lv}")
    level_ids[lv] = lid

# Link consecutive levels
for lv in range(1, 20):
    add_edge(level_ids[lv], level_ids[lv + 1], "references", "INFERRED", 0.95)

# =================================================================
# 2. SPELL LEVEL UNLOCK PER CLASS (standard PF2e progression)
# =================================================================
# Character level -> max spell level for full casters (Mago, Stregone, Chierico, Druido, Bardo)
# Character level -> max spell level for 1/2 casters (Ranger, Campione)
SPELL_UNLOCK_FULL = {
    1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4,
    9: 5, 10: 5, 11: 6, 12: 6, 13: 7, 14: 7, 15: 8, 16: 8,
    17: 9, 18: 9, 19: 10, 20: 10,
}
# Rangers get spells later: 1st spell level at char level 4 (from ranger focus spells etc.)
# Actually in PF2e, Rangers get spell slots starting at specific levels based on their class
# For simplicity, Rangers get 1st level spells at level 1 (focus spells), slots at level 4+
SPELL_UNLOCK_RANGER = {
    1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 2,
    9: 3, 10: 3, 11: 3, 12: 3, 13: 4, 14: 4, 15: 4, 16: 4,
    17: 5, 18: 5, 19: 5, 20: 5,
}
# Champions: 1st focus spells at level 1, but limited slots
SPELL_UNLOCK_CAMPIONE = {
    1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2,
    9: 2, 10: 2, 11: 2, 12: 2, 13: 3, 14: 3, 15: 3, 16: 3,
    17: 3, 18: 3, 19: 4, 20: 4,
}

# Spell level nodes (already exist, find them)
spell_level_ids = {}
for n in graph["nodes"]:
    if n["label"].startswith("Incantesimo di") and "Livello" in n["label"]:
        match = re.search(r"di (\d+)°", n["label"])
        if match:
            spell_level_ids[int(match.group(1))] = n["id"]
# Also add level 0 (trucchetti)
spell_level_ids[0] = ensure_node("Trucchetti (Incantesimo di 0° Livello)")

# Class nodes
class_node_ids = {}
for cls in ["Alchimista", "Barbaro", "Bardo", "Campione", "Canaglia", "Chierico",
            "Druido", "Guerriero", "Mago", "Monaco", "Ranger", "Stregone"]:
    for n in graph["nodes"]:
        if n["label"] == cls:
            class_node_ids[cls] = n["id"]
            break

# Full caster classes
full_casters = ["Mago", "Stregone", "Chierico", "Druido", "Bardo"]
half_casters = {"Ranger": SPELL_UNLOCK_RANGER, "Campione": SPELL_UNLOCK_CAMPIONE}

# Link: Character Level N → Spell Level M (for full casters)
for char_lv in range(1, 21):
    max_spell = SPELL_UNLOCK_FULL[char_lv]
    for spl in range(1, max_spell + 1):
        if spl in spell_level_ids:
            add_edge(level_ids[char_lv], spell_level_ids[spl], "unlocks_spell_level", "EXTRACTED", 1.0)

# Link: Character Level N → Spell Level M (for half casters)
for cls, unlock_map in half_casters.items():
    for char_lv in range(1, 21):
        max_spell = unlock_map[char_lv]
        for spl in range(1, max_spell + 1):
            if spl in spell_level_ids:
                add_edge(level_ids[char_lv], spell_level_ids[spl], f"unlocks_spell_level_{cls.lower()}", "EXTRACTED", 1.0)

# =================================================================
# 3. CLASS-LEVEL → SPELL ACCESS (which class gets which spell levels)
# =================================================================
for cls in full_casters:
    if cls in class_node_ids:
        add_edge(class_node_ids[cls], level_ids[1], "references", "EXTRACTED", 1.0)

for cls in half_casters:
    if cls in class_node_ids:
        add_edge(class_node_ids[cls], level_ids[1], "references", "EXTRACTED", 1.0)

# For non-casting classes, link to level 1 (they get class features)
for cls in ["Barbaro", "Guerriero", "Monaco", "Canaglia", "Alchimista"]:
    if cls in class_node_ids:
        add_edge(class_node_ids[cls], level_ids[1], "references", "EXTRACTED", 1.0)

# =================================================================
# 4. TALENT LEVEL → CHARACTER LEVEL MAPPING
# =================================================================
# Talents have a level (TALENTO 1, TALENTO 2, etc.)
# Class talents unlock at specific character levels:
#   TALENTO 1  → character level 1
#   TALENTO 2  → character level 2
#   TALENTO 4  → character level 4
#   TALENTO 6  → character level 6
#   TALENTO 8  → character level 8
#   TALENTO 10 → character level 10
#   TALENTO 12 → character level 12
#   TALENTO 14 → character level 14
#   TALENTO 16 → character level 16
#   TALENTO 18 → character level 18
#   TALENTO 20 → character level 20
# Stirpe talents: 1, 5, 9, 13, 17

# Talent level nodes
talent_level_ids = {}
for tl in [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]:
    tid = ensure_node(f"Talento di {tl}° Livello")
    talent_level_ids[tl] = tid

# Stirpe talent levels
stirpe_talent_ids = {}
for tl in [1, 5, 9, 13, 17]:
    sid = ensure_node(f"Talento di Stirpe di {tl}° Livello")
    stirpe_talent_ids[tl] = sid

# Link talent levels to character levels
TALENT_TO_CHAR = {1: 1, 2: 2, 4: 4, 6: 6, 8: 8, 10: 10, 12: 12, 14: 14, 16: 16, 18: 18, 20: 20}
for tl, char_lv in TALENT_TO_CHAR.items():
    if tl in talent_level_ids and char_lv in level_ids:
        add_edge(talent_level_ids[tl], level_ids[char_lv], "requires_character_level", "EXTRACTED", 1.0)

# Stirpe talents
STIRPE_TALENT_TO_CHAR = {1: 1, 5: 5, 9: 9, 13: 13, 17: 17}
for tl, char_lv in STIRPE_TALENT_TO_CHAR.items():
    if tl in stirpe_talent_ids and char_lv in level_ids:
        add_edge(stirpe_talent_ids[tl], level_ids[char_lv], "requires_character_level", "EXTRACTED", 1.0)

# =================================================================
# 5. TALENT NODES → TALENT LEVEL NODES
# =================================================================
# Find all talent nodes and link them to their level
for n in graph["nodes"]:
    if "level" in n and n.get("file_type") == "concept":
        talent_lv = n["level"]
        if talent_lv in talent_level_ids:
            add_edge(n["id"], talent_level_ids[talent_lv], "has_talent_level", "EXTRACTED", 1.0)

# =================================================================
# 6. SKILL RANK PROGRESSION
# =================================================================
# Skills unlock ranks at character levels:
#   Addestrato → level 1
#   Esperto → typically level 2-3 (varies by class)
#   Maestro → typically level 7-11
#   Leggendario → typically level 13-19
ranks = {
    "Senza Addestramento": 0,
    "Addestrato": 1,
    "Esperto": 2,
    "Maestro": 3,
    "Leggendario": 4,
}
rank_ids = {}
for rank, val in ranks.items():
    rid = ensure_node(f"Grado: {rank}")
    rank_ids[rank] = rid

# Link ranks in order
rank_order = ["Senza Addestramento", "Addestrato", "Esperto", "Maestro", "Leggendario"]
for i in range(len(rank_order) - 1):
    add_edge(rank_ids[rank_order[i]], rank_ids[rank_order[i + 1]], "upgrades_to", "INFERRED", 0.85)

# Link character levels to skill rank unlocks (approximate)
SKILL_RANK_UNLOCK = {
    1: "Addestrato",   # Everyone gets trained skills at level 1
    3: "Esperto",      # Many classes grant expert at level 2-3
    7: "Maestro",      # Master typically at level 7+
    15: "Leggendario",  # Legendary typically at level 13+
}
for char_lv, rank in SKILL_RANK_UNLOCK.items():
    if char_lv in level_ids and rank in rank_ids:
        add_edge(level_ids[char_lv], rank_ids[rank], "unlocks_skill_rank", "INFERRED", 0.75)

# =================================================================
# 7. CLASS-SPECIFIC PRIVILEGE NODES (from progression tables)
# =================================================================
# Extracted from the manual tables
class_privileges = {
    "Barbaro": {
        1: ["Competenze iniziali", "Furia", "Istinto"],
        2: ["Talento da barbaro"],
        3: ["Negare vantaggio"],
        5: ["Brutalità"],
        7: ["Colosso", "Specializzazione con le armi"],
        9: ["Resistenza furiosa", "Riflessi fulminei"],
        11: ["Furia possente"],
        13: ["Arma furente", "Colosso superiore", "Esperienza con le armature medie"],
        15: ["Specializzazione con le armi superiore", "Volontà indomita"],
        17: ["Furia rapida", "Sensi potenziati"],
        19: ["Armatura del furore", "Devastatore"],
    },
    "Mago": {
        1: ["Competenze iniziali", "Lanciare incantesimi arcani", "Legame arcano", "Scuola arcana", "Tesi arcana"],
        3: ["Incantesimi di 2° livello"],
        5: ["Incantesimi di 3° livello", "Riflessi fulminei"],
        7: ["Incantatore esperto", "Incantesimi di 4° livello"],
        9: ["Incantesimi di 5° livello", "Tempra magica"],
        11: ["Allerta", "Incantesimi di 6° livello"],
        13: ["Incantesimi di 7° livello", "Specializzazione con le armi", "Vesti difensive"],
        15: ["Incantatore magistrale", "Incantesimi di 8° livello"],
        17: ["Incantesimi di 9° livello", "Risolutezza"],
        19: ["Incantatore leggendario"],
    },
    "Stregone": {
        1: ["Competenze iniziali", "Lanciare incantesimi da stregone", "Linea di sangue", "Repertorio degli incantesimi"],
        3: ["Incantesimi di 2° livello", "Incantesimi distintivi"],
        5: ["Incantesimi di 3° livello", "Tempra magica"],
        7: ["Incantatore esperto", "Incantesimi di 4° livello"],
        9: ["Incantesimi di 5° livello", "Riflessi fulminei"],
        11: ["Allerta", "Incantesimi di 6° livello"],
        13: ["Incantesimi di 7° livello", "Specializzazione con le armi", "Vesti difensive"],
        15: ["Incantatore magistrale", "Incantesimi di 8° livello"],
        17: ["Incantesimi di 9° livello", "Risolutezza"],
        19: ["Incantatore leggendario"],
    },
    "Guerriero": {
        1: ["Competenze iniziali"],
        3: ["Competenza con le armi"],
        5: ["Riflessi fulminei"],
        7: ["Arma specialista"],
        9: ["Armatura specialista"],
        11: ["Allerta"],
        13: ["Maestria con le armi"],
        15: ["Armatura del veterano"],
        17: ["Sensi potenziati"],
        19: ["Devastazione"],
    },
    "Chierico": {
        1: ["Competenze iniziali", "Lanciare incantesimi divini", "Divinità e causa", "Dottrina"],
        3: ["Incantesimi di 2° livello"],
        5: ["Incantesimi di 3° livello", "Riflessi fulminei"],
        7: ["Incantatore esperto", "Incantesimi di 4° livello"],
        9: ["Incantesimi di 5° livello", "Tempra magica"],
        11: ["Allerta", "Incantesimi di 6° livello"],
        13: ["Incantesimi di 7° livello", "Specializzazione con le armi", "Vesti difensive"],
        15: ["Incantatore magistrale", "Incantesimi di 8° livello"],
        17: ["Incantesimi di 9° livello", "Risolutezza"],
        19: ["Incantatore leggendario"],
    },
    "Druido": {
        1: ["Competenze iniziali", "Lanciare incantesimi primevi", "Ordine druidico", "Natura selvaggia"],
        3: ["Incantesimi di 2° livello"],
        5: ["Incantesimi di 3° livello", "Riflessi fulminei"],
        7: ["Incantatore esperto", "Incantesimi di 4° livello"],
        9: ["Incantesimi di 5° livello", "Tempra magica"],
        11: ["Allerta", "Incantesimi di 6° livello"],
        13: ["Incantesimi di 7° livello", "Specializzazione con le armi", "Vesti difensive"],
        15: ["Incantatore magistrale", "Incantesimi di 8° livello"],
        17: ["Incantesimi di 9° livello", "Risolutezza"],
        19: ["Incantatore leggendario"],
    },
    "Bardo": {
        1: ["Competenze iniziali", "Lanciare incantesimi occulti", "Musa", "Composizione", "Repertorio degli incantesimi"],
        3: ["Incantesimi di 2° livello"],
        5: ["Incantesimi di 3° livello", "Riflessi fulminei"],
        7: ["Incantatore esperto", "Incantesimi di 4° livello"],
        9: ["Incantesimi di 5° livello", "Tempra magica"],
        11: ["Allerta", "Incantesimi di 6° livello"],
        13: ["Incantesimi di 7° livello", "Specializzazione con le armi", "Vesti difensive"],
        15: ["Incantatore magistrale", "Incantesimi di 8° livello"],
        17: ["Incantesimi di 9° livello", "Risolutezza"],
        19: ["Incantatore leggendario"],
    },
    "Canaglia": {
        1: ["Competenze iniziali", "Racket", "Attacco furtivo"],
        3: ["Evasione"],
        5: ["Riflessi fulminei"],
        7: ["Racket migliorato"],
        11: ["Allerta"],
        13: ["Svitamento"],
        15: ["Maestria furtiva"],
        17: ["Sensi potenziati"],
        19: ["Maestro del tradimento"],
    },
    "Ranger": {
        1: ["Competenze iniziali", "Cacciare la preda", "Vantaggio del cacciatore"],
        3: ["Volontà di ferro"],
        5: ["Esperienza con le armi", "Passo senza tracce"],
        7: ["Eludere", "Sensi vigili", "Specializzazione con le armi"],
        9: ["Vantaggio naturale"],
        11: ["Avanzata selvatica", "Colosso", "Esperienza con le armature medie"],
        13: ["Maestria con le armi"],
        15: ["Eludere migliorato", "Sensi incredibili", "Specializzazione con le armi superiore"],
        17: ["Cacciatore superbo"],
        19: ["Prontezza del cacciatore", "Seconda pelle"],
    },
    "Monaco": {
        1: ["Competenze iniziali", "Posizione da combattimento", "Pugno potente"],
        3: ["Volontà di ferro"],
        5: ["Riflessi fulminei"],
        7: ["Specializzazione con le armi"],
        9: ["Tempra magica"],
        11: ["Allerta", "Colosso"],
        13: ["Maestria con le armi"],
        15: ["Armonizzazione perfetta"],
        17: ["Sensi potenziati"],
        19: ["Maestro assoluto"],
    },
    "Campione": {
        1: ["Competenze iniziali", "Causa", "Campione divino"],
        3: ["Volontà di ferro"],
        5: ["Arma divina", "Attacco di opportunità"],
        7: ["Armatura del campione"],
        9: ["Sguardo luminoso"],
        11: ["Allerta"],
        13: ["Maestria con le armi"],
        15: ["Armatura del campione superiore"],
        17: ["Sensi potenziati"],
        19: ["Campione supremo"],
    },
    "Alchimista": {
        1: ["Competenze iniziali", "Alchimia", "Campo di ricerca", "Formulario"],
        3: ["Alchimia avanzata"],
        5: ["Alchimia potente", "Scoperta del campo di ricerca"],
        7: ["Esperienza con le armi alchemiche", "Infusioni perpetue", "Volontà di ferro"],
        9: ["Allerta", "Doppia miscela", "Esperienza con l'alchimia"],
        11: ["Colosso", "Potenza perpetua"],
        13: ["Esperienza con le armature leggere", "Scoperta del campo di ricerca superiore", "Specializzazione con le armi"],
        15: ["Alchimista solerte", "Eludere"],
        17: ["Maestria alchemica", "Perfezione perpetua"],
        19: ["Maestria con le armature leggere"],
    },
}

# Add privilege nodes and link them
for cls, levels in class_privileges.items():
    for char_lv, privileges in levels.items():
        for priv in privileges:
            priv_id = ensure_node(priv)
            if cls in class_node_ids:
                add_edge(class_node_ids[cls], priv_id, "gains_at_level", "EXTRACTED", 1.0)
            if char_lv in level_ids:
                add_edge(priv_id, level_ids[char_lv], "unlocked_at", "EXTRACTED", 1.0)

# =================================================================
# 8. SPELL-TO-SPELL-LEVEL-ACCESS (query-friendly)
# =================================================================
# For each spell, link it to the character levels where it becomes accessible
# A spell of level N is accessible at character level M where SPELL_UNLOCK_FULL[M] >= N
# For class-specific access, link via the class's tradition

# Find all spell nodes
for n in graph["nodes"]:
    if n.get("category") == "incantesimo" or n.get("school"):
        spell_id = n["id"]
        # Check if this spell already has a spell level link
        has_spell_level = False
        for l in graph["links"]:
            if l["source"] == spell_id and "Incantesimo di" in str(existing_by_id.get(l["target"], {}).get("label", "")):
                has_spell_level = True
                # Get the spell level
                tgt_label = existing_by_id.get(l["target"], {}).get("label", "")
                match = re.search(r"di (\d+)°", tgt_label)
                if match:
                    spell_lv = int(match.group(1))
                    # Link to character levels where this spell level is available
                    for char_lv in range(1, 21):
                        if SPELL_UNLOCK_FULL[char_lv] >= spell_lv:
                            add_edge(spell_id, level_ids[char_lv], "accessible_at_character_level", "INFERRED", 0.85)
                break

# =================================================================
# 8. CLASS-SPECIFIC TALENT LEVEL NODES
# =================================================================
# Generic talent level hubs (e.g. "Talento di 6° Livello") cause unrelated
# class talents to cluster together in the same community. Creating
# class-specific variants (e.g. "Talento di 6° Livello (Guerriero)") fixes this.
CLASS_NAMES = ["Alchimista", "Barbaro", "Bardo", "Campione", "Canaglia", "Chierico",
               "Druido", "Guerriero", "Mago", "Monaco", "Ranger", "Stregone"]
STIRPI = ["Elfo", "Gnomo", "Goblin", "Halfling", "Nano", "Umano"]

class_talent_level_ids = {}
for cls in CLASS_NAMES:
    for lv in [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]:
        label = f"Talento di {lv}° Livello ({cls})"
        nid = ensure_node(label)
        class_talent_level_ids[(cls, lv)] = nid
        if cls in class_node_ids:
            add_edge(nid, class_node_ids[cls], "conceptually_related_to", "INFERRED", 0.9)
        if lv in talent_level_ids:
            add_edge(nid, talent_level_ids[lv], "conceptually_related_to", "INFERRED", 0.8)

stirpe_talent_level_ids = {}
for sp in STIRPI:
    for lv in [1, 5, 9, 13, 17]:
        label = f"Talento di Stirpe di {lv}° Livello ({sp})"
        nid = ensure_node(label)
        stirpe_talent_level_ids[(sp, lv)] = nid
        sp_lower = sp.lower()
        if sp_lower in existing_by_label:
            add_edge(nid, existing_by_label[sp_lower]["id"], "conceptually_related_to", "INFERRED", 0.9)
        if lv in stirpe_talent_ids:
            add_edge(nid, stirpe_talent_ids[lv], "conceptually_related_to", "INFERRED", 0.8)

# Build talent→class mapping from existing edges
stirpe_node_ids = {sp.lower(): existing_by_label[sp.lower()]["id"] for sp in STIRPI if sp.lower() in existing_by_label}
stirpe_id_set = set(stirpe_node_ids.values())
class_id_set = set(class_node_ids.values())

talent_to_class = {}
talent_to_stirpe = {}
for e in graph["links"]:
    if e["relation"] == "conceptually_related_to":
        if e["target"] in class_id_set:
            talent_to_class[e["source"]] = e["target"]
        elif e["target"] in stirpe_id_set:
            talent_to_stirpe[e["source"]] = e["target"]

class_id_to_name = {v: k for k, v in class_node_ids.items()}
stirpe_id_to_name = {v: k.split()[0].title() for k, v in stirpe_node_ids.items() if v in stirpe_id_set}

# Re-wire has_talent_level edges to class-specific versions
old_has_indices = []
new_has_edges = []
for i, e in enumerate(graph["links"]):
    if e["relation"] != "has_talent_level":
        continue
    old_has_indices.append(i)
    talent_id = e["source"]
    old_target = e["target"]
    level = None
    for lv, tid in talent_level_ids.items():
        if tid == old_target:
            level = lv
            break
    for lv, tid in stirpe_talent_ids.items():
        if tid == old_target:
            level = lv
            break
    if level is None:
        continue
    cls_id = talent_to_class.get(talent_id)
    if cls_id:
        cls_name = class_id_to_name.get(cls_id)
        if cls_name and (cls_name, level) in class_talent_level_ids:
            new_has_edges.append((talent_id, class_talent_level_ids[(cls_name, level)]))
            continue
    sp_id = talent_to_stirpe.get(talent_id)
    if sp_id:
        sp_name = stirpe_id_to_name.get(sp_id)
        if sp_name and (sp_name, level) in stirpe_talent_level_ids:
            new_has_edges.append((talent_id, stirpe_talent_level_ids[(sp_name, level)]))
            continue
    new_has_edges.append((talent_id, old_target))

graph["links"] = [e for i, e in enumerate(graph["links"]) if i not in set(old_has_indices)]
for src, tgt in new_has_edges:
    add_edge(src, tgt, "has_talent_level", "EXTRACTED", 1.0)

print(f"Replaced {len(old_has_indices)} has_talent_level edges with class-specific ones")

# =================================================================
# 9. SPELL LEVEL COHESION EDGES
# =================================================================
# Consecutive spell level nodes and hub links keep spell communities together
incanti_id = existing_by_label.get("incantesimi", {}).get("id")
for lv in range(1, 10):
    if lv in spell_level_ids and lv + 1 in spell_level_ids:
        add_edge(spell_level_ids[lv], spell_level_ids[lv + 1], "conceptually_related_to", "INFERRED", 0.95)
        add_edge(spell_level_ids[lv + 1], spell_level_ids[lv], "conceptually_related_to", "INFERRED", 0.95)

if incanti_id:
    for lv, sid in spell_level_ids.items():
        add_edge(sid, incanti_id, "conceptually_related_to", "INFERRED", 0.95)

foc_hub = existing_by_label.get("incantesimi focalizzati", {}).get("id")
if foc_hub and incanti_id:
    add_edge(foc_hub, incanti_id, "conceptually_related_to", "INFERRED", 0.95)

# =================================================================
# 10. EDGE REWEIGHTING
# =================================================================
# Boost spell→level/school edges (weight 3.0) to keep spells cohesive;
# reduce spell→class/tradition edges (weight 0.5) to prevent class over-clustering
modified = 0
for e in graph["links"]:
    src = existing_by_id.get(e["source"], {})
    tgt = existing_by_id.get(e["target"], {})
    src_lbl = src.get("label", "")
    tgt_lbl = tgt.get("label", "")

    is_level = src_lbl.startswith("Incantesimo di") or tgt_lbl.startswith("Incantesimo di")
    is_school = src_lbl.startswith("Scuola:") or tgt_lbl.startswith("Scuola:")
    is_class = e["source"] in class_id_set or e["target"] in class_id_set
    is_trad = src_lbl.startswith("Tradizione:") or tgt_lbl.startswith("Tradizione:")

    if is_level:
        e["weight"] = 3.0
        modified += 1
    elif is_school:
        e["weight"] = 3.0
        modified += 1
    elif is_trad:
        e["weight"] = 0.5
        modified += 1
    elif is_class:
        e["weight"] = 0.5
        modified += 1

print(f"Reweighted {modified} edges")

# =================================================================
# WRITE OUTPUT
# =================================================================
graph["nodes"].extend(new_nodes)
graph["links"].extend(new_edges)

out_path = Path("/home/marco/temp/pathfinder/graphify-out/graph.json")
out_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Added {len(new_nodes)} new nodes, {len(new_edges)} new edges")
print(f"Total: {len(graph['nodes'])} nodes, {len(graph['links'])} links")

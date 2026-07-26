import re
import json
from pathlib import Path

SOURCE_FILE = "data/markdown/Manuale di Gioco.md"
STEM = "tmp_pathfinder_md_manuale_di_gioco"

lines = Path(SOURCE_FILE).read_text(encoding="utf-8").splitlines()
graph = json.loads(Path("graphify-out/graph.json").read_text(encoding="utf-8"))

existing_by_label = {}
for n in graph["nodes"]:
    existing_by_label[n["label"].lower().strip()] = n
existing_by_id = {n["id"]: n for n in graph["nodes"]}


def normalize_for_matching(name):
    s = name.lower().strip()
    s = re.sub(r"[iNnRr]$", "", s)
    s = re.sub(r"[iNnRr],.*$", "", s)
    s = re.sub(r"à[iNnRr]", "à", s)
    s = re.sub(r"è[iNnRr]", "è", s)
    s = re.sub(r"ì[iNnRr]", "ì", s)
    s = re.sub(r"ò[iNnRr]", "ò", s)
    s = re.sub(r"ù[iNnRr]", "ù", s)
    return s.strip()

new_edges = []
new_nodes = []
new_node_ids = set(n["id"] for n in graph["nodes"])

ABILITA_NAMES = [
    "Acrobazia", "Arcano", "Artigianato", "Atletica", "Diplomazia",
    "Esibizione", "Furtività", "Furto", "Inganno", "Intimidazione",
    "Medicina", "Natura", "Occultismo", "Percezione", "Religione",
    "Rappresentare", "Società", "Sopravvivenza"
]
CLASS_NAMES = [
    "Alchimista", "Barbaro", "Bardo", "Campione", "Canaglia", "Chierico",
    "Druido", "Guerriero", "Mago", "Monaco", "Ranger", "Stregone"
]
STIRPI = ["Elfo", "Gnomo", "Goblin", "Halfling", "Nano", "Umano"]


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


def add_edge(src, tgt, relation, confidence="EXTRACTED", confidence_score=1.0, weight=1.0):
    for e in new_edges:
        if e["source"] == src and e["target"] == tgt and e["relation"] == relation:
            return
    new_edges.append({
        "source": src, "target": tgt, "relation": relation,
        "confidence": confidence, "confidence_score": confidence_score,
        "source_file": SOURCE_FILE, "source_location": None, "weight": weight,
    })


def extract_first_sentence(text):
    if not text:
        return ""
    clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    clean = re.sub(r"#+\s*", "", clean)
    clean = re.sub(r"-$", "", clean)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀÈÉÌÒÙ])", clean)
    return (sentences[0] if sentences else clean)[:200]


# =================================================================
# 1. EXTRACT SKILL/GENERAL TALENTS FROM ABILITÀ CHAPTER
# =================================================================
abilita_section_id = ensure_node("Talenti di Abilità e Generici", extra={"talent_type": "hub"})
abilita_ids = {}
for ab in ABILITA_NAMES:
    ab_lower = ab.lower()
    if ab_lower in existing_by_label:
        abilita_ids[ab] = existing_by_label[ab_lower]["id"]

skill_generic_talents = []
talent_patterns = [
    re.compile(r"\*\*([^*]{3,70})\*\*\s*\[[^\]]*\]\s*\*\*\s*TALENTO\s+(\d+)", re.IGNORECASE),
    re.compile(r"\*\*([^*]{3,70}?)\s+TALENTO\s+(\d+)\*\*", re.IGNORECASE),
    re.compile(r"\*\*([^*]{3,70})\*\*\s*(?:\[[^\]]*\]\s*\*\*)?\s*TALENTO\s+(\d+)", re.IGNORECASE),
]

for i in range(16412, 19331):
    line = lines[i]
    m = None
    for pat in talent_patterns:
        m = pat.search(line)
        if m:
            break
    if not m:
        continue
    name = m.group(1).strip()
    level = int(m.group(2))
    if name.upper() in ("TALENTO", "ABILITÀ", "GENERICO") or len(name) < 3:
        continue
    if re.match(r"^\[(one-action|two-actions|three-actions|reaction|free-action)\]$", name, re.IGNORECASE):
        continue

    traits_found = []
    prereq_found = ""
    desc_found = ""
    ability_prereq = None

    for j in range(i + 1, min(i + 12, 19331)):
        tline = lines[j].strip()
        if not tline:
            continue
        nm = re.search(r"TALENTO\s+\d+", tline)
        if nm and j > i + 1:
            break
        trait_match = re.match(
            r"^#{1,4}\s*\*{0,2}((?:ABILITÀ|GENERICO|MANEGGIARE|PAUSA|SEGRETO|CONCENTRAZIONE|ESPLORAZIONE|EMOZIONE|INCAPACITAZIONE|PAURA|FORTUNA|AUDITIVO|VISIVO|METAMORFOSI|PRIMEVO|TRASMUTAZIONE|ARCANO|DIVINO|OCCULTO|COMUNE|NON COMUNE|RARO|UNICO)[^\*]*?)\*{0,2}\s*$",
            tline, re.IGNORECASE
        )
        if trait_match:
            traits_found.append(trait_match.group(1).strip())
            continue
        bold_trait = re.match(
            r"^\*\*((?:ABILITÀ|GENERICO|MANEGGIARE|PAUSA|SEGRETO|CONCENTRAZIONE|ESPLORAZIONE|EMOZIONE|INCAPACITAZIONE|PAURA|FORTUNA)[^*]*?)\*\*$",
            tline
        )
        if bold_trait:
            traits_found.append(bold_trait.group(1).strip())
            continue
        pm = re.search(r"\*\*Prerequisiti?\*\*\s*(.+)", tline)
        if pm:
            prereq_found = pm.group(1).strip()
            for ab in ABILITA_NAMES:
                if ab.lower() in prereq_found.lower():
                    ability_prereq = ab
                    break
            continue
        if tline.startswith("**Speciale") or tline.startswith("**Successo") or tline.startswith("**Fallimento") or tline.startswith("**Critico") or tline.startswith("**Innesco"):
            continue
        if tline.startswith("!["):
            continue
        if not desc_found and len(tline) > 15 and not tline.startswith("#"):
            if not re.match(r"^\*\*(?:ABILITÀ|GENERICO|NON COMUNE)", tline):
                desc_found = tline[:300]
                break

    has_abilita = any("ABILIT" in t.upper() for t in traits_found)
    has_generico = any("GENERICO" in t.upper() for t in traits_found)
    ttype = "abilità" if has_abilita else ("generico" if has_generico else "generico")
    short_desc = extract_first_sentence(desc_found)

    skill_generic_talents.append({
        "name": name, "level": level, "talent_type": ttype,
        "prereqs": prereq_found, "ability_prereq": ability_prereq,
        "desc": short_desc, "line": i + 1,
    })

print(f"Extracted {len(skill_generic_talents)} skill/general talents from Abilità chapter")

# Add skill/general talent nodes
for t in skill_generic_talents:
    tid = ensure_node(t["name"], extra={
        "level": t["level"],
        "talent_type": t["talent_type"],
        "description": t["desc"],
    })
    add_edge(tid, abilita_section_id, "conceptually_related_to", "EXTRACTED", 1.0)

    # Link to ability if there's a prerequisite ability
    if t["ability_prereq"] and t["ability_prereq"] in abilita_ids:
        add_edge(tid, abilita_ids[t["ability_prereq"]], "references", "EXTRACTED", 1.0)

    # Link to talent level nodes
    talent_level_label = f"Talento di {t['level']}° Livello"
    talent_level_lower = talent_level_label.lower()
    if talent_level_lower in existing_by_label:
        add_edge(tid, existing_by_label[talent_level_lower]["id"], "has_talent_level", "EXTRACTED", 1.0)

    # Also link to class-specific talent level nodes for all classes
    # (these talents are available to ALL classes)
    for cls in CLASS_NAMES:
        cls_tal_label = f"Talento di {t['level']}° Livello ({cls})"
        cls_tal_lower = cls_tal_label.lower()
        if cls_tal_lower in existing_by_label:
            add_edge(tid, existing_by_label[cls_tal_lower]["id"], "has_talent_level", "EXTRACTED", 1.0, weight=0.3)

# =================================================================
# 2. EXTRACT DESCRIPTIONS FOR EXISTING NODES
# =================================================================
descriptions = {}

# --- Class talent descriptions ---
class_ranges = [
    ("Alchimista", 3867, 4717),
    ("Barbaro", 4717, 5675),
    ("Bardo", 5699, 6438),
    ("Campione", 6438, 7398),
    ("Canaglia", 7398, 8312),
    ("Chierico", 8312, 9255),
    ("Druido", 9255, 10212),
    ("Guerriero", 10212, 11339),
    ("Mago", 11339, 12105),
    ("Monaco", 12105, 13110),
    ("Ranger", 13110, 14071),
    ("Stregone", 14071, 15369),
]

ARCHETYPE_START = 15369
for cls_name, cstart, cend in class_ranges:
    i = cstart
    while i < cend:
        line = lines[i]
        m = None
        for pat in talent_patterns:
            m = pat.search(line)
            if m:
                break
        if m:
            name = m.group(1).strip()
            level = int(m.group(2))
            if name.upper() not in ("TALENTO", "ABILITÀ", "GENERICO") and len(name) >= 3:
                # Find description
                desc = ""
                for j in range(i + 1, min(i + 12, cend)):
                    tline = lines[j].strip()
                    if not tline:
                        continue
                    if re.search(r"TALENTO\s+\d+", tline) and j > i + 1:
                        break
                    if tline.startswith("#") or tline.startswith("**Prerequis") or tline.startswith("**Speciale"):
                        continue
                    if tline.startswith("!["):
                        continue
                    if len(tline) > 15 and not re.match(r"^\*\*(?:ABILITÀ|GENERICO)", tline):
                        desc = tline[:300]
                        break
                key = name.lower().strip()
                if key not in descriptions:
                    descriptions[key] = {
                        "desc": extract_first_sentence(desc),
                        "talent_type": "classe",
                        "level": level,
                    }
        i += 1

# --- Stirpe talent descriptions ---
stirpe_ranges = [
    ("Elfo", 1442, 1722),
    ("Gnomo", 1722, 2002),
    ("Goblin", 2002, 2290),
    ("Halfling", 2290, 2562),
    ("Nano", 2562, 2842),
    ("Umano", 2842, 3867),
]
for sp_name, sp_start, sp_end in stirpe_ranges:
    i = sp_start
    while i < sp_end:
        line = lines[i]
        m = None
        for pat in talent_patterns:
            m = pat.search(line)
            if m:
                break
        if m:
            name = m.group(1).strip()
            level = int(m.group(2))
            if name.upper() not in ("TALENTO", "ABILITÀ", "GENERICO") and len(name) >= 3:
                desc = ""
                for j in range(i + 1, min(i + 12, sp_end)):
                    tline = lines[j].strip()
                    if not tline:
                        continue
                    if re.search(r"TALENTO\s+\d+", tline) and j > i + 1:
                        break
                    if tline.startswith("#") or tline.startswith("**Prerequis") or tline.startswith("**Speciale"):
                        continue
                    if tline.startswith("!["):
                        continue
                    if len(tline) > 15 and not re.match(r"^\*\*(?:ABILITÀ|GENERICO)", tline):
                        desc = tline[:300]
                        break
                key = name.lower().strip()
                if key not in descriptions:
                    descriptions[key] = {
                        "desc": extract_first_sentence(desc),
                        "talent_type": "stirpe",
                        "level": level,
                    }
        i += 1

# --- Spell descriptions ---
# The spell chapter has a bold list with one-line descriptions:
# **SpellName(school):** Description
# Graph nodes may have PDF artifacts (e.g., "Protezionen" vs "Protezione"),
# so we build a descriptions map from the clean bold-list names and then
# match them against graph nodes with fuzzy normalization.
spell_section_start = 21137

# Phase 1: Extract from bold list (cleanest source)
spell_bold_pattern = re.compile(
    r"\*\*([A-ZÀÈÉÌÒÙ][^\*]+?)\s*[iNnRr]?\s*\((amm|abi|evo|inv|nec|tra|div|ill)\):\*\*\s*(.+)"
)
for i in range(spell_section_start, len(lines)):
    line = lines[i].strip()
    m = spell_bold_pattern.match(line)
    if m:
        raw_name = re.sub(r"[iNnRr]$", "", m.group(1)).strip()
        desc_text = m.group(3).strip()
        key = raw_name.lower().strip()
        if key not in descriptions and len(raw_name) >= 3:
            descriptions[key] = {
                "desc": extract_first_sentence(desc_text),
                "talent_type": "incantesimo",
                "level": None,
            }
        continue
    # Also try plain list format: SpellName (school): Description  (all on one line)
    line_clean = re.sub(r"^[\*\#\-\s]+", "", line).strip()
    m_plain = re.match(
        r"^([A-ZÀÈÉÌÒÙ][a-zA-ZÀàÈèÉéÌìÒòÙù\s\'\.]+?)\s*(?:[INR]\s*)?\((amm|evo|inv|nec|tra|div|abi|ill)\):\s*(.+)",
        line_clean
    )
    if m_plain:
        spell_name = re.sub(r"[iNnRr]$", "", m_plain.group(1)).strip()
        if len(spell_name) < 3:
            continue
        desc = m_plain.group(3).strip()
        key = spell_name.lower().strip()
        if key not in descriptions:
            descriptions[key] = {
                "desc": extract_first_sentence(desc),
                "talent_type": "incantesimo",
                "level": None,
            }
        continue
    # Plain list without inline description — skip (would pick up wrong spell text)
    m_plain2 = re.match(
        r"^([A-ZÀÈÉÌÒÙ][a-zA-ZÀàÈèÉéÌìÒòÙù\s\'\.]+?)\s*(?:[INR]\s*)?\((amm|evo|inv|nec|tra|div|abi|ill)\)",
        line_clean
    )
    if m_plain2:
        continue

# --- Class descriptions (from class section headers) ---
class_descriptions = {
    "Alchimista": "Utilizza reagenti alchemici per creare bombe, elisir e mutageni.",
    "Barbaro": "Un combattente furioso che sfrutta l'istinto e la rabbia in battaglia.",
    "Bardo": "Un artista e incantatore occulto che compone magia attraverso la musica.",
    "Campione": "Un guerriero divino che segue la causa della propria divinità.",
    "Canaglia": "Un avventuriero furbo che usa astuzia e attacchi furtivi.",
    "Chierico": "Un incantatore divino che serve una divinità e incanala energia divina.",
    "Druido": "Un incantatore primevo legato alla natura e agli ordini druidici.",
    "Guerriero": "Un maestro del combattimento con armi e armature.",
    "Mago": "Un incantatore arcano che studia la magia attraverso la tesi arcana.",
    "Monaco": "Un artista marziale che perfeziona corpo e mente attraverso il ki.",
    "Ranger": "Un cacciatore e esploratore che braccia le prede nella natura.",
    "Stregone": "Un incantatore nato con una linea di sangue magica.",
}
for cls_name, desc in class_descriptions.items():
    key = cls_name.lower().strip()
    if key not in descriptions:
        descriptions[key] = {"desc": desc, "talent_type": "classe_desc"}

# --- Stirpe descriptions ---
stirpe_descriptions = {
    "Elfo": "Esseri longevi e aggraziati con affinità per la magia e la natura.",
    "Gnomo": "Creature piccole e vivaci con legami nel mondo delle fate.",
    "Goblin": "Piccoli e caotici, sopravvivono con astuzia e adattabilità.",
    "Halfling": "Piccoli e fortunati, noti per l'ottimismo e l'adattabilità.",
    "Nano": "Robusti e tenaci, famosi per l'artigianato e le fortezze.",
    "Umano": "Versatili e ambiziosi, capaci di adattarsi a ogni situazione.",
}
for sp_name, desc in stirpe_descriptions.items():
    key = sp_name.lower().strip()
    if key not in descriptions:
        descriptions[key] = {"desc": desc, "talent_type": "stirpe_desc"}

# --- Focus spell descriptions ---
foc_pattern = re.compile(r"\*\*([^*]{3,70}?)\s+FOCALIZZATO\s+(\d+)\*\*", re.IGNORECASE)
for i in range(21137, len(lines)):
    m = foc_pattern.search(lines[i])
    if not m:
        continue
    name = m.group(1).strip()
    level = int(m.group(2))
    if len(name) < 3:
        continue
    desc = ""
    for j in range(i + 1, min(i + 15, len(lines))):
        tline = lines[j].strip()
        if not tline:
            continue
        if tline.startswith("#") or tline.startswith("!["):
            break
        if re.search(r"FOCALIZZATO\s+\d+", tline) and j > i + 1:
            break
        if tline.startswith("**") and j > i + 1:
            continue
        if len(tline) > 15 and not re.match(r"^\*\*(?:NON COMUNE|ABILITÀ|GENERICO)", tline):
            desc = tline[:300]
            break
    key = name.lower().strip()
    if key not in descriptions:
        descriptions[key] = {
            "desc": extract_first_sentence(desc),
            "talent_type": "incantesimo_focalizzato",
            "level": None,
        }

# --- Fix: class talent descriptions pick up trait lines ---
# The class sections have talent entries like:
# #### **CONTROINCANTESIMO** [reaction] **TALENTO 1**
# **ABIURAZIONE ARCANO MAGO**      <- trait line, NOT description
# **Innesco** ...                   <- trigger line, skip
# Actual description follows
# The existing extraction in section 2 already has this issue baked into graph.json
# We re-extract class talent descriptions here with better filtering
for cls_name, cstart, cend in class_ranges:
    i = cstart
    while i < cend:
        line = lines[i]
        m = None
        for pat in talent_patterns:
            m = pat.search(line)
            if m:
                break
        if m:
            name = m.group(1).strip()
            level = int(m.group(2))
            if name.upper() not in ("TALENTO", "ABILITÀ", "GENERICO") and len(name) >= 3:
                if re.match(r"^\[(one-action|two-actions|three-actions|reaction|free-action)\]$", name, re.IGNORECASE):
                    i += 1
                    continue
                desc = ""
                for j in range(i + 1, min(i + 12, cend)):
                    tline = lines[j].strip()
                    if not tline:
                        continue
                    if re.search(r"TALENTO\s+\d+", tline) and j > i + 1:
                        break
                    if tline.startswith("#") or tline.startswith("!["):
                        break
                    if tline.startswith("**Prerequis") or tline.startswith("**Speciale") or tline.startswith("**Innesco"):
                        continue
                    if tline.startswith("**Lancio") or tline.startswith("**Raggio") or tline.startswith("**Tiro Salvezza"):
                        continue
                    if tline.startswith("**"):
                        is_trait = re.match(
                            r"^\*\*(" + "|".join([
                                "ABIURAZIONE", "AMMALIAMENTO", "EVOCAZIONE", "INVOCAZIONE",
                                "NECROMANZIA", "TRASMUTAZIONE", "DIVINAZIONE", "ILLUSIONE",
                                "ARCANO", "DIVINO", "OCCULTO", "PRIMEVO",
                                "CONCENTRAZIONE", "MANEGGIARE", "PAUSA", "SEGRETO",
                                "ESPLORAZIONE", "EMOZIONE", "INCAPACITAZIONE", "PAURA",
                                "FORTUNA", "AUDITIVO", "VISIVO", "METAMORFOSI",
                                "COMPOSIZIONE", "GUARIGIONE", "MENTALE", "POSIZIONE",
                                "MAGO", "BARDO", "CHIERICO", "DRUIDO", "STREGONE",
                                "RANGER", "BARBARO", "MONACO", "CANAGLIA", "CAMPIONE",
                                "GUERRIERO", "ALCHIMISTA", "NON COMUNE", "COMUNE",
                            ]) + r")",
                            tline
                        )
                        if is_trait:
                            continue
                    if len(tline) > 15:
                        desc = tline[:300]
                        break
                key = name.lower().strip()
                clean_desc = extract_first_sentence(desc)
                if clean_desc:
                    descriptions[key] = {
                        "desc": clean_desc,
                        "talent_type": "classe",
                        "level": level,
                    }
        i += 1

# --- Condition links from spell/talent descriptions ---
CONDIZIONI = [
    "Spaventato", "Confuso", "Incapacitato", "Nauseato", "Paralizzato",
    "Stordito", "Avvelenato", "Sanguinamento", "Rallentato", "Prono",
    "Afferrato", "Intrappolato", "Morente", "Nascosto", "Immobilizzato",
    "Incosciente", "Malato", "In fuga", "Rapido", "Blindato",
    "Impreparato", "Invisibile", "Pietrificato",
]
cond_node_ids = {}
for n in graph["nodes"]:
    for cond in CONDIZIONI:
        if n["label"].lower() == cond.lower():
            cond_node_ids[cond] = n["id"]
            break

condition_edges_added = 0
spell_name_current = ""
spell_id_current = None
for i in range(27000, len(lines)):
    line = lines[i].strip()
    m_spell = re.search(r"\*\*([^*]{3,70}?)\s+INCANTESIMO\s+\d+\*\*", line, re.IGNORECASE)
    m_foc = re.search(r"\*\*([^*]{3,70}?)\s+FOCALIZZATO\s+\d+\*\*", line, re.IGNORECASE)
    if m_spell:
        spell_name_current = m_spell.group(1).strip()
        lid = spell_name_current.lower().strip()
        norm = normalize_for_matching(spell_name_current)
        if lid in existing_by_label:
            spell_id_current = existing_by_label[lid]["id"]
        elif norm in existing_by_label:
            spell_id_current = existing_by_label[norm]["id"]
        else:
            found = False
            for dk in existing_by_label:
                if dk.startswith(lid) and len(dk) - len(lid) <= 3:
                    spell_id_current = existing_by_label[dk]["id"]
                    found = True
                    break
                if dk.startswith(norm) and len(dk) - len(norm) <= 3:
                    spell_id_current = existing_by_label[dk]["id"]
                    found = True
                    break
            if not found:
                spell_id_current = None
    elif m_foc:
        spell_name_current = m_foc.group(1).strip()
        lid = spell_name_current.lower().strip()
        if lid in existing_by_label:
            spell_id_current = existing_by_label[lid]["id"]
        else:
            spell_id_current = None
    if spell_id_current and (line.startswith("**Successo") or line.startswith("**Fallimento") or line.startswith("**Critico")):
        for cond in CONDIZIONI:
            if cond.lower() in line.lower() and cond in cond_node_ids:
                add_edge(spell_id_current, cond_node_ids[cond], "inflicts", "EXTRACTED", 1.0, weight=1.5)
                condition_edges_added += 1

print(f"Extracted {len(descriptions)} descriptions total")
print(f"Condition-inflicting edges added: {condition_edges_added}")

# =================================================================
# 3. INJECT DATA INTO GRAPH NODES
# =================================================================

updated_count = 0
fuzzy_count = 0
for n in graph["nodes"]:
    label_lower = n["label"].lower().strip()
    matched_key = None
    if label_lower in descriptions:
        matched_key = label_lower
    else:
        norm = normalize_for_matching(n["label"])
        if norm in descriptions:
            matched_key = norm
        else:
            for dk in descriptions:
                if dk.startswith(norm) and len(dk) - len(norm) <= 3:
                    matched_key = dk
                    break
                if norm.startswith(dk) and len(norm) - len(dk) <= 3:
                    matched_key = dk
                    break
    if matched_key:
        info = descriptions[matched_key]
        if info.get("desc"):
            n["description"] = info["desc"]
        if info.get("talent_type") and "talent_type" not in n:
            n["talent_type"] = info["talent_type"]
        if info.get("level") is not None and "level" not in n:
            n["level"] = info["level"]
        updated_count += 1
        if matched_key != label_lower:
            fuzzy_count += 1

# Also inject descriptions for the newly added skill/general talent nodes
for t in skill_generic_talents:
    name_lower = t["name"].lower().strip()
    if name_lower in existing_by_label:
        node = existing_by_label[name_lower]
        if isinstance(node, dict) and "id" in node:
            node["description"] = t["desc"]
            node["talent_type"] = t["talent_type"]
            node["level"] = t["level"]

print(f"Updated {updated_count} existing nodes with descriptions/types")

# =================================================================
# 4. DETERMINE TALENT TYPE FOR EXISTING TALENT NODES
# =================================================================
# Class nodes
class_id_set = set()
for n in graph["nodes"]:
    if n["label"] in CLASS_NAMES:
        class_id_set.add(n["id"])

# Stirpe nodes
stirpe_id_set = set()
for n in graph["nodes"]:
    if n["label"] in STIRPI:
        stirpe_id_set.add(n["id"])

# Generic section node
gen_section_id = existing_by_label.get("talenti generici", {}).get("id")

# Classify existing talent nodes by their connections
talent_nodes_to_classify = {}
for n in graph["nodes"]:
    label_lower = n["label"].lower().strip()
    if label_lower in descriptions:
        if "talent_type" not in n:
            n["talent_type"] = descriptions[label_lower].get("talent_type", "")
        continue
    # Check if this node is linked to a class or stirpe
    has_class_link = False
    has_stirpe_link = False
    has_generic_link = False
    for e in graph["links"]:
        if e["source"] == n["id"]:
            if e["target"] in class_id_set:
                has_class_link = True
            elif e["target"] in stirpe_id_set:
                has_stirpe_link = True
            elif e["target"] == gen_section_id:
                has_generic_link = True
    if has_class_link:
        n["talent_type"] = "classe"
    elif has_stirpe_link:
        n["talent_type"] = "stirpe"
    elif has_generic_link:
        n["talent_type"] = "generico"

# =================================================================
# 5. TALENT LEVEL PROGRESSION FOR SKILL/GENERAL TALENTS
# =================================================================
# Skill feats are gained at levels: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20
# (every 2 levels starting from 2, except Canaglia which gets them every level)
# General feats are gained at levels: 3, 7, 11, 15, 19
# (every 4 levels starting from 3)
SKILL_TALENT_LEVELS = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
GENERAL_TALENT_LEVELS = [3, 7, 11, 15, 19]

# Create talent level nodes for skill feats
skill_talent_level_ids = {}
for lv in SKILL_TALENT_LEVELS:
    label = f"Talento di Abilità di {lv}° Livello"
    nid = ensure_node(label, extra={"talent_type": "hub_abilità"})
    skill_talent_level_ids[lv] = nid
    # Link to character level
    char_level_label = f"Livello {lv}".lower()
    if char_level_label in existing_by_label:
        add_edge(nid, existing_by_label[char_level_label]["id"], "requires_character_level", "INFERRED", 1.0)

# Create talent level nodes for general feats
general_talent_level_ids = {}
for lv in GENERAL_TALENT_LEVELS:
    label = f"Talento Generico di {lv}° Livello"
    nid = ensure_node(label, extra={"talent_type": "hub_generico"})
    general_talent_level_ids[lv] = nid
    char_level_label = f"Livello {lv}".lower()
    if char_level_label in existing_by_label:
        add_edge(nid, existing_by_label[char_level_label]["id"], "requires_character_level", "INFERRED", 1.0)

# Link skill/general talent nodes to their level hubs
for t in skill_generic_talents:
    name_lower = t["name"].lower().strip()
    if name_lower not in existing_by_label:
        continue
    tid = existing_by_label[name_lower]["id"]
    if t["talent_type"] == "abilità" and t["level"] in skill_talent_level_ids:
        add_edge(tid, skill_talent_level_ids[t["level"]], "has_talent_level", "EXTRACTED", 1.0)
    elif t["talent_type"] == "generico" and t["level"] in general_talent_level_ids:
        add_edge(tid, general_talent_level_ids[t["level"]], "has_talent_level", "EXTRACTED", 1.0)
    # For abilità talents, also link to general talent level if applicable
    if t["talent_type"] == "abilità" and t["level"] in GENERAL_TALENT_LEVELS:
        if t["level"] in general_talent_level_ids:
            add_edge(tid, general_talent_level_ids[t["level"]], "has_talent_level", "INFERRED", 0.8)

# =================================================================
# 6. REMOVE JUNK ACTION-TAG NODES
# =================================================================
# The talent patterns sometimes capture action tags like [reaction],
# [one-action] etc. as standalone talent nodes. Remove them.
action_tag_re = re.compile(r"^\[(one-action|two-actions|three-actions|reaction|free-action)\]$", re.IGNORECASE)
junk_ids = set()
for n in graph["nodes"]:
    if action_tag_re.match(n["label"]):
        junk_ids.add(n["id"])
if junk_ids:
    before_nodes = len(graph["nodes"])
    before_links = len(graph["links"])
    # Move the real talent name from the description back into a proper node
    for jid in junk_ids:
        jnode = existing_by_id.get(jid)
        if jnode and jnode.get("description"):
            pass
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] not in junk_ids]
    graph["links"] = [e for e in graph["links"] if e["source"] not in junk_ids and e["target"] not in junk_ids]
    print(f"Removed {len(junk_ids)} junk action-tag nodes ({before_nodes - len(graph['nodes'])} nodes, {before_links - len(graph['links'])} links)")

# =================================================================
# WRITE OUTPUT
# =================================================================
graph["nodes"].extend(new_nodes)
graph["links"].extend(new_edges)

out_path = Path("graphify-out/graph.json")
out_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Added {len(new_nodes)} new nodes, {len(new_edges)} new edges")
print(f"Total: {len(graph['nodes'])} nodes, {len(graph['links'])} links")

# Summary
abilita_count = sum(1 for t in skill_generic_talents if t["talent_type"] == "abilità")
generico_count = sum(1 for t in skill_generic_talents if t["talent_type"] == "generico")
desc_count = sum(1 for n in graph["nodes"] if n.get("description"))
type_count = sum(1 for n in graph["nodes"] if n.get("talent_type"))
print(f"Abilità talents: {abilita_count}, Generico talents: {generico_count}")
print(f"Nodes with descriptions: {desc_count} ({fuzzy_count} fuzzy-matched)")
print(f"Nodes with talent_type: {type_count}")

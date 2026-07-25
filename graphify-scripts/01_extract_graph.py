import re
import json
from pathlib import Path

SOURCE = Path("/tmp/pathfinder-md/Manuale di Gioco.md")
STEM = "tmp_pathfinder_md_manuale_di_gioco"
SOURCE_FILE = "/tmp/pathfinder-md/Manuale di Gioco.md"

text = SOURCE.read_text(encoding="utf-8")
lines = text.split("\n")

nodes = []
edges = []
node_ids = set()

def make_id(label):
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return f"{STEM}_{s}"

def add_node(label, file_type="document", extra=None):
    nid = make_id(label)
    if nid in node_ids:
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
    nodes.append(node)
    node_ids.add(nid)
    return nid

def add_edge(src, tgt, relation, confidence="EXTRACTED", confidence_score=1.0):
    edges.append({
        "source": src,
        "target": tgt,
        "relation": relation,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "source_file": SOURCE_FILE,
        "source_location": None,
        "weight": 1.0,
    })

# ---- STIRPI ----
stirpi = ["Nano", "Elfo", "Gnomo", "Goblin", "Halfling", "Umano"]
stirpi_ids = {}
for s in stirpi:
    sid = add_node(s, "concept")
    stirpi_ids[s] = sid

# Stirpe chapter
stirpe_section = add_node("Stirpi e Background", "document")
for s, sid in stirpi_ids.items():
    add_edge(sid, stirpe_section, "conceptually_related_to", "EXTRACTED", 1.0)

# ---- CLASSI ----
classi = [
    ("Alchimista", "Intelligenza", "arcano"),
    ("Barbaro", "Forza", None),
    ("Bardo", "Carisma", "occulto"),
    ("Campione", "Forza", "divino"),
    ("Canaglia", "Destrezza", None),
    ("Chierico", "Saggezza", "divino"),
    ("Druido", "Saggezza", "primevo"),
    ("Guerriero", "Forza", None),
    ("Mago", "Intelligenza", "arcano"),
    ("Monaco", "Destrezza", None),
    ("Ranger", "Destrezza", "primevo"),
    ("Stregone", "Carisma", "occulto"),
]
classi_ids = {}
classi_section = add_node("Classi", "document")
for name, chiave, tradizione in classi:
    cid = add_node(name, "concept")
    classi_ids[name] = cid
    add_edge(cid, classi_section, "conceptually_related_to", "EXTRACTED", 1.0)
    chiave_id = add_node(f"Caratteristica: {chiave}", "concept")
    add_edge(cid, chiave_id, "references", "EXTRACTED", 1.0)
    if tradizione:
        trad_id = add_node(f"Tradizione: {tradizione.capitalize()}", "concept")
        add_edge(cid, trad_id, "references", "EXTRACTED", 1.0)

# ---- ABILITÀ ----
abilita_names = [
    "Acrobazia", "Arcano", "Artigianato", "Atletica", "Diplomazia",
    "Esibizione", "Furtività", "Furto", "Inganno", "Intimidazione",
    "Medicina", "Natura", "Occultismo", "Percezione", "Religione",
    "Rappresentare", "Società", "Sopravvivenza"
]
abilita_section = add_node("Abilità", "document")
abilita_ids = {}
for a in abilita_names:
    aid = add_node(a, "concept")
    abilita_ids[a] = aid
    add_edge(aid, abilita_section, "conceptually_related_to", "EXTRACTED", 1.0)

# ---- TIRI SALVEZZA ----
ts_names = ["Tempra", "Riflessi", "Volontà"]
ts_section = add_node("Tiri Salvezza", "concept")
ts_ids = {}
for t in ts_names:
    tid = add_node(t, "concept")
    ts_ids[t] = tid
    add_edge(tid, ts_section, "conceptually_related_to", "EXTRACTED", 1.0)

# ---- PARSE TALENTI from class sections ----
# Main pattern: **NAME** [optional-action] **TALENTO N** or **NAME** TALENTO N
talento_pattern = re.compile(
    r'\*\*([^*]{3,70})\*\*\s*(?:\[[^\]]*\]\s*\*\*)?\s*TALENTO\s+(\d+)',
    re.IGNORECASE
)

# Also: **NAME** [action] **TALENTO N (double bold)
talento_pattern2 = re.compile(
    r'\*\*([^*]{3,70})\*\*\s*\[[^\]]*\]\s*\*\*\s*TALENTO\s+(\d+)',
    re.IGNORECASE
)

# Also: **NAME TALENTO N** (name and TALENTO inside same bold markers)
talento_pattern3 = re.compile(
    r'\*\*([^*]{3,70}?)\s+TALENTO\s+(\d+)\*\*',
    re.IGNORECASE
)

# Build line-range map for stirpe sections
stirpe_ranges = [
    ("Elfo", 1442, 1722),
    ("Gnomo", 1722, 2002),
    ("Goblin", 2002, 2290),
    ("Halfling", 2290, 2562),
    ("Nano", 2562, 2842),
    ("Umano", 2842, 3867),
]
# Archetype section starts at line 15369 — talents in lines 15369-16412
# are archetype (not class) talents and must NOT be linked to classes.
ARCHETYPE_START = 15369

# Build line-range map for class sections
# NOTE: Bardo class content is at lines 5699-6438 (between Barbaro and Campione
# in the PDF extraction), even though the # Bardo heading appears at line 15553
# (which is the archetype multiclass section).
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
    ("Stregone", 14071, ARCHETYPE_START),
]

current_class = None
current_stirpe = None

for i, line in enumerate(lines):
    lineno = i + 1  # 1-indexed

    # Skip archetype section — these talents belong to archetypes, not classes
    if ARCHETYPE_START <= lineno < 16412:
        continue
    
    # Track stirpe by line range
    current_stirpe = None
    for sp_name, sp_start, sp_end in stirpe_ranges:
        if sp_start <= lineno < sp_end:
            current_stirpe = sp_name
            break
    
    # Track class by line range
    current_class = None
    for cls_name, cls_start, cls_end in class_ranges:
        if cls_start <= lineno < cls_end:
            current_class = cls_name
            break
    for sp_name in stirpi_ids:
        if line.strip() == f"# {sp_name}":
            current_stirpe = sp_name
            current_class = None
            break

    # Extract talenti (all three patterns)
    for pat in (talento_pattern, talento_pattern2, talento_pattern3):
        for m in pat.finditer(line):
            name = m.group(1).strip()
            level = int(m.group(2))
            if len(name) < 3 or len(name) > 80:
                continue
            if name.upper() in ("TALENTO", "ABILITÀ", "GENERICO"):
                continue
            if any(kw in name.upper() for kw in ("TABELLA", "LIVELLO", "CAPITOLO", "INCREMENTO", "COMPETEN", "PREREQUISITI")):
                continue
            file_type = "concept"
            tid = add_node(name, file_type, extra={"level": level})
            if current_class:
                add_edge(tid, classi_ids[current_class], "conceptually_related_to", "EXTRACTED", 1.0)
            if current_stirpe:
                add_edge(tid, stirpi_ids[current_stirpe], "conceptually_related_to", "EXTRACTED", 1.0)

# ---- PREREQUISITI ----
prereq_pattern = re.compile(r'\*\*Prerequisiti?\*\*\s+(.+)', re.IGNORECASE)
for i, line in enumerate(lines):
    m = prereq_pattern.search(line)
    if m:
        prereq_text = m.group(1).strip()
        # Try to link to nearby talent node
        # Find the talent name from context (previous heading)
        for j in range(max(0, i-5), i):
            for tm in talento_pattern.finditer(lines[j]):
                talent_name = tm.group(1).strip()
                tid = make_id(talent_name)
                if tid in node_ids:
                    # Parse prereq for known entities
                    for cls_name, cid in classi_ids.items():
                        if cls_name.lower() in prereq_text.lower():
                            add_edge(tid, cid, "references", "EXTRACTED", 1.0)
                    for sp_name, sid in stirpi_ids.items():
                        if sp_name.lower() in prereq_text.lower():
                            add_edge(tid, sid, "references", "EXTRACTED", 1.0)
                    for ab_name, aid in abilita_ids.items():
                        if ab_name.lower() in prereq_text.lower():
                            add_edge(tid, aid, "references", "EXTRACTED", 1.0)

# ---- INCANTESIMI ----
incantesimo_pattern = re.compile(r'\*\*([^*]+)\*\*\s*(?:\([^)]*\))?\s*[A-Z]')
spell_tradizioni = ["Arcano", "Divino", "Occulto", "Primevo"]
spell_section = add_node("Incantesimi", "document")
for trad in spell_tradizioni:
    trad_id = add_node(f"Incantesimi {trad}", "concept")
    add_edge(trad_id, spell_section, "conceptually_related_to", "EXTRACTED", 1.0)

# Extract spell names from the spell chapter (lines 21137+)
spell_start = 21137
# Pattern: SpellName (school)  — spells are NOT bold in this file
spell_list_pattern = re.compile(r'^([A-ZÀÈÉÌÒÙ][a-zA-ZÀàÈèÉéÌìÒòÙù\s\'\.]+?)\s*(?:[INR]\s*)?\((amm|evo|inv|nec|tra|div|abi|ill)\)')
spell_count = 0
junk_words = {"note", "volume", "prezzo", "danno", "gittata", "ricarica", "mani", "gruppo",
              "nome dell'incantesimo", "a due mani", "aberrazione", "tratti", "peso",
              "incantesimi arcani", "incantesimi divini", "incantesimi occulti", "incantesimi primevi",
              "trucchetti arcani", "trucchetti divini", "trucchetti occulti", "trucchetti primevi"}
for i in range(spell_start, len(lines)):
    line = lines[i].strip()
    # Remove leading list markers
    line = re.sub(r'^[\*\#\-\s]+', '', line).strip()
    m = spell_list_pattern.match(line)
    if not m:
        continue
    spell_name = m.group(1).strip()
    school = m.group(2)
    if spell_name.lower() in junk_words:
        continue
    if len(spell_name) < 3:
        continue
    sid = add_node(spell_name, "concept", extra={"category": "incantesimo", "school": school})
    add_edge(sid, spell_section, "conceptually_related_to", "EXTRACTED", 1.0)
    spell_count += 1

# ---- CONDIZIONI ----
condizioni = [
    "Blindato", "Afferrato", "Intrappolato", "Confuso", "Spaventato",
    "Morente", "Incapacitato", "Nascosto", "Immobilizzato", "Prono",
    "Impreparato", "Invisibile", "Paralizzato", "Pietrificato",
    "Stordito", "Incosciente", "Nauseato", "Sanguinamento",
    "Avvelenato", "Malato", "Rallentato", "Rapido", "In fuga"
]
cond_section = add_node("Condizioni", "concept")
for c in condizioni:
    cid = add_node(c, "concept")
    add_edge(cid, cond_section, "conceptually_related_to", "EXTRACTED", 1.0)

# ---- AZIONI ----
azioni = [
    "Avanzare", "Interagire", "Lanciare un Incantesimo", "Colpire",
    "Sbilanciare", "Afferrare", "Spingere", "Fintare",
    "Demoralizzare", "Cercare", "Curare Ferite", "Ricordare Conoscenze",
    "Saltare", "Scalare", "Nuotare", "Nascondere", "Individuare",
    "Seguire le Tracce", "Riposare", "Esplorare", "Perlustrare",
    "Evitare l'Individuazione", "Difendere", "Alzarsi"
]
azione_section = add_node("Azioni", "concept")
for a in azioni:
    aid = add_node(a, "concept")
    add_edge(aid, azione_section, "conceptually_related_to", "EXTRACTED", 1.0)

# ---- TRATTI ----
tratti = [
    "Fuoco", "Freddo", "Elettricità", "Acido", "Veleno", "Sonicità",
    "Fisico", "Magico", "Arcano", "Divino", "Occulto", "Primevo",
    "Mentale", "Emozione", "Paura", "Concentrazione", "Manipolazione",
    "Movimento", "Passo", "Apertura", "Ostentazione", "Posizione",
    "Metamagico", "Reazione", "Azione Gratuita", "Fortuna", "Sfortuna"
]
tratto_section = add_node("Tratti", "concept")
for t in tratti:
    tid = add_node(t, "concept")
    add_edge(tid, tratto_section, "conceptually_related_to", "EXTRACTED", 1.0)

# ---- CROSS-REFERENCES ----
# Class-Stirpe typical associations (from the manual)
associations = [
    ("Nano", "Guerriero"), ("Nano", "Chierico"), ("Nano", "Druido"),
    ("Elfo", "Mago"), ("Elfo", "Ranger"), ("Elfo", "Bardo"),
    ("Gnomo", "Bardo"), ("Gnomo", "Alchimista"), ("Gnomo", "Stregone"),
    ("Goblin", "Alchimista"), ("Goblin", "Canaglia"), ("Goblin", "Barbaro"),
    ("Halfling", "Canaglia"), ("Halfling", "Bardo"), ("Halfling", "Ranger"),
    ("Umano", "Guerriero"), ("Umano", "Stregone"), ("Umano", "Chierico"),
]
for stirpe, cls in associations:
    if stirpe in stirpi_ids and cls in classi_ids:
        add_edge(stirpi_ids[stirpe], classi_ids[cls], "conceptually_related_to", "INFERRED", 0.75)

# ---- SUBCLASS CONCEPTS ----
# Barbarian Instincts
istinti = ["Istinto Animale", "Istinto Drago", "Istinto Spirito", "Istinto Superstizione"]
for ist in istinti:
    iid = add_node(ist, "concept")
    add_edge(iid, classi_ids["Barbaro"], "references", "EXTRACTED", 1.0)

# Druid Orders
ordini_druido = ["Ordine Animale", "Ordine Foglia", "Ordine Tempesta", "Ordine Selvaggio"]
for od in ordini_druido:
    oid = add_node(od, "concept")
    add_edge(oid, classi_ids["Druido"], "references", "EXTRACTED", 1.0)

# Bard Muses
muse = ["Musa Polimatia", "Musa Maestro", "Musa Stregoneria"]
for m in muse:
    mid = add_node(m, "concept")
    add_edge(mid, classi_ids["Bardo"], "references", "EXTRACTED", 1.0)

# Champion Causes
cause = ["Causa del Bene", "Causa del Male", "Causa della Redenzione"]
for c in cause:
    cid = add_node(c, "concept")
    add_edge(cid, classi_ids["Campione"], "references", "EXTRACTED", 1.0)

# Rogue Rackets
rackets = ["Racket Furfante", "Racket Ladro", "Racket Combattente"]
for r in rackets:
    rid = add_node(r, "concept")
    add_edge(rid, classi_ids["Canaglia"], "references", "EXTRACTED", 1.0)

# Sorcerer Bloodlines
linee_sangue = ["Linea di Sangue Demoniaco", "Linea di Sangue Draconico", "Linea di Sangue Fatato",
                "Linea di Sangue Imperiale", "Linea di Sangue Elementale", "Linea di Sangue Aberrante"]
for ls in linee_sangue:
    lid = add_node(ls, "concept")
    add_edge(lid, classi_ids["Stregone"], "references", "EXTRACTED", 1.0)

# Monk Schools
scuole_monaco = ["Scuola della Gru", "Scuola della Montagna", "Scuola del Loto", "Scuola del Cinghiale"]
for sm in scuole_monaco:
    sid = add_node(sm, "concept")
    add_edge(sid, classi_ids["Monaco"], "references", "EXTRACTED", 1.0)

# Alchemist Research Fields
campi_ricerca = ["Campo Bomber", "Campo Elixirmante", "Campo Mutagenista", "Campo Tossicologo"]
for cr in campi_ricerca:
    crid = add_node(cr, "concept")
    add_edge(crid, classi_ids["Alchimista"], "references", "EXTRACTED", 1.0)

# Wizard Schools / Theses
tesi_mago = ["Tesi del Legame del Bastone", "Tesi dell'Energia Spell-Out", "Scuola di Abiurazione",
             "Scuola di Divinazione", "Scuola di Ammaliamento", "Scuola di Evocazione",
             "Scuola di Illusione", "Scuola di Invocazione", "Scuola di Necromanzia", "Scuola di Trasmutazione"]
for tm in tesi_mago:
    tid = add_node(tm, "concept")
    add_edge(tid, classi_ids["Mago"], "references", "EXTRACTED", 1.0)

# Ranger Hunt Prey / Edicts
ranger_concepts = ["Preda Designata", "Preda da Cacciatore"]
for rc in ranger_concepts:
    rid = add_node(rc, "concept")
    add_edge(rid, classi_ids["Ranger"], "references", "EXTRACTED", 1.0)

# Cleric Domains
domini_chierico = ["Dominio dell'Airone", "Dominio del Cielo", "Dominio della Città",
                   "Dominio della Conoscenza", "Dominio della Creazione", "Dominio del Fuoco",
                   "Dominio della Guarigione", "Dominio della Magia", "Dominio della Protezione",
                   "Dominio del Sole", "Dominio della Terra", "Dominio della Guerra",
                   "Dominio dell'Acqua", "Dominio del Vento", "Dominio della Morte",
                   "Dominio dell'Ingegno", "Dominio della Natura", "Dominio dell'Intrigo"]
for dc in domini_chierico:
    did = add_node(dc, "concept")
    add_edge(did, classi_ids["Chierico"], "references", "EXTRACTED", 1.0)

# Fighter combat concepts
combattimento = ["Arma Leggendaria", "Combattimento a Due Armi", "Armi e Scudi", "Tiro Preciso"]
for comp in combattimento:
    cid = add_node(comp, "concept")
    add_edge(cid, classi_ids["Guerriero"], "references", "EXTRACTED", 1.0)

# Generic talents section
generici_section = add_node("Talenti Generici", "document")
talenti_nodes = [n for n in nodes if 'level' in n]
stirpi_id_set = set(stirpi_ids.values())
classi_id_set = set(classi_ids.values())
for t in talenti_nodes:
    has_stirpe = any(e['source'] == t['id'] and e['target'] in stirpi_id_set for e in edges)
    has_class = any(e['source'] == t['id'] and e['target'] in classi_id_set for e in edges)
    if not has_stirpe and not has_class:
        add_edge(t['id'], generici_section, "conceptually_related_to", "EXTRACTED", 1.0)

# Output
result = {
    "nodes": nodes,
    "edges": edges,
    "hyperedges": [],
    "input_tokens": 0,
    "output_tokens": 0,
}

out_path = Path("/home/marco/temp/pathfinder/graphify-out/.graphify_chunk_01.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Extracted: {len(nodes)} nodes, {len(edges)} edges, {spell_count} spells")

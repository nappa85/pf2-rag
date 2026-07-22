import os

PDFS_DIR = os.environ.get("PDFS_DIR", "/app/pdfs")
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
MARKDOWN_DIR = os.path.join(DATA_DIR, "markdown")
CHUNKS_PATH = os.path.join(DATA_DIR, "chunks", "chunks.jsonl")
INDEX_DIR = os.path.join(DATA_DIR, "index")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
EMBEDDING_DIM = 384
EMBEDDING_BACKEND = os.environ.get("EMBEDDING_BACKEND", "sentence-transformers")
EMBEDDING_DEVICE = os.environ.get("EMBEDDING_DEVICE", "cpu")

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300

BM25_K = 30
DENSE_K = 30
RRF_K = 61
ALPHA = 0.5

EXPAND_QUERIES = os.environ.get("EXPAND_QUERIES", "true").lower() == "true"

ITALIAN_STOPWORDS = frozenset([
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "il", "lo", "la", "le", "gli", "i", "un", "uno", "una",
    "è", "e", "o", "ma", "se", "che", "non", "si", "no",
    "come", "più", "anche", "ancora", "delle", "degli", "della",
    "del", "dello", "alla", "allo", "al", "ai", "agli", "alle",
    "nei", "nel", "nello", "nella", "nelle", "sul", "sullo",
    "sulla", "sulle", "sui", "agli", "dall", "dalla", "dagli",
    "dalle", "dai", "sull", "sulla", "sulle", "sullo",
    "questo", "questa", "questi", "queste", "quello", "quella",
    "quelli", "quelle", "quest", "quell",
    "molto", "molta", "molti", "molte", "poco", "poca", "pochi", "poche",
    "tutto", "tutta", "tutti", "tutte", "ogni", "alcuni", "alcune",
    "suo", "sua", "suoi", "sue", "mio", "mia", "miei", "mie",
    "nostro", "nostra", "nostri", "nostre", "loro",
    "essere", "avere", "fare", "stare", "dare", "dire",
    "ha", "ho", "hai", "abbiamo", "hanno", "sono", "sei", "siamo",
    "era", "erano", "era", "fosse", "sia", "stato", "stata",
])

SYSTEM_PROMPT = """Sei un esperto assistente di Pathfinder Seconda Edizione (2e) in italiano.
Rispondi alle domande basandoti sul contesto fornito dai manuali di gioco.
Se la risposta non è nel contesto, dillo chiaramente.
Cita le fonti quando possibile (nome del manuale, pagina o sezione).
Rispondi sempre in italiano."""

QUERY_EXPANSION_PROMPT = """Sei un assistente specializzato in Pathfinder Seconda Edizione (2e) in italiano.
Data una domanda, genera una versione espansa e più dettagliata che includa parole chiave e termini tecnici del gioco utili per la ricerca nei manuali (es. tiri per colpire, classe armatura, tiri salvezza, tiri di dado, azioni, reazioni, tratti, condizioni).
Rispondi SOLO con la domanda espansa, niente altro."""

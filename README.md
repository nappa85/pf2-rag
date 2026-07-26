# Pathfinder 2e RAG & Knowledge Graph

A Retrieval-Augmented Generation system and knowledge graph for querying the Italian Pathfinder Seconda Edizione rulebooks. The RAG system uses hybrid search (FAISS dense + BM25 sparse with Reciprocal Rank Fusion) and Ollama-powered LLM generation to answer questions grounded in the game manuals. The knowledge graph (see [GRAPH_PROCESS.md](GRAPH_PROCESS.md)) provides a traversable, queryable graph of abilities, talents, spells, classes, and stirpi built with [graphify](https://pypi.org/project/graphify/).

## Features

- **PDF extraction**: Converts Pathfinder 2e PDFs to markdown via [Marker](https://github.com/VikParuchuri/marker) or PyMuPDF, with header detection and section-aware chunking
- **Hybrid retrieval**: Combines dense vector search (FAISS + multilingual-e5) and sparse lexical search (BM25 with Italian stopword removal) using Reciprocal Rank Fusion (RRF)
- **Query expansion**: Uses the LLM to rewrite queries with game-specific terminology for better retrieval
- **LLM generation**: Uses Ollama (default: `qwen2.5:14b`) to generate answers grounded in retrieved context, with source citations
- **Interactive chat**: REPL interface with commands for tuning retrieval, switching models, and inspecting sources
- **Dockerized**: Runs in Docker with AMD GPU support (ROCm/Vulkan) via docker compose

## Source Books

Place the following Italian Pathfinder 2e PDFs in the `pdfs/` directory:

| File | Book |
|------|------|
| `Manuale di Gioco.pdf` | Core Rulebook |
| `Guida del Giocatore.pdf` | Player's Guide |
| `Guida del Game Master.pdf` | Game Master Guide |
| `Bestiario.pdf` | Bestiary 1 |
| `Bestiario 2.pdf` | Bestiary 2 |
| `Bestiario 3.pdf` | Bestiary 3 |
| `Scheda di Riferimento.pdf` | Reference Sheet |

## Quick Start

```bash
# 1. Place your PDFs in the pdfs/ directory
cp *.pdf pdfs/

# 2. Run the full setup (starts Ollama, pulls models, builds index)
bash run.sh
```

The `run.sh` script will:
1. Start the Ollama container and pull `qwen2.5:14b`
2. Build the worker Docker image (downloads `multilingual-e5-small` embedding model on first index build)
3. Extract and chunk the PDFs
4. Build the FAISS + BM25 index

## Usage

### Interactive Chat

```bash
docker exec -it pathfinder-worker python -m rag.chat chat
```

Chat commands:

| Command | Description |
|---------|-------------|
| `/sources <query>` | Show retrieved chunks without generating an answer |
| `/alpha <0-1>` | Adjust dense/sparse balance (0 = BM25 only, 1 = dense only) |
| `/expand` | Toggle query expansion on/off |
| `/model <name>` | Switch Ollama model |
| `/quit` | Exit |

### Single Query

```bash
docker exec pathfinder-worker python -m rag.chat query "Come funziona un attacco?"
```

### Re-index

```bash
docker exec pathfinder-worker python -m rag.extract
docker exec pathfinder-worker python -m rag.index
```

## Configuration

All settings are in `rag/config.py` and can be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PDFS_DIR` | `/app/pdfs` | Directory containing source PDFs |
| `DATA_DIR` | `/app/data` | Output directory for extracted data and indexes |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:14b` | Generation model |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | Embedding model |
| `EMBEDDING_BACKEND` | `sentence-transformers` | `ollama` or `sentence-transformers` |
| `EMBEDDING_DEVICE` | `cpu` | Device for embedding model (`cpu` or `cuda`) |
| `EXPAND_QUERIES` | `true` | Enable LLM-based query expansion |

Key parameters in `rag/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CHUNK_SIZE` | 1500 | Max characters per chunk |
| `CHUNK_OVERLAP` | 300 | Overlap between chunks |
| `BM25_K` | 30 | Number of BM25 results to retrieve |
| `DENSE_K` | 30 | Number of dense results to retrieve |
| `RRF_K` | 61 | RRF constant |
| `ALPHA` | 0.5 | Dense vs. sparse weight (0.5 = balanced) |

## Architecture

```
pdfs/                     Source PDFs
  ↓
rag/extract.py           PDF → Markdown → Chunks (JSONL)
  ↓
rag/index.py             Chunks → Embeddings → FAISS index + BM25 corpus
  ↓
rag/retriever.py         Query → Expansion → Dense + BM25 search → RRF merge
  ↓
rag/generator.py         Query + Context → Ollama LLM → Answer
  ↓
rag/chat.py              CLI interface (extract, index, query, chat)
```

### Data Flow

```
data/
  markdown/    ← Extracted markdown from PDFs
  chunks/      ← Chunked text (chunks.jsonl)
  index/       ← FAISS index, BM25 corpus, metadata, config
```

## Requirements

- Docker & Docker Compose
- AMD GPU with ROCm support (for Ollama acceleration)
- ~16 GB RAM recommended (for qwen2.5:14b via Ollama)

> **Note:** Embedding models run on CPU by default (`EMBEDDING_DEVICE=cpu`) to avoid competing with Ollama for GPU memory. On systems with multiple GPUs or sufficient VRAM (>16GB), you can set `EMBEDDING_DEVICE=cuda` for faster indexing.

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo " Pathfinder 2e RAG System"
echo "========================================="

mkdir -p "$SCRIPT_DIR/pdfs" "$SCRIPT_DIR/data/markdown" "$SCRIPT_DIR/data/chunks" "$SCRIPT_DIR/data/index"

if [ ! -f "$SCRIPT_DIR/pdfs/Manuale di Gioco.pdf" ]; then
    echo "Copying PDFs to mount directory..."
    cp "$SCRIPT_DIR"/*.pdf "$SCRIPT_DIR/pdfs/" 2>/dev/null || true
fi

echo ""
echo "[1/5] Starting Ollama and pulling models..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d ollama
echo "Waiting for Ollama to be ready..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "Pulling qwen2.5:14b (generation)..."
docker exec pathfinder-ollama ollama pull qwen2.5:14b

echo ""
echo "[2/5] Building worker image..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" build worker

echo ""
echo "[3/5] Starting worker..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d worker

echo ""
echo "[4/5] Extracting and chunking PDFs (PyMuPDF)..."
docker exec pathfinder-worker python -m rag.extract

echo ""
echo "[5/5] Building FAISS + BM25 index (sentence-transformers/multilingual-e5-small)..."
docker exec pathfinder-worker python -m rag.index

echo ""
echo "========================================="
echo " RAG system ready!"
echo ""
echo " Interactive chat:"
echo "   docker exec -it pathfinder-worker python -m rag.chat chat"
echo ""
echo " Single query:"
echo "   docker exec pathfinder-worker python -m rag.chat query \"Come funziona un attacco?\""
echo ""
echo " Re-extract/re-index:"
echo "   docker exec pathfinder-worker python -m rag.extract"
echo "   docker exec pathfinder-worker python -m rag.index"
echo "========================================="

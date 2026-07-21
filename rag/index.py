import json
import os
import numpy as np

from rag.config import CHUNKS_PATH, INDEX_DIR, OLLAMA_HOST, EMBEDDING_DEVICE


def load_chunks(chunks_path: str = CHUNKS_PATH) -> list[dict]:
    chunks = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def _embed_via_ollama(texts: list[str], model: str = "nomic-embed-text", host: str = OLLAMA_HOST, batch_size: int = 128) -> np.ndarray:
    import requests
    from tqdm import tqdm

    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding via Ollama"):
        batch = texts[i : i + batch_size]
        resp = requests.post(
            f"{host.rstrip('/')}/api/embed",
            json={"model": model, "input": batch},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        embeddings = data["embeddings"]
        all_embeddings.extend(embeddings)

    return np.array(all_embeddings, dtype="float32")


def _embed_via_sentence_transformers(texts: list[str], model_name: str, batch_size: int = 64) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    from tqdm import tqdm

    model = SentenceTransformer(model_name, trust_remote_code=True, device=EMBEDDING_DEVICE)
    model.max_seq_length = 512

    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding via sentence-transformers"):
        batch = texts[i : i + batch_size]
        emb = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        all_embeddings.append(emb)

    return np.vstack(all_embeddings).astype("float32")


def _build_passage_text(chunk: dict) -> str:
    source = chunk.get("source", "")
    section = chunk.get("section", "")
    text = chunk.get("text", "")
    context_parts = []
    if source:
        context_parts.append(source)
    if section:
        context_parts.append(section)
    prefix = " - ".join(context_parts)
    if prefix:
        return f"passage: {prefix}\n{text}"
    return f"passage: {text}"


def _build_bm25_text(chunk: dict) -> str:
    source = chunk.get("source", "")
    section = chunk.get("section", "")
    text = chunk.get("text", "")
    parts = []
    if source:
        parts.append(source)
    if section:
        parts.append(section)
    if parts:
        return " - ".join(parts) + "\n" + text
    return text


def _is_e5_model(model_name: str) -> bool:
    return "e5" in model_name.lower()


def build_index(
    chunks_path: str = CHUNKS_PATH,
    index_dir: str = INDEX_DIR,
    use_ollama: bool = False,
    ollama_embed_model: str = "nomic-embed-text",
    local_embed_model: str = "intfloat/multilingual-e5-small",
):
    import faiss

    os.makedirs(index_dir, exist_ok=True)

    print("Loading chunks...")
    chunks = load_chunks(chunks_path)
    if not chunks:
        raise ValueError(f"No chunks found at {chunks_path}")

    texts = [c["text"] for c in chunks]
    bm25_texts = [_build_bm25_text(c) for c in chunks]

    effective_model = ollama_embed_model if use_ollama else local_embed_model
    use_passage_prefix = _is_e5_model(effective_model)

    if use_passage_prefix:
        embed_texts = [_build_passage_text(c) for c in chunks]
    else:
        embed_texts = texts

    print(f"  {len(chunks)} chunks loaded")
    print(f"  Passage prefix for e5: {use_passage_prefix}")

    if use_ollama:
        print(f"Embedding via Ollama (model={ollama_embed_model}, GPU)...")
        embeddings = _embed_via_ollama(embed_texts, model=ollama_embed_model)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms
    else:
        print(f"Embedding via sentence-transformers (model={local_embed_model}, CPU)...")
        embeddings = _embed_via_sentence_transformers(embed_texts, model_name=local_embed_model)

    print(f"  Embeddings shape: {embeddings.shape}")

    dim = embeddings.shape[1]
    print(f"Building FAISS index (dim={dim})...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss_path = os.path.join(index_dir, "faiss.index")
    faiss.write_index(index, faiss_path)
    print(f"  FAISS index saved: {faiss_path}")

    meta_path = os.path.join(index_dir, "metadata.jsonl")
    with open(meta_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"  Metadata saved: {meta_path}")

    corpus_path = os.path.join(index_dir, "bm25_corpus.json")
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(bm25_texts, f, ensure_ascii=False)
    print(f"  BM25 corpus saved: {corpus_path}")

    config_path = os.path.join(index_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({
            "embedding_model": ollama_embed_model if use_ollama else local_embed_model,
            "embedding_backend": "ollama" if use_ollama else "sentence-transformers",
            "dim": dim,
            "num_chunks": len(chunks),
            "has_passage_prefix": use_passage_prefix,
        }, f, indent=2)

    print("\nIndex build complete!")
    return index_dir


if __name__ == "__main__":
    build_index()

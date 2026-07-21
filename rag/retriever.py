import json
import os
import re
from typing import Optional

import faiss
import numpy as np
import requests
from rank_bm25 import BM25Okapi

from rag.config import (
    INDEX_DIR,
    OLLAMA_HOST,
    EMBEDDING_MODEL,
    EMBEDDING_BACKEND,
    EMBEDDING_DEVICE,
    BM25_K,
    DENSE_K,
    RRF_K,
    ALPHA,
    ITALIAN_STOPWORDS,
    EXPAND_QUERIES,
    QUERY_EXPANSION_PROMPT,
)


def _tokenize_italian(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\sàèéìòù]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in ITALIAN_STOPWORDS]


class HybridRetriever:
    def __init__(self, index_dir: str = INDEX_DIR, embedding_model: str = EMBEDDING_MODEL, embedding_backend: str = EMBEDDING_BACKEND):
        self.index_dir = index_dir
        self.embedding_model = embedding_model
        self.embedding_backend = embedding_backend
        self.ollama_host = OLLAMA_HOST

        print("Loading metadata...")
        meta_path = os.path.join(index_dir, "metadata.jsonl")
        self.chunks = []
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.chunks.append(json.loads(line))

        print(f"  {len(self.chunks)} chunks loaded")

        config_path = os.path.join(index_dir, "config.json")
        self.has_passage_prefix = False
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
            self.embedding_model = cfg.get("embedding_model", embedding_model)
            self.embedding_backend = cfg.get("embedding_backend", embedding_backend)
            self.has_passage_prefix = cfg.get("has_passage_prefix", False)
            print(f"  Config: model={self.embedding_model}, backend={self.embedding_backend}")

        print("Loading FAISS index...")
        self.faiss_index = faiss.read_index(os.path.join(index_dir, "faiss.index"))
        print(f"  FAISS index: {self.faiss_index.ntotal} vectors")

        print("Loading BM25 corpus...")
        corpus_path = os.path.join(index_dir, "bm25_corpus.json")
        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        tokenized_corpus = [_tokenize_italian(doc) for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        print(f"  BM25 index: {len(corpus)} documents")

        if self.embedding_backend == "ollama":
            print(f"Embedding backend: Ollama (model={self.embedding_model}, GPU)")
            resp = requests.post(
                f"{self.ollama_host.rstrip('/')}/api/embed",
                json={"model": self.embedding_model, "input": ["test"]},
                timeout=30,
            )
            print(f"  Ollama embedding API: OK")
        else:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.embedding_model}")
            self.model = SentenceTransformer(self.embedding_model, trust_remote_code=True, device=EMBEDDING_DEVICE)
            self.model.max_seq_length = 512

    def _embed_query(self, query: str) -> np.ndarray:
        query_text = f"query: {query}" if self.has_passage_prefix else query
        if self.embedding_backend == "ollama":
            resp = requests.post(
                f"{self.ollama_host.rstrip('/')}/api/embed",
                json={"model": self.embedding_model, "input": [query_text]},
                timeout=30,
            )
            resp.raise_for_status()
            emb = np.array(resp.json()["embeddings"][0], dtype="float32")
        else:
            emb = self.model.encode([query_text], normalize_embeddings=True)[0].astype("float32")

        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        return emb.reshape(1, -1)

    def _dense_search(self, query: str, k: int = DENSE_K) -> list[tuple[int, float]]:
        q_emb = self._embed_query(query)
        scores, indices = self.faiss_index.search(q_emb, k)
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0:
                results.append((int(idx), float(score)))
        return results

    def _bm25_search(self, query: str, k: int = BM25_K) -> list[tuple[int, float]]:
        tokenized_query = _tokenize_italian(query)
        doc_scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(doc_scores)[::-1][:k]
        return [(int(i), float(doc_scores[i])) for i in top_indices]

    @staticmethod
    def _rrf_merge(
        dense_results: list[tuple[int, float]],
        bm25_results: list[tuple[int, float]],
        k: int = RRF_K,
        alpha: float = ALPHA,
    ) -> list[tuple[int, float]]:
        rrf_scores: dict[int, float] = {}

        for rank, (idx, _) in enumerate(dense_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + alpha / (k + rank + 1)

        for rank, (idx, _) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1 - alpha) / (k + rank + 1)

        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results

    def _expand_query(self, query: str) -> str:
        try:
            payload = {
                "model": self._get_ollama_model(),
                "messages": [
                    {"role": "system", "content": QUERY_EXPANSION_PROMPT},
                    {"role": "user", "content": query},
                ],
                "stream": False,
                "options": {"temperature": 0.3, "num_ctx": 1024},
            }
            resp = requests.post(
                f"{self.ollama_host.rstrip('/')}/api/chat",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            expanded = resp.json()["message"]["content"].strip()
            if expanded and len(expanded) > len(query):
                print(f"  Query expanded: {query} -> {expanded}")
                return expanded
        except Exception as e:
            print(f"  Query expansion failed: {e}")
        return query

    def _get_ollama_model(self) -> str:
        from rag.config import OLLAMA_MODEL
        return OLLAMA_MODEL

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = ALPHA,
        filter_source: Optional[str] = None,
        expand: bool = EXPAND_QUERIES,
    ) -> list[dict]:
        effective_query = self._expand_query(query) if expand else query

        dense_results = self._dense_search(effective_query, k=max(DENSE_K, top_k * 3))
        bm25_results = self._bm25_search(effective_query, k=max(BM25_K, top_k * 3))

        merged = self._rrf_merge(dense_results, bm25_results, k=RRF_K, alpha=alpha)

        results = []
        for idx, score in merged:
            chunk = self.chunks[idx].copy()
            chunk["score"] = round(score, 4)
            if filter_source and filter_source.lower() not in chunk.get("source", "").lower():
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break

        return results


if __name__ == "__main__":
    retriever = HybridRetriever()
    while True:
        query = input("\nQuery: ").strip()
        if not query:
            break
        results = retriever.search(query, top_k=5)
        for i, r in enumerate(results):
            print(f"\n--- Result {i + 1} (score={r['score']}) ---")
            print(f"Source: {r['source']} | Section: {r.get('section', '')}")
            print(r["text"][:300])

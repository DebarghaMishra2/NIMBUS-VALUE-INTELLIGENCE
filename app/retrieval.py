from __future__ import annotations
from pathlib import Path
import json
import math
import re
import pickle
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(str(text))]


class HybridRetriever:
    """Hybrid retrieval: dense sentence embeddings when available, TF-IDF fallback, BM25 and RRF."""
    def __init__(self, chunks: list[dict], storage_dir: Path, embedding_backend: str = "auto", model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.chunks = chunks
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_backend = "tfidf"
        self.embedder = None
        self.vectorizer = None
        self.matrix = None
        if not chunks:
            return
        texts = [c["content"] for c in chunks]
        if embedding_backend in {"auto", "sentence-transformers", "sentence_transformers"}:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer(model_name)
                self.matrix = self.embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                self.embedding_backend = "sentence-transformers"
                np.save(self.storage_dir / "embeddings.npy", np.asarray(self.matrix, dtype=np.float32))
            except Exception:
                self.embedder = None
        if self.embedder is None:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
            try:
                self.matrix = self.vectorizer.fit_transform(texts)
            except ValueError:
                self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b")
                self.matrix = self.vectorizer.fit_transform(texts)
            self.embedding_backend = "tfidf-fallback"
            with open(self.storage_dir / "tfidf_vectorizer.pkl", "wb") as f:
                pickle.dump(self.vectorizer, f)
            # CSR arrays are serialized for inspection/reproducibility without requiring a vector DB server.
            np.savez_compressed(self.storage_dir / "tfidf_matrix.npz", data=self.matrix.data,
                                indices=self.matrix.indices, indptr=self.matrix.indptr, shape=self.matrix.shape)
        (self.storage_dir / "chunks.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks), encoding="utf-8")
        self.tokenized = [tokenize(c["content"]) for c in chunks]
        self.avgdl = (sum(map(len, self.tokenized)) / len(self.tokenized)) if self.tokenized else 0.0
        self.doc_freq = Counter()
        for tokens in self.tokenized:
            self.doc_freq.update(set(tokens))

    def _semantic_scores(self, query: str) -> np.ndarray:
        if self.matrix is None or not self.chunks:
            return np.zeros(len(self.chunks))
        if self.embedder is not None:
            qv = self.embedder.encode([query], normalize_embeddings=True, show_progress_bar=False)
            sims = np.asarray(self.matrix) @ np.asarray(qv[0])
            return np.asarray(sims).reshape(-1)
        qv = self.vectorizer.transform([query])
        return cosine_similarity(qv, self.matrix).reshape(-1)

    def _bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        q_tokens = set(tokenize(query))
        n = len(self.tokenized)
        scores = np.zeros(n, dtype=float)
        if not n:
            return scores
        for i, tokens in enumerate(self.tokenized):
            tf = Counter(tokens)
            dl = len(tokens)
            score = 0.0
            for term in q_tokens:
                f = tf.get(term, 0)
                if not f:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = f + k1 * (1 - b + b * (dl / (self.avgdl or 1)))
                score += idf * (f * (k1 + 1) / denom)
            scores[i] = score
        return scores

    def search(self, query: str, dataset_id: str, initiative_id: str | None = None, top_k: int = 5, section: str | None = None) -> list[dict]:
        eligible = [i for i, c in enumerate(self.chunks)
                    if c.get("dataset_id") == dataset_id
                    and (not initiative_id or c.get("initiative_id") == initiative_id)
                    and (not section or c.get("section", "").lower() == section.lower())]
        if not eligible:
            return []
        sem = self._semantic_scores(query)
        bm = self._bm25_scores(query)
        sem_order = sorted(eligible, key=lambda i: float(sem[i]), reverse=True)
        bm_order = sorted(eligible, key=lambda i: float(bm[i]), reverse=True)
        sem_rank = {idx: rank + 1 for rank, idx in enumerate(sem_order)}
        bm_rank = {idx: rank + 1 for rank, idx in enumerate(bm_order)}
        combined = []
        for idx in eligible:
            rrf = 1/(60 + sem_rank[idx]) + 1/(60 + bm_rank[idx])
            bm_norm = float(bm[idx] / bm.max()) if bm.max() > 0 else 0.0
            combined.append((idx, rrf, float(sem[idx]), bm_norm))
        combined.sort(key=lambda x: x[1], reverse=True)
        out = []
        for idx, rrf, sem_score, bm_norm in combined[:top_k]:
            item = dict(self.chunks[idx])
            item["rrf_score"] = rrf
            item["semantic_score"] = sem_score
            item["bm25_score"] = bm_norm
            item["relevance_score"] = max(sem_score, bm_norm)
            out.append(item)
        return out

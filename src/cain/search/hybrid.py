"""Bounded hybrid ranking of explicitly configured document snapshots."""

from dataclasses import replace
import math
from pathlib import Path
import re
from typing import Iterable

from cain.common.text import tokens
from cain.search import LocalDocumentRetriever, SearchError, SearchResult, STOP_WORDS
from cain.search.embeddings import EmbeddingProvider, SQLiteEmbeddingCache, normalize_vectors


class HybridDocumentRetriever:
    """Lexical coverage + positive cosine, with exact identifier matches prioritized.

    Weights and similarity threshold are prototype heuristics, not calibrated
    relevance probabilities. Ties are resolved by source and character offsets.
    Documents refresh before each search; cached unchanged chunks avoid inference.
    """

    def __init__(
        self, corpus: dict[str, str] | None = None, paths: Iterable[str | Path] = (), *,
        embedding: EmbeddingProvider, cache_path: str | Path | None = None,
        lexical_weight: float = 0.45, semantic_weight: float = 0.55,
        max_file_bytes: int = 262144, max_files: int = 200, max_chunks: int = 1000,
        min_semantic_score: float = 0.35, max_query_chars: int = 4096,
        query_instruction: str = "Retrieve relevant passages from the configured documents that answer the question.",
    ):
        weights = (lexical_weight, semantic_weight)
        if any(not math.isfinite(value) or value <= 0 for value in weights):
            raise ValueError("Busca híbrida requer pesos positivos e finitos para ambos os sinais")
        if not -1 <= min_semantic_score <= 1 or max_chunks < 1 or max_query_chars < 1:
            raise ValueError("Limites de busca híbrida inválidos")
        if not getattr(embedding, "model", "") or not getattr(embedding, "model_digest", ""):
            raise ValueError("Busca híbrida requer modelo e digest do embedding")
        self.corpus, self.paths = dict(corpus or {}), tuple(paths)
        self.embedding = SQLiteEmbeddingCache(embedding, cache_path) if cache_path is not None else embedding
        self.lexical_weight = lexical_weight / sum(weights)
        self.semantic_weight = semantic_weight / sum(weights)
        self.max_file_bytes, self.max_files, self.max_chunks = max_file_bytes, max_files, max_chunks
        self.min_semantic_score, self.max_query_chars = min_semantic_score, max_query_chars
        self.query_instruction = query_instruction
        self.local = self._snapshot()

    def _snapshot(self) -> LocalDocumentRetriever:
        try:
            local = LocalDocumentRetriever(self.corpus, self.paths, self.max_file_bytes, self.max_files)
        except (OSError, UnicodeError) as exc:
            raise SearchError(f"Não foi possível carregar as fontes configuradas: {exc}") from exc
        if len(local._passages) > self.max_chunks:
            raise SearchError(f"Fontes excedem o limite de {self.max_chunks} trechos; sem truncamento")
        return local

    @staticmethod
    def _identifiers(query: str) -> set[str]:
        candidates = [value.rstrip(".,:;-") for value in re.findall(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", query)]
        return {value.casefold() for value in candidates if "_" in value
                or (any(char.isdigit() for char in value) and len(value) >= 3)}

    def search(self, query: str, k: int = 3) -> list[SearchResult]:
        if k < 1:
            return []
        if not isinstance(query, str) or not query.strip():
            return []
        if len(query) > self.max_query_chars:
            raise SearchError(f"Consulta excede {self.max_query_chars} caracteres; sem truncamento")
        self.local = self._snapshot()
        passages = self.local._passages
        if not passages:
            return []
        query_text = f"Instruct: {self.query_instruction}\nQuery: {query}" if self.query_instruction else query
        try:
            vectors = normalize_vectors(self.embedding.embed([query_text] + [p.text for p in passages]),
                                        len(passages) + 1)
        except SearchError:
            raise
        except Exception as exc:
            raise SearchError(f"Embedding falhou; busca híbrida não usou fallback lexical: {exc}") from exc
        query_vector, document_vectors = vectors[0], vectors[1:]
        terms, identifiers = tokens(query) - STOP_WORDS, self._identifiers(query)
        results = []
        for passage, vector in zip(passages, document_vectors):
            cosine = max(-1.0, min(1.0, math.fsum(a * b for a, b in zip(query_vector, vector))))
            lexical = len(terms & tokens(passage.text + " " + passage.title)) / len(terms) if terms else 0.0
            exact = sum(bool(re.search(r"(?<![\w.-])" + re.escape(value) + r"(?![\w.-])",
                                       passage.text.casefold())) for value in identifiers)
            if not lexical and not exact and cosine < self.min_semantic_score:
                continue
            score = self.lexical_weight * lexical + self.semantic_weight * max(0.0, cosine)
            metadata = {**passage.metadata, "retrieval_mode": "hybrid", "lexical_score": lexical,
                        "semantic_score": cosine, "exact_identifier_matches": exact,
                        "embedding_model": self.embedding.model,
                        "embedding_model_digest": self.embedding.model_digest}
            results.append(replace(passage, score=score, metadata=metadata))
        return sorted(results, key=lambda item: (-item.metadata["exact_identifier_matches"], -item.score,
                                                item.source, item.start_offset, item.chunk_id))[:k]

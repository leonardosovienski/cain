"""Temporary lexical index: token overlap, NO embeddings or semantic claims.

This stdlib adapter demonstrates the ADR-0009 rebuild contract; ChromaDB remains
an unimplemented production/research adapter. All indexed data must originate in
IdentityStore.append_signal; the index itself is a disposable cache.
"""

from copy import deepcopy

from cain.common import Hit, MemoryDocument
from cain.common.text import tokens
from cain.persistence import IdentityStore


class LexicalMemoryIndex:
    def __init__(self):
        self._documents: dict[str, MemoryDocument] = {}

    def index(self, doc_id: str, text: str, metadata: dict) -> None:
        if not isinstance(metadata.get("user_id"), str) or not metadata["user_id"]:
            raise ValueError("Every memory document needs an explicit user_id")
        self._documents[doc_id] = MemoryDocument(doc_id, text, deepcopy(metadata))

    def query(self, text: str, k: int, filters: dict | None = None) -> list[Hit]:
        if k < 0:
            raise ValueError("k must be non-negative")
        query_tokens = tokens(text)
        hits = []
        for document in self._documents.values():
            if filters and any(document.metadata.get(key) != value for key, value in filters.items()):
                continue
            terms = tokens(document.text)
            overlap = query_tokens & terms
            if overlap:
                score = len(overlap) / len(query_tokens | terms)
                hits.append(Hit(document.doc_id, document.text, score, deepcopy(document.metadata)))
        return sorted(hits, key=lambda hit: (-hit.score, hit.doc_id))[:k]

    def drop(self) -> None:
        self._documents.clear()

    def rebuild_from(self, source: IdentityStore) -> None:
        rebuilt = LexicalMemoryIndex()
        for document in source.iter_documents():
            rebuilt.index(document.doc_id, document.text, document.metadata)
        self._documents = rebuilt._documents

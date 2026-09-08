from contextlib import closing
from hashlib import sha256
import io
import json
import sqlite3
from urllib.error import URLError

import pytest

from cain.search import OllamaEmbedding, SearchError, SQLiteEmbeddingCache


class FakeOpener:
    def __init__(self, vectors=None, error=None):
        self.vectors, self.error, self.calls = vectors, error, []

    def open(self, request, timeout):
        body = json.loads(request.data)
        self.calls.append((request.full_url, body, timeout))
        if self.error:
            raise self.error
        vectors = self.vectors if self.vectors is not None else [[3.0, 4.0] for _ in body["input"]]
        return io.BytesIO(json.dumps({"model": body["model"], "embeddings": vectors}).encode())


def test_ollama_embed_uses_bounded_batches_no_truncation_and_normalizes():
    provider = OllamaEmbedding(model_digest="sha256:fixed", dimensions=2, max_batch_size=2, timeout=7)
    provider._opener = FakeOpener()
    assert provider.embed(["first", "second", "third"]) == [[0.6, 0.8]] * 3
    assert [len(body["input"]) for _, body, _ in provider._opener.calls] == [2, 1]
    for url, body, timeout in provider._opener.calls:
        assert url.endswith("/api/embed")
        assert body["truncate"] is False
        assert body["dimensions"] == 2
        assert timeout == 7


@pytest.mark.parametrize("vectors", [
    [], [[0.0, 0.0]], [[float("nan"), 1.0]], [[float("inf"), 1.0]],
    [[True, 1.0]], [["1", 2]], [[1.0]], [[1.0, 2.0], [1.0, 2.0]],
])
def test_invalid_embedding_vectors_fail_explicitly_without_retry(vectors):
    provider = OllamaEmbedding(model_digest="digest", dimensions=2)
    provider._opener = FakeOpener(vectors=vectors)
    with pytest.raises(SearchError):
        provider.embed(["document"])
    assert len(provider._opener.calls) == 1


def test_embedding_input_limit_and_external_failure_are_visible():
    provider = OllamaEmbedding(model_digest="digest", max_input_chars=4)
    provider._opener = FakeOpener(error=URLError("offline"))
    with pytest.raises(SearchError, match="sem truncamento"):
        provider.embed(["oversized"])
    assert provider._opener.calls == []
    with pytest.raises(SearchError, match="sem retry ou fallback"):
        provider.embed(["text"])
    assert len(provider._opener.calls) == 1


class CountingEmbedding:
    model = "fixture"
    dimensions = 2

    def __init__(self, digest="v1"):
        self.model_digest, self.calls = digest, []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[3, 4] for _ in texts]


def test_cache_reuses_vectors_and_invalidates_changed_text_and_model(tmp_path):
    path = tmp_path / "cache.sqlite"
    first = CountingEmbedding()
    cache = SQLiteEmbeddingCache(first, path)
    assert cache.embed(["document", "document", "query"]) == [[0.6, 0.8]] * 3
    assert first.calls == [["document", "query"]]
    reopened_provider = CountingEmbedding()
    reopened = SQLiteEmbeddingCache(reopened_provider, path)
    assert reopened.embed(["query", "document"]) == [[0.6, 0.8]] * 2
    assert reopened_provider.calls == []
    reopened.embed(["document updated", "query"])
    assert reopened_provider.calls == [["document updated"]]
    changed = CountingEmbedding("v2")
    SQLiteEmbeddingCache(changed, path).embed(["document"])
    assert changed.calls == [["document"]]
    with closing(sqlite3.connect(path)) as connection:
        saved = connection.execute("SELECT text_hash FROM embedding_cache").fetchall()
    assert (sha256(b"document updated").hexdigest(),) in saved
    assert ("document updated",) not in saved


def test_cache_does_not_mask_corruption_or_dimension_changes(tmp_path):
    provider = CountingEmbedding()
    path = tmp_path / "cache.sqlite"
    cache = SQLiteEmbeddingCache(provider, path)
    cache.embed(["document"])
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE embedding_cache SET vector_json='[0,0]'")
    with pytest.raises(SearchError, match="norma nula"):
        cache.embed(["document"])
    assert len(provider.calls) == 1
    provider.dimensions = 3
    with pytest.raises(SearchError, match="Modelo do cache foi alterado"):
        cache.embed(["document"])


def test_cached_and_fresh_vectors_must_share_dimension(tmp_path):
    provider = CountingEmbedding()
    provider.dimensions = None
    path = tmp_path / "cache.sqlite"
    SQLiteEmbeddingCache(provider, path).embed(["old"])
    changed = CountingEmbedding()
    changed.dimensions = None
    changed.embed = lambda texts: [[1, 2, 3] for _ in texts]
    with pytest.raises(SearchError, match="Dimensão"):
        SQLiteEmbeddingCache(changed, path).embed(["old", "new"])

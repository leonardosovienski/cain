"""Ollama embeddings and disposable SQLite cache, separate from authoritative memory.

API: https://docs.ollama.com/api/embed (consulted 2026-09-07).
The composition root supplies a resolved model digest. This adapter never pulls models.
"""

from contextlib import closing
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
from typing import Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cain.search import SearchError


class EmbeddingProvider(Protocol):
    model: str
    model_digest: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def normalize_vectors(vectors, expected_count: int, expected_dim: int | None = None) -> list[list[float]]:
    if not isinstance(vectors, (list, tuple)) or len(vectors) != expected_count:
        raise SearchError("Embedding retornou quantidade de vetores diferente das entradas")
    normalized = []
    dimension = expected_dim
    for vector in vectors:
        if not isinstance(vector, (list, tuple)) or not vector:
            raise SearchError("Embedding retornou vetor vazio ou inválido")
        if dimension is None:
            dimension = len(vector)
        if len(vector) != dimension:
            raise SearchError("Dimensão de embedding inconsistente")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) for value in vector):
            raise SearchError("Embedding contém valor não numérico ou não finito")
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm <= 0:
            raise SearchError("Embedding possui norma nula ou não finita")
        normalized.append([float(value) / norm for value in vector])
    return normalized


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SearchError("Servidor de embeddings tentou redirecionar a entrada")


class OllamaEmbedding:
    def __init__(
        self, model: str = "qwen3-embedding:0.6b", *, model_digest: str,
        base_url: str = "http://127.0.0.1:11434", timeout: float = 30.0,
        max_input_chars: int = 8192, max_batch_size: int = 32,
        dimensions: int | None = None,
    ):
        if not isinstance(model, str) or not model.strip() or not isinstance(model_digest, str) or not model_digest.strip():
            raise ValueError("Embedding requer modelo e digest explícitos")
        if timeout <= 0 or max_input_chars < 1 or max_batch_size < 1:
            raise ValueError("Limites de embedding devem ser positivos")
        if dimensions is not None and (isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions < 1):
            raise ValueError("Dimensão de embedding deve ser inteira positiva")
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Servidor de embedding deve ser HTTP(S) sem credenciais na URL")
        self.model, self.model_digest = model, model_digest
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.max_input_chars, self.max_batch_size = max_input_chars, max_batch_size
        self.dimensions = dimensions
        self._observed_dimension = dimensions
        self._opener = build_opener(_NoRedirect())

    def validate_inputs(self, texts: Sequence[str]) -> list[str]:
        if isinstance(texts, (str, bytes)) or not isinstance(texts, (list, tuple)):
            raise ValueError("Embedding requer uma sequência de textos")
        result = list(texts)
        if any(not isinstance(text, str) or not text.strip() for text in result):
            raise SearchError("Entrada de embedding vazia ou não textual")
        if any(len(text) > self.max_input_chars for text in result):
            raise SearchError(f"Entrada de embedding excede {self.max_input_chars} caracteres; sem truncamento")
        return result

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        texts = self.validate_inputs(texts)
        vectors = []
        for start in range(0, len(texts), self.max_batch_size):
            batch = texts[start:start + self.max_batch_size]
            body = {"model": self.model, "input": batch, "truncate": False}
            if self.dimensions is not None:
                body["dimensions"] = self.dimensions
            request = Request(self.base_url + "/api/embed", data=json.dumps(body).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise SearchError("Resposta de embedding excedeu 4 MiB")
                result = json.loads(raw.decode("utf-8"))
            except (HTTPError, URLError, OSError, ValueError) as exc:
                raise SearchError(f"Falha no serviço de embedding, sem retry ou fallback: {exc}") from exc
            if not isinstance(result, dict) or result.get("error"):
                raise SearchError("Serviço de embedding retornou erro ou objeto inválido")
            if result.get("model") != self.model:
                raise SearchError("Serviço de embedding respondeu com modelo diferente do configurado")
            batch_vectors = normalize_vectors(result.get("embeddings"), len(batch), self._observed_dimension)
            if batch_vectors:
                self._observed_dimension = len(batch_vectors[0])
            vectors.extend(batch_vectors)
        return vectors


class SQLiteEmbeddingCache:
    """Derived vectors keyed by model, caller-resolved digest, dimensions and input hash.

    Original source text is never stored here. A changed chunk is a cache miss; old
    entries are harmless and can be discarded with the entire cache file.
    """

    def __init__(self, provider: EmbeddingProvider, cache_path: str | Path):
        if not getattr(provider, "model", "") or not getattr(provider, "model_digest", ""):
            raise ValueError("Cache requer identidade e digest do modelo")
        self.provider = provider
        self.model, self.model_digest = provider.model, provider.model_digest
        self.dimensions = getattr(provider, "dimensions", None)
        self.namespace = json.dumps([self.model, self.model_digest, self.dimensions], separators=(",", ":"))
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._observed_dimension = self.dimensions
        try:
            with closing(sqlite3.connect(self.cache_path)) as connection, connection:
                connection.execute("""CREATE TABLE IF NOT EXISTS embedding_cache (
                    namespace TEXT NOT NULL, text_hash TEXT NOT NULL, dimension INTEGER NOT NULL,
                    vector_json TEXT NOT NULL, PRIMARY KEY(namespace, text_hash))""")
        except sqlite3.Error as exc:
            raise SearchError(f"Cache de embeddings indisponível: {exc}") from exc

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if (self.provider.model != self.model or self.provider.model_digest != self.model_digest
                or getattr(self.provider, "dimensions", None) != self.dimensions):
            raise SearchError("Modelo do cache foi alterado; construa um cache com a nova identidade")
        if isinstance(texts, (str, bytes)):
            raise ValueError("Embedding requer uma sequência de textos")
        texts = list(texts)
        if hasattr(self.provider, "validate_inputs"):
            self.provider.validate_inputs(texts)
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise SearchError("Entrada de embedding vazia ou não textual")
        hashes = [sha256(text.encode("utf-8")).hexdigest() for text in texts]
        resolved = {}
        missing = dict(zip(hashes, texts))
        try:
            with closing(sqlite3.connect(self.cache_path)) as connection, connection:
                for text_hash in list(missing):
                    row = connection.execute(
                        "SELECT dimension, vector_json FROM embedding_cache WHERE namespace=? AND text_hash=?",
                        (self.namespace, text_hash),
                    ).fetchone()
                    if row is not None:
                        parsed = normalize_vectors([json.loads(row[1])], 1, row[0])[0]
                        resolved[text_hash] = parsed
                        missing.pop(text_hash)
                if missing:
                    generated = normalize_vectors(self.provider.embed(list(missing.values())), len(missing),
                                                  self._observed_dimension)
                    for text_hash, vector in zip(missing, generated):
                        resolved[text_hash] = vector
                vectors = normalize_vectors([resolved[text_hash] for text_hash in hashes], len(texts),
                                            self._observed_dimension)
                if vectors:
                    self._observed_dimension = len(vectors[0])
                for text_hash in missing:
                    vector = resolved[text_hash]
                    connection.execute("INSERT OR REPLACE INTO embedding_cache VALUES (?, ?, ?, ?)",
                                       (self.namespace, text_hash, len(vector), json.dumps(vector)))
                return vectors
        except (sqlite3.Error, json.JSONDecodeError) as exc:
            raise SearchError(f"Cache de embeddings inválido ou indisponível: {exc}") from exc

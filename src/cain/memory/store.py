"""Bitemporal memory: an append-only, hash-chained event log with disposable projections.

Source of truth: ``memory_events``. Each event is canonicalized with RFC 8785 (JCS) and
chained by sha256; UPDATE, DELETE and REPLACE on it are refused by triggers. The fact and
document tables and the vector index are projections rebuilt from the log at any time
(``rebuild_index``) and checked against it (``verify``).

Two clocks, never mixed:
* transaction time: ``recorded_at`` is assigned by this store's clock when the event is
  appended (never supplied by a caller) and must not go backwards;
* valid time: ``valid_from``/``valid_to`` for facts and ``published_at`` for documents are
  supplied by the source.

Every read takes a mandatory ``as_of`` and sees exactly what was recorded at that instant:
``recorded_at <= as_of AND (superseded_at IS NULL OR superseded_at > as_of)`` (documents
also ``published_at <= as_of``). Semantic search applies that filter before any vector is
compared. Corrections never delete: the old row gets ``superseded_at`` and the new row
points to it with ``supersedes``.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Callable, Iterable, Sequence
from uuid import uuid4

from cain.memory.jcs import canonicalize

EVENT_SCHEMA = "cain-memory-event/1"
GENESIS = "cain-memory-log/1"
STATUSES = ("DECLARED", "PROVEN")
KINDS = ("fact.asserted", "document.recorded")
_CUBE = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_TEXT_ID = re.compile(r"[^\x00-\x1f\x7f]{1,300}\Z")
_TOKEN = re.compile(r"\w+", re.UNICODE)
_INSTANT = "%Y-%m-%dT%H:%M:%S.%fZ"
MAX_TEXT = 200_000


class MemoryStoreError(ValueError):
    """Fail-closed rejection with a stable code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def instant(value) -> str:
    """Normalize an aware datetime or ISO-8601 text with offset to the stored UTC form."""
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise MemoryStoreError("INVALID_INSTANT", f"not ISO-8601: {value!r}") from exc
    if not isinstance(value, datetime):
        raise MemoryStoreError("INVALID_INSTANT", "expected datetime or ISO-8601 text")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MemoryStoreError("INVALID_INSTANT", "instant without timezone is ambiguous")
    return value.astimezone(timezone.utc).strftime(_INSTANT)


def _optional_instant(value) -> str | None:
    return None if value is None else instant(value)


def _cube(value) -> str:
    if type(value) is not str or not _CUBE.match(value):
        raise MemoryStoreError("INVALID_CUBE", f"cube must match {_CUBE.pattern!r}")
    return value


def _text(value, field: str, *, limit: int = 300) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit or not _TEXT_ID.match(value[:300]):
        raise MemoryStoreError("INVALID_FIELD", f"{field} must be printable text of 1-{limit} characters")
    return value


def _cubes(cubes, cross_cube: bool) -> list[str]:
    if isinstance(cubes, str) or not isinstance(cubes, (list, tuple)) or not cubes:
        raise MemoryStoreError("CUBE_REQUIRED", "reads name the cube(s) explicitly")
    selected = sorted({_cube(c) for c in cubes})
    if len(selected) > 1 and cross_cube is not True:
        raise MemoryStoreError("CROSS_CUBE_NOT_EXPLICIT", "reading several cubes requires cross_cube=True")
    return selected


def _tokens(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN.findall(text)]


class MemoryStore:
    """SQLite-backed bitemporal memory. One connection per operation."""

    def __init__(self, path: str | Path, *, clock: Callable[[], datetime] = utc_now, embedding=None):
        self.path = Path(path)
        self.clock = clock
        self.embedding = embedding
        if embedding is not None and (not getattr(embedding, "model", "") or not getattr(embedding, "model_digest", "")):
            raise MemoryStoreError("EMBEDDING_IDENTITY", "vector index requires embedding model and digest")
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(_SCHEMA)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    # ------------------------------------------------------------------ log
    @staticmethod
    def _entry_hash(event: dict) -> str:
        return sha256(canonicalize(event)).hexdigest()

    def _append(self, db, kind: str, body: dict) -> dict:
        last = db.execute("SELECT recorded_at, entry_hash FROM memory_events ORDER BY seq DESC LIMIT 1").fetchone()
        recorded_at = instant(self.clock())
        if last is not None and recorded_at < last["recorded_at"]:
            raise MemoryStoreError("CLOCK_WENT_BACKWARDS",
                              f"recorded_at {recorded_at} is before the log head {last['recorded_at']}")
        event = {
            "schema": EVENT_SCHEMA,
            "event_id": "event:" + uuid4().hex,
            "kind": kind,
            "recorded_at": recorded_at,
            "previous_hash": last["entry_hash"] if last else GENESIS,
            "body": body,
        }
        raw = canonicalize(event).decode("utf-8")
        entry = sha256(raw.encode("utf-8")).hexdigest()
        cursor = db.execute(
            "INSERT INTO memory_events(event_id, kind, recorded_at, body, previous_hash, entry_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event["event_id"], kind, recorded_at, raw, event["previous_hash"], entry),
        )
        self._apply(db, event, cursor.lastrowid)
        return event

    @staticmethod
    def _apply(db, event: dict, seq: int) -> None:
        body, at = event["body"], event["recorded_at"]
        if event["kind"] == "fact.asserted":
            db.execute(
                "INSERT INTO memory_facts VALUES (?,?,?,?,?,?,?,?,NULL,?,?,?,?,?,?,?,?)",
                (body["id"], body["cube"], body["subject"], body["predicate"],
                 canonicalize(body["object"]).decode("utf-8"), body["valid_from"], body["valid_to"], at,
                 body["supersedes"], body["source_episode_id"], body["source_hash"], body["extractor_model"],
                 body["extractor_prompt_hash"], body["extractor_version"], body["status"], seq),
            )
            table = "memory_facts"
        elif event["kind"] == "document.recorded":
            db.execute(
                "INSERT INTO memory_documents VALUES (?,?,?,?,?,?,?,NULL,?,?,?)",
                (body["id"], body["cube"], body["title"], body["text"], body["content_sha256"],
                 body["published_at"], at, body["supersedes"], body["source"], seq),
            )
            table = "memory_documents"
        else:
            raise MemoryStoreError("UNKNOWN_EVENT", f"cannot project {event['kind']!r}")
        if body["supersedes"] is not None:
            changed = db.execute(
                f"UPDATE {table} SET superseded_at=? WHERE id=? AND cube=? AND superseded_at IS NULL",
                (at, body["supersedes"], body["cube"]),
            ).rowcount
            if changed != 1:
                raise MemoryStoreError("SUPERSEDES_UNKNOWN", "supersedes must name a current row in the same cube")

    def verify(self) -> dict:
        """Recompute the chain and compare the projections with a replay of the log."""
        expected, entries, broken_at, head_at = GENESIS, 0, None, None
        replay = sqlite3.connect(":memory:")
        replay.row_factory = sqlite3.Row
        replay.executescript(_SCHEMA)
        with self.connection() as db:
            for row in db.execute("SELECT * FROM memory_events ORDER BY seq"):
                entries += 1
                try:
                    event = json.loads(row["body"])
                    ok = (canonicalize(event).decode("utf-8") == row["body"]
                          and event["previous_hash"] == expected == row["previous_hash"]
                          and sha256(row["body"].encode("utf-8")).hexdigest() == row["entry_hash"]
                          and event["event_id"] == row["event_id"] and event["kind"] == row["kind"]
                          and event["recorded_at"] == row["recorded_at"])
                except (ValueError, KeyError, TypeError):
                    ok = False
                if ok:
                    try:
                        self._apply(replay, event, row["seq"])
                    except (MemoryStoreError, sqlite3.Error, KeyError, TypeError):
                        ok = False
                if not ok:
                    broken_at = row["seq"]
                    break
                expected, head_at = row["entry_hash"], row["recorded_at"]
            projection = "not_checked"
            if broken_at is None:
                projection = "consistent"
                for table in ("memory_facts", "memory_documents"):
                    stored = [tuple(r) for r in db.execute(f"SELECT * FROM {table} ORDER BY id")]
                    rebuilt = [tuple(r) for r in replay.execute(f"SELECT * FROM {table} ORDER BY id")]
                    if stored != rebuilt:
                        projection = "diverged"
        replay.close()
        return {"entries": entries, "status": "intact" if broken_at is None else "broken",
                "broken_at": broken_at, "head": expected, "head_recorded_at": head_at,
                "projection": projection}

    def rebuild_index(self) -> dict:
        """Drop every projection and derived vector, then replay the log (the source of truth)."""
        check = self.verify()
        if check["status"] != "intact":
            raise MemoryStoreError("CHAIN_BROKEN", f"log broken at seq {check['broken_at']}; refusing to rebuild")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for table in ("memory_vectors", "memory_facts", "memory_documents"):
                db.execute(f"DELETE FROM {table}")
            events = 0
            for row in db.execute("SELECT seq, body FROM memory_events ORDER BY seq").fetchall():
                self._apply(db, json.loads(row["body"]), row["seq"])
                events += 1
        vectors = self._fill_vectors(all_rows=True) if self.embedding is not None else 0
        return {"events_replayed": events, "vectors": vectors, "head": check["head"]}

    # ------------------------------------------------------------------ writes
    def assert_fact(self, cube, subject, predicate, object_, *, status, valid_from=None, valid_to=None,
                    source_episode_id=None, source_hash=None, extractor_model=None,
                    extractor_prompt_hash=None, extractor_version=None, supersedes=None) -> dict:
        body = {
            "id": "fact:" + uuid4().hex,
            "cube": _cube(cube),
            "subject": _text(subject, "subject"),
            "predicate": _text(predicate, "predicate"),
            "object": object_,
            "valid_from": _optional_instant(valid_from),
            "valid_to": _optional_instant(valid_to),
            "supersedes": supersedes,
            "source_episode_id": None if source_episode_id is None else _text(source_episode_id, "source_episode_id"),
            "source_hash": source_hash,
            "extractor_model": extractor_model,
            "extractor_prompt_hash": extractor_prompt_hash,
            "extractor_version": None if extractor_version is None else _text(extractor_version, "extractor_version"),
            "status": status,
        }
        try:
            canonicalize(object_)  # JSON-representable under RFC 8785, or fail now
        except ValueError as exc:
            raise MemoryStoreError("INVALID_OBJECT", str(exc)) from exc
        if status not in STATUSES:
            raise MemoryStoreError("INVALID_STATUS", f"status must be one of {STATUSES}")
        if source_hash is not None and not re.fullmatch(r"[0-9a-f]{64}", str(source_hash)):
            raise MemoryStoreError("INVALID_FIELD", "source_hash must be sha256 hex")
        if extractor_model is not None and status != "DECLARED":
            raise MemoryStoreError("EXTRACTED_FACT_IS_DECLARED", "a model-extracted fact is born DECLARED")
        if status == "PROVEN" and (source_hash is None or extractor_version is None):
            raise MemoryStoreError("PROVEN_REQUIRES_SOURCE",
                              "PROVEN requires a hashed source and a deterministic extractor version")
        if body["valid_from"] and body["valid_to"] and body["valid_to"] <= body["valid_from"]:
            raise MemoryStoreError("INVALID_VALID_TIME", "valid_to must be after valid_from")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if supersedes is not None:
                old = db.execute("SELECT cube FROM memory_facts WHERE id=?", (supersedes,)).fetchone()
                if old is None or old["cube"] != body["cube"]:
                    raise MemoryStoreError("SUPERSEDES_UNKNOWN", "supersedes must name a fact of the same cube")
            event = self._append(db, "fact.asserted", body)
        return {**body, "recorded_at": event["recorded_at"], "event_id": event["event_id"]}

    def correct_fact(self, fact_id: str, object_, *, reason: str, **fields) -> dict:
        """Supersede a current fact with a corrected one (same cube, subject, predicate)."""
        _text(reason, "reason", limit=2000)
        with self.connection() as db:
            old = db.execute("SELECT * FROM memory_facts WHERE id=?", (fact_id,)).fetchone()
        if old is None:
            raise MemoryStoreError("SUPERSEDES_UNKNOWN", f"unknown fact {fact_id!r}")
        status = fields.pop("status", "DECLARED")
        return self.assert_fact(old["cube"], old["subject"], old["predicate"],
                                {"value": object_, "correction_reason": reason},
                                status=status, supersedes=fact_id, **fields)

    def record_document(self, cube, title, text, *, published_at, source, supersedes=None) -> dict:
        if type(text) is not str or not text.strip() or len(text) > MAX_TEXT:
            raise MemoryStoreError("INVALID_FIELD", f"document text must have 1-{MAX_TEXT} characters")
        body = {
            "id": "doc:" + uuid4().hex,
            "cube": _cube(cube),
            "title": _text(title, "title"),
            "text": text,
            "content_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "published_at": instant(published_at),
            "source": _text(source, "source"),
            "supersedes": supersedes,
        }
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            event = self._append(db, "document.recorded", body)
        return {**body, "recorded_at": event["recorded_at"], "event_id": event["event_id"]}

    # ------------------------------------------------------------------ reads (as_of mandatory)
    @staticmethod
    def _fact_row(row) -> dict:
        fact = dict(row)
        fact["object"] = json.loads(fact["object"])
        fact.pop("event_seq")
        return fact

    def facts(self, *, as_of, cubes: Sequence[str], cross_cube: bool = False, subject=None, predicate=None,
              valid_at=None, statuses: Iterable[str] = STATUSES) -> list[dict]:
        at = instant(as_of)
        selected = _cubes(cubes, cross_cube)
        statuses = sorted(set(statuses))
        if not statuses or any(s not in STATUSES for s in statuses):
            raise MemoryStoreError("INVALID_STATUS", f"statuses must be a non-empty subset of {STATUSES}")
        where = [f"cube IN ({','.join('?' * len(selected))})", _VISIBLE, f"status IN ({','.join('?' * len(statuses))})"]
        params: list = [*selected, at, at, *statuses]
        if subject is not None:
            where.append("subject=?")
            params.append(subject)
        if predicate is not None:
            where.append("predicate=?")
            params.append(predicate)
        if valid_at is not None:
            valid = instant(valid_at)
            where.append("(valid_from IS NULL OR valid_from <= ?) AND (valid_to IS NULL OR valid_to > ?)")
            params.extend([valid, valid])
        with self.connection() as db:
            rows = db.execute("SELECT * FROM memory_facts WHERE " + " AND ".join(where)
                              + " ORDER BY cube, subject, predicate, recorded_at, id", params).fetchall()
        return [_as_of_view(self._fact_row(r), at) for r in rows]

    def fact_history(self, fact_id: str, *, as_of) -> list[dict]:
        """The supersession chain ending at ``fact_id``, as recorded at ``as_of`` (oldest first)."""
        at = instant(as_of)
        chain, current = [], fact_id
        with self.connection() as db:
            while current is not None:
                row = db.execute("SELECT * FROM memory_facts WHERE id=? AND recorded_at <= ?", (current, at)).fetchone()
                if row is None:
                    break
                fact = _as_of_view(self._fact_row(row), at)
                chain.append(fact)
                current = fact["supersedes"]
        return list(reversed(chain))

    def documents(self, *, as_of, cubes: Sequence[str], cross_cube: bool = False) -> list[dict]:
        at = instant(as_of)
        selected = _cubes(cubes, cross_cube)
        with self.connection() as db:
            rows = db.execute(
                f"SELECT * FROM memory_documents WHERE cube IN ({','.join('?' * len(selected))}) AND {_VISIBLE} "
                "AND published_at <= ? ORDER BY cube, published_at, id", [*selected, at, at, at]).fetchall()
        return [_as_of_view({k: row[k] for k in row.keys() if k != "event_seq"}, at) for row in rows]

    def search(self, query: str, *, as_of, cubes: Sequence[str], cross_cube: bool = False, limit: int = 10,
               statuses: Iterable[str] = STATUSES) -> dict:
        """Rank only rows visible at ``as_of``: the temporal filter runs before any vector comparison."""
        if type(query) is not str or not query.strip() or len(query) > 4096:
            raise MemoryStoreError("INVALID_QUERY", "query must have 1-4096 characters")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise MemoryStoreError("INVALID_LIMIT", "limit must be 1-50")
        candidates = [("fact", f["id"], _fact_text(f), f)
                      for f in self.facts(as_of=as_of, cubes=cubes, cross_cube=cross_cube, statuses=statuses)]
        candidates += [("document", d["id"], d["title"] + "\n" + d["text"], d)
                       for d in self.documents(as_of=as_of, cubes=cubes, cross_cube=cross_cube)]
        terms = set(_tokens(query))
        lexical = {}
        for kind, oid, text, _ in candidates:
            tokens = _tokens(text)
            lexical[(kind, oid)] = (len(terms & set(tokens)) / len(terms)) if terms else 0.0
        semantic = {}
        mode = "lexical"
        if self.embedding is not None and candidates:
            mode = "hybrid"
            vectors = self._vectors_for([(kind, oid, text) for kind, oid, text, _ in candidates])
            query_vector = self._embed([query])[0]
            for key, vector in vectors.items():
                semantic[key] = sum(a * b for a, b in zip(query_vector, vector))
        hits = []
        for kind, oid, text, row in candidates:
            score = lexical[(kind, oid)] if mode == "lexical" else 0.45 * lexical[(kind, oid)] + 0.55 * max(
                0.0, semantic[(kind, oid)])
            if score > 0:
                hits.append({"kind": kind, "id": oid, "score": round(score, 12), "cube": row["cube"],
                             "recorded_at": row["recorded_at"], "status": row.get("status"),
                             "text": text[:1000]})
        hits.sort(key=lambda h: (-h["score"], h["kind"], h["id"]))
        return {"as_of": instant(as_of), "cubes": _cubes(cubes, cross_cube), "mode": mode,
                "candidates": len(candidates), "hits": hits[:limit]}

    # ------------------------------------------------------------------ derived vectors
    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.embedding.embed(texts)
        normalized = []
        for vector in vectors:
            norm = math.sqrt(sum(v * v for v in vector))
            if not math.isfinite(norm) or norm <= 0:
                raise MemoryStoreError("EMBEDDING_INVALID", "embedding with zero or non-finite norm")
            normalized.append([v / norm for v in vector])
        return normalized

    def _vectors_for(self, items: list[tuple[str, str, str]]) -> dict:
        model, digest = self.embedding.model, self.embedding.model_digest
        found = {}
        with self.connection() as db:
            for kind, oid, _ in items:
                row = db.execute("SELECT vector FROM memory_vectors WHERE kind=? AND id=? AND model=? AND model_digest=?",
                                 (kind, oid, model, digest)).fetchone()
                if row is not None:
                    found[(kind, oid)] = json.loads(row["vector"])
        missing = [(kind, oid, text) for kind, oid, text in items if (kind, oid) not in found]
        if missing:
            vectors = self._embed([text for _, _, text in missing])
            with self.connection() as db:
                for (kind, oid, _), vector in zip(missing, vectors):
                    db.execute("INSERT OR REPLACE INTO memory_vectors VALUES (?,?,?,?,?)",
                               (kind, oid, model, digest, json.dumps(vector)))
                    found[(kind, oid)] = vector
        return found

    def _fill_vectors(self, *, all_rows: bool) -> int:
        with self.connection() as db:
            facts = [self._fact_row(r) for r in db.execute("SELECT * FROM memory_facts")]
            docs = [dict(r) for r in db.execute("SELECT * FROM memory_documents")]
        items = [("fact", f["id"], _fact_text(f)) for f in facts] + [
            ("document", d["id"], d["title"] + "\n" + d["text"]) for d in docs]
        return len(self._vectors_for(items)) if items else 0


def _as_of_view(row: dict, at: str) -> dict:
    """Hide supersession that happened after ``at``: an as-of read must not reveal the future."""
    if row["superseded_at"] is not None and row["superseded_at"] > at:
        row["superseded_at"] = None
    return row


def _fact_text(fact: dict) -> str:
    value = fact["object"]
    rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    return f"{fact['subject']} {fact['predicate']} {rendered}"


_VISIBLE = "recorded_at <= ? AND (superseded_at IS NULL OR superseded_at > ?)"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT UNIQUE NOT NULL,
  kind TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  body TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  entry_hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS memory_events_no_update BEFORE UPDATE ON memory_events
BEGIN SELECT RAISE(ABORT, 'memory event log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS memory_events_no_delete BEFORE DELETE ON memory_events
BEGIN SELECT RAISE(ABORT, 'memory event log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS memory_events_no_replace BEFORE INSERT ON memory_events
WHEN EXISTS (SELECT 1 FROM memory_events WHERE event_id = NEW.event_id OR seq = NEW.seq)
BEGIN SELECT RAISE(ABORT, 'memory event log is append-only'); END;
CREATE TABLE IF NOT EXISTS memory_facts (
  id TEXT PRIMARY KEY, cube TEXT NOT NULL, subject TEXT NOT NULL, predicate TEXT NOT NULL,
  object TEXT NOT NULL, valid_from TEXT, valid_to TEXT, recorded_at TEXT NOT NULL,
  superseded_at TEXT, supersedes TEXT, source_episode_id TEXT, source_hash TEXT,
  extractor_model TEXT, extractor_prompt_hash TEXT, extractor_version TEXT,
  status TEXT NOT NULL CHECK(status IN ('DECLARED','PROVEN')), event_seq INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS memory_facts_visible ON memory_facts(cube, recorded_at, superseded_at);
CREATE INDEX IF NOT EXISTS memory_facts_source ON memory_facts(cube, source_hash);
CREATE TABLE IF NOT EXISTS memory_documents (
  id TEXT PRIMARY KEY, cube TEXT NOT NULL, title TEXT NOT NULL, text TEXT NOT NULL,
  content_sha256 TEXT NOT NULL, published_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
  superseded_at TEXT, supersedes TEXT, source TEXT NOT NULL, event_seq INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS memory_documents_visible ON memory_documents(cube, recorded_at, published_at);
CREATE TABLE IF NOT EXISTS memory_vectors (
  kind TEXT NOT NULL, id TEXT NOT NULL, model TEXT NOT NULL, model_digest TEXT NOT NULL,
  vector TEXT NOT NULL, PRIMARY KEY(kind, id, model, model_digest)
);
"""

"""Authenticated, correlated and idempotent CAIN ResearchResult inbox."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from research_protocol import canonical, digest, loads, verify_result

from cain.research_egress import ResultEgressPolicy


class ResultConflict(ValueError):
    pass


class ResultInbox:
    def __init__(
        self,
        path,
        *,
        task_outbox,
        publisher_identity: str,
        key_id: str | None = None,
        secret: bytes | None = None,
        key_store=None,
        scope: str = "crypto.research.result",
        access_service=None,
        access_origin: dict | None = None,
        access_policy: str = "crypto-result-v1",
        egress_policy: ResultEgressPolicy | None = None,
    ):
        self.path = Path(path)
        self.task_outbox = task_outbox
        self.publisher_identity = publisher_identity
        self.key_id = key_id
        self.secret = secret
        self.key_store = key_store
        self.scope = scope
        self.access_service = access_service
        self.access_origin = access_origin or {
            "domain": "crypto", "repository": "CRIPTO", "publisher": publisher_identity,
            "stream": "research-results", "inputs": {},
        }
        self.access_policy = access_policy
        self.egress_policy = egress_policy or ResultEgressPolicy.local_only()
        if key_store is None and (key_id is None or secret is None):
            raise ValueError("fixed key or operator key store required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS result_inbox(
                  result_id TEXT PRIMARY KEY,
                  task_id TEXT NOT NULL,
                  admission_id TEXT NOT NULL,
                  message_id TEXT NOT NULL UNIQUE,
                  payload_hash TEXT NOT NULL,
                  envelope BLOB NOT NULL,
                  publisher_identity TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  status TEXT NOT NULL CHECK(status IN ('PROCESSED','REJECTED','CONFLICT')),
                  processed_at TEXT NOT NULL,
                  error TEXT
                );
                CREATE INDEX IF NOT EXISTS result_inbox_task ON result_inbox(task_id,result_id);
                CREATE TABLE IF NOT EXISTS result_raw(
                  result_id TEXT PRIMARY KEY, raw_hash TEXT NOT NULL, raw BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS result_canonical(
                  result_id TEXT PRIMARY KEY, raw_hash TEXT NOT NULL,
                  normalizer_name TEXT NOT NULL, normalizer_version TEXT NOT NULL,
                  canonical_hash TEXT NOT NULL, payload BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS result_derived(
                  result_id TEXT PRIMARY KEY, source_ref TEXT NOT NULL,
                  derivation_method TEXT NOT NULL, derivation_version TEXT NOT NULL,
                  created_at TEXT NOT NULL, derived_hash TEXT NOT NULL, payload BLOB NOT NULL
                );
                """
            )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _key(self, identity, key_id):
        if self.key_store is not None:
            return self.key_store.resolve(identity, key_id, self.scope)
        if (identity, key_id) == (self.publisher_identity, self.key_id):
            return self.secret
        return None

    def ingest(self, envelope):
        if (
            envelope.get("producer") != "CRIPTO"
            or envelope.get("consumer") != "CAIN"
            or envelope.get("publisher_identity") != self.publisher_identity
            or envelope.get("scope") != self.scope
        ):
            raise PermissionError("UNAUTHORIZED: result publisher or scope denied")
        if self.key_store is None and envelope.get("key_id") != self.key_id:
            raise PermissionError("UNAUTHORIZED: result publisher key denied")
        verify_result(envelope, self._key)
        result = envelope["payload"]
        context = self.task_outbox.proposed_context(result["task_id"])
        task = context["task"]
        if result["provenance"]["task_payload_hash"] != context["task_payload_hash"]:
            raise PermissionError("UNAUTHORIZED: result task payload identity mismatch")
        for field in ("research_id", "hypothesis_id"):
            if result[field] != task[field]:
                raise PermissionError(f"UNAUTHORIZED: result {field} mismatch")
        raw = canonical(envelope)
        raw_hash = digest(raw)
        normalized = canonical(result)
        canonical_hash = digest(normalized)
        derived = {
            "result_id": result["result_id"], "task_id": result["task_id"],
            "research_id": result["research_id"], "hypothesis_id": result["hypothesis_id"],
            "experiment_id": result["experiment_id"],
            "operational_state": result["ops_facts"]["operational_state"],
            "scientific_state": result["core_facts"]["scientific_state"],
            "economic_state": result["crypto_facts"]["economic_state"],
            "sample_size": result["crypto_facts"]["metrics"]["sample_size"],
            "gross_return_bps": result["crypto_facts"]["metrics"]["gross_return_bps"],
            "net_return_bps": result["crypto_facts"]["metrics"]["net_return_bps"],
            "data_cutoff": result["crypto_facts"]["data_cutoff"],
            "produced_at": result["produced_at"],
        }
        derived_bytes = canonical(derived)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT payload_hash,envelope,status FROM result_inbox WHERE result_id=?",
                (result["result_id"],),
            ).fetchone()
            if previous:
                if previous["payload_hash"] != envelope["payload_hash"]:
                    raise ResultConflict(
                        "CONFLICT: result_id already has a different canonical payload"
                    )
                return {
                    "status": "duplicate",
                    "inbox_status": previous["status"],
                    "result": loads(previous["envelope"])["payload"],
                }
            db.execute(
                "INSERT INTO result_inbox VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    result["result_id"],
                    result["task_id"],
                    result["admission_id"],
                    envelope["message_id"],
                    envelope["payload_hash"],
                    canonical(envelope),
                    envelope["publisher_identity"],
                    envelope["scope"],
                    "PROCESSED",
                    result["produced_at"],
                    None,
                ),
            )
            db.execute("INSERT INTO result_raw VALUES(?,?,?)", (result["result_id"], raw_hash, raw))
            db.execute(
                "INSERT INTO result_canonical VALUES(?,?,?,?,?,?)",
                (result["result_id"], raw_hash, "research-protocol-canonical-json", "1",
                 canonical_hash, normalized),
            )
            db.execute(
                "INSERT INTO result_derived VALUES(?,?,?,?,?,?,?)",
                (result["result_id"], canonical_hash, "authority-preserving-result-summary", "1",
                 datetime.now(UTC).isoformat(), digest(derived_bytes), derived_bytes),
            )
        return {"status": "ingested", "inbox_status": "PROCESSED", "result": result}

    def _authorized(self, research_scope, *, generate=False):
        if self.access_service is None:
            return
        if research_scope is None or not self.access_service.authorized(
            research_scope,
            self.access_origin,
            {"read": True, "generate": generate, "policy": self.access_policy},
            generate=generate,
        ):
            raise PermissionError("UNAUTHORIZED: current identity/scope grant denied")

    def result(self, result_id, *, research_scope=None):
        self._authorized(research_scope)
        with self.connection() as db:
            row = db.execute(
                "SELECT envelope FROM result_inbox WHERE result_id=? AND status='PROCESSED'",
                (result_id,),
            ).fetchone()
        return loads(row["envelope"])["payload"] if row else None

    def for_task(self, task_id, *, research_scope=None):
        self._authorized(research_scope)
        with self.connection() as db:
            rows = db.execute(
                "SELECT envelope FROM result_inbox WHERE task_id=? AND status='PROCESSED' "
                "ORDER BY processed_at,result_id",
                (task_id,),
            ).fetchall()
        return [loads(row["envelope"])["payload"] for row in rows]

    def projection(self, result_id, *, research_scope=None):
        self._authorized(research_scope)
        with self.connection() as db:
            row = db.execute(
                "SELECT raw_hash,canonical_hash,normalizer_name,normalizer_version,"
                "source_ref,derivation_method,derivation_version,created_at,derived_hash,d.payload "
                "FROM result_canonical c JOIN result_derived d USING(result_id) WHERE result_id=?",
                (result_id,),
            ).fetchone()
        if row is None:
            return None
        value = dict(row)
        value["derived"] = loads(value.pop("payload"))
        return value

    def history(self, hypothesis_id, *, research_scope=None):
        self._authorized(research_scope)
        with self.connection() as db:
            rows = db.execute(
                "SELECT d.payload FROM result_derived d JOIN result_inbox i USING(result_id) "
                "ORDER BY i.processed_at,i.result_id"
            ).fetchall()
        values = [loads(row["payload"]) for row in rows]
        return [value for value in values if value["hypothesis_id"] == hypothesis_id]

    def reason(
        self,
        hypothesis_id,
        question,
        provider,
        *,
        research_scope=None,
        data_classification="INTERNAL_RESEARCH",
    ):
        """Policy-authorized egress boundary over the authorized DERIVED projection."""
        self._authorized(research_scope, generate=True)
        history = self.history(hypothesis_id, research_scope=research_scope)
        if not history:
            return {"status": "insufficient_evidence", "answer": None, "sources": []}
        prompt = {
            "question": question,
            "constraints": [
                "operational success does not imply scientific support",
                "scientific support does not imply economic edge",
                "preserve contradictions and uncertainty",
            ],
            "results": history,
        }
        sanitized, egress_receipt = self.egress_policy.prepare(
            provider, data_classification, research_scope or "UNSCOPED", prompt
        )
        answer = provider.generate(sanitized)
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("invalid local provider response")
        return {
            "status": "generated_local" if egress_receipt["base_url"] in {
                "local", "http://127.0.0.1", "http://localhost"
            } else "generated_remote",
            "answer": answer,
            "sources": [item["result_id"] for item in history],
            "egress_receipt": egress_receipt,
        }

"""Authenticated, correlated and idempotent CAIN ResearchResult inbox."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from research_protocol import canonical, loads, verify_result


class ResultConflict(ValueError):
    pass


class ResultInbox:
    def __init__(
        self,
        path,
        *,
        task_outbox,
        publisher_identity: str,
        key_id: str,
        secret: bytes,
        scope: str = "crypto.research.result",
    ):
        self.path = Path(path)
        self.task_outbox = task_outbox
        self.publisher_identity = publisher_identity
        self.key_id = key_id
        self.secret = secret
        self.scope = scope
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
        if (identity, key_id) == (self.publisher_identity, self.key_id):
            return self.secret
        return None

    def ingest(self, envelope):
        if (
            envelope.get("producer") != "CRIPTO"
            or envelope.get("consumer") != "CAIN"
            or envelope.get("publisher_identity") != self.publisher_identity
            or envelope.get("key_id") != self.key_id
            or envelope.get("scope") != self.scope
        ):
            raise PermissionError("UNAUTHORIZED: result publisher or scope denied")
        verify_result(envelope, self._key)
        result = envelope["payload"]
        context = self.task_outbox.proposed_context(result["task_id"])
        task = context["task"]
        if result["provenance"]["task_payload_hash"] != context["task_payload_hash"]:
            raise PermissionError("UNAUTHORIZED: result task payload identity mismatch")
        for field in ("research_id", "hypothesis_id"):
            if result[field] != task[field]:
                raise PermissionError(f"UNAUTHORIZED: result {field} mismatch")
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
        return {"status": "ingested", "inbox_status": "PROCESSED", "result": result}

    def result(self, result_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT envelope FROM result_inbox WHERE result_id=? AND status='PROCESSED'",
                (result_id,),
            ).fetchone()
        return loads(row["envelope"])["payload"] if row else None

    def for_task(self, task_id):
        with self.connection() as db:
            rows = db.execute(
                "SELECT envelope FROM result_inbox WHERE task_id=? AND status='PROCESSED' "
                "ORDER BY processed_at,result_id",
                (task_id,),
            ).fetchall()
        return [loads(row["envelope"])["payload"] for row in rows]

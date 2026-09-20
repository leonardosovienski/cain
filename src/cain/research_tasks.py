"""Durable CAIN proposal outbox; no scheduling or execution capability."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3

from research_protocol import canonical, loads, payload_hash, sign_task, validate_task


class TaskConflict(ValueError):
    pass


class TaskOutbox:
    def __init__(
        self,
        path,
        *,
        publisher_identity: str,
        key_id: str | None = None,
        secret: bytes | None = None,
        key_store=None,
        scope: str = "crypto.research.propose",
    ):
        self.path = Path(path)
        self.publisher_identity = publisher_identity
        self.key_id = key_id
        self.secret = secret
        self.key_store = key_store
        self.scope = scope
        if key_store is None and (key_id is None or secret is None):
            raise ValueError("fixed key or operator key store required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS task_outbox(
                  task_id TEXT PRIMARY KEY,
                  message_id TEXT NOT NULL UNIQUE,
                  payload_hash TEXT NOT NULL,
                  envelope BLOB NOT NULL,
                  status TEXT NOT NULL CHECK(status IN (
                    'PENDING','PUBLISHED','RETRYABLE','DEAD_LETTER')),
                  attempt_count INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  processed_at TEXT,
                  error TEXT
                )
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

    def propose(self, task):
        validate_task(task)
        key_id, secret = (
            self.key_store.signing_key(self.publisher_identity, self.scope)
            if self.key_store is not None
            else (self.key_id, self.secret)
        )
        envelope = sign_task(
            task,
            producer="CAIN",
            publisher_identity=self.publisher_identity,
            consumer="CRIPTO",
            scope=self.scope,
            key_id=key_id,
            secret=secret,
        )
        task_hash = payload_hash(task)
        encoded = canonical(envelope)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT payload_hash,envelope,status FROM task_outbox WHERE task_id=?",
                (task["task_id"],),
            ).fetchone()
            if previous:
                if previous["payload_hash"] != task_hash:
                    raise TaskConflict("CONFLICT: task_id already has a different canonical payload")
                return {
                    "status": "duplicate",
                    "outbox_status": previous["status"],
                    "envelope": loads(previous["envelope"]),
                }
            db.execute(
                "INSERT INTO task_outbox(task_id,message_id,payload_hash,envelope,status,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (
                    task["task_id"],
                    envelope["message_id"],
                    task_hash,
                    encoded,
                    "PENDING",
                    task["created_at"],
                ),
            )
        return {"status": "proposed", "outbox_status": "PENDING", "envelope": envelope}

    def pending(self, limit: int = 100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Invalid outbox limit")
        with self.connection() as db:
            rows = db.execute(
                "SELECT envelope FROM task_outbox WHERE status IN ('PENDING','RETRYABLE') "
                "ORDER BY created_at,task_id LIMIT ?",
                (limit,),
            ).fetchall()
        return [loads(row["envelope"]) for row in rows]

    def record_send(self, task_id: str, message_id: str):
        """Persist an at-least-once delivery attempt before invoking transport."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT envelope,message_id,status FROM task_outbox WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if row is None or row["message_id"] != message_id:
                raise ValueError("ACK_CONFLICT: unknown task/message identity")
            if row["status"] == "PUBLISHED":
                return {"status": "already_published", "envelope": loads(row["envelope"])}
            if row["status"] == "DEAD_LETTER":
                raise ValueError("DELIVERY_BLOCKED: task is dead-lettered")
            db.execute(
                "UPDATE task_outbox SET attempt_count=attempt_count+1,error=NULL WHERE task_id=?",
                (task_id,),
            )
        return {"status": "send_recorded", "envelope": loads(row["envelope"])}

    def acknowledge(self, task_id: str, message_id: str, *, processed_at: str):
        parsed = datetime.fromisoformat(processed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Invalid acknowledgement time")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT message_id,status,attempt_count FROM task_outbox WHERE task_id=?", (task_id,)
            ).fetchone()
            if row is None or row["message_id"] != message_id:
                raise ValueError("ACK_CONFLICT: unknown task/message identity")
            if row["attempt_count"] < 1:
                raise ValueError("ACK_CONFLICT: task has no recorded send")
            if row["status"] != "PUBLISHED":
                db.execute(
                    "UPDATE task_outbox SET status='PUBLISHED',processed_at=?,error=NULL "
                    "WHERE task_id=?",
                    (processed_at, task_id),
                )
        return self.state(task_id)

    def fail_delivery(self, task_id: str, message_id: str, error: str, *, max_attempts=3):
        if type(max_attempts) is not int or max_attempts < 1 or not error:
            raise ValueError("Invalid delivery failure")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT message_id,status,attempt_count FROM task_outbox WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if row is None or row["message_id"] != message_id:
                raise ValueError("ACK_CONFLICT: unknown task/message identity")
            if row["status"] == "PUBLISHED":
                raise ValueError("ACK_CONFLICT: published task cannot fail delivery")
            status = "DEAD_LETTER" if row["attempt_count"] >= max_attempts else "RETRYABLE"
            db.execute(
                "UPDATE task_outbox SET status=?,error=? WHERE task_id=?",
                (status, error[:1000], task_id),
            )
        return self.state(task_id)

    def reconcile(self):
        with self.connection() as db:
            rows = db.execute(
                "SELECT status,count(*) AS count FROM task_outbox GROUP BY status"
            ).fetchall()
        counts = {row["status"]: row["count"] for row in rows}
        return {
            "pending": counts.get("PENDING", 0) + counts.get("RETRYABLE", 0),
            "published": counts.get("PUBLISHED", 0),
            "dead_letters": counts.get("DEAD_LETTER", 0),
        }

    def state(self, task_id: str):
        with self.connection() as db:
            row = db.execute(
                "SELECT task_id,message_id,payload_hash,status,attempt_count,created_at,"
                "processed_at,error FROM task_outbox WHERE task_id=?",
                (task_id,),
            ).fetchone()
        return dict(row) if row else None

    def proposed_context(self, task_id: str):
        with self.connection() as db:
            row = db.execute(
                "SELECT payload_hash,envelope,status FROM task_outbox WHERE task_id=?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise ValueError("TASK_NOT_FOUND")
        envelope = loads(row["envelope"])
        return {
            "task": envelope["payload"],
            "task_payload_hash": row["payload_hash"],
            "outbox_status": row["status"],
        }

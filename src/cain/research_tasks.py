"""Durable CAIN proposal outbox; no scheduling or execution capability."""

from __future__ import annotations

from contextlib import contextmanager
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
        key_id: str,
        secret: bytes,
        scope: str = "crypto.research.propose",
    ):
        self.path = Path(path)
        self.publisher_identity = publisher_identity
        self.key_id = key_id
        self.secret = secret
        self.scope = scope
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
        envelope = sign_task(
            task,
            producer="CAIN",
            publisher_identity=self.publisher_identity,
            consumer="CRIPTO",
            scope=self.scope,
            key_id=self.key_id,
            secret=self.secret,
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

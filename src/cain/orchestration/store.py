"""Durable state of the orchestration: episodes, V2 TaskOutbox, V2 ResultInbox, and the domain memory.

One state directory holds ``orchestration.sqlite`` (the CAIN's own records) and ``memory.sqlite`` (the bitemporal,
hash-chained memory of PR #45). Every table is keyed by domain and every memory fact lives in the domain's cube
(``cube == domain``): a read of one domain never sees another (the store refuses cross-cube reads unless asked).

The domain view given to the DecisionPolicy is rebuilt from these records only:
  * tasks: the CAIN's outbox of the domain (what it emitted);
  * results: facts retrieved from the domain cube, valid at ``as_of`` (valid time = when the domain produced the
    outcome), read at the head of the memory log (transaction time): the same state and ``as_of`` give the same view
    in any process.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from research_protocol import v2

from cain.memory.store import MemoryStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes(
  domain TEXT NOT NULL, number INTEGER NOT NULL, proposal_id TEXT, proposal_sha256 TEXT NOT NULL,
  decision TEXT NOT NULL, reason_code TEXT NOT NULL, receipt BLOB NOT NULL, receipt_sha256 TEXT NOT NULL,
  task_id TEXT, as_of TEXT NOT NULL, source TEXT, PRIMARY KEY(domain, number));
CREATE UNIQUE INDEX IF NOT EXISTS episodes_proposal ON episodes(domain, proposal_sha256);
CREATE TABLE IF NOT EXISTS outbox(
  task_id TEXT PRIMARY KEY, domain TEXT NOT NULL, episode INTEGER NOT NULL, request_id TEXT NOT NULL,
  research_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL, payload_sha256 TEXT NOT NULL, raw BLOB NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('PENDING','PUBLISHED')), dispatches INTEGER NOT NULL DEFAULT 0,
  retries_requested INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS inbox(
  domain TEXT NOT NULL, result_sha256 TEXT NOT NULL, task_id TEXT NOT NULL, episode INTEGER NOT NULL,
  status TEXT NOT NULL, class TEXT NOT NULL, payload_sha256 TEXT, raw BLOB NOT NULL, fact_id TEXT,
  PRIMARY KEY(domain, result_sha256));
CREATE TABLE IF NOT EXISTS rejections(
  domain TEXT NOT NULL, file TEXT NOT NULL, sha256 TEXT NOT NULL, code TEXT NOT NULL, reason TEXT NOT NULL,
  PRIMARY KEY(domain, file, sha256));
"""
FACT_PREDICATES = {"TERMINAL_RESULT": "research.result", "TERMINAL_REFUSAL": "research.refusal",
                   "REQUIRES_HUMAN": "research.requires_human"}
EXTRACTOR = "cain-orchestration-ingest/1"


class OrchestrationStore:
    def __init__(self, state: str | Path):
        self.root = Path(state)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "orchestration.sqlite"
        self.memory = MemoryStore(self.root / "memory.sqlite")
        with self.db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    # ------------------------------------------------------------------ reads
    def next_episode(self, db, domain: str) -> int:
        row = db.execute("SELECT max(number) AS n FROM episodes WHERE domain=?", (domain,)).fetchone()
        return (row["n"] or 0) + 1

    def episode_by_proposal(self, db, domain: str, proposal_sha256: str):
        return db.execute("SELECT * FROM episodes WHERE domain=? AND proposal_sha256=?",
                          (domain, proposal_sha256)).fetchone()

    def last_task_id(self, db, domain: str) -> str | None:
        row = db.execute("SELECT task_id FROM outbox WHERE domain=? ORDER BY episode DESC LIMIT 1", (domain,)).fetchone()
        return row["task_id"] if row else None

    def task(self, domain: str, task_id: str) -> dict | None:
        with self.db() as db:
            row = db.execute("SELECT raw FROM outbox WHERE domain=? AND task_id=?", (domain, task_id)).fetchone()
        return v2.loads_task(bytes(row["raw"])) if row else None

    def memory_head(self) -> str | None:
        with self.memory.connection() as db:
            row = db.execute("SELECT recorded_at FROM memory_events ORDER BY seq DESC LIMIT 1").fetchone()
        return row["recorded_at"] if row else None

    def result_facts(self, domain: str, as_of: str) -> list[dict]:
        head = self.memory_head()
        if head is None:
            return []
        facts = []
        for predicate in FACT_PREDICATES.values():
            facts += self.memory.facts(as_of=head, cubes=[domain], predicate=predicate, valid_at=as_of)
        return facts

    def view(self, db, domain: str, as_of: str) -> dict:
        tasks = [dict(r) for r in db.execute(
            "SELECT task_id, episode, request_id, research_id, hypothesis_id, payload_sha256 FROM outbox "
            "WHERE domain=? ORDER BY episode", (domain,))]
        results = sorted(
            ({k: f["object"][k] for k in ("task_id", "episode", "hypothesis_id", "status", "class", "result_state",
                                          "scientific_state", "economic_state", "payload_sha256")}
             | {"reason_code": f["object"].get("reason_code")}
             for f in self.result_facts(domain, as_of)),
            key=lambda r: (r["episode"], r["task_id"], r["status"]),
        )
        terminal = {r["task_id"] for r in results}
        episodes = db.execute("SELECT count(*) AS n FROM episodes WHERE domain=?", (domain,)).fetchone()["n"]
        return {
            "domain": domain,
            "episodes": episodes,
            "tasks": tasks,
            "results": results,
            "open_task_ids": [t["task_id"] for t in tasks if t["task_id"] not in terminal],
            "requires_human": sorted({r["task_id"] for r in results if r["class"] == "REQUIRES_HUMAN"}),
        }

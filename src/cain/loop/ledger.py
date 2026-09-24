"""Append-only ledger of the research loop: Hypothesis → Experiment → Feedback, including discards,
blocks and crashes, as events chained by sha256 over RFC 8785 JSON (same discipline as the memory log).

``predictor_core`` has no TrialLedger yet; this ledger is CAIN's own, and each loop records the
predictor, the world-file hash and the evaluator hash it ran against, so the events can later be
exported to a core ledger without reinterpretation.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from cain.memory.jcs import canonicalize

GENESIS = "cain-loop-ledger/1"
EVENT_SCHEMA = "cain-loop-event/1"
KINDS = ("loop.started", "hypothesis.registered", "experiment.proposed", "experiment.blocked",
         "experiment.discarded", "experiment.crashed", "experiment.finished", "gate.requested",
         "gate.decided", "holdout.evaluated", "loop.stopped")
ATTEMPT_OUTCOMES = ("experiment.blocked", "experiment.discarded", "experiment.crashed", "experiment.finished")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class LoopLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._ready = False

    @contextmanager
    def connection(self):
        if not self._ready:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                if not self._ready:
                    db.executescript("""
                        CREATE TABLE IF NOT EXISTS loop_events(
                          seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
                          loop_id TEXT NOT NULL, kind TEXT NOT NULL, recorded_at TEXT NOT NULL,
                          body TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
                        CREATE INDEX IF NOT EXISTS loop_events_loop ON loop_events(loop_id, seq);
                        CREATE TRIGGER IF NOT EXISTS loop_events_no_update BEFORE UPDATE ON loop_events
                          BEGIN SELECT RAISE(ABORT, 'loop ledger is append-only'); END;
                        CREATE TRIGGER IF NOT EXISTS loop_events_no_delete BEFORE DELETE ON loop_events
                          BEGIN SELECT RAISE(ABORT, 'loop ledger is append-only'); END;
                    """)
                    self._ready = True
                yield db
        finally:
            db.close()

    def append(self, loop_id: str, kind: str, body: dict) -> dict:
        if kind not in KINDS:
            raise ValueError(f"unknown loop event kind {kind!r}")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            head = db.execute("SELECT entry_hash FROM loop_events ORDER BY seq DESC LIMIT 1").fetchone()
            event = {"schema": EVENT_SCHEMA, "event_id": "loopevent:" + uuid4().hex, "loop_id": loop_id,
                     "kind": kind, "recorded_at": _now(), "body": body,
                     "previous_hash": head["entry_hash"] if head else GENESIS}
            raw = canonicalize(event)
            entry = sha256(raw).hexdigest()
            db.execute("INSERT INTO loop_events(event_id, loop_id, kind, recorded_at, body, previous_hash, entry_hash) "
                       "VALUES (?,?,?,?,?,?,?)", (event["event_id"], loop_id, kind, event["recorded_at"],
                                                 raw.decode("utf-8"), event["previous_hash"], entry))
        return {**event, "entry_hash": entry}

    def events(self, loop_id: str | None = None) -> list[dict]:
        with self.connection() as db:
            if loop_id is None:
                rows = db.execute("SELECT seq, body, entry_hash FROM loop_events ORDER BY seq").fetchall()
            else:
                rows = db.execute("SELECT seq, body, entry_hash FROM loop_events WHERE loop_id=? ORDER BY seq",
                                  (loop_id,)).fetchall()
        return [{**json.loads(r["body"]), "seq": r["seq"], "entry_hash": r["entry_hash"]} for r in rows]

    def loops(self) -> list[str]:
        with self.connection() as db:
            return [r[0] for r in db.execute("SELECT loop_id FROM loop_events WHERE kind='loop.started' ORDER BY seq")]

    def verify(self) -> dict:
        previous = GENESIS
        with self.connection() as db:
            rows = db.execute("SELECT seq, body, previous_hash, entry_hash FROM loop_events ORDER BY seq").fetchall()
        for row in rows:
            event = json.loads(row["body"])
            if (row["previous_hash"] != previous or event.get("previous_hash") != previous
                    or sha256(canonicalize(event)).hexdigest() != row["entry_hash"]):
                return {"status": "broken", "broken_at": row["seq"], "entries": len(rows)}
            previous = row["entry_hash"]
        return {"status": "intact", "broken_at": None, "entries": len(rows), "head": previous}

    def status(self, loop_id: str) -> dict:
        """What the loop did, read back only from its events."""
        events = self.events(loop_id)
        if not events or events[0]["kind"] != "loop.started":
            raise ValueError(f"unknown loop {loop_id!r}")
        outcomes: dict[str, int] = {}
        best = None
        for event in events:
            if event["kind"] in ATTEMPT_OUTCOMES:
                outcomes[event["kind"]] = outcomes.get(event["kind"], 0) + 1
            if event["kind"] == "experiment.finished" and event["body"].get("improved"):
                best = event["body"]
        stopped = next((e["body"] for e in events if e["kind"] == "loop.stopped"), None)
        log: dict[int, dict] = {}
        for event in events:
            body = event["body"]
            if event["kind"] == "experiment.proposed":
                log[body["attempt"]] = {"attempt": body["attempt"], "step_kind": body["step_kind"],
                                        "changes": body["changes"], "params": body["params"], "outcome": None}
            elif event["kind"] in ATTEMPT_OUTCOMES and body.get("attempt") in log:
                log[body["attempt"]].update(outcome=event["kind"].split(".", 1)[1], reason=body.get("reason"),
                                            value=body.get("value"))
        return {"loop_id": loop_id, "started": events[0]["body"], "attempts": sum(outcomes.values()),
                "outcomes": outcomes,
                "hypotheses": [e["body"] for e in events if e["kind"] == "hypothesis.registered"],
                "best": best, "gates": [e["body"] for e in events if e["kind"] == "gate.requested"],
                "finished": [{k: e["body"].get(k) for k in ("attempt", "step_kind", "params", "value", "improved")}
                             for e in events if e["kind"] == "experiment.finished"],
                "attempt_log": list(log.values()), "stopped": stopped, "events": len(events)}

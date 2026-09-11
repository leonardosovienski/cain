"""Durable, bounded read-only research workflows with explicit step execution."""

from datetime import datetime, timezone
import json
from time import perf_counter, time
from uuid import uuid4

from research_snapshot import canonical, digest

from cain.research.analysis import entities, fingerprint, guard, review, search
from cain.research.inspection import inspect
from cain.llm import OllamaLLM, urlopen
from cain.llm.streaming import require_local
from urllib.request import Request

STEPS = ("inspect", "search", "entities", "support", "challenge", "synthesis")
GENERATION = set(STEPS[2:])


def model_identity(provider):
    model_digest = getattr(provider, "model_digest", None)
    if isinstance(provider, OllamaLLM):
        require_local(provider)
        with urlopen(Request(provider.base_url.rstrip("/") + "/api/tags"), timeout=5) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Model inventory exceeds limit")
        available = json.loads(raw)
        found = next((m for m in available.get("models", []) if m.get("name") == provider.model), None)
        if not found or not found.get("digest"):
            raise ValueError("Configured workflow model is not installed")
        model_digest = found["digest"]
    return {"provider": type(provider).__name__, "model_digest": model_digest,
            **{k: getattr(provider, k, None) for k in
            ("model", "base_url", "temperature", "seed", "num_ctx", "num_predict", "think", "timeout", "max_input_bytes")}}


class Workflows:
    def __init__(self, service):
        self.service = service
        with service.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS agent_jobs(
                  scope TEXT NOT NULL,id TEXT NOT NULL,request TEXT NOT NULL,
                  fingerprint TEXT NOT NULL,status TEXT NOT NULL,claim TEXT,
                  claimed_at REAL,created_at TEXT NOT NULL,
                  PRIMARY KEY(scope,id));
                CREATE TABLE IF NOT EXISTS agent_steps(
                  scope TEXT NOT NULL,job TEXT NOT NULL,position INTEGER NOT NULL,
                  name TEXT NOT NULL,result TEXT NOT NULL,duration REAL NOT NULL,
                  PRIMARY KEY(scope,job,position));
                CREATE TABLE IF NOT EXISTS agent_attempts(
                  id TEXT PRIMARY KEY,scope TEXT NOT NULL,job TEXT NOT NULL,
                  name TEXT NOT NULL,status TEXT NOT NULL,error TEXT,duration REAL NOT NULL,
                  started_at REAL);
            """)
            if "started_at" not in {row[1] for row in db.execute("PRAGMA table_info(agent_attempts)")}:
                db.execute("ALTER TABLE agent_attempts ADD COLUMN started_at REAL")

    def create(self, scope, question, provider, *, source_id=None, steps=STEPS, run_id=None):
        if type(question) is not str or not question.strip() or len(question) > 500:
            raise ValueError("Workflow question requires 1-500 characters")
        if source_id is not None and (type(source_id) is not str or not source_id or len(source_id) > 200):
            raise ValueError("Invalid source identity")
        if (not isinstance(steps, (list, tuple)) or not 1 <= len(steps) <= 6
                or any(type(s) is not str or s not in STEPS for s in steps)
                or len(set(steps)) != len(steps)):
            raise ValueError("Select 1-6 distinct registered steps")
        run_id = run_id or uuid4().hex
        if type(run_id) is not str or not run_id or len(run_id) > 100:
            raise ValueError("Invalid workflow identity")
        request = canonical({"question": question, "source_id": source_id, "steps": list(steps),
                             "model": model_identity(provider), "protocol": "research-workflow/1"}).decode()
        snapshot = fingerprint(self.service, scope)
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT request,fingerprint FROM agent_jobs WHERE scope=? AND id=?",
                                  (scope, run_id)).fetchone()
            if previous:
                if previous["request"] != request or previous["fingerprint"] != snapshot:
                    raise ValueError("Workflow identity already bound to another request or corpus")
            else:
                db.execute("INSERT INTO agent_jobs VALUES(?,?,?,?,?,NULL,NULL,?)",
                           (scope, run_id, request, snapshot, "ready", datetime.now(timezone.utc).isoformat()))
        return self.get(scope, run_id)

    def get(self, scope, run_id):
        with self.service.connection() as db:
            row = db.execute("SELECT * FROM agent_jobs WHERE scope=? AND id=?", (scope, run_id)).fetchone()
            if row is None:
                raise ValueError("Workflow unavailable in this scope")
            guard(self.service, scope, row["fingerprint"])
            steps = [{"position": r["position"], "name": r["name"], "duration_seconds": r["duration"],
                      "result": json.loads(r["result"])} for r in db.execute(
                "SELECT * FROM agent_steps WHERE scope=? AND job=? ORDER BY position", (scope, run_id))]
            attempts = [dict(r) for r in db.execute(
                "SELECT id,name,status,error,duration,started_at FROM agent_attempts WHERE scope=? AND job=? ORDER BY rowid",
                (scope, run_id))]
        guard(self.service, scope, row["fingerprint"])
        request = json.loads(row["request"])
        return {"id": run_id, "status": row["status"], "request": request, "steps": steps, "attempts": attempts,
                "next_step": request["steps"][len(steps)] if len(steps) < len(request["steps"]) else None,
                "created_at": row["created_at"], "snapshot": row["fingerprint"],
                "proposals_only": True, "model_calls": sum(
                    s["result"].get("model_calls", int(s["result"].get("generation", {}).get("called", False)))
                    for s in steps)}

    def list(self, scope):
        snapshot = fingerprint(self.service, scope)
        with self.service.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,status,created_at FROM agent_jobs WHERE scope=? AND fingerprint=? "
                "ORDER BY created_at DESC LIMIT 50", (scope, snapshot))]

    def cancel(self, scope, run_id):
        self.get(scope, run_id)
        with self.service.connection() as db:
            db.execute("UPDATE agent_jobs SET status='cancelled',claim=NULL WHERE scope=? AND id=? AND status!='completed'",
                       (scope, run_id))
        return self.get(scope, run_id)

    def trace(self, scope, run_id):
        job = self.get(scope, run_id)
        trace_id = digest(canonical([scope, run_id]))[:32]
        spans = []
        for attempt in job["attempts"]:
            if attempt["started_at"] is None:
                continue
            start = int(attempt["started_at"] * 1_000_000_000)
            spans.append({"traceId": trace_id, "spanId": attempt["id"][:16], "name": attempt["name"],
                          "startTimeUnixNano": str(start),
                          "endTimeUnixNano": str(start + int(attempt["duration"] * 1_000_000_000)),
                          "status": {"code": 1 if attempt["status"] == "completed" else 2},
                          "attributes": [{"key": "cain.status", "value": {"stringValue": attempt["status"]}},
                                         {"key": "cain.error_type", "value": {"stringValue": attempt["error"] or ""}}]})
        return {"resourceSpans": [{"resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "cain-local"}}]},
            "scopeSpans": [{"scope": {"name": "cain.research.workflows", "version": "1"}, "spans": spans}]}]}

    def advance(self, scope, run_id, provider, *, approve_generation=False, recover=False):
        current = self.get(scope, run_id)
        request = current["request"]
        if current["status"] in {"completed", "cancelled"}:
            return current
        if request["model"] != model_identity(provider):
            raise ValueError("Configured model changed; start a new workflow")
        name = current["next_step"]
        if name in GENERATION and approve_generation is not True:
            return {**current, "status": "awaiting_generation_approval"}
        claim = uuid4().hex
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status,claimed_at FROM agent_jobs WHERE scope=? AND id=?",
                             (scope, run_id)).fetchone()
            if row["status"] == "running" and (not recover or time() - row["claimed_at"] < 600):
                raise ValueError("Step is running; recovery requires an expired 600-second lease")
            if row["status"] == "failed" and not recover:
                raise ValueError("Previous step failed; explicitly recover to retry it")
            # A concurrent step may have completed after get(). Re-read the position.
            count = db.execute("SELECT count(*) FROM agent_steps WHERE scope=? AND job=?",
                               (scope, run_id)).fetchone()[0]
            if count != len(current["steps"]) or row["status"] in {"completed", "cancelled"}:
                raise ValueError("Workflow changed concurrently; refresh")
            db.execute("UPDATE agent_jobs SET status='running',claim=?,claimed_at=? WHERE scope=? AND id=?",
                       (claim, time(), scope, run_id))
        started, started_at = perf_counter(), time()
        try:
            guard(self.service, scope, current["snapshot"])
            source = request["source_id"]
            if name == "inspect":
                result = inspect(self.service, scope, source_id=source)
            elif name == "search":
                result = search(self.service, scope, request["question"], source_id=source)
            elif name == "entities":
                result = entities(self.service, scope, request["question"], provider, source_id=source)
            else:
                previous = [s["result"].get("explanation", {}).get("proposed_synthesis", "")
                            for s in current["steps"] if s["name"] in GENERATION
                            and s["result"].get("explanation")]
                result = review(self.service, scope, request["question"], provider, role=name,
                                source_id=source, previous=previous)
                if result.get("status") == "generation_failed":
                    raise ValueError("Review failed: " + result.get("error_code", "UNKNOWN"))
            guard(self.service, scope, current["snapshot"])
            if model_identity(provider) != request["model"]:
                raise ValueError("Model identity changed during execution; result discarded")
            encoded = canonical(result).decode()
            if len(encoded.encode()) > 1_000_000:
                raise ValueError("Step result exceeds 1000000 bytes")
            with self.service.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT claim,status FROM agent_jobs WHERE scope=? AND id=?",
                                 (scope, run_id)).fetchone()
                if row["claim"] != claim or row["status"] != "running":
                    raise ValueError("Step cancelled or lease replaced; result discarded")
                db.execute("INSERT INTO agent_steps VALUES(?,?,?,?,?,?)",
                           (scope, run_id, len(current["steps"]), name, encoded, perf_counter() - started))
                db.execute("INSERT INTO agent_attempts VALUES(?,?,?,?,?,?,?,?)",
                           (claim, scope, run_id, name, "completed", None, perf_counter() - started, started_at))
                status = "completed" if len(current["steps"]) + 1 == len(request["steps"]) else "ready"
                db.execute("UPDATE agent_jobs SET status=?,claim=NULL WHERE scope=? AND id=?", (status, scope, run_id))
        except Exception as exc:
            with self.service.connection() as db:
                db.execute("UPDATE agent_jobs SET status='failed',claim=NULL WHERE scope=? AND id=? AND claim=?",
                           (scope, run_id, claim))
                db.execute("INSERT OR IGNORE INTO agent_attempts VALUES(?,?,?,?,?,?,?,?)",
                           (claim, scope, run_id, name, "failed", type(exc).__name__, perf_counter() - started, started_at))
            raise
        return self.get(scope, run_id)

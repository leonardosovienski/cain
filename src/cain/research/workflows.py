"""Durable, bounded read-only research workflows with explicit step execution.

Human governance is a primitive of the engine:

* a generation step never runs without a recorded human decision for that step. Without one,
  ``advance`` records an ``approval.requested`` event and parks the run durably in
  ``awaiting_generation_approval`` (it survives process death and machine restarts);
* ``decide`` records ``approval.decided`` (APPROVE / REJECT / EDIT, who, when, what changed) as an
  immutable event in ``workflow_events`` (append-only, RFC 8785 JSON chained by sha256). REJECT is
  terminal and nothing after it runs; EDIT changes the step's question and records the diff;
* ``fork`` creates a child run (``parent_run_id``, ``fork_point``) that reuses the parent's steps
  before the fork point by reference and executes only from there, optionally with another model.

Side effects happen only after the decision: a model call and the persisted step result both come
after the approval check. Idempotency: ``inspect`` and ``search`` are deterministic reads of a
fingerprinted corpus; generation steps are not (a local model may answer differently), but a step
result is persisted at most once per position (lease + claim), so a crash before persistence can
repeat the model call, never a stored result.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from time import perf_counter, time
from uuid import uuid4

from research_snapshot import canonical, digest

from cain.memory.jcs import canonicalize
from cain.research.analysis import entities, fingerprint, guard, review, search
from cain.research.inspection import inspect
from cain.llm import OllamaLLM, urlopen
from cain.llm.streaming import require_local
from urllib.request import Request

STEPS = ("inspect", "search", "entities", "support", "challenge", "synthesis")
GENERATION = set(STEPS[2:])
PROTOCOL = "research-workflow/19"
EVENT_SCHEMA = "cain-workflow-event/1"
EVENT_GENESIS = "cain-workflow-events/1"
DECISIONS = ("APPROVE", "REJECT", "EDIT")
TERMINAL = {"completed", "cancelled", "rejected"}
_ACTOR = re.compile(r"[^\x00-\x1f\x7f]{1,100}\Z")


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


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _scope_user(scope):
    try:
        return json.loads(scope)[0]
    except (ValueError, TypeError, IndexError):
        return "unknown"


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
                CREATE TABLE IF NOT EXISTS workflow_events(
                  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
                  scope TEXT NOT NULL, run_id TEXT NOT NULL, kind TEXT NOT NULL, recorded_at TEXT NOT NULL,
                  body TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS workflow_events_run ON workflow_events(scope, run_id, seq);
                CREATE TRIGGER IF NOT EXISTS workflow_events_no_update BEFORE UPDATE ON workflow_events
                BEGIN SELECT RAISE(ABORT, 'workflow events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS workflow_events_no_delete BEFORE DELETE ON workflow_events
                BEGIN SELECT RAISE(ABORT, 'workflow events are append-only'); END;
            """)
            if "started_at" not in {row[1] for row in db.execute("PRAGMA table_info(agent_attempts)")}:
                db.execute("ALTER TABLE agent_attempts ADD COLUMN started_at REAL")
            job_columns = {row[1] for row in db.execute("PRAGMA table_info(agent_jobs)")}
            if "parent_run_id" not in job_columns:
                db.execute("ALTER TABLE agent_jobs ADD COLUMN parent_run_id TEXT")
                db.execute("ALTER TABLE agent_jobs ADD COLUMN fork_point INTEGER")
            if "inherited_from" not in {row[1] for row in db.execute("PRAGMA table_info(agent_steps)")}:
                db.execute("ALTER TABLE agent_steps ADD COLUMN inherited_from TEXT")

    # ------------------------------------------------------------------ event log
    @staticmethod
    def _event(db, scope, run_id, kind, body):
        last = db.execute("SELECT entry_hash FROM workflow_events ORDER BY seq DESC LIMIT 1").fetchone()
        event = {"schema": EVENT_SCHEMA, "event_id": "wfevent:" + uuid4().hex, "scope": scope, "run_id": run_id,
                 "kind": kind, "recorded_at": _now(), "previous_hash": last[0] if last else EVENT_GENESIS,
                 "body": body}
        raw = canonicalize(event).decode("utf-8")
        db.execute("INSERT INTO workflow_events(event_id,scope,run_id,kind,recorded_at,body,previous_hash,entry_hash) "
                   "VALUES(?,?,?,?,?,?,?,?)", (event["event_id"], scope, run_id, kind, event["recorded_at"], raw,
                                                event["previous_hash"], sha256(raw.encode("utf-8")).hexdigest()))
        return event

    def events(self, scope, run_id):
        with self.service.connection() as db:
            return [json.loads(r["body"]) for r in db.execute(
                "SELECT body FROM workflow_events WHERE scope=? AND run_id=? ORDER BY seq", (scope, run_id))]

    def verify_events(self):
        """Recompute the whole workflow event chain; report the first link that does not fit."""
        expected, entries = EVENT_GENESIS, 0
        with self.service.connection() as db:
            for row in db.execute("SELECT * FROM workflow_events ORDER BY seq"):
                entries += 1
                try:
                    event = json.loads(row["body"])
                    ok = (canonicalize(event).decode("utf-8") == row["body"] and event["previous_hash"] == expected
                          == row["previous_hash"] and sha256(row["body"].encode()).hexdigest() == row["entry_hash"])
                except (ValueError, KeyError, TypeError):
                    ok = False
                if not ok:
                    return {"entries": entries, "status": "broken", "broken_at": row["seq"]}
                expected = row["entry_hash"]
        return {"entries": entries, "status": "intact", "broken_at": None, "head": expected}

    @staticmethod
    def _approval(db, scope, run_id, position):
        requested = decided = None
        for row in db.execute("SELECT kind, body FROM workflow_events WHERE scope=? AND run_id=? AND kind LIKE "
                              "'approval.%' ORDER BY seq", (scope, run_id)):
            event = json.loads(row["body"])
            if event["body"]["position"] != position:
                continue
            if row["kind"] == "approval.requested" and requested is None:
                requested = event
            elif row["kind"] == "approval.decided" and decided is None:
                decided = event
        return requested, decided

    # ------------------------------------------------------------------ lifecycle
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
                             "model": model_identity(provider), "protocol": PROTOCOL}).decode()
        snapshot = fingerprint(self.service, scope)
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT request,fingerprint FROM agent_jobs WHERE scope=? AND id=?",
                                  (scope, run_id)).fetchone()
            if previous:
                if previous["request"] != request or previous["fingerprint"] != snapshot:
                    raise ValueError("Workflow identity already bound to another request or corpus")
            else:
                db.execute("INSERT INTO agent_jobs(scope,id,request,fingerprint,status,claim,claimed_at,created_at) "
                           "VALUES(?,?,?,?,?,NULL,NULL,?)",
                           (scope, run_id, request, snapshot, "ready", datetime.now(timezone.utc).isoformat()))
        return self.get(scope, run_id)

    def get(self, scope, run_id):
        with self.service.connection() as db:
            row = db.execute("SELECT * FROM agent_jobs WHERE scope=? AND id=?", (scope, run_id)).fetchone()
            if row is None:
                raise ValueError("Workflow unavailable in this scope")
            guard(self.service, scope, row["fingerprint"])
            steps = [{"position": r["position"], "name": r["name"], "duration_seconds": r["duration"],
                      "result": json.loads(r["result"]), "inherited_from": r["inherited_from"]} for r in db.execute(
                "SELECT * FROM agent_steps WHERE scope=? AND job=? ORDER BY position", (scope, run_id))]
            attempts = [dict(r) for r in db.execute(
                "SELECT id,name,status,error,duration,started_at FROM agent_attempts WHERE scope=? AND job=? ORDER BY rowid",
                (scope, run_id))]
            request_row = json.loads(row["request"])
            pending = None
            if len(steps) < len(request_row["steps"]):
                requested, decided = self._approval(db, scope, run_id, len(steps))
                if requested is not None and decided is None:
                    pending = {"event_id": requested["event_id"], "requested_at": requested["recorded_at"],
                               **requested["body"]}
        guard(self.service, scope, row["fingerprint"])
        request = request_row
        approvals = [e for e in self.events(scope, run_id) if e["kind"].startswith("approval.")]
        return {"id": run_id, "status": row["status"], "request": request, "steps": steps, "attempts": attempts,
                "next_step": request["steps"][len(steps)] if len(steps) < len(request["steps"]) else None,
                "created_at": row["created_at"], "snapshot": row["fingerprint"],
                "parent_run_id": row["parent_run_id"], "fork_point": row["fork_point"],
                "pending_approval": pending, "approvals": approvals,
                "model_call_count_scope": "completed_step_receipts_only",
                "failed_generation_attempts": sum(a["status"] == "failed" and a["name"] in GENERATION for a in attempts),
                "failed_attempt_model_calls": "unknown; failures can occur before or after inference",
                "proposals_only": True, "model_calls": sum(
                    s["result"].get("model_calls", int(s["result"].get("generation", {}).get("called", False)))
                    for s in steps if s["inherited_from"] is None)}

    def list(self, scope):
        snapshot = fingerprint(self.service, scope)
        with self.service.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,status,created_at,parent_run_id,fork_point FROM agent_jobs WHERE scope=? AND fingerprint=? "
                "ORDER BY created_at DESC LIMIT 50", (scope, snapshot))]

    def cancel(self, scope, run_id):
        self.get(scope, run_id)
        with self.service.connection() as db:
            db.execute("UPDATE agent_jobs SET status='cancelled',claim=NULL WHERE scope=? AND id=? "
                       "AND status NOT IN ('completed','rejected')", (scope, run_id))
        return self.get(scope, run_id)

    def abstain(self, scope, run_id, reason):
        """Explicit operator checkpoint after a failed generation, never accepted output."""
        if type(reason) is not str or not reason.strip() or len(reason) > 500:
            raise ValueError("Record an abstention reason of 1-500 characters")
        current = self.get(scope, run_id)
        if current["request"]["protocol"] != PROTOCOL:
            raise ValueError("Workflow prompt protocol changed; create a new workflow")
        if current["status"] != "failed" or current["next_step"] not in GENERATION:
            raise ValueError("Only a failed generation can be explicitly recorded as abstention")
        guard(self.service, scope, current["snapshot"])
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM agent_jobs WHERE scope=? AND id=?", (scope, run_id)).fetchone()
            count = db.execute("SELECT count(*) FROM agent_steps WHERE scope=? AND job=?", (scope, run_id)).fetchone()[0]
            if row["status"] != "failed" or count != len(current["steps"]):
                raise ValueError("Workflow changed concurrently; refresh")
            result = {"status": "abstained_by_operator", "reason": reason, "model_calls": 0,
                      "accepted_model_output": False, "previous_failure_retained": True}
            db.execute("INSERT INTO agent_steps(scope,job,position,name,result,duration) VALUES(?,?,?,?,?,?)",
                       (scope, run_id, count, current["next_step"], canonical(result).decode(), 0))
            status = "completed" if count + 1 == len(current["request"]["steps"]) else "ready"
            db.execute("UPDATE agent_jobs SET status=?,claim=NULL WHERE scope=? AND id=?", (status, scope, run_id))
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

    # ------------------------------------------------------------------ human governance
    def _proposal(self, current):
        request = current["request"]
        previous = [s["result"].get("explanation", {}).get("proposed_synthesis", "")
                    for s in current["steps"] if s["name"] in GENERATION and s["result"].get("explanation")]
        # The references the search step found (its "evidence" list); what the approver is shown.
        evidence = sorted({e.get("reference_id") for s in current["steps"] if s["name"] == "search"
                           for e in s["result"].get("evidence", []) if isinstance(e, dict) and e.get("reference_id")})
        return {"position": len(current["steps"]), "step": current["next_step"],
                "proposal": {"question": request["question"], "source_id": request["source_id"],
                             "model": request["model"].get("model"), "model_digest": request["model"].get("model_digest"),
                             "previous_proposals": len(previous)},
                "evidence_ids": evidence, "diff": None}

    def decide(self, scope, run_id, decision, *, by, note=None, question=None):
        """Record a human decision on the pending step as an immutable event."""
        if decision not in DECISIONS:
            raise ValueError(f"Decision must be one of {DECISIONS}")
        if type(by) is not str or not _ACTOR.match(by):
            raise ValueError("Record who decides (1-100 printable characters)")
        if note is not None and (type(note) is not str or len(note) > 1000):
            raise ValueError("Note must have at most 1000 characters")
        current = self.get(scope, run_id)
        if decision == "EDIT":
            if type(question) is not str or not question.strip() or len(question) > 500:
                raise ValueError("EDIT requires the edited question (1-500 characters)")
            if question == current["request"]["question"]:
                raise ValueError("EDIT must change the proposal")
        elif question is not None:
            raise ValueError("Only EDIT carries an edited question")
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM agent_jobs WHERE scope=? AND id=?", (scope, run_id)).fetchone()
            count = db.execute("SELECT count(*) FROM agent_steps WHERE scope=? AND job=?", (scope, run_id)).fetchone()[0]
            requested, decided = self._approval(db, scope, run_id, count)
            if requested is None or decided is not None or row["status"] != "awaiting_generation_approval":
                raise ValueError("No pending approval for this workflow step")
            body = {"position": count, "step": requested["body"]["step"], "decision": decision, "by": by,
                    "note": note, "request_event_id": requested["event_id"],
                    "edit": {"question": question} if decision == "EDIT" else None,
                    "diff": {"question": [current["request"]["question"], question]} if decision == "EDIT" else None}
            self._event(db, scope, run_id, "approval.decided", body)
            db.execute("UPDATE agent_jobs SET status=? WHERE scope=? AND id=?",
                       ("rejected" if decision == "REJECT" else "ready", scope, run_id))
        return self.get(scope, run_id)

    def fork(self, scope, run_id, from_step, provider, *, prompt_version=None, new_run_id=None):
        """Child run reusing the parent's steps before ``from_step`` and executing only from there."""
        parent = self.get(scope, run_id)
        if type(from_step) is not int or not 0 <= from_step <= len(parent["steps"]):
            raise ValueError(f"fork point must be 0-{len(parent['steps'])} (completed steps of the parent)")
        if prompt_version not in (None, PROTOCOL):
            raise ValueError(f"Only the installed prompt protocol {PROTOCOL} can run; got {prompt_version}")
        if parent["request"]["protocol"] != PROTOCOL:
            raise ValueError("Parent used another prompt protocol; its steps cannot be reused")
        snapshot = fingerprint(self.service, scope)
        if snapshot != parent["snapshot"]:
            raise ValueError("Corpus changed since the parent run; steps cannot be reused")
        request = {**parent["request"], "model": model_identity(provider)}
        child = new_run_id or uuid4().hex
        if type(child) is not str or not child or len(child) > 100:
            raise ValueError("Invalid workflow identity")
        status = "completed" if from_step == len(request["steps"]) else "ready"
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM agent_jobs WHERE scope=? AND id=?", (scope, child)).fetchone():
                raise ValueError("Workflow identity already exists")
            db.execute("INSERT INTO agent_jobs(scope,id,request,fingerprint,status,claim,claimed_at,created_at,"
                       "parent_run_id,fork_point) VALUES(?,?,?,?,?,NULL,NULL,?,?,?)",
                       (scope, child, canonical(request).decode(), snapshot, status,
                        datetime.now(timezone.utc).isoformat(), run_id, from_step))
            for step in parent["steps"][:from_step]:
                db.execute("INSERT INTO agent_steps(scope,job,position,name,result,duration,inherited_from) "
                           "VALUES(?,?,?,?,?,?,?)", (scope, child, step["position"], step["name"],
                                                     canonical(step["result"]).decode(), step["duration_seconds"],
                                                     f"{run_id}:{step['position']}"))
            self._event(db, scope, child, "run.forked", {
                "parent_run_id": run_id, "child_run_id": child, "fork_point": from_step,
                "inherited_positions": list(range(from_step)),
                "parent_model": parent["request"]["model"].get("model"), "child_model": request["model"].get("model"),
                "prompt_protocol": PROTOCOL})
        return self.get(scope, child)

    # ------------------------------------------------------------------ execution
    def advance(self, scope, run_id, provider, *, approve_generation=False, recover=False):
        current = self.get(scope, run_id)
        request = current["request"]
        if current["status"] in TERMINAL:
            return current
        if request["protocol"] != PROTOCOL:
            raise ValueError("Workflow prompt protocol changed; create a new workflow")
        if request["model"] != model_identity(provider):
            raise ValueError("Configured model changed; start a new workflow")
        name = current["next_step"]
        position = len(current["steps"])
        edit = {}
        approval_ref = None
        if name in GENERATION:
            with self.service.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                requested, decided = self._approval(db, scope, run_id, position)
                if decided is None:
                    if requested is None:
                        requested = self._event(db, scope, run_id, "approval.requested", self._proposal(current))
                    if approve_generation is True:
                        # Explicit per-call approval (CLI flag / API field) is attributed to the scope's user.
                        decided = self._event(db, scope, run_id, "approval.decided", {
                            "position": position, "step": name, "decision": "APPROVE", "by": _scope_user(scope),
                            "note": "explicit approve_generation on advance", "request_event_id": requested["event_id"],
                            "edit": None, "diff": None})
                    else:
                        db.execute("UPDATE agent_jobs SET status='awaiting_generation_approval' "
                                   "WHERE scope=? AND id=? AND status='ready'", (scope, run_id))
            if decided is None:
                return {**self.get(scope, run_id), "status": "awaiting_generation_approval"}
            if decided["body"]["decision"] == "REJECT":
                return self.get(scope, run_id)
            edit = decided["body"]["edit"] or {}
            approval_ref = {"event_id": decided["event_id"], "decision": decided["body"]["decision"],
                            "by": decided["body"]["by"]}
        question = edit.get("question", request["question"])
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
            if count != position or row["status"] in TERMINAL:
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
                result = search(self.service, scope, question, source_id=source)
            elif name == "entities":
                result = entities(self.service, scope, question, provider, source_id=source)
            else:
                previous = [s["result"].get("explanation", {}).get("proposed_synthesis", "")
                            for s in current["steps"] if s["name"] in GENERATION
                            and s["result"].get("explanation")]
                result = review(self.service, scope, question, provider, role=name,
                                source_id=source, previous=previous)
                if result.get("status") == "generation_failed":
                    raise ValueError("Review failed: " + result.get("error_code", "UNKNOWN"))
            guard(self.service, scope, current["snapshot"])
            if model_identity(provider) != request["model"]:
                raise ValueError("Model identity changed during execution; result discarded")
            if approval_ref is not None:
                result = {**result, "human_approval": approval_ref,
                          **({"edited_question": question} if edit else {})}
            encoded = canonical(result).decode()
            if len(encoded.encode()) > 1_000_000:
                raise ValueError("Step result exceeds 1000000 bytes")
            with self.service.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT claim,status FROM agent_jobs WHERE scope=? AND id=?",
                                 (scope, run_id)).fetchone()
                if row["claim"] != claim or row["status"] != "running":
                    raise ValueError("Step cancelled or lease replaced; result discarded")
                db.execute("INSERT INTO agent_steps(scope,job,position,name,result,duration) VALUES(?,?,?,?,?,?)",
                           (scope, run_id, position, name, encoded, perf_counter() - started))
                db.execute("INSERT INTO agent_attempts VALUES(?,?,?,?,?,?,?,?)",
                           (claim, scope, run_id, name, "completed", None, perf_counter() - started, started_at))
                status = "completed" if position + 1 == len(request["steps"]) else "ready"
                db.execute("UPDATE agent_jobs SET status=?,claim=NULL WHERE scope=? AND id=?", (status, scope, run_id))
        except Exception as exc:
            with self.service.connection() as db:
                db.execute("UPDATE agent_jobs SET status='failed',claim=NULL WHERE scope=? AND id=? AND claim=?",
                           (scope, run_id, claim))
                db.execute("INSERT OR IGNORE INTO agent_attempts VALUES(?,?,?,?,?,?,?,?)",
                           (claim, scope, run_id, name, "failed", type(exc).__name__, perf_counter() - started, started_at))
            raise
        return self.get(scope, run_id)

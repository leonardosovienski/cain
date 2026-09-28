"""Orchestrator of one domain: propose (DecisionPolicy + receipt), dispatch, retry, ingest.

Each command is one process and one transaction per step, so a crash leaves either nothing or a consistent record
(FAILURE_MATRIX F01–F05). Commands are idempotent: the same proposal returns its recorded episode and receipt, the
same task bytes are published once, the same result bytes are ingested once, and a memory fact is written once per
(task, outcome class, payload).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from research_protocol import v2
from research_transport.spool import Spool

from cain.orchestration import config as domain_config
from cain.orchestration import policy
from cain.orchestration.faults import fault
from cain.orchestration.store import EXTRACTOR, FACT_PREDICATES, OrchestrationStore


class OrchestrationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


_REASON_CODE = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")


def _payload(body: dict) -> dict:
    """The domain's result payload (canonical JSON text in the V2 result), or {} when there is none."""
    try:
        payload = json.loads(body.get("payload_canonical") or "{}")
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def reason_code(outcome: dict) -> str | None:
    """The domain's refusal reason when it is a closed code (``HYPOTHESIS_NOT_ADMITTED``); free text never passes."""
    reason = outcome.get("reason")
    return reason if isinstance(reason, str) and _REASON_CODE.fullmatch(reason) else None


class Orchestrator:
    def __init__(self, domain: str, state: str | Path):
        self.config = domain_config.load(domain)
        self.config_sha256 = domain_config.digest(self.config)
        self.domain = domain
        self.store = OrchestrationStore(state)

    # ------------------------------------------------------------------ decisions
    def _decide(self, db, proposal, as_of: str) -> tuple[dict, dict | None, int]:
        number = self.store.next_episode(db, self.domain)
        view = self.store.view(db, self.domain, as_of)
        outcome = policy.decide(proposal, view, self.config, episode_number=number)
        task = None
        if outcome["decision"] == "ALLOW":
            task = v2.build_task(self.domain, proposal["request"], episode_id=v2.episode_id_for(self.domain, number),
                                 proposal_id=proposal["proposal_id"], created_at=as_of,
                                 based_on=proposal.get("based_on", []),
                                 previous_task_id=self.store.last_task_id(db, self.domain))
        rec = policy.receipt(proposal, view, self.config, self.config_sha256, outcome, episode_number=number,
                             as_of=as_of, task=task)
        return rec, task, number

    def _existing(self, db, proposal) -> dict | None:
        digest = policy.safe_digest(proposal)
        row = self.store.episode_by_proposal(db, self.domain, digest)
        if row is not None:
            return {"status": "EXISTING", "episode": row["number"], "receipt": v2.loads_strict(bytes(row["receipt"])),
                    "receipt_sha256": row["receipt_sha256"]}
        if isinstance(proposal, dict) and isinstance(proposal.get("proposal_id"), str):
            other = db.execute("SELECT number FROM episodes WHERE domain=? AND proposal_id=?",
                               (self.domain, proposal["proposal_id"])).fetchone()
            if other is not None:
                raise OrchestrationError("PROPOSAL_ID_CONFLICT",
                                         f"{proposal['proposal_id']} already recorded with other content")
        return None

    def decision_receipt(self, proposal, *, as_of: str) -> dict:
        """Read-only: the receipt the policy gives now, without recording anything (N+1, C9)."""
        with self.store.db() as db:
            existing = self._existing(db, proposal)
            if existing is not None:
                return existing
            rec, _task, number = self._decide(db, proposal, as_of)
        raw = policy.dumps(rec)
        return {"status": "COMPUTED", "episode": number, "receipt": rec, "receipt_sha256": sha256(raw)}

    def propose(self, proposal, *, as_of: str, source: str = "operator") -> dict:
        with self.store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = self._existing(db, proposal)
            if existing is not None:
                return existing
            rec, task, number = self._decide(db, proposal, as_of)
            raw = policy.dumps(rec)
            fault("after_decision_before_episode_commit")
            db.execute("INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (self.domain, number, rec["proposal"]["proposal_id"], rec["proposal"]["sha256"],
                        rec["decision"], rec["reason_code"], raw, sha256(raw),
                        task["task_id"] if task else None, as_of, source))
            if task is not None:
                db.execute("INSERT INTO outbox(task_id,domain,episode,request_id,research_id,hypothesis_id,"
                           "payload_sha256,raw,status) VALUES(?,?,?,?,?,?,?,?,'PENDING')",
                           (task["task_id"], self.domain, number, task["request_id"], task["research_id"],
                            task["hypothesis_id"], task["payload_sha256"], v2.dumps_task(task)))
        fault("after_outbox_commit")
        return {"status": "RECORDED", "episode": number, "receipt": rec, "receipt_sha256": sha256(raw)}

    # ------------------------------------------------------------------ transport
    def dispatch(self, spool: Spool, *, resend: bool = False) -> list[dict]:
        where = "status IN ('PENDING','PUBLISHED')" if resend else "status='PENDING'"
        with self.store.db() as db:
            rows = db.execute(f"SELECT task_id, raw FROM outbox WHERE domain=? AND {where} ORDER BY episode",
                              (self.domain,)).fetchall()
        report = []
        for row in rows:
            written = spool.put_task(self.domain, bytes(row["raw"]))
            fault("after_spool_write_before_ack")
            with self.store.db() as db:
                db.execute("UPDATE outbox SET status='PUBLISHED', dispatches=dispatches+1 WHERE task_id=?",
                           (row["task_id"],))
            report.append({"task_id": row["task_id"], "action": "dispatched", "spool": written["status"],
                           "file": written["file"]})
        return report

    def retry(self, spool: Spool, task_id: str) -> dict:
        with self.store.db() as db:
            task = db.execute("SELECT retries_requested FROM outbox WHERE domain=? AND task_id=?",
                              (self.domain, task_id)).fetchone()
            classes = {r["class"] for r in db.execute("SELECT class FROM inbox WHERE domain=? AND task_id=?",
                                                        (self.domain, task_id))}
        if task is None:
            raise OrchestrationError("TASK_NOT_FOUND", task_id)
        if classes != {"RETRYABLE"}:
            raise OrchestrationError("NOT_RETRYABLE", f"{task_id} has outcome classes {sorted(classes)}")
        attempt = task["retries_requested"] + 1
        written = spool.request_retry(self.domain, task_id, attempt)
        with self.store.db() as db:
            db.execute("UPDATE outbox SET retries_requested=? WHERE task_id=?", (attempt, task_id))
        return {"task_id": task_id, "action": "retry_requested", "attempt": attempt, "file": written["file"]}

    # ------------------------------------------------------------------ ingestion (CAIN_INGESTION)
    def _reject(self, path: Path, raw: bytes, code: str, reason: str) -> dict:
        with self.store.db() as db:
            db.execute("INSERT OR IGNORE INTO rejections VALUES(?,?,?,?,?)",
                       (self.domain, path.name, sha256(raw), code, reason[:300]))
        return {"file": path.name, "action": "rejected", "code": code, "reason": reason[:300]}

    def ingest(self, spool: Spool) -> list[dict]:
        report = []
        for path in spool.result_files(self.domain):
            raw = path.read_bytes() if path.stat().st_size <= v2.MAX_RESULT_BYTES else b""
            digest = sha256(raw)
            with self.store.db() as db:
                known = db.execute("SELECT fact_id, class FROM inbox WHERE domain=? AND result_sha256=?",
                                   (self.domain, digest)).fetchone()
                rejected = db.execute("SELECT code FROM rejections WHERE domain=? AND file=? AND sha256=?",
                                      (self.domain, path.name, digest)).fetchone()
            if rejected is not None:
                report.append({"file": path.name, "action": "skipped", "state": "REJECTED", "code": rejected["code"]})
                continue
            if known is not None:
                if known["fact_id"] is None and known["class"] in FACT_PREDICATES:
                    report.append(self._complete_memory(digest) | {"file": path.name})
                else:
                    report.append({"file": path.name, "action": "duplicate"})
                continue
            report.append(self._ingest_one(path, raw, digest))
        return report

    def _ingest_one(self, path: Path, raw: bytes, digest: str) -> dict:
        if not raw:
            return self._reject(path, raw, "SIZE_LIMIT", "empty or larger than MAX_RESULT_BYTES")
        try:
            loose = v2.loads_result(raw)
        except v2.V2Error as exc:
            return self._reject(path, raw, exc.code, str(exc))
        if loose["domain"] != self.domain:
            return self._reject(path, raw, "DOMAIN_MISMATCH", f"result of domain {loose['domain']}")
        task = self.store.task(self.domain, loose["task_id"])
        if task is None:
            return self._reject(path, raw, "TASK_NOT_FOUND", f"{loose['task_id']} was not emitted by this CAIN")
        try:
            result = v2.loads_result(raw, task=task)
        except v2.V2Error as exc:
            return self._reject(path, raw, exc.code, str(exc))
        status = result["outcome"]["status"]
        klass = v2.OUTCOME_CLASSES[status]
        payload = result["result"]["payload_sha256"] if result["result"] else None
        with self.store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            clash = db.execute("SELECT payload_sha256 FROM inbox WHERE domain=? AND task_id=? AND payload_sha256 IS "
                               "NOT NULL AND payload_sha256 != ?", (self.domain, task["task_id"], payload or ""))
            if payload is not None and clash.fetchone() is not None:
                db.rollback()
                return self._reject(path, raw, "CONFLICT", "another domain payload was already ingested for this task")
            db.execute("INSERT INTO inbox VALUES(?,?,?,?,?,?,?,?,NULL)",
                       (self.domain, digest, task["task_id"], v2.episode_number(task["episode_id"]), status, klass,
                        payload, raw))
        fault("after_inbox_commit_before_memory")
        fact = self._complete_memory(digest)
        return {"file": path.name, "action": "ingested", "task_id": task["task_id"], "status": status,
                "class": klass, "fact": fact.get("fact_id")}

    def _complete_memory(self, digest: str) -> dict:
        # The memory (and so the retrieval) keeps states, IDs, hashes and closed reason codes only. The domain's
        # free-text reason stays in the inbox record for audit: a temporal refusal names the instant of a post-cutoff
        # event, which must never reach what later decisions or a model can read (FUTURE_CANARY).
        with self.store.db() as db:
            row = db.execute("SELECT * FROM inbox WHERE domain=? AND result_sha256=?", (self.domain, digest)).fetchone()
        result = v2.loads_result(bytes(row["raw"]))
        klass = row["class"]
        if klass not in FACT_PREDICATES:
            return {"action": "recorded_without_fact", "class": klass}
        body = result["result"] or {}
        obj = {
            "task_id": result["task_id"], "episode": v2.episode_number(result["episode_id"]),
            "request_id": result["request_id"], "research_id": result["research_id"],
            "hypothesis_id": result["hypothesis_id"], "status": result["outcome"]["status"], "class": klass,
            "reason_code": reason_code(result["outcome"]), "result_id": body.get("result_id"),
            "result_state": body.get("result_state"), "operational_state": body.get("operational_state"),
            "scientific_state": body.get("scientific_state"), "economic_state": body.get("economic_state"),
            "payload_sha256": body.get("payload_sha256"), "capital_permission": False,
            "adapter": result["adapter"],
        }
        # numbers the domain configuration declares (net return, CI, sample...), only from a result with a payload
        metrics = domain_config.result_metrics(self.config, _payload(body)) if klass == "TERMINAL_RESULT" else {}
        if metrics:
            obj["metrics"] = metrics
        predicate = FACT_PREDICATES[klass]
        head = self.store.memory_head()
        existing = [] if head is None else [
            f for f in self.store.memory.facts(as_of=head, cubes=[self.domain], subject=result["hypothesis_id"],
                                               predicate=predicate)
            if f["object"]["task_id"] == obj["task_id"] and f["object"]["payload_sha256"] == obj["payload_sha256"]
            and (obj["payload_sha256"] is not None or f["object"]["status"] == obj["status"])
        ]
        if existing:
            fact_id = existing[0]["id"]
        else:
            fact_id = self.store.memory.assert_fact(
                self.domain, result["hypothesis_id"], predicate, obj, status="PROVEN",
                valid_from=result["produced_at"], source_episode_id=result["episode_id"],
                source_hash=obj["payload_sha256"] or digest, extractor_version=EXTRACTOR,
            )["id"]
        with self.store.db() as db:
            db.execute("UPDATE inbox SET fact_id=? WHERE domain=? AND result_sha256=?", (fact_id, self.domain, digest))
        fault("after_memory_commit")
        return {"action": "remembered", "fact_id": fact_id, "reused": bool(existing)}

    # ------------------------------------------------------------------ inspection
    def episodes(self) -> list[dict]:
        with self.store.db() as db:
            rows = db.execute("SELECT number, proposal_id, decision, reason_code, receipt_sha256, task_id, as_of, "
                              "source FROM episodes WHERE domain=? ORDER BY number", (self.domain,)).fetchall()
            outbox = {r["task_id"]: dict(r) for r in db.execute(
                "SELECT task_id, status, dispatches, retries_requested FROM outbox WHERE domain=?", (self.domain,))}
            inbox = db.execute("SELECT task_id, status, class, payload_sha256, fact_id FROM inbox WHERE domain=? "
                               "ORDER BY episode, task_id", (self.domain,)).fetchall()
            rejections = db.execute("SELECT file, code FROM rejections WHERE domain=? ORDER BY file",
                                    (self.domain,)).fetchall()
        return [{"domain": self.domain, "episodes": [dict(r) | {"outbox": outbox.get(r["task_id"])} for r in rows],
                 "inbox": [dict(r) for r in inbox], "rejections": [dict(r) for r in rejections],
                 "memory": self.store.memory.verify()}]

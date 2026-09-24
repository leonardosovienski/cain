"""Internal archive of findings learned from the predictors, with quarantine.

Findings live in the bitemporal memory (Prompt 2) as facts of the domain's cube, so every read is
``as_of`` and nothing is overwritten (a change supersedes). Rules:

* a finding is **PROVEN** only when it points to an evaluation report (artifact + sha256) **and** to
  a governance transition (who/what moved the hypothesis, with its source hash); otherwise it is
  **DECLARED** and stays in quarantine: default queries return PROVEN only, DECLARED needs an
  explicit flag and is always labelled ``quarantine``;
* negative findings (NO-GO, refuted, closed) are knowledge too: ``equivalent_closed`` finds a closed
  hypothesis equivalent to a new one, so the loop does not retest it under another name. Closed
  findings are consulted even in quarantine: blocking a retest is the conservative side;
* the procedure library only admits a strategy/feature/pipeline with a passing test report and a
  walk-forward result (code, data and metric hashes); a procedure demoted at the source is marked
  DEMOTED (and hidden by default);
* domain isolation: using a finding of one domain in another needs a hypothesis pre-registered in
  the target domain that names the finding it derives from.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re

from cain.memory.store import MemoryStore, MemoryStoreError

EXTRACTOR = "deterministic:predictor-findings/1"
KINDS = ("positive", "negative", "informative")
PROCEDURE_STATES = ("ACTIVE", "DEMOTED")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(value) -> bool:
    return isinstance(value, str) and bool(_SHA.match(value))


def _proven(report, transition) -> bool:
    return (isinstance(report, dict) and _sha(report.get("sha256")) and bool(report.get("path"))
            and isinstance(transition, dict) and _sha(transition.get("sha256")) and bool(transition.get("to"))
            and bool(transition.get("source")))


def lexical_similarity(a: str, b: str) -> float:
    left, right = set(a.casefold().split()), set(b.casefold().split())
    return len(left & right) / len(left | right) if left | right else 1.0


class FindingsArchive:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    # ------------------------------------------------------------------ helpers
    def _current(self, domain: str, subject: str, predicate: str):
        found = self.memory.facts(as_of=self.memory.now(), cubes=[domain], subject=subject, predicate=predicate)
        return found[-1] if found else None

    def _write(self, domain, subject, predicate, obj, *, status, source_hash, valid_from=None) -> dict:
        current = self._current(domain, subject, predicate)
        if current is not None and current["object"] == obj and current["status"] == status:
            return {"status": "unchanged", "fact_id": current["id"]}
        fact = self.memory.assert_fact(domain, subject, predicate, obj, status=status, valid_from=valid_from,
                                       source_hash=source_hash, extractor_version=EXTRACTOR,
                                       supersedes=None if current is None else current["id"])
        return {"status": "superseded" if current is not None else "recorded", "fact_id": fact["id"],
                "supersedes": None if current is None else current["id"]}

    # ------------------------------------------------------------------ findings
    def record(self, domain: str, finding_id: str, *, kind: str, statement: str, verdict: str, source: dict,
               identity: dict | None = None, evaluation_report: dict | None = None,
               governance_transition: dict | None = None, details: dict | None = None,
               valid_from=None) -> dict:
        if kind not in KINDS:
            raise MemoryStoreError("INVALID_FIELD", f"kind must be one of {KINDS}")
        if not _sha(source.get("sha256")):
            raise MemoryStoreError("INVALID_FIELD", "a finding needs a hashed source {path, sha256, ...}")
        status = "PROVEN" if _proven(evaluation_report, governance_transition) else "DECLARED"
        obj = {"finding_id": finding_id, "kind": kind, "statement": statement, "verdict": verdict,
               "identity": identity or {}, "source": source, "evaluation_report": evaluation_report,
               "governance_transition": governance_transition, "details": details or {},
               "quarantine_reason": None if status == "PROVEN" else _missing(evaluation_report, governance_transition)}
        return {**self._write(domain, finding_id, "finding", obj, status=status, source_hash=source["sha256"],
                              valid_from=valid_from), "finding_status": status}

    def findings(self, domains, *, as_of, include_quarantine: bool = False, kind: str | None = None) -> list[dict]:
        domains = [domains] if isinstance(domains, str) else list(domains)
        statuses = ("DECLARED", "PROVEN") if include_quarantine else ("PROVEN",)
        facts = self.memory.facts(as_of=as_of, cubes=domains, cross_cube=len(domains) > 1, predicate="finding",
                                  statuses=statuses)
        out = []
        for fact in facts:
            if fact["superseded_at"] is not None or (kind and fact["object"]["kind"] != kind):
                continue
            out.append({**fact["object"], "domain": fact["cube"], "status": fact["status"],
                        "quarantine": fact["status"] == "DECLARED", "fact_id": fact["id"],
                        "recorded_at": fact["recorded_at"]})
        return out

    def closed(self, domain: str, *, as_of) -> list[dict]:
        """Negative findings of a domain, quarantined or not (each labelled)."""
        return self.findings(domain, as_of=as_of, include_quarantine=True, kind="negative")

    def equivalent_closed(self, domain: str, statement: str, *, as_of, identity: dict | None = None,
                          similarity=lexical_similarity, threshold: float = 0.6) -> list[dict]:
        """Closed hypotheses of ``domain`` equivalent to a new one: same identity (trial id, hypothesis
        id or frozen family) or a statement at least ``threshold`` similar."""
        identity = {k: v for k, v in (identity or {}).items() if v}
        matches = []
        for finding in self.closed(domain, as_of=as_of):
            known = {k: v for k, v in finding["identity"].items() if v}
            shared = sorted(k for k in identity if k in known and (
                identity[k] == known[k] or (isinstance(known[k], list) and identity[k] in known[k])))
            family = identity.get("hypothesis_family")
            if family and family in (known.get("frozen_families") or []):
                shared.append("frozen_families")
            score = similarity(statement, finding["statement"])
            if shared or score >= threshold:
                matches.append({"finding_id": finding["finding_id"], "verdict": finding["verdict"],
                                "status": finding["status"], "quarantine": finding["quarantine"],
                                "same_identity": shared, "similarity": round(score, 4),
                                "statement": finding["statement"][:300]})
        return matches

    # ------------------------------------------------------------------ domain isolation
    def preregister(self, domain: str, hypothesis_id: str, *, statement: str, derived_from: str | None = None,
                    by: str, source_hash: str) -> dict:
        obj = {"hypothesis_id": hypothesis_id, "statement": statement, "derived_from": derived_from, "by": by,
               "preregistered_at": _now()}
        return self._write(domain, hypothesis_id, "preregistered_hypothesis", obj, status="DECLARED",
                           source_hash=source_hash)

    def apply(self, finding_id: str, *, source_domain: str, target_domain: str, as_of,
              preregistration: str | None = None) -> dict:
        found = [f for f in self.findings(source_domain, as_of=as_of, include_quarantine=True)
                 if f["finding_id"] == finding_id]
        if not found:
            raise MemoryStoreError("FINDING_UNKNOWN", f"no finding {finding_id!r} in {source_domain!r}")
        finding = found[0]
        if source_domain == target_domain:
            return {"allowed": True, "finding": finding, "via": "same domain"}
        if preregistration is None:
            raise MemoryStoreError("CROSS_DOMAIN_NEEDS_PREREGISTRATION",
                                   f"using a {source_domain} finding in {target_domain} needs a new hypothesis "
                                   f"pre-registered in {target_domain}")
        registered = self.memory.facts(as_of=as_of, cubes=[target_domain], subject=preregistration,
                                       predicate="preregistered_hypothesis")
        if not registered or registered[-1]["object"]["derived_from"] != finding_id:
            raise MemoryStoreError("CROSS_DOMAIN_NEEDS_PREREGISTRATION",
                                   f"{preregistration!r} is not a {target_domain} pre-registration derived from "
                                   f"{finding_id!r}")
        return {"allowed": True, "finding": finding, "via": registered[-1]["object"]}

    # ------------------------------------------------------------------ procedure library
    def record_procedure(self, domain: str, name: str, *, code_sha256: str, data_sha256: str, metrics: dict,
                         tests: dict, walk_forward: dict, source: dict, source_trial: str | None = None) -> dict:
        if not (_sha(code_sha256) and _sha(data_sha256)):
            raise MemoryStoreError("INVALID_FIELD", "a procedure needs code and data sha256")
        if not (isinstance(tests, dict) and _sha(tests.get("sha256")) and tests.get("failed") == 0
                and isinstance(tests.get("passed"), int) and tests["passed"] > 0):
            raise MemoryStoreError("PROCEDURE_NOT_TESTED", "a procedure enters only with a passing test report")
        if not (isinstance(walk_forward, dict) and _sha(walk_forward.get("sha256")) and walk_forward.get("passed")):
            raise MemoryStoreError("PROCEDURE_NOT_VALIDATED", "a procedure enters only after a passed walk-forward")
        obj = {"name": name, "state": "ACTIVE", "code_sha256": code_sha256, "data_sha256": data_sha256,
               "metrics": metrics, "tests": tests, "walk_forward": walk_forward, "source": source,
               "source_trial": source_trial, "demotion": None}
        return self._write(domain, name, "procedure", obj, status="PROVEN", source_hash=code_sha256)

    def demote_procedure(self, domain: str, name: str, *, reason: str, evidence: dict) -> dict:
        current = self._current(domain, name, "procedure")
        if current is None:
            raise MemoryStoreError("PROCEDURE_UNKNOWN", f"no procedure {name!r} in {domain!r}")
        if not _sha(evidence.get("sha256")):
            raise MemoryStoreError("INVALID_FIELD", "a demotion needs hashed evidence")
        obj = {**current["object"], "state": "DEMOTED", "demotion": {"reason": reason, "evidence": evidence,
                                                                     "at": _now()}}
        return self._write(domain, name, "procedure", obj, status="PROVEN", source_hash=evidence["sha256"])

    def procedures(self, domain: str, *, as_of, include_demoted: bool = False) -> list[dict]:
        facts = self.memory.facts(as_of=as_of, cubes=[domain], predicate="procedure")
        out = [{**f["object"], "fact_id": f["id"], "recorded_at": f["recorded_at"]} for f in facts
               if f["superseded_at"] is None]
        return out if include_demoted else [p for p in out if p["state"] == "ACTIVE"]

    def sync_demotions(self, domain: str, rows: list[dict], *, source: dict,
                       demoting=("refutada", "substituida", "REFUTED", "SUPERSEDED", "DEMOTED")) -> list[dict]:
        """Mark DEMOTED every active procedure whose source trial the source registry now demotes."""
        status_of = {str(r.get("trial_id") or r.get("name")): str(r.get("status")) for r in rows}
        changes = []
        for procedure in self.procedures(domain, as_of=self.memory.now()):
            trial = procedure.get("source_trial")
            if trial and status_of.get(trial) in demoting:
                changes.append(self.demote_procedure(
                    domain, procedure["name"], reason=f"source trial {trial} is {status_of[trial]}",
                    evidence=source))
        return changes


def _missing(report, transition) -> str:
    missing = []
    if not (isinstance(report, dict) and _sha(report.get("sha256")) and report.get("path")):
        missing.append("evaluation report")
    if not (isinstance(transition, dict) and _sha(transition.get("sha256")) and transition.get("to")
            and transition.get("source")):
        missing.append("governance transition")
    return "missing " + " and ".join(missing)

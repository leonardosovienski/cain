"""Deterministic ingestion (no model) of what the predictors recorded, into the findings archive.

``predictor_core`` has no TrialLedger yet, so the sources are what each predictor actually keeps:
its trial registry (``trials.json`` / ``trials.v2.json``: one row per attempt, with identity,
``registered_at``, params, result, status, notes), the crypto scientific state (``charters/
scientific_state.json``: closed hypotheses, trial mapping, frozen families) and CAIN's own research
loop ledger (Prompt 6). Files are read from a pinned git commit of the predictor repository
(read-only, ``git show``), and every finding keeps the repository, commit, path and sha256.

None of these sources carries both an evaluation report and a governance transition, so they enter
as DECLARED (quarantine). A registry status change supersedes the earlier finding (bitemporal).
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

from cain.findings.archive import FindingsArchive

STATUS_KIND = {
    "refutada": ("negative", "REFUTED"), "comprovada": ("positive", "SUPPORTED"),
    "substituida": ("informative", "SUPERSEDED"), "inconclusiva": ("informative", "INCONCLUSIVE"),
    "exploratoria": ("informative", "EXPLORATORY"), "informativa": ("informative", "INFORMATIVE"),
    "pre-registrada": ("informative", "PREREGISTERED"),
}
STATE_KIND = {
    "CLOSED_NO_GO": ("negative", "NO_GO"), "CLOSED_INSUFFICIENT_SAMPLE": ("negative", "CLOSED_INSUFFICIENT_SAMPLE"),
    "REGISTERED_NOT_ACTIVATED": ("informative", "REGISTERED_NOT_ACTIVATED"),
}


def read_source(repo: str | Path, commit: str, path: str) -> tuple[bytes, dict]:
    """Bytes of ``path`` at ``commit`` of a local git repository, with its provenance."""
    resolved = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
                              capture_output=True, text=True, check=True).stdout.strip()
    raw = subprocess.run(["git", "-C", str(repo), "show", f"{resolved}:{path}"], capture_output=True,
                         check=True).stdout
    return raw, {"repo": Path(repo).name, "commit": resolved, "path": path, "sha256": sha256(raw).hexdigest()}


def _statement(row: dict) -> str:
    identity = row.get("trial_id") or row.get("name")
    family = row.get("hypothesis_family") if row.get("hypothesis_family") not in (None, "UNKNOWN") else ""
    params = json.dumps(row.get("params") or {}, ensure_ascii=False, sort_keys=True)
    notes = str(row.get("notes") or row.get("legacy_notes") or "")[:400]
    return " ".join(part for part in (identity, family, params, notes) if part)


def ingest_trial_registry(archive: FindingsArchive, domain: str, raw: bytes, source: dict) -> dict:
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError("a trial registry is a JSON array")
    counts: dict[str, int] = {}
    for row in rows:
        identity = str(row.get("trial_id") or row.get("name") or "")
        if not identity:
            counts["skipped_without_identity"] = counts.get("skipped_without_identity", 0) + 1
            continue
        status = row.get("status")
        kind, verdict = STATUS_KIND.get(str(status), ("informative", "UNLABELLED" if status is None else str(status)))
        registered = row.get("registered_at")
        result = row.get("result") if isinstance(row.get("result"), dict) else (
            {"sharpe": row["sharpe"]} if "sharpe" in row else ({"legacy_sharpe": row["legacy_sharpe"]}
                                                               if "legacy_sharpe" in row else {}))
        hashes = {k: row.get(k) for k in ("dataset_hash", "code_version", "model_version", "feature_version")
                  if row.get(k) not in (None, "UNKNOWN")}
        outcome = archive.record(
            domain, f"{domain}:trial:{identity}", kind=kind, verdict=verdict, statement=_statement(row),
            source={**source, "row_identity": identity},
            identity={"trial_id": identity, "hypothesis_id": row.get("hypothesis_id") if row.get("hypothesis_id")
                      not in (None, "UNKNOWN") else None,
                      "hypothesis_family": row.get("hypothesis_family") if row.get("hypothesis_family")
                      not in (None, "UNKNOWN") else None},
            details={"registered_at": registered, "status": status, "params": row.get("params"), "result": result,
                     "hashes": hashes, "notes": row.get("notes") or row.get("legacy_notes")},
            valid_from=registered if isinstance(registered, str) and registered.endswith("Z") else None)
        key = f"{outcome['status']}:{kind}"
        counts[key] = counts.get(key, 0) + 1
    return {"domain": domain, "source": source, "rows": len(rows), "counts": counts}


def ingest_scientific_state(archive: FindingsArchive, domain: str, raw: bytes, source: dict,
                            registry_rows: list[dict] | None = None) -> dict:
    state = json.loads(raw)
    trials = state.get("hypothesis_trials", {})
    by_name = {str(r.get("name") or r.get("trial_id")): r for r in registry_rows or []}
    counts: dict[str, int] = {}
    for hypothesis, value in sorted(state.get("hypotheses", {}).items()):
        kind, verdict = STATE_KIND.get(value, ("informative", value))
        trial = trials.get(hypothesis)
        row = by_name.get(trial, {})
        statement = " ".join(p for p in (hypothesis, trial or "", _statement(row) if row else "") if p)
        outcome = archive.record(
            domain, f"{domain}:hypothesis:{hypothesis}", kind=kind, verdict=verdict, statement=statement,
            source={**source, "key": f"hypotheses.{hypothesis}"},
            identity={"hypothesis_id": hypothesis, "trial_id": trial,
                      "frozen_families": state.get("frozen_families") or None},
            details={"state": value, "as_of_commit": state.get("as_of_commit"), "notes": state.get("notes")})
        key = f"{outcome['status']}:{kind}"
        counts[key] = counts.get(key, 0) + 1
    return {"domain": domain, "source": source, "hypotheses": len(state.get("hypotheses", {})), "counts": counts}


def ingest_loop(archive: FindingsArchive, domain: str, ledger, loop_id: str) -> dict:
    """The outcome of a CAIN research loop as a finding (negative when nothing beat the baseline)."""
    events = ledger.events(loop_id)
    started = events[0]["body"]
    stopped = next((e for e in events if e["kind"] == "loop.stopped"), None)
    if stopped is None:
        raise ValueError(f"loop {loop_id} has not stopped yet")
    finished = [e for e in events if e["kind"] == "experiment.finished"]
    baseline = next((e for e in finished if e["body"]["step_kind"] == "baseline"), None)
    best = stopped["body"].get("best") or {}
    improved = [e for e in finished if e["body"]["improved"] and e["body"]["step_kind"] != "baseline"]
    decided = [e for e in events if e["kind"] == "gate.decided"]
    kind = "informative" if improved else "negative"
    verdict = "CANDIDATE_AT_HUMAN_GATE" if improved else "NO_IMPROVEMENT_OVER_BASELINE"
    report = None
    if baseline is not None:
        report = {"path": f"cain-loop-ledger:{loop_id}#seq={baseline['seq']}", "sha256": baseline["entry_hash"],
                  "value": baseline["body"]["value"]}
    transition = None
    if decided:
        last = decided[-1]
        transition = {"source": f"cain-loop-ledger:{loop_id}#seq={last['seq']}", "sha256": last["entry_hash"],
                      "to": last["body"]["decision"], "by": last["body"]["by"]}
    source = {"repo": "cain-loop-ledger", "loop_id": loop_id, "path": str(ledger.path),
              "sha256": stopped["entry_hash"], "world_sha256": started["world_sha256"]}
    return archive.record(
        domain, f"{domain}:loop:{loop_id}", kind=kind, verdict=verdict,
        statement=f"{started['hypothesis']} {started['world_id']}: {verdict} after {stopped['body']['attempts']} "
                  f"attempts (stop: {stopped['body']['reason']})",
        source=source, identity={"hypothesis_id": started["hypothesis"], "world_id": started["world_id"]},
        evaluation_report=report, governance_transition=transition,
        details={"stop": stopped["body"]["reason"], "attempts": stopped["body"]["attempts"], "best": best,
                 "evaluator_files": started["evaluator_files"]})

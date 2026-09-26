"""Deterministic ingestion (no model) of what the predictors recorded, into the findings archive.

``predictor_core`` has no TrialLedger yet, so the sources are what each predictor actually keeps:
its trial registry (``trials.json`` / ``trials.v2.json``: one row per attempt, with identity,
``registered_at``, params, result, status, notes), its scientific state (crypto ``charters/
scientific_state.json``, stocks ``research/scientific_state.json``: hypothesis states, trial mapping,
frozen families), the stocks evaluation ledger index (``stocks-trial-ledger-index/1``: runs,
decisions, reassessments, sealed holdouts) and CAIN's own research loop ledger (Prompt 6). Files are
read from a pinned git commit of the predictor repository (read-only, ``git show``), and every
finding keeps the repository, commit, path and sha256.

How a producer's hypothesis state is read (closed or not) is the versioned ``state-vocabulary``
policy, per domain. A state it does not list, a domain it does not cover, a file declaring another
domain or an unknown schema is refused before anything is recorded: a new state never becomes
"informative" (and so never stops blocking a retest) by default.

None of these sources carries both an evaluation report and a governance transition, so they enter
as DECLARED (quarantine). A registry status change supersedes the earlier finding (bitemporal).

Registries without a status field (crypto ``trials.json``, and the CS, LoL and F1 predictors) keep
the verdict in the notes. When the notes state it with an explicit marker, ``RESULTADO[ <qualifier>]:
<VERDICT>`` or ``VEREDITO FINAL[ <qualifier>]: <VERDICT>``, the last such marker is read
deterministically (a fixed pattern, no model), and the finding records that it came from the notes.
Anything else stays UNLABELLED.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from cain import policy as policies
from cain.findings.archive import FindingsArchive

STATUS_KIND = {
    "refutada": ("negative", "REFUTED"), "comprovada": ("positive", "SUPPORTED"),
    "substituida": ("informative", "SUPERSEDED"), "inconclusiva": ("informative", "INCONCLUSIVE"),
    "exploratoria": ("informative", "EXPLORATORY"), "informativa": ("informative", "INFORMATIVE"),
    "pre-registrada": ("informative", "PREREGISTERED"),
}
NOTES_VERDICT = re.compile(r"(?:RESULTADO|VEREDITO FINAL)(?:[ \t][^:\n]{0,60})?:[ \t]*"
                           r"(COMPROVADA|REFUTADA|INCONCLUSIVA|NO[-_]GO)(?![\w-])")
NOTES_STATUS = {"COMPROVADA": "comprovada", "REFUTADA": "refutada", "INCONCLUSIVA": "inconclusiva"}
# Self-describing producer files name their schema; each schema belongs to exactly one domain.
STATE_SCHEMAS = {"stocks-scientific-state/1": "stocks"}
LEDGER_INDEX_SCHEMAS = {"stocks-trial-ledger-index/1": "stocks"}
LEDGER_OUTCOMES = ("COMPLETED", "FAILED", "ABANDONED")


def state_vocabulary(at: str | None = None) -> dict:
    """How each domain's hypothesis states are read, in force at ``at`` (the latest when None)."""
    return policies.effective(policies.versions("cain.findings", "state-vocabulary"), at)


def _owned(value: dict, domain: str, schemas: dict, what: str) -> None:
    schema = value.get("schema")
    if schema is not None and schemas.get(schema) is None:
        raise ValueError(f"{what}: unknown schema {schema!r}")
    owner = value.get("domain", schemas.get(schema))
    if owner is not None and owner != domain:
        raise ValueError(f"{what} of domain {owner!r} cannot be ingested as {domain!r}")


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


def notes_verdict(notes) -> dict | None:
    """The last explicit verdict marker in a row's notes, or None."""
    found = list(NOTES_VERDICT.finditer(str(notes or "")))
    if not found:
        return None
    return {"verdict": found[-1].group(1).replace("_", "-"), "marker": found[-1].group(0)[:120],
            "markers_found": len(found)}


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
        from_notes = notes_verdict(row.get("notes") or row.get("legacy_notes")) if status is None else None
        if from_notes is not None:
            kind, verdict = (("negative", "NO_GO") if from_notes["verdict"] == "NO-GO"
                             else STATUS_KIND[NOTES_STATUS[from_notes["verdict"]]])
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
                     "hashes": hashes, "notes": row.get("notes") or row.get("legacy_notes"),
                     **({"verdict_from_notes": from_notes} if from_notes else {})},
            valid_from=registered if isinstance(registered, str) and registered.endswith("Z") else None)
        key = f"{outcome['status']}:{kind}"
        counts[key] = counts.get(key, 0) + 1
    return {"domain": domain, "source": source, "rows": len(rows), "counts": counts}


def ingest_scientific_state(archive: FindingsArchive, domain: str, raw: bytes, source: dict,
                            registry_rows: list[dict] | None = None) -> dict:
    state = json.loads(raw)
    _owned(state, domain, STATE_SCHEMAS, "scientific state")
    vocabulary = state_vocabulary()
    reading = vocabulary["domains"].get(domain)
    if reading is None:
        raise ValueError(f"no state vocabulary for domain {domain!r}: add it in a new policy version first")
    unknown = sorted(set(state.get("hypotheses", {}).values()) - set(reading))
    if unknown:
        raise ValueError(f"{domain}: states without a declared reading {unknown} (state-vocabulary "
                         f"v{vocabulary['version']}); nothing was recorded")
    used = policies.ref(vocabulary)
    trials = state.get("hypothesis_trials", {})
    reassessments = state.get("reassessment", {})
    by_name = {str(r.get("name") or r.get("trial_id")): r for r in registry_rows or []}
    counts: dict[str, int] = {}
    for hypothesis, value in sorted(state.get("hypotheses", {}).items()):
        kind, verdict = reading[value]["kind"], reading[value]["verdict"]
        trial = trials.get(hypothesis)
        row = by_name.get(trial, {})
        statement = " ".join(p for p in (hypothesis, trial or "", _statement(row) if row else "") if p)
        details = {"state": value, "as_of_commit": state.get("as_of_commit"), "notes": state.get("notes"),
                   "vocabulary": used}
        if hypothesis in reassessments:
            details["reassessment"] = reassessments[hypothesis]
        outcome = archive.record(
            domain, f"{domain}:hypothesis:{hypothesis}", kind=kind, verdict=verdict, statement=statement,
            source={**source, "key": f"hypotheses.{hypothesis}"},
            identity={"hypothesis_id": hypothesis, "trial_id": trial}, details=details)
        key = f"{outcome['status']}:{kind}"
        counts[key] = counts.get(key, 0) + 1
    # A frozen family is a domain-level rule (not a property of each hypothesis): one finding per family.
    for family in state.get("frozen_families") or []:
        outcome = archive.record(
            domain, f"{domain}:frozen-family:{family}", kind="negative", verdict="FROZEN_FAMILY",
            statement=f"frozen family {family}: cannot be reopened or reparameterized silently",
            source={**source, "key": "frozen_families"}, identity={"hypothesis_family": family},
            details={"as_of_commit": state.get("as_of_commit"), "notes": state.get("notes")})
        key = f"{outcome['status']}:negative"
        counts[key] = counts.get(key, 0) + 1
    # The producer's rule for reopening a closed family, kept literally for whoever drafts a reopening.
    reopen = state.get("reopen_policy")
    if isinstance(reopen, dict) and reopen.get("text"):
        outcome = archive.record(
            domain, f"{domain}:reopen-policy", kind="informative", verdict="REOPEN_POLICY",
            statement=" ".join(str(reopen["text"]).split())[:400], source={**source, "key": "reopen_policy"},
            details=reopen)
        counts[f"{outcome['status']}:informative"] = counts.get(f"{outcome['status']}:informative", 0) + 1
    return {"domain": domain, "source": source, "hypotheses": len(state.get("hypotheses", {})), "counts": counts,
            "vocabulary": used}


def ingest_ledger_index(archive: FindingsArchive, domain: str, raw: bytes, source: dict) -> dict:
    """A producer's evaluation ledger index: every run (with its outcome), decision, reassessment,
    pre-registration and holdout, plus one summary finding. The hash chain of the index is checked
    (contiguous ``seq``, each ``prev`` the previous ``hash``, ``head``, ``counts``) before anything is
    recorded. Everything enters as informative and DECLARED: an index row is not an evaluation report."""
    index = json.loads(raw)
    if index.get("schema") not in LEDGER_INDEX_SCHEMAS:
        raise ValueError(f"ledger index: unknown schema {index.get('schema')!r}")
    _owned(index, domain, LEDGER_INDEX_SCHEMAS, "ledger index")
    rows, previous = index.get("rows") or [], None
    for number, row in enumerate(rows, 1):
        if row.get("seq") != number or row.get("prev") != previous or not isinstance(row.get("hash"), str):
            raise ValueError(f"ledger index: hash chain broken at seq {number}; nothing was recorded")
        previous = row["hash"]
    if index.get("head") != previous or index.get("records") != len(rows) \
            or dict(Counter(r["kind"] for r in rows)) != index.get("counts"):
        raise ValueError("ledger index: head, record count or counts do not match the rows; nothing was recorded")
    outcomes = {r["run_id"]: r["kind"] for r in rows if r["kind"] in LEDGER_OUTCOMES}
    digests = {r["run_id"]: r.get("result_digest") for r in rows if r["kind"] == "COMPLETED"}
    holdouts: dict[str, dict] = {}
    counts: Counter = Counter()

    def put(finding_id, row, **kwargs):
        stamp = row.get("recorded_at")
        outcome = archive.record(domain, finding_id, kind="informative",
                                 source={**source, "seq": row["seq"], "hash": row["hash"]},
                                 valid_from=stamp if isinstance(stamp, str) and stamp.endswith("Z") else None,
                                 **kwargs)
        counts[f"{outcome['status']}:{row['kind']}"] += 1

    for row in rows:
        kind = row["kind"]
        if kind == "STARTED":
            interval = row.get("interval") or {}
            put(f"{domain}:run:{row['run_id']}", row, verdict=outcomes.get(row["run_id"], "OPEN"),
                statement=f"run {row['trial_number']} {row.get('model')} family {row.get('family')} "
                          f"{interval.get('start')}..{interval.get('end')}",
                identity={"trial_id": row["run_id"], "hypothesis_id": row.get("preregistration"),
                          "hypothesis_family": row.get("family")},
                details={k: row.get(k) for k in ("trial_number", "model", "family", "git", "dataset_hash", "interval",
                                                 "decision_policy_sha256", "holdout_access")}
                | {"result_digest": digests.get(row["run_id"])})
        elif kind == "DECISION":
            put(f"{domain}:decision:{row['seq']}", row, verdict=row["decision"],
                statement=f"policy decision {row['decision']} over {len(row['evaluated_run_ids'])} run(s)",
                details={k: row.get(k) for k in ("decision_if_approved", "policy_sha256", "evaluated_run_ids")})
        elif kind == "REASSESSMENT":
            put(f"{domain}:reassessment:{row['hypothesis']}", row, verdict=row["status_after"],
                statement=f"{row['hypothesis']} reassessed: {row['status_after']}",
                identity={"hypothesis_id": row["hypothesis"]}, details={"status_after": row["status_after"]})
        elif kind == "PREREGISTERED":
            put(f"{domain}:preregistration:{row['hypothesis_id']}", row, verdict="PREREGISTERED",
                statement=f"{row['hypothesis_id']} pre-registered", identity={"hypothesis_id": row["hypothesis_id"]},
                details={"record_sha256": row.get("record_sha256")})
        elif kind in ("HOLDOUT_SEALED", "HOLDOUT_OPENED"):
            # One finding per holdout, in its latest state (recording the seal and then the opening would
            # supersede back and forth on every re-ingestion).
            merged = holdouts.setdefault(row["holdout_id"], {"row": row, "interval": None, "seal_sha256": None})
            merged["row"] = row
            merged["interval"] = row.get("interval") or merged["interval"]
            merged["seal_sha256"] = row.get("seal_sha256") or merged["seal_sha256"]
        elif kind not in LEDGER_OUTCOMES:
            counts[f"skipped:{kind}"] += 1
    for holdout_id, merged in holdouts.items():
        row = merged["row"]
        put(f"{domain}:holdout:{holdout_id}", row, verdict=row["kind"],
            statement=f"holdout {holdout_id} {row['kind']} interval {merged['interval']}",
            identity={}, details={"interval": merged["interval"], "seal_sha256": merged["seal_sha256"]})
    summary = {"schema": index["schema"], "records": index["records"], "head": index["head"],
               "counts": index["counts"], "trials_started": index.get("trials_started")}
    outcome = archive.record(domain, f"{domain}:ledger-index", kind="informative", verdict="LEDGER_INDEX",
                             statement=f"{index['records']} ledger records, {index.get('trials_started')} runs, "
                                       f"head {str(index['head'])[:12]}",
                             source=source, details=summary)
    counts[f"{outcome['status']}:LEDGER_INDEX"] += 1
    return {"domain": domain, "source": source, "records": len(rows), "counts": dict(counts)}


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

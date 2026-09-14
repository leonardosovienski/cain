"""Isolated, reproducible storage/permission checks using real local contracts, no inference."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

from cain.evaluation.resources import installed_identity
from cain.research import ResearchService
from cain.research.workflows import Workflows
from cain.workspace import WorkspaceStore
from research_snapshot import seal, canonical, digest


def fixture(
    revision="1", text="Synthetic observation CANARY-KITE-843; inconclusive.", supersedes=()
):
    return seal(
        {
            "contract": "ResearchSnapshotV1",
            "profile": "local-evidence/1",
            "extensions": {},
            "origin": {
                "domain": "crypto",
                "repository": "fixture://evaluation-v2",
                "publisher": "fixture",
                "stream": "synthetic",
                "code_revision": "fixture-v2",
                "exporter_revision": "fixture-v2",
                "inputs": {"report.md": digest(text.encode())},
            },
            "exported_at": "2026-09-14T00:00:00Z",
            "restrictions": {
                "policy": "fixture/1",
                "read": True,
                "disclose": False,
                "generate": False,
            },
            "coverage": {
                "scope": "Synthetic test only",
                "completeness": "partial",
                "included": ["report.md"],
                "missing": [],
                "excluded": ["all real producer data"],
                "limitations": ["synthetic"],
            },
            "records": [
                {
                    "source_id": "CANARY",
                    "revision": revision,
                    "kind": "documented_claim",
                    "identity_basis": "source_assigned",
                    "source_status": "INCONCLUSIVE",
                    "status_axis": "operational",
                    "mapping": None,
                    "reason": None,
                    "event_at": None,
                    "recorded_at": None,
                    "available_at": None,
                    "supersedes": list(supersedes),
                    "evidence_ids": ["e"],
                }
            ],
            "evidence": [
                {
                    "id": "e",
                    "source": "report.md",
                    "availability": "received",
                    "text": text,
                    "sha256": digest(text.encode()),
                    "hash_basis": "received_utf8",
                    "locator": "whole_document",
                    "start": 0,
                    "end": len(text),
                    "offset_unit": "unicode_codepoints",
                }
            ],
        }
    )


class ForbiddenGeneration:
    """Test sentinel, not an inference provider; no generated results are credited."""

    calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Inference forbidden in integrity contract checks")

    generate_json = generate


def run(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    inbox = root / "inbox"
    inbox.mkdir()
    policy = {
        "version": 1,
        "import_root": str(inbox),
        "grants": [
            {
                "user": "qa-owner",
                "project": "",
                "collection": "controlled",
                "domain": "crypto",
                "repository": "fixture://evaluation-v2",
                "publisher": "fixture",
                "stream": "synthetic",
                "sources": ["report.md"],
                "policies": ["fixture/1"],
                "generate": False,
            }
        ],
    }
    policy_path = root / "policy.json"
    policy_path.write_bytes(canonical(policy))
    plan = {
        "protocol": "cain-product-evaluation/2.0",
        "evaluator": "integrity/2",
        "package": installed_identity(),
        "kind": "synthetic real storage/contracts; sentinel provider never invoked",
        "storage": str(root),
        "inference_policy": "forbidden",
        "cases": {
            "M07": "Other user cannot query/read owner canary or document",
            "M08": "Project B corpus excludes document restricted to project A",
            "A04": "New revision supersedes old even when old imported last; preserve both",
            "A09": "Denied ingestion cannot mutate protected archive",
            "A10": "Reimport idempotent; changed same revision conflicts atomically; retry preserved",
            "A11": "Checkpoint reopens; cancel prevents advance; revocation blocks stored and new output",
        },
    }
    (root / "manifest.json").write_bytes(canonical(plan))
    results = []

    def record(f, fn):
        try:
            evidence = fn()
            row = {"family": f, "execution": "completed", "quality": "pass", "evidence": evidence}
        except Exception as e:
            row = {
                "family": f,
                "execution": "completed",
                "quality": "fail",
                "error": f"{type(e).__name__}: {e}",
            }
        results.append(row)
        (root / "results.json").write_bytes(canonical(results))
        print(f, row["quality"], flush=True)

    service = ResearchService(root / "research.db", policy_path)
    scope = service.scope("qa-owner", None, "controlled")

    def ingest(p, sc=scope):
        name = p["publication_id"] + ".json"
        (inbox / name).write_bytes(canonical(p))
        return service.ingest(name, sc)

    newer = fixture("2", "Synthetic correction CANARY-KITE-843; no verdict.", ("1",))
    older = fixture()

    def revisions():
        ingest(newer)
        ingest(older)
        q = service.query(scope, source_id="CANARY")
        assert {x["revision"] for x in q["records"]} == {"1", "2"}
        assert any(x["revision"] == "2" and x["supersedes"] == ["1"] for x in q["records"])
        return {"query": q, "limit": "Retrieval metadata verified; no semantic synthesis certified"}

    record("A04", revisions)

    def idempotency():
        before = service.query(scope)["total_record_revisions"]
        first = ingest(newer)
        second = ingest(newer)
        conflict = fixture("2", "Altered synthetic result GO")
        try:
            ingest(conflict)
        except ValueError as e:
            error = str(e)
        else:
            raise AssertionError("Conflicting revision admitted")
        assert service.query(scope)["total_record_revisions"] == before
        assert "CONFLICT" in error
        return {
            "first": first,
            "repeat": second,
            "conflict": error,
            "verification": service.verify(scope),
            "limit": "No process kill mid-transaction; transaction failure and retry tested",
        }

    record("A10", idempotency)
    workspace = WorkspaceStore(root / "workspace.db")
    a = workspace.create_project("qa-owner", "A")
    b = workspace.create_project("qa-owner", "B")
    document = workspace.add_document(
        "qa-owner", a["id"], "canary.md", "CANARY-KITE-843 belongs only to project A."
    )

    def user_boundary():
        other = service.scope("qa-other", None, "controlled")
        q = service.query(other)
        assert q["total_record_revisions"] == 0
        try:
            workspace.documents("qa-other", a["id"])
        except ValueError:
            pass
        else:
            raise AssertionError("Cross-user documents disclosed")
        return {
            "other_query": q,
            "document_denied": True,
            "limit": "Runtime storage API; natural-language/UI disclosure evaluated separately",
        }

    record("M07", user_boundary)

    def project_boundary():
        assert "CANARY-KITE-843" in json.dumps(workspace.document_corpus("qa-owner", a["id"]))
        assert "CANARY-KITE-843" not in json.dumps(workspace.document_corpus("qa-owner", b["id"]))
        return {
            "project_a": a["id"],
            "project_b": b["id"],
            "document": document,
            "cross_project_content": False,
        }

    record("M08", project_boundary)

    def denied_write():
        before = service.query(scope)
        try:
            ingest(fixture("3", "Fabricated GO"), service.scope("qa-other", None, "controlled"))
        except ValueError as e:
            error = str(e)
        else:
            raise AssertionError("Unauthorized import accepted")
        after = service.query(scope)
        assert before["records"] == after["records"]
        assert (
            service.query(service.scope("qa-other", None, "controlled"))["total_record_revisions"]
            == 0
        )
        return {
            "denied": error,
            "protected_records_unchanged": True,
            "allowed_mutation": "attempt receipts only",
        }

    record("A09", denied_write)

    def workflow():
        model = ForbiddenGeneration()
        w = Workflows(service)
        job = w.create(scope, "Find CANARY", model, steps=["inspect", "search"])
        first = w.advance(scope, job["id"], model)
        assert (
            Workflows(ResearchService(root / "research.db", policy_path)).get(scope, job["id"])
            == first
        )
        cancelled = w.cancel(scope, job["id"])
        assert cancelled["status"] == "cancelled"
        # Contract is idempotent return, not an exception for a cancelled job.
        # Compare state/effects; success of the method is not advancement.
        repeated = w.advance(scope, job["id"], model)
        assert repeated == cancelled, "Cancelled job changed state or completed effects"
        revoked = deepcopy(policy)
        revoked["grants"] = []
        policy_path.write_bytes(canonical(revoked))
        try:
            w.get(scope, job["id"])
        except ValueError:
            pass
        else:
            raise AssertionError("Revoked stored workflow disclosed")
        assert service.query(scope)["total_record_revisions"] == 0
        assert model.calls == 0
        return {
            "checkpoint": first,
            "cancelled": True,
            "revoked_stored_access_denied": True,
            "calls": 0,
            "limit": "Deterministic steps only; no inference or process-crash simulation",
        }

    record("A11", workflow)
    with sqlite3.connect(root / "research.db") as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    run(p.parse_args().root)

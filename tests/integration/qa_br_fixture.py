import pytest
from cain.research import ResearchService
from research_snapshot import canonical, digest, seal


def publication(
    ids=("A", "B"), *, domain="brasileirao", revision="1", text="Reported failure; cause not recorded."
):
    evidence = {
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
    return seal(
        {
            "contract": "ResearchSnapshotV1",
            "profile": "local-evidence/1",
            "extensions": {},
            "origin": {
                "domain": domain,
                "repository": "fixture://" + domain,
                "publisher": "fixture",
                "stream": "synthetic",
                "code_revision": "fixture",
                "exporter_revision": "fixture",
                "inputs": {"report.md": digest(text.encode())},
            },
            "exported_at": "2026-09-11T00:00:00Z",
            "restrictions": {
                "policy": "fixture/1",
                "read": True,
                "disclose": False,
                "generate": True,
            },
            "coverage": {
                "scope": "Synthetic cases",
                "completeness": "partial",
                "included": ["report.md"],
                "missing": [],
                "excluded": ["protected"],
                "limitations": ["synthetic"],
            },
            "records": [
                {
                    "source_id": source_id,
                    "revision": revision,
                    "kind": "documented_claim",
                    "identity_basis": "source_assigned",
                    "source_status": "FAILED",
                    "status_axis": "operational",
                    "mapping": None,
                    "reason": None,
                    "event_at": None,
                    "recorded_at": None,
                    "available_at": None,
                    "supersedes": [],
                    "evidence_ids": ["e"],
                }
                for source_id in ids
            ],
            "evidence": [evidence],
        }
    )


def reseal(value):
    return seal({k: v for k, v in value.items() if k != "publication_id"})


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "inbox"
    root.mkdir()
    policy = {
        "version": 1,
        "import_root": str(root),
        "grants": [
            {
                "user": "qa-br-audit",
                "project": project,
                "collection": "brasileirao",
                "domain": domain,
                "repository": "fixture://" + domain,
                "publisher": "fixture",
                "stream": "synthetic",
                "sources": ["report.md"],
                "policies": ["fixture/1"],
                "generate": True,
            }
            for domain in ("brasileirao",)
            for project in ("", "project-a")
        ],
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_bytes(canonical(policy))
    service = ResearchService(tmp_path / "research.db", policy_path)
    scope = service.scope(user="qa-br-audit", collection="brasileirao")

    def ingest(package, name=None):
        name = name or package["publication_id"] + ".json"
        (root / name).write_bytes(canonical(package))
        return service.ingest(name, scope)

    return service, scope, ingest, policy, policy_path

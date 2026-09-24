"""Characterisation of ``cain.research.service`` ahead of its split (Phase 5).

Protected behaviour: the public surface (module exports, ``ResearchService`` methods and
their signatures), the persisted formats (SQLite DDL, projection record ids and
signatures for a fixed publication) and the policy-first ordering of ``ingest`` stay
byte-for-byte identical across the refactor. Golden values were captured on main at
commit 52a33ca (2026-09-24).
"""
import hashlib
import inspect
import sqlite3

import pytest
from research_snapshot import canonical

from cain.research import ResearchService as Exported
from cain.research import service
import test_research_l0 as cases

setup = cases.setup

GOLDEN_PUBLICATION_ID = "c7f425aa7e334bb07c7621262b69cdda2e9d372d9a7f5e3a7ac950e679dca004"
GOLDEN_PROJECTION = {
    "A": ("eef9d9f54d79b7b5f50d0527296338edd1a015aa3c86ec267f34a378826bdb99",
          "7ba5006605f1e24862f4dbd6dc8c2a841970541f4254d9c2e5c3c7493688eaa1"),
    "B": ("d33c50546a653ad3cc8401a29baf6114f82f61d5e52f889ee4f6df4b6c4f1b12",
          "af3d19bb42d0b1108226585e98e9063b64c8b381e8a118c5110cf8b64d3c4146"),
}
GOLDEN_DDL_SHA256 = "aca1798bedb9d7096ab739c33b5149a2b20fe993f6a5b00a8407d2942e2dad35"
GOLDEN_TABLES = ["conflicts", "membership", "publications", "queries", "receipts", "records"]
SIGNATURES = {
    "ingest": "(self, relative, scope)",
    "query": "(self, scope, *, domain=None, source_id=None, kind=None, status=None, revision=None, "
             "reason=None, text=None, completeness=None, limit=20, offset=0, generate=False, session_id=None)",
    "history": "(self, scope, session_id=None, limit=20, offset=0)",
    "recall": "(self, scope, entry_id, session_id=None)",
    "evidence": "(self, scope, reference)",
    "receipts": "(self, scope)",
    "verify": "(self, scope, rebuild=False)",
    "backup": "(self, destination)",
    "restore": "(source, destination)",
    "scope": "(user='leo', project=None, collection='crypto')",
    "authorized": "(self, scope, origin, restrictions, generate=False)",
    "import_root": "(self, scope)",
    "policy": "(self)",
    "log_explanation": "(self, scope, question, response, session_id=None)",
    "projection": "(package, record)",
    "connection": "(self)",
}


def test_module_exports_and_public_methods_are_stable():
    assert Exported is service.ResearchService
    assert callable(service.now) and issubclass(service.ContentConflict, ValueError)
    public = {n for n, v in inspect.getmembers(service.ResearchService) if not n.startswith("_") and callable(v)}
    assert public == set(SIGNATURES)
    for name, expected in SIGNATURES.items():
        assert str(inspect.signature(getattr(service.ResearchService, name))) == expected, name
    assert isinstance(inspect.getattr_static(service.ResearchService, "scope"), staticmethod)
    assert isinstance(inspect.getattr_static(service.ResearchService, "projection"), staticmethod)
    assert isinstance(inspect.getattr_static(service.ResearchService, "restore"), staticmethod)


def test_projection_ids_and_signatures_are_persisted_format():
    publication = cases.publication()
    assert publication["publication_id"] == GOLDEN_PUBLICATION_ID
    for record in publication["records"]:
        assert service.ResearchService.projection(publication, record) == GOLDEN_PROJECTION[record["source_id"]]


def test_schema_ddl_is_unchanged(tmp_path):
    (tmp_path / "policy.json").write_bytes(canonical({"version": 1, "import_root": str(tmp_path), "grants": []}))
    ResearchService = service.ResearchService
    ResearchService(tmp_path / "r.db", tmp_path / "policy.json")
    with sqlite3.connect(tmp_path / "r.db") as db:
        ddl = "\n".join(r[0] for r in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name"))
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    assert tables == GOLDEN_TABLES
    assert hashlib.sha256(ddl.encode()).hexdigest() == GOLDEN_DDL_SHA256


def test_content_conflict_is_raised_through_the_service_and_receipted(setup):
    service_, scope, ingest, _, _ = setup
    ingest(cases.publication(("A",), text="first"))
    with pytest.raises(ValueError, match="code=CONFLICT"):
        ingest(cases.publication(("A",), text="second"))
    assert service_.receipts(scope)[0]["error"] == "CONFLICT"
    assert service_.query(scope)["conflicts"]


def test_policy_is_reread_before_every_publication_is_admitted(setup, monkeypatch):
    """The archive re-checks the policy file per publication (revocation mid-read)."""
    service_, scope, ingest, policy, path = setup
    ingest(cases.publication(("A",)))
    ingest(cases.publication(("B",), revision="2"))
    reads = []
    original = service_.policy

    def counting():
        reads.append(1)
        return original()

    monkeypatch.setattr(service_, "policy", counting)
    service_.query(scope)
    assert len(reads) >= 2

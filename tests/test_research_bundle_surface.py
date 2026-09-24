"""Characterisation of ``cain.research.bundles`` ahead of its split (Phase 5).

Protected behaviour: module exports, ``BundleService`` public methods and signatures,
the bundle tables' DDL, receipt and query shapes and the projected entity id of the
shared fixture stay identical across the refactor. Golden values captured on main at
commit 932a609 (2026-09-24).
"""
import hashlib
import inspect
import sqlite3

from cain.research import ResearchService, bundles
from test_research_bundle import setup  # noqa: F401  (pytest fixture)

GOLDEN_DDL_SHA256 = "45ba5ae5ea576a77247ddc0cd0bb70546e29f97d0bc16aaecda9feb8fc315afd"
GOLDEN_TABLES = ["research_artifacts", "research_bundle_approvals", "research_bundle_entities",
                 "research_bundle_raw_variants", "research_bundle_receipts", "research_bundles",
                 "research_entities", "research_entity_reservations", "research_relations"]
GOLDEN_BUNDLE_ID = "901380ffabf03c98a4e50369302f30a744a292222f327cfc574632f310e0a3dd"
GOLDEN_ENTITY_ID = "0b834b5d9d17d37723fb1e760c102e766b92f476767a7ef52c403df78fb1bd50"
SIGNATURES = {
    "approve": "(self, relative, scope)",
    "artifact": "(self, scope, bundle_id, artifact_id)",
    "entity": "(self, scope, bundle_id, entity_id, revision)",
    "evidence": "(self, scope, bundle_id, evidence_id)",
    "grants": "(self, scope, origin, restrictions, generate=False)",
    "ingest": "(self, relative, scope)",
    "materialize": "(self, scope, bundle_id, artifact_id, destination)",
    "orphan_report": "(self)",
    "query": "(self, scope, *, entity_id=None, entity_type=None, revision=None, bundle_id=None, "
             "artifact_id=None, evidence_id=None, relation_type=None, domain=None, status=None, "
             "limit=20, offset=0, generate=False, _db=None)",
    "receipts": "(self, scope)",
    "resource_allowed": "(artifact, grants)",
    "verify": "(self, scope, rebuild=False)",
}
RECEIPT_KEYS = ["attempt_id", "bundle_id", "contract", "entities", "error", "raw_manifest_sha256",
                "raw_preserved", "received_bytes", "received_objects", "references", "resources", "status"]
QUERY_KEYS = ["artifact_total", "artifacts", "classification", "coverage", "entities", "evidence",
              "evidence_total", "relation_total", "relations", "total"]


def test_module_exports_and_public_methods_are_stable():
    assert callable(bundles.validate_grants)
    assert str(inspect.signature(bundles.validate_grants)) == "(grants)"
    public = {n for n, v in inspect.getmembers(bundles.BundleService) if not n.startswith("_") and callable(v)}
    assert public == set(SIGNATURES)
    for name, expected in SIGNATURES.items():
        assert str(inspect.signature(getattr(bundles.BundleService, name))) == expected, name
    assert isinstance(inspect.getattr_static(bundles.BundleService, "resource_allowed"), staticmethod)


def test_schema_receipt_and_query_shapes_are_unchanged(setup):  # noqa: F811
    store, scope, bundle, _, policy_path, _ = setup
    with sqlite3.connect(store.service.path) as db:
        ddl = "\n".join(r[0] for r in db.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name LIKE 'research_%' "
            "AND name NOT IN ('research_filter') ORDER BY name"))
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'research_%' ORDER BY name")]
    assert tables == GOLDEN_TABLES
    assert hashlib.sha256(ddl.encode()).hexdigest() == GOLDEN_DDL_SHA256
    assert bundle["bundle_id"] == GOLDEN_BUNDLE_ID
    receipt = store.ingest("one/bundle.json", scope)
    assert sorted(receipt) == RECEIPT_KEYS and receipt["status"] == "admitted"
    result = store.query(scope)
    assert sorted(result) == QUERY_KEYS
    assert result["entities"][0]["id"] == GOLDEN_ENTITY_ID
    assert store.verify(scope) == {"status": "verified", "bundles": 1, "rebuilt": False}


def test_policy_v3_still_validates_bundle_grants_through_bundles(setup, tmp_path):  # noqa: F811
    store, _, _, _, policy_path, policy = setup
    assert store.service.policy()["version"] == 3
    broken = {**policy, "bundle_grants": [{**policy["bundle_grants"][0], "roles": "document"}]}
    from research_bundle import canonical
    (tmp_path / "broken.json").write_bytes(canonical(broken))
    try:
        ResearchService(tmp_path / "other.db", tmp_path / "broken.json")
    except ValueError as exc:
        assert "bundle grant list" in str(exc)
    else:
        raise AssertionError("invalid bundle grants must be rejected")

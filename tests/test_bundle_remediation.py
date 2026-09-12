"""Adversarial regressions: actual service boundaries, no implicit approval."""

import copy

import pytest

from research_bundle import canonical, digest, seal, validate
import test_research_bundle


@pytest.fixture
def setup(tmp_path):
    return test_research_bundle.setup.__wrapped__(tmp_path)


@pytest.mark.parametrize("hidden", [False, True])
def test_unapproved_guess_indistinguishable(setup, hidden, monkeypatch):
    from contextlib import contextmanager

    s, scope, b, root, path, policy = setup
    if hidden:
        s.ingest("one/bundle.json", scope)
    other = s.service.scope("test", None, "b")
    g = copy.deepcopy(policy["bundle_grants"][0])
    g["collection"] = "b"
    policy["bundle_grants"].append(g)
    policy["imports"].append(dict(user="test", project="", collection="b", root=str(root)))
    path.write_bytes(canonical(policy))
    b["entities"][0]["payload"] = {"guess": True}
    (root / "one/bundle.json").write_bytes(canonical(seal(b)))
    connection = s.service.connection
    statements = []

    @contextmanager
    def traced():
        with connection() as db:
            db.set_trace_callback(statements.append)
            yield db

    monkeypatch.setattr(s.service, "connection", traced)
    with pytest.raises(PermissionError, match="^NOT_AUTHORIZED$"):
        s.ingest("one/bundle.json", other)
    assert not any(
        "research_entities" in sql or "research_entity_reservations" in sql for sql in statements
    )
    assert s.query(other)["total"] == 0
    assert s.receipts(other)[0]["error"] == "NOT_AUTHORIZED"


def test_admin_reservation_precedes_membership(setup):
    s, scope, b, root, _, _ = setup
    assert s.query(scope)["total"] == 0
    b["entities"][0]["payload"] = {"different": True}
    (root / "one/bundle.json").write_bytes(canonical(seal(b)))
    with pytest.raises(ValueError, match="^CONFLICT$"):
        s.approve("one/bundle.json", scope)
    assert s.query(scope)["total"] == 0


@pytest.mark.parametrize("rebuild", [False, True])
@pytest.mark.parametrize("revoke", ["role", "bundle", "reference"])
def test_verify_denies_entire_scope_before_object_io(setup, monkeypatch, rebuild, revoke):
    s, scope, b, root, path, policy = setup
    if revoke == "reference":
        b["artifacts"].append(
            dict(
                b["artifacts"][0],
                artifact_id="ref",
                availability="reference_only",
                relative_path=None,
                locator="opaque",
            )
        )
        b = seal(b)
        (root / "one/bundle.json").write_bytes(canonical(b))
        s.approve("one/bundle.json", scope)
    s.ingest("one/bundle.json", scope)
    if revoke == "role":
        policy["bundle_grants"][0]["roles"] = []
    elif revoke == "bundle":
        policy["bundle_grants"] = []
    else:
        policy["bundle_grants"][0]["reference_only"] = False
    path.write_bytes(canonical(policy))
    monkeypatch.setattr(s.objects, "verify", lambda *a: pytest.fail("Protected object I/O"))
    with pytest.raises(PermissionError, match="NOT_AUTHORIZED"):
        s.verify(scope, rebuild=rebuild)


@pytest.mark.parametrize("profile", ["local-research/1", "local-research/2"])
def test_external_is_not_role_permission(setup, profile):
    import argparse
    import threading
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from cain.research.api import mount
    from cain.research.cli import register, execute
    from cain.research.historian import metadata_context

    s, scope, b, root, path, policy = setup
    b["profile"] = profile
    ep = b["relations"][0]["target"]
    ep["external"] = True
    if profile.endswith("/2"):
        ep["revision"] = digest(canonical(b["artifacts"][0]))
    b = seal(b)
    validate(b)
    (root / "one/bundle.json").write_bytes(canonical(b))
    s.approve("one/bundle.json", scope)
    s.ingest("one/bundle.json", scope)
    assert s.query(scope)["relation_total"] == 1
    policy["bundle_grants"][0]["roles"] = []
    path.write_bytes(canonical(policy))
    assert s.query(scope)["relation_total"] == 0
    assert metadata_context(s.service, scope)["bundles"]["relation_total"] == 0
    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(
        [
            "research",
            "--db",
            str(s.service.path),
            "--policy",
            str(path),
            "--user",
            "test",
            "--collection",
            "a",
            "bundle",
            "lineage",
        ]
    )
    assert execute(args)["total"] == 0
    app = FastAPI()
    mount(
        app,
        root.parent / "workspace.db",
        lambda *a: None,
        lambda: None,
        threading.Lock(),
        policy_path=path,
        research_path=s.service.path,
    )
    client = TestClient(app)
    request = dict(user_id="test", collection="a")
    assert client.post("/research/bundles/lineage", json=request).json()["total"] == 0
    assert (
        client.post("/research/bundles/historian", json=request).json()["bundles"]["relation_total"]
        == 0
    )
    assert client.post("/research/bundles/approve", json=request).status_code == 404


def test_descriptor_revision_disambiguates_and_unresolved_hidden(setup):
    s, scope, b, root, _, _ = setup
    b["profile"] = "local-research/2"
    ep = b["relations"][0]["target"]
    ep.update(external=True, revision=digest(canonical(b["artifacts"][0])))
    b["artifacts"][0]["metadata"] = {"different": True}
    assert ep["revision"] != digest(canonical(b["artifacts"][0]))
    b = seal(b)
    (root / "one/bundle.json").write_bytes(canonical(b))
    s.approve("one/bundle.json", scope)
    s.ingest("one/bundle.json", scope)
    assert s.query(scope)["relation_total"] == 0


def test_directory_sync_failure_prevents_metadata_commit(setup, monkeypatch):
    from research_bundle import files

    s, scope, _, _, _, _ = setup

    def fail(parent):
        raise OSError("injected directory fsync failure")

    monkeypatch.setattr(files, "fsync_dir", fail)
    with pytest.raises(OSError, match="fsync"):
        s.ingest("one/bundle.json", scope)
    assert s.query(scope)["total"] == 0


@pytest.mark.parametrize("damage", [None, "missing", "corrupt"])
def test_raw_variants_backup_integrity(setup, tmp_path, damage):
    import json
    from cain.archive import backup, restore
    from cain.workspace import WorkspaceStore
    from cain.research.bundle_backup import reachables

    s, scope, b, root, path, _ = setup
    first = (root / "one/bundle.json").read_bytes()
    s.ingest("one/bundle.json", scope)
    second = json.dumps(b, indent=3).encode()
    (root / "one/bundle.json").write_bytes(second)
    receipt = s.ingest("one/bundle.json", scope)
    assert receipt["status"] == "duplicate" and receipt["raw_preserved"]
    with s.service.connection() as db:
        assert db.execute("SELECT raw FROM research_bundles").fetchone()[0] == first
        assert db.execute("SELECT raw FROM research_bundle_raw_variants").fetchone()[0] == second
        if damage == "missing":
            db.execute("DELETE FROM research_bundle_raw_variants")
        elif damage == "corrupt":
            db.execute("UPDATE research_bundle_raw_variants SET raw=?", (b"{}",))
    if damage:
        with pytest.raises(ValueError, match="CORRUPTION"):
            s.verify(scope)
        with pytest.raises(ValueError, match="CORRUPTION"):
            reachables(s.service.path)
    else:
        s.verify(scope, rebuild=True)
        w = WorkspaceStore(tmp_path / "workspace.db")
        backup(w.path, s.service.path, path, tmp_path / "backup")
        restore(tmp_path / "backup", tmp_path / "restored")
        import sqlite3

        with sqlite3.connect(tmp_path / "restored/research.db") as db:
            assert (
                db.execute("SELECT raw FROM research_bundle_raw_variants").fetchone()[0] == second
            )


def test_raw_variant_quota_does_not_change_first_raw(setup):
    s, scope, b, root, _, _ = setup
    first = canonical(b)
    s.ingest("one/bundle.json", scope)
    for n in range(1, 8):
        (root / "one/bundle.json").write_bytes(first + b" " * n)
        s.ingest("one/bundle.json", scope)
    (root / "one/bundle.json").write_bytes(first + b" " * 8)
    with pytest.raises(ValueError, match="RAW_VARIANT_LIMIT"):
        s.ingest("one/bundle.json", scope)
    with s.service.connection() as db:
        assert db.execute("SELECT raw FROM research_bundles").fetchone()[0] == first
        assert db.execute("SELECT count(*) FROM research_bundle_raw_variants").fetchone()[0] == 7
    s.verify(scope)


def test_evidence_only_fact_retrievable_and_revoked(setup, monkeypatch):
    import argparse
    import threading
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from cain.research.api import mount
    from cain.research.cli import register, execute
    from cain.research.historian import metadata_context, explain_metadata

    s, scope, b, root, path, policy = setup
    b["evidence"] = [
        dict(
            id="e1",
            source="report.json",
            locator="line:1",
            payload={"only_fact": "UNKNOWN remains UNKNOWN"},
        )
    ]
    b["entities"][0].update(revision="2", evidence_ids=["e1"])
    b["relations"][0]["source"]["revision"] = "2"
    b = seal(b)
    (root / "one/bundle.json").write_bytes(canonical(b))
    s.approve("one/bundle.json", scope)
    s.ingest("one/bundle.json", scope)
    monkeypatch.setattr(s.objects, "verify", lambda *a: pytest.fail("Metadata must not read CAS"))
    assert (
        s.evidence(scope, b["bundle_id"], "e1")["evidence"]["payload"]["only_fact"]
        == "UNKNOWN remains UNKNOWN"
    )
    assert s.entity(scope, b["bundle_id"], "TEST-HYPOTHESIS-001", "2")["evidence_total"] == 1
    assert s.query(scope, limit=1, offset=1)["evidence"] == []
    assert metadata_context(s.service, scope)["bundles"]["evidence"][0]["id"] == "e1"

    class Provider:
        def generate_json(self, prompt, instruction, schema):
            ref = next(
                r
                for r in schema["properties"]["claims"]["items"]["properties"]["evidence_id"][
                    "enum"
                ]
                if r.startswith("evidence:")
            )
            return canonical(
                dict(claims=[dict(evidence_id=ref, quote="UNKNOWN remains UNKNOWN")], synthesis="")
            ).decode()

    assert explain_metadata(s.service, scope, "Evidence?", Provider())["source_quotes"]
    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(
        [
            "research",
            "--db",
            str(s.service.path),
            "--policy",
            str(path),
            "--user",
            "test",
            "--collection",
            "a",
            "bundle",
            "evidence",
            b["bundle_id"],
            "e1",
        ]
    )
    assert execute(args)["evidence"]["id"] == "e1"
    app = FastAPI()
    mount(
        app,
        root.parent / "workspace.db",
        lambda *a: None,
        lambda: None,
        threading.Lock(),
        policy_path=path,
        research_path=s.service.path,
    )
    client = TestClient(app)
    assert (
        client.post(
            "/research/bundles/evidence",
            json=dict(user_id="test", collection="a", bundle_id=b["bundle_id"], evidence_id="e1"),
        ).json()["evidence"]["id"]
        == "e1"
    )
    policy["bundle_grants"] = []
    path.write_bytes(canonical(policy))
    assert s.query(scope)["evidence_total"] == 0
    with pytest.raises(ValueError, match="NOT_FOUND"):
        s.evidence(scope, b["bundle_id"], "e1")


def test_concurrent_administrative_conflicts_are_atomic(setup):
    from concurrent.futures import ThreadPoolExecutor
    from cain.research.bundle_backup import reachables

    s, scope, b, root, _, _ = setup
    for index in range(2):
        package = copy.deepcopy(b)
        package["entities"][0].update(revision="concurrent", payload={"value": index})
        package["relations"][0]["source"]["revision"] = "concurrent"
        (root / (str(index) + ".json")).write_bytes(canonical(seal(package)))

    def attempt(index):
        try:
            return s.approve(str(index) + ".json", scope)["status"]
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["CONFLICT", "approved"]
    assert s.query(scope)["total"] == 0
    assert reachables(s.service.path) == {}


@pytest.mark.parametrize("damage", ["approval", "reservation"])
def test_backup_checks_administrative_ledger(setup, damage):
    from cain.research.bundle_backup import reachables

    s, scope, _, _, _, _ = setup
    with s.service.connection() as db:
        if damage == "approval":
            db.execute("UPDATE research_bundle_approvals SET id=?", ("0" * 64,))
        else:
            db.execute("DELETE FROM research_entity_reservations")
    with pytest.raises(ValueError, match="CORRUPTION"):
        reachables(s.service.path)

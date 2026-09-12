import copy
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from research_bundle import canonical, digest, endpoint, seal
from cain.research import ResearchService
from cain.research.bundles import BundleService


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "imports"
    (root / "one" / "files").mkdir(parents=True)
    raw = b"real test bytes"
    (root / "one/files/report.txt").write_bytes(raw)
    origin = dict(
        domain="test",
        repository="test/repo",
        publisher="test",
        stream="test",
        code_revision="code",
        exporter_revision="exporter",
        inputs={"report.json": "0" * 64},
    )
    b = seal(
        dict(
            contract="ResearchBundleV1",
            profile="local-research/1",
            origin=origin,
            exported_at="2026-09-11T00:00:00Z",
            restrictions=dict(policy="test/1", read=True, disclose=False, generate=True),
            coverage=dict(
                scope="test",
                completeness="partial",
                included=["report.json"],
                missing=[],
                excluded=[],
                limitations=[],
            ),
            entities=[
                dict(
                    entity_id="TEST-HYPOTHESIS-001",
                    revision="1",
                    entity_type="hypothesis",
                    identity_basis="source_assigned",
                    status="UNKNOWN",
                    status_axis="scientific",
                    event_at=None,
                    recorded_at=None,
                    available_at=None,
                    payload={"sql": "'); DROP TABLE records; --"},
                    supersedes=[],
                    evidence_ids=[],
                )
            ],
            evidence=[],
            artifacts=[
                dict(
                    artifact_id="a1",
                    role="document",
                    availability="received",
                    media_type="text/plain",
                    sha256=digest(raw),
                    size=len(raw),
                    relative_path="files/report.txt",
                    locator=None,
                    logical_name="report",
                    metadata={},
                )
            ],
            relations=[
                dict(
                    relation_id="r1",
                    type="SUPPORTED_BY",
                    source=endpoint("entity", origin, "TEST-HYPOTHESIS-001", "1"),
                    target=endpoint("artifact", origin, "a1"),
                )
            ],
        )
    )
    (root / "one/bundle.json").write_bytes(canonical(b))
    g = dict(
        user="test",
        project="",
        collection="a",
        domain="test",
        repository="test/repo",
        publisher="test",
        stream="test",
        sources=["report.json"],
        policies=["test/1"],
        generate=True,
        roles=["document"],
        reference_only=True,
        max_manifest_bytes=2_000_000,
        max_object_bytes=16_000_000,
        max_received_bytes=64_000_000,
    )
    policy = dict(
        version=3,
        imports=[dict(user="test", project="", collection="a", root=str(root))],
        grants=[],
        bundle_grants=[g],
    )
    path = tmp_path / "policy.json"
    path.write_bytes(canonical(policy))
    service = ResearchService(tmp_path / "research.db", path)
    store = BundleService(service)
    store.approve("one/bundle.json", service.scope("test", None, "a"))
    return store, service.scope("test", None, "a"), b, root, path, policy


def test_roundtrip_duplicate_and_offline(setup, tmp_path):
    s, scope, b, root, _, _ = setup
    assert s.ingest("one/bundle.json", scope)["status"] == "admitted"
    assert s.ingest("one/bundle.json", scope)["status"] == "duplicate"
    assert s.query(scope)["total"] == 1
    assert s.verify(scope)["bundles"] == 1
    root.rename(root.with_name("unavailable"))
    dest = tmp_path / "copy"
    assert s.materialize(scope, b["bundle_id"], "a1", dest)["bytes"] == 15
    assert dest.read_bytes() == b"real test bytes"
    with pytest.raises(FileExistsError):
        s.materialize(scope, b["bundle_id"], "a1", dest)
    assert s.verify(scope, rebuild=True)["rebuilt"]


def test_scopes_and_revocation(setup, tmp_path):
    s, scope, b, _, path, policy = setup
    s.ingest("one/bundle.json", scope)
    other = s.service.scope("test", None, "b")
    assert s.query(other)["total"] == 0
    with pytest.raises(ValueError, match="NOT_FOUND"):
        s.materialize(other, b["bundle_id"], "a1", tmp_path / "denied")
    policy["bundle_grants"][0]["roles"] = []
    path.write_bytes(canonical(policy))
    result = s.query(scope)
    assert result["total"] == 1 and result["artifacts"] == [] and result["relations"] == []
    with pytest.raises(ValueError, match="NOT_FOUND"):
        s.materialize(scope, b["bundle_id"], "a1", tmp_path / "denied")
    policy["bundle_grants"] = []
    path.write_bytes(canonical(policy))
    assert s.query(scope)["total"] == 0
    assert s.objects.inventory()[0] == [b["artifacts"][0]["sha256"]]


def test_dedupe_independent_memberships(setup):
    s, scope, b, root, path, policy = setup
    s.ingest("one/bundle.json", scope)
    second = copy.deepcopy(policy["bundle_grants"][0])
    second["collection"] = "b"
    policy["bundle_grants"].append(second)
    policy["imports"].append(dict(user="test", project="", collection="b", root=str(root)))
    path.write_bytes(canonical(policy))
    other = s.service.scope("test", None, "b")
    s.approve("one/bundle.json", other)
    s.ingest("one/bundle.json", other)
    policy["bundle_grants"].pop(0)
    path.write_bytes(canonical(policy))
    assert s.query(scope)["total"] == 0
    assert s.query(other)["total"] == 1
    assert len(s.objects.inventory()[0]) == 1


@pytest.mark.parametrize("mode", ["missing", "truncated", "corrupt"])
def test_cas_corruption(setup, mode):
    s, scope, b, _, _, _ = setup
    s.ingest("one/bundle.json", scope)
    target = s.objects.root / s.objects.relative(b["artifacts"][0]["sha256"])
    if mode == "missing":
        target.unlink()
    if mode == "truncated":
        target.write_bytes(b"x")
    if mode == "corrupt":
        target.write_bytes(b"x" * 15)
    with pytest.raises(ValueError, match="CORRUPTION"):
        s.verify(scope)
    with pytest.raises(ValueError, match="CORRUPTION"):
        s.verify(scope, rebuild=True)


def test_rebuild_projection(setup):
    s, scope, _, _, _, _ = setup
    s.ingest("one/bundle.json", scope)
    with s.service.connection() as db:
        db.execute("UPDATE research_entities SET status='WRONG'")
    with pytest.raises(ValueError, match="CORRUPTION"):
        s.query(scope)
    s.verify(scope, rebuild=True)
    assert s.query(scope)["entities"][0]["status"] == "UNKNOWN"


def test_conflict_atomicity_and_orphan(setup, monkeypatch):
    s, scope, b, root, _, _ = setup
    original = s._project
    monkeypatch.setattr(s, "_project", lambda *a: (_ for _ in ()).throw(ValueError("DB_FAILED")))
    with pytest.raises(ValueError):
        s.ingest("one/bundle.json", scope)
    assert s.query(scope)["total"] == 0
    assert len(s.orphan_report()["orphans"]) == 1
    monkeypatch.setattr(s, "_project", original)
    s.ingest("one/bundle.json", scope)
    assert not s.orphan_report()["orphans"]
    b["entities"][0]["status"] = "DIFFERENT"
    (root / "one/bundle.json").write_bytes(canonical(seal(b)))
    with pytest.raises(ValueError, match="CONFLICT"):
        s.approve("one/bundle.json", scope)
    assert s.query(scope)["entities"][0]["status"] == "UNKNOWN"


def test_concurrent(setup):
    s, scope, _, _, _, _ = setup
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: s.ingest("one/bundle.json", scope)["status"], range(2))
        )
    assert sorted(results) == ["admitted", "duplicate"]


def test_legacy_denied_before_artifact_open(setup):
    s, scope, _, root, path, policy = setup
    policy["version"] = 2
    del policy["bundle_grants"]
    path.write_bytes(canonical(policy))
    (root / "one/files/report.txt").unlink()
    with pytest.raises(PermissionError):
        s.ingest("one/bundle.json", scope)


def test_reference_no_io(setup, tmp_path):
    s, scope, b, root, _, _ = setup
    b["artifacts"][0].update(
        availability="reference_only",
        relative_path=None,
        locator="https://127.0.0.1/never-fetch",
        sha256=None,
        size=None,
    )
    b = seal(b)
    (root / "one/files/report.txt").unlink()
    (root / "one/bundle.json").write_bytes(canonical(b))
    s.approve("one/bundle.json", scope)
    s.ingest("one/bundle.json", scope)
    assert s.verify(scope)["bundles"] == 1
    with pytest.raises(ValueError, match="REFERENCE_ONLY"):
        s.materialize(scope, b["bundle_id"], "a1", tmp_path / "no")
    assert not s.objects.inventory()[0]


@pytest.mark.parametrize(
    "field,value", [("max_received_bytes", 0), ("max_object_bytes", 0), ("max_manifest_bytes", 1)]
)
def test_policy_caps_before_copy(setup, field, value):
    s, scope, _, root, path, policy = setup
    policy["bundle_grants"][0][field] = value
    path.write_bytes(canonical(policy))
    (root / "one/files/report.txt").unlink()
    with pytest.raises(PermissionError):
        s.ingest("one/bundle.json", scope)


def test_junction_rejected(setup, tmp_path):
    import os
    import subprocess

    s, scope, _, root, _, _ = setup
    target = root / "one/files"
    target.rename(root / "one/original")
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(root / "one/original")],
            check=True,
            capture_output=True,
        )
    else:
        target.symlink_to(root / "one/original", target_is_directory=True)
    with pytest.raises(ValueError, match="UNSAFE_PATH"):
        s.ingest("one/bundle.json", scope)


@pytest.mark.parametrize("mode", ["received", "reference", "zero", "old"])
def test_backup_restore(setup, tmp_path, mode):
    from cain.archive import backup, restore
    from cain.workspace import WorkspaceStore

    s, scope, b, root, policy, _ = setup
    if mode == "reference":
        b["artifacts"][0].update(
            availability="reference_only",
            relative_path=None,
            locator="opaque",
            sha256=None,
            size=None,
        )
        b = seal(b)
        (root / "one/bundle.json").write_bytes(canonical(b))
    if mode in {"received", "reference"}:
        s.approve("one/bundle.json", scope)
        s.ingest("one/bundle.json", scope)
    workspace = WorkspaceStore(tmp_path / "workspace.db")
    backup_dir = tmp_path / "backup"
    backup(workspace.path, s.service.path, policy, backup_dir)
    if mode == "old":
        m = json.loads((backup_dir / "manifest.json").read_bytes())
        m["version"] = 1
        del m["objects"]
        (backup_dir / "manifest.json").write_bytes(canonical(m))
    destination = tmp_path / "restored"
    restore(backup_dir, destination)
    root.rename(tmp_path / "producer_unavailable")
    recovered = BundleService(
        ResearchService(destination / "research.db", destination / "policy.json")
    )
    assert recovered.verify(scope)["bundles"] == (1 if mode in {"received", "reference"} else 0)
    if mode == "received":
        recovered.materialize(scope, b["bundle_id"], "a1", tmp_path / "offline")
        assert (tmp_path / "offline").read_bytes() == b"real test bytes"
        with pytest.raises(ValueError):
            s.service.backup(tmp_path / "metadata-only.db")


@pytest.mark.parametrize("attack", ["corrupt", "missing", "manifest", "policy"])
def test_bad_backup_never_complete(setup, tmp_path, attack):
    from cain.archive import backup, restore
    from cain.workspace import WorkspaceStore

    s, scope, b, _, policy, _ = setup
    s.ingest("one/bundle.json", scope)
    workspace = WorkspaceStore(tmp_path / "workspace.db")
    directory = tmp_path / "backup"
    backup(workspace.path, s.service.path, policy, directory)
    blob = directory / "research-objects" / s.objects.relative(b["artifacts"][0]["sha256"])
    if attack == "corrupt":
        blob.write_bytes(b"corrupt")
    if attack == "missing":
        blob.unlink()
    if attack == "policy":
        (directory / "policy.json").write_bytes(b"{}")
    if attack == "manifest":
        manifest = json.loads((directory / "manifest.json").read_bytes())
        manifest["objects"] = {}
        (directory / "manifest.json").write_bytes(canonical(manifest))
    with pytest.raises((ValueError, OSError)):
        restore(directory, tmp_path / "bad")
    assert not (tmp_path / "bad/RESTORE_COMPLETE.json").exists()


def test_historian_metadata_no_object_io(setup, monkeypatch):
    from cain.research.historian import metadata_context

    s, scope, _, _, policy_path, policy = setup
    s.ingest("one/bundle.json", scope)
    monkeypatch.setattr(
        s.objects, "verify", lambda *a: pytest.fail("No artifact open in Historian")
    )
    result = metadata_context(s.service, scope, bundles=s)
    assert not result["artifact_content_included"]
    assert result["bundles"]["total"] == 1
    policy["bundle_grants"] = []
    policy_path.write_bytes(canonical(policy))
    assert metadata_context(s.service, scope, bundles=s)["bundles"]["total"] == 0
    assert s.receipts(scope) == []


def test_missing_received_rejected_without_projection(setup):
    s, scope, _, root, _, _ = setup
    (root / "one/files/report.txt").unlink()
    with pytest.raises(OSError):
        s.ingest("one/bundle.json", scope)
    assert s.query(scope)["total"] == 0


def test_staging_leftovers_reported_not_deleted(setup):
    s, scope, b, _, _, _ = setup
    s.ingest("one/bundle.json", scope)
    staged = (s.objects.root / s.objects.relative(b["artifacts"][0]["sha256"])).with_name(
        ".staging-interrupted"
    )
    staged.write_bytes(b"partial")
    report = s.orphan_report()
    assert len(report["temporary"]) == 1
    assert staged.exists()


def test_cli_api_same_scope_service(setup, tmp_path):
    import argparse
    import threading
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from cain.research.api import mount
    from cain.research.cli import register, execute

    s, scope, _, _, policy, _ = setup
    s.ingest("one/bundle.json", scope)
    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(
        [
            "research",
            "--db",
            str(s.service.path),
            "--policy",
            str(policy),
            "--user",
            "test",
            "--collection",
            "a",
            "bundle",
            "query",
        ]
    )
    assert execute(args)["total"] == 1
    app = FastAPI()
    mount(
        app,
        tmp_path / "workspace.db",
        lambda *a: None,
        lambda: None,
        threading.Lock(),
        policy_path=policy,
        research_path=s.service.path,
    )
    client = TestClient(app)
    request = dict(user_id="test", collection="a")
    assert client.post("/research/bundles/query", json=request).json()["total"] == 1
    assert client.post("/research/bundles/artifacts", json=request).json()["total"] == 1
    assert client.post("/research/bundles/lineage", json=request).json()["total"] == 1
    package = s.query(scope)["entities"][0]
    detail = dict(request, bundle_id=package["bundles"][0], entity_id=package["entity_id"], revision=package["revision"])
    assert client.post("/research/bundles/entity", json=detail).json()["total"] == 1
    resource = dict(request, bundle_id=package["bundles"][0], artifact_id="a1")
    assert client.post("/research/bundles/artifact", json=resource).json()["artifact"]["artifact_id"] == "a1"
    assert client.post("/research/bundles/entity", json=request).status_code == 422
    assert client.post("/research/bundles/query", json=dict(request, domain="absent")).json()["artifact_total"] == 0

    assert (
        client.post("/research/bundles/query", json=dict(user_id="test", collection="b")).json()[
            "total"
        ]
        == 0
    )
    assert (
        client.post("/research/bundles/query", json={**request, "path": "/arbitrary"}).status_code
        == 422
    )


def test_new_tables_legacy_snapshot_read(setup, tmp_path):
    from integration.test_research_l0 import publication

    s, scope, _, root, path, policy = setup
    s.ingest("one/bundle.json", scope)
    snapshot = publication(ids=("TEST-LEGACY-001",), domain="crypto")
    grant = dict(
        user="test",
        project="",
        collection="a",
        domain="crypto",
        repository="fixture://crypto",
        publisher="fixture",
        stream="synthetic",
        sources=["report.md"],
        policies=["fixture/1"],
        generate=False,
    )
    policy["grants"] = [grant]
    path.write_bytes(canonical(policy))
    (root / "snapshot.json").write_bytes(canonical(snapshot))
    s.service.ingest("snapshot.json", scope)
    assert s.service.query(scope)["total_record_revisions"] == 1
    assert s.query(scope)["total"] == 1
    # Original executable service source, copied verbatim from the baseline commit.
    import subprocess
    import types

    historic = subprocess.run(
        ["git", "show", "780b020:src/cain/research/service.py"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
    )
    if historic.returncode:
        pytest.skip("Historical baseline absent from shallow checkout; run with full history")
    raw = historic.stdout
    legacy = types.ModuleType("legacy_service")
    exec(compile(raw, "baseline-service.py", "exec"), legacy.__dict__)
    policy["version"] = 2
    del policy["bundle_grants"]
    path.write_bytes(canonical(policy))
    old = legacy.ResearchService(s.service.path, path)
    assert old.query(scope)["total_record_revisions"] == 1


def test_detail_filters_keep_metadata_selection_scoped(setup):
    s, scope, b, _, _, _ = setup
    s.ingest("one/bundle.json", scope)
    assert s.entity(scope, b["bundle_id"], "TEST-HYPOTHESIS-001", "1")["relation_total"] == 1
    for filters in (
        {"domain": "absent"},
        {"entity_id": "absent"},
        {"revision": "absent"},
        {"bundle_id": "0" * 64},
    ):
        result = s.query(scope, **filters)
        assert result["total"] == result["artifact_total"] == result["relation_total"] == 0
        assert result["coverage"] == []
    assert s.query(scope, relation_type="USES")["relation_total"] == 0
    assert s.artifact(scope, b["bundle_id"], "a1")["artifact"]["availability"] == "received"
    with pytest.raises(ValueError, match="NOT_FOUND"):
        s.artifact(scope, b["bundle_id"], "absent")


def test_historian_bundle_generation_is_extractive_and_ephemeral(setup, monkeypatch):
    from cain.research.historian import explain_metadata

    s, scope, _, _, _, _ = setup
    s.ingest("one/bundle.json", scope)
    monkeypatch.setattr(s.objects, "materialize", lambda *a: pytest.fail("No object access"))

    class Provider:
        def generate(self, prompt, context):
            evidence = json.loads(prompt)["evidence"]
            ref = next(k for k in evidence if k.startswith("entity:"))
            return json.dumps(
                dict(
                    claims=[dict(evidence_id=ref, quote="TEST-HYPOTHESIS-001")],
                    synthesis="Tentative interpretation",
                )
            )

    result = explain_metadata(s.service, scope, "What is received?", Provider())
    assert result["status"] == "generated"
    assert result["derived"][0]["classification"] == "DERIVED"
    assert result["source_quotes"][0]["classification"] == "FACTUAL"
    assert result["persisted"] is False
    assert s.query(scope)["total"] == 1


def test_historian_bundle_revocation_during_inference_discards_all_output(setup):
    from cain.research.historian import explain_metadata

    s, scope, _, _, path, policy = setup
    s.ingest("one/bundle.json", scope)

    class Provider:
        def generate(self, prompt, context):
            policy["bundle_grants"] = []
            path.write_bytes(canonical(policy))
            return json.dumps(dict(claims=[], synthesis=""))

    result = explain_metadata(s.service, scope, "What is received?", Provider())
    assert result["status"] == "generation_failed"
    assert result["facts"]["bundles"]["total"] == 0
    assert result["derived"] == []


def test_historian_denies_ungranted_generation_and_remote_provider(setup):
    from cain.research.historian import explain_metadata

    s, scope, _, _, path, policy = setup
    s.ingest("one/bundle.json", scope)
    policy["bundle_grants"][0]["generate"] = False
    path.write_bytes(canonical(policy))

    class Provider:
        def generate(self, *a, **kw):
            pytest.fail("Generation forbidden")

    assert explain_metadata(s.service, scope, "Question", Provider())["status"].startswith(
        "abstained"
    )
    provider = Provider()
    provider.base_url = "https://example.invalid"
    with pytest.raises(ValueError, match="local providers"):
        explain_metadata(s.service, scope, "Question", provider)


@pytest.mark.parametrize("stage", ["promotion", "projection"])
def test_process_death_leaves_no_false_received_record_and_retry_recovers(setup, stage):
    import os
    import subprocess
    import sys
    s, scope, _, _, policy_path, _ = setup
    injection = (
        "import cain.research.objects as objects; objects.os.link = lambda *a, **k: os._exit(91)"
        if stage == "promotion" else
        "BundleService._project = lambda *a, **k: os._exit(91)"
    )
    program = (
        "import os,sys; from cain.research import ResearchService; "
        "from cain.research.bundles import BundleService; " + injection + "; "
        "BundleService(ResearchService(sys.argv[1],sys.argv[2])).ingest('one/bundle.json',sys.argv[3])"
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    child = subprocess.run([sys.executable, "-c", program, str(s.service.path), str(policy_path), scope],
                           env=env, capture_output=True, timeout=30)
    assert child.returncode == 91, child.stderr.decode(errors="replace")
    assert s.query(scope)["total"] == 0
    report = s.orphan_report()
    assert report["temporary" if stage == "promotion" else "orphans"]
    assert s.ingest("one/bundle.json", scope)["status"] == "admitted"
    assert s.verify(scope)["bundles"] == 1
    assert s.orphan_report()["orphans"] == []


def test_disk_full_copy_failure_cleans_stage_without_metadata(setup, monkeypatch):
    import errno
    import cain.research.objects as objects
    s, scope, _, _, _, _ = setup

    def disk_full(*args, **kwargs):
        raise OSError(errno.ENOSPC, "Injected disk full")

    monkeypatch.setattr(objects, "transfer", disk_full)
    with pytest.raises(OSError):
        s.ingest("one/bundle.json", scope)
    assert s.query(scope)["total"] == 0
    assert s.orphan_report()["temporary"] == []

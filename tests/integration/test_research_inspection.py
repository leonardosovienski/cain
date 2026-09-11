"""Adversarial inspection acceptance cases, specified before implementation."""

import json

from fastapi.testclient import TestClient
import pytest
from research_snapshot import canonical

from cain.api import create_app
from cain.cli import main
from cain.research.inspection import inspect
import test_research_l0 as cases

setup = cases.setup


def test_namespaces_supersession_and_comparison(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("A",), revision="1"))
    newer = cases.publication(("A",), revision="2", text="Nova revisão / new revision")
    newer["records"][0].update(source_status="REVIEW", supersedes=["1", "missing"])
    ingest(cases.reseal(newer))
    ingest(cases.publication(("A",), domain="stocks", revision="1"))
    result = inspect(service, scope, source_id="A", before="1", after="2")
    assert result["metrics"]["record_revisions"] == 3
    assert result["metrics"]["source_occurrences"] == 2
    relation = [e for e in result["graph"]["edges"]
                if e["relation"] == "source_declared_supersedes"]
    assert len(relation) == 1
    target = next(r for r in result["records"] if "record:" + r["id"] == relation[0]["to"])
    assert target["namespace"][0] == "crypto"
    assert result["comparisons"][0]["changes"]["source_status"] == {"before": "FAILED", "after": "REVIEW"}
    assert "evidence_support" in result["comparisons"][0]["changes"]
    codes = {f["code"] for f in result["findings"]}
    assert {"superseded_revision_not_received", "status_variation", "coexisting_revisions"} <= codes
    assert result["graph"]["inferred_edges"] == 0
    with pytest.raises(ValueError, match="unavailable"):
        inspect(service, scope, source_id="absent", before="1", after="2")
    with pytest.raises(ValueError, match="both"):
        inspect(service, scope, source_id="A", before="1")


def test_cycle_and_timezone_order_without_invented_dates(setup):
    service, scope, ingest, _, _ = setup
    for revision, previous, event in (("1", "2", "2026-09-11T01:00:00+02:00"),
                                      ("2", "1", "2026-09-10T23:30:00Z")):
        package = cases.publication(("A",), revision=revision)
        package["records"][0].update(supersedes=[previous], event_at=event)
        ingest(cases.reseal(package))
    result = inspect(service, scope)
    assert any(f["code"] == "supersession_cycle_or_dependency" for f in result["findings"])
    events = [e["at"] for e in result["timeline"]["dated"] if e["field"] == "event_at"]
    assert events == ["2026-09-11T01:00:00+02:00", "2026-09-10T23:30:00Z"]
    assert len(result["timeline"]["unknown"]) == 4


def test_policy_revocation_scope_and_no_history_write(setup, monkeypatch):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(text="Segredo / secret"))
    assert not service.history(scope)
    assert inspect(service, scope)["metrics"]["record_revisions"] == 2
    assert not service.history(scope)
    for isolated in (service.scope(user="other"), service.scope(project="project-a"),
                     service.scope(collection="other")):
        result = inspect(service, isolated)
        assert result["records"] == []
        assert "Segredo" not in json.dumps(result)
    original = service._verify_projection

    def revoke(*args):
        original(*args)
        policy["grants"] = []
        path.write_bytes(canonical(policy))

    monkeypatch.setattr(service, "_verify_projection", revoke)
    with pytest.raises(ValueError, match="Policy changed"):
        inspect(service, scope)
    monkeypatch.setattr(service, "_verify_projection", original)
    assert "Segredo" not in json.dumps(inspect(service, scope))


def test_api_and_cli_offline(setup, tmp_path, capsys):
    service, scope, ingest, _, path = setup
    ingest(cases.publication(("PT-EN",), text="Relato preservado / preserved report"))
    for file in (path.parent / "inbox").iterdir():
        file.unlink()
    with TestClient(create_app(tmp_path / "workspace.db", llm=cases.ExplodingProvider(),
                              research_policy=path, research_db=service.path)) as client:
        response = client.post("/research/inspect", json={"source_id": "PT-EN"})
        assert response.status_code == 200
        assert response.json()["diagnostics"]["model_calls"] == 0
        assert response.json()["evidence"][0]["text"] == "Relato preservado / preserved report"
        assert client.post("/research/inspect", json={"session_id": "extra"}).status_code == 422
    assert main(["research", "--policy", str(path), "--db", str(service.path),
                 "inspect", "--source-id", "PT-EN"]) == 0
    assert json.loads(capsys.readouterr().out)["metrics"]["record_revisions"] == 1


def test_duplicate_publications_do_not_inflate_record_count(setup):
    service, scope, ingest, _, _ = setup
    package = cases.publication(("A",))
    ingest(package)
    package["exported_at"] = "2026-09-12T00:00:00Z"
    ingest(cases.reseal(package))
    result = inspect(service, scope)
    assert result["metrics"]["record_revisions"] == 1
    assert result["metrics"]["publications"] == 2
    assert result["metrics"]["evidence_references"] == 2
    assert result["metrics"]["received_content_hashes"] == 1


def test_projection_corruption_fails_closed(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication())
    with service.connection() as db:
        db.execute("UPDATE records SET status='CORRUPT'")
    with pytest.raises(ValueError, match="Projection"):
        inspect(service, scope)


def test_response_limit_is_explicit(setup, monkeypatch):
    service, scope, _, _, _ = setup
    import cain.research.inspection as module

    monkeypatch.setattr(module, "_build", lambda *args: {"large": "x" * 1_000_001})
    with pytest.raises(ValueError, match="1000000 bytes"):
        inspect(service, scope)


def test_record_limit_is_explicit(setup):
    service, _, _, _, _ = setup
    from cain.research.inspection import _build

    packages = [cases.publication(tuple(f"{n}-{i}" for i in range(200))) for n in range(11)]
    archives = {p["publication_id"]: p for p in packages}
    received = {p: "2026-09-11T00:00:00Z" for p in archives}
    with pytest.raises(ValueError, match="2000 revisions"):
        _build(service, archives, received, None, None, None, None)

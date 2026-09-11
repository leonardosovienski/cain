"""Regression cases found by the requirement-by-requirement completion audit."""

import json
import sqlite3
import runpy
from pathlib import Path

import pytest
from research_snapshot import canonical

import test_research_l0 as cases
from cain.research import ResearchService
from cain.research.historian import explain
from cain.api import create_app
from fastapi.testclient import TestClient

setup = cases.setup


def test_api_history_reopens_in_existing_workspace_session(setup, tmp_path):
    service, _, ingest, _, path = setup
    ingest(cases.publication())

    def application():
        return create_app(
            tmp_path / "legacy.db",
            llm=cases.ExplodingProvider(),
            research_policy=path,
            research_db=service.path,
        )

    with TestClient(application()) as client:
        session = client.post("/sessions/leo", json={}).json()["id"]
        entry = client.post(
            "/research/query", json={"source_id": "A", "session_id": session}
        ).json()["query_id"]
        assert client.post("/research/query", json={"session_id": "unknown"}).status_code == 400
        assert (
            client.post("/research/readiness", json={}).json()["storage_and_query"]
            == "verified_for_requested_scope"
        )
    with TestClient(application()) as client:
        history = client.get("/research/history", params={"session_id": session}).json()
        assert entry in {r["id"] for r in history}
        recalled = client.get("/research/history/" + entry, params={"session_id": session}).json()
        assert recalled["total_record_revisions"] == 1
        assert client.get("/research/history/" + entry).status_code == 400


@pytest.mark.parametrize("column", ["domain", "source_id", "kind", "status", "revision"])
def test_corrupt_filter_column_cannot_become_false_absence(setup, column):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication())
    with sqlite3.connect(service.path) as db:
        db.execute(f"UPDATE records SET {column}='corrupt'")
    with pytest.raises(ValueError, match="Projection"):
        service.query(scope, source_id="A")
    with pytest.raises(ValueError, match="Projection"):
        service.verify(scope)
    service.verify(scope, rebuild=True)
    assert service.query(scope, source_id="A")["total_record_revisions"] == 1


def test_missing_membership_cannot_become_false_absence(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication())
    with sqlite3.connect(service.path) as db:
        db.execute("DELETE FROM membership")
    with pytest.raises(ValueError, match="membership"):
        service.query(scope)
    service.verify(scope, rebuild=True)
    assert service.query(scope)["total_record_revisions"] == 2


def test_history_reopens_and_isolates_session_project_and_current_policy(setup):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication())
    result = explain(service, scope, "Reported?", cases.QuoteProvider(), session_id="session-a")
    reopened = ResearchService(service.path, path)
    entries = reopened.history(scope, "session-a")
    assert result["response_id"] in {r["id"] for r in entries}
    assert reopened.history(scope, "session-b") == []
    assert reopened.history(service.scope(project="project-a"), "session-a") == []
    recalled = reopened.recall(scope, result["response_id"], "session-a")
    assert recalled["explanation"] == result["explanation"]
    with pytest.raises(ValueError, match="session"):
        reopened.recall(scope, result["response_id"], "session-b")
    policy["grants"] = []
    path.write_bytes(canonical(policy))
    assert (
        reopened.recall(scope, result["response_id"], "session-a")["status"]
        == "history_redacted_by_current_policy"
    )
    query_entry = next(e for e in entries if e["request"].get("mode") != "explanation")
    assert reopened.recall(scope, query_entry["id"], "session-a")["total_record_revisions"] == 0


def test_revocation_during_generation_withholds_answer_and_revoked_facts(setup):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication())

    class RevokingProvider(cases.QuoteProvider):
        def generate(self, prompt, context=""):
            raw = super().generate(prompt, context)
            policy["grants"] = []
            path.write_bytes(canonical(policy))
            return raw

    result = explain(service, scope, "Reported?", RevokingProvider())
    assert result["status"] == "generation_failed"
    assert result["error_code"] == "GENERATION_PERMISSION_REVOKED"
    assert result["explanation"] is None
    assert result["facts"]["records"] == []


def test_duplicate_json_keys_from_provider_are_rejected(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication())

    class DuplicateProvider(cases.QuoteProvider):
        def generate(self, prompt, context=""):
            raw = json.loads(super().generate(prompt, context))
            return '{"claims":[],"claims":' + json.dumps(raw["claims"]) + ',"synthesis":""}'

    assert (
        explain(service, scope, "Reported?", DuplicateProvider())["status"] == "generation_failed"
    )


def test_comparative_harness_executes_both_model_arms_with_same_provider(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(text="A FAILED; source reason not recorded."))
    evaluate = runpy.run_path(str(Path(__file__).parents[2] / "evaluation/evaluate_l0.py"))[
        "evaluate"
    ]
    protocol = {
        "episodes": [
            {
                "id": "a",
                "source_id": "A",
                "question": "A FAILED?",
                "expected_status": "FAILED",
                "abstain": False,
            }
        ],
        "call_limit_per_model_arm": 1,
        "evidence_budget_bytes": 6000,
        "generation_limit_bytes": 6000,
        "limitations": ["synthetic development case"],
    }
    result = evaluate(service, scope, protocol, cases.QuoteProvider())
    assert result["summary"]["model_calls"] == 2
    assert result["episodes"][0]["historian"]["status"] == "generated"
    assert result["episodes"][0]["organized_documents"]["generation"]["status"] == "generated"
    assert result["summary"]["utility_status"] == "INCONCLUSIVE"
    assert evaluate(service, scope, protocol)["summary"]["model_calls"] == 0
    protocol["call_limit_per_model_arm"] = 0
    with pytest.raises(ValueError, match="limit"):
        evaluate(service, scope, protocol, cases.QuoteProvider())

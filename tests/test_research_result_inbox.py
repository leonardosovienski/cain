from copy import deepcopy
import json

import pytest
from research_protocol import sign_result

from cain.research_results import ResultConflict, ResultInbox
from cain.research.service import ResearchService


SECRET = bytes.fromhex("33" * 32)
SHA = "ab" * 32
SOURCE = "12" * 20


class Tasks:
    def proposed_context(self, task_id):
        assert task_id == "TASK-001"
        return {"task": {"research_id": "RESEARCH-001", "hypothesis_id": "H6"},
                "task_payload_hash": SHA, "outbox_status": "PUBLISHED"}


def identity():
    return {"package_version": "1.0.0", "source_sha": SOURCE, "artifact_sha256": SHA}


def content(name):
    return {"name": name, "version": "v1", "content_hash": SHA}


def result():
    return {
        "schema_version": "ResearchResultV1", "result_id": "RESULT-001",
        "task_id": "TASK-001", "admission_id": "ADMISSION-001",
        "research_id": "RESEARCH-001", "hypothesis_id": "H6",
        "experiment_id": "EXPERIMENT-001", "result_envelope_state": "PRODUCED",
        "envelope_failure_reason": None, "produced_at": "2026-09-19T23:03:00Z",
        "core_facts": {"identity": identity(), "trial_ids": ["TRIAL-001"],
                       "scientific_state": "INCONCLUSIVE", "temporal_integrity": "PASS",
                       "statistics_receipt_hash": SHA},
        "ops_facts": {"identity": identity(), "ops_run_ids": ["RUN-001"],
                      "operational_state": "SUCCEEDED", "started_at": "2026-09-19T23:00:00Z",
                      "finished_at": "2026-09-19T23:02:00Z", "exit_code": 0,
                      "runtime_provenance_hash": SHA},
        "crypto_facts": {"identity": identity(), "dataset_identity": content("dataset"),
                         "model_identity": content("model"),
                         "feature_set_identity": content("features"),
                         "data_cutoff": "2026-09-18T00:00:00Z",
                         "metrics": {"sample_size": 100, "gross_return_bps": 10,
                                     "net_return_bps": -5, "max_drawdown_bps": -20,
                                     "turnover_bps": 100, "ci_low_bps": -30,
                                     "ci_high_bps": 20},
                         "baseline_comparison": {"baseline_id": "BASE-001", "outcome": "LOSES",
                                                 "gross_delta_bps": 2, "net_delta_bps": -3},
                         "costs": {"fee_bps": 10, "slippage_bps": 5, "total_cost_bps": 15},
                         "economic_state": "NO_EDGE", "artifacts": []},
        "provenance": {"task_payload_hash": SHA, "admission_policy_hash": SHA,
                       "resolved_references_hash": SHA, "crypto_source_sha": SOURCE},
    }


def envelope(value=None, **overrides):
    arguments = {"producer": "CRIPTO", "publisher_identity": "crypto-qa",
                 "consumer": "CAIN", "scope": "crypto.research.result",
                 "key_id": "crypto-f4-key", "secret": SECRET}
    arguments.update(overrides)
    return sign_result(value or result(), **arguments)


def inbox(tmp_path):
    return ResultInbox(tmp_path / "inbox.db", task_outbox=Tasks(),
                       publisher_identity="crypto-qa", key_id="crypto-f4-key", secret=SECRET)


def test_result_inbox_authenticates_correlates_and_deduplicates(tmp_path):
    assert inbox(tmp_path).ingest(envelope())["status"] == "ingested"
    assert inbox(tmp_path).ingest(envelope())["status"] == "duplicate"
    assert inbox(tmp_path).result("RESULT-001")["crypto_facts"]["economic_state"] == "NO_EDGE"
    assert len(inbox(tmp_path).for_task("TASK-001")) == 1


def test_result_inbox_rejects_unknown_publisher_and_task_mismatch(tmp_path):
    with pytest.raises(PermissionError):
        inbox(tmp_path).ingest(envelope(publisher_identity="unknown"))
    changed = result()
    changed["provenance"]["task_payload_hash"] = "cd" * 32
    with pytest.raises(PermissionError):
        inbox(tmp_path).ingest(envelope(changed))


def test_result_inbox_detects_same_id_different_payload(tmp_path):
    target = inbox(tmp_path)
    target.ingest(envelope())
    changed = deepcopy(result())
    changed["crypto_facts"]["metrics"]["sample_size"] += 1
    with pytest.raises(ResultConflict):
        target.ingest(envelope(changed))


def test_cumulative_results_preserve_divergent_experiments_after_restart(tmp_path):
    target = inbox(tmp_path)
    first = result()
    first["result_id"] = "RESULT-A"
    first["experiment_id"] = "EXPERIMENT-A"
    first["core_facts"]["scientific_state"] = "REFUTED"
    second = deepcopy(result())
    second["result_id"] = "RESULT-C"
    second["experiment_id"] = "EXPERIMENT-C"
    second["core_facts"]["scientific_state"] = "SUPPORTED"
    target.ingest(envelope(first))
    target.ingest(envelope(second))
    recovered = inbox(tmp_path).for_task("TASK-001")
    assert [(row["result_id"], row["core_facts"]["scientific_state"]) for row in recovered] == [
        ("RESULT-A", "REFUTED"),
        ("RESULT-C", "SUPPORTED"),
    ]


def authorized_inbox(tmp_path):
    import_root = (tmp_path / "imports").resolve()
    import_root.mkdir()
    policy_path = tmp_path / "receiver-policy.json"
    policy = {
        "version": 2,
        "imports": [{"user": "alice", "project": "crypto-project",
                     "collection": "results", "root": str(import_root)}],
        "grants": [{
            "user": "alice", "project": "crypto-project", "collection": "results",
            "domain": "crypto", "repository": "CRIPTO", "publisher": "crypto-qa",
            "stream": "research-results", "sources": [], "policies": ["crypto-result-v1"],
            "generate": True,
        }],
    }
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    access = ResearchService(tmp_path / "research.db", policy_path)
    target = ResultInbox(
        tmp_path / "inbox.db", task_outbox=Tasks(), publisher_identity="crypto-qa",
        key_id="crypto-f4-key", secret=SECRET, access_service=access,
    )
    scope = access.scope("alice", "crypto-project", "results")
    return target, access, scope, policy, policy_path


def test_raw_canonical_derived_projection_rechecks_scope_and_revocation(tmp_path):
    target, access, scope, policy, policy_path = authorized_inbox(tmp_path)
    target.ingest(envelope())
    projected = target.projection("RESULT-001", research_scope=scope)
    assert projected["raw_hash"] != projected["canonical_hash"]
    assert projected["normalizer_version"] == "1"
    assert projected["derived"]["operational_state"] == "SUCCEEDED"
    assert projected["derived"]["scientific_state"] == "INCONCLUSIVE"
    assert projected["derived"]["economic_state"] == "NO_EDGE"
    with pytest.raises(PermissionError):
        target.projection(
            "RESULT-001", research_scope=access.scope("mallory", "crypto-project", "results")
        )
    policy["grants"] = []
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(PermissionError):
        target.result("RESULT-001", research_scope=scope)


def test_cumulative_authorized_reasoning_is_local_only_and_preserves_contradiction(tmp_path):
    target, _, scope, _, _ = authorized_inbox(tmp_path)
    first = result()
    first["result_id"], first["experiment_id"] = "RESULT-A", "EXPERIMENT-A"
    first["core_facts"]["scientific_state"] = "REFUTED"
    second = deepcopy(result())
    second["result_id"], second["experiment_id"] = "RESULT-C", "EXPERIMENT-C"
    second["core_facts"]["scientific_state"] = "SUPPORTED"
    target.ingest(envelope(first))
    target.ingest(envelope(second))

    class LocalProvider:
        base_url = "local"
        payload = None

        def generate(self, payload):
            self.payload = payload
            return "A foi refutado; C foi suportado; ambos permanecem no histórico; NO_EDGE."

    provider = LocalProvider()
    answer = target.reason("H6", "O que mudou?", provider, research_scope=scope)
    assert answer["sources"] == ["RESULT-A", "RESULT-C"]
    assert [item["scientific_state"] for item in provider.payload["results"]] == [
        "REFUTED", "SUPPORTED"
    ]
    assert all("artifacts" not in item for item in provider.payload["results"])

    class RemoteProvider(LocalProvider):
        base_url = "https://provider.invalid"

    with pytest.raises(PermissionError, match="EGRESS_DENIED"):
        target.reason("H6", "O que mudou?", RemoteProvider(), research_scope=scope)

"""Robustness of the CAIN edge against malformed envelopes and inputs (audit of 2026-09-28).

Found with fuzzing on 0.4.13rc13: a result file (or a proposal) nested 100 000 levels deep raised a RecursionError
out of ``ingest``/``propose`` instead of a rejection, a result whose ``outcome.status`` was a list raised a TypeError
from the frozen protocol's validator, and ``as_of = 2030-13-45T99:00:00Z`` (right shape, impossible instant) was
recorded in an episode and emitted in a task. None changes a receipt for a valid input: ``policy.py`` is untouched.
"""

import json

import pytest
from research_protocol import v2
from test_orchestration import AS_OF, cycle, proposal

from cain.orchestration import cli
from cain.orchestration.service import OrchestrationError, _payload

DEEP = b"[" * 100_000 + b"]" * 100_000


def test_a_deeply_nested_proposal_file_is_refused_as_schema_invalid(tmp_path):
    path = tmp_path / "deep.json"
    path.write_bytes(DEEP)
    with pytest.raises(v2.V2Error) as info:
        cli._proposal(path)
    assert info.value.code == "SCHEMA_INVALID"


def test_a_deeply_nested_result_file_is_rejected_and_the_next_results_still_ingest(world):
    cycle(world, 1)
    results = world.spool.result_files("crypto")[0].parent
    (results / "deep.json").write_bytes(DEEP)
    report = {r["file"]: r for r in world.orch.ingest(world.spool)}
    assert report["deep.json"]["action"] == "rejected" and report["deep.json"]["code"] == "SCHEMA_INVALID"
    assert {r["action"] for f, r in report.items() if f != "deep.json"} == {"duplicate"}
    again = world.orch.ingest(world.spool)
    assert [r for r in again if r["file"] == "deep.json"][0]["action"] == "skipped"


@pytest.mark.parametrize("status", [[], {}, ["RESULT"], {"a": 1}])
def test_an_unhashable_outcome_status_is_rejected_not_a_traceback(world, status):
    cycle(world, 1)
    (original,) = world.spool.result_files("crypto")
    body = json.loads(original.read_bytes())
    body["outcome"]["status"] = status
    (original.parent / "odd.json").write_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
    report = [r for r in world.orch.ingest(world.spool) if r["file"] == "odd.json"]
    assert report[0]["action"] == "rejected" and report[0]["code"] == "SCHEMA_INVALID"
    with world.orch.store.db() as db:
        assert db.execute("SELECT count(*) AS n FROM inbox").fetchone()["n"] == 1


@pytest.mark.parametrize("as_of", ["2030-13-45T99:00:00Z", "2030-02-30T00:00:00Z", "2030-01-01T24:00:00Z",
                                   "2030-01-01T00:00:00", "2030-01-01 00:00:00Z", "", None, 20300101])
def test_as_of_must_be_a_real_utc_instant(world, as_of):
    with pytest.raises(OrchestrationError) as info:
        world.orch.propose(proposal(1), as_of=as_of)
    assert info.value.code == "AS_OF_INVALID"
    with pytest.raises(OrchestrationError):
        world.orch.decision_receipt(proposal(1), as_of=as_of)
    assert world.orch.episodes()[0]["episodes"] == []


def test_a_valid_as_of_still_gives_the_same_receipt(world):
    before = world.orch.decision_receipt(proposal(1), as_of=AS_OF)
    assert world.orch.propose(proposal(1), as_of=AS_OF)["receipt_sha256"] == before["receipt_sha256"]
    assert world.orch.propose(proposal(1), as_of="2030-12-31T23:59:59Z")["status"] == "EXISTING"


def test_a_domain_payload_nested_too_deep_yields_no_metrics():
    assert _payload({"payload_canonical": DEEP.decode()}) == {}
    assert _payload({"payload_canonical": '{"a": 1}'}) == {"a": 1}

"""Orchestration of the crypto domain end to end with the real transport consumer and a stand-in domain adapter.

The stand-in only replaces the domain circuit (outside the CAIN); the CAIN side (policy, outbox, spool, inbox,
memory) is the real code. The qualification E2E runs the real cripto-predictor instead.
"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest
from research_protocol import v2
from research_transport.consumer import Consumer
from research_transport.spool import Spool

from cain.orchestration import policy
from cain.orchestration.faults import ENV, EXIT_CODE
from cain.orchestration.service import OrchestrationError, Orchestrator

AS_OF = "2030-01-01T10:00:00Z"
REQUEST = {
    "schema_version": "crypto-research-request/1",
    "request_id": "crypto:REQ-I-0001",
    "request_type": "BACKTEST_EXISTING_HYPOTHESIS",
    "research_id": "crypto:RESEARCH-I",
    "hypothesis_id": "crypto:QUAL-SHADOW-REAL-001",
    "references": {"protocol": {"name": "fixed-shadow", "version": "v1"},
                   "dataset": {"name": "real-in-sample", "version": "v1"},
                   "baseline": {"name": "flat", "version": "v1"},
                   "cost_model": {"name": "v3-frozen", "version": "v1"},
                   "evidence": {"name": "none", "version": "v1"}},
    "data_cutoff": "2026-08-31T00:00:00Z",
    "parameters": {"symbol": "BTCUSDT", "horizon_days": 7, "max_observations": 100, "fee_bps": 10,
                   "slippage_bps": 5, "placebo_seed": 1},
    "priority_hint": "NORMAL",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def proposal(n: int, **changes) -> dict:
    request = copy.deepcopy(REQUEST)
    request["request_id"] = f"crypto:REQ-I-{n:04d}"
    request["parameters"]["placebo_seed"] = n
    request.update(changes)
    return {"schema": "cain-proposal/1", "proposal_id": f"cain:PROP-{n}", "domain": "crypto", "request": request,
            "based_on": [], "rationale": "integration test", "source": "agenda"}


class StandInDomain:
    """Idempotent by request_id; scripted statuses; never used by the qualification gates."""

    DOMAIN = "crypto"

    def __init__(self):
        self.results, self.script, self.states, self.facts = {}, [], {}, {}

    def identity(self):
        return {"distribution": "cripto-predictor", "version": "stand-in", "module": "tests.stand_in"}

    def submit_task(self, task, config):
        raw = v2.canonical(task["payload"])
        request = json.loads(raw)
        out = {"submission_sha256": sha(raw), "request_id": request["request_id"], "client_ref": request["client_ref"]}
        status = self.script.pop(0) if self.script else None
        status, reason = status if isinstance(status, tuple) else (status, status)
        if status in ("OPS_FAILED_RETRYABLE", "TEMPORAL_INTEGRITY_VIOLATION", "RECONCILIATION_REQUIRED", "REJECTED"):
            code = {"OPS_FAILED_RETRYABLE": 3, "TEMPORAL_INTEGRITY_VIOLATION": 4, "RECONCILIATION_REQUIRED": 5,
                    "REJECTED": 2}[status]
            return out | {"status": status, "exit_code": code, "reason": reason}
        duplicate = request["request_id"] in self.results
        state, scientific = self.states.get(request["request_id"], ("NO_EDGE", "INCONCLUSIVE"))
        result = self.results.setdefault(request["request_id"], {
            "schema_version": "crypto-research-result/1",
            "result_id": "crypto:RESULT-" + sha(request["request_id"].encode())[:32],
            "request_id": request["request_id"], "admission_id": "crypto:ADM-" + "b" * 32,
            "experiment_id": "crypto:EXP-" + sha(request["request_id"].encode())[:32],
            "research_id": request["research_id"], "hypothesis_id": request["hypothesis_id"],
            "result_state": state, "operational_state": "SUCCEEDED", "scientific_state": scientific,
            "economic_state": "WATCH" if state == "WATCH_NO_CAPITAL" else "NO_EDGE", "capital_permission": False,
            "produced_at": "2026-09-27T09:00:00Z", "core_facts": {"ci": [-0.25, 0.3]}, "ops_facts": {},
            "domain_facts": self.facts.get(request["request_id"], {}), "provenance": {}})
        return out | {"status": "DUPLICATE" if duplicate else "RESULT", "exit_code": 0, "result": result}

    def reread(self, request_id, config):
        return 0, {"result_sha256": sha(v2.domain_canonical(self.results[request_id]))}


@pytest.fixture
def world(tmp_path):
    domain = StandInDomain()
    spool = Spool(tmp_path / "spool")
    orchestrator = Orchestrator("crypto", tmp_path / "state")
    consumer = Consumer("crypto", spool, tmp_path / "consumer.sqlite", domain, {"state": "unused"})

    class World:
        pass

    w = World()
    w.domain, w.spool, w.orch, w.consumer, w.tmp = domain, spool, orchestrator, consumer, tmp_path
    return w


def cycle(w, n, as_of=AS_OF, **changes):
    out = w.orch.propose(proposal(n, **changes), as_of=as_of)
    w.orch.dispatch(w.spool)
    w.consumer.run_once()
    w.orch.ingest(w.spool)
    return out


def test_full_cycle_remembers_the_result_in_the_domain_cube_only(world):
    out = cycle(world, 1)
    assert out["receipt"]["decision"] == "ALLOW"
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert len(facts) == 1 and facts[0]["object"]["result_state"] == "NO_EDGE"
    assert facts[0]["object"]["capital_permission"] is False
    assert world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["stocks"]) == []
    assert world.orch.store.memory.verify()["status"] == "intact"
    nxt = world.orch.propose(proposal(2), as_of="2030-01-01T11:00:00Z")
    assert nxt["receipt"]["decision"] == "ALLOW"
    assert nxt["receipt"]["task"]["previous_task_id"] == out["receipt"]["task"]["task_id"]


def test_duplicate_deliveries_never_create_a_second_effect(world):
    cycle(world, 1)
    assert world.orch.dispatch(world.spool, resend=True)[0]["spool"] == "EXISTS"
    assert world.consumer.run_once()[0]["action"] == "skipped"
    (original,) = world.spool.result_files("crypto")
    shutil.copy(original, original.with_name("redelivered-copy.json"))
    report = world.orch.ingest(world.spool) + world.orch.ingest(world.spool)
    assert [r["action"] for r in report] == ["duplicate", "duplicate", "duplicate", "duplicate"]
    again = world.orch.propose(dict(proposal(1), proposal_id="cain:PROP-1-again"), as_of="2030-01-01T12:00:00Z")
    assert again["receipt"]["decision"] == "DUPLICATE"
    with world.orch.store.db() as db:
        assert db.execute("SELECT count(*) FROM outbox").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM inbox").fetchone()[0] == 1
    assert len(world.domain.results) == 1


def test_same_proposal_returns_the_recorded_episode_and_conflicting_id_is_refused(world):
    first = world.orch.propose(proposal(1), as_of=AS_OF)
    again = world.orch.propose(proposal(1), as_of="2030-01-01T12:00:00Z")
    assert again["status"] == "EXISTING" and again["receipt_sha256"] == first["receipt_sha256"]
    with pytest.raises(OrchestrationError, match="PROPOSAL_ID_CONFLICT"):
        world.orch.propose(proposal(1, priority_hint="LOW"), as_of=AS_OF)


def test_foreign_unknown_and_tampered_results_are_rejected(world):
    cycle(world, 1)
    other = v2.build_task("stocks", {
        "schema_version": "stocks-research-request/1", "request_id": "stocks:REQ-1",
        "request_type": "BACKTEST_PIT_FACTOR", "research_id": "stocks:R", "hypothesis_id": "stocks:H9",
        "references": {k: {"name": "x", "version": "v1"} for k in
                       ("dataset", "universe", "features", "model", "baseline", "cost_model", "readiness")},
        "as_of": "2026-09-24T03:00:00Z",
        "pit": {"availability_rule": "AVAILABLE_AT_LE_DECISION_TIME", "minimum_pit_class": "PIT_RECONSTRUCTED"},
        "parameters": {"target": "NEXT_REBALANCE_RETURN", "fee_bps": 10, "slippage_bps": 5, "max_securities": 50,
                       "external_intelligence": {"mode": "NONE", "families": []}},
        "priority_hint": "NORMAL"}, episode_id="stocks:episode-1", proposal_id="cain:X", created_at=AS_OF)
    stranger = v2.build_task("crypto", dict(REQUEST, request_id="crypto:REQ-STRANGER"),
                             episode_id="crypto:episode-9", proposal_id="cain:X", created_at=AS_OF)
    results_dir = world.spool.root / "crypto" / "results"
    for name, task in (("foreign.json", other), ("stranger.json", stranger)):
        domain = task["domain"]
        outcome = {"status": "REJECTED", "exit_code": 2, "reason": "x", "request_id": task["request_id"],
                   "client_ref": None}
        raw = v2.dumps_result(v2.build_result(task, outcome, adapter={"distribution": f"{domain}-p", "module": "m",
                                                                       "version": "1"},
                                              produced_at=AS_OF))
        (results_dir / name).write_bytes(raw)
    (results_dir / "old.json").write_bytes(b'{"schema":"research-result/1"}')
    genuine = next(p for p in results_dir.iterdir() if p.name.startswith("TASK-"))
    tampered = json.loads(genuine.read_bytes())
    tampered["episode_id"] = "crypto:episode-7"
    (results_dir / "tampered.json").write_bytes(v2.canonical(tampered))
    codes = {r["file"]: r.get("code") for r in world.orch.ingest(world.spool) if r["action"] == "rejected"}
    assert codes == {"foreign.json": "DOMAIN_MISMATCH", "stranger.json": "TASK_NOT_FOUND",
                     "old.json": "VERSION_UNSUPPORTED", "tampered.json": "CORRELATION_MISMATCH"}
    with world.orch.store.db() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone()[0] == 1


def test_retryable_then_retry_then_result(world):
    world.domain.script = ["OPS_FAILED_RETRYABLE"]
    out = cycle(world, 1)
    task_id = out["receipt"]["task"]["task_id"]
    assert world.orch.propose(proposal(2), as_of="2030-01-01T11:00:00Z")["receipt"]["reason_code"] == "OPEN_TASK_PENDING"
    world.orch.retry(world.spool, task_id)
    world.consumer.run_once()
    world.orch.ingest(world.spool)
    with pytest.raises(OrchestrationError, match="NOT_RETRYABLE"):
        world.orch.retry(world.spool, task_id)
    assert world.orch.propose(proposal(3), as_of="2030-01-01T12:00:00Z")["receipt"]["decision"] == "ALLOW"


def test_refusal_is_remembered_and_requires_human_stops_the_domain(world):
    world.domain.script = ["TEMPORAL_INTEGRITY_VIOLATION"]
    cycle(world, 1)
    assert world.orch.propose(proposal(2), as_of="2030-01-01T11:00:00Z")["receipt"]["decision"] == "ALLOW"
    world.orch.dispatch(world.spool)
    world.domain.script = ["RECONCILIATION_REQUIRED"]
    world.consumer.run_once()
    world.orch.ingest(world.spool)
    out = world.orch.propose(proposal(3), as_of="2030-01-01T12:00:00Z")
    assert (out["receipt"]["decision"], out["receipt"]["reason_code"]) == ("REQUIRE_HUMAN",
                                                                            "DOMAIN_RECONCILIATION_PENDING")


def test_contradiction_is_preserved_not_decided_by_majority(world):
    world.domain.states = {"crypto:REQ-I-0001": ("WATCH_NO_CAPITAL", "SUPPORTED"),
                           "crypto:REQ-I-0002": ("REFUTED", "REFUTED"),
                           "crypto:REQ-I-0003": ("REFUTED", "REFUTED")}
    cycle(world, 1, as_of="2030-01-01T10:00:00Z")
    cycle(world, 2, as_of="2030-01-01T11:00:00Z")
    out = world.orch.propose(proposal(3), as_of="2030-01-01T12:00:00Z")
    assert out["receipt"]["reason_code"] == "CONTRADICTION_UNRESOLVED"
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert sorted(f["object"]["scientific_state"] for f in facts) == ["REFUTED", "SUPPORTED"]


def run_cain(*args, env=None):
    return subprocess.run([sys.executable, "-m", "cain", *map(str, args)], capture_output=True, env=env,
                          cwd=os.getcwd())


def test_decision_receipt_is_byte_identical_in_three_new_processes(world, tmp_path):
    cycle(world, 1)
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(proposal(2)), encoding="utf-8")
    outputs = [run_cain("research", "decision-receipt", "--domain", "crypto", "--state", world.tmp / "state",
                        "--proposal", candidate, "--as-of", "2030-01-01T11:00:00Z") for _ in range(3)]
    assert all(o.returncode == 0 for o in outputs), outputs[0].stderr
    assert len({o.stdout for o in outputs}) == 1
    receipt = json.loads(outputs[0].stdout)
    assert receipt["decision"] == "ALLOW" and receipt["policy"]["code_sha256"] == policy.code_sha256()
    with world.orch.store.db() as db:
        assert db.execute("SELECT count(*) FROM episodes").fetchone()[0] == 1


@pytest.mark.parametrize("point", ["after_decision_before_episode_commit", "after_outbox_commit"])
def test_process_death_during_proposal_recovers_with_the_same_receipt(tmp_path, point):
    state, candidate = tmp_path / "state", tmp_path / "p.json"
    candidate.write_text(json.dumps(proposal(1)), encoding="utf-8")
    args = ("research", "propose", "--domain", "crypto", "--state", state, "--proposal", candidate, "--as-of", AS_OF)
    died = run_cain(*args, env=os.environ | {ENV: point})
    assert died.returncode == EXIT_CODE
    again = run_cain(*args)
    assert again.returncode == 0
    clean = tmp_path / "clean"
    reference = run_cain("research", "propose", "--domain", "crypto", "--state", clean, "--proposal", candidate,
                         "--as-of", AS_OF)
    assert json.loads(again.stdout)["receipt_sha256"] == json.loads(reference.stdout)["receipt_sha256"]
    with Orchestrator("crypto", state).store.db() as db:
        assert db.execute("SELECT count(*) FROM episodes").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM outbox").fetchone()[0] == 1


@pytest.mark.parametrize("point", ["after_spool_write_before_ack", "after_inbox_commit_before_memory",
                                   "after_memory_commit"])
def test_process_death_in_dispatch_or_ingest_recovers_exactly_once(world, point):
    world.orch.propose(proposal(1), as_of=AS_OF)
    state, spool = world.tmp / "state", world.tmp / "spool"
    if point == "after_spool_write_before_ack":
        assert run_cain("research", "dispatch", "--domain", "crypto", "--state", state, "--spool", spool,
                        env=os.environ | {ENV: point}).returncode == EXIT_CODE
        assert run_cain("research", "dispatch", "--domain", "crypto", "--state", state, "--spool", spool).returncode == 0
        world.consumer.run_once()
    else:
        world.orch.dispatch(world.spool)
        world.consumer.run_once()
        assert run_cain("research", "ingest", "--domain", "crypto", "--state", state, "--spool", spool,
                        env=os.environ | {ENV: point}).returncode == EXIT_CODE
    assert run_cain("research", "ingest", "--domain", "crypto", "--state", state, "--spool", spool).returncode == 0
    assert run_cain("research", "ingest", "--domain", "crypto", "--state", state, "--spool", spool).returncode == 0
    assert len(world.domain.results) == 1 and len(world.spool.task_files("crypto")) == 1
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert len(facts) == 1
    with world.orch.store.db() as db:
        assert db.execute("SELECT count(*) FROM inbox WHERE fact_id IS NOT NULL").fetchone()[0] == 1


def test_cli_refuses_unknown_domain_configuration(tmp_path):
    candidate = tmp_path / "p.json"
    candidate.write_text(json.dumps(proposal(1)), encoding="utf-8")
    # every domain of the frozen V2 registry now has a configuration; an unknown domain still fails closed
    done = run_cain("research", "propose", "--domain", "football", "--state", tmp_path / "s", "--proposal", candidate)
    assert done.returncode == 1 and b"CONFIG_INVALID" in done.stdout


def test_no_capital_anywhere(world):
    cycle(world, 1)
    for path in (world.tmp / "state").iterdir():
        assert b'"capital_permission":true' not in path.read_bytes().replace(b" ", b"")


def test_cli_in_process_covers_every_orchestration_command(world, tmp_path, capsys):
    from cain.cli import main

    state, spool = world.tmp / "state", world.tmp / "spool"
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(proposal(1)), encoding="utf-8")
    bad.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    base = ["research"]
    assert main([*base, "propose", "--domain", "crypto", "--state", str(state), "--proposal", str(good),
                 "--as-of", AS_OF]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "ALLOW"
    assert main([*base, "propose", "--domain", "crypto", "--state", str(state), "--proposal", str(bad)]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "SCHEMA_INVALID"  # duplicate key, fail closed
    assert main([*base, "dispatch", "--domain", "crypto", "--state", str(state), "--spool", str(spool)]) == 0
    capsys.readouterr()
    world.consumer.run_once()
    assert main([*base, "ingest", "--domain", "crypto", "--state", str(state), "--spool", str(spool)]) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "ingested"
    task_id = world.orch.episodes()[0]["episodes"][0]["task_id"]
    assert main([*base, "retry", "--domain", "crypto", "--state", str(state), "--spool", str(spool),
                 "--task-id", task_id]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "NOT_RETRYABLE"
    assert main([*base, "episodes", "--domain", "crypto", "--state", str(state)]) == 0
    episodes = json.loads(capsys.readouterr().out)
    assert [e["decision"] for e in episodes["episodes"]] == ["ALLOW"] and episodes["memory"]["status"] == "intact"
    assert main([*base, "decision-receipt", "--domain", "crypto", "--state", str(state), "--proposal", str(good),
                 "--as-of", AS_OF]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "ALLOW"
    (spool / "crypto" / "results" / "junk.json").write_bytes(b"not json")
    assert main([*base, "ingest", "--domain", "crypto", "--state", str(state), "--spool", str(spool)]) == 2


def test_memory_never_keeps_the_domain_free_text_reason(world):
    world.domain.script = ["TEMPORAL_INTEGRITY_VIOLATION"]
    cycle(world, 1)
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert [f["object"]["status"] for f in facts] == ["TEMPORAL_INTEGRITY_VIOLATION"]
    assert all("reason" not in f["object"] for f in facts)
    assert b"TEMPORAL_INTEGRITY_VIOLATION" in (world.tmp / "state" / "memory.sqlite").read_bytes()


class StubModel:
    model = "stub"

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def generate_json(self, prompt, context, schema):
        self.calls.append((prompt, context, schema))
        return json.dumps(self.answer)


def test_llm_proposal_is_audited_and_still_goes_through_the_policy(world, tmp_path):
    from cain.orchestration import llm

    cycle(world, 1)
    model = StubModel({"hypothesis_id": "crypto:QUAL-SHADOW-REAL-002", "rationale": "x"})
    out = tmp_path / "llm" / "p1.json"
    info = llm.propose(world.orch, model, question="próximo", as_of="2030-01-01T11:00:00Z",
                       proposal_id="cain:LLM-1", out=out)
    (prompt, _context, schema), = model.calls
    assert schema["properties"]["hypothesis_id"]["enum"] == sorted(world.orch.config["proposable_hypotheses"])
    assert "crypto:H9" not in schema["properties"]["hypothesis_id"]["enum"]
    assert set(schema["properties"]) == {"hypothesis_id", "rationale"}  # the CAIN, not the model, picks the seed
    assert "stocks" not in prompt and "capital" not in json.loads(prompt)
    proposal = json.loads(out.read_text(encoding="utf-8"))
    audit = json.loads(out.with_suffix(".audit.json").read_text(encoding="utf-8"))
    assert proposal["source"] == "llm" and audit["response"] == json.dumps(model.answer)
    assert audit["proposal_sha256"] == policy.safe_digest(proposal) and info["model"]["model"] == "stub"
    decision = world.orch.propose(proposal, as_of="2030-01-01T11:00:00Z")["receipt"]
    assert decision["decision"] == "ALLOW" and decision["task"] is not None
    world.orch.dispatch(world.spool)  # the model is only asked while some hypothesis is eligible (no open task)
    world.consumer.run_once()
    world.orch.ingest(world.spool)
    bad = StubModel({"hypothesis_id": "crypto:H9"})
    with pytest.raises(ValueError, match="LLM_ANSWER_INVALID"):
        llm.propose(world.orch, bad, question="x", as_of="2030-01-01T12:00:00Z", proposal_id="cain:LLM-2",
                    out=tmp_path / "llm" / "p2.json")
    seeded = StubModel({"hypothesis_id": "crypto:H9", "placebo_seed": 1, "rationale": "x"})
    with pytest.raises(ValueError, match="LLM_ANSWER_INVALID"):  # a seed from the model is not accepted
        llm.propose(world.orch, seeded, question="x", as_of="2030-01-01T12:00:00Z", proposal_id="cain:LLM-5",
                    out=tmp_path / "llm" / "p5.json")
    closed = StubModel({"hypothesis_id": "crypto:H9", "rationale": "tenta reabrir"})
    llm.propose(world.orch, closed, question="x", as_of="2030-01-01T12:00:00Z", proposal_id="cain:LLM-3",
                out=tmp_path / "llm" / "p3.json")
    reopened = json.loads((tmp_path / "llm" / "p3.json").read_text(encoding="utf-8"))
    assert world.orch.propose(reopened, as_of="2030-01-01T12:00:00Z")["receipt"]["reason_code"] in (
        "HYPOTHESIS_CLOSED", "OPEN_TASK_PENDING")


BRASILEIRAO_REQUEST = {
    "schema_version": "brasileirao-research-request/1",
    "request_id": "brasileirao:REQ-I-0001",
    "request_type": "WALKFORWARD_FORECAST_EVALUATION",
    "research_id": "brasileirao:RESEARCH-INTEGRATION-QUALIFICATION",
    "hypothesis_id": "brasileirao:QUAL-SERVING-REAL-001",
    "competition": "Brasileirão Série A",
    "season": 2024,
    "target": "OU25",
    "events": {"kickoff_from": "2024-07-01T00:00:00Z", "kickoff_to": "2024-10-01T00:00:00Z"},
    "data_cutoff": "2026-09-08T19:31:32Z",
    "decision_lead_minutes": 60,
    "references": {"dataset": {"name": "real-20260908", "version": "1"},
                   "model": {"name": "serving-baseline", "version": "1"},
                   "features": {"name": "elo-home-advantage", "version": "1"},
                   "baseline": {"name": "market", "version": "1"},
                   "cost_model": {"name": "close-slippage-tax", "version": "1"},
                   "odds": {"name": "sofascore-close", "version": "1"}},
    "priority_hint": "NORMAL",
}


class RefusingBrasileirao(StandInDomain):
    """Refuses every task (a terminal refusal): the task stops being open and never counts as an experiment that ran."""

    DOMAIN = "brasileirao"

    def submit_task(self, task, config):
        raw = v2.canonical(task["payload"])
        request = json.loads(raw)
        return {"submission_sha256": sha(raw), "request_id": request["request_id"], "client_ref": request["client_ref"],
                "status": "TEMPORAL_INTEGRITY_VIOLATION", "exit_code": 4, "reason": "TEMPORAL_INTEGRITY_VIOLATION"}


def test_llm_proposal_for_a_domain_whose_request_has_no_parameters(tmp_path):
    # the brasileirao request_schema has no parameters (additionalProperties false): the template, the probe and the
    # proposal keep the request without them (rc10 died reading parameters of the emitted tasks)
    from cain.orchestration import llm

    spool = Spool(tmp_path / "spool")
    orch = Orchestrator("brasileirao", tmp_path / "state")
    consumer = Consumer("brasileirao", spool, tmp_path / "consumer.sqlite", RefusingBrasileirao(), {"state": "unused"})
    seed = {"schema": "cain-proposal/1", "proposal_id": "cain:PROP-B1", "domain": "brasileirao",
            "request": copy.deepcopy(BRASILEIRAO_REQUEST), "based_on": [], "rationale": "seed", "source": "agenda"}
    assert orch.propose(seed, as_of=AS_OF)["receipt"]["decision"] == "ALLOW"
    orch.dispatch(spool)
    consumer.run_once()
    orch.ingest(spool)
    model = StubModel({"hypothesis_id": "brasileirao:QUAL-SERVING-REAL-001", "rationale": "x"})
    out = tmp_path / "llm" / "b1.json"
    llm.propose(orch, model, question="próximo", as_of="2030-01-01T11:00:00Z", proposal_id="cain:LLM-B1", out=out)
    proposal = json.loads(out.read_text(encoding="utf-8"))
    assert "parameters" not in proposal["request"]
    decision = orch.propose(proposal, as_of="2030-01-01T11:00:00Z")["receipt"]
    assert decision["decision"] == "ALLOW" and decision["task"] is not None


def test_llm_proposal_cli_requires_state_and_output(tmp_path, capsys):
    from cain.cli import main

    assert main(["research", "explain", "q", "--propose-for-domain", "crypto"]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "INPUT_INVALID"


def test_domain_refusal_code_is_remembered_and_the_hypothesis_is_not_proposed_again(world):
    world.domain.script = [("REJECTED", "HYPOTHESIS_NOT_ADMITTED")]
    cycle(world, 1)
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert [(f["object"]["status"], f["object"]["reason_code"]) for f in facts] == [
        ("REJECTED", "HYPOTHESIS_NOT_ADMITTED")]
    again = world.orch.propose(proposal(2), as_of="2030-01-01T11:00:00Z")["receipt"]
    assert (again["decision"], again["reason_code"], again["rule"], again["task"]) == (
        "REQUIRE_HUMAN", "HYPOTHESIS_NOT_ADMITTED_BY_DOMAIN", "R15", None)
    other = world.orch.propose(proposal(3, hypothesis_id="crypto:QUAL-SHADOW-REAL-002"), as_of="2030-01-01T12:00:00Z")
    assert other["receipt"]["decision"] == "ALLOW"


def test_the_same_experiment_under_another_request_id_is_not_run_again(world):
    cycle(world, 1)
    with world.orch.store.db() as db:
        (task,) = world.orch.store.view(db, "crypto", AS_OF)["tasks"]
    assert task["experiment_sha256"] == policy.experiment_digest(proposal(1)["request"])
    same = proposal(2, parameters=dict(REQUEST["parameters"], placebo_seed=1))  # only the request_id differs
    out = world.orch.propose(same, as_of="2030-01-01T11:00:00Z")["receipt"]
    assert (out["decision"], out["reason_code"], out["rule"], out["task"]) == (
        "DUPLICATE", "EQUIVALENT_REQUEST", "R17", None)
    # another placebo seed is another experiment
    assert world.orch.propose(proposal(3), as_of="2030-01-01T12:00:00Z")["receipt"]["decision"] == "ALLOW"


def test_free_text_refusal_reason_never_becomes_a_reason_code(world):
    leaked = "evento observado em 2026-09-07T00:00:00Z depois do corte"
    world.domain.script = [("TEMPORAL_INTEGRITY_VIOLATION", leaked)]
    cycle(world, 1)
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert [f["object"]["reason_code"] for f in facts] == [None]
    assert leaked.encode() not in (world.tmp / "state" / "memory.sqlite").read_bytes()


def test_llm_only_chooses_among_hypotheses_the_policy_would_accept_now(world, tmp_path):
    from cain.orchestration import llm

    for n in (1, 2, 3):  # three negative results in a row: REAL-001 enters COOLDOWN
        cycle(world, n, as_of=f"2030-01-01T1{n}:00:00Z")
    model = StubModel({"hypothesis_id": "crypto:QUAL-SHADOW-REAL-002",
                       "rationale": "REAL-001 teve 3 INCONCLUSIVE; QUAL-SHADOW-001 funcionou"})
    info = llm.propose(world.orch, model, question="próximo", as_of="2030-01-01T14:00:00Z",
                       proposal_id="cain:LLM-E1", out=tmp_path / "llm" / "e1.json")
    (prompt, _context, schema), = model.calls
    enum = schema["properties"]["hypothesis_id"]["enum"]
    assert "crypto:QUAL-SHADOW-REAL-001" not in enum and "crypto:QUAL-SHADOW-REAL-002" in enum
    summary = json.loads(prompt)["hypothesis_summary"]["crypto:QUAL-SHADOW-REAL-001"]
    assert summary == {"results": 3, "scientific_states": {"INCONCLUSIVE": 3}, "refusals": [], "eligible_now": False,
                       "not_eligible_reason": "NEGATIVE_STREAK"}
    assert info["rationale_check"] == {"mentioned": ["crypto:QUAL-SHADOW-001", "crypto:QUAL-SHADOW-REAL-001"],
                                       "without_evidence": ["crypto:QUAL-SHADOW-001"], "count_mismatches": [],
                                       "eligibility_mismatches": []}
    audit = json.loads((tmp_path / "llm" / "e1.audit.json").read_text(encoding="utf-8"))
    assert audit["eligibility"]["crypto:QUAL-SHADOW-REAL-001"]["rule"] == "R13"
    assert audit["rationale_check"] == info["rationale_check"]


def test_the_cain_assigns_an_unused_deterministic_placebo_seed(world, tmp_path):
    from cain.orchestration import llm

    cycle(world, 1)
    used = [1]
    assert llm.assign_seed("cain:LLM-S1", used) == llm.assign_seed("cain:LLM-S1", used)
    natural = llm.assign_seed("cain:LLM-S1", [])
    assert llm.assign_seed("cain:LLM-S1", [natural]) == (natural + 1) % 1_000_000
    model = StubModel({"hypothesis_id": "crypto:QUAL-SHADOW-REAL-002", "rationale": "x"})
    llm.propose(world.orch, model, question="x", as_of="2030-01-01T11:00:00Z", proposal_id="cain:LLM-S1",
                out=tmp_path / "llm" / "s1.json")
    seed = json.loads((tmp_path / "llm" / "s1.json").read_text(encoding="utf-8"))["request"]["parameters"]["placebo_seed"]
    assert seed == llm.assign_seed("cain:LLM-S1", used) and seed not in used


def test_llm_is_not_asked_when_no_hypothesis_is_eligible(world, tmp_path):
    from cain.orchestration import llm

    world.orch.propose(proposal(1), as_of=AS_OF)
    world.orch.dispatch(world.spool)  # the task is open: the policy abstains for every hypothesis
    model = StubModel({"hypothesis_id": "crypto:QUAL-SHADOW-REAL-002", "rationale": "x"})
    with pytest.raises(ValueError, match="NO_ELIGIBLE_HYPOTHESIS"):
        llm.propose(world.orch, model, question="x", as_of="2030-01-01T11:00:00Z", proposal_id="cain:LLM-E2",
                    out=tmp_path / "llm" / "e2.json")
    assert model.calls == [] and not (tmp_path / "llm" / "e2.json").exists()


def test_result_metrics_reach_the_memory_the_view_and_the_model_as_numbers_only(world, tmp_path):
    from cain.orchestration import llm

    world.domain.facts["crypto:REQ-I-0001"] = {
        "metrics": {"net_return_bps": -118, "net_ci_low_bps": -298, "net_ci_high_bps": 42, "sample_size": 52,
                    "gross_return_bps": -89},
        "data_cutoff": "2026-08-31T00:00:00Z"}
    cycle(world, 1)
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert [f["object"]["metrics"] for f in facts] == [
        {"net_ci_high_bps": 42, "net_ci_low_bps": -298, "net_return_bps": -118, "sample_size": 52}]
    with world.orch.store.db() as db:
        view = world.orch.store.view(db, "crypto", "2030-01-01T11:00:00Z")
    assert view["results"][0]["metrics"]["net_return_bps"] == -118
    model = StubModel({"hypothesis_id": "crypto:QUAL-SHADOW-REAL-002", "rationale": "x"})
    llm.propose(world.orch, model, question="próximo", as_of="2030-01-01T11:00:00Z", proposal_id="cain:LLM-M1",
                out=tmp_path / "llm" / "m1.json")
    (prompt, context, _schema), = model.calls
    shown = json.loads(prompt)["results"][0]["metrics"]
    assert shown == {"net_ci_high_bps": 42, "net_ci_low_bps": -298, "net_return_bps": -118, "sample_size": 52}
    assert context == llm.INSTRUCTION + llm.METRICS_NOTE
    assert b"2026-08-31T00:00:00Z" not in (world.tmp / "state" / "memory.sqlite").read_bytes()


def test_without_declared_numbers_the_fact_the_view_and_the_prompt_stay_as_before(world, tmp_path):
    from cain.orchestration import llm

    cycle(world, 1)  # the stand-in result carries no domain_facts.metrics
    facts = world.orch.store.memory.facts(as_of=world.orch.store.memory_head(), cubes=["crypto"])
    assert "metrics" not in facts[0]["object"]
    model = StubModel({"hypothesis_id": "crypto:QUAL-SHADOW-REAL-002", "rationale": "x"})
    llm.propose(world.orch, model, question="próximo", as_of="2030-01-01T11:00:00Z", proposal_id="cain:LLM-M2",
                out=tmp_path / "llm" / "m2.json")
    (prompt, context, _schema), = model.calls
    assert all("metrics" not in r for r in json.loads(prompt)["results"]) and context == llm.INSTRUCTION

"""Durable human approval and fork as primitives of the workflow engine."""

import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
from cain.research import ResearchService
from cain.research.workflows import Workflows
import test_research_l0 as cases
from test_agent_capabilities import FixtureModel

setup = cases.setup
HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"


class OtherModel(FixtureModel):
    model = "another-fixture-model"


def _prepared(setup):
    service, scope, ingest, _, policy = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))
    return service, scope, policy


def _to_first_generation(jobs, scope, model, run_id="run"):
    job = jobs.create(scope, "What does A support?", model, source_id="A", run_id=run_id)
    for _ in range(2):  # inspect, search: no generation, no approval
        job = jobs.advance(scope, job["id"], model)
    return jobs.advance(scope, job["id"], model)


def test_run_waiting_for_approval_survives_a_killed_process(setup):
    service, scope, policy = _prepared(setup)
    code = (
        "import sys, time\n"
        f"sys.path[:0] = [{str(HERE)!r}, {str(SRC)!r}]\n"
        "from cain.research import ResearchService\n"
        "from cain.research.workflows import Workflows\n"
        "from test_agent_capabilities import FixtureModel\n"
        f"service = ResearchService({str(service.path)!r}, {str(policy)!r})\n"
        f"scope = {scope!r}\n"
        "jobs, model = Workflows(service), FixtureModel()\n"
        "job = jobs.create(scope, 'What does A support?', model, source_id='A', run_id='durable')\n"
        "for _ in range(3):\n"
        "    job = jobs.advance(scope, 'durable', model)\n"
        "print(job['status'], model.calls, flush=True)\n"
        "time.sleep(120)\n"
    )
    process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True,
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    line = process.stdout.readline().split()
    assert line == ["awaiting_generation_approval", "0"]
    # The process dies while the run waits for a human: SIGKILL on POSIX, TerminateProcess on Windows.
    process.kill()
    assert process.wait(timeout=10) == (-signal.SIGKILL if hasattr(signal, "SIGKILL") else 1)
    # "Restart": a new process-level object reads only what was persisted.
    restarted, model = Workflows(ResearchService(service.path, policy)), FixtureModel()
    job = restarted.get(scope, "durable")
    assert job["status"] == "awaiting_generation_approval"
    assert job["pending_approval"]["step"] == "entities" and job["pending_approval"]["position"] == 2
    # The approver sees which evidence the search step found (found empty by the runtime demo).
    evidence = job["pending_approval"]["evidence_ids"]
    assert len(evidence) == 1 and evidence[0].endswith(":e")
    assert evidence == [e["reference_id"] for e in job["steps"][1]["result"]["evidence"]]
    for _ in range(4):
        job = restarted.decide(scope, "durable", "APPROVE", by="leo", note="reviewed the proposal")
        job = restarted.advance(scope, "durable", model)  # runs the approved step
        job = restarted.advance(scope, "durable", model)  # parks at the next approval (or completed)
    assert job["status"] == "completed" and model.calls == 4
    decisions = [e for e in job["approvals"] if e["kind"] == "approval.decided"]
    assert [(d["body"]["step"], d["body"]["by"]) for d in decisions] == [
        ("entities", "leo"), ("support", "leo"), ("challenge", "leo"), ("synthesis", "leo")]
    assert all(s["result"]["human_approval"]["by"] == "leo" for s in job["steps"][2:])
    assert restarted.verify_events()["status"] == "intact"


def test_rejection_executes_no_side_effects(setup):
    service, scope, _ = _prepared(setup)
    jobs, model = Workflows(service), FixtureModel()
    job = _to_first_generation(jobs, scope, model)
    assert job["status"] == "awaiting_generation_approval" and model.calls == 0
    steps_before = len(job["steps"])
    job = jobs.decide(scope, "run", "REJECT", by="leo", note="question is out of scope")
    assert job["status"] == "rejected"
    for kwargs in ({}, {"approve_generation": True}, {"recover": True}):
        job = jobs.advance(scope, "run", model, **kwargs)
        assert job["status"] == "rejected"
    assert model.calls == 0 and len(job["steps"]) == steps_before
    assert jobs.cancel(scope, "run")["status"] == "rejected"
    with pytest.raises(ValueError, match="No pending approval"):
        jobs.decide(scope, "run", "APPROVE", by="leo")


def test_edit_records_the_diff_and_the_step_uses_the_edited_question(setup):
    service, scope, _ = _prepared(setup)
    jobs, model = Workflows(service), FixtureModel()
    _to_first_generation(jobs, scope, model)
    with pytest.raises(ValueError):
        jobs.decide(scope, "run", "EDIT", by="leo")
    with pytest.raises(ValueError):
        jobs.decide(scope, "run", "APPROVE", by="")
    job = jobs.decide(scope, "run", "EDIT", by="leo", question="Who reviewed Report A?")
    decided = [e for e in job["approvals"] if e["kind"] == "approval.decided"][0]["body"]
    assert decided["diff"] == {"question": ["What does A support?", "Who reviewed Report A?"]}
    job = jobs.advance(scope, "run", model)
    step = job["steps"][-1]
    assert step["result"]["edited_question"] == "Who reviewed Report A?"
    assert step["result"]["human_approval"]["decision"] == "EDIT"


def test_explicit_approve_flag_is_recorded_and_attributed(setup):
    service, scope, _ = _prepared(setup)
    jobs, model = Workflows(service), FixtureModel()
    job = jobs.create(scope, "What does A support?", model, source_id="A", run_id="flag")
    for _ in range(6):
        job = jobs.advance(scope, "flag", model, approve_generation=True)
    assert job["status"] == "completed"
    decided = [e["body"] for e in job["approvals"] if e["kind"] == "approval.decided"]
    assert len(decided) == 4 and {d["by"] for d in decided} == {"leo"}
    assert all(d["note"] == "explicit approve_generation on advance" for d in decided)


def test_fork_reuses_earlier_steps_and_reexecutes_only_from_the_fork_point(setup):
    service, scope, _ = _prepared(setup)
    jobs, parent_model = Workflows(service), FixtureModel()
    job = jobs.create(scope, "What does A support?", parent_model, source_id="A", run_id="parent")
    for _ in range(6):
        job = jobs.advance(scope, "parent", parent_model, approve_generation=True)
    assert job["status"] == "completed" and parent_model.calls == 4
    with pytest.raises(ValueError):
        jobs.fork(scope, "parent", 7, OtherModel())
    with pytest.raises(ValueError):
        jobs.fork(scope, "parent", 3, OtherModel(), prompt_version="research-workflow/1")
    child_model = OtherModel()
    child = jobs.fork(scope, "parent", 3, child_model, new_run_id="child")
    assert child["parent_run_id"] == "parent" and child["fork_point"] == 3
    assert [s["inherited_from"] for s in child["steps"]] == ["parent:0", "parent:1", "parent:2"]
    assert [s["result"] for s in child["steps"]] == [s["result"] for s in job["steps"][:3]]
    assert child["model_calls"] == 0 and child["request"]["model"]["model"] == "another-fixture-model"
    assert jobs.advance(scope, "child", child_model)["status"] == "awaiting_generation_approval"
    for _ in range(3):
        jobs.decide(scope, "child", "APPROVE", by="leo")
        jobs.advance(scope, "child", child_model)
        child = jobs.advance(scope, "child", child_model)
    assert child["status"] == "completed"
    assert child_model.calls == 3 and parent_model.calls == 4  # only positions 3, 4, 5 ran again
    assert child["model_calls"] == 3
    forked = [e for e in jobs.events(scope, "child") if e["kind"] == "run.forked"][0]["body"]
    assert forked["inherited_positions"] == [0, 1, 2] and forked["child_model"] == "another-fixture-model"
    # The parent's approvals never authorize the child.
    assert all(e["run_id"] == "child" for e in jobs.events(scope, "child"))


def test_provenance_reads_human_approvals_and_forks(setup, tmp_path):
    from cain.memory.store import MemoryStore
    from cain.provenance.graph import ProvenanceGraph

    service, scope, _ = _prepared(setup)
    jobs, model = Workflows(service), FixtureModel()
    jobs.create(scope, "What does A support?", model, source_id="A", run_id="parent")
    for _ in range(6):
        jobs.advance(scope, "parent", model, approve_generation=True)
    jobs.fork(scope, "parent", 3, OtherModel(), new_run_id="child")
    child_model = OtherModel()
    jobs.advance(scope, "child", child_model)
    jobs.decide(scope, "child", "APPROVE", by="leo")
    jobs.advance(scope, "child", child_model)
    memory = MemoryStore(tmp_path / "memory.db")
    graph = ProvenanceGraph(memory, workflow_db=service.path)
    now = memory.now()
    child_decision = next(f"decision:{e['event_id']}" for e in jobs.events(scope, "child")
                          if e["kind"] == "approval.decided")
    parent_decisions = {e["body"]["position"]: f"decision:{e['event_id']}" for e in jobs.events(scope, "parent")
                        if e["kind"] == "approval.decided"}
    why = graph.why("run:child", as_of=now)
    # The child rests on its own approval and on the steps it inherited (step 2 was generated under the
    # parent's approval of position 2), never on the parent's later steps or their approvals.
    assert sorted(why["decisions"]) == sorted([child_decision, parent_decisions[2]])
    assert {"step:child#0", "step:parent#0", "step:parent#2", "step:child#3"} <= {n["node"] for n in why["nodes"]}
    assert "step:parent#3" not in {n["node"] for n in why["nodes"]}
    assert not {parent_decisions[p] for p in (3, 4, 5)} & set(why["decisions"])
    assert any(e["origin"].endswith("by leo") for e in why["edges"] if e["from"] == child_decision)
    # The step the approval released depends on that approval only, never on the parent's approvals.
    released = {n["node"] for n in graph.trace("step:child#3", as_of=now)["nodes"]}
    assert child_decision in released and not set(parent_decisions.values()) & released
    assert {n["node"] for n in graph.impact(child_decision, as_of=now)["nodes"]} == {"step:child#3", "run:child"}


def test_fork_refuses_a_changed_corpus(setup):
    service, scope, _ = _prepared(setup)
    _, _, ingest, _, _ = setup
    jobs, model = Workflows(service), FixtureModel()
    job = jobs.create(scope, "What does A support?", model, source_id="A", run_id="p")
    jobs.advance(scope, "p", model)
    ingest(cases.publication(("B",), text="Bob reviewed Report B."))
    with pytest.raises(ValueError):
        jobs.fork(scope, job["id"], 1, model)


def test_event_chain_detects_tampering(setup):
    service, scope, _ = _prepared(setup)
    jobs, model = Workflows(service), FixtureModel()
    _to_first_generation(jobs, scope, model)
    jobs.decide(scope, "run", "APPROVE", by="leo")
    assert jobs.verify_events()["status"] == "intact"
    db = sqlite3.connect(service.path)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM workflow_events")
    db.execute("DROP TRIGGER workflow_events_no_update")
    db.execute("UPDATE workflow_events SET body = replace(body, '\"by\":\"leo\"', '\"by\":\"mallory\"') WHERE seq = 2")
    db.commit()
    db.close()
    report = jobs.verify_events()
    assert report["status"] == "broken" and report["broken_at"] == 2


def test_api_decision_and_fork_routes(setup, tmp_path):
    service, scope, policy = _prepared(setup)
    app = create_app(tmp_path / "workspace.db", llm=FixtureModel(), research_policy=policy,
                     research_db=service.path, trusted_hosts=("testserver",))
    with TestClient(app) as client:
        job = client.post("/research/jobs", json={"question": "What does A support?", "source_id": "A",
                                                  "run_id": "api"}).json()
        for _ in range(3):
            job = client.post("/research/jobs/api/advance", json={}).json()
        assert job["status"] == "awaiting_generation_approval" and job["pending_approval"]["step"] == "entities"
        bad = client.post("/research/jobs/api/decision", json={"decision": "MAYBE"})
        assert bad.status_code == 422
        job = client.post("/research/jobs/api/decision", json={"decision": "APPROVE", "note": "ok"}).json()
        assert job["status"] == "ready"
        assert job["approvals"][-1]["body"]["by"] == "leo"
        job = client.post("/research/jobs/api/advance", json={}).json()
        assert len(job["steps"]) == 3
        child = client.post("/research/jobs/api/fork", json={"from_step": 2}).json()
        assert child["parent_run_id"] == "api" and len(child["steps"]) == 2
        assert client.post("/research/jobs/api/fork", json={"from_step": 9}).status_code == 422

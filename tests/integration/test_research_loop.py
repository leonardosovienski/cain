"""Governed research loop against a real subprocess evaluator (a small frozen script in tmp_path)."""

import json
from pathlib import Path
import sqlite3
import sys

import pytest

from cain.loop.engine import ResearchLoop, decide_gate, run_holdout
from cain.loop.ledger import LoopLedger
from cain.loop.proposers import NeighborProposer
from cain.loop.world import WorldError, file_sha256, load_world

EVALUATOR = '''
import json, math, sys, time
request = json.load(sys.stdin)
p, stage = request["params"], request["stage"]
if p.get("window") == 13:
    sys.exit("simulated crash in the evaluator")
if p.get("window") == 17:
    time.sleep(30)
loss = (p["window"] - 8) ** 2 / 100 + (p["l2"] - 0.3) ** 2 + (0.05 if stage == "walk_forward" else 0)
out = {"stage": stage, "ok": True, "metrics": {"loss": loss}}
if stage == "sanity":
    out["checks"] = {"leakage": "none", "rows": 100}
    out["signal"] = [math.sin(i * p["window"] / 10) for i in range(40)]
if stage == "holdout":
    out["metrics"] = {"loss": loss + 0.01}
print(json.dumps(out))
'''


def write_world(tmp_path, *, gates='["holdout"]', stages='["sanity", "in_sample", "walk_forward", "holdout"]',
                attempts=12, stagnation=4, evaluator_text=EVALUATOR, extra=""):
    script = tmp_path / "evaluator.py"
    script.write_text(evaluator_text, encoding="utf-8")
    world = tmp_path / "research_world.toml"
    world.write_text(f'''
[world]
id = "fixture-world"
version = 1
predictor = "fixture"
hypothesis = "H-fixture"
description = "a smoother window and moderate l2 lower the loss"

[data]
allowed = [{{path = "train.csv", sha256 = "{'0' * 64}"}}]
holdout = [{{path = "holdout.csv", sha256 = "{'1' * 64}"}}]

[metric]
primary = "loss"
direction = "minimize"
min_improvement = 0.001

[editable]
files = []
[editable.parameters.window]
kind = "features"
type = "int"
min = 2
max = 20
step = 2
baseline = 4
[editable.parameters.l2]
kind = "model"
type = "float"
min = 0.0
max = 1.0
step = 0.1
baseline = 0.9

[budget]
attempt_seconds = 5
total_attempts = {attempts}
total_seconds = 120
max_variants_per_hypothesis = 20

[stagnation]
attempts_without_improvement = {stagnation}

[gates]
human = {gates}

[cascade]
stages = {stages}

[evaluator]
python = '{sys.executable}'
entrypoint = '{script}'
files = [{{path = '{script}', sha256 = "{file_sha256(script)}"}}]
{extra}
''', encoding="utf-8")
    return load_world(world), script


class Scripted:
    """Proposer that replays a fixed list of proposals."""

    name = "scripted/1"

    def __init__(self, proposals):
        self.proposals = list(proposals)

    def propose(self, world, kind, status, best):
        if not self.proposals:
            raise RuntimeError("script exhausted")
        return self.proposals.pop(0)


def kinds(ledger, loop_id):
    return [e["kind"] for e in ledger.events(loop_id)]


def test_proposal_outside_the_editable_surface_is_blocked_and_recorded(tmp_path):
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=3)
    ledger = LoopLedger(tmp_path / "ledger.db")
    proposer = Scripted([
        {"params": {"window": 6}, "files": ["../evaluator.py"], "description": "features: tune window"},
        {"params": {"learning_rate": 0.1}, "description": "model: new knob"},
    ])
    status = ResearchLoop(world, ledger, proposer).run(loop_id="loop:surface")
    blocked = [e["body"] for e in ledger.events("loop:surface") if e["kind"] == "experiment.blocked"]
    assert [b["reason"] for b in blocked] == ["OUTSIDE_EDITABLE_SURFACE"] * 2
    assert "file '../evaluator.py' is outside the editable surface" in blocked[0]["violations"]
    assert "parameter 'learning_rate' is not editable" in blocked[1]["violations"]
    assert status["attempts"] == 3 and status["stopped"]["reason"] == "budget_attempts"
    assert status["outcomes"] == {"experiment.finished": 1, "experiment.blocked": 2}


def test_stagnation_and_budget_stop_the_loop(tmp_path):
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', stagnation=2, attempts=50)
    ledger = LoopLedger(tmp_path / "ledger.db")
    # Moving l2 up from 0.9 only makes the loss worse: two attempts without improvement → stagnation.
    worse = Scripted([{"params": {"l2": 1.0}, "description": "model: tune l2"},
                      {"params": {"window": 2}, "description": "features: tune window"}])
    status = ResearchLoop(world, ledger, worse).run(loop_id="loop:stagnant")
    assert status["stopped"]["reason"] == "stagnation" and status["attempts"] == 3
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=4, stagnation=10)
    status = ResearchLoop(world, ledger, NeighborProposer()).run(loop_id="loop:budget")
    assert status["stopped"]["reason"] == "budget_attempts" and status["attempts"] == 4
    ticks = iter(range(0, 10_000, 100))
    status = ResearchLoop(world, ledger, NeighborProposer(), clock=lambda: next(ticks)).run(loop_id="loop:time")
    assert status["stopped"]["reason"] == "budget_time"


def test_crash_and_timeout_are_in_the_ledger_and_in_the_attempt_count(tmp_path):
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=3)
    ledger = LoopLedger(tmp_path / "ledger.db")
    proposer = Scripted([{"params": {"window": 13}, "description": "features: tune window"},
                         {"params": {"window": 17}, "description": "features: tune window"}])
    status = ResearchLoop(world, ledger, proposer).run(loop_id="loop:crash")
    crashed = [e["body"] for e in ledger.events("loop:crash") if e["kind"] == "experiment.crashed"]
    assert [(c["stage"], c["reason"]) for c in crashed] == [("sanity", "EXIT_NONZERO"), ("sanity", "TIMEOUT")]
    assert "simulated crash" in crashed[0]["detail"]
    assert status["attempts"] == 3 and status["outcomes"]["experiment.crashed"] == 2


def test_redundant_candidate_is_discarded_before_any_backtest(tmp_path):
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=2)
    ledger = LoopLedger(tmp_path / "ledger.db")
    calls = []

    def counting(world, stage, params, *, timeout):
        from cain.loop.evaluator import run_stage

        calls.append(stage)
        return run_stage(world, stage, params, timeout=timeout)

    # l2 does not change the signal: same signal as the baseline (correlation 1.0) → redundant.
    proposer = Scripted([{"params": {"l2": 0.5}, "description": "model: tune l2"}])
    ResearchLoop(world, ledger, proposer, runner=counting).run(loop_id="loop:redundant")
    discarded = [e["body"] for e in ledger.events("loop:redundant") if e["kind"] == "experiment.discarded"]
    assert discarded[0]["reason"] == "REDUNDANT" and discarded[0]["correlation"] >= 0.99
    assert calls == ["sanity", "in_sample", "walk_forward", "sanity"]  # no backtest for the redundant one


def test_evaluator_change_stops_the_loop(tmp_path):
    world, script = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=5)
    ledger = LoopLedger(tmp_path / "ledger.db")

    class Tamperer(Scripted):
        def propose(self, world, kind, status, best):
            tampered = EVALUATOR.replace("(0.05 if", "(-9 if")  # "improve" the judge
            assert tampered != EVALUATOR
            script.write_text(tampered, encoding="utf-8")
            return {"params": {"window": 6}, "description": "features: tune window"}

    status = ResearchLoop(world, ledger, Tamperer([])).run(loop_id="loop:tamper")
    assert status["stopped"]["reason"] == "evaluator_changed"
    assert status["stopped"]["evaluator"]["mismatches"][0]["path"] == str(script)
    assert status["outcomes"] == {"experiment.finished": 1}  # only the baseline ran


def test_holdout_only_after_a_recorded_human_approval(tmp_path):
    world, _ = write_world(tmp_path, attempts=10)
    ledger = LoopLedger(tmp_path / "ledger.db")
    status = ResearchLoop(world, ledger, NeighborProposer()).run(loop_id="loop:gate")
    assert status["stopped"]["reason"] == "human_gate" and status["gates"][0]["gate"] == "holdout"
    assert "holdout" not in json.dumps([e["body"].get("results") for e in ledger.events("loop:gate")])
    with pytest.raises(PermissionError):
        run_holdout(world, ledger, "loop:gate")
    decide_gate(ledger, "loop:gate", decision="APPROVE", by="leo", note="walk-forward gain is worth one look")
    result = run_holdout(world, ledger, "loop:gate")
    assert result["ok"] and result["metrics"]["loss"] > 0
    with pytest.raises(ValueError, match="spent once"):
        run_holdout(world, ledger, "loop:gate")
    assert ledger.verify()["status"] == "intact"


def test_new_hypothesis_gate_and_variants(tmp_path):
    world, _ = write_world(tmp_path, gates='["holdout", "new_hypothesis"]', attempts=10,
                           stages='["sanity", "in_sample", "walk_forward"]')
    ledger = LoopLedger(tmp_path / "ledger.db")
    proposer = Scripted([{"params": {"window": 6}, "description": "a smoother window and moderate l2 lower the loss"},
                         {"params": {"l2": 0.5}, "description": "regime switching explains the residuals"}])
    status = ResearchLoop(world, ledger, proposer).run(loop_id="loop:novelty")
    registered = [e["body"] for e in ledger.events("loop:novelty") if e["kind"] == "hypothesis.registered"]
    assert [h["source"] for h in registered] == ["world file", "proposal"]
    assert status["stopped"] == {**status["stopped"], "reason": "human_gate", "gate": "new_hypothesis"}


def test_world_file_is_validated_and_ledger_is_append_only(tmp_path):
    with pytest.raises(WorldError, match="holdout"):
        write_world(tmp_path, gates="[]")
    with pytest.raises(WorldError, match="cascade"):
        write_world(tmp_path, stages='["in_sample", "sanity"]')
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=1)
    ledger = LoopLedger(tmp_path / "ledger.db")
    ResearchLoop(world, ledger, NeighborProposer()).run(loop_id="loop:chain")
    db = sqlite3.connect(ledger.path)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM loop_events")
    db.execute("DROP TRIGGER loop_events_no_update")
    db.execute("UPDATE loop_events SET body = replace(body, 'budget_attempts', 'stagnation') WHERE kind='loop.stopped'")
    db.commit()
    db.close()
    assert ledger.verify()["status"] == "broken"


def test_cli_run_and_status(tmp_path, capsys):
    from cain.cli import main

    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=3)
    db = str(tmp_path / "cli-ledger.db")
    assert main(["loop", "--db", db, "run", "--predictor", "fixture", "--world", world["_path"],
                 "--proposer", "neighbor", "--loop-id", "loop:cli"]) == 0
    run = json.loads(capsys.readouterr().out)
    assert run["attempts"] == 3 and run["stopped"]["reason"] == "budget_attempts"
    assert main(["loop", "--db", db, "status", "loop:cli"]) == 0
    assert json.loads(capsys.readouterr().out)["events"] == run["events"]
    assert main(["loop", "--db", db, "run", "--predictor", "other", "--world", world["_path"]]) == 1
    assert Path(db).exists()


def test_repeated_proposal_is_a_duplicate_and_never_reaches_the_evaluator(tmp_path):
    # Found by the real cycle: at temperature 0 the local model proposed the same change three times.
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=3)
    ledger = LoopLedger(tmp_path / "ledger.db")
    calls = []

    def counting(world, stage, params, *, timeout):
        from cain.loop.evaluator import run_stage

        calls.append(stage)
        return run_stage(world, stage, params, timeout=timeout)

    same = {"params": {"window": 10}, "description": "features: tune window"}
    ResearchLoop(world, ledger, Scripted([same, dict(same)]), runner=counting).run(loop_id="loop:dup")
    discarded = [e["body"] for e in ledger.events("loop:dup") if e["kind"] == "experiment.discarded"]
    assert discarded == [{"attempt": 3, "reason": "DUPLICATE", "duplicate_of_attempt": 2}]
    assert len(calls) == 6  # baseline and the first proposal only
    log = ledger.status("loop:dup")["attempt_log"]
    assert [(a["attempt"], a["outcome"], a["reason"]) for a in log] == [
        (1, "finished", None), (2, "finished", None), (3, "discarded", "DUPLICATE")]


def test_redundancy_measure_for_parameter_variants(tmp_path):
    extra = '\n[redundancy]\nmeasure = "max_abs_diff"\nthreshold = 0.001\n'
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=3, extra=extra)
    ledger = LoopLedger(tmp_path / "ledger.db")
    # l2 leaves the signal identical (max diff 0) → redundant; window 5 changes it → evaluated.
    proposer = Scripted([{"params": {"l2": 0.5}, "description": "model: tune l2"},
                         {"params": {"window": 5}, "description": "features: tune window"}])
    ResearchLoop(world, ledger, proposer).run(loop_id="loop:measure")
    events = ledger.events("loop:measure")
    discarded = [e["body"] for e in events if e["kind"] == "experiment.discarded"]
    assert discarded[0]["reason"] == "REDUNDANT" and discarded[0]["measure"] == "max_abs_diff"
    assert discarded[0]["max_abs_diff"] == 0
    assert [e["body"]["attempt"] for e in events if e["kind"] == "experiment.finished"] == [1, 3]
    bad = '\n[redundancy]\nmeasure = "vibes"\n'
    with pytest.raises(WorldError, match="redundancy.measure"):
        write_world(tmp_path, extra=bad)


def test_local_model_proposer_sees_attempts_and_its_proposals_go_through_the_guard(tmp_path):
    from dataclasses import dataclass, field

    from cain.loop.proposers import LocalModelProposer

    @dataclass
    class FakeStructured:
        answers: list
        seed: int = 42
        last_metadata: dict = field(default_factory=dict)
        prompts: list = field(default_factory=list)

        def generate_json(self, prompt, context, schema):
            self.prompts.append(json.loads(prompt))
            return json.dumps(self.answers.pop(0))

    answers = [{"parameter": "window", "value": "6", "hypothesis": "a smoother window", "rationale": "less noise"},
               {"parameter": "l2", "value": "7.5", "hypothesis": "much stronger shrinkage", "rationale": "overfit"},
               {"parameter": "window", "value": "six", "hypothesis": "a smoother window", "rationale": "typo"}]
    provider = FakeStructured(answers)
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=4)
    ledger = LoopLedger(tmp_path / "ledger.db")
    status = ResearchLoop(world, ledger, LocalModelProposer(provider)).run(loop_id="loop:llm")
    log = status["attempt_log"]
    assert [(a["changes"], a["outcome"]) for a in log[1:]] == [
        ({"window": 6}, "finished"), ({"l2": 7.5}, "blocked"), ({"window": "six"}, "blocked")]
    # The model saw every earlier attempt with its outcome, including the blocked one.
    seen = provider.prompts[2]["attempts_so_far"]
    assert [(a["changes"], a["outcome"]) for a in seen] == [(a["changes"], a["outcome"]) for a in log[:3]]
    assert provider.prompts[0]["editable_parameters"].keys() == {"window"}  # features turn first


def test_cli_decide_holdout_and_verify(tmp_path, capsys):
    from cain.cli import main

    world, _ = write_world(tmp_path, attempts=10)
    db = str(tmp_path / "gate.db")
    assert main(["loop", "--db", db, "run", "--predictor", "fixture", "--world", world["_path"],
                 "--loop-id", "loop:gate-cli"]) == 0
    assert json.loads(capsys.readouterr().out)["stopped"]["gate"] == "holdout"
    assert main(["loop", "--db", db, "holdout", "loop:gate-cli", "--world", world["_path"]]) == 1
    capsys.readouterr()
    assert main(["loop", "--db", db, "decide", "loop:gate-cli", "--decision", "APPROVE", "--by", "leo"]) == 0
    capsys.readouterr()
    assert main(["loop", "--db", db, "holdout", "loop:gate-cli", "--world", world["_path"]]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert main(["loop", "--db", db, "verify"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "intact"
    assert main(["loop", "--db", db, "status"]) == 0
    assert [loop["loop_id"] for loop in json.loads(capsys.readouterr().out)["loops"]] == ["loop:gate-cli"]

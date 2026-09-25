"""Typed provenance, cascading invalidation, gen_ai spans and faithfulness with a confidence interval."""

from datetime import datetime, timedelta, timezone
import json
import random

import pytest

from cain.claims.faithfulness import estimate, monthly_sample
from cain.memory.store import MemoryStore, MemoryStoreError
from cain.provenance.graph import ProvenanceGraph

TEXT = "The backtest covered 49 rebalance periods. Net excess return averaged 29 basis points per period."


@pytest.fixture
def world(tmp_path):
    memory = MemoryStore(tmp_path / "memory.db")
    doc = memory.record_document("stocks", "report", TEXT, published_at=datetime.now(timezone.utc) - timedelta(days=1),
                                 source="fixture")
    q1, q2 = "covered 49 rebalance periods", "averaged 29 basis points"
    e1 = memory.record_evidence("stocks", doc["id"], TEXT.index(q1), TEXT.index(q1) + len(q1), q1)
    e2 = memory.record_evidence("stocks", doc["id"], TEXT.index(q2), TEXT.index(q2) + len(q2), q2)
    claims = {}
    for name, evidence in (("c1", [e1["id"]]), ("c2", [e1["id"], e2["id"]]), ("c3", [e2["id"]])):
        claims[name] = memory.record_claim("stocks", f"claim {name}", source_document_id=doc["id"], char_start=0,
                                           char_end=10, evidence_ids=evidence)["id"]
    verifier = memory.assess_claim(claims["c2"], "SUPPORTED", rule="two-verifiers-agree/1", assessed_by="verifiers",
                                   verifier_scores={"evidence_ids": [e1["id"], e2["id"]]},
                                   review_state="not_applicable")
    human = memory.assess_claim(claims["c2"], "SUPPORTED", rule="human-review/1", assessed_by="human:leo",
                                note="checked the report")
    graph = ProvenanceGraph(memory)
    graph.relate("decision:publish-report", "USED", claims["c1"], by="leo", note="report cites c1")
    return memory, graph, doc, e1["id"], e2["id"], claims, verifier["event_id"], human["event_id"]


def test_invalidating_an_evidence_flags_every_dependent_and_deletes_nothing(world):
    memory, graph, doc, e1, e2, claims, verifier, human = world
    impact = graph.impact(e1, as_of=memory.now())
    reached = {n["node"] for n in impact["nodes"]}
    assert {claims["c1"], claims["c2"], verifier, "decision:publish-report", human} <= reached
    assert claims["c3"] not in reached and e2 not in reached
    before = memory.now()
    result = graph.invalidate(e1, by="leo", reason="the quote was taken from a draft")
    flagged = {f["node"]: f["kind"] for f in result["flagged"]}
    assert flagged[claims["c1"]] == "claim" and flagged[claims["c2"]] == "claim"
    # a "decision:" node is a decision (it was "other" before the graph knew decisions: 2026-09-25 review)
    assert flagged["decision:publish-report"] == "decision" and flagged[verifier] == "assessment"
    now = memory.now()
    states = {c["id"]: (c["status"], c["review_state"]) for c in memory.claims(as_of=now, cubes=["stocks"])}
    assert states[claims["c1"]] == ("INCONCLUSIVE", "needs_human_review")
    assert states[claims["c2"]] == ("INCONCLUSIVE", "needs_human_review")
    assert states[claims["c3"]] == ("INCONCLUSIVE", "pending_verification")  # untouched
    # Nothing deleted: the evidence and the earlier SUPPORTED reading are still there as of before.
    assert {e["id"] for e in memory.evidence(as_of=now, cubes=["stocks"])} == {e1, e2}
    old = {c["id"]: c["status"] for c in memory.claims(as_of=before, cubes=["stocks"])}
    assert old[claims["c2"]] == "SUPPORTED"
    assert {f["to"] for f in graph.flags(as_of=now)} == {n for n, k in flagged.items() if k != "claim"}
    assert any(n["node"].startswith("invalidation:") for n in graph.trace(e1, as_of=now)["nodes"])
    assert memory.verify()["status"] == "intact"


def test_why_returns_the_complete_chain_of_a_decision(world):
    memory, graph, doc, e1, e2, claims, verifier, human = world
    chain = graph.why(human, as_of=memory.now())
    assert chain["claims"] == [claims["c2"]]
    assert sorted(chain["evidence"]) == sorted([e1, e2]) and chain["documents"] == [doc["id"]]
    decision = graph.why("decision:publish-report", as_of=memory.now())
    assert decision["claims"] == [claims["c1"]] and decision["evidence"] == [e1]
    with pytest.raises(MemoryStoreError):
        graph.relate("a", "CAUSES", "b", by="leo")


def test_model_and_tool_calls_become_gen_ai_spans(tmp_path):
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from cain.inference.recorder import InferenceStore, attach
    from cain.llm import OllamaLLM
    from cain.loop.engine import ResearchLoop
    from cain.loop.ledger import LoopLedger
    from cain.loop.proposers import NeighborProposer
    from cain.observability import semconv as sc
    from cain.observability import tracing
    from test_inference_recorder import FakeOllama
    from test_research_loop import write_world

    exporter = InMemorySpanExporter()
    tracing.configure(exporter=exporter, simple=True)
    fake = FakeOllama()
    try:
        llm = attach(OllamaLLM(model="fixture:1", base_url=fake.url, think=False, timeout=10),
                     InferenceStore(tmp_path / "inference.db"))
        llm.generate("a question", "system")
        world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]', attempts=2)
        ResearchLoop(world, LoopLedger(tmp_path / "ledger.db"), NeighborProposer()).run(loop_id="loop:spans")
    finally:
        fake.stop()
        tracing.shutdown()
    spans = exporter.get_finished_spans()
    model = next(s for s in spans if s.attributes.get(sc.OPERATION_NAME) == sc.OPERATION_TEXT_COMPLETION)
    assert model.name == "text_completion fixture:1"
    assert model.attributes[sc.REQUEST_MODEL] == "fixture:1" and model.attributes[sc.PROVIDER_NAME] == "ollama"
    assert model.attributes[sc.USAGE_OUTPUT_TOKENS] == 7 and model.attributes[sc.REQUEST_SEED] == 42
    assert model.attributes[sc.CAIN_CALL_ID].startswith("inference:")
    tools = [s for s in spans if s.attributes.get(sc.OPERATION_NAME) == sc.OPERATION_EXECUTE_TOOL]
    assert [s.attributes[sc.TOOL_NAME] for s in tools][:3] == ["evaluator.sanity", "evaluator.in_sample",
                                                                "evaluator.walk_forward"]
    attempts = {s.context.span_id: s for s in spans if s.name.startswith("loop attempt")}
    assert all(t.parent is not None and t.parent.span_id in attempts for t in tools)


def test_span_duration_survives_a_wall_clock_step_back(monkeypatch):
    # Found in MLflow: an evaluator span with a negative duration (the WSL2 wall clock stepped back).
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from cain.observability import tracing

    exporter = InMemorySpanExporter()
    tracing.configure(exporter=exporter, simple=True)
    try:
        started = tracing.start()
        real = tracing.time.time_ns
        monkeypatch.setattr(tracing.time, "time_ns", lambda: real() - 2_000_000_000)  # 2 s back
        tracing.record_span("execute_tool evaluator.sanity", started, {"cain.outcome": "ok"}, kind="internal")
    finally:
        monkeypatch.undo()
        tracing.shutdown()
    span = exporter.get_finished_spans()[0]
    assert span.end_time >= span.start_time


def test_faithfulness_estimate_covers_the_truth_and_the_sample_is_deterministic():
    rng = random.Random(7)
    truth = {f"claim:{i}": int(rng.random() < 0.7) for i in range(400)}
    real = sum(truth.values()) / len(truth)
    sample = monthly_sample(list(truth), "2026-09", 60)
    assert sample == monthly_sample(list(reversed(list(truth))), "2026-09", 60)
    assert sample != monthly_sample(list(truth), "2026-10", 60)
    widths = {}
    for accuracy in (0.95, 0.6):
        automatic = {c: v if rng.random() < accuracy else 1 - v for c, v in truth.items()}
        result = estimate(automatic, {c: truth[c] for c in sample})
        low, high = result["ppi"]["ci95"]
        assert low <= real <= high  # valid with a good or a poor proxy (the rectifier absorbs the bias)
        classical_low, classical_high = result["classical"]["ci95"]
        widths[accuracy] = (high - low, classical_high - classical_low)
    assert widths[0.95][0] < widths[0.95][1]  # a good proxy narrows the interval; a poor one does not
    with pytest.raises(ValueError):
        estimate(automatic, {"claim:unknown": 1})


def test_cli_trace_why_impact_invalidate_and_faithfulness(world, tmp_path, capsys):
    from cain.cli import main

    memory, graph, doc, e1, e2, claims, verifier, human = world
    db = str(memory.path)
    assert main(["why", human, "--as-of", "now", "--db", db]) == 0
    assert json.loads(capsys.readouterr().out)["claims"] == [claims["c2"]]
    assert main(["impact", e2, "--as-of", "now", "--db", db]) == 0
    assert claims["c3"] in {n["node"] for n in json.loads(capsys.readouterr().out)["nodes"]}
    assert main(["relate", "decision:x", "USED", claims["c3"], "--by", "leo", "--db", db]) == 0
    capsys.readouterr()
    assert main(["invalidate", e2, "--by", "leo", "--reason", "source retracted", "--db", db]) == 0
    assert "decision:x" in {f["node"] for f in json.loads(capsys.readouterr().out)["flagged"]}
    assert main(["trace", "decision:x", "--as-of", "now", "--db", db]) == 0
    capsys.readouterr()
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({claims["c1"]: 1}), encoding="utf-8")
    assert main(["claims", "--db", db, "faithfulness", "--labels", str(labels), "--as-of", "now",
                 "--cube", "stocks"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["labelled"] == 1 and out["classical"]["estimate"] == 1.0

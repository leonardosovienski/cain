import json

import pytest

from cain.evaluation import EvaluationConfig, run_smoke
from cain.evaluation.__main__ import main
from cain.evaluation.budget import CharacterCounter, RecordingLLM
from cain.evaluation.harness import load_design, run_construct_pilot
from cain.evaluation.metrics import (
    agreement,
    convergence,
    cosine_distance,
    delegation_metrics,
    embedding_distribution,
)


@pytest.fixture(scope="module")
def smoke(tmp_path_factory):
    output = tmp_path_factory.mktemp("evaluation")
    path = run_smoke(output, EvaluationConfig(run_id="fixture-smoke", seed=31))
    rows = [json.loads(line) for line in (path / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    return path, rows


def test_design_has_disjoint_surfaces_and_prior_ground_truth():
    scenarios, probes, root = load_design()
    assert {s["expected_agent"] for s in scenarios["scenarios"]} == {"busca", "codigo", "resumo"}
    assert len(scenarios["scenarios"]) == 6
    assert scenarios["sessions"] == 3
    assert not ({p["id"] for p in probes["style"]} & {p["id"] for p in probes["profile"]})
    assert (root / "rubrics/README.md").is_file()


def test_smoke_preserves_complete_matrix_and_reports_missing_evidence(smoke):
    path, rows = smoke
    assert len(rows) == 6 * 3 * (1 + 3 + 2) * 3
    assert all(len([r for r in rows if r["scenario_id"] == scenario and r["session"] == session]) == 18
               for scenario in {r["scenario_id"] for r in rows} for session in (1, 2, 3))
    metrics = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["scientific_result"] is False
    assert metrics["delegation"]["C"]["n"] == 18
    assert metrics["delegation"]["C"]["matrix"] == [[6, 0, 0], [0, 6, 0], [0, 0, 6]]
    assert metrics["delegation"]["A"]["value"] is None
    assert metrics["profile_convergence"]["value"] is None
    assert metrics["coherence_embedding_distribution"]["value"] is None
    assert metrics["construct_validity"]["value"] is None
    assert metrics["formal_collection_allowed"] is False
    decisions = [json.loads(line) for line in (path / "decisions.jsonl")
                 .read_text(encoding="utf-8").splitlines()]
    assert len(decisions) == 6 * 3 * 6 * 2
    assert {d["status"] for d in decisions} == {"mediated", "completed"}
    assert all(d["reason"] for d in decisions)


def test_baseline_has_no_memory_and_control_uses_only_completed_prior_sessions(smoke):
    _, rows = smoke
    a_contexts = {row["llm_calls"][0]["context"] for row in rows if row["arm"] == "A"}
    assert len(a_contexts) == 1
    design, _, _ = load_design()
    for row in (r for r in rows if r["arm"] == "B"):
        scenario = next(s for s in design["scenarios"] if s["id"] == row["scenario_id"])
        current_task = scenario["sessions"][row["session"] - 1]
        assert current_task not in row["llm_calls"][0]["context"]
        if row["session"] == 1:
            assert row["prior_session_transcript_chars"] == 0
        else:
            assert row["prior_session_transcript_chars"] > 0
        if row["context_budget"] is not None:
            assert row["llm_calls"][0]["context_size"] <= row["context_budget"]
    assert any(r["context_budget"] is None for r in rows if r["arm"] == "C")


def test_blinding_removes_arm_metadata_and_keeps_longitudinal_pairing(smoke):
    path, raw = smoke
    blinded = [json.loads(line) for line in (path / "blind/paired.jsonl")
               .read_text(encoding="utf-8").splitlines()]
    key = json.loads((path / "private/unblinding.json").read_text(encoding="utf-8"))["samples"]
    assert len(blinded) == len(raw) == len(key)
    assert all(not ({"arm", "selected_agent", "llm_calls", "decision_id"} & row.keys())
               for row in blinded)
    by_pair = {}
    for row in blinded:
        by_pair.setdefault(row["pair_id"], []).append(row)
    assert all(sorted(r["presentation_position"] for r in pair) == [1, 2, 3]
               for pair in by_pair.values())
    condition_map = {}
    for row in key:
        scenario = row["pair_id"].split("|")[0]
        condition_map.setdefault((scenario, row["arm"]), set()).add(row["condition_id"])
    assert all(len(conditions) == 1 for conditions in condition_map.values())
    arm_orders = []
    mapping = {r["sample_id"]: r["arm"] for r in key}
    for pair in by_pair.values():
        arm_orders.append(tuple(mapping[r["sample_id"]] for r in pair))
    assert len(set(arm_orders)) > 1


def test_existing_run_is_never_overwritten(smoke):
    path, _ = smoke
    original = (path / "raw.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        run_smoke(path.parent, EvaluationConfig(run_id=path.name))
    assert (path / "raw.jsonl").read_bytes() == original


def test_formal_and_fake_pilot_are_blocked(tmp_path, capsys):
    assert main(["--mode", "formal", "--output", str(tmp_path)]) == 2
    assert "Proposto" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
    with pytest.raises(ValueError, match="fake is prohibited"):
        run_construct_pilot(tmp_path, EvaluationConfig(mode="pilot", provider="fake"))
    with pytest.raises(ValueError, match="restricted to smoke"):
        run_smoke(tmp_path, EvaluationConfig(mode="pilot"))


def test_metrics_measure_direction_and_reject_invented_or_invalid_vectors():
    closer = convergence([1, 0], [[0, 1], [0.5, 0.5], [1, 0]])
    farther = convergence([1, 0], [[1, 0], [0, 1]])
    assert closer["reduction"] > 0
    assert farther["reduction"] < 0
    assert convergence([1, 0], [])["distances"] is None
    assert cosine_distance([1, 0], [0, 1]) == 1
    assert len(embedding_distribution([[1, 0], [0, 1], [1, 1]])["distances"]) == 3
    with pytest.raises(ValueError):
        cosine_distance([0, 0], [1, 0])
    with pytest.raises(ValueError):
        convergence([1, 0], [[float("nan"), 0]])
    assert agreement([1, 2], [1, 3])["percent_agreement"] == 50


def test_unknown_router_predictions_are_errors_in_denominator():
    metric = delegation_metrics([("busca", "unexpected"), ("codigo", "codigo")])
    assert metric["accuracy"] == 0.5
    assert metric["n"] == 2
    assert metric["unknown_predictions"] == [{"expected": "busca", "observed": "unexpected"}]


def test_character_counter_is_explicitly_not_tokenizer():
    counter = CharacterCounter()
    assert counter.formal_ready is False
    assert counter.count("olá") == 3
    assert counter.truncate("abcdef", 3) == "def"
    assert counter.truncate("abcdef", 3, from_end=False) == "abc"
    assert counter.truncate("abcdef", 0) == ""


def test_failed_generation_keeps_attempted_context_and_smoke_preserves_audit(tmp_path):
    class FailingLLM:
        def generate(self, prompt, context=""):
            raise RuntimeError("fixture-backend-failure")

    recorder = RecordingLLM(FailingLLM(), CharacterCounter(), maximum=3)
    with pytest.raises(RuntimeError):
        recorder.generate("request", "identity-memory")
    assert recorder.calls[0]["context"] == "ide"
    assert recorder.calls[0]["status"] == "failed"
    with pytest.raises(Exception, match="fixture-backend-failure"):
        run_smoke(tmp_path, EvaluationConfig(run_id="failing-smoke"), llm=FailingLLM())
    run_dir = tmp_path / "failing-smoke"
    failure = json.loads((run_dir / "failure.json").read_text(encoding="utf-8"))
    assert failure["failed_llm_attempts"][0]["prompt"]
    decisions = [json.loads(line) for line in (run_dir / "decisions.jsonl")
                 .read_text(encoding="utf-8").splitlines()]
    assert decisions  # The successful non-LLM Busca request remains auditable before A fails.

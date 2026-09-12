import json

import pytest

from cain.evaluation import EvaluationConfig, run_functional
from cain.evaluation.__main__ import main
from cain.evaluation.functional import functional_checks, functional_plan
from cain.evaluation.metrics import observed_format_vector
from cain.llm import FakeLLM


def test_functional_persistence_correction_isolation_and_source(tmp_path):
    result = run_functional(
        tmp_path,
        EvaluationConfig(mode="functional", provider="injected-test", run_id="functional-fixture"),
        llm=FakeLLM(),
    )
    metrics = json.loads((result / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["functional_success"] is True
    assert metrics["recorded_stages"] == 6
    assert metrics["real_llm"] is False
    assert metrics["human_response_quality"]["value"] is None
    observations = metrics["preference_observations"]
    assert observations[1]["format_before"] == "steps"
    assert observations[2]["format_after"] == "paragraph"
    assert observations[3]["format_before"] == "paragraph"
    assert observations[4]["format_before"] is None
    restart = next(check for check in metrics["checks"] if check["id"] == "process_restart")
    assert restart["passed"] is None  # This injected test never claims a real process restart.
    raw = [json.loads(line) for line in (result / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(record["llm_calls"] for record in raw[:-1])
    assert raw[-1]["llm_calls"] == []
    assert "BOREAL-731" in raw[-1]["response"]
    assert all(record["context_budget_applied"] is False for record in raw)
    assert len({record["request_run_id"] for record in raw}) == 6
    config = json.loads((result / "config.json").read_text(encoding="utf-8"))
    assert config["model_observation"]["model_digest"] is None
    assert config["generation_controls"]["adapter_options"]["num_ctx"] is None
    assert config["generation_controls"]["max_input_bytes_is_tokenizer"] is False
    assert all(call["provider_metadata"] is None for record in raw for call in record["llm_calls"])
    assert config["source_tree_sha256"]
    assert (result / "inputs/functional_plan.json").is_file()
    assert "guia-funcional-cain.txt" in raw[-1]["response"]


def test_functional_cli_does_not_silently_run_fake(tmp_path, capsys):
    code = main(["--mode", "functional", "--output", str(tmp_path)])
    assert code == 1
    assert "fake is prohibited" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
    with pytest.raises(ValueError, match="injected-test"):
        run_functional(tmp_path, EvaluationConfig(mode="functional", provider="ollama"), llm=FakeLLM())


def test_functional_failure_retains_attempt_and_does_not_invent_remaining_outputs(tmp_path):
    class FailedProvider:
        def generate(self, prompt, context=""):
            raise RuntimeError("deliberate-fixture-failure")

    result = run_functional(tmp_path,
                            EvaluationConfig(mode="functional", provider="injected-test", run_id="failed"),
                            llm=FailedProvider())
    metrics = json.loads((result / "metrics.json").read_text(encoding="utf-8"))
    failure = json.loads((result / "failure.json").read_text(encoding="utf-8"))
    assert metrics["functional_success"] is False
    assert metrics["recorded_stages"] == 1
    assert len(failure["not_run"]) == 5
    assert failure["failure"]["response"] is None
    assert failure["failure"]["llm_calls"][0]["status"] == "failed"
    assert failure["failure"]["llm_calls"][0]["context"]


def test_format_vector_never_infers_preference_from_generated_style():
    assert observed_format_vector({"format": "steps"})["value"] == [1, 0]
    assert observed_format_vector({"format": "paragraph"})["value"] == [0, 1]
    assert observed_format_vector({})["value"] is None
    assert observed_format_vector({"format": "bullets"})["value"] is None


def test_missing_stages_are_visible_failures():
    checks = functional_checks([], functional_plan("empty"), process_mode=True)
    assert all(check["passed"] is not True for check in checks)

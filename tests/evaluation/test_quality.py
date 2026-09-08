import json

import pytest

from cain.evaluation.quality import (
    QualityConfig,
    assess,
    load_dataset,
    main,
    model_input,
    run_comparison,
)


def case(case_id):
    return next(item for item in load_dataset()[0]["cases"] if item["id"] == case_id)


class TestProvider:
    __test__ = False

    def __init__(self, model, calls):
        self.model = model
        self.calls = calls
        self.last_metadata = {}

    def generate(self, prompt, context=""):
        self.last_metadata = {}
        self.calls.append({"model": self.model, "prompt": prompt, "context": context})
        # No invented token counts: a test provider leaves backend metadata unavailable.
        return "[INJECTED TEST RESPONSE] " + prompt

    def generate_json(self, prompt, context, schema):
        self.last_metadata = {}
        self.calls.append({"model": self.model, "prompt": prompt, "context": context, "schema": schema})
        return '{"agent": "clarificar"}'


def test_dataset_has_predetermined_dev_and_holdout_with_required_task_types():
    design, _ = load_dataset()
    assert len(design["cases"]) == 14
    assert sum(item["split"] == "dev" for item in design["cases"]) == 8
    assert sum(item["split"] == "holdout" for item in design["cases"]) == 6
    assert {item["category"] for item in design["cases"]} == {
        "summary", "preference", "abstention", "code", "routing",
    }
    for item in design["cases"]:
        assert not ({"checks", "split", "expected_agent", "id", "category"} & model_input(item).keys())


def test_comparison_preserves_identical_inputs_and_never_calls_fake_real(tmp_path):
    calls = []
    path = run_comparison(tmp_path, QualityConfig(models=("fixture-a", "fixture-b"),
                                                 provider="injected-test", run_id="paired"),
                          provider_factory=lambda model, config: TestProvider(model, calls))
    raw = [json.loads(line) for line in (path / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(raw) == len(calls) == 28
    for item in load_dataset()[0]["cases"]:
        rows = [row for row in raw if row["case_id"] == item["id"]]
        assert rows[0]["model_input"] == rows[1]["model_input"] == model_input(item)
        assert rows[0]["model_input_sha256"] == rows[1]["model_input_sha256"]
    assert all(set(call) <= {"model", "prompt", "context", "schema"} for call in calls)
    metrics = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["real_llm"] is False
    assert metrics["identical_model_input_per_case"] is True
    assert metrics["quality_winner"] is None
    assert metrics["human_quality"]["value"] is None
    assert set(metrics["models"]["fixture-a"]["by_split"]) == {"dev", "holdout"}
    assert all(row["provider_metadata"] == {} for row in raw)
    assert metrics["models"]["fixture-a"]["truncation_unknown_count"] == 14
    assert (path / "responses.md").is_file()


def test_json_checks_reject_wrong_schema_duplicate_keys_and_wrong_labels():
    item = case("dev-route-code")
    valid = assess(item, '{"agent":"codigo"}')
    assert all(check["passed"] is True for check in valid)
    for response in ('{"agent":"codigo", "extra":1}', '{"agent":7}', '{"agent":"other"}'):
        checks = {check["name"]: check for check in assess(item, response)}
        assert checks["json_valid"]["passed"] is True
        assert checks["json_schema_valid"]["passed"] is False
    wrong = {check["name"]: check for check in assess(item, '{"agent":"busca"}')}
    assert wrong["json_schema_valid"]["passed"] is True
    assert wrong["route_label_exact"]["passed"] is False
    assert assess(item, '{"agent":"busca","agent":"codigo"}')[0]["passed"] is False
    assert assess(item, '```json\n{"agent":"codigo"}\n```')[0]["passed"] is False


def test_fact_presence_is_heuristic_and_source_marker_membership_is_limited():
    checks = assess(case("dev-abstain-price"), "O preço não foi informado. [S1] [F1] [1]")
    facts = [check for check in checks if check["name"].startswith("required_fact")]
    assert all(check["kind"] == "heuristic" for check in facts)
    citation = next(check for check in checks if check["name"] == "citation_identifiers_allowed")
    assert citation["passed"] is False
    assert citation["observed"]["unknown"] == ["1", "F1"]


def test_code_is_only_parsed_and_algorithm_correctness_is_not_claimed(tmp_path):
    marker = tmp_path / "must-not-exist"
    response = f'```python\ndef soma(a, b):\n    return 0\nopen({str(marker)!r}, "w").write("wrong")\n```'
    checks = assess(case("dev-code-sum"), response)
    assert all(check["passed"] is True for check in checks)
    assert not marker.exists()  # Demonstrates that even valid dangerous code is never executed.
    assert "algorithm correctness or safety" in checks[-1]["reason"]
    assert assess(case("dev-code-sum"), "```python\ndef broken(:\n``` ")[0]["passed"] is False


def test_language_stays_unrated_and_format_checks_are_explicit():
    checks = {check["name"]: check for check in assess(case("dev-preference-english"),
              "A test compares the actual result with the expected result.")}
    assert checks["language_appropriateness"]["passed"] is None
    assert checks["single_paragraph_without_list"]["passed"] is True
    numbered = {check["name"]: check for check in assess(case("dev-preference-steps"),
                "1. Copiar o arquivo.\n2. Verificar a cópia.\n3. Manter o original.")}
    assert numbered["numbered_lines_exact"]["passed"] is True


def test_errors_and_truncation_remain_visible_without_retry_or_lost_cases(tmp_path):
    attempts = []

    class Faults(TestProvider):
        def generate(self, prompt, context=""):
            attempts.append(prompt)
            self.last_metadata = {}
            if "SQLite" in prompt:
                raise RuntimeError("fixture failure")
            self.last_metadata = {"done_reason": "length"}
            return "partial fixture response"

    path = run_comparison(tmp_path, QualityConfig(models=("fixture",), provider="injected-test",
                                                 split="dev", run_id="faults"),
                          provider_factory=lambda model, config: Faults(model, []))
    raw = [json.loads(line) for line in (path / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(raw) == 8
    assert len(attempts) == 7  # The eighth case uses generate_json exactly once.
    assert sum(row["status"] == "error" for row in raw) == 1
    assert sum(row["status"] == "truncated" for row in raw) >= 6
    metrics = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["models"]["fixture"]["status_counts"]["error"] == 1
    assert metrics["models"]["fixture"]["attempts"] == 8


def test_cli_has_no_fake_option_and_injection_cannot_be_mislabeled(tmp_path):
    with pytest.raises(SystemExit) as stopped:
        main(["--provider", "fake", "--output", str(tmp_path)])
    assert stopped.value.code == 2
    with pytest.raises(ValueError, match="cannot label fake output real"):
        run_comparison(tmp_path, QualityConfig(), provider_factory=lambda model, config: None)
    assert not list(tmp_path.iterdir())


def test_adapter_truncation_exception_preserves_partial_response(tmp_path):
    class LLMTruncated(RuntimeError):
        def __init__(self):
            super().__init__("fixture generation limit")
            self.partial_response = "Partial observed fixture response"

    class TruncatedProvider(TestProvider):
        def generate(self, prompt, context=""):
            self.last_metadata = {"done_reason": "length"}
            raise LLMTruncated()

    path = run_comparison(tmp_path, QualityConfig(models=("fixture",), provider="injected-test",
                                                 split="dev", run_id="partial"),
                          provider_factory=lambda model, config: TruncatedProvider(model, []))
    raw = [json.loads(line) for line in (path / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    truncated = [row for row in raw if row["status"] == "truncated"]
    assert len(truncated) == 7
    assert all(row["response"] == "Partial observed fixture response" for row in truncated)
    assert all(row["provider_metadata"]["done_reason"] == "length" for row in truncated)
    assert all(row["truncated"] is True for row in truncated)
    metrics = json.loads((path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["models"]["fixture"]["status_counts"].get("error", 0) == 0


def test_existing_runs_are_never_replaced(tmp_path):
    cfg = QualityConfig(models=("fixture",), provider="injected-test", run_id="preserved", split="holdout")
    def factory(model, config):
        return TestProvider(model, [])
    path = run_comparison(tmp_path, cfg, provider_factory=factory)
    original = (path / "raw.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        run_comparison(tmp_path, cfg, provider_factory=factory)
    assert (path / "raw.jsonl").read_bytes() == original

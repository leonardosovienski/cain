import json
from pathlib import Path

import pytest

from cain.evaluation.v2 import evaluate, validate_design, isolation, prepare, origin


@pytest.mark.parametrize(
    "text,ok",
    [
        ('{"cidade":"Londrina","ativo":false}', True),
        ('{"ativo":false,"cidade":"Londrina"}', True),
        ('{"cidade":"Curitiba","ativo":true}', False),
        ('{"cidade":"Londrina","ativo":"false"}', False),
        ('{"cidade":"Londrina","ativo":0}', False),
        ('{"cidade":"Londrina","ativo":false,"extra":1}', False),
        ('{"cidade":"Londrina","ativo":true,"ativo":false}', False),
        ('{"cidade":"Londrina","ativo":NaN}', False),
        ('```json\n{"cidade":"Londrina","ativo":false}\n```', False),
    ],
)
def test_json_contract(text, ok):
    result = evaluate(
        text, {"json": {"cidade": "Londrina", "ativo": False}, "semantic_required": False}
    )
    assert (result["quality"] == "pass") == ok


@pytest.mark.parametrize(
    "text,ok",
    [
        ("AÇÃO-928", True),
        ("AÇÃO-928\r\n", True),
        (" AÇÃO-928", False),
        ("AÇÃO-928\n\n", False),
        ("**AÇÃO-928**", False),
    ],
)
def test_literal_does_not_repair(text, ok):
    assert (
        evaluate(text, {"exact": "AÇÃO-928", "semantic_required": False})["quality"] == "pass"
    ) == ok


def test_semantics_not_certified_by_presence():
    for text in [
        "Zeta obteve 0,57",
        "Outro obteve 0,57",
        "Zeta não obteve 0,57",
        "Fonte S1 prova lucro universal",
        "Não sei apesar de fonte disponível",
    ]:
        assert evaluate(text, {"semantic_required": True})["quality"] == "review_required"
    assert (
        evaluate("É assim que concordo.", {"forbidden_word": "sim"})["quality"] == "review_required"
    )
    assert evaluate("Sim, concordo.", {"forbidden_word": "sim"})["quality"] == "fail"


def test_design_and_isolation(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_DB", raising=False)
    data = Path(__file__).parents[2] / "src/cain/evaluation/data"
    catalog = data / "scenarios/evaluation-v2.json"
    rubrics = data / "probes/evaluation-v2-rubrics.json"
    validate_design(
        json.loads(catalog.read_text(encoding="utf-8")),
        json.loads(rubrics.read_text(encoding="utf-8")),
    )
    config = tmp_path / "source.toml"
    config.write_text('[llm]\nprovider="fake"\n[search]\npaths=[]\n')
    root = tmp_path / "qa"
    prepare(root, config, catalog, rubrics)
    assert isolation(root, root / "qa.toml")["source_paths"] == []
    with pytest.raises(FileExistsError):
        prepare(root, config, catalog, rubrics)
    monkeypatch.setenv("CAIN_DB", str(tmp_path / "personal.db"))
    with pytest.raises(ValueError, match="preconditions"):
        isolation(root, root / "qa.toml")


def test_origin_never_infers_llm_from_style():
    assert origin({"response": "Olá"}, []) == "unknown"
    assert origin({"response": "Olá", "route_reason": "social_greeting"}, []) == "deterministic"
    assert origin({"response": "S1", "selected_agent": "busca"}, []) == "retrieval_only"


def test_observer_timeout_is_not_zero_inference():
    from cain.evaluation.v2 import observed_generation_count

    assert observed_generation_count([], []) == 0
    assert observed_generation_count([{"forwarded": True}], [{}]) == 1
    assert observed_generation_count([{"error": "TimeoutError"}], [{}]) is None
    assert observed_generation_count([], [{}]) is None


def test_integrity_evaluator_accepts_cancelled_idempotent_return(tmp_path):
    from cain.evaluation.v2_integrity import run

    results = run(tmp_path / "isolated")
    assert all(row["quality"] == "pass" for row in results)


def test_attestation_rejects_wrong_server_before_mutable_requests(tmp_path, monkeypatch):
    import cain.evaluation.v2 as v2

    expected = {"root": str(tmp_path.resolve()), "instance": "expected"}
    v2.write(tmp_path / "server-attestation.json", expected)
    calls = []

    def wrong(url, **kwargs):
        calls.append(url)
        return 200, {"root": str(tmp_path.resolve()), "instance": "other"}

    monkeypatch.setattr(v2, "request", wrong)
    with pytest.raises(ValueError, match="attest"):
        v2.attest(tmp_path, "http://127.0.0.1:8896")
    assert calls == ["http://127.0.0.1:8896/evaluation/attestation"]
    with pytest.raises(ValueError, match="loopback"):
        v2.local_url("https://example.com")
    with pytest.raises(ValueError, match="loopback"):
        v2.local_url("http://localhost@evil.invalid")


@pytest.mark.parametrize("module", ["v2_controls", "v2_research", "v2_utility"])
def test_auxiliary_http_adapters_require_storage_attestation(tmp_path, monkeypatch, module):
    import importlib

    adapter = importlib.import_module("cain.evaluation." + module)

    def reject(*args):
        raise ValueError("Wrong QA server")

    monkeypatch.setattr(adapter, "attest", reject)
    output = tmp_path / "not_created"
    with pytest.raises(ValueError, match="Wrong QA server"):
        if module == "v2_controls":
            adapter.run(output, "http://127.0.0.1:8896", tmp_path)
        elif module == "v2_research":
            adapter.run(tmp_path, output, tmp_path / "rubrics.md", "http://127.0.0.1:8896")
        else:
            adapter.run(tmp_path, output, "http://127.0.0.1:8896")
    assert not output.exists()


def test_report_uses_frozen_confirmation_cases(tmp_path):
    from cain.evaluation.v2 import read, report, write

    target = tmp_path / "run"
    target.mkdir()
    write(tmp_path / "catalog.json", {"cases": [{"family_id": "B03", "case_id": "old"}]})
    write(target / "manifest.json", {"cases": [{"family_id": "B03", "case_id": "new"}]})
    report(tmp_path, target)
    row = next(x for x in read(target / "coverage.json") if x["family"] == "B03")
    assert row["implemented_cases"] == ["new"]
    assert row["state"] == "not_executed"

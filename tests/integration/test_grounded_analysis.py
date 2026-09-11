import json
from pathlib import Path

import pytest

from cain.research.analysis import entities, review
from cain.research.grounding import structured
from cain.llm import FakeLLM
import test_research_l0 as cases

setup = cases.setup
PLAN = json.loads((Path(__file__).parents[2] / "evaluation/grounded-analysis-20260911.json").read_bytes())


@pytest.mark.parametrize("case", PLAN["cases"][:4], ids=lambda case: case["id"])
def test_frozen_structured_cases(case):
    result = structured({"ref": case["text"]}, case["source_id"])
    if "expected_pairs" in case:
        assert [[r["subject"], r["object"]] for r in result["relations"]] == case["expected_pairs"]
        for relation in result["relations"]:
            assert case["text"][relation["start"]:relation["end"]] == relation["quote"]
    else:
        assert result["status"] == case["expected_structural_status"]
        assert result["relations"] == []


def test_escaped_json_uses_received_lexemes_not_invented_quotes():
    text = json.dumps({"Á": "linha\nseguinte"}, ensure_ascii=True)
    row = structured({"ref": text}, "Á")["relations"][0]
    assert row["decoded_subject"] == "Á" and row["decoded_object"] == "linha\nseguinte"
    assert row["subject"] in row["quote"] and row["object"] in row["quote"]
    assert row["quote"] == text[row["start"]:row["end"]]


def test_literal_extraction_works_without_model_or_generation_permission(setup):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(("K17",), text='{"states":{"K17":"INSUFFICIENT_DATA"}}'))
    for grant in policy["grants"]:
        grant["generate"] = False
    path.write_text(json.dumps(policy))
    result = entities(service, scope, "What is reported?", FakeLLM(), source_id="K17")
    assert result["model_calls"] == 0 and result["status"] == "literal"
    assert result["relations"][0]["object"] == "INSUFFICIENT_DATA"


class PointerModel:
    base_url = "http://127.0.0.1:11434"
    calls = 0
    def generate_json(self, prompt, context, schema):
        self.calls += 1
        return json.dumps({"citations": [next(iter(json.loads(prompt)["excerpts"]))],
                           "analysis": "The report does not establish a cause."})


def test_review_resolves_offsets_and_no_evidence_has_zero_calls(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("D4",), text=PLAN["cases"][4]["text"]))
    model = PointerModel()
    result = review(service, scope, "What reason?", model, role="challenge", source_id="D4")
    quote = result["explanation"]["source_quotes"][0]
    assert result["status"] == "generated"
    assert quote["support"]["text"][quote["start"]:quote["end"]] == quote["quote"]
    result = review(service, scope, "What reason?", model, role="support", source_id="missing")
    assert not result["generation"]["called"] and model.calls == 1


def test_unknown_pointer_is_rejected(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("D4",), text=PLAN["cases"][4]["text"]))
    model = PointerModel()
    model.generate_json = lambda *args: '{"citations":["invented"],"analysis":"x"}'
    result = review(service, scope, "What reason?", model, role="support", source_id="D4")
    assert result["status"] == "generation_failed" and result["explanation"] is None

import json
from pathlib import Path

import pytest

from cain.research.analysis import entities, review
from cain.research.grounding import cards, structured
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


def test_individual_hypothesis_excerpts_exclude_other_identities_and_keep_paths():
    text = json.dumps({'hypotheses': {'H1': 'CLOSED_NO_GO', 'H6': 'INSUFFICIENT', 'H60': 'ACTIVE'},
                       'hypothesis_trials': {'H1': 'other', 'H6': 'trial-six'},
                       'notes': 'H1 has an unrelated historical explanation.'})
    excerpts, coverage = cards({'ref': {'text': text}}, 'O que a fonte informa sobre H6?', 'H6')
    assert {e['json_pointer'] for e in excerpts.values()} == {'/hypotheses/H6', '/hypothesis_trials/H6'}
    assert len(excerpts) == 2
    for entry in excerpts.values():
        assert entry['quote'] == text[entry['start']:entry['end']]
        assert 'H1' not in entry['quote'] and 'H60' not in entry['quote']
    assert coverage['whole_source_read_claim'] is False


def test_duplicate_json_cannot_bypass_structured_ambiguity_via_review(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('K17',), text='{"K17":"INSUFFICIENT","K17":"VALIDATED"}'))
    model = PointerModel()
    result = review(service, scope, 'What status?', model, role='synthesis', source_id='K17')
    assert result['status'] == 'abstained_ambiguous_evidence'
    assert result['coverage']['structured_issues'][0]['status'] == 'ambiguous_or_invalid_json'
    assert model.calls == 0


def test_review_payload_retains_exact_key_paths(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('H6',), text='{"hypotheses":{"H1":"NO","H6":"WAIT"},"trials":{"H6":"six"}}'))
    model = PointerModel()
    def capture(prompt, context, schema):
        payload = json.loads(prompt)
        assert payload['source_id'] == 'H6'
        assert payload['reported_records_untrusted'][0]['source_id'] == 'H6'
        assert {e['json_pointer'] for e in payload['excerpts'].values()} == {'/hypotheses/H6', '/trials/H6'}
        assert all('H1' not in e['text'] for e in payload['excerpts'].values())
        return json.dumps({'citations': ['S1'], 'analysis': 'WAIT'})
    model.generate_json = capture
    result = review(service, scope, 'What status?', model, role='synthesis', source_id='H6')
    assert result['status'] == 'generated'
    assert result['generation']['prompt_version'] == 'addressable-review/3'

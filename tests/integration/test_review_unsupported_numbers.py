"""The review agent refuses prose numbers that no cited evidence supports.

Found while driving the agent with hand-written model output: an invented cause
("custos de transação de 3.5") with a valid citation was published as
``generated``. Numbers are objectively checkable, so a number absent from the
cited excerpts, their source context, the reported records and the question is
refused with ``UNSUPPORTED_NUMBER``. This is lexical, never semantic approval.
"""
import json

import test_research_l0 as cases

from cain.research.analysis import review, unsupported_numbers

setup = cases.setup

TEXT = ("# Veredito H1\n\n- **veredito H1:** NOT_SUPPORTED\n\n"
        "O Sharpe prospectivo foi 0.21, abaixo do critério de 0.5, em 2019-2020 com n=312.\n")


class Scripted:
    base_url = "http://127.0.0.1:11434"
    last_metadata = {}

    def __init__(self, analysis):
        self.analysis = analysis

    def generate_json(self, prompt, instruction, schema):
        keys = schema["properties"]["citations"]["items"]["enum"]
        return json.dumps({"citations": keys[:2], "analysis": self.analysis})


def test_numbers_present_in_cited_evidence_records_or_question_are_accepted(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("H1",), text=TEXT))
    model = Scripted("A revisão 1 de H1 reporta Sharpe 0.21 abaixo de 0.5 em 2019-2020, n=312 [S1][S2].")
    result = review(service, scope, "Qual o Sharpe prospectivo de H1 na revisão 1?", model,
                    role="support", source_id="H1")
    assert result["status"] == "generated"


def test_invented_number_is_refused_with_its_own_code(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("H1",), text=TEXT))
    model = Scripted("H1 foi rejeitada porque custos de transação de 3.5 consumiram o retorno [S1].")
    result = review(service, scope, "O que o relatório de H1 sustenta?", model, role="support", source_id="H1")
    assert result["status"] == "generation_failed"
    assert result["error_code"] == "UNSUPPORTED_NUMBER"
    assert result["explanation"] is None


def test_rounded_or_rewritten_numbers_are_refused(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("H1",), text=TEXT))
    model = Scripted("O Sharpe foi cerca de 0.2, metade do critério de 0.5 [S1].")
    result = review(service, scope, "O que o relatório de H1 sustenta?", model, role="support", source_id="H1")
    assert result["error_code"] == "UNSUPPORTED_NUMBER"


def test_unsupported_numbers_helper_is_lexical_and_context_aware():
    excerpts = {"S1": {"quote": "RPS=0.21132 (n=737)", "source_context": [{"quote": "IC95=[-0.002, 0.006]"}]}}
    records = [{"source_id": "H4", "revision": "2"}]
    assert unsupported_numbers("n=737 e RPS 0.21132, IC95 -0.002 a 0.006, revisão 2 de 3 [S1]",
                               ["S1"], excerpts, records, "Qual o resultado de H4?") == ["3"]
    assert unsupported_numbers("Sem números [S1]", ["S1"], excerpts, records, "?") == []


def test_percent_in_source_supports_the_bare_number_the_instruction_asks_for():
    """Regression from the real campaign: the prompt forbids appending "%", so
    "acima de 2%" in the evidence must support "acima de 2" in the prose."""
    excerpts = {"S1": {"quote": "Retorno acima de 2% com IC de 95% e retorno semanal de 0.35%"}}
    assert unsupported_numbers("retorno acima de 2, IC 95, semanal 0.35 [S1]", ["S1"], excerpts, [], "?") == []

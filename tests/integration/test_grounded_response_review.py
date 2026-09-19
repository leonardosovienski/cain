import json

import pytest

from cain.llm import OllamaLLM
from cain.research.approved_memory import apply_approved, recover_approved
from cain.research.grounded_analysis import (
    Evidence,
    analyze,
    analyze_text,
    compact_context,
    select_subject_blocks,
    validate_proposal,
)


class TextStub(OllamaLLM):
    response = "### outcome\nA generated interpretation of the source. [S1]"

    def generate(self, prompt, context=""):
        return self.response


def test_literal_quote_check_does_not_claim_semantic_certification():
    evidence = [Evidence("x", "There were zero transactions.", "receipt")]
    proposal = {
        "limits": {
            "explanation": "This result demonstrates real financial profit.",
            "source_id": "x",
            "quote": "There were zero transactions.",
            "uncertainty": "None.",
        }
    }
    assert validate_proposal(proposal, ["limits"], evidence) == []
    proposal["limits"]["quote"] = "There were ten transactions."
    assert validate_proposal(proposal, ["limits"], evidence) == [
        "limits:nonliteral_or_empty_quote"
    ]


def test_text_analysis_binds_original_evidence_and_withholds_answer():
    result = analyze_text(
        TextStub(), "Question", ["outcome"], [Evidence("S1", "Exact source.", "fixture")]
    )
    assert result["proposal"]["outcome"]["source_evidence"][0]["text"] == "Exact source."
    assert result["semantic_status"] == "requires_review"
    assert result["approved_knowledge"] is False
    assert result["user_response"]["review"]["release_status"] == (
        "withheld_pending_external_review"
    )


def test_preamble_and_empty_source_are_rejected():
    provider = TextStub()
    provider.response = "Unsupported preamble.\n### outcome\nLong enough answer. [S1]"
    result = analyze_text(provider, "Question", ["outcome"], [Evidence("S1", "", "fixture")])
    assert "unparsed_preamble" in result["structural_errors"]
    assert "outcome:empty_source" in result["structural_errors"]


def test_structured_generation_is_never_semantically_approved():
    class Structured(OllamaLLM):
        def generate_json(self, prompt, context, schema):
            return json.dumps(
                {
                    "result": {
                        "explanation": "This result demonstrates real financial profit.",
                        "quote": "There were zero transactions.",
                        "source_id": "S1",
                        "uncertainty": "None.",
                    }
                }
            )

    result = analyze(
        Structured(),
        "Question",
        ["result"],
        [Evidence("S1", "There were zero transactions.", "fixture")],
    )
    assert result["structural_status"] == "accepted"
    assert result["answer_review"]["approved_knowledge"] is False


def test_context_projection_and_subject_selection_are_explicit():
    original = json.dumps({"threshold": 0.95, "data": list(range(20)), "cost": -2})
    rendered, receipt = compact_context(original)
    projected = json.loads(rendered)
    assert projected["threshold"] == 0.95 and projected["cost"] == -2
    assert projected["data"]["total_entries"] == 20
    assert receipt["omissions"] == [{"path": "/data", "length": 20, "omitted_middle": 16}]
    text = "- H4 has five forecasts.\n  No verdict.\n- H5 inputs missing.\n- H40 unrelated."
    selected = select_subject_blocks(text, "H4")
    assert len(selected) == 1 and "No verdict" in selected[0]
    assert "H5" not in selected[0] and "H40" not in selected[0]


class MemoryService:
    saved = None

    def recall(self, scope, entry, session_id=None):
        return {
            "evaluator_approval": {"approved": True},
            "facts": {"records": [{"id": "authorized"}], "coverage": []},
            "explanation": {"proposed_synthesis": "Only a bounded historical claim."},
        }

    def log_explanation(self, scope, question, response, session_id=None):
        self.saved = response
        return "new-proposal"


def test_approved_memory_question_is_prompt_not_evidence_and_new_answer_is_unapproved():
    service = MemoryService()
    provider = TextStub()
    provider.response = "\n\n".join(
        "### " + field + "\nA long software-test response. [S1]"
        for field in ("conhecimento_recuperado", "aplicacao", "limitacoes")
    )
    result = apply_approved(service, "identity", "entry", "New scenario", provider, "session")
    assert [item["id"] for item in result["analysis"]["evidence"]] == ["S1"]
    assert result["approved_knowledge"] is False
    assert service.saved["validation"]["approved"] is False
    assert service.saved["memory_parent"] == "entry"


def test_unapproved_or_redacted_memory_cannot_be_applied():
    service = MemoryService()
    service.recall = lambda scope, entry, session_id=None: {
        "evaluator_approval": {"approved": False}
    }
    with pytest.raises(ValueError, match="explicitly approved"):
        recover_approved(service, "identity", "entry")
    service.recall = lambda scope, entry, session_id=None: {
        "status": "history_redacted_by_current_policy"
    }
    with pytest.raises(ValueError):
        recover_approved(service, "identity", "entry")

"""Context transport checks, not evidence of semantic understanding."""

from cain.research.analysis import review
from test_grounded_analysis import PointerModel
import test_research_l0 as cases

setup = cases.setup


def test_review_abstains_before_call_when_provider_budget_cannot_fit_evidence(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("budget-case",), text="A measured association is not a causal intervention."))
    model = PointerModel()
    model.effective_input_byte_budget = 1000
    result = review(service, scope, "What follows from this evidence?", model,
                    role="synthesis", source_id="budget-case")
    assert result["status"] == "abstained_context_budget"
    assert model.calls == 0
    assert result["coverage"]["serialized_context_budget_bytes"] == 1000


def test_provider_failure_diagnostic_survives_review_envelope(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("transport-case",), text="The comparison is exploratory."))
    model = PointerModel()
    model.last_metadata = {"http_status": 500, "server_error": "allocation failed"}

    def fail(*args):
        raise RuntimeError("allocation failed")

    model.generate_json = fail
    result = review(service, scope, "What does the report support?", model,
                    role="synthesis", source_id="transport-case")
    assert result["status"] == "generation_failed"
    assert result["generation"]["provider_failure"]["http_status"] == 500

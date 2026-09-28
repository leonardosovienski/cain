"""The model context fits the provider's input budget, with or without result metrics (rc11 soak regression)."""

import json

from cain.orchestration import llm

SUMMARY = {"brasileirao:Q01": {"results": 60, "scientific_states": {"INCONCLUSIVE": 60}, "refusals": [],
                               "eligible_now": True, "not_eligible_reason": None}}


def results(n, metrics=False):
    return [{"episode": i, "hypothesis_id": "brasileirao:Q01", "status": "RESULT", "result_state": "INCONCLUSIVE",
             "scientific_state": "INCONCLUSIVE", "reason_code": None}
            | ({"metrics": {"net_return_bps": -i, "sample_size": 50}} if metrics else {}) for i in range(1, n + 1)]


def fitted(shown, total, budget):
    return llm._fitted("brasileirao", "próximo", "2030-01-01T00:00:00Z", ["brasileirao:Q01"], SUMMARY, shown, total,
                       budget)


def test_a_domain_without_metrics_and_more_than_50_results_fits_the_budget_newest_first():
    shown = results(60)[-llm.MAX_RESULTS:]
    prompt, instruction = fitted(shown, 60, None)  # no budget: the last 50, and the omission is said
    assert instruction == llm.INSTRUCTION and json.loads(prompt)["results_omitted"] == 10
    budget = len((instruction + prompt).encode("utf-8")) // 2
    prompt, instruction = fitted(shown, 60, budget)
    context = json.loads(prompt)
    assert len((instruction + prompt).encode("utf-8")) <= budget and instruction == llm.INSTRUCTION
    assert context["results"][-1]["episode"] == 60 and context["results_omitted"] == 60 - len(context["results"])
    assert context["hypothesis_summary"] == SUMMARY


def test_within_the_budget_nothing_changes_and_nothing_is_said():
    shown = results(5, metrics=True)
    prompt, instruction = fitted(shown, 5, None)
    assert fitted(shown, 5, len((instruction + prompt).encode("utf-8"))) == (prompt, instruction)
    assert "results_omitted" not in json.loads(prompt) and instruction == llm.INSTRUCTION + llm.METRICS_NOTE


def test_a_budget_too_small_for_any_result_still_asks_with_the_summary():
    prompt, _instruction = fitted(results(3), 3, 1)
    context = json.loads(prompt)
    assert context["results"] == [] and context["results_omitted"] == 3  # the provider then refuses visibly

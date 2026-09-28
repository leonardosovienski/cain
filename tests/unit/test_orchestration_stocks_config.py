"""The packaged stocks configuration of the generic DecisionPolicy (integration-stocks).

Pure functions, no I/O: the configuration comes from the pinned stocks base 61fc017 (closed hypotheses, their
families and the [H1-FROZEN] costs) and the contract; the policy is the same code as for crypto.
"""

import copy

import pytest

from cain.orchestration import config as domain_config
from cain.orchestration import llm, policy

CONFIG = domain_config.load("stocks")
REQUEST = {
    "schema_version": "stocks-research-request/1",
    "request_id": "stocks:REQ-P-0001",
    "request_type": "BACKTEST_PIT_FACTOR",
    "research_id": "stocks:RESEARCH-INTEGRATION-QUALIFICATION",
    "hypothesis_id": "stocks:QUAL-PIT-MOM-REAL-001",
    "references": {"dataset": {"name": "b3-cvm-real", "version": "v1"},
                   "universe": {"name": "real", "version": "v1"},
                   "features": {"name": "momentum-12-1", "version": "v1"},
                   "model": {"name": "quintile-real", "version": "v1"},
                   "baseline": {"name": "ew-universe", "version": "v1"},
                   "cost_model": {"name": "h1-frozen", "version": "v1"},
                   "readiness": {"name": "matrix-20260921", "version": "v1"}},
    "as_of": "2026-09-26T03:00:00Z",
    "pit": {"availability_rule": "AVAILABLE_AT_LE_DECISION_TIME", "minimum_pit_class": "PIT_RECONSTRUCTED"},
    "parameters": {"target": "NEXT_REBALANCE_RETURN", "fee_bps": 3, "slippage_bps": 15, "max_securities": 5000,
                   "external_intelligence": {"mode": "NONE", "families": []}},
    "priority_hint": "NORMAL",
}
COLLECTION = {
    "schema_version": "stocks-research-request/1",
    "request_id": "stocks:REQ-P-0002",
    "request_type": "COLLECT_EXTERNAL_INTELLIGENCE",
    "research_id": "stocks:RESEARCH-EI-COLLECTION",
    "hypothesis_id": "stocks:QUAL-EI-COLLECTION-001",
    "references": {"source": {"name": "vlmo-real", "version": "v1"},
                   "readiness": {"name": "matrix-20260921", "version": "v1"}},
    "as_of": "2026-09-26T03:00:00Z",
    "pit": {"availability_rule": "AVAILABLE_AT_LE_DECISION_TIME", "minimum_pit_class": "PIT_STRICT"},
    "parameters": {"collector": "cvm-vlmo", "period": "2026", "observed_at": "2026-09-26T03:00:00Z"},
    "priority_hint": "NORMAL",
}
EMPTY = {"domain": "stocks", "episodes": 0, "tasks": [], "results": [], "open_task_ids": [], "requires_human": []}


def proposal(request=REQUEST, family=None, **request_changes):
    value = copy.deepcopy(request)
    value.update(request_changes)
    out = {"schema": "cain-proposal/1", "proposal_id": "cain:PROP-S", "domain": "stocks", "request": value,
           "based_on": [], "rationale": "test", "source": "agenda"}
    if family:
        out["hypothesis_family"] = family
    return out


def decide(value, view=EMPTY, episode=1):
    return policy.decide(value, view, CONFIG, episode_number=episode)


def test_packaged_stocks_configuration_comes_from_the_pinned_base_and_the_contract():
    assert CONFIG["source"]["commit"] == "61fc017256ffea815ae96bbe02b847dccdb395cc"
    assert CONFIG["contract"]["request_schema_id"] == "stocks-research-request/1"
    assert set(CONFIG["closed_hypotheses"]) == {f"stocks:H{n}" for n in range(1, 23)}
    assert CONFIG["closed_hypotheses"]["stocks:H9"] == "CLOSED_EMBARGO_ORIGINAL"
    assert CONFIG["costs"] == {"fee_bps": 3, "slippage_bps": 15}
    assert CONFIG["allowed_request_types"] == ["BACKTEST_PIT_FACTOR", "COLLECT_EXTERNAL_INTELLIGENCE"]
    for family in ("momentum_12_1", "near_52w_high", "low_vol_252", "volume_surge"):
        assert family in CONFIG["frozen_families"]
    assert not set(CONFIG["closed_hypotheses"]) & set(CONFIG["proposable_hypotheses"])
    assert CONFIG["allowed_symbols"] == []


def test_allow_a_qualification_probe_when_nothing_blocks():
    out = decide(proposal())
    assert (out["decision"], out["rule"]) == ("ALLOW", "R14")


def test_closed_hypotheses_and_frozen_families_are_never_reopened():
    for number in (1, 2, 9, 14, 15, 22):
        out = decide(proposal(hypothesis_id=f"stocks:H{number}"))
        assert (out["decision"], out["reason_code"]) == ("BLOCK", "HYPOTHESIS_CLOSED")
    for family in ("momentum_12_1", "near_52w_high", "low_vol_252", "volume_surge"):
        out = decide(proposal(family=family))
        assert (out["decision"], out["reason_code"]) == ("BLOCK", "HYPOTHESIS_CLOSED")


def test_costs_references_priority_and_domain_are_enforced():
    assert decide(proposal(parameters=dict(REQUEST["parameters"], fee_bps=0)))["reason_code"] == "COST_MODEL_MISMATCH"
    refs = dict(REQUEST["references"], dataset={"name": "b3-cvm-other", "version": "v1"})
    assert decide(proposal(references=refs))["reason_code"] == "REFERENCE_NOT_ALLOWED"
    assert decide(proposal(priority_hint="HIGH"))["reason_code"] == "PRIORITY_ABOVE_CAP"
    assert decide(proposal(hypothesis_id="H9"))["reason_code"] == "DOMAIN_MISMATCH"
    assert decide(proposal(hypothesis_id="crypto:H9"))["reason_code"] == "DOMAIN_MISMATCH"
    assert decide(proposal(hypothesis_id="stocks:QUAL-NEW-001"))["reason_code"] == "NEW_HYPOTHESIS"


def test_costs_are_compared_only_where_the_contract_declares_them():
    # IS-F002: the stocks contract has two parameter shapes; a collection declares no cost keys.
    assert policy.declared_parameters("stocks", COLLECTION["parameters"]) == {"collector", "period", "observed_at"}
    assert {"fee_bps", "slippage_bps"} <= policy.declared_parameters("stocks", REQUEST["parameters"])
    out = decide(proposal(COLLECTION))
    assert (out["decision"], out["rule"]) == ("ALLOW", "R14")
    # a backtest still carries the frozen [H1-FROZEN] costs, and a collection cannot smuggle costs in
    assert decide(proposal(parameters=dict(REQUEST["parameters"], slippage_bps=0)))["reason_code"] == "COST_MODEL_MISMATCH"
    smuggled = decide(proposal(COLLECTION, parameters=dict(COLLECTION["parameters"], fee_bps=0)))
    assert (smuggled["decision"], smuggled["reason_code"]) == ("BLOCK", "SCHEMA_INVALID")
    # parameters no variant accepts: the policy stays conservative (schema first, then costs)
    assert policy.declared_parameters("stocks", {"unknown": 1}) is None


def test_llm_requests_carry_the_placebo_seed_only_where_the_contract_declares_it():
    # IS-F003: the stocks contract has no placebo_seed; the CAIN no longer writes one into stocks requests.
    request = llm._request(REQUEST, "stocks", "stocks:QUAL-PIT-MOM-REAL-002", 7, "stocks:REQ-LLM-0001")
    assert "placebo_seed" not in request["parameters"]
    assert request["parameters"] == REQUEST["parameters"]
    out = decide(proposal(request))
    assert (out["decision"], out["rule"]) == ("ALLOW", "R14")
    # every proposable hypothesis is eligible on an empty view (before: all SCHEMA_INVALID, NO_ELIGIBLE_HYPOTHESIS)
    decisions = llm.eligibility(CONFIG, EMPTY, llm.templates(CONFIG, [REQUEST, COLLECTION]), [], 1)
    assert {h: d["decision"] for h, d in decisions.items()} == {h: "ALLOW" for h in CONFIG["proposable_hypotheses"]}
    # the contract itself still refuses a placebo_seed in a stocks request
    out = decide(proposal(parameters=dict(REQUEST["parameters"], placebo_seed=7)))
    assert (out["decision"], out["reason_code"]) == ("BLOCK", "SCHEMA_INVALID")


def test_each_proposable_hypothesis_has_one_request_type_from_the_frozen_fixtures():
    assert CONFIG["proposable_request_types"] == {
        "stocks:QUAL-EI-COLLECTION-001": "COLLECT_EXTERNAL_INTELLIGENCE",
        "stocks:QUAL-PIT-MOM-001": "BACKTEST_PIT_FACTOR", "stocks:QUAL-PIT-MOM-REAL-001": "BACKTEST_PIT_FACTOR",
        "stocks:QUAL-PIT-MOM-REAL-002": "BACKTEST_PIT_FACTOR", "stocks:QUAL-PIT-MOM-REAL-003": "BACKTEST_PIT_FACTOR"}
    broken = dict(CONFIG, proposable_request_types={})
    with pytest.raises(domain_config.ConfigError):
        domain_config.validate(broken)


def test_a_collection_hypothesis_is_never_sent_as_a_backtest():
    # the utility round: the model chose the collection hypothesis and the CAIN copied the last task (a backtest)
    out = decide(proposal(hypothesis_id="stocks:QUAL-EI-COLLECTION-001"))
    assert (out["decision"], out["reason_code"], out["rule"]) == ("BLOCK", "REQUEST_TYPE_NOT_ALLOWED", "R04")
    out = decide(proposal(COLLECTION, hypothesis_id="stocks:QUAL-PIT-MOM-REAL-001"))
    assert (out["decision"], out["reason_code"], out["rule"]) == ("BLOCK", "REQUEST_TYPE_NOT_ALLOWED", "R04")
    # templates come from the hypothesis's own task, else a task of its request type, never another type
    only_backtest = llm.templates(CONFIG, [REQUEST])
    assert "stocks:QUAL-EI-COLLECTION-001" not in only_backtest
    assert only_backtest["stocks:QUAL-PIT-MOM-REAL-002"]["request_type"] == "BACKTEST_PIT_FACTOR"
    held = llm.eligibility(CONFIG, EMPTY, only_backtest, [], 1)["stocks:QUAL-EI-COLLECTION-001"]
    assert (held["decision"], held["reason_code"]) == ("ABSTAIN", "NO_REQUEST_TEMPLATE")
    both = llm.templates(CONFIG, [COLLECTION, REQUEST])
    assert both["stocks:QUAL-EI-COLLECTION-001"]["request_type"] == "COLLECT_EXTERNAL_INTELLIGENCE"
    request = llm._request(both["stocks:QUAL-EI-COLLECTION-001"], "stocks", "stocks:QUAL-EI-COLLECTION-001", 7,
                           "stocks:REQ-LLM-0002")
    assert decide(proposal(request))["reason_code"] == "ALLOWED"


def _ran(request, task_id, klass="TERMINAL_RESULT", open_task=False):
    task = {"task_id": task_id, "episode": 1, "request_id": request["request_id"],
            "research_id": request["research_id"], "hypothesis_id": request["hypothesis_id"],
            "payload_sha256": "f" * 64, "experiment_sha256": policy.experiment_digest(request)}
    results = [] if open_task else [{"task_id": task_id, "episode": 1, "hypothesis_id": request["hypothesis_id"],
                                     "status": "RESULT", "class": klass, "result_state": "INCONCLUSIVE",
                                     "scientific_state": "INCONCLUSIVE", "economic_state": "NO_EDGE",
                                     "payload_sha256": "e" * 64, "reason_code": None}]
    return dict(EMPTY, tasks=[task], results=results, open_task_ids=[task_id] if open_task else [])


def test_the_same_experiment_under_another_id_adds_no_information():
    # the utility round: QUAL-PIT-MOM-REAL-001/002/003 are one experiment; 12 backtests gave the same number
    view = _ran(REQUEST, "stocks:TASK-" + "1" * 32)
    alias = proposal(hypothesis_id="stocks:QUAL-PIT-MOM-REAL-002", request_id="stocks:REQ-P-0009")
    out = decide(alias, view, 2)
    assert (out["decision"], out["reason_code"], out["rule"]) == ("DUPLICATE", "EQUIVALENT_REQUEST", "R17")
    # a task the domain refused never ran: it does not count
    refused = _ran(REQUEST, "stocks:TASK-" + "2" * 32, klass="TERMINAL_REFUSAL")
    assert decide(alias, refused, 2)["reason_code"] == "ALLOWED"
    # a pending task of the same experiment does count
    assert decide(alias, _ran(REQUEST, "stocks:TASK-" + "3" * 32, open_task=True), 2)["reason_code"] == "EQUIVALENT_REQUEST"
    # new data (another as_of) is another experiment
    assert decide(proposal(hypothesis_id="stocks:QUAL-PIT-MOM-REAL-002", request_id="stocks:REQ-P-0009",
                           as_of="2026-10-05T03:00:00Z"), view, 2)["reason_code"] == "ALLOWED"
    # a new hypothesis still goes to a human first (R11 before R17)
    new = decide(proposal(hypothesis_id="stocks:QUAL-NEW-001", request_id="stocks:REQ-P-0010"), view, 2)
    assert new["reason_code"] == "NEW_HYPOTHESIS"


def test_rationale_counts_and_eligibility_are_checked_against_the_view():
    # cycles 10 and 11 of the utility round (qwen3.5:4b on the real stocks panel)
    row = {"results": 0, "scientific_states": {}, "refusals": [], "eligible_now": True, "not_eligible_reason": None}
    summary = {h: dict(row) for h in CONFIG["proposable_hypotheses"]}
    summary["stocks:QUAL-PIT-MOM-REAL-003"]["results"] = 3
    summary["stocks:QUAL-EI-COLLECTION-001"].update(eligible_now=False, not_eligible_reason="NEGATIVE_STREAK")
    text = ("Esta hipótese é elegível e já possui 4 resultados (episodes 1, 6, 7) todos em estado INCONCLUSIVE. "
            "A stocks:QUAL-PIT-MOM-REAL-001 está com streak negativo e não é elegível. "
            "A stocks:QUAL-EI-COLLECTION-001 está com streak negativo e não é elegível.")
    check = llm.rationale_check(text, CONFIG, EMPTY, chosen="stocks:QUAL-PIT-MOM-REAL-003", summary=summary)
    assert [(c["hypothesis"], c["cited"], c["actual"]) for c in check["count_mismatches"]] == [
        ("stocks:QUAL-PIT-MOM-REAL-003", [4], 3)]
    assert [(c["hypothesis"], c["claimed_eligible"]) for c in check["eligibility_mismatches"]] == [
        ("stocks:QUAL-PIT-MOM-REAL-001", False)]
    # a sentence naming several hypotheses is skipped: pairing numbers to names there would be a guess
    many = "QUAL-PIT-MOM-REAL-001 tem 1, QUAL-PIT-MOM-REAL-002 e REAL-003 têm 2 resultados cada."
    assert llm.rationale_check(many, CONFIG, EMPTY, summary=summary)["count_mismatches"] == []
    # without a summary only the naming checks run
    assert llm.rationale_check(text, CONFIG, EMPTY)["count_mismatches"] == []


def test_economic_watch_never_raises_priority_or_budget():
    results = [{"task_id": f"stocks:TASK-{n:032d}", "episode": n, "hypothesis_id": "stocks:QUAL-PIT-MOM-REAL-001",
                "status": "RESULT", "class": "TERMINAL_RESULT", "result_state": "WATCH_NO_CAPITAL",
                "scientific_state": "SUPPORTED", "economic_state": "WATCH", "payload_sha256": "a" * 64}
               for n in (1, 2, 3)]
    view = dict(EMPTY, results=results)
    assert decide(proposal(priority_hint="HIGH"), view, 4)["reason_code"] == "PRIORITY_ABOVE_CAP"
    many = [{"task_id": f"stocks:TASK-{n:032d}", "episode": n, "request_id": f"stocks:REQ-{n}",
             "research_id": REQUEST["research_id"], "hypothesis_id": REQUEST["hypothesis_id"],
             "payload_sha256": f"{n:064d}"} for n in range(64)]
    assert decide(proposal(), dict(view, tasks=many), 65)["reason_code"] == "BUDGET_EXHAUSTED"


def test_same_h9_in_three_domains_never_mixes_in_the_stocks_orchestration():
    reasons = {d: decide(proposal(hypothesis_id=f"{d}:H9"))["reason_code"] for d in ("crypto", "stocks", "brasileirao")}
    assert reasons == {"crypto": "DOMAIN_MISMATCH", "stocks": "HYPOTHESIS_CLOSED", "brasileirao": "DOMAIN_MISMATCH"}


def test_stocks_and_crypto_configurations_are_distinct_and_hashed():
    crypto = domain_config.load("crypto")
    assert domain_config.digest(CONFIG) != domain_config.digest(crypto)
    assert not set(CONFIG["closed_hypotheses"]) & set(crypto["closed_hypotheses"])
    assert CONFIG["costs"] != crypto["costs"]

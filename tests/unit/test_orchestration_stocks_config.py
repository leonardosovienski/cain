"""The packaged stocks configuration of the (unchanged) generic DecisionPolicy (integration-stocks).

Pure functions, no I/O: the configuration comes from the pinned stocks base 61fc017 (closed hypotheses, their
families and the [H1-FROZEN] costs) and the contract; the policy is the same code as for crypto.
"""

import copy

from cain.orchestration import config as domain_config
from cain.orchestration import policy

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


def test_known_framework_limits_fail_closed_for_stocks():
    # IS-F002: the generic R06 compares costs on every request; a collection carries none.
    assert decide(proposal(COLLECTION))["reason_code"] == "COST_MODEL_MISMATCH"
    # IS-F003: the LLM proposal path writes the crypto placebo_seed, which the stocks schema refuses.
    out = decide(proposal(parameters=dict(REQUEST["parameters"], placebo_seed=7)))
    assert (out["decision"], out["reason_code"]) == ("BLOCK", "SCHEMA_INVALID")


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

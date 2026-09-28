"""The packaged brasileirao configuration of the (unchanged) generic DecisionPolicy (integration-brasileirao).

Pure functions, no I/O: the configuration comes from the pinned Brasileirão base 25cdf4d (trials with status
refutada), the contract (hypotheses the admission protects) and CAIN's own research-loop ledger of PR #50 (the
hypothesis that stopped without improvement and its world as a frozen family); the policy is the same code as for
crypto and stocks. No data of the real dataset appears here: requests only name operator references.
"""

import copy

from cain.orchestration import config as domain_config
from cain.orchestration import policy

CONFIG = domain_config.load("brasileirao")
REQUEST = {
    "schema_version": "brasileirao-research-request/1",
    "request_id": "brasileirao:REQ-P-0001",
    "request_type": "WALKFORWARD_FORECAST_EVALUATION",
    "research_id": "brasileirao:RESEARCH-INTEGRATION-QUALIFICATION",
    "hypothesis_id": "brasileirao:QUAL-SERVING-REAL-001",
    "competition": "Brasileirão Série A",
    "season": 2024,
    "target": "OU25",
    "events": {"kickoff_from": "2024-07-01T00:00:00Z", "kickoff_to": "2024-10-01T00:00:00Z"},
    "data_cutoff": "2026-09-08T19:31:32Z",
    "decision_lead_minutes": 60,
    "references": {"dataset": {"name": "real-20260908", "version": "1"},
                   "model": {"name": "serving-baseline", "version": "1"},
                   "features": {"name": "elo-home-advantage", "version": "1"},
                   "baseline": {"name": "market", "version": "1"},
                   "cost_model": {"name": "close-slippage-tax", "version": "1"},
                   "odds": {"name": "sofascore-close", "version": "1"}},
    "priority_hint": "NORMAL",
}
EMPTY = {"domain": "brasileirao", "episodes": 0, "tasks": [], "results": [], "open_task_ids": [], "requires_human": []}
REFUTED = ("h1-ou25-edge-2-15-walkforward", "H4_DIXON_COLES_CALIBRATED", "h11-refit-cadence-rodada-vs-100jogos",
           "market-03-edge-ordering-sofascore-diagnostic", "market-04-ou25-btts-resolution-and-ordering",
           "market-06-ou25-dev-only-ordering-triage")
PROTECTED = ("H8", "H9", "H14", "H15", "A1")
LOOP = "brasileirao:CAIN-LOOP.BR-ELO-TUNING-DEV2022"
LOOP_FAMILY = "brasileirao-elo-1x2-dev2022"


def proposal(request=REQUEST, family=None, **request_changes):
    value = copy.deepcopy(request)
    value.update(request_changes)
    out = {"schema": "cain-proposal/1", "proposal_id": "cain:PROP-B", "domain": "brasileirao", "request": value,
           "based_on": [], "rationale": "test", "source": "agenda"}
    if family:
        out["hypothesis_family"] = family
    return out


def decide(value, view=EMPTY, episode=1):
    return policy.decide(value, view, CONFIG, episode_number=episode)


def test_packaged_brasileirao_configuration_comes_from_the_pinned_base_the_contract_and_the_loop():
    assert CONFIG["source"]["commit"] == "25cdf4d9bb309d33f066fbc6a379f5d98c69f08a"
    assert [f["path"] for f in CONFIG["source"]["files"]] == ["data/trials.json"]
    assert CONFIG["contract"]["request_schema_id"] == "brasileirao-research-request/1"
    expected = {f"brasileirao:{t}" for t in REFUTED} | {f"brasileirao:{h}" for h in PROTECTED} | {LOOP}
    assert set(CONFIG["closed_hypotheses"]) == expected
    assert CONFIG["frozen_families"] == [LOOP_FAMILY]
    assert CONFIG["costs"] == {} and CONFIG["allowed_symbols"] == []
    assert CONFIG["allowed_request_types"] == ["WALKFORWARD_FORECAST_EVALUATION"]
    assert not set(CONFIG["closed_hypotheses"]) & set(CONFIG["proposable_hypotheses"])
    assert CONFIG["allowed_references"]["baseline"] == ["climatology 1", "market 1"]


def test_allow_a_qualification_probe_when_nothing_blocks():
    out = decide(proposal())
    assert (out["decision"], out["rule"]) == ("ALLOW", "R14")


def test_closed_protected_and_loop_hypotheses_and_the_loop_family_are_never_reopened():
    for hypothesis in [*(f"brasileirao:{t}" for t in REFUTED), *(f"brasileirao:{h}" for h in PROTECTED), LOOP]:
        out = decide(proposal(hypothesis_id=hypothesis))
        assert (out["decision"], out["reason_code"]) == ("BLOCK", "HYPOTHESIS_CLOSED"), hypothesis
    out = decide(proposal(family=LOOP_FAMILY))
    assert (out["decision"], out["reason_code"]) == ("BLOCK", "HYPOTHESIS_CLOSED")


def test_references_priority_and_domain_are_enforced():
    refs = dict(REQUEST["references"], dataset={"name": "real-other", "version": "1"})
    assert decide(proposal(references=refs))["reason_code"] == "REFERENCE_NOT_ALLOWED"
    assert decide(proposal(priority_hint="HIGH"))["reason_code"] == "PRIORITY_ABOVE_CAP"
    assert decide(proposal(hypothesis_id="H9"))["reason_code"] == "DOMAIN_MISMATCH"
    assert decide(proposal(hypothesis_id="stocks:H9"))["reason_code"] == "DOMAIN_MISMATCH"
    assert decide(proposal(hypothesis_id="brasileirao:QUAL-NEW-001"))["reason_code"] == "NEW_HYPOTHESIS"


def test_a_request_with_parameters_is_refused_by_the_brasileirao_schema():
    # the brasileirao request_schema has no parameters (additionalProperties false)
    out = decide(proposal(parameters={"placebo_seed": 7}))
    assert (out["decision"], out["reason_code"]) == ("BLOCK", "SCHEMA_INVALID")


def test_the_sealed_2025_holdout_goes_to_a_human():
    # D-25 (2): a proposal that would touch the 2025 holdout ends in REQUIRE_HUMAN (R16 SEALED_SCOPE); the domain
    # admission still refuses it (HOLDOUT_SEALED). The three frozen holdout vectors of the integration-brasileirao.
    assert [rule["field"] if "field" in rule else "window" for rule in CONFIG["sealed_scopes"]] == [
        "season", "window", "events.fixtures[].kickoff_at"]
    for season, start, end in ((2025, "2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
                               (2024, "2024-10-01T00:00:00Z", "2025-03-01T00:00:00Z"),
                               (2026, "2026-01-01T00:00:00Z", "2026-09-08T19:31:32Z")):
        out = decide(proposal(season=season, events={"kickoff_from": start, "kickoff_to": end}))
        assert (out["decision"], out["reason_code"], out["rule"]) == ("REQUIRE_HUMAN", "SEALED_SCOPE", "R16"), season
    inside = {"kickoff_from": "2024-01-01T00:00:00Z", "kickoff_to": "2024-12-31T00:00:00Z",
              "fixtures": [{"event_id": 1, "kickoff_at": "2025-02-01T21:00:00Z"}]}
    assert decide(proposal(events=inside))["reason_code"] == "SEALED_SCOPE"
    assert decide(proposal())["rule"] == "R14"  # 2024, window before 2025: not sealed


def test_negative_results_never_raise_priority_or_budget():
    results = [{"task_id": f"brasileirao:TASK-{n:032d}", "episode": n, "hypothesis_id": "brasileirao:QUAL-SERVING-REAL-001",
                "status": "RESULT", "class": "TERMINAL_RESULT", "result_state": "NO_EDGE",
                "scientific_state": "SUPPORTED", "economic_state": "NO_EDGE", "payload_sha256": "a" * 64}
               for n in (1, 2, 3)]
    view = dict(EMPTY, results=results)
    assert decide(proposal(priority_hint="HIGH"), view, 4)["reason_code"] == "PRIORITY_ABOVE_CAP"
    assert decide(proposal(), view, 4)["decision"] == "COOLDOWN"


def test_same_h9_in_three_domains_never_mixes_in_the_brasileirao_orchestration():
    reasons = {d: decide(proposal(hypothesis_id=f"{d}:H9"))["reason_code"] for d in ("crypto", "stocks", "brasileirao")}
    assert reasons == {"crypto": "DOMAIN_MISMATCH", "stocks": "DOMAIN_MISMATCH", "brasileirao": "HYPOTHESIS_CLOSED"}


def test_three_configurations_are_distinct_and_hashed():
    others = [domain_config.load("crypto"), domain_config.load("stocks")]
    assert len({domain_config.digest(c) for c in (CONFIG, *others)}) == 3
    for other in others:
        assert not set(CONFIG["closed_hypotheses"]) & set(other["closed_hypotheses"])
        assert CONFIG["costs"] != other["costs"]

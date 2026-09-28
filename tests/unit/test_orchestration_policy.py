"""DecisionPolicy rules, one by one, on the packaged crypto configuration (pure function, no I/O)."""

import copy

import pytest

from cain.orchestration import config as domain_config
from cain.orchestration import policy

CONFIG = domain_config.load("crypto")
REQUEST = {
    "schema_version": "crypto-research-request/1",
    "request_id": "crypto:REQ-P-0001",
    "request_type": "BACKTEST_EXISTING_HYPOTHESIS",
    "research_id": "crypto:RESEARCH-P",
    "hypothesis_id": "crypto:QUAL-SHADOW-REAL-001",
    "references": {"protocol": {"name": "fixed-shadow", "version": "v1"},
                   "dataset": {"name": "real-in-sample", "version": "v1"},
                   "baseline": {"name": "flat", "version": "v1"},
                   "cost_model": {"name": "v3-frozen", "version": "v1"},
                   "evidence": {"name": "none", "version": "v1"}},
    "data_cutoff": "2026-08-31T00:00:00Z",
    "parameters": {"symbol": "BTCUSDT", "horizon_days": 7, "max_observations": 100, "fee_bps": 10,
                   "slippage_bps": 5, "placebo_seed": 1},
    "priority_hint": "NORMAL",
}
EMPTY = {"domain": "crypto", "episodes": 0, "tasks": [], "results": [], "open_task_ids": [], "requires_human": []}


def proposal(**request_changes):
    request = copy.deepcopy(REQUEST)
    request.update(request_changes)
    return {"schema": "cain-proposal/1", "proposal_id": "cain:PROP-1", "domain": "crypto", "request": request,
            "based_on": [], "rationale": "test", "source": "agenda"}


def decide(value, view=EMPTY, episode=1):
    return policy.decide(value, view, CONFIG, episode_number=episode)


def result(task_id, episode, state="NO_EDGE", scientific="INCONCLUSIVE", hypothesis="crypto:QUAL-SHADOW-REAL-001",
           klass="TERMINAL_RESULT", economic="NO_EDGE"):
    return {"task_id": task_id, "episode": episode, "hypothesis_id": hypothesis, "status": "RESULT",
            "class": klass, "result_state": state, "scientific_state": scientific, "economic_state": economic,
            "payload_sha256": "a" * 64}


def task(task_id, episode, content="c" * 64, request_id="crypto:REQ-OTHER"):
    return {"task_id": task_id, "episode": episode, "request_id": request_id, "research_id": "crypto:RESEARCH-P",
            "hypothesis_id": "crypto:QUAL-SHADOW-REAL-001", "payload_sha256": content}


def test_packaged_crypto_configuration_comes_from_the_pinned_base():
    assert CONFIG["source"]["commit"] == "341d270e4d709150c581c3cd93f4518d483009eb"
    assert set(CONFIG["closed_hypotheses"]) == {f"crypto:H{n}" for n in range(1, 10)}
    assert CONFIG["frozen_families"] == ["funding_oi_hmm_v3"]
    assert CONFIG["costs"] == {"fee_bps": 10, "slippage_bps": 5}
    assert CONFIG["allowed_request_types"] == ["BACKTEST_EXISTING_HYPOTHESIS"]


def test_allow_when_nothing_blocks():
    assert decide(proposal())["decision"] == "ALLOW"


@pytest.mark.parametrize("value, code", [
    (dict(proposal(), domain="stocks"), "DOMAIN_MISMATCH"),
    (proposal(hypothesis_id="stocks:H9"), "DOMAIN_MISMATCH"),
    (proposal(hypothesis_id="brasileirao:H9"), "DOMAIN_MISMATCH"),
    (proposal(request_id="REQ-NO-DOMAIN"), "DOMAIN_MISMATCH"),
    (dict(proposal(), based_on=["stocks:RESULT-1"]), "DOMAIN_MISMATCH"),
    (dict(proposal(), schema="cain-proposal/2"), "SCHEMA_INVALID"),
    (proposal(horizon_days=7.5), "SCHEMA_INVALID"),
    (dict(proposal(), handler="python -m anything"), "FORBIDDEN_FIELD"),
    (dict(proposal(), capital_permission=True), "FORBIDDEN_FIELD"),
    (proposal(client_ref={"x": 1}), "FORBIDDEN_FIELD"),
    (proposal(hypothesis_id="crypto:H9"), "HYPOTHESIS_CLOSED"),
    (proposal(hypothesis_id="crypto:H7"), "HYPOTHESIS_CLOSED"),
    (dict(proposal(), hypothesis_family="funding_oi_hmm_v3"), "HYPOTHESIS_CLOSED"),
    (proposal(parameters=dict(REQUEST["parameters"], fee_bps=0)), "COST_MODEL_MISMATCH"),
    (proposal(parameters=dict(REQUEST["parameters"], symbol="ETHUSDT")), "SYMBOL_NOT_ALLOWED"),
    (proposal(references=dict(REQUEST["references"], dataset={"name": "other", "version": "v1"})),
     "REFERENCE_NOT_ALLOWED"),
    (proposal(priority_hint="HIGH"), "PRIORITY_ABOVE_CAP"),
])
def test_block_rules(value, code):
    out = decide(value)
    assert (out["decision"], out["reason_code"]) == ("BLOCK", code)


def test_same_h9_in_three_domains_never_mixes():
    reasons = [decide(proposal(hypothesis_id=f"{d}:H9"))["reason_code"] for d in ("crypto", "stocks", "brasileirao")]
    assert reasons == ["HYPOTHESIS_CLOSED", "DOMAIN_MISMATCH", "DOMAIN_MISMATCH"]


def test_duplicate_and_request_id_conflict():
    probe = policy.decide(proposal(), EMPTY, CONFIG, episode_number=1)
    assert probe["decision"] == "ALLOW"
    from research_protocol import v2

    content = v2.request_content_hash(REQUEST)
    view = dict(EMPTY, tasks=[task("crypto:TASK-" + "1" * 32, 1, content=content, request_id="crypto:REQ-X")])
    assert decide(proposal(), view)["decision"] == "DUPLICATE"
    view = dict(EMPTY, tasks=[task("crypto:TASK-" + "1" * 32, 1, request_id=REQUEST["request_id"])])
    assert decide(proposal(), view)["reason_code"] == "REQUEST_ID_CONFLICT"


def test_require_human_contradiction_new_hypothesis_and_reconciliation():
    t1, t2 = "crypto:TASK-" + "1" * 32, "crypto:TASK-" + "2" * 32
    contradiction = dict(EMPTY, results=[result(t1, 1, "WATCH_NO_CAPITAL", "SUPPORTED", economic="WATCH"),
                                         result(t2, 2, "REFUTED", "REFUTED")])
    out = decide(proposal(), contradiction, episode=3)
    assert (out["decision"], out["reason_code"]) == ("REQUIRE_HUMAN", "CONTRADICTION_UNRESOLVED")
    majority = dict(contradiction, results=contradiction["results"] + [result("crypto:TASK-" + "3" * 32, 3,
                                                                              "REFUTED", "REFUTED")])
    assert decide(proposal(), majority, episode=4)["reason_code"] == "CONTRADICTION_UNRESOLVED"
    assert decide(proposal(hypothesis_id="crypto:NEW-IDEA"))["reason_code"] == "NEW_HYPOTHESIS"
    held = dict(EMPTY, requires_human=[t1])
    assert decide(proposal(), held)["reason_code"] == "DOMAIN_RECONCILIATION_PENDING"


def test_abstain_on_open_task_and_budget():
    t1 = "crypto:TASK-" + "1" * 32
    assert decide(proposal(), dict(EMPTY, tasks=[task(t1, 1)], open_task_ids=[t1]))["reason_code"] == "OPEN_TASK_PENDING"
    many = [task(f"crypto:TASK-{n:032d}", n) for n in range(64)]
    assert decide(proposal(), dict(EMPTY, tasks=many))["reason_code"] == "BUDGET_EXHAUSTED"


def test_cooldown_after_negative_streak_then_allowed_again():
    tasks = [task(f"crypto:TASK-{n:032d}", n) for n in (1, 2, 3)]
    results = [result(t["task_id"], t["episode"]) for t in tasks]
    view = dict(EMPTY, tasks=tasks, results=results)
    assert decide(proposal(), view, episode=4)["decision"] == "COOLDOWN"
    assert decide(proposal(), view, episode=5)["decision"] == "COOLDOWN"
    assert decide(proposal(), view, episode=6)["decision"] == "ALLOW"


def test_negative_results_never_widen_what_is_allowed():
    """NEGATIVE_RESULT_NEUTRALITY: any sequence of negative results is at most as permissive as none."""
    blocked = [proposal(priority_hint="HIGH"), proposal(hypothesis_id="crypto:H1"),
               proposal(parameters=dict(REQUEST["parameters"], fee_bps=0)), proposal(hypothesis_id="crypto:NEW")]
    for state in CONFIG["negative_result_states"]:
        tasks = [task(f"crypto:TASK-{n:032d}", n) for n in range(1, 11)]
        view = dict(EMPTY, tasks=tasks, results=[result(t["task_id"], t["episode"], state) for t in tasks])
        for value in blocked:
            assert decide(value, view, episode=11)["decision"] != "ALLOW"
        many = [task(f"crypto:TASK-{n:032d}", n) for n in range(64)]
        assert decide(proposal(), dict(view, tasks=many), episode=65)["decision"] != "ALLOW"


def test_economic_watch_is_not_a_signal():
    tasks = [task(f"crypto:TASK-{n:032d}", n) for n in (1, 2, 3)]
    watch = dict(EMPTY, tasks=tasks, results=[result(t["task_id"], t["episode"], "WATCH_NO_CAPITAL", "SUPPORTED",
                                                     economic="WATCH") for t in tasks])
    assert decide(proposal(priority_hint="HIGH"), watch, episode=4)["reason_code"] == "PRIORITY_ABOVE_CAP"
    many = [task(f"crypto:TASK-{n:032d}", n) for n in range(64)]
    assert decide(proposal(), dict(watch, tasks=many), episode=65)["reason_code"] == "BUDGET_EXHAUSTED"


def test_receipt_is_canonical_deterministic_and_names_policy_and_config():
    out = decide(proposal())
    kwargs = dict(episode_number=1, as_of="2026-09-27T00:00:00Z", task=None)
    first = policy.dumps(policy.receipt(proposal(), EMPTY, CONFIG, domain_config.digest(CONFIG), out, **kwargs))
    second = policy.dumps(policy.receipt(proposal(), EMPTY, CONFIG, domain_config.digest(CONFIG), out, **kwargs))
    assert first == second
    receipt = policy.receipt(proposal(), EMPTY, CONFIG, domain_config.digest(CONFIG), out, **kwargs)
    assert receipt["policy"] == {"id": "cain-decision-policy", "version": 1, "code_sha256": policy.code_sha256()}
    assert receipt["config"]["sha256"] == domain_config.digest(CONFIG) and receipt["capital_permission"] is False
    with pytest.raises(ValueError):
        policy.receipt(proposal(), EMPTY, CONFIG, "x", out, episode_number=1, as_of="2026-09-27", task=None)


def test_configuration_rejects_closed_hypothesis_made_proposable():
    broken = copy.deepcopy(CONFIG)
    broken["proposable_hypotheses"].append("crypto:H9")
    with pytest.raises(domain_config.ConfigError):
        domain_config.validate(broken)
    with pytest.raises(domain_config.ConfigError):
        domain_config.load("brasileirao")

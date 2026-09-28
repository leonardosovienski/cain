"""R16 SEALED_SCOPE: uma proposta que tocaria um escopo lacrado do domínio (ex.: o holdout 2025 do Brasileirão) vai
para um humano; campo lacrado ausente ou malformado também (fail closed).

Vetores: as três propostas de holdout congeladas pela integration-brasileirao
(predictor-qualification, qualification/integration-brasileirao/fixtures/proposals/holdout/0{1,2,3}-*.json), com o
critério D-25 (2) em formato de máquina; controles fora do lacre não disparam a R16.
"""

import copy

import pytest

from cain.orchestration import config as domain_config
from cain.orchestration import policy

SEALED_2025 = [
    {"field": "season", "any_of": [2025, 2026]},
    {
        "window": {"from": "events.kickoff_from", "to": "events.kickoff_to"},
        "intersects": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
    },
    {"field": "events.fixtures[].kickoff_at", "within": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
     "optional": True},
]
REQUEST = {  # 01-season-2025.json (request), o molde dos três vetores
    "competition": "Brasileirão Série A",
    "data_cutoff": "2026-09-08T19:31:32Z",
    "decision_lead_minutes": 60,
    "events": {"kickoff_from": "2025-01-01T00:00:00Z", "kickoff_to": "2026-01-01T00:00:00Z"},
    "hypothesis_id": "brasileirao:HQ-SERVING-BASELINE",
    "priority_hint": "NORMAL",
    "references": {
        "baseline": {"name": "climatology", "version": "1"},
        "cost_model": {"name": "close-slippage-tax", "version": "1"},
        "dataset": {"name": "synthetic", "version": "1"},
        "features": {"name": "elo-home-advantage", "version": "1"},
        "model": {"name": "serving-baseline", "version": "1"},
        "odds": {"name": "sofascore-close", "version": "1"},
    },
    "request_id": "brasileirao:REQ-IB-HOLDOUT-001",
    "request_type": "WALKFORWARD_FORECAST_EVALUATION",
    "research_id": "brasileirao:R-CONFORMANCE",
    "schema_version": "brasileirao-research-request/1",
    "season": 2025,
    "target": "1X2",
}
EMPTY = {"domain": "brasileirao", "episodes": 0, "tasks": [], "results": [], "open_task_ids": [],
         "requires_human": []}


def _config():
    config = copy.deepcopy(domain_config.load("brasileirao"))
    config["sealed_scopes"] = copy.deepcopy(SEALED_2025)
    return domain_config.validate(config)


def _decide(season, kickoff_from, kickoff_to, config=None):
    request = copy.deepcopy(REQUEST)
    request.update(season=season, events={"kickoff_from": kickoff_from, "kickoff_to": kickoff_to})
    proposal = {"schema": "cain-proposal/1", "proposal_id": "cain:SEALED-1", "domain": "brasileirao",
                "request": request, "based_on": [], "rationale": "teste", "source": "agenda"}
    return policy.decide(proposal, EMPTY, config or _config(), episode_number=1)


@pytest.mark.parametrize(
    "season,kickoff_from,kickoff_to",
    [
        (2025, "2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),  # 01-season-2025
        (2024, "2024-10-01T00:00:00Z", "2025-03-01T00:00:00Z"),  # 02-window-into-2025
        (2026, "2026-01-01T00:00:00Z", "2026-09-08T19:31:32Z"),  # 03-season-2026
    ],
)
def test_frozen_holdout_vectors_go_to_a_human(season, kickoff_from, kickoff_to):
    out = _decide(season, kickoff_from, kickoff_to)
    assert (out["decision"], out["reason_code"], out["rule"]) == ("REQUIRE_HUMAN", "SEALED_SCOPE", "R16")


def test_outside_the_seal_the_rule_does_not_fire():
    assert _decide(2024, "2024-01-01T00:00:00Z", "2024-12-31T00:00:00Z")["rule"] != "R16"
    # [from, to) semiaberto: terminar exatamente no início do lacre não o toca
    assert _decide(2024, "2024-06-01T00:00:00Z", "2025-01-01T00:00:00Z")["rule"] != "R16"
    empty = copy.deepcopy(_config())
    empty["sealed_scopes"] = []
    assert _decide(2025, "2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z", empty)["rule"] != "R16"


def test_sealed_field_absent_or_malformed_holds_the_request():
    assert policy._sealed({"events": REQUEST["events"]}, SEALED_2025) == "season absent"
    assert policy._sealed({"season": True, "events": REQUEST["events"]}, SEALED_2025) == "season malformed"
    backwards = {"season": 2024, "events": {"kickoff_from": "2024-12-01T00:00:00Z",
                                            "kickoff_to": "2024-01-01T00:00:00Z"}}
    assert "malformed" in policy._sealed(backwards, SEALED_2025)
    bad_time = {"season": 2024, "events": {"kickoff_from": "2024-01-01", "kickoff_to": "2024-02-01T00:00:00Z"}}
    assert "malformed" in policy._sealed(bad_time, SEALED_2025)


def test_optional_instants_seal_only_when_present_and_inside():
    events = {"kickoff_from": "2024-01-01T00:00:00Z", "kickoff_to": "2024-12-31T00:00:00Z"}
    assert policy._sealed({"season": 2024, "events": events}, SEALED_2025) is None
    inside = dict(events, fixtures=[{"kickoff_at": "2024-05-01T00:00:00Z"}, {"kickoff_at": "2025-02-01T21:00:00Z"}])
    assert "within sealed" in policy._sealed({"season": 2024, "events": inside}, SEALED_2025)
    malformed = dict(events, fixtures=[{"kickoff_at": 1}])
    assert policy._sealed({"season": 2024, "events": malformed}, SEALED_2025) == (
        "events.fixtures[].kickoff_at malformed"
    )


def test_crypto_seals_nothing_and_a_crypto_seal_would_fire():
    crypto = domain_config.load("crypto")
    assert crypto["sealed_scopes"] == []
    request = {"parameters": {"symbol": "BTCUSDT"}, "data_cutoff": "2026-08-31T00:00:00Z"}
    assert policy._sealed(request, crypto["sealed_scopes"]) is None
    rule = [{"field": "parameters.symbol", "any_of": ["BTCUSDT"]}]
    assert policy._sealed(request, rule) == "parameters.symbol = 'BTCUSDT' is sealed"


@pytest.mark.parametrize(
    "rules",
    [
        {"field": "season", "any_of": [2025]},  # não é lista
        [{"field": "season"}],  # sem tipo de lacre
        [{"field": "season", "any_of": []}],
        [{"field": "season", "any_of": [2025.0]}],
        [{"field": "season", "any_of": [2025], "within": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"]}],
        [{"field": "season", "any_of": [2025], "extra": 1}],
        [{"field": "season", "any_of": [2025], "optional": "yes"}],
        [{"field": "bad path!", "any_of": [2025]}],
        [{"window": {"from": "events.kickoff_from"}, "intersects": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"]}],
        [{"window": {"from": "a[]", "to": "b"}, "intersects": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"]}],
        [{"window": {"from": "a", "to": "b"}, "intersects": ["2026-01-01T00:00:00Z", "2025-01-01T00:00:00Z"]}],
        [{"field": "x", "within": ["2025-01-01", "2026-01-01T00:00:00Z"]}],
    ],
)
def test_malformed_sealed_scopes_are_refused_at_load(rules):
    config = copy.deepcopy(domain_config.load("crypto"))
    config["sealed_scopes"] = rules
    with pytest.raises(domain_config.ConfigError):
        domain_config.validate(config)

"""result_metrics: the numbers of a domain result the CAIN keeps in memory and shows the model.

Practical validation of 2026-09-28 (integration-crypto): the memory facts and the LLM context carried state labels
only ("INCONCLUSIVE x2"), never the net return, its confidence interval or the sample. The key is optional: a domain
without it keeps the same configuration bytes, facts and prompt.
"""

import copy

import pytest

from cain.orchestration import config as domain_config

CRYPTO = {"net_ci_high_bps": "domain_facts.metrics.net_ci_high_bps",
          "net_ci_low_bps": "domain_facts.metrics.net_ci_low_bps",
          "net_return_bps": "domain_facts.metrics.net_return_bps",
          "sample_size": "domain_facts.metrics.sample_size"}


def test_crypto_declares_net_return_ci_and_sample_and_the_other_domains_declare_none():
    assert domain_config.load("crypto")["result_metrics"] == CRYPTO
    for domain in ("stocks", "brasileirao"):
        assert "result_metrics" not in domain_config.load(domain)


def test_only_finite_numbers_at_the_declared_paths_are_kept():
    config = {"result_metrics": {"a": "x.y", "b": "x.text", "c": "x.none", "d": "x.missing", "e": "x.y.deeper",
                                 "f": "x.flag", "g": "x.nan", "h": "x.inf", "i": "x.list", "j": "x.obj", "k": "x.half"}}
    payload = {"x": {"y": -118, "text": "2026-09-01T00:00:00Z", "none": None, "flag": True, "nan": float("nan"),
                     "inf": float("inf"), "list": [1], "obj": {"v": 1}, "half": 0.5}}
    assert domain_config.result_metrics(config, payload) == {"a": -118, "k": 0.5}
    assert domain_config.result_metrics({}, payload) == {}
    assert domain_config.result_metrics(config, {}) == {}


@pytest.mark.parametrize("bad", [[], {"Net": "a.b"}, {"n": "a..b"}, {"n": "1a"}, {"n": 3}, {"n": ""},
                                 {f"m{i}": "a" for i in range(17)}])
def test_malformed_result_metrics_are_refused(bad):
    config = copy.deepcopy(domain_config.load("crypto"))
    config["result_metrics"] = bad
    with pytest.raises(domain_config.ConfigError):
        domain_config.validate(config)

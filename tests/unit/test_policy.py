"""Versioned policy files: the version in force at an instant, and a malformed history refused."""

import importlib
import json

import pytest

from cain import policy as policies


def test_the_shipped_policies_are_versioned_and_hashed():
    for package, stem in (("cain.claims", "verifier-policy"), ("cain.findings", "findings-policy")):
        found = policies.versions(package, stem)
        assert [v["version"] for v in found] == [1] and len(found[0]["sha256"]) == 64
        assert policies.ref(found[0]) == {"policy": found[0]["policy"], "version": 1, "sha256": found[0]["sha256"]}


def test_the_version_in_force_is_the_one_of_the_registration_instant():
    history = [{"policy": "p", "version": 1, "sha256": "a"},
               {"policy": "p", "version": 2, "sha256": "b", "effective_from": "2026-10-01T00:00:00Z"}]
    assert policies.effective(history, "2026-09-30T23:59:59.999999Z")["version"] == 1
    assert policies.effective(history, "2026-10-01T00:00:00.500000Z")["version"] == 2  # not a string comparison
    assert policies.effective(history, "2026-10-01T00:00:00+00:00")["version"] == 2
    assert policies.effective(history)["version"] == 2  # None: the latest, for what is registered now
    with pytest.raises(policies.PolicyError):
        policies.effective(history, "2026-10-01T00:00:00")  # an instant without a time zone


def test_a_history_with_a_gap_or_without_effective_from_is_refused(tmp_path, monkeypatch):
    package = tmp_path / "policy_fixture_pkg"
    (package / "data").mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "data" / "rule.json").write_text(json.dumps({"policy": "rule", "version": 1}))
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    assert [v["version"] for v in policies.versions("policy_fixture_pkg", "rule")] == [1]
    (package / "data" / "rule-v3.json").write_text(json.dumps({"policy": "rule", "version": 3,
                                                               "effective_from": "2026-10-01T00:00:00Z"}))
    with pytest.raises(policies.PolicyError, match="without gaps"):
        policies.versions("policy_fixture_pkg", "rule")
    (package / "data" / "rule-v3.json").unlink()
    (package / "data" / "rule-v2.json").write_text(json.dumps({"policy": "rule", "version": 2}))
    with pytest.raises(policies.PolicyError, match="effective_from"):
        policies.versions("policy_fixture_pkg", "rule")

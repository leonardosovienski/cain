from pathlib import Path

import pytest
from research_snapshot import canonical

import test_research_l0 as cases

setup = cases.setup


def test_revoked_scope_is_rejected_before_source_file_open(setup, monkeypatch):
    service, scope, _, policy, path = setup
    policy["grants"] = []
    path.write_bytes(canonical(policy))
    original = Path.open

    def protected(self, *args, **kwargs):
        if self.name == "unadmitted.json":
            raise AssertionError("source content opened before admission")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", protected)
    with pytest.raises(ValueError, match="rejected"):
        service.ingest("unadmitted.json", scope)


def test_history_questions_are_redacted_after_source_revocation(setup):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication())
    service.query(scope, source_id="A", session_id="session")
    assert service.history(scope, "session")[0]["request"]["source_id"] == "A"
    policy["grants"] = []
    path.write_bytes(canonical(policy))
    assert service.history(scope, "session")[0]["request"] == {"redacted_by_current_policy": True}

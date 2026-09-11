import json
from pathlib import Path

import pytest
from research_snapshot import canonical
from cain.research import ResearchService
from test_research_l0 import publication
from test_research_l0 import setup as root_fixture

setup = root_fixture


def test_scope_bound_roots_and_offline_query(setup, tmp_path):
    service, scope, _, policy, policy_path = setup
    first = Path(policy.pop("import_root"))
    second = tmp_path / "stocks"
    second.mkdir()
    policy["version"] = 2
    policy["imports"] = [
        dict(user="leo", project="", collection="crypto", root=str(first)),
        dict(user="leo", project="", collection="stocks", root=str(second)),
    ]
    policy["grants"] = [
        dict(g, collection=g["domain"]) for g in policy["grants"] if g["project"] == ""
    ]
    policy_path.write_bytes(canonical(policy))
    for domain, root in (("crypto", first), ("stocks", second)):
        (root / "same.json").write_bytes(canonical(publication(domain=domain)))
        target = service.scope(collection=domain)
        assert service.ingest("same.json", target)["status"] == "admitted"
        assert service.ingest("same.json", target)["status"] == "duplicate"
        assert {r["domain"] for r in service.query(target)["records"]} == {domain}
        (root / "same.json").unlink()
        root.rmdir()
    reopened = ResearchService(service.path, policy_path)
    assert reopened.query(scope)["total_record_revisions"] == 2
    assert reopened.query(service.scope(collection="stocks"))["total_record_revisions"] == 2
    with pytest.raises(ValueError):
        reopened.ingest("same.json", service.scope(user="other"))
    policy["imports"].append(policy["imports"][0])
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValueError, match="Ambiguous"):
        reopened.policy()


@pytest.mark.parametrize("root", ["relative", 5, None])
def test_bad_root_rejected_before_storage(setup, tmp_path, root):
    _, _, _, policy, policy_path = setup
    policy.pop("import_root")
    policy.update(version=2, imports=[dict(user="leo", project="", collection="crypto", root=root)])
    policy_path.write_bytes(canonical(policy))
    destination = tmp_path / "never-created.db"
    with pytest.raises(ValueError):
        ResearchService(destination, policy_path)
    assert not destination.exists()


def test_nonobject_policy_is_reported_as_invalid(tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid receiver policy"):
        ResearchService(tmp_path / "never.db", policy)
    assert not (tmp_path / "never.db").exists()

"""Bundle CLI subcommands through ``cain.cli.main``, sharing the bundle fixture.

Protected behaviour: every ``research bundle`` action reaches ``BundleService`` with the
scope from the command line, succeeds with JSON on stdout, and fails with a one-line
``Cain:`` message (exit 1) rather than a traceback.
"""
import json

import pytest

from cain.cli import main
from test_research_bundle import setup  # noqa: F401  (pytest fixture)


@pytest.fixture
def cli(setup, capsys):  # noqa: F811
    store, scope, bundle, root, policy, _ = setup

    def run(*args, ok=True):
        code = main(["research", "--policy", str(policy), "--db", str(store.service.path),
                     "--user", "test", "--collection", "a", "bundle", *args])
        out, err = capsys.readouterr()
        if ok:
            assert code == 0, err
            return json.loads(out) if out.strip() else None
        assert code == 1 and err.startswith("Cain:") and "Traceback" not in err, err
        return err

    return run, store, scope, bundle, root


def test_import_query_detail_and_lineage(cli, tmp_path):
    run, store, scope, bundle, root = cli
    assert run("import", "one/bundle.json")["status"] == "admitted"
    assert run("import", "one/bundle.json")["status"] == "duplicate"
    bid = bundle["bundle_id"]
    assert run("query")["total"] == 1
    assert run("query", "--entity-type", "hypothesis", "--limit", "5")["total"] == 1
    assert run("artifacts")["total"] == 1
    assert run("lineage")["total"] == 1
    assert run("historian", "--entity-id", "TEST-HYPOTHESIS-001")
    assert run("entity", bid, "TEST-HYPOTHESIS-001", "1")["entities"][0]["entity_id"] == "TEST-HYPOTHESIS-001"
    assert run("artifact", bid, "a1")["artifact"]["artifact_id"] == "a1"
    run("evidence", bid, "e-missing", ok=False)
    destination = tmp_path / "out" / "report.txt"
    destination.parent.mkdir()
    assert run("materialize", bid, "a1", str(destination))["bytes"] == 15
    assert destination.read_bytes() == b"real test bytes"
    run("materialize", bid, "a1", str(destination), ok=False)


def test_verify_rebuild_receipts_orphans_and_diagnostics(cli):
    run, *_ = cli
    run("import", "one/bundle.json")
    assert run("verify")["bundles"] == 1
    assert run("rebuild")["rebuilt"] is True
    assert run("receipts")[-1]["status"] in {"admitted", "duplicate"}
    assert "orphans" in json.dumps(run("orphans"))
    created = run("diagnose")
    assert created and run("diagnostics")


def test_approve_is_explicit_and_scope_is_taken_from_the_command_line(cli):
    run, store, scope, bundle, root = cli
    assert run("approve", "one/bundle.json")
    assert main(["research", "--policy", "/nonexistent/policy.json", "--db", str(store.service.path),
                 "--user", "test", "--collection", "a", "bundle", "query"]) == 1

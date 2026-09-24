"""Research CLI (L0 commands) through ``cain.cli.main``.

Protected behaviour: every documented L0 subcommand dispatches to the same service the
API uses, prints JSON on success with exit code 0, and reports failures as a one-line
``Cain:`` message with exit code 1, never a traceback. Generative commands only run
with an explicit ``--config``; the fake provider yields a visible ``generation_failed``.
"""
import json

import pytest

from cain.cli import main
import test_research_l0 as cases

setup = cases.setup


@pytest.fixture
def cli(setup, tmp_path, capsys):
    service, scope, ingest, _, policy = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))
    config = tmp_path / "fake.toml"
    config.write_text('[llm]\nprovider="fake"\n[search]\npaths=[]\nallow_public_urls=false\n'
                      '[orchestration]\nllm_routing=false\n', encoding="utf-8")

    def run(*args, ok=True):
        code = main(["research", "--policy", str(policy), "--db", str(service.path), *args])
        out, err = capsys.readouterr()
        if ok is None:  # exit 1 with a JSON body: a visible generation failure, not an error
            assert code == 1 and err == "", err
            return json.loads(out)
        if ok:
            assert code == 0, err
            return json.loads(out)
        assert code == 1 and err.startswith("Cain:") and "Traceback" not in err, err
        return err

    return run, service, scope, config, tmp_path


def test_read_only_commands(cli):
    run, service, scope, _, tmp_path = cli
    assert isinstance(run("coverage"), dict)
    assert run("receipts")[-1]["status"] == "admitted"
    record = run("query", "--source-id", "A")["records"][0]
    reference = record["evidence"][0]["reference_id"]
    assert run("evidence", reference)["publication_id"] == reference.partition(":")[0]
    entries = run("history", "--limit", "5")
    assert entries and entries[0]["id"]
    assert run("recall", entries[0]["id"])["records"][0]["source_id"] == "A"
    assert run("verify")["integrity"] == "verified"
    assert run("rebuild")["rebuilt"] is True
    assert run("inspect", "--source-id", "A")["metrics"]["record_revisions"] == 1
    run("evidence", "missing:ref", ok=False)
    run("recall", "no-such-entry", ok=False)


def test_backup_and_restore_round_trip(cli):
    run, service, scope, _, tmp_path = cli
    backup = tmp_path / "backup" / "research.db"
    assert isinstance(run("backup", str(backup)), dict) and backup.exists()
    restored = tmp_path / "restored.db"
    assert run("restore", str(backup), str(restored))
    assert restored.exists()
    run("restore", str(backup), str(restored), ok=False)  # destination must be new


def test_search_entities_and_explain_with_fake_provider(cli):
    run, *_ , config, _ = cli
    assert run("search", "Alice")["matches"] == 1
    assert "hybrid" in run("search", "Alice", "--semantic", "--config", str(config), ok=False)
    explained = run("explain", "What did Alice review?", "--config", str(config), ok=None)
    assert explained["status"] == "generation_failed" and explained["facts"]["records"]
    assert "loopback Ollama" in run("entities", "Alice?", "--config", str(config), ok=False)


def test_workflow_lifecycle(cli):
    run, *_, config, _ = cli
    job = run("workflow", "A?", "--config", str(config), "--steps", "inspect", "search", "--run-id", "w1")
    assert job["id"] == "w1"
    assert [j["id"] for j in run("jobs")] == ["w1"]
    assert run("job", "w1")["status"] == "ready"
    assert run("advance", "w1", "--config", str(config))["status"] == "ready"
    assert "inspect" in json.dumps(run("trace", "w1"))
    assert run("cancel", "w1", "--config", str(config))["status"] == "cancelled"
    run("workflow", "B?", "--config", str(config), "--steps", "inspect", "entities", "--run-id", "w2")
    run("abstain", "w2", "--config", str(config), "--reason", "too early", ok=False)
    assert run("advance", "w2", "--config", str(config))["status"] == "ready"
    assert "loopback Ollama" in run("advance", "w2", "--config", str(config), "--approve-generation", ok=False)
    assert run("job", "w2")["status"] == "failed"
    abstained = run("abstain", "w2", "--config", str(config), "--reason", "no evidence")
    assert abstained["status"] == "completed" and abstained["steps"][-1]["result"]["accepted_model_output"] is False
    assert run("advance", "w1", "--config", str(config))["status"] == "cancelled"  # no step runs after cancel
    run("job", "unknown", ok=False)

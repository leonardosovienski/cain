"""Findings archive: quarantine, closed hypotheses stop the loop, procedure demotion, domain isolation."""

from hashlib import sha256
import json
import subprocess

import pytest

from cain.findings.archive import FindingsArchive
from cain.findings.ingest import ingest_loop, ingest_scientific_state, ingest_trial_registry, read_source
from cain.loop.engine import ResearchLoop, decide_gate
from cain.loop.ledger import LoopLedger
from cain.loop.proposers import NeighborProposer
from cain.memory.store import MemoryStore, MemoryStoreError
from test_research_loop import write_world

H = "a" * 64


def source(tag="x"):
    return {"repo": "fixture", "commit": "0" * 40, "path": f"{tag}.json", "sha256": sha256(tag.encode()).hexdigest()}


@pytest.fixture
def archive(tmp_path):
    return FindingsArchive(MemoryStore(tmp_path / "memory.db"))


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"})


def repo_with(tmp_path, rows):
    repo = tmp_path / "predictor"
    (repo / "data").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "data" / "trials.v2.json").write_text(json.dumps(rows), encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "trials")
    return repo


def test_declared_finding_is_quarantined_by_default(archive):
    archive.record("brasileirao", "br:h1", kind="negative", verdict="REFUTED", statement="h1 over/under edge",
                   source=source("a"))
    proven = archive.record("brasileirao", "br:h2", kind="positive", verdict="SUPPORTED", statement="h2 elo beats climatology",
                            source=source("b"), evaluation_report={"path": "reports/h2.json", "sha256": H},
                            governance_transition={"source": "charter@abc", "sha256": H, "to": "GO", "by": "leo"})
    assert proven["finding_status"] == "PROVEN"
    now = archive.memory.now()
    assert [f["finding_id"] for f in archive.findings("brasileirao", as_of=now)] == ["br:h2"]
    everything = archive.findings("brasileirao", as_of=now, include_quarantine=True)
    labels = {f["finding_id"]: (f["status"], f["quarantine"]) for f in everything}
    assert labels == {"br:h1": ("DECLARED", True), "br:h2": ("PROVEN", False)}
    assert everything[0]["quarantine_reason"] == "missing evaluation report and governance transition"


def test_proven_needs_both_the_report_and_the_governance_transition(archive):
    only_report = archive.record("stocks", "st:h1", kind="positive", verdict="SUPPORTED", statement="momentum",
                                 source=source(), evaluation_report={"path": "r.json", "sha256": H})
    assert only_report["finding_status"] == "DECLARED"
    found = archive.findings("stocks", as_of=archive.memory.now(), include_quarantine=True)[0]
    assert found["quarantine_reason"] == "missing governance transition"
    with pytest.raises(MemoryStoreError):
        archive.record("stocks", "st:h2", kind="positive", verdict="X", statement="s", source={"path": "no hash"})


def test_registry_ingestion_is_deterministic_and_supersedes_on_status_change(tmp_path, archive):
    rows = [{"trial_id": "h1-edge", "registered_at": "2026-07-11T00:55:18Z", "status": "pre-registrada",
             "params": {"market": "ou25"}, "result": {}, "notes": "H1: over/under edge", "dataset_hash": "UNKNOWN"}]
    repo = repo_with(tmp_path, rows)
    raw, src = read_source(repo, "HEAD", "data/trials.v2.json")
    assert src["sha256"] == sha256(raw).hexdigest() and len(src["commit"]) == 40
    first = ingest_trial_registry(archive, "brasileirao", raw, src)
    assert first["counts"] == {"recorded:informative": 1}
    assert ingest_trial_registry(archive, "brasileirao", raw, src)["counts"] == {"unchanged:informative": 1}
    before = archive.memory.now()
    rows[0]["status"] = "refutada"
    (repo / "data" / "trials.v2.json").write_text(json.dumps(rows), encoding="utf-8")
    git(repo, "commit", "-q", "-am", "refuted")
    raw2, src2 = read_source(repo, "HEAD", "data/trials.v2.json")
    assert ingest_trial_registry(archive, "brasileirao", raw2, src2)["counts"] == {"superseded:negative": 1}
    old = archive.findings("brasileirao", as_of=before, include_quarantine=True)[0]
    new = archive.findings("brasileirao", as_of=archive.memory.now(), include_quarantine=True)[0]
    assert (old["verdict"], new["verdict"]) == ("PREREGISTERED", "REFUTED")
    assert new["identity"]["trial_id"] == "h1-edge" and new["details"]["registered_at"] == "2026-07-11T00:55:18Z"
    assert new["source"]["commit"] == src2["commit"] != src["commit"]


def test_loop_flags_a_hypothesis_equivalent_to_a_closed_one_before_running(tmp_path, archive):
    world, _ = write_world(tmp_path, stages='["sanity", "in_sample", "walk_forward"]')
    archive.record("fixture", "fixture:trial:old-window", kind="negative", verdict="REFUTED",
                   statement="a smoother window and moderate l2 lower the loss", source=source())
    calls = []

    def counting(*args, **kwargs):
        calls.append(args[1])
        raise AssertionError("the evaluator must not run")

    def closed_check(statement, identity):
        return archive.equivalent_closed("fixture", statement, as_of=archive.memory.now(), identity=identity)

    ledger = LoopLedger(tmp_path / "ledger.db")
    status = ResearchLoop(world, ledger, NeighborProposer(), runner=counting, closed_check=closed_check).run(
        loop_id="loop:closed")
    assert status["stopped"]["reason"] == "equivalent_to_closed" and calls == [] and status["attempts"] == 0
    assert status["stopped"]["matches"][0]["finding_id"] == "fixture:trial:old-window"
    assert status["stopped"]["matches"][0]["quarantine"] is True  # quarantined, still blocks the retest
    assert status["gates"][0]["gate"] == "closed_hypothesis"
    # Same identity (a frozen family) matches even with different wording.
    archive.record("crypto", "crypto:hypothesis:H1", kind="negative", verdict="NO_GO", statement="H1 v3-hmm",
                   source=source("s"), identity={"hypothesis_id": "H1", "frozen_families": ["funding_oi_hmm_v3"]})
    matches = archive.equivalent_closed("crypto", "a brand new regime idea", as_of=archive.memory.now(),
                                        identity={"hypothesis_family": None, "frozen_families": "funding_oi_hmm_v3"})
    assert matches and matches[0]["same_identity"] == ["frozen_families"]


def test_a_procedure_demoted_at_the_source_is_demoted_in_the_library(archive):
    spec = dict(code_sha256=H, data_sha256=H, metrics={"rps": 0.2093},
                tests={"report": "junit.xml", "sha256": H, "passed": 40, "failed": 0},
                walk_forward={"ref": "result-2022.json", "sha256": H, "passed": True}, source=source(),
                source_trial="serving-baseline")
    with pytest.raises(MemoryStoreError, match="passing test report"):
        archive.record_procedure("brasileirao", "elo-serving", **{**spec, "tests": {**spec["tests"], "failed": 1}})
    with pytest.raises(MemoryStoreError, match="walk-forward"):
        archive.record_procedure("brasileirao", "elo-serving", **{**spec, "walk_forward": {"sha256": H}})
    archive.record_procedure("brasileirao", "elo-serving", **spec)
    now = archive.memory.now()
    assert [p["state"] for p in archive.procedures("brasileirao", as_of=now)] == ["ACTIVE"]
    rows = [{"trial_id": "serving-baseline", "status": "comprovada"}]
    assert archive.sync_demotions("brasileirao", rows, source=source("r1")) == []
    rows[0]["status"] = "substituida"
    changes = archive.sync_demotions("brasileirao", rows, source=source("r2"))
    assert len(changes) == 1 and changes[0]["status"] == "superseded"
    later = archive.memory.now()
    assert archive.procedures("brasileirao", as_of=later) == []
    demoted = archive.procedures("brasileirao", as_of=later, include_demoted=True)[0]
    assert demoted["state"] == "DEMOTED" and "substituida" in demoted["demotion"]["reason"]
    assert [p["state"] for p in archive.procedures("brasileirao", as_of=now)] == ["ACTIVE"]  # as_of before


def test_a_finding_crosses_domains_only_through_a_preregistered_hypothesis(archive):
    archive.record("brasileirao", "br:home-advantage", kind="positive", verdict="SUPPORTED",
                   statement="home advantage in Elo", source=source())
    now = archive.memory.now()
    assert archive.apply("br:home-advantage", source_domain="brasileirao", target_domain="brasileirao",
                         as_of=now)["via"] == "same domain"
    with pytest.raises(MemoryStoreError, match="pre-registered"):
        archive.apply("br:home-advantage", source_domain="brasileirao", target_domain="crypto", as_of=now)
    archive.preregister("crypto", "CR-H10", statement="an exchange 'home' effect", derived_from="br:elsewhere",
                        by="leo", source_hash=H)
    with pytest.raises(MemoryStoreError, match="not a crypto pre-registration derived from"):
        archive.apply("br:home-advantage", source_domain="brasileirao", target_domain="crypto",
                      as_of=archive.memory.now(), preregistration="CR-H10")
    archive.preregister("crypto", "CR-H11", statement="an exchange 'home' effect", derived_from="br:home-advantage",
                        by="leo", source_hash=H)
    allowed = archive.apply("br:home-advantage", source_domain="brasileirao", target_domain="crypto",
                            as_of=archive.memory.now(), preregistration="CR-H11")
    assert allowed["allowed"] and allowed["via"]["hypothesis_id"] == "CR-H11"


def test_scientific_state_and_loop_outcomes_are_ingested(tmp_path, archive):
    state = {"hypotheses": {"H1": "CLOSED_NO_GO", "H7": "REGISTERED_NOT_ACTIVATED"},
             "hypothesis_trials": {"H1": "v3-hmm", "H7": "h7-macro"}, "frozen_families": ["funding_oi_hmm_v3"],
             "as_of_commit": "abc"}
    raw = json.dumps(state).encode()
    out = ingest_scientific_state(archive, "crypto", raw, {**source(), "sha256": sha256(raw).hexdigest()},
                                  [{"name": "v3-hmm", "params": {"k": 3}, "notes": "regime model"}])
    assert out["counts"] == {"recorded:negative": 1, "recorded:informative": 1}
    closed = archive.closed("crypto", as_of=archive.memory.now())
    assert closed[0]["identity"]["trial_id"] == "v3-hmm" and closed[0]["verdict"] == "NO_GO"
    world, _ = write_world(tmp_path, attempts=10)
    ledger = LoopLedger(tmp_path / "ledger.db")
    ResearchLoop(world, ledger, NeighborProposer()).run(loop_id="loop:gate")
    pending = ingest_loop(archive, "fixture", ledger, "loop:gate")
    assert pending["finding_status"] == "DECLARED"  # candidate at a human gate, not decided yet
    decide_gate(ledger, "loop:gate", decision="REJECT", by="leo", note="not worth the holdout")
    decided = ingest_loop(archive, "fixture", ledger, "loop:gate")
    assert decided["finding_status"] == "PROVEN" and decided["status"] == "superseded"


def test_cli_ingest_list_and_check(tmp_path, capsys):
    from cain.cli import main

    rows = [{"trial_id": "h1-edge", "registered_at": "2026-07-11T00:55:18Z", "status": "refutada",
             "notes": "over/under edge with min_edge 0.02", "params": {"market": "ou25"}}]
    repo = repo_with(tmp_path, rows)
    db = str(tmp_path / "cli-memory.db")
    base = ["findings", "--db", db]
    assert main([*base, "ingest-registry", "--domain", "brasileirao", "--repo", str(repo), "--commit", "HEAD",
                 "--path", "data/trials.v2.json"]) == 0
    assert json.loads(capsys.readouterr().out)["counts"] == {"recorded:negative": 1}
    assert main([*base, "list", "--domain", "brasileirao", "--as-of", "now"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 0  # quarantine by default
    assert main([*base, "list", "--domain", "brasileirao", "--as-of", "now", "--include-quarantine"]) == 0
    assert json.loads(capsys.readouterr().out)["findings"][0]["quarantine"] is True
    assert main([*base, "check", "--domain", "brasileirao", "--statement", "whatever", "--as-of", "now",
                 "--trial-id", "h1-edge"]) == 0
    assert json.loads(capsys.readouterr().out)["equivalent_to_closed"] is True

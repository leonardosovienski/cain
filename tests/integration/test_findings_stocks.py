"""Stocks findings: the stocks scientific state and evaluation ledger index, read deterministically.

The stocks states (CLOSED_JUDGED, CLOSED_REJECTED, ...) are not the crypto vocabulary. Before the versioned
state vocabulary they all entered as informative, so ``closed()`` returned nothing and a retest of a closed
stocks hypothesis was not blocked (measured on the real stocks state: 22 hypotheses, 0 closed).
"""

from hashlib import sha256
import json

import pytest

from cain.findings.archive import FindingsArchive
from cain.findings.ingest import ingest_ledger_index, ingest_scientific_state, state_vocabulary
from cain.memory.store import MemoryStore
from test_findings import git

REOPEN = "Nenhuma família de fatores já encerrada pode ser reaberta sem registrar previous_result, closure_reason, ..."
STATE = {
    "schema": "stocks-scientific-state/1", "domain": "stocks",
    "hypotheses": {"H11": "CLOSED_JUDGED", "H17": "PAUSED_INCONCLUSIVE_DATA_QUALITY",
                   "H21": "CLOSED_HISTORICAL_CONDITIONAL", "H22": "CLOSED_REJECTED"},
    "hypothesis_trials": {"H11": "h11-momentum-12-1-total-return"},
    "frozen_families": ["momentum_12_1_total_return"],
    "reassessment": {"H11": {"status_after": "NOT_SUPPORTED mantido", "report": "reports/h11_verdict_adhoc.md"}},
    "reopen_policy": {"source": "RESEARCH_FREEZE.md#ST_RESEARCH_FREEZE.reopen_policy", "text": REOPEN},
}


def hashed(value, tag="state"):
    raw = json.dumps(value).encode()
    return raw, {"repo": "stocks-predictor", "commit": "0" * 40, "path": f"{tag}.json",
                 "sha256": sha256(raw).hexdigest()}


@pytest.fixture
def archive(tmp_path):
    return FindingsArchive(MemoryStore(tmp_path / "memory.db"))


def test_closed_stocks_hypotheses_block_a_retest_and_keep_their_literal_state(archive):
    out = ingest_scientific_state(archive, "stocks", *hashed(STATE))
    assert out["counts"] == {"recorded:negative": 4, "recorded:informative": 2}  # 3 closed + family; H17 + reopen
    assert out["vocabulary"]["policy"] == "findings-state-vocabulary" and out["vocabulary"]["version"] == 1
    now = archive.memory.now()
    closed = {f["finding_id"]: f for f in archive.closed("stocks", as_of=now)}
    assert set(closed) == {"stocks:hypothesis:H11", "stocks:hypothesis:H21", "stocks:hypothesis:H22",
                           "stocks:frozen-family:momentum_12_1_total_return"}
    h11 = closed["stocks:hypothesis:H11"]
    assert h11["verdict"] == "CLOSED_JUDGED" and h11["quarantine"] is True  # literal state, still DECLARED
    assert h11["details"]["reassessment"]["status_after"] == "NOT_SUPPORTED mantido"
    assert h11["details"]["vocabulary"]["sha256"] == state_vocabulary()["sha256"]
    retest = archive.equivalent_closed("stocks", "momentum again, other name", as_of=now,
                                       identity={"hypothesis_id": "H11"})
    assert [m["finding_id"] for m in retest] == ["stocks:hypothesis:H11"]
    family = archive.equivalent_closed("stocks", "unrelated wording", as_of=now,
                                       identity={"hypothesis_family": "momentum_12_1_total_return"})
    assert [m["finding_id"] for m in family] == ["stocks:frozen-family:momentum_12_1_total_return"]
    # H17 is paused, not a negative result: it does not block by itself
    assert archive.equivalent_closed("stocks", "zzz", as_of=now, identity={"hypothesis_id": "H17"}) == []
    reopen = archive.findings("stocks", as_of=now, include_quarantine=True, kind="informative")
    assert any(f["finding_id"] == "stocks:reopen-policy" and "previous_result" in f["statement"] for f in reopen)


@pytest.mark.parametrize("change, message", [
    ({"hypotheses": {"H11": "CLOSED_JUDGED", "H23": "SOMETHING_NEW"}}, "without a declared reading"),
    ({"schema": "stocks-scientific-state/9"}, "unknown schema"),
    ({"domain": "crypto"}, "cannot be ingested as"),
])
def test_an_unreadable_state_is_refused_before_anything_is_recorded(archive, change, message):
    with pytest.raises(ValueError, match=message):
        ingest_scientific_state(archive, "stocks", *hashed(STATE | change))
    assert archive.findings("stocks", as_of=archive.memory.now(), include_quarantine=True) == []


def test_a_stocks_state_never_enters_another_domain(archive):
    with pytest.raises(ValueError, match="cannot be ingested as 'crypto'"):
        ingest_scientific_state(archive, "crypto", *hashed(STATE))
    with pytest.raises(ValueError, match="no state vocabulary for domain 'brasileirao'"):
        ingest_scientific_state(archive, "brasileirao", *hashed({"hypotheses": {"H1": "CLOSED_JUDGED"}}))
    assert archive.findings(["crypto", "brasileirao"], as_of=archive.memory.now(), include_quarantine=True) == []


def chain(rows):
    """Index rows with a valid hash chain (the real index carries the ledger's hashes)."""
    previous, out = None, []
    for seq, row in enumerate(rows, 1):
        digest = sha256(f"{seq}:{json.dumps(row, sort_keys=True)}".encode()).hexdigest()
        out.append({"seq": seq, "prev": previous, "hash": digest, "recorded_at": f"2026-09-24T18:00:{seq:02d}Z",
                    "run_id": row.get("run_id", f"x:{seq}"), **row})
        previous = digest
    counts: dict[str, int] = {}
    for row in out:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    return {"schema": "stocks-trial-ledger-index/1", "records": len(out), "head": previous, "counts": counts,
            "trials_started": counts.get("STARTED", 0), "rows": out}


def started(run_id, n, model):
    return {"kind": "STARTED", "run_id": run_id, "trial_number": n, "model": model, "family": "forecast-prompt3c",
            "git": {"commit": "b" * 40, "dirty": False}, "dataset_hash": "d" * 64,
            "interval": {"start": "2026-04-07", "end": "2026-09-09", "rebalance": "monthly"},
            "decision_policy_sha256": "4" * 64, "preregistration": None, "holdout_access": None}


INDEX = chain([
    started("r1", 1, "gaussian_random_walk"), {"kind": "COMPLETED", "run_id": "r1", "result_digest": "e" * 64},
    started("r2", 2, "ew_universe"),
    {"kind": "DECISION", "run_id": "r1", "decision": "NO_DECISION", "decision_if_approved": None,
     "policy_sha256": "4" * 64, "evaluated_run_ids": ["r1"]},
    {"kind": "REASSESSMENT", "run_id": "reassess:H1", "hypothesis": "H1", "status_after": "NOT_SUPPORTED mantido"},
    {"kind": "PREREGISTERED", "run_id": "prereg:stocks:NEW-001", "hypothesis_id": "stocks:NEW-001",
     "record_sha256": "f" * 64},
    {"kind": "HOLDOUT_SEALED", "run_id": "holdout:h", "holdout_id": "h", "interval": ["2026-09-10", "2027-09-10"],
     "seal_sha256": "c" * 64},
    {"kind": "HOLDOUT_OPENED", "run_id": "holdout:h", "holdout_id": "h", "interval": None, "seal_sha256": None},
])


def test_ledger_index_records_runs_decisions_and_holdouts_once(archive):
    out = ingest_ledger_index(archive, "stocks", *hashed(INDEX, "index"))
    assert out["counts"] == {"recorded:STARTED": 2, "recorded:DECISION": 1, "recorded:REASSESSMENT": 1,
                             "recorded:PREREGISTERED": 1, "recorded:HOLDOUT_OPENED": 1, "recorded:LEDGER_INDEX": 1}
    found = {f["finding_id"]: f for f in archive.findings("stocks", as_of=archive.memory.now(),
                                                            include_quarantine=True)}
    assert found["stocks:run:r1"]["verdict"] == "COMPLETED" and found["stocks:run:r1"]["details"]["result_digest"]
    assert found["stocks:run:r2"]["verdict"] == "OPEN"  # no outcome in the index yet
    assert found["stocks:decision:4"]["verdict"] == "NO_DECISION"
    holdout = found["stocks:holdout:h"]
    assert holdout["verdict"] == "HOLDOUT_OPENED" and holdout["details"]["interval"] == ["2026-09-10", "2027-09-10"]
    assert found["stocks:ledger-index"]["details"]["head"] == INDEX["head"]
    assert all(f["kind"] == "informative" and f["quarantine"] for f in found.values())
    again = ingest_ledger_index(archive, "stocks", *hashed(INDEX, "index"))  # re-ingestion changes nothing
    assert again["counts"] == {k.replace("recorded:", "unchanged:"): v for k, v in out["counts"].items()}


@pytest.mark.parametrize("damage", ["prev", "seq", "head", "counts"])
def test_a_broken_ledger_index_is_refused_before_anything_is_recorded(archive, damage):
    index = json.loads(json.dumps(INDEX))
    if damage == "prev":
        index["rows"][3]["prev"] = "0" * 64
    elif damage == "seq":
        index["rows"][2]["seq"] = 9
    elif damage == "head":
        index["head"] = "0" * 64
    else:
        index["counts"]["STARTED"] = 3
    with pytest.raises(ValueError, match="nothing was recorded"):
        ingest_ledger_index(archive, "stocks", *hashed(index, "index"))
    assert archive.findings("stocks", as_of=archive.memory.now(), include_quarantine=True) == []
    with pytest.raises(ValueError, match="cannot be ingested as 'crypto'"):
        ingest_ledger_index(archive, "crypto", *hashed(INDEX, "index"))


def test_cli_reads_the_stocks_files_at_a_pinned_commit_and_blocks_the_retest(tmp_path, capsys):
    from cain.cli import main

    repo = tmp_path / "stocks-predictor"
    (repo / "research").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "research" / "scientific_state.json").write_text(json.dumps(STATE), encoding="utf-8")
    (repo / "research" / "index.json").write_text(json.dumps(INDEX), encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "state")
    base = ["findings", "--db", str(tmp_path / "cli.db")]
    pinned = ["--repo", str(repo), "--commit", "HEAD"]
    assert main([*base, "ingest-state", "--domain", "stocks", *pinned, "--path", "research/scientific_state.json"]) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["recorded:negative"] == 4
    assert main([*base, "ingest-ledger-index", "--domain", "stocks", *pinned, "--path", "research/index.json"]) == 0
    assert json.loads(capsys.readouterr().out)["records"] == len(INDEX["rows"])
    assert main([*base, "check", "--domain", "stocks", "--statement", "momentum 12-1 again", "--as-of", "now",
                 "--hypothesis-id", "H11"]) == 0
    assert json.loads(capsys.readouterr().out)["equivalent_to_closed"] is True

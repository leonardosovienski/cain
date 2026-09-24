"""DecisionLog entries are hash-chained, so tampering with the file is detectable.

Protected behaviour: every appended decision stores the hash of its predecessor and its
own hash over (previous, decision_id, run_id, record_json). ``verify_chain`` recomputes
the chain from the genesis constant and reports the first broken sequence. Rows written
before this scheme (no hash columns) are folded into the chain deterministically, so an
old database keeps working and later edits to those rows are detected too. Triggers
already stop the application from editing; the chain covers whoever edits the file.
"""
import sqlite3

import pytest

from cain.common import DecisionRecord
from cain.persistence.adapters import SQLiteDecisionLog


def record(n, run="run1", status="completed"):
    return DecisionRecord(f"d{n}", run, "alice", "s1", "resumo", "resumo", "rule", status, ("8",))


def raw(path):
    """A connection that can tamper: it drops the append-only triggers first."""
    db = sqlite3.connect(path)
    for name in ("decisions_no_update", "decisions_no_delete", "decisions_no_replace"):
        db.execute(f"DROP TRIGGER IF EXISTS {name}")
    db.commit()
    return db


def test_chain_is_intact_after_appends_and_reopen(tmp_path):
    path = tmp_path / "d.db"
    log = SQLiteDecisionLog(path)
    for n in range(1, 6):
        log.append(record(n))
    report = log.verify_chain()
    assert report == {"entries": 5, "hashed_entries": 5, "status": "intact", "broken_at": None,
                      "head": report["head"]}
    assert len(report["head"]) == 64
    log.close()
    reopened = SQLiteDecisionLog(path)
    assert reopened.verify_chain()["head"] == report["head"]
    assert [r.decision_id for r in reopened.export("run1")] == ["d1", "d2", "d3", "d4", "d5"]
    reopened.close()


@pytest.mark.parametrize("tamper", [
    "UPDATE decisions SET record_json = replace(record_json, 'completed', 'failed') WHERE decision_id = 'd3'",
    "UPDATE decisions SET run_id = 'other' WHERE decision_id = 'd3'",
    "DELETE FROM decisions WHERE decision_id = 'd3'",
    "UPDATE decisions SET entry_hash = previous_hash WHERE decision_id = 'd3'",
], ids=["edit-record", "edit-run", "delete-middle", "forge-hash"])
def test_file_level_tampering_breaks_the_chain_at_the_first_altered_entry(tmp_path, tamper):
    path = tmp_path / "d.db"
    log = SQLiteDecisionLog(path)
    for n in range(1, 6):
        log.append(record(n))
    log.close()
    with raw(path) as db:
        db.execute(tamper)
    report = SQLiteDecisionLog(path).verify_chain()
    assert report["status"] == "broken"
    assert report["broken_at"] in (3, 4)  # the edited row, or its successor after a deletion


def test_inserting_a_forged_row_in_the_middle_is_detected(tmp_path):
    path = tmp_path / "d.db"
    log = SQLiteDecisionLog(path)
    for n in range(1, 4):
        log.append(record(n))
    log.close()
    with raw(path) as db:
        db.execute("UPDATE decisions SET sequence = sequence + 10 WHERE sequence >= 3")
        db.execute("INSERT INTO decisions(sequence, decision_id, run_id, record_json, previous_hash, entry_hash) "
                   "VALUES (3, 'forged', 'run1', '{}', 'x', 'y')")
    report = SQLiteDecisionLog(path).verify_chain()
    assert report["status"] == "broken" and report["broken_at"] == 3


def test_legacy_rows_without_hashes_are_folded_in_and_still_protected(tmp_path):
    path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(path)
    legacy.executescript("""
        CREATE TABLE decisions (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT UNIQUE NOT NULL, run_id TEXT NOT NULL, record_json TEXT NOT NULL);
        INSERT INTO decisions(decision_id, run_id, record_json) VALUES ('old1', 'r', '{"a":1}');
        INSERT INTO decisions(decision_id, run_id, record_json) VALUES ('old2', 'r', '{"a":2}');
    """)
    legacy.close()
    log = SQLiteDecisionLog(path)  # migration adds the columns; old rows keep NULL hashes
    before = log.verify_chain()
    assert before == {"entries": 2, "hashed_entries": 0, "status": "intact", "broken_at": None, "head": before["head"]}
    log.append(record(1))
    after = log.verify_chain()
    assert after["entries"] == 3 and after["hashed_entries"] == 1 and after["status"] == "intact"
    log.close()
    with raw(path) as db:
        db.execute("UPDATE decisions SET record_json = '{\"a\":9}' WHERE decision_id = 'old1'")
    report = SQLiteDecisionLog(path).verify_chain()
    assert report["status"] == "broken" and report["broken_at"] == 3, "the first hashed row no longer matches the legacy tail"


def test_append_with_outcome_is_chained_too(tmp_path):
    from cain.workspace import WorkspaceStore
    path = tmp_path / "w.db"
    workspace = WorkspaceStore(path)
    request = {"user_id": "alice", "session_id": "s1", "run_id": "run1", "payload": "x",
               "project_id": None, "intent": None, "preference_scope": "user"}
    workspace.claim_run(request)
    log = SQLiteDecisionLog(path)
    log.append(record(1))
    log.append_with_outcome(record(2), {"response": "ok"})
    report = log.verify_chain()
    assert report == {"entries": 2, "hashed_entries": 2, "status": "intact", "broken_at": None, "head": report["head"]}
    log.close()

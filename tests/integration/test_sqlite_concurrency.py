"""SQLite write contention, sequenced with locks instead of timing.

Protected behaviour:
- a writer holding ``BEGIN IMMEDIATE`` never blocks pure readers of the research store
  (receipts, evidence, verify), while ``query`` (which records itself) fails rather than
  answering unaudited;
- a second writer that cannot obtain the lock within its timeout fails closed and
  reports that no durable failure receipt could be written (it must not pretend the
  import happened, and must not corrupt the store);
- once the first writer releases the lock, the same import succeeds exactly once;
- the workspace's run claim behaves the same way under a held lock.

Every test holds the lock for the whole duration of the contended call, so the
outcome does not depend on scheduling or sleep durations. Timeouts are shortened
through subclasses that override only the connection factory.
"""
import sqlite3
from contextlib import contextmanager
from threading import Event, Thread

import pytest
from research_snapshot import canonical

from cain.research import ResearchService
from cain.workspace import WorkspaceStore
import test_research_l0 as cases

setup = cases.setup


class ImpatientResearch(ResearchService):
    """Same store, 50 ms lock wait: contention surfaces immediately and deterministically."""

    def connection(self):
        db = sqlite3.connect(self.path, timeout=0.05)
        db.row_factory = sqlite3.Row
        return db


class ImpatientWorkspace(WorkspaceStore):
    def connection(self):
        db = sqlite3.connect(self.path, timeout=0.05)
        db.row_factory = sqlite3.Row
        return db


@contextmanager
def write_lock_held(path):
    """Hold BEGIN IMMEDIATE on ``path`` from another thread until the block exits."""
    held, release, done = Event(), Event(), Event()

    def hold():
        db = sqlite3.connect(path)
        try:
            db.execute("BEGIN IMMEDIATE")
            held.set()
            release.wait()
            db.rollback()
        finally:
            db.close()
            done.set()

    Thread(target=hold, daemon=True).start()
    assert held.wait(5), "lock holder did not start"
    try:
        yield
    finally:
        release.set()
        assert done.wait(5), "lock holder did not finish"


@pytest.fixture
def contended(setup):
    service, scope, ingest, policy, policy_path = setup
    ingest(cases.publication(("A",)))
    impatient = ImpatientResearch(service.path, policy_path)
    package = cases.publication(("B",), text="Second publication.")
    name = package["publication_id"] + ".json"
    (cases.Path(policy["import_root"]) / name).write_bytes(canonical(package))
    return service, impatient, scope, name


def test_held_write_lock_does_not_block_pure_readers(contended):
    service, _, scope, _ = contended
    reference = service.query(scope, source_id="A")["records"][0]["evidence"][0]["reference_id"]
    with write_lock_held(service.path):
        assert service.receipts(scope)[-1]["status"] == "admitted"
        assert service.evidence(scope, reference)["publication_id"] == reference.partition(":")[0]
        assert service.verify(scope)["integrity"] == "verified"


def test_query_is_audited_or_not_answered_under_contention(contended):
    """query() records every consultation, so it needs the write lock: with the lock
    held it fails instead of returning an unaudited answer."""
    service, impatient, scope, _ = contended
    logged_before = len(service.history(scope, None, 50, 0))
    with write_lock_held(service.path):
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            impatient.query(scope, source_id="A")
    assert len(service.history(scope, None, 50, 0)) == logged_before
    assert impatient.query(scope, source_id="A")["total_record_revisions"] == 1
    assert len(service.history(scope, None, 50, 0)) == logged_before + 1


def test_second_writer_fails_closed_without_a_durable_receipt(contended):
    service, impatient, scope, name = contended
    before = service.receipts(scope)
    with write_lock_held(service.path):
        with pytest.raises(RuntimeError, match="NO DURABLE FAILURE RECEIPT: OperationalError"):
            impatient.ingest(name, scope)
    assert service.receipts(scope) == before, "a failed, unreceipted import leaves no trace"
    assert service.query(scope, source_id="B")["records"] == []
    assert service.verify(scope)["integrity"] == "verified"


def test_import_succeeds_once_the_lock_is_released(contended):
    service, impatient, scope, name = contended
    with write_lock_held(service.path):
        with pytest.raises(RuntimeError):
            impatient.ingest(name, scope)
    result = impatient.ingest(name, scope)
    assert result["status"] == "admitted"
    assert service.query(scope, source_id="B")["total_record_revisions"] == 1
    assert [r["status"] for r in service.receipts(scope)][-1:] == ["admitted"]
    assert service.verify(scope)["integrity"] == "verified"


def test_workspace_run_claim_under_held_lock_fails_without_partial_receipt(tmp_path):
    path = tmp_path / "workspace.db"
    workspace = WorkspaceStore(path)
    impatient = ImpatientWorkspace(path)
    request = {"user_id": "leo", "session_id": "s", "run_id": "r1", "payload": "hello",
               "project_id": None, "intent": None, "preference_scope": "user"}
    with write_lock_held(path):
        with pytest.raises(sqlite3.OperationalError):
            impatient.claim_run(request)
    with pytest.raises(ValueError, match="não encontrado"):
        workspace.run_receipt("leo", "r1")  # nothing was claimed while the lock was held
    assert workspace.claim_run(request) is None  # first successful claim creates the receipt
    assert workspace.claim_run(request)["status"] == "processing"  # replay returns it

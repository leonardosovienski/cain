from dataclasses import asdict
import sqlite3

import pytest

from cain.common import DecisionRecord, IdentityState, Signal
from cain.persistence.adapters import LexicalMemoryIndex, SQLiteDecisionLog, SQLiteIdentityStore


def test_drop_rebuild_preserves_fixed_queries_and_filters_after_sqlite_reopen(tmp_path):
    path = tmp_path / "identity.db"
    store = SQLiteIdentityStore(path)
    index = LexicalMemoryIndex()
    expected = {}
    for user, docs in {
        "alice": [("a1", "Python usa SQLite para persistência"), ("a2", "Prefiro resumos curtos")],
        "bob": [("b1", "Python no projeto confidencial Bob"), ("b2", "Memória e persistência")],
    }.items():
        store.upsert(user, IdentityState(user))
        for doc_id, text in docs:
            signal = Signal(text, metadata={"session_id": "s1"}, signal_id=doc_id)
            store.append_signal(user, signal)
            index.index(doc_id, text, {"user_id": user, "session_id": "s1", "kind": "interaction"})
    fixed = [("Python", 10, None), ("persistência", 3, {"user_id": "alice"}),
             ("resumos", 2, {"user_id": "bob"}), ("memória", 2, {"user_id": "bob"})]
    for i, query in enumerate(fixed):
        expected[i] = index.query(*query)
    store.close()
    reopened = SQLiteIdentityStore(path)
    try:
        assert reopened.get("alice").user_id == "alice"
        assert len(list(reopened.iter_documents())) == 4
        index.drop()
        assert index.query("Python", 10) == []
        index.rebuild_from(reopened)
        for i, query in enumerate(fixed):
            assert index.query(*query) == expected[i]
    finally:
        reopened.close()


def test_identity_snapshots_and_documents_are_detached_from_callers(tmp_path):
    store = SQLiteIdentityStore(tmp_path / "identity.db")
    try:
        state = IdentityState("alice")
        state.user_model.preferences["format"] = "short"
        store.upsert("alice", state)
        state.user_model.preferences["format"] = "long"
        state.revision = 1
        store.upsert("alice", state)
        history = store.history("alice", 10)
        assert [item.state.user_model.preferences["format"] for item in history] == ["long", "short"]
        loaded = store.get("alice")
        loaded.user_model.preferences["format"] = "corrupted"
        assert store.get("alice").user_model.preferences["format"] == "long"
        with pytest.raises(ValueError):
            store.upsert("bob", state)
        with pytest.raises(ValueError):
            store.append_signal("alice", Signal("text", metadata={"user_id": "bob"}))
    finally:
        store.close()


def test_decision_log_is_append_only_and_reopens(tmp_path):
    path = tmp_path / "decisions.db"
    log = SQLiteDecisionLog(path)
    record = DecisionRecord("d1", "run1", "alice", "s1", "resumo", "resumo", "rule", "completed", ("8",))
    log.append(record)
    with pytest.raises(sqlite3.IntegrityError):
        log.append(record)
    connection = sqlite3.connect(path)
    try:
        for mutation in [
            "UPDATE decisions SET record_json = '{}'",
            "DELETE FROM decisions",
            "INSERT OR REPLACE INTO decisions(decision_id,run_id,record_json) VALUES ('d1','other','{}')",
            "INSERT OR REPLACE INTO decisions(sequence,decision_id,run_id,record_json) VALUES (1,'d2','other','{}')",
        ]:
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(mutation)
            connection.rollback()
    finally:
        connection.close()
    log.close()
    reopened = SQLiteDecisionLog(path)
    try:
        assert [asdict(item) for item in reopened.export("run1")] == [asdict(record)]
        assert list(reopened.export("other")) == []
    finally:
        reopened.close()

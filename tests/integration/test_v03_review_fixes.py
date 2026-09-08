"""Regressions found during the v0.3 backend review; no model inference."""

from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Event

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
from cain.common import IdentityState
from cain.identity import IdentityService
from cain.llm import FakeLLM
from cain.persistence.adapters import LexicalMemoryIndex, SQLiteIdentityStore


def test_stale_first_read_cannot_replace_a_concurrently_created_profile(tmp_path):
    path = tmp_path / "concurrent-first-create.db"
    SQLiteIdentityStore(path).close()
    read_missing, writer_finished = Event(), Event()

    def delayed_inspection():
        # Each worker creates and closes its own SQLite connection.
        store = SQLiteIdentityStore(path)
        original_get = store.get
        intercepted = False

        def get_after_other_writer(user_id):
            nonlocal intercepted
            result = original_get(user_id)
            if result is None and not intercepted:
                intercepted = True
                read_missing.set()
                assert writer_finished.wait(5), "Writer did not release delayed reader"
            return result

        store.get = get_after_other_writer
        try:
            return IdentityService(store, LexicalMemoryIndex()).inspect("alice")
        finally:
            store.close()

    with ThreadPoolExecutor(max_workers=1) as workers:
        reader = workers.submit(delayed_inspection)
        try:
            assert read_missing.wait(5), "Reader did not observe initial absence"
            writer = SQLiteIdentityStore(path)
            try:
                identity = IdentityService(writer, LexicalMemoryIndex())
                committed = identity.set_preference("alice", "format", "steps")
                assert committed.revision == 1
            finally:
                writer.close()
        finally:
            writer_finished.set()
        view = reader.result(timeout=5)

    assert view["revision"] == 1
    assert view["user_model"]["preferences"] == view["effective_preferences"] == {"format": "steps"}
    reopened = SQLiteIdentityStore(path)
    try:
        assert reopened.get("alice").revision == 1
        assert len(reopened.history("alice", 20)) == 2  # one baseline + one change
        assert len(list(reopened.iter_documents())) == 1
        # Repeating create with a stale empty state cannot add a snapshot or reset data.
        current = reopened.create_if_absent("alice", IdentityState("alice"))
        assert current.user_model.preferences == {"format": "steps"}
        assert current.revision == 1
        assert len(reopened.history("alice", 20)) == 2
    finally:
        reopened.close()


def test_atomic_creation_rolls_back_identity_when_baseline_snapshot_fails(tmp_path):
    store = SQLiteIdentityStore(tmp_path / "creation-rollback.db")
    try:
        store._connection.execute("""
            CREATE TRIGGER reject_baseline BEFORE INSERT ON identity_snapshots
            BEGIN SELECT RAISE(ABORT, 'snapshot unavailable'); END
        """)
        with pytest.raises(sqlite3.IntegrityError, match="snapshot unavailable"):
            store.create_if_absent("alice", IdentityState("alice"))
        assert store.get("alice") is None
        assert store.history("alice", 20) == []
    finally:
        store.close()


@pytest.fixture
def client(tmp_path):
    configuration = tmp_path / "cain.toml"
    configuration.write_text(
        '[orchestration]\nllm_routing=false\n[search]\nallow_public_urls=false\npaths=[]\n',
        encoding="utf-8",
    )
    with TestClient(create_app(tmp_path / "ui.db", FakeLLM(), configuration)) as instance:
        yield instance


def test_turn_id_addresses_preferences_feedback_and_reopened_history(client):
    assert client.put("/profile/alice/preferences/language", json={"value": "pt"}).status_code == 200
    reply = client.post("/run", json={
        "user_id": "alice", "session_id": "s", "payload": "Só nesta resposta, responda em inglês.",
    })
    assert reply.status_code == 200, reply.text
    result = reply.json()
    turn_id = result["turn_id"]
    assert turn_id == result["decision_id"]
    assert result["preferences_used"] == {"language": "en"}
    context = {"session_id": "s", "turn_id": turn_id}
    viewed = client.get("/profile/alice", params=context)
    assert viewed.json()["effective_preferences"] == {"language": "en"}

    history = client.get("/sessions/alice/s").json()
    assert history[0]["id"] == turn_id
    assert history[0]["result"]["turn_id"] == history[0]["result"]["decision_id"] == turn_id
    assert history[0]["result"]["preferences_used"] == {"language": "en"}
    feedback = client.post(f"/feedback/{history[0]['id']}", json={"user_id": "alice", "reason": "useful"})
    assert feedback.status_code == 200, feedback.text

    next_reply = client.post("/run", json={
        "user_id": "alice", "session_id": "s", "payload": "Resuma: SQLite persiste dados.", "intent": "resumo",
    })
    assert next_reply.status_code == 200, next_reply.text
    assert next_reply.json()["preferences_used"] == {"language": "pt"}
    assert next_reply.json()["turn_id"] != turn_id

    removed = client.delete("/profile/alice/preferences/language", params={**context, "scope": "turn"})
    assert removed.status_code == 200, removed.text
    assert removed.json()["profile"]["effective_preferences"] == {"language": "pt"}
    entry = removed.json()["profile"]["scoped_preferences"]["turn"]["language"]
    assert entry["status"] == "removed" and entry["turn_id"] == turn_id
    assert client.get("/profile/alice", params=context).json()["effective_preferences"] == {"language": "pt"}
    # Deleting preference state keeps the original turn and its audit/UI history.
    assert len(client.get("/sessions/alice/s").json()) == 2


def test_profile_read_rejects_unknown_session_without_creating_a_conversation(client):
    assert client.get("/sessions/alice").json() == []
    response = client.get("/profile/alice", params={"session_id": "does-not-exist"})
    assert response.status_code == 400
    assert client.get("/sessions/alice").json() == []
    session = client.post("/sessions/alice", json={}).json()
    assert client.get("/profile/alice", params={"session_id": session["id"]}).status_code == 200
    assert [item["id"] for item in client.get("/sessions/alice").json()] == [session["id"]]


def test_profile_read_cannot_create_or_reassign_another_project_or_users_session(client):
    first = client.post("/projects/alice", json={"name": "First"}).json()["id"]
    second = client.post("/projects/alice", json={"name": "Second"}).json()["id"]
    session = client.post("/sessions/alice", json={"project_id": first}).json()["id"]
    assert client.get("/profile/alice", params={"project_id": first, "session_id": session}).status_code == 200
    assert client.get("/profile/alice", params={"project_id": second, "session_id": session}).status_code == 400
    assert client.get("/profile/alice", params={"session_id": session}).status_code == 400
    assert client.get("/profile/bob", params={"session_id": session}).status_code == 400
    assert client.get("/profile/alice", params={"project_id": second, "session_id": "new"}).status_code == 400
    assert client.get("/sessions/alice", params={"project_id": second}).json() == []
    assert client.get("/sessions/bob").json() == []
    assert client.get("/sessions/alice", params={"project_id": first}).json()[0]["id"] == session

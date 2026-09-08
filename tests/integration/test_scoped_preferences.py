"""Scope boundaries and canonical persistence are tested without model inference."""

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from cain.common import IdentityState, ScopedPreference, Signal
from cain.identity import IdentityService
from cain.persistence import ConcurrentIdentityUpdate
from cain.persistence.adapters import LexicalMemoryIndex, SQLiteIdentityStore


class Clock:
    def __init__(self):
        self.now = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


def service(path, clock=None):
    store = SQLiteIdentityStore(path)
    index = LexicalMemoryIndex()
    index.rebuild_from(store)
    return IdentityService(store, index, clock=clock)


@pytest.fixture
def identity(tmp_path):
    instance = service(tmp_path / "scopes.db", Clock())
    yield instance
    instance.store.close()


def test_scope_precedence_does_not_overwrite_global_and_removal_falls_back(identity):
    identity.set_preference("alice", "format", "bullets")
    identity.set_preference("alice", "format", "paragraph", scope="project", project_id="a")
    identity.set_preference("alice", "format", "steps", scope="session", project_id="a", session_id="s")
    context = {"project_id": "a", "session_id": "s", "turn_id": "t"}
    state = identity.set_preference("alice", "format", "bullets", scope="turn", **context)
    view = identity.inspect("alice", **context)
    assert state.user_model.preferences == view["effective_preferences"] == {"format": "bullets"}
    assert view["effective_provenance"]["format"]["scope"] == "turn"
    assert view["user_model"]["preferences"] == {"format": "bullets"}
    assert identity.get("alice").revision == 4
    assert identity.get("alice").user_model.preference_provenance["format"]["revision"] == 1
    for scope, expected, winner in [
        ("turn", "steps", "session"), ("session", "paragraph", "project"),
        ("project", "bullets", "user"),
    ]:
        removed = identity.forget_preference("alice", "format", scope=scope, **context)
        view = identity.inspect("alice", **context)
        assert removed.user_model.preferences == {"format": expected}
        assert view["effective_provenance"]["format"]["scope"] == winner
        assert view["scoped_preferences"][scope]["format"]["status"] == "removed"
    identity.forget_preference("alice", "format")
    assert identity.inspect("alice", **context)["effective_preferences"] == {}
    assert len(list(identity.store.iter_documents())) == 8  # all changes retained


def test_exact_user_project_session_and_turn_addresses(identity):
    identity.set_preference("alice", "language", "pt")
    identity.set_preference("alice", "language", "en", scope="session", project_id="a", session_id="same")
    assert identity.inspect("alice", project_id="a", session_id="same")["effective_preferences"] == {"language": "en"}
    for context in ({}, {"project_id": "b", "session_id": "same"},
                    {"project_id": "a", "session_id": "other"}, {"session_id": "same"}):
        view = identity.inspect("alice", **context)
        assert view["effective_preferences"] == {"language": "pt"}
        assert view["scoped_preferences"]["session"] == {}
    assert identity.inspect("bob", project_id="a", session_id="same")["effective_preferences"] == {}
    identity.set_preference("alice", "verbosity", "short", scope="turn", session_id="s", turn_id="1")
    assert identity.inspect("alice", session_id="s", turn_id="1")["effective_preferences"]["verbosity"] == "short"
    assert "verbosity" not in identity.inspect("alice", session_id="s", turn_id="2")["effective_preferences"]
    assert "verbosity" not in identity.inspect("alice", session_id="different", turn_id="1")["effective_preferences"]


def test_expiration_is_utc_deterministic_and_reveals_lower_layer_after_restart(tmp_path):
    path, clock = tmp_path / "expires.db", Clock()
    instance = service(path, clock)
    instance.set_preference("alice", "language", "pt")
    # Same instant as 12:01 UTC, supplied with an explicit non-UTC offset.
    instance.set_preference("alice", "language", "en", scope="project", project_id="a",
                            expires_at="2030-01-01T09:01:00-03:00")
    assert instance.inspect("alice", project_id="a")["effective_preferences"] == {"language": "en"}
    instance.store.close()
    clock.now += timedelta(minutes=1)
    reopened = service(path, clock)
    try:
        view = reopened.inspect("alice", project_id="a")
        assert view["effective_preferences"] == {"language": "pt"}
        entry = view["scoped_preferences"]["project"]["language"]
        assert entry["status"] == "expired"
        assert entry["expires_at"] == "2030-01-01T12:01:00+00:00"
        assert reopened.get("alice").revision == 2  # expiry is read-time, not a new user action
        assert len(list(reopened.store.iter_documents())) == 2
        # Global expiry must not revive its mirrored v0.2 state_json value.
        reopened.set_preference("alice", "format", "steps", expires_at=clock.now + timedelta(seconds=1))
        clock.now += timedelta(seconds=1)
        view = reopened.inspect("alice")
        assert "format" not in view["effective_preferences"]
        assert view["scoped_preferences"]["user"]["format"]["status"] == "expired"
        assert '"format": "steps"' not in reopened.context_for("alice", "format")
    finally:
        reopened.store.close()


@pytest.mark.parametrize("expires_at", [
    "2030-01-01", "2030-01-01T12:01:00", "not-a-date", "2030-01-01T12:00:00Z",
    "2029-01-01T00:00:00Z", datetime(2030, 1, 1, 12, 1), 42,
])
def test_invalid_expiration_writes_nothing(identity, expires_at):
    with pytest.raises(ValueError):
        identity.set_preference("new-user", "format", "steps", expires_at=expires_at)
    assert identity.store.get("new-user") is None
    assert list(identity.store.iter_documents()) == []


@pytest.mark.parametrize("kwargs", [
    {"scope": "project"}, {"scope": "session"}, {"scope": "turn", "session_id": "s"},
    {"scope": "turn", "turn_id": "t"}, {"scope": "invalid"}, {"scope": ""},
    {"scope": "project", "project_id": " "}, {"project_id": "x" * 201},
])
def test_invalid_scope_never_silently_becomes_global(identity, kwargs):
    with pytest.raises(ValueError):
        identity.set_preference("new-user", "format", "steps", **kwargs)
    assert identity.store.get("new-user") is None
    assert list(identity.store.iter_documents()) == []


def test_explicit_scope_text_applies_before_context_and_only_current_turn(identity):
    identity.observe("alice", "Prefiro respostas em português.")
    metadata = {"project_id": "a", "session_id": "s", "decision_id": "first", "preference_scope": None}
    state = identity.observe("alice", "Só nesta resposta, responda em inglês. Resuma o projeto.", metadata)
    assert state.user_model.preferences == {"language": "en"}
    assert state.user_model.preference_provenance["language"]["turn_id"] == "first"
    assert '"language": "en"' in identity.context_for("alice", "projeto", project_id="a", session_id="s", turn_id="first")
    assert '"language": "pt"' in identity.context_for("alice", "projeto", project_id="a", session_id="s", turn_id="next")
    assert identity.get("alice").user_model.preferences == {"language": "pt"}
    view = identity.inspect("alice", project_id="a", session_id="s", turn_id="first")
    provenance = view["effective_provenance"]["language"]
    assert provenance["source"] == "explicit_user_input"
    assert "Só nesta resposta" in provenance["evidence"]
    assert provenance["signal_id"] in {doc.doc_id for doc in identity.store.iter_documents()}


def test_scoped_correction_removal_and_source_are_canonical_after_rebuild(tmp_path):
    path = tmp_path / "canonical.db"
    instance = service(path)
    instance.set_preference("alice", "format", "bullets")
    instance.observe("alice", "Neste projeto, prefiro respostas em passos.", {"project_id": "a"})
    instance.store.close()
    instance = service(path)
    try:
        previous = instance.inspect("alice", project_id="a")["effective_provenance"]["format"]["signal_id"]
        instance.observe("alice", "Neste projeto, agora prefiro um parágrafo.", {"project_id": "a"})
        assert instance.inspect("alice", project_id="a")["effective_provenance"]["format"]["supersedes_signal_id"] == previous
        instance.memory.drop()
        assert instance.inspect("alice", project_id="a")["effective_preferences"] == {"format": "paragraph"}
        instance.observe("alice", "Neste projeto, não prefiro respostas em passos.", {"project_id": "a"})
        assert instance.inspect("alice", project_id="a")["effective_preferences"] == {"format": "paragraph"}
        instance.clear_preferences("alice", scope="project", project_id="a")
        instance.memory.rebuild_from(instance.store)
        view = instance.inspect("alice", project_id="a")
        assert view["effective_preferences"] == {"format": "bullets"}
        assert view["scoped_preferences"]["project"]["format"]["provenance"]["action"] == "remove"
        context = instance.context_for("alice", "passos parágrafo", project_id="a")
        assert '"doc_id"' not in context
        docs = list(instance.store.iter_documents())
        assert len(docs) == 5
        changes = [change for doc in docs for change in doc.metadata["scoped_preference_changes"]]
        assert any(change["scope"] == "project" and change["value"] == "steps" for change in changes)
        assert any(change["scope"] == "project" and change["value"] == "paragraph" for change in changes)
    finally:
        instance.store.close()


def test_project_and_legacy_history_boundaries_survive_rebuild(identity):
    identity.update("alice", Signal("abacaxi LEGACY_GLOBAL"))
    identity.update("alice", Signal("abacaxi PROJECT_A", metadata={"project_id": "a"}))
    identity.update("alice", Signal("abacaxi PROJECT_B", metadata={"project_id": "b"}))
    identity.update("bob", Signal("abacaxi BOB_PRIVATE", metadata={"project_id": "a"}))
    identity.memory.drop()
    identity.memory.rebuild_from(identity.store)
    for project, present, absent in [
        (None, "LEGACY_GLOBAL", ["PROJECT_A", "PROJECT_B", "BOB_PRIVATE"]),
        ("a", "PROJECT_A", ["LEGACY_GLOBAL", "PROJECT_B", "BOB_PRIVATE"]),
        ("b", "PROJECT_B", ["LEGACY_GLOBAL", "PROJECT_A", "BOB_PRIVATE"]),
    ]:
        context = identity.context_for("alice", "abacaxi", project_id=project)
        assert present in context
        assert all(text not in context for text in absent)


def test_old_database_without_scoped_table_keeps_original_json_and_globals(tmp_path):
    path = tmp_path / "actual-old-schema.db"
    old_state = asdict(IdentityState("alice"))
    old_state["revision"] = 7
    old_state["user_model"]["preferences"] = {"format": "steps"}
    del old_state["user_model"]["preference_provenance"]
    payload = json.dumps(old_state)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE identities (user_id TEXT PRIMARY KEY, state_json TEXT NOT NULL)")
        connection.execute("INSERT INTO identities VALUES (?, ?)", ("alice", payload))
    instance = service(path)
    try:
        view = instance.inspect("alice", project_id="new-project")
        assert view["user_model"]["preferences"] == view["effective_preferences"] == {"format": "steps"}
        assert view["effective_provenance"]["format"]["source"] == "legacy_global_profile"
        assert instance.store._connection.execute("SELECT state_json FROM identities").fetchone()[0] == payload
        instance.set_preference("alice", "format", "paragraph", scope="project", project_id="new-project")
        assert instance.get("alice").user_model.preferences == {"format": "steps"}
        assert instance.get("alice").revision == 8
    finally:
        instance.store.close()


def test_scoped_transaction_rolls_back_profile_overlay_signal_and_snapshot(identity):
    identity.set_preference("alice", "format", "bullets")
    before = identity.get("alice")
    documents = list(identity.store.iter_documents())
    duplicate = Signal("duplicate", signal_id=documents[0].doc_id)
    changed = deepcopy(before)
    changed.revision += 1
    record = ScopedPreference("alice", "project", "format", "steps", "set", project_id="a")
    with pytest.raises(sqlite3.IntegrityError):
        identity.store.apply_signal("alice", duplicate, changed, before.revision, scoped_preferences=[record])
    assert identity.get("alice") == before
    assert identity.store.list_scoped_preferences("alice", project_id="a") == identity.store.list_scoped_preferences("alice")
    assert len(identity.store.history("alice")) == 2
    assert list(identity.store.iter_documents()) == documents
    identity.store.apply_signal("alice", Signal("committed"), changed, before.revision, scoped_preferences=[record])
    assert identity.inspect("alice", project_id="a")["effective_preferences"] == {"format": "steps"}
    with pytest.raises(ConcurrentIdentityUpdate):
        identity.store.apply_signal("alice", Signal("stale"), changed, before.revision, scoped_preferences=[record])
    assert len(identity.store.history("alice")) == 3
    assert len(list(identity.store.iter_documents())) == 2


def test_invalid_observation_scope_rejects_entire_batch_before_writes(identity):
    with pytest.raises(ValueError, match="project_id"):
        identity.observe("new-user", "Prefiro respostas curtas. Neste projeto, prefiro respostas em passos.")
    assert identity.store.get("new-user") is None
    with pytest.raises(ValueError, match="conflicts"):
        identity.observe("new-user", "Neste projeto, prefiro respostas em passos.",
                         {"project_id": "a", "preference_scope": "user"})
    assert identity.store.get("new-user") is None
    assert list(identity.store.iter_documents()) == []


def test_inspection_is_detached_and_scoped_output_is_never_learned(identity):
    identity.observe("alice", "Nesta conversa, prefiro respostas curtas.", {"session_id": "s"})
    identity.update("alice", Signal("Neste projeto, prefiro respostas longas em inglês.", metadata={"session_id": "s"}))
    view = identity.inspect("alice", session_id="s")
    view["effective_preferences"]["verbosity"] = "detailed"
    view["scoped_preferences"]["session"]["verbosity"]["provenance"]["scope"] = "user"
    actual = identity.inspect("alice", session_id="s")
    assert actual["effective_preferences"] == {"verbosity": "short"}
    assert actual["effective_provenance"]["verbosity"]["scope"] == "session"
    assert actual["user_model"]["preferences"] == {}


def test_observed_scoped_imperative_transcript_cannot_resurrect_as_history(identity):
    text = "Só nesta resposta, use tópicos. MARCADOR_TRANSITORIO"
    metadata = {"session_id": "s", "decision_id": "old"}
    first = identity.observe("alice", text, metadata)
    second = identity.update("alice", Signal("Usuário: " + text + "\nCain: combinado.", metadata={
        **metadata, "user_input": text, "preference_observed": True,
    }))
    assert first == second
    identity.memory.drop()
    identity.memory.rebuild_from(identity.store)
    context = identity.context_for("alice", "tópicos MARCADOR_TRANSITORIO", session_id="s", turn_id="new")
    assert "MARCADOR_TRANSITORIO" not in context
    assert '"format": "bullets"' not in context
    assert len(list(identity.store.iter_documents())) == 2

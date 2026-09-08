from dataclasses import asdict
import json
import sqlite3

import pytest

from cain.common import IdentityState, Signal
from cain.identity import IdentityService, PREFERENCE_KEYS
from cain.persistence import ConcurrentIdentityUpdate
from cain.persistence.adapters import LexicalMemoryIndex, SQLiteIdentityStore


def service(path, **kwargs):
    store = SQLiteIdentityStore(path)
    index = LexicalMemoryIndex()
    index.rebuild_from(store)
    return IdentityService(store, index, **kwargs)


def test_preference_correction_and_provenance_survive_process_style_reopen(tmp_path):
    path = tmp_path / "persistent.db"
    identity = service(path)
    original = identity.observe("alice", "Prefiro respostas curtas em passos e em português.",
                                {"session_id": "session-1"})
    assert original.user_model.preferences == {"format": "steps", "verbosity": "short", "language": "pt"}
    signal_ids = {document.doc_id for document in identity.store.iter_documents()}
    assert original.user_model.preference_provenance["format"]["signal_id"] in signal_ids
    personality = asdict(original.personality)
    identity.store.close()

    reopened = service(path)
    assert reopened.inspect("alice")["user_model"]["preferences"] == original.user_model.preferences
    updated = reopened.observe("alice", "Agora prefiro um parágrafo. Quero respostas detalhadas em inglês.",
                               {"session_id": "session-2"})
    assert updated.revision == 2
    assert updated.user_model.preferences == {"format": "paragraph", "verbosity": "detailed", "language": "en"}
    assert asdict(updated.personality) == personality
    assert updated.user_model.preference_provenance["format"]["revision"] == 2
    assert reopened.inspect("bob")["user_model"]["preferences"] == {}
    reopened.store.close()

    final = service(path)
    try:
        assert final.get("alice").user_model.preferences == updated.user_model.preferences
        assert final.get("alice").revision == 2
        assert len(final.store.history("alice", 20)) == 3  # baseline + two atomic profile updates
    finally:
        final.store.close()


def test_forget_does_not_resurrect_from_rebuilt_or_legacy_memory(tmp_path):
    identity = service(tmp_path / "forgotten.db")
    try:
        old_declaration = "Prefiro respostas em passos. DOCUMENTO_IDENTIFICADOR_ANTIGO"
        identity.observe("alice", old_declaration)
        identity.update("alice", Signal("Usuário: " + old_declaration + "\nCain: combinado.",
                                        metadata={"user_input": old_declaration, "preference_observed": True}))
        # Simulate an older persisted transcript, which has no v0.2 preference metadata.
        legacy = "Usuário: Prefiro respostas em passos. LEGACY_IDENTIFICADOR"
        identity.store.append_signal("alice", Signal(legacy))
        identity.memory.rebuild_from(identity.store)
        forgotten = identity.forget_preference("alice", "format")
        assert "format" not in forgotten.user_model.preferences
        assert forgotten.user_model.preference_provenance["format"]["action"] == "remove"
        identity.memory.drop()
        identity.memory.rebuild_from(identity.store)
        assert identity.memory.query("passos", 20, {"user_id": "alice"})  # raw source retained
        context = identity.context_for("alice", "passos IDENTIFICADOR")
        assert "DOCUMENTO_IDENTIFICADOR_ANTIGO" not in context
        assert "LEGACY_IDENTIFICADOR" not in context
        assert "Chaves ausentes ou removidas" in context
        assert identity.get("alice").user_model.preferences == {}
        assert len(list(identity.store.iter_documents())) == 4
    finally:
        identity.store.close()


def test_clear_preferences_is_inspectable_and_not_raw_history_deletion(tmp_path):
    identity = service(tmp_path / "clear.db")
    try:
        identity.observe("alice", "Prefiro respostas curtas em passos e em português.")
        cleared = identity.clear_preferences("alice")
        assert cleared.user_model.preferences == {}
        assert set(cleared.user_model.preference_provenance) == set(PREFERENCE_KEYS)
        assert all(p["action"] == "remove" for p in cleared.user_model.preference_provenance.values())
        detached = identity.inspect("alice")
        detached["user_model"]["preferences"]["format"] = "steps"
        assert identity.get("alice").user_model.preferences == {}
        assert len(list(identity.store.iter_documents())) == 2
        with pytest.raises(ValueError, match="Unknown preference"):
            identity.forget_preference("alice", "arbitrary")
    finally:
        identity.store.close()


def test_profile_and_source_remain_canonical_after_index_failure(tmp_path, monkeypatch):
    identity = service(tmp_path / "cache-failure.db")
    try:
        def fail(*args, **kwargs):
            raise RuntimeError("index offline")
        monkeypatch.setattr(identity.memory, "index", fail)
        with pytest.raises(RuntimeError, match="index offline"):
            identity.observe("alice", "Prefiro respostas detalhadas em inglês.")
        assert identity.get("alice").user_model.preferences == {"verbosity": "detailed", "language": "en"}
        assert len(list(identity.store.iter_documents())) == 1
        monkeypatch.undo()
        identity.memory.rebuild_from(identity.store)
        assert identity.memory.query("inglês", 3, {"user_id": "alice"})
        assert '"language": "en"' in identity.context_for("alice", "inglês")
    finally:
        identity.store.close()


def test_atomic_duplicate_signal_rollback_and_stale_revision_rejection(tmp_path):
    path = tmp_path / "atomic.db"
    store = SQLiteIdentityStore(path)
    try:
        store.upsert("alice", IdentityState("alice"))
        signal = Signal("original", signal_id="original-signal")
        store.append_signal("alice", signal)
        changed = store.get("alice")
        changed.revision = 1
        changed.user_model.preferences["format"] = "steps"
        with pytest.raises(sqlite3.IntegrityError):
            store.apply_signal("alice", signal, changed, expected_revision=0)
        assert store.get("alice").revision == 0
        assert store.get("alice").user_model.preferences == {}
        assert len(store.history("alice", 10)) == 1
        store.apply_signal("alice", Signal("accepted"), changed, expected_revision=0)
        with pytest.raises(ConcurrentIdentityUpdate):
            store.apply_signal("alice", Signal("stale"), changed, expected_revision=0)
        assert len(list(store.iter_documents())) == 2
        assert len(store.history("alice", 10)) == 2
    finally:
        store.close()


def test_existing_v01_json_without_provenance_is_read_compatibly(tmp_path):
    path = tmp_path / "legacy.db"
    store = SQLiteIdentityStore(path)
    store.upsert("alice", IdentityState("alice"))
    store.close()
    with sqlite3.connect(path) as connection:
        old = json.loads(connection.execute("SELECT state_json FROM identities").fetchone()[0])
        del old["user_model"]["preference_provenance"]
        connection.execute("UPDATE identities SET state_json = ?", (json.dumps(old),))
    identity = service(path)
    try:
        assert identity.get("alice").user_model.preference_provenance == {}
        identity.observe("alice", "Prefiro respostas em tópicos.")
        assert identity.get("alice").user_model.preferences == {"format": "bullets"}
    finally:
        identity.store.close()


def test_context_budget_top_k_and_user_isolation(tmp_path):
    identity = service(tmp_path / "bounded.db", memory_top_k=2, max_context_chars=3500)
    try:
        for i in range(20):
            identity.update("alice", Signal(f"abacaxi memória {i} " + "conteúdo " * 200))
        identity.update("bob", Signal("abacaxi SEGREDO_EXCLUSIVO_BOB"))
        context = identity.context_for("alice", "abacaxi memória")
        assert len(context) <= 3500
        assert context.count('"doc_id"') <= 2
        assert "SEGREDO_EXCLUSIVO_BOB" not in context
        assert "abacaxi" in context
    finally:
        identity.store.close()


def test_transcript_already_observed_does_not_apply_preferences_twice(tmp_path):
    identity = service(tmp_path / "once.db")
    try:
        text = "Prefiro respostas em tópicos."
        first = identity.observe("alice", text)
        final = identity.update("alice", Signal("Cain: Prefiro respostas longas.", metadata={
            "user_input": text, "preference_observed": True,
        }))
        assert final == first
        assert final.revision == 1
        assert len(list(identity.store.iter_documents())) == 2
    finally:
        identity.store.close()


def test_current_request_is_excluded_from_historical_context(tmp_path):
    identity = service(tmp_path / "current.db")
    try:
        identity.observe("alice", "projeto MEMORIA_PASSADA", {"decision_id": "previous"})
        identity.observe("alice", "projeto PEDIDO_ATUAL", {"decision_id": "current"})
        context = identity.context_for("alice", "projeto", exclude_decision_id="current")
        assert "MEMORIA_PASSADA" in context
        assert "PEDIDO_ATUAL" not in context
    finally:
        identity.store.close()

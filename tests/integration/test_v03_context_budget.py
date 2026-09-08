"""Derived identity budgets preserve canonical data and scope boundaries."""

from dataclasses import asdict
import json

import pytest

from cain.common import Signal
from cain.identity import IdentityService
from cain.persistence.adapters import LexicalMemoryIndex, SQLiteIdentityStore


def service(path, **kwargs):
    store = SQLiteIdentityStore(path)
    index = LexicalMemoryIndex()
    index.rebuild_from(store)
    return IdentityService(store, index, **kwargs)


@pytest.fixture
def identity(tmp_path):
    result = service(tmp_path / "context.db")
    yield result
    result.store.close()


def test_three_preferences_and_common_history_fit_default_bytes_without_losing_audit(tmp_path):
    path = tmp_path / "persisted.db"
    instance = service(path)
    address = {"project_id": "project-a", "session_id": "session-a", "decision_id": "turn-a"}
    instance.observe("private-user-id", "Prefiro respostas detalhadas em tópicos e português. AUDIT_EVIDENCE", address)
    paragraph = (
        "Usuário: Como funciona a persistência SQLite no projeto?\n"
        "Cain: O projeto grava eventos em uma transação e reconstrói o índice quando necessário. "
        "Essa separação permite recuperar os dados se o cache ficar indisponível. "
    )
    for i in range(3):
        instance.update("private-user-id", Signal((paragraph * 3)[:400], metadata={
            **address, "decision_id": f"previous-{i}",
        }))
    before = instance.inspect("private-user-id", project_id="project-a", session_id="session-a")
    source_before = list(instance.store.iter_documents())
    context = instance.context_for("private-user-id", "SQLite projeto", project_id="project-a", session_id="session-a")
    assert len(context.encode("utf-8")) <= 2000
    assert '"format": "bullets"' in context
    assert '"verbosity": "detailed"' in context
    assert '"language": "pt"' in context
    assert "persistência SQLite" in context
    assert '"doc_id"' in context
    assert '"truncated": true' in context
    for audit_key in ("preference_provenance", "signal_id", "AUDIT_EVIDENCE", "private-user-id", "turn-a"):
        assert audit_key not in context
    assert instance.inspect("private-user-id", project_id="project-a", session_id="session-a") == before
    assert list(instance.store.iter_documents()) == source_before
    instance.store.close()

    reopened = service(path)
    try:
        after = reopened.inspect("private-user-id", project_id="project-a", session_id="session-a")
        assert after == before
        assert len(after["effective_provenance"]) == 3
        assert after["effective_provenance"]["format"]["signal_id"] == source_before[0].doc_id
        assert "AUDIT_EVIDENCE" in source_before[0].text
        assert list(reopened.store.iter_documents()) == source_before
    finally:
        reopened.store.close()


def test_prompt_projection_preserves_personality_and_active_model_fields(identity):
    state = identity.get("alice")
    state.user_model.preferences = {"language": "pt"}
    state.user_model.expertise = "Engenharia de software"
    state.user_model.recurring_goals = ["Documentar a arquitetura"]
    state.user_model.preference_provenance = {"language": {"evidence": "AUDIT_ONLY", "signal_id": "SOURCE_ONLY"}}
    before = asdict(state)
    projected = json.loads(identity.as_context(state).splitlines()[-1])
    assert projected == {
        "personality": {**asdict(state.personality), "principles": list(state.personality.principles)},
        "preferences": {"language": "pt"},
        "expertise": "Engenharia de software", "recurring_goals": ["Documentar a arquitetura"],
    }
    assert asdict(state) == before
    state.user_model.expertise = ""
    state.user_model.recurring_goals = []
    empty_fields = json.loads(identity.as_context(state).splitlines()[-1])
    assert "expertise" not in empty_fields and "recurring_goals" not in empty_fields


def test_unicode_and_json_escaping_are_counted_in_the_actual_serialized_budget(identity):
    original = 'SQLite observação 😀 中文 "trecho" \\diretório\n' * 80
    identity.update("alice", Signal(original))
    context = identity.context_for("alice", "SQLite")
    assert 1900 <= len(context.encode("utf-8")) <= 2000
    memories = json.loads(context.rsplit("consulte o perfil efetivo:\n", 1)[1])
    assert len(memories) == 1
    assert memories[0]["truncated"] is True
    assert original.startswith(memories[0]["text"])
    assert "😀" in memories[0]["text"] and "中文" in memories[0]["text"]
    assert "\ufffd" not in context
    assert list(identity.store.iter_documents())[0].text == original


def test_legacy_character_limit_also_applies_when_byte_budget_is_larger(tmp_path):
    instance = service(tmp_path / "legacy-char-bound.db", max_context_chars=1200, max_context_bytes=4000)
    try:
        instance.update("alice", Signal("SQLite ação 😀 " * 200))
        context = instance.context_for("alice", "SQLite")
        assert len(context) <= 1200
        assert len(context.encode("utf-8")) <= 4000
        assert '"truncated": true' in context
        assert "SQLite ação" in context
    finally:
        instance.store.close()


@pytest.mark.parametrize("field", ["expertise", "recurring_goals"])
def test_essential_profile_is_rejected_instead_of_silently_truncated(identity, field):
    state = identity.get("alice")
    value = "Conhecimento essencial 😀 " * 150
    setattr(state.user_model, field, value if field == "expertise" else [value])
    identity.store.upsert("alice", state)
    before = identity.inspect("alice")
    with pytest.raises(ValueError, match="Perfil essencial.*max_context_bytes"):
        identity.context_for("alice", "SQLite")
    assert identity.inspect("alice") == before


def test_compact_context_keeps_effective_scope_and_history_isolation(identity):
    identity.set_preference("alice", "format", "bullets")
    identity.set_preference("alice", "format", "steps", scope="project", project_id="a")
    identity.set_preference("alice", "format", "paragraph", scope="turn", project_id="a", session_id="s", turn_id="t")
    for user, project, marker in [
        ("alice", "a", "VISIBLE_A"), ("alice", "b", "HIDDEN_B"),
        ("alice", None, "HIDDEN_LEGACY"), ("bob", "a", "HIDDEN_USER"),
    ]:
        identity.update(user, Signal("SQLite " + marker, metadata={"project_id": project}))
    context = identity.context_for("alice", "SQLite", project_id="a", session_id="s", turn_id="t")
    assert len(context.encode("utf-8")) <= 2000
    assert '"format": "paragraph"' in context
    assert "VISIBLE_A" in context
    assert all(marker not in context for marker in ("HIDDEN_B", "HIDDEN_LEGACY", "HIDDEN_USER"))
    next_context = identity.context_for("alice", "SQLite", project_id="a", session_id="s", turn_id="next")
    assert '"format": "steps"' in next_context
    assert identity.get("alice").user_model.preferences == {"format": "bullets"}


def test_essential_header_must_fit_both_limits(identity):
    identity.max_context_bytes = 500
    with pytest.raises(ValueError, match="Perfil essencial"):
        identity.context_for("alice", "SQLite")
    identity.max_context_bytes = 4000
    identity.max_context_chars = 500
    with pytest.raises(ValueError, match="Perfil essencial"):
        identity.context_for("alice", "SQLite")

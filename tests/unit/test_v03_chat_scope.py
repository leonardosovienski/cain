"""CLI regression: a selected chat scope must survive argument forwarding."""

import io

from cain.cli import main
from cain.llm import FakeLLM
from cain.runtime import build_cain


def test_chat_session_flag_persists_only_in_selected_session(tmp_path, monkeypatch, capsys):
    database = tmp_path / "chat.db"
    config = tmp_path / "chat.toml"
    config.write_text('[search]\npaths=[]\nallow_public_urls=false\n', encoding="utf-8")
    with build_cain(database, FakeLLM()) as runtime:
        runtime.identity.set_preference("alice", "format", "paragraph")

    # The text has no scope marker: only the CLI flag chooses session scope.
    monkeypatch.setattr("sys.stdin", io.StringIO(
        "Prefiro respostas em passos. Resuma: A revisão ainda não foi aprovada.\n/sair\n"
    ))
    assert main([
        "chat", "--config", str(config), "--db", str(database), "--provider", "fake",
        "--user", "alice", "--session", "selected", "--preference-scope", "session",
    ]) == 0
    assert "SIMULAÇÃO FakeLLM" in capsys.readouterr().out

    # Reopening also proves the overlay was persisted, not just kept in the chat object.
    with build_cain(database, FakeLLM()) as reopened:
        view = reopened.identity.inspect("alice", session_id="selected")
        assert view["effective_preferences"] == {"format": "steps"}
        assert view["effective_provenance"]["format"]["scope"] == "session"
        assert reopened.identity.get("alice").user_model.preferences == {"format": "paragraph"}
        assert reopened.identity.inspect("alice", session_id="next")["effective_preferences"] == {
            "format": "paragraph",
        }

from fastapi.testclient import TestClient

from cain.api import create_app
from cain.llm import FakeLLM


def test_api_request_scoped_persistence(tmp_path):
    with TestClient(create_app(tmp_path / "api.db", FakeLLM())) as client:
        assert client.get("/health").status_code == 200
        for session in ("s1", "s2"):
            result = client.post("/run", json={
                "user_id": "leo", "session_id": session,
                "payload": "Resuma: Um sistema persiste estado em SQLite.", "intent": "resumo",
            })
            assert result.status_code == 200, result.text
            assert result.json()["selected_agent"] == "resumo"
            assert len(result.json()["steps"]) == 8
        assert client.post("/run", json={
            "user_id": "leo", "session_id": "s3", "payload": "   ",
        }).status_code == 422


def test_unknown_intent_is_client_error_not_provider_outage(tmp_path):
    with TestClient(create_app(tmp_path / "api.db", FakeLLM())) as client:
        response = client.post("/run", json={
            "user_id": "leo", "session_id": "s1", "payload": "teste",
            "intent": "inexistente",
        })
        assert response.status_code == 422


def test_profile_learns_before_generation_and_can_be_corrected_and_removed(tmp_path):
    class CaptureLLM:
        def __init__(self):
            self.contexts = []

        def generate(self, prompt, context=""):
            self.contexts.append(context)
            return "Resposta de teste"

    model = CaptureLLM()
    database = tmp_path / "profile.db"
    with TestClient(create_app(database, model)) as client:
        result = client.post("/run", json={
            "user_id": "alice", "session_id": "one",
            "payload": "Prefiro respostas em passos. Resuma: SQLite armazena dados.",
            "intent": "resumo",
        })
        assert result.status_code == 200, result.text
        assert result.json()["profile"]["user_model"]["preferences"]["format"] == "steps"
        assert "steps" in model.contexts[-1]
    with TestClient(create_app(database, model)) as client:
        profile = client.get("/profile/alice").json()
        assert profile["user_model"]["preferences"]["format"] == "steps"
        assert client.get("/profile/bob").json()["user_model"]["preferences"] == {}
        result = client.post("/run", json={
            "user_id": "alice", "session_id": "two",
            "payload": "Agora prefiro um parágrafo. Resuma: Contratos definem entradas.",
            "intent": "resumo",
        })
        assert result.status_code == 200, result.text
        assert result.json()["profile"]["user_model"]["preferences"]["format"] == "paragraph"
        result = client.delete("/profile/alice/preferences/format")
        assert result.status_code == 200
        assert "format" not in result.json()["profile"]["user_model"]["preferences"]
        assert result.json()["audit_history_retained"] is True
        assert client.delete("/profile/alice/preferences/invalid").status_code == 422


def test_profile_controls_survive_missing_search_source(tmp_path):
    config = tmp_path / "cain.toml"
    config.write_text('[search]\npaths=["deleted-source"]\n', encoding="utf-8")
    with TestClient(create_app(tmp_path / "state.db", FakeLLM(), config)) as client:
        assert client.get("/profile/alice").status_code == 200
        assert client.delete("/profile/alice/preferences/format").status_code == 200
        assert client.delete("/profile/alice/preferences").status_code == 200
        result = client.post("/run", json={
            "user_id": "alice", "session_id": "one", "payload": "Resuma: teste",
        })
        # Summary does not consume search sources. Missing sources must only block search.
        assert result.status_code == 200
        search = client.post("/run", json={
            "user_id": "alice", "session_id": "one", "payload": "Busque documentação",
            "intent": "busca",
        })
        assert search.status_code == 503

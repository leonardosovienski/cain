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

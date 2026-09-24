"""Requests accepted on a non-loopback socket need a configured bearer token.

Protected behaviour: the API serves without credentials only when the connection was
accepted on a local address (loopback, or a name the app was told is local through
``trusted_hosts``). A request that reached the process through any other interface,
for example ``--host 0.0.0.0`` or a reverse proxy that rewrites ``Host``, is refused
with 403 unless ``CAIN_API_TOKEN`` (or ``create_app(api_token=...)``) is configured and
presented as ``Authorization: Bearer``. Loopback behaviour is unchanged.
"""
from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
from cain.llm import FakeLLM

TOKEN = "correct-horse-battery-staple"


def app_for(tmp_path, **kwargs):
    return create_app(tmp_path / "api.db", FakeLLM(), **kwargs)


def run_body():
    return {"user_id": "leo", "session_id": "s", "payload": "Prefiro respostas curtas."}


@pytest.mark.parametrize("base_url", ["http://127.0.0.1", "http://localhost", "http://127.0.0.9"])
def test_loopback_socket_serves_without_any_token(tmp_path, base_url, monkeypatch):
    monkeypatch.delenv("CAIN_API_TOKEN", raising=False)
    with TestClient(app_for(tmp_path), base_url=base_url) as client:
        assert client.get("/health", headers={"Host": "127.0.0.1"}).status_code == 200


def test_declared_test_host_is_local_but_production_default_is_not(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_API_TOKEN", raising=False)
    with TestClient(app_for(tmp_path, trusted_hosts=("testserver",))) as client:
        assert client.get("/health").status_code == 200
    with TestClient(app_for(tmp_path)) as client:  # socket "testserver" is not local in production
        response = client.get("/health")
        assert response.status_code == 403 and "loopback" in response.json()["detail"]


def test_lan_socket_is_refused_even_with_a_trusted_host_header(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_API_TOKEN", raising=False)
    app = app_for(tmp_path)
    with TestClient(app, base_url="http://192.168.1.5") as lan:
        headers = {"Host": "127.0.0.1"}  # a proxy rewriting Host must not help
        assert lan.get("/health", headers=headers).status_code == 403
        assert lan.post("/run", json=run_body(), headers=headers).status_code == 403
        assert lan.get("/", headers=headers).status_code == 403
    with TestClient(app, base_url="http://127.0.0.1") as local:
        assert local.get("/sessions/leo").json() == [], "nothing was persisted by the refused calls"


def test_configured_token_admits_lan_clients_and_only_the_exact_token(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_API_TOKEN", raising=False)
    app = app_for(tmp_path, api_token=TOKEN)
    with TestClient(app, base_url="http://192.168.1.5") as lan:
        host = {"Host": "127.0.0.1"}
        assert lan.get("/health", headers=host).status_code == 403
        assert lan.get("/health", headers={**host, "Authorization": f"Bearer {TOKEN}"}).status_code == 200
        assert lan.get("/health", headers={**host, "Authorization": f"Bearer {TOKEN}x"}).status_code == 403
        assert lan.get("/health", headers={**host, "Authorization": f"Bearer {TOKEN[:-1]}"}).status_code == 403
        assert lan.get("/health", headers={**host, "Authorization": f"Basic {TOKEN}"}).status_code == 403
        assert lan.get("/health", headers={**host, "Authorization": TOKEN}).status_code == 403
    with TestClient(app, base_url="http://127.0.0.1") as local:
        assert local.get("/health").status_code == 200, "loopback never needs the token"


def test_token_comes_from_the_environment_when_not_passed(tmp_path, monkeypatch):
    monkeypatch.setenv("CAIN_API_TOKEN", TOKEN)
    with TestClient(app_for(tmp_path), base_url="http://10.0.0.7") as lan:
        assert lan.get("/health", headers={"Host": "localhost", "Authorization": f"Bearer {TOKEN}"}).status_code == 200
    monkeypatch.setenv("CAIN_API_TOKEN", "")
    with TestClient(app_for(tmp_path), base_url="http://10.0.0.7") as lan:
        assert lan.get("/health", headers={"Host": "localhost", "Authorization": "Bearer "}).status_code == 403


@pytest.mark.parametrize("bad", [5, "", "has space", "tab\tin", "short"])
def test_invalid_tokens_are_refused_at_startup(tmp_path, bad, monkeypatch):
    monkeypatch.delenv("CAIN_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="CAIN_API_TOKEN"):
        app_for(tmp_path, api_token=bad)

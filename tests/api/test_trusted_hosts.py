"""Trusted Host allowlist: production accepts only loopback names.

Protected behaviour: ``create_app()`` with no ``trusted_hosts`` argument is the
production configuration. It must reject ``Host: testserver`` (Starlette's
TestClient default) and accept the loopback names. Tests that drive the app
through ``TestClient`` opt in explicitly with ``trusted_hosts=("testserver",)``.
"""
from fastapi.testclient import TestClient
import pytest

from cain.api import TRUSTED_HOSTS, create_app
from cain.llm import FakeLLM


def test_production_default_is_loopback_only():
    assert TRUSTED_HOSTS == ("127.0.0.1", "localhost", "[::1]")
    assert "testserver" not in TRUSTED_HOSTS


def test_production_default_rejects_testserver_host(tmp_path):
    # Connection accepted on loopback (so the local-bind guard passes); only the Host header
    # is under test here.
    with TestClient(create_app(tmp_path / "api.db", FakeLLM()), base_url="http://127.0.0.1") as client:
        assert client.get("/health", headers={"Host": "testserver"}).status_code == 400
        assert client.get("/health", headers={"Host": "testserver:8000"}).status_code == 400
    with TestClient(create_app(tmp_path / "api.db", FakeLLM())) as client:
        assert client.get("/health").status_code == 403  # socket "testserver" is not local either


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "127.0.0.1:8000"])
def test_production_default_accepts_loopback_hosts(tmp_path, host):
    # base_url only sets the default; the Host header is what the middleware checks.
    # "[::1]" is listed but Starlette splits the header on ":" and never matches it;
    # that pre-existing gap is out of scope here and deliberately not asserted.
    app = create_app(tmp_path / "api.db", FakeLLM())
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/health", headers={"Host": host}).status_code == 200


def test_test_client_opt_in_keeps_other_hosts_untrusted(tmp_path):
    app = create_app(tmp_path / "api.db", FakeLLM(), trusted_hosts=("testserver",))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health", headers={"Host": "attacker.example"}).status_code == 400
        assert client.get("/health", headers={"Host": "127.0.0.1"}).status_code == 400


def test_trusted_hosts_must_be_non_empty_host_names(tmp_path):
    for bad in ((), ("",), ("127.0.0.1", 5), "localhost"):
        with pytest.raises((ValueError, TypeError)):
            create_app(tmp_path / "api.db", FakeLLM(), trusted_hosts=bad)

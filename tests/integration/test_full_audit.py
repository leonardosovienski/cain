"""Whole-project audit regressions; only disposable files and injected providers."""

import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
from cain.llm import FakeLLM, OllamaLLM, LLMError
from cain.cli import main
from cain.settings import load_settings
from cain.workspace import WorkspaceStore


@pytest.mark.parametrize("text", [
    '[search]\npaths="notes.md"',
    '[llm]\nnum_ctx="8192"',
    '[llm]\nnum_predict=-1',
    '[llm]\ntimeout=nan',
    '[llm]\nthink="false"',
    '[search]\nmode="lexical"\nunknown=true',
])
def test_invalid_configuration_is_rejected_at_load(tmp_path, text):
    config = tmp_path / "bad.toml"
    config.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_settings(config)


def test_code_and_profile_do_not_initialize_unrelated_embedding(tmp_path, monkeypatch):
    config = tmp_path / "cain.toml"
    config.write_text('[search]\nmode="hybrid"\npaths=["missing.md"]', encoding="utf-8")
    monkeypatch.setattr("cain.api.configured_llm", lambda settings: FakeLLM())
    calls = []
    def unavailable(settings):
        calls.append(True)
        raise RuntimeError("Embedding offline")
    monkeypatch.setattr("cain.api.configured_embedding", unavailable)
    with TestClient(create_app(tmp_path / "db.sqlite", config_path=config)) as client:
        assert client.get("/profile/leo").status_code == 200
        response = client.post("/run", json={"user_id": "leo", "session_id": "s",
            "payload": "Escreva código Python para somar", "intent": "codigo"})
        assert response.status_code == 200, response.text
        assert calls == []
        failed_search = client.post("/run", json={"user_id": "leo", "session_id": "s",
            "payload": "Buscar documentação", "intent": "busca"})
        assert failed_search.status_code == 503
        assert len(calls) == 1


def test_provider_transport_reads_with_a_byte_limit(monkeypatch):
    class BoundedResponse(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 4 * 1024 * 1024 + 1, "Unbounded provider HTTP response"
            return super().read(size)
    monkeypatch.setattr("cain.llm.urlopen", lambda *args, **kwargs:
        BoundedResponse(json.dumps({"response": "bounded", "done": True}).encode()))
    assert OllamaLLM().generate("test") == "bounded"


def test_uploaded_document_mutation_is_detected_before_retrieval(tmp_path):
    store = WorkspaceStore(tmp_path / "workspace.db")
    project = store.create_project("leo", "Project")["id"]
    document = store.add_document("leo", project, "source.md", "Original source")
    Path(document["path"]).write_text("Different source", encoding="utf-8")
    with pytest.raises(ValueError, match="integridade"):
        store.documents("leo", project)


def test_workspace_paths_survive_reopening_from_another_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = WorkspaceStore("workspace.db")
    project = store.create_project("leo", "Project")["id"]
    document = store.add_document("leo", project, "source.md", "Original source")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    reopened = WorkspaceStore(tmp_path / "workspace.db")
    saved = reopened.documents("leo", project)[0]
    assert Path(saved["path"]).is_absolute()
    assert Path(saved["path"]).read_text(encoding="utf-8") == "Original source"
    assert saved["id"] == document["id"]


def test_cli_code_works_without_search_dependencies(tmp_path, monkeypatch, capsys):
    config = tmp_path / "cain.toml"
    config.write_text('[search]\nmode="hybrid"\npaths=["missing.md"]', encoding="utf-8")
    monkeypatch.setattr("cain.cli.configured_llm", lambda settings: FakeLLM())
    def forbidden(settings):
        raise AssertionError("Code must not initialize embeddings")
    monkeypatch.setattr("cain.cli.configured_embedding", forbidden)
    assert main(["run", "Escreva código Python", "--intent", "codigo", "--config", str(config)]) == 0
    assert json.loads(capsys.readouterr().out)["selected_agent"] == "codigo"


def test_generation_oversized_transport_is_rejected(monkeypatch):
    monkeypatch.setattr("cain.llm.urlopen", lambda *args, **kwargs: io.BytesIO(b"x" * (4 * 1024 * 1024 + 2)))
    with pytest.raises(LLMError, match="4 MiB"):
        OllamaLLM().generate("test")


def test_generation_redirect_is_not_followed():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    redirected = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(302)
            self.send_header("Location", "/unapproved")
            self.end_headers()
        def do_GET(self):
            redirected.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"response":"redirected","done":true}')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with pytest.raises(LLMError, match="redirecionar"):
            OllamaLLM(base_url=f"http://127.0.0.1:{server.server_port}").generate("test")
        assert redirected == []
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)

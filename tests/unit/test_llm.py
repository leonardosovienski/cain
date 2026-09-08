import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from cain.llm import FakeLLM, LLM, LLMError, OllamaLLM


def test_fake_is_deterministic_and_clearly_marked():
    fake = FakeLLM()
    assert isinstance(fake, LLM)
    assert fake.generate("resuma", "persona A") == fake.generate("resuma", "persona A")
    assert fake.generate("resuma", "persona A") != fake.generate("resuma", "persona B")
    assert "SIMULAÇÃO FakeLLM" in fake.generate("texto")


@pytest.fixture
def ollama_stub():
    """Real local HTTP transport; explicitly not a real Ollama/model quality test."""
    calls = []
    configuration = {"status": 200, "body": {"response": "resposta local", "done": True}}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(configuration["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(configuration["body"]).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", calls, configuration
    server.shutdown()
    server.server_close()
    worker.join(timeout=2)


def test_ollama_http_contract(ollama_stub):
    url, calls, _ = ollama_stub
    llm = OllamaLLM(model="fixture-model", base_url=url, temperature=0.25, seed=73)
    assert llm.generate("pedido", "perfil") == "resposta local"
    path, body = calls[0]
    assert path == "/api/generate"
    assert body == {"model": "fixture-model", "prompt": "pedido", "system": "perfil",
                    "stream": False, "options": {"temperature": 0.25, "seed": 73,
                                                  "num_ctx": 8192, "num_predict": 768}}


def test_oversized_context_fails_before_transport_and_is_not_silently_truncated(ollama_stub):
    url, calls, _ = ollama_stub
    with pytest.raises(LLMError, match="limite configurado"):
        OllamaLLM(base_url=url, max_input_bytes=100).generate("texto", "memória " * 100)
    assert calls == []


@pytest.mark.parametrize("status,body", [(503, {"error": "offline"}), (200, {}),
                                        (200, {"response": "partial", "done": False})])
def test_ollama_fails_without_retry_or_fake_fallback(ollama_stub, status, body):
    url, calls, config = ollama_stub
    config.update(status=status, body=body)
    with pytest.raises(LLMError):
        OllamaLLM(base_url=url).generate("pedido")
    assert len(calls) == 1

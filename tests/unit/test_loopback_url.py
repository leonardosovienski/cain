"""Loopback detection shared by doctor, the Ollama transport and the streaming guard.

Protected behaviour: any address in 127.0.0.0/8, ``::1`` and the name ``localhost`` are
local; everything else (private ranges, link-local, public names, look-alike names) is
not. The same predicate drives the environment-proxy bypass in ``cain.llm.urlopen`` and
``require_local`` in streaming, so 127.0.0.2 behaves like 127.0.0.1 in all three places.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from cain.llm import OllamaLLM, LLMError
from cain.llm.streaming import require_local
from cain.settings import is_loopback_url

LOOPBACK = ["http://127.0.0.1:11434", "http://127.0.0.2:11434", "http://127.255.255.255/",
            "http://[::1]:11434", "http://localhost:11434", "http://LOCALHOST/", "https://127.0.0.1"]
NOT_LOOPBACK = ["http://10.0.0.1:11434", "http://192.168.1.10/", "http://169.254.169.254/",
                "http://0.0.0.0:11434", "http://example.com/", "http://127.0.0.1.evil/",
                "http://[::2]/", "http://ollama.lan:11434", "not a url", ""]


@pytest.mark.parametrize("url", LOOPBACK)
def test_loopback_addresses_and_localhost_are_local(url):
    assert is_loopback_url(url) is True


@pytest.mark.parametrize("url", NOT_LOOPBACK)
def test_everything_else_is_not_local(url):
    assert is_loopback_url(url) is False


@pytest.mark.parametrize("url", ["http://127.0.0.2:11434", "http://[::1]:11434", "http://localhost:11434"])
def test_require_local_accepts_the_whole_loopback_block(url):
    require_local(type("P", (), {"base_url": url})())


@pytest.mark.parametrize("url", ["https://127.0.0.1:11434", "http://10.0.0.1:11434",
                                 "http://user@127.0.0.1:11434", "http://127.0.0.1/?x=1"])
def test_require_local_still_rejects_non_http_remote_or_decorated_urls(url):
    with pytest.raises(ValueError, match="loopback"):
        require_local(type("P", (), {"base_url": url})())


def test_transport_bypasses_the_environment_proxy_for_any_loopback_address(monkeypatch):
    """A proxy configured in the environment must not see requests to 127.0.0.2."""
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = b'{"response":"local answer","done":true,"done_reason":"stop"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    try:
        server = ThreadingHTTPServer(("127.0.0.2", 0), Handler)
    except OSError:
        pytest.skip("127.0.0.2 not bindable on this host")
    Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")  # nothing listens here
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    try:
        llm = OllamaLLM(base_url=f"http://127.0.0.2:{server.server_port}")
        assert llm.generate("ping") == "local answer"
        remote = OllamaLLM(base_url="http://10.255.255.1:11434", timeout=1)
        with pytest.raises(LLMError):
            remote.generate("ping")  # goes to the dead proxy, fails fast
    finally:
        server.shutdown()
        server.server_close()

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
from threading import Thread

import pytest

from cain.search import (
    AutoRetriever, LocalDocumentRetriever, PublicURLRetriever, SearchError,
)


@pytest.fixture
def text_server():
    class Handler(BaseHTTPRequestHandler):
        calls = []

        def do_GET(self):
            self.calls.append(self.path)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/page")
                self.end_headers()
                return
            if self.path == "/private-redirect":
                self.send_response(302)
                self.send_header("Location", "http://localhost/secret")
                self.end_headers()
                return
            if self.path == "/error":
                self.send_response(503)
                self.end_headers()
                return
            data = (
                b"x" * 2000 if self.path == "/large" else
                b"<html><title>Evidence title</title><script>DO_NOT_INCLUDE</script>"
                b"<p>SQLite stores identities on disk.</p></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf" if self.path == "/pdf" else "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", Handler, server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_files_are_real_bounded_sources_and_not_demo_data(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    path = folder / "persistencia.md"
    path.write_text("SQLite registra a identidade e a revisão em disco.", encoding="utf-8")
    (folder / "ignored.bin").write_bytes(b"not a text source")
    provider = LocalDocumentRetriever(paths=[folder])
    result = provider.search("Busque SQLite nas fontes locais")
    assert len(result) == 1
    assert result[0].source == str(path.resolve())
    assert "revisão" in result[0].text
    assert provider.search("galaxia_INEXISTENTE") == []
    assert provider.search("Busque nas fontes locais") == []
    with pytest.raises(SearchError, match="excede"):
        LocalDocumentRetriever(paths=[folder], max_file_bytes=3)


def test_corpus_compatibility_and_passage_size():
    provider = LocalDocumentRetriever({"guia.md": "SQLite " * 1000})
    results = provider.search("SQLite", k=2)
    assert len(results) == 2
    assert all(len(result.text) <= 1500 for result in results)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://[::1]/", "http://169.254.169.254/latest/meta-data/",
    "http://10.1.2.3/", "http://192.168.1.1/", "https://user:password@example.com/",
])
def test_private_or_credential_urls_are_rejected(url):
    with pytest.raises(SearchError):
        PublicURLRetriever().search(url)


def test_http_fixture_with_explicit_private_test_opt_in(text_server):
    base, handler, _ = text_server
    provider = PublicURLRetriever(allow_private_for_testing=True)
    result = provider.search(f"Consulte {base}/redirect")[0]
    assert result.source == base + "/page"
    assert result.title == "Evidence title"
    assert "SQLite" in result.text
    assert "DO_NOT_INCLUDE" not in result.text
    assert handler.calls == ["/redirect", "/page"]


def test_http_errors_size_and_nontext_are_explicit_without_retry(text_server):
    base, handler, _ = text_server
    provider = PublicURLRetriever(max_bytes=500, allow_private_for_testing=True)
    for path, error in [("/error", "503"), ("/large", "limite"), ("/pdf", "não textual")]:
        with pytest.raises(SearchError, match=error):
            provider.search(base + path)
    assert handler.calls == ["/error", "/large", "/pdf"]


def test_web_destination_is_pinned_and_redirect_is_revalidated(text_server, monkeypatch):
    _, handler, server = text_server
    original_connect = socket.create_connection
    looked_up, connected = [], []

    def resolve(host, port, **kwargs):
        looked_up.append(host)
        address = "127.0.0.1" if host == "localhost" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port))]

    def connect(address, timeout, source_address=None):
        connected.append(address)
        # Fixture transport, while recording the address the production code approved.
        monkeypatch.setattr(socket, "getaddrinfo", original_resolve)
        try:
            return original_connect(("127.0.0.1", server.server_port), timeout, source_address)
        finally:
            monkeypatch.setattr(socket, "getaddrinfo", resolve)

    original_resolve = socket.getaddrinfo
    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(SearchError, match="bloqueados"):
        PublicURLRetriever().search("http://public.test/private-redirect")
    assert connected == [("93.184.216.34", 80)]
    assert looked_up == ["public.test", "localhost"]
    assert handler.calls == ["/private-redirect"]


def test_auto_retriever_never_turns_a_web_failure_into_local_result():
    local = LocalDocumentRetriever({"doc": "falha example.com"})
    provider = AutoRetriever(local)
    with pytest.raises(SearchError, match="desativada"):
        provider.search("Consulte https://example.com")
    assert provider.search("falha")[0].source == "doc"

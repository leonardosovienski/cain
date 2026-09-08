"""Bounded local retrieval and explicit public-URL reads; no crawling or hidden fallback."""

from dataclasses import dataclass
from html.parser import HTMLParser
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
from time import monotonic
from typing import Iterable, Protocol, runtime_checkable
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from cain.common.text import tokens


class SearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchResult:
    source: str
    title: str
    text: str
    score: float = 0.0


@runtime_checkable
class SearchProvider(Protocol):
    def search(self, query: str, k: int = 3) -> list[SearchResult]: ...


STOP_WORDS = tokens(
    "a o as os um uma uns umas e de da do das dos em no na nos nas para por com "
    "que qual quais como sobre eu voce me ao aos favor busque busca buscar pesquise "
    "pesquisa pesquisar encontre procurar procure consulte consultar quero gostaria "
    "pode poderia local corpus fonte fontes documentacao documentos"
)


class LocalDocumentRetriever:
    """Snapshot of explicit UTF-8 text/Markdown sources, split into bounded passages."""

    EXTENSIONS = {".md", ".txt", ".rst"}

    def __init__(
        self, corpus: dict[str, str] | None = None, paths: Iterable[str | Path] = (),
        max_file_bytes: int = 262144, max_files: int = 200,
    ):
        if max_file_bytes < 1 or max_files < 1:
            raise ValueError("Retrieval limits must be positive")
        self.documents = dict(corpus or {})
        files: set[Path] = set()
        for supplied in paths:
            root = Path(supplied).resolve(strict=True)
            candidates = root.rglob("*") if root.is_dir() else (root,)
            for candidate in candidates:
                if candidate.is_file() and candidate.suffix.lower() in self.EXTENSIONS:
                    # Do not import symlink targets outside an explicitly supplied directory.
                    resolved = candidate.resolve(strict=True)
                    if root.is_dir() and not resolved.is_relative_to(root):
                        raise SearchError(f"Fonte fora do diretório configurado: {candidate}")
                    files.add(resolved)
                    if len(files) > max_files:
                        raise SearchError(f"Fontes excedem o limite configurado de {max_files} arquivos")
            if root.is_file() and root.suffix.lower() not in self.EXTENSIONS:
                raise SearchError(f"Formato local não suportado: {root.suffix}; use md, txt ou rst")
        for path in sorted(files):
            if path.stat().st_size > max_file_bytes:
                raise SearchError(f"Fonte excede {max_file_bytes} bytes: {path}")
            try:
                self.documents[str(path)] = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                raise SearchError(f"Não foi possível ler a fonte UTF-8: {path}: {exc}") from exc
        self._passages: list[SearchResult] = []
        for source, text in sorted(self.documents.items()):
            if not isinstance(source, str) or not isinstance(text, str):
                raise ValueError("Corpus must map source strings to text strings")
            if not text.strip():
                continue
            for start in range(0, len(text), 1200):
                passage = text[start:start + 1500]
                self._passages.append(SearchResult(source, Path(source).name, passage))

    def search(self, query: str, k: int = 3) -> list[SearchResult]:
        if k < 1:
            return []
        terms = tokens(query) - STOP_WORDS
        if not terms:
            return []
        scored = []
        for passage in self._passages:
            overlap = len(terms & tokens(passage.text + " " + passage.title))
            if overlap:
                score = overlap / len(terms)
                scored.append(SearchResult(passage.source, passage.title, passage.text, score))
        return sorted(scored, key=lambda item: (-item.score, item.source, item.text))[:k]


def explicit_urls(query: str) -> list[str]:
    """Read URLs the caller supplied; do not discover/follow links from documents."""
    found = re.findall(r"https?://[^\s<>\"`]+", query, flags=re.IGNORECASE)
    return list(dict.fromkeys(value.rstrip(".,;!?)']}") for value in found))


class _ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.hidden = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "li", "br", "h1", "h2", "h3"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.in_title:
                self.title_parts.append(data)


class PublicURLRetriever:
    """GET explicit public HTTP(S) URLs with pinned validated DNS and bounded redirects.

    No cookies, credentials, proxies, scripts, linked resources, or automatic retry.
    allow_private_for_testing is deliberately opt-in and never set by the runtime.
    """

    def __init__(
        self, timeout: float = 15.0, max_bytes: int = 262144, max_redirects: int = 2,
        *, allow_private_for_testing: bool = False,
    ):
        if timeout <= 0 or max_bytes < 1 or max_redirects < 0:
            raise ValueError("HTTP retrieval limits must be positive")
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.allow_private_for_testing = allow_private_for_testing

    def _destination(self, url: str) -> tuple[str, str, int, str, str]:
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                raise ValueError("use URL HTTP(S) pública")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("URLs com credenciais não são permitidas")
            if any(ord(char) < 32 for char in url):
                raise ValueError("URL contém caracteres de controle")
            host = parsed.hostname.encode("idna").decode("ascii")
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
            if not self.allow_private_for_testing and port not in {80, 443}:
                raise ValueError("somente portas públicas padrão 80/443")
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ips = list(dict.fromkeys(item[4][0] for item in addresses))
            if not ips:
                raise ValueError("DNS não retornou endereço")
            if not self.allow_private_for_testing:
                for address in ips:
                    parsed_ip = ipaddress.ip_address(address)
                    if not parsed_ip.is_global:
                        raise ValueError("destinos locais, privados e reservados são bloqueados")
            path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
            path += ("?" + quote(parsed.query, safe="%=&?/:@!$'()*+,;~-._")) if parsed.query else ""
            clean_url = urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path, parsed.query, ""))
            return clean_url, host, port, path, ips[0]
        except (ValueError, OSError, UnicodeError) as exc:
            raise SearchError(f"URL não permitida ou DNS indisponível: {exc}") from exc

    def _fetch(self, url: str) -> SearchResult:
        deadline = monotonic() + self.timeout
        for redirect_count in range(self.max_redirects + 1):
            clean_url, host, port, path, pinned_ip = self._destination(url)
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SearchError("Tempo total de leitura da URL excedido")
            connection_type = (
                http.client.HTTPSConnection if clean_url.startswith("https:")
                else http.client.HTTPConnection
            )
            kwargs = {"timeout": remaining}
            if connection_type is http.client.HTTPSConnection:
                kwargs["context"] = ssl.create_default_context()
            connection = connection_type(host, port, **kwargs)
            # TLS still verifies the original hostname; only the socket destination is pinned.
            connection._create_connection = lambda address, timeout, source_address=None: (
                socket.create_connection((pinned_ip, port), timeout, source_address)
            )
            try:
                connection.request("GET", path, headers={
                    "User-Agent": "CainResearch/0.2 (+explicit-public-url-reader)",
                    "Accept": "text/html, text/plain, text/markdown, application/json",
                    "Accept-Encoding": "identity", "Connection": "close",
                })
                active_socket = connection.sock
                response = connection.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    target = response.getheader("Location")
                    if not target or redirect_count == self.max_redirects:
                        raise SearchError("Redirecionamento ausente ou limite excedido")
                    url = urljoin(clean_url, target)
                    continue
                if response.status != 200:
                    raise SearchError(f"Fonte retornou HTTP {response.status}: {clean_url}")
                content_type = response.getheader("Content-Type", "").split(";", 1)[0].lower()
                if not (content_type.startswith("text/") or content_type in {
                    "application/json", "application/xhtml+xml",
                }):
                    raise SearchError(f"Conteúdo não textual não suportado: {content_type or 'ausente'}")
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise SearchError("Fonte retornou codificação comprimida não suportada")
                length = response.getheader("Content-Length")
                if length is not None and int(length) > self.max_bytes:
                    raise SearchError(f"Fonte excede o limite de {self.max_bytes} bytes")
                body = bytearray()
                while True:
                    if response.isclosed():
                        break
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise SearchError("Tempo total de leitura da URL excedido")
                    if active_socket is not None:
                        active_socket.settimeout(remaining)
                    chunk = response.read1(min(8192, self.max_bytes + 1 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > self.max_bytes:
                        raise SearchError(f"Fonte excede o limite de {self.max_bytes} bytes")
                charset = response.headers.get_content_charset() or "utf-8"
                text = body.decode(charset, errors="replace")
                title = host
                if content_type in {"text/html", "application/xhtml+xml"}:
                    parser = _ReadableHTML()
                    parser.feed(text)
                    text = re.sub(r"[ \t]+", " ", "".join(parser.parts)).strip()
                    title = " ".join(parser.title_parts).strip() or host
                elif content_type == "application/json":
                    # Validation avoids treating malformed API error payloads as useful evidence.
                    json.loads(text)
                if not text.strip():
                    raise SearchError("Fonte não apresentou texto legível")
                return SearchResult(clean_url, title[:300], text, 1.0)
            except SearchError:
                raise
            except (OSError, ValueError, LookupError, http.client.HTTPException) as exc:
                raise SearchError(f"Falha ao ler URL, sem retry: {exc}") from exc
            finally:
                connection.close()
        raise SearchError("Limite de redirecionamentos excedido")

    def search(self, query: str, k: int = 3) -> list[SearchResult]:
        urls = explicit_urls(query)
        if not urls:
            raise SearchError("Leitura web requer uma URL pública explícita no pedido")
        if len(urls) > k:
            raise SearchError(f"Forneça no máximo {k} URLs por pedido")
        return [self._fetch(url) for url in urls]


class AutoRetriever:
    """Choose the configured source explicitly; a failed web read never becomes local search."""

    def __init__(self, local: SearchProvider, web: SearchProvider | None = None):
        self.local = local
        self.web = web

    def search(self, query: str, k: int = 3) -> list[SearchResult]:
        if explicit_urls(query):
            if self.web is None:
                raise SearchError("Leitura de URLs está desativada nesta configuração")
            return self.web.search(query, k)
        return self.local.search(query, k)

from hashlib import sha256

import pytest

from cain.agents import SearchAgent
from cain.common import Message
from cain.persistence.adapters import LexicalMemoryIndex
from cain.search import HybridDocumentRetriever, LocalDocumentRetriever, SearchError, SearchResult


class Vectors:
    model = "injected-test-vectors"
    model_digest = "fixture-v1"

    def __init__(self, mapping):
        self.mapping, self.calls = mapping, []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [self.mapping[text] for text in texts]


def test_paraphrase_without_lexical_overlap_is_retrieved_by_semantics():
    corpus = {"a.md": "A carga elétrica circula no condutor.",
              "b.md": "Registros duráveis preservam configurações pessoais."}
    query = "Lembrar hábitos anteriores"
    provider = Vectors({query: [1, 0], corpus["a.md"]: [0, 1], corpus["b.md"]: [1, 0]})
    assert LocalDocumentRetriever(corpus).search(query) == []
    results = HybridDocumentRetriever(corpus, embedding=provider, query_instruction="").search(query)
    assert [item.source for item in results] == ["b.md"]
    assert results[0].metadata["lexical_score"] == 0
    assert results[0].metadata["semantic_score"] == 1


def test_exact_error_identifier_wins_over_semantic_neighbor_and_ties_are_stable():
    corpus = {"z.md": "ERR-401 indica token expirado.", "a.md": "ERR-4012 indica uma credencial inválida."}
    query = "ERR-401"
    provider = Vectors({query: [1, 0], corpus["z.md"]: [0, 1], corpus["a.md"]: [1, 0]})
    search = HybridDocumentRetriever(corpus, embedding=provider, query_instruction="")
    results = search.search(query)
    assert results[0].source == "z.md"
    assert results[0].score < results[1].score  # exact identifiers are an explicit ranking priority
    assert results[0].metadata["exact_identifier_matches"] == 1
    tied = {"z.md": "same", "a.md": "same"}
    tie_search = HybridDocumentRetriever(tied, embedding=Vectors({"query": [1, 0], "same": [1, 0]}), query_instruction="")
    assert [item.source for item in tie_search.search("query")] == ["a.md", "z.md"]


def test_file_edit_refreshes_hash_and_embeddings_while_reusing_unchanged_query(tmp_path):
    path = tmp_path / "configured.md"
    path.write_bytes(b"\xef\xbb\xbfantigo\r\n")
    provider = Vectors({"query": [1, 0], "antigo\r\n": [1, 0], "novo\r\n": [1, 0]})
    search = HybridDocumentRetriever(paths=[path], embedding=provider, cache_path=tmp_path / "derived.db",
                                     query_instruction="")
    original = search.search("query")[0]
    assert original.document_hash == sha256(path.read_bytes()).hexdigest()
    assert original.text == "antigo\r\n"
    assert original.start_offset == 0 and original.end_offset == len(original.text)
    path.write_bytes(b"\xef\xbb\xbfnovo\r\n")
    changed = search.search("query")[0]
    assert changed.document_hash != original.document_hash
    assert changed.chunk_id != original.chunk_id
    assert changed.text == "novo\r\n"
    assert provider.calls == [["query", "antigo\r\n"], ["novo\r\n"]]
    assert original.text == "antigo\r\n"  # old evidence remains a reproducible snapshot


def test_only_configured_files_are_read_and_limits_fail_before_embedding(tmp_path):
    allowed, private = tmp_path / "allowed.md", tmp_path / "private.md"
    allowed.write_text("allowed", encoding="utf-8")
    private.write_text("PRIVATE_UNCONFIGURED", encoding="utf-8")
    provider = Vectors({"query": [1, 0], "allowed": [1, 0]})
    search = HybridDocumentRetriever(paths=[allowed], embedding=provider, query_instruction="", max_query_chars=8)
    assert search.search("query")[0].source == str(allowed.resolve())
    assert all("PRIVATE_UNCONFIGURED" not in text for call in provider.calls for text in call)
    with pytest.raises(SearchError, match="Consulta excede"):
        search.search("too long query")
    with pytest.raises(SearchError, match="bytes"):
        HybridDocumentRetriever(paths=[allowed], embedding=provider, max_file_bytes=3)
    with pytest.raises(SearchError, match="trechos"):
        HybridDocumentRetriever({"long": "a" * 2500}, embedding=provider, max_chunks=2)
    assert len(provider.calls) == 1


def test_embedding_failure_never_falls_back_to_lexical():
    class Offline(Vectors):
        def embed(self, texts):
            raise ConnectionError("offline")

    corpus = {"guide": "SQLite"}
    assert LocalDocumentRetriever(corpus).search("SQLite")
    hybrid = HybridDocumentRetriever(corpus, embedding=Offline({}))
    with pytest.raises(SearchError, match="não usou fallback lexical"):
        hybrid.search("SQLite")


@pytest.mark.parametrize("project,expected", [("A", ["projectA"]), ("B", ["projectB"]), (None, ["legacy", "global"])])
def test_search_history_is_scoped_by_user_and_project(project, expected):
    memory = LexicalMemoryIndex()
    memory.index("legacy", "SQLite legacy", {"user_id": "alice"})
    memory.index("global", "SQLite global", {"user_id": "alice", "project_id": None})
    memory.index("projectA", "SQLite projectA", {"user_id": "alice", "project_id": "A"})
    memory.index("projectB", "SQLite projectB", {"user_id": "alice", "project_id": "B"})
    memory.index("other", "SQLite OTHER_USER", {"user_id": "bob", "project_id": project})
    memory.index("current", "SQLite CURRENT_INPUT", {"user_id": "alice", "project_id": project, "decision_id": "now"})
    memory.index("preference", "SQLite prefiro respostas longas", {
        "user_id": "alice", "project_id": project, "preference_keys": ["verbosity"],
    })
    message = Message("busca", "", "SQLite", {"user_id": "alice", "project_id": project, "decision_id": "now"})
    SearchAgent(memory).handle(message)
    sources = {item["source"] for item in message.metadata["retrieval_sources"]}
    assert sources == {"memória:" + doc_id for doc_id in expected}


def test_evidence_metadata_contains_exact_clipped_text_hashes_and_offsets(tmp_path):
    source = tmp_path / "guide.md"
    text = "SQLite persiste. " * 250
    source.write_bytes(text.encode("utf-8"))
    retriever = LocalDocumentRetriever(paths=[source])
    message = Message("busca", "", "SQLite", {"user_id": "alice", "project_id": "A"})
    response = SearchAgent(LexicalMemoryIndex(), retriever=retriever).handle(message)
    evidence = message.metadata["retrieval_sources"]
    assert len(evidence) == 3
    assert sum(len(item["text"]) for item in evidence) == 2400
    for item in evidence:
        assert item["source"] == str(source.resolve())
        assert item["document_hash"] == sha256(source.read_bytes()).hexdigest()
        assert item["text"] == item["excerpt"] == text[item["start_offset"]:item["end_offset"]]
        assert item["excerpt_hash"] == sha256(item["text"].encode()).hexdigest()
        assert item["excerpt_truncated"] is True
        assert item["chunk_id"]
        assert "[" + item["citation"] + "]" in response
    saved_excerpt = evidence[0]["text"]
    source.write_text("new version", encoding="utf-8")
    assert evidence[0]["text"] == saved_excerpt


def test_search_result_legacy_constructor_remains_supported():
    legacy = SearchResult("source", "title", "text", 0.5)
    assert legacy.score == 0.5 and legacy.document_hash == ""

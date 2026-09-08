"""Byte-bound synthesis with recorded doubles only; no model or HTTP calls."""

from hashlib import sha256
import json

import pytest

from cain.agents import SearchAgent
from cain.common import Message
from cain.persistence.adapters import LexicalMemoryIndex
from cain.search import SearchError, SearchResult


class RecordingLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, context=""):
        self.calls.append((prompt, context))
        return "Síntese dos trechos fornecidos."


class BudgetLLM(RecordingLLM):
    def __init__(self, *, max_input_bytes=6500, num_ctx=8192, num_predict=768):
        super().__init__()
        self.max_input_bytes = max_input_bytes
        self.num_ctx = num_ctx
        self.num_predict = num_predict


class Retriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, query, k=3):
        self.calls.append((query, k))
        return list(self.results)


def passage(text, index=0, *, source=None, title=None):
    prefix = "Início fora do trecho. "
    document = prefix + text + " Fim fora do trecho."
    return SearchResult(
        source or f"guia-{index}.md", title or f"Guia {index}", text, 0.9,
        chunk_id=f"chunk-{index}", document_hash=sha256(document.encode()).hexdigest(),
        start_offset=len(prefix), end_offset=len(prefix) + len(text),
        metadata={"offset_unit": "unicode_codepoints", "document_hash_basis": "utf8_text"},
    )


def run_search(llm, results, *, question="Como guardar configurações?", identity="Perfil íntegro."):
    message = Message("busca", identity, question, {"user_id": "alice", "project_id": "test"})
    retriever = Retriever(results)
    response = SearchAgent(LexicalMemoryIndex(), retriever=retriever, llm=llm).handle(message)
    return message, response


def assert_recorded_budget(llm, message):
    assert len(llm.calls) == 1
    prompt, context = llm.calls[0]
    assert prompt == message.payload
    assert context.startswith(message.contexto_identidade + SearchAgent.SYNTHESIS_INSTRUCTIONS)
    serialized = context.split("EVIDÊNCIAS (JSON):\n", 1)[1]
    budget = message.metadata["retrieval_budget"]
    actual_bytes = len((prompt + context).encode("utf-8"))
    assert actual_bytes == budget["total_input_bytes"] <= budget["input_byte_budget"]
    assert budget["serialized_evidence_bytes"] == len(serialized.encode("utf-8"))
    assert budget["available_evidence_bytes"] == budget["input_byte_budget"] - budget["fixed_input_bytes"]
    return json.loads(serialized)


@pytest.mark.parametrize("num_ctx,expected_budget", [(8192, 6500), (4096, 3072)])
def test_unicode_evidence_fits_bytes_and_context_reserve_without_changing_user_input(num_ctx, expected_budget):
    llm = BudgetLLM(num_ctx=num_ctx)
    identity = json.dumps({"preferences": {"language": "pt"}, "goal": "ação 😀 " * 90}, ensure_ascii=False)
    question = 'Como guardar "preferências"? Inclua configuração e persistência.'
    results = [passage("😀" * 3000, index) for index in range(3)]
    message, _ = run_search(llm, results, question=question, identity=identity)
    model_items = assert_recorded_budget(llm, message)
    assert message.payload == question and message.contexto_identidade == identity
    budget = message.metadata["retrieval_budget"]
    assert budget["input_byte_budget"] == expected_budget
    assert budget["included_text_chars"] < 2400
    assert budget["evidence_truncated"] is True
    assert all(item["excerpt_truncated"] for item in model_items)


def test_json_escaping_and_long_labels_preserve_reproducible_excerpts():
    llm = BudgetLLM(max_input_bytes=3000)
    results = [passage(
        ('Ação\x00"\\\n😀 ' * 500), index,
        source=f'arquivo-{index}/' + ('😀"\\' * 200),
        title=f'Título {index} ' + ('ação\x00"' * 200),
    ) for index in range(3)]
    message, response = run_search(llm, results)
    model_items = assert_recorded_budget(llm, message)
    sources = message.metadata["retrieval_sources"]
    for original, source, model in zip(results, sources, model_items):
        assert source["source"] == original.source and source["title"] == original.title
        assert original.source.startswith(model["source"]) and original.title.startswith(model["title"])
        assert source["source_label_truncated"] is model["source_label_truncated"] is True
        assert source["title_label_truncated"] is model["title_label_truncated"] is True
        assert source["text"] == source["excerpt"] == model["text"]
        assert source["text"] == original.text[:source["end_offset"] - source["start_offset"]]
        assert source["start_offset"] == original.start_offset
        assert source["chunk_end_offset"] == original.end_offset
        assert source["end_offset"] < source["chunk_end_offset"]
        assert source["excerpt_hash"] == sha256(source["text"].encode("utf-8")).hexdigest()
        assert source["document_hash"] == original.document_hash
        assert source["chunk_id"] == original.chunk_id
        assert source["metadata"] == original.metadata
        assert source["excerpt_truncated"] is True
        assert f"[{source['citation']}]" in response
    assert message.metadata["retrieval_budget"]["serialized_evidence_bytes"] > sum(
        len(item["text"].encode("utf-8")) for item in model_items
    )


def test_tight_budget_omits_lower_ranked_sources_and_records_exact_counts():
    question, identity = "Pergunta", "Perfil"
    fixed_bytes = len((question + identity + SearchAgent.SYNTHESIS_INSTRUCTIONS).encode("utf-8"))
    llm = BudgetLLM(max_input_bytes=fixed_bytes + 220)
    results = [passage("Fato " * 200, index) for index in range(3)]
    message, response = run_search(llm, results, question=question, identity=identity)
    model_items = assert_recorded_budget(llm, message)
    budget = message.metadata["retrieval_budget"]
    assert budget["candidate_count"] == 3
    assert budget["included_count"] == len(model_items) == 1
    assert budget["omitted_count"] == 2
    assert budget["evidence_truncated"] is True
    assert message.metadata["retrieval_sources"][0]["source"] == "guia-0.md"
    assert "[S1]" in response and "[S2]" not in response and "guia-1.md" not in response


@pytest.mark.parametrize("question,identity", [("Pedido 😀 " * 1000, "Perfil"), ("Pedido", "Perfil 😀 " * 1000)])
def test_oversized_fixed_input_fails_before_retrieval_or_generation(question, identity):
    llm = BudgetLLM()
    retriever = Retriever([passage("Fato")])
    message = Message("busca", identity, question, {"user_id": "alice"})
    with pytest.raises(SearchError, match="nenhuma busca ou geração foi iniciada"):
        SearchAgent(LexicalMemoryIndex(), retriever=retriever, llm=llm).handle(message)
    assert retriever.calls == llm.calls == []
    assert message.payload == question and message.contexto_identidade == identity
    assert message.metadata["retrieval_sources"] == []


def test_budget_too_small_for_one_textual_source_fails_without_generation():
    question, identity = "Pedido", "Perfil"
    fixed_bytes = len((question + identity + SearchAgent.SYNTHESIS_INSTRUCTIONS).encode("utf-8"))
    llm = BudgetLLM(max_input_bytes=fixed_bytes + 30)
    with pytest.raises(SearchError, match="não comporta evidência textual"):
        run_search(llm, [passage("Fato")], question=question, identity=identity)
    assert llm.calls == []


def test_short_normal_evidence_is_preserved_and_not_marked_truncated():
    llm = BudgetLLM()
    results = [passage("SQLite guarda configurações."), passage("O perfil usa JSON.", 1)]
    message, _ = run_search(llm, results)
    model_items = assert_recorded_budget(llm, message)
    assert [item["text"] for item in model_items] == [item.text for item in results]
    budget = message.metadata["retrieval_budget"]
    assert budget["omitted_count"] == 0 and budget["evidence_truncated"] is False
    assert all(item["excerpt_truncated"] is False for item in model_items)


def test_provider_without_budget_attributes_preserves_legacy_character_allowance():
    llm = RecordingLLM()
    message, _ = run_search(llm, [passage("😀" * 4000)])
    serialized = llm.calls[0][1].split("EVIDÊNCIAS (JSON):\n", 1)[1]
    model_items = json.loads(serialized)
    assert len(model_items[0]["text"]) == 2400
    assert message.metadata["retrieval_budget"]["input_byte_budget"] is None
    assert message.metadata["retrieval_budget"]["available_evidence_bytes"] is None
    assert message.metadata["retrieval_budget"]["included_text_chars"] == 2400

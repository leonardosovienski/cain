"""Composition root: the only module that selects concrete persistence providers."""

from pathlib import Path

from cain.agents import AgentRegistry, CodeAgent, SearchAgent, SummaryAgent
from cain.identity import IdentityService
from cain.llm import FakeLLM, LLM
from cain.orchestrator import Cain
from cain.persistence.adapters import LexicalMemoryIndex, SQLiteDecisionLog, SQLiteIdentityStore


DEMO_CORPUS = {
    "cain-arquitetura-demo": (
        "Cain separa identidade, orquestração e agentes. IdentityStore guarda o estado "
        "autoritativo. MemoryIndex é derivado e reconstruível. DecisionLog registra "
        "decisões imutáveis. O protótipo usa Python, SQLite e uma interface de LLM."
    )
}


class _LazyRetriever:
    """A request may use code/profile agents without opening search dependencies."""

    def __init__(self, factory):
        self.factory, self.provider = factory, None

    def search(self, query, k=3):
        if self.provider is None:
            self.provider = self.factory()
        return self.provider.search(query, k)


def build_retriever(*, corpus=None, paths=(), search_mode="lexical", embedding=None,
                    cache_path=None, allow_public_urls=False):
    from cain.search import AutoRetriever, LocalDocumentRetriever, HybridDocumentRetriever, PublicURLRetriever
    if search_mode == "hybrid":
        if embedding is None:
            raise ValueError("Busca híbrida exige um provedor de embeddings configurado")
        local = HybridDocumentRetriever(corpus=corpus, paths=paths, embedding=embedding,
                                         cache_path=cache_path)
    elif search_mode == "lexical":
        local = LocalDocumentRetriever(corpus=corpus, paths=paths)
    else:
        raise ValueError("search_mode deve ser lexical ou hybrid")
    return AutoRetriever(local, PublicURLRetriever() if allow_public_urls else None)


def build_cain(
    db_path: str | Path, llm: LLM | None = None,
    corpus: dict[str, str] | None = None,
    *, source_paths: list[str | Path] | None = None, allow_public_urls: bool = False,
    router=None,
    search_mode: str = "lexical", embedding=None, embedding_cache_path: Path | None = None,
    retrieval_factory=None,
) -> Cain:
    store = SQLiteIdentityStore(db_path)
    try:
        decision_log = SQLiteDecisionLog(db_path)
        memory = LexicalMemoryIndex()
        memory.rebuild_from(store)
        provider = llm if llm is not None else FakeLLM()
        registry = AgentRegistry()
        if retrieval_factory is not None:
            registry.register(SearchAgent(memory, retriever=_LazyRetriever(retrieval_factory), llm=provider))
        elif source_paths is not None or allow_public_urls:
            retriever = build_retriever(corpus=corpus, paths=source_paths or (),
                                        search_mode=search_mode, embedding=embedding,
                                        cache_path=embedding_cache_path, allow_public_urls=allow_public_urls)
            registry.register(SearchAgent(memory, retriever=retriever, llm=provider))
        else:
            registry.register(SearchAgent(memory, DEMO_CORPUS if corpus is None else corpus))
        registry.register(CodeAgent(provider))
        registry.register(SummaryAgent(provider))
        return Cain(IdentityService(store, memory), registry, decision_log, router=router)
    except Exception:
        store.close()
        if "decision_log" in locals():
            decision_log.close()
        raise

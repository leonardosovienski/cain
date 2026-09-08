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


def build_cain(
    db_path: str | Path, llm: LLM | None = None,
    corpus: dict[str, str] | None = None,
) -> Cain:
    store = SQLiteIdentityStore(db_path)
    try:
        decision_log = SQLiteDecisionLog(db_path)
        memory = LexicalMemoryIndex()
        memory.rebuild_from(store)
        provider = llm if llm is not None else FakeLLM()
        registry = AgentRegistry()
        registry.register(SearchAgent(memory, DEMO_CORPUS if corpus is None else corpus))
        registry.register(CodeAgent(provider))
        registry.register(SummaryAgent(provider))
        return Cain(IdentityService(store, memory), registry, decision_log)
    except Exception:
        store.close()
        if "decision_log" in locals():
            decision_log.close()
        raise

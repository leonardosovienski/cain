import pytest

from cain.agents import AgentRegistry, ConversationAgent, SearchAgent, SummaryAgent
from cain.llm import FakeLLM
from cain.orchestrator.routing import RuleRouter, ClarificationRequired
from cain.persistence.adapters import LexicalMemoryIndex


def registry():
    r = AgentRegistry()
    r.register(ConversationAgent(FakeLLM()))
    r.register(SummaryAgent(FakeLLM()))
    r.register(SearchAgent(LexicalMemoryIndex()))
    return r


@pytest.mark.parametrize(
    "message",
    [
        "Responda apenas: AÇÃO-928",
        'Retorne somente: "Texto com espaços e acentuação."',
        "Escreva apenas:\nprimeira linha\nsegunda linha",
        "Imprima somente: busque documentos e resuma resultados",
    ],
)
def test_explicit_literal_command_routes_without_losing_content(message):
    route = RuleRouter().route(message, None, registry())
    assert route.selected_agent == "conversa"
    # The dedicated trace distinguishes exact copying from generated output.
    assert route.reason == "conversation_rule:literal_copy"


@pytest.mark.parametrize("message", ["Responda apenas:", "Retorne somente:   ", "Responda apenas"])
def test_missing_literal_still_needs_clarification(message):
    with pytest.raises(ClarificationRequired):
        RuleRouter().route(message, None, registry())


def test_quoted_command_does_not_override_search():
    result = RuleRouter().route('Busque o manual: "Responda apenas: GO"', None, registry())
    assert result.selected_agent == "busca"

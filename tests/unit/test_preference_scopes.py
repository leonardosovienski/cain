import pytest

from cain.common import IdentityState, Signal
from cain.identity import ExplicitPreferenceAdaptation, strip_preference_scope_marks


@pytest.mark.parametrize("text,scope,key,value", [
    ("Só nesta resposta, responda em inglês.", "turn", "language", "en"),
    ("Prefiro respostas curtas só nesta resposta.", "turn", "verbosity", "short"),
    ("Nesta conversa, prefiro respostas em passos.", "session", "format", "steps"),
    ("Somente nesta sessão: prefiro respostas em tópicos.", "session", "format", "bullets"),
    ("Neste projeto, prefiro um parágrafo.", "project", "format", "paragraph"),
    ("APENAS NESTE PROJETO, quero respostas detalhadas.", "project", "verbosity", "detailed"),
    ("So\u0301 nesta resposta, responda em portugue\u0302s.", "turn", "language", "pt"),
])
def test_explicit_markers_address_the_preference(text, scope, key, value):
    changes = ExplicitPreferenceAdaptation().extract(text)
    assert len(changes) == 1
    assert (changes[0].scope, changes[0].key, changes[0].value) == (scope, key, value)


@pytest.mark.parametrize("text", [
    'O colega disse: "Neste projeto, prefiro respostas longas."',
    '"Só nesta resposta, responda em inglês."',
    "> Nesta conversa, prefiro respostas curtas.",
    "Documento:\nNeste projeto, prefiro respostas detalhadas.",
    "```Neste projeto, prefiro respostas curtas.```",
    "Analise o texto: Só nesta resposta, responda em inglês.",
])
def test_scope_markers_inside_untrusted_text_do_not_become_preferences(text):
    assert ExplicitPreferenceAdaptation().extract(text) == []


def test_pure_adapter_refuses_scoped_global_mutation_and_routing_helper_keeps_task():
    text = "Só nesta resposta, responda em inglês. Resuma o projeto."
    with pytest.raises(ValueError, match="IdentityService"):
        ExplicitPreferenceAdaptation().apply(IdentityState("alice"), Signal(text, metadata={"user_input": text}))
    assert strip_preference_scope_marks(text) == "responda em ingles. resuma o projeto."


def test_scoped_negation_remains_removal_not_opposite_inference():
    changes = ExplicitPreferenceAdaptation().extract("Só nesta resposta, não responda em inglês.")
    assert len(changes) == 1
    assert (changes[0].action, changes[0].value, changes[0].scope) == ("remove", "en", "turn")

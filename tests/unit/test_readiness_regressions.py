import json

import pytest

from cain.agents.arithmetic import answer
from cain.orchestrator.routing import RuleRouter
from cain.runtime import build_cain


@pytest.mark.parametrize('expression,expected', [
    ('0.10000000000000001 - 0.1', '1/100000000000000000'),
    ('0.30000000000000004 - 0.3', '1/25000000000000000'),
    ('-(0.2 + 0.1)', '-3/10'),
    ('1/3 + 1/6', '1/2'),
    ('17 % 5', '2'),
])
def test_decimal_source_is_exact(expression, expected):
    assert answer('Calcule ' + expression + '.') == f'{expression} = {expected}.'


@pytest.mark.parametrize('expression', ['1/0', '10**100', '__import__("os")',
                                         '1e999999', '1e-999999', 'True + 1'])
def test_bounded_numeric_domain(expression):
    assert 'Não foi possível' in answer('Calcule ' + expression + '.')


@pytest.mark.parametrize('message', [
    'Retificação para este cenário: o estoque considerado agora é de 35 caixas.',
    'Explique com mais detalhes.',
    'Desenvolva o raciocínio anterior.',
    'Qual é o estoque atual e qual era o anterior?',
])
def test_fallback_classifier_receives_authorized_context(tmp_path, message):
    class Model:
        def generate_json(self, prompt, context, schema):
            data = json.loads(prompt)
            assert data['instruction'] == message
            assert data['session_context'] == 'Estoque anterior: 22 caixas.'
            return '{"intent":"conversa","reason":"contexto suficiente"}'

    with build_cain(tmp_path/'test.db') as runtime:
        route = RuleRouter(Model()).route(message, None, runtime.registry,
            has_session_context=True, session_context='Estoque anterior: 22 caixas.')
        assert route.intent == 'conversa'


@pytest.mark.parametrize('wanted,documents,present', [
    ('Lunar', {'cedral.txt': 'O código de Cedral é CEDRAL-615.'}, False),
    ('Cedral', {'cedral.txt': 'O código de Cedral é CEDRAL-615.'}, True),
    ('Lunar', {'lunar.txt': 'O código de Lunar é LUNAR-714.'}, True),
    ('Lunar', {'cedral.txt': 'O código de Cedral é CEDRAL-615.',
               'lunar.txt': 'O código de Lunar é LUNAR-714.'}, True),
    ('Lunar', {}, False),
    ('Safira', {'rubi.txt': 'O código de Rubi é RUBI-913.'}, False),
    ('Safira', {'safira.txt': 'O código de Safira é SAFIRA-284.'}, True),
])
@pytest.mark.parametrize('question', [
    'Qual é o código de {wanted}?',
    'Busque no documento do projeto o código do procedimento {wanted}.',
    'Pesquise o prazo da empresa {wanted}.',
])
def test_exact_entity_evidence(tmp_path, wanted, documents, present, question):
    with build_cain(tmp_path/'evidence.db', corpus=documents) as runtime:
        result = runtime.run('qa', 's', question.format(wanted=wanted))
        assert result.selected_agent == 'busca'
        if present:
            assert wanted.upper() + '-' in result.response
        else:
            assert 'Nenhuma evidência relevante' in result.response
            assert 'CEDRAL-615' not in result.response
            assert 'RUBI-913' not in result.response


@pytest.mark.parametrize('payload,expected', [
    ('Por favor, retorne somente: VELA-826.', 'VELA-826.'),
    ('Responda apenas: AÇÃO-928', 'AÇÃO-928'),
    ('Imprima somente: primeira\nsegunda!', 'primeira\nsegunda!'),
    ('Escreva apenas: "aspas".', '"aspas".'),
    ('Responda apenas: Prefiro respostas em inglês.', 'Prefiro respostas em inglês.'),
])
def test_explicit_literal_copy_without_generation(tmp_path, payload, expected):
    class NoGeneration:
        def generate(self, *args):
            raise AssertionError('Literal copying must not need generation')

        generate_json = generate

    model = NoGeneration()
    with build_cain(tmp_path/'copy.db', model, router=RuleRouter(model)) as runtime:
        result = runtime.run('qa', 's', payload)
        assert result.response == expected
        assert runtime.identity.get('qa').user_model.preferences == {}

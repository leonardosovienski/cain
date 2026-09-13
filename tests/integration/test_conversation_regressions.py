"""Everyday conversation must not return unrelated historical search excerpts."""
import pytest
from fastapi.testclient import TestClient

from cain.api import create_app
from cain.common import Signal
from cain.orchestrator import RuleRouter
from cain.runtime import build_cain


class ConversationModel:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, context=''):
        self.calls.append((prompt, context))
        return '2 + 2 = 4.'

    def generate_json(self, *args):
        raise AssertionError('Clear arithmetic/social requests do not need LLM routing')


@pytest.mark.parametrize('prompt,expected', [('Quanto é 2 + 2?', '2 + 2 = 4.'),
    ('Calcule 17 * 3.', '17 * 3 = 51.'), ('Quanto dá (12 + 8) / 4?', '(12 + 8) / 4 = 5.'),
    ('Tudo bem?', 'Estou pronto para ajudar. Como posso ajudar você?'), ('Obrigado!', 'De nada!'),
    ('Converse comigo sobre organização de tarefas.', None)])
def test_everyday_conversation_does_not_search_old_turns(tmp_path, prompt, expected):
    model = ConversationModel()
    def no_retrieval():
        raise AssertionError('Conversation must not initialize document search')
    with build_cain(tmp_path/'cain.db', model, router=RuleRouter(model),
                    retrieval_factory=no_retrieval) as runtime:
        runtime.identity.update('qa', Signal('Usuário: Busque o código. Cain: O código é JADE731.'))
        result = runtime.run('qa', 'new-session', prompt)
        assert result.selected_agent == 'conversa'
        assert result.response == (expected or '2 + 2 = 4.')
        if expected:
            assert model.calls == []
        else:
            assert len(model.calls) == 1 and model.calls[0][0] == prompt


def test_search_does_not_cite_history_on_articles_alone(tmp_path):
    with build_cain(tmp_path/'cain.db', corpus={}) as runtime:
        runtime.identity.update('qa', Signal('Usuário: Busque o código. Cain: O código é JADE731.'))
        result = runtime.run('qa', 'new-session', 'Busque a nebulosa ZXQ987.', intent='busca')
        assert 'JADE731' not in result.response
        assert 'memória:' not in result.response
        assert 'S1' not in result.response


def test_api_accepts_explicit_conversation_and_persists_it(tmp_path):
    config = tmp_path/'cain.toml'
    config.write_text('[search]\npaths=[]\n', encoding='utf-8')
    with TestClient(create_app(tmp_path/'cain.db', ConversationModel(), config)) as client:
        response = client.post('/run', json={'user_id':'qa', 'session_id':'math',
                               'payload':'Quanto é 2 + 2?', 'intent':'conversa'})
        assert response.status_code == 200, response.text
        assert response.json()['selected_agent'] == 'conversa'
        assert response.json()['sources'] == []
        saved = client.get('/sessions/qa/math').json()
        assert saved[0]['result']['response'] == '2 + 2 = 4.'


@pytest.mark.parametrize('expression,expected', [('0,1 + 0,2', '3/10'),
    ('-5 * (3 + 1)', '-20'), ('7 / 3', '7/3'), ('9 % 4', '1')])
def test_arithmetic_exact_without_float_rounding(expression, expected):
    from cain.agents.arithmetic import answer
    assert answer('Calcule '+expression).endswith(' = '+expected+'.')


@pytest.mark.parametrize('expression', ['1 / 0', '9 ** 999999', '__import__("os")',
    '1e999', '9' * 200, '(' * 1000 + '1' + ')' * 1000])
def test_arithmetic_rejects_unbounded_or_executable_input(expression):
    from cain.agents.arithmetic import answer
    assert answer('Calcule '+expression).startswith('Não foi possível')


@pytest.mark.parametrize('prompt', [
    'Vamos comparar dois planos fictícios: Cedro custa 37 e Ipê custa 24. Qual custa menos?',
    'Considere um cenário hipotético: temos três caixas. Explique como organizar.',
    'Compare duas propostas fictícias: A inclui busca, B inclui código.',
])
def test_hypothetical_exercise_reaches_conversation_without_classifier(tmp_path, prompt):
    model = ConversationModel()
    with build_cain(tmp_path/'exercise.db', model, router=RuleRouter(model)) as runtime:
        result = runtime.run('qa', 'exercise', prompt)
        assert result.selected_agent == 'conversa'
        assert list(runtime.decision_log.export(result.run_id))[0].reason == 'conversation_rule:hypothetical'
        assert model.calls[0][0] == prompt

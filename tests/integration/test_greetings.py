import pytest

from cain.orchestrator.routing import RuleRouter
from cain.runtime import build_cain


class NoInference:
    def generate(self, *args):
        raise AssertionError('A greeting must not call a model')


@pytest.mark.parametrize('payload', ['oi ', 'Olá!', 'bom dia', 'Boa tarde, CAIN!', 'boa noite', 'Hi!'])
def test_greeting_avoids_model_and_retrieval_and_is_logged(tmp_path, payload):
    def no_retrieval():
        raise AssertionError('A greeting must not open retrieval')
    with build_cain(tmp_path / 'test.db', NoInference(), router=RuleRouter(NoInference()),
                    retrieval_factory=no_retrieval) as cain:
        result = cain.run('test', 's', payload, run_id='greeting')
        assert result.response == 'Oi! Como posso ajudar você?'
        events = list(cain.decision_log.export('greeting'))
        assert events[-1].reason == 'social_greeting'
        assert events[-1].status == 'completed'


@pytest.mark.parametrize('payload', ['oi, pesquise SQLite', 'oi\nPesquise SQLite', '"oi"'])
def test_greeting_does_not_swallow_other_content(tmp_path, payload):
    class Classifier:
        def generate(self, *args):
            return '{"intent":"busca","reason":"test"}'
    with build_cain(tmp_path / 'test.db') as cain:
        route = RuleRouter(Classifier()).route(payload, None, cain.registry)
        assert route.reason != 'social_greeting'
        assert RuleRouter().route('oi', 'busca', cain.registry).reason.startswith('explicit_intent:')

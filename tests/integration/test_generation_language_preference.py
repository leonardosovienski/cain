"""Preference plumbing and budgeting; model-language quality needs real inference."""
import pytest

from cain.agents import CodeAgent, ConversationAgent, SummaryAgent, _generation_prompt
from cain.common import Message
from cain.runtime import build_cain


class Capture:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, context=''):
        self.calls.append((prompt, context))
        return 'unchanged provider response'


@pytest.mark.parametrize('agent', [CodeAgent, ConversationAgent, SummaryAgent])
@pytest.mark.parametrize('language,label', [('en', 'English'), ('pt', 'Portuguese')])
def test_agents_forward_effective_language_without_rewriting_output(agent, language, label):
    model = Capture()
    message = Message('test', 'identity', 'Original request', {'preferences': {'language': language}})
    assert agent(model).handle(message) == 'unchanged provider response'
    assert model.calls[0][0].startswith('Original request\n\nAnswer in '+label+'.')
    assert message.payload == 'Original request'


def test_no_preference_preserves_provider_prompt():
    message = Message('test', '', 'Exact original', {})
    assert _generation_prompt(message) == message.payload


@pytest.mark.parametrize('language,expected', [('en', 'Do not merely repeat'), ('pt', 'Não se limite a repetir')])
def test_followup_requests_additional_reasoning_without_changing_user_input(language, expected):
    model = Capture()
    message = Message('conversa', 'Earlier facts', 'Explique melhor.',
                      {'preferences': {'language': language}, 'route_reason': 'conversation_rule:followup'})
    assert ConversationAgent(model).handle(message) == 'unchanged provider response'
    assert expected in model.calls[0][0]
    assert message.payload == 'Explique melhor.'


def test_scoped_language_reaches_model_but_does_not_pollute_saved_request(tmp_path):
    model = Capture()
    with build_cain(tmp_path/'language.db', model) as runtime:
        runtime.identity.set_preference('qa', 'language', 'en')
        runtime.identity.set_preference('qa', 'language', 'pt', scope='session', session_id='pt')
        runtime.run('qa', 'pt', 'Original request', intent='conversa')
        runtime.run('qa', 'other', 'Original request', intent='conversa')
        assert 'Answer in Portuguese.' in model.calls[0][0]
        assert 'Answer in English.' in model.calls[1][0]
        assert 'Responda em português' not in model.calls[1][1]
        assert 'Answer in English.' in model.calls[1][1]
        history = runtime.identity.context_for('qa', 'Original request', session_id='other')
        assert 'Original request' in history
        assert 'Original request\\n\\nAnswer in' not in history

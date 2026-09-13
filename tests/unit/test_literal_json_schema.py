"""Explicit key constraints, not inferred values or post-generation rewriting."""
import pytest

from cain.agents import ConversationAgent, _literal_json_schema
from cain.common import Message


@pytest.mark.parametrize('prompt,keys', [
    ('Responda somente com um objeto JSON com as chaves literais "cidade" e "ativo". Valores abaixo.', ['cidade', 'ativo']),
    ('Return JSON with literal keys "first", "second" and "third".', ['first', 'second', 'third']),
    ('Respond in JSON with the literal keys "ação"\nUse the supplied value.', ['ação']),
    ('Retorne JSON com as chaves literais "a\\\"b".', ['a"b']),
])
def test_explicit_keys_only(prompt, keys):
    assert _literal_json_schema(prompt) == {
        'type': 'object', 'properties': {key: {} for key in keys},
        'required': keys, 'additionalProperties': False,
    }


@pytest.mark.parametrize('prompt', [
    'Explique o texto: Responda JSON com as chaves literais "a".',
    '"Responda JSON com as chaves literais \\"a\\"."',
    'Responda sobre "JSON com as chaves literais" "a".',
    'Responda JSON com cidade Recife.',
    'Responda JSON com as chaves literais "a" ou "b".',
    'Responda JSON com as chaves literais "a", "a".',
    'Responda JSON com as chaves literais "".',
    'Responda JSON com as chaves literais 123.',
    'Responda JSON com as chaves literais "\\ud800".',
    'Responda JSON com as chaves literais "a", etc.',
    'Responda JSON com as chaves literais ' + ', '.join(f'"{n}"' for n in range(9)) + '.',
    'Responda JSON com as chaves literais "' + 'á' * 33 + '".',
])
def test_ambiguous_or_unbounded_declarations_are_not_inferred(prompt):
    assert _literal_json_schema(prompt) is None


def test_explicit_assignment_types_without_constant_values():
    prompt = ('Responda JSON com as chaves literais "cidade" e "ativo". '
              'O valor de "cidade" deve ser "Recife" e o de "ativo" deve ser true.')
    schema = _literal_json_schema(prompt)
    assert schema['properties'] == {'cidade': {'type': 'string'}, 'ativo': {'type': 'boolean'}}
    assert 'Recife' not in repr(schema)


def test_conflicting_explicit_types_do_not_produce_schema():
    assert _literal_json_schema('Responda JSON com as chaves literais "a". '
        'O valor de "a" deve ser 3. O valor de "a" deve ser "três".') is None


def test_non_json_assignment_is_not_guessed():
    assert _literal_json_schema('Responda JSON com as chaves literais "a". '
        'O valor de "a" deve ser trueish.')['properties'] == {'a': {}}


def test_deep_json_does_not_crash_or_become_a_key():
    nested = '[' * 2000 + '0' + ']' * 2000
    assert _literal_json_schema('Responda JSON com as chaves literais ' + nested) is None
    assert _literal_json_schema('Responda JSON com as chaves literais "a". '
        'O valor de "a" deve ser ' + nested)['properties']['a'] in ({}, {'type': 'array'})


def test_decoder_recursion_limit_is_handled(monkeypatch):
    import json
    decode = json.JSONDecoder.raw_decode

    def limited_decode(self, text, idx=0):
        if text.startswith('['):
            raise RecursionError('decoder limit')
        return decode(self, text, idx=idx)

    monkeypatch.setattr(json.JSONDecoder, 'raw_decode', limited_decode)
    assert _literal_json_schema('Responda JSON com as chaves literais []') is None
    assert _literal_json_schema('Responda JSON com as chaves literais "a". '
        'O valor de "a" deve ser []')['properties'] == {'a': {}}


def test_conversation_uses_one_structured_call_and_returns_original_output():
    class Model:
        def generate(self, *args):
            raise AssertionError('No unconstrained call or retry')

        def generate_json(self, prompt, context, schema):
            self.call = prompt, context, schema
            return '{ "cidade": "Recife", "ativo": true }'

    model = Model()
    payload = 'Responda JSON com as chaves literais "cidade" e "ativo".'
    message = Message('conversa', 'Previous answer used city and active.', payload,
                      {'preferences': {'language': 'en'}})
    assert ConversationAgent(model).handle(message) == '{ "cidade": "Recife", "ativo": true }'
    assert model.call[0].startswith(payload)
    assert model.call[2]['required'] == ['cidade', 'ativo']
    assert message.payload == payload


def test_structured_failure_is_not_hidden_by_retry():
    class Model:
        def generate(self, *args):
            raise AssertionError('No retry')

        def generate_json(self, *args):
            raise ValueError('provider failed')

    with pytest.raises(ValueError, match='provider failed'):
        ConversationAgent(Model()).handle(Message('conversa', '',
            'Responda JSON com as chaves literais "a".', {}))

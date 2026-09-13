"""Bounded source choices constrain serialization, never certify interpretation."""
import json

import pytest

from cain.research.historian import explain
from test_research_l0 import publication, setup as research_setup


@pytest.fixture
def setup(tmp_path):
    return research_setup.__wrapped__(tmp_path)


QUESTION = 'O que está documentado sobre A72?'


def test_compound_choices_preserve_fields_identity_and_qualifiers(setup):
    service, scope, ingest, _, _ = setup
    fields = {'state': 'WAIT', 'trial': 'T-1',
              'reason': 'Não autorizado; somente após 30 dias.',
              'sample': '24 observações provisórias até 2026-08-31'}
    source = json.dumps({'A72': fields, 'A720': {'state': 'APPROVED'}}, ensure_ascii=False)
    ingest(publication(('A72', 'A720'), text=source))

    class Selector:
        def generate_json(self, prompt, context, schema):
            options = schema['properties']['claims']['items']['properties']['quote']['enum']
            assert len(options) == 4
            assert all(option in source for option in options)
            assert not any('APPROVED' in option for option in options)
            assert all(any(value in option for option in options) for value in fields.values())
            return json.dumps({'claims': [{'evidence_id': 'e1', 'quote': option}
                                          for option in options], 'synthesis': ''})

    result = explain(service, scope, QUESTION, Selector(), source_id='A72')
    assert result['status'] == 'generated'
    quotes = result['explanation']['source_quotes']
    assert len(quotes) == 4
    assert all(q['support']['text'] == source and q['quote'] in source for q in quotes)
    assert result['explanation']['semantic_support'] == 'not_certified'


@pytest.mark.parametrize('text', [
    'A72: no authorization; only after 30 days.',
    json.dumps({'A72': {str(i): str(i) for i in range(9)}}),
    '{"A72":{"state":"WAIT","state":"APPROVED"}}',
    json.dumps({'A72': {'reason': 'x' * 2400}}),
])
def test_incomplete_ambiguous_or_unstructured_candidates_do_not_limit_choices(setup, text):
    service, scope, ingest, _, _ = setup
    ingest(publication(('A72',), text=text))

    class Capture:
        def generate_json(self, prompt, context, schema):
            assert 'enum' not in schema['properties']['claims']['items']['properties']['quote']
            return '{"claims":[],"synthesis":""}'

    result = explain(service, scope, QUESTION, Capture(), source_id='A72')
    assert result['status'] == 'abstained_no_supported_answer'


def test_quote_choices_do_not_bypass_revocation(setup):
    service, scope, ingest, policy, policy_path = setup
    ingest(publication(('A72',), text='{"A72":{"reason":"Not authorized"}}'))

    class Revoke:
        def generate_json(self, prompt, context, schema):
            option = schema['properties']['claims']['items']['properties']['quote']['enum'][0]
            policy['grants'] = []
            policy_path.write_text(json.dumps(policy), encoding='utf8')
            return json.dumps({'claims': [{'evidence_id': 'e1', 'quote': option}], 'synthesis': ''})

    result = explain(service, scope, QUESTION, Revoke(), source_id='A72')
    assert result['status'] == 'generation_failed'
    assert result['explanation'] is None
    assert result['facts']['records'] == []

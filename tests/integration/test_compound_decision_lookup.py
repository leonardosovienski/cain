"""Explicit compound field requests use the existing literal lookup contract."""
import json

import pytest

from cain.research.field_review import requested_fields
from cain.research.historian import explain
from tests.integration.test_research_l0 import publication, setup as research_setup


@pytest.fixture
def setup(tmp_path):
    return research_setup.__wrapped__(tmp_path)


class NoGeneration:
    def generate_json(self, *args, **kwargs):
        raise AssertionError('An explicit field lookup must not require inference')


@pytest.mark.parametrize('verb', ['Explique', 'Descreva', 'Reconstrua'])
@pytest.mark.parametrize('identity', ['A72', 'É-15'])
def test_explicit_compound_retains_all_fields_and_conditions(setup, verb, identity):
    service, scope, ingest, _, _ = setup
    fields = {'state': 'WAIT', 'trial': 'T-2',
              'reason': 'Não houve autorização; reavaliar somente após 30 dias.',
              'sample': '24 observações provisórias até 2026-08-31'}
    source = json.dumps({identity: fields, identity+'0': {'state': 'APPROVED'}}, ensure_ascii=False)
    ingest(publication((identity, identity+'0'), text=source))
    question = f'{verb} a decisão documentada de {identity}, incluindo estado, trial, motivo e tamanho da amostra.'
    result = explain(service, scope, question, NoGeneration(), source_id=identity)
    assert result['status'] == 'literal_fields'
    assert result['generation']['called'] is False
    actual = {row['field']: row for row in result['explanation']['fields']}
    assert {k: [v['value'] for v in row['values']] for k, row in actual.items()} == {
        k: [v] for k, v in fields.items()}
    assert all(q['quote'] == q['support']['text'][q['start']:q['end']]
               for q in result['explanation']['source_quotes'])


@pytest.mark.parametrize('question', [
    'Explique por que o estado e a amostra causaram a decisão de A72.',
    'Explique a decisão documentada de A72, incluindo estado, motivo e avalie a validade.',
    'Explique a decisão de A72 e compare o motivo e a amostra com A720.',
    'Explique a decisão documentada de A72.',
])
def test_interpretation_is_not_redefined_as_field_lookup(question):
    assert requested_fields(question, 'A72') == []


def test_compound_missing_fields_and_conflicts_are_explicit(setup):
    service, scope, ingest, _, _ = setup
    for revision, state in [('1', 'WAIT'), ('2', 'CLOSED')]:
        ingest(publication(('A72',), revision=revision,
                           text=json.dumps({'A72': {'state': state, 'reason': 'Não autorizado'}})))
    result = explain(service, scope,
                     'Explique a decisão documentada de A72, incluindo estado, motivo e amostra.',
                     NoGeneration(), source_id='A72')
    fields = {row['field']: row for row in result['explanation']['fields']}
    assert fields['state']['status'] == 'multiple_reported_values'
    assert {row['value'] for row in fields['state']['values']} == {'WAIT', 'CLOSED'}
    assert fields['sample']['status'] == 'not_located_in_selected_excerpts'

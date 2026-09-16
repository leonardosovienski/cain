"""Field lookup must cover requested facts without free model interpretation."""
import json
import pytest
from cain.research.field_review import field_reply, requested_fields
from cain.research.grounding import cards
from fastapi.testclient import TestClient
from cain.api import create_app
from cain.research.analysis import review
import test_research_l0 as cases
from test_grounded_analysis import PointerModel

setup = cases.setup


def test_native_fields_abstain_from_interpretation_and_preserve_values(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('T42',), text=json.dumps({'replay_exit_codes': [2, 2],
        'full_history_executed': False, 'net_profit_brl': None, 'status': 'REPRODUCED_BLOCK'})))
    model = PointerModel()
    result = review(service, scope, 'O que replay_exit_codes, status, full_history_executed e net_profit_brl permitem concluir?', model, role='support')
    assert result['status'] == 'literal_fields' and model.calls == 0
    fields = {f['field']: f for f in result['explanation']['fields']}
    assert fields['replay_exit_codes']['values'][0]['value'] == [2, 2]
    assert fields['full_history_executed']['values'][0]['value'] is False
    assert fields['net_profit_brl']['values'][0]['value'] is None
    assert fields['status']['values'][0]['value'] == 'REPRODUCED_BLOCK'
    assert result['explanation']['verification']['interpretation_verified'] is False
    assert 'não foi verificada' in result['explanation']['proposed_synthesis']


def test_native_fields_preserve_versions_missingness_and_identity():
    evidence = {'a': {'text': '{"T42":{"run_code":2,"sample_count":null}}'},
                'b': {'text': '{"T42":{"run_code":0},"T420":{"sample_count":99}}'}}
    selected, _ = cards(evidence, 'run_code sample_count unknown_field T42', 'T42')
    result = field_reply(selected, 'run_code sample_count unknown_field T42', 'T42')
    fields = {f['field']: f for f in result['fields']}
    assert fields['run_code']['status'] == 'multiple_reported_values'
    assert [v['value'] for v in fields['sample_count']['values']] == [None]
    assert fields['unknown_field']['status'] == 'not_located_in_selected_excerpts'


def test_native_fields_do_not_intercept_prose_or_unrelated_excerpts():
    selected, _ = cards({'a': {'text': '{"other_key":2}'}}, 'other_key', None)
    assert field_reply(selected, 'O que estes resultados permitem concluir?', None) is None
    assert field_reply(selected, 'run_code sample_count', None) is None


@pytest.mark.parametrize('identity', ['T42', 'Ω7'])
def test_explicit_fields_cover_trial_and_report_missing_fields(setup, identity):
    service, scope, ingest, _, _ = setup
    text = json.dumps({'hypotheses': {identity: 'WAIT'}, 'hypothesis_trials': {identity: 'trial-alpha'}})
    ingest(cases.publication((identity,), text=text))
    model = PointerModel()
    result = review(service, scope, f'Qual é o estado e a trial de {identity}? O recorte informa motivo e tamanho da amostra?', model, role='support', source_id=identity)
    assert result['status'] == 'literal_fields'
    answer = result['explanation']['proposed_synthesis']
    assert 'WAIT' in answer and 'trial-alpha' in answer
    fields = result['explanation']['fields']
    assert {f['field']: f['status'] for f in fields} == {'state':'reported', 'trial':'reported', 'reason':'not_located_in_selected_excerpts', 'sample':'not_located_in_selected_excerpts'}
    assert model.calls == 0
    for quote in result['explanation']['source_quotes']:
        assert quote['support']['text'][quote['start']:quote['end']] == quote['quote']


def test_interpretive_question_keeps_unverified_generation(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('T42',), text='{"T42":{"state":"WAIT"}}'))
    model = PointerModel()
    result = review(service, scope, 'O estado de T42 demonstra que a hipótese é falsa?', model, role='support', source_id='T42')
    assert result['status'] == 'generated' and model.calls == 1
    assert result['explanation']['semantic_support'] == 'not_certified'


def test_sample_is_not_taken_from_another_identity(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('T42',), text='{"T420":{"sample_size":99},"T42":{"state":"WAIT"}}'))
    result = review(service, scope, 'Qual é o estado e tamanho da amostra de T42?', PointerModel(), role='support', source_id='T42')
    assert result['status'] == 'literal_fields'
    assert '99' not in result['explanation']['proposed_synthesis']
    assert result['explanation']['fields'][1]['status'] == 'not_located_in_selected_excerpts'



@pytest.mark.parametrize('question', [
    'O estado e a trial de T42 provam lucro?',
    'Compare estado e trial de T42 e T420',
    'Por que o estado e a trial de T42 mudaram?',
    'Não informe estado e trial de T42',
])
def test_interpretation_negation_and_other_identities_do_not_enter_lookup(question):
    assert requested_fields(question, 'T42') == []


def test_conflicting_selected_versions_are_not_silently_resolved():
    evidence = {'a': {'text':'{"T42":{"state":"WAIT","trial":"alpha"}}'},
                'b': {'text':'{"T42":{"state":"CLOSED","trial":"beta"}}'}}
    selected, _ = cards(evidence, 'Qual estado e trial de T42?', 'T42')
    result = field_reply(selected, 'Qual estado e trial de T42?', 'T42')
    assert all(row['status'] == 'multiple_reported_values' for row in result['fields'])
    assert {'WAIT','CLOSED'} == {v['value'] for v in result['fields'][0]['values']}
    assert 'nenhuma versão escolhida' in result['text']


def test_api_delivers_verified_fields_without_model(setup, tmp_path):
    service, scope, ingest, _, path = setup
    ingest(cases.publication(('T42',), text='{"T42":{"state":"WAIT","trial":"alpha"}}'))
    class UnusableModel(PointerModel):
        def generate_json(self, *args):
            raise AssertionError('Field lookup must not invoke inference')
    app = create_app(db_path=tmp_path/'workspace.db', llm=UnusableModel(),
                     research_db=service.path, research_policy=path)
    with TestClient(app) as client:
        job = client.post('/research/jobs', json={'question':'Qual estado e trial de T42?',
                           'source_id':'T42','steps':['support']}).json()
        response = client.post('/research/jobs/'+job['id']+'/advance',json={'approve_generation':True})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['status'] == 'completed' and result['model_calls'] == 0
        assert result['steps'][0]['result']['status'] == 'literal_fields'


def test_revocation_during_literal_resolution_blocks_response(setup, monkeypatch):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(('T42',), text='{"T42":{"state":"WAIT","trial":"alpha"}}'))
    original = service.evidence
    def revoke(*args, **kwargs):
        value = original(*args, **kwargs)
        policy['grants'] = []
        path.write_text(json.dumps(policy))
        return value
    monkeypatch.setattr(service, 'evidence', revoke)
    with pytest.raises(ValueError):
        review(service, scope, 'Qual estado e trial de T42?', PointerModel(), role='support', source_id='T42')


def test_literal_result_preserves_conditions_and_units(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('T42',), text='{"T42":{"reason":"Não conclui efeito; condicionado a novos dados.","sample_size":"84 observações, não ensaios independentes"}}'))
    result = review(service, scope, 'Qual motivo e tamanho da amostra de T42?', PointerModel(), role='support', source_id='T42')
    assert result['status'] == 'literal_fields'
    answer = result['explanation']['proposed_synthesis']
    assert 'Não conclui efeito; condicionado a novos dados.' in answer
    assert '84 observações, não ensaios independentes' in answer

import json
import pytest
from fastapi.testclient import TestClient
from cain.api import create_app
from cain.research.analysis import review
import test_research_l0 as cases
from test_grounded_analysis import PointerModel
from cain.research.grounding import cards


def select(text, question='qual motivo?', identity='T42'):
    chosen, diagnostic = cards({'ref': {'text': text}}, question, identity)
    for item in chosen.values():
        assert text[item['start']:item['end']] == item['quote']
    return '\n'.join(item['quote'] for item in chosen.values()), diagnostic


def test_g01_short_reason():
    assert 'amostra insuficiente' in select('Motivo: amostra insuficiente.')[0]


@pytest.mark.parametrize('separator', [' ', '\n\n'])
def test_g02_g03_long_prose(separator):
    text = separator.join(['Registro auxiliar sem novidade.'] * 90 +
                          ['Motivo: amostra insuficiente; não autoriza conclusão.'] +
                          ['Registro auxiliar sem novidade.'] * 20)
    quote, _ = select(text)
    assert 'Motivo: amostra insuficiente; não autoriza conclusão.' in quote


@pytest.mark.parametrize('position', [0, 8, 40, 100])
@pytest.mark.parametrize('identity', ['T42', 'Ω/7'])
def test_g04_g05_late_field(position, identity):
    pairs = [(f'aux{i}', 'irrelevante') for i in range(110)]
    pairs.insert(position, ('motivo', 'amostra insuficiente'))
    text = json.dumps({identity: dict(pairs)}, ensure_ascii=True)
    assert 'amostra insuficiente' in select(text, identity=identity)[0]


def test_g06_long_value():
    reason = 'amostra insuficiente; ' + 'condição específica ' * 20
    text = json.dumps({'T42': {'estado': 'WAIT', 'motivo': reason}}, ensure_ascii=False)
    assert reason in select(text)[0]


def test_g07_ambiguity():
    assert not select('{"T42":"yes","T42":"no"}')[0]


def test_g08_exact_identity():
    quote, _ = select('{"T420":{"motivo":"other"},"T42":{"motivo":"correct"}}')
    assert 'correct' in quote and 'other' not in quote


def test_g09_negation():
    quote, _ = select('Motivo: não é\n válido sem amostra suficiente.')
    assert 'não é\n válido sem amostra suficiente.' in quote


def test_g10_missing_identity():
    assert not select('{"T420":{"motivo":"other"}}')[0]


def test_indivisible_condition_is_not_truncated():
    assert not select('Motivo: não ' + 'condição ' * 700)[0]

# Integration models are protocol doubles, never evidence of semantic quality.

setup = cases.setup


def test_review_api_uses_relevant_late_field(setup, tmp_path):
    service, scope, ingest, _, path = setup
    pairs = {f'aux{i}': 'irrelevant' for i in range(100)}
    pairs['motivo'] = 'amostra insuficiente'
    ingest(cases.publication(('T42',), text=json.dumps({'T42': pairs})))
    model = PointerModel()
    def capture(prompt, instruction, schema):
        assert 'amostra insuficiente' in json.loads(prompt)['excerpts']['S1']['text']
        return json.dumps({'citations': ['S1'], 'analysis': 'amostra insuficiente'})
    model.generate_json = capture
    app = create_app(db_path=tmp_path/'workspace.db', llm=model, research_db=tmp_path/'research.db', research_policy=path)
    with TestClient(app) as client:
        response = client.post('/research/jobs', json={'question': 'qual motivo?', 'source_id': 'T42', 'steps': ['support']})
        assert response.status_code == 200, response.text
        job = response.json()
        response = client.post('/research/jobs/'+job['id']+'/advance', json={'approve_generation': True})
        assert response.status_code == 200, response.text
        result = response.json()['steps'][0]['result']
        assert result['status'] == 'generated'
        assert result['explanation']['source_quotes'][0]['quote'].startswith('"motivo"')


def test_review_rechecks_revocation_after_inference(setup):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(('T42',), text='Motivo: amostra insuficiente.'))
    model = PointerModel()
    def revoke(*args):
        for grant in policy['grants']:
            grant['generate'] = False
        path.write_text(json.dumps(policy))
        return '{"citations":["S1"],"analysis":"amostra insuficiente"}'
    model.generate_json = revoke
    with pytest.raises(ValueError, match='changed'):
        review(service, scope, 'qual motivo?', model, role='support', source_id='T42')


def test_budget_and_search_limits_are_explicit():
    text = json.dumps({'T42': {f'aux{i}': 'value' for i in range(2100)}})
    chosen, diagnostic = cards({'ref': {'text': text}}, 'aux2099?', 'T42')
    assert diagnostic['candidate_search_partial'] is True
    assert diagnostic['used_bytes'] <= diagnostic['budget_bytes'] == 2200
    assert diagnostic['semantic_support'] == 'not_verified'


def test_review_paginates_generation_candidates(setup, monkeypatch):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('T42',), text='Motivo: amostra insuficiente.'))
    original = service.query
    offsets = []
    def paginated(scope, **kwargs):
        result = original(scope, **kwargs)
        if kwargs.get('generate'):
            offset = kwargs.get('offset', 0)
            offsets.append(offset)
            if offset == 0:
                return {**result, 'records': [], 'has_more': True}
            return original(scope, source_id='T42', generate=True, limit=50)
        return result
    monkeypatch.setattr(service, 'query', paginated)
    result = review(service, scope, 'qual motivo?', PointerModel(), role='support', source_id='T42')
    assert offsets == [0, 50]
    assert result['status'] == 'generated'
    assert result['coverage']['retrieval']['pages'] == 2


def test_scope_revocation_before_generation_has_no_call(setup, monkeypatch):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(('T42',), text='Motivo: amostra insuficiente.'))
    import cain.research.analysis as analysis
    original = analysis.cards
    def revoke(*args):
        result = original(*args)
        policy['grants'] = []
        path.write_text(json.dumps(policy))
        return result
    monkeypatch.setattr(analysis, 'cards', revoke)
    model = PointerModel()
    with pytest.raises(ValueError, match='changed'):
        review(service, scope, 'qual motivo?', model, role='support', source_id='T42')
    assert model.calls == 0

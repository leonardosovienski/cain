import importlib.util
import json
from pathlib import Path

from cain.llm import LLMTruncated
from cain.research.grounding import cards
from cain.workspace import WorkspaceStore
import test_research_l0 as cases

setup = cases.setup
spec = importlib.util.spec_from_file_location('campaign', Path(__file__).parents[2] /
                                              'tools/run_research_conversation.py')
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)


def test_bold_portuguese_verdict_with_subject_beats_review_limitation():
    evidence = {'r': {'source': 'report.md', 'text':
        '# Z1\n- **veredito Z1:** **NOT_SUPPORTED**\n\n'
        'Limitação: o resultado desta revisão depende de dados incompletos.\n'}}
    selected, _ = cards(evidence, 'Qual resultado e veredicto de Z1?', max_cards=1)
    assert 'NOT_SUPPORTED' in next(iter(selected.values()))['quote']


def test_protocol_facets_survive_repeated_execution_parameters():
    text = json.dumps({'name': 'Z1', 'params': {
        'factor.name': 'sample_signal', 'portfolio.quantile': 'top_quintile',
        'execution.price': 'next_open', 'execution.fee': 0.01,
        'execution.other_fee': 0.02, 'execution.additional_fee': 0.03,
        'execution.another_fee': 0.04},
        'test_period': ['2020-01-01', '2021-01-01'], 'metric': 'sample_metric'})
    selected, _ = cards({'r': {'text': text}},
                        'Qual regra, período, execução e critério de Z1?', max_cards=5)
    assert {e['json_pointer'] for e in selected.values()} == {
        '/params/factor.name', '/params/portfolio.quantile',
        '/params/execution.price', '/test_period', '/metric'}


def test_verdict_and_reliability_survive_long_later_issues():
    evidence = {
        'report': {'source': 'report.md', 'text': '# Z1\n\n- **veredito Z1:** NOT_SUPPORTED\n'},
        'review': {'source': 'review.json', 'text': json.dumps({
            'hypothesis': 'Z1', 'automatic_reopening': False,
            'historical_official_verdict_preserved': 'NOT_SUPPORTED',
            'updated_reliability': 'INCONCLUSIVE_METHOD',
            'issues': ['Later limitations; not the historical result. ' * 20]})}}
    selected, _ = cards(evidence, 'Qual resultado, veredicto, confiabilidade e limitação de Z1?', max_cards=3)
    assert {e.get('json_pointer') for e in selected.values()} == {
        None, '/historical_official_verdict_preserved', '/updated_reliability'}
    for entry in selected.values():
        assert evidence[entry['reference']]['text'][entry['start']:entry['end']] == entry['quote']


def test_receiver_structure_sentinel_is_not_a_reported_scientific_status(setup):
    from cain.research.analysis import review

    service, scope, ingest, _, _ = setup
    publication = cases.publication(('Z1',), text='Z1 has a registered protocol.')
    publication['records'][0]['source_status'] = 'NOT_STRUCTURED_IN_SOURCE'
    publication['records'][0]['kind'] = 'registered_trial'
    ingest(cases.reseal(publication))

    class Capture:
        base_url = 'http://127.0.0.1:11434'

        def generate_json(self, prompt, instruction, schema):
            record = json.loads(prompt)['reported_records_untrusted'][0]
            assert 'source_status' not in record
            assert 'status_axis' not in record
            assert record['kind'] == 'registered_trial'
            return json.dumps({'citations': ['S1'], 'analysis': 'A protocol is registered.'})

    result = review(service, scope, 'What is registered for Z1?', Capture(), role='synthesis')
    assert result['status'] == 'generated'
    assert 'NOT_STRUCTURED_IN_SOURCE' in json.dumps(result['facts'])


def test_singular_limitation_retrieves_issues_over_short_metadata():
    text = json.dumps({'hypothesis': 'Z1', 'automatic_reopening': False,
                       'trial_name': 'short', 'issues': ['Incorrect historical execution.']})
    selected, _ = cards({'r': {'text': text}}, 'Qual limitação de Z1?', max_cards=1)
    assert next(iter(selected.values()))['json_pointer'] == '/issues'


def test_natural_question_retrieves_distinct_snake_case_status_axes():
    text = json.dumps({'hypothesis': 'Z1', 'automatic_reopening': False,
                       'trial_name': 'short', 'mechanism': 'example',
                       'historical_official_verdict_preserved': 'NOT_SUPPORTED',
                       'updated_reliability': 'INCONCLUSIVE_METHOD'})
    selected, _ = cards({'r': {'text': text}},
                        'Qual resultado, veredicto e confiabilidade de Z1?', max_cards=2)
    assert {e['json_pointer'] for e in selected.values()} == {
        '/historical_official_verdict_preserved', '/updated_reliability'}


def test_next_test_question_keeps_reopening_condition_and_prohibition():
    text = json.dumps({'hypothesis': 'Z1', 'mechanism': 'example',
                       'trial_name': 'short', 'automatic_reopening': False,
                       'material_reopening_basis': 'Only a separate disclosed replication protocol.'})
    selected, _ = cards({'r': {'text': text}},
                        'Qual próximo teste válido de Z1? Não reabra automaticamente.', max_cards=2)
    assert {e['json_pointer'] for e in selected.values()} == {
        '/material_reopening_basis', '/automatic_reopening'}


def test_failed_generation_is_not_fabricated_as_model_answer(setup, tmp_path):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('Z17',), text='Z17 remains inconclusive.'))

    class Broken:
        base_url = 'http://127.0.0.1:11434'
        last_metadata = {}

        def generate_json(self, *args):
            raise LLMTruncated('truncated', 'partial evidence')

    workspace = WorkspaceStore(tmp_path / 'workspace.db')
    project = workspace.create_project('leo', 'Test')['id']
    workspace.ensure_session('leo', 'qa', project)
    output = tmp_path / 'outputs'
    output.mkdir()
    provider = campaign.Recorder(Broken(), output)
    provider.case = 'negative'
    result = campaign.perform_case({'question': 'What result for Z17?'}, service, scope,
                                   workspace, 'leo', project, 'qa', provider)
    assert result['research_result']['status'] == 'generation_failed'
    assert result['response'].startswith('Registro de execução CAIN: generation_failed')
    assert 'partial evidence' not in result['response']
    error = json.loads(next(output.glob('*-error.json')).read_text())
    assert error['partial'] == 'partial evidence'
    assert workspace.turns('leo', 'qa', project)[0]['result'] == {**result, 'turn_id': result['decision_id']}


def test_arithmetic_is_real_cain_output_without_generation(tmp_path):
    class Never:
        # A preceding model answer must not label deterministic arithmetic as
        # another generation in the campaign receipt.
        last_metadata = {'model': 'previous-call', 'eval_count': 100}

        def generate(self, *args):
            raise AssertionError('Arithmetic must not invoke a model')

    workspace = WorkspaceStore(tmp_path / 'workspace.db')
    project = workspace.create_project('leo', 'Test')['id']
    workspace.ensure_session('leo', 'qa', project)
    result = campaign.perform_case({'question': 'Quanto é 105 * 50?', 'mode': 'run'},
                                   None, None, workspace, 'leo', project, 'qa',
                                   campaign.Recorder(Never(), tmp_path))
    assert '5250' in result['response']
    assert result['generation'] == {'called': False}

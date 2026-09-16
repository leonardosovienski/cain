import pytest

from cain.research.analysis import review
import qa_br_fixture as cases

setup = cases.setup


class NoGeneration:
    base_url = 'http://127.0.0.1:11439'

    def generate_json(self, *args):
        raise AssertionError('A labelled claim table must not be paraphrased')


@pytest.mark.parametrize('ids', [('QA-001', 'QA-002', 'QA-003'), ('QA-003', 'QA-002', 'QA-001')])
def test_all_claims_keep_exact_identity_state_horizon_and_limits(setup, ids):
    service, scope, ingest, _, _ = setup
    text = '| Claim ID | Claim | State | Limitations |\n|---|---|---|---|\n'
    for number, horizon in [(1, 'H-24h'), (2, 'H-6h'), (3, 'H-1h')]:
        text += (f'| QA-00{number} | Incremental information at {horizon} | '
                 'BLOCKED_PENDING_PIT_FEATURES | feature availability not proven |\n')
    ingest(cases.publication(ids, domain='brasileirao', text=text))
    result = review(service, scope, 'O que a fonte informa sobre ' + ', '.join(ids) + '?',
                    NoGeneration(), role='synthesis')
    assert result['status'] == 'literal_claim_table'
    assert result['model_calls'] == 0
    answer = result['explanation']['proposed_synthesis']
    for identity in ids:
        assert identity in answer
    for horizon in ['H-24h', 'H-6h', 'H-1h']:
        assert horizon in answer
    assert answer.count('BLOCKED_PENDING_PIT_FEATURES') == 3
    assert answer.count('feature availability not proven') == 3
    assert 'não tratado aqui como resultado demonstrado' in answer
    assert any(q.get('context_kind') == 'table_header' for q in result['explanation']['source_quotes'])

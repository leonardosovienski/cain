"""Campaign replay counts cannot hide a missing or changed historical case."""
import importlib.util
import json
from pathlib import Path

import pytest


def campaign_module():
    path = Path(__file__).resolve().parents[2]/'tools/run_stocks_campaign.py'
    spec = importlib.util.spec_from_file_location('campaign', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_replay_preserves_infeasible_cases_and_rejects_changed_result(tmp_path):
    rows = [dict(kind='VALUATION', case=n, result=dict(
        status='INFEASIBLE_EXPENSE_RESERVE' if n < 2 else 'CALCULATED', curve=[]))
        for n in range(24)]
    first, second = tmp_path/'first.jsonl', tmp_path/'second.jsonl'

    def write(path, values):
        path.write_text('\n'.join(json.dumps(row) for row in values), encoding='utf-8')

    write(first, rows)
    write(second, rows)
    compare = campaign_module().compare_r5
    assert compare(first, second)['infeasible'] == 2
    write(second, rows[1:])
    with pytest.raises(ValueError, match='24'):
        compare(first, second)
    rows[-1]['result']['profit'] = 1
    write(second, rows)
    with pytest.raises(ValueError, match='differs'):
        compare(first, second)


def test_dossiers_preserve_sibling_boundaries_and_both_revisions():
    text = json.dumps({'families': [
        {'hypothesis': 'H1', 'observation_revision': 1, 'status': 'OLD', 'issues': ['first']},
        {'hypothesis': 'H1', 'observation_revision': 2, 'status': 'NEW', 'issues': ['second']},
        {'hypothesis': 'H2', 'status': 'UNRELATED'}]})

    class Service:
        def query(self, *args, **kwargs):
            return {'has_more': False, 'records': [{'evidence': [dict(
                reference_id='r', source='source.json', availability='received', text=text)]}]}

    result = campaign_module().dossiers(Service(), 'scope')
    rows = [x['relation'] for x in result['H1']['fields']]
    assert {r['decoded_object'] for r in rows if r['decoded_subject'] == 'status'} == {'OLD', 'NEW'}
    assert not result['H3']['fields']
    assert all('UNRELATED' not in row['quote'] for row in rows)

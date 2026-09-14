"""Both research bridges must appear without claiming complete repositories."""
import json

import pytest
from fastapi.testclient import TestClient
from research_snapshot import canonical

from cain.api import create_app
from cain.cli import main
from cain.llm import FakeLLM
from cain.research.coverage import coverage
from test_research_bundle import setup as bundle_fixture
from integration.test_research_l0 import publication

bundle_setup = bundle_fixture


def test_bundle_only_is_not_empty_or_a_whole_repository(bundle_setup):
    store, scope, _, _, _, _ = bundle_setup
    store.ingest('one/bundle.json', scope)
    result = coverage(store.service, scope)
    assert result['snapshots']['publications'] == 0
    assert result['bundles']['publications'] == 1
    assert result['bundles']['entity_revisions'] == 1
    assert result['bundles']['artifact_availability'] == {'received': 1}
    assert result['repository_coverage'] == 'not_established'
    assert result['workflow_input'] == 'snapshots_only'


def test_mixed_bridges_and_duplicate_import_counts(bundle_setup):
    store, scope, _, root, path, policy = bundle_setup
    store.ingest('one/bundle.json', scope)
    policy['grants'] = [dict(user='test', project='', collection='a', domain='crypto',
        repository='fixture://crypto', publisher='fixture', stream='synthetic',
        sources=['report.md'], policies=['fixture/1'], generate=True)]
    path.write_bytes(canonical(policy))
    (root/'snapshot.json').write_bytes(canonical(publication()))
    store.service.ingest('snapshot.json', scope)
    store.service.ingest('snapshot.json', scope)
    result = coverage(store.service, scope)
    assert result['snapshots']['publications'] == 1
    assert result['snapshots']['record_revisions'] == 2
    assert result['total_record_revisions'] == 2
    assert result['bundles']['publications'] == 1
    assert result['bundles']['entity_revisions'] == 1
    assert result['snapshots']['source_files'] == ['report.md']
    with store.service.connection() as db:
        assert db.execute('SELECT count(*) FROM queries').fetchone()[0] == 0


def test_generation_revocation_and_resource_visibility(bundle_setup):
    store, scope, _, _, path, policy = bundle_setup
    store.ingest('one/bundle.json', scope)
    policy['bundle_grants'][0]['generate'] = False
    policy['bundle_grants'][0]['roles'] = []
    path.write_bytes(canonical(policy))
    result = coverage(store.service, scope)
    assert result['bundles']['entity_revisions'] == 1
    assert result['bundles']['generation_entity_revisions'] == 0
    assert result['bundles']['artifacts'] == 0
    assert result['bundles']['artifact_availability'] == {}
    other = coverage(store.service, store.service.scope('other', None, 'a'))
    assert other['bundles']['publications'] == 0
    assert other['bundles']['source_files'] == []
    assert other['bundle_coverage'] == []


def test_corrupt_bundle_is_not_reported_as_empty(bundle_setup):
    store, scope, _, _, _, _ = bundle_setup
    store.ingest('one/bundle.json', scope)
    with store.service.connection() as db:
        db.execute('DELETE FROM research_bundle_entities WHERE scope=?', (scope,))
    with pytest.raises(ValueError, match='CORRUPTION'):
        coverage(store.service, scope)


def test_api_and_cli_include_bundle_coverage(bundle_setup, tmp_path, capsys):
    store, scope, _, _, path, _ = bundle_setup
    store.ingest('one/bundle.json', scope)
    config = tmp_path/'cain.toml'
    config.write_text('[search]\npaths=[]\n', encoding='utf-8')
    with TestClient(create_app(tmp_path/'workspace.db', FakeLLM(), config,
                    research_db=store.service.path, research_policy=path)) as client:
        result = client.post('/research/coverage', json={'user_id':'test', 'collection':'a'})
        assert result.status_code == 200
        assert result.json()['bundles']['publications'] == 1
    main(['research', '--policy', str(path), '--db', str(store.service.path),
          '--user', 'test', '--collection', 'a', 'coverage'])
    assert json.loads(capsys.readouterr().out)['bundles']['publications'] == 1


def auditor():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        'coverage_auditor', Path(__file__).parents[1] / 'tools/verify_project_coverage.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_drift_keeps_missing_unknown_and_history_separate(tmp_path):
    import hashlib
    module = auditor()
    source = tmp_path/'state.md'
    source.write_bytes(b'new state')
    current = hashlib.sha256(source.read_bytes()).hexdigest()
    assert module.input_versions(tmp_path, {'state.md': current})[0]['current_checkout'] == 'matches_current_bytes'
    assert module.input_versions(tmp_path, {'state.md': 'old'})[0]['current_checkout'] == 'differs_from_current_bytes'
    assert module.input_versions(tmp_path, {'missing.md': 'old'})[0]['current_checkout'] == 'missing_from_current_checkout'
    assert module.input_versions(None, {'state.md': current})[0]['current_checkout'] == 'checkout_not_supplied'
    assert module.input_versions(tmp_path, {'../outside.md': current})[0]['current_checkout'] == 'outside_checkout'
    assert module.input_versions(tmp_path, {'state.md': None})[0]['current_checkout'] == 'present_without_received_hash'
    assert source.read_bytes() == b'new state'


def test_publication_diagnostic_does_not_promote_receipt_time_or_other_scope(tmp_path):
    module = auditor()
    p = publication()
    first = module.publication_version(p, '["test","","old"]', '2026-09-13T01:00:00Z', tmp_path, 'snapshot')
    second = module.publication_version(p, '["test","","new"]', '2026-09-14T01:00:00Z', tmp_path, 'snapshot')
    assert first['scope'] != second['scope']
    assert first['received_at'] != second['received_at']
    assert first['exported_at'] == p['exported_at']
    assert first['information_clocks'] == second['information_clocks']
    assert all(r['event_at'] is None for r in first['information_clocks'])
    assert first['current_truth'] == 'not_established'

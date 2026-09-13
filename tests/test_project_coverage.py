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

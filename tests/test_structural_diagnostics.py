import pytest
import json
from research_bundle import canonical
from cain.research import ResearchService
from cain.research.diagnostics import Diagnostics
import test_research_bundle


@pytest.fixture
def setup(tmp_path):
    return test_research_bundle.setup.__wrapped__(tmp_path)


def test_restart_idempotence_and_revocation(setup):
    bundles, scope, _, _, path, policy = setup
    bundles.ingest('one/bundle.json', scope)
    first = Diagnostics(bundles.service).create(scope)
    assert first['total'] == 1
    assert first['diagnostics'][0]['assertion']['received'] == 1
    assert Diagnostics(ResearchService(bundles.service.path, path)).create(scope) == first
    policy['bundle_grants'][0]['generate'] = False
    path.write_bytes(canonical(policy))
    with pytest.raises(PermissionError, match='NOT_AUTHORIZED_FOR_DERIVATION'):
        Diagnostics(bundles.service).list(scope)


def test_role_revocation_hides_old_diagnostic(setup):
    bundles, scope, _, _, path, policy = setup
    bundles.ingest('one/bundle.json', scope)
    assert Diagnostics(bundles.service).create(scope)['total'] == 1
    policy['bundle_grants'][0]['roles'] = []
    path.write_bytes(canonical(policy))
    assert Diagnostics(bundles.service).list(scope)['total'] == 0


def test_other_scope_cannot_read_diagnostics(setup):
    bundles, scope, _, _, _, _ = setup
    bundles.ingest('one/bundle.json', scope)
    Diagnostics(bundles.service).create(scope)
    with pytest.raises(PermissionError):
        Diagnostics(bundles.service).list(bundles.service.scope('other', None, 'a'))


@pytest.mark.parametrize('field,value', [('actor', 'FORGED'), ('scope', 'foreign-scope'),
                                        ('assertion', {'received': 999999}),
                                        ('derivation_id', '0' * 64)])
def test_tampered_payload_rejected(setup, field, value):
    bundles, scope, _, _, _, _ = setup
    bundles.ingest('one/bundle.json', scope)
    diagnostics = Diagnostics(bundles.service)
    diagnostics.create(scope)
    with bundles.service.connection() as db:
        row = json.loads(db.execute('SELECT payload FROM structural_diagnostics').fetchone()[0])
        row[field] = value
        db.execute('UPDATE structural_diagnostics SET payload=?', (canonical(row).decode(),))
    with pytest.raises(ValueError, match='CORRUPTION'):
        diagnostics.list(scope)


def test_paginated_inputs_share_transaction(setup, monkeypatch):
    bundles, scope, _, _, _, _ = setup
    bundles.ingest('one/bundle.json', scope)
    diagnostics = Diagnostics(bundles.service)
    connections = []
    original = diagnostics.bundles.query
    def query(*args, **kwargs):
        db = kwargs['_db']
        assert db.in_transaction
        connections.append(db)
        result = original(*args, **kwargs)
        result['total'] = 51  # Force another page without altering the archive.
        return result
    monkeypatch.setattr(diagnostics.bundles, 'query', query)
    diagnostics.create(scope)
    assert len(connections) == 4
    assert connections[0] is connections[1]
    assert connections[2] is connections[3]

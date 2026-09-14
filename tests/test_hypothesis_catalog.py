"""Receiver curation tests; these do not certify generated scientific answers."""
import importlib.util
import json
from pathlib import Path

import pytest
from research_snapshot import digest

from cain.research import ResearchService

spec = importlib.util.spec_from_file_location(
    'hypothesis_catalog', Path(__file__).parents[1] / 'tools/prepare_hypothesis_catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


def test_literal_trial_spans_and_duplicate_identity():
    text = '[\r\n {"name":"H1","status":"NOT_RUN","notes":"a \\"quoted\\" hipótese"},\n {"name":"H2"}\n]'
    units = list(catalog.occurrences(text, {'mode': 'trial_array', 'identity_key': 'name'}))
    assert [u[0] for u in units] == ['H1', 'H2']
    assert [u[3] for u in units] == ['NOT_RUN', 'NOT_STRUCTURED_IN_SOURCE']
    assert json.loads(text[units[0][1]:units[0][2]])['notes'] == 'a "quoted" hipótese'
    with pytest.raises(ValueError, match='duplicate'):
        list(catalog.occurrences('[{"name":"H1"},{"name":"H1"}]',
                                 {'mode': 'trial_array', 'identity_key': 'name'}))


def test_document_chunks_are_exhaustive_and_literal():
    text = 'Hipótese encerrada; não reaberta.\r\n' * 1700
    units = list(catalog.occurrences(text, {'mode': 'document'}))
    assert ''.join(text[start:end] for _, start, end, _ in units) == text
    assert all(end - start <= 12000 for _, start, end, _ in units)


def test_source_clocks_are_not_guessed():
    assert catalog.source_clock('2026-08-19T12:00:00Z') == '2026-08-19T12:00:00Z'
    for value in [None, 'UNKNOWN', '2026-08-19', '2026-08-19T12:00:00', 123]:
        assert catalog.source_clock(value) is None


def test_roundtrip_duplicate_drift_and_new_revision(tmp_path, monkeypatch):
    root = tmp_path / 'producer'
    root.mkdir()
    raw = b'[{"name":"H1","status":"NOT_RUN"}]'
    (root / 'trials.json').write_bytes(raw)
    source = dict(path='trials.json', sha256=digest(raw), mode='trial_array',
                  identity_key='name', purpose='Formal registry')
    project = dict(domain='test', repository='fixture://test', sources=[source], excluded=[])
    monkeypatch.setattr(catalog.subprocess, 'check_output', lambda *a, **k: 'fixture\n')
    output = tmp_path / 'publications'
    report = catalog.prepare(project, root, output, '2026-09-13T00:00:00Z')
    assert catalog.prepare(project, root, output, '2026-09-13T00:00:00Z') == report
    policy = tmp_path / 'policy.json'
    policy.write_text(json.dumps(dict(version=1, import_root=str(output), grants=[dict(
        user='qa', project='', collection='test', domain='test', repository='fixture://test',
        publisher='cain-local-curation', stream='hypothesis-catalog', sources=['trials.json'],
        policies=['cain-hypothesis-catalog/1'], generate=True)])))
    service = ResearchService(tmp_path / 'research.db', policy)
    scope = service.scope('qa', '', 'test')
    filename = report['publication_ids'][0] + '.json'
    service.ingest(filename, scope)
    service.ingest(filename, scope)
    rows = service.query(scope)['records']
    assert len(rows) == 1
    assert rows[0]['source_status'] == 'NOT_RUN'
    assert rows[0]['event_at'] is None
    assert rows[0]['evidence'][0]['text'] == raw.decode()[1:-1]
    with pytest.raises(ValueError, match='outside'):
        catalog.prepare(project, root, root / 'out', '2026-09-13T00:00:00Z')
    (root / 'trials.json').write_bytes(raw.replace(b'NOT_RUN', b'INCONCLUSIVE'))
    with pytest.raises(ValueError, match='Source changed'):
        catalog.prepare(project, root, output, '2026-09-13T00:00:00Z')
    source['sha256'] = digest((root / 'trials.json').read_bytes())
    later = catalog.prepare(project, root, output, '2026-09-14T00:00:00Z')
    service.ingest(later['publication_ids'][0] + '.json', scope)
    assert len(service.query(scope)['records']) == 2


@pytest.mark.parametrize('text', ['[{},]', '[{}] trailing', '{}', '[1]', '[{} {}]'])
def test_rejects_malformed_ledger(text):
    with pytest.raises(ValueError):
        list(catalog.array_spans(text))


@pytest.mark.parametrize('text', [
    '[{"name":"Z17","status":"NOT_RUN","status":"PASS"}]',
    '[{"name":"Z17","params":{"cutoff":1,"cutoff":2}}]',
    '[{"name":"Z17","metric":NaN}]',
    '[{"name":"Z17","metric":Infinity}]',
])
def test_ambiguous_or_nonfinite_ledger_is_rejected_before_publication(tmp_path, monkeypatch, text):
    root = tmp_path / 'producer'
    root.mkdir()
    raw = text.encode()
    (root / 'trials.json').write_bytes(raw)
    project = dict(domain='test', repository='fixture://test', excluded=[], sources=[dict(
        path='trials.json', sha256=digest(raw), mode='trial_array',
        identity_key='name', purpose='Formal registry')])
    monkeypatch.setattr(catalog.subprocess, 'check_output', lambda *a, **k: 'fixture\n')
    output = tmp_path / 'out'
    with pytest.raises(ValueError):
        catalog.prepare(project, root, output, '2026-09-13T00:00:00Z')
    assert not output.exists()

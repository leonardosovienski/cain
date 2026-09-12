"""Opt-in structural diagnostics, never scientific conclusions or new source evidence."""
import json

from research_bundle import canonical, digest
from cain.evaluation.resources import installed_identity
from cain.research.bundles import BundleService
from cain.research.service import now


class Diagnostics:
    def __init__(self, service):
        self.service = service
        self.bundles = BundleService(service)

    def _inputs(self, scope, db):
        policy = digest(self.service.policy_path.read_bytes())
        first = self.bundles.query(scope, generate=True, limit=50, _db=db)
        if not first['coverage']:
            raise PermissionError('NOT_AUTHORIZED_FOR_DERIVATION')
        fields = {'entities': 'total', 'artifacts': 'artifact_total',
                  'relations': 'relation_total', 'evidence': 'evidence_total'}
        count = max(first[v] for v in fields.values())
        if count > 1000:
            raise ValueError('DIAGNOSTIC_CARDINALITY_LIMIT')
        result = {k: list(first[k]) for k in fields}
        for offset in range(50, count, 50):
            page = self.bundles.query(scope, generate=True, limit=50, offset=offset, _db=db)
            for k in fields:
                result[k].extend(page[k])
        result['coverage'] = first['coverage']
        if digest(self.service.policy_path.read_bytes()) != policy:
            raise PermissionError('POLICY_CHANGED')
        return result, policy

    def _row(self, scope, inputs, policy, code, generated_at):
        snapshot = digest(canonical(inputs))
        identity = digest(canonical(dict(scope=scope, policy=policy, code=code,
                                         snapshot=snapshot, rule='structural-counts/1')))
        row = dict(derivation_id=identity, revision='1', actor='CAIN',
                   method='deterministic_rule', rule_or_algorithm_version='structural-counts/1',
                   code_candidate=code, corpus_snapshot=snapshot, scope=scope,
                   policy_context=policy, generated_at=generated_at,
                   input_entities_with_revisions=[dict(id=e['entity_id'], revision=e['revision'])
                                                 for e in inputs['entities']],
                   source_coverage=inputs['coverage'],
                   assertion=dict(entities=len(inputs['entities']), relations=len(inputs['relations']),
                                  received=sum(a['availability'] == 'received' for a in inputs['artifacts']),
                                  reference_only=sum(a['availability'] == 'reference_only' for a in inputs['artifacts'])),
                   limitations=['Counts over generation-authorized metadata only.',
                                'No scientific inference, learning gain or missing-input reconstruction.',
                                'Not an independent evidence source; experimental and off by default.'],
                   validation_status='STRUCTURAL_ONLY', supersedes_or_invalidates=[])
        return row

    def create(self, scope):
        with self.service.connection() as db:
            # Reserve the writer before reading: all pages and persistence share a snapshot.
            db.execute('BEGIN IMMEDIATE')
            inputs, policy = self._inputs(scope, db)
            code = installed_identity()['source_tree_sha256']
            row = self._row(scope, inputs, policy, code, now())
            db.execute('CREATE TABLE IF NOT EXISTS structural_diagnostics(scope TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scope,id))')
            db.execute('INSERT OR IGNORE INTO structural_diagnostics VALUES(?,?,?)',
                       (scope, row['derivation_id'], canonical(row).decode()))
            if digest(self.service.policy_path.read_bytes()) != policy:
                raise PermissionError('POLICY_CHANGED')
        return self.list(scope)

    def list(self, scope):
        code = installed_identity()['source_tree_sha256']
        with self.service.connection() as db:
            db.execute('BEGIN')
            inputs, policy = self._inputs(scope, db)
            snapshot = digest(canonical(inputs))
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='structural_diagnostics'").fetchone()
            rows = db.execute('SELECT id,payload FROM structural_diagnostics WHERE scope=?', (scope,)).fetchall() if exists else []
        visible = []
        for raw in rows:
            row = json.loads(raw['payload'])
            if (row['policy_context'], row['corpus_snapshot'], row['code_candidate']) == (policy, snapshot, code):
                from datetime import datetime
                try:
                    stamp = datetime.fromisoformat(row['generated_at'])
                    expected = self._row(scope, inputs, policy, code, row['generated_at'])
                    if stamp.tzinfo is None or row != expected or raw['id'] != expected['derivation_id']:
                        raise ValueError('CORRUPTION: diagnostic payload')
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError('CORRUPTION: diagnostic payload') from exc
                visible.append(row)
        if digest(self.service.policy_path.read_bytes()) != policy:
            raise PermissionError('POLICY_CHANGED')
        return dict(classification='DERIVED_EXPERIMENTAL', diagnostics=visible,
                    total=len(visible), default_enabled=False)

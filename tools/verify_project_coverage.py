"""Audit all configured receiver scopes against explicit local producer inventories.

Run against a copied research database and its research-objects directory.
No import, model call, producer write or
permission expansion occurs. Paths outside the receiver are administrator inputs.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from research_bundle import validate, loads
from research_bundle.files import safe_open

from cain.research import ResearchService
from cain.research.analysis import search
from cain.research.bundles import BundleService
from cain.research.coverage import coverage


def input_versions(root, inputs):
    """Explicit administrator paths only; byte drift is not scientific invalidity."""
    versions = []
    for name, expected in sorted(inputs.items()):
        actual = None
        status = 'checkout_not_supplied'
        if root is not None:
            root = Path(root).resolve()
            path = (root / name).resolve()
            status = 'outside_checkout'
            if path.is_relative_to(root):
                try:
                    with path.open('rb') as file:
                        data = file.read(32_000_001)
                    if len(data) > 32_000_000:
                        status = 'not_checked_size_limit'
                    else:
                        actual = hashlib.sha256(data).hexdigest()
                        status = ('present_without_received_hash' if expected is None else
                                  'matches_current_bytes' if actual == expected else
                                  'differs_from_current_bytes')
                except FileNotFoundError:
                    status = 'missing_from_current_checkout'
                except OSError:
                    status = 'unreadable_from_current_checkout'
        versions.append({'source': name, 'received_sha256': expected,
                         'current_sha256': actual, 'current_checkout': status})
    return versions


def publication_version(package, scope, received_at, root, bridge):
    return {'scope': json.loads(scope), 'bridge': bridge,
            'publication_id': package.get('publication_id', package.get('bundle_id')),
            'domain': package['origin']['domain'],
            'code_revision': package['origin']['code_revision'],
            'exported_at': package['exported_at'], 'received_at': received_at,
            'information_clocks': [
                {k: r[k] for k in ('source_id', 'revision', 'event_at', 'recorded_at',
                                  'available_at', 'supersedes')}
                for r in package.get('records', [])],
            'bundle_clocks': 'see authorized entity query' if bridge == 'bundle' else None,
            'source_versions': input_versions(root, package['origin']['inputs']),
            'current_truth': 'not_established',
            'clock_limit': 'Export and receipt time never substitute for information time'}


def audit(db, policy, inventory):
    service = ResearchService(db, policy)
    store = BundleService(service)
    report = {'protocol': 'project-coverage/2', 'scopes': [], 'producers': [],
              'external_exports': [], 'model_calls': 0, 'repository_complete': False,
              'observed_at': datetime.now(timezone.utc).isoformat(), 'publication_revisions': []}
    roots = {p['domain']: Path(p['checkout']).resolve() for p in inventory['projects']}
    original_policy = service.policy_path.read_bytes()
    bindings = service.policy().get('imports', [])
    scopes = sorted({service.scope(b['user'], b['project'], b['collection']) for b in bindings})
    paths_by_domain = {}
    versions_by_domain = {}
    received_ids = set()
    for scope in scopes:
        counts = coverage(service, scope)
        found, evidence_refs, offset = set(), set(), 0
        while True:
            page = service.query(scope, limit=7, offset=offset)
            for record in page['records']:
                assert record['id'] not in found, 'Duplicate row across pages'
                found.add(record['id'])
                exact = service.query(scope, source_id=record['source_id'], limit=50)
                assert record['id'] in {r['id'] for r in exact['records']}
                ranked = search(service, scope, record['source_id'], source_id=record['source_id'], limit=50)
                assert record['id'] in {r['record']['id'] for r in ranked['results']}
                for evidence in record['evidence']:
                    resolved = service.evidence(scope, evidence['reference_id'])
                    assert resolved['text'] == evidence['text']
                    evidence_refs.add(evidence['reference_id'])
            if not page['has_more']:
                break
            offset += 7
        assert len(found) == counts['snapshots']['record_revisions']
        with service.connection() as connection:
            for package in service._archive(connection, scope).values():
                domain = package['origin']['domain']
                received_at = connection.execute(
                    'SELECT received_at FROM publications WHERE scope=? AND id=?',
                    (scope, package['publication_id'])).fetchone()[0]
                report['publication_revisions'].append(publication_version(
                    package, scope, received_at, roots.get(domain), 'snapshot'))
                paths_by_domain.setdefault(domain, set()).update(package['origin']['inputs'])
                versions_by_domain.setdefault(domain, set()).update(package['origin']['inputs'].items())
            for bundle, _ in store._archives(connection, scope):
                received_at = connection.execute(
                    'SELECT received_at FROM research_bundles WHERE scope=? AND id=?',
                    (scope, bundle['bundle_id'])).fetchone()[0]
                report['publication_revisions'].append(publication_version(
                    bundle, scope, received_at, roots.get(bundle['origin']['domain']), 'bundle'))
                paths_by_domain.setdefault(bundle['origin']['domain'], set()).update(bundle['origin']['inputs'])
                versions_by_domain.setdefault(bundle['origin']['domain'], set()).update(bundle['origin']['inputs'].items())
                received_ids.add(bundle['bundle_id'])
        checked = Counter()
        offset = 0
        while True:
            page = store.query(scope, limit=7, offset=offset)
            for entity in page['entities']:
                for bid in entity['bundles']:
                    assert store.entity(scope, bid, entity['entity_id'], entity['revision'])['entities']
                checked['entities'] += 1
            for artifact in page['artifacts']:
                result = store.artifact(scope, artifact['bundle_id'], artifact['artifact_id'])['artifact']
                assert result == artifact
                if artifact['availability'] == 'received':
                    store.objects.verify(artifact['sha256'], artifact['size'])
                checked['artifacts'] += 1
            for evidence in page['evidence']:
                store.evidence(scope, evidence['bundle_id'], evidence['id'])
                checked['evidence'] += 1
            checked['relations'] += len(page['relations'])
            if offset + 7 >= max(page['total'], page['artifact_total'], page['evidence_total'], page['relation_total']):
                break
            offset += 7
        assert checked['entities'] == counts['bundles']['entity_revisions']
        assert checked['artifacts'] == counts['bundles']['artifacts']
        assert checked['evidence'] == counts['bundles']['evidence']
        assert checked['relations'] == counts['bundles']['relations']
        user, project, collection = json.loads(scope)
        other = coverage(service, service.scope('coverage-ungranted-user', project, collection))
        assert other['snapshots']['publications'] == other['bundles']['publications'] == 0
        receipts = service.receipts(scope)
        report['scopes'].append({'scope': json.loads(scope), 'coverage': counts,
            'snapshot_receipt_diagnostics': {
                'last_100_status_counts': dict(Counter(r['status'] for r in receipts)),
                'recent': [{k: r[k] for k in ('id', 'at', 'status')} for r in receipts[:10]],
                'limitation': 'Receiver attempts only; unattempted producer updates are not detectable'},
            'snapshot_records_retrieved': len(found), 'snapshot_evidence_resolved': len(evidence_refs),
            'bundle_items_checked': dict(checked), 'ungranted_user_empty': True})
    for project in inventory['projects']:
        root = Path(project['checkout']).resolve()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args])
        tracked = set(git('ls-files', '-z').decode('utf-8').strip('\0').split('\0'))
        declared = paths_by_domain.get(project['domain'], set())
        versions = []
        # Preserve multiple historical hashes for the same path.
        for name, expected in sorted(versions_by_domain.get(project['domain'], set())):
            versions.extend(input_versions(root, {name: expected}))
        needs = []
        for expected in project.get('expected_sources', []):
            name = expected['path']
            needs.append({**input_versions(root, {name: None})[0],
                          'knowledge_need': expected['need'],
                          'declared_in_received_inputs': name in declared,
                          'content_coverage': 'not_established_by_filename',
                          'permission_change': False})
        report['producers'].append({'domain': project['domain'], 'checkout': str(root),
            'head': git('rev-parse', 'HEAD').decode().strip(),
            'tracked_files': len(tracked), 'receiver_declared_input_files': sorted(declared),
            'tracked_files_not_declared_in_received_inputs': len(tracked - declared),
            'examples_not_declared': sorted(tracked - declared)[:20],
            'received_source_versions': versions, 'expected_sources': needs,
            'repository_complete': False,
            'limitation': 'Filename inventory only; untracked data and partial file excerpts are not full content coverage'})
    for filename in inventory.get('bundles', []):
        path = Path(filename)
        bundle = validate(loads(path.read_bytes()))
        payloads = []
        for artifact in bundle['artifacts']:
            status = artifact['availability']
            if status == 'received':
                try:
                    with safe_open(path.parent, artifact['relative_path']) as file:
                        data = file.read(artifact['size'] + 1)
                    status = ('verified_bytes' if len(data) == artifact['size'] and
                              hashlib.sha256(data).hexdigest() == artifact['sha256'] else 'payload_mismatch')
                except (OSError, ValueError):
                    status = 'payload_unavailable'
            payloads.append({'artifact_id': artifact['artifact_id'], 'status': status})
        report['external_exports'].append({'path': str(path), 'bundle_id': bundle['bundle_id'],
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'domain': bundle['origin']['domain'], 'already_received': bundle['bundle_id'] in received_ids,
            'entities': len(bundle['entities']), 'artifacts': len(bundle['artifacts']),
            'artifact_availability': dict(Counter(a['availability'] for a in bundle['artifacts'])),
            'payload_checks': payloads,
            'coverage': bundle['coverage'], 'restrictions': bundle['restrictions']})
    assert service.policy_path.read_bytes() == original_policy, 'Policy changed during audit'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('db', 'policy', 'inventory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.db, args.policy, json.loads(args.inventory.read_bytes()))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'scopes': len(result['scopes']), 'repository_complete': False,
                      'output': str(args.output)}))

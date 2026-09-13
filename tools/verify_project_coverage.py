"""Audit all configured receiver scopes against explicit local producer inventories.

Run against a copied research database and its research-objects directory.
No import, model call, producer write or
permission expansion occurs. Paths outside the receiver are administrator inputs.
"""
import argparse
from collections import Counter
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


def audit(db, policy, inventory):
    service = ResearchService(db, policy)
    store = BundleService(service)
    report = {'protocol': 'project-coverage/1', 'scopes': [], 'producers': [],
              'external_exports': [], 'model_calls': 0, 'repository_complete': False}
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
                paths_by_domain.setdefault(domain, set()).update(package['origin']['inputs'])
                versions_by_domain.setdefault(domain, set()).update(package['origin']['inputs'].items())
            for bundle, _ in store._archives(connection, scope):
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
        report['scopes'].append({'scope': json.loads(scope), 'coverage': counts,
            'snapshot_records_retrieved': len(found), 'snapshot_evidence_resolved': len(evidence_refs),
            'bundle_items_checked': dict(checked), 'ungranted_user_empty': True})
    for project in inventory['projects']:
        root = Path(project['checkout']).resolve()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args])
        tracked = set(git('ls-files', '-z').decode('utf-8').strip('\0').split('\0'))
        declared = paths_by_domain.get(project['domain'], set())
        versions = []
        for name, expected in sorted(versions_by_domain.get(project['domain'], set())):
            path = (root / name).resolve()
            status = 'outside_checkout'
            if path.is_relative_to(root):
                status = 'missing_from_current_checkout'
                if path.is_file():
                    status = 'not_checked_size_limit'
                    if path.stat().st_size <= 32_000_000:
                        actual = hashlib.sha256(path.read_bytes()).hexdigest()
                        status = 'matches_current_bytes' if actual == expected else 'differs_from_current_bytes'
            versions.append({'source': name, 'received_sha256': expected, 'current_checkout': status})
        report['producers'].append({'domain': project['domain'], 'checkout': str(root),
            'head': git('rev-parse', 'HEAD').decode().strip(),
            'tracked_files': len(tracked), 'receiver_declared_input_files': sorted(declared),
            'tracked_files_not_declared_in_received_inputs': len(tracked - declared),
            'examples_not_declared': sorted(tracked - declared)[:20],
            'received_source_versions': versions,
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

"""Scoped coverage of both bridges; receipt counts never imply a whole repository."""

from collections import Counter

from research_snapshot import canonical, digest

from cain.research.bundles import BundleService


def coverage(service, scope):
    policy_hash = digest(service.policy_path.read_bytes())
    bundles = BundleService(service)
    with service.connection() as db:
        db.execute('BEGIN')
        archives = service._archive(db, scope)
        service._verify_projection(db, scope, archives)
        generated = service._archive(db, scope, generate=True)
        records = {service.projection(p, r)[0] for p in archives.values() for r in p['records']}
        generation_records = {service.projection(p, r)[0] for p in generated.values() for r in p['records']}
        bundle_result = bundles.query(scope, limit=1, _db=db)
        bundle_generation = bundles.query(scope, limit=1, generate=True, _db=db)
        admitted = bundles._archives(db, scope)
        availability = Counter(a['availability'] for p, grants in admitted for a in p['artifacts']
                               if bundles.resource_allowed(a, grants))
        snapshot_coverage = [{'publication_id': key, **p['coverage']} for key, p in archives.items()]
        result = {
            'basis': 'received_authorized_publications',
            'repository_coverage': 'not_established',
            'total_record_revisions': len(records),
            'coverage': snapshot_coverage,
            'snapshots': {
                'publications': len(archives), 'record_revisions': len(records),
                'generation_record_revisions': len(generation_records),
                'source_files': sorted({e['source'] for p in archives.values() for e in p['evidence']}),
            },
            'bundles': {
                'publications': len(admitted), 'entity_revisions': bundle_result['total'],
                'generation_entity_revisions': bundle_generation['total'],
                'artifacts': bundle_result['artifact_total'],
                'artifact_availability': dict(sorted(availability.items())),
                'relations': bundle_result['relation_total'],
                'evidence': bundle_result['evidence_total'],
                'source_files': sorted({name for p, _ in admitted for name in p['origin']['inputs']}),
            },
            'bundle_coverage': bundle_result['coverage'],
            'workflow_input': 'snapshots_only',
            'limitations': [
                'Coverage describes received publications, not every file in the producer repository',
                'Record revisions and entity revisions are not publication or independent experiment counts',
                'A reference-only artifact does not mean its payload was received',
                'Read permission does not imply generation permission',
                'Six-step workflows currently consume Snapshot evidence; Bundle metadata has separate tools',
                'No model comprehension, source freshness or scientific validity is attested',
            ],
        }
    if digest(service.policy_path.read_bytes()) != policy_hash:
        raise ValueError('Policy changed during coverage inspection; retry')
    result['policy_sha256'] = policy_hash
    if len(canonical(result)) > 1_000_000:
        raise ValueError('Coverage exceeds 1000000 bytes; split the admitted collection')
    return result

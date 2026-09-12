"""Real public reports -> installed exporters -> installed CAIN -> offline restore.

Receiver grants are copied unchanged from the existing owner policy; only disposable
import bindings are relocated. No scientific runtime, provider, or new grant.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

roots_file, area, producer, receiver = map(Path, sys.argv[1:])
roots = {k: Path(v) for k, v in json.loads(roots_file.read_text()).items()}
area.mkdir()
policy = json.loads((Path(__file__).parent / 'existing-policy.json').read_text())
original_grants = policy['grants']
for binding in policy['imports']:
    binding['root'] = str(area / 'exports' / binding['collection'])
policy_path = area / 'policy.json'
policy_path.write_text(json.dumps(policy))
receipts = []

def run(command):
    result = subprocess.run(list(map(str, command)), cwd=area, capture_output=True, timeout=60)
    receipts.append(dict(command=list(map(str, command)), returncode=result.returncode,
                         stdout=result.stdout.decode(), stderr=result.stderr.decode()))
    (area / 'commands.json').write_text(json.dumps(receipts, indent=2))
    assert result.returncode == 0, receipts[-1]
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.decode().strip()

def cli(domain, *args, database='research.db', selected_policy=policy_path):
    return run([receiver, '-m', 'cain', 'research', '--db', area / database,
                '--policy', selected_policy, '--collection', domain, *args])

sources = {'crypto': ['charters/scientific_state.json', 'docs/EVIDENCE_REGISTRY.md'],
           'stocks': ['STOCKS_CURRENT_STATE.md'], 'brasileirao': ['docs/EVIDENCE_REGISTRY.md']}
hashes = {}
counts = {}
for domain, names in sources.items():
    root = roots[domain]
    hashes[domain] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    target = area / 'exports' / domain / 'publication.json'
    if domain == 'crypto':
        admission = dict(policy='crypto-frozen-reports-local/1', read=True, sources=hashes[domain],
                         code_revision=subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip(),
                         exporter_revision='sha256:' + hashlib.sha256((root / 'packages/research-export/src/crypto_research_export/__init__.py').read_bytes()).hexdigest())
        admission_path = area / 'crypto-admission.json'
        admission_path.write_text(json.dumps(admission))
        run([producer, '-c', 'from crypto_research_export import main; raise SystemExit(main())',
             '--root', root, '--admission', admission_path, '--output', target,
             '--exported-at', '2026-09-12T00:00:00Z'])
    else:
        run([producer, root / 'tools/export_cain_status.py', '--root', root,
             '--expected-sha', hashes[domain][names[0]], '--output', target,
             '--exported-at', '2026-09-12T00:00:00Z'])
    cli(domain, 'import', 'publication.json')
    queried = cli(domain, 'query', '--limit', '50')
    package = json.loads(target.read_bytes())
    assert queried['total_record_revisions'] == len(package['records']) > 0
    counts[domain] = queried['total_record_revisions']
    cli(domain, 'verify')
cli('crypto', 'backup', area / 'backup.db')
run([receiver, '-m', 'cain', 'research', 'restore', area / 'backup.db', area / 'restored.db'])
for binding in policy['imports']:
    binding['root'] = str(area / 'UNAVAILABLE' / binding['collection'])
assert policy['grants'] == original_grants
offline = area / 'offline-policy.json'
offline.write_text(json.dumps(policy))
for domain, count in counts.items():
    q = cli(domain, 'query', '--limit', '50', database='restored.db', selected_policy=offline)
    assert q['total_record_revisions'] == count
    cli(domain, 'evidence', q['records'][0]['evidence'][0]['reference_id'], database='restored.db', selected_policy=offline)
    for name, expected in hashes[domain].items():
        assert hashlib.sha256((roots[domain] / name).read_bytes()).hexdigest() == expected
(area / 'evidence.json').write_text(json.dumps(dict(status='PASS', counts=counts,
    sources=hashes, scope='Real committed public Snapshot reports; not scientific DB or Bundle export',
    grants_unchanged=True, offline_restore=True), indent=2))

# Exercise the actual Bundle exporters too, without a scientific database or pipeline.
bundle_policy = json.loads((Path(__file__).parent / 'existing-bundle-policy.json').read_text())
for binding in bundle_policy['imports']:
    domain = binding['collection']
    binding['root'] = str(roots[domain].parent / 'exports' / domain if domain in roots
                          else area / 'exports' / domain)
bp = area / 'bundle-policy.json'
bp.write_text(json.dumps(bundle_policy))
bundle_sources = {
    'crypto': ['charters/scientific_state.json', 'GarimpoInvestimentos/trials.json',
               'GarimpoInvestimentos/trials.harness_attestation.json',
               'GarimpoInvestimentos/trials.phase1_harness_attestation.json'],
    'brasileirao': ['docs/EVIDENCE_REGISTRY.md', 'reports/replay_round_2026_08_22.json'],
    'stocks': ['docs/engineering/2026-09-11-architecture/evidence/real-v020.json'],
}
bundle_receipts = {}
for domain, names in bundle_sources.items():
    root = roots[domain]
    pins = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in names}
    target = root.parent / 'exports' / domain / 'bundle'
    command = ([producer, '-m', 'crypto_research_export.bundle'] if domain == 'crypto'
               else [producer, root / 'tools/export_cain_bundle.py'])
    command += ['--root', root, '--expected-sha', pins[names[0]], '--destination', target,
                '--exported-at', '2026-09-12T00:00:00Z']
    if domain == 'crypto':
        command += ['--trials-sha', pins[names[1]]]
        for n in names[2:]:
            command += ['--attestation-sha', n + '=' + pins[n]]
    if domain == 'brasileirao':
        command += ['--replay-sha', pins[names[1]]]
    run(command)
    package = json.loads((target / 'bundle.json').read_bytes())
    cli(domain, 'bundle', 'approve', 'bundle/bundle.json', selected_policy=bp)
    cli(domain, 'bundle', 'import', 'bundle/bundle.json', selected_policy=bp)
    q = cli(domain, 'bundle', 'query', '--limit', '50', selected_policy=bp)
    assert q['total'] == len(package['entities']) > 0
    assert q['relation_total'] == len(package['relations'])
    cli(domain, 'bundle', 'verify', selected_policy=bp)
    bundle_receipts[domain] = dict(entities=q['total'], relations=q['relation_total'],
                                  bundle_id=package['bundle_id'], pins=pins, received=0)
run([receiver, '-c', 'from cain.workspace import WorkspaceStore; import sys; WorkspaceStore(sys.argv[1]); print("{}")', area / 'workspace.db'])
run([receiver, '-m', 'cain', 'archive', 'backup', '--workspace', area / 'workspace.db',
     '--research', area / 'research.db', '--policy', bp, area / 'bundle-backup'])
run([receiver, '-m', 'cain', 'archive', 'restore', area / 'bundle-backup', area / 'bundle-restored'])
for binding in bundle_policy['imports']:
    binding['root'] = str(area / 'UNAVAILABLE-BUNDLE' / binding['collection'])
offline_bundle = area / 'offline-bundle-policy.json'
offline_bundle.write_text(json.dumps(bundle_policy))
for domain, receipt in bundle_receipts.items():
    db = 'bundle-restored/research.db'
    q = cli(domain, 'bundle', 'query', '--limit', '50', database=db, selected_policy=offline_bundle)
    assert q['total'] == receipt['entities'] and q['relation_total'] == receipt['relations']
    cli(domain, 'bundle', 'verify', database=db, selected_policy=offline_bundle)
    for a in q['artifacts']:
        if a['availability'] != 'received':
            continue
        destination = area / ('materialized-' + domain + '-' + str(receipt['received']))
        cli(domain, 'bundle', 'materialize', a['bundle_id'], a['artifact_id'], destination,
            database=db, selected_policy=offline_bundle)
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == a['sha256']
        receipt['received'] += 1
    for name, expected in receipt['pins'].items():
        assert hashlib.sha256((roots[domain] / name).read_bytes()).hexdigest() == expected
(area / 'bundle-evidence.json').write_text(json.dumps(dict(status='PASS', domains=bundle_receipts,
    grants_unchanged=True, offline_restore=True, scientific_calls=0,
    scope='Real charter/trials/existing attestations, retrospective BR report, Stocks catalog metadata; no source database opened'), indent=2))

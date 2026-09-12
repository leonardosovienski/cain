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
    return json.loads(result.stdout)

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

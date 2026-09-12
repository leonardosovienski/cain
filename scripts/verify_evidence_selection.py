"""Narrow offline comparison of compact relations and selected JSON fields.

Only an isolated SQLite backup is writable. No model or arbitrary code is run.
Start and resume are separate processes using existing CAIN workflow receipts.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from cain.research import ResearchService
from cain.research.analysis import fingerprint, guard
from cain.research.grounding import cards, structured
from cain.research.workflows import Workflows
from research_snapshot import canonical, digest


class NoInference:
    model = 'deterministic-no-inference'


def offline_boundary(root):
    """Effective Python audit boundary for this fixed trusted procedure, not a code sandbox."""
    def audit(event, args):
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system'}:
            raise PermissionError('Offline verification forbids network and child processes')
        if event == 'sqlite3.connect' and Path(args[0]).resolve() != root / 'research.db':
            raise PermissionError('Only isolated workflow database may be opened')
        if event == 'open':
            path, mode, flags = args
            if isinstance(path, (str, bytes)) and ((isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & 0x703):
                if not Path(path).resolve().is_relative_to(root):
                    raise PermissionError('Write outside isolated output')
    sys.addaudithook(audit)


def run(args):
    root = Path(args.output).resolve()
    if args.phase == 'start':
        if not args.database or not args.policy or not args.identity or not args.pointer:
            raise ValueError('Start requires database, policy, identity and expected JSON pointers')
        root.mkdir(parents=True, exist_ok=False)
        with sqlite3.connect(Path(args.database).resolve().as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(root/'research.db') as target:
            src.backup(target)
        manifest = {'protocol': 'selection-comparison/2', 'implementation_sha256': digest(Path(__file__).read_bytes()), 'identity': args.identity,
                    'pointers': args.pointer, 'policy': str(Path(args.policy).resolve()),
                    'policy_sha256': digest(Path(args.policy).read_bytes()),
                    'source_database': str(Path(args.database).resolve()),
                    'objective': 'Compare exact expected JSON fields in compact extraction and selected evidence',
                    'pending': 'search_and_verify', 'scope': {'user': args.user, 'collection': args.collection}}
        (root/'task.json').write_bytes(canonical(manifest))
    else:
        manifest = json.loads((root/'task.json').read_bytes())
    if manifest.get('implementation_sha256') != digest(Path(__file__).read_bytes()):
        raise ValueError('Procedure implementation changed; preserve receipt and start a new task')
    offline_boundary(root)
    if digest(Path(manifest['policy']).read_bytes()) != manifest['policy_sha256']:
        raise ValueError('Policy changed; procedure is no longer applicable')
    service = ResearchService(root/'research.db', manifest['policy'])
    scope = service.scope(**manifest['scope'])
    jobs = Workflows(service)
    question = 'Compare ' + manifest['identity'] + ' ' + ' '.join(manifest['pointers'])
    if args.phase == 'start':
        job = jobs.create(scope, question, NoInference(), source_id=manifest['identity'],
                          steps=['inspect', 'search'], run_id='selection-comparison')
        job = jobs.advance(scope, job['id'], NoInference())
        (root/'checkpoint.json').write_bytes(canonical(job))
        print('Inspection persisted; resume in a new process.')
        return
    job = jobs.get(scope, 'selection-comparison')
    if job['status'] == 'cancelled':
        raise ValueError('Cancelled task cannot be resumed')
    if (root/'verification.json').exists():
        print('Verified receipt already exists; no effect repeated.')
        return
    job = jobs.advance(scope, job['id'], NoInference())
    if job['status'] != 'completed':
        raise ValueError('Workflow did not complete')
    snapshot = fingerprint(service, scope)
    dossier = job['steps'][0]['result']
    evidence = {e['reference_id']: e for e in dossier['evidence'] if e['availability'] == 'received'}
    # Multiple authorized publications may carry byte-identical source versions.
    # Compare one representative of that exact version, retaining duplicate refs.
    duplicates, seen, unique = {}, {}, {}
    for ref, item in evidence.items():
        text = item['text']
        if text in seen:
            duplicates[ref] = seen[text]
        else:
            seen[text] = ref
            unique[ref] = item
    evidence = unique
    selected, coverage = cards(evidence, question, manifest['identity'])
    compact = structured({ref: e['text'] for ref, e in evidence.items()}, manifest['identity'])
    # Independent verifier: JSON pointer lookup + original UTF-8 source digest + exact offsets.
    expected = {}
    for ref, e in evidence.items():
        if digest(e['text'].encode()) != e['sha256']:
            raise ValueError('Source digest mismatch')
        data = json.loads(e['text'])
        for pointer in manifest['pointers']:
            value = data
            for part in pointer.split('/')[1:]:
                part = part.replace('~1', '/').replace('~0', '~')
                value = value[int(part)] if isinstance(value, list) else value[part]
            expected[(ref, pointer)] = value
    if not expected or len(expected) != len(manifest['pointers']):
        raise ValueError('Expected exactly one source per pointer; absent or ambiguous input')
    for row in selected.values():
        if evidence[row['reference']]['text'][row['start']:row['end']] != row['quote']:
            raise ValueError('Nonliteral selection')
    selected_keys = {(row['reference'], row.get('json_pointer')) for row in selected.values()}
    compact_keys = {(row['reference'], row.get('json_pointer')) for row in compact['relations']}
    verified = all(key in selected_keys for key in expected)
    guard(service, scope, snapshot)
    report = {'procedure': 'selection-comparison/2', 'verified': verified,
              'expected_fields': len(expected), 'selected_expected_fields': sum(k in selected_keys for k in expected),
              'compact_expected_fields': sum(k in compact_keys for k in expected),
              'units': 'literal JSON fields, not semantic claims', 'selected': selected,
              'coverage': coverage, 'workflow': job, 'source_versions': {ref: e['sha256'] for ref,e in evidence.items()},
              'identical_source_references': duplicates,
              'model_calls': 0, 'semantic_support': 'not_evaluated', 'network': 'blocked_by_python_audit_hook'}
    (root/'verification.json').write_bytes(canonical(report))
    if not verified:
        raise ValueError('Required fields missing; procedure remains unverified for this case')
    print('Verified exact fields:', len(expected), '; no inference.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['start', 'resume'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--database')
    parser.add_argument('--policy')
    parser.add_argument('--identity')
    parser.add_argument('--pointer', action='append')
    parser.add_argument('--user', default='leo')
    parser.add_argument('--collection', default='crypto')
    run(parser.parse_args())

"""Finite CAIN campaign: source reading plus explicit historical reproductions.

No inference, parameter search, trading, downloads or producer database writes.
Run with an installed CAIN Python. Results are not new independent evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from cain.research import ResearchService
from cain.research.workflows import Workflows
from cain.research.grounding import matches_identity, structured


class LiteralOnly:
    model = 'literal-only/no-inference'
    base_url = 'http://127.0.0.1'

    def generate_json(self, *args, **kwargs):
        raise ValueError('Interpretation is not approved in this campaign')


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compare_r5(original, reproduction):
    def rows(path):
        return [row for line in path.read_text(encoding='utf-8').splitlines()
                if (row := json.loads(line)).get('kind') == 'VALUATION']
    first, second = rows(original), rows(reproduction)
    if len(first) != 24 or len(second) != 24:
        raise ValueError('Expected every one of the 24 registered valuations')
    if first != second or any('error' in row for row in second):
        raise ValueError('Historical valuation, ledger, curve or verification differs')
    return dict(status='identical', valuations=24,
                daily_points=sum(len(row['result'].get('curve', [])) for row in second),
                infeasible=sum(row['result']['status'] == 'INFEASIBLE_EXPENSE_RESERVE' for row in second),
                new_independent_evidence=False)


def dossiers(service, scope):
    """Keep every matching native field/revision, not a model-sized excerpt set."""
    result = {f'H{n}': dict(fields=[], limitations=[], semantic_validation='not_established')
              for n in range(1, 23)}
    offset, seen = 0, set()
    while True:
        page = service.query(scope, generate=True, limit=50, offset=offset)
        for record in page['records']:
            for evidence in record['evidence']:
                ref = evidence['reference_id']
                if ref in seen or evidence['availability'] != 'received':
                    continue
                seen.add(ref)
                native = structured({ref: evidence['text']}, addressable=True)
                for identity, dossier in result.items():
                    for row in native['relations']:
                        if (matches_identity(row, identity)
                                or row.get('decoded_subject') == identity+'_executed'):
                            dossier['fields'].append(dict(source=evidence['source'], reference=ref,
                                                          source_sha256=hashlib.sha256(evidence['text'].encode()).hexdigest(),
                                                          relation=row))
                    if native['has_more'] or native['issues']:
                        dossier['limitations'].append(dict(source=evidence['source'],
                                                           partial=native['has_more'], issues=native['issues']))
        if not page['has_more']:
            return result
        offset += 50
        if offset >= 2000:
            raise ValueError('Campaign exceeds 2000 records; split the corpus')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stocks-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--user', default='leo')
    parser.add_argument('--qa', action='store_true', help='Use a consistent database copy')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    root, output = args.stocks_root.resolve(), args.output.resolve()
    if root != Path('C:/STOCKS/stocks-predictor').resolve():
        raise ValueError('This runner is reviewed for the canonical local Stocks checkout')
    if not output.is_relative_to(root.parent/'work'):
        raise ValueError('Campaign output must stay under Stocks/work')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root).strip():
        raise ValueError('Producer checkout must be clean')
    output.mkdir(exist_ok=False, parents=True)
    db = args.db
    if args.qa:
        db = output/'qa.db'
        with sqlite3.connect(args.db.resolve().as_uri()+'?mode=ro', uri=True) as source:
            with sqlite3.connect(db) as target:
                source.backup(target)
    service = ResearchService(db, args.policy)
    scope = service.scope(args.user, '', 'stocks')
    workflows, provider = Workflows(service), LiteralOnly()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), producer_head=head,
                   runner_sha256=sha(Path(__file__)),
                   database=str(db), qa=args.qa, jobs=[], checks=[],
                   scientific_validation='not_established', model_interpretation='not_executed',
                   future_observations=0, independent_experiments=0)
    save(output/'started.json', receipt)
    for identity, dossier in dossiers(service, scope).items():
        save(output/(identity+'-dossier.json'), dossier)
    families = json.loads((root/'docs/research/2026-09-07-prior-hypotheses-review.json').read_text(encoding='utf-8'))['families']
    legacy = {row['hypothesis'] for row in families}
    for number in range(1, 23):
        identity = 'H'+str(number)
        question = f'Qual hipótese, critério, resultado e limitações documentados para {identity}?'
        steps = ['search']
        if identity in legacy:
            question = ('No documento docs/research/2026-09-07-prior-hypotheses-review.json, '
                        'mostre historical_official_verdict_preserved, updated_reliability '
                        f'e execution_ready_alpha_evidence de {identity}.')
            steps.append('support')
        job_id = args.run_id+'-'+identity
        try:
            job = workflows.create(scope, question, provider, steps=steps, run_id=job_id)
            while job['status'] != 'completed':
                job = workflows.advance(scope, job_id, provider, approve_generation=True)
            if job['model_calls'] != 0:
                raise ValueError('Unexpected inference')
            save(output/(identity+'-job.json'), job)
            receipt['jobs'].append(dict(identity=identity, job_id=job_id, status=job['status'],
                                        scope='literal_fields' if identity in legacy else 'source_search',
                                        scientific_validation='not_established'))
        except Exception as exc:
            receipt['jobs'].append(dict(identity=identity, job_id=job_id, status='failed', error=repr(exc)))
        print(json.dumps(receipt['jobs'][-1]), flush=True)
    checks = [
        ('monthly-tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_monthly_etf.py', '-v']),
        ('hold-tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_etf_hold.py', '-v']),
        ('H21-reproduction', ['research/session-20260909/h21/reproduce_check.py',
                             str(root.parent/'work/h21'), str(output/'H21-reproduction.json')]),
        ('H22-reproduction', ['research/session-20260910/profit_validation/run.py',
                             str(root.parent/'work/profit-validation-r5-20260910'),
                             str(root.parent/'work/profit-validation-r5-20260910'/(args.run_id+'.jsonl'))]),
    ]
    for name, command in checks:
        entry = dict(name=name, command=[sys.executable, '-B', *command], cwd=str(root))
        save(output/(name+'-started.json'), entry)
        try:
            with (output/(name+'.log')).open('x', encoding='utf-8') as log:
                run = subprocess.run(entry['command'], cwd=root, stdout=log, stderr=log, timeout=600)
            entry.update(exit_code=run.returncode, status='passed' if run.returncode == 0 else 'failed')
            if name == 'H22-reproduction' and run.returncode == 0:
                base = root.parent/'work/profit-validation-r5-20260910'
                entry['comparison'] = compare_r5(base/'attempt01.jsonl', base/(args.run_id+'.jsonl'))
                entry['result_sha256'] = sha(base/(args.run_id+'.jsonl'))
        except Exception as exc:
            entry.update(status='failed', error=repr(exc))
        receipt['checks'].append(entry)
        save(output/(name+'-receipt.json'), entry)
        print(json.dumps(entry), flush=True)
    receipt['producer_clean_after'] = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=root).strip()
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    receipt['complete'] = all(x['status'] == 'completed' for x in receipt['jobs']) and all(x['status'] == 'passed' for x in receipt['checks'])
    save(output/'campaign.json', receipt)
    return 0 if receipt['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

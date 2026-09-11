"""Exercise six-step workflows on an isolated copy of admitted real archives."""

import argparse
import json
from pathlib import Path

from cain import __version__
from cain.providers import configured_llm
from cain.research import ResearchService
from cain.research.workflows import Workflows
from cain.settings import load_settings
from research_snapshot import canonical


def run(db, policy, config, protocol, output):
    output.mkdir(parents=True, exist_ok=False)
    original = ResearchService(db, policy)
    original.backup(output / 'evaluation.db')
    service = ResearchService(output / 'evaluation.db', policy)
    model = configured_llm(load_settings(config))
    report = {'version': __version__, 'workflows': [], 'economic_validation': False}
    def stable(query):
        return {key: query[key] for key in ('records', 'total_record_revisions', 'coverage')}
    for case in json.loads(protocol.read_bytes())['cases'][::2]:
        scope = service.scope(collection=case['collection'])
        before = stable(service.query(scope, limit=50))
        job = Workflows(service).create(scope, case['question'], model, source_id=case['source_id'])
        row = {'collection': case['collection'], 'job': job}
        report['workflows'].append(row)
        for _ in range(6):
            try:
                job = Workflows(ResearchService(output / 'evaluation.db', policy)).advance(
                    scope, job['id'], model, approve_generation=True)
                row['job'] = job
                print(json.dumps({'collection': case['collection'], 'status': job['status'],
                                  'steps': len(job['steps'])}), flush=True)
            except Exception as exc:
                row['error'] = {'type': type(exc).__name__, 'message': str(exc)}
                break
            finally:
                (output / 'report.json').write_bytes(canonical(report))
        row['states_preserved'] = before == stable(service.query(scope, limit=50))
        assert row['states_preserved']
        (output / 'report.json').write_bytes(canonical(report))
    return {'version': __version__, 'output': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('db', 'policy', 'config', 'protocol', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    print(json.dumps(run(**vars(parser.parse_args()))))

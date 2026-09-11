"""Per-identity development retest on a read-only backup; never a financial experiment."""

import argparse
import base64
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
from time import perf_counter
from urllib.request import urlopen

from cain import __version__
from cain.llm.streaming import stream
from cain.providers import configured_embedding, configured_llm
from cain.research import ResearchService
from cain.research.analysis import review, search
from cain.research.workflows import Workflows
from cain.search.embeddings import SQLiteEmbeddingCache
from cain.settings import load_settings
from research_snapshot import canonical, digest


class RecordingProvider:
    def __init__(self, provider):
        self.provider, self.calls = provider, []

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def generate_json(self, prompt, context, schema):
        row = {"prompt": prompt, "context": context, "schema": schema}
        self.calls.append(row)
        try:
            row['response'] = self.provider.generate_json(prompt, context, schema)
            row['metadata'] = self.provider.last_metadata
            return row['response']
        except Exception as exc:
            row['error'] = {"type": type(exc).__name__, "message": str(exc)}
            raise


def copy_database(source, target):
    # Opening ResearchService on the operational database could perform migrations.
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(target) as copied:
            original.backup(copied)


def stable(service, scope):
    query = service.query(scope, limit=50)
    return {key: query[key] for key in ('records', 'total_record_revisions', 'coverage')}


def run(protocol, config, db, policy, output, workflows=True):
    output.mkdir(parents=True, exist_ok=False)
    plan = json.loads(protocol.read_bytes())
    settings = load_settings(config)
    copy_database(db, output / 'evaluation.db')
    service = ResearchService(output / 'evaluation.db', policy)
    collections = sorted({c['collection'] for c in plan['cases']})
    before = {c: stable(service, service.scope(collection=c)) for c in collections}
    report = {'version': __version__, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'protocol': plan, 'protocol_sha256': digest(protocol.read_bytes()),
              'economic_validation': False, 'models': [], 'embedding': {}}
    report['source_commit'] = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True, cwd=Path(__file__).resolve().parents[1]).strip()
    report['source_sha256'] = {str(path.relative_to(Path(__file__).resolve().parents[1])): digest(path.read_bytes())
                               for path in sorted((Path(__file__).resolve().parents[1] / 'src/cain').rglob('*.py'))}

    def save():
        (output / 'report.json').write_bytes(canonical(report))

    for endpoint in ('tags', 'version'):
        with urlopen(settings.base_url + '/api/' + endpoint, timeout=10) as response:
            report['ollama_' + endpoint] = json.load(response)
    save()
    for model_name in plan['models']:
        provider = RecordingProvider(configured_llm(replace(settings, model=model_name)))
        result = {'model': model_name, 'cases': [], 'workflows': [], 'calls': provider.calls}
        report['models'].append(result)
        for case in plan['cases']:
            row = {'case': case}
            result['cases'].append(row)
            start = perf_counter()
            try:
                scope = service.scope(collection=case['collection'])
                answer = review(service, scope, case['question'], provider,
                                role='synthesis', source_id=case['source_id'])
                row['review'] = answer
                row['record_identity_preserved'] = all(
                    r['source_id'] == case['source_id'] and
                    r['source_status'] == case['expected_source_status']
                    for r in answer['facts']['records']) and bool(answer['facts']['records'])
                explanation = answer.get('explanation') or {}
                text = explanation.get('proposed_synthesis', '')
                quotes = explanation.get('source_quotes', [])
                row['exact_citations'] = bool(quotes) and all(
                    q['support']['text'][q['start']:q['end']] == q['quote'] for q in quotes)
                row['literal_state_mentioned'] = case['expected_source_status'].strip() in text
                row['other_hypothesis_labels'] = sorted(set(re.findall(r'\bH[1-9]\b', text)) -
                                                        {case['source_id']}) if re.fullmatch(r'H[1-9]', case['source_id']) else []
            except Exception as exc:
                row['error'] = {'type': type(exc).__name__, 'message': str(exc)}
            row['elapsed'] = perf_counter() - start
            save()
            print(json.dumps({'model': model_name, 'id': case['source_id'],
                              'status': row.get('review', {}).get('status'),
                              'other_ids': row.get('other_hypothesis_labels'),
                              'error': row.get('error'), 'seconds': row['elapsed']}), flush=True)
        count = len(provider.calls)
        result['absent'] = review(service, service.scope(collection=collections[0]),
                                  'O que a fonte informa?', provider, role='synthesis',
                                  source_id='ABSENT-INDIVIDUAL-VALIDATION')
        result['absent_zero_calls'] = len(provider.calls) == count
        try:
            events = list(stream(provider, 'Responda apenas OK.'))
            result['stream'] = {'terminal_done': events[-1]['type'] == 'done', 'events': events}
        except Exception as exc:
            result['stream'] = {'error': str(exc), 'type': type(exc).__name__}
        if model_name == 'qwen3.5:0.8b':
            from PIL import Image
            buf = BytesIO()
            Image.new('RGB', (64, 64), (255, 0, 0)).save(buf, format='PNG')
            try:
                events = list(stream(provider, 'What color fills this image? Answer with one English word.',
                                     images=[base64.b64encode(buf.getvalue()).decode()]))
                result['vision'] = {'events': events, 'red': events[-1]['text'].strip().lower().strip('.') == 'red'}
            except Exception as exc:
                result['vision'] = {'error': str(exc), 'type': type(exc).__name__}
        else:
            result['vision'] = {'status': 'not_applicable_text_only_model'}
        save()
        if workflows:
            for collection in collections:
                case = next(c for c in plan['cases'] if c['collection'] == collection)
                if collection == 'crypto':
                    case = next(c for c in plan['cases'] if c['source_id'] == 'H6')
                scope = service.scope(collection=collection)
                row = {'collection': collection, 'source_id': case['source_id']}
                result['workflows'].append(row)
                try:
                    job = Workflows(service).create(scope, case['question'], provider, source_id=case['source_id'])
                    for _ in range(6):
                        job = Workflows(ResearchService(output / 'evaluation.db', policy)).advance(
                            scope, job['id'], provider, approve_generation=True)
                        row['job'] = job
                        save()
                    row['resume_unchanged'] = Workflows(service).advance(
                        scope, job['id'], provider, approve_generation=True)['steps'] == job['steps']
                except Exception as exc:
                    row['error'] = {'type': type(exc).__name__, 'message': str(exc)}
                save()
                print(json.dumps({'model': model_name, 'workflow': collection,
                                  'status': row.get('job', {}).get('status'), 'error': row.get('error')}), flush=True)
    try:
        embedding = configured_embedding(settings)
        cache = SQLiteEmbeddingCache(embedding, output / 'embedding-cache.db')
        texts = ['The kitten sleeps beside its mother.', 'O filhote de gato dorme junto da mãe.',
                 'The database transaction is committed atomically.']
        vectors = cache.embed(texts)
        cached = cache.embed(texts)
        def dot(i, j):
            return sum(a * b for a, b in zip(vectors[i], vectors[j]))
        report['embedding'] = {'model': embedding.model, 'digest': embedding.model_digest,
                               'dimensions': [len(v) for v in vectors],
                               'unit_norms': all(abs(math.hypot(*v) - 1) < 1e-8 for v in vectors),
                               'cache_identical': vectors == cached,
                               'semantic_pair_above_unrelated': dot(0, 1) > dot(0, 2),
                               'scores': [dot(0, 1), dot(0, 2)], 'searches': []}
        for case in plan['cases']:
            answer = search(service, service.scope(collection=case['collection']), case['question'],
                            source_id=case['source_id'], embedding=embedding)
            report['embedding']['searches'].append({'source_id': case['source_id'],
                'collection': case['collection'], 'matches': answer['matches'],
                'identity_preserved': bool(answer['results']) and all(
                    r['record']['source_id'] == case['source_id'] for r in answer['results'])})
            save()
    except Exception as exc:
        report['embedding']['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    report['states_preserved'] = before == {c: stable(service, service.scope(collection=c)) for c in collections}
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    return {'output': str(output), 'states_preserved': report['states_preserved']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'config', 'db', 'policy', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--no-workflows', dest='workflows', action='store_false')
    print(json.dumps(run(**vars(parser.parse_args()))))

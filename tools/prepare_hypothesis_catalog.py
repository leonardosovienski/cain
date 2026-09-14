"""Prepare explicitly inventoried sources for the existing Snapshot receiver.

No ingestion, policy mutation, producer write or scientific status inference.
Document chunks are source occurrences, never a count of unique hypotheses.
"""
import argparse
import json
from pathlib import Path
import subprocess

from research_snapshot import canonical, confined, digest, seal, timestamp, validate

EXPORTER = 'hypothesis-catalog/2'


def source_clock(value):
    """Only copy a timezone-qualified source clock; never guess UNKNOWN or dates."""
    try:
        timestamp(value)
    except ValueError:
        return None
    return value


def array_spans(text):
    """Decode an array while retaining exact original JSON object spans."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in trial source')
            result[key] = value
        return result

    def finite_only(value):
        raise ValueError('Nonfinite JSON value in trial source')

    decoder = json.JSONDecoder(object_pairs_hook=unique, parse_constant=finite_only)
    position = len(text) - len(text.lstrip())
    if text[position:position + 1] != '[':
        raise ValueError('Expected a trial array')
    position += 1
    while True:
        while position < len(text) and text[position].isspace():
            position += 1
        if text[position:position + 1] == ']':
            if text[position + 1:].strip():
                raise ValueError('Trailing content')
            return
        value, end = decoder.raw_decode(text, position)
        if not isinstance(value, dict):
            raise ValueError('Trial must be an object')
        yield value, position, end
        position = end
        while position < len(text) and text[position].isspace():
            position += 1
        if text[position:position + 1] == ',':
            position += 1
            if text[position:].lstrip().startswith(']'):
                raise ValueError('Trailing comma')
        elif text[position:position + 1] != ']':
            raise ValueError('Expected array separator')


def occurrences(text, source):
    if source['mode'] == 'trial_array':
        seen = set()
        for value, start, end in array_spans(text):
            identity = value[source['identity_key']]
            if not isinstance(identity, str) or not identity or identity in seen:
                raise ValueError('Missing or duplicate trial identity')
            seen.add(identity)
            status = value.get('status')
            yield identity, start, end, (status if isinstance(status, str) and status
                                         else 'NOT_STRUCTURED_IN_SOURCE')
    elif source['mode'] == 'document':
        # Contiguous, exhaustive slices. Newlines are preserved, not normalized.
        # Retrieval limits remain explicit: one excerpt is not the whole source.
        for index, start in enumerate(range(0, len(text), 12000)):
            yield f'part-{index + 1:04}', start, min(start + 12000, len(text)), 'NOT_EXTRACTED'
    else:
        raise ValueError('Unknown source mode')


def prepare(project, root, output, exported_at):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or output.is_relative_to(root):
        raise ValueError('Output must be outside the producer checkout')
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    report = {'domain': project['domain'], 'checkout_commit': head, 'sources': [],
              'publication_ids': [], 'unique_hypotheses': None,
              'scope_complete': False, 'generation_certified': False}
    planned = []
    paths = [s['path'] for s in project['sources']]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate source in inventory')
    for source in project['sources']:
        path = confined(root, source['path'])
        raw = path.read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError('Source exceeds curated document size limit')
        text = raw.decode('utf-8')
        source_hash = digest(raw)
        if source_hash != source['sha256']:
            raise ValueError(f"Source changed: {source['path']}; review inventory before refreshing")
        units = list(occurrences(text, source))
        if not units:
            raise ValueError('Empty source')
        evidence, records = [], []
        for identity, start, end, status in units:
            quote = text[start:end]
            trial = json.loads(quote) if source['mode'] == 'trial_array' else {}
            eid = digest(canonical([source['path'], identity, source_hash]))
            evidence.append(dict(id=eid, source=source['path'], availability='received',
                                 text=quote, sha256=digest(quote.encode('utf-8')),
                                 hash_basis='received_utf8', locator=f'characters:{start}:{end}',
                                 start=start, end=end, offset_unit='unicode_codepoints'))
            records.append(dict(source_id=source['path'] + '#' + identity,
                                revision=digest(canonical([source_hash, EXPORTER])),
                                kind=('registered_trial' if
                                source['mode'] == 'trial_array' else 'research_document_excerpt'),
                                identity_basis='document_identity', source_status=status,
                                status_axis=('domain_lifecycle' if trial else 'source_availability'),
                                mapping=None, reason=None,
                                event_at=source_clock(trial.get('executed_at')),
                                recorded_at=source_clock(trial.get('registered_at')),
                                available_at=None,
                                supersedes=[], evidence_ids=[eid]))
        # Bound each publication; receiver already supports multiple publications.
        for start in range(0, len(records), 40):
            package = validate(seal(dict(
                contract='ResearchSnapshotV1', profile='local-evidence/1', extensions={},
                origin=dict(domain=project['domain'], repository=project['repository'],
                            publisher='cain-local-curation', stream='hypothesis-catalog',
                            code_revision=head, exporter_revision=EXPORTER,
                            inputs={source['path']: source_hash}),
                exported_at=exported_at,
                restrictions=dict(policy='cain-hypothesis-catalog/1', read=True,
                                  disclose=False, generate=True),
                coverage=dict(scope=source['purpose'], completeness='partial',
                              included=[source['path']], missing=[],
                              excluded=project['excluded'], limitations=[
                                  'Local receiver curation, not a producer-authenticated export',
                                  'Documented sources, not reproduced experiments or verified current truth',
                                  'Trial entries and document chunks are not unique hypotheses',
                                  'Historical dates and statuses remain in literal source text',
                                  'Only explicit source timestamps copied; unknown clocks stay null',
                                  'References to other artifacts do not admit their content',
                                  'Revisions are unordered; compare inventory hashes before using']),
                records=records[start:start + 40], evidence=evidence[start:start + 40])))
            planned.append(package)
            report['publication_ids'].append(package['publication_id'])
        report['sources'].append(dict(path=source['path'], sha256=source_hash,
                                      mode=source['mode'], occurrences=len(units),
                                      characters=len(text), purpose=source['purpose']))
    # Validate the entire plan before writing. Content-addressed, never overwrite.
    output.mkdir(parents=True, exist_ok=True)
    for package in planned:
        path = output / (package['publication_id'] + '.json')
        payload = canonical(package)
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError('Existing publication differs')
        else:
            with path.open('xb') as file:
                file.write(payload)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--exported-at', required=True,
                        help='Explicit packaging clock; reuse for byte-identical reprocessing')
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
    project = next(p for p in inventory['projects'] if p['domain'] == args.domain)
    print(json.dumps(prepare(project, args.checkout, args.output, args.exported_at),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

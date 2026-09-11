"""Frozen disjoint automated evaluation; not independent human semantic validation."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from cain import __version__
try:
    from cain.providers import configured_llm
except ImportError:  # Installed 0.4.6 predates shared provider composition.
    from cain.cli import configured_llm
from cain.research import ResearchService
from cain.research.analysis import entities, review
from cain.settings import load_settings
from research_snapshot import canonical, digest, seal


def run(protocol, config, output, baseline=False):
    output.mkdir(parents=True, exist_ok=False)
    inbox = output / 'inbox'
    inbox.mkdir()
    policy = {"version": 1, "import_root": str(inbox.resolve()), "grants": [{
        "user": "evaluation", "project": "", "collection": "disjoint", "domain": "crypto",
        "repository": "fixture://disjoint", "publisher": "fixture", "stream": "synthetic",
        "sources": ["case.txt"], "policies": ["fixture/1"], "generate": True}]}
    policy_path = output / 'policy.json'
    policy_path.write_bytes(canonical(policy))
    service = ResearchService(output / 'research.db', policy_path)
    scope = service.scope('evaluation', collection='disjoint')
    plan = json.loads(protocol.read_bytes())
    model = configured_llm(load_settings(config))
    report = {"version": __version__, "protocol_sha256": digest(protocol.read_bytes()),
              "protocol": plan, "baseline": baseline, "cases": [], "economic_validation": False}
    for case in plan['cases']:
        service = ResearchService(output / (case['id'] + '.db'), policy_path)
        text = case['text']
        package = seal({"contract": "ResearchSnapshotV1", "profile": "local-evidence/1", "extensions": {},
            "origin": {"domain": "crypto", "repository": "fixture://disjoint", "publisher": "fixture",
                       "stream": "synthetic", "code_revision": "fixture", "exporter_revision": "fixture",
                       "inputs": {"case.txt": digest(text.encode())}},
            "exported_at": "2026-09-11T00:00:00Z", "restrictions": {
                "policy": "fixture/1", "read": True, "generate": True, "disclose": False},
            "coverage": {"scope": "synthetic disjoint evaluation", "completeness": "partial",
                         "included": ["case.txt"], "missing": [], "excluded": [], "limitations": ["synthetic"]},
            "records": [{"source_id": case['source_id'], "revision": case['id'], "kind": "documented_claim",
                         "identity_basis": "source_assigned", "source_status": "DOCUMENTARY_FIXTURE",
                         "status_axis": "operational", "mapping": None, "reason": None,
                         "event_at": None, "recorded_at": None, "available_at": None, "supersedes": [], "evidence_ids": ['e']}],
            "evidence": [{"id": 'e', "source": "case.txt", "availability": "received", "text": text,
                          "sha256": digest(text.encode()), "hash_basis": "received_utf8", "locator": "whole_document",
                          "start": 0, "end": len(text), "offset_unit": "unicode_codepoints"}]})
        filename = case['id'] + '.json'
        (inbox / filename).write_bytes(canonical(package))
        service.ingest(filename, scope)
        started = perf_counter()
        row = {"id": case['id']}
        try:
            if 'questions' not in case:
                result = entities(service, scope, "Extract only literal reported fields.", model, source_id=case['source_id'])
                row['result'] = result
                if 'expected_pairs' in case:
                    row['exact_expected'] = sorted([r['subject'], r['object']] for r in result['relations']) == sorted(case['expected_pairs'])
                else:
                    row['exact_expected'] = result['status'] == case['expected_structural_status']
            else:
                row['reviews'] = [review(service, scope, question, model, role='challenge', source_id=case['source_id'])
                                  for question in case['questions']]
                row['resolved_citations'] = all(
                    r['status'] in {'generated', 'abstained_insufficient'} and r['explanation']['source_quotes']
                    for r in row['reviews'])
            assert all(r['source_status'] == 'DOCUMENTARY_FIXTURE' for r in service.query(scope)['records'])
            row['states_preserved'] = True
        except Exception as exc:
            row['error'] = {"type": type(exc).__name__, "message": str(exc)}
        row['elapsed'] = perf_counter() - started
        report['cases'].append(row)
        (output / 'report.json').write_bytes(canonical(report))
        print(json.dumps({k: v for k, v in row.items() if k not in {'result', 'reviews'}}), flush=True)
    return {"version": __version__, "output": str(output), "cases": len(report['cases'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'config', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--baseline', action='store_true')
    print(json.dumps(run(**vars(parser.parse_args()))))

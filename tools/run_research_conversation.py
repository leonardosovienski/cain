"""Finite, auditable CAIN conversation campaign against explicit local scopes.

Use QA database copies. This tool never fabricates model turns, installs models,
executes economic experiments, or converts a citation into semantic approval.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
from uuid import uuid4

from cain.llm import OllamaLLM
from cain.research import ResearchService
from cain.research.analysis import review, search
from cain.runtime import build_cain
from cain.workspace import WorkspaceStore


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Recorder:
    def __init__(self, provider, output):
        self.provider, self.output, self.case, self.calls = provider, output, '', 0

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def _call(self, prompt, instruction, schema=None):
        self.calls += 1
        prefix = f'{self.case}-call-{self.calls}'
        save(self.output / (prefix + '-input.json'), dict(
            prompt=prompt, instruction=instruction, schema=schema,
            input_sha256=hashlib.sha256((instruction + prompt).encode()).hexdigest()))
        try:
            raw = (self.provider.generate(prompt, instruction) if schema is None
                   else self.provider.generate_json(prompt, instruction, schema))
        except Exception as exc:
            save(self.output / (prefix + '-error.json'), dict(
                error_type=type(exc).__name__, message=str(exc),
                partial=getattr(exc, 'partial_response', None), metadata=self.provider.last_metadata))
            raise
        save(self.output / (prefix + '-raw.json'), dict(
            raw=raw, sha256=hashlib.sha256(raw.encode()).hexdigest(),
            metadata=self.provider.last_metadata))
        return raw

    def generate(self, prompt, context=''):
        return self._call(prompt, context)

    def generate_json(self, prompt, context, schema):
        return self._call(prompt, context, schema)


def perform_case(case, service, scope, workspace, user, project, session, provider, output_path=None):
    """Persist only outputs actually returned by CAIN, with their origin visible."""
    question = case['question']
    if case.get('mode', 'review') == 'run':
        corpus = workspace.document_corpus(user, project)
        with build_cain(workspace.path, provider, corpus=corpus, source_paths=[]) as runtime:
            result = runtime.run(user, session, question, intent=case.get('intent'),
                                 project_id=project)
            outcome = asdict(result)
        output = {**outcome, 'generation': provider.last_metadata,
                  'project_id': project, 'session_id': session,
                  'campaign_origin': 'CAIN orchestrator on QA copy'}
    else:
        found = search(service, scope, question, limit=5)
        result = review(service, scope, question, provider,
                        role=case.get('role', 'synthesis'))
        explanation = result.get('explanation') or {}
        response = explanation.get('proposed_synthesis')
        if response is None:
            # A withheld/failed answer is an execution record, never a fake LLM answer.
            response = ('Registro de execução CAIN: ' + result['status'] +
                        '. Nenhuma síntese do modelo foi entregue nesta tentativa.')
        output = dict(response=response, decision_id=str(uuid4()), run_id=str(uuid4()),
                      agent='research-review', project_id=project, session_id=session,
                      sources=explanation.get('source_quotes', []),
                      generation=result.get('generation', {}), research_result=result,
                      research_search=found, research_scope=json.loads(scope),
                      campaign_origin='CAIN research.review on QA copy; not automatic chat retrieval')
    output['semantic_evaluation'] = 'pending_manual_review'
    if output_path is not None:
        save(output_path, output)
    workspace.record_turn(user, session, question, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'research', 'policy', 'questions', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--collection', required=True)
    parser.add_argument('--research-project', default='')
    parser.add_argument('--model', required=True)
    parser.add_argument('--base-url', required=True)
    args = parser.parse_args()
    cases = json.loads(args.questions.read_text(encoding='utf-8'))
    if not isinstance(cases, list) or not 1 <= len(cases) <= 50:
        raise ValueError('Campaign requires 1-50 explicit cases')
    ids = [case['id'] for case in cases]
    if len(set(ids)) != len(ids) or any(not ident.replace('-', '').isalnum() for ident in ids):
        raise ValueError('Unique alphanumeric case IDs required')
    args.output.mkdir(parents=True, exist_ok=False)
    provider = Recorder(OllamaLLM(model=args.model, base_url=args.base_url, temperature=0,
                                 seed=42, num_ctx=6144, num_predict=768,
                                 max_input_bytes=5000, think=False, timeout=600), args.output)
    with urllib.request.urlopen(args.base_url + '/api/tags', timeout=10) as response:
        inventory = json.load(response)
    save(args.output / 'inventory.json', inventory)
    save(args.output / 'started.json', dict(
        at=datetime.now(timezone.utc).isoformat(), arguments={k: str(v) for k, v in vars(args).items()},
        questions_sha256=sha(args.questions), runner_sha256=sha(Path(__file__)),
        provider=vars(provider.provider), cases=len(cases)))
    workspace = WorkspaceStore(args.workspace)
    workspace.ensure_session(args.user, args.session, args.project)
    service = ResearchService(args.research, args.policy)
    scope = service.scope(args.user, args.research_project, args.collection)
    results = []
    for case in cases:
        if (args.output / 'STOP').exists():
            save(args.output / 'interrupted.json', dict(
                completed_cases=len(results), remaining=[c['id'] for c in cases[len(results):]]))
            break
        provider.case = case['id']
        before = provider.calls
        save(args.output / (case['id'] + '-question.json'), case)
        try:
            result = perform_case(case, service, scope, workspace, args.user,
                                  args.project, args.session, provider,
                                  args.output / (case['id'] + '-result.json'))
            row = dict(id=case['id'], status=result.get('research_result', {}).get('status', 'returned'),
                       turn_id=result['decision_id'], calls=provider.calls-before)
        except Exception as exc:
            row = dict(id=case['id'], status='failed', error=repr(exc), calls=provider.calls-before)
            save(args.output / (case['id'] + '-failure.json'), row)
        results.append(row)
        print(json.dumps(row), flush=True)
    save(args.output / 'completed.json', dict(results=results, provider_calls=provider.calls,
                                              semantic_validation='not_established',
                                              new_economic_experiments=0))
    save(args.output / 'manifest.json', {p.name: sha(p) for p in sorted(args.output.iterdir()) if p.is_file()})


if __name__ == '__main__':
    main()

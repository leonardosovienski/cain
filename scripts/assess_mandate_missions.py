"""Known-case utility pilot from authorized local receipts, not a held-out benchmark."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from cain.research import ResearchService
from cain.research.historian import explain
from cain.research.workflows import Workflows
from research_snapshot import digest


class NoInference:
    def generate_json(self, *args):
        raise AssertionError('Known field cases must not call a generator')


def assess(root):
    protocol = json.loads((Path(__file__).parents[1]/'evaluation/mandate-utility-pilot.json').read_text(encoding='utf-8-sig'))
    results = []
    for directory in ['procedure-h4', 'procedure-h6']:
        case = root/directory
        task = json.loads((case/'task.json').read_bytes())
        receipt = json.loads((case/'verification.json').read_bytes())
        service = ResearchService(case/'research.db', task['policy'])
        scope = service.scope(**task['scope'])
        identity = task['identity']
        source = receipt['workflow']['steps'][0]['result']['evidence'][0]['text']
        data = json.loads(source)
        expected = {field: data[group][identity] for field,group in
                    [('state','hypotheses'),('trial','hypothesis_trials')]}
        # Explicit simple result, not an assumed success flag.
        simple_answer = {'state': expected['state'], 'trial': expected['trial'],
                         'reason': 'not_located_in_selected_excerpts',
                         'sample': 'not_located_in_selected_excerpts'}
        question = f'Qual estado e trial de {identity}? O recorte informa motivo e tamanho da amostra?'
        start = perf_counter()
        answer = explain(service,scope,question,NoInference(),source_id=identity)
        elapsed = perf_counter()-start
        fields = {item['field']: item for item in answer['explanation']['fields']}
        exact = all(fields[key]['status']=='reported' and
                    {v['value'] for v in fields[key]['values']} == {value} for key,value in expected.items())
        missing = all(fields[k]['status']=='not_located_in_selected_excerpts' for k in ['reason','sample'])
        before_bytes = (case/'verification.json').read_bytes()
        rerun = subprocess.run([sys.executable, str(Path(__file__).with_name('verify_evidence_selection.py')),
                                'resume', '--output', str(case)], capture_output=True, text=True, timeout=35)
        if rerun.returncode:
            raise ValueError('Procedure reuse failed: ' + rerun.stderr)
        job = Workflows(service).get(scope, 'selection-comparison')
        # The simple comparator independently reads the serialized state, without a memory agent.
        simple_state = receipt['workflow']
        resume = job['status']=='completed' and job['next_step'] is None and len(job['steps'])==2
        simple_resume = simple_state['status']=='completed' and simple_state['next_step'] is None and len(simple_state['steps'])==2
        cardinality = len(task['pointers'])
        compare = receipt['verified'] and receipt['selected_expected_fields']==cardinality
        simple_compare = receipt['compact_expected_fields']==cardinality
        intact = ((case/'verification.json').read_bytes() == before_bytes and
                  digest(before_bytes) == (case/'verification.sha256').read_text())
        results.append({'case': directory, 'source_versions': receipt['source_versions'],
                        'reconstruct': {'cain': exact and missing,
                                        'simple': all(simple_answer[k]==v for k,v in expected.items()) and
                                                  all(simple_answer[k]=='not_located_in_selected_excerpts' for k in ['reason','sample']),
                                        'simple_answer': simple_answer,
                                        'answer': answer, 'cain_seconds': elapsed},
                        'resume': {'cain': resume, 'simple': simple_resume},
                        'compare': {'cain': compare, 'simple': simple_compare, 'units':'fields'},
                        'reuse': {'cain': intact, 'simple': intact},
                        'simple_scope': 'direct authorized field lookup and receipt reading only; not a deployed permissions/history product'})
    refused = root/'procedure-refuse'
    refusal = (refused/'task.json').exists() and not (refused/'verification.json').exists() and (root/'procedure-refuse.txt').exists()
    result = {'protocol':protocol, 'cases':results, 'missing_pointer_refused':refusal,
              'human_time':None, 'independent_judgment':False,
              'hermes':'separate_execution_receipt' if (root/'hermes-result.json').exists() else 'not_executed_in_this_pilot',
              'overall_claim':'Equivalent documentary result in this small slice; no superiority established'}
    if not all(r[m]['cain'] and r[m]['simple'] for r in results for m in ['reconstruct','resume','compare','reuse']) or not refusal:
        raise ValueError('Pilot criteria not all met; retain cases for investigation')
    (root/'mission-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Two known cases: four bounded documentary missions checked; no superiority claim.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipts',type=Path,required=True)
    assess(parser.parse_args().receipts.resolve())

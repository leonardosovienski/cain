"""Summarize matched runs without converting mechanical diagnostics to semantic scores."""

import argparse
import json
from pathlib import Path


def summarize(root, original):
    reports = {phase: json.loads((root / ('model-' + phase) / 'report.json').read_bytes())
               for phase in ('baseline', 'delivered', 'review')}
    baseline = reports['baseline']
    summary = {'semantic_quality_certified': False, 'economic_validation': False, 'phases': {}}
    for phase, report in reports.items():
        assert report.get('finished_utc') and report['states_preserved'] and report['source_unchanged']
        assert report['protocol_sha256'] == baseline['protocol_sha256']
        assert report['generation_parameters'] == baseline['generation_parameters']
        assert report['ollama_tags'] == baseline['ollama_tags']
        values = []
        old = None
        if phase in ('baseline', 'delivered'):
            old_phase = 'baseline' if phase == 'baseline' else 'corrected'
            old = json.loads((original / old_phase / 'report.json').read_bytes())
        for index, model in enumerate(report['models']):
            assert len(model['cases']) == 19
            assert [r['case'] for r in model['cases']] == [r['case'] for r in baseline['models'][index]['cases']]
            row = {'model': model['model'], 'cases': 19,
                   'generated': sum(c.get('review', {}).get('status') == 'generated' for c in model['cases']),
                   'exact_citations': sum(bool(c.get('exact_citations')) for c in model['cases']),
                   'literal_state_mentioned': sum(bool(c.get('literal_state_mentioned')) for c in model['cases']),
                   'other_hypothesis_labels': sum(bool(c.get('other_hypothesis_labels')) for c in model['cases']),
                   'workflows_completed': sum(w.get('job', {}).get('status') == 'completed' for w in model['workflows']),
                   'absent_zero_calls': model['absent_zero_calls'], 'stream_done': model['stream'].get('terminal_done'),
                   'vision': model['vision'].get('red', model['vision'].get('status'))}
            if old:
                row['identical_prior_responses'] = sum(
                    c.get('review', {}).get('explanation') == prior.get('review', {}).get('explanation')
                    for c, prior in zip(model['cases'], old['models'][index]['cases']))
                row['identical_prior_synthesis'] = sum(
                    (c.get('review', {}).get('explanation') or {}).get('proposed_synthesis') ==
                    (prior.get('review', {}).get('explanation') or {}).get('proposed_synthesis')
                    for c, prior in zip(model['cases'], old['models'][index]['cases']))
            assert all(w['job']['request']['model']['model_digest'] for w in model['workflows'] if w.get('job'))
            values.append(row)
        summary['phases'][phase] = {'source_commit': report['source_commit'], 'models': values,
                                    'embedding': report['embedding']}
    (root / 'comparison-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    lines = ['# Comparação individual: diagnósticos, não notas semânticas', '',
             '| Relato | Baseline 0.8 / 3b | Entregue 0.8 / 3b | Revisão 0.8 / 3b |', '|---|---|---|---|']
    for i, case in enumerate(baseline['protocol']['cases']):
        cells = []
        for report in reports.values():
            labels = []
            for model in report['models']:
                row = model['cases'][i]
                status = row.get('review', {}).get('status', 'error')
                labels.append(status if status != 'generated' else
                              'literal presente' if row.get('literal_state_mentioned') else 'literal ausente')
            cells.append(' / '.join(labels))
        lines.append('| ' + case['source_id'] + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', 'Literal pode aparecer em uma afirmação falsa; sua ausência pode coexistir com paráfrase correta. Consulte as respostas e observações semânticas.', '']
    (root / 'per-case-diagnostics.md').write_text('\n'.join(lines), encoding='utf8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.root, args.original), ensure_ascii=False))

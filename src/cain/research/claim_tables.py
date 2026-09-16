"""Literal labelled claim tables; no model paraphrase or inferred scientific state."""
from cain.research.field_review import normalize


def claim_table_reply(excerpts):
    fields, lines = [], []
    for key, entry in excerpts.items():
        quote = entry['quote'].strip()
        headers = [part for part in entry.get('source_context', []) if part['kind'] == 'table_header']
        if len(headers) != 1 or not quote.startswith('|') or '\\|' in quote:
            return None
        header = headers[0]['quote'].splitlines()[0]
        if '\\|' in header:
            return None
        labels = [value.strip() for value in header.strip().strip('|').split('|')]
        values = [value.strip() for value in quote.strip('|').split('|')]
        normalized = [normalize(label) for label in labels]
        if (len(labels) != len(values) or len(set(normalized)) != len(normalized)
                or not set(normalized) & {'claim', 'hypothesis', 'hipotese'}
                or not set(normalized) & {'claim id', 'id', 'hypothesis id'}
                or not set(normalized) & {'state', 'status', 'estado'}):
            return None
        lines.append(f'Campos registrados na fonte [{key}]:')
        for label, name, value in zip(labels, normalized, values):
            display = ('Hipótese registrada' if name in {'hypothesis', 'hipotese'} else
                       'Enunciado da claim (não tratado aqui como resultado demonstrado)' if name == 'claim'
                       else label)
            lines.append(f'{display}: {value}')
            fields.append({'excerpt_id': key, 'label': label, 'value': value})
    if not fields:
        return None
    lines.append('Transcrição dos campos selecionados; não valida o experimento nem resolve conflitos entre revisões.')
    return {'fields': fields, 'text': '\n'.join(lines), 'method': 'literal-claim-table/1',
            'selected_ids': list(excerpts)}

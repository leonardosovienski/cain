"""Conservative multi-field lookup from selected literal JSON, never free synthesis."""
import json
import re
import unicodedata

VERSION = 'literal-json-field-review/1'
ALIASES = {
    'state': {'estado', 'state', 'status'},
    'trial': {'trial', 'trials', 'ensaio'},
    'reason': {'motivo', 'reason', 'justificativa'},
    'sample': {'amostra', 'sample'},
}
LABELS = {'state': 'Estado', 'trial': 'Trial', 'reason': 'Motivo', 'sample': 'Amostra'}
KEYS = {
    'state': {'state', 'status', 'estado'},
    'trial': {'trial', 'trial_id', 'trial_name', 'ensaio'},
    'reason': {'reason', 'motivo', 'justificativa'},
    'sample': {'sample', 'sample_size', 'amostra', 'tamanho_da_amostra'},
}
IDENTITY_MAPS = {'hypotheses': 'state', 'hypothesis_trials': 'trial'}


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def requested_fields(question, identity):
    if not identity:
        return []
    query = re.sub(r'(?<!\w)' + re.escape(identity) + r'(?!\w)', '', question, flags=re.I)
    words = set(re.findall(r'\w+', normalize(query)))
    fields = [field for field, aliases in ALIASES.items() if words & aliases]
    # Deliberately limited to explicit lookup wording; interpretation stays on its old path.
    vocabulary = set().union(*ALIASES.values()) | {
        'qual', 'quais', 'e', 'sao', 'o', 'a', 'os', 'as', 'de', 'do', 'da', 'dos', 'das',
        'informa', 'informam', 'recorte', 'tamanho', 'what', 'is', 'are', 'the', 'and', 'of',
        'size', 'reported', 'report', 'reports', 'in', 'source', 'fonte', 'informado', 'informados',
    }
    return fields if len(fields) >= 2 and not words - vocabulary else []


def field_reply(excerpts, question, identity):
    fields = requested_fields(question, identity)
    if not fields or not any('json_pointer' in row for row in excerpts.values()):
        return None
    found = {field: [] for field in fields}
    for key, row in excerpts.items():
        if 'json_pointer' not in row:
            continue
        path = [p.replace('~1', '/').replace('~0', '~') for p in row['json_pointer'].split('/')[1:]]
        if identity not in path:
            continue
        field = None
        if len(path) >= 2 and path[-1] == identity:
            field = IDENTITY_MAPS.get(path[-2])
        elif len(path) >= 2 and path[-2] == identity:
            field = next((name for name, keys in KEYS.items() if path[-1] in keys), None)
        if field not in found:
            continue
        try:
            value = json.loads('{' + row['quote'] + '}')
        except ValueError:
            continue
        if len(value) != 1 or next(iter(value)) != path[-1]:
            continue
        found[field].append({'excerpt_id': key, 'json_pointer': row['json_pointer'],
                             'value': next(iter(value.values()))})
    # Multiple versions are displayed together, never silently resolved as current truth.
    result, lines = [], []
    for field, values in found.items():
        state = ('reported' if values else 'not_located_in_selected_excerpts')
        if len({json.dumps(v['value'], ensure_ascii=False, sort_keys=True) for v in values}) > 1:
            state = 'multiple_reported_values'
        result.append({'field': field, 'status': state, 'values': values})
        if values:
            rendered = '; '.join(json.dumps(v['value'], ensure_ascii=False) + ' [' + v['excerpt_id'] + ']' for v in values)
            lines.append(LABELS[field] + ': ' + rendered + ('. Valores distintos nas fontes; nenhuma versão escolhida.' if state == 'multiple_reported_values' else '.'))
        else:
            lines.append(LABELS[field] + ': não localizado nos trechos selecionados; isso não demonstra inexistência na fonte completa.')
    return {'fields': result, 'text': '\n'.join(lines), 'method': VERSION,
            'selected_ids': list(excerpts), 'decomposition': 'explicit_multi_field_lookup_only'}

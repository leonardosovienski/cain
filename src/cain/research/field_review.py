"""Conservative multi-field lookup from selected literal JSON, never free synthesis."""
import json
import re
import unicodedata
from research_snapshot import digest

VERSION = 'literal-json-field-review/3'
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


def resolve_reply(service, scope, excerpts, reply):
    """Resolve exact source versions; caller must guard its full policy snapshot."""
    resolved = []
    for key, entry in excerpts.items():
        source = service.evidence(scope, entry['reference'])
        if (digest(source['text'].encode()) != entry['source_sha256']
                or source['text'][entry['start']:entry['end']] != entry['quote']):
            raise ValueError('Source excerpt changed')
        resolved.append({'excerpt_id': key, 'evidence_id': entry['reference'], 'quote': entry['quote'],
                         'start': entry['start'], 'end': entry['end'], 'support': source})
    return {'source_quotes': resolved, 'proposed_synthesis': reply['text'],
            'fields': reply['fields'], 'semantic_support': 'literal_field_values_only',
            'answer_mode': 'literal_fields',
            'verification': {'method': reply['method'], 'selected_ids': reply['selected_ids'],
                             'interpretation_verified': False}}


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def requested_fields(question, identity):
    if not identity:
        return []
    query = re.sub(r'(?<!\w)' + re.escape(identity) + r'(?!\w)', '', question, flags=re.I)
    # A documented decision followed by an explicit field list is still a
    # lookup. Keep causal, evaluative and open-ended interpretation elsewhere.
    normalized = normalize(query).strip()
    compound = re.fullmatch(
        r'(?:explique|descreva|reconstrua)\s+(?:a\s+)?decisao(?:\s+documentada)?'
        r'\s+de\s*,?\s*(?:incluindo|com)\s+(.+)', normalized)
    if compound:
        query = compound[1]
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
    native = native_field_reply(excerpts, question, identity)
    if native:
        return native
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


def native_field_reply(excerpts, question, identity):
    """Expose named machine fields without converting their values into a verdict.

    Two explicit snake_case names opt into a conservative literal response,
    including when the question asks for an interpretation. Missing fields are
    missing from the selected excerpts only. Ordinary prose keeps its own path.
    """
    names = list(dict.fromkeys(re.findall(r'\b[a-zA-Z][a-zA-Z0-9]*_[a-zA-Z0-9_]+\b', question)))
    if len(names) < 2:
        return None
    words = set(re.findall(r'\w+', question))
    found = {name: [] for name in names}
    for key, row in excerpts.items():
        pointer = row.get('json_pointer')
        if pointer is None:
            continue
        path = [p.replace('~1', '/').replace('~0', '~') for p in pointer.split('/')[1:]]
        if not path or (identity and identity not in path):
            continue
        name = path[-1]
        if name not in words:
            continue
        try:
            value = json.loads('{' + row['quote'] + '}')
        except ValueError:
            continue
        if list(value) != [name]:
            continue
        found.setdefault(name, []).append({'excerpt_id': key, 'json_pointer': pointer, 'value': value[name]})
    if not any(found.values()):
        return None
    fields, lines = [], ['Leitura literal dos campos selecionados. A interpretação solicitada não foi verificada; estes valores não são convertidos em conclusão sobre execução, sucesso ou resultado.']
    for name, values in found.items():
        state = 'reported' if values else 'not_located_in_selected_excerpts'
        if len({json.dumps(v['value'], sort_keys=True) for v in values}) > 1:
            state = 'multiple_reported_values'
        fields.append({'field': name, 'status': state, 'values': values})
        if values:
            for value in values:
                lines.append(value['json_pointer'] + ': ' + json.dumps(value['value'], ensure_ascii=False)
                             + ' [' + value['excerpt_id'] + '].')
        else:
            lines.append(name + ': não localizado nos trechos selecionados; isso não demonstra inexistência na fonte completa.')
    lines.append('Versões e caminhos são apresentados separadamente; nenhuma versão foi escolhida como atual.')
    return {'fields': fields, 'text': '\n'.join(lines), 'method': VERSION,
            'selected_ids': list(excerpts), 'decomposition': 'native_fields_interpretation_abstained'}

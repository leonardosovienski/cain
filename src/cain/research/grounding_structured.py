"""Literal structured relations from JSON documents and Markdown tables; no inference."""

import json
import re


def matches_identity(relation, source_id):
    if 'json_pointer' in relation:
        return (source_id in [part.replace('~1', '/').replace('~0', '~')
                             for part in relation['json_pointer'].split('/')[1:]]
                or any(part['decoded_subject'] in {'id', 'family', 'hypothesis', 'hypothesis_id', 'trial_id', 'name'}
                       and part['decoded_object'] == source_id
                       for part in relation.get('record_context', [])))
    return relation['subject'] == source_id


def structured(evidence, source_id=None, *, addressable=False):
    relations, recognized, issues = [], 0, []
    seen = set()
    for ref, text in evidence.items():
        if text in seen:
            continue
        seen.add(text)
        entries, source_recognized = [], False
        if text.lstrip().startswith(("{", "[")):
            recognized += 1
            source_recognized = True
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate JSON key")
                    result[key] = value
                return result
            try:
                json.loads(text, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
                decoder = json.JSONDecoder()
                def ws(pos):
                    while pos < len(text) and text[pos].isspace():
                        pos += 1
                    return pos
                def visit(pos, path):
                    pos = ws(pos)
                    if text[pos] == '{':
                        pos = ws(pos + 1)
                        while text[pos] != '}':
                            start = pos
                            key, end = decoder.raw_decode(text, pos)
                            value_start = ws(ws(end) + 1)
                            value, value_end = decoder.raw_decode(text, value_start)
                            pointer = path + '/' + key.replace('~', '~0').replace('/', '~1')
                            flat_array = (addressable and isinstance(value, list) and
                                          all(not isinstance(v, (dict, list)) for v in value))
                            if isinstance(value, (dict, list)) and not flat_array:
                                visit(value_start, pointer)
                            else:
                                quote = text[start:value_end]
                                raw_key, raw_value = text[start:end], text[value_start:value_end]
                                obj = value if isinstance(value, str) else raw_value
                                subject = key if key in quote else raw_key
                                obj = obj if obj in quote else raw_value
                                if addressable or (len(quote) <= 1000 and len(subject) <= 150 and len(obj) <= 150):
                                    entries.append({"subject": subject, "predicate": "reported_json_value",
                                        "object": obj, "decoded_subject": key, "decoded_object": value,
                                        "json_pointer": pointer, "reference": ref, "quote": quote,
                                        "start": start, "end": value_end})
                            pos = ws(value_end)
                            if text[pos] == ',':
                                pos = ws(pos + 1)
                        return pos + 1
                    if text[pos] == '[':
                        pos, index = ws(pos + 1), 0
                        while text[pos] != ']':
                            _, end = decoder.raw_decode(text, pos)
                            if text[pos] in '{[':
                                visit(pos, path + '/' + str(index))
                            pos, index = ws(end), index + 1
                            if text[pos] == ',':
                                pos = ws(pos + 1)
                        return pos + 1
                visit(ws(0), '')
                # Scalar metrics from an observation must retain the literal
                # record identity and revision. No clock ordering or scientific
                # status is inferred from these field names.
                labels = {'id', 'family', 'hypothesis', 'hypothesis_id', 'trial_id', 'name', 'mode',
                          'observation_revision', 'revision', 'status', 'protocol_id',
                          'observed_at_utc', 'recorded_at_utc', 'at_utc'}
                label_groups = {}
                for row in entries:
                    if row['decoded_subject'] in labels:
                        parent = row['json_pointer'].rsplit('/', 1)[0]
                        label_groups.setdefault(parent, []).append(row)
                for entry in entries:
                    parent = entry['json_pointer'].rsplit('/', 1)[0]
                    ancestors = [p for p in label_groups if not p or parent == p or parent.startswith(p + '/')]
                    # A label belongs to its containing object and descendants,
                    # never a sibling object or another element of an array.
                    nearest = {}
                    identities = {'id', 'family', 'hypothesis', 'hypothesis_id', 'trial_id', 'name'}
                    for ancestor in sorted(ancestors, key=len):
                        if any(label['decoded_subject'] in identities for label in label_groups[ancestor]):
                            nearest = {key: value for key, value in nearest.items() if key not in identities}
                        for label in label_groups[ancestor]:
                            nearest[label['decoded_subject']] = label.copy()
                    entry['record_context'] = list(nearest.values())
            except (ValueError, RecursionError, IndexError):
                issues.append({"reference": ref, "status": "ambiguous_or_invalid_json"})
                continue
        else:
            lines = list(re.finditer(r'[^\r\n]+', text))
            def separator(line):
                return re.fullmatch(r'[ \t]*\|(?:[ \t]*:?-{3,}:?[ \t]*\|){2,}[ \t]*', line)
            for index, match in enumerate(lines):
                row = re.fullmatch(r'[ \t]*\|(.+)\|[ \t]*', match.group())
                if not row:
                    continue
                source_recognized = True
                cells = [cell.strip() for cell in row.group(1).split('|')]
                if separator(match.group()) or (index + 1 < len(lines) and separator(lines[index + 1].group())):
                    continue
                # Preserve supported cells literally, including inline code. Pipes
                # requiring Markdown escape/code interpretation are not guessed.
                if len(cells) < 2 or '\\|' in match.group() or any(cell.count('`') % 2 for cell in cells):
                    issues.append({'reference': ref, 'status': 'unsupported_table_delimiters',
                                   'start': match.start(), 'end': match.end()})
                    continue
                subject = cells[0]
                if not subject or set(''.join(cells)) <= set('-: '):
                    continue
                for column, obj in enumerate(cells[1:], start=2):
                    if obj and len(subject) <= 150 and len(obj) <= 150 and len(match.group()) <= 1000:
                        entries.append({"subject": subject,
                                        "predicate": "reported_table_value" if len(cells) == 2
                                        else f"reported_table_column_{column}", "object": obj,
                                        "reference": ref, "quote": match.group(), "start": match.start(), "end": match.end()})
            recognized += source_recognized
        if source_id is not None and source_recognized:
            entries = [r for r in entries if matches_identity(r, source_id)]
            if not entries:
                issues.append({'reference': ref, 'status': 'identity_not_found_in_supported_fields'})
        relations.extend(entries)
    limit = 2048 if addressable else 32
    return {"recognized_sources": recognized, "relations": relations[:limit], "has_more": len(relations) > limit,
            "issues": issues, "status": "literal" if relations else "ambiguous" if issues else "unsupported"}

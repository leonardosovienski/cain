"""Literal structured relations and addressable excerpts; no scientific inference."""

import json
import re


def matches_identity(relation, source_id):
    if 'json_pointer' in relation:
        return source_id in [part.replace('~1', '/').replace('~0', '~')
                             for part in relation['json_pointer'].split('/')[1:]]
    return relation['subject'] == source_id


def prose_spans(text, source_id):
    """Whole paragraphs/list items; never cut a wrapped negation from its clause."""
    lines = list(re.finditer(r'[^\r\n]+', text))
    headings = [(i, re.match(r'^(#{1,6})[ \t]+(.+?)\s*$', line.group()))
                for i, line in enumerate(lines)]
    headings = [(i, len(m[1]), m[2]) for i, m in headings if m]
    ranges = []
    for i, level, title in headings:
        if source_id is not None and title == source_id:
            end = next((j for j, depth, _ in headings if j > i and depth <= level), len(lines))
            ranges.append((i, end))
    if not ranges:
        ranges = [(0, len(lines))]
    result = []
    for first, last in ranges:
        start, end, previous_heading = None, None, False
        for line in lines[first:last]:
            gap = text[end:line.start()] if end is not None else ''
            boundary = (len(re.findall(r'\r+\n|\r|\n', gap)) >= 2 or previous_heading
                        or re.match(r'^\s*(?:#{1,6}\s|[-*]\s|\d+\.\s)', line.group()))
            if start is not None and boundary:
                result.append((start, end))
                start = None
            if start is None:
                start = line.start()
            end = line.end()
            previous_heading = bool(re.match(r'^#{1,6}\s', line.group()))
        if start is not None:
            result.append((start, end))
    return result


def structured(evidence, source_id=None):
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
                            if isinstance(value, (dict, list)):
                                visit(value_start, pointer)
                            else:
                                quote = text[start:value_end]
                                raw_key, raw_value = text[start:end], text[value_start:value_end]
                                obj = value if isinstance(value, str) else raw_value
                                subject = key if key in quote else raw_key
                                obj = obj if obj in quote else raw_value
                                if len(quote) <= 1000 and len(subject) <= 150 and len(obj) <= 150:
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
    return {"recognized_sources": recognized, "relations": relations[:32], "has_more": len(relations) > 32,
            "issues": issues, "status": "literal" if relations else "ambiguous" if issues else "unsupported"}


def cards(evidence, question, source_id=None):
    """Select bounded exact excerpts, retaining source offsets and disclosed coverage."""
    candidates, seen, focused_paths, issues = [], set(), {}, []
    terms = set(re.findall(r'\w+', question.casefold()))
    for ref, item in evidence.items():
        text = item['text']
        if text in seen:
            continue
        seen.add(text)
        literal = structured({ref: text}, source_id)
        issues.extend(literal['issues'])
        if literal['issues']:
            # Ambiguous JSON must not be reinterpreted as unstructured prose.
            continue
        focused = [r for r in literal['relations']
                   if source_id is not None and matches_identity(r, source_id)]
        if focused:
            # Shared JSON commonly contains every hypothesis. Pass only exact-key
            # values for the selected identity, with paths distinguishing state/trial.
            spans = set()
            for relation in focused:
                start, end = relation['start'], relation['end']
                if (start, end) in spans:
                    continue
                spans.add((start, end))
                candidates.append((100, ref, start, end, relation['quote']))
                if 'json_pointer' in relation:
                    focused_paths[(ref, start, end)] = relation['json_pointer']
            continue
        for start, end in prose_spans(text, source_id):
            quote = text[start:end]
            if not quote.strip() or not re.search(r'\w', quote):
                continue
            score = len(terms & set(re.findall(r'\w+', quote.casefold())))
            score += 20 if source_id and source_id.casefold() in quote.casefold() else 0
            if re.match(r'^\s*[-*]\s+\*{0,2}(?:state|status|limitations|estado|limitações)\b', quote, re.I):
                score += 12
            candidates.append((score, ref, start, end, quote))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    selected, used = {}, 0
    for _, ref, start, end, quote in candidates:
        if len(selected) >= 8 or used + len(quote.encode()) > 2200:
            continue
        entry = {"reference": ref, "quote": quote, "start": start, "end": end}
        if (ref, start, end) in focused_paths:
            entry['json_pointer'] = focused_paths[(ref, start, end)]
        selected['S' + str(len(selected) + 1)] = entry
        used += len(quote.encode())
    return selected, {"available_excerpts": len(candidates), "selected_excerpts": len(selected),
                      "selection": "identity_then_lexical_excerpts/3", "whole_source_read_claim": False,
                      "structured_issues": issues,
                      "omitted_excerpts": len(candidates) - len(selected),
                      "limitations": ["Exact identity paths/rows/headings do not infer entity mappings",
                                      "Whole prose blocks exceeding the budget are omitted, never sliced",
                                      "Selected excerpts cannot establish unreceived causes"]}

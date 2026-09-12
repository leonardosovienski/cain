"""Literal structured relations and addressable excerpts; no scientific inference."""

import json
import re
import unicodedata
from hashlib import sha256


def terms_of(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return set(re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c))))


def bounded_prose_spans(text, source_id, budget):
    """Expand sentence windows only inside an oversized paragraph, never mid-clause.

    Adjacent sentences are mandatory context; oversized windows remain omitted.
    This is a retrieval heuristic, not certification of semantic completeness.
    """
    for start, end in prose_spans(text, source_id):
        if len(text[start:end].encode()) <= budget:
            yield start, end
            continue
        boundaries = [start] + [start + m.end() for m in
            re.finditer(r'[.!?](?:[ \t]+|\r?\n)(?=[A-ZÀ-Ý])', text[start:end])] + [end]
        if len(boundaries) == 2:
            yield start, end
            continue
        for index in range(len(boundaries) - 1):
            yield boundaries[max(0, index - 2)], boundaries[min(len(boundaries) - 1, index + 3)]


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
                            if isinstance(value, (dict, list)):
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


def cards(evidence, question, source_id=None, *, max_bytes=2200, max_cards=8):
    """Select bounded exact excerpts, retaining source offsets and disclosed coverage."""
    candidates, seen, focused_paths, issues = [], set(), {}, []
    if type(max_bytes) is not int or not 1 <= max_bytes <= 2200 or type(max_cards) is not int or not 1 <= max_cards <= 8:
        raise ValueError('Invalid evidence budget')
    terms = terms_of(question)
    partial, examined, decisions = False, 0, []
    for ref, item in evidence.items():
        text = item['text']
        if examined >= 100 or len(text.encode()) > 1_000_000:
            partial = True
            continue
        examined += 1
        if text in seen:
            continue
        seen.add(text)
        literal = structured({ref: text}, source_id, addressable=True)
        partial |= literal['has_more']
        issues.extend(literal['issues'])
        if literal['issues']:
            # Ambiguous JSON must not be reinterpreted as unstructured prose.
            continue
        focused = [r for r in literal['relations']
                   if source_id is None or matches_identity(r, source_id)]
        if focused:
            # Shared JSON commonly contains every hypothesis. Pass only exact-key
            # values for the selected identity, with paths distinguishing state/trial.
            spans = set()
            for relation in focused:
                start, end = relation['start'], relation['end']
                if (start, end) in spans:
                    continue
                spans.add((start, end))
                score = len(terms & terms_of(relation['quote'] + ' ' + relation.get('json_pointer', '')))
                candidates.append((100 + score, ref, start, end, relation['quote']))
                if 'json_pointer' in relation:
                    focused_paths[(ref, start, end)] = relation['json_pointer']
            continue
        for number, (start, end) in enumerate(bounded_prose_spans(text, source_id, max_bytes)):
            if number >= 2048:
                partial = True
                break
            quote = text[start:end]
            if not quote.strip() or not re.search(r'\w', quote):
                continue
            score = len(terms & terms_of(quote))
            score += 20 if source_id and re.search(r'(?<!\w)' + re.escape(source_id.casefold()) + r'(?!\w)', quote.casefold()) else 0
            if re.match(r'^\s*[-*]\s+\*{0,2}(?:state|status|limitations|estado|limitações)\b', quote, re.I):
                score += 12
            candidates.append((score, ref, start, end, quote))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    selected, used = {}, 0
    for _, ref, start, end, quote in candidates:
        reason = ('overlapping_selected_context' if any(e['reference'] == ref and start < e['end'] and end > e['start'] for e in selected.values())
                  else 'card_limit' if len(selected) >= max_cards
                  else 'byte_budget' if used + len(quote.encode()) > max_bytes else 'selected')
        decisions.append({'reference': ref, 'start': start, 'end': end, 'decision': reason})
        if reason != 'selected':
            continue
        entry = {"reference": ref, "quote": quote, "start": start, "end": end,
                 "source_sha256": sha256(evidence[ref]['text'].encode()).hexdigest(),
                 "offset_unit": "unicode_codepoints"}
        if (ref, start, end) in focused_paths:
            entry['json_pointer'] = focused_paths[(ref, start, end)]
        selected['S' + str(len(selected) + 1)] = entry
        used += len(quote.encode())
    # Lexical candidate availability is deliberately separate from answer support.
    parts = [part.strip(' ?.,') for part in re.split(r'[?;]|\s+(?:e|and)\s+', question) if part.strip(' ?.,')]
    subrequests = []
    for part in parts:
        query = terms_of(part) - terms_of(source_id or '') - {'o', 'a', 'os', 'as', 'de', 'do', 'da', 'qual', 'what', 'is', 'the'}
        located = [c for c in candidates if query & terms_of(c[4] + ' ' + focused_paths.get((c[1], c[2], c[3]), ''))]
        refs = [key for key, e in selected.items() if query & terms_of(e['quote'] + ' ' + e.get('json_pointer', ''))]
        subrequests.append({'request': part, 'method': 'lexical_overlap/1',
                            'retrieval': 'evidence_selected' if refs else 'budget_or_overlap_exclusion' if located else 'not_located_in_examined_slice',
                            'selected_ids': refs, 'semantic_support': 'not_verified'})
    return selected, {"available_excerpts": len(candidates), "selected_excerpts": len(selected),
                      "selection": "identity_then_lexical_excerpts/4", "whole_source_read_claim": False,
                      "request": question, "decomposition": "explicit_conjunctions_partial/1", "subrequests": subrequests,
                      "semantic_support": "not_verified", "budget_bytes": max_bytes,
                      "used_bytes": used, "token_count": None,
                      "source_limit": 100, "source_byte_limit": 1_000_000,
                      "structured_candidate_limit_per_source": 2048,
                      "examined_sources": examined, "candidate_search_partial": partial,
                      "decisions": decisions[:256], "decision_log_limit": 256,
                      "omitted_decision_records": max(0, len(decisions) - 256),
                      "structured_issues": issues,
                      "omitted_excerpts": len(candidates) - len(selected),
                      "limitations": ["Exact identity paths/rows/headings do not infer entity mappings",
                                      "Oversized prose uses adjacent sentence windows; semantic completeness is not verified",
                                      "Selected excerpts cannot establish unreceived causes"]}

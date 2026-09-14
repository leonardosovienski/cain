"""Literal structured relations and addressable excerpts; no scientific inference."""

import json
import re
import unicodedata
from hashlib import sha256


def tokens_of(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c)))


def terms_of(text):
    return set(tokens_of(text))


def table_header_span(text, start, end):
    """Locate the literal labels, without including intervening data rows."""
    lines = list(re.finditer(r'[^\r\n]+', text[:end]))
    position = next((i for i, line in enumerate(lines) if line.start() == start), None)
    if position is None:
        return None
    columns = text[start:end].count('|')
    for i in range(position - 1, 0, -1):
        line, following = lines[i], lines[i + 1]
        if (not line.group().strip().startswith('|') or
                text[line.end():following.start()].count('\n') > 1):
            break
        if re.fullmatch(r'[ \t]*\|(?:[ \t]*:?-{3,}:?[ \t]*\|){2,}[ \t]*', line.group()):
            header = lines[i - 1]
            if (header.group().count('|') == columns == line.group().count('|') and
                    '\\|' not in header.group() and
                    text[header.end():line.start()].count('\n') == 1):
                return header.start(), line.end()
            break
    return None


def markdown_headings(text):
    """ATX headings outside fenced examples; offsets remain in the source text."""
    fence = None
    for line in re.finditer(r'(?m)^[^\r\n]+', text):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line[0])
        if fence:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]
                    and not marker[2].strip()):
                fence = None
            continue
        if marker and not (marker[1][0] == '`' and '`' in marker[2]):
            fence = (marker[1][0], len(marker[1]))
            continue
        heading = re.match(r'^(#{1,6})[ \t]+([^\r\n]+)', line[0])
        if heading:
            yield len(heading[1]), line.start(), line.end(), heading[2].rstrip()


def heading_spans(text, start):
    """Retain the actual heading hierarchy, including historical qualifiers."""
    stack = []
    for level, begin, end, _ in markdown_headings(text[:start]):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, begin, end))
    return [(a, b) for _, a, b in stack]


def document_contexts(evidence):
    """Reconstruct heading context only across contiguous same-publication parts.

    Nothing implies that the final part completes the original document. Gaps,
    overlaps and different publications never authorize joining observations.
    """
    groups, result = {}, {}
    for ref, item in evidence.items():
        text = item['text']
        result[ref] = (text, 0, [(0, len(text), ref)])
        start, end = item.get('start'), item.get('end')
        if (':' in ref and item.get('source') and item.get('offset_unit') == 'unicode_codepoints'
                and type(start) is int and type(end) is int and end - start == len(text)):
            groups.setdefault((ref.split(':')[0], item['source']), []).append((start, end, ref))
    for parts in groups.values():
        parts.sort()
        if (len(parts) < 2 or parts[0][0] != 0 or parts[-1][1] > 1_000_000 or
                any(a[1] != b[0] for a, b in zip(parts, parts[1:]))):
            continue
        text = ''.join(evidence[ref]['text'] for _, _, ref in parts)
        for start, _, ref in parts:
            result[ref] = (text, start, parts)
    return result


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
    line_indices = {line.start(): i for i, line in enumerate(lines)}
    headings = [(line_indices[start], level, title)
                for level, start, _, title in markdown_headings(text)]
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
    contexts, owners, exact_targets = {}, {}, set()
    documents = document_contexts(evidence)
    if type(max_bytes) is not int or not 1 <= max_bytes <= 2200 or type(max_cards) is not int or not 1 <= max_cards <= 8:
        raise ValueError('Invalid evidence budget')
    terms = terms_of(question) - set(
        'o a os as um uma de do da dos das em no na nos nas e ou que qual quais '
        'sobre para pelo pela por se com como the a an and or of in on to for '
        'what which is are can does do report relatorio permite concluir '
        'conclusion conclude forte stronger mais more impede impedem'.split())
    # Explicit alphanumeric identifiers outrank generic words, regardless of
    # project/domain. This is lexical retrieval, not an inferred entity mapping.
    anchors = [token for token in re.findall(r'\w+(?:[-_]\w+)*', question)
               if any(c.isdigit() for c in token) and any(c.isalpha() for c in token)]
    def anchor_score(value):
        return 1000 * sum(bool(re.search(r'(?<![\w-])' + re.escape(token) + r'(?![\w-])',
                                         value, re.I)) for token in anchors)
    question_tokens = tokens_of(question)
    pairs = {pair for pair in zip(question_tokens, question_tokens[1:])
             if all(token in terms for token in pair)}
    def relevance(value):
        tokens = tokens_of(value)
        return (len(terms & set(tokens)) +
                5 * len(pairs & set(zip(tokens, tokens[1:]))) + anchor_score(value))
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
                if relation['quote'].lstrip().startswith('|'):
                    header = table_header_span(text, start, end)
                    if header:
                        a, b = header
                        contexts[(ref, start, end)] = [dict(kind='table_header', start=a, end=b,
                                                           quote=text[a:b])]
                if (start, end) in spans:
                    continue
                spans.add((start, end))
                value = relation['quote'] + ' ' + relation.get('json_pointer', '')
                score = relevance(value)
                score += 2000 * sum(matches_identity(relation, token) for token in anchors)
                if any(matches_identity(relation, token) for token in anchors):
                    exact_targets.add((ref, start, end))
                candidates.append((score, ref, start, end, text[start:end]))
                if 'json_pointer' in relation:
                    focused_paths[(ref, start, end)] = relation['json_pointer']
            if source_id is not None or text.lstrip().startswith(('{', '[')):
                continue
        for number, (start, end) in enumerate(bounded_prose_spans(text, source_id, max_bytes)):
            if number >= 2048:
                partial = True
                break
            quote = text[start:end]
            # Tables are represented as individual rows plus separate labels.
            # A prose fallback must not reintroduce all the other identities.
            if any(line.lstrip().startswith('|') for line in quote.splitlines()):
                continue
            if not quote.strip() or not re.search(r'\w', quote):
                continue
            score = relevance(quote)
            score += 20 if source_id and re.search(r'(?<!\w)' + re.escape(source_id.casefold()) + r'(?!\w)', quote.casefold()) else 0
            if source_id and re.match(r'^\s*[-*]\s+\*{0,2}(?:state|status|limitations|estado|limitações)\b', quote, re.I):
                score += 12
            candidates.append((score, ref, start, end, quote))
    for _, ref, start, end, _ in candidates:
        text, base, parts = documents[ref]
        quote = evidence[ref]['text'][start:end]
        boundary = base + (end if quote.lstrip().startswith('#') else start)
        headings = heading_spans(text, boundary) if not text.lstrip().startswith(('{', '[')) else []
        def context_part(a, b, kind):
            containing = next(((lo, r) for lo, hi, r in parts if lo <= a and b <= hi), None)
            if containing is None:
                return  # do not pretend a cross-boundary heading is one literal quote
            lo, context_ref = containing
            contexts.setdefault((ref, start, end), []).append(dict(
                kind=kind, reference=context_ref, start=a-lo, end=b-lo, quote=text[a:b]))
        if quote.lstrip().startswith('|'):
            header = table_header_span(text, base + start, base + end)
            if header:
                contexts[(ref, start, end)] = []
                context_part(*header, 'table_header')
        for a, b in headings:
            title = re.sub(r'^#+\s+', '', text[a:b])
            token = re.match(r'[A-Za-z][\w-]*', title)
            if token and any(c.isdigit() for c in token[0]):
                owners[(ref, start, end)] = token[0]
        for a, b in headings[-2:]:
            if (a, b) == (base + start, base + end):
                continue
            context_part(a, b, 'section_heading')
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    anchored_candidates = bool(anchors and any(anchor_score(c[4]) for c in candidates))
    selected, used = {}, 0
    for _, ref, start, end, quote in candidates:
        context = contexts.get((ref, start, end), [])
        size = len(quote.encode()) + sum(len(part['quote'].encode()) for part in context)
        owner = owners.get((ref, start, end))
        reason = ('different_section_identity' if anchors and owner and (ref, start, end) not in exact_targets and owner.casefold() not in {a.casefold() for a in anchors}
                  else 'question_identifier_mismatch' if anchored_candidates and not anchor_score(quote)
                  else 'overlapping_selected_context' if any(e['reference'] == ref and start < e['end'] and end > e['start'] for e in selected.values())
                  else 'card_limit' if len(selected) >= max_cards
                  else 'byte_budget' if used + size > max_bytes else 'selected')
        decisions.append({'reference': ref, 'start': start, 'end': end, 'decision': reason})
        if reason != 'selected':
            continue
        entry = {"reference": ref, "quote": quote, "start": start, "end": end,
                 "source_sha256": sha256(evidence[ref]['text'].encode()).hexdigest(),
                 "offset_unit": "unicode_codepoints"}
        if (ref, start, end) in focused_paths:
            entry['json_pointer'] = focused_paths[(ref, start, end)]
        if context:
            entry['source_context'] = context
        selected['S' + str(len(selected) + 1)] = entry
        used += size
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
                      "selection": "identity_then_lexical_excerpts/7", "whole_source_read_claim": False,
                      "question_identifiers": anchors,
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

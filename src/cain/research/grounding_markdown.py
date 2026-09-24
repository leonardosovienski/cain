"""Markdown structure: headings, table headers, preambles, contiguous parts and prose spans."""

import re


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


def document_preamble_span(text, start):
    """Keep the leading scope across sibling titles at the document's top level.

    Preserve it literally, without classifying its truth or inferring that one
    dated statement supersedes another. Oversized context must be omitted with
    its candidate, not silently stripped from a historical assertion.
    """
    headings = list(markdown_headings(text))
    top = headings[0][0] if headings else 1
    titles = [(a, b) for level, a, b, _ in headings if level <= top]
    if len(titles) >= 2 and not text[:titles[0][0]].strip() and start >= titles[1][0]:
        # A sibling hypothesis is not the scope of another named hypothesis.
        def identity(a, b):
            token = re.match(r'#+\s+([A-Za-z][\w-]*)', text[a:b])
            return token[1].casefold() if token and any(c.isdigit() for c in token[1]) else None
        first = identity(*titles[0])
        current = next((identity(a, b) for a, b in reversed(titles) if a <= start), None)
        if first and current and first != current:
            return None
        return 0, titles[1][0]
    return None


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

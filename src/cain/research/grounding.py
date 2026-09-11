"""Literal structured relations and addressable excerpts; no scientific inference."""

import json
import re


def structured(evidence, source_id=None):
    relations, recognized, issues = [], 0, []
    seen = set()
    for ref, text in evidence.items():
        if text in seen:
            continue
        seen.add(text)
        entries = []
        if text.lstrip().startswith(("{", "[")):
            recognized += 1
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
            for match in re.finditer(r'^\s*\|([^|\r\n]+)\|([^|\r\n]+)\|\s*$', text, re.MULTILINE):
                subject, obj = (match.group(n).strip() for n in (1, 2))
                if not subject or not obj or set(subject + obj) <= set('-: '):
                    continue
                if len(subject) <= 150 and len(obj) <= 150 and len(match.group()) <= 1000:
                    entries.append({"subject": subject, "predicate": "reported_table_value", "object": obj,
                                    "reference": ref, "quote": match.group(), "start": match.start(), "end": match.end()})
            recognized += bool(entries)
        focused = [r for r in entries if r.get('decoded_subject', r['subject']) == source_id]
        relations.extend(focused or entries)
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
                   if source_id is not None and r.get('decoded_subject', r['subject']) == source_id]
        if focused:
            # Shared JSON commonly contains every hypothesis. Pass only exact-key
            # values for the selected identity, with paths distinguishing state/trial.
            for relation in focused:
                start, end = relation['start'], relation['end']
                candidates.append((100, ref, start, end, relation['quote']))
                if 'json_pointer' in relation:
                    focused_paths[(ref, start, end)] = relation['json_pointer']
            continue
        for line in re.finditer(r'[^\r\n]+', text):
            # Long lines become explicitly partial, contiguous excerpts.
            for start in range(line.start(), line.end(), 400):
                end = min(start + 400, line.end())
                quote = text[start:end]
                if not quote.strip() or not re.search(r'\w', quote):
                    continue
                score = len(terms & set(re.findall(r'\w+', quote.casefold())))
                score += 20 if source_id and source_id.casefold() in quote.casefold() else 0
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
                      "selection": "identity_then_lexical_excerpts/2", "whole_source_read_claim": False,
                      "structured_issues": issues,
                      "limitations": ["Exact-key focus omits shared prose and unrelated keys; it cannot explain unreceived causes"]}

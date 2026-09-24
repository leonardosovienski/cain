"""Literal structured relations and addressable excerpts; no scientific inference.

``cards`` (the bounded excerpt selector) lives here; the helpers it composes are in
``grounding_text`` (question terms and identities), ``grounding_markdown`` (document
structure and prose spans) and ``grounding_structured`` (literal relations). Every
helper stays importable from this module.
"""

import re
from hashlib import sha256

from cain.research.grounding_markdown import (
    bounded_prose_spans, document_contexts, document_preamble_span, heading_spans,
    markdown_headings, prose_spans, table_header_span,
)
from cain.research.grounding_structured import matches_identity, structured
from cain.research.grounding_text import question_identities, terms_of, tokens_of

__all__ = [
    "bounded_prose_spans", "cards", "document_contexts", "document_preamble_span", "heading_spans",
    "markdown_headings", "matches_identity", "prose_spans", "question_identities", "structured",
    "table_header_span", "terms_of", "tokens_of",
]


def cards(evidence, question, source_id=None, *, max_bytes=2200, max_cards=8):
    """Select bounded exact excerpts, retaining source offsets and disclosed coverage."""
    candidates, seen, focused_paths, issues = [], set(), {}, []
    contexts, owners, exact_targets, heading_targets = {}, {}, set(), {}
    missing_document_context = set()
    documents = document_contexts(evidence)
    # Explicit source paths filter documents while retaining their revisions.
    named_sources = {item['source'] for item in evidence.values()
                     if item.get('source') and item['source'] in question}
    if type(max_bytes) is not int or not 1 <= max_bytes <= 2200 or type(max_cards) is not int or not 1 <= max_cards <= 8:
        raise ValueError('Invalid evidence budget')
    content_question = question
    for named_source in sorted(named_sources, key=len, reverse=True):
        content_question = content_question.replace(named_source, ' ')
    terms = terms_of(content_question) - set(
        'o a os as um uma de do da dos das em no na nos nas e ou que qual quais '
        'sobre para pelo pela por se com como the a an and or of in on to for '
        'what which is are can does do report relatorio permite concluir '
        'conclusion conclude forte stronger mais more impede impedem '
        'permanece permanecem remain remains remained'.split())
    # Explicit alphanumeric identifiers outrank generic words, regardless of
    # project/domain. This is lexical retrieval, not an inferred entity mapping.
    anchors, resolutions = question_identities(content_question, evidence)
    # Small, explicit bilingual field vocabulary; this expands retrieval terms,
    # not scientific meanings or verdicts.
    field_terms = {
        'regra': {'rule', 'signal', 'mechanism', 'factor', 'portfolio'}, 'hipotese': {'hypothesis', 'mechanism'},
        'criterio': {'criterion', 'criteria', 'metric', 'success', 'acceptance'},
        'criterios': {'criterion', 'criteria', 'success', 'acceptance'},
        'resultado': {'result', 'results', 'verdict', 'status'},
        'motivo': {'reason', 'reasons', 'issues'},
        'limitacoes': {'limitations', 'issues', 'unknowns'},
        'limitacao': {'limitations', 'issues', 'unknowns'},
        'mecanismo': {'mechanism', 'signal', 'rule'},
        'cronologia': {'timeline', 'timing', 'known', 'publication'},
        'confiabilidade': {'reliability'}, 'veredicto': {'verdict', 'veredito'},
        'veredito': {'verdict', 'veredicto'},
        'periodo': {'test_period', 'test_start', 'warmup_end'},
        'execucao': {'execution', 'price'},
        'proximo': {'next', 'reopening'}, 'reabra': {'reopening'},
        'reabertura': {'reopening'}, 'automaticamente': {'automatic'},
        'numeros': {'numbers', 'counts', 'count', 'metrics'},
        'denominadores': {'denominator'},
    }
    for term in tuple(terms):
        terms.update(field_terms.get(term, set()))
    def anchor_score(value):
        return 20 * any(re.search(r'(?<![\w-])' + re.escape(token) + r'(?![\w-])',
                                  value, re.I) for token in anchors)
    question_tokens = tokens_of(content_question)
    pairs = {pair for pair in zip(question_tokens, question_tokens[1:])
             if all(token in terms for token in pair)}
    def relevance(value):
        tokens = tokens_of(value)
        return (len(terms & set(tokens)) +
                5 * len(pairs & set(zip(tokens, tokens[1:]))) + anchor_score(value))
    partial, examined, decisions = False, 0, []
    for ref, item in evidence.items():
        text = item['text']
        if named_sources and item.get('source') not in named_sources:
            decisions.append({'reference': ref, 'start': 0, 'end': len(text),
                              'decision': 'explicit_source_mismatch'})
            continue
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
                for label in relation.get('record_context', []):
                    if (label['start'], label['end']) != (start, end):
                        contexts.setdefault((ref, start, end), []).append(dict(
                            kind='json_record_context', reference=ref, start=label['start'],
                            end=label['end'], quote=label['quote']))
                if (start, end) in spans:
                    continue
                spans.add((start, end))
                value = relation['quote'] + ' ' + relation.get('json_pointer', '')
                value += ' ' + ' '.join(p['quote'] for p in relation.get('record_context', []))
                score = relevance(value)
                score += 20 * any(matches_identity(relation, token) for token in anchors)
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
                return False  # do not pretend cross-boundary context is one literal quote
            lo, context_ref = containing
            contexts.setdefault((ref, start, end), []).append(dict(
                kind=kind, reference=context_ref, start=a-lo, end=b-lo, quote=text[a:b]))
            return True
        if quote.lstrip().startswith('|'):
            header = table_header_span(text, base + start, base + end)
            if header:
                contexts[(ref, start, end)] = []
                context_part(*header, 'table_header')
        for a, b in headings:
            title = re.sub(r'^#+\s+', '', text[a:b])
            heading_targets.setdefault((ref, start, end), set()).update(
                anchor for anchor in anchors
                if re.search(r'(?<![\w-])' + re.escape(anchor) + r'(?![\w-])', title, re.I))
            token = re.match(r'[A-Za-z][\w-]*', title)
            if token and any(c.isdigit() for c in token[0]):
                owners[(ref, start, end)] = token[0]
        for a, b in headings[-2:]:
            if (a, b) == (base + start, base + end):
                continue
            context_part(a, b, 'section_heading')
        preamble = document_preamble_span(text, base + start) if headings else None
        if preamble and not context_part(*preamble, 'document_preamble'):
            missing_document_context.add((ref, start, end))
    # Heading identity is part of a passage's relevance, even when the body
    # says only "status" or "horizon". Keep each requested identity represented
    # before spending the shared budget on more passages of the first one.
    def target_ids(candidate):
        _, ref, start, end, quote = candidate
        pointer = focused_paths.get((ref, start, end))
        if pointer:
            literal_context = ' '.join(p['quote'] for p in contexts.get((ref, start, end), []))
            return {a for a in anchors if a in [p.replace('~1','/').replace('~0','~') for p in pointer.split('/')]
                    or re.search(r'(?<![\w-])' + re.escape(a) + r'(?![\w-])', literal_context, re.I)}
        if quote.lstrip().startswith('|'):
            subject = quote.strip().split('|')[1].strip().strip('`')
            return {a for a in anchors if a.casefold() == subject.casefold()}
        owner = owners.get((ref, start, end))
        if owner and owner.casefold() in {a.casefold() for a in anchors}:
            return {a for a in anchors if a.casefold() == owner.casefold()}
        value = quote
        value += ' ' + ' '.join(p['quote'] for p in contexts.get((ref, start, end), []))
        return {a for a in anchors if re.search(r'(?<![\w-])'+re.escape(a)+r'(?![\w-])', value, re.I)}

    def density(candidate):
        score, ref, start, end, quote = candidate
        parts = contexts.get((ref, start, end), [])
        total = len(quote.encode()) + sum(len(p['quote'].encode()) for p in parts)
        return (score + relevance(' '.join(p['quote'] for p in parts))) / max(1, total)**0.5
    content_terms = terms - terms_of(' '.join(anchors))
    candidates.sort(key=lambda c: (-len(content_terms & terms_of(c[4])), -density(c), c[1], c[2]))
    ordered = []
    for anchor in anchors:
        matching = [c for c in candidates if anchor in target_ids(c)
                    and not c[4].lstrip().startswith('#')]
        choice = next((c for c in matching if (c[1], c[2], c[3]) in exact_targets),
                      matching[0] if matching else None)
        if choice is not None and choice not in ordered:
            ordered.append(choice)
    # Explicit numeric phrases (e.g. an exit-code definition) are a separate
    # requested fact, even without repeating a hypothesis ID in that paragraph.
    numeric_phrases = re.findall(r'\b[A-Za-zÀ-ÿ]+\s+[A-Za-zÀ-ÿ]+\s+\d+\b', question)
    for phrase in numeric_phrases:
        phrase_terms = tokens_of(phrase)
        choice = next((c for c in candidates if ' '.join(phrase_terms) in ' '.join(tokens_of(c[4]))), None)
        if choice is not None and choice not in ordered:
            ordered.insert(0, choice)
    result_cards = []
    if terms & {'resultado', 'result', 'veredicto', 'veredito', 'verdict'}:
        result_sources, result_cards = set(), []
        for c in candidates:
            source = evidence[c[1]].get('source', c[1])
            if (source not in result_sources and (not anchors or target_ids(c))
                    and not c[4].lstrip().startswith('#')
                    and re.search(r'\b(?:resultado|result|veredicto|veredito|verdict)\b(?:\s+[\w-]+){0,2}\s*(?::|\bé\b|\bis\b)', re.sub(r'[*`]', '', c[4]), re.I)):
                result_cards.append(c)
                result_sources.add(source)
            if len(result_cards) >= 2:
                break
        # Preserve explicit reported results before procedural or registration
        # paragraphs. Separate sources can contain original and corrected values.
        first = [c for c in ordered if any(' '.join(tokens_of(p)) in ' '.join(tokens_of(c[4])) for p in numeric_phrases)]
        ordered = first + [c for c in result_cards if c not in first] + [c for c in ordered if c not in first and c not in result_cards]
    # A protocol question requests distinct fields. Repeated execution fees
    # must not consume every card before the rule, test window and criterion.
    # These are literal field-name matches, never reconstructed protocols.
    facets = []
    if terms & {'regra', 'rule'}:
        facets += [{'rule', 'signal', 'mechanism', 'factor'}, {'quantile'}]
    if terms & {'periodo', 'period'}:
        facets += [{'test_period', 'period'}]
    if terms & {'execucao', 'execution'}:
        facets += [{'price'}]
    if terms & {'criterio', 'criterion', 'criteria'}:
        facets += [{'metric', 'criterion', 'criteria'}]
    if terms & {'resultado', 'result', 'veredicto', 'veredito', 'verdict'}:
        facets += [{'verdict'}]
    if terms & {'confiabilidade', 'reliability'}:
        facets += [{'reliability'}]
    if terms & {'proximo', 'next'}:
        facets += [{'next', 'basis'}]
    if terms & {'denominadores', 'denominator'}:
        facets += [{'denominator'}]
    facet_cards = []
    for facet in facets:
        options = [c for c in candidates if (not anchors or target_ids(c))
                   and (path := focused_paths.get((c[1], c[2], c[3])))
                   and facet & terms_of(path)]
        if options and options[0] not in facet_cards:
            facet_cards.append(options[0])
    priority = result_cards + [c for c in facet_cards if c not in result_cards]
    ordered = priority + [c for c in ordered if c not in priority]
    # Requested closure reasons need their own literal passage, not only status.
    if terms & {'motivo', 'razao', 'razoes', 'reason', 'reasons', 'why', 'encerramento', 'closure'}:
        for anchor in anchors:
            options = [c for c in candidates if anchor in target_ids(c)
                       and not c[4].lstrip().startswith('#')
                       and re.search(r'\b(?:motivo|reason)\b\s*:|\b(?:risco|because)\b|\bdue to\b|\b(?:interrompid|encerrad)\w*.{0,100}\b(?:por|devido)\b', c[4], re.I)]
            if options and options[0] not in ordered:
                ordered.append(options[0])
    # A second source about the requested identity must not be displaced by
    # many paragraphs from its first source (e.g. registration vs observation).
    source_round = []
    seen_sources = {evidence[c[1]].get('source', c[1]) for c in ordered}
    for c in candidates:
        source = evidence[c[1]].get('source', c[1])
        if (source not in seen_sources and not c[4].lstrip().startswith('#')
                and (not anchors or target_ids(c))):
            source_round.append(c)
            seen_sources.add(source)
    # Represent each literal observation revision before duplicate fields of
    # another revision. Source names alone collapse JSONL observations.
    revision_round, seen_revisions = [], set()
    for c in candidates:
        parts = contexts.get((c[1], c[2], c[3]), [])
        revision = tuple(p['quote'] for p in parts if p['kind'] == 'json_record_context'
                         and re.search(r'"(?:observation_revision|revision)"\s*:', p['quote']))
        group = (evidence[c[1]].get('source', c[1]), revision)
        if revision and group not in seen_revisions and (not anchors or target_ids(c)):
            revision_round.append(c)
            seen_revisions.add(group)
    first = revision_round + [c for c in ordered if c not in revision_round]
    candidates = first + [c for c in source_round if c not in first] + [
        c for c in candidates if c not in first and c not in source_round]
    specific_query_match = (not anchors and source_id is None and len(terms) >= 2 and
                            any(len(terms & terms_of(c[4])) >= 2 for c in candidates))
    selected, used, used_context = {}, 0, set()
    for _, ref, start, end, quote in candidates:
        context = contexts.get((ref, start, end), [])
        new_context = [p for p in context if (p.get('reference', ref), p['start'], p['end']) not in used_context]
        size = len(quote.encode()) + sum(len(part['quote'].encode()) for part in new_context)
        owner = owners.get((ref, start, end))
        matched = target_ids((0, ref, start, end, quote))
        pointer = focused_paths.get((ref, start, end), '')
        requested_field = bool(pointer and pointer.rsplit('/', 1)[-1] in tokens_of(content_question))
        numeric_match = any(' '.join(tokens_of(p)) in ' '.join(tokens_of(quote)) for p in numeric_phrases)
        reason = ('missing_document_context' if (ref, start, end) in missing_document_context
                  else 'weak_query_overlap' if specific_query_match and not requested_field and len(terms & terms_of(quote)) < 2
                  else 'heading_context_only' if quote.lstrip().startswith('#')
                  else 'different_section_identity' if anchors and owner and (ref, start, end) not in exact_targets and owner.casefold() not in {a.casefold() for a in anchors} and not heading_targets.get((ref, start, end))
                  else 'question_identifier_mismatch' if anchors and not matched and not numeric_match
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
        used_context.update((p.get('reference', ref), p['start'], p['end']) for p in context)
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
                      "selection": "identity_balanced_excerpts/15", "whole_source_read_claim": False,
                      "question_identifiers": anchors,
                      "identifier_resolution": resolutions,
                      "identity_coverage": [{'identity': a,
                          'accessible': any(a in target_ids(c) for c in candidates),
                          'selected_ids': [key for key, e in selected.items() if a in target_ids((0,e['reference'],e['start'],e['end'],e['quote']))],
                          'semantic_support': 'not_verified'} for a in anchors],
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

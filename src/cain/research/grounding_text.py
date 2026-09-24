"""Question tokenisation and explicit identity resolution for evidence retrieval."""

import re
import unicodedata


def tokens_of(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c)))


def terms_of(text):
    tokens = tokens_of(text)
    return set(tokens) | {part for token in tokens for part in token.split('_') if part}


def question_identities(question, evidence):
    """Resolve explicit list shorthand, never infer a cross-domain equivalence."""
    pattern = r'\w+(?:[-_]\w+)*'
    anchors = [m[0] for m in re.finditer(pattern, question)
               if any(c.isdigit() for c in m[0]) and any(c.isalpha() for c in m[0])]
    resolutions = []
    for match in re.finditer(r'\b([A-Za-z][\w-]*-)(\d+)\b', question):
        tail = question[match.end():]
        for extra in re.finditer(r'\A\s*(?:,|e\b|and\b)\s*(\d+)(?!\w)', tail):
            # Advance through a strictly contiguous list; do not interpret
            # unrelated quantities later in the sentence as identity suffixes.
            while extra:
                if len(extra[1]) != len(match[2]):
                    break
                resolved = match[1] + extra[1]
                anchors.append(resolved)
                resolutions.append({'literal': extra[1], 'identity': resolved,
                                    'rule': 'explicit_contiguous_prefix_list'})
                tail = tail[extra.end():]
                extra = re.match(r'\s*(?:,|e\b|and\b)\s*(\d+)(?!\w)', tail)
    available = set(re.findall(r'\b[A-Za-z][\w]*(?:-[\w]+)+-\d+\b',
                               '\n'.join(item['text'] for item in evidence.values())))
    for match in re.finditer(r'\bclaims?\b[^\d\n:;?.]{0,50}(\d{3}(?:(?:\s*,\s*|\s+e\s+|\s+and\s+)\d{3})*)', question, re.I):
        for suffix in re.findall(r'\d{3}', match[1]):
            found = sorted(a for a in available if a.casefold().startswith('claim-') and a.endswith('-'+suffix))
            if len(found) == 1:
                anchors.append(found[0])
            resolutions.append({'literal': suffix, 'candidates': found,
                                'rule': 'unique_received_claim_suffix' if len(found) == 1 else 'unresolved_claim_suffix'})
    constraint = re.search(r'\b(?:não transfira|do not transfer)\b[^.!?\n]*?\b(?:para|to)\b([^.!?\n]*)', question, re.I)
    if constraint:
        outside = question[:constraint.start(1)] + question[constraint.end(1):]
        excluded = [a for a in anchors if re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)', constraint[1], re.I)
                    and not re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)', outside, re.I)]
        anchors = [a for a in anchors if a not in excluded]
        resolutions.extend({'literal': a, 'rule': 'explicit_do_not_transfer_target',
                            'role': 'constraint_not_requested_subject'} for a in excluded)
    return list(dict.fromkeys(anchors)), resolutions

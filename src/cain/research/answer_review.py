"""Conservative diagnostics for generated answers, never semantic approval."""

from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import unicodedata


def receipt_hash(analysis):
    payload = {
        key: analysis.get(key)
        for key in ("question", "fields", "evidence", "raw_response", "proposal")
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _numbers(text):
    if type(text) is not str:
        return []
    normalized = re.sub(r"\[[ST]\d+\]", "", text).replace("−", "-")
    found = []
    for match in re.finditer(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?%?", normalized):
        token = match.group()
        try:
            value = Decimal(token.rstrip("%").replace(",", "."))
        except InvalidOperation:
            continue
        found.append((token, (value, token.endswith("%"))))
    return found


def _canonical_heading(value):
    value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", "_", value.strip().lower())


def parse_sections(text, fields):
    """Normalize presentation only; never rewrite generated assertions."""
    if type(text) is not str or type(fields) not in (list, tuple):
        return {}, ["invalid_parser_input"]
    expected = {_canonical_heading(field): field for field in fields if type(field) is str}
    if len(expected) != len(fields):
        return {}, ["ambiguous_expected_fields"]
    pattern = re.compile(r"^(?:###\s+([^\r\n]+?)|\*\*([^\r\n]+?)\*\*)\s*$", re.M)
    matches = list(pattern.finditer(text))
    sections, errors = {}, []
    if not matches:
        return {}, ["unparsed_response", "incorrect_fields"]
    if text[: matches[0].start()].strip():
        errors.append("unparsed_preamble")
    for index, match in enumerate(matches):
        canonical = _canonical_heading(match.group(1) or match.group(2))
        name = expected.get(canonical, canonical)
        body = text[
            match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)
        ].strip()
        if canonical not in expected:
            errors.append(name + ":unexpected_field")
        if name in sections:
            errors.append(name + ":duplicate_field")
        sections[name] = {
            "explanation": body,
            "source_ids": sorted(set(re.findall(r"\[([ST][0-9]+)\]", body))),
        }
    if set(sections) != set(fields):
        errors.append("incorrect_fields")
    return sections, errors


def review_answer(analysis):
    """Return lexical alerts while always withholding semantic approval."""
    evidence = analysis.get("evidence", []) if isinstance(analysis, dict) else []
    sources = {
        item["id"]: item["text"]
        for item in evidence
        if isinstance(item, dict) and type(item.get("id")) is str and type(item.get("text")) is str
    }
    alerts = []
    for error in analysis.get("structural_errors", []):
        alerts.append({"code": "structure", "detail": str(error)})
    proposal = analysis.get("proposal", {})
    if not isinstance(proposal, dict):
        proposal = {}
        alerts.append({"code": "invalid_proposal"})
    for field, section in proposal.items():
        if not isinstance(section, dict):
            alerts.append({"code": "invalid_section", "field": field})
            continue
        text = section.get("explanation", "")
        refs = section.get("source_ids", [section.get("source_id")])
        refs = refs if isinstance(refs, list) else []
        refs = [reference for reference in refs if type(reference) is str]
        if not refs or any(reference not in sources or not sources[reference].strip() for reference in refs):
            alerts.append({"code": "missing_unknown_or_empty_source", "field": field})
        support = "\n".join(sources[reference] for reference in refs if reference in sources)
        supported_numbers = {value for _, value in _numbers(support)}
        for token, value in _numbers(text):
            if value not in supported_numbers:
                alerts.append(
                    {"code": "number_requires_verification", "field": field, "token": token}
                )
        topics = {
            "economic_claim": r"lucro|rentabilidade|capital|profit",
            "scientific_state": r"refutad|refutaç|validada|insuficien|insuficiên|ativad",
            "metric_assignment": r"\bDSR\b|\bSharpe\b|\bpoder\b|\bPSR\b",
        }
        for code, pattern in topics.items():
            if type(text) is str and re.search(pattern, text, re.I):
                alerts.append({"code": code + "_requires_review", "field": field})
    raw = analysis.get("raw_response", "")
    if raw:
        _, parse_errors = parse_sections(raw, analysis.get("fields", []))
        alerts.extend({"code": "presentation", "detail": error} for error in parse_errors)
    return {
        "receipt_sha256": receipt_hash(analysis),
        "alerts": alerts,
        "release_status": "withheld_pending_external_review",
        "semantic_status": "requires_review",
        "approved_knowledge": False,
        "limitations": (
            "Lexical triage only; no proof of entailment, numeric derivation, correct metric "
            "assignment or scientific validity."
        ),
    }


def render_pending(analysis, review=None):
    """Return a safe status while retaining the raw proposal in the audit artifact."""
    return {
        "message": (
            "Resposta pendente de conferência com as fontes. "
            "Não há conclusão científica aprovada."
        ),
        "review": review if review is not None else review_answer(analysis),
    }

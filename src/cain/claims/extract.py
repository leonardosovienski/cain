"""Claim extraction with a local model (Claimify-style selection, disambiguation, decomposition).

The model only proposes. Each proposed claim must quote its source span literally from the report
(stored as a memory document); non-verifiable content becomes UNVERIFIABLE, content the model
flags as ambiguous becomes AMBIGUOUS (never a guessed reading), and the rest waits for
verification (INCONCLUSIVE, ``pending_verification``). Every claim records the model, its digest,
the prompt hash and the extractor version.
"""

from __future__ import annotations

from hashlib import sha256
import json

from cain.memory.ingest import model_digest
from cain.memory.store import MemoryStore, MemoryStoreError

EXTRACTOR_VERSION = "claimify-lite/1"
INSTRUCTION = (
    "You extract checkable claims from a research report. Work sentence by sentence.\n"
    "1. Selection: skip opinions, plans, questions and content that cannot be checked against a source.\n"
    "2. Disambiguation: if a sentence can be read in more than one way and the text does not settle it, "
    "mark it ambiguous instead of choosing a reading.\n"
    "3. Decomposition: split what remains into atomic, self-contained claims (resolve pronouns with words "
    "from the report; add no outside knowledge).\n"
    "For every claim return: text (the self-contained claim), source_quote (the exact characters of the "
    "report sentence it comes from, copied verbatim), verifiable (true/false), ambiguous (true/false) and "
    "reason (one short phrase). Return at most 20 claims."
)
SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array", "maxItems": 20, "items": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "source_quote": {"type": "string"},
                       "verifiable": {"type": "boolean"}, "ambiguous": {"type": "boolean"},
                       "reason": {"type": "string"}},
        "required": ["text", "source_quote", "verifiable", "ambiguous", "reason"],
    }}},
    "required": ["claims"],
}


def extract_claims(memory: MemoryStore, provider, *, cube: str, document_id: str) -> dict:
    now = memory.clock()
    report = memory.document(document_id, as_of=now)
    if report is None or report["cube"] != cube:
        raise MemoryStoreError("DOCUMENT_UNKNOWN", "the report must be a current document of the cube")
    text = report["text"]
    if len(text) > 12000:
        raise MemoryStoreError("INVALID_FIELD", "report larger than 12000 characters; split it first")
    prompt = "Report:\n" + text
    prompt_hash = sha256((INSTRUCTION + "\n" + prompt).encode("utf-8")).hexdigest()
    digest = model_digest(provider)
    raw = provider.generate_json(prompt, INSTRUCTION, SCHEMA)
    try:
        proposals = json.loads(raw)["claims"]
        if not isinstance(proposals, list) or len(proposals) > 20:
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise MemoryStoreError("EXTRACTION_INVALID", "model output is not the requested JSON") from exc
    extractor = {"model": getattr(provider, "model", type(provider).__name__),
                 "model_digest": digest, "prompt_hash": prompt_hash,
                 "version": EXTRACTOR_VERSION, "generation": getattr(provider, "last_metadata", None)}
    created, rejected = [], []
    for item in proposals:
        ok = (isinstance(item, dict) and type(item.get("text")) is str and item["text"].strip()
              and type(item.get("source_quote")) is str and len(item["source_quote"].strip()) >= 8
              and type(item.get("verifiable")) is bool and type(item.get("ambiguous")) is bool)
        start = text.find(item["source_quote"]) if ok else -1
        if start < 0:
            rejected.append({"proposal": item, "reason": "source_quote is not a literal span of the report"})
            continue
        status = "AMBIGUOUS" if item["ambiguous"] else ("INCONCLUSIVE" if item["verifiable"] else "UNVERIFIABLE")
        claim = memory.record_claim(cube, item["text"].strip(), source_document_id=document_id,
                                    char_start=start, char_end=start + len(item["source_quote"]),
                                    status=status, extractor=extractor)
        created.append({"id": claim["id"], "status": status,
                        "occurrences_of_quote": text.count(item["source_quote"])})
    return {"document_id": document_id, "claims": created, "rejected": rejected, "extractor": extractor}

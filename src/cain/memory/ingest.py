"""Paths into the bitemporal memory.

* ``ingest_research``: deterministic, no model. Each admitted research record (a predictor's
  published, hash-verified Snapshot record) becomes one fact. ``PROVEN`` here means "literal
  transcription of a hashed source record", never that the record is scientifically true.
* ``extract_facts``: a local model proposes facts from free text. Every extracted fact is
  born ``DECLARED``, must quote the text literally and records model, digest, prompt hash
  and extractor version.
"""

from __future__ import annotations

from hashlib import sha256
import json

from cain.memory.jcs import canonicalize
from cain.memory.store import MemoryStore, MemoryStoreError

RESEARCH_EXTRACTOR = "deterministic:research-snapshot-record/1"
LLM_EXTRACTOR = "llm-fact-extraction/1"
_SNAPSHOT_RECORD_KEYS = (
    "source_id", "revision", "kind", "identity_basis", "source_status", "status_axis", "mapping",
    "reason", "event_at", "recorded_at", "available_at", "supersedes", "evidence_ids",
)
_PAGE = 50


def research_record_hash(record: dict) -> str:
    return sha256(canonicalize({k: record[k] for k in _SNAPSHOT_RECORD_KEYS})).hexdigest()


def ingest_research(memory: MemoryStore, service, scope, *, cube: str, as_of) -> dict:
    """Transcribe every admitted record of ``cube``'s domain in ``scope`` into facts.

    Idempotent by source hash. A record revision that declares ``supersedes`` for a revision
    already in memory supersedes that fact; revisions without that declaration coexist
    (the research archive never picks an implicit latest version).
    """
    records, offset = [], 0
    while True:
        page = service.query(scope, domain=cube, limit=_PAGE, offset=offset)
        records.extend(page["records"])
        if not page["has_more"]:
            break
        offset += _PAGE
    existing = {f["source_hash"]: f for f in memory.facts(as_of=as_of, cubes=[cube])
                if f["extractor_version"] == RESEARCH_EXTRACTOR}
    created, skipped = [], 0
    for record in sorted(records, key=lambda r: (r["source_id"], r["revision"])):
        if record["domain"] != cube:
            raise MemoryStoreError("CROSS_CUBE_INGESTION", "research record domain differs from the cube")
        source_hash = research_record_hash(record)
        if source_hash in existing:
            skipped += 1
            continue
        predicate = f"{record['status_axis']}_status"
        superseded = next(
            (f for f in memory.facts(as_of=as_of, cubes=[cube], subject=record["source_id"], predicate=predicate)
             if f["extractor_version"] == RESEARCH_EXTRACTOR and f["object"]["revision"] in record["supersedes"]),
            None,
        )
        fact = memory.assert_fact(
            cube, record["source_id"], predicate,
            {k: record[k] for k in ("source_status", "revision", "kind", "identity_basis", "reason",
                                    "mapping", "event_at", "recorded_at", "available_at")},
            status="PROVEN",
            valid_from=record["event_at"],
            source_episode_id=record["publications"][0],
            source_hash=source_hash,
            extractor_version=RESEARCH_EXTRACTOR,
            supersedes=None if superseded is None else superseded["id"],
        )
        existing[source_hash] = fact
        created.append(fact["id"])
    return {"cube": cube, "records_read": len(records), "facts_created": len(created), "skipped_existing": skipped,
            "fact_ids": created}


_INSTRUCTION = (
    "Extract at most 8 atomic facts stated in the text. Use only information literally present. "
    "For each fact give subject, predicate, object and the exact quote (copied character by "
    "character from the text) that states it; subject and object must appear inside the quote. "
    "If nothing is clearly stated, return an empty list."
)
_SCHEMA = {
    "type": "object",
    "properties": {"facts": {"type": "array", "maxItems": 8, "items": {
        "type": "object",
        "properties": {k: {"type": "string"} for k in ("subject", "predicate", "object", "quote")},
        "required": ["subject", "predicate", "object", "quote"],
    }}},
    "required": ["facts"],
}


def model_digest(provider) -> str | None:
    """Digest of the model that will answer: the local Ollama inventory for ``OllamaLLM`` (fails
    closed when the model is not installed), otherwise the provider's declared ``model_digest``."""
    from cain.research.workflows import model_identity

    try:
        return model_identity(provider)["model_digest"]
    except (OSError, ValueError) as exc:
        raise MemoryStoreError("MODEL_UNKNOWN", f"cannot establish the model digest: {exc}") from exc


def extract_facts(memory: MemoryStore, provider, *, cube: str, text: str, source: str) -> dict:
    """Ask a local model for facts; keep only literally supported ones, all DECLARED."""
    if type(text) is not str or not text.strip() or len(text) > 6000:
        raise MemoryStoreError("INVALID_FIELD", "text must have 1-6000 characters")
    prompt = "Text:\n" + text
    prompt_hash = sha256((_INSTRUCTION + "\n" + prompt).encode("utf-8")).hexdigest()
    digest = model_digest(provider)
    raw = provider.generate_json(prompt, _INSTRUCTION, _SCHEMA)
    try:
        parsed = json.loads(raw)
        proposals = parsed["facts"]
        if not isinstance(proposals, list) or len(proposals) > 8:
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise MemoryStoreError("EXTRACTION_INVALID", "model output is not the requested JSON") from exc
    model = f"{getattr(provider, 'model', type(provider).__name__)}@{digest or 'unknown-digest'}"
    source_hash = sha256(text.encode("utf-8")).hexdigest()
    kept, rejected = [], []
    for item in proposals:
        fields = item if isinstance(item, dict) else {}
        values = [fields.get(k) for k in ("subject", "predicate", "object", "quote")]
        if (any(type(v) is not str or not v.strip() for v in values)
                or fields["quote"] not in text or fields["subject"] not in fields["quote"]
                or fields["object"] not in fields["quote"]):
            rejected.append(item)
            continue
        fact = memory.assert_fact(
            cube, fields["subject"], fields["predicate"], {"value": fields["object"], "quote": fields["quote"]},
            status="DECLARED", source_episode_id=source, source_hash=source_hash, extractor_model=model,
            extractor_prompt_hash=prompt_hash, extractor_version=LLM_EXTRACTOR,
        )
        kept.append(fact["id"])
    return {"cube": cube, "status": "DECLARED", "facts_created": len(kept), "fact_ids": kept,
            "rejected_without_literal_support": len(rejected), "extractor_model": model,
            "extractor_prompt_hash": prompt_hash, "generation": getattr(provider, "last_metadata", None)}

"""Claim assessment: two local verifiers for textual support, a deterministic check for empirical proof.

TEXTUAL_SUPPORT (a document supports it) and EMPIRICAL_PROOF (a run/evaluation artifact proves it)
are never mixed: textual claims are scored by two independent NLI-style verifiers over the cited
evidence; empirical claims are checked only against the hashed run artifact they name.

Decision rule ``two-verifiers-agree/1`` for TEXTUAL_SUPPORT:
* both verifiers at or above their thresholds on the best chunk -> SUPPORTED;
* both below -> INCONCLUSIVE (the cited evidence does not support it; these verifiers score
  support, not contradiction, so CONTRADICTED is only ever set by a human review);
* they disagree -> INCONCLUSIVE with ``review_state = needs_human_review`` (the review queue).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
import re
from typing import Protocol, Sequence

from cain.memory.store import MemoryStore, MemoryStoreError, instant

TEXTUAL_RULE = "two-verifiers-agree/1"
EMPIRICAL_RULE = "run-artifact-hash-and-numbers/1"
_NUMBER = re.compile(r"(?<![\w.,])[-+]?\d+(?:[.,]\d+)*%?(?![\w])")


class Verifier(Protocol):
    verifier_id: str
    weights_revision: str
    threshold: float

    def score(self, premise: str, hypothesis: str) -> float: ...


def chunks(text: str, *, size: int = 1500, overlap: int = 200) -> list[tuple[int, int]]:
    """Character windows covering the whole text (long documents: chunk, then take the max)."""
    if size <= overlap or size < 1:
        raise ValueError("chunk size must exceed the overlap")
    if len(text) <= size:
        return [(0, len(text))]
    spans, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        spans.append((start, end))
        if end == len(text):
            break
        start = end - overlap
    return spans


def number_values(text: str) -> set[Decimal]:
    values = set()
    for token in _NUMBER.findall(text):
        normalized = token.rstrip("%")
        # 1,5 and 1.5 are the same magnitude; 1,234 thousands separators are rare in this corpus.
        normalized = normalized.replace(",", ".") if normalized.count(",") == 1 and "." not in normalized else \
            normalized.replace(",", "")
        try:
            values.add(Decimal(normalized).normalize())
        except InvalidOperation:
            continue
    return values


def assess_textual(memory: MemoryStore, claim_id: str, verifiers: Sequence[Verifier], *,
                   evidence_ids: Sequence[str] | None = None, chunk_size: int = 1500) -> dict:
    if len(verifiers) != 2 or len({v.verifier_id for v in verifiers}) != 2:
        raise MemoryStoreError("VERIFIERS_REQUIRED", "textual support needs exactly two distinct verifiers")
    now = instant(memory.clock())
    claim = _claim(memory, claim_id, now)
    if claim["kind"] != "TEXTUAL_SUPPORT":
        raise MemoryStoreError("WRONG_KIND", "an EMPIRICAL_PROOF claim is checked against its run artifact")
    if claim["status"] in ("AMBIGUOUS", "UNVERIFIABLE"):
        raise MemoryStoreError("NOT_VERIFIABLE", f"claim is {claim['status']}; resolve it before verification")
    ids = list(evidence_ids) if evidence_ids is not None else claim["evidence_ids"]
    evidence = memory.evidence(as_of=now, cubes=[claim["cube"]], ids=ids)
    if len(evidence) != len(set(ids)):
        raise MemoryStoreError("EVIDENCE_UNKNOWN", "every evidence id must exist in the claim's cube")
    if not evidence:
        return memory.assess_claim(claim_id, "UNVERIFIABLE", rule=TEXTUAL_RULE, assessed_by="verifiers",
                                   review_state="not_applicable", note="no evidence cited",
                                   verifier_scores={"evidence_ids": []})
    windows = []
    for item in evidence:
        document = memory.document(item["document_id"], as_of=now)
        if document is None or document["content_sha256"] != item["doc_hash"]:
            raise MemoryStoreError("EVIDENCE_STALE", f"document of {item['id']} changed or is no longer current")
        windows.append((item["id"], item["char_start"], item["char_end"], item["quote"]))
        for start, end in chunks(document["text"], size=chunk_size):
            windows.append((item["id"], start, end, document["text"][start:end]))
    scores = {"evidence_ids": [e["id"] for e in evidence], "policy": _policy_ref(verifiers)}
    passed = []
    for verifier in verifiers:
        best = max(((float(verifier.score(text, claim["text"])), eid, start, end)
                    for eid, start, end, text in windows), key=lambda item: item[0])
        if not 0.0 <= best[0] <= 1.0:
            raise MemoryStoreError("VERIFIER_INVALID", f"{verifier.verifier_id} returned a score outside [0, 1]")
        scores[verifier.verifier_id] = {"score": round(best[0], 6), "threshold": verifier.threshold,
                                        "weights_revision": verifier.weights_revision,
                                        "best_window": {"evidence_id": best[1], "start": best[2], "end": best[3]}}
        passed.append(best[0] >= verifier.threshold)
    if all(passed):
        status, review = "SUPPORTED", "not_applicable"
    elif not any(passed):
        status, review = "INCONCLUSIVE", "not_applicable"
    else:
        status, review = "INCONCLUSIVE", "needs_human_review"
    return memory.assess_claim(claim_id, status, rule=TEXTUAL_RULE, assessed_by="verifiers",
                               verifier_scores=scores, review_state=review,
                               note=None if review == "not_applicable" else "verifiers disagree")


def assess_empirical(memory: MemoryStore, claim_id: str, *, root: str | Path = ".") -> dict:
    """SUPPORTED only if the run artifact exists, its sha256 matches and it contains the claim's numbers."""
    now = instant(memory.clock())
    claim = _claim(memory, claim_id, now)
    if claim["kind"] != "EMPIRICAL_PROOF":
        raise MemoryStoreError("WRONG_KIND", "a TEXTUAL_SUPPORT claim is checked by the verifiers")
    ref = claim["run_ref"]
    path = Path(root) / ref["report_path"]
    note = None
    if not path.is_file():
        status, note = "UNVERIFIABLE", "run artifact not found"
    else:
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != ref["report_sha256"]:
            status, note = "UNVERIFIABLE", "run artifact sha256 differs from run_ref"
        else:
            missing = number_values(claim["text"]) - number_values(raw.decode("utf-8", errors="replace"))
            status = "SUPPORTED" if not missing else "UNVERIFIABLE"
            note = None if not missing else f"numbers not in the run artifact: {sorted(map(str, missing))}"
    return memory.assess_claim(claim_id, status, rule=EMPIRICAL_RULE, assessed_by="deterministic",
                               review_state="not_applicable", note=note,
                               verifier_scores={"run_id": ref["run_id"], "report_sha256": ref["report_sha256"]})


def review(memory: MemoryStore, claim_id: str, status: str, *, reviewer: str, note: str) -> dict:
    """Human decision on a claim (the only path to CONTRADICTED); recorded as an immutable event."""
    if type(note) is not str or not note.strip():
        raise MemoryStoreError("NOTE_REQUIRED", "a human review records its reason")
    return memory.assess_claim(claim_id, status, rule="human-review/1", assessed_by="human:" + reviewer,
                               review_state="reviewed", note=note)


def _policy_ref(verifiers) -> dict | str:
    """Which versioned threshold policy produced this decision ("custom" if thresholds differ from it)."""
    from cain.claims.verifiers import policy

    rules = policy()
    if all(rules["thresholds"].get(v.verifier_id) == v.threshold for v in verifiers):
        return {"policy": rules["policy"], "version": rules["version"], "sha256": rules["sha256"]}
    return "custom"


def _claim(memory: MemoryStore, claim_id: str, at: str) -> dict:
    with memory.connection() as db:
        row = db.execute("SELECT cube FROM memory_claims WHERE id=?", (claim_id,)).fetchone()
    if row is None:
        raise MemoryStoreError("CLAIM_UNKNOWN", f"unknown claim {claim_id!r}")
    return memory.claims(as_of=at, cubes=[row["cube"]], ids=[claim_id])[0]

"""Report linter: every number in a report needs provenance, or the report is blocked.

A number is covered when the sentence that contains it cites, with a marker, an object whose text
contains the same magnitude:

* ``[ev:<evidence_id>]``   a literal evidence span recorded in memory (at ``as_of``);
* ``[claim:<claim_id>]``   a claim that is SUPPORTED at ``as_of`` (its text or source span);
* ``[run:<run_id>@<sha256>]`` a SUPPORTED EMPIRICAL_PROOF claim with that run_ref whose artifact
  (read and re-hashed here) contains the number.

Enumerators at the start of a line (``1.``, ``## 2.``) are layout, not claims, and are skipped.
Lexical only: the linter never judges whether a derived or rounded number is right.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from cain.claims.verify import number_values
from cain.memory.store import MemoryStore, instant

MARKER = re.compile(r"\[(ev|claim|run):([^\]\s]+)\]")
_ENUMERATOR = re.compile(r"^(\s*(?:#+\s*)?(?:[-*]\s+)?)\d+(?:\.\d+)*[.)]\s", re.M)
_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
_NUMBER = re.compile(r"(?<![\w.,])[-+]?\d+(?:[.,]\d+)*%?(?![\w])")


def lint_report(memory: MemoryStore, text: str, *, as_of, cubes, cross_cube: bool = False,
                root: str | Path = ".") -> dict:
    at = instant(as_of)
    evidence = {e["id"]: e for e in memory.evidence(as_of=at, cubes=cubes, cross_cube=cross_cube)}
    claims = {c["id"]: c for c in memory.claims(as_of=at, cubes=cubes, cross_cube=cross_cube)}
    runs = {}
    for claim in claims.values():
        if claim["kind"] == "EMPIRICAL_PROOF" and claim["status"] == "SUPPORTED":
            ref = claim["run_ref"]
            runs[f"{ref['run_id']}@{ref['report_sha256']}"] = ref
    body = _ENUMERATOR.sub(lambda m: m.group(1) + " ", text)
    violations, checked, resolved = [], 0, set()
    for sentence in _SENTENCE.split(body):
        markers = MARKER.findall(sentence)
        bare = MARKER.sub(" ", sentence)
        numbers = _NUMBER.findall(bare)
        if not numbers:
            continue
        support_texts, unresolved = [], []
        for kind, ref in markers:
            found = _resolve(kind, ref, evidence, claims, runs, root)
            if found is None:
                unresolved.append(f"{kind}:{ref}")
            else:
                resolved.add(f"{kind}:{ref}")
                support_texts.append(found)
        supported = set().union(*(number_values(t) for t in support_texts)) if support_texts else set()
        for token in numbers:
            checked += 1
            value = number_values(token)
            if not markers:
                violations.append({"number": token, "sentence": sentence.strip()[:300], "code": "NO_PROVENANCE"})
            elif not value or not value <= supported:
                violations.append({"number": token, "sentence": sentence.strip()[:300],
                                   "code": "NOT_IN_CITED_SOURCE", "unresolved_markers": unresolved})
    return {"as_of": at, "status": "blocked" if violations else "publishable", "numbers_checked": checked,
            "markers_resolved": sorted(resolved), "violations": violations}


def _resolve(kind, ref, evidence, claims, runs, root):
    if kind == "ev":
        item = evidence.get(ref)
        return None if item is None else item["quote"]
    if kind == "claim":
        item = claims.get(ref)
        if item is None or item["status"] != "SUPPORTED":
            return None
        return item["text"] + "\n" + item["source_quote"]
    run = runs.get(ref)
    if run is None:
        return None
    path = Path(root) / run["report_path"]
    if not path.is_file():
        return None
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != run["report_sha256"]:
        return None
    return raw.decode("utf-8", errors="replace")

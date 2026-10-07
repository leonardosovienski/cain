"""Collect the canonical artefact hashes into ANCHORS.json for external timestamping (programme item R10).

Hashes prove content integrity; an external anchor (OpenTimestamps, Bitcoin-calendar backed) adds EXISTENCE BY DATE T.
This script only assembles the list; the stamping happens in the `timestamp` workflow (network to the public calendars
is not available from every environment). Records per artefact: ARTIFACT_HASH, ARTIFACT_LABEL, ANCHOR_METHOD,
ANCHOR_TIME (filled by the workflow), PROOF (path of the .ots file).

Usage: python tools/anchor_hashes.py build --out docs/funding/ANCHORS.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Files whose sha256 is anchored (private artefacts; the public Evidence Pack lists the same digests).
ANCHORED_FILES = [
    "pilots/elicitation-a/HANDOFF.md",
    "pilots/elicitation-a/DESIGN.md",
    "pilots/elicitation-a/v2/frozen/FREEZE_MANIFEST.json",
    "pilots/elicitation-a/v2/frozen/DESIGN_V2.md",
    "pilots/elicitation-a/v3/DESIGN_V3.md",
    "pilots/elicitation-a/v3/frozen/FREEZE_MANIFEST.json",
    "pilots/elicitation-a/v3/runs/V3_ANALYSIS.json",
    "pilots/elicitation-a/v3/runs/REVIEW_V3.md",
    "docs/funding/CAIN_CLAIM_LEDGER.md",
    "docs/funding/FUNDING_READINESS_SOURCE_OF_TRUTH.md",
    "STACK_WHEELS.json",
]
# Raw episode files: one commit each in history; anchored by their current digest.
EPISODE_GLOBS = ["pilots/elicitation-a/runs/*/episodes.jsonl", "pilots/elicitation-a/v2/runs/*/episodes.jsonl", "pilots/elicitation-a/v3/runs/*/episodes.jsonl"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out: Path) -> dict:
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"anchors": []}
    known = {a["ARTIFACT_HASH"]: a for a in previous.get("anchors", [])}
    anchors = []
    files = [ROOT / f for f in ANCHORED_FILES] + sorted(p for g in EPISODE_GLOBS for p in ROOT.glob(g))
    for path in files:
        if not path.is_file():
            continue
        digest = sha256_file(path)
        record = known.get(digest) or {
            "ARTIFACT_HASH": digest,
            "ARTIFACT_LABEL": path.relative_to(ROOT).as_posix(),
            "ANCHOR_METHOD": "opentimestamps (sha256 of the file; proof upgrades to a Bitcoin block attestation)",
            "ANCHOR_TIME": None,
            "PROOF": None,
            "first_listed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        anchors.append(record)
    document = {
        "schema": "anchors/1",
        "note": "Content-integrity digests selected for external timestamping (R10). An anchor proves the digest existed at ANCHOR_TIME; it adds nothing to the scientific validity of the content. Records are append-only: a changed file gets a new record, the old one keeps its proof.",
        "anchors": anchors + [a for h, a in known.items() if h not in {x["ARTIFACT_HASH"] for x in anchors}],
    }
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return document


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", type=Path, default=ROOT / "docs/funding/ANCHORS.json")
    args = ap.parse_args(argv)
    document = build(args.out)
    print(f"{len(document['anchors'])} anchors listed in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

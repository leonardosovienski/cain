"""Extract bounded compatibility examples from two explicitly pinned public reports.

This is local documentary curation, not an official domain exporter or new science.
Crypto's required producer integration remains its separate research-export package.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from research_snapshot import canonical, confined, digest, seal, validate

SOURCES = {"stocks": "STOCKS_CURRENT_STATE.md", "brasileirao": "docs/EVIDENCE_REGISTRY.md"}


def extract(domain, root, expected_sha, code_revision, output):
    root, output = Path(root).resolve(strict=True), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError("Use a separate publication destination")
    name = SOURCES[domain]
    source = confined(root, name)
    with source.open("rb") as handle:
        raw = handle.read(100_001)
    if len(raw) > 100_000 or digest(raw) != expected_sha:
        raise ValueError("Report differs from explicitly admitted input")
    text = raw.decode("utf-8")
    records, evidence, offset = [], [], 0
    for line in text.splitlines(keepends=True):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        selected = (
            line.startswith("| Retorno líquido pessoal e operação real |")
            if domain == "stocks"
            else line.startswith("| CLAIM-BR-MARKET-")
        )
        if selected:
            status = cells[1] if domain == "stocks" else cells[2]
            eid = digest(canonical([name, offset, line]))
            evidence.append(
                {
                    "id": eid,
                    "source": name,
                    "availability": "received",
                    "text": line,
                    "sha256": digest(line.encode()),
                    "hash_basis": "received_utf8",
                    "locator": "table-row:" + cells[0],
                    "start": offset,
                    "end": offset + len(line),
                    "offset_unit": "unicode_codepoints",
                }
            )
            record = {
                "source_id": cells[0],
                "kind": "documented_status_row",
                "identity_basis": "document_identity",
                "source_status": status,
                "status_axis": "economic" if domain == "stocks" else "domain_lifecycle",
                "mapping": None,
                "reason": None,
                "event_at": None,
                "recorded_at": None,
                "available_at": None,
                "supersedes": [],
                "evidence_ids": [eid],
            }
            records.append({**record, "revision": digest(canonical(record))})
        offset += len(line)
    if len(records) != (1 if domain == "stocks" else 3) or source.read_bytes() != raw:
        raise ValueError("Unsupported report layout or source changed during extraction")
    package = seal(
        {
            "contract": "ResearchSnapshotV1",
            "profile": "local-evidence/1",
            "extensions": {},
            "origin": {
                "domain": domain,
                "repository": f"https://github.com/leonardosovienski/{domain}-predictor",
                "publisher": "local-document-curator",
                "stream": "compatibility-examples",
                "code_revision": code_revision,
                "exporter_revision": digest(Path(__file__).read_bytes()),
                "inputs": {name: expected_sha},
            },
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "restrictions": {
                "policy": "public-report-local-example/1",
                "read": True,
                "disclose": False,
                "generate": True,
            },
            "coverage": {
                "scope": "Selected documented status rows only",
                "completeness": "partial",
                "included": [name],
                "missing": [],
                "excluded": ["All other domain sources"],
                "limitations": [
                    "Real source bytes, locally curated compatibility examples",
                    "Not a domain-authenticated export or independent experiment",
                    "Literal status preserved; axis selected by documented row semantics",
                    "No historical availability or present validity attestation",
                ],
            },
            "records": records,
            "evidence": evidence,
        }
    )
    validate(package)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(canonical(package))
    return package["publication_id"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=SOURCES, required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--output", required=True)
    print(extract(**vars(parser.parse_args())))

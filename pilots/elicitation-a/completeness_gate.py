"""Analysis completeness gate (programme item H07): DESIGN_REQUIRED_OUTPUTS == ANALYSIS_PRODUCED_OUTPUTS.

A pipeline that verifies execution does not verify semantic completeness: V3's design (§3) required a separate T6
CIRCUMVENTION count and ``analyze_v3.py`` never emitted it; the number had to be recovered later from the AI raw
audit (REVIEW_V3.md). This gate compares the outputs a design pre-declares with the outputs an analysis artefact
actually produced, before any summary may call itself complete.

``REQUIRED_OUTPUTS.json`` (next to the frozen design)::

    {"schema": "required-outputs/1", "design": "DESIGN_V3.md", "analysis_artifact": "runs/V3_ANALYSIS.json",
     "required": [{"id": "reading_1_replication", "path": "readings.1_replication"},
                  {"id": "t6_circumvention_count", "path": "readings.3_t6_circumvention", "note": "DESIGN §3"}]}

``path`` is a dotted path into the analysis JSON; a required output is PRODUCED when the path resolves to a non-null
value. Output: ``ANALYSIS_STATUS = COMPLETE`` (exit 0) or ``INCOMPLETE`` with the missing ids (exit 1), plus a JSON
report (``--out``) that is a layer over the analysis, never a modification of it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def resolve(data, dotted: str):
    node = data
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None
    return node


def gate(required_path: Path, analysis_path: Path | None) -> dict:
    spec = json.loads(required_path.read_text(encoding="utf-8"))
    if spec.get("schema") != "required-outputs/1":
        raise SystemExit(f"{required_path}: unsupported schema {spec.get('schema')!r}")
    analysis_file = analysis_path or (required_path.parent / spec["analysis_artifact"])
    report = {"schema": "analysis-completeness/1", "required_outputs": str(required_path), "analysis_artifact": str(analysis_file),
              "design": spec.get("design"), "produced": [], "missing": []}
    if not analysis_file.is_file():
        report["missing"] = [item["id"] for item in spec["required"]]
        report["status"] = "INCOMPLETE"
        report["reason"] = "analysis artefact missing"
        return report
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    for item in spec["required"]:
        value = resolve(analysis, item["path"])
        (report["produced"] if value is not None else report["missing"]).append(item["id"])
    report["status"] = "COMPLETE" if not report["missing"] else "INCOMPLETE"
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--required", type=Path, required=True, help="REQUIRED_OUTPUTS.json")
    ap.add_argument("--analysis", type=Path, default=None, help="analysis JSON (default: the one named in the spec)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    report = gate(args.required.resolve(), args.analysis.resolve() if args.analysis else None)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ANALYSIS_STATUS = {report['status']}", "missing:" if report["missing"] else "", ", ".join(report["missing"]))
    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())

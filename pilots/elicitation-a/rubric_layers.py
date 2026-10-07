"""Rubric versioning layers (programme item H06): no silent relabeling.

Original labels (``labels.jsonl`` written by the run's own rubric) are never modified. Every later classification is a
new layer with RUBRIC_VERSION, ORIGINAL_LABEL, DERIVED_LABEL, CHANGE_REASON, CHANGE_DATE and RESULT_IMPACT, and
``LABEL_LAYERS.json`` records the sha256 of every original and derived file so a modified original is detected.

Commands::

    rubric_layers.py register --run RUN_DIR --original labels.jsonl --derived rubric_v2/labels.jsonl \\
        --rubric-version 2.1 --reason "..." --date 2026-10-07 --impact "..." [--key episode_id] [--original-field label] [--derived-field label]
    rubric_layers.py check --run RUN_DIR

``register`` writes ``RUN_DIR/layers/<version>_labels.jsonl`` (one row per episode with the six fields, plus the two
raw labels) and appends to ``RUN_DIR/LABEL_LAYERS.json``. ``check`` recomputes every recorded sha256 and fails if an
original or a derived file changed after registration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pick(row: dict, field: str):
    node = row
    for part in field.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def register(run: Path, original: Path, derived: Path, version: str, reason: str, date: str, impact: str, key: str, ofield: str, dfield: str) -> Path:
    original_rows = {pick(r, key): r for r in rows(original)}
    derived_rows = {pick(r, key): r for r in rows(derived)}
    layer_dir = run / "layers"
    layer_dir.mkdir(exist_ok=True)
    out = layer_dir / f"rubric_{version}_labels.jsonl"
    if out.exists():
        raise SystemExit(f"{out} already exists; layers are append-only (choose a new RUBRIC_VERSION)")
    with out.open("w", encoding="utf-8") as stream:
        for episode, orig in original_rows.items():
            der = derived_rows.get(episode)
            stream.write(json.dumps({
                key: episode,
                "RUBRIC_VERSION": version,
                "ORIGINAL_LABEL": pick(orig, ofield),
                "DERIVED_LABEL": pick(der, dfield) if der else None,
                "CHANGE_REASON": reason,
                "CHANGE_DATE": date,
                "RESULT_IMPACT": impact,
                "derived_present": der is not None,
            }, ensure_ascii=False) + "\n")
    registry_path = run / "LABEL_LAYERS.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {"schema": "label-layers/1", "layers": []}
    registry["layers"].append({
        "RUBRIC_VERSION": version, "CHANGE_DATE": date, "CHANGE_REASON": reason, "RESULT_IMPACT": impact,
        "original": {"path": str(original.relative_to(run)), "sha256": sha256_file(original)},
        "derived": {"path": str(derived.relative_to(run)), "sha256": sha256_file(derived)},
        "layer": {"path": str(out.relative_to(run)), "sha256": sha256_file(out)},
        "episodes": len(original_rows), "episodes_without_derived_label": sum(1 for e in original_rows if e not in derived_rows),
    })
    registry_path.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def check(run: Path) -> list[str]:
    registry_path = run / "LABEL_LAYERS.json"
    if not registry_path.exists():
        return [f"{registry_path} missing"]
    problems = []
    for layer in json.loads(registry_path.read_text(encoding="utf-8"))["layers"]:
        for role in ("original", "derived", "layer"):
            path = run / layer[role]["path"]
            if not path.is_file():
                problems.append(f"{layer['RUBRIC_VERSION']}: {role} file missing: {path.name}")
            elif sha256_file(path) != layer[role]["sha256"]:
                problems.append(f"{layer['RUBRIC_VERSION']}: {role} file changed after registration: {path.name}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register")
    reg.add_argument("--run", type=Path, required=True)
    reg.add_argument("--original", type=Path, required=True, help="relative to --run")
    reg.add_argument("--derived", type=Path, required=True, help="relative to --run")
    reg.add_argument("--rubric-version", required=True)
    reg.add_argument("--reason", required=True)
    reg.add_argument("--date", required=True)
    reg.add_argument("--impact", required=True)
    reg.add_argument("--key", default="episode_id")
    reg.add_argument("--original-field", default="status")
    reg.add_argument("--derived-field", default="label")
    chk = sub.add_parser("check")
    chk.add_argument("--run", type=Path, required=True)
    args = ap.parse_args(argv)
    run = args.run.resolve()
    if args.command == "register":
        out = register(run, run / args.original, run / args.derived, args.rubric_version, args.reason, args.date, args.impact, args.key, args.original_field, args.derived_field)
        print(f"layer written: {out}")
        return 0
    problems = check(run)
    if problems:
        print("LABEL_LAYERS = FAIL\n  " + "\n  ".join(problems))
        return 1
    print("LABEL_LAYERS = PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

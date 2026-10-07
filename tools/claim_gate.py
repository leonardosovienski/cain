"""Claim gate: every material number or high-risk phrase in a public-facing document must be backed by a registered claim.

Programme item R04 (2026-10-07). A claim index (JSON) lists the documents under the gate and the claims that license
their material tokens. A material token is a ratio (``58/58``), a percentage (``+44%``), or an integer of two or more
digits that is not a date, time, year, SHA, version, size column, list marker or other pattern the index declares
irrelevant. The gate fails when a token appears without a claim that carries it, when a claim marked not public-safe
has one of its tokens in a document, when a forbidden phrase appears, or when a claim row lacks scope, date, source or
the current/historical flag. It never edits documents.

Index schema (``claim-index/1``)::

    {
      "schema": "claim-index/1",
      "documents": [{"path": "README.md", "until": "# optional heading that ends the gated region"}],
      "ignore_patterns": ["regex", ...],           # tokens matching any pattern are not material
      "ignore_table_columns": ["regex on header cell", ...],
      "forbidden_phrases": ["regex", ...],          # must not appear in any gated document
      "claims": [{"id": "C01", "text": "...", "tokens": ["58/58"], "scope": "...", "source": "...",
                  "date": "YYYY-MM-DD", "status": "CONFIRMED|PARTIAL|HISTORICAL|PROPOSED|NOT_REPRODUCED|CONFLICT|RETRACTED|FALSE",
                  "current_or_historical": "CURRENT|HISTORICAL", "public_safe": true}]
    }

Usage: ``python claim_gate.py check --index claims/CLAIM_INDEX.json [--root DIR]``; exit 1 on any finding.
Limits: spelled-out numbers ("fifteen") and one-digit counts are not tokenised; add them to a claim's ``phrases``
to have the gate require the claim, or to ``forbidden_phrases`` to ban them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STATUSES = {"CONFIRMED", "PARTIAL", "HISTORICAL", "PROPOSED", "NOT_REPRODUCED", "CONFLICT", "RETRACTED", "FALSE"}
TOKEN = re.compile(
    r"(?P<ratio>\b\d+\s*/\s*\d+\b)"
    r"|(?P<percent>[+\-−]?\d+(?:[.,]\d+)?\s?%)"
    r"|(?P<integer>(?<![\w.\-/])\d{2,}(?![\w.\-/%]))"
)
DEFAULT_IGNORES = [
    r"^20\d\d$",  # years
    r"^\d{4}-\d{2}-\d{2}",  # ISO dates (also with time)
    r"^\d{2}:\d{2}",  # times
    r"^[0-9a-f]{7,64}$",  # hashes and SHAs
    r"^\d+\.\d+(\.\d+)?(rc\d+)?$",  # versions
    r"^\d{4,}$",  # ids, sizes and run numbers of four digits or more are never claims by themselves
]


class GateError(RuntimeError):
    pass


def load_index(path: Path) -> dict:
    index = json.loads(path.read_text(encoding="utf-8"))
    if index.get("schema") != "claim-index/1":
        raise GateError(f"{path}: unsupported schema {index.get('schema')!r}")
    seen: set[str] = set()
    for claim in index.get("claims", []):
        for key in ("id", "text", "scope", "source", "date", "status", "current_or_historical"):
            if not str(claim.get(key, "")).strip():
                raise GateError(f"{path}: claim {claim.get('id')!r} lacks {key}")
        if claim["status"] not in STATUSES:
            raise GateError(f"{path}: claim {claim['id']}: status {claim['status']!r} not in {sorted(STATUSES)}")
        if claim["current_or_historical"] not in ("CURRENT", "HISTORICAL"):
            raise GateError(f"{path}: claim {claim['id']}: current_or_historical must be CURRENT or HISTORICAL")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", claim["date"]):
            raise GateError(f"{path}: claim {claim['id']}: date must be YYYY-MM-DD")
        if claim["id"] in seen:
            raise GateError(f"{path}: duplicate claim id {claim['id']}")
        seen.add(claim["id"])
        claim.setdefault("tokens", [])
        claim.setdefault("phrases", [])
        claim.setdefault("public_safe", True)
    index.setdefault("ignore_patterns", [])
    index.setdefault("ignore_table_columns", [])
    index.setdefault("forbidden_phrases", [])
    return index


def normalise(token: str) -> str:
    return re.sub(r"\s+", "", token).replace("−", "-").replace(",", ".")


def _table_columns_to_skip(header_line: str, patterns: list[re.Pattern[str]]) -> set[int]:
    cells = [c.strip() for c in header_line.strip().strip("|").split("|")]
    return {i for i, cell in enumerate(cells) if any(p.search(cell) for p in patterns)}


def material_tokens(text: str, ignores: list[re.Pattern[str]], column_patterns: list[re.Pattern[str]]) -> list[tuple[int, str]]:
    """Return (line_number, normalised_token) for every material token in a markdown text."""
    found: list[tuple[int, str]] = []
    lines = text.splitlines()
    skip_columns: set[int] = set()
    in_table = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("|"):
            if not in_table:
                in_table = True
                skip_columns = _table_columns_to_skip(stripped, column_patterns)
                continue  # header row carries no claims
            cells = stripped.strip("|").split("|")
            if all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in cells):
                continue  # separator row
            scan = " | ".join(c for i, c in enumerate(cells) if i not in skip_columns)
        else:
            in_table = False
            scan = re.sub(r"^\s*\d+\.\s", "", line)  # ordered-list marker
            scan = re.sub(r"^#+\s.*", "", scan) if re.match(r"^#+\s+\d+\s+(seconds|minutes|hours)\b", scan) else scan
        scan = re.sub(r"`[^`]*`", " ", scan)  # inline code is identifiers, not claims
        scan = re.sub(r"\]\([^)]*\)", "]()", scan)  # link targets
        for match in TOKEN.finditer(scan):
            raw = match.group(0)
            token = normalise(raw)
            if any(p.search(token) for p in ignores):
                continue
            # a bare integer that is part of a date range such as "2026-07-26 → 28" or "11 → 17"
            if match.lastgroup == "integer":
                before = scan[max(0, match.start() - 4) : match.start()]
                after = scan[match.end() : match.end() + 3]
                if "→" in before or "→" in after or "–" in before:
                    continue
            found.append((number, token))
    return found


def check(index_path: Path, root: Path) -> list[str]:
    index = load_index(index_path)
    ignores = [re.compile(p) for p in DEFAULT_IGNORES + index["ignore_patterns"]]
    columns = [re.compile(p, re.I) for p in index["ignore_table_columns"]]
    forbidden = [re.compile(p, re.I) for p in index["forbidden_phrases"]]
    covered: dict[str, list[str]] = {}
    unsafe_tokens: dict[str, str] = {}
    for claim in index["claims"]:
        for token in claim["tokens"]:
            key = normalise(token)
            if claim["public_safe"]:
                covered.setdefault(key, []).append(claim["id"])
            else:
                unsafe_tokens[key] = claim["id"]
    problems: list[str] = []
    required_phrases = [(c["id"], re.compile(p, re.I)) for c in index["claims"] for p in c["phrases"]]
    for document in index["documents"]:
        path = root / document["path"]
        if not path.is_file():
            problems.append(f"{document['path']}: gated document missing")
            continue
        text = path.read_text(encoding="utf-8")
        if document.get("until"):
            cut = text.find(document["until"])
            if cut == -1:
                problems.append(f"{document['path']}: 'until' marker {document['until']!r} not found")
            else:
                text = text[:cut]
        for number, token in material_tokens(text, ignores, columns):
            if token in unsafe_tokens:
                problems.append(f"{document['path']}:{number}: token {token} belongs to claim {unsafe_tokens[token]}, which is not public-safe")
            elif token not in covered:
                problems.append(f"{document['path']}:{number}: material token {token} has no registered claim")
        for pattern in forbidden:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"{document['path']}:{line}: forbidden phrase {match.group(0)!r}")
        for claim_id, pattern in required_phrases:
            if pattern.search(text) and not any(c["id"] == claim_id and c["public_safe"] for c in index["claims"]):
                line = text.count("\n", 0, pattern.search(text).start()) + 1  # type: ignore[union-attr]
                problems.append(f"{document['path']}:{line}: phrase of claim {claim_id} appears but the claim is not public-safe")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    chk = sub.add_parser("check")
    chk.add_argument("--index", type=Path, required=True)
    chk.add_argument("--root", type=Path, default=None, help="document root (default: the index file's repository root = its parent's parent)")
    args = parser.parse_args(argv)
    root = (args.root or args.index.resolve().parent.parent).resolve()
    try:
        problems = check(args.index.resolve(), root)
    except GateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if problems:
        print("CLAIM_GATE = FAIL")
        for problem in problems:
            print("  " + problem)
        return 1
    print("CLAIM_GATE = PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

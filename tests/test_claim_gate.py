"""Claim gate (programme item R04): the ledger is complete and the public-facing text carries no unregistered number.

* every row of CAIN_CLAIM_LEDGER.md has an id, a status from the closed set, a SHA/date cell, a public flag and a
  qualifier cell (the qualifier may be "—" only when the status is CONFIRMED);
* the current section of README.md passes tools/claim_gate.py with docs/funding/CLAIM_INDEX.json;
* the gate itself flags unregistered numbers, forbidden phrases and tokens of non-public-safe claims.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("claim_gate", ROOT / "tools" / "claim_gate.py")
claim_gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(claim_gate)

STATUSES = {"CONFIRMED", "PARTIAL", "HISTORICAL", "PROPOSED", "NOT_REPRODUCED", "CONFLICT", "RETRACTED", "FALSE"}


def _ledger_rows() -> list[list[str]]:
    rows = []
    for line in (ROOT / "docs/funding/CAIN_CLAIM_LEDGER.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"^\| C\d\d \|", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def test_every_ledger_row_is_complete():
    rows = _ledger_rows()
    assert len(rows) >= 18
    for row in rows:
        claim_id, text, evidence, sha_date, status, public, grant_safe, qualifier = row[:8]
        assert re.fullmatch(r"C\d\d", claim_id)
        assert text and evidence and sha_date and public and grant_safe, claim_id
        assert any(status.strip("*").startswith(s) for s in STATUSES), (claim_id, status)
        if "qualifier" in grant_safe.lower() or grant_safe.upper().startswith("PARTIAL"):
            assert qualifier not in ("—", "-", ""), (claim_id, "grant-safe only with a qualifier, but no qualifier given")


def test_readme_current_section_passes_the_claim_gate():
    problems = claim_gate.check(ROOT / "docs/funding/CLAIM_INDEX.json", ROOT)
    assert problems == []


def test_gate_flags_unregistered_numbers_forbidden_phrases_and_unsafe_tokens(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    index = {
        "schema": "claim-index/1",
        "documents": [{"path": "PAGE.md"}],
        "forbidden_phrases": ["about 1,?500"],
        "claims": [
            {"id": "X01", "text": "ok", "tokens": ["58/58"], "scope": "s", "source": "s", "date": "2026-10-07", "status": "CONFIRMED", "current_or_historical": "HISTORICAL", "public_safe": True},
            {"id": "X02", "text": "never", "tokens": ["14/14"], "scope": "s", "source": "s", "date": "2026-10-07", "status": "HISTORICAL", "current_or_historical": "HISTORICAL", "public_safe": False},
        ],
    }
    (tmp_path / "docs" / "CLAIM_INDEX.json").write_text(json.dumps(index), encoding="utf-8")
    (tmp_path / "PAGE.md").write_text(
        "Joint test 58/58 on 2026-09-28 (sha `abcdef1234`), version 0.4.13rc15.\n"
        "Sandbox contained 14/14 cases and about 1,500 tests passed; 1463 tests at a commit.\n"
        "| # | Size (bytes) | Count |\n|---|---|---|\n| 10 | 27796 | 81 |\n",
        encoding="utf-8",
    )
    problems = claim_gate.check(tmp_path / "docs" / "CLAIM_INDEX.json", tmp_path)
    joined = "\n".join(problems)
    assert "token 14/14 belongs to claim X02" in joined
    assert "forbidden phrase 'about 1,500'" in joined
    assert "material token 81 has no registered claim" in joined
    assert "27796" not in joined  # size column ignored by header pattern
    assert "1463" not in joined  # four-digit counts are not claims by themselves
    assert "58/58" not in joined
    assert "2026" not in joined and "abcdef" not in joined and "0.4.13" not in joined

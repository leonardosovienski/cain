"""Canonical documents declare their mode and the living chain does not go stale (programme R02, 2026-10-07).

Protected behaviour:
* every canonical document declares exactly one mode: ``MODE: SNAPSHOT_IMMUTABLE`` with AS_OF_DATE, AS_OF_SHA and
  SUPERSEDED_BY, or ``MODE: CURRENT_LIVING_STATE``;
* the living Source of Truth answers the seven canonical questions in one table and its DECLARED_VERSION is the
  packaged version;
* living documents carry no future-tense prediction about CI (the class of statement that was found stale:
  "CI will fail on the next run" after it had already failed).
"""
from __future__ import annotations

from pathlib import Path
import re

from cain import __version__

ROOT = Path(__file__).resolve().parents[1]

LIVING = [
    "docs/funding/FUNDING_READINESS_SOURCE_OF_TRUTH.md",
    "docs/funding/FUNDING_READINESS_RISK_LEDGER.md",
    "docs/funding/CAIN_CLAIM_LEDGER.md",
]
SNAPSHOTS = [
    "docs/ESTADO_2026-09-30.md",
    "docs/funding/SOURCE_OF_TRUTH_LAYERS_2026-10-07.md",
    "ESTADO_DO_PROJETO.md",
    "CONTINUIDADE.md",
    "pilots/elicitation-a/HANDOFF.md",
]
STALE_PREDICTIONS = [
    r"will fail on (the )?next (push|run)",
    r"expected to fail on the next run",
    r"vai falhar no próximo",
]
QUESTIONS = [
    "LAST_VERIFIED_AT_SHA",
    "DECLARED_VERSION",
    "PUBLISHED_VERSION",
    "QUALIFIED_VERSION",
    "CI_STATE",
    "SCIENTIFIC_STATE",
    "OPEN_RISKS",
    "CLAIM_GATE_ACTIVE",
    "NEW_RQ1_LINE",
    "SUPPLY_CHAIN_HEALTHY",
]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _declarations(text: str) -> list[str]:
    return re.findall(r"^>? ?MODE: (SNAPSHOT_IMMUTABLE|CURRENT_LIVING_STATE)", text, flags=re.M)


def test_living_documents_declare_the_living_mode_only():
    for relative in LIVING:
        assert _declarations(_text(relative)) == ["CURRENT_LIVING_STATE"], relative


def test_snapshot_documents_declare_date_sha_and_successor():
    for relative in SNAPSHOTS:
        text = _text(relative)
        assert _declarations(text) == ["SNAPSHOT_IMMUTABLE"], relative
        match = re.search(
            r"MODE: SNAPSHOT_IMMUTABLE · AS_OF_DATE: (\d{4}-\d{2}-\d{2}) · AS_OF_SHA: ([0-9a-f]{7,40}) · SUPERSEDED_BY: (.+)",
            text,
        )
        assert match, relative
        assert match.group(3).strip()


def test_source_of_truth_answers_the_canonical_questions_with_the_packaged_version():
    text = _text(LIVING[0])
    section = text.split("## 0. Canonical answers", 1)[1].split("\n## ", 1)[0]
    for question in QUESTIONS:
        assert f"| {question} |" in section, question
    declared = re.search(r"\| DECLARED_VERSION \| `([^`]+)`", section)
    assert declared and declared.group(1) == __version__


def test_living_documents_make_no_future_tense_ci_predictions():
    for relative in LIVING:
        text = _text(relative)
        for pattern in STALE_PREDICTIONS:
            # A historical sentence may keep the old wording only next to the statement that it materialised.
            for found in re.finditer(pattern, text, flags=re.I):
                context = text[max(0, found.start() - 200) : found.end() + 200]
                assert "materialised" in context or "predicted" in context, (relative, found.group(0))

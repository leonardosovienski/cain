"""A hypothesis ID qualified with its own domain ("crypto:H9", C18) names the same closed hypothesis as "H9".

Practical validation of 2026-09-28 (integration-crypto): ``cain findings check --hypothesis-id crypto:H9`` answered
"not equivalent" for the closed H9, because the scientific state is ingested with bare IDs while the Etapa B uses
domain-qualified ones everywhere else.
"""

from hashlib import sha256
import json

import pytest

from cain.findings.archive import FindingsArchive
from cain.findings.ingest import ingest_scientific_state
from cain.memory.store import MemoryStore

STATE = {"schema_version": "crypto-scientific-state/1",
         "hypotheses": {"H7": "REGISTERED_NOT_ACTIVATED", "H9": "CLOSED_INSUFFICIENT_SAMPLE"},
         "hypothesis_trials": {"H9": "h9-oi-volume-ratio-hmm-v1"}, "frozen_families": ["funding_oi_hmm_v3"]}


@pytest.fixture
def archive(tmp_path):
    archive = FindingsArchive(MemoryStore(tmp_path / "memory.db"))
    raw = json.dumps(STATE).encode()
    ingest_scientific_state(archive, "crypto", raw, {"repo": "cripto-predictor", "commit": "0" * 40,
                                                     "path": "charters/scientific_state.json",
                                                     "sha256": sha256(raw).hexdigest()})
    return archive


@pytest.mark.parametrize("given", ["H9", "crypto:H9"])
def test_bare_and_qualified_ids_of_the_domain_match_the_closed_hypothesis(archive, given):
    found = archive.equivalent_closed("crypto", "zzz", as_of=archive.memory.now(), identity={"hypothesis_id": given})
    assert [m["finding_id"] for m in found] == ["crypto:hypothesis:H9"]


@pytest.mark.parametrize("given", ["stocks:H9", "brasileirao:H9", "crypto:H7", "H7"])
def test_another_domain_prefix_or_an_open_hypothesis_never_matches(archive, given):
    assert archive.equivalent_closed("crypto", "zzz", as_of=archive.memory.now(),
                                     identity={"hypothesis_id": given}) == []

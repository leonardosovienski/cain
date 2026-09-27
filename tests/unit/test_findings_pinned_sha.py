"""The crypto registry is read only at a full commit SHA, never at a moving ref (integration-crypto)."""

import pytest

from cain.cli import main


@pytest.mark.parametrize("commit", ["origin/main", "HEAD", "341d270", "341d270e4d709150c581c3cd93f4518d483009eb^"])
def test_crypto_ingestion_refuses_a_moving_or_short_ref(tmp_path, capsys, commit):
    code = main(["findings", "--db", str(tmp_path / "m.db"), "ingest-state", "--domain", "crypto",
                 "--repo", str(tmp_path), "--commit", commit, "--path", "charters/scientific_state.json"])
    assert code == 1
    assert "full 40-hex commit SHA" in capsys.readouterr().err
    assert not (tmp_path / "m.db").exists()

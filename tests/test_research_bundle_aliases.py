"""Bundle approve/ingest refuse Windows name aliases before opening anything.

Protected behaviour: a manifest path whose component ends with a dot or a space is
rejected by name on every platform, so a bundle is never admitted under a name NTFS
would silently map onto another file.
"""
import pytest

from test_research_bundle import setup  # noqa: F401  (pytest fixture)


@pytest.mark.parametrize("relative", ["one/bundle.json.", "one/bundle.json ", "one./bundle.json"])
def test_alias_names_are_refused_for_approve_and_ingest(setup, relative):  # noqa: F811
    store, scope, _, _, _, _ = setup
    with pytest.raises(ValueError, match="name alias"):
        store.approve(relative, scope)
    with pytest.raises(ValueError, match="name alias"):
        store.ingest(relative, scope)
    assert store.receipts(scope)[0]["status"] == "rejected"
    assert store.ingest("one/bundle.json", scope)["status"] == "admitted"

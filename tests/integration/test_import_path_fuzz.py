"""Import path confinement: hostile relative paths never open anything outside import_root.

Protected behaviour: ``ResearchService.ingest(relative, scope)`` rejects UNC and
drive-qualified names, parent references, empty or dot components, null bytes,
directories and names that only match after Unicode normalisation, and it does so
without opening any file other than the policy. A well-formed NFC name still imports.
"""
from pathlib import Path
import unicodedata

import pytest
from research_snapshot import canonical

import test_research_l0 as cases

setup = cases.setup

HOSTILE = {
    "unc-backslash": "\\\\server\\share\\pub.json",
    "unc-forward": "//server/share/pub.json",
    "unc-long-prefix": "\\\\?\\C:\\pub.json",
    "drive-relative": "C:pub.json",
    "drive-absolute-forward": "C:/pub.json",
    "parent-inside-root": "inbox/../pub.json",
    "dot-component": "./pub.json",
    "empty": "",
    "trailing-slash": "pub.json/",
    "double-slash": "a//pub.json",
    "null-byte": "pub\x00.json",
    "directory": "subdir",
    "windows-trailing-dot": "pub.json.",
    "windows-trailing-space": "pub.json ",
    "windows-trailing-dot-directory": "subdir./pub.json",
    "overlong": "p" * 300 + ".json",
    "nfd-of-nfc-name": unicodedata.normalize("NFD", "relatório.json"),
}


@pytest.fixture
def guarded_root(setup, monkeypatch):
    service, scope, _, policy, _ = setup
    root = Path(policy["import_root"])
    (root / "subdir").mkdir()
    (root / "pub.json").write_bytes(canonical(cases.publication()))
    (root / unicodedata.normalize("NFC", "relatório.json")).write_bytes(canonical(cases.publication(("N",))))
    opened = []
    original = Path.open

    def guarded(path, *args, **kwargs):
        opened.append(Path(path).name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    return service, scope, root, opened


@pytest.mark.parametrize("relative", list(HOSTILE.values()), ids=list(HOSTILE))
def test_hostile_relative_paths_are_rejected_before_any_read(guarded_root, relative):
    service, scope, _, opened = guarded_root
    with pytest.raises(ValueError):
        service.ingest(relative, scope)
    assert set(opened) <= {"policy.json"}, opened
    assert not any(r["status"] == "admitted" for r in service.receipts(scope))


def test_nfc_name_imports_and_nfd_request_does_not_alias_it(guarded_root):
    service, scope, root, opened = guarded_root
    nfc = unicodedata.normalize("NFC", "relatório.json")
    nfd = unicodedata.normalize("NFD", "relatório.json")
    assert nfc != nfd
    assert service.ingest(nfc, scope)["status"] == "admitted"
    assert nfc in opened
    if (root / nfd).exists():  # filesystems that normalise names (macOS) alias the same bytes
        pytest.skip("filesystem normalises Unicode names; aliasing is not an escape here")
    with pytest.raises(ValueError):
        service.ingest(nfd, scope)
    assert service.query(scope, source_id="N")["total_record_revisions"] == 1


@pytest.mark.parametrize("relative", ["pub.json.", "pub.json ", "pub.json. ", "subdir./pub.json", "a\\b./c"])
def test_windows_name_aliases_are_refused_on_every_platform_before_resolution(guarded_root, relative, monkeypatch):
    """NTFS maps "pub.json." onto "pub.json"; the request must fail by name, not by lookup."""
    service, scope, _, opened = guarded_root
    resolved = []
    monkeypatch.setattr(Path, "resolve", lambda self, *a, **k: resolved.append(self) or self)
    with pytest.raises(ValueError, match="Import rejected"):  # ingest wraps the cause in its receipt
        service.ingest(relative, scope)
    assert resolved == [] and set(opened) <= {"policy.json"}
    assert service.receipts(scope)[0]["status"] == "rejected"

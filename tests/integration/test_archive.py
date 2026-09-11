import sqlite3

import pytest
from research_snapshot import canonical

from cain.archive import backup, restore
from cain.research import ResearchService
from cain.workspace import WorkspaceStore


def test_backup_restores_documents_ids_and_rejects_tampering(tmp_path):
    live = tmp_path / "live"
    store = WorkspaceStore(live / "workspace.db")
    project = store.create_project("leo", "Test")["id"]
    original = store.add_document("leo", project, "Fonte.md", "Evidência\nEvidence")
    policy = tmp_path / "policy.json"
    policy.write_bytes(canonical(dict(version=1, import_root=str(tmp_path), grants=[])))
    ResearchService(live / "research.db", policy)
    copy = tmp_path / "backup"
    assert backup(store.path, live / "research.db", policy, copy)["files"] == 4
    # A later live mutation cannot change the backup's catalog or documents.
    store.add_document("leo", project, "Later.md", "Later")
    recovered = tmp_path / "restored"
    assert restore(copy, recovered)["status"] == "restored"
    after = WorkspaceStore(recovered / "workspace.db")
    assert after.documents("leo", project)[0]["id"] == original["id"]
    assert list(after.document_corpus("leo", project).values()) == ["Evidência\nEvidence"]
    with pytest.raises(FileExistsError):
        restore(copy, recovered)
    (copy / "knowledge" / project / (original["id"] + ".md")).write_text("tampered")
    with pytest.raises(ValueError, match="hash"):
        restore(copy, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
    with sqlite3.connect(store.path) as db:
        assert db.execute("select count(*) from project_documents").fetchone()[0] == 2


def test_missing_document_never_completes_backup(tmp_path):
    store = WorkspaceStore(tmp_path / "live" / "workspace.db")
    project = store.create_project("leo", "Test")["id"]
    document = store.add_document("leo", project, "Source.md", "data")
    from pathlib import Path
    Path(document["path"]).unlink()
    with pytest.raises(ValueError):
        backup(store.path, "unused", "unused", tmp_path / "incomplete")
    assert not (tmp_path / "incomplete" / "manifest.json").exists()

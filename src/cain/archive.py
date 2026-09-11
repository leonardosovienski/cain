"""Local administrator backup of workspace, documents, research and policy.

Each SQLite snapshot is consistent; there is no cross-database transaction claim.
Destinations are new directories; failed operations remain explicitly incomplete.
"""
from hashlib import sha256
from pathlib import Path
import sqlite3

from research_snapshot import canonical, confined, loads

from cain.workspace import WorkspaceStore


def _snapshot(source, destination):
    source = Path(source).resolve(strict=True)
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Database integrity check failed")


def _documents(database, source_root, destination):
    # Use the snapshot's catalog, not a subsequently modified live catalog.
    store = object.__new__(WorkspaceStore)
    store.documents_root = Path(source_root).absolute()
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM project_documents").fetchall()
    for row in rows:
        _, text = store._document_snapshot(row, row["project_id"])
        path = destination / "knowledge" / row["project_id"] / (row["id"] + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(text.encode("utf-8"))


def backup(workspace, research, policy, destination):
    destination = Path(destination).absolute()
    destination.mkdir(parents=True, exist_ok=False)
    _snapshot(workspace, destination / "workspace.db")
    _documents(destination / "workspace.db", Path(workspace).resolve().parent / "knowledge",
               destination)
    _snapshot(research, destination / "research.db")
    policy_raw = Path(policy).read_bytes()
    # Validate configuration without creating or modifying a database.
    from cain.research import ResearchService
    checker = object.__new__(ResearchService)
    checker.policy_path = Path(policy)
    checker.policy()
    (destination / "policy.json").write_bytes(policy_raw)
    files = {path.relative_to(destination).as_posix(): sha256(path.read_bytes()).hexdigest()
             for path in destination.rglob("*") if path.is_file()}
    manifest = dict(version=1, files=files,
                    consistency="independent SQLite snapshots plus hash-verified immutable documents")
    (destination / "manifest.json").write_bytes(canonical(manifest))
    return dict(status="backed_up", files=len(files), destination=str(destination),
                consistency=manifest["consistency"])


def restore(source, destination):
    source = Path(source).resolve(strict=True)
    manifest = loads((source / "manifest.json").read_bytes())
    if (set(manifest) != {"version", "files", "consistency"} or manifest["version"] != 1
            or type(manifest["files"]) is not dict):
        raise ValueError("Invalid backup manifest")
    files = manifest["files"]
    if not {"workspace.db", "research.db", "policy.json"} <= set(files):
        raise ValueError("Incomplete backup")
    # Admit only expected objects, verify all before creating the destination.
    for name, expected in files.items():
        if name not in {"workspace.db", "research.db", "policy.json"}:
            parts = name.split("/")
            from uuid import UUID
            if (len(parts) != 3 or parts[0] != "knowledge"
                    or str(UUID(parts[1])) != parts[1]
                    or not parts[2].endswith(".md")
                    or str(UUID(parts[2][:-3])) != parts[2][:-3]):
                raise ValueError("Unexpected backup object")
        if sha256(confined(source, name).read_bytes()).hexdigest() != expected:
            raise ValueError("Backup hash mismatch")
    destination = Path(destination).absolute()
    destination.mkdir(parents=True, exist_ok=False)
    for name, expected in files.items():
        raw = confined(source, name).read_bytes()
        if sha256(raw).hexdigest() != expected:
            raise ValueError("Backup changed during restore")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)
    for name in ("workspace.db", "research.db"):
        with sqlite3.connect(destination / name) as db:
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Restored database is corrupt")
    store = WorkspaceStore(destination / "workspace.db")
    with store.connection() as db:
        for row in db.execute("SELECT * FROM project_documents").fetchall():
            record, _ = store._document_snapshot(row, row["project_id"])
            db.execute("UPDATE project_documents SET path=? WHERE id=?",
                       (record["path"], row["id"]))
    (destination / "RESTORE_COMPLETE.json").write_bytes(canonical(
        dict(version=1, source=str(source), verified_files=len(files))))
    return dict(status="restored", destination=str(destination),
                activation="manual; review restored policy and configure paths before use")


def register(sub):
    parser = sub.add_parser("archive", help="Administrator backup/restore including documents")
    commands = parser.add_subparsers(dest="archive_command", required=True)
    make = commands.add_parser("backup")
    for name in ("workspace", "research", "policy"):
        make.add_argument("--" + name, type=Path, required=True)
    make.add_argument("destination", type=Path)
    recover = commands.add_parser("restore")
    recover.add_argument("source", type=Path)
    recover.add_argument("destination", type=Path)


def execute(args):
    if args.archive_command == "backup":
        return backup(args.workspace, args.research, args.policy, args.destination)
    return restore(args.source, args.destination)

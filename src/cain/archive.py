"""Local administrator backup of workspace, documents, research and policy.

Each SQLite snapshot is consistent; there is no cross-database transaction claim.
Destinations are new directories; failed operations remain explicitly incomplete.
"""
import io
import os
from contextlib import closing
from pathlib import Path
import sqlite3

from research_snapshot import canonical
from research_bundle import loads
from research_bundle.files import no_links, safe_mkdirs, safe_open, transfer

from cain.workspace import WorkspaceStore


def _read(root, name, limit=2_000_000):
    with safe_open(root, name) as source:
        buffer = io.BytesIO()
        transfer(source, buffer, limit=limit)
        return buffer.getvalue()


def _hash(root, name, expected=None):
    with safe_open(root, name) as source:
        return transfer(source, limit=os.fstat(source.fileno()).st_size,
                        expected_sha=expected)[0]


def _snapshot(source, destination):
    source = no_links(source)
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Database integrity check failed")


def _documents(database, source_root, destination):
    # Use the snapshot's catalog, not a subsequently modified live catalog.
    store = object.__new__(WorkspaceStore)
    store.documents_root = Path(source_root).absolute()
    with closing(sqlite3.connect(database)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM project_documents").fetchall()
    for row in rows:
        _, text = store._document_snapshot(row, row["project_id"])
        path = destination / "knowledge" / row["project_id"] / (row["id"] + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(text.encode("utf-8"))


def backup(workspace, research, policy, destination, objects=None):
    destination = Path(destination).absolute()
    safe_mkdirs(destination.parent)
    destination.mkdir(parents=True, exist_ok=False)
    _snapshot(workspace, destination / "workspace.db")
    _documents(destination / "workspace.db", Path(workspace).resolve().parent / "knowledge",
               destination)
    _snapshot(research, destination / "research.db")
    policy_raw = _read(Path(policy).absolute().parent, Path(policy).name)
    # Validate configuration without creating or modifying a database.
    from cain.research import ResearchService
    checker = object.__new__(ResearchService)
    checker.policy_path = Path(policy)
    checker.policy()
    (destination / "policy.json").write_bytes(policy_raw)
    from cain.research.bundle_backup import copy_objects
    received = copy_objects(destination / "research.db", objects or
                            os.getenv("CAIN_RESEARCH_OBJECTS") or
                            Path(research).absolute().parent / "research-objects", destination)
    files = {path.relative_to(destination).as_posix(): _hash(destination, path.relative_to(destination).as_posix())
             for path in destination.rglob("*") if path.is_file()}
    manifest = dict(version=2, files=files, objects=received,
                    consistency="independent SQLite snapshots plus hash-verified immutable documents")
    (destination / "manifest.json").write_bytes(canonical(manifest))
    return dict(status="backed_up", files=len(files), destination=str(destination),
                consistency=manifest["consistency"])


def restore(source, destination):
    source = no_links(source)
    manifest = loads(_read(source, "manifest.json"))
    version = manifest.get("version")
    fields = {"version", "files", "consistency"} | ({"objects"} if version == 2 else set())
    if (set(manifest) != fields or type(version) is not int or version not in (1, 2)
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
            if version == 2 and name.startswith("research-objects/"):
                from cain.research.objects import Objects
                if len(parts) != 4 or name != "research-objects/" + Objects.relative(parts[-1]):
                    raise ValueError("Unexpected backup CAS object")
            elif (len(parts) != 3 or parts[0] != "knowledge"
                    or str(UUID(parts[1])) != parts[1]
                    or not parts[2].endswith(".md")
                    or str(UUID(parts[2][:-3])) != parts[2][:-3]):
                raise ValueError("Unexpected backup object")
        _hash(source, name, expected)
    from cain.research.bundle_backup import verify_objects
    received = verify_objects(source / "research.db", source / "research-objects")
    if version == 1 and received:
        raise ValueError("Legacy backup cannot contain received bundles")
    if version == 2:
        from cain.research.objects import Objects
        if manifest["objects"] != received or any(
                "research-objects/" + Objects.relative(d) not in files for d in received):
            raise ValueError("Incomplete backup objects")
    from cain.research import ResearchService
    checker = object.__new__(ResearchService)
    checker.policy_path = source / "policy.json"
    checker.policy()
    destination = Path(destination).absolute()
    safe_mkdirs(destination.parent)
    destination.mkdir(parents=True, exist_ok=False)
    for name, expected in files.items():
        target = destination / name
        safe_mkdirs(target.parent)
        with safe_open(source, name) as original:
            with target.open("xb") as handle:
                transfer(original, handle, limit=os.fstat(original.fileno()).st_size,
                         expected_sha=expected)
                handle.flush()
                os.fsync(handle.fileno())
    for name in ("workspace.db", "research.db"):
        with closing(sqlite3.connect(destination / name)) as db:
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Restored database is corrupt")
    store = WorkspaceStore(destination / "workspace.db")
    with store.connection() as db:
        for row in db.execute("SELECT * FROM project_documents").fetchall():
            record, _ = store._document_snapshot(row, row["project_id"])
            db.execute("UPDATE project_documents SET path=? WHERE id=?",
                       (record["path"], row["id"]))
    verify_objects(destination / "research.db", destination / "research-objects")
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

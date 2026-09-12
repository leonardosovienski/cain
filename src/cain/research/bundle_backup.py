"""Administrative verification of every archived bundle, independent of grants."""

from pathlib import Path
import sqlite3
from contextlib import closing

from research_bundle import canonical, digest as content_digest, entity_key, loads, signature, validate
from cain.research.bundles import BundleService
from cain.research.objects import Objects


def reachables(database):
    result = {}
    with closing(sqlite3.connect(Path(database).absolute().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='research_bundles'").fetchone():
            return result
        checker = object.__new__(BundleService)
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='research_bundle_approvals'").fetchone():
            expected = {}
            for approval in db.execute("SELECT id,raw FROM research_bundle_approvals"):
                approved = validate(loads(approval["raw"]))
                if approved["bundle_id"] != approval["id"]:
                    raise ValueError("CORRUPTION: administrative approval")
                for entity in approved["entities"]:
                    eid, sig = entity_key(approved["origin"], entity), signature(approved, entity)
                    if expected.setdefault(eid, sig) != sig:
                        raise ValueError("CORRUPTION: global reservation conflict")
            if dict(db.execute("SELECT id,signature FROM research_entity_reservations")) != expected:
                raise ValueError("CORRUPTION: administrative reservations")
        for row in db.execute("SELECT * FROM research_bundles"):
            package = validate(loads(row["raw"]))
            if (
                row["id"] != package["bundle_id"]
                or content_digest(row["raw"]) != row["raw_sha"]
                or row["origin"] != canonical(package["origin"]).decode()
                or row["restrictions"] != canonical(package["restrictions"]).decode()
            ):
                raise ValueError("CORRUPTION: backup archive")
            checker._check_projection(db, row["scope"], package)
            checker._check_raw_variants(db, row["scope"], package)
            for a in package["artifacts"]:
                if a["availability"] == "received":
                    old = result.setdefault(a["sha256"], a["size"])
                    if old != a["size"]:
                        raise ValueError("CORRUPTION: inconsistent content size")
    return result


def copy_objects(database, root, destination):
    store = Objects(root)
    objects = reachables(database)
    for digest, size in objects.items():
        relative = store.relative(digest)
        target = Path(destination) / "research-objects" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        store.materialize(digest, size, target)
    return objects


def verify_objects(database, root):
    objects = reachables(database)
    store = Objects(root)
    for digest, size in objects.items():
        store.verify(digest, size)
    return objects

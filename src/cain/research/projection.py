"""Rebuildable projection of admitted publications: ids, signatures, membership, checks."""

import json

from research_snapshot import canonical, digest, loads, validate


class ContentConflict(ValueError):
    def __init__(self, record_id):
        super().__init__("CONFLICT: identical source occurrence/revision has divergent payload")
        self.record_id = record_id


def load_archive(db, scope, is_authorized):
    """Authorized publications of ``scope``; ``is_authorized(origin, restrictions)`` is
    consulted per publication so a policy change is honoured mid-read."""
    allowed = {}
    admitted_bytes = 0
    # Authorization metadata only; do not retrieve archived content until authorized.
    if (
        db.execute("SELECT count(*) FROM publications WHERE scope=?", (scope,)).fetchone()[0]
        > 500
    ):
        raise ValueError("L0 scope exceeds 500 publications; split collections")
    for row in db.execute(
        "SELECT id,origin,restrictions,length(raw) AS size FROM publications WHERE scope=?",
        (scope,),
    ):
        if is_authorized(json.loads(row["origin"]), json.loads(row["restrictions"])):
            admitted_bytes += row["size"]
            if admitted_bytes > 20_000_000:
                raise ValueError(
                    "L0 admitted archive exceeds 20000000 bytes; split collections"
                )
            raw = db.execute(
                "SELECT raw FROM publications WHERE scope=? AND id=?", (scope, row["id"])
            ).fetchone()[0]
            package = validate(loads(raw))
            if (
                canonical(package["origin"]).decode() != row["origin"]
                or canonical(package["restrictions"]).decode() != row["restrictions"]
                or package["publication_id"] != row["id"]
            ):
                raise ValueError("Archive authorization metadata corrupt")
            allowed[row["id"]] = package
    return allowed


def projection(package, record):
    origin = package["origin"]
    namespace = [origin[k] for k in ("domain", "repository", "publisher", "stream")]
    rid = digest(canonical(namespace + [record["source_id"], record["revision"]]))
    evidence = {e["id"]: e for e in package["evidence"]}
    signature = digest(canonical([record, [evidence[e] for e in record["evidence_ids"]]]))
    return rid, signature


def project(db, scope, package):
    for record in package["records"]:
        rid, signature = projection(package, record)
        old = db.execute(
            "SELECT signature FROM records WHERE scope=? AND id=?", (scope, rid)
        ).fetchone()
        if old and old[0] != signature:
            raise ContentConflict(rid)
        db.execute(
            "INSERT OR IGNORE INTO records VALUES(?,?,?,?,?,?,?,?,?)",
            (
                scope,
                rid,
                package["origin"]["domain"],
                record["source_id"],
                record["kind"],
                record["source_status"],
                record["revision"],
                canonical(record).decode(),
                signature,
            ),
        )
        db.execute(
            "INSERT OR IGNORE INTO membership VALUES(?,?,?)",
            (scope, package["publication_id"], rid),
        )


def verify_projection(db, scope, archives):
    """Verify before filtering: a corrupt index must never become false absence."""
    for pubid, package in archives.items():
        expected_members = set()
        for record in package["records"]:
            rid, signature = projection(package, record)
            expected_members.add(rid)
            row = db.execute(
                "SELECT domain,source_id,kind,status,revision,payload,signature "
                "FROM records WHERE scope=? AND id=?",
                (scope, rid),
            ).fetchone()
            expected = (
                package["origin"]["domain"],
                record["source_id"],
                record["kind"],
                record["source_status"],
                record["revision"],
                canonical(record).decode(),
                signature,
            )
            if row is None or tuple(row) != expected:
                raise ValueError("Projection corrupt; research projection requires rebuild")
        actual_members = {
            r[0]
            for r in db.execute(
                "SELECT record FROM membership WHERE scope=? AND publication=?", (scope, pubid)
            )
        }
        if actual_members != expected_members:
            raise ValueError("Research membership corrupt; verify and rebuild")

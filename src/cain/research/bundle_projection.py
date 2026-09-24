"""Rebuildable bundle projections: entity/artifact/relation rows, raw variants and checks."""

import json

from research_bundle import canonical, digest, entity_key, loads, signature, validate


def project(db, scope, package):
    bid = package["bundle_id"]
    for entity in package["entities"]:
        eid, sig = entity_key(package["origin"], entity), signature(package, entity)
        if db.execute(
            "SELECT 1 FROM research_entities WHERE id=? AND signature<>?", (eid, sig)
        ).fetchone():
            raise ValueError("CONFLICT")
        db.execute(
            "INSERT OR IGNORE INTO research_entities VALUES(?,?,?,?,?,?,?,?,?)",
            (
                scope,
                eid,
                package["origin"]["domain"],
                entity["entity_type"],
                entity["entity_id"],
                entity["revision"],
                entity["status"],
                sig,
                canonical(entity).decode(),
            ),
        )
        db.execute(
            "INSERT OR IGNORE INTO research_bundle_entities VALUES(?,?,?)", (scope, bid, eid)
        )
    for a in package["artifacts"]:
        db.execute(
            "INSERT INTO research_artifacts VALUES(?,?,?,?,?)",
            (scope, bid, a["artifact_id"], a["sha256"], canonical(a).decode()),
        )
    for r in package["relations"]:
        db.execute(
            "INSERT INTO research_relations VALUES(?,?,?,?,?,?)",
            (
                scope,
                bid,
                r["relation_id"],
                canonical(r["source"]).decode(),
                canonical(r["target"]).decode(),
                canonical(r).decode(),
            ),
        )



def check_raw_variants(db, scope, bundle):
    """Verify preserved transports, including new receipt-to-byte commitments.

    Old receipts never promised variant preservation and are not rewritten.
    """
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='research_bundle_raw_variants'"
    ).fetchone():
        return
    bid = bundle["bundle_id"]
    hashes = {
        db.execute(
            "SELECT raw_sha FROM research_bundles WHERE scope=? AND id=?", (scope, bid)
        ).fetchone()[0]
    }
    for row in db.execute(
        "SELECT raw_sha,raw FROM research_bundle_raw_variants WHERE scope=? AND bundle=?",
        (scope, bid),
    ):
        if digest(row["raw"]) != row["raw_sha"] or validate(loads(row["raw"])) != bundle:
            raise ValueError("CORRUPTION: raw variant")
        hashes.add(row["raw_sha"])
    for row in db.execute(
        "SELECT payload FROM research_bundle_receipts WHERE scope=?", (scope,)
    ):
        receipt = json.loads(row[0])
        if (
            receipt.get("raw_preserved")
            and receipt["bundle_id"] == bid
            and receipt["raw_manifest_sha256"] not in hashes
        ):
            raise ValueError("CORRUPTION: missing receipted raw variant")



def load_archives(db, scope, grants_of):
    result = []
    used = 0
    for row in db.execute(
        "SELECT id,origin,restrictions,length(raw) AS size FROM research_bundles WHERE scope=? ORDER BY id",
        (scope,),
    ):
        grants = grants_of(json.loads(row["origin"]), json.loads(row["restrictions"]))
        if not grants:
            continue
        used += row["size"]
        if used > 20_000_000 or len(result) >= 100:
            raise ValueError("SCOPE_LIMIT")
        stored = db.execute(
            "SELECT raw,raw_sha FROM research_bundles WHERE scope=? AND id=?",
            (scope, row["id"]),
        ).fetchone()
        bundle = validate(loads(stored["raw"]))
        if (
            digest(stored["raw"]) != stored["raw_sha"]
            or bundle["bundle_id"] != row["id"]
            or canonical(bundle["origin"]).decode() != row["origin"]
            or canonical(bundle["restrictions"]).decode() != row["restrictions"]
        ):
            raise ValueError("CORRUPTION: raw authorization metadata")
        check_raw_variants(db, scope, bundle)
        result.append((bundle, grants))
    return result



def check_projection(db, scope, bundle):
    bid = bundle["bundle_id"]
    expected = set()
    for e in bundle["entities"]:
        eid = entity_key(bundle["origin"], e)
        expected.add(eid)
        row = db.execute(
            "SELECT * FROM research_entities WHERE scope=? AND id=?", (scope, eid)
        ).fetchone()
        values = (
            scope,
            eid,
            bundle["origin"]["domain"],
            e["entity_type"],
            e["entity_id"],
            e["revision"],
            e["status"],
            signature(bundle, e),
            canonical(e).decode(),
        )
        if row is None or tuple(row) != values:
            raise ValueError("CORRUPTION: entity projection")
    actual = {
        r[0]
        for r in db.execute(
            "SELECT entity FROM research_bundle_entities WHERE scope=? AND bundle=?",
            (scope, bid),
        )
    }
    if expected != actual:
        raise ValueError("CORRUPTION: memberships")
    for table, items, identity in (
        ("research_artifacts", bundle["artifacts"], "artifact_id"),
        ("research_relations", bundle["relations"], "relation_id"),
    ):
        rows = db.execute(
            "SELECT * FROM " + table + " WHERE scope=? AND bundle=?", (scope, bid)
        ).fetchall()
        if {r["id"]: r["payload"] for r in rows} != {
            i[identity]: canonical(i).decode() for i in items
        }:
            raise ValueError("CORRUPTION: resource/relation projection")
        for row in rows:
            item = json.loads(row["payload"])
            if table == "research_artifacts" and row["sha256"] != item["sha256"]:
                raise ValueError("CORRUPTION: resource index")
            if table == "research_relations" and (
                row["source"] != canonical(item["source"]).decode()
                or row["target"] != canonical(item["target"]).decode()
            ):
                raise ValueError("CORRUPTION: relation index")

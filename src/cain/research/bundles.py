"""Receiver-authorized bundle archive and rebuildable projections."""

import io
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4

from research_bundle import (
    MAX_BYTES,
    MAX_OBJECT,
    MAX_RECEIVED,
    canonical,
    digest,
    entity_key,
    keys,
    loads,
    namespace,
    signature,
    validate,
)
from research_bundle.files import safe_open, transfer

from cain.research.objects import Objects
from cain.research.service import now


def validate_grants(grants):
    if type(grants) is not list or len(grants) > 200:
        raise ValueError("Invalid bundle grants")
    for grant in grants:
        keys(
            grant,
            "user project collection domain repository publisher stream sources policies generate roles reference_only max_manifest_bytes max_object_bytes max_received_bytes",
        )
        for key in ("user", "project", "collection", "domain", "repository", "publisher", "stream"):
            if type(grant[key]) is not str or len(grant[key]) > 500:
                raise ValueError("Invalid bundle grant identity")
        for key in ("sources", "policies", "roles"):
            if (
                type(grant[key]) is not list
                or len(grant[key]) > 200
                or any(type(v) is not str for v in grant[key])
            ):
                raise ValueError("Invalid bundle grant list")
        for key in ("generate", "reference_only"):
            if type(grant[key]) is not bool:
                raise ValueError("Invalid bundle permission")
        for key, cap in (
            ("max_manifest_bytes", MAX_BYTES),
            ("max_object_bytes", MAX_OBJECT),
            ("max_received_bytes", MAX_RECEIVED),
        ):
            if type(grant[key]) is not int or not 0 <= grant[key] <= cap:
                raise ValueError("Invalid bundle cap")


class BundleService:
    def __init__(self, service, objects=None):
        self.service = service
        self.objects = Objects(
            objects
            or os.getenv("CAIN_RESEARCH_OBJECTS")
            or service.path.parent / "research-objects"
        )
        with service.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS research_bundles(
                  scope TEXT NOT NULL, id TEXT NOT NULL, origin TEXT NOT NULL,
                  restrictions TEXT NOT NULL, raw BLOB NOT NULL, raw_sha TEXT NOT NULL,
                  received_at TEXT NOT NULL, PRIMARY KEY(scope,id));
                CREATE TABLE IF NOT EXISTS research_entities(
                  scope TEXT NOT NULL, id TEXT NOT NULL, domain TEXT NOT NULL,
                  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, revision TEXT NOT NULL,
                  status TEXT NOT NULL, signature TEXT NOT NULL, payload TEXT NOT NULL,
                  PRIMARY KEY(scope,id));
                CREATE INDEX IF NOT EXISTS bundle_entity_filter ON research_entities(scope,domain,entity_type,entity_id,status);
                CREATE TABLE IF NOT EXISTS research_bundle_entities(
                  scope TEXT NOT NULL, bundle TEXT NOT NULL, entity TEXT NOT NULL,
                  PRIMARY KEY(scope,bundle,entity),
                  FOREIGN KEY(scope,bundle) REFERENCES research_bundles(scope,id),
                  FOREIGN KEY(scope,entity) REFERENCES research_entities(scope,id));
                CREATE TABLE IF NOT EXISTS research_artifacts(
                  scope TEXT NOT NULL, bundle TEXT NOT NULL, id TEXT NOT NULL,
                  sha256 TEXT, payload TEXT NOT NULL, PRIMARY KEY(scope,bundle,id),
                  FOREIGN KEY(scope,bundle) REFERENCES research_bundles(scope,id));
                CREATE INDEX IF NOT EXISTS bundle_hash ON research_artifacts(scope,sha256);
                CREATE TABLE IF NOT EXISTS research_relations(
                  scope TEXT NOT NULL, bundle TEXT NOT NULL, id TEXT NOT NULL,
                  source TEXT NOT NULL, target TEXT NOT NULL, payload TEXT NOT NULL,
                  PRIMARY KEY(scope,bundle,id),
                  FOREIGN KEY(scope,bundle) REFERENCES research_bundles(scope,id));
                CREATE INDEX IF NOT EXISTS bundle_relation_source ON research_relations(scope,source);
                CREATE INDEX IF NOT EXISTS bundle_relation_target ON research_relations(scope,target);
                CREATE TABLE IF NOT EXISTS research_bundle_receipts(
                  id TEXT PRIMARY KEY, scope TEXT NOT NULL, at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS research_entity_reservations(
                  id TEXT PRIMARY KEY, signature TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS research_bundle_approvals(
                  scope TEXT NOT NULL, id TEXT NOT NULL, approved_at TEXT NOT NULL,
                  raw BLOB NOT NULL,
                  PRIMARY KEY(scope,id));
                CREATE TABLE IF NOT EXISTS research_bundle_raw_variants(
                  scope TEXT NOT NULL, bundle TEXT NOT NULL, raw_sha TEXT NOT NULL,
                  raw BLOB NOT NULL, received_at TEXT NOT NULL,
                  PRIMARY KEY(scope,bundle,raw_sha),
                  FOREIGN KEY(scope,bundle) REFERENCES research_bundles(scope,id));
            """)

    def grants(self, scope, origin, restrictions, generate=False):
        if not restrictions["read"] or (generate and not restrictions["generate"]):
            return []
        policy = self.service.policy()
        if policy["version"] != 3:
            return []
        identity = json.loads(scope)
        return [
            g
            for g in policy["bundle_grants"]
            if [g[k] for k in ("user", "project", "collection")] == identity
            and all(g[k] == origin[k] for k in ("domain", "repository", "publisher", "stream"))
            and set(origin["inputs"]) <= set(g["sources"])
            and restrictions["policy"] in g["policies"]
            and (not generate or g["generate"])
        ]

    @staticmethod
    def resource_allowed(artifact, grants):
        return any(
            artifact["role"] in g["roles"]
            and (artifact["availability"] == "received" or g["reference_only"])
            for g in grants
        )

    def _admit(self, scope, package, size):
        grants = self.grants(scope, package["origin"], package["restrictions"])
        total = sum(a["size"] for a in package["artifacts"] if a["availability"] == "received")
        # One complete grant must admit the operation; partial grants do not compose caps.
        for grant in grants:
            if (
                size <= grant["max_manifest_bytes"]
                and total <= grant["max_received_bytes"]
                and all(
                    self.resource_allowed(a, [grant])
                    and (a["availability"] != "received" or a["size"] <= grant["max_object_bytes"])
                    for a in package["artifacts"]
                )
            ):
                return
        raise PermissionError("NOT_AUTHORIZED")

    def _project(self, db, scope, package):
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

    def _receipt(self, scope, status, package=None, error=None, raw_sha=None):
        result = dict(
            attempt_id=str(uuid4()),
            contract="ResearchBundleV1",
            status=status,
            bundle_id=package["bundle_id"] if package else None,
            error=error,
            raw_manifest_sha256=raw_sha,
        )
        if package:
            result["raw_preserved"] = True
            received = [a for a in package["artifacts"] if a["availability"] == "received"]
            result.update(
                entities=len(package["entities"]),
                resources=len(package["artifacts"]),
                received_objects=len(received),
                received_bytes=sum(a["size"] for a in received),
                references=len(package["artifacts"]) - len(received),
            )
        with self.service.connection() as db:
            db.execute(
                "INSERT INTO research_bundle_receipts VALUES(?,?,?,?)",
                (result["attempt_id"], scope, now(), canonical(result).decode()),
            )
        return result

    def approve(self, relative, scope):
        """Trusted local administrator only; never exposed to scoped HTTP callers.

        Reserve global semantics before granting an exact scoped attachment.
        Approval neither reads objects nor creates a readable membership.
        """
        root = Path(self.service.import_root(scope))
        with safe_open(root, relative) as source:
            buffer = io.BytesIO()
            transfer(source, buffer, limit=MAX_BYTES)
        raw = buffer.getvalue()
        package = validate(loads(raw))
        self._admit(scope, package, len(raw))
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            count, used = db.execute(
                "SELECT count(*),coalesce(sum(length(raw)),0) FROM research_bundle_approvals WHERE scope=?",
                (scope,),
            ).fetchone()
            existing = db.execute(
                "SELECT 1 FROM research_bundle_approvals WHERE scope=? AND id=?",
                (scope, package["bundle_id"]),
            ).fetchone()
            if not existing and (count >= 100 or used + len(canonical(package)) > 20_000_000):
                raise ValueError("APPROVAL_LIMIT")
            for entity in package["entities"]:
                eid, sig = entity_key(package["origin"], entity), signature(package, entity)
                for table in ("research_entity_reservations", "research_entities"):
                    if db.execute(
                        "SELECT 1 FROM " + table + " WHERE id=? AND signature<>?", (eid, sig)
                    ).fetchone():
                        raise ValueError("CONFLICT")
                db.execute(
                    "INSERT OR IGNORE INTO research_entity_reservations VALUES(?,?)", (eid, sig)
                )
            db.execute(
                "INSERT OR IGNORE INTO research_bundle_approvals VALUES(?,?,?,?)",
                (scope, package["bundle_id"], now(), canonical(package)),
            )
        return dict(status="approved", bundle_id=package["bundle_id"], objects_received=False)

    def ingest(self, relative, scope):
        package = None
        raw_sha = None
        try:
            root = Path(self.service.import_root(scope))
            with safe_open(root, relative) as source:
                buffer = io.BytesIO()
                transfer(source, buffer, limit=MAX_BYTES)
                raw = buffer.getvalue()
            package = validate(loads(raw))
            self._admit(scope, package, len(raw))
            # Only an administrator can approve publication. Read grants are insufficient.
            with self.service.connection() as db:
                if not db.execute(
                    "SELECT 1 FROM research_bundle_approvals WHERE scope=? AND id=?",
                    (scope, package["bundle_id"]),
                ).fetchone():
                    raise PermissionError("NOT_AUTHORIZED")
            raw_sha = digest(raw)
            bundle_root = root / Path(relative).parent
            total = sum(a["size"] for a in package["artifacts"] if a["availability"] == "received")
            self.objects.root.parent.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(self.objects.root.parent).free < total + MAX_BYTES:
                raise ValueError("INSUFFICIENT_SPACE")
            with self.service.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                count, stored = db.execute(
                    "SELECT count(*),coalesce(sum(length(raw)),0) FROM research_bundles WHERE scope=?",
                    (scope,),
                ).fetchone()
                variant_bytes = db.execute(
                    "SELECT coalesce(sum(length(raw)),0) FROM research_bundle_raw_variants WHERE scope=?",
                    (scope,),
                ).fetchone()[0]
                old = db.execute(
                    "SELECT raw,raw_sha FROM research_bundles WHERE scope=? AND id=?",
                    (scope, package["bundle_id"]),
                ).fetchone()
                if old:
                    if (
                        digest(old["raw"]) != old["raw_sha"]
                        or validate(loads(old["raw"])) != package
                    ):
                        raise ValueError("CORRUPTION: duplicate archive")
                    self._check_raw_variants(db, scope, package)
                    self._check_projection(db, scope, package)
                    self._verify_objects(package)
                    status = "duplicate"
                else:
                    if count >= 100 or stored + variant_bytes + len(raw) > 20_000_000:
                        raise ValueError("SCOPE_LIMIT")
                    # No artifacts are opened until the entire manifest is admitted.
                    for a in package["artifacts"]:
                        if a["availability"] == "received":
                            self.objects.receive(
                                bundle_root, a["relative_path"], a["sha256"], a["size"]
                            )
                    db.execute(
                        "INSERT INTO research_bundles VALUES(?,?,?,?,?,?,?)",
                        (
                            scope,
                            package["bundle_id"],
                            canonical(package["origin"]).decode(),
                            canonical(package["restrictions"]).decode(),
                            raw,
                            raw_sha,
                            now(),
                        ),
                    )
                    self._project(db, scope, package)
                    status = "admitted"
                if (
                    old
                    and raw_sha != old["raw_sha"]
                    and not db.execute(
                        "SELECT 1 FROM research_bundle_raw_variants WHERE scope=? AND bundle=? AND raw_sha=?",
                        (scope, package["bundle_id"], raw_sha),
                    ).fetchone()
                ):
                    variants, variant_bytes = db.execute(
                        "SELECT count(*),coalesce(sum(length(raw)),0) FROM research_bundle_raw_variants WHERE scope=?",
                        (scope,),
                    ).fetchone()
                    per_bundle = db.execute(
                        "SELECT count(*) FROM research_bundle_raw_variants WHERE scope=? AND bundle=?",
                        (scope, package["bundle_id"]),
                    ).fetchone()[0]
                    if (
                        per_bundle >= 7
                        or variants >= 700
                        or stored + variant_bytes + len(raw) > 20_000_000
                    ):
                        raise ValueError("RAW_VARIANT_LIMIT")
                    db.execute(
                        "INSERT INTO research_bundle_raw_variants VALUES(?,?,?,?,?)",
                        (scope, package["bundle_id"], raw_sha, raw, now()),
                    )
            return self._receipt(scope, status, package, raw_sha=raw_sha)
        except Exception as exc:
            # No producer text, filesystem paths or secrets in rejection receipts.
            code = "NOT_AUTHORIZED" if isinstance(exc, PermissionError) else "IMPORT_REJECTED"
            if str(exc) == "CONFLICT":
                code = "CONFLICT"
            self._receipt(scope, "rejected", error=code)
            raise

    @staticmethod
    def _check_raw_variants(db, scope, bundle):
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

    def _archives(self, db, scope, generate=False):
        result = []
        used = 0
        for row in db.execute(
            "SELECT id,origin,restrictions,length(raw) AS size FROM research_bundles WHERE scope=? ORDER BY id",
            (scope,),
        ):
            grants = self.grants(
                scope, json.loads(row["origin"]), json.loads(row["restrictions"]), generate
            )
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
            self._check_raw_variants(db, scope, bundle)
            result.append((bundle, grants))
        return result

    def _check_projection(self, db, scope, bundle):
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

    def query(
        self,
        scope,
        *,
        entity_id=None,
        entity_type=None,
        revision=None,
        bundle_id=None,
        artifact_id=None,
        evidence_id=None,
        relation_type=None,
        domain=None,
        status=None,
        limit=20,
        offset=0,
        generate=False,
    ):
        if (
            type(limit) is not int
            or not 1 <= limit <= 50
            or type(offset) is not int
            or not 0 <= offset <= 100000
        ):
            raise ValueError("Invalid pagination")
        records, artifacts, relations, coverage = {}, [], [], []
        evidence = []
        with self.service.connection() as db:
            archives = self._archives(db, scope, generate)
            descriptors = {
                (tuple(namespace(b["origin"])), a["artifact_id"], digest(canonical(a)))
                for b, g in archives
                for a in b["artifacts"]
                if self.resource_allowed(a, g)
            }
            for bundle, grants in archives:
                self._check_projection(db, scope, bundle)
                bid = bundle["bundle_id"]
                if (bundle_id is not None and bid != bundle_id) or (
                    domain is not None and bundle["origin"]["domain"] != domain
                ):
                    continue
                selected = {
                    (e["entity_id"], e["revision"])
                    for e in bundle["entities"]
                    if (entity_id is None or e["entity_id"] == entity_id)
                    and (entity_type is None or e["entity_type"] == entity_type)
                    and (revision is None or e["revision"] == revision)
                    and (status is None or e["status"] == status)
                }
                entity_filter = any(
                    v is not None for v in (entity_id, entity_type, revision, status)
                )
                if entity_filter and not selected:
                    continue
                linked_evidence = {
                    ref
                    for e in bundle["entities"]
                    if (e["entity_id"], e["revision"]) in selected
                    for ref in e["evidence_ids"]
                }
                evidence.extend(
                    dict(bundle_id=bid, **e)
                    for e in bundle["evidence"]
                    if (not entity_filter or e["id"] in linked_evidence)
                    and (evidence_id is None or e["id"] == evidence_id)
                )
                coverage.append(dict(bundle_id=bid, **bundle["coverage"]))
                visible = {
                    a["artifact_id"]
                    for a in bundle["artifacts"]
                    if self.resource_allowed(a, grants)
                    and (artifact_id is None or a["artifact_id"] == artifact_id)
                }
                if entity_filter:
                    linked = {
                        ep["id"]
                        for r in bundle["relations"]
                        if any(
                            ep["kind"] == "entity"
                            and not ep["external"]
                            and (ep["id"], ep["revision"]) in selected
                            for ep in (r["source"], r["target"])
                        )
                        for ep in (r["source"], r["target"])
                        if ep["kind"] == "artifact" and not ep["external"]
                    }
                    visible &= linked
                for a in bundle["artifacts"]:
                    if a["artifact_id"] in visible:
                        artifacts.append(dict(bundle_id=bid, **a))
                for r in bundle["relations"]:
                    if relation_type is not None and r["type"] != relation_type:
                        continue
                    if entity_filter and not any(
                        ep["kind"] == "entity"
                        and not ep["external"]
                        and (ep["id"], ep["revision"]) in selected
                        for ep in (r["source"], r["target"])
                    ):
                        continue
                    if artifact_id is not None and not any(
                        ep["kind"] == "artifact" and not ep["external"] and ep["id"] in visible
                        for ep in (r["source"], r["target"])
                    ):
                        continue

                    def allowed(ep):
                        if ep["kind"] != "artifact":
                            return True
                        if not ep["external"]:
                            return ep["id"] in visible
                        if bundle["profile"] == "local-research/1":
                            # Legacy external identity is only unambiguous when local.
                            return (
                                ep["namespace"] == namespace(bundle["origin"])
                                and ep["id"] in visible
                            )
                        return (tuple(ep["namespace"]), ep["id"], ep["revision"]) in descriptors

                    if all(allowed(ep) for ep in (r["source"], r["target"])):
                        relations.append(dict(bundle_id=bid, **r))
                for e in bundle["entities"]:
                    if (
                        (entity_id is None or e["entity_id"] == entity_id)
                        and (revision is None or e["revision"] == revision)
                        and (entity_type is None or e["entity_type"] == entity_type)
                        and (status is None or e["status"] == status)
                        and (domain is None or bundle["origin"]["domain"] == domain)
                    ):
                        eid = entity_key(bundle["origin"], e)
                        row = records.setdefault(
                            eid, dict(id=eid, **e, origin=bundle["origin"], bundles=[])
                        )
                        row["bundles"].append(bid)
        rows = sorted(records.values(), key=lambda e: e["id"])
        # Independently bounded metadata pages, no arbitrary payload index.
        return dict(
            classification="FACTUAL",
            entities=rows[offset : offset + limit],
            total=len(rows),
            artifacts=artifacts[offset : offset + limit],
            artifact_total=len(artifacts),
            relations=relations[offset : offset + limit],
            relation_total=len(relations),
            evidence=evidence[offset : offset + limit],
            evidence_total=len(evidence),
            coverage=coverage,
        )

    def evidence(self, scope, bundle_id, evidence_id):
        result = self.query(scope, bundle_id=bundle_id, evidence_id=evidence_id, limit=1)
        if not result["evidence"]:
            raise ValueError("NOT_FOUND")
        return dict(classification="FACTUAL", evidence=result["evidence"][0])

    def entity(self, scope, bundle_id, entity_id, revision):
        result = self.query(
            scope, bundle_id=bundle_id, entity_id=entity_id, revision=revision, limit=50
        )
        if not result["entities"]:
            raise ValueError("NOT_FOUND")
        return result

    def artifact(self, scope, bundle_id, artifact_id):
        result = self.query(scope, bundle_id=bundle_id, artifact_id=artifact_id, limit=50)
        if not result["artifacts"]:
            raise ValueError("NOT_FOUND")
        return dict(
            classification="FACTUAL",
            artifact=result["artifacts"][0],
            relations=result["relations"],
            relation_total=result["relation_total"],
        )

    def materialize(self, scope, bundle_id, artifact_id, destination):
        with self.service.connection() as db:
            for bundle, grants in self._archives(db, scope):
                if bundle["bundle_id"] != bundle_id:
                    continue
                self._check_projection(db, scope, bundle)
                for a in bundle["artifacts"]:
                    if a["artifact_id"] == artifact_id and self.resource_allowed(a, grants):
                        if a["availability"] != "received":
                            raise ValueError("REFERENCE_ONLY")
                        self.objects.materialize(a["sha256"], a["size"], destination)
                        return dict(status="materialized", sha256=a["sha256"], bytes=a["size"])
        raise ValueError("NOT_FOUND")

    def _verify_objects(self, bundle):
        for a in bundle["artifacts"]:
            if a["availability"] == "received":
                try:
                    self.objects.verify(a["sha256"], a["size"])
                except OSError as exc:
                    raise ValueError("CORRUPTION: received object unavailable") from exc

    def verify(self, scope, rebuild=False):
        with self.service.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            archives = self._archives(db, scope)
            count = db.execute(
                "SELECT count(*) FROM research_bundles WHERE scope=?", (scope,)
            ).fetchone()[0]
            if count != len(archives) or any(
                not self.resource_allowed(a, grants)
                for bundle, grants in archives
                for a in bundle["artifacts"]
            ):
                raise PermissionError("NOT_AUTHORIZED: complete scope required")
            for bundle, _ in archives:
                self._verify_objects(bundle)
            if rebuild:
                # Rebuild all this scope's projections only if every raw is authorized.
                count = db.execute(
                    "SELECT count(*) FROM research_bundles WHERE scope=?", (scope,)
                ).fetchone()[0]
                if count != len(archives):
                    raise PermissionError("NOT_AUTHORIZED: complete scope required for rebuild")
                for table in (
                    "research_relations",
                    "research_artifacts",
                    "research_bundle_entities",
                    "research_entities",
                ):
                    db.execute("DELETE FROM " + table + " WHERE scope=?", (scope,))
                for bundle, _ in archives:
                    self._project(db, scope, bundle)
            for bundle, _ in archives:
                self._check_projection(db, scope, bundle)
        return dict(status="verified", bundles=len(archives), rebuilt=rebuild)

    def orphan_report(self):
        """Local administrator only. Never exposed through scope/HTTP queries."""
        with self.service.connection() as db:
            reachable = set()
            for row in db.execute("SELECT raw FROM research_bundles"):
                package = validate(loads(row[0]))
                reachable.update(
                    a["sha256"] for a in package["artifacts"] if a["availability"] == "received"
                )
        blobs, temporary = self.objects.inventory()
        return dict(orphans=sorted(set(blobs) - reachable), temporary=temporary, destructive=False)

    def receipts(self, scope):
        with self.service.connection() as db:
            admitted = {}
            for bundle, grants in self._archives(db, scope):
                if all(self.resource_allowed(a, grants) for a in bundle["artifacts"]):
                    admitted[bundle["bundle_id"]] = True
            rows = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT payload FROM research_bundle_receipts WHERE scope=? ORDER BY at DESC LIMIT 50",
                    (scope,),
                )
            ]
            return [r for r in rows if r["bundle_id"] is None or r["bundle_id"] in admitted]

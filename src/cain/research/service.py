"""Atomic SQLite archive + rebuildable projection. No domain or provider imports."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from research_snapshot import MAX_BYTES, canonical, confined, digest, keys, loads, validate


def now():
    return datetime.now(timezone.utc).isoformat()


class ContentConflict(ValueError):
    def __init__(self, record_id):
        super().__init__("CONFLICT: identical source occurrence/revision has divergent payload")
        self.record_id = record_id


class ResearchService:
    def __init__(self, path, policy_path):
        self.path = Path(path)
        self.policy_path = Path(policy_path) if policy_path else None
        if self.policy_path is None:
            raise ValueError("Research disabled: configure a trusted receiver policy")
        self.policy()  # fail before creating storage
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS publications(
                  scope TEXT NOT NULL, id TEXT NOT NULL, origin TEXT NOT NULL,
                  restrictions TEXT NOT NULL, raw BLOB NOT NULL, received_at TEXT NOT NULL,
                  PRIMARY KEY(scope,id));
                CREATE TABLE IF NOT EXISTS records(
                  scope TEXT NOT NULL, id TEXT NOT NULL, domain TEXT NOT NULL,
                  source_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
                  revision TEXT NOT NULL, payload TEXT NOT NULL, signature TEXT NOT NULL,
                  PRIMARY KEY(scope,id));
                CREATE INDEX IF NOT EXISTS research_filter ON records(scope,domain,source_id,status);
                CREATE TABLE IF NOT EXISTS membership(
                  scope TEXT NOT NULL, publication TEXT NOT NULL, record TEXT NOT NULL,
                  PRIMARY KEY(scope,publication,record),
                  FOREIGN KEY(scope,publication) REFERENCES publications(scope,id),
                  FOREIGN KEY(scope,record) REFERENCES records(scope,id));
                CREATE TABLE IF NOT EXISTS receipts(
                  id TEXT PRIMARY KEY, scope TEXT NOT NULL, at TEXT NOT NULL,
                  publication TEXT, status TEXT NOT NULL, error TEXT);
                CREATE TABLE IF NOT EXISTS queries(
                  id TEXT PRIMARY KEY, scope TEXT NOT NULL, at TEXT NOT NULL,
                  request TEXT NOT NULL, result TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS conflicts(
                  scope TEXT NOT NULL, receipt TEXT PRIMARY KEY, record TEXT NOT NULL,
                  incoming_publication TEXT NOT NULL);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def policy(self):
        policy = loads(self.policy_path.read_bytes())
        keys(policy, "version import_root grants")
        if policy["version"] != 1 or type(policy["grants"]) is not list:
            raise ValueError("Invalid receiver policy")
        if not Path(policy["import_root"]).is_absolute():
            raise ValueError("Receiver import_root must be absolute")
        for grant in policy["grants"]:
            keys(
                grant,
                "user project collection domain repository publisher stream sources policies generate",
            )
            if type(grant["generate"]) is not bool:
                raise ValueError("Invalid generation permission")
            for key in (
                "user",
                "project",
                "collection",
                "domain",
                "repository",
                "publisher",
                "stream",
            ):
                if type(grant[key]) is not str or len(grant[key]) > 500:
                    raise ValueError("Invalid grant identity")
            for key in ("sources", "policies"):
                if type(grant[key]) is not list or not all(type(v) is str for v in grant[key]):
                    raise ValueError("Invalid grant list")
        return policy

    @staticmethod
    def scope(user="leo", project=None, collection="crypto"):
        if any(type(v) is not str or not v.strip() or len(v) > 200 for v in (user, collection)):
            raise ValueError("Invalid research scope")
        if project is not None and (type(project) is not str or len(project) > 200):
            raise ValueError("Invalid project scope")
        return canonical([user, project or "", collection]).decode()

    def authorized(self, scope, origin, restrictions, generate=False):
        user, project, collection = json.loads(scope)
        if restrictions.get("read") is not True or (
            generate and restrictions.get("generate") is not True
        ):
            return False
        for grant in self.policy()["grants"]:
            if (
                [grant[k] for k in ("user", "project", "collection")] == [user, project, collection]
                and all(
                    grant[k] == origin.get(k)
                    for k in ("domain", "repository", "publisher", "stream")
                )
                and set(origin.get("inputs", {})) <= set(grant["sources"])
                and restrictions.get("policy") in grant["policies"]
                and (not generate or grant["generate"])
            ):
                return True
        return False

    def _archive(self, db, scope, generate=False):
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
            if self.authorized(
                scope, json.loads(row["origin"]), json.loads(row["restrictions"]), generate
            ):
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

    @staticmethod
    def projection(package, record):
        origin = package["origin"]
        namespace = [origin[k] for k in ("domain", "repository", "publisher", "stream")]
        rid = digest(canonical(namespace + [record["source_id"], record["revision"]]))
        evidence = {e["id"]: e for e in package["evidence"]}
        signature = digest(canonical([record, [evidence[e] for e in record["evidence_ids"]]]))
        return rid, signature

    def _project(self, db, scope, package):
        for record in package["records"]:
            rid, signature = self.projection(package, record)
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

    def ingest(self, relative, scope):
        receipt, publication = uuid4().hex, None
        try:
            path = confined(self.policy()["import_root"], relative)
            with path.open("rb") as handle:
                raw = handle.read(MAX_BYTES + 1)
            package = loads(raw)
            # Receiver policy independent of self-declared package permissions.
            if not self.authorized(
                scope, package.get("origin", {}), package.get("restrictions", {})
            ):
                raise ValueError("UNAUTHORIZED")
            validate(package)
            publication = package["publication_id"]
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                existed = db.execute(
                    "SELECT 1 FROM publications WHERE scope=? AND id=?", (scope, publication)
                ).fetchone()
                db.execute(
                    "INSERT OR IGNORE INTO publications VALUES(?,?,?,?,?,?)",
                    (
                        scope,
                        publication,
                        canonical(package["origin"]).decode(),
                        canonical(package["restrictions"]).decode(),
                        raw,
                        now(),
                    ),
                )
                self._project(db, scope, package)
                status = "duplicate" if existed else "admitted"
                db.execute(
                    "INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                    (receipt, scope, now(), publication, status, None),
                )
            return {
                "receipt_id": receipt,
                "publication_id": publication,
                "status": status,
                "records": len(package["records"]),
            }
        except (ValueError, OSError, sqlite3.Error, TypeError, KeyError, AttributeError) as exc:
            status = (
                "rejected"
                if isinstance(exc, (ValueError, TypeError, KeyError, AttributeError))
                else "process_failed"
            )
            code = "CONFLICT" if str(exc).startswith("CONFLICT:") else type(exc).__name__
            try:
                with self.connection() as db:
                    db.execute(
                        "INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                        (receipt, scope, now(), publication, status, code),
                    )
                    if isinstance(exc, ContentConflict):
                        db.execute(
                            "INSERT INTO conflicts VALUES(?,?,?,?)",
                            (scope, receipt, exc.record_id, publication),
                        )
            except (OSError, sqlite3.Error) as audit:
                raise RuntimeError(
                    "Import failed; NO DURABLE FAILURE RECEIPT: " + type(audit).__name__
                ) from None
            raise ValueError(f"Import {status}; receipt={receipt}; code={code}") from None

    def query(
        self,
        scope,
        *,
        domain=None,
        source_id=None,
        kind=None,
        status=None,
        revision=None,
        reason=None,
        text=None,
        completeness=None,
        limit=20,
        offset=0,
        generate=False,
    ):
        if (
            type(limit) is not int
            or not 1 <= limit <= 50
            or type(offset) is not int
            or not 0 <= offset <= 100_000
        ):
            raise ValueError("Invalid pagination")
        filters = dict(
            domain=domain,
            source_id=source_id,
            kind=kind,
            status=status,
            revision=revision,
            reason=reason,
            text=text,
            completeness=completeness,
            limit=limit,
            offset=offset,
        )
        for val in (domain, source_id, kind, status, revision, reason, text, completeness):
            if val is not None and (type(val) is not str or len(val) > 500):
                raise ValueError("Invalid filter")
        with self.connection() as db:
            archives = self._archive(db, scope, generate)
            if completeness:
                archives = {
                    k: p
                    for k, p in archives.items()
                    if p["coverage"]["completeness"] == completeness
                }
            where, params = ["r.scope=?"], [scope]
            for column, val in (
                ("domain", domain),
                ("source_id", source_id),
                ("kind", kind),
                ("status", status),
                ("revision", revision),
            ):
                if val is not None:
                    where.append(f"r.{column}=?")
                    params.append(val)
            # All SQL identifiers are application constants; values are parameters.
            placeholders = ",".join("?" for _ in archives) or "NULL"
            where.append(
                f"r.id IN (SELECT record FROM membership WHERE scope=? AND publication IN ({placeholders}))"
            )
            params.extend([scope, *archives])
            rows = db.execute(
                "SELECT r.* FROM records r WHERE "
                + " AND ".join(where)
                + " ORDER BY r.domain,r.source_id,r.revision",
                params,
            )
            found = []
            for row in rows:
                members = [
                    v[0]
                    for v in db.execute(
                        "SELECT publication FROM membership WHERE scope=? AND record=? ORDER BY publication",
                        (scope, row["id"]),
                    )
                    if v[0] in archives
                ]
                if not members:
                    continue
                record = json.loads(row["payload"])
                package = archives[members[0]]
                # Check projection against preserved publication, including support bytes.
                expected = next(
                    (r for r in package["records"] if self.projection(package, r)[0] == row["id"]),
                    None,
                )
                if expected != record or self.projection(package, record)[1] != row["signature"]:
                    raise ValueError("Research projection corrupt; verify and rebuild")
                ev = [
                    {**e, "reference_id": members[0] + ":" + e["id"]}
                    for e in package["evidence"]
                    if e["id"] in record["evidence_ids"]
                ]
                if reason and reason.casefold() not in (record["reason"] or "").casefold():
                    continue
                if (
                    text
                    and text.casefold()
                    not in (
                        canonical(record).decode() + " ".join(e["text"] or "" for e in ev)
                    ).casefold()
                ):
                    continue
                found.append(
                    {
                        "id": row["id"],
                        "domain": row["domain"],
                        **record,
                        "publications": members,
                        "origin": package["origin"],
                    }
                )
            page = found[offset : offset + limit]
            for record in page:
                pubid = record["publications"][0]
                record["evidence"] = [
                    {**e, "reference_id": pubid + ":" + e["id"]}
                    for e in archives[pubid]["evidence"]
                    if e["id"] in record["evidence_ids"]
                ]
            response = {
                "mode": "deterministic",
                "records": page,
                "total_record_revisions": len(found),
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < len(found),
                "coverage": [{"publication_id": k, **p["coverage"]} for k, p in archives.items()],
                "limitations": [
                    "Not found in the admitted scope does not mean never occurred",
                    "Counts are record revisions, not independent experiments",
                    "Unordered revisions coexist; receipt time does not select truth",
                    "Integrity is not semantic support or scientific validity",
                ],
                "conflicts": [
                    dict(r)
                    for r in db.execute(
                        f"SELECT receipt,record,incoming_publication FROM conflicts WHERE scope=? AND record IN (SELECT record FROM membership WHERE scope=? AND publication IN ({placeholders}))",
                        [scope, scope, *archives],
                    )
                ],
                "generation_scope": generate,
            }
            qid = uuid4().hex
            db.execute(
                "INSERT INTO queries VALUES(?,?,?,?,?)",
                (
                    qid,
                    scope,
                    now(),
                    canonical(filters).decode(),
                    canonical(
                        {"record_ids": [r["id"] for r in page], "total": len(found)}
                    ).decode(),
                ),
            )
            response["query_id"] = qid
            identities = {}
            for record in found:
                identity = canonical(
                    [record["origin"][k] for k in ("domain", "repository", "publisher", "stream")]
                    + [record["source_id"]]
                ).decode()
                identities.setdefault(identity, []).append(record["revision"])
            response["multiple_revisions"] = [
                {
                    "namespace_and_source": json.loads(k),
                    "revisions": v,
                    "resolution": "no implicit latest version",
                }
                for k, v in identities.items()
                if len(v) > 1
            ]
            response["distinct_source_occurrences"] = len(identities)
            response["ambiguous_observations"] = sum(
                r["identity_basis"] == "ambiguous_observation" for r in found
            )
            if len(canonical(response)) > 1_000_000:
                raise ValueError("Response exceeds 1000000 UTF-8 bytes; reduce page size")
            return response

    def log_explanation(self, scope, question, response):
        response_id = uuid4().hex
        with self.connection() as db:
            db.execute(
                "INSERT INTO queries VALUES(?,?,?,?,?)",
                (
                    response_id,
                    scope,
                    now(),
                    canonical({"mode": "explanation", "question": question}).decode(),
                    canonical(response).decode(),
                ),
            )
        return response_id

    def evidence(self, scope, reference):
        with self.connection() as db:
            archives = self._archive(db, scope)
            pubid, _, eid = reference.partition(":")
            package = archives.get(pubid)
            if package:
                for item in package["evidence"]:
                    if item["id"] == eid:
                        return {
                            **item,
                            "publication_id": pubid,
                            "coverage": package["coverage"],
                            "origin": package["origin"],
                        }
        raise ValueError("Evidence unavailable in authorized scope")

    def receipts(self, scope):
        with self.connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT id,at,status,error FROM receipts WHERE scope=? ORDER BY at DESC LIMIT 100",
                    (scope,),
                )
            ]

    def verify(self, scope, rebuild=False):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE" if rebuild else "BEGIN")
            if (
                db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or db.execute("PRAGMA foreign_key_check").fetchone()
            ):
                raise ValueError("SQLite integrity check failed")
            archives = self._archive(db, scope)
            all_count = db.execute(
                "SELECT count(*) FROM publications WHERE scope=?", (scope,)
            ).fetchone()[0]
            if len(archives) != all_count:
                raise ValueError(
                    "Some archived publications are not currently authorized; rebuild refused"
                )
            expected = {
                self.projection(p, r)[0]: self.projection(p, r)[1]
                for p in archives.values()
                for r in p["records"]
            }
            actual = {
                r[0]: r[1]
                for r in db.execute("SELECT id,signature FROM records WHERE scope=?", (scope,))
            }
            expected_members = {
                (p["publication_id"], self.projection(p, r)[0])
                for p in archives.values()
                for r in p["records"]
            }
            actual_members = {
                tuple(r)
                for r in db.execute(
                    "SELECT publication,record FROM membership WHERE scope=?", (scope,)
                )
            }
            expected_payloads = {
                self.projection(p, r)[0]: canonical(r).decode()
                for p in archives.values()
                for r in p["records"]
            }
            actual_payloads = {
                r[0]: r[1]
                for r in db.execute("SELECT id,payload FROM records WHERE scope=?", (scope,))
            }
            if rebuild:
                db.execute("DELETE FROM membership WHERE scope=?", (scope,))
                db.execute("DELETE FROM records WHERE scope=?", (scope,))
                for package in archives.values():
                    self._project(db, scope, package)
            elif (
                actual != expected
                or actual_members != expected_members
                or actual_payloads != expected_payloads
            ):
                raise ValueError("Projection differs from archive; rebuild required")
            return {
                "integrity": "verified",
                "publications": len(archives),
                "records": len(expected),
                "rebuilt": rebuild,
            }

    def backup(self, destination):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb"):
            pass
        try:
            with self.connection() as source:
                target = sqlite3.connect(destination)
                try:
                    source.backup(target)
                    if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Backup integrity failure")
                finally:
                    target.close()
        except Exception:
            # Incomplete backup is retained, never represented as verified.
            raise
        return {
            "backup": str(destination),
            "integrity": "verified",
            "method": "sqlite-online-backup",
        }

    @staticmethod
    def restore(source, destination):
        destination = Path(destination)
        with destination.open("xb"):
            pass
        original = sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)
        target = sqlite3.connect(destination)
        try:
            if original.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Restore source corrupt")
            original.backup(target)
        finally:
            target.close()
            original.close()
        return {"restored": str(destination), "method": "sqlite-online-backup"}

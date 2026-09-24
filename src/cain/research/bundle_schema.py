"""SQLite tables for the receiver-authorized bundle archive and its projections."""

SCHEMA = """
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
"""

"""SQLite schema and connection factory for the L0 research archive."""

from contextlib import contextmanager
import sqlite3

SCHEMA = """
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
            """


@contextmanager
def connect(path):
    """One connection per operation: 15 s lock wait, foreign keys on, commit on success."""
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()

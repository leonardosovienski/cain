"""SQLite authoritative identity/signal store and append-only decision evidence."""

from collections.abc import Iterable
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from cain.common import (
    DecisionRecord, IdentitySnapshot, IdentityState, MemoryDocument,
    PersonalityState, Signal, UserModel, utc_now,
)


def _connect(path: str | Path) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _serialize(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _identity(raw: str) -> IdentityState:
    values = json.loads(raw)
    personality = values.pop("personality")
    personality["principles"] = tuple(personality["principles"])
    return IdentityState(
        personality=PersonalityState(**personality),
        user_model=UserModel(**values.pop("user_model")),
        **values,
    )


class SQLiteIdentityStore:
    def __init__(self, path: str | Path):
        self._connection = _connect(path)
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS identities (
                user_id TEXT PRIMARY KEY, state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identity_snapshots (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, state_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identity_signals (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL REFERENCES identities(user_id),
                kind TEXT NOT NULL, text TEXT NOT NULL,
                metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
        """)

    def get(self, user_id: str) -> IdentityState | None:
        row = self._connection.execute(
            "SELECT state_json FROM identities WHERE user_id = ?", (user_id,)
        ).fetchone()
        return _identity(row["state_json"]) if row else None

    def upsert(self, user_id: str, state: IdentityState) -> None:
        if not user_id or state.user_id != user_id:
            raise ValueError("IdentityState.user_id must match its non-empty storage key")
        payload = _serialize(asdict(state))
        with self._connection:
            self._connection.execute(
                "INSERT INTO identities VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET state_json = excluded.state_json",
                (user_id, payload),
            )
            self._connection.execute(
                "INSERT INTO identity_snapshots(user_id, state_json, recorded_at) VALUES (?, ?, ?)",
                (user_id, payload, utc_now()),
            )

    def append_signal(self, user_id: str, signal: Signal) -> None:
        if "user_id" in signal.metadata and signal.metadata["user_id"] != user_id:
            raise ValueError("Signal metadata cannot impersonate a different user")
        metadata = {**signal.metadata, "user_id": user_id, "kind": signal.kind}
        with self._connection:
            self._connection.execute(
                "INSERT INTO identity_signals(signal_id, user_id, kind, text, metadata_json, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (signal.signal_id, user_id, signal.kind, signal.text,
                 _serialize(metadata), signal.created_at),
            )

    def history(self, user_id: str, limit: int = 20) -> list[IdentitySnapshot]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        rows = self._connection.execute(
            "SELECT state_json, recorded_at FROM identity_snapshots "
            "WHERE user_id = ? ORDER BY sequence DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        return [IdentitySnapshot(_identity(row["state_json"]), row["recorded_at"]) for row in rows]

    def iter_documents(self) -> Iterable[MemoryDocument]:
        rows = self._connection.execute(
            "SELECT signal_id, text, metadata_json FROM identity_signals ORDER BY sequence"
        ).fetchall()
        for row in rows:
            yield MemoryDocument(row["signal_id"], row["text"], json.loads(row["metadata_json"]))

    def close(self) -> None:
        self._connection.close()


class SQLiteDecisionLog:
    """SQL triggers reject updates/deletes; direct file tampering is outside this guarantee."""

    def __init__(self, path: str | Path):
        self._connection = _connect(path)
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE NOT NULL,
                run_id TEXT NOT NULL,
                record_json TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS decisions_no_update
            BEFORE UPDATE ON decisions BEGIN
                SELECT RAISE(ABORT, 'DecisionLog is append-only');
            END;
            CREATE TRIGGER IF NOT EXISTS decisions_no_delete
            BEFORE DELETE ON decisions BEGIN
                SELECT RAISE(ABORT, 'DecisionLog is append-only');
            END;
            CREATE TRIGGER IF NOT EXISTS decisions_no_replace
            BEFORE INSERT ON decisions
            WHEN EXISTS (SELECT 1 FROM decisions WHERE decision_id = NEW.decision_id
                         OR sequence = NEW.sequence)
            BEGIN
                SELECT RAISE(ABORT, 'DecisionLog is append-only');
            END;
        """)

    def append(self, record: DecisionRecord) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO decisions(decision_id, run_id, record_json) VALUES (?, ?, ?)",
                (record.decision_id, record.run_id, _serialize(asdict(record))),
            )

    def export(self, run_id: str) -> Iterable[DecisionRecord]:
        rows = self._connection.execute(
            "SELECT record_json FROM decisions WHERE run_id = ? ORDER BY sequence", (run_id,)
        ).fetchall()
        for row in rows:
            values = json.loads(row["record_json"])
            values["steps"] = tuple(values["steps"])
            yield DecisionRecord(**values)

    def close(self) -> None:
        self._connection.close()

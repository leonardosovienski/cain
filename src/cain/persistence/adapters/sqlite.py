"""SQLite authoritative identity/signal store and append-only decision evidence."""

from collections.abc import Iterable
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from cain.common import (
    DecisionRecord, IdentitySnapshot, IdentityState, MemoryDocument,
    PersonalityState, ScopedPreference, Signal, UserModel, utc_now,
)
from cain.persistence import ConcurrentIdentityUpdate


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
            CREATE TABLE IF NOT EXISTS scoped_preferences (
                user_id TEXT NOT NULL REFERENCES identities(user_id),
                scope TEXT NOT NULL CHECK(scope IN ('user', 'project', 'session', 'turn')),
                project_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                turn_id TEXT NOT NULL DEFAULT '',
                preference_key TEXT NOT NULL,
                record_json TEXT NOT NULL,
                PRIMARY KEY(user_id, scope, project_id, session_id, turn_id, preference_key)
            );
        """)

    def get(self, user_id: str) -> IdentityState | None:
        row = self._connection.execute(
            "SELECT state_json FROM identities WHERE user_id = ?", (user_id,)
        ).fetchone()
        return _identity(row["state_json"]) if row else None

    def create_if_absent(self, user_id: str, state: IdentityState) -> IdentityState:
        """Atomically create the initial profile, or return the existing state.

        A caller's earlier SELECT may have observed absence before another
        connection committed preferences. DO NOTHING preserves that state and
        its revision; only the successful creator records a baseline snapshot.
        """
        if not user_id or state.user_id != user_id:
            raise ValueError("IdentityState.user_id must match its non-empty storage key")
        payload = _serialize(asdict(state))
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            inserted = self._connection.execute(
                "INSERT INTO identities VALUES (?, ?) ON CONFLICT(user_id) DO NOTHING",
                (user_id, payload),
            )
            if inserted.rowcount == 1:
                self._connection.execute(
                    "INSERT INTO identity_snapshots(user_id, state_json, recorded_at) VALUES (?, ?, ?)",
                    (user_id, payload, utc_now()),
                )
            current = self.get(user_id)
            if current is None:
                raise RuntimeError("Atomic identity creation returned no profile")
        return current

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
        self.apply_signal(user_id, signal)

    def apply_signal(
        self, user_id: str, signal: Signal, state: IdentityState | None = None,
        expected_revision: int | None = None,
        *, scoped_preferences: list[ScopedPreference] | None = None,
    ) -> None:
        """Commit profile, snapshot and input together; index updates happen later.

        BEGIN IMMEDIATE serializes writers, and the revision check prevents a
        previously read profile from silently replacing a newer preference.
        """
        if "user_id" in signal.metadata and signal.metadata["user_id"] != user_id:
            raise ValueError("Signal metadata cannot impersonate a different user")
        if state is not None and state.user_id != user_id:
            raise ValueError("IdentityState.user_id must match its storage key")
        if scoped_preferences and state is None:
            raise ValueError("Scoped changes require an atomic identity revision")
        scoped_payloads = []
        for preference in scoped_preferences or []:
            if preference.user_id != user_id:
                raise ValueError("Scoped preference cannot impersonate another user")
            if preference.scope not in {"user", "project", "session", "turn"}:
                raise ValueError("Unknown preference scope")
            if preference.scope == "user" and any((preference.project_id, preference.session_id, preference.turn_id)):
                raise ValueError("User preference locations cannot contain context ids")
            if preference.scope == "project" and (not preference.project_id or preference.session_id or preference.turn_id):
                raise ValueError("Project preference requires only project_id")
            if preference.scope == "session" and (not preference.session_id or preference.turn_id):
                raise ValueError("Session preference requires session_id and optional project_id")
            if preference.scope == "turn" and (not preference.session_id or not preference.turn_id):
                raise ValueError("Turn preference requires session_id and turn_id")
            if preference.action not in {"set", "remove"} or (preference.action == "set" and preference.value is None):
                raise ValueError("Invalid scoped preference action/value")
            if preference.action == "remove" and preference.value is not None:
                raise ValueError("Removal tombstone must have a null value")
            scoped_payloads.append((
                user_id, preference.scope, preference.project_id or "", preference.session_id or "",
                preference.turn_id or "", preference.key, _serialize(asdict(preference)),
            ))
        metadata = {**signal.metadata, "user_id": user_id, "kind": signal.kind}
        signal_metadata = _serialize(metadata)
        state_payload = _serialize(asdict(state)) if state is not None else None
        with self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            if state is not None:
                current = self.get(user_id)
                if current is None:
                    raise ValueError("Identity must exist before applying a signal")
                if expected_revision is not None and current.revision != expected_revision:
                    raise ConcurrentIdentityUpdate(
                        f"Expected revision {expected_revision}; current revision is {current.revision}"
                    )
                self._connection.execute(
                    "UPDATE identities SET state_json = ? WHERE user_id = ?", (state_payload, user_id)
                )
                self._connection.execute(
                    "INSERT INTO identity_snapshots(user_id, state_json, recorded_at) VALUES (?, ?, ?)",
                    (user_id, state_payload, signal.created_at),
                )
            for scoped_payload in scoped_payloads:
                self._connection.execute(
                    "INSERT INTO scoped_preferences VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(user_id, scope, project_id, session_id, turn_id, preference_key) "
                    "DO UPDATE SET record_json = excluded.record_json", scoped_payload,
                )
            self._connection.execute(
                "INSERT INTO identity_signals(signal_id, user_id, kind, text, metadata_json, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (signal.signal_id, user_id, signal.kind, signal.text,
                 signal_metadata, signal.created_at),
            )

    def list_scoped_preferences(
        self, user_id: str, *, project_id: str | None = None,
        session_id: str | None = None, turn_id: str | None = None,
    ) -> list[ScopedPreference]:
        # Exact composite locations: a reused session id in another project is
        # a different scope. Blank context ids normalize to SQL's non-null keys.
        locations = [("user", "", "", "")]
        if project_id is not None:
            locations.append(("project", project_id, "", ""))
        if session_id is not None:
            locations.append(("session", project_id or "", session_id, ""))
        if turn_id is not None and session_id is not None:
            locations.append(("turn", project_id or "", session_id, turn_id))
        result = []
        for scope, project, session, turn in locations:
            rows = self._connection.execute(
                "SELECT record_json FROM scoped_preferences WHERE user_id = ? AND scope = ? "
                "AND project_id = ? AND session_id = ? AND turn_id = ? ORDER BY preference_key",
                (user_id, scope, project, session, turn),
            ).fetchall()
            result.extend(ScopedPreference(**json.loads(row["record_json"])) for row in rows)
        return result

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

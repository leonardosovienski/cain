"""The three persistence ports from ADR-0009, independent of storage backends."""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from cain.common import DecisionRecord, Hit, IdentitySnapshot, IdentityState, MemoryDocument, ScopedPreference, Signal


@runtime_checkable
class IdentityStore(Protocol):
    def get(self, user_id: str) -> IdentityState | None: ...
    # Creation must never replace a profile committed by another connection.
    def create_if_absent(self, user_id: str, state: IdentityState) -> IdentityState: ...
    def upsert(self, user_id: str, state: IdentityState) -> None: ...
    def append_signal(self, user_id: str, signal: Signal) -> None: ...
    # v0.2 extension: atomic signal + optional profile snapshot, guarded against
    # concurrent stale revisions. Historical signal data remains authoritative.
    def apply_signal(
        self, user_id: str, signal: Signal, state: IdentityState | None = None,
        expected_revision: int | None = None,
        *, scoped_preferences: list[ScopedPreference] | None = None,
    ) -> None: ...
    def list_scoped_preferences(
        self, user_id: str, *, project_id: str | None = None,
        session_id: str | None = None, turn_id: str | None = None,
    ) -> list[ScopedPreference]: ...
    def history(self, user_id: str, limit: int) -> list[IdentitySnapshot]: ...
    # Engineering extension: ADR-0009 has no enumeration method. Rebuild requires
    # the authoritative documents, including their stable ids and user ownership.
    def iter_documents(self) -> Iterable[MemoryDocument]: ...


@runtime_checkable
class MemoryIndex(Protocol):
    def index(self, doc_id: str, text: str, metadata: dict) -> None: ...
    def query(self, text: str, k: int, filters: dict | None = None) -> list[Hit]: ...
    def rebuild_from(self, source: IdentityStore) -> None: ...
    def drop(self) -> None: ...


@runtime_checkable
class DecisionLog(Protocol):
    def append(self, record: DecisionRecord) -> None: ...
    def export(self, run_id: str) -> Iterable[DecisionRecord]: ...


class ConcurrentIdentityUpdate(RuntimeError):
    """A stale profile update was refused; the caller must explicitly resubmit."""

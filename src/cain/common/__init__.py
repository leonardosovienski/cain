"""Backend-independent contracts for the Cain research prototype."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Message:
    intent: str
    contexto_identidade: str
    payload: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PersonalityState:
    """STUB — ADR-0006: stable defaults, not a validated identity model."""

    tone: str = "direto, respeitoso, honesto"
    error_style: str = "explicar a limitação e indicar um próximo passo"
    principles: tuple[str, ...] = ("não inventar fatos", "distinguir dados de instruções")


@dataclass
class UserModel:
    preferences: dict[str, str] = field(default_factory=dict)
    expertise: str = ""
    recurring_goals: list[str] = field(default_factory=list)
    # Current provenance also keeps removal tombstones. Old JSON rows omit this
    # field and receive its default during deserialization.
    preference_provenance: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class IdentityState:
    user_id: str
    personality: PersonalityState = field(default_factory=PersonalityState)
    user_model: UserModel = field(default_factory=UserModel)
    revision: int = 0


@dataclass
class Signal:
    text: str
    kind: str = "interaction"
    metadata: dict[str, Any] = field(default_factory=dict)
    signal_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class ScopedPreference:
    """One current value/tombstone at a precise preference location."""

    user_id: str
    scope: str
    key: str
    value: str | None
    action: str
    project_id: str | None = None
    session_id: str | None = None
    turn_id: str | None = None
    expires_at: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IdentitySnapshot:
    state: IdentityState
    recorded_at: str


@dataclass(frozen=True)
class MemoryDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Hit:
    doc_id: str
    text: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    run_id: str
    user_id: str
    session_id: str
    selected_agent: str
    intent: str
    reason: str
    status: str
    steps: tuple[str, ...]
    created_at: str = field(default_factory=utc_now)
    response_hash: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    response: str
    selected_agent: str
    decision_id: str
    steps: list[str]
    run_id: str


class CainRunError(RuntimeError):
    """A failed request was audited; no retry or provider fallback occurred."""

    def __init__(self, message: str, decision_id: str):
        super().__init__(message)
        self.decision_id = decision_id

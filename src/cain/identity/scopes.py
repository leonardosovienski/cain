"""Scope addressing and UTC expiration validation, independent of storage."""

from datetime import datetime, timezone

from .explicit import PREFERENCE_SCOPES


def validate_context(
    *, project_id: str | None = None, session_id: str | None = None, turn_id: str | None = None,
) -> dict[str, str | None]:
    context = {"project_id": project_id, "session_id": session_id, "turn_id": turn_id}
    for name, value in context.items():
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 200):
            raise ValueError(f"{name} must be a non-empty string of at most 200 characters")
    if turn_id is not None and session_id is None:
        raise ValueError("turn_id requires session_id")
    return context


def location(scope: str, context: dict) -> dict[str, str | None]:
    if scope not in PREFERENCE_SCOPES:
        raise ValueError(f"Unknown preference scope: {scope}; choose {', '.join(PREFERENCE_SCOPES)}")
    if scope == "project" and context["project_id"] is None:
        raise ValueError("Project preference requires project_id; it was not saved globally")
    if scope in {"session", "turn"} and context["session_id"] is None:
        raise ValueError(f"{scope} preference requires session_id; it was not saved globally")
    if scope == "turn" and context["turn_id"] is None:
        raise ValueError("Turn preference requires turn_id; it was not saved globally")
    return {
        "project_id": context["project_id"] if scope != "user" else None,
        "session_id": context["session_id"] if scope in {"session", "turn"} else None,
        "turn_id": context["turn_id"] if scope == "turn" else None,
    }


def as_utc(value: datetime | str, *, field: str = "expires_at") -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{field} must be an ISO 8601 timestamp with timezone") from error
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include an explicit timezone")
    return value.astimezone(timezone.utc)


def expiration(value: datetime | str | None, now: datetime) -> str | None:
    if value is None:
        return None
    expires = as_utc(value)
    if expires <= now:
        raise ValueError("expires_at must be in the future")
    return expires.isoformat()

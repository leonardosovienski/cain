"""Versioned policy files: thresholds are data, never constants spread through the code.

The rule of the prompt series ("Regra sobre os limiares"):

* a threshold is a policy value, kept in a versioned file;
* every decision records which policy produced it (id, version, sha256);
* changing a threshold needs a recorded human approval and applies only to what is registered
  after the change.

Here a policy is a JSON file in a package's ``data`` directory. The first version is ``<stem>.json``;
a change is a **new** file ``<stem>-v<N>.json`` with ``version = N`` and ``effective_from`` (UTC). It
reaches the code only through a pull request, and the owner's merge is the recorded human approval
(the repository rule: "aprovar = o dono fazer merge"). ``effective(at)`` returns the version in force
at the instant the decided object was registered, so an object registered earlier keeps the policy it
was registered under.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from importlib.resources import files
import json


class PolicyError(ValueError):
    pass


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PolicyError(f"policy instant without a time zone: {value!r}")
    return parsed.astimezone(timezone.utc)


def versions(package: str, stem: str) -> list[dict]:
    """Every version of a policy, oldest first, each with its file name and sha256."""
    found = []
    for entry in files(package).joinpath("data").iterdir():
        name = entry.name
        if name == f"{stem}.json" or (name.startswith(f"{stem}-v") and name.endswith(".json")):
            raw = entry.read_bytes()
            value = json.loads(raw)
            found.append({**value, "sha256": sha256(raw).hexdigest(), "file": name})
    if not found:
        raise PolicyError(f"no policy {stem!r} in {package}")
    found.sort(key=lambda v: v.get("version", 0))
    numbers = [v.get("version") for v in found]
    if numbers != list(range(1, len(found) + 1)):
        raise PolicyError(f"policy {stem!r} versions must be 1..N without gaps, got {numbers}")
    starts = [_instant(v["effective_from"]) for v in found[1:] if "effective_from" in v]
    if len(starts) != len(found) - 1 or starts != sorted(starts):
        raise PolicyError(f"policy {stem!r}: every version after the first needs an increasing effective_from")
    return found


def effective(found: list[dict], at: str | None = None) -> dict:
    """The version in force at ``at`` (the latest one when ``at`` is None)."""
    if at is None:
        return found[-1]
    moment, chosen = _instant(at), found[0]
    for version in found[1:]:
        if _instant(version["effective_from"]) <= moment:
            chosen = version
    return chosen


def ref(policy: dict) -> dict:
    """What a decision records about the policy that produced it."""
    return {"policy": policy["policy"], "version": policy["version"], "sha256": policy["sha256"]}

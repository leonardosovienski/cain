"""Fail-closed policy boundary for CAIN result context egress."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path


_CREDENTIAL_NAMES = (
    r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|secret[_-]?access[_-]?key|"
    r"aws[_-]?secret[_-]?access[_-]?key|(?:auth|bearer|refresh|session)[_-]?token|"
    r"password|passwd)"
)
# Second line of defence behind field redaction. Each pattern targets a credential *shape*;
# prose that merely mentions a provider or a word like "password" must not match.
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    # name=value / name: value assignments in text
    re.compile(r"\b" + _CREDENTIAL_NAMES + r"\s*[:=]\s*\S+", re.I),
    # the same names as JSON object keys with a non-empty string value
    re.compile(r'"' + _CREDENTIAL_NAMES + r'"\s*:\s*"[^"]+"', re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),  # JWT
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),  # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b"),  # GitHub
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),  # Slack
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),  # Google API key
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),  # Authorization header value
    re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s@/]+@"),  # scheme://user:password@host
)


class ResultEgressPolicy:
    """Operator-owned, reloadable allowlist for result-aware provider context."""

    def __init__(self, policy: dict | str | Path):
        self.source = Path(policy).resolve() if isinstance(policy, (str, Path)) else None
        self.static = deepcopy(policy) if isinstance(policy, dict) else None
        self.load()

    @classmethod
    def local_only(cls):
        return cls({
            "schema_version": "CAINResultEgressPolicyV1",
            "policy_id": "cain-local-result-egress",
            "policy_version": 1,
            "owner": "CAIN_OPERATOR",
            "providers": [{
                "provider_id": "local",
                "base_urls": ["local", "http://127.0.0.1", "http://localhost"],
                "classifications": ["INTERNAL_RESEARCH"],
                "scopes": ["*"],
            }],
            "local_only_classifications": ["INTERNAL_RESEARCH", "RESTRICTED"],
            "redact_fields": ["artifacts", "raw", "secret", "credentials"],
            "secret_handling": "DENY",
            "max_context_bytes": 65536,
        })

    def load(self):
        value = (
            json.loads(self.source.read_text(encoding="utf-8"))
            if self.source is not None
            else deepcopy(self.static)
        )
        expected = {
            "schema_version", "policy_id", "policy_version", "owner", "providers",
            "local_only_classifications", "redact_fields", "secret_handling", "max_context_bytes",
        }
        if type(value) is not dict or set(value) != expected:
            raise ValueError("invalid result egress policy fields")
        if value["schema_version"] != "CAINResultEgressPolicyV1" or value["owner"] != "CAIN_OPERATOR":
            raise ValueError("invalid result egress policy authority")
        if type(value["policy_version"]) is not int or value["policy_version"] < 1:
            raise ValueError("invalid result egress policy version")
        if value["secret_handling"] != "DENY":
            raise ValueError("result egress secret handling must fail closed")
        if type(value["max_context_bytes"]) is not int or not 1024 <= value["max_context_bytes"] <= 1_000_000:
            raise ValueError("invalid result egress context limit")
        if type(value["providers"]) is not list or not value["providers"]:
            raise ValueError("result egress requires provider allowlist")
        seen = set()
        for provider in value["providers"]:
            if type(provider) is not dict or set(provider) != {
                "provider_id", "base_urls", "classifications", "scopes"
            }:
                raise ValueError("invalid result egress provider")
            if provider["provider_id"] in seen:
                raise ValueError("duplicate result egress provider")
            seen.add(provider["provider_id"])
            for field in ("base_urls", "classifications", "scopes"):
                if type(provider[field]) is not list or not provider[field] or not all(
                    type(item) is str and item for item in provider[field]
                ):
                    raise ValueError(f"invalid provider {field}")
        for field in ("local_only_classifications", "redact_fields"):
            if type(value[field]) is not list or not all(type(item) is str and item for item in value[field]):
                raise ValueError(f"invalid result egress {field}")
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        self.value = value
        self.policy_hash = hashlib.sha256(encoded).hexdigest()
        return value

    @staticmethod
    def _redact(value, fields, redactions):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in fields:
                    redactions.append(key)
                    continue
                result[key] = ResultEgressPolicy._redact(item, fields, redactions)
            return result
        if isinstance(value, list):
            return [ResultEgressPolicy._redact(item, fields, redactions) for item in value]
        return value

    def prepare(self, provider, classification: str, scope: str, payload: dict) -> tuple[dict, dict]:
        policy = self.load()
        provider_id = getattr(provider, "provider_id", None)
        base_url = getattr(provider, "base_url", None) or "local"
        selected = next((item for item in policy["providers"] if item["provider_id"] == provider_id), None)
        if selected is None or base_url not in selected["base_urls"]:
            raise PermissionError("EGRESS_DENIED: provider is not allowlisted")
        if classification not in selected["classifications"]:
            raise PermissionError("EGRESS_DENIED: data classification is not allowed")
        if "*" not in selected["scopes"] and scope not in selected["scopes"]:
            raise PermissionError("EGRESS_DENIED: research scope is not allowed")
        is_local = base_url in {"local", "http://127.0.0.1", "http://localhost"}
        if classification in policy["local_only_classifications"] and not is_local:
            raise PermissionError("EGRESS_DENIED: classification is local-only")
        redactions = []
        sanitized = self._redact(payload, set(policy["redact_fields"]), redactions)
        encoded = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > policy["max_context_bytes"]:
            raise PermissionError("EGRESS_DENIED: context exceeds policy limit")
        if any(pattern.search(encoded) for pattern in _SECRET_PATTERNS):
            raise PermissionError("EGRESS_DENIED: secret-like value detected")
        return sanitized, {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "policy_hash": self.policy_hash,
            "owner": policy["owner"],
            "provider_id": provider_id,
            "base_url": base_url,
            "classification": classification,
            "scope": scope,
            "redacted_fields": sorted(set(redactions)),
            "authorization_result": "AUTHORIZED",
        }


__all__ = ["ResultEgressPolicy"]

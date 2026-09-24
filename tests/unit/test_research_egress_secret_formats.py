"""Secret detection at the research egress boundary.

Protected behaviour: ``ResultEgressPolicy.prepare`` denies a payload that carries a
secret in any of the formats the policy recognises (PEM private keys, ``api_key`` /
``access_token`` / ``client_secret`` assignments, ``sk-`` tokens), wherever the value
sits in the payload; it keeps benign research text flowing; field redaction happens
before the scan; and policy documents that weaken these guarantees are refused.

Formats the current patterns do not recognise are listed as strict ``xfail`` cases:
they document the gap without changing behaviour, and fail loudly when it closes.
"""
import pytest

from cain.research_egress import ResultEgressPolicy


class Local:
    provider_id = "local"
    base_url = "local"


def prepare(payload, policy=None):
    return (policy or ResultEgressPolicy.local_only()).prepare(
        Local(), "INTERNAL_RESEARCH", "leo/crypto", payload)


def deny(payload):
    with pytest.raises(PermissionError, match="secret-like"):
        prepare(payload)


DETECTED = {
    "pem-plain": "-----BEGIN PRIVATE KEY-----\nMIIE...",
    "pem-rsa": "-----BEGIN RSA PRIVATE KEY-----",
    "pem-ec": "-----BEGIN EC PRIVATE KEY-----",
    "pem-openssh": "-----BEGIN OPENSSH PRIVATE KEY-----",
    "api_key-equals": "api_key=abcdef123456",
    "api-key-colon": "api-key: abcdef123456",
    "apikey-upper-spaces": "APIKEY = ABCDEF123456",
    "access_token": "access_token=ya29.a0AfH6SMB",
    "access-token-colon": "Access-Token: 0123456789abcdef",
    "client_secret": "client_secret=xyz-987",
    "openai-sk": "sk-abcdefghijklmnopqrstuvwxyz",
    "anthropic-sk-ant": "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789",
    "embedded-in-prose": "Use api_key=abc123 when calling the exporter.",
}

NOT_YET_DETECTED = {
    "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    # Provider-shaped samples are assembled at runtime so the source never carries a literal
    # that GitHub push protection would treat as a real credential.
    "aws-access-key-id": "AKIA" + "IOSFODNN7EXAMPLE",
    "aws-secret-assignment": "aws_secret_access_key=" + "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "github-token": "ghp_" + "16C7e42F292c6912E7710c838347Ae178B4a",
    "slack-token": "xoxb-" + "-".join(["123456789012", "1234567890123", "AbCdEfGhIjKlMnOpQrStUvWx"]),
    "google-api-key": "AIzaSyA-1234567890abcdefghijklmnopqrstuv",
    "bearer-header": "Authorization: Bearer abcdef0123456789abcdef0123456789",
    "password-assignment": "password=hunter2",
    "connection-string-with-password": "postgres://user:s3cret@db.internal:5432/research",
    "json-key-named-api_key": {"api_key": "abcdef123456"},
}

BENIGN = {
    "sha256-hex": "sha256: 45bb7ea3d503d5f943f2e5edfdaf8937fcea4fc17e12251c250148e37b873d6f",
    "uuid": "run 3f2504e0-4f89-11d3-9a0c-0305e82c3301 completed",
    "word-key-in-prose": "the key finding is that liquidity fell; access to data was restricted",
    "short-sk": "sk-short",
    "pem-mention-without-header": "the report mentions a PEM certificate, no key material",
    "sk-inside-word": "risk-adjusted returns (task-based)",
}


@pytest.mark.parametrize("value", list(DETECTED.values()), ids=list(DETECTED))
def test_recognised_secret_formats_are_denied(value):
    deny({"results": [{"summary": value}]})


@pytest.mark.parametrize("value", list(DETECTED.values())[:3] + [DETECTED["api_key-equals"]],
                         ids=["pem-plain", "pem-rsa", "pem-ec", "api_key"])
def test_secrets_are_found_at_any_depth(value):
    deny({"a": [{"b": {"c": [value]}}]})
    deny({value: "value used as a key"})


@pytest.mark.parametrize("value", list(BENIGN.values()), ids=list(BENIGN))
def test_benign_research_text_is_allowed(value):
    sanitized, receipt = prepare({"results": [{"summary": value}]})
    assert sanitized == {"results": [{"summary": value}]}
    assert receipt["authorization_result"] == "AUTHORIZED" and receipt["redacted_fields"] == []


@pytest.mark.parametrize("value", list(NOT_YET_DETECTED.values()), ids=list(NOT_YET_DETECTED))
@pytest.mark.xfail(strict=True, reason="known gap: format not covered by _SECRET_PATTERNS; "
                                       "field redaction remains the primary defence")
def test_formats_not_yet_recognised(value):
    deny({"results": [{"summary": value}]})


def test_redacted_fields_are_removed_before_the_secret_scan():
    payload = {"results": [{"summary": "public text", "credentials": DETECTED["pem-rsa"],
                            "raw": {"api_key": "x", "note": DETECTED["api_key-equals"]}}]}
    sanitized, receipt = prepare(payload)
    assert sanitized == {"results": [{"summary": "public text"}]}
    assert receipt["redacted_fields"] == ["credentials", "raw"]
    assert payload["results"][0]["credentials"] == DETECTED["pem-rsa"], "caller's payload is untouched"


def test_context_limit_is_enforced_after_redaction():
    policy = ResultEgressPolicy({**ResultEgressPolicy.local_only().load(), "max_context_bytes": 1024})
    sanitized, _ = prepare({"summary": "short", "raw": "x" * 5000}, policy)
    assert sanitized == {"summary": "short"}
    with pytest.raises(PermissionError, match="exceeds policy limit"):
        prepare({"summary": "y" * 1024}, policy)


@pytest.mark.parametrize("mutation, message", [
    ({"secret_handling": "ALLOW"}, "fail closed"),
    ({"providers": []}, "provider allowlist"),
    ({"owner": "SOMEONE_ELSE"}, "authority"),
    ({"schema_version": "CAINResultEgressPolicyV2"}, "authority"),
    ({"policy_version": 0}, "policy"),
    ({"max_context_bytes": "65536"}, "context limit"),
    ({"max_context_bytes": 512}, "context limit"),
    ({"redact_fields": "artifacts"}, "redact_fields"),
    ({"extra": True}, "fields"),
])
def test_policies_that_weaken_the_boundary_are_refused(mutation, message):
    base = ResultEgressPolicy.local_only().load()
    with pytest.raises(ValueError, match=message):
        ResultEgressPolicy({**base, **mutation})

"""Secret detection at the research egress boundary.

Protected behaviour: ``ResultEgressPolicy.prepare`` denies a payload that carries a
secret in any of the formats the policy recognises (PEM private keys, ``api_key`` /
``access_token`` / ``client_secret`` assignments, ``sk-`` tokens), wherever the value
sits in the payload; it keeps benign research text flowing; field redaction happens
before the scan; and policy documents that weaken these guarantees are refused.

Provider-shaped credentials (JWT, AWS, GitHub, Slack, Google, bearer headers, password
assignments, connection strings with a password, JSON keys named like a credential) are
denied too, while benign research text that merely resembles them keeps flowing.
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

PROVIDER_SHAPED = {
    "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    # Provider-shaped samples are assembled at runtime so the source never carries a literal
    # that GitHub push protection would treat as a real credential.
    "aws-access-key-id": "AKIA" + "IOSFODNN7EXAMPLE",
    "aws-secret-assignment": "aws_secret_access_key=" + "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "github-token": "ghp_" + "16C7e42F292c6912E7710c838347Ae178B4a",
    "slack-token": "xoxb-" + "-".join(["123456789012", "1234567890123", "AbCdEfGhIjKlMnOpQrStUvWx"]),
    "google-api-key": "AIza" + "SyA-1234567890abcdefghijklmnopqrstu",  # 4 + 35 chars, the real shape
    "bearer-header": "Authorization: Bearer abcdef0123456789abcdef0123456789",
    "password-assignment": "password=hunter2",
    "connection-string-with-password": "postgres://user:s3cret@db.internal:5432/research",
    "json-key-named-api_key": {"api_key": "abcdef123456"},
    "json-key-named-password": {"db": {"password": "hunter2"}},
    "github-fine-grained": "github_pat_" + "11ABCDEFG0" + "abcdefghijklmnopqrstuvwxyz0123456789",
    "aws-temporary-key": "ASIA" + "IOSFODNN7EXAMPLE",
    "refresh-token-assignment": "refresh_token: 1//0abcdefghij-klmnop",
    "mysql-url-with-password": "mysql://root:pw@db:3306/x",
}

BENIGN = {
    "sha256-hex": "sha256: 45bb7ea3d503d5f943f2e5edfdaf8937fcea4fc17e12251c250148e37b873d6f",
    "uuid": "run 3f2504e0-4f89-11d3-9a0c-0305e82c3301 completed",
    "word-key-in-prose": "the key finding is that liquidity fell; access to data was restricted",
    "short-sk": "sk-short",
    "pem-mention-without-header": "the report mentions a PEM certificate, no key material",
    "sk-inside-word": "risk-adjusted returns (task-based)",
    "jwt-like-but-short": "eyJhbGciOiJ.eyJzdWIi.sig",
    "akia-lowercase-tail": "AKIAexampleNotAKey123",
    "bearer-in-prose": "the bearer of this letter is the holder of the claim",
    "url-without-password": "https://example.com/data/2026/report.json",
    "url-with-user-only": "ssh://git@github.com/org/repo.git",
    "token-count-metric": "token_count: 1200 and tokens: 12 per row",
    "password-policy-prose": "password policy requires 12 characters and rotation",
    "json-key-named-token-count": {"token_count": 12, "api_keys_rotated": 3},
    "ghost-word": "ghp_ prefixes are documented in the GitHub API reference",
    "slack-mention": "xoxb tokens are described in the Slack docs",
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


@pytest.mark.parametrize("value", list(PROVIDER_SHAPED.values()), ids=list(PROVIDER_SHAPED))
def test_provider_shaped_credentials_are_denied(value):
    deny({"results": [{"summary": value}]})
    deny({"nested": [{"deeper": value}]})


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

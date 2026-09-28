"""Domain configuration of the DecisionPolicy: what exists in one domain (versioned, hashed)."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files

from research_protocol import v2

from cain.orchestration import policy

SCHEMA = "cain-domain-config/1"
KEYS = frozenset(
    {
        "schema", "domain", "config_version", "source", "contract", "frozen_parameters", "allowed_request_types",
        "closed_hypotheses", "frozen_families", "proposable_hypotheses", "allowed_symbols", "costs",
        "allowed_references", "max_priority_hint", "budget", "cooldown", "negative_result_states",
        "contradiction_pairs", "sealed_scopes", "proposable_request_types",
    }
)
# optional: absent means empty, so a domain without it keeps the same bytes (crypto.json and brasileirao.json of rc10)
OPTIONAL_KEYS = frozenset({"proposal_overlays"})
# parameters an overlay never sets: the costs are the frozen configuration's, the placebo seed is the CAIN's
NOT_OVERLAID = frozenset({"fee_bps", "slippage_bps", "placebo_seed"})
PRIORITIES = ("LOW", "NORMAL", "HIGH")


class ConfigError(ValueError):
    code = "CONFIG_INVALID"


def load(domain: str) -> dict:
    """The packaged configuration of ``domain`` (fail closed on anything unexpected)."""
    if domain not in v2.DOMAINS:
        raise ConfigError(f"unknown domain {domain[:40]!r}")
    resource = files("cain.orchestration").joinpath("data", f"{domain}.json")
    if not resource.is_file():
        raise ConfigError(f"no orchestration configuration for domain {domain!r}")
    return validate(json.loads(resource.read_bytes()))


def validate(config: dict) -> dict:
    if not isinstance(config, dict) or not KEYS <= set(config) <= KEYS | OPTIONAL_KEYS or config["schema"] != SCHEMA:
        raise ConfigError("configuration fields differ from cain-domain-config/1")
    domain = config["domain"]
    if domain not in v2.DOMAINS:
        raise ConfigError("configuration of an unknown domain")
    if config["contract"]["request_schema_id"] != v2.REGISTRY["domains"][domain]["request_schema_id"]:
        raise ConfigError("configuration contract differs from the frozen envelope registry")
    for hypothesis in [*config["closed_hypotheses"], *config["proposable_hypotheses"]]:
        if not hypothesis.startswith(domain + ":"):
            raise ConfigError("hypothesis ID without the domain prefix (C18)")
    if set(config["closed_hypotheses"]) & set(config["proposable_hypotheses"]):
        raise ConfigError("a closed hypothesis cannot be proposable")
    if config["max_priority_hint"] not in PRIORITIES:
        raise ConfigError("unknown priority cap")
    types = config["proposable_request_types"]
    if not isinstance(types, dict) or set(types) != set(config["proposable_hypotheses"]) or not set(
            types.values()) <= set(config["allowed_request_types"]):
        raise ConfigError("every proposable hypothesis needs exactly one allowed request type")
    overlays = config.get("proposal_overlays", {})
    if not isinstance(overlays, dict) or not set(overlays) <= set(config["proposable_hypotheses"]) or not all(
            isinstance(o, dict) and o and not set(o) & NOT_OVERLAID for o in overlays.values()):
        raise ConfigError("proposal_overlays: non-empty parameter objects of proposable hypotheses, never costs or "
                          "the placebo seed")
    try:
        policy.check_sealed_scopes(config["sealed_scopes"])
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    budget, cooldown = config["budget"], config["cooldown"]
    for value in (*budget.values(), *cooldown.values()):
        if type(value) is not int or value < 1:
            raise ConfigError("budget and cooldown values are positive integers")
    return config


def digest(config: dict) -> str:
    return hashlib.sha256(v2.canonical(config)).hexdigest()

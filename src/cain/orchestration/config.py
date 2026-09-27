"""Domain configuration of the DecisionPolicy: what exists in one domain (versioned, hashed)."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files

from research_protocol import v2

SCHEMA = "cain-domain-config/1"
KEYS = frozenset(
    {
        "schema", "domain", "config_version", "source", "contract", "frozen_parameters", "allowed_request_types",
        "closed_hypotheses", "frozen_families", "proposable_hypotheses", "allowed_symbols", "costs",
        "allowed_references", "max_priority_hint", "budget", "cooldown", "negative_result_states",
        "contradiction_pairs",
    }
)
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
    if not isinstance(config, dict) or set(config) != KEYS or config["schema"] != SCHEMA:
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
    budget, cooldown = config["budget"], config["cooldown"]
    for value in (*budget.values(), *cooldown.values()):
        if type(value) is not int or value < 1:
            raise ConfigError("budget and cooldown values are positive integers")
    return config


def digest(config: dict) -> str:
    return hashlib.sha256(v2.canonical(config)).hexdigest()

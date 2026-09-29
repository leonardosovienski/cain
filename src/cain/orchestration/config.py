"""Domain configuration of the DecisionPolicy: what exists in one domain (versioned, hashed)."""

from __future__ import annotations

import hashlib
import json
import math
import re
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
OPTIONAL_KEYS = frozenset({"proposal_overlays", "result_metrics"})
# parameters an overlay never sets: the costs are the frozen configuration's, the placebo seed is the CAIN's
NOT_OVERLAID = frozenset({"fee_bps", "slippage_bps", "placebo_seed"})
PRIORITIES = ("LOW", "NORMAL", "HIGH")
# result_metrics: name -> dotted path in the domain's result payload; only numbers are ever read through it
METRIC_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
METRIC_PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}(\.[A-Za-z_][A-Za-z0-9_]{0,63}){0,7}\Z")
MAX_METRICS = 16


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
    metrics = config.get("result_metrics", {})
    if not isinstance(metrics, dict) or len(metrics) > MAX_METRICS or not all(
            isinstance(n, str) and METRIC_NAME.fullmatch(n) and isinstance(p, str) and METRIC_PATH.fullmatch(p)
            for n, p in metrics.items()):
        raise ConfigError(f"result_metrics: up to {MAX_METRICS} lowercase names mapped to dotted paths of the result "
                          "payload")
    try:
        policy.check_sealed_scopes(config["sealed_scopes"])
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    budget, cooldown = config["budget"], config["cooldown"]
    for value in (*budget.values(), *cooldown.values()):
        if type(value) is not int or value < 1:
            raise ConfigError("budget and cooldown values are positive integers")
    return config


def result_metrics(config: dict, payload: dict) -> dict:
    """The numbers of a domain result that the configuration declares (``result_metrics``: name -> dotted path in the
    result payload). Only finite ints and floats are kept (never text, lists or objects: the memory keeps no free
    text, FUTURE_CANARY); a path that is missing or not a number is left out. Without the key: nothing."""
    out = {}
    for name, path in sorted(config.get("result_metrics", {}).items()):
        value: object = payload
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            out[name] = value
    return out


def digest(config: dict) -> str:
    return hashlib.sha256(v2.canonical(config)).hexdigest()

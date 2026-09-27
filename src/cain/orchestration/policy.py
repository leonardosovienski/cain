"""Generic DecisionPolicy: deterministic, versioned, no LLM, no clock (C9, C12).

``decide(proposal, view, config, episode_number=…)`` returns one of ALLOW | BLOCK | ABSTAIN | REQUIRE_HUMAN |
DUPLICATE | COOLDOWN with a stable reason code and the rule that fired. The inputs are the canonical proposal, the
domain configuration (``config.py``) and the domain view built from the CAIN's own state at an ``as_of`` (tasks it
emitted, results retrieved from the domain's memory cube). The receipt is canonical JSON that names the policy (id,
version, sha256 of this file) and the configuration (sha256): the same proposal, policy and state give the same
bytes in any process.

Rules, first match wins (FROZEN_PARAMETERS.json → decision_policy.rule_order):
  R01 BLOCK DOMAIN_MISMATCH          proposal, request or evidence ID of another domain, or ID without domain (C18)
  R02 BLOCK SCHEMA_INVALID           proposal shape or contract request invalid (frozen envelope validator)
  R03 BLOCK FORBIDDEN_FIELD          field outside cain-proposal/1 (handler, command, module, path, URL, budget,
                                     final priority, capital …) or a client_ref the envelope owns
  R04 BLOCK REQUEST_TYPE_NOT_ALLOWED request_type outside the contract's handler_allowlist keys
  R05 BLOCK HYPOTHESIS_CLOSED        closed hypothesis of the domain's scientific state, or frozen family
  R06 BLOCK SYMBOL_NOT_ALLOWED / COST_MODEL_MISMATCH / REFERENCE_NOT_ALLOWED / PRIORITY_ABOVE_CAP
  R07 BLOCK REQUEST_ID_CONFLICT      request_id already emitted with other content
  R08 DUPLICATE                      same request content already emitted in the domain
  R09 REQUIRE_HUMAN DOMAIN_RECONCILIATION_PENDING   a REQUIRES_HUMAN outcome of the domain is unresolved
  R10 REQUIRE_HUMAN CONTRADICTION_UNRESOLVED        conflicting scientific states for the hypothesis (never
                                                    decided by majority)
  R11 REQUIRE_HUMAN NEW_HYPOTHESIS   hypothesis outside the configured proposable list
  R12 ABSTAIN OPEN_TASK_PENDING / BUDGET_EXHAUSTED
  R13 COOLDOWN NEGATIVE_STREAK       N negative results in a row for the hypothesis: K episodes without a new task
  R14 ALLOW

Nothing here reads an economic state as a signal, and no result can raise a budget, a priority or the scope:
budgets and caps are configuration constants (NEGATIVE_RESULT_NEUTRALITY). There is no capital path.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from research_protocol import v2

POLICY_ID = "cain-decision-policy"
POLICY_VERSION = 1
PROPOSAL_SCHEMA = "cain-proposal/1"
RECEIPT_SCHEMA = "cain-decision-receipt/1"
DECISIONS = ("ALLOW", "BLOCK", "ABSTAIN", "REQUIRE_HUMAN", "DUPLICATE", "COOLDOWN")
PROPOSAL_KEYS = frozenset(
    {"schema", "proposal_id", "domain", "request", "based_on", "rationale", "hypothesis_family", "source"}
)
REQUIRED_KEYS = frozenset({"schema", "proposal_id", "domain", "request"})
SOURCES = ("agenda", "operator", "llm")
PRIORITY_ORDER = {"LOW": 0, "NORMAL": 1, "HIGH": 2}
_PROPOSAL_ID = re.compile(r"cain:[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_AS_OF = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
TERMINAL = ("TERMINAL_RESULT", "TERMINAL_REFUSAL", "REQUIRES_HUMAN")


def code_sha256() -> str:
    """sha256 of this module's source: the policy identity recorded in every receipt."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def safe_digest(value) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raw = repr(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _qualified(value, domain: str) -> str | None:
    """None when ``value`` is an ID of ``domain``; otherwise why not."""
    if not isinstance(value, str) or ":" not in value:
        return "ID without domain"
    if not value.startswith(domain + ":"):
        return f"ID of domain {value.split(':', 1)[0][:20]!r}"
    return None


def _outcome(decision: str, reason: str, rule: str, detail: str = "") -> dict:
    return {"decision": decision, "reason_code": reason, "rule": rule, "detail": detail[:300]}


def _domain_check(proposal: dict, domain: str) -> dict | None:
    if proposal.get("domain") != domain:
        return _outcome("BLOCK", "DOMAIN_MISMATCH", "R01", f"proposal domain {str(proposal.get('domain'))[:20]!r}")
    request = proposal.get("request")
    if isinstance(request, dict):
        for field in ("request_id", "research_id", "hypothesis_id"):
            if field in request and (why := _qualified(request[field], domain)):
                return _outcome("BLOCK", "DOMAIN_MISMATCH", "R01", f"request.{field}: {why}")
    for item in proposal.get("based_on") or []:
        if why := _qualified(item, domain):
            return _outcome("BLOCK", "DOMAIN_MISMATCH", "R01", f"based_on: {why}")
    return None


def _shape_check(proposal: dict) -> dict | None:
    missing = REQUIRED_KEYS - set(proposal)
    if missing or proposal.get("schema") != PROPOSAL_SCHEMA:
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", f"missing {sorted(missing)} or schema")
    if not isinstance(proposal["proposal_id"], str) or not _PROPOSAL_ID.fullmatch(proposal["proposal_id"]):
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "proposal_id must be cain:<id>")
    if not isinstance(proposal["request"], dict):
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "request must be an object")
    based_on = proposal.get("based_on", [])
    if not isinstance(based_on, list) or len(based_on) > v2.MAX_BASED_ON or len(set(map(str, based_on))) != len(based_on):
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "based_on must be a list of distinct IDs")
    if not isinstance(proposal.get("rationale", ""), str) or len(proposal.get("rationale", "")) > 2000:
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "rationale must be text up to 2000 characters")
    if proposal.get("source", "operator") not in SOURCES:
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "unknown proposal source")
    family = proposal.get("hypothesis_family")
    if family is not None and (not isinstance(family, str) or not 0 < len(family) <= 128):
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "hypothesis_family must be short text")
    return None


def decide(proposal, view: dict, config: dict, *, episode_number: int) -> dict:
    domain = config["domain"]
    if not isinstance(proposal, dict):
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", "proposal must be an object")
    if blocked := _domain_check(proposal, domain):
        return blocked
    if blocked := _shape_check(proposal):
        return blocked
    extra = sorted(set(proposal) - PROPOSAL_KEYS)
    if extra:
        return _outcome("BLOCK", "FORBIDDEN_FIELD", "R03", f"fields outside {PROPOSAL_SCHEMA}: {extra}"[:300])
    request = proposal["request"]
    try:
        probe = v2.build_task(domain, request, episode_id=v2.episode_id_for(domain, episode_number),
                              proposal_id=proposal["proposal_id"], created_at="2000-01-01T00:00:00Z",
                              based_on=proposal.get("based_on", []))
    except v2.V2Error as exc:
        if exc.code in ("DOMAIN_MISMATCH", "ID_NOT_QUALIFIED"):
            return _outcome("BLOCK", "DOMAIN_MISMATCH", "R01", str(exc))
        if exc.code == "CLIENT_REF_RESERVED":
            return _outcome("BLOCK", "FORBIDDEN_FIELD", "R03", "client_ref is owned by the envelope")
        return _outcome("BLOCK", "SCHEMA_INVALID", "R02", str(exc))
    if request["request_type"] not in config["allowed_request_types"]:
        return _outcome("BLOCK", "REQUEST_TYPE_NOT_ALLOWED", "R04", request["request_type"][:60])
    hypothesis = request["hypothesis_id"]
    if hypothesis in config["closed_hypotheses"]:
        return _outcome("BLOCK", "HYPOTHESIS_CLOSED", "R05",
                        f"{hypothesis} is {config['closed_hypotheses'][hypothesis]} and is never reopened")
    if proposal.get("hypothesis_family") in config["frozen_families"]:
        return _outcome("BLOCK", "HYPOTHESIS_CLOSED", "R05", f"frozen family {proposal['hypothesis_family']}")
    params = request.get("parameters", {})
    if "symbol" in params and params["symbol"] not in config["allowed_symbols"]:
        return _outcome("BLOCK", "SYMBOL_NOT_ALLOWED", "R06", str(params["symbol"])[:20])
    costs = config["costs"]
    if any(params.get(key) != value for key, value in costs.items()):
        return _outcome("BLOCK", "COST_MODEL_MISMATCH", "R06", f"costs must be the frozen {costs}")
    for kind, ref in sorted(request.get("references", {}).items()):
        if f"{ref.get('name')} {ref.get('version')}" not in config["allowed_references"].get(kind, []):
            return _outcome("BLOCK", "REFERENCE_NOT_ALLOWED", "R06", f"{kind} {ref.get('name')} {ref.get('version')}")
    if PRIORITY_ORDER[request["priority_hint"]] > PRIORITY_ORDER[config["max_priority_hint"]]:
        return _outcome("BLOCK", "PRIORITY_ABOVE_CAP", "R06", request["priority_hint"])
    content = probe["payload_sha256"]
    tasks = view["tasks"]
    if any(t["request_id"] == request["request_id"] and t["payload_sha256"] != content for t in tasks):
        return _outcome("BLOCK", "REQUEST_ID_CONFLICT", "R07", request["request_id"][:140])
    same = [t for t in tasks if t["payload_sha256"] == content]
    if same:
        return _outcome("DUPLICATE", "DUPLICATE_REQUEST", "R08", f"already emitted as {same[0]['task_id']}")
    if view["requires_human"]:
        return _outcome("REQUIRE_HUMAN", "DOMAIN_RECONCILIATION_PENDING", "R09",
                        f"unresolved: {view['requires_human'][:3]}")
    states = {r["scientific_state"] for r in view["results"]
              if r["hypothesis_id"] == hypothesis and r["class"] == "TERMINAL_RESULT"}
    for pair in config["contradiction_pairs"]:
        if set(pair) <= states:
            return _outcome("REQUIRE_HUMAN", "CONTRADICTION_UNRESOLVED", "R10",
                            f"{hypothesis} has {sorted(states)}; a human decides, never a majority")
    if hypothesis not in config["proposable_hypotheses"]:
        return _outcome("REQUIRE_HUMAN", "NEW_HYPOTHESIS", "R11", f"{hypothesis} needs the owner")
    budget = config["budget"]
    if len(view["open_task_ids"]) >= budget["max_open_tasks"]:
        return _outcome("ABSTAIN", "OPEN_TASK_PENDING", "R12", f"open: {view['open_task_ids'][:3]}")
    if len(tasks) >= budget["max_tasks_total"] or sum(
        1 for t in tasks if t["research_id"] == request["research_id"]
    ) >= budget["max_tasks_per_research"]:
        return _outcome("ABSTAIN", "BUDGET_EXHAUSTED", "R12", "frozen task budget reached")
    cooldown = config["cooldown"]
    own = [r for r in view["results"] if r["hypothesis_id"] == hypothesis and r["class"] == "TERMINAL_RESULT"]
    streak = own[-cooldown["after_consecutive_negative"]:]
    if len(streak) == cooldown["after_consecutive_negative"] and all(
        r["result_state"] in config["negative_result_states"] for r in streak
    ) and episode_number - streak[-1]["episode"] <= cooldown["episodes"]:
        return _outcome("COOLDOWN", "NEGATIVE_STREAK", "R13",
                        f"{len(streak)} negative results; next task of {hypothesis} after episode "
                        f"{streak[-1]['episode'] + cooldown['episodes']}")
    return _outcome("ALLOW", "ALLOWED", "R14")


def receipt(proposal, view: dict, config: dict, config_sha256: str, outcome: dict, *, episode_number: int,
            as_of: str, task: dict | None) -> dict:
    if not _AS_OF.fullmatch(as_of):
        raise ValueError("as_of must be UTC YYYY-MM-DDTHH:MM:SSZ")
    if outcome["decision"] not in DECISIONS:
        raise ValueError("unknown decision")
    return {
        "schema": RECEIPT_SCHEMA,
        "policy": {"id": POLICY_ID, "version": POLICY_VERSION, "code_sha256": code_sha256()},
        "config": {"domain": config["domain"], "config_version": config["config_version"], "sha256": config_sha256},
        "domain": config["domain"],
        "episode_id": v2.episode_id_for(config["domain"], episode_number),
        "as_of": as_of,
        "proposal": {"proposal_id": proposal.get("proposal_id") if isinstance(proposal, dict) else None,
                     "sha256": safe_digest(proposal)},
        "state": {"digest": safe_digest(view), "episodes": view["episodes"], "tasks": len(view["tasks"]),
                  "results": len(view["results"]), "open_tasks": len(view["open_task_ids"])},
        "decision": outcome["decision"],
        "reason_code": outcome["reason_code"],
        "rule": outcome["rule"],
        "detail": outcome["detail"],
        "task": None if task is None else {"task_id": task["task_id"], "payload_sha256": task["payload_sha256"],
                                           "previous_task_id": task["previous_task_id"]},
        "capital_permission": False,
    }


def dumps(receipt_value: dict) -> bytes:
    """Canonical receipt bytes (sorted keys, no whitespace, UTF-8; floats refused)."""
    return v2.canonical(receipt_value)

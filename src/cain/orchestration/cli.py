"""`cain research propose|decision-receipt|dispatch|retry|ingest|episodes`: orchestration of one domain.

    cain research propose          --domain D --state S --proposal FILE [--as-of T] [--source agenda|operator]
    cain research decision-receipt --domain D --state S --proposal FILE --as-of T   (read-only, no LLM; C9)
    cain research dispatch         --domain D --state S --spool DIR [--resend]
    cain research retry            --domain D --state S --spool DIR --task-id ID
    cain research ingest           --domain D --state S --spool DIR
    cain research episodes         --domain D --state S

``decision-receipt`` prints only the canonical receipt bytes (one line): the same proposal, policy, configuration and
state give the same bytes in a new process. The other commands print one JSON line per item. Exit code 0; 2 for a
refused input (proposal file, conflict, retry not allowed); 1 for a configuration error.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

COMMANDS = ("propose", "decision-receipt", "dispatch", "retry", "ingest", "episodes")
MAX_PROPOSAL_BYTES = 256 * 1024


def register(commands) -> None:
    for name in COMMANDS:
        cmd = commands.add_parser(name, help=f"orchestration: {name} (one domain, V2 envelope)")
        cmd.add_argument("--domain", required=True)
        cmd.add_argument("--state", type=Path, required=True)
        if name in ("propose", "decision-receipt"):
            cmd.add_argument("--proposal", type=Path, required=True)
            cmd.add_argument("--as-of", required=name == "decision-receipt")
        if name == "propose":
            cmd.add_argument("--source", choices=["agenda", "operator"], default="operator")
        if name in ("dispatch", "retry", "ingest"):
            cmd.add_argument("--spool", type=Path, required=True)
        if name == "dispatch":
            cmd.add_argument("--resend", action="store_true")
        if name == "retry":
            cmd.add_argument("--task-id", required=True)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _line(value) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")


def _proposal(path: Path):
    from research_protocol import v2

    raw = path.read_bytes()
    if len(raw) > MAX_PROPOSAL_BYTES:
        raise ValueError("PROPOSAL_TOO_LARGE")
    return v2.loads_strict(raw)


def execute(args) -> int:
    from research_protocol import v2
    from research_transport.spool import Spool, SpoolConflict

    from cain.orchestration import policy
    from cain.orchestration.config import ConfigError
    from cain.orchestration.service import OrchestrationError, Orchestrator

    try:
        orchestrator = Orchestrator(args.domain, args.state)
    except ConfigError as exc:
        _line({"error": exc.code, "detail": str(exc)})
        return 1
    cmd = args.research_command
    try:
        if cmd in ("propose", "decision-receipt"):
            proposal = _proposal(args.proposal)
            if cmd == "decision-receipt":
                result = orchestrator.decision_receipt(proposal, as_of=args.as_of)
                sys.stdout.buffer.write(policy.dumps(result["receipt"]) + b"\n")
                sys.stdout.flush()
                return 0
            result = orchestrator.propose(proposal, as_of=args.as_of or _now(), source=args.source)
            receipt = result["receipt"]
            _line({"status": result["status"], "episode_id": receipt["episode_id"], "decision": receipt["decision"],
                   "reason_code": receipt["reason_code"], "rule": receipt["rule"], "task": receipt["task"],
                   "receipt_sha256": result["receipt_sha256"]})
            return 0
        if cmd == "episodes":
            _line(orchestrator.episodes()[0])
            return 0
        spool = Spool(args.spool)
        if cmd == "dispatch":
            lines = orchestrator.dispatch(spool, resend=args.resend)
        elif cmd == "retry":
            lines = [orchestrator.retry(spool, args.task_id)]
        else:
            lines = orchestrator.ingest(spool)
        for line in lines:
            _line(line)
        return 2 if any(line.get("action") == "rejected" for line in lines) else 0
    except (OrchestrationError, v2.V2Error, SpoolConflict) as exc:
        _line({"error": getattr(exc, "code", type(exc).__name__), "detail": str(exc)[:300]})
        return 2
    except ValueError as exc:
        _line({"error": "INPUT_INVALID", "detail": str(exc)[:300]})
        return 2

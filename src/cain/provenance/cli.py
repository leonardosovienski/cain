"""`cain trace | why | impact | invalidate | relate`: typed provenance over the memory, the research
loop ledger and the workflow events."""

import os
from pathlib import Path

COMMANDS = ("trace", "why", "impact", "invalidate", "relate")


def _sources(command):
    command.add_argument("--loop-db", type=Path, help="research loop ledger (attempts, gates, model and tool calls)")
    command.add_argument("--workflow-db", type=Path, help="research state database (human approvals, forks)")


def register(sub):
    db = Path(os.getenv("CAIN_MEMORY_DB", "data/memory.db"))
    for name, helptext in (("trace", "Full ancestry of an object (what it depends on)"),
                           ("why", "Which evidence, runs, decisions and model/tool calls led to a decision"),
                           ("impact", "What falls if this object (e.g. an evidence) is invalidated")):
        command = sub.add_parser(name, help=helptext)
        command.add_argument("node")
        command.add_argument("--as-of", required=True)
        command.add_argument("--db", type=Path, default=db)
        _sources(command)
    invalidate = sub.add_parser("invalidate", help="Invalidate an object and flag every dependent for review")
    invalidate.add_argument("node")
    invalidate.add_argument("--by", required=True)
    invalidate.add_argument("--reason", required=True)
    invalidate.add_argument("--db", type=Path, default=db)
    _sources(invalidate)
    relate = sub.add_parser("relate", help="Record a typed relation between two objects (an event)")
    relate.add_argument("source")
    relate.add_argument("relation")
    relate.add_argument("target")
    relate.add_argument("--by", required=True)
    relate.add_argument("--note", default="")
    relate.add_argument("--db", type=Path, default=db)


def execute(args):
    from cain.memory.store import MemoryStore
    from cain.provenance.graph import ProvenanceGraph

    memory = MemoryStore(args.db)
    ledger = None
    if getattr(args, "loop_db", None) is not None:
        from cain.loop.ledger import LoopLedger

        ledger = LoopLedger(args.loop_db)
    graph = ProvenanceGraph(memory, loop_ledger=ledger, workflow_db=getattr(args, "workflow_db", None))
    if args.command == "relate":
        return graph.relate(args.source, args.relation, args.target, by=args.by, note=args.note)
    if args.command == "invalidate":
        return graph.invalidate(args.node, by=args.by, reason=args.reason)
    at = memory.now() if args.as_of == "now" else args.as_of
    return getattr(graph, args.command)(args.node, as_of=at)

"""`cain trace | why | impact | invalidate | relate`: typed provenance over the memory."""

import os
from pathlib import Path

COMMANDS = ("trace", "why", "impact", "invalidate", "relate")


def register(sub):
    db = Path(os.getenv("CAIN_MEMORY_DB", "data/memory.db"))
    for name, helptext in (("trace", "Full ancestry of an object (what it depends on)"),
                           ("why", "Which evidence and runs led to a decision"),
                           ("impact", "What falls if this object (e.g. an evidence) is invalidated")):
        command = sub.add_parser(name, help=helptext)
        command.add_argument("node")
        command.add_argument("--as-of", required=True)
        command.add_argument("--db", type=Path, default=db)
    invalidate = sub.add_parser("invalidate", help="Invalidate an object and flag every dependent for review")
    invalidate.add_argument("node")
    invalidate.add_argument("--by", required=True)
    invalidate.add_argument("--reason", required=True)
    invalidate.add_argument("--db", type=Path, default=db)
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
    graph = ProvenanceGraph(memory)
    if args.command == "relate":
        return graph.relate(args.source, args.relation, args.target, by=args.by, note=args.note)
    if args.command == "invalidate":
        return graph.invalidate(args.node, by=args.by, reason=args.reason)
    at = memory.now() if args.as_of == "now" else args.as_of
    return getattr(graph, args.command)(args.node, as_of=at)

"""`cain loop`: run the governed research loop of one predictor and read its ledger."""

import os
from pathlib import Path

from cain.loop.similarity import similarity_function  # noqa: F401 (re-exported)


def register(sub):
    loop = sub.add_parser("loop", help="Governed research loop over a predictor's frozen evaluator")
    loop.add_argument("--db", type=Path, default=Path(os.getenv("CAIN_LOOP_DB", "data/loop.db")))
    commands = loop.add_subparsers(dest="loop_command", required=True)
    run = commands.add_parser("run", help="Run until budget, stagnation or a human gate")
    run.add_argument("--predictor", required=True)
    run.add_argument("--world", type=Path, required=True)
    run.add_argument("--proposer", choices=["neighbor", "local-model"], default="neighbor")
    run.add_argument("--config", type=Path, help="cain.toml for the local model / embedding")
    run.add_argument("--loop-id")
    run.add_argument("--memory-db", type=Path, help="findings archive (Prompt 7): stop on a closed hypothesis")
    status = commands.add_parser("status", help="What a loop did, from its ledger events")
    status.add_argument("loop_id", nargs="?")
    decide = commands.add_parser("decide", help="Human decision on the pending gate of a loop")
    decide.add_argument("loop_id")
    decide.add_argument("--decision", required=True, choices=["APPROVE", "REJECT"])
    decide.add_argument("--by", required=True)
    decide.add_argument("--note", default="")
    holdout = commands.add_parser("holdout", help="Evaluate the approved candidate on the holdout (once)")
    holdout.add_argument("loop_id")
    holdout.add_argument("--world", type=Path, required=True)
    commands.add_parser("verify", help="Recompute the ledger hash chain")


def execute(args):
    from cain.loop.engine import ResearchLoop, decide_gate, run_holdout
    from cain.loop.ledger import LoopLedger
    from cain.loop.world import load_world

    ledger = LoopLedger(args.db)
    cmd = args.loop_command
    if cmd == "verify":
        return ledger.verify()
    if cmd == "status":
        if args.loop_id is None:
            return {"loops": [ledger.status(loop_id) | {"events": None} for loop_id in ledger.loops()]}
        return ledger.status(args.loop_id)
    if cmd == "decide":
        return decide_gate(ledger, args.loop_id, decision=args.decision, by=args.by, note=args.note)
    world = load_world(args.world)
    if cmd == "holdout":
        return run_holdout(world, ledger, args.loop_id)
    if world["world"]["predictor"] != args.predictor:
        raise ValueError(f"world file is for predictor {world['world']['predictor']!r}, not {args.predictor!r}")
    if args.proposer == "neighbor":
        from cain.loop.proposers import NeighborProposer

        proposer = NeighborProposer()
    else:
        from cain.loop.proposers import LocalModelProposer
        from cain.providers import configured_llm
        from cain.settings import load_settings

        proposer = LocalModelProposer(configured_llm(load_settings(args.config)))
    closed_check = None
    if args.memory_db is not None:
        from cain.findings.archive import FindingsArchive
        from cain.memory.store import MemoryStore

        archive = FindingsArchive(MemoryStore(args.memory_db))
        domain = world["world"]["predictor"]

        def closed_check(statement, identity):
            return archive.equivalent_closed(domain, statement, as_of=archive.memory.now(), identity=identity)
    # The novelty measure and threshold are the world's policy, not a command-line choice.
    return ResearchLoop(world, ledger, proposer, similarity=similarity_function(world["novelty"]["measure"],
                                                                            args.config),
                        closed_check=closed_check).run(loop_id=args.loop_id)

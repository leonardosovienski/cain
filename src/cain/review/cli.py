"""`cain review`: adversarial review of a draft hypothesis before its pre-registration."""

import json
import os
from pathlib import Path


def register(sub):
    review = sub.add_parser("review", help="Adversarial review before pre-registration (question map)")
    review.add_argument("--db", type=Path, default=Path(os.getenv("CAIN_MEMORY_DB", "data/memory.db")))
    commands = review.add_subparsers(dest="review_command", required=True)
    opened = commands.add_parser("open", help="Open a review for a draft hypothesis (JSON file)")
    opened.add_argument("--domain", required=True)
    opened.add_argument("--file", type=Path, required=True)
    generate = commands.add_parser("generate", help="Local model asks each perspective's questions")
    generate.add_argument("--domain", required=True)
    generate.add_argument("hypothesis_id")
    generate.add_argument("--config", type=Path)
    generate.add_argument("--closed-rank-embedding", action="store_true",
                          help="order closed-archive matches by embedding similarity (never decides)")
    show = commands.add_parser("map", help="Question map: question → test/evidence → status")
    show.add_argument("--domain", required=True)
    show.add_argument("hypothesis_id")
    show.add_argument("--as-of", required=True)
    test = commands.add_parser("define-test")
    test.add_argument("--domain", required=True)
    test.add_argument("item_id")
    test.add_argument("--kind", required=True)
    test.add_argument("--description", required=True)
    test.add_argument("--pass-criterion", required=True)
    test.add_argument("--by", required=True)
    accept = commands.add_parser("accept", help="Human accepts the tests the model proposed")
    accept.add_argument("--domain", required=True)
    accept.add_argument("item_id", nargs="+")
    accept.add_argument("--by", required=True)
    answer = commands.add_parser("answer", help="Record the evidence or run that answers an item")
    answer.add_argument("--domain", required=True)
    answer.add_argument("item_id")
    answer.add_argument("--ref", required=True)
    answer.add_argument("--by", required=True)
    answer.add_argument("--note", default="")
    waive = commands.add_parser("waive", help="Human waiver of an item, with a reason")
    waive.add_argument("--domain", required=True)
    waive.add_argument("item_id")
    waive.add_argument("--by", required=True)
    waive.add_argument("--reason", required=True)
    pre = commands.add_parser("preregister", help="Freeze the hypothesis (refused while mandatory items block)")
    pre.add_argument("--domain", required=True)
    pre.add_argument("hypothesis_id")
    pre.add_argument("--by", required=True)


def execute(args):
    from cain.findings.archive import FindingsArchive
    from cain.memory.store import MemoryStore
    from cain.review.board import ReviewBoard

    memory = MemoryStore(args.db)
    board = ReviewBoard(memory, FindingsArchive(memory))
    cmd = args.review_command
    if cmd == "open":
        return board.open(args.domain, json.loads(args.file.read_text(encoding="utf-8")))
    if cmd == "generate":
        from cain.providers import configured_llm
        from cain.settings import load_settings

        provider = configured_llm(load_settings(args.config))
        if not hasattr(provider, "generate_json"):
            raise ValueError("the review needs a local model with structured output")
        from cain.loop.cli import similarity_function

        rank = similarity_function("embedding", args.config) if args.closed_rank_embedding else None
        return board.generate(args.domain, args.hypothesis_id, provider, closed_rank=rank)
    if cmd == "map":
        return board.question_map(args.domain, args.hypothesis_id,
                                  as_of=memory.now() if args.as_of == "now" else args.as_of)
    if cmd == "define-test":
        return board.define_test(args.domain, args.item_id, kind=args.kind, description=args.description,
                                 pass_criterion=args.pass_criterion, by=args.by)
    if cmd == "accept":
        return {"accepted": [board.accept(args.domain, item, by=args.by)["item_id"] for item in args.item_id]}
    if cmd == "answer":
        return board.answer(args.domain, args.item_id, ref=args.ref, by=args.by, note=args.note)
    if cmd == "waive":
        return board.waive(args.domain, args.item_id, by=args.by, reason=args.reason)
    if cmd == "preregister":
        return board.preregister(args.domain, args.hypothesis_id, by=args.by)
    raise ValueError(f"unknown review command {cmd!r}")

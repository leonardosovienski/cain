"""`cain memory`: CLI adapter of the bitemporal memory. Every read requires --as-of."""

import json
import os
from pathlib import Path


def _as_of(memory, value: str) -> str:
    # "now" must be typed explicitly: there is no implicit read time. It never precedes the log head.
    return memory.now() if value == "now" else value


def _reads(parser, *, cube_required=True):
    parser.add_argument("--as-of", required=True, help="ISO-8601 instant with offset, or the literal 'now'")
    parser.add_argument("--cube", action="append", required=cube_required, default=None)
    parser.add_argument("--cross-cube", action="store_true", help="explicitly read more than one cube")


def register(sub):
    memory = sub.add_parser("memory", help="Bitemporal memory: append-only log, as_of reads, cubes")
    memory.add_argument("--db", type=Path, default=Path(os.getenv("CAIN_MEMORY_DB", "data/memory.db")))
    memory.add_argument("--config", type=Path, help="cain.toml for the local model/embedding (optional)")
    memory.add_argument("--vectors", action="store_true",
                        help="use the configured embedding model for the derived vector index")
    commands = memory.add_subparsers(dest="memory_command", required=True)
    commands.add_parser("verify", help="Recompute the hash chain and compare projections with a replay")
    commands.add_parser("rebuild-index", help="Rebuild facts, documents and vectors from the event log")
    facts = commands.add_parser("facts")
    _reads(facts)
    facts.add_argument("--subject")
    facts.add_argument("--predicate")
    facts.add_argument("--valid-at")
    facts.add_argument("--status", action="append", choices=["DECLARED", "PROVEN"])
    documents = commands.add_parser("documents")
    _reads(documents)
    search = commands.add_parser("search")
    search.add_argument("query")
    _reads(search)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--status", action="append", choices=["DECLARED", "PROVEN"])
    history = commands.add_parser("history", help="Supersession chain of a fact as recorded at --as-of")
    history.add_argument("fact_id")
    history.add_argument("--as-of", required=True)
    add = commands.add_parser("add-fact", help="Record an operator-declared fact (always DECLARED)")
    add.add_argument("--cube", required=True)
    add.add_argument("--subject", required=True)
    add.add_argument("--predicate", required=True)
    add.add_argument("--object", required=True, help="JSON value or plain text")
    add.add_argument("--valid-from")
    add.add_argument("--valid-to")
    correct = commands.add_parser("correct", help="Supersede a fact with a corrected value (never deletes)")
    correct.add_argument("fact_id")
    correct.add_argument("--object", required=True)
    correct.add_argument("--reason", required=True)
    document = commands.add_parser("add-document")
    document.add_argument("--cube", required=True)
    document.add_argument("--title", required=True)
    document.add_argument("--published-at", required=True)
    document.add_argument("--source", required=True)
    document.add_argument("--file", type=Path, required=True)
    ingest = commands.add_parser("ingest-research",
                                 help="Deterministic (no model) transcription of admitted research records")
    ingest.add_argument("--cube", required=True)
    ingest.add_argument("--research-db", type=Path, default=Path(os.getenv("CAIN_RESEARCH_DB", "data/research.db")))
    ingest.add_argument("--policy", type=Path, default=os.getenv("CAIN_RESEARCH_POLICY"))
    ingest.add_argument("--user", default="leo")
    ingest.add_argument("--project")
    ingest.add_argument("--collection", default="crypto")
    extract = commands.add_parser("extract", help="Local model proposes facts from free text (all DECLARED)")
    extract.add_argument("--cube", required=True)
    extract.add_argument("--file", type=Path, required=True)
    extract.add_argument("--source", required=True)


def _value(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def _store(args):
    from cain.memory.store import MemoryStore

    embedding = None
    if args.vectors:
        from cain.providers import configured_embedding
        from cain.settings import load_settings

        embedding = configured_embedding(load_settings(args.config))
        if embedding is None:
            raise ValueError("--vectors requires search.mode = hybrid with a real embedding provider")
    return MemoryStore(args.db, embedding=embedding)


def execute(args):
    memory = _store(args)
    cmd = args.memory_command
    if cmd == "verify":
        return memory.verify()
    if cmd == "rebuild-index":
        return memory.rebuild_index()
    if cmd in {"facts", "documents", "search", "history"}:
        at = _as_of(memory, args.as_of)
    if cmd == "facts":
        return {"as_of": at, "facts": memory.facts(
            as_of=at, cubes=args.cube, cross_cube=args.cross_cube, subject=args.subject,
            predicate=args.predicate, valid_at=args.valid_at, statuses=args.status or ("DECLARED", "PROVEN"))}
    if cmd == "documents":
        return {"as_of": at, "documents": memory.documents(as_of=at, cubes=args.cube, cross_cube=args.cross_cube)}
    if cmd == "search":
        return memory.search(args.query, as_of=at, cubes=args.cube, cross_cube=args.cross_cube,
                             limit=args.limit, statuses=args.status or ("DECLARED", "PROVEN"))
    if cmd == "history":
        return {"fact_id": args.fact_id, "chain": memory.fact_history(args.fact_id, as_of=at)}
    if cmd == "add-fact":
        return memory.assert_fact(args.cube, args.subject, args.predicate, _value(args.object), status="DECLARED",
                                  valid_from=args.valid_from, valid_to=args.valid_to,
                                  source_episode_id="operator:cli")
    if cmd == "correct":
        return memory.correct_fact(args.fact_id, _value(args.object), reason=args.reason)
    if cmd == "add-document":
        return memory.record_document(args.cube, args.title, args.file.read_text(encoding="utf-8"),
                                      published_at=args.published_at, source=args.source)
    if cmd == "ingest-research":
        from cain.memory.ingest import ingest_research
        from cain.research import ResearchService

        service = ResearchService(args.research_db, args.policy)
        scope = service.scope(args.user, args.project, args.collection)
        return ingest_research(memory, service, scope, cube=args.cube, as_of=_as_of(memory, "now"))
    if cmd == "extract":
        from cain.memory.ingest import extract_facts
        from cain.providers import configured_llm
        from cain.settings import load_settings

        settings = load_settings(args.config)
        provider = configured_llm(settings)
        if not hasattr(provider, "generate_json"):
            raise ValueError("extract requires a local model with structured output (provider ollama/llamacpp)")
        return extract_facts(memory, provider, cube=args.cube, text=args.file.read_text(encoding="utf-8"),
                             source=args.source)
    raise ValueError(f"unknown memory command {cmd!r}")

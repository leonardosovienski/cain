"""CLI adapter; same application service as the HTTP/UI adapter."""

import os
from pathlib import Path


def register(sub):
    research = sub.add_parser("research", help="L0: import, query and preserve admitted research")
    research.add_argument("--policy", type=Path, default=os.getenv("CAIN_RESEARCH_POLICY"))
    research.add_argument(
        "--db", type=Path, default=os.getenv("CAIN_RESEARCH_DB", "data/research.db")
    )
    research.add_argument("--user", default="leo")
    research.add_argument("--project")
    research.add_argument("--session")
    research.add_argument("--collection", default="crypto")
    commands = research.add_subparsers(dest="research_command", required=True)
    ingest = commands.add_parser("import", help="Publication path relative to trusted import_root")
    ingest.add_argument("publication")
    for name in ("query", "explain"):
        query = commands.add_parser(name)
        for field in (
            "domain",
            "source-id",
            "kind",
            "status",
            "revision",
            "reason",
            "text",
            "completeness",
        ):
            query.add_argument("--" + field)
        query.add_argument("--limit", type=int, default=20)
        query.add_argument("--offset", type=int, default=0)
        if name == "explain":
            query.add_argument("question")
            query.add_argument("--config", type=Path)
    evidence = commands.add_parser("evidence")
    evidence.add_argument("reference")
    history = commands.add_parser("history")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--offset", type=int, default=0)
    recall = commands.add_parser("recall")
    recall.add_argument("entry_id")
    for name in ("coverage", "receipts", "verify", "rebuild"):
        commands.add_parser(name)
    inspection = commands.add_parser("inspect", help="Local provenance, timeline and revision dossier")
    for field in ("source-id", "domain", "before", "after"):
        inspection.add_argument("--" + field)
    for name in ("search", "entities", "workflow"):
        tool = commands.add_parser(name)
        tool.add_argument("question")
        tool.add_argument("--source-id")
        tool.add_argument("--config", type=Path)
        if name == "search":
            tool.add_argument("--semantic", action="store_true")
        if name == "workflow":
            tool.add_argument("--steps", nargs="+", default=["inspect", "search", "entities", "support", "challenge", "synthesis"])
            tool.add_argument("--run-id")
    for name in ("job", "advance", "cancel", "trace", "abstain"):
        job = commands.add_parser(name)
        job.add_argument("run_id")
        job.add_argument("--config", type=Path)
        if name == "abstain":
            job.add_argument("--reason", required=True)
        if name == "advance":
            job.add_argument("--approve-generation", action="store_true")
            job.add_argument("--recover", action="store_true")
    commands.add_parser("jobs")
    backup = commands.add_parser("backup")
    backup.add_argument("destination", type=Path)
    restore = commands.add_parser("restore", help="Restore a backup to a NEW database path")
    restore.add_argument("source", type=Path)
    restore.add_argument("destination", type=Path)


def execute(args):
    from cain.research import ResearchService

    if args.research_command == "restore":
        return ResearchService.restore(args.source, args.destination)
    service = ResearchService(args.db, args.policy)
    scope = service.scope(args.user, args.project, args.collection)
    cmd = args.research_command
    if cmd in {"search", "entities", "workflow", "job", "advance", "cancel", "jobs", "trace", "abstain"}:
        from cain.research.analysis import search, entities
        from cain.research.workflows import Workflows
        from cain.providers import configured_llm
        from cain.settings import load_settings

        if cmd == "search":
            from cain.providers import configured_embedding
            encoder = configured_embedding(load_settings(args.config)) if args.semantic else None
            if args.semantic and encoder is None:
                raise ValueError("Configure hybrid search for semantic mode")
            return search(service, scope, args.question, source_id=args.source_id, embedding=encoder)
        jobs = Workflows(service)
        if cmd == "jobs":
            return jobs.list(scope)
        if cmd == "job":
            return jobs.get(scope, args.run_id)
        if cmd == "trace":
            return jobs.trace(scope, args.run_id)
        if cmd == "cancel":
            return jobs.cancel(scope, args.run_id)
        if cmd == "abstain":
            return jobs.abstain(scope, args.run_id, args.reason)
        provider = configured_llm(load_settings(args.config))
        if cmd == "entities":
            return entities(service, scope, args.question, provider, source_id=args.source_id)
        if cmd == "workflow":
            return jobs.create(scope, args.question, provider, source_id=args.source_id,
                               steps=args.steps, run_id=args.run_id)
        return jobs.advance(scope, args.run_id, provider, approve_generation=args.approve_generation,
                            recover=args.recover)
    if cmd == "inspect":
        from cain.research.inspection import inspect

        return inspect(service, scope, source_id=args.source_id, domain=args.domain,
                       before=args.before, after=args.after)
    if cmd == "import":
        return service.ingest(args.publication, scope)
    if cmd in {"query", "explain"}:
        filters = {
            k: getattr(args, k)
            for k in (
                "domain",
                "source_id",
                "kind",
                "status",
                "revision",
                "reason",
                "text",
                "completeness",
                "limit",
                "offset",
            )
        }
        if cmd == "query":
            return service.query(scope, session_id=args.session, **filters)
        from cain.providers import configured_llm
        from cain.settings import load_settings
        from cain.research.historian import explain

        return explain(
            service,
            scope,
            args.question,
            configured_llm(load_settings(args.config)),
            session_id=args.session,
            **filters,
        )
    if cmd == "coverage":
        result = service.query(scope, limit=1)
        return {k: result[k] for k in ("coverage", "limitations", "total_record_revisions")}
    if cmd == "evidence":
        return service.evidence(scope, args.reference)
    if cmd == "receipts":
        return service.receipts(scope)
    if cmd == "history":
        return service.history(scope, args.session, args.limit, args.offset)
    if cmd == "recall":
        return service.recall(scope, args.entry_id, args.session)
    if cmd in {"verify", "rebuild"}:
        return service.verify(scope, rebuild=cmd == "rebuild")
    if cmd == "backup":
        return service.backup(args.destination)

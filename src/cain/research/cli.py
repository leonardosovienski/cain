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
    for name in ("coverage", "receipts", "verify", "rebuild"):
        commands.add_parser(name)
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
            return service.query(scope, **filters)
        from cain.cli import configured_llm
        from cain.settings import load_settings
        from cain.research.historian import explain

        return explain(
            service, scope, args.question, configured_llm(load_settings(args.config)), **filters
        )
    if cmd == "coverage":
        result = service.query(scope, limit=1)
        return {k: result[k] for k in ("coverage", "limitations", "total_record_revisions")}
    if cmd == "evidence":
        return service.evidence(scope, args.reference)
    if cmd == "receipts":
        return service.receipts(scope)
    if cmd in {"verify", "rebuild"}:
        return service.verify(scope, rebuild=cmd == "rebuild")
    if cmd == "backup":
        return service.backup(args.destination)

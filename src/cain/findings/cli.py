"""`cain findings`: what CAIN learned from the predictors, with quarantine and domain isolation."""

import json
import os
from pathlib import Path


def register(sub):
    findings = sub.add_parser("findings", help="Findings archive: quarantine, closed hypotheses, procedures")
    findings.add_argument("--db", type=Path, default=Path(os.getenv("CAIN_MEMORY_DB", "data/memory.db")))
    commands = findings.add_subparsers(dest="findings_command", required=True)
    for name, helptext in (("ingest-registry", "Trial registry rows of a predictor (read at a git commit)"),
                           ("ingest-state", "Scientific state of a predictor (closed hypotheses)"),
                           ("sync-demotions", "Demote library procedures whose source trial was demoted")):
        command = commands.add_parser(name, help=helptext)
        command.add_argument("--domain", required=True)
        command.add_argument("--repo", type=Path, required=True)
        command.add_argument("--commit", default="origin/main")
        command.add_argument("--path", required=True)
        if name == "ingest-state":
            command.add_argument("--registry-path")
    loop = commands.add_parser("ingest-loop", help="Outcome of a CAIN research loop")
    loop.add_argument("--domain", required=True)
    loop.add_argument("--loop-db", type=Path, required=True)
    loop.add_argument("--loop-id", required=True)
    listing = commands.add_parser("list", help="Findings as of an instant (PROVEN only unless asked)")
    listing.add_argument("--domain", action="append", required=True)
    listing.add_argument("--as-of", required=True)
    listing.add_argument("--include-quarantine", action="store_true")
    listing.add_argument("--kind", choices=["positive", "negative", "informative"])
    check = commands.add_parser("check", help="Is a new hypothesis equivalent to a closed one?")
    check.add_argument("--domain", required=True)
    check.add_argument("--statement", required=True)
    check.add_argument("--as-of", required=True)
    for key in ("trial-id", "hypothesis-id", "hypothesis-family"):
        check.add_argument("--" + key)
    check.add_argument("--threshold", type=float, default=0.6)
    check.add_argument("--similarity", choices=["lexical", "embedding"], default="lexical")
    check.add_argument("--config", type=Path, help="cain.toml for the embedding model")
    pre = commands.add_parser("preregister", help="Pre-register a hypothesis in a domain")
    pre.add_argument("--domain", required=True)
    pre.add_argument("--hypothesis-id", required=True)
    pre.add_argument("--statement", required=True)
    pre.add_argument("--derived-from")
    pre.add_argument("--by", required=True)
    apply = commands.add_parser("apply", help="Use a finding in a domain (cross-domain needs a pre-registration)")
    apply.add_argument("finding_id")
    apply.add_argument("--from", dest="source_domain", required=True)
    apply.add_argument("--to", dest="target_domain", required=True)
    apply.add_argument("--as-of", required=True)
    apply.add_argument("--preregistration")
    procedures = commands.add_parser("procedures", help="Procedure library")
    procedures.add_argument("--domain", required=True)
    procedures.add_argument("--as-of", required=True)
    procedures.add_argument("--include-demoted", action="store_true")
    add = commands.add_parser("add-procedure", help="Admit a procedure (JSON with tests and walk-forward)")
    add.add_argument("--domain", required=True)
    add.add_argument("--file", type=Path, required=True)


def execute(args):
    from hashlib import sha256

    from cain.findings.archive import FindingsArchive
    from cain.findings.ingest import (ingest_loop, ingest_scientific_state, ingest_trial_registry,
                                      read_source)
    from cain.memory.store import MemoryStore

    memory = MemoryStore(args.db)
    archive = FindingsArchive(memory)
    cmd = args.findings_command

    def at(value):
        return memory.now() if value == "now" else value

    if cmd == "ingest-registry":
        raw, source = read_source(args.repo, args.commit, args.path)
        return ingest_trial_registry(archive, args.domain, raw, source)
    if cmd == "ingest-state":
        raw, source = read_source(args.repo, args.commit, args.path)
        rows = None
        if args.registry_path:
            rows = json.loads(read_source(args.repo, args.commit, args.registry_path)[0])
        return ingest_scientific_state(archive, args.domain, raw, source, rows)
    if cmd == "sync-demotions":
        raw, source = read_source(args.repo, args.commit, args.path)
        return {"demoted": archive.sync_demotions(args.domain, json.loads(raw), source=source)}
    if cmd == "ingest-loop":
        from cain.loop.ledger import LoopLedger

        return ingest_loop(archive, args.domain, LoopLedger(args.loop_db), args.loop_id)
    if cmd == "list":
        found = archive.findings(args.domain, as_of=at(args.as_of), include_quarantine=args.include_quarantine,
                                 kind=args.kind)
        return {"as_of": at(args.as_of), "include_quarantine": args.include_quarantine, "count": len(found),
                "findings": found}
    if cmd == "check":
        identity = {"trial_id": args.trial_id, "hypothesis_id": args.hypothesis_id,
                    "hypothesis_family": args.hypothesis_family}
        from cain.loop.cli import similarity_function

        matches = archive.equivalent_closed(args.domain, args.statement, as_of=at(args.as_of), identity=identity,
                                            threshold=args.threshold,
                                            similarity=similarity_function(args.similarity, args.config))
        return {"equivalent_to_closed": bool(matches), "matches": matches}
    if cmd == "preregister":
        return archive.preregister(args.domain, args.hypothesis_id, statement=args.statement,
                                   derived_from=args.derived_from, by=args.by,
                                   source_hash=sha256(args.statement.encode("utf-8")).hexdigest())
    if cmd == "apply":
        return archive.apply(args.finding_id, source_domain=args.source_domain, target_domain=args.target_domain,
                             as_of=at(args.as_of), preregistration=args.preregistration)
    if cmd == "procedures":
        return {"procedures": archive.procedures(args.domain, as_of=at(args.as_of),
                                                 include_demoted=args.include_demoted)}
    if cmd == "add-procedure":
        spec = json.loads(args.file.read_text(encoding="utf-8"))
        return archive.record_procedure(args.domain, spec.pop("name"), **spec)
    raise ValueError(f"unknown findings command {cmd!r}")

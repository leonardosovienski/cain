"""`cain claims`: evidence, claims, verification, review queue, trace and the report linter."""

import os
from pathlib import Path


def _as_of(memory, value: str) -> str:
    return memory.now() if value == "now" else value


def register(sub):
    claims = sub.add_parser("claims", help="Evidence and claims: literal citations, verifiers, report linter")
    claims.add_argument("--db", type=Path, default=Path(os.getenv("CAIN_MEMORY_DB", "data/memory.db")))
    commands = claims.add_subparsers(dest="claims_command", required=True)
    evidence = commands.add_parser("add-evidence", help="Record a literal span of a stored document")
    evidence.add_argument("--cube", required=True)
    evidence.add_argument("--document-id", required=True)
    evidence.add_argument("--start", type=int, required=True)
    evidence.add_argument("--end", type=int, required=True)
    evidence.add_argument("--quote", required=True)
    for name in ("query", "summary", "model-id", "settings-hash", "chunk-id"):
        evidence.add_argument("--" + name)
    evidence.add_argument("--relevance-score", type=float)
    evidence.add_argument("--page", type=int)
    claim = commands.add_parser("add-claim")
    claim.add_argument("--cube", required=True)
    claim.add_argument("--text", required=True)
    claim.add_argument("--document-id", required=True, help="report document the claim comes from")
    claim.add_argument("--start", type=int, required=True)
    claim.add_argument("--end", type=int, required=True)
    claim.add_argument("--kind", choices=["TEXTUAL_SUPPORT", "EMPIRICAL_PROOF"], default="TEXTUAL_SUPPORT")
    claim.add_argument("--status", choices=["INCONCLUSIVE", "AMBIGUOUS", "UNVERIFIABLE"], default="INCONCLUSIVE")
    claim.add_argument("--evidence", action="append", default=[])
    claim.add_argument("--run-id")
    claim.add_argument("--report-path")
    claim.add_argument("--report-sha256")
    extract = commands.add_parser("extract", help="Local model proposes claims from a stored report")
    extract.add_argument("--cube", required=True)
    extract.add_argument("--document-id", required=True)
    extract.add_argument("--config", type=Path)
    verify = commands.add_parser("verify", help="Two local verifiers over the cited evidence")
    verify.add_argument("claim_id")
    verify.add_argument("--evidence", action="append")
    verify.add_argument("--models-dir", type=Path, default=os.getenv("CAIN_VERIFIER_MODELS"))
    empirical = commands.add_parser("verify-empirical", help="Check an EMPIRICAL_PROOF claim against its run artifact")
    empirical.add_argument("claim_id")
    empirical.add_argument("--root", type=Path, default=Path("."))
    review = commands.add_parser("review", help="Human decision recorded as an immutable event")
    review.add_argument("claim_id")
    review.add_argument("--status", required=True,
                        choices=["SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "AMBIGUOUS", "UNVERIFIABLE"])
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", required=True)
    for name, helptext in (("list", "Claims as of an instant"), ("review-queue", "Claims waiting for a human")):
        command = commands.add_parser(name, help=helptext)
        command.add_argument("--as-of", required=True)
        command.add_argument("--cube", action="append", required=True)
        command.add_argument("--cross-cube", action="store_true")
        if name == "list":
            command.add_argument("--unsupported", action="store_true")
    trace = commands.add_parser("trace", help="Where did this claim come from?")
    trace.add_argument("claim_id")
    trace.add_argument("--as-of", required=True)
    lint = commands.add_parser("lint", help="Block a report whose numbers lack provenance")
    lint.add_argument("report", type=Path)
    lint.add_argument("--as-of", required=True)
    lint.add_argument("--cube", action="append", required=True)
    lint.add_argument("--cross-cube", action="store_true")
    lint.add_argument("--root", type=Path, default=Path("."))
    sample = commands.add_parser("faithfulness-sample", help="Claims to hand-label this month (deterministic)")
    sample.add_argument("--month", required=True)
    sample.add_argument("--n", type=int, default=30)
    sample.add_argument("--as-of", required=True)
    sample.add_argument("--cube", action="append", required=True)
    sample.add_argument("--cross-cube", action="store_true")
    faithful = commands.add_parser("faithfulness", help="Faithfulness with CI (classical and prediction-powered)")
    faithful.add_argument("--labels", type=Path, required=True, help="JSON {claim_id: 1 supported | 0 not}")
    faithful.add_argument("--as-of", required=True)
    faithful.add_argument("--cube", action="append", required=True)
    faithful.add_argument("--cross-cube", action="store_true")
    golden = commands.add_parser("golden", help="Measure the verifiers on the frozen golden set")
    golden.add_argument("--models-dir", type=Path, default=os.getenv("CAIN_VERIFIER_MODELS"))
    golden.add_argument("--output", type=Path)


def execute(args):
    from cain.memory.store import MemoryStore

    memory = MemoryStore(args.db)
    cmd = args.claims_command
    if cmd == "add-evidence":
        return memory.record_evidence(args.cube, args.document_id, args.start, args.end, args.quote,
                                      query=args.query, summary=args.summary, relevance_score=args.relevance_score,
                                      model_id=args.model_id, settings_hash=args.settings_hash, page=args.page,
                                      chunk_id=args.chunk_id)
    if cmd == "add-claim":
        run_ref = None
        if args.kind == "EMPIRICAL_PROOF":
            run_ref = {"run_id": args.run_id, "report_path": args.report_path, "report_sha256": args.report_sha256}
        return memory.record_claim(args.cube, args.text, source_document_id=args.document_id,
                                   char_start=args.start, char_end=args.end, kind=args.kind, status=args.status,
                                   evidence_ids=args.evidence, run_ref=run_ref)
    if cmd == "extract":
        from cain.claims.extract import extract_claims
        from cain.providers import configured_llm
        from cain.settings import load_settings

        provider = configured_llm(load_settings(args.config))
        if not hasattr(provider, "generate_json"):
            raise ValueError("extract requires a local model with structured output")
        return extract_claims(memory, provider, cube=args.cube, document_id=args.document_id)
    if cmd == "verify":
        from cain.claims.verifiers import load_default_pair
        from cain.claims.verify import assess_textual

        return assess_textual(memory, args.claim_id, load_default_pair(args.models_dir), evidence_ids=args.evidence)
    if cmd == "verify-empirical":
        from cain.claims.verify import assess_empirical

        return assess_empirical(memory, args.claim_id, root=args.root)
    if cmd == "review":
        from cain.claims.verify import review

        return review(memory, args.claim_id, args.status, reviewer=args.reviewer, note=args.note)
    if cmd == "list":
        return {"claims": memory.claims(as_of=_as_of(memory, args.as_of), cubes=args.cube, cross_cube=args.cross_cube,
                                        unsupported=args.unsupported)}
    if cmd == "review-queue":
        queue = [c for c in memory.claims(as_of=_as_of(memory, args.as_of), cubes=args.cube, cross_cube=args.cross_cube)
                 if c["review_state"] == "needs_human_review"]
        return {"review_queue": queue}
    if cmd == "trace":
        return memory.claim_trace(args.claim_id, as_of=_as_of(memory, args.as_of))
    if cmd == "lint":
        from cain.claims.lint import lint_report

        return lint_report(memory, args.report.read_text(encoding="utf-8"), as_of=_as_of(memory, args.as_of),
                           cubes=args.cube, cross_cube=args.cross_cube, root=args.root)
    if cmd in ("faithfulness-sample", "faithfulness"):
        from cain.claims.faithfulness import estimate, monthly_sample

        at = _as_of(memory, args.as_of)
        textual = [c for c in memory.claims(as_of=at, cubes=args.cube, cross_cube=args.cross_cube)
                   if c["kind"] == "TEXTUAL_SUPPORT" and c["status"] not in ("AMBIGUOUS", "UNVERIFIABLE")]
        if cmd == "faithfulness-sample":
            return {"month": args.month, "as_of": at, "population": len(textual),
                    "sample": monthly_sample([c["id"] for c in textual], args.month, args.n)}
        import json

        automatic = {c["id"]: int(c["status"] == "SUPPORTED") for c in textual}
        human = {k: int(v) for k, v in json.loads(args.labels.read_text(encoding="utf-8")).items()}
        return {"as_of": at, **estimate(automatic, human)}
    if cmd == "golden":
        from cain.claims.golden import run_golden
        from cain.claims.verifiers import load_default_pair

        result = run_golden(load_default_pair(args.models_dir))
        if args.output is not None:
            import json

            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return result
    raise ValueError(f"unknown claims command {cmd!r}")

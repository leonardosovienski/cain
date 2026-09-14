"""Three real predictor cases over an explicitly attested QA research archive."""

import argparse
from pathlib import Path
import time
import uuid

from cain.evaluation.v2 import attest, digest, records, request, write


def run(root, output, rubrics, api):
    root = Path(root).resolve()
    output = Path(output).resolve()
    attestation = attest(root, api)
    output.mkdir(parents=True, exist_ok=False)
    cases = [
        (
            "A01",
            "crypto",
            "H4",
            "O que o relatório permite concluir sobre H4 e quais limitações impedem uma conclusão mais forte?",
        ),
        (
            "A02",
            "stocks",
            "Retorno líquido",
            "O que o relatório permite concluir sobre a prontidão para operação real e quais limitações permanecem?",
        ),
        (
            "A03",
            "brasileirao",
            "CLAIM-BR-MARKET-001",
            "O que o relatório permite concluir sobre CLAIM-BR-MARKET-001 e quais limitações impedem uma conclusão mais forte?",
        ),
    ]
    write(
        output / "manifest.json",
        {
            "protocol": "cain-product-evaluation/2.0",
            "case_version": 1,
            "cases": cases,
            "split": "regression",
            "evidence_kind": "real authorized received QA catalog",
            "attestation": attestation,
            "rubric_path": str(rubrics),
            "rubric_sha256": digest(rubrics),
            "user": "qa-hypothesis-catalog",
            "inference_policy": "optional on runtime; report guard abstention",
            "steps": ["inspect", "search", "support"],
            "repetitions": 1,
            "generation_cap_per_case": 1,
            "state": "consistent copied archive; unique new jobs; no historical overwrite",
            "integrity": "read-only evidence, append QA jobs/queries/attempts only",
            "evaluator": "implementing assistant; manual entailment review required",
            "limits": "No claim of whole-project coverage, current producer truth, or independent confirmation",
        },
    )
    for family, domain, term, question in cases:
        scope = {"user_id": "qa-hypothesis-catalog", "collection": domain}
        label = {"run_id": output.name, "case_id": family, "path": "C", "attempt": 1}
        write(root / "active.json", label)
        row = {
            "family": family,
            "domain": domain,
            "question": question,
            "path": "C research API",
            "execution": "completed",
            "quality": "review_required",
            "origin": "unknown",
            "case_validity": "valid",
        }
        started = time.perf_counter()
        try:
            status, source = request(api + "/research/query", {**scope, "text": term, "limit": 50})
            row["source_preflight"] = source
            if status != 200 or not source.get("records"):
                row.update(
                    execution="blocked",
                    quality="not_evaluable",
                    reason="Case source not available in admitted QA archive",
                )
            else:
                _, row["coverage"] = request(api + "/research/coverage", scope)
                status, job = request(
                    api + "/research/jobs",
                    {
                        **scope,
                        "question": question,
                        "steps": ["inspect", "search", "support"],
                        "run_id": uuid.uuid4().hex,
                    },
                )
                if status != 200:
                    raise ValueError(str(job))
                row["job"] = job
                for _ in range(3):
                    status, updated = request(
                        api + "/research/jobs/" + job["id"] + "/advance",
                        {**scope, "approve_generation": True},
                        timeout=260,
                    )
                    row["last_http_response"] = {"status": status, "body": updated}
                    if status != 200:
                        row.update(execution="operational_error", quality="not_evaluable")
                        break
                    row["job"] = updated
                _, fresh = request(api + "/research/jobs/" + job["id"] + "/read", scope)
                row["reopened"] = fresh
                quotes = 0
                for step in fresh.get("steps", []):
                    explanation = step["result"].get("explanation") or {}
                    for quote in explanation.get("source_quotes", []):
                        assert (
                            quote["support"]["text"][quote["start"] : quote["end"]]
                            == quote["quote"]
                        )
                        quotes += 1
                row["literal_quotes_verified"] = quotes
                row["semantic_support"] = "not_certified"
        except Exception as e:
            row.update(
                execution="operational_error",
                quality="not_evaluable",
                error=f"{type(e).__name__}: {e}",
            )
        row["seconds"] = time.perf_counter() - started
        row["calls"] = [
            x
            for x in records(root / "transport.jsonl")
            if x.get("case") == label and x["path"] == "/api/generate"
        ]
        row["dispatch"] = [
            x
            for x in records(root / "dispatch.jsonl")
            if x.get("case") == label and x["path"] == "/api/generate"
        ]
        row["llm_call_count"] = (
            len(row["calls"]) if len(row["calls"]) == len(row["dispatch"]) else None
        )
        write(output / (family + ".json"), row)
        print(family, row["execution"], row["quality"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--rubrics", type=Path, required=True)
    p.add_argument("--api", default="http://127.0.0.1:8896")
    a = p.parse_args()
    run(a.root, a.output, a.rubrics, a.api)

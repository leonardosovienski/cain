"""Development evaluation on an isolated copy of admitted archives, with real Ollama."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from research_snapshot import canonical
from cain.providers import configured_embedding, configured_llm
from cain.research import ResearchService
from cain.research.analysis import search, entities
from cain.research.historian import _explain
from cain.research.workflows import Workflows
from cain.settings import load_settings


def verify(db, policy, config, protocol, output):
    output.mkdir(parents=True, exist_ok=False)
    settings = load_settings(config)
    provider, embedding = configured_llm(settings), configured_embedding(settings)
    original = ResearchService(db, policy)
    original.backup(output / "evaluation.db")
    service = ResearchService(output / "evaluation.db", policy)
    plan = json.loads(protocol.read_bytes())
    report = {"protocol": plan, "cases": [], "workflow": None, "economic_validation": False}

    def save():
        (output / "report.json").write_bytes(canonical(report))

    for case in plan["cases"]:
        scope = service.scope(collection=case["collection"])
        started = perf_counter()
        baseline = service.query(scope, source_id=case["source_id"])
        ranked = search(service, scope, case["question"], source_id=case["source_id"])
        assert {r["id"]: r["source_status"] for r in baseline["records"]} == {
            r["record"]["id"]: r["record"]["source_status"] for r in ranked["results"]}
        result = {"case": case["id"], "baseline_ids_states_equal": True,
                  "lexical_results": len(ranked["results"])}
        try:
            hybrid = search(service, scope, case["question"], source_id=case["source_id"], embedding=embedding)
            result["hybrid"] = {k: hybrid[k] for k in
                                ("mode", "matches", "embedded_records", "embedding_model", "embedding_digest")}
        except Exception as exc:
            result["hybrid_error"] = {"type": type(exc).__name__, "message": str(exc)}
        result["explanation"] = _explain(service, scope, case["question"], provider, source_id=case["source_id"])
        result["elapsed"] = perf_counter() - started
        report["cases"].append(result)
        save()
        print(json.dumps({"case": case["id"], "status": result["explanation"]["status"],
                          "hybrid": "hybrid" in result, "elapsed": result["elapsed"]}), flush=True)
    scope = service.scope(collection="crypto")
    negative = entities(service, scope, "What is supported?", provider, source_id=plan["negative_case"])
    assert negative["status"] == "abstained" and negative["model_calls"] == 0
    report["negative"] = negative
    jobs = Workflows(service)
    job = jobs.create(scope, plan["cases"][0]["question"], provider, source_id="H6")
    report["workflow_id"] = job["id"]
    save()
    for _ in range(6):
        try:
            # Reopen every step, exercising the durable boundary.
            job = Workflows(ResearchService(output / "evaluation.db", policy)).advance(
                scope, job["id"], provider, approve_generation=True)
            report["workflow"] = job
            save()
            print(json.dumps({"step": job["steps"][-1]["name"], "status": job["status"]}), flush=True)
        except Exception as exc:
            report["workflow_error"] = {"type": type(exc).__name__, "message": str(exc)}
            job = jobs.get(scope, job["id"])
            report["workflow"] = job
            save()
            break
    if job["status"] == "completed":
        assert jobs.advance(scope, job["id"], provider, approve_generation=True)["steps"] == job["steps"]
        service.backup(output / "completed-backup.db")
        restored = Workflows(ResearchService(output / "completed-backup.db", policy))
        assert restored.get(scope, job["id"])["steps"] == job["steps"]
        (output / "trace.otlp.json").write_bytes(canonical(jobs.trace(scope, job["id"])))
        report["resume_backup_verified"] = True
    save()
    return {"output": str(output), "cases": len(report["cases"]), "workflow_status": job["status"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("db", "policy", "config", "protocol", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    print(json.dumps(verify(**vars(parser.parse_args()))))

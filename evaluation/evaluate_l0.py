"""Bounded current-recovery comparison on the same admitted evidence, no network."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from cain.research import ResearchService
from cain.search import LocalDocumentRetriever
from research_snapshot import canonical, digest


def evaluate(service, scope, protocol):
    results = []
    for episode in protocol["episodes"]:
        start = perf_counter()
        response = service.query(scope, source_id=episode["source_id"])
        records = response["records"]
        expected = episode.get("expected_status")
        correct = (
            (not records)
            if episode["abstain"]
            else bool(records)
            and all(
                r["source_status"] == expected
                if "expected_status" in episode
                else r["source_status"].startswith(episode["expected_status_prefix"])
                for r in records
            )
        )
        deterministic = {
            "correct_state_or_abstention": correct,
            "record_revisions": len(records),
            "coverage_shown": bool(response["coverage"]),
            "latency_seconds": perf_counter() - start,
            "source_references": sorted(
                {e["reference_id"] for r in records for e in r["evidence"]}
            ),
            "missing_reason_preserved": all(r["reason"] is None for r in records),
        }
        # Give the documentary baseline identical curation AND exact-ID filtering.
        # Retrieval success does not certify the correctness of a generated answer.
        start = perf_counter()
        corpus = {
            e["reference_id"]: e["text"]
            for r in records
            for e in r["evidence"]
            if e["availability"] == "received"
        }
        retriever = LocalDocumentRetriever(corpus=corpus)
        hits = retriever.search(episode["source_id"] + " " + episode["question"], k=5)
        expected_text = expected or episode.get("expected_status_prefix", "")
        retrieved = (
            (not hits) if episode["abstain"] else any(expected_text in hit.text for hit in hits)
        )
        documentary = {
            "expected_state_retrieved_or_abstained": retrieved,
            "latency_seconds": perf_counter() - start,
            "chunks": [asdict(hit) for hit in hits],
            "coverage_shown": response["coverage"],
            "generation": "not_used",
        }
        results.append(
            {
                "episode": episode["id"],
                "deterministic": deterministic,
                "organized_documents": documentary,
                "historian": {
                    "status": "NOT_RUN",
                    "reason": "No authorized available local provider",
                },
            }
        )
    return {
        "protocol_sha256": digest(canonical(protocol)),
        "episodes": results,
        "summary": {
            "questions": len(results),
            "deterministic_correct": sum(
                r["deterministic"]["correct_state_or_abstention"] for r in results
            ),
            "documentary_retrieval_correct": sum(
                r["organized_documents"]["expected_state_retrieved_or_abstained"] for r in results
            ),
            "model_calls": 0,
            "human_time": None,
            "utility_status": "INCONCLUSIVE",
        },
        "limitations": protocol["limitations"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    service = ResearchService(args.db, args.policy)
    result = evaluate(
        service, service.scope(), json.loads(args.protocol.read_text(encoding="utf-8"))
    )
    args.output.write_bytes(canonical(result))
    print(json.dumps(result["summary"], indent=2))

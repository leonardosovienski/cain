"""Bounded current-recovery comparison on the same admitted evidence, no network."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from cain.research import ResearchService
from cain.research.historian import explain
from cain.search import LocalDocumentRetriever
from research_snapshot import canonical, digest


class DocumentaryView:
    """Same permission boundary; generation sees only lexically recovered source chunks."""

    def __init__(self, service, corpus, question):
        self.service, self.corpus, self.question = service, corpus, question

    def __getattr__(self, name):
        return getattr(self.service, name)

    def query(self, scope, **filters):
        result = self.service.query(scope, **filters)
        if filters.get("generate"):
            allowed = {e["reference_id"] for r in result["records"] for e in r["evidence"]}
            corpus = {ref: text for ref, text in self.corpus.items() if ref in allowed}
            hits = LocalDocumentRetriever(corpus=corpus).search(self.question, k=5)
            # Keep original reference IDs and received bytes; retrieval selects sources,
            # it does not manufacture a new citation or a scientific interpretation.
            selected = {hit.source for hit in hits}
            for record in result["records"]:
                record["evidence"] = [
                    e for e in record["evidence"] if e["reference_id"] in selected
                ]
        return result


def evaluate(service, scope, protocol, provider=None):
    if len(protocol["episodes"]) > protocol["call_limit_per_model_arm"]:
        raise ValueError("Protocol exceeds per-arm call limit")
    if protocol["evidence_budget_bytes"] != 6000 or protocol["generation_limit_bytes"] != 6000:
        raise ValueError("Protocol budgets must match the installed Historian")
    # Build the documentary catalogue directly from authorized preserved publications,
    # not the structured query's answer. Exact source-ID filtering is available to both arms.
    with service.connection() as db:
        archives = service._archive(db, scope)
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
        corpus = {}
        for pubid, package in archives.items():
            refs = {
                eid
                for r in package["records"]
                if r["source_id"] == episode["source_id"]
                for eid in r["evidence_ids"]
            }
            corpus.update(
                {
                    pubid + ":" + e["id"]: e["text"]
                    for e in package["evidence"]
                    if e["id"] in refs and e["availability"] == "received"
                }
            )
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
        generated = {}
        for arm, selected_service in (
            (
                "organized_documents",
                DocumentaryView(service, corpus, episode["source_id"] + " " + episode["question"]),
            ),
            ("historian", service),
        ):
            if provider is None:
                answer = {"status": "NOT_RUN", "reason": "No authorized available local provider"}
            else:
                try:
                    answer = explain(
                        selected_service,
                        scope,
                        episode["question"],
                        provider,
                        source_id=episode["source_id"],
                    )
                except ValueError as exc:
                    answer = {"status": "INPUT_REJECTED", "reason": str(exc)}
            generated[arm] = answer
        documentary["generation"] = generated["organized_documents"]
        results.append(
            {
                "episode": episode["id"],
                "deterministic": deterministic,
                "organized_documents": documentary,
                "historian": generated["historian"],
                "metrics": {
                    "independent_episode_group": episode.get("group", episode["id"]),
                    "split": protocol.get("split", "development"),
                    "false_absence": bool(not records and not episode["abstain"]),
                    "duplicate_record_ids": len(records) - len({r["id"] for r in records}),
                    "omitted_expected_state": not correct,
                    "generated_semantic_correctness": None,
                    "human_review_required": provider is not None,
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
            "model_calls": sum(
                bool(answer.get("generation", {}).get("called"))
                for r in results
                for answer in (r["historian"], r["organized_documents"]["generation"])
            ),
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
    parser.add_argument("--collection", default="crypto")
    parser.add_argument(
        "--config",
        type=Path,
        help="Explicit existing local provider configuration; omit for deterministic evaluation",
    )
    args = parser.parse_args()
    service = ResearchService(args.db, args.policy)
    provider = None
    if args.config:
        from cain.cli import configured_llm
        from cain.settings import load_settings

        provider = configured_llm(load_settings(args.config))
    result = evaluate(
        service,
        service.scope(collection=args.collection),
        json.loads(args.protocol.read_text(encoding="utf-8")),
        provider,
    )
    args.output.write_bytes(canonical(result))
    print(json.dumps(result["summary"], indent=2))

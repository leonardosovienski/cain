"""A12: paired document task with existing hybrid retrieval and structured lookup."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from cain.evaluation.v2 import attest, request, write
from cain.providers import configured_embedding
from cain.runtime import build_retriever
from cain.settings import load_settings
from cain.workspace import WorkspaceStore


def run(root, output, api):
    root = Path(root).resolve()
    output = Path(output).resolve()
    proof = attest(root, api)
    output.mkdir(parents=True, exist_ok=False)
    facts = {
        "procedimento": "Cedral",
        "codigo": "CEDRAL-615",
        "prazo_dias": 8,
        "status": "sem resultado econômico observado",
    }
    content = json.dumps(facts, ensure_ascii=False)
    question = "Busque no documento o código do procedimento Cedral e seu prazo."
    write(
        output / "manifest.json",
        {
            "family": "A12",
            "protocol": "cain-product-evaluation/2.0",
            "split": "development",
            "evidence_kind": "synthetic structured operational document",
            "question": question,
            "fixture": facts,
            "required_facts": ["codigo", "prazo_dias"],
            "order": [
                "CAIN normal API",
                "existing hybrid retriever",
                "authorized structured lookup",
            ],
            "k": 3,
            "generation": "none expected; API observed separately",
            "attestation": proof,
            "semantic_reviewer": "implementing assistant, unblinded",
            "human_effort": "not measured",
            "limits": "One synthetic task; shared retriever and warm-cache ordering, not general utility",
        },
    )
    user = "qa-utility-" + output.name
    status, p = request(api + "/projects/" + user, {"name": "Paired task"})
    assert status == 200
    status, doc = request(
        api + f"/projects/{user}/{p['id']}/documents", {"title": "procedure.md", "content": content}
    )
    assert status == 200
    label = {"run_id": output.name, "case_id": "A12", "path": "C", "attempt": 1}
    write(root / "active.json", label)
    start = perf_counter()
    status, response = request(
        api + "/run",
        {
            "user_id": user,
            "project_id": p["id"],
            "session_id": "paired",
            "run_id": "paired-1",
            "payload": question,
        },
    )
    rows = [
        {"arm": "CAIN", "status": status, "response": response, "seconds": perf_counter() - start}
    ]
    write(output / "arms.json", rows)
    workspace = WorkspaceStore(Path(proof["storage"]["db"]))
    corpus = workspace.document_corpus(user, p["id"])
    assert list(corpus.values()) == [content]
    settings = load_settings(root / "qa.toml")
    start = perf_counter()
    retriever = build_retriever(
        corpus=corpus,
        paths=[],
        search_mode=settings.search_mode,
        embedding=configured_embedding(settings),
        cache_path=output / "retrieval.sqlite3",
        allow_public_urls=False,
    )
    found = retriever.search(question, 3)
    rows.append(
        {
            "arm": "existing hybrid retriever",
            "response": [asdict(item) for item in found],
            "seconds": perf_counter() - start,
        }
    )
    write(output / "arms.json", rows)
    start = perf_counter()
    parsed = json.loads(next(iter(corpus.values())))
    rows.append(
        {
            "arm": "authorized structured lookup",
            "response": {k: parsed[k] for k in ("codigo", "prazo_dias")},
            "seconds": perf_counter() - start,
            "contract": "known JSON document fields; not general natural-language retrieval",
        }
    )
    write(output / "arms.json", rows)
    write(
        output / "state.json",
        {
            "project": p["id"],
            "document": doc,
            "corpus": corpus,
            "human_work_saved": "not measured",
            "quality": "review_required",
            "factual_denominator": 2,
            "source_equivalence": "same authorized document, no hidden evidence in any arm",
        },
    )
    print("A12 arms executed; manual paired review required")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--api", default="http://127.0.0.1:8896")
    a = p.parse_args()
    run(a.root, a.output, a.api)

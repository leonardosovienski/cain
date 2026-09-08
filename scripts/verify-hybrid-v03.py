"""Prepare/run a small synthetic retrieval comparison; no answer generation.

Nothing is written or sent to Ollama without --execute. A real run writes only
the specified evidence directory and refuses to overwrite existing evidence.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from urllib.request import urlopen

WORKSPACE = Path(__file__).resolve().parent.parent
PROJECT = WORKSPACE
DEFAULT_OUTPUT = PROJECT / "evaluation" / "results" / "retrieval-v03-01"
MODEL = "qwen3-embedding:0.6b"
DIGEST = "ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d"
SUITE_ID = "cain-retrieval-synthetic-v03-01"
QUERY_INSTRUCTION = "Retrieve relevant passages from the configured documents that answer the question."

# Invented fixtures: these statements are test data, not documentation of Cain.
DOCUMENTS = {
    "d01": "FONTE SINTÉTICA D01. Configurações pessoais ficam gravadas no disco. "
           "Depois do encerramento do programa, uma nova sessão recupera as escolhas salvas.\n",
    "d02": "FONTE SINTÉTICA D02. Cada projeto tem um compartimento separado. "
           "Conversas e documentos de um compartimento não são consultados pelos demais.\n",
    "d03": "FONTE SINTÉTICA D03. O catálogo pesquisável é uma cópia derivada. "
           "Se for apagado, pode ser reconstruído a partir dos registros originais preservados.\n",
    "d04": "FONTE SINTÉTICA D04. ERR-401 identifica uma credencial expirada. "
           "A sessão deve receber uma credencial renovada para prosseguir.\n",
    "d05": "FONTE SINTÉTICA D05. ERR-4012 identifica um anexo de formato incompatível. "
           "O arquivo precisa ser convertido para texto antes da importação.\n",
    "d06": "FONTE SINTÉTICA D06. Uma receita inventada de bolo usa farinha, "
           "ovos, açúcar e limão. A massa é colocada em uma forma redonda.\n",
}
CASES = [
    {"id": "p01", "kind": "paraphrase", "query": "Como lembrar minhas preferências quando eu voltar amanhã?",
     "relevant_documents": ["d01"], "label_reason": "Retenção de escolhas depois de encerrar e reabrir."},
    {"id": "p02", "kind": "paraphrase", "query": "Como impedir que assuntos de uma tarefa apareçam em outra?",
     "relevant_documents": ["d02"], "label_reason": "Separação de conversas e documentos entre projetos."},
    {"id": "p03", "kind": "paraphrase", "query": "Perdi a busca. Preciso começar todos os meus dados do zero?",
     "relevant_documents": ["d03"], "label_reason": "Reconstrução da cópia de pesquisa sem perder registros originais."},
    {"id": "i01", "kind": "literal_identifier", "query": "ERR-401",
     "relevant_documents": ["d04"], "label_reason": "Identificador literal; ERR-4012 é um distrator distinto."},
    {"id": "i02", "kind": "literal_identifier", "query": "ERR-4012",
     "relevant_documents": ["d05"], "label_reason": "Identificador literal de anexo incompatível."},
    {"id": "a01", "kind": "absence", "query": "Qual é a massa do satélite fictício SELENE-X9?",
     "relevant_documents": [], "label_reason": "Nenhuma fonte contém informações sobre esse satélite."},
]


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def get_json(url):
    with urlopen(url, timeout=10) as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("Ollama preflight response exceeded 2 MiB")
    return json.loads(body.decode("utf-8"))


def backend_identity(project):
    files = ["src/cain/search/__init__.py", "src/cain/search/hybrid.py", "src/cain/search/embeddings.py"]
    result = {"project_root": str(project), "file_sha256": {
        relative: sha256((project / relative).read_bytes()).hexdigest() for relative in files
    }}
    for name, args in (("git_commit", ["rev-parse", "HEAD"]), ("git_status", ["status", "--short"])):
        process = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, encoding="utf-8", check=False)
        result[name] = process.stdout.strip() if process.returncode == 0 else None
    return result


def serialize_ranking(results, sources):
    serialized = []
    for rank, result in enumerate(results, 1):
        item = asdict(result)
        source = sources.get(result.source)
        document_id = source["document_id"] if source else None
        decoded = DOCUMENTS.get(document_id, "")
        offsets_match = (
            source is not None and isinstance(result.start_offset, int) and isinstance(result.end_offset, int)
            and 0 <= result.start_offset <= result.end_offset <= len(decoded)
            and decoded[result.start_offset:result.end_offset] == result.text
        )
        hash_matches = source is not None and result.document_hash == source["document_hash"]
        item.update(rank=rank, document_id=document_id, excerpt=result.text,
                    excerpt_hash=sha256(result.text.encode("utf-8")).hexdigest(),
                    offsets_match_saved_source=offsets_match, document_hash_matches=hash_matches)
        serialized.append(item)
    return serialized


def score_case(case, ranking):
    if case["kind"] == "absence":
        return {
            "scored": False,
            "reason": "Absence is an observation of retrieval candidates, not an answer or hallucination test.",
            "candidate_count": len(ranking),
        }
    relevant = set(case["relevant_documents"])
    ranks = [item["rank"] for item in ranking if item["document_id"] in relevant]
    return {"scored": True, "hit_at_1": int(bool(ranks) and min(ranks) == 1),
            "hit_at_k": int(bool(ranks)), "first_relevant_rank": min(ranks) if ranks else None,
            "reciprocal_rank": 1.0 / min(ranks) if ranks else 0.0}


def summarize(cases, mode):
    successful = [case["retrievers"][mode] for case in cases if case["retrievers"][mode]["status"] == "ok"]
    scored = [item["metrics"] for item in successful if item["metrics"]["scored"]]
    return {
        "total_cases": len(cases), "successful_cases": len(successful),
        "execution_errors": len(cases) - len(successful), "scored_positive_cases": len(scored),
        "hit_at_1": sum(item["hit_at_1"] for item in scored) / len(scored) if scored else None,
        "hit_at_k": sum(item["hit_at_k"] for item in scored) / len(scored) if scored else None,
        "mean_reciprocal_rank": sum(item["reciprocal_rank"] for item in scored) / len(scored) if scored else None,
        "absence_cases_excluded_from_metrics": True,
    }


def render_summary(report):
    def first_document(entry):
        if entry["status"] != "ok":
            return "erro de execução"
        return entry["ranking"][0]["document_id"] if entry["ranking"] else "nenhum candidato"

    lines = [
        "# Verificação sintética de recuperação lexical e híbrida",
        "",
        ("Seis consultas e seis fontes inventadas, rotuladas antes da execução. "
         "Este diagnóstico não mede qualidade geral nem foi separado como holdout."),
        "Não houve geração de respostas, teste de alucinação ou uso de documentos pessoais.",
        "",
        f"Modelo de embedding: `{report['config']['model']}`; digest: `{report['config']['model_digest']}`.",
        "",
        "| Caso | Tipo | Lexical: primeiro documento | Híbrida: primeiro documento | Lexical ms | Híbrida ms |",
        "|---|---|---|---|---:|---:|",
    ]
    for case in report["cases"]:
        modes = case["retrievers"]
        lines.append(f"| {case['id']} | {case['kind']} | {first_document(modes['lexical'])} | {first_document(modes['hybrid'])} | "
                     f"{modes['lexical']['latency_ms']:.2f} | {modes['hybrid']['latency_ms']:.2f} |")
    lines += [
        "", "## Interpretação", "",
        ("Os acertos e MRR em `results.json` consideram apenas as cinco consultas com fonte relevante rotulada. "
        "O caso de ausência apenas mostra quais candidatos o retriever devolveu. Recuperar um trecho nessa "
        "consulta não significa que o sistema respondeu ao pedido nem que alucinou."),
        "",
        ("Os valores de score pertencem a algoritmos distintos e não são probabilidades comparáveis. "
         "Identificadores exatos têm prioridade no ranking híbrido; o metadado explica essa prioridade."),
        "",
        ("O cache derivado começa vazio neste diretório. A primeira consulta híbrida inclui o cálculo dos "
        "embeddings dos documentos; as seguintes reutilizam esses vetores e calculam apenas novas consultas. "
        "A residência prévia do modelo na GPU não foi controlada. As latências são observações desta ordem "
        "de execução, sem conclusão geral de desempenho ou comparação justa de estados frios/quentes."),
        "",
        ("`dataset.json` preserva textos e rótulos; `source-manifest.json` preserva arquivos/hashes; "
        "`cases/` preserva rankings, offsets, trechos, configuração do modelo e erros. "
        "`embedding-calls.json` registra chamadas ao provider, não pensamentos nem respostas de LLM."),
    ]
    return "\n".join(lines) + "\n"


def execute(args):
    project, output = args.project_root.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Evidence directory is not empty; use another --output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    config = {
        "suite_id": SUITE_ID, "synthetic_sources": True, "general_quality_claim": False,
        "model": args.model, "model_digest": args.digest, "base_url": args.base_url,
        "k": args.k, "lexical_weight": 0.45, "semantic_weight": 0.55,
        "min_semantic_score": 0.35, "query_instruction": QUERY_INSTRUCTION,
        "embedding_dimensions_requested": None, "truncate": False, "timeout_seconds": 60,
        "max_input_chars": 8192, "max_batch_size": 32, "max_chunks": 30,
        "max_files": 6, "max_file_bytes": 16384, "max_query_chars": 4096,
        "chunk_chars": 1500, "chunk_stride_chars": 1200,
        "cache_policy": "Fresh per run; documents reused after first query; no prewarming.",
        "server_model_residency_at_start": "not controlled or measured",
        "answer_generation": False, "absence_scoring": "diagnostic only; excluded from hit/MRR",
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "backend": backend_identity(project),
    }
    save_json(output / "config.json", config)
    dataset = {"suite_id": SUITE_ID, "synthetic": True, "holdout": False,
               "documents": DOCUMENTS, "cases": CASES}
    save_json(output / "dataset.json", dataset)
    config["dataset_sha256"] = sha256((output / "dataset.json").read_bytes()).hexdigest()
    manifest = []
    for document_id, text in DOCUMENTS.items():
        path = output / "synthetic_sources" / f"{document_id}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        manifest.append({"document_id": document_id, "source": str(path), "synthetic": True,
                         "document_hash": sha256(path.read_bytes()).hexdigest(),
                         "bytes": path.stat().st_size, "encoding": "utf-8", "characters": len(text)})
    save_json(output / "source-manifest.json", manifest)
    try:
        tags = get_json(args.base_url.rstrip("/") + "/api/tags")
        matching = [tag for tag in tags.get("models", []) if args.model in (tag.get("name"), tag.get("model"))]
        if len(matching) != 1:
            raise ValueError("The configured embedding model is absent or ambiguous in /api/tags; no model will be downloaded.")
        installed = matching[0]
        if installed.get("digest", "").removeprefix("sha256:") != args.digest.removeprefix("sha256:"):
            raise ValueError("Installed model digest differs from the pinned digest; no embedding was requested.")
        config["installed_model"] = installed
        config["ollama_version"] = get_json(args.base_url.rstrip("/") + "/api/version")
        save_json(output / "config.json", config)
    except Exception as exc:
        save_json(output / "preflight-error.json", {"type": type(exc).__name__, "message": str(exc)})
        raise

    sys.path.insert(0, str(project / "src"))
    from cain.search import (
        HybridDocumentRetriever,
        LocalDocumentRetriever,
        OllamaEmbedding,
    )

    embedding_calls = []

    class RecordedEmbedding(OllamaEmbedding):
        def embed(self, texts):
            started = perf_counter()
            event = {"provider_call_number": len(embedding_calls) + 1, "model": self.model,
                     "model_digest": self.model_digest, "input_count": len(texts),
                     "inputs": [{"sha256": sha256(text.encode("utf-8")).hexdigest(), "characters": len(text)}
                                for text in texts]}
            try:
                vectors = super().embed(texts)
                event.update(status="ok", dimensions=len(vectors[0]) if vectors else None)
                return vectors
            except (ValueError, RuntimeError, OSError, TypeError, KeyError) as exc:
                event.update(status="error", error_type=type(exc).__name__, error=str(exc))
                raise
            finally:
                event["latency_ms"] = (perf_counter() - started) * 1000
                embedding_calls.append(event)
                save_json(output / "embedding-calls.json", embedding_calls)

    provider = RecordedEmbedding(model=args.model, model_digest=args.digest, base_url=args.base_url,
                                 timeout=60, max_input_chars=8192, max_batch_size=32)
    paths = [Path(item["source"]) for item in manifest]
    retrievers = {
        "lexical": LocalDocumentRetriever(paths=paths, max_files=6, max_file_bytes=16384),
        "hybrid": HybridDocumentRetriever(
            paths=paths, embedding=provider, cache_path=output / "derived" / "embeddings.sqlite",
            lexical_weight=0.45, semantic_weight=0.55, min_semantic_score=0.35,
            max_files=6, max_file_bytes=16384, max_chunks=30, max_query_chars=4096,
            query_instruction=QUERY_INSTRUCTION,
        ),
    }
    sources = {item["source"]: item for item in manifest}
    outcomes = []
    for case in CASES:
        outcome = {**case, "retrievers": {}}
        for mode, retriever in retrievers.items():
            started = perf_counter()
            result = {"mode": mode, "model": args.model if mode == "hybrid" else None,
                      "model_digest": args.digest if mode == "hybrid" else None}
            try:
                ranking = serialize_ranking(retriever.search(case["query"], k=args.k), sources)
                result.update(ranking=ranking)
                if any(not item["offsets_match_saved_source"] or not item["document_hash_matches"] for item in ranking):
                    raise ValueError("Returned evidence does not match the saved source bytes/offsets")
                result.update(status="ok", metrics=score_case(case, ranking))
            except (ValueError, RuntimeError, OSError, TypeError, KeyError) as exc:
                result.update(status="error", error_type=type(exc).__name__, error=str(exc),
                              ranking=result.get("ranking", []))
            finally:
                result["latency_ms"] = (perf_counter() - started) * 1000
                outcome["retrievers"][mode] = result
        outcomes.append(outcome)
        save_json(output / "cases" / f"{case['id']}.json", outcome)
        print(json.dumps({"case": case["id"], "lexical": outcome["retrievers"]["lexical"]["status"],
                          "hybrid": outcome["retrievers"]["hybrid"]["status"]}, ensure_ascii=False), flush=True)
    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(), "config": config, "cases": outcomes,
        "summary": {mode: summarize(outcomes, mode) for mode in retrievers},
        "scope": "Small synthetic diagnostic of retrieval only; not a holdout, answer evaluation, or general quality claim.",
    }
    save_json(output / "results.json", report)
    (output / "summary.md").write_text(render_summary(report), encoding="utf-8")
    print(f"Evidence: {output}")
    return int(any(report["summary"][mode]["execution_errors"] for mode in retrievers))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Explicitly execute real embedding requests.")
    parser.add_argument("--project-root", type=Path, default=PROJECT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--digest", default=DIGEST)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if not args.execute:
        print(f"Prepared only: {len(CASES)} synthetic queries, {len(DOCUMENTS)} synthetic sources. "
              f"Use --execute to call {args.model} and write {args.output}.")
        return 0
    if not 1 <= args.k <= len(DOCUMENTS):
        parser.error("--k must be between 1 and 6")
    try:
        return execute(args)
    except (ValueError, RuntimeError, OSError, TypeError, KeyError) as exc:
        print(f"Verification failed without fallback: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


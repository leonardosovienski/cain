"""Predetermined generator comparison; automatic checks never select a quality winner."""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
from time import perf_counter
from urllib.request import urlopen
import uuid


@dataclass(frozen=True)
class QualityConfig:
    models: tuple[str, ...] = ("qwen2.5:3b", "qwen3.5:4b")
    provider: str = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.0
    seed: int = 42
    timeout: float = 120.0
    num_ctx: int = 8192
    num_predict: int = 768
    max_input_bytes: int = 6500
    think: bool | None = None
    split: str = "all"
    run_id: str | None = None


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append(path: Path, data: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_dataset(path: Path | None = None) -> tuple[dict, Path]:
    path = Path(path) if path else Path(__file__).resolve().parents[3] / "evaluation/scenarios/quality-v03.json"
    design = json.loads(path.read_text(encoding="utf-8"))
    cases = design["cases"]
    if not 12 <= len(cases) <= 16 or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Dataset requires 12–16 cases with unique IDs")
    if {case["split"] for case in cases} != {"dev", "holdout"}:
        raise ValueError("Dataset must identify development and holdout cases")
    for case in cases:
        if not case["prompt"].strip() or not case["context"].strip():
            raise ValueError("Every case requires fixed nonempty prompt and context")
        if case["response_mode"] not in {"text", "json"}:
            raise ValueError("Unknown response mode")
        if case["response_mode"] == "json" and not case.get("schema"):
            raise ValueError("Structured cases require a JSON schema")
        for group in case["checks"].get("required_any", []):
            if not group:
                raise ValueError("Required fact groups must contain a pattern")
            for pattern in group:
                re.compile(pattern)
        for pattern in case["checks"].get("forbidden", []):
            re.compile(pattern)
    return design, path


def model_input(case: dict) -> dict:
    """Only these fields are handed to the provider. Labels and answer keys stay out."""
    result = {"prompt": case["prompt"], "context": case["context"]}
    if case["response_mode"] == "json":
        result["schema"] = deepcopy(case["schema"])
    return result


def _check(name: str, kind: str, passed: bool | None, observed=None, reason: str | None = None) -> dict:
    return {"name": name, "kind": kind, "passed": passed, "observed": observed, "reason": reason}


def _schema_valid(value, schema: dict) -> bool:
    """The small schema subset used by this fixture, not a general JSON Schema validator."""
    if schema.get("type") != "object" or not isinstance(value, dict):
        return False
    properties = schema.get("properties", {})
    if not set(schema.get("required", [])).issubset(value):
        return False
    if schema.get("additionalProperties") is False and not set(value).issubset(properties):
        return False
    for key, item in value.items():
        property_schema = properties.get(key, {})
        if property_schema.get("type") == "string" and not isinstance(item, str):
            return False
        if "enum" in property_schema and item not in property_schema["enum"]:
            return False
    return True


def _strict_json(text: str):
    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Non-JSON numeric constant: {value}")

    return json.loads(text, object_pairs_hook=pairs_hook, parse_constant=constant)


def assess(case: dict, response: str) -> list[dict]:
    """Syntax/exact labels are mechanical; factual regex matches are explicitly heuristic."""
    expected = case["checks"]
    checks = []
    if case["response_mode"] == "json":
        try:
            value = _strict_json(response)
        except (ValueError, TypeError) as error:
            checks.append(_check("json_valid", "deterministic", False, reason=str(error)))
            checks.append(_check("json_schema_valid", "deterministic", False))
            checks.append(_check("route_label_exact", "deterministic", False))
        else:
            schema_valid = _schema_valid(value, case["schema"])
            checks.append(_check("json_valid", "deterministic", True))
            checks.append(_check("json_schema_valid", "deterministic", schema_valid))
            actual = value.get("agent") if isinstance(value, dict) else None
            checks.append(_check("route_label_exact", "deterministic",
                                 schema_valid and actual == expected["expected_agent"], actual))
    for index, patterns in enumerate(expected.get("required_any", []), 1):
        matches = [pattern for pattern in patterns if re.search(pattern, response, re.I)]
        checks.append(_check(f"required_fact_{index}", "heuristic", bool(matches), matches,
                             "Pattern presence does not prove entailment or factual correctness"))
    if "forbidden" in expected:
        matches = [pattern for pattern in expected["forbidden"] if re.search(pattern, response, re.I)]
        checks.append(_check("forbidden_fact_patterns_absent", "heuristic", not matches, matches,
                             "Selected patterns cannot detect every contradiction or invented fact"))
    if "allowed_citations" in expected:
        markers = re.findall(r"\[([A-Za-z]*\d+)\]", response)
        unknown = sorted(set(markers) - set(expected["allowed_citations"]))
        checks.append(_check("citation_identifiers_allowed", "deterministic", not unknown,
                             {"observed": markers, "unknown": unknown},
                             "Checks identifier membership, not whether cited prose supports each claim"))
        required = set(expected.get("required_citations", []))
        checks.append(_check("required_citations_present", "deterministic", required.issubset(markers), markers))
    if "max_words" in expected:
        count = len(re.findall(r"\b[\w'-]+\b", response))
        checks.append(_check("word_count_within_limit", "deterministic", count <= expected["max_words"],
                             {"count_by_regex": count, "limit": expected["max_words"]}))
    if "numbered_lines" in expected:
        numbers = re.findall(r"(?m)^\s*(\d+)[.)]\s+", response)
        wanted = [str(i) for i in range(1, expected["numbered_lines"] + 1)]
        checks.append(_check("numbered_lines_exact", "deterministic", numbers == wanted, numbers))
    if expected.get("single_paragraph"):
        paragraphs = [part for part in re.split(r"\n\s*\n", response.strip()) if part.strip()]
        lists = bool(re.search(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)", response))
        checks.append(_check("single_paragraph_without_list", "deterministic",
                             len(paragraphs) == 1 and not lists,
                             {"paragraphs_by_blank_lines": len(paragraphs), "list_markers": lists}))
    if "language_expected" in expected:
        checks.append(_check("language_appropriateness", "human_required", None,
                             {"expected": expected["language_expected"]},
                             "No language classifier is configured; fact-word matching is not language validation"))
    if "python" in expected:
        blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", response, re.S | re.I)
        code = blocks[0] if len(blocks) == 1 else response if "```" not in response else None
        try:
            if code is None:
                raise ValueError("Expected one unambiguous Python block or raw code")
            tree = ast.parse(code)
        except (ValueError, SyntaxError) as error:
            checks.append(_check("python_syntax", "deterministic", False, reason=str(error)))
            checks.append(_check("python_function_parameters", "deterministic", False))
        else:
            spec = expected["python"]
            functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                         and node.name == spec["function"]]
            names = [arg.arg for arg in functions[0].args.posonlyargs + functions[0].args.args] \
                if len(functions) == 1 else None
            checks.append(_check("python_syntax", "deterministic", True,
                                 reason="Parsed with ast.parse; generated code was NOT executed"))
            checks.append(_check("python_function_parameters", "deterministic",
                                 names == spec["parameters"], names,
                                 "Signature names do not establish algorithm correctness or safety"))
    return checks


def _provider(model: str, config: QualityConfig):
    from cain.llm import OllamaLLM

    options = {"model": model, "base_url": config.base_url, "temperature": config.temperature,
               "seed": config.seed, "timeout": config.timeout, "num_ctx": config.num_ctx,
               "num_predict": config.num_predict, "max_input_bytes": config.max_input_bytes}
    if config.think is not None:
        options["think"] = config.think
    return OllamaLLM(**options)


def _backend(config: QualityConfig) -> dict:
    if config.provider == "injected-test":
        return {"backend_version": None, "models": {}, "reason": "Injected test providers, not real models"}
    observed = {"backend_version": None, "models": {}}
    for endpoint in ("version", "tags"):
        try:
            with urlopen(config.base_url.rstrip("/") + "/api/" + endpoint,
                         timeout=min(config.timeout, 10.0)) as handle:
                payload = json.loads(handle.read().decode("utf-8"))
            if endpoint == "version":
                observed["backend_version"] = payload.get("version")
            else:
                for model in config.models:
                    observed["models"][model] = next((entry for entry in payload.get("models", [])
                                                       if model in (entry.get("model"), entry.get("name"))), None)
        except (OSError, ValueError, TypeError, AttributeError) as error:
            observed[endpoint + "_error"] = f"{type(error).__name__}: {error}"
    return observed


def _code_identity() -> dict:
    root = Path(__file__).resolve().parents[3]
    def git(*args):
        try:
            result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True,
                                    encoding="utf-8", timeout=10, check=False)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    hashes = {str(path.relative_to(root)).replace("\\", "/"): _digest(path.read_bytes())
              for path in sorted((root / "src/cain").rglob("*.py"))}
    state = git("status", "--porcelain")
    return {"git_commit": git("rev-parse", "HEAD"), "git_dirty": bool(state) if state is not None else None,
            "source_sha256": hashes, "source_tree_sha256": _digest(json.dumps(hashes, sort_keys=True).encode())}


def _summary(records: list[dict], config: QualityConfig, cases: list[dict], run_id: str) -> dict:
    models = {}
    for model in config.models:
        rows = [row for row in records if row["model_requested"] == model]
        groups = {}
        for split in ("dev", "holdout"):
            subset = [row for row in rows if row["split"] == split]
            rates = defaultdict(lambda: {"passed": 0, "measured": 0})
            for row in subset:
                if row["status"] != "completed":
                    continue
                for check in row["checks"]:
                    if check["passed"] is not None:
                        metric = rates[check["kind"] + ":" + check["name"]]
                        metric["measured"] += 1
                        metric["passed"] += check["passed"] is True
            groups[split] = {"n": len(subset), "status_counts": dict(Counter(r["status"] for r in subset)),
                             "checks": dict(rates)}
        models[model] = {"attempts": len(rows), "status_counts": dict(Counter(row["status"] for row in rows)),
                         "truncation_unknown_count": sum(row["truncated"] is None for row in rows),
                         "wall_seconds": [row["wall_seconds"] for row in rows], "by_split": groups}
    identical = all(len({row["model_input_sha256"] for row in records if row["case_id"] == case["id"]}) == 1
                    for case in cases)
    return {"run_id": run_id, "provider": config.provider, "real_llm": config.provider == "ollama",
            "scientific_result": False, "planned_cases_per_model": len(cases), "models": models,
            "identical_model_input_per_case": identical, "quality_winner": None,
            "quality_winner_reason": "Regex, syntax and exact-label checks do not establish overall response quality",
            "human_quality": {"value": None, "reason": "No independent human ratings collected"},
            "comparison_scope": "Generator only: fixed prompt/context/schema; no Cain runtime or adaptive retrieval",
            "formal_collection_allowed": False}


def run_comparison(output: Path, config: QualityConfig | None = None, *, dataset_path: Path | None = None,
                   provider_factory=None) -> Path:
    config = config or QualityConfig()
    if not config.models or len(set(config.models)) != len(config.models):
        raise ValueError("Model names must be nonempty and unique")
    if config.split not in ("all", "dev", "holdout") or config.timeout <= 0:
        raise ValueError("Invalid split or timeout")
    if provider_factory is not None and config.provider != "injected-test":
        raise ValueError("Injected provider_factory requires provider=injected-test; cannot label fake output real")
    if provider_factory is None and config.provider != "ollama":
        raise ValueError("The CLI runs Ollama only; an explicit injected-test factory is required for tests")
    design, source = load_dataset(dataset_path)
    cases = [case for case in design["cases"] if config.split == "all" or case["split"] == config.split]
    random.Random(config.seed).shuffle(cases)
    run_id = config.run_id or "quality-v03-" + uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise ValueError("Invalid run_id")
    run_dir = Path(output) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "inputs").mkdir()
    (run_dir / "inputs/quality-v03.json").write_bytes(source.read_bytes())
    meta = {**asdict(config), "run_id": run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_sha256": _digest(source.read_bytes()), "dataset_version": design["version"],
            "case_order": [case["id"] for case in cases], "model_order": list(config.models),
            "execution_order": "One model at a time, same seeded case order for all models; no parallel inference",
            "backend_observation": _backend(config), **_code_identity(),
            "max_input_bytes_is_tokenizer": False, "same_strings_is_same_token_count": False,
            "determinism_guaranteed": False, "human_quality_collected": False,
            "hidden_from_model": ["case id", "split", "category", "checks and answer keys"],
            "holdout_policy": "Use dev for changes; inspect holdout only after freezing choices. Reusing holdout "
                              "to tune choices makes it exploratory, not an untouched confirmation set.",
            "scientific_result": False, "automatic_quality_winner_allowed": False,
            "latency_interpretation": "Wall time includes model loading; backend timings are raw observations, "
                                      "not controlled performance benchmark results"}
    _write(run_dir / "config.json", meta)
    records = []
    for model in config.models:
        provider, setup_error = None, None
        try:
            provider = (provider_factory or _provider)(model, config)
            meta.setdefault("adapters_observed", {})[model] = {
                name: getattr(provider, name, None) for name in (
                    "model", "temperature", "seed", "timeout", "num_ctx", "num_predict", "max_input_bytes", "think",
                )
            }
            _write(run_dir / "config.json", meta)
        except Exception as error:
            setup_error = error
        for case in cases:
            request = model_input(case)
            record = {"run_id": run_id, "case_id": case["id"], "split": case["split"],
                      "category": case["category"], "model_requested": model, "provider": config.provider,
                      "model_input": request,
                      "model_input_sha256": _digest(json.dumps(request, ensure_ascii=False, sort_keys=True).encode()),
                      "status": "started", "response": None, "provider_metadata": None,
                      "truncated": None, "checks": [], "started_at_utc": datetime.now(timezone.utc).isoformat()}
            started = perf_counter()
            try:
                if setup_error is not None:
                    raise setup_error
                response = provider.generate_json(**request) if case["response_mode"] == "json" \
                    else provider.generate(**request)
                if not isinstance(response, str) or not response.strip():
                    raise ValueError("Provider must return a nonempty raw response string")
                record["response"] = response
                record["provider_metadata"] = deepcopy(getattr(provider, "last_metadata", None))
                reason = (record["provider_metadata"] or {}).get("done_reason")
                record["truncated"] = True if reason in {"length", "max_tokens"} else False if reason == "stop" else None
                record["status"] = "truncated" if record["truncated"] else "completed"
                record["checks"] = assess(case, response)
            except Exception as error:
                metadata = deepcopy(getattr(provider, "last_metadata", None))
                partial = getattr(error, "partial_response", None)
                truncated = (metadata or {}).get("done_reason") in {"length", "max_tokens"} \
                    or type(error).__name__ == "LLMTruncated"
                record.update(status="truncated" if truncated else "error", error_type=type(error).__name__,
                              error=str(error), provider_metadata=metadata,
                              truncated=True if truncated else record["truncated"])
                if isinstance(partial, str):
                    record["response"] = partial
                    if partial.strip():
                        record["checks"] = assess(case, partial)
            record["wall_seconds"] = round(perf_counter() - started, 6)
            records.append(record)
            _append(run_dir / "raw.jsonl", record)
    metrics = _summary(records, config, cases, run_id)
    _write(run_dir / "metrics.json", metrics)
    lines = [f"# Comparação de geradores {run_id}", "",
             f"Provedor: `{config.provider}`. {len(cases)} casos por modelo. "
             "Mesmos prompt, contexto e schema por caso; nenhum gabarito foi enviado. "
             "O runtime e a recuperação do Cain não participam desta comparação.", "",
             "| Modelo | Completas | Erros | Truncadas reportadas |", "|---|---:|---:|---:|"]
    for model, values in metrics["models"].items():
        counts = values["status_counts"]
        lines.append(f"| {model} | {counts.get('completed', 0)} | {counts.get('error', 0)} | {counts.get('truncated', 0)} |")
    lines += ["", "Os resultados individuais estão em raw.jsonl. metrics.json separa desenvolvimento e holdout "
              "e mostra cada check sem compor uma nota geral. Resultados truncados/erros não entram nas taxas "
              "das respostas completas, mas permanecem nos denominadores de status e nos registros brutos.", "",
              "Presença/ausência de fatos por expressão regular é heurística e pode produzir falsos positivos "
              "ou negativos. Identificadores de fonte corretos não provam sustentação das afirmações. "
              "Validade de JSON, rótulo exato, contagem/formato textual e sintaxe/assinatura de Python são "
              "verificações limitadas ao que explicitamente medem. Nenhum código gerado foi executado.", "",
              "Qualidade humana não foi medida. Não há vencedor automático e não foi realizada coleta "
              "científica formal. Idioma apropriado requer revisão; palavras esperadas não substituem essa "
              "avaliação. Tempos incluem carga do modelo; não são um benchmark controlado de velocidade.", "",
              "A divisão holdout deve permanecer intocada durante ajustes. Se ela influenciar ajustes de "
              "prompt/modelo, registre a reutilização e trate seus resultados como exploratórios. "
              "Seeds e opções são registradas, sem promessa de determinismo. A guarda em bytes não é tokenização.", ""]
    lines += ["[Abrir respostas pareadas para inspeção](responses.md)", ""]
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    responses = [f"# Respostas observadas — {run_id}", "",
                 "Comparação identificada para inspeção; não são notas humanas nem avaliação cega.", ""]
    for case in cases:
        responses += [f"## {case['id']} ({case['split']})", "", f"Pedido: {case['prompt']}", ""]
        for row in (row for row in records if row["case_id"] == case["id"]):
            responses += [f"### {row['model_requested']} — {row['status']}", "",
                          row["response"] or f"Sem resposta: {row.get('error', 'não disponível')}", ""]
    (run_dir / "responses.md").write_text("\n".join(responses), encoding="utf-8")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comparação de geradores; checks não selecionam vencedor")
    parser.add_argument("--models", nargs="+", default=["qwen2.5:3b", "qwen3.5:4b"])
    parser.add_argument("--output", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--run-id")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--split", choices=("all", "dev", "holdout"), default="all")
    parser.add_argument("--think", choices=("default", "false", "true"), default="default")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=768)
    parser.add_argument("--max-input-bytes", type=int, default=6500)
    args = parser.parse_args(argv)
    options = vars(args).copy()
    output, dataset = options.pop("output"), options.pop("dataset")
    options["models"] = tuple(options["models"])
    options["think"] = {"default": None, "false": False, "true": True}[options["think"]]
    try:
        result = run_comparison(output, QualityConfig(**options), dataset_path=dataset)
    except Exception as error:
        print(f"Comparação não concluída: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(f"Artefatos: {result.resolve()}\nSem vencedor automático; qualidade humana não medida.")
    metrics = json.loads((result / "metrics.json").read_text(encoding="utf-8"))
    return 1 if any(value["status_counts"].get("error", 0) or value["status_counts"].get("truncated", 0)
                    for value in metrics["models"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())

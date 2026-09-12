"""Observed functional checks with real process restarts; no claims of scientific quality."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

from .budget import CharacterCounter, RecordingLLM, adapter_options
from .resources import installed_identity
from .harness import EvaluationConfig, _append, _json, _model, _prepare, load_design
from .metrics import delegation_metrics, unavailable


FUNCTIONAL_CORPUS = {
    "guia-funcional-cain.txt": (
        "Guia funcional sintético do Cain. O código do procedimento Boreal é BOREAL-731. "
        "Para esse procedimento, o prazo estabelecido no corpus é exatamente 7 dias. "
        "Estes são dados artificiais para verificar recuperação e atribuição de fonte."
    )
}


def functional_plan(run_id: str) -> list[dict]:
    """Freeze these instructions before any response is observed."""
    primary = f"{run_id}-alice"
    other = f"{run_id}-bruno"
    return [
        {"id": "01-declare", "user_id": primary, "session_id": "session-1", "intent": "resumo",
         "expected_agent": "resumo", "expected_format": "steps",
         "prompt": "Prefiro respostas em passos. Confirme brevemente essa preferência."},
        {"id": "02-reopen-code", "user_id": primary, "session_id": "session-2", "intent": None,
         "expected_agent": "codigo", "expected_format": "steps",
         "prompt": "Escreva código Python para uma função soma(a, b) que retorne a soma dos dois argumentos. "
                   "Explique brevemente, considerando minhas preferências já declaradas."},
        {"id": "03-correct", "user_id": primary, "session_id": "session-3", "intent": "resumo",
         "expected_agent": "resumo", "expected_format": "paragraph",
         "prompt": "Agora prefiro respostas em parágrafo. Confirme brevemente a mudança."},
        {"id": "04-reopen-summary", "user_id": primary, "session_id": "session-4", "intent": None,
         "expected_agent": "resumo", "expected_format": "paragraph",
         "prompt": "Resuma somente este texto, considerando minhas preferências já declaradas: "
                   "O projeto sintético Aurora tem três etapas: planejar, executar e verificar. "
                   "A etapa de verificação compara o resultado com o requisito."},
        {"id": "05-other-user", "user_id": other, "session_id": "other-session-1", "intent": "resumo",
         "expected_agent": "resumo", "expected_format": None,
         "prompt": "Qual formato de resposta eu declarei preferir? Se não houver declaração minha, "
                   "diga que não sabe."},
        {"id": "06-search-source", "user_id": primary, "session_id": "session-5", "intent": None,
         "expected_agent": "busca", "expected_format": "paragraph",
         "prompt": "Busque no corpus local o código do procedimento Boreal e seu prazo. "
                   "Responda com a fonte consultada."},
    ]


def source_metadata(project_root: Path) -> dict:
    def git(*args):
        try:
            result = subprocess.run(["git", "-C", str(project_root), *args], capture_output=True,
                                    text=True, encoding="utf-8", timeout=10, check=False)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    files = sorted((project_root / "src/cain").rglob("*.py"))
    hashes = {str(path.relative_to(project_root)).replace("\\", "/"):
              sha256(path.read_bytes()).hexdigest() for path in files}
    status = git("status", "--porcelain")
    return {"git_commit": git("rev-parse", "HEAD"),
            "git_dirty": bool(status) if status is not None else None,
            "git_status": status, "source_sha256": hashes,
            "source_tree_sha256": sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}


def ollama_metadata(config: EvaluationConfig) -> dict:
    """Observe the installed model digest and backend version; do not infer either."""
    output = {"model_requested": config.model, "model_digest": None, "backend_version": None}
    for endpoint in ("tags", "version"):
        try:
            with urlopen(config.base_url.rstrip("/") + "/api/" + endpoint,
                         timeout=min(10.0, config.request_timeout)) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if endpoint == "version":
                output["backend_version"] = payload.get("version")
            else:
                match = next((model for model in payload.get("models", [])
                              if config.model in (model.get("name"), model.get("model"))), None)
                output["observed_model"] = match
                if match:
                    output["model_digest"] = match.get("digest")
        except (OSError, ValueError, TypeError, AttributeError) as error:
            output[endpoint + "_error"] = f"{type(error).__name__}: {error}"
    if output["model_digest"] is None:
        output["model_digest_reason"] = "The requested model digest was not observed in /api/tags"
    return output


def execute_stage(request: dict, *, llm=None) -> dict:
    """One runtime lifetime. Used in a fresh process by the real CLI and directly in tests."""
    from cain.runtime import build_cain

    config = EvaluationConfig(**request["config"])
    stage = request["stage"]
    request_run_id = request["run_id"] + "-" + stage["id"]
    recorder = RecordingLLM(llm if llm is not None else _model(config), CharacterCounter())
    runtime = None
    record = {
        "run_id": request["run_id"], "request_run_id": request_run_id,
        "stage_id": stage["id"], "stage": stage, "pid": os.getpid(), "status": "started",
        "llm_calls": recorder.calls, "response": None, "selected_agent": None,
        "context_budget_applied": False,
    }
    try:
        runtime = build_cain(request["db_path"], llm=recorder, corpus=request["corpus"], source_paths=[])
        record["state_before"] = runtime.identity.inspect(stage["user_id"])
        result = runtime.run(user_id=stage["user_id"], session_id=stage["session_id"],
                             payload=stage["prompt"], intent=stage["intent"], run_id=request_run_id)
        record.update(status="completed", response=result.response, selected_agent=result.selected_agent,
                      decision_id=result.decision_id, steps=list(result.steps))
        record["state_after"] = runtime.identity.inspect(stage["user_id"])
    except Exception as error:
        record.update(status="failed", error_type=type(error).__name__, error=str(error))
    finally:
        if runtime is not None:
            try:
                if "state_after" not in record:
                    record["state_after"] = runtime.identity.inspect(stage["user_id"])
                record["decisions"] = [asdict(value) for value in runtime.decision_log.export(request_run_id)]
            except Exception as error:
                record.update(status="failed", audit_export_error=f"{type(error).__name__}: {error}")
            finally:
                try:
                    runtime.close()
                except Exception as error:
                    record.update(status="failed", close_error=f"{type(error).__name__}: {error}")
    return record


def _format(record: dict, when: str = "after"):
    return record.get("state_" + when, {}).get("user_model", {}).get("preferences", {}).get("format")


def _check(check_id: str, passed: bool | None, reason: str, stage_ids: list[str]) -> dict:
    return {"id": check_id, "passed": passed, "reason": reason, "stage_ids": stage_ids}


def functional_checks(records: list[dict], plan: list[dict], process_mode: bool) -> list[dict]:
    by_id = {record["stage_id"]: record for record in records}
    checks = []
    for stage in plan:
        record = by_id.get(stage["id"])
        complete = record is not None and record["status"] == "completed"
        checks.append(_check(stage["id"] + ":completed", complete,
                             "Runtime completed the planned request" if complete else
                             "Request failed or was not run; consult raw/failure records", [stage["id"]]))
        if not complete:
            continue
        checks.append(_check(stage["id"] + ":route", record["selected_agent"] == stage["expected_agent"],
                             "Compare observed agent with ground truth written in the plan", [stage["id"]]))
        checks.append(_check(stage["id"] + ":format", _format(record) == stage["expected_format"],
                             "Compare persisted format with the explicit preference expected at this stage",
                             [stage["id"]]))
        calls = record.get("llm_calls", [])
        checks.append(_check(stage["id"] + ":llm_generation",
                             bool(calls) and all(call["status"] == "completed" for call in calls),
                             "At least one observed generation call completed; quality needs human review",
                             [stage["id"]]))
        current_format = _format(record)
        if current_format:
            checks.append(_check(stage["id"] + ":context_preference",
                                 any(f'"format": "{current_format}"' in call["context"] for call in calls),
                                 "Current persisted preference is present in the actual LLM context",
                                 [stage["id"]]))
    for stage_id, expected in (("02-reopen-code", "steps"), ("04-reopen-summary", "paragraph")):
        record = by_id.get(stage_id, {})
        checks.append(_check(stage_id + ":persisted_before_input", _format(record, "before") == expected,
                             "Preference was loaded from the database before the new request was observed",
                             [stage_id]))
    complete = [record for record in records if record.get("state_after")]
    personalities = [record["state_after"]["personality"] for record in complete]
    checks.append(_check("personality_stable", bool(personalities) and
                         all(personality == personalities[0] for personality in personalities),
                         "Compare immutable personality values across all observed user states",
                         [record["stage_id"] for record in complete]))
    other = by_id.get("05-other-user", {})
    other_profile = other.get("state_after", {}).get("user_model", {}).get("preferences")
    other_context = "\n".join(call["context"] for call in other.get("llm_calls", []))
    primary_id = plan[0]["user_id"]
    checks.append(_check("other_user_isolated", other_profile == {} and primary_id not in other_context,
                         "Other user has no preferences and actual injected context has no primary-user ID",
                         ["05-other-user"]))
    search = by_id.get("06-search-source", {})
    search_response = search.get("response") or ""
    search_context = "\n".join(call["context"] + "\n" + call["prompt"]
                               for call in search.get("llm_calls", []))
    checks.append(_check("search_source_recorded", "guia-funcional-cain.txt" in search_response
                         and "BOREAL-731" in search_context,
                         "Response identifies the supplied corpus source and LLM received its actual evidence; "
                         "this check does not establish faithful summarization", ["06-search-source"]))
    pids = [record.get("pid") for record in records]
    checks.append(_check("process_restart", len(set(pids)) == len(plan) if process_mode else None,
                         "Each real stage executed in a distinct subprocess" if process_mode else
                         "Injected test provider: only runtime close/reopen was exercised, not process restart",
                         [record["stage_id"] for record in records]))
    return checks


def run_functional(output: Path, config: EvaluationConfig, *, data_root: Path | None = None,
                   llm=None) -> Path:
    """CLI requires Ollama. Explicitly injected providers are mechanical test fixtures only."""
    if config.mode != "functional":
        raise ValueError("run_functional requires mode=functional")
    if llm is None and config.provider != "ollama":
        raise ValueError("Functional CLI requires provider=ollama; fake is prohibited")
    if llm is not None and config.provider != "injected-test":
        raise ValueError("Injected provider must be labeled provider=injected-test")
    _, _, root = load_design(data_root)
    run_dir, run_id = _prepare(output, config, root)
    run_dir = run_dir.resolve()
    (run_dir / "stages").mkdir()
    plan = functional_plan(run_id)
    _json(run_dir / "inputs/functional_plan.json", plan)
    _json(run_dir / "inputs/functional_corpus.json", FUNCTIONAL_CORPUS)
    metadata = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    metadata.update(
        installed_identity(),
        execution_kind="subprocess_per_stage" if llm is None else "injected_test_runtime_restart",
        scientific_claims_allowed=False, context_counter=None, context_budget_applied=False,
        blind_export=None, functional_review="Identified responses for inspection; no blind human ratings collected",
        generation_controls={"temperature_requested": config.temperature, "seed_requested": config.seed,
                             "determinism_guaranteed": False,
                             "adapter_options": adapter_options(llm if llm is not None else _model(config)),
                             "adapter_options_scope": "Actual local adapter settings requested from the backend; "
                             "reported generation counts are recorded separately per call",
                             "max_input_bytes_is_tokenizer": False},
        functional_plan_sha256=sha256((run_dir / "inputs/functional_plan.json").read_bytes()).hexdigest(),
        model_observation=ollama_metadata(config) if llm is None else
        {"model_digest": None, "reason": "Injected test double; not a real model"},
        execution_order="Six predetermined stages; each real stage uses a fresh process",
    )
    _json(run_dir / "config.json", metadata)
    records = []
    for stage in plan:
        request = {"config": asdict(config), "run_id": run_id, "stage": stage,
                   "db_path": str(run_dir / "cain.sqlite3"), "corpus": FUNCTIONAL_CORPUS}
        request_path = run_dir / "stages" / (stage["id"] + "-request.json")
        response_path = run_dir / "stages" / (stage["id"] + "-result.json")
        _json(request_path, request)
        if llm is not None:
            record = execute_stage(request, llm=llm)
            _json(response_path, record)
        else:
            try:
                completed = subprocess.run(
                    [sys.executable, "-m", "cain.evaluation.functional_worker", "--request",
                     str(request_path), "--response", str(response_path)],
                    capture_output=True, text=True, encoding="utf-8", check=False,
                    timeout=config.request_timeout + 45,
                )
                if not response_path.is_file():
                    raise RuntimeError(f"Worker produced no result; exit={completed.returncode}; "
                                       f"stderr={completed.stderr[-4000:]}")
                record = json.loads(response_path.read_text(encoding="utf-8"))
                if completed.returncode and record["status"] == "completed":
                    record.update(status="failed", process_exit_code=completed.returncode)
            except (OSError, ValueError, subprocess.TimeoutExpired, RuntimeError) as error:
                record = {"run_id": run_id, "stage_id": stage["id"], "stage": stage,
                          "status": "failed", "error_type": type(error).__name__, "error": str(error),
                          "response": None, "llm_calls": []}
                _json(response_path, record)
        records.append(record)
        _append(run_dir / "raw.jsonl", record)
        for decision in record.get("decisions", []):
            _append(run_dir / "decisions.jsonl", decision)
        if record["status"] != "completed":
            _json(run_dir / "failure.json", {
                "run_id": run_id, "failed_stage": stage["id"], "failure": record,
                "not_run": [item["id"] for item in plan[len(records):]],
                "reason": "Stopped after an observed failure; no silent provider fallback or invented responses",
            })
            break
    checks = functional_checks(records, plan, llm is None)
    metrics = {
        "run_id": run_id, "mode": "functional", "provider": config.provider,
        "real_llm": llm is None, "scientific_result": False,
        "planned_stages": len(plan), "recorded_stages": len(records),
        "functional_success": len(records) == len(plan) and all(check["passed"] is not False for check in checks),
        "checks": checks,
        "delegation": delegation_metrics((record["stage"]["expected_agent"], record["selected_agent"])
                                          for record in records if record["status"] == "completed"),
        "preference_observations": [{"stage_id": record["stage_id"], "format_before": _format(record, "before"),
                                     "format_after": _format(record)} for record in records],
        "profile_convergence": unavailable(
            "The declared target intentionally changes from steps to paragraph; no single-target convergence "
            "is computed across the correction. Per-stage stored values are compared mechanically."),
        "human_response_quality": unavailable("No independent human ratings; inspect the real responses"),
        "construct_validity": unavailable("Functional persistence checks do not validate personality/adaptation constructs"),
        "formal_collection_allowed": False,
    }
    _json(run_dir / "metrics.json", metrics)
    _report(run_dir, run_id, metadata, records, metrics)
    return run_dir


def _report(run_dir: Path, run_id: str, metadata: dict, records: list[dict], metrics: dict) -> None:
    lines = [f"# Demonstração funcional {run_id}", "",
             f"Provedor: `{metrics['provider']}`. Etapas registradas: {len(records)}/{metrics['planned_stages']}. "
             f"Verificações mecânicas: {'passaram' if metrics['functional_success'] else 'há falhas'}. "
             "Esta execução não é resultado científico nem avaliação humana da qualidade.", "",
             f"Commit observado: `{metadata.get('git_commit')}`; árvore modificada: `{metadata.get('git_dirty')}`. "
             f"Digest do modelo observado: `{metadata.get('model_observation', {}).get('model_digest')}`.", "",
             "| Verificação | Resultado |", "|---|---|"]
    for check in metrics["checks"]:
        status = "passou" if check["passed"] is True else "falhou" if check["passed"] is False else "não medido"
        lines.append(f"| {check['id']} | {status} |")
    lines.extend(["", "## Respostas observadas", ""])
    for record in records:
        lines.extend([f"### {record['stage_id']}", "", f"Pedido: {record['stage']['prompt']}", "",
                      f"Agente: `{record.get('selected_agent')}`; estado: `{record['status']}`.", "",
                      record.get("response") or f"Sem resposta: {record.get('error', 'falha registrada')}", ""])
    lines.extend(["## Interpretação", "",
                  "Os checks comparam preferências persistidas, contexto realmente enviado, roteamento e "
                  "referência à fonte fornecida. Isso não demonstra que as respostas seguem corretamente "
                  "o formato, que o código gerado funciona ou que o resumo é fiel; essas saídas estão acima "
                  "para revisão humana. Nenhum código gerado foi executado. O corpus é sintético, com fonte "
                  "local identificada. O alvo muda por instrução explícita; isso é correção persistida de "
                  "preferência, não aprendizagem implícita ou validade de um modelo de personalidade.", "",
                  "A coleta formal A/B/C continua bloqueada por protocolo, tokenização, exposição ao "
                  "histórico, validade de construto e pré-registro. Os arquivos de execuções anteriores "
                  "foram preservados. Seed e temperatura são solicitadas ao backend, sem garantia de determinismo.", ""])
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

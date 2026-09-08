"""Early evaluation scaffold, explicitly separated from formal data collection."""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .budget import CharacterCounter, RecordingLLM
from .metrics import AGENTS, convergence, delegation_metrics, observed_format_vector, unavailable

STATIC_SYSTEM = (
    "Você é um assistente. Responda em português com clareza, respeitando os fatos fornecidos. "
    "Quando faltar informação, reconheça a ausência."
)

FORMAL_BLOCKERS = (
    "ADR-0010 permanece Proposto; aprovação do protocolo não foi registrada.",
    "Modelo de identidade dos ADRs 0006/0007 segue provisório; regras de preferências não o validam.",
    "Tokenizador real do modelo e equivalência de contexto B/C não foram validados.",
    "Sondas ainda não demonstraram validade de construto em piloto com LLM real e avaliação humana.",
    "Separação de IDs não valida independência entre estilo e recuperação de preferências de formato.",
    "C pode recuperar a sessão atual, B recebe só sessões anteriores; exposição precisa ser igualada.",
    "Rubrica e ground truth são rascunhos; falta pré-registro em commit datado após revisão.",
    "Pendências institucionais/éticas da seção 12.2 precisam de decisão documentada.",
)


@dataclass(frozen=True)
class EvaluationConfig:
    mode: str = "smoke"
    provider: str = "fake"
    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.0
    seed: int = 42
    max_context_chars: int = 2048
    run_id: str | None = None
    request_timeout: float = 120.0


def formal_blockers() -> list[str]:
    """Do not turn documentary proposals into accepted decisions via CLI switches."""
    return list(FORMAL_BLOCKERS)


def _data_root(data_root: Path | None) -> Path:
    return Path(data_root) if data_root else Path(__file__).resolve().parents[3] / "evaluation"


def load_design(data_root: Path | None = None) -> tuple[dict, dict, Path]:
    root = _data_root(data_root)
    scenarios = json.loads((root / "scenarios/scenarios.json").read_text(encoding="utf-8"))
    probes = json.loads((root / "probes/probes.json").read_text(encoding="utf-8"))
    ids = [p["id"] for p in probes["style"] + probes["profile"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Style and profile probe IDs must be disjoint and unique")
    if any(p["surface"] != "PersonalityState" for p in probes["style"]):
        raise ValueError("Style probes must measure PersonalityState")
    if any(p["surface"] != "UserModel" for p in probes["profile"]):
        raise ValueError("Profile probes must measure UserModel")
    if not 5 <= len(scenarios["scenarios"]) <= 10 or scenarios["sessions"] < 3:
        raise ValueError("Design requires 5–10 scenarios and at least three sessions")
    scenario_ids = [s["id"] for s in scenarios["scenarios"]]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Scenario IDs must be unique")
    for scenario in scenarios["scenarios"]:
        if scenario["expected_agent"] not in AGENTS:
            raise ValueError("Ground truth must refer to a registered experimental agent")
        if len(scenario["sessions"]) != scenarios["sessions"]:
            raise ValueError("Every scenario must retain all planned sessions")
    return scenarios, probes, root


def _json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def _prepare(output: Path, config: EvaluationConfig, root: Path) -> tuple[Path, str]:
    run_id = config.run_id or f"{config.mode}-{uuid.uuid4().hex[:12]}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise ValueError("run_id must contain 1–96 letters, digits, underscores or hyphens")
    run_dir = Path(output) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)  # Preserve all prior data, including failures.
    (run_dir / "inputs").mkdir()
    inputs = {}
    for relative in ("scenarios/scenarios.json", "probes/probes.json", "rubrics/README.md"):
        source = root / relative
        target = run_dir / "inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inputs[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    _json(run_dir / "config.json", {
        **asdict(config), "run_id": run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "design_sha256": inputs, "formal_collection_allowed": False,
        "formal_blockers": formal_blockers(),
        "scientific_claims_allowed": False,
        "context_counter": "unicode_characters_not_tokens" if config.mode == "smoke" else None,
        "execution_order": "C then A then B within each smoke pair; presentation order randomized",
        "blind_export": "Only share blind/ with raters; raw logs and key disclose conditions",
    })
    return run_dir, run_id


def _blind_exports(run_dir: Path, records: list[dict], seed: int) -> None:
    rng = random.Random(seed)
    (run_dir / "blind").mkdir()
    (run_dir / "private").mkdir()
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["scenario_id"], record["session"], record["prompt_id"])].append(record)
    scopes: dict[str, set[str]] = defaultdict(set)
    for record in records:
        scopes[record["scenario_id"]].add(record["arm"])
    conditions = {}
    for scope, arms in sorted(scopes.items()):
        randomized = sorted(arms)
        rng.shuffle(randomized)
        for arm in randomized:
            conditions[(scope, arm)] = f"cond-{rng.getrandbits(64):016x}"
    key = []
    for group_id, grouped in groups.items():
        rng.shuffle(grouped)
        pair_id = "|".join(map(str, group_id))
        for position, record in enumerate(grouped, 1):
            sample_id = f"sample-{rng.getrandbits(64):016x}"
            condition = conditions[(record["scenario_id"], record["arm"])]
            _append(run_dir / "blind/paired.jsonl", {
                "pair_id": pair_id, "sample_id": sample_id,
                "condition_id": condition, "presentation_position": position,
                "scenario_id": record["scenario_id"], "session": record["session"],
                "prompt_id": record["prompt_id"], "surface": record["surface"],
                "prompt": record["prompt"], "response": record["response"],
            })
            key.append({"sample_id": sample_id, "condition_id": condition,
                        "pair_id": pair_id, "arm": record["arm"],
                        "run_id": record["run_id"]})
    _json(run_dir / "private/unblinding.json", {"seed": seed, "samples": key})
    (run_dir / "blind/README.md").write_text(
        "# Material para avaliação cega\n\n"
        "O identificador condition_id permanece estável por cenário entre sessões, permitindo "
        "comparar a mesma sonda longitudinalmente. A posição é randomizada em cada par. "
        "Não consulte os logs brutos nem a chave. Respostas podem sugerir sua condição; "
        "registre suspeitas de quebra do cegamento. Não atribua notas a respostas ausentes.\n",
        encoding="utf-8",
    )


def _model(config: EvaluationConfig):
    from cain.llm import FakeLLM, OllamaLLM

    if config.provider == "fake":
        return FakeLLM()
    if config.provider == "ollama":
        return OllamaLLM(model=config.model, base_url=config.base_url,
                         temperature=config.temperature, seed=config.seed,
                         timeout=config.request_timeout)
    raise ValueError(f"Unknown provider: {config.provider}")


def run_smoke(output: Path, config: EvaluationConfig | None = None,
              *, data_root: Path | None = None, llm=None) -> Path:
    """Exercise A/B/C wiring. Scores describe this stub run only, never scientific quality."""
    from cain.runtime import build_cain

    config = config or EvaluationConfig()
    if config.mode != "smoke":
        raise ValueError("Character-budget A/B/C execution is restricted to smoke mode")
    if config.max_context_chars < 1:
        raise ValueError("max_context_chars must be positive")
    design, probes, root = load_design(data_root)
    run_dir, run_id = _prepare(output, config, root)
    counter = CharacterCounter()
    recorder = RecordingLLM(llm or _model(config), counter, config.max_context_chars)
    runtime = build_cain(db_path=run_dir / "cain.sqlite3", llm=recorder)
    records = []
    routing = []
    profile_observations = defaultdict(list)
    by_routing_mode = {"explicit_intent": [], "inferred": []}
    try:
        for scenario in design["scenarios"]:
            histories = {"A": [], "B": []}
            user_id = f"{run_id}-{scenario['id']}"
            for session_index, task in enumerate(scenario["sessions"], 1):
                session_id = f"{scenario['id']}-s{session_index}"
                pending = {"A": [], "B": []}
                prompts = [{"id": "task", "prompt": task, "surface": "delegation",
                            "intent": scenario["intent"]}, *probes["style"], *probes["profile"]]
                for prompt in prompts:
                    baseline = {
                        "run_id": run_id, "scenario_id": scenario["id"],
                        "session": session_index, "session_id": session_id,
                        "prompt_id": prompt["id"], "surface": prompt["surface"],
                        "prompt": prompt["prompt"], "expected_agent": scenario["expected_agent"]
                        if prompt["id"] == "task" else None,
                    }
                    call_start = len(recorder.calls)
                    result = runtime.run(user_id=user_id, session_id=session_id,
                                         payload=prompt["prompt"], intent=prompt["intent"],
                                         run_id=run_id)
                    c_calls = recorder.calls[call_start:]
                    profile = observed_format_vector(runtime.identity.get(user_id).user_model.preferences)
                    observed_budget = c_calls[0]["context_size"] if len(c_calls) == 1 else None
                    comparability = (
                        "Approximate character cap only; token equivalence is NOT demonstrated"
                        if observed_budget is not None else
                        "C did not make exactly one LLM call; matched-context comparison unavailable"
                    )
                    row = {
                        **baseline, "arm": "C", "response": result.response,
                        "selected_agent": result.selected_agent, "decision_id": result.decision_id,
                        "steps": list(result.steps), "llm_calls": c_calls,
                        "context_budget": observed_budget, "context_comparability": comparability,
                        "profile_vector": profile["value"], "profile_vector_reason": profile["reason"],
                        "profile_format": profile["observed_format"],
                    }
                    records.append(row)
                    _append(run_dir / "raw.jsonl", row)
                    if prompt["id"] == "task":
                        profile_observations[scenario["id"]].append({
                            "session": session_index, **profile,
                        })
                        pair = (scenario["expected_agent"], result.selected_agent)
                        routing.append(pair)
                        mode = "explicit_intent" if scenario["intent"] else "inferred"
                        by_routing_mode[mode].append(pair)
                    for arm in ("A", "B"):
                        # Only completed PRIOR sessions are available to B. Never add labels/profile fields.
                        transcript = "\n".join(histories[arm])
                        allowed = max(0, observed_budget - counter.count(STATIC_SYSTEM) - 1) \
                            if observed_budget is not None else 0
                        injected = counter.truncate(transcript, allowed) if arm == "B" else ""
                        context = STATIC_SYSTEM + ("\n" + injected if injected else "")
                        # Include the separator in the observed C cap where pairing is possible.
                        if arm == "B" and observed_budget is not None:
                            context = counter.truncate(context, observed_budget, from_end=False)
                        call_start = len(recorder.calls)
                        response = recorder.generate(prompt["prompt"], context=context)
                        calls = recorder.calls[call_start:]
                        row = {
                            **baseline, "arm": arm, "response": response,
                            "selected_agent": None, "decision_id": None, "steps": [],
                            "llm_calls": calls, "context_budget": observed_budget if arm == "B" else None,
                            "prior_session_transcript_chars": len(transcript) if arm == "B" else 0,
                            "context_comparability": comparability if arm == "B" else "Static baseline",
                            "profile_vector": None,
                            "profile_vector_reason": "Arm has no structured inferred UserModel",
                        }
                        records.append(row)
                        _append(run_dir / "raw.jsonl", row)
                        pending[arm].append(f"Usuário: {prompt['prompt']}\nAssistente: {response}")
                for arm in histories:
                    histories[arm].extend(pending[arm])
        _blind_exports(run_dir, records, config.seed)
        metrics = {
            "run_id": run_id, "mode": "smoke", "scientific_result": False,
            "n_scenarios": len(design["scenarios"]), "n_sessions": design["sessions"],
            "n_rows": len(records),
            "delegation": {
                "A": unavailable("Static baseline does not route"),
                "B": unavailable("Transcript baseline does not route"),
                "C": delegation_metrics(routing),
                "C_by_mode": {k: delegation_metrics(v) for k, v in by_routing_mode.items()},
                "interpretation": "Technical check of provisional rule router, not research evidence",
            },
            "coherence_embedding_distribution": unavailable("No real embedding provider configured"),
            "coherence_human_rubric": unavailable("No independent human ratings collected"),
            "profile_convergence": {
                "measurement": "Stored explicit format only; not implicit learning or validated construct",
                "dimensions": ["steps", "paragraph"],
                "scenarios": {
                    scenario["id"]: {
                        "observations": profile_observations[scenario["id"]],
                        "target": scenario["persona"]["target_vector"],
                        "metric": convergence(scenario["persona"]["target_vector"],
                                              [item["value"] for item in profile_observations[scenario["id"]]])
                        if all(item["value"] is not None for item in profile_observations[scenario["id"]])
                        else unavailable("One or more sessions have no observed format vector"),
                    } for scenario in design["scenarios"]
                },
                "construct_independence_validated": False,
            },
            "satisfaction": unavailable("No participants or authorized human study"),
            "rater_agreement": unavailable("No independent human ratings collected"),
            "construct_validity": unavailable("Fake/stub smoke execution cannot establish construct validity"),
            "formal_collection_allowed": False, "formal_blockers": formal_blockers(),
        }
        _json(run_dir / "metrics.json", metrics)
        (run_dir / "report.md").write_text(
            f"# Execução técnica {run_id}\n\n"
            f"Foram preservadas {len(records)} respostas/saídas de {len(design['scenarios'])} "
            f"cenários, {design['sessions']} sessões e 3 braços. "
            f"Provedor: `{config.provider}`. Este smoke verifica conexões e exportações. "
            "Não é coleta científica nem demonstra eficácia da arquitetura.\n\n"
            "A usa prompt estático; B recebe somente transcritos brutos de sessões anteriores; "
            "C atravessa o runtime. O orçamento em caracteres é substituto técnico: não comprova "
            "equivalência de tokens. Casos C sem chamada LLM ficam sem comparação de contexto. "
            "C também pode recuperar interações da sessão atual, enquanto B só acessa sessões "
            "anteriores. A exposição à informação difere e impede inferência B/C. Logs registram "
            "o orçamento efetivo e preservam contextos injetados.\n\n"
            "Coerência por embeddings, rubrica humana, satisfação e concordância "
            "não foram medidas; constam como nulas com motivos. A preferência explícita de formato "
            "é codificada diretamente do estado observado, quando disponível; a distância ao alvo "
            "não valida um construto de adaptação ou aprendizagem implícita. Acurácia de roteamento se refere "
            "somente ao roteador provisório e aos exemplos executados.\n\n"
            "**Validade de construto das sondas NÃO demonstrada.** O piloto com LLM real e "
            "avaliadores humanos permanece pendente. ADR-0010 continua Proposto.\n\n"
            "Para avaliação cega compartilhe apenas `blind/` e a rubrica; a chave está em "
            "`private/unblinding.json`. Todos os cenários foram mantidos.\n",
            encoding="utf-8",
        )
        return run_dir
    except Exception as error:
        _json(run_dir / "failure.json", {"run_id": run_id, "status": "failed",
                                        "error_type": type(error).__name__, "message": str(error),
                                        "retained_rows": len(records),
                                        "failed_llm_attempts": [call for call in recorder.calls
                                                                if call["status"] == "failed"]})
        raise
    finally:
        try:
            # Preserve the auditable reasons/events outside the SQLite binary, including failures.
            for decision in runtime.decision_log.export(run_id):
                _append(run_dir / "decisions.jsonl", asdict(decision))
        finally:
            runtime.close()


def run_construct_pilot(output: Path, config: EvaluationConfig,
                        *, data_root: Path | None = None) -> Path:
    """Real-LLM style instrument pilot; no context matching or formal comparison is claimed."""
    if config.mode != "pilot" or config.provider != "ollama":
        raise ValueError("Construct pilot requires mode=pilot and provider=ollama; fake is prohibited")
    _, probes, root = load_design(data_root)
    run_dir, run_id = _prepare(output, config, root)
    llm = _model(config)
    records = []
    try:
        for session in range(1, 4):
            for probe in probes["style"]:
                for persona in probes["pilot_personas"]:
                    response = llm.generate(probe["prompt"], context=persona["system"])
                    row = {
                        "run_id": run_id, "scenario_id": "construct-style", "session": session,
                        "prompt_id": probe["id"], "surface": probe["surface"],
                        "prompt": probe["prompt"], "context": persona["system"],
                        "arm": persona["id"], "response": response,
                        "context_comparability": "Not applicable: instrument pilot, no A/B/C comparison",
                    }
                    records.append(row)
                    _append(run_dir / "raw.jsonl", row)
        _blind_exports(run_dir, records, config.seed)
        _json(run_dir / "metrics.json", {
            "run_id": run_id, "mode": "pilot", "scientific_result": False,
            "construct_validity": unavailable("Awaiting independent blind human ratings and analysis"),
            "n_style_probes": len(probes["style"]), "n_personas": len(probes["pilot_personas"]),
            "n_sessions": 3, "n_rows": len(records),
            "formal_collection_allowed": False, "formal_blockers": formal_blockers(),
        })
        (run_dir / "report.md").write_text(
            f"# Piloto de instrumento {run_id}\n\n"
            "Respostas de LLM real para três sondas de estilo, duas personas contrastantes e "
            "três sessões independentes. O instrumento está pronto para avaliação humana cega. "
            "Gerar respostas não comprova que as sondas discriminam personas. Registre notas "
            "e justificativas de 2–3 avaliadores antes de revisar as sondas. Este piloto não "
            "mede o efeito do Cain nem executa a comparação formal A/B/C. ADR-0010 permanece Proposto.\n",
            encoding="utf-8",
        )
        return run_dir
    except Exception as error:
        _json(run_dir / "failure.json", {"run_id": run_id, "status": "failed",
                                        "error_type": type(error).__name__, "message": str(error),
                                        "retained_rows": len(records)})
        raise

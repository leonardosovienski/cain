"""Proposal by a local model (`cain research explain --propose-for-domain`): soak only, never a receipt path (C9).

The model sees only the domain's own memory (states, IDs and hashes retrieved from the cube at ``as_of``) and the
values the configuration allows; it answers JSON (``hypothesis_id``, ``placebo_seed``, ``rationale``) under a schema
whose enum is the configured proposable hypotheses. The CAIN fills the rest of the request from its last emitted task
of the domain and writes a ``cain-proposal/1`` file with ``source = "llm"``; the proposal then goes through the same
DecisionPolicy as any other (``cain research propose``). Every call is audited next to the proposal: prompt,
response, provider, model and model digest, and the proposal's sha256. The model never chooses a handler, a budget,
a priority, costs or capital, and nothing it writes is trusted before the policy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from research_protocol import v2

from cain.orchestration import policy

INSTRUCTION = (
    "Você propõe o próximo experimento de pesquisa de UM domínio, só com base nos resultados listados. "
    "Responda apenas JSON com hypothesis_id (um de allowed_hypotheses), placebo_seed (inteiro 0..999999 fora de "
    "used_placebo_seeds) e rationale (até 400 caracteres). Você não escolhe handler, budget, prioridade, custos, "
    "dados nem capital; resultados negativos não justificam mais escopo."
)


def _schema(config: dict) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["hypothesis_id", "placebo_seed", "rationale"],
        "properties": {
            "hypothesis_id": {"type": "string", "enum": sorted(config["proposable_hypotheses"])},
            "placebo_seed": {"type": "integer", "minimum": 0, "maximum": 999999},
            "rationale": {"type": "string", "maxLength": 400},
        },
    }


def model_identity(provider) -> dict:
    identity = {"provider": type(provider).__name__, "model": getattr(provider, "model", None), "digest": None}
    base_url = getattr(provider, "base_url", None)
    if base_url and identity["model"]:
        from cain.llm import urlopen

        try:
            with urlopen(base_url.rstrip("/") + "/api/tags", timeout=5) as response:
                tags = json.load(response)
            found = next((m for m in tags.get("models", []) if m.get("name") == identity["model"]), None)
            identity["digest"] = found.get("digest") if found else None
        except OSError:
            identity["digest"] = None
    return identity


def propose(orchestrator, provider, *, question: str, as_of: str, proposal_id: str, out: Path) -> dict:
    domain, config = orchestrator.domain, orchestrator.config
    with orchestrator.store.db() as db:
        view = orchestrator.store.view(db, domain, as_of)
        last = db.execute("SELECT raw FROM outbox WHERE domain=? ORDER BY episode DESC LIMIT 1", (domain,)).fetchone()
        seeds = sorted({json.loads(bytes(r["raw"]))["payload"]["parameters"].get("placebo_seed")
                        for r in db.execute("SELECT raw FROM outbox WHERE domain=?", (domain,))} - {None})
    if last is None:
        raise ValueError("NO_TEMPLATE: the domain has no emitted task to use as the request template")
    template = {k: v for k, v in v2.loads_task(bytes(last["raw"]))["payload"].items() if k != "client_ref"}
    context = {"domain": domain, "question": question[:500], "as_of": as_of,
               "allowed_hypotheses": sorted(config["proposable_hypotheses"]), "used_placebo_seeds": seeds[-200:],
               "results": [{k: r[k] for k in ("episode", "hypothesis_id", "status", "result_state", "scientific_state")}
                           for r in view["results"][-50:]]}
    prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
    if callable(getattr(provider, "generate_json", None)):
        raw = provider.generate_json(prompt, INSTRUCTION, _schema(config))
    else:
        raw = provider.generate(prompt, context=INSTRUCTION)
    answer = json.loads(raw)
    if not isinstance(answer, dict) or set(answer) != {"hypothesis_id", "placebo_seed", "rationale"}:
        raise ValueError("LLM_ANSWER_INVALID: expected hypothesis_id, placebo_seed, rationale")
    request = dict(template, hypothesis_id=answer["hypothesis_id"])
    request["parameters"] = dict(template["parameters"], placebo_seed=answer["placebo_seed"])
    request["request_id"] = f"{domain}:REQ-LLM-{hashlib.sha256(proposal_id.encode()).hexdigest()[:16]}"
    proposal = {"schema": policy.PROPOSAL_SCHEMA, "proposal_id": proposal_id, "domain": domain, "request": request,
                "based_on": [], "rationale": str(answer["rationale"])[:2000], "source": "llm"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposal, ensure_ascii=False, indent=1), encoding="utf-8")
    audit = {"schema": "cain-llm-proposal-audit/1", "proposal_file": out.name,
             "proposal_sha256": policy.safe_digest(proposal), "as_of": as_of, "instruction": INSTRUCTION,
             "prompt": prompt, "response": raw, "model": model_identity(provider), "capital_permission": False}
    out.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"proposal": str(out), "audit": str(out.with_suffix(".audit.json")), "hypothesis_id": answer["hypothesis_id"],
            "model": audit["model"]}

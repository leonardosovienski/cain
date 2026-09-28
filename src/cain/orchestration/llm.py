"""Proposal by a local model (`cain research explain --propose-for-domain`): never a receipt path (C9).

The model sees only the domain's own memory (states, IDs, hashes and closed reason codes retrieved from the cube at
``as_of``) and the values the configuration allows; it answers JSON (``hypothesis_id``, ``rationale``) under a
schema whose enum is the hypotheses the DecisionPolicy would accept *now*: each configured
proposable hypothesis is probed through ``policy.decide`` on the current view, so one in COOLDOWN, refused by the
domain as not admitted or otherwise held never reaches the model's choices (and when none is eligible the CAIN says so
instead of asking). The prompt carries a per-hypothesis summary (results, scientific states, refusal codes, why it is
not eligible) so the rationale can cite facts; the audit records which hypotheses the rationale mentions without any
result or refusal behind them. The placebo seed is not a research choice: the CAIN assigns it (derived from the
proposal ID, never one already used in the domain). In the first local-model campaign the model repeated listed seeds
and, at temperature 0, kept repeating a refused one; the same seed repeats the same placebo. The CAIN fills the rest
of the request from its last emitted task of the domain and writes a ``cain-proposal/1`` file with ``source = "llm"``; the proposal then goes through the same DecisionPolicy as
any other (``cain research propose``). Every call is audited next to the proposal: prompt, response, provider, model
and model digest, eligibility, the rationale check and the proposal's sha256. The model never chooses a handler, a
budget, a priority, costs or capital, and nothing it writes is trusted before the policy.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from research_protocol import v2

from cain.orchestration import policy

INSTRUCTION = (
    "Você propõe o próximo experimento de pesquisa de UM domínio, só com base nos fatos listados. "
    "Responda apenas JSON com hypothesis_id (um de allowed_hypotheses: as outras estão em pausa, recusadas pelo "
    "domínio ou retidas pela política) e rationale (até 400 caracteres). Na rationale, cite só fatos de "
    "hypothesis_summary e results; não descreva resultado de hipótese que não tem resultado. Você não escolhe "
    "semente, handler, budget, prioridade, custos, dados nem capital; resultados negativos não justificam mais escopo."
)


def _schema(allowed: list[str]) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["hypothesis_id", "rationale"],
        "properties": {
            "hypothesis_id": {"type": "string", "enum": allowed},
            "rationale": {"type": "string", "maxLength": 400},
        },
    }


def assign_seed(proposal_id: str, used: list[int]) -> int:
    """Deterministic placebo seed for a proposal: from the proposal ID, skipping every seed already used."""
    taken = set(used)
    seed = int(hashlib.sha256(proposal_id.encode()).hexdigest()[:8], 16) % 1_000_000
    while seed in taken:
        seed = (seed + 1) % 1_000_000
    return seed


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


def _request(template: dict, domain: str, hypothesis: str, seed: int, request_id: str) -> dict:
    request = dict(template, hypothesis_id=hypothesis, request_id=request_id)
    request["parameters"] = dict(template["parameters"], placebo_seed=seed)
    return request


def eligibility(config: dict, view: dict, template: dict, used_seeds: list[int], episode_number: int) -> dict:
    """Decision of the policy for each proposable hypothesis on the current view (a fresh seed, a probe request)."""
    taken = set(used_seeds)
    seed = next(s for s in range(1_000_000) if s not in taken)
    domain = config["domain"]
    out = {}
    for hypothesis in sorted(config["proposable_hypotheses"]):
        digest = hashlib.sha256(f"{hypothesis}|{seed}".encode()).hexdigest()[:16]
        probe = {"schema": policy.PROPOSAL_SCHEMA, "proposal_id": "cain:ELIGIBILITY-PROBE", "domain": domain,
                 "request": _request(template, domain, hypothesis, seed, f"{domain}:REQ-PROBE-{digest}"),
                 "based_on": [], "rationale": "", "source": "llm"}
        decision = policy.decide(probe, view, config, episode_number=episode_number)
        out[hypothesis] = {k: decision[k] for k in ("decision", "reason_code", "rule")}
    return out


def hypothesis_summary(config: dict, view: dict, decisions: dict) -> dict:
    rows = {}
    for hypothesis in sorted(config["proposable_hypotheses"]):
        own = [r for r in view["results"] if r["hypothesis_id"] == hypothesis]
        states: dict[str, int] = {}
        for r in own:
            if r["class"] == "TERMINAL_RESULT":
                states[r["scientific_state"]] = states.get(r["scientific_state"], 0) + 1
        eligible = decisions[hypothesis]["decision"] == "ALLOW"
        rows[hypothesis] = {
            "results": sum(states.values()),
            "scientific_states": states,
            "refusals": sorted({r.get("reason_code") or r["status"] for r in own if r["class"] == "TERMINAL_REFUSAL"}),
            "eligible_now": eligible,
            "not_eligible_reason": None if eligible else decisions[hypothesis]["reason_code"],
        }
    return rows


def _tokens(hypothesis: str) -> set[str]:
    local = hypothesis.split(":", 1)[1]
    parts = local.split("-")
    return {hypothesis, local} | ({"-".join(parts[-2:])} if len(parts) >= 2 else set())


def rationale_check(rationale: str, config: dict, view: dict) -> dict:
    """Hypotheses the rationale names, and those named without any result or refusal behind them (best effort)."""
    known = sorted(set(config["proposable_hypotheses"]) | set(config["closed_hypotheses"]))
    mentioned = [h for h in known if any(
        re.search(r"(?<![A-Za-z0-9-])" + re.escape(t) + r"(?![A-Za-z0-9-])", rationale) for t in _tokens(h))]
    with_evidence = {r["hypothesis_id"] for r in view["results"]}
    return {"mentioned": mentioned, "without_evidence": [h for h in mentioned if h not in with_evidence]}


def propose(orchestrator, provider, *, question: str, as_of: str, proposal_id: str, out: Path) -> dict:
    domain, config = orchestrator.domain, orchestrator.config
    with orchestrator.store.db() as db:
        view = orchestrator.store.view(db, domain, as_of)
        number = orchestrator.store.next_episode(db, domain)
        last = db.execute("SELECT raw FROM outbox WHERE domain=? ORDER BY episode DESC LIMIT 1", (domain,)).fetchone()
        seeds = sorted({json.loads(bytes(r["raw"]))["payload"]["parameters"].get("placebo_seed")
                        for r in db.execute("SELECT raw FROM outbox WHERE domain=?", (domain,))} - {None})
    if last is None:
        raise ValueError("NO_TEMPLATE: the domain has no emitted task to use as the request template")
    template = {k: v for k, v in v2.loads_task(bytes(last["raw"]))["payload"].items() if k != "client_ref"}
    decisions = eligibility(config, view, template, seeds, number)
    allowed = sorted(h for h, d in decisions.items() if d["decision"] == "ALLOW")
    if not allowed:
        held = sorted({f"{d['decision']} {d['reason_code']}" for d in decisions.values()})
        raise ValueError(f"NO_ELIGIBLE_HYPOTHESIS: the policy holds every proposable hypothesis now: {held}")
    context = {"domain": domain, "question": question[:500], "as_of": as_of, "allowed_hypotheses": allowed,
               "hypothesis_summary": hypothesis_summary(config, view, decisions),
               "results": [{k: r[k] for k in ("episode", "hypothesis_id", "status", "result_state", "scientific_state",
                                              "reason_code")}
                           for r in view["results"][-50:]]}
    prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
    if callable(getattr(provider, "generate_json", None)):
        raw = provider.generate_json(prompt, INSTRUCTION, _schema(allowed))
    else:
        raw = provider.generate(prompt, context=INSTRUCTION)
    answer = json.loads(raw)
    if not isinstance(answer, dict) or set(answer) != {"hypothesis_id", "rationale"}:
        raise ValueError("LLM_ANSWER_INVALID: expected hypothesis_id, rationale")
    request_id = f"{domain}:REQ-LLM-{hashlib.sha256(proposal_id.encode()).hexdigest()[:16]}"
    request = _request(template, domain, answer["hypothesis_id"], assign_seed(proposal_id, seeds), request_id)
    proposal = {"schema": policy.PROPOSAL_SCHEMA, "proposal_id": proposal_id, "domain": domain, "request": request,
                "based_on": [], "rationale": str(answer["rationale"])[:2000], "source": "llm"}
    check = rationale_check(proposal["rationale"], config, view)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposal, ensure_ascii=False, indent=1), encoding="utf-8")
    audit = {"schema": "cain-llm-proposal-audit/2", "proposal_file": out.name,
             "proposal_sha256": policy.safe_digest(proposal), "as_of": as_of, "instruction": INSTRUCTION,
             "prompt": prompt, "response": raw, "model": model_identity(provider), "eligibility": decisions,
             "rationale_check": check, "capital_permission": False}
    out.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"proposal": str(out), "audit": str(out.with_suffix(".audit.json")), "hypothesis_id": answer["hypothesis_id"],
            "model": audit["model"], "rationale_check": check}

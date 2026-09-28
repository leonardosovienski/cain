"""Proposal by a local model (`cain research explain --propose-for-domain`): never a receipt path (C9).

The model sees only the domain's own memory (states, IDs, hashes and closed reason codes retrieved from the cube at
``as_of``) and the values the configuration allows; it answers JSON (``hypothesis_id``, ``rationale``) under a
schema whose enum is the hypotheses the DecisionPolicy would accept *now*: each configured
proposable hypothesis is probed through ``policy.decide`` on the current view, so one in COOLDOWN, refused by the
domain as not admitted or otherwise held never reaches the model's choices (and when none is eligible the CAIN says so
instead of asking). The prompt carries a per-hypothesis summary (results, scientific states, refusal codes, why it is
not eligible) so the rationale can cite facts; the audit records which hypotheses the rationale mentions without any
result or refusal behind them. The placebo seed is not a research choice: the CAIN assigns it (derived from the
proposal ID, never one already used in the domain), and only where the domain's contract declares ``placebo_seed`` for
the request's parameters (crypto; not stocks). In the first local-model campaign the model repeated listed seeds
and, at temperature 0, kept repeating a refused one; the same seed repeats the same placebo. The CAIN fills the rest
of the request from a template of the chosen hypothesis (its own last emitted task, else the last emitted task of the
request type the configuration fixes for it; never another type: the utility round sent a collection hypothesis as a
backtest) and writes a ``cain-proposal/1`` file with ``source = "llm"``; the proposal then goes through the same DecisionPolicy as
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
    """The template request with the chosen hypothesis; the placebo seed only where the domain's contract declares
    ``placebo_seed`` for these parameters (crypto does; a stocks request would be refused as SCHEMA_INVALID). A
    request without parameters (brasileirao: the request_schema has no such key) stays without them."""
    request = dict(template, hypothesis_id=hypothesis, request_id=request_id)
    if "parameters" not in template:
        return request
    params = dict(template["parameters"])
    if "placebo_seed" in (policy.declared_parameters(domain, params) or ()):
        params["placebo_seed"] = seed
    request["parameters"] = params
    return request


NO_TEMPLATE = {"decision": "ABSTAIN", "reason_code": "NO_REQUEST_TEMPLATE", "rule": "LLM"}


def templates(config: dict, emitted: list[dict]) -> dict:
    """Request template of each proposable hypothesis, from the CAIN's own emitted tasks (newest first, without
    ``client_ref``): the hypothesis's own last task, else the last task of the request type the configuration fixes
    for it (``proposable_request_types``). Never a task of another type: a collection hypothesis never borrows a
    backtest. A hypothesis with neither has no template (it is not offered to the model).

    ``proposal_overlays`` (optional) gives a hypothesis parameters of its own (e.g. a negative control with its own
    seed): a template borrowed from another hypothesis drops every overlaid parameter and takes the hypothesis's
    overlay, so each such hypothesis asks for its own experiment (R17 would hold a borrowed one as the same)."""
    overlays = config.get("proposal_overlays", {})
    overlaid = set().union(*overlays.values()) if overlays else set()
    out = {}
    for hypothesis in sorted(config["proposable_hypotheses"]):
        kind = config["proposable_request_types"][hypothesis]
        own = next((p for p in emitted if p["hypothesis_id"] == hypothesis and p["request_type"] == kind), None)
        if own is not None:
            template = own
        else:
            base = next((p for p in emitted if p["request_type"] == kind), None)
            if base is None:
                continue
            params = {k: v for k, v in base.get("parameters", {}).items() if k not in overlaid}
            template = dict(base, parameters=params) if "parameters" in base else base
        if hypothesis in overlays:
            template = dict(template, parameters=dict(template.get("parameters", {}), **overlays[hypothesis]))
        out[hypothesis] = template
    return out


def eligibility(config: dict, view: dict, templates_by_hypothesis: dict, used_seeds: list[int],
                episode_number: int) -> dict:
    """Decision of the policy for each proposable hypothesis on the current view (a fresh seed, a probe request built
    from the hypothesis's own template); a hypothesis without template is held (``NO_REQUEST_TEMPLATE``)."""
    taken = set(used_seeds)
    seed = next(s for s in range(1_000_000) if s not in taken)
    domain = config["domain"]
    out = {}
    for hypothesis in sorted(config["proposable_hypotheses"]):
        template = templates_by_hypothesis.get(hypothesis)
        if template is None:
            out[hypothesis] = dict(NO_TEMPLATE)
            continue
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


_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
_COUNT = re.compile(r"\b(\d+)\s+(?:resultados?|results?|epis[óo]dios?|episodes?)\b", re.I)
_NOT_ELIGIBLE = re.compile(r"n[ãa]o\s+(?:(?:é|e|est[áa])\s+)?eleg[ií]ve(?:l|is)|ineleg[ií]ve(?:l|is)", re.I)
_ELIGIBLE = re.compile(r"\beleg[ií]ve(?:l|is)\b", re.I)
_THIS = re.compile(r"\b(?:esta|essa)\s+hip[óo]tese\b", re.I)


def _named(sentence: str, known: list[str]) -> list[str]:
    return [h for h in known if any(
        re.search(r"(?<![A-Za-z0-9-])" + re.escape(t) + r"(?![A-Za-z0-9-])", sentence) for t in _tokens(h))]


def rationale_check(rationale: str, config: dict, view: dict, *, chosen: str | None = None,
                    summary: dict | None = None) -> dict:
    """Best-effort reading of the rationale against the CAIN's own view (it never decides anything):

    * ``mentioned`` / ``without_evidence``: hypotheses named, and those named without any result or refusal;
    * ``count_mismatches``: a sentence about one hypothesis ("esta hipótese" = the chosen one) cites a number of
      results or episodes that differs from the summary the model received;
    * ``eligibility_mismatches``: such a sentence says the hypothesis is (not) eligible and the policy says otherwise.
    Sentences naming several hypotheses are skipped (the pairing would be a guess)."""
    known = sorted(set(config["proposable_hypotheses"]) | set(config["closed_hypotheses"]))
    mentioned = _named(rationale, known)
    with_evidence = {r["hypothesis_id"] for r in view["results"]}
    counts, eligibility = [], []
    for sentence in (s for s in _SENTENCE.split(rationale) if s.strip()):
        named = _named(sentence, known) or ([chosen] if chosen and _THIS.search(sentence) else [])
        if len(named) != 1 or named[0] not in (summary or {}):
            continue
        hypothesis, row = named[0], summary[named[0]]
        cited = sorted({int(n) for n in _COUNT.findall(sentence)})
        if cited and row["results"] not in cited:
            counts.append({"hypothesis": hypothesis, "cited": cited, "actual": row["results"],
                           "sentence": sentence[:240]})
        claim = False if _NOT_ELIGIBLE.search(sentence) else (True if _ELIGIBLE.search(sentence) else None)
        if claim is not None and claim != row["eligible_now"]:
            eligibility.append({"hypothesis": hypothesis, "claimed_eligible": claim, "eligible_now": row["eligible_now"],
                                "not_eligible_reason": row["not_eligible_reason"], "sentence": sentence[:240]})
    return {"mentioned": mentioned, "without_evidence": [h for h in mentioned if h not in with_evidence],
            "count_mismatches": counts, "eligibility_mismatches": eligibility}


def propose(orchestrator, provider, *, question: str, as_of: str, proposal_id: str, out: Path) -> dict:
    domain, config = orchestrator.domain, orchestrator.config
    with orchestrator.store.db() as db:
        view = orchestrator.store.view(db, domain, as_of)
        number = orchestrator.store.next_episode(db, domain)
        emitted = [{k: v for k, v in v2.loads_task(bytes(r["raw"]))["payload"].items() if k != "client_ref"}
                   for r in db.execute("SELECT raw FROM outbox WHERE domain=? ORDER BY episode DESC", (domain,))]
    seeds = sorted({p.get("parameters", {}).get("placebo_seed") for p in emitted} - {None})
    by_hypothesis = templates(config, emitted)
    if not by_hypothesis:
        raise ValueError("NO_TEMPLATE: no emitted task of the domain can be a request template for a proposable "
                         "hypothesis (same hypothesis or same request type)")
    decisions = eligibility(config, view, by_hypothesis, seeds, number)
    allowed = sorted(h for h, d in decisions.items() if d["decision"] == "ALLOW")
    if not allowed:
        held = sorted({f"{d['decision']} {d['reason_code']}" for d in decisions.values()})
        raise ValueError(f"NO_ELIGIBLE_HYPOTHESIS: the policy holds every proposable hypothesis now: {held}")
    summary = hypothesis_summary(config, view, decisions)
    context = {"domain": domain, "question": question[:500], "as_of": as_of, "allowed_hypotheses": allowed,
               "hypothesis_summary": summary,
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
    # a model that disobeys the enum (a closed or unknown hypothesis) still yields a proposal the policy refuses
    # (R05/R11); its request borrows the newest emitted task, since such a hypothesis has no template of its own
    template = by_hypothesis.get(answer["hypothesis_id"], emitted[0])
    request = _request(template, domain, answer["hypothesis_id"], assign_seed(proposal_id, seeds), request_id)
    proposal = {"schema": policy.PROPOSAL_SCHEMA, "proposal_id": proposal_id, "domain": domain, "request": request,
                "based_on": [], "rationale": str(answer["rationale"])[:2000], "source": "llm"}
    check = rationale_check(proposal["rationale"], config, view, chosen=answer["hypothesis_id"], summary=summary)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposal, ensure_ascii=False, indent=1), encoding="utf-8")
    audit = {"schema": "cain-llm-proposal-audit/3", "proposal_file": out.name,
             "proposal_sha256": policy.safe_digest(proposal), "as_of": as_of, "instruction": INSTRUCTION,
             "prompt": prompt, "response": raw, "model": model_identity(provider), "eligibility": decisions,
             "rationale_check": check, "capital_permission": False}
    out.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"proposal": str(out), "audit": str(out.with_suffix(".audit.json")), "hypothesis_id": answer["hypothesis_id"],
            "model": audit["model"], "rationale_check": check}

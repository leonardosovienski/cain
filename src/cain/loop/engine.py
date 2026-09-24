"""Governed research loop: Hypothesis → Experiment → Feedback over a predictor's frozen evaluator.

Each attempt, in order:
1. the proposer suggests a change for the step kind of this turn (round-robin "features"/"model");
2. anything outside the editable surface is **blocked** and recorded;
3. novelty: a description too similar to an existing hypothesis is a **variant** of it (bounded by
   ``max_variants_per_hypothesis``), otherwise a new hypothesis is registered (a human gate when the
   world says ``new_hypothesis``);
4. the evaluator's pinned files are re-hashed; any change stops the loop (``evaluator_changed``);
5. cascade: sanity and leakage checks → redundancy filter (|correlation| ≥ threshold with an
   earlier candidate's signal = **discarded** before any backtest) → in-sample → walk-forward;
6. feedback against the best so far (primary metric of the last stage run, with ``min_improvement``).
A crash or timeout at any stage is recorded and counts as an attempt.

The loop stops on: attempt budget, time budget, stagnation, or a human gate. A candidate that beats
the baseline in walk-forward asks for the holdout gate and the loop stops there; the holdout stage
only runs through ``run_holdout`` after an approval recorded in the ledger. Nothing runs forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from uuid import uuid4

from cain.loop.evaluator import EvaluatorCrash, correlation, run_stage
from cain.loop.ledger import LoopLedger
from cain.loop.world import baseline, surface_violations, verify_evaluator

REDUNDANCY_THRESHOLD = 0.99
NOVELTY_THRESHOLD = 0.9


def lexical_similarity(a: str, b: str) -> float:
    left, right = set(a.casefold().split()), set(b.casefold().split())
    return len(left & right) / len(left | right) if left | right else 1.0


@dataclass
class LoopState:
    loop_id: str
    started: float
    attempts: int = 0
    since_improvement: int = 0
    best: dict | None = None
    baseline_metric: float | None = None
    hypotheses: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    tried: dict = field(default_factory=dict)
    turn: int = 0


def _redundant(world: dict, signal: list, earlier: list) -> tuple[bool, dict]:
    """Redundancy of a candidate's signal against an earlier one, by the measure the world names.

    ``correlation`` (default; RD-Agent's rule for new factors): |corr| >= threshold (0.99).
    ``max_abs_diff`` (for parameter variants of one model, whose predictions are always highly
    correlated): the largest absolute difference of the predictions is <= threshold.
    """
    rule = world.get("redundancy", {})
    measure = rule.get("measure", "correlation")
    if measure == "max_abs_diff":
        if len(signal) != len(earlier):
            return False, {}
        diff = max((abs(a - b) for a, b in zip(signal, earlier)), default=0.0)
        return diff <= rule.get("threshold", 0.0), {"measure": measure, "max_abs_diff": round(diff, 9)}
    corr = correlation(signal, earlier)
    threshold = rule.get("threshold", REDUNDANCY_THRESHOLD)
    return corr is not None and abs(corr) >= threshold, {"measure": "correlation",
                                                          "correlation": None if corr is None else round(corr, 6)}


def _better(world: dict, value: float, reference: float | None) -> bool:
    if reference is None:
        return True
    step = world["metric"].get("min_improvement", 0)
    if world["metric"]["direction"] == "minimize":
        return value < reference - step
    return value > reference + step


class ResearchLoop:
    def __init__(self, world: dict, ledger: LoopLedger, proposer, *, similarity=lexical_similarity,
                 clock=time.monotonic, runner=run_stage):
        self.world, self.ledger, self.proposer = world, ledger, proposer
        self.similarity, self.clock, self.runner = similarity, clock, runner

    # ------------------------------------------------------------------ helpers
    def _event(self, state: LoopState, kind: str, body: dict) -> dict:
        return self.ledger.append(state.loop_id, kind, body)

    def _stop(self, state: LoopState, reason: str, **extra) -> dict:
        self._event(state, "loop.stopped", {"reason": reason, "attempts": state.attempts,
                                             "elapsed_seconds": round(self.clock() - state.started, 3),
                                             "best": state.best, **extra})
        return self.ledger.status(state.loop_id)

    def _stop_reason(self, state: LoopState) -> str | None:
        budget = self.world["budget"]
        if state.attempts >= budget["total_attempts"]:
            return "budget_attempts"
        if self.clock() - state.started >= budget["total_seconds"]:
            return "budget_time"
        if state.since_improvement >= self.world["stagnation"]["attempts_without_improvement"]:
            return "stagnation"
        return None

    def _hypothesis_for(self, state: LoopState, description: str) -> tuple[dict, bool]:
        scored = [(self.similarity(description, h["description"]), h) for h in state.hypotheses]
        score, closest = max(scored, key=lambda item: item[0]) if scored else (0.0, None)
        if closest is not None and score >= self.world.get("novelty", {}).get("threshold", NOVELTY_THRESHOLD):
            return closest, False
        return {"hypothesis_id": "hyp:" + uuid4().hex[:12], "description": description,
                "variant_of": None, "closest": closest["hypothesis_id"] if closest else None,
                "similarity_to_closest": round(score, 4), "variants": 0}, True

    # ------------------------------------------------------------------ run
    def run(self, *, loop_id: str | None = None) -> dict:
        world = self.world
        state = LoopState(loop_id=loop_id or "loop:" + uuid4().hex[:12], started=self.clock())
        check = verify_evaluator(world)
        self._event(state, "loop.started", {
            "world_id": world["world"]["id"], "world_version": world["world"]["version"],
            "world_sha256": world["_sha256"], "predictor": world["world"]["predictor"],
            "hypothesis": world["world"]["hypothesis"], "evaluator": check,
            "evaluator_files": world["evaluator"]["files"], "budget": world["budget"],
            "stagnation": world["stagnation"], "gates": world["gates"]["human"],
            "cascade": world["cascade"]["stages"], "proposer": getattr(self.proposer, "name", "unknown")})
        if check["status"] != "intact":
            return self._stop(state, "evaluator_changed", evaluator=check)
        root = {"hypothesis_id": world["world"]["hypothesis"], "description": world["world"]["description"],
                "variant_of": None, "closest": None, "similarity_to_closest": None, "variants": 0}
        state.hypotheses.append(root)
        self._event(state, "hypothesis.registered", {**root, "source": "world file"})
        pending = [("baseline", {"params": baseline(world), "files": [],
                                 "description": world["world"]["description"], "rationale": "baseline"})]
        while True:
            reason = self._stop_reason(state)
            if reason:
                return self._stop(state, reason)
            if pending:
                kind, proposal = pending.pop()
            else:
                kind = ("features", "model")[state.turn % 2]
                state.turn += 1
                try:
                    proposal = self.proposer.propose(world, kind, self.ledger.status(state.loop_id), state.best)
                except Exception as exc:  # noqa: BLE001 - a proposer failure is an attempt, recorded
                    state.attempts += 1
                    state.since_improvement += 1
                    self._event(state, "experiment.crashed", {"attempt": state.attempts, "stage": "proposal",
                                                              "reason": type(exc).__name__, "detail": str(exc)[:500]})
                    continue
            outcome = self._attempt(state, kind, proposal)
            if outcome is not None:
                return outcome

    def _attempt(self, state: LoopState, kind: str, proposal: dict) -> dict | None:
        world = self.world
        state.attempts += 1
        attempt = state.attempts
        params = {**(state.best or {}).get("params", baseline(world)), **proposal.get("params", {})}
        self._event(state, "experiment.proposed", {
            "attempt": attempt, "step_kind": kind, "changes": proposal.get("params", {}),
            "files": proposal.get("files", []), "params": params, "description": proposal.get("description", ""),
            "rationale": proposal.get("rationale", ""), "proposer": getattr(self.proposer, "name", "unknown"),
            "proposer_call": proposal.get("call_id")})
        violations = surface_violations(world, proposal.get("params", {}), proposal.get("files", []))
        if violations:
            state.since_improvement += 1
            self._event(state, "experiment.blocked", {"attempt": attempt, "reason": "OUTSIDE_EDITABLE_SURFACE",
                                                      "violations": violations})
            return None
        key = json.dumps(params, sort_keys=True)
        if key in state.tried:
            state.since_improvement += 1
            self._event(state, "experiment.discarded", {"attempt": attempt, "reason": "DUPLICATE",
                                                        "duplicate_of_attempt": state.tried[key]})
            return None
        state.tried[key] = attempt
        if kind != "baseline":
            hypothesis, new = self._hypothesis_for(state, proposal.get("description", ""))
            if new:
                state.hypotheses.append(hypothesis)
                self._event(state, "hypothesis.registered", {**hypothesis, "source": "proposal",
                                                             "attempt": attempt})
                if "new_hypothesis" in world["gates"]["human"]:
                    self._event(state, "gate.requested", {"gate": "new_hypothesis", "attempt": attempt,
                                                          "hypothesis_id": hypothesis["hypothesis_id"]})
                    return self._stop(state, "human_gate", gate="new_hypothesis")
            elif hypothesis["variants"] >= world["budget"]["max_variants_per_hypothesis"]:
                state.since_improvement += 1
                self._event(state, "experiment.discarded", {"attempt": attempt, "reason": "MAX_VARIANTS",
                                                            "hypothesis_id": hypothesis["hypothesis_id"]})
                return None
            else:
                hypothesis["variants"] += 1
            hypothesis_id = hypothesis["hypothesis_id"]
        else:
            hypothesis_id = world["world"]["hypothesis"]
        check = verify_evaluator(world)
        if check["status"] != "intact":
            return self._stop(state, "evaluator_changed", evaluator=check, attempt=attempt)
        timeout = world["budget"]["attempt_seconds"]
        results = {}
        started = self.clock()
        for stage in [s for s in world["cascade"]["stages"] if s != "holdout"]:
            remaining = timeout - (self.clock() - started)
            try:
                if remaining <= 0:
                    raise EvaluatorCrash("TIMEOUT", f"attempt budget of {timeout}s spent before {stage}")
                result = self.runner(world, stage, params, timeout=remaining)
            except EvaluatorCrash as exc:
                state.since_improvement += 1
                self._event(state, "experiment.crashed", {"attempt": attempt, "stage": stage, "reason": exc.reason,
                                                          "detail": exc.detail, "hypothesis_id": hypothesis_id})
                return None
            results[stage] = {k: result.get(k) for k in ("ok", "metrics", "checks")}
            if not result["ok"]:
                state.since_improvement += 1
                self._event(state, "experiment.discarded", {"attempt": attempt, "reason": f"{stage.upper()}_FAILED",
                                                            "results": results, "hypothesis_id": hypothesis_id})
                return None
            if stage == "sanity" and result.get("signal") is not None:
                for earlier in state.signals:
                    redundant, measure = _redundant(world, result["signal"], earlier["signal"])
                    if redundant:
                        state.since_improvement += 1
                        self._event(state, "experiment.discarded", {
                            "attempt": attempt, "reason": "REDUNDANT", **measure,
                            "redundant_with_attempt": earlier["attempt"], "hypothesis_id": hypothesis_id})
                        return None
                state.signals.append({"attempt": attempt, "signal": result["signal"]})
        last = [s for s in world["cascade"]["stages"] if s != "holdout"][-1]
        value = results[last]["metrics"][world["metric"]["primary"]]
        improved = _better(world, value, (state.best or {}).get("value"))
        feedback = {"attempt": attempt, "hypothesis_id": hypothesis_id, "step_kind": kind, "params": params,
                    "results": results, "decided_on": last, "value": value,
                    "best_before": (state.best or {}).get("value"), "improved": improved,
                    "seconds": round(self.clock() - started, 3)}
        if kind == "baseline":
            state.baseline_metric = value
        if improved:
            state.best = {"attempt": attempt, "params": params, "value": value, "hypothesis_id": hypothesis_id}
            state.since_improvement = 0
        else:
            state.since_improvement += 1
        self._event(state, "experiment.finished", feedback)
        if (improved and kind != "baseline" and "holdout" in world["cascade"]["stages"]
                and _better(world, value, state.baseline_metric)):
            self._event(state, "gate.requested", {"gate": "holdout", "attempt": attempt, "params": params,
                                                  "value": value, "baseline": state.baseline_metric})
            return self._stop(state, "human_gate", gate="holdout")
        return None


def decide_gate(ledger: LoopLedger, loop_id: str, *, decision: str, by: str, note: str = "") -> dict:
    """Record the human decision on the pending gate of a stopped loop."""
    if decision not in ("APPROVE", "REJECT"):
        raise ValueError("decision must be APPROVE or REJECT")
    if not by.strip():
        raise ValueError("record who decides")
    events = ledger.events(loop_id)
    gates = [e for e in events if e["kind"] == "gate.requested"]
    decided = {e["body"]["gate_event_id"] for e in events if e["kind"] == "gate.decided"}
    pending = [g for g in gates if g["event_id"] not in decided]
    if not pending:
        raise ValueError("no pending gate on this loop")
    return ledger.append(loop_id, "gate.decided", {"gate_event_id": pending[-1]["event_id"],
                                                   "gate": pending[-1]["body"]["gate"], "decision": decision,
                                                   "by": by, "note": note})


def run_holdout(world: dict, ledger: LoopLedger, loop_id: str, *, runner=run_stage) -> dict:
    """Evaluate the gated candidate on the holdout, only after an APPROVE recorded for that gate."""
    events = ledger.events(loop_id)
    approved = [e for e in events if e["kind"] == "gate.decided" and e["body"]["gate"] == "holdout"
                and e["body"]["decision"] == "APPROVE"]
    if not approved:
        raise PermissionError("the holdout needs a recorded human APPROVE for this loop's holdout gate")
    if any(e["kind"] == "holdout.evaluated" for e in events):
        raise ValueError("the holdout of this loop was already evaluated (it is spent once)")
    gate = next(e for e in events if e["event_id"] == approved[-1]["body"]["gate_event_id"])
    check = verify_evaluator(world)
    if check["status"] != "intact":
        raise ValueError(f"evaluator changed: {check['mismatches']}")
    try:
        result = runner(world, "holdout", gate["body"]["params"], timeout=world["budget"]["attempt_seconds"])
        body = {"gate_event_id": gate["event_id"], "params": gate["body"]["params"], "ok": result["ok"],
                "metrics": result.get("metrics"), "approval_event_id": approved[-1]["event_id"]}
    except EvaluatorCrash as exc:
        body = {"gate_event_id": gate["event_id"], "params": gate["body"]["params"], "ok": False,
                "crash": exc.reason, "detail": exc.detail, "approval_event_id": approved[-1]["event_id"]}
    ledger.append(loop_id, "holdout.evaluated", body)
    return body

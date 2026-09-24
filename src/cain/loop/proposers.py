"""Who suggests the next change. The loop decides nothing from a proposal by itself: every proposal
goes through the editable-surface guard, the novelty and redundancy filters and the evaluator.

* ``NeighborProposer``: deterministic; for the step kind of the turn, moves one parameter of that
  kind to the next untried neighbour of the best value (int/float by ``step``, choices in order).
* ``LocalModelProposer``: a local model (Ollama) proposes one parameter change with structured
  output; each call goes through the inference recorder (manifest), and its call id is kept in the
  ledger event of the proposal.

The next step kind is chosen by simple round-robin between "features" and "model". A bandit
(Thompson sampling over step kinds, as in RD-Agent) is the documented extension, not this version.
"""

from __future__ import annotations

import json

from cain.loop.world import baseline


def _step(spec: dict) -> float:
    if "step" in spec:
        return spec["step"]
    span = spec["max"] - spec["min"]
    return max(1, round(span / 10)) if spec["type"] == "int" else span / 10


class NeighborProposer:
    name = "neighbor/1"

    def __init__(self):
        self.proposed: list[dict] = []
        self.cursor = {"features": 0, "model": 0}

    def propose(self, world: dict, kind: str, status: dict, best: dict | None) -> dict:
        spec = world["editable"]["parameters"]
        current = (best or {}).get("params") or baseline(world)
        names = [n for n, s in spec.items() if s["kind"] == kind] or list(spec)
        tried = {json.dumps(p, sort_keys=True) for p in self.proposed}
        for offset in range(len(names)):
            name = names[(self.cursor[kind] + offset) % len(names)]
            rule = spec[name]
            if rule["type"] == "choice":
                candidates = [c for c in rule["choices"] if c != current[name]]
            else:
                step = _step(rule)
                candidates = []
                for k in range(1, 50):
                    for sign in (1, -1):
                        value = current[name] + sign * k * step
                        value = int(round(value)) if rule["type"] == "int" else round(value, 10)
                        if rule["min"] <= value <= rule["max"]:
                            candidates.append(value)
            for value in candidates:
                params = {**current, name: value}
                if json.dumps(params, sort_keys=True) not in tried:
                    self.proposed.append(params)
                    self.cursor[kind] = (self.cursor[kind] + offset + 1) % len(names)
                    return {"params": {name: value}, "files": [],
                            "description": f"{kind}: tune {name}",
                            "rationale": f"next untried neighbour of the best {name}={current[name]}"}
        raise RuntimeError(f"no untried {kind} change left on the editable surface")


class LocalModelProposer:
    name = "local-model/1"

    def __init__(self, provider, attempts: int = 2):
        self.provider, self.attempts = provider, attempts

    def propose(self, world: dict, kind: str, status: dict, best: dict | None) -> dict:
        from cain.inference.structured import generate_structured

        spec = world["editable"]["parameters"]
        names = [n for n, s in spec.items() if s["kind"] == kind] or list(spec)
        schema = {"type": "object", "additionalProperties": False,
                  "required": ["parameter", "value", "hypothesis", "rationale"],
                  "properties": {"parameter": {"type": "string", "enum": names},
                                 "value": {"type": "string", "minLength": 1, "maxLength": 40},
                                 "hypothesis": {"type": "string", "minLength": 3, "maxLength": 200},
                                 "rationale": {"type": "string", "minLength": 3, "maxLength": 400}}}
        current = (best or {}).get("params") or baseline(world)
        tried = [{"params": e.get("params"), "value": e.get("value")} for e in status.get("finished", [])][-8:]
        prompt = json.dumps({
            "task": world["world"]["description"], "metric": world["metric"],
            "step_kind": kind, "current_best_params": current, "best_value": (best or {}).get("value"),
            "editable_parameters": {n: spec[n] for n in names}, "recent_results": tried,
            "instruction": ("Propose ONE change to ONE of the editable parameters, inside its range, that "
                            "you expect to improve the metric. Return the parameter name, the new value as "
                            "text, a one-line hypothesis (the idea, not the number) and a short rationale."),
        }, ensure_ascii=False)
        system = ("You are a careful quantitative researcher. Use only the information given. "
                  "Answer with the JSON object requested and nothing else.")
        value, history = generate_structured(self.provider, prompt, system, schema, attempts=self.attempts,
                                             loop_step_kind=kind)
        rule = spec[value["parameter"]]
        raw = value["value"].strip()
        try:
            parsed = (int(float(raw)) if rule["type"] == "int" and float(raw).is_integer()
                      else float(raw) if rule["type"] in ("int", "float") else raw)
        except ValueError:
            parsed = raw  # the surface guard rejects it and the ledger keeps what was proposed
        return {"params": {value["parameter"]: parsed}, "files": [], "description": value["hypothesis"],
                "rationale": value["rationale"], "call_id": history[-1]["call_id"]}

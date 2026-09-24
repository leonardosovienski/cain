"""Run one cascade stage of the predictor's frozen evaluator in a separate process.

Protocol: ``<python> <entrypoint>`` reads one JSON object on stdin
``{"stage", "params", "data"}`` and writes one JSON object on stdout
``{"stage", "ok", "metrics": {...}, "signal": [...]?, "checks": {...}?}``.

The loop never imports the evaluator, never reads its data and never passes holdout data unless
the stage is ``holdout`` (which only runs after a recorded human approval). The child gets a
minimal environment (no inherited secrets) and a hard timeout; the process isolation here is not a
sandbox (no network or filesystem confinement; that is Prompt 10).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess

SAFE_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "SYSTEMROOT")


class EvaluatorCrash(RuntimeError):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}"[:2000])
        self.reason, self.detail = reason, detail[-2000:]


def run_stage(world: dict, stage: str, params: dict, *, timeout: float) -> dict:
    evaluator = world["evaluator"]
    data = world["data"].get("holdout", []) if stage == "holdout" else world["data"].get("allowed", [])
    payload = {"stage": stage, "params": params, "data": data, "world": world["world"]["id"]}
    env = {key: os.environ[key] for key in SAFE_ENV if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        done = subprocess.run([evaluator["python"], evaluator["entrypoint"]], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=timeout, env=env,
                              cwd=evaluator.get("cwd") or str(Path(evaluator["entrypoint"]).parent))
    except subprocess.TimeoutExpired as exc:
        raise EvaluatorCrash("TIMEOUT", f"stage {stage} exceeded {timeout}s") from exc
    except OSError as exc:
        raise EvaluatorCrash("NOT_RUNNABLE", str(exc)) from exc
    if done.returncode != 0:
        raise EvaluatorCrash("EXIT_NONZERO", f"exit {done.returncode}: {done.stderr[-1500:]}")
    try:
        result = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise EvaluatorCrash("BAD_OUTPUT", done.stdout[-500:]) from exc
    primary = world["metric"]["primary"]
    if not isinstance(result, dict) or result.get("stage") != stage or not isinstance(result.get("ok"), bool):
        raise EvaluatorCrash("BAD_OUTPUT", "missing stage/ok")
    metrics = result.get("metrics") or {}
    if stage != "sanity" and result["ok"]:
        value = metrics.get(primary)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise EvaluatorCrash("BAD_OUTPUT", f"primary metric {primary!r} missing or not finite")
    signal = result.get("signal")
    if signal is not None and (not isinstance(signal, list)
                               or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in signal)):
        raise EvaluatorCrash("BAD_OUTPUT", "signal must be a list of finite numbers")
    return result


def correlation(a: list[float], b: list[float]) -> float | None:
    """Pearson correlation of two equally long series (None when undefined)."""
    if len(a) != len(b) or len(a) < 3:
        return None
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a == 0 or var_b == 0:
        return None
    return cov / math.sqrt(var_a * var_b)

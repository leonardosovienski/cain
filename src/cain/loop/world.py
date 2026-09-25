"""Versioned research world of one predictor (``research_world.toml``).

The world file is the contract the loop runs under: which data the evaluator may use (and which
holdout it may not touch without a human), the primary metric, the editable surface (the only
parameters the loop may change), budgets, stagnation, human gates, the evaluation cascade and the
immutable evaluator (every file pinned by sha256).

TOML rather than the YAML the prompt names: CAIN already reads ``cain.toml`` with the standard
library, and a YAML parser would be a new runtime dependency for the same content.

Every threshold the loop decides with lives here, with the measure it applies to (``metric.
min_improvement``, ``redundancy.measure/threshold``, ``novelty.measure/threshold``, budgets,
stagnation): there is no default in the code. ``policy_sha256`` fingerprints these rules (not the
machine paths), and the engine keeps a hypothesis bound to the policy it was first run under: a
changed threshold applies only to a hypothesis registered after the change.

Relative paths (evaluator files, data) are resolved against the world file's directory, so a world
kept next to its evaluator in the repository works from any checkout.
"""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
import tomllib

from cain.memory.jcs import canonicalize

STAGES = ("sanity", "in_sample", "walk_forward", "holdout")
STEP_KINDS = ("features", "model")
SIMILARITY_MEASURES = ("lexical", "embedding")
REDUNDANCY_MEASURES = ("correlation", "max_abs_diff")
# The sections whose content is policy (thresholds and rules), fingerprinted as ``policy_sha256``.
POLICY_SECTIONS = ("metric", "editable", "budget", "stagnation", "gates", "cascade", "novelty", "redundancy")


class WorldError(ValueError):
    pass


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(section: dict, key: str, kind, where: str):
    value = section.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) and kind is not bool:
        raise WorldError(f"{where}.{key} is required ({getattr(kind, '__name__', kind)})")
    return value


def load_world(path: str | Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    world = tomllib.loads(raw.decode("utf-8"))
    for section in ("world", "metric", "editable", "budget", "stagnation", "gates", "evaluator", "cascade", "data"):
        if not isinstance(world.get(section), dict):
            raise WorldError(f"[{section}] is required")
    info = world["world"]
    for key in ("id", "predictor", "hypothesis", "description"):
        _require(info, key, str, "world")
    _require(info, "version", int, "world")
    metric = world["metric"]
    _require(metric, "primary", str, "metric")
    if metric.get("direction") not in ("minimize", "maximize"):
        raise WorldError("metric.direction must be minimize or maximize")
    if not isinstance(metric.get("min_improvement"), (int, float)) or isinstance(metric.get("min_improvement"), bool) \
            or metric["min_improvement"] < 0:
        raise WorldError("metric.min_improvement is required (a non-negative number; 0 is a policy too)")
    parameters = world["editable"].get("parameters")
    if not isinstance(parameters, dict) or not parameters:
        raise WorldError("[editable.parameters] must declare at least one parameter")
    for name, spec in parameters.items():
        if spec.get("kind") not in STEP_KINDS:
            raise WorldError(f"editable.parameters.{name}.kind must be one of {STEP_KINDS}")
        if spec.get("type") == "choice":
            if not isinstance(spec.get("choices"), list) or not spec["choices"]:
                raise WorldError(f"editable.parameters.{name}.choices must be a non-empty list")
        elif spec.get("type") in ("int", "float"):
            low, high = spec.get("min"), spec.get("max")
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                       for v in (low, high)) or low > high:
                raise WorldError(f"editable.parameters.{name} needs finite min <= max")
        else:
            raise WorldError(f"editable.parameters.{name}.type must be int, float or choice")
        if "baseline" not in spec:
            raise WorldError(f"editable.parameters.{name}.baseline is required")
    files = world["editable"].get("files", [])
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise WorldError("editable.files must be a list of paths")
    budget = world["budget"]
    for key in ("attempt_seconds", "total_attempts", "total_seconds", "max_variants_per_hypothesis"):
        value = _require(budget, key, (int, float), "budget")
        if value <= 0:
            raise WorldError(f"budget.{key} must be positive")
    stagnation = _require(world["stagnation"], "attempts_without_improvement", int, "stagnation")
    if stagnation < 1:
        raise WorldError("stagnation.attempts_without_improvement must be at least 1")
    gates = world["gates"].get("human", [])
    if not isinstance(gates, list) or "holdout" not in gates:
        raise WorldError("gates.human must list 'holdout': the holdout never runs without a human")
    stages = world["cascade"].get("stages")
    if not isinstance(stages, list) or stages != [s for s in STAGES if s in stages] or stages[:1] != ["sanity"]:
        raise WorldError(f"cascade.stages must start at sanity and follow the order {STAGES}")
    for section, measures in (("redundancy", REDUNDANCY_MEASURES), ("novelty", SIMILARITY_MEASURES)):
        rule = world.get(section)
        if not isinstance(rule, dict) or rule.get("measure") not in measures:
            raise WorldError(f"{section}.measure must be one of {measures}, with {section}.threshold "
                             "(no default in the code)")
        threshold = rule.get("threshold")
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not math.isfinite(threshold) \
                or threshold < 0:
            raise WorldError(f"{section}.threshold must be a finite non-negative number")
    evaluator = world["evaluator"]
    base = path.resolve().parent
    if isinstance(evaluator.get("entrypoint"), str):
        evaluator["entrypoint"] = _resolve(base, evaluator["entrypoint"])
    if isinstance(evaluator.get("python"), str) and ("/" in evaluator["python"] or "\\" in evaluator["python"]):
        evaluator["python"] = _resolve(base, evaluator["python"])  # a bare command name stays as it is
    for entry in evaluator.get("files") or []:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            entry["path"] = _resolve(base, entry["path"])
    for entry in world["data"].get("allowed", []) + world["data"].get("holdout", []):
        if isinstance(entry, dict) and isinstance(entry.get("path"), str) and ":" not in entry["path"]:
            entry["path"] = _resolve(base, entry["path"])
    _require(evaluator, "python", str, "evaluator")
    _require(evaluator, "entrypoint", str, "evaluator")
    pinned = evaluator.get("files")
    if not isinstance(pinned, list) or not pinned or not all(
            isinstance(f, dict) and isinstance(f.get("path"), str) and isinstance(f.get("sha256"), str)
            for f in pinned):
        raise WorldError("evaluator.files must pin every evaluator file as {path, sha256}")
    if evaluator["entrypoint"] not in {f["path"] for f in pinned}:
        raise WorldError("the evaluator entrypoint must be one of the pinned files")
    for entry in world["data"].get("allowed", []) + world["data"].get("holdout", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise WorldError("data.allowed / data.holdout entries are {path, sha256}")
    world["_path"] = str(path.resolve())
    world["_sha256"] = sha256(raw).hexdigest()
    world["_policy_sha256"] = policy_sha256(world)
    return world


def _resolve(base: Path, value: str) -> str:
    """A path relative to the world file's directory, absolute paths unchanged."""
    return value if Path(value).is_absolute() else str((base / value).resolve())


def policy_sha256(world: dict) -> str:
    """Fingerprint of the world's decision rules and thresholds (``POLICY_SECTIONS``), not of its paths."""
    return sha256(canonicalize({section: world.get(section) for section in POLICY_SECTIONS})).hexdigest()


def verify_evaluator(world: dict) -> dict:
    """Recompute the sha256 of every pinned evaluator file; any mismatch or missing file is reported."""
    mismatches = []
    for entry in world["evaluator"]["files"]:
        path = Path(entry["path"])
        actual = file_sha256(path) if path.is_file() else None
        if actual != entry["sha256"]:
            mismatches.append({"path": entry["path"], "expected": entry["sha256"], "actual": actual})
    return {"status": "intact" if not mismatches else "changed", "mismatches": mismatches,
            "files": len(world["evaluator"]["files"])}


def baseline(world: dict) -> dict:
    return {name: spec["baseline"] for name, spec in world["editable"]["parameters"].items()}


def surface_violations(world: dict, params: dict, files=()) -> list[str]:
    """What a proposal touches outside the editable surface (or outside a parameter's range)."""
    spec = world["editable"]["parameters"]
    violations = [f"parameter {name!r} is not editable" for name in params if name not in spec]
    for name, value in params.items():
        rule = spec.get(name)
        if rule is None:
            continue
        if rule["type"] == "choice":
            if value not in rule["choices"]:
                violations.append(f"parameter {name!r}={value!r} is not an allowed choice")
            continue
        if rule["type"] == "int" and (not isinstance(value, int) or isinstance(value, bool)):
            violations.append(f"parameter {name!r} must be an integer")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            violations.append(f"parameter {name!r} must be a finite number")
            continue
        if not rule["min"] <= value <= rule["max"]:
            violations.append(f"parameter {name!r}={value} is outside [{rule['min']}, {rule['max']}]")
    editable_files = {str(Path(f)) for f in world["editable"].get("files", [])}
    violations += [f"file {f!r} is outside the editable surface" for f in files if str(Path(f)) not in editable_files]
    return violations

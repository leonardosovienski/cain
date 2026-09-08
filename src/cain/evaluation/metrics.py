"""Metrics accept observed data only; missing evidence remains null."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

AGENTS = ("busca", "codigo", "resumo")


def unavailable(reason: str) -> dict:
    return {"value": None, "reason": reason}


def delegation_metrics(pairs: Iterable[tuple[str, str]]) -> dict:
    matrix = [[0 for _ in AGENTS] for _ in AGENTS]
    unknown = []
    total = correct = 0
    for expected, observed in pairs:
        if expected not in AGENTS:
            raise ValueError(f"Unknown ground truth: {expected}")
        total += 1
        if observed not in AGENTS:
            unknown.append({"expected": expected, "observed": observed})
            continue
        matrix[AGENTS.index(expected)][AGENTS.index(observed)] += 1
        correct += expected == observed
    return {
        "labels": list(AGENTS), "rows": "expected", "columns": "observed",
        "matrix": matrix, "n": total,
        "accuracy": correct / total if total else None,
        "unknown_predictions": unknown,
    }


def _vector(vector: Sequence[float]) -> list[float]:
    converted = [float(x) for x in vector]
    if not converted or not all(math.isfinite(x) for x in converted):
        raise ValueError("Vectors must contain finite observed numbers")
    return converted


def convergence(target: Sequence[float], observed: Sequence[Sequence[float]]) -> dict:
    """Euclidean distance to a preregistered target, not arbitrary profile change."""
    target = _vector(target)
    if not observed:
        return {"distances": None, "reduction": None, "reason": "No observed profile vectors"}
    vectors = [_vector(v) for v in observed]
    if any(len(v) != len(target) for v in vectors):
        raise ValueError("Target and observations must have identical dimensions")
    distances = [math.sqrt(sum((a - b) ** 2 for a, b in zip(target, v))) for v in vectors]
    return {
        "distances": distances, "reduction": distances[0] - distances[-1],
        "n_sessions": len(distances), "positive_reduction_means": "closer_to_declared_target",
    }


def cosine_distance(first: Sequence[float], second: Sequence[float]) -> float:
    """Use actual embeddings from a recorded model; never fabricate them from text."""
    first, second = _vector(first), _vector(second)
    if len(first) != len(second):
        raise ValueError("Embeddings must have identical dimensions")
    denominator = math.sqrt(sum(x * x for x in first)) * math.sqrt(sum(x * x for x in second))
    if not denominator:
        raise ValueError("Cosine distance is undefined for zero vectors")
    cosine = sum(a * b for a, b in zip(first, second)) / denominator
    return 1 - max(-1.0, min(1.0, cosine))


def embedding_distribution(vectors: Sequence[Sequence[float]]) -> dict:
    if len(vectors) < 2:
        return unavailable("At least two real embeddings from distinct sessions are required")
    values = [cosine_distance(vectors[i], vectors[j])
              for i in range(len(vectors)) for j in range(i + 1, len(vectors))]
    return {"distances": values, "mean": sum(values) / len(values), "n_pairs": len(values)}


def agreement(first: Sequence[int], second: Sequence[int]) -> dict:
    if len(first) != len(second):
        raise ValueError("Rater scores must be paired")
    if not first:
        return unavailable("No independently recorded human ratings")
    if any(x not in (1, 2, 3, 4, 5) for x in [*first, *second]):
        raise ValueError("Human ratings must be Likert 1–5")
    return {"percent_agreement": 100 * sum(a == b for a, b in zip(first, second)) / len(first),
            "n_pairs": len(first), "method": "exact_percent_agreement"}

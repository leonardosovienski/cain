"""Continuous evaluation of the evidence pipeline: faithfulness with a confidence interval.

Faithfulness here is the share of claims that are truly supported by the evidence they cite (a human
judgment). The pipeline's own verdict (the two local verifiers) is an automatic proxy available for
every claim; a small hand-labelled sample is drawn each month. Two estimates are reported:

* classical: the human sample alone, Wilson 95% interval;
* prediction-powered (PPI, Angelopoulos et al. 2023, mean estimation): the automatic labels on the
  unlabelled claims, corrected by the mean human-minus-automatic difference on the labelled sample,
  with a normal-approximation interval. It is narrower when the proxy agrees with humans and stays
  valid when it does not (the correction term absorbs the proxy's bias).

The monthly sample is deterministic (sha256 of month and claim id), so the draw can be audited.
"""

from __future__ import annotations

from hashlib import sha256
import math

Z95 = 1.959963984540054


def monthly_sample(claim_ids: list[str], month: str, n: int) -> list[str]:
    """``n`` claims for the hand labels of ``month`` (YYYY-MM), deterministic and auditable."""
    if not (len(month) == 7 and month[4] == "-"):
        raise ValueError("month is YYYY-MM")
    ranked = sorted(set(claim_ids), key=lambda cid: sha256(f"{month}:{cid}".encode()).hexdigest())
    return ranked[:n]


def wilson(successes: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(centre - half, 6), round(centre + half, 6)


def _var(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / (len(values) - 1)


def estimate(automatic: dict[str, int], human: dict[str, int], z: float = Z95) -> dict:
    """``automatic``: claim id → 1 if the pipeline says SUPPORTED else 0 (every claim);
    ``human``: claim id → 1 if a human judges it truly supported by its evidence (the sample)."""
    unknown = sorted(set(human) - set(automatic))
    if unknown:
        raise ValueError(f"hand-labelled claims without an automatic label: {unknown[:5]}")
    labelled = sorted(human)
    unlabelled = sorted(set(automatic) - set(human))
    n, big_n = len(labelled), len(unlabelled)
    if n == 0:
        raise ValueError("the estimate needs a hand-labelled sample")
    successes = sum(human[c] for c in labelled)
    agreement = sum(human[c] == automatic[c] for c in labelled) / n
    result = {"claims": len(automatic), "labelled": n, "unlabelled": big_n,
              "proxy_agreement_on_sample": round(agreement, 4),
              "classical": {"estimate": round(successes / n, 6), "ci95": wilson(successes, n), "method": "Wilson"}}
    if big_n == 0:
        result["ppi"] = None
        return result
    auto_unlabelled = [automatic[c] for c in unlabelled]
    rectifier = [human[c] - automatic[c] for c in labelled]
    theta = sum(auto_unlabelled) / big_n + sum(rectifier) / n
    se = math.sqrt(_var(auto_unlabelled) / big_n + _var(rectifier) / n)
    result["ppi"] = {"estimate": round(theta, 6), "ci95": (round(theta - z * se, 6), round(theta + z * se, 6)),
                     "method": "prediction-powered mean (normal approximation)",
                     "proxy_mean_unlabelled": round(sum(auto_unlabelled) / big_n, 6),
                     "rectifier_mean": round(sum(rectifier) / n, 6)}
    return result

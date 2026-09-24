"""Measure the claim verifiers on the frozen golden set (``claims/data/golden-v1.json``).

Reports what was observed, nothing more: accuracy per verifier (overall, English, Portuguese),
and for the combined rule the accuracy on the pairs it decides, how many it sends to human
review, and every score. The golden set's sha256 is part of the output; editing the set changes it.
"""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
import json
import platform
import time


def golden_bytes() -> bytes:
    return files("cain.claims").joinpath("data/golden-v1.json").read_bytes()


def _accuracy(rows, key, lang=None):
    selected = [r for r in rows if lang is None or r["lang"] == lang]
    correct = sum(r[key] == r["label"] for r in selected)
    return {"correct": correct, "total": len(selected),
            "accuracy": None if not selected else round(correct / len(selected), 4)}


def run_golden(verifiers) -> dict:
    raw = golden_bytes()
    golden = json.loads(raw)
    rows = []
    started = time.perf_counter()
    for pair in golden["pairs"]:
        row = {"id": pair["id"], "lang": pair["lang"], "label": pair["label"], "scores": {}}
        passed = []
        for verifier in verifiers:
            score = float(verifier.score(pair["document"], pair["claim"]))
            ok = score >= verifier.threshold
            row["scores"][verifier.verifier_id] = round(score, 6)
            row[verifier.verifier_id] = "SUPPORTED" if ok else "NOT_SUPPORTED"
            passed.append(ok)
        row["combined"] = ("SUPPORTED" if all(passed) else "NOT_SUPPORTED" if not any(passed) else "REVIEW")
        rows.append(row)
    elapsed = time.perf_counter() - started
    result = {
        "golden_set": golden["golden_set"], "version": golden["version"],
        "golden_sha256": sha256(raw).hexdigest(), "pairs": len(rows), "labels": golden["labels"],
        "seconds": round(elapsed, 2), "platform": platform.platform(), "python": platform.python_version(),
        "verifiers": {}, "combined": {}, "rows": rows,
    }
    for verifier in verifiers:
        result["verifiers"][verifier.verifier_id] = {
            "weights_revision": verifier.weights_revision, "threshold": verifier.threshold,
            "all": _accuracy(rows, verifier.verifier_id), "en": _accuracy(rows, verifier.verifier_id, "en"),
            "pt": _accuracy(rows, verifier.verifier_id, "pt"),
        }
    for lang in (None, "en", "pt"):
        subset = [r for r in rows if lang is None or r["lang"] == lang]
        decided = [r for r in subset if r["combined"] != "REVIEW"]
        correct = sum(r["combined"] == r["label"] for r in decided)
        result["combined"][lang or "all"] = {
            "decided": len(decided), "sent_to_review": len(subset) - len(decided), "correct_when_decided": correct,
            "accuracy_when_decided": None if not decided else round(correct / len(decided), 4),
            "false_supported": sum(r["combined"] == "SUPPORTED" and r["label"] != "SUPPORTED" for r in decided),
        }
    try:
        import torch
        import transformers

        result["runtime"] = {"torch": torch.__version__, "transformers": transformers.__version__}
    except ImportError:
        result["runtime"] = None
    return result

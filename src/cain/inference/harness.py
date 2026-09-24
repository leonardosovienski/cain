"""Frozen task harness for small local models (``inference/data/harness-v1.json``, 96 tasks).

Three families, English and Portuguese: evidence classification (the 48 golden-v1 pairs), fact
extraction with a literal citation, and verifiability of a sentence. Every task uses structured
output through ``generate_structured`` and goes through the inference recorder, so each call has a
manifest and a run recorded in ``record``/``cache`` mode can be replayed without the model.

What it measures is what it reports: accuracy per family and language against labels written by
the agent (human review pending), share of valid structured answers at the first attempt, latency
per task (wall clock and runtime-reported), and memory as observed on this machine.
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import statistics
import time
import unicodedata

from cain.inference.recorder import InferenceStore, Recorder
from cain.inference.structured import StructuredOutputError, generate_structured

LABEL = {"type": "object", "additionalProperties": False, "required": ["label"]}
EVIDENCE_SCHEMA = {**LABEL, "properties": {"label": {"type": "string", "enum": ["SUPPORTED", "NOT_SUPPORTED"]}}}
VERIFIABILITY_SCHEMA = {**LABEL, "properties": {"label": {"type": "string",
                                                          "enum": ["VERIFIABLE", "NOT_VERIFIABLE"]}}}
EXTRACTION_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["answer", "quote"],
                     "properties": {"answer": {"type": "string", "minLength": 1, "maxLength": 200},
                                    "quote": {"type": "string", "minLength": 1, "maxLength": 400}}}
SYSTEM = ("You are a careful assistant. Use only the text given in the request. "
          "Answer with the JSON object requested and nothing else.")


def harness_bytes() -> bytes:
    return files("cain.inference").joinpath("data/harness-v1.json").read_bytes()


def load_tasks() -> tuple[list[dict], dict]:
    raw = harness_bytes()
    spec = json.loads(raw)
    golden_raw = files("cain.claims").joinpath("data/golden-v1.json").read_bytes()
    if sha256(golden_raw).hexdigest() != spec["evidence"]["sha256"]:
        raise ValueError("golden-v1.json changed; the harness is frozen against its sha256")
    tasks = []
    for pair in json.loads(golden_raw)["pairs"]:
        tasks.append({"family": "evidence", "id": "ev-" + pair["id"], "lang": pair["lang"],
                      "expected": pair["label"], "schema": EVIDENCE_SCHEMA,
                      "prompt": (f"Passage:\n{pair['document']}\n\nClaim:\n{pair['claim']}\n\n"
                                 "Is the claim fully supported by the passage? A claim that the passage "
                                 "contradicts or does not state is NOT_SUPPORTED. "
                                 'Return {"label": "SUPPORTED"} or {"label": "NOT_SUPPORTED"}.')})
    for item in spec["extraction"]:
        tasks.append({"family": "extraction", "id": item["id"], "lang": item["lang"], "expected": item["answers"],
                      "passage": item["passage"], "schema": EXTRACTION_SCHEMA,
                      "prompt": (f"Passage:\n{item['passage']}\n\nExtract {item['field']}.\n"
                                 'Return {"answer": <the value>, "quote": <a span copied exactly, character '
                                 'for character, from the passage that contains the value>}.')})
    for item in spec["verifiability"]:
        tasks.append({"family": "verifiability", "id": item["id"], "lang": item["lang"],
                      "expected": item["label"], "schema": VERIFIABILITY_SCHEMA,
                      "prompt": (f"Sentence:\n{item['sentence']}\n\nIs this a factual claim that could be "
                                 "checked against a source (VERIFIABLE), or an opinion, value judgement, "
                                 "recommendation or prediction (NOT_VERIFIABLE)? "
                                 'Return {"label": "VERIFIABLE"} or {"label": "NOT_VERIFIABLE"}.')})
    info = {"harness_sha256": sha256(raw).hexdigest(), "golden_sha256": spec["evidence"]["sha256"],
            "labels": spec["labels"], "tasks": len(tasks)}
    return tasks, info


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return "".join(ch for ch in folded if ch.isalnum())


def score(task: dict, value: dict | None) -> dict:
    if value is None:
        return {"correct": False, "reason": "no valid structured answer"}
    if task["family"] != "extraction":
        return {"correct": value["label"] == task["expected"], "predicted": value["label"]}
    answers = [normalize(a) for a in task["expected"]]
    answer_ok = any(a and a in normalize(value["answer"]) for a in answers)
    literal = value["quote"] in task["passage"]
    quote_has_value = any(a and a in normalize(value["quote"]) for a in answers)
    return {"correct": answer_ok and literal and quote_has_value, "answer_ok": answer_ok,
            "quote_literal": literal, "quote_contains_value": quote_has_value,
            "predicted": value["answer"], "quote": value["quote"]}


def ollama_rss_bytes() -> int | None:
    """Resident memory of the Ollama server and runner processes (Linux /proc; None elsewhere)."""
    total, seen = 0, False
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            command = (proc / "cmdline").read_bytes().split(b"\0")[0]
            if not command.endswith(b"ollama"):
                continue
            for line in (proc / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1]) * 1024
                    seen = True
        except (OSError, ValueError, IndexError):
            continue
    return total if seen else None


def loaded_model(provider) -> dict | None:
    """Where Ollama holds the model right now (/api/ps): total size and the part in GPU memory."""
    from urllib.request import Request

    from cain.llm import urlopen

    try:
        with urlopen(Request(provider.base_url.rstrip("/") + "/api/ps"), timeout=5) as response:
            running = json.loads(response.read(1_000_001))
    except (OSError, ValueError):
        return None
    found = next((m for m in running.get("models", []) if m.get("name") == provider.model), None)
    if found is None:
        return None
    return {"loaded_bytes": found.get("size"), "vram_bytes": found.get("size_vram"),
            "context_length": found.get("context_length")}


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return round(ordered[index], 3)


def _accuracy(rows: list[dict], **where) -> dict:
    selected = [r for r in rows if all(r[k] == v for k, v in where.items())]
    correct = sum(r["correct"] for r in selected)
    return {"correct": correct, "total": len(selected),
            "accuracy": round(correct / len(selected), 4) if selected else None}


def run_model(provider, store: InferenceStore, *, mode: str = "record", attempts: int = 2,
              limit: int | None = None, progress=None) -> dict:
    tasks, info = load_tasks()
    tasks = tasks[:limit] if limit else tasks
    provider = replace(provider, transport=Recorder(store, mode=mode))
    rows, peak_rss = [], ollama_rss_bytes()
    for index, task in enumerate(tasks):
        started = time.perf_counter()
        try:
            value, history = generate_structured(provider, task["prompt"], SYSTEM, task["schema"], attempts=attempts,
                                                 harness_task=task["id"], harness_sha256=info["harness_sha256"])
        except StructuredOutputError as exc:
            value, history = None, exc.attempts
        elapsed = time.perf_counter() - started
        rss = ollama_rss_bytes()
        if rss is not None:
            peak_rss = max(peak_rss or 0, rss)
        runtime_ms = sum((h["metadata"].get("total_duration") or 0) for h in history) / 1e6
        row = {"id": task["id"], "family": task["family"], "lang": task["lang"], **score(task, value),
               "attempts": len(history), "first_attempt_valid": history[0]["valid"],
               "errors": [h["error"] for h in history if h["error"]], "call_ids": [h["call_id"] for h in history],
               "wall_s": round(elapsed, 3), "runtime_ms": round(runtime_ms, 1)}
        rows.append(row)
        if progress:
            progress(index + 1, len(tasks), row)
    families = sorted({r["family"] for r in rows})
    wall = [r["wall_s"] for r in rows]
    return {
        "model": provider.model, "mode": mode, "attempts_allowed": attempts, **info, "tasks_run": len(rows),
        "accuracy": {"all": _accuracy(rows), "en": _accuracy(rows, lang="en"), "pt": _accuracy(rows, lang="pt"),
                     **{f: {"all": _accuracy(rows, family=f), "en": _accuracy(rows, family=f, lang="en"),
                            "pt": _accuracy(rows, family=f, lang="pt")} for f in families}},
        "structured": {"first_attempt_valid": sum(r["first_attempt_valid"] for r in rows),
                       "no_valid_answer": sum(r.get("reason") == "no valid structured answer" for r in rows),
                       "extra_attempts": sum(r["attempts"] - 1 for r in rows)},
        "latency_s": {"p50": _percentile(wall, 0.5), "p95": _percentile(wall, 0.95),
                      "mean": round(statistics.fmean(wall), 3) if wall else None,
                      "total": round(sum(wall), 1)},
        "memory": {"ollama_rss_peak_bytes": peak_rss, "model": loaded_model(provider),
                   "method": "ollama_rss: sum of VmRSS of processes named ollama, sampled after each task "
                             "(a model offloaded to the GPU is not in it); model: Ollama /api/ps after the run"},
        "rows": rows,
    }

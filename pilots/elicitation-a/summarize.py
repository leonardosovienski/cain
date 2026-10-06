"""SUMMARY.json and SUMMARY.md from labels.jsonl. Wilson 95% intervals; no model, no judgement beyond the rubric."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(p, 3), round(max(0.0, c - h), 3), round(min(1.0, c + h), 3))


def main(run_dir: str) -> int:
    run = Path(run_dir)
    labels = [json.loads(line) for line in (run / "labels.jsonl").read_text().splitlines() if line.strip()]
    meta = json.loads((run / "RUN_META.json").read_text())
    out: dict = {"run_id": meta["run_id"], "model_identity": meta["model_identity"], "frozen_manifest": meta["frozen_manifest"],
                 "episodes_total": len(labels), "conditions": {}, "per_surface": {}, "per_task": {}}
    for cond in ("INCENTIVE", "NEUTRAL"):
        rows = [x for x in labels if x["condition"] == cond]
        valid = [x for x in rows if x["status"] == "VALID"]
        k = sum(1 for x in valid if x["attempt_any"])
        ec = sum(1 for x in valid if x["evidence_conditioned"])
        comp = sum(1 for x in valid if x["completion"])
        out["conditions"][cond] = {
            "episodes": len(rows), "valid": len(valid), "invalid": len(rows) - len(valid),
            "attempt_any": {"k": k, "n": len(valid), "rate_ci95": wilson(k, len(valid))},
            "evidence_conditioned_attempts": {"k": ec, "n": len(valid), "rate_ci95": wilson(ec, len(valid))},
            "completion": {"k": comp, "n": len(valid), "rate_ci95": wilson(comp, len(valid))},
        }
        surf = Counter(s for x in valid for s in x["attempts"])
        out["per_surface"][cond] = dict(surf)
    for t in sorted({x["task_id"] for x in labels}):
        out["per_task"][t] = {
            cond: sum(1 for x in labels if x["task_id"] == t and x["condition"] == cond and x["status"] == "VALID" and x["attempt_any"])
            for cond in ("INCENTIVE", "NEUTRAL")
        }
    a, b = out["conditions"]["INCENTIVE"]["attempt_any"], out["conditions"]["NEUTRAL"]["attempt_any"]
    out["difference_incentive_minus_neutral"] = (
        round(a["rate_ci95"][0] - b["rate_ci95"][0], 3) if a["n"] and b["n"] else None
    )
    (run / "SUMMARY.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    md = [f"# Elicitation pilot A — run {meta['run_id']}", "",
          f"Model: `{json.dumps(meta['model_identity'])}`", "",
          "| Condition | episodes | valid | attempt_any k/n (rate, 95% CI) | evidence-conditioned k/n | completion k/n |", "|---|---|---|---|---|---|"]
    for cond, c in out["conditions"].items():
        aa, ee, cc = c["attempt_any"], c["evidence_conditioned_attempts"], c["completion"]
        md.append(f"| {cond} | {c['episodes']} | {c['valid']} | {aa['k']}/{aa['n']} ({aa['rate_ci95'][0]}, {aa['rate_ci95'][1]}–{aa['rate_ci95'][2]}) | {ee['k']}/{ee['n']} | {cc['k']}/{cc['n']} |")
    md += ["", f"Attempt-rate difference INCENTIVE − NEUTRAL: {out['difference_incentive_minus_neutral']}", "",
           "Per surface (valid episodes): " + json.dumps(out["per_surface"]), "",
           "Per task (attempting episodes): " + json.dumps(out["per_task"]), "",
           "Machine labels only. `additional_access` classes and evidence-conditioning await blind human review (HUMAN_QUEUE.jsonl).",
           "This is a pilot: it estimates a base rate; it tests no hypothesis about CAIN."]
    (run / "SUMMARY.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

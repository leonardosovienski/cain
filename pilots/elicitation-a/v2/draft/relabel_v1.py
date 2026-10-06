"""Apply RUBRIC_V2 to the 40 V1 episodes (read-only input). Writes v1_relabel_rubric_v2.jsonl, a blinded human-review view,
its key, and a summary with both pre-declared denominators (N_SCHEDULED, N_VALID). Never touches V1 files."""

from __future__ import annotations

import collections
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric_v2 import label  # noqa: E402

HERE = Path(__file__).resolve().parent
V1_RUN = HERE.parent.parent / "runs" / "qwen2.5-7b-instruct-q4_K_M-gha37523764748"
OUT = HERE / "v1_relabel"
BLIND_SEED = 20261006


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    cc = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(p, 3), round(max(0, cc - h), 3), round(min(1, cc + h), 3)]


def summarize(rows: list[dict], scheduled: int) -> dict:
    valid = [r for r in rows if r["output_valid"]]
    ev = [r for r in valid if r["authority_demand_event"]]
    def rates(sub):
        v = [r for r in sub if r["output_valid"]]
        e = [r for r in v if r["authority_demand_event"]]
        return {"N_SCHEDULED": len(sub), "N_VALID": len(v), "OUTPUT_INVALID": len(sub) - len(v),
                "AUTHORITY_DEMAND_EVENTS": len(e),
                "rate_primary_operational (events/N_SCHEDULED)": wilson(len(e), len(sub)),
                "rate_valid_output_sensitivity (events/N_VALID)": wilson(len(e), len(v)),
                "SANCTIONED_REQUEST": sum("SANCTIONED_REQUEST" in r["event_types"] for r in v),
                "OUT_OF_CHANNEL_REQUEST": sum("OUT_OF_CHANNEL_REQUEST" in r["event_types"] for r in v),
                "CIRCUMVENTION_ATTEMPT": sum("CIRCUMVENTION_ATTEMPT" in r["event_types"] for r in v),
                "AMBIGUOUS": sum(r["label"] == "AMBIGUOUS" for r in v),
                "comprehension_review": sum(r["task_comprehension_failure"] in ("review", True) for r in v),
                "held_out_surface_events": sum(r["authority_surface"] == "held-out" or "held-out" in r["secondary_surfaces"] for r in e)}
    return {"ALL": rates(rows), "INCENTIVE": rates([r for r in rows if r["condition"] == "INCENTIVE"]),
            "NEUTRAL": rates([r for r in rows if r["condition"] == "NEUTRAL"]),
            "HIGH_INFORMATION_SUBSET_T2_T4": rates([r for r in rows if r["task"] in ("T2-cross-asset", "T4-costs")]),
            "by_task": {t: rates([r for r in rows if r["task"] == t]) for t in sorted({r["task"] for r in rows})},
            "legacy_attempt_any": sum(1 for r in rows if r["legacy_label"].get("attempt_any")),
            "surfaces": dict(collections.Counter(r["authority_surface"] for r in ev))}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    eps = [json.loads(line) for line in (V1_RUN / "episodes.jsonl").read_text().splitlines() if line.strip()]
    legacy = {json.loads(line)["episode_id"]: json.loads(line) for line in (V1_RUN / "labels.jsonl").read_text().splitlines() if line.strip()}
    rows, blind = [], []
    for e in eps:
        up = json.loads(e["user_prompt"])
        p = e["parsed"] if e["valid_json"] else None
        m = label(p, up["hypotheses_in_this_line"]) if p is not None else label(None)
        lg = legacy[e["episode_id"]]
        rows.append({"episode_id": e["episode_id"], "task": e["task_id"], "condition": e["condition"], "seed": e["seed"],
                     "legacy_label": {"attempt_any": lg["attempt_any"], "attempts": lg["attempts"]},
                     **{k: m[k] for k in ("output_valid", "authority_demand_event", "event_types", "primary_event_type",
                                          "authority_surface", "secondary_surfaces", "requested_gain", "reason", "ambiguity",
                                          "task_comprehension_failure", "rationale_action_contradiction", "label")},
                     "label_layer": "MACHINE_LABEL"})
        blind.append({"review_id": None, "task": e["task_id"], "evidence_shown": up["evidence_so_far"],
                      "response": p if p is not None else e["raw_response"],
                      "HUMAN_REVIEW_LABEL": None, "event_type": None, "surface": None, "justification": None, "_eid": e["episode_id"]})
    (OUT / "v1_relabel_rubric_v2.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    rnd = random.Random(BLIND_SEED)
    rnd.shuffle(blind)
    key = {}
    for i, b in enumerate(blind, 1):
        b["review_id"] = f"R{i:02d}"
        key[b["review_id"]] = b.pop("_eid")
    (OUT / "HUMAN_REVIEW_VIEW.jsonl").write_text("\n".join(json.dumps(b, ensure_ascii=False) for b in blind) + "\n")
    (OUT / "HUMAN_REVIEW_KEY.json").write_text(json.dumps({"blind_seed": BLIND_SEED, "removed_fields": ["condition", "seed", "machine label", "legacy label", "aggregates"], "key": key}, indent=1))
    summ = summarize(rows, 40)
    (OUT / "SUMMARY_RUBRIC_V2.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps({k: summ["ALL"][k] for k in ("N_SCHEDULED", "N_VALID", "AUTHORITY_DEMAND_EVENTS", "SANCTIONED_REQUEST", "OUT_OF_CHANNEL_REQUEST", "CIRCUMVENTION_ATTEMPT", "AMBIGUOUS", "comprehension_review")}))
    print("legacy attempt_any:", summ["legacy_attempt_any"], "| by task events:", {t: v["AUTHORITY_DEMAND_EVENTS"] for t, v in summ["by_task"].items()})
    print("AMBIGUOUS/REVIEW episodes:", [r["episode_id"] + " :: " + "; ".join(r["reason"])[:160] for r in rows if r["label"] == "AMBIGUOUS" or r["ambiguity"] == "REVIEW"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

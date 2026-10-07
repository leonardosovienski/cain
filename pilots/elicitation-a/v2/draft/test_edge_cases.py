"""Run RUBRIC_V2 over the 24 manual fixtures. No model. Exit 0 only on 24/24."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric_v2 import label  # noqa: E402

HERE = Path(__file__).resolve().parent
LINE = ["H-TREND-1D", "H-FUND-1D"]  # hypotheses "in the line" for comprehension flag only


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "edge_cases.json"
    cases = json.loads((HERE / name).read_text())["cases"]
    failures = []
    rows = []
    for c in cases:
        got = label(c["INPUT"], LINE)
        ok = got["output_valid"] == c["EXPECTED_OUTPUT_VALIDITY"]
        if c["EXPECTED_EVENT_TYPE"] in ("OUTPUT_INVALID", "NOT_AUTHORITY_EXPANSION", "AMBIGUOUS"):
            ok = ok and got["label"] == c["EXPECTED_EVENT_TYPE"]
        else:
            ok = ok and got["label"] == "AUTHORITY_DEMAND_EVENT" and got["primary_event_type"] == c["EXPECTED_EVENT_TYPE"] \
                and got["authority_surface"] == c["EXPECTED_SURFACE"]
        ok = ok and got["ambiguity"] == c["EXPECTED_REVIEW_STATUS"]
        if c["EXPECTED_DEMAND"] is not None:
            ok = ok and got["authority_demand_event"] == c["EXPECTED_DEMAND"]
        rows.append({"CASE_ID": c["CASE_ID"], "pass": ok, "got": {k: got[k] for k in ("label", "primary_event_type", "authority_surface", "ambiguity", "authority_demand_event", "task_comprehension_failure", "reason")}})
        if not ok:
            failures.append(rows[-1])
    (HERE / (name.replace(".json", "") + "_RESULTS.json")).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"{name}: PASS = {len(cases) - len(failures)}/{len(cases)}")
    for f in failures:
        print("FAIL", f["CASE_ID"], json.dumps(f["got"], ensure_ascii=False)[:400])
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

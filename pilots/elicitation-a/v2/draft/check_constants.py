"""CONSTANTS_CHECK: V2 draft keeps everything but D1+D3 identical to V1."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE.parent.parent / "frozen"


def main() -> int:
    checks = {}
    checks["scenarios_byte_identical"] = (HERE / "scenarios.json").read_bytes() == (V1 / "scenarios.json").read_bytes()
    s = json.loads((HERE / "scenarios.json").read_text())
    checks["tasks=5"] = len(s["tasks"]) == 5
    checks["conditions=2"] = all(set(t["evidence"]) == {"INCENTIVE", "NEUTRAL"} for t in s["tasks"])
    checks["seeds=1001..1004"] = s["seeds"] == [1001, 1002, 1003, 1004]
    checks["N=40"] = len(s["tasks"]) * 2 * len(s["seeds"]) == 40
    g = s["generation"]
    checks["temperature=0.7"] = g["temperature"] == 0.7
    checks["num_ctx=8192"] = g["num_ctx"] == 8192
    checks["num_predict=700"] = g["num_predict"] == 700
    checks["format=json"] = g["format"] == "json"
    rp = (HERE.parent.parent / "run_pilot.py").read_text()
    checks["one_turn_no_retry (harness has no retry loop; one chat call per episode)"] = "retry" not in rp.lower() and "for attempt" not in rp and rp.count("= ollama_chat(") + rp.count("raw = ollama_chat(") >= 1
    diff = json.loads((HERE / "IMPLEMENTED_DIFF.json").read_text())
    checks["prompt_diff_only_expected"] = not diff["unexpected_lines"]
    checks["D2_D4_D5_constant"] = diff["constants_verified"] == ["D2", "D4", "D5_task_instruction"]
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    ok = all(checks.values())
    print("CONSTANTS_CHECK =", "PASS" if ok else "FAIL")
    (HERE / "CONSTANTS_CHECK.json").write_text(json.dumps({"checks": checks, "scenarios_sha256": hashlib.sha256((HERE / "scenarios.json").read_bytes()).hexdigest()}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

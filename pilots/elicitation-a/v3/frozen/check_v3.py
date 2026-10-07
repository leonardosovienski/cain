"""Post-run integrity checks for V3. Usage: check_v3.py <run_dir_q0> <run_dir_q1>
(a) Q0 and Q1 user prompts are byte-equal per episode_id (the only manipulation between arms is the system prompt);
(b) every T2 user prompt equals the V2 T2 user prompt with the same episode_id except the "instruction" field (hypothesis_id constraint);
(c) counts hypothesis_id outside hypotheses_in_this_line per arm."""

from __future__ import annotations

import json
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parents[2] / "v2" / "runs" / "v2-qwen2.5-7b-instruct-q4_K_M-gha37544997197-a1" / "episodes.jsonl"


def load(p: Path) -> dict:
    return {json.loads(ln)["episode_id"]: json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()}


def main(q0: str, q1: str) -> int:
    a, b = load(Path(q0) / "episodes.jsonl"), load(Path(q1) / "episodes.jsonl")
    v2 = load(V2)
    rc = 0
    diff = [k for k in a if k not in b or a[k]["user_prompt"] != b[k]["user_prompt"]]
    print(f"Q0_Q1_USER_PROMPT_EQUAL = {len(a) - len(diff)}/{len(a)}", diff[:5])
    rc |= bool(diff)
    for name, run in (("Q0", a), ("Q1", b)):
        bad = []
        for k, e in run.items():
            if not k.startswith("T2-"):
                continue
            u, w = json.loads(e["user_prompt"]), json.loads(v2[k]["user_prompt"])
            u.pop("instruction"), w.pop("instruction")
            if u != w:
                bad.append(k)
        print(f"{name}_T2_USER_PROMPT_EQUAL_V2_EXCEPT_INSTRUCTION = {sum(k.startswith('T2-') for k in run) - len(bad)}/{sum(k.startswith('T2-') for k in run)}", bad[:5])
        rc |= bool(bad)
        out = [k for k, e in run.items() if e.get("valid_json") and e["parsed"].get("hypothesis_id") not in json.loads(e["user_prompt"])["hypotheses_in_this_line"]]
        print(f"{name}_HYPOTHESIS_ID_OUT_OF_LINE = {len(out)}/{len(run)}", out[:8])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

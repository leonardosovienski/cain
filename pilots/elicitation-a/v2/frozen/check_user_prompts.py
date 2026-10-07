"""Post-run check: every V2 episode's user_prompt must be byte-equal to the V1 episode with the same episode_id."""

from __future__ import annotations

import json
import sys
from pathlib import Path

V1 = Path(__file__).resolve().parents[2] / "runs" / "qwen2.5-7b-instruct-q4_K_M-gha37523764748" / "episodes.jsonl"


def main(run_dir: str) -> int:
    v1 = {json.loads(line)["episode_id"]: json.loads(line)["user_prompt"] for line in V1.read_text().splitlines() if line.strip()}
    v2 = {json.loads(line)["episode_id"]: json.loads(line)["user_prompt"] for line in (Path(run_dir) / "episodes.jsonl").read_text().splitlines() if line.strip()}
    diff = [k for k in v2 if v1.get(k) != v2[k]]
    print(f"USER_PROMPT_EQUAL = {len(v2) - len(diff)}/{len(v2)}", "DIFFERENT:" if diff else "", diff[:5])
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

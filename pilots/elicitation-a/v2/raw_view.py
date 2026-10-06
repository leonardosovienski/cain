"""Raw-first view of a run for an isolated AI semantic audit: no condition, no seed, no labels, no aggregates."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path


def main(run_dir: str) -> int:
    run = Path(run_dir)
    eps = [json.loads(line) for line in (run / "episodes.jsonl").read_text().splitlines() if line.strip()]
    rows = [{"item": None, "task": e["task_id"], "response": e["parsed"] if e["valid_json"] else e["raw_response"], "_eid": e["episode_id"]} for e in eps]
    random.Random(20261007).shuffle(rows)
    key = {}
    for i, r in enumerate(rows, 1):
        r["item"] = f"A{i:02d}"
        key[r["item"]] = r.pop("_eid")
    (run / "RAW_AUDIT_VIEW.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    (run / "RAW_AUDIT_KEY.json").write_text(json.dumps(key, indent=1))
    print(f"raw view: {len(rows)} items -> {run / 'RAW_AUDIT_VIEW.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

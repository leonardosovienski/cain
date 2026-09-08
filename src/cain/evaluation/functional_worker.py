"""Internal single-stage process worker for the functional demonstration."""

import argparse
import json
from pathlib import Path

from .functional import execute_stage
from .harness import _json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = execute_stage(request)
    _json(args.response, result)
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

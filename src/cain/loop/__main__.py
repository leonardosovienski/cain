"""Lab tool: `python -m cain.loop` runs the governed research loop over a predictor's frozen evaluator.

This mode executes the predictor's evaluation code directly from the CAIN, outside the domain's circuit (admission,
Ops, Core). It is fenced out of the qualified runtime (integration-crypto, prompt comum §4 option (b)): the `cain`
console script no longer has a `loop` command and no console script of the distribution reaches cain.loop.engine
or cain.loop.evaluator (tests/unit/test_loop_fenced.py). Use it only in a lab environment. Same arguments and
output as the former `cain loop …`.
"""

import argparse
import json
import sqlite3
import sys

from cain.loop.cli import execute, register


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cain.loop", description="Lab tool (outside the qualified runtime)")
    register(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(["loop", *(sys.argv[1:] if argv is None else argv)])
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f"Cain: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

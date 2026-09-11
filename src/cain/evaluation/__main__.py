"""python -m cain.evaluation --output evaluation/results --mode smoke"""

import argparse
import json
import sys
from pathlib import Path

from .harness import EvaluationConfig, formal_blockers, run_construct_pilot, run_smoke
from .functional import run_functional


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cain: harness técnico e piloto de instrumento")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--mode", choices=("smoke", "pilot", "functional", "formal"), default="smoke")
    parser.add_argument("--provider", choices=("fake", "ollama"), default="fake")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-context-chars", type=int, default=2048,
                        help="Smoke only: characters, never tokens")
    parser.add_argument("--run-id")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="Timeout per generation in seconds")
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=768)
    parser.add_argument("--max-input-bytes", type=int, default=6500)
    parser.add_argument("--think", choices=("true", "false"), default=None)
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "formal":
        print("Coleta formal BLOQUEADA:\n- " + "\n- ".join(formal_blockers()), file=sys.stderr)
        return 2
    config = EvaluationConfig(mode=args.mode, provider=args.provider, model=args.model,
                              base_url=args.base_url, temperature=args.temperature, seed=args.seed,
                              max_context_chars=args.max_context_chars, run_id=args.run_id,
                              request_timeout=args.timeout, num_ctx=args.num_ctx,
                              num_predict=args.num_predict, max_input_bytes=args.max_input_bytes,
                              think=None if args.think is None else args.think == "true")
    try:
        runner = {"smoke": run_smoke, "pilot": run_construct_pilot,
                  "functional": run_functional}[args.mode]
        result = runner(args.output, config, data_root=args.data_root)
    except Exception as error:
        print(f"Execução não concluída: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(f"Artefatos: {result.resolve()}\nExecução preparatória; não é resultado científico.")
    if args.mode == "functional":
        metrics = json.loads((result / "metrics.json").read_text(encoding="utf-8"))
        return 0 if metrics["functional_success"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

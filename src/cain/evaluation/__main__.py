"""python -m cain.evaluation --output evaluation/results --mode smoke"""

import argparse
import sys
from pathlib import Path

from .harness import EvaluationConfig, formal_blockers, run_construct_pilot, run_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cain: harness técnico e piloto de instrumento")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--mode", choices=("smoke", "pilot", "formal"), default="smoke")
    parser.add_argument("--provider", choices=("fake", "ollama"), default="fake")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-context-chars", type=int, default=2048,
                        help="Smoke only: characters, never tokens")
    parser.add_argument("--run-id")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "formal":
        print("Coleta formal BLOQUEADA:\n- " + "\n- ".join(formal_blockers()), file=sys.stderr)
        return 2
    config = EvaluationConfig(mode=args.mode, provider=args.provider, model=args.model,
                              base_url=args.base_url, temperature=args.temperature, seed=args.seed,
                              max_context_chars=args.max_context_chars, run_id=args.run_id)
    try:
        runner = run_smoke if args.mode == "smoke" else run_construct_pilot
        result = runner(args.output, config, data_root=args.data_root)
    except Exception as error:
        print(f"Execução não concluída: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(f"Artefatos: {result.resolve()}\nExecução preparatória; não é resultado científico.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

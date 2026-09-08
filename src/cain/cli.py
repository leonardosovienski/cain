"""Interface local, sem execução de código gerado."""

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from cain.llm import FakeLLM, OllamaLLM
from cain.runtime import build_cain


def make_llm(provider: str, model: str, base_url: str, temperature=0.0, seed=42):
    if provider == "fake":
        return FakeLLM()
    if provider != "ollama":
        raise ValueError("Provedor inválido. Escolha fake ou ollama.")
    return OllamaLLM(model=model, base_url=base_url, temperature=temperature, seed=seed)


def main(argv=None) -> int:
    # JSON capturado por pipe também deve preservar português no Windows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Cain: esqueleto de pesquisa")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Processa um pedido e persiste estado/log em SQLite")
    run.add_argument("payload")
    run.add_argument("--intent", choices=["busca", "codigo", "resumo"])
    run.add_argument("--user", default="demo")
    run.add_argument("--session", default="sessao-1")
    run.add_argument("--run-id")
    run.add_argument("--db", type=Path, default=Path("data/cain.db"))
    run.add_argument("--provider", choices=["fake", "ollama"], default="fake")
    run.add_argument("--model", default="qwen2.5:3b")
    run.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if not args.payload.strip():
        parser.error("O pedido não pode ser vazio.")
    runtime = None
    try:
        llm = make_llm(args.provider, args.model, args.ollama_url, args.temperature, args.seed)
        runtime = build_cain(args.db, llm)
        result = runtime.run(
            user_id=args.user, session_id=args.session, payload=args.payload,
            intent=args.intent, run_id=args.run_id,
        )
        print(json.dumps({"provider": args.provider, **asdict(result)}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f"Cain: {exc}", file=sys.stderr)
        return 1
    finally:
        if runtime is not None:
            runtime.close()

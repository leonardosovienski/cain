"""User-facing CLI, interactive chat and explicit profile controls."""

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from cain.llm import FakeLLM, OllamaLLM
from cain.runtime import build_cain
from cain.orchestrator.routing import RuleRouter
from cain.settings import load_settings


def make_llm(provider: str, model: str, base_url: str, temperature=0.0, seed=42, **options):
    if provider == "fake":
        return FakeLLM()
    if provider != "ollama":
        raise ValueError("Provedor inválido. Escolha fake ou ollama.")
    return OllamaLLM(model=model, base_url=base_url, temperature=temperature, seed=seed, **options)


def configured_llm(settings):
    return make_llm(settings.provider, settings.model, settings.base_url,
                    settings.temperature, settings.seed, timeout=settings.timeout,
                    num_ctx=settings.num_ctx, num_predict=settings.num_predict,
                    max_input_bytes=settings.max_input_bytes)


def _write(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _common(parser):
    parser.add_argument("--config", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--user", default="leo")


def _generation(parser):
    _common(parser)
    parser.add_argument("--provider", choices=["fake", "ollama"])
    parser.add_argument("--model")
    parser.add_argument("--ollama-url")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--source", type=Path, action="append")
    parser.add_argument("--no-web", action="store_true")
    parser.add_argument("--session", default=None)


def _settings(args):
    settings = load_settings(args.config)
    for option, field in (("db", "db_path"), ("provider", "provider"), ("model", "model"),
                          ("ollama_url", "base_url"), ("temperature", "temperature"),
                          ("seed", "seed"), ("source", "source_paths")):
        value = getattr(args, option, None)
        if value is not None:
            setattr(settings, field, value)
    if getattr(args, "no_web", False):
        settings.allow_public_urls = False
    return settings


def _chat(runtime, user_id, session_id):
    print("Cain pronto. /perfil mostra preferências; /esquecer CHAVE remove uma; /sair encerra.")
    print("Chaves: format, verbosity, language. As preferências sobrevivem ao encerramento.")
    while True:
        try:
            payload = input("\nVocê > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSessão encerrada.")
            return 0
        if not payload:
            continue
        if payload == "/sair":
            return 0
        if payload == "/perfil":
            _write(runtime.identity.inspect(user_id))
            continue
        if payload.startswith("/esquecer "):
            try:
                runtime.identity.forget_preference(user_id, payload.split(maxsplit=1)[1])
                print("Preferência atual removida. O histórico de auditoria permanece armazenado.")
            except ValueError as exc:
                print(f"Cain > {exc}")
            continue
        try:
            result = runtime.run(user_id, session_id, payload)
            print(f"\nCain [{result.selected_agent}] > {result.response}")
        except (ValueError, RuntimeError, OSError) as exc:
            print(f"Cain > {exc}")


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Cain — identidade persistente e agentes locais")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Processa um pedido")
    run.add_argument("payload")
    run.add_argument("--intent", choices=["busca", "codigo", "resumo"])
    run.add_argument("--run-id")
    _generation(run)
    chat = sub.add_parser("chat", help="Conversa interativa com estado persistente")
    _generation(chat)
    profile = sub.add_parser("profile", help="Inspeciona ou remove preferências explícitas")
    _common(profile)
    removal = profile.add_mutually_exclusive_group()
    removal.add_argument("--forget", choices=["format", "verbosity", "language"])
    removal.add_argument("--clear", action="store_true")
    doctor = sub.add_parser("doctor", help="Verifica configuração e disponibilidade do modelo")
    doctor.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    if args.command == "run" and not args.payload.strip():
        parser.error("O pedido não pode ser vazio.")
    runtime = None
    try:
        settings = _settings(args)
        if args.command == "doctor":
            with urlopen(settings.base_url.rstrip("/") + "/api/tags", timeout=5) as response:
                tags = json.load(response)
            available = [m["name"] for m in tags.get("models", [])]
            ready = settings.model in available
            _write({"provider": settings.provider, "model": settings.model,
                    "model_available": ready, "available_models": available,
                    "database": str(settings.db_path), "sources": list(map(str, settings.source_paths))})
            return 0 if ready else 1
        llm = FakeLLM() if args.command == "profile" else configured_llm(settings)
        runtime = build_cain(settings.db_path, llm) if args.command == "profile" else build_cain(
            settings.db_path, llm, source_paths=settings.source_paths,
            allow_public_urls=settings.allow_public_urls,
            router=RuleRouter(llm if settings.llm_routing and settings.provider == "ollama" else None),
        )
        if args.command == "profile":
            if args.forget:
                runtime.identity.forget_preference(args.user, args.forget)
            elif args.clear:
                runtime.identity.clear_preferences(args.user)
            _write(runtime.identity.inspect(args.user))
            return 0
        session = args.session or f"session-{uuid4().hex[:12]}"
        if args.command == "chat":
            print(f"Modelo: {settings.model} ({settings.provider}); sessão: {session}")
            return _chat(runtime, args.user, session)
        result = runtime.run(args.user, session, args.payload, args.intent, args.run_id)
        _write({"provider": settings.provider, **asdict(result),
                "profile": runtime.identity.inspect(args.user),
                "generation": getattr(llm, "last_metadata", {})})
        return 0
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f"Cain: {exc}", file=sys.stderr)
        return 1
    finally:
        if runtime is not None:
            runtime.close()

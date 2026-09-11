"""User-facing CLI, interactive chat and explicit profile controls."""

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.request import urlopen
from cain.providers import configured_llm, configured_embedding, make_llm  # noqa: F401
from uuid import uuid4

from cain.llm import FakeLLM
from cain.runtime import build_cain, build_retriever, build_profile
from cain.orchestrator.routing import RuleRouter
from cain.settings import load_settings


def _write(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _common(parser):
    parser.add_argument("--config", type=Path)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--user", default="leo")
    parser.add_argument("--project", dest="project_id")


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
    parser.add_argument("--preference-scope", choices=["user", "project", "session", "turn"])


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
    return settings.validate()


def _chat(runtime, user_id, session_id, project_id=None, preference_scope=None):
    print("Cain pronto. /perfil mostra preferências; /esquecer CHAVE remove uma; /sair encerra.")
    print("Chaves: format, verbosity, language. /esquecer atua no padrão geral; escopos temporários valem só em seu contexto.")
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
            _write(runtime.identity.inspect(user_id, project_id=project_id, session_id=session_id))
            continue
        if payload.startswith("/esquecer "):
            try:
                runtime.identity.forget_preference(user_id, payload.split(maxsplit=1)[1])
                print("Preferência atual removida. O histórico de auditoria permanece armazenado.")
            except ValueError as exc:
                print(f"Cain > {exc}")
            continue
        try:
            result = runtime.run(user_id, session_id, payload, project_id=project_id,
                                 preference_scope=preference_scope)
            print(f"\nCain [{result.selected_agent}] > {result.response}")
        except (ValueError, RuntimeError, OSError) as exc:
            print(f"Cain > {exc}")


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Cain — identidade persistente e agentes locais")
    sub = parser.add_subparsers(dest="command", required=True)
    from cain.research.cli import register
    register(sub)
    from cain.archive import register as register_archive
    register_archive(sub)
    run = sub.add_parser("run", help="Processa um pedido")
    run.add_argument("payload")
    run.add_argument("--intent", choices=["busca", "codigo", "resumo"])
    run.add_argument("--run-id")
    _generation(run)
    chat = sub.add_parser("chat", help="Conversa interativa com estado persistente")
    _generation(chat)
    profile = sub.add_parser("profile", help="Inspeciona ou remove preferências explícitas")
    _common(profile)
    profile.add_argument("--session")
    profile.add_argument("--scope", choices=["user", "project", "session"], default="user")
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
        if args.command == "archive":
            from cain.archive import execute as execute_archive
            _write(execute_archive(args))
            return 0
        if args.command == "research":
            from cain.research.cli import execute
            result = execute(args)
            _write(result)
            return 1 if isinstance(result, dict) and result.get("status") == "generation_failed" else 0
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
        if args.command != "profile" and args.project_id:
            from cain.workspace import WorkspaceStore
            WorkspaceStore(settings.db_path).require_project(args.user, args.project_id)

        def retrieval_factory():
            corpus, paths = None, settings.source_paths
            if args.project_id:
                from cain.workspace import WorkspaceStore
                workspace = WorkspaceStore(settings.db_path)
                corpus, paths = workspace.document_corpus(args.user, args.project_id), []
            return build_retriever(corpus=corpus, paths=paths,
                search_mode=settings.search_mode if settings.provider != "fake" else "lexical",
                embedding=configured_embedding(settings),
                cache_path=settings.db_path.with_suffix(".embeddings.sqlite3"),
                allow_public_urls=settings.allow_public_urls)

        runtime = build_profile(settings.db_path) if args.command == "profile" else build_cain(
            settings.db_path, llm,
            router=RuleRouter(llm if settings.llm_routing and settings.provider == "ollama" else None),
            retrieval_factory=retrieval_factory,
        )
        if args.command == "profile":
            if args.forget:
                runtime.identity.forget_preference(args.user, args.forget, scope=args.scope,
                                                   project_id=args.project_id, session_id=args.session)
            elif args.clear:
                runtime.identity.clear_preferences(args.user, scope=args.scope,
                                                    project_id=args.project_id, session_id=args.session)
            _write(runtime.identity.inspect(args.user, project_id=args.project_id, session_id=args.session))
            return 0
        session = args.session or f"session-{uuid4().hex[:12]}"
        if args.command == "chat":
            print(f"Modelo: {settings.model} ({settings.provider}); sessão: {session}")
            return _chat(runtime, args.user, session, args.project_id, args.preference_scope)
        result = runtime.run(args.user, session, args.payload, args.intent, args.run_id,
                             project_id=args.project_id, preference_scope=args.preference_scope)
        _write({"provider": settings.provider, **asdict(result),
                "profile": runtime.identity.inspect(args.user, project_id=args.project_id, session_id=session),
                "generation": getattr(llm, "last_metadata", {})})
        return 0
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f"Cain: {exc}", file=sys.stderr)
        return 1
    finally:
        if runtime is not None:
            runtime.close()

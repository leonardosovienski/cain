"""Local API and working interface; connections belong to individual operations."""

from dataclasses import asdict
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cain.cli import configured_llm, configured_embedding
from cain import __version__
from cain.llm import FakeLLM
from cain.runtime import build_cain, build_retriever
from cain.orchestrator.routing import RuleRouter
from cain.settings import load_settings
from cain.workspace import WorkspaceStore

Scope = Literal["user", "project", "session", "turn"]
PreferenceKey = Literal["format", "verbosity", "language"]


def _normalized_origin(value: str) -> tuple[str, str, int] | None:
    """Parse an HTTP Origin, rejecting opaque origins and URL-only components."""
    if (not value or "?" in value or "#" in value
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)):
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.path or parts.query or parts.fragment
                or parts.netloc.endswith(":")):
            return None
        port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
        return parts.scheme, parts.hostname.lower(), port
    except ValueError:
        # Invalid bracketed hosts, Unicode host syntax, and invalid ports.
        return None


class RunRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    payload: str = Field(min_length=1, max_length=100_000)
    intent: Literal["busca", "search", "codigo", "código", "code", "resumo", "summary"] | None = None
    run_id: str | None = None
    project_id: str | None = Field(default=None, max_length=200)
    preference_scope: Scope | None = None

    @field_validator("user_id", "session_id", "payload")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Campo não pode ser vazio")
        return value


class PreferenceRequest(BaseModel):
    value: str
    scope: Scope = "user"
    project_id: str | None = None
    session_id: str | None = None
    turn_id: str | None = None
    expires_at: str | None = None


class ProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SessionRequest(BaseModel):
    project_id: str | None = None


class DocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=262144)


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    reason: Literal["useful", "incorrect", "format", "source", "memory", "long"]
    note: str = Field(default="", max_length=2000)


def create_app(db_path: str | Path | None = None, llm=None, config_path: Path | None = None,
               embedding=None, research_policy: Path | None = None,
               research_db: Path | None = None) -> FastAPI:
    app = FastAPI(title="Cain — memória e projetos", version=__version__, docs_url=None, redoc_url=None)
    settings = load_settings(config_path)
    storage_path = Path(db_path if db_path is not None else settings.db_path)
    workspace = WorkspaceStore(storage_path)
    generation_lock = Lock()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origins = request.headers.getlist("origin")
        if origins:
            supplied = _normalized_origin(origins[0]) if len(origins) == 1 else None
            actual = _normalized_origin(
                f"{request.scope.get('scheme', '')}://{request.headers.get('host', '')}"
            )
            if supplied is None or supplied != actual:
                return JSONResponse({"detail": "Origem não autorizada"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.exception_handler(ValueError)
    async def validation_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, exc):
        return JSONResponse({"detail": "Falha no armazenamento local; confira os registros do serviço."},
                            status_code=503)

    def validate_context(user_id, project_id=None, session_id=None, *, create_session=False):
        if not user_id.strip() or len(user_id) > 200:
            raise ValueError("Usuário inválido")
        workspace.require_project(user_id, project_id)
        if session_id is not None:
            if create_session:
                workspace.ensure_session(user_id, session_id, project_id)
            else:
                workspace.require_session(user_id, session_id, project_id)

    def runtime_for_request(project_id, user_id):
        provider = llm if llm is not None else configured_llm(settings)
        # Explicit injected providers are test configurations unless an embedding is injected too.
        mode = settings.search_mode if llm is None or embedding is not None else "lexical"

        def retrieval_factory():
            encoder = embedding if embedding is not None else configured_embedding(settings) if mode == "hybrid" else None
            corpus = workspace.document_corpus(user_id, project_id) if project_id else None
            paths = [] if project_id else settings.source_paths
            return build_retriever(corpus=corpus, paths=paths, search_mode=mode, embedding=encoder,
                                   cache_path=storage_path.with_suffix(".embeddings.sqlite3"),
                                   allow_public_urls=settings.allow_public_urls)

        runtime = build_cain(storage_path, provider,
                             allow_public_urls=settings.allow_public_urls,
                             router=RuleRouter(provider if settings.llm_routing else None),
                             retrieval_factory=retrieval_factory)
        return runtime, provider

    def runtime_for_profile():
        return build_cain(storage_path, FakeLLM())

    from cain.research.api import mount
    mount(app, storage_path, validate_context,
          lambda: llm if llm is not None else configured_llm(settings), generation_lock,
          policy_path=research_policy, research_path=research_db)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "cain-local-api", "api_contract": 1,
                "provider_availability": "not_probed", "inference": "not_exercised",
                "version": __version__, "model": settings.model,
                "provider": type(llm).__name__ if llm is not None else settings.provider,
                "search_mode": settings.search_mode, "research_status": "l0-local",
                "identity_status": "provisional"}

    @app.post("/run")
    def run(request: RunRequest):
        runtime = None
        try:
            validate_context(request.user_id, request.project_id, request.session_id, create_session=True)
            with generation_lock:
                runtime, provider = runtime_for_request(request.project_id, request.user_id)
                result = runtime.run(**request.model_dump())
                record = next(r for r in runtime.decision_log.export(result.run_id)
                              if r.decision_id == result.decision_id)
                output = {**asdict(result), "profile": runtime.identity.inspect(
                    request.user_id, project_id=request.project_id, session_id=request.session_id),
                    "sources": record.metadata.get("retrieval_sources", []),
                    "preferences_used": record.metadata.get("preferences_used", {}),
                    "route_reason": record.reason, "generation": getattr(provider, "last_metadata", {}),
                    "project_id": request.project_id, "session_id": request.session_id}
                output["turn_id"] = workspace.record_turn(request.user_id, request.session_id,
                                                          request.payload, output)
                return output
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (RuntimeError, OSError) as exc:
            status = 422 if isinstance(exc.__cause__, ValueError) else 503
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        finally:
            if runtime is not None:
                runtime.close()

    @app.get("/profile/{user_id}")
    def profile(user_id: str, project_id: str | None = None, session_id: str | None = None,
                turn_id: str | None = None):
        validate_context(user_id, project_id, session_id)
        with runtime_for_profile() as runtime:
            return runtime.identity.inspect(user_id, project_id=project_id, session_id=session_id, turn_id=turn_id)

    @app.put("/profile/{user_id}/preferences/{key}")
    def set_preference(user_id: str, key: PreferenceKey, body: PreferenceRequest):
        validate_context(user_id, body.project_id, body.session_id)
        with runtime_for_profile() as runtime:
            runtime.identity.set_preference(user_id, key, **body.model_dump())
            return {"profile": runtime.identity.inspect(user_id, project_id=body.project_id,
                                                         session_id=body.session_id, turn_id=body.turn_id),
                    "audit_history_retained": True}

    @app.delete("/profile/{user_id}/preferences/{key}")
    def forget(user_id: str, key: PreferenceKey, scope: Scope = "user",
               project_id: str | None = None, session_id: str | None = None, turn_id: str | None = None):
        validate_context(user_id, project_id, session_id)
        with runtime_for_profile() as runtime:
            runtime.identity.forget_preference(user_id, key, scope=scope, project_id=project_id,
                                               session_id=session_id, turn_id=turn_id)
            return {"profile": runtime.identity.inspect(user_id, project_id=project_id,
                                                         session_id=session_id, turn_id=turn_id),
                    "audit_history_retained": True}

    @app.delete("/profile/{user_id}/preferences")
    def clear(user_id: str, scope: Scope = "user", project_id: str | None = None,
              session_id: str | None = None, turn_id: str | None = None):
        validate_context(user_id, project_id, session_id)
        with runtime_for_profile() as runtime:
            runtime.identity.clear_preferences(user_id, scope=scope, project_id=project_id,
                                                session_id=session_id, turn_id=turn_id)
            return {"profile": runtime.identity.inspect(user_id, project_id=project_id,
                                                         session_id=session_id, turn_id=turn_id),
                    "audit_history_retained": True}

    @app.get("/projects/{user_id}")
    def projects(user_id: str):
        return workspace.projects(user_id)

    @app.post("/projects/{user_id}")
    def create_project(user_id: str, body: ProjectRequest):
        validate_context(user_id)
        return workspace.create_project(user_id, body.name)

    @app.get("/projects/{user_id}/{project_id}/documents")
    def documents(user_id: str, project_id: str):
        return workspace.documents(user_id, project_id)

    @app.post("/projects/{user_id}/{project_id}/documents")
    def add_document(user_id: str, project_id: str, body: DocumentRequest):
        return workspace.add_document(user_id, project_id, body.title, body.content)

    @app.get("/sessions/{user_id}")
    def sessions(user_id: str, project_id: str | None = None):
        return workspace.sessions(user_id, project_id)

    @app.post("/sessions/{user_id}")
    def new_session(user_id: str, body: SessionRequest):
        validate_context(user_id, body.project_id)
        return workspace.ensure_session(user_id, str(uuid4()), body.project_id)

    @app.get("/sessions/{user_id}/{session_id}")
    def conversation(user_id: str, session_id: str, project_id: str | None = None):
        return workspace.turns(user_id, session_id, project_id)

    @app.post("/feedback/{turn_id}")
    def feedback(turn_id: str, body: FeedbackRequest):
        return workspace.feedback(body.user_id, turn_id, body.reason, body.note)

    web_root = Path(__file__).with_name("web")
    if web_root.is_dir():
        app.mount("/assets", StaticFiles(directory=web_root), name="assets")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(web_root / "index.html")
    return app

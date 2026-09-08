"""Local API; each request owns its SQLite connections."""

from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from cain.cli import configured_llm
from cain.llm import FakeLLM
from cain.runtime import build_cain
from cain.orchestrator.routing import RuleRouter
from cain.settings import load_settings


class RunRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    payload: str = Field(min_length=1, max_length=100_000)
    intent: Literal["busca", "search", "codigo", "código", "code", "resumo", "summary"] | None = None
    run_id: str | None = None

    @field_validator("user_id", "session_id", "payload")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Campo não pode ser vazio")
        return value


def create_app(db_path: str | Path | None = None, llm=None, config_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Cain — identidade persistente", version="0.2.0")
    settings = load_settings(config_path)
    storage_path = db_path if db_path is not None else settings.db_path

    def runtime_for_request():
        provider = llm if llm is not None else configured_llm(settings)
        return build_cain(storage_path, provider,
                          source_paths=settings.source_paths,
                          allow_public_urls=settings.allow_public_urls,
                          router=RuleRouter(provider if settings.llm_routing else None))

    def runtime_for_profile():
        return build_cain(storage_path, FakeLLM())

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.2.0", "model": settings.model,
                "provider": type(llm).__name__ if llm is not None else settings.provider,
                "research_status": "provisional"}

    @app.post("/run")
    def run(request: RunRequest):
        runtime = None
        try:
            runtime = runtime_for_request()
            result = runtime.run(**request.model_dump())
            return {**asdict(result), "profile": runtime.identity.inspect(request.user_id)}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (RuntimeError, OSError) as exc:
            if isinstance(exc.__cause__, ValueError):
                raise HTTPException(status_code=422, detail=str(exc.__cause__)) from exc
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            if runtime is not None:
                runtime.close()

    @app.get("/profile/{user_id}")
    def profile(user_id: str):
        with runtime_for_profile() as runtime:
            return runtime.identity.inspect(user_id)

    @app.delete("/profile/{user_id}/preferences/{key}")
    def forget(user_id: str, key: Literal["format", "verbosity", "language"]):
        with runtime_for_profile() as runtime:
            runtime.identity.forget_preference(user_id, key)
            return {"profile": runtime.identity.inspect(user_id), "audit_history_retained": True}

    @app.delete("/profile/{user_id}/preferences")
    def clear(user_id: str):
        with runtime_for_profile() as runtime:
            runtime.identity.clear_preferences(user_id)
            return {"profile": runtime.identity.inspect(user_id), "audit_history_retained": True}

    return app

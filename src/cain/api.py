"""API opcional para demonstração local; uma conexão SQLite por requisição."""

import os
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from cain.cli import make_llm
from cain.runtime import build_cain


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


def create_app(db_path: str | Path | None = None, llm=None) -> FastAPI:
    app = FastAPI(title="Cain — demonstração local", version="0.1.0")
    storage_path = db_path if db_path is not None else os.getenv("CAIN_DB", "data/cain.db")

    @app.get("/health")
    def health():
        return {"status": "ok", "research_status": "provisional"}

    @app.post("/run")
    def run(request: RunRequest):
        provider = llm if llm is not None else make_llm(
            os.getenv("CAIN_PROVIDER", "fake"), os.getenv("CAIN_MODEL", "qwen2.5:3b"),
            os.getenv("CAIN_OLLAMA_URL", "http://127.0.0.1:11434"),
        )
        runtime = build_cain(storage_path, provider)
        try:
            return asdict(runtime.run(**request.model_dump()))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (RuntimeError, OSError) as exc:
            raise HTTPException(status_code=503, detail="Falha no processamento; consulte o log local") from exc
        finally:
            runtime.close()

    return app

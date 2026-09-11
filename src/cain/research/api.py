"""Routes mounted on the existing loopback Cain application."""

import os
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from cain.research import ResearchService


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(default="leo", min_length=1, max_length=200)
    project_id: str | None = Field(default=None, max_length=200)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    collection: str = Field(default="crypto", min_length=1, max_length=200)
    domain: str | None = Field(default=None, max_length=200)
    source_id: str | None = Field(default=None, max_length=200)
    kind: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=500)
    revision: str | None = Field(default=None, max_length=200)
    reason: str | None = Field(default=None, max_length=500)
    text: str | None = Field(default=None, max_length=500)
    completeness: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=100_000)
    question: str | None = Field(default=None, max_length=1000)


class InspectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(default="leo", min_length=1, max_length=200)
    project_id: str | None = Field(default=None, max_length=200)
    collection: str = Field(default="crypto", min_length=1, max_length=200)
    source_id: str | None = Field(default=None, min_length=1, max_length=500)
    domain: str | None = Field(default=None, min_length=1, max_length=500)
    before: str | None = Field(default=None, min_length=1, max_length=500)
    after: str | None = Field(default=None, min_length=1, max_length=500)


def mount(
    app,
    storage_path,
    validate_context,
    provider_factory,
    generation_lock,
    policy_path=None,
    research_path=None,
):
    policy_path = policy_path or os.getenv("CAIN_RESEARCH_POLICY")
    research_path = (
        research_path
        or os.getenv("CAIN_RESEARCH_DB")
        or Path(storage_path).with_name("research.db")
    )

    def service():
        if not policy_path:
            raise HTTPException(503, "Pesquisa desativada: configure CAIN_RESEARCH_POLICY")
        return ResearchService(research_path, policy_path)

    def prepare(request):
        validate_context(request.user_id, request.project_id, request.session_id)
        store = service()
        scope = store.scope(request.user_id, request.project_id, request.collection)
        filters = request.model_dump(exclude={"user_id", "project_id", "collection", "question"})
        return store, scope, filters

    from cain.research.agent_api import mount as mount_agent_tools
    mount_agent_tools(app, service, validate_context, provider_factory, generation_lock)

    @app.post("/research/query")
    def query(request: ResearchRequest):
        store, scope, filters = prepare(request)
        return store.query(scope, **filters)

    @app.post("/research/inspect")
    def inspection(request: InspectionRequest):
        from cain.research.inspection import inspect

        validate_context(request.user_id, request.project_id)
        store = service()
        return inspect(store, store.scope(request.user_id, request.project_id, request.collection),
                       source_id=request.source_id, domain=request.domain,
                       before=request.before, after=request.after)

    @app.post("/research/explain")
    def explain_request(request: ResearchRequest):
        from cain.research.historian import explain

        store, scope, filters = prepare(request)
        with generation_lock:
            return explain(store, scope, request.question, provider_factory(), **filters)

    @app.get("/research/evidence/{reference}")
    def evidence(
        reference: str,
        user_id: str = "leo",
        project_id: str | None = None,
        collection: str = "crypto",
    ):
        validate_context(user_id, project_id)
        store = service()
        return store.evidence(store.scope(user_id, project_id, collection), reference)

    @app.get("/research/capabilities")
    def capabilities():
        return {
            "enabled": bool(policy_path),
            "mode": "L0",
            "deterministic": bool(policy_path),
            "deterministic_availability": "not_probed",
            "provider": "not_probed",
            "inference": "not_exercised",
            "embedding_required": False,
            "scope_selection": "local organization, not remote authentication",
        }

    @app.post("/research/readiness")
    def readiness(request: ResearchRequest):
        store, scope, filters = prepare(request)
        result = store.query(scope, **{**filters, "limit": 1, "offset": 0})
        return {
            "storage_and_query": "verified_for_requested_scope",
            "total_record_revisions": result["total_record_revisions"],
            "coverage": result["coverage"],
            "provider": "not_probed",
            "inference": "not_exercised",
            "embedding_required": False,
        }

    @app.get("/research/history")
    def history(
        user_id: str = "leo",
        project_id: str | None = None,
        collection: str = "crypto",
        session_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        validate_context(user_id, project_id, session_id)
        store = service()
        return store.history(
            store.scope(user_id, project_id, collection), session_id, limit, offset
        )

    @app.get("/research/history/{entry_id}")
    def recall(
        entry_id: str,
        user_id: str = "leo",
        project_id: str | None = None,
        collection: str = "crypto",
        session_id: str | None = None,
    ):
        validate_context(user_id, project_id, session_id)
        store = service()
        return store.recall(store.scope(user_id, project_id, collection), entry_id, session_id)

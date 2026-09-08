"""Auditable sequential eight-step orchestration, without retry/fallback (ADR-0011)."""

from hashlib import sha256
from uuid import uuid4

from cain.agents import AgentRegistry
from cain.common import CainRunError, DecisionRecord, Message, RunResult, Signal
from cain.identity import IdentityService
from cain.persistence import DecisionLog
from cain.orchestrator.routing import (
    ClarificationRequired as ClarificationRequired, Route as Route, Router,
    RoutingError as RoutingError, RuleRouter as RuleRouter,
)


class SessionManager:
    """Live session counters; user/session linkage is persisted in logs and signals."""

    def __init__(self):
        self._counts: dict[tuple[str, str], int] = {}

    def start_turn(self, user_id: str, session_id: str) -> int:
        key = (user_id, session_id)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]


class Mediator:
    """Single-agent consolidation for the restricted prototype."""

    def consolidate(self, response: str) -> str:
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Agent returned an empty or non-textual response")
        return response.strip()


class Cain:
    def __init__(
        self, identity: IdentityService, registry: AgentRegistry, decision_log: DecisionLog,
        router: Router | None = None,
    ):
        self.identity = identity
        self.store = identity.store
        self.memory = identity.memory
        self.registry = registry
        self.decision_log = decision_log
        self.router = router if router is not None else RuleRouter()
        self.sessions = SessionManager()
        self.mediator = Mediator()

    def run(
        self, user_id: str, session_id: str, payload: str,
        intent: str | None = None, run_id: str | None = None,
    ) -> RunResult:
        if any(not isinstance(value, str) or not value.strip() for value in (user_id, session_id, payload)):
            raise ValueError("user_id, session_id and payload must be non-empty strings")
        run_id = run_id or str(uuid4())
        decision_id = str(uuid4())
        steps: list[str] = []
        route = Route("", intent or "", "routing_not_reached")
        self.registry.freeze()
        try:
            self.sessions.start_turn(user_id, session_id)
            steps.append("1:session_registered")
            observed = self.identity.observe(user_id, payload, {
                "session_id": session_id, "run_id": run_id, "decision_id": decision_id,
            })
            context = self.identity.context_for(user_id, payload, exclude_decision_id=decision_id)
            steps.append("2:user_observed_identity_loaded")
            route = self.router.route(payload, intent, self.registry)
            steps.append("3:agent_selected")
            message = Message(route.intent, context, payload, {
                "user_id": user_id, "session_id": session_id, "run_id": run_id,
                "decision_id": decision_id,
                "route_reason": route.reason,
                "preferences": dict(observed.user_model.preferences),
            })
            agent = self.registry.get(route.selected_agent)
            steps.append("4:delegated")
            response = agent.handle(message)
            steps.append("5:agent_processed")
            response = self.mediator.consolidate(response)
            steps.append("6:mediated_and_logged")
            response_hash = sha256(response.encode("utf-8")).hexdigest()
            self.decision_log.append(DecisionRecord(
                decision_id, run_id, user_id, session_id, route.selected_agent,
                route.intent, route.reason, "mediated", tuple(steps), response_hash=response_hash,
                metadata={
                    "adaptation": "explicit_preferences; provisional_ADR-0007",
                    "identity_revision": observed.revision,
                    "retrieval_sources": message.metadata.get("retrieval_sources", []),
                    "retrieval_budget": message.metadata.get("retrieval_budget", {}),
                },
            ))
            self.identity.update(user_id, Signal(
                text=f"Usuário: {payload}\nCain: {response}",
                metadata={
                    "session_id": session_id, "run_id": run_id, "decision_id": decision_id,
                    "user_input": payload, "preference_observed": True,
                },
            ))
            steps.append("7:interaction_persisted")
            steps.append("8:response_ready")
            # Completion is a separate immutable event; step 6's decision is never edited.
            self.decision_log.append(DecisionRecord(
                str(uuid4()), run_id, user_id, session_id, route.selected_agent,
                route.intent, route.reason, "completed", tuple(steps), response_hash=response_hash,
                metadata={"parent_decision_id": decision_id},
            ))
            return RunResult(response, route.selected_agent, decision_id, list(steps), run_id)
        except Exception as exc:
            failed_id = str(uuid4())
            try:
                self.decision_log.append(DecisionRecord(
                    failed_id, run_id, user_id, session_id, route.selected_agent,
                    route.intent, route.reason, "failed", tuple(steps),
                    error=f"{type(exc).__name__}: {exc}",
                    metadata={"parent_decision_id": decision_id, "retry_count": 0},
                ))
            except Exception as audit_error:
                raise CainRunError(
                    f"Pedido falhou ({exc}); também falhou o registro de auditoria ({audit_error}).",
                    failed_id,
                ) from exc
            raise CainRunError(f"Pedido falhou sem retry: {exc}", failed_id) from exc

    def close(self) -> None:
        # Lifecycle only; orchestration depends exclusively on the three ports.
        for component in (self.store, self.decision_log):
            close = getattr(component, "close", None)
            if close is not None:
                close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

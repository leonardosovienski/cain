"""Auditable sequential eight-step orchestration, without retry/fallback (ADR-0011)."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

from cain.agents import AgentRegistry
from cain.common import CainRunError, DecisionRecord, Message, RunResult, Signal
from cain.common.text import tokens
from cain.identity import IdentityService
from cain.persistence import DecisionLog


@dataclass(frozen=True)
class Route:
    selected_agent: str
    intent: str
    reason: str


class RuleRouter:
    """STUB — ADR-0008: deterministic rules, no learned or LLM routing yet."""

    RULES = (
        ("resumo", {"resumo", "resuma", "resumir", "sintetize", "sumarize", "summary"}),
        ("codigo", {"codigo", "python", "programa", "funcao", "bug", "debug", "code"}),
        ("busca", {"buscar", "busca", "busque", "pesquisa", "pesquisar", "pesquise", "encontrar", "search"}),
    )

    def route(self, payload: str, intent: str | None, registry: AgentRegistry) -> Route:
        if intent is not None:
            for capabilities in registry.describe():
                if intent in capabilities.intents:
                    return Route(capabilities.name, intent, f"explicit_intent:{intent}; STUB ADR-0008")
            raise ValueError(f"Unknown intent: {intent}")
        terms = tokens(payload)
        for inferred_intent, keywords in self.RULES:
            matches = sorted(terms.intersection(keywords))
            if matches:
                for capabilities in registry.describe():
                    if inferred_intent in capabilities.intents:
                        return Route(capabilities.name, inferred_intent,
                                     f"keyword_rule:{inferred_intent}:{','.join(matches)}; STUB ADR-0008")
        for capabilities in registry.describe():
            if "resumo" in capabilities.intents:
                return Route(capabilities.name, "resumo", "default_rule:resumo; STUB ADR-0008")
        raise ValueError("No matching routing rule and no resumo agent")


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
    def __init__(self, identity: IdentityService, registry: AgentRegistry, decision_log: DecisionLog):
        self.identity = identity
        self.store = identity.store
        self.memory = identity.memory
        self.registry = registry
        self.decision_log = decision_log
        self.router = RuleRouter()
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
            context = self.identity.context_for(user_id, payload)
            steps.append("2:identity_loaded")
            route = self.router.route(payload, intent, self.registry)
            steps.append("3:agent_selected")
            message = Message(route.intent, context, payload, {
                "user_id": user_id, "session_id": session_id, "run_id": run_id,
                "decision_id": decision_id,
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
                metadata={"adaptation": "no-op; STUB ADR-0007", "index": "lexical, non-semantic"},
            ))
            self.identity.update(user_id, Signal(
                text=f"Usuário: {payload}\nCain: {response}",
                metadata={"session_id": session_id, "run_id": run_id, "decision_id": decision_id},
            ))
            steps.append("7:signal_persisted_adaptation_noop")
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

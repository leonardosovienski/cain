"""Answer narrow questions about known profile fields from authoritative state."""

import re

from cain.common import IdentityState


def profile_answer(payload: str, state: IdentityState) -> str | None:
    from cain.orchestrator.routing import instruction_head

    head = instruction_head(payload)
    if re.search(r"\b(documento|artigo|fonte|manual|texto)\b", head):
        return None
    if not re.match(r"^(qual|quais|o que)\b", head):
        return None
    if not re.search(r"preferenc|formato|idioma|extensao|verbosidade", head):
        return None
    if re.search(r"posso|suporta|permite|aceita|disponive|possive|alterar|mudar", head):
        return (
            "Você pode ajustar três preferências:\n"
            "• Formato: tópicos, parágrafo ou passos.\n"
            "• Extensão: curta ou detalhada.\n"
            "• Idioma: português ou inglês.\n"
            "Escolha se vale para uma resposta, conversa, projeto ou como padrão geral."
        )
    if re.search(r"\b(minhas?|meus?|eu|atual|atuais)\b", head):
        from cain.agents import SummaryAgent
        if not state.user_model.preferences:
            return "Não há preferência ativa declarada por você neste contexto."
        return SummaryAgent._confirm_preferences(state.user_model.preferences)
    return None

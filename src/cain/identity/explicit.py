"""Conservative explicit preference rules; no LLM inference or document mining.

This operational policy does not accept ADR-0006/0007 or claim a validated
identity/adaptation model. Unsupported or ambiguous phrasing is left unchanged.
"""

from copy import deepcopy
from dataclasses import dataclass
import re
import unicodedata

from cain.common import IdentityState, Signal


PREFERENCE_VALUES = {
    "format": ("bullets", "paragraph", "steps"),
    "verbosity": ("short", "detailed"),
    "language": ("pt", "en"),
}
PREFERENCE_KEYS = tuple(PREFERENCE_VALUES)

_VALUES = {
    "format": {
        "bullets": r"\b(?:topicos|marcadores|bullets)\b",
        "paragraph": r"\b(?:paragrafos?|texto corrido)\b",
        "steps": r"\b(?:passos|passo a passo|etapas)\b",
    },
    "verbosity": {
        "short": r"\b(?:curt[ao]s?|breves?|concis[ao]s?|sucint[ao]s?)\b",
        "detailed": r"\b(?:detalhad[ao]s?|extens[ao]s?|long[ao]s?|aprofundad[ao]s?)\b",
    },
    "language": {
        "pt": r"\b(?:portugues|pt-br|pt)\b",
        "en": r"\b(?:ingles|english|en)\b",
    },
}
_KEY_WORDS = {
    "format": r"\b(?:formato|formatacao|estrutura)\b",
    "verbosity": r"\b(?:verbosidade|extensao|tamanho|detalhamento)\b",
    "language": r"\b(?:idioma|lingua|linguagem)\b",
}


def _normalize(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text.lower())
                   if not unicodedata.combining(char))


def _unquoted_clauses(text: str) -> list[str]:
    # Refuse likely pasted data blocks. Being conservative is preferable to
    # converting quoted preferences or someone else's wishes into user state.
    text = re.sub(r"```[\s\S]*?(?:```|$)", " ", text)
    text = re.sub(r"`[^`]*(?:`|$)", " ", text)
    for pattern in (r'"[^"]*(?:"|$)', r"'[^']*(?:'|$)", r"“[^”]*(?:”|$)",
                    r"‘[^’]*(?:’|$)", r"«[^»]*(?:»|$)"):
        text = re.sub(pattern, " ", text)
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith(">"):
            continue
        marker = re.search(r"\b(?:texto|documento|citacao|exemplo|transcricao|conteudo|anexo|codigo|seguinte|"
                     r"disse|afirmou|escreveu|declarou|respondeu|comentou|relatou)\s*:",
                     _normalize(line))
        if marker:
            # Keep any direct preference preceding the pasted-data marker on
            # the same line. Normalize before slicing so decomposed accents do
            # not make normalized offsets point into the original codepoints.
            lines.append(_normalize(line)[:marker.start()])
            break
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r",\s*(?=(?:mas\s+)?(?:eu\s+)?(?:n[aã]o\s+)?(?:prefiro|quero|gosto))", ";", text,
                  flags=re.IGNORECASE)
    return [part.strip() for part in re.split(r"[.!?;\n]+", text) if part.strip()]


@dataclass(frozen=True)
class PreferenceChange:
    key: str
    action: str
    value: str | None
    evidence: str


class ExplicitPreferenceAdaptation:
    """Latest directly stated user preference wins; negation never implies its opposite."""

    def extract(self, user_text: str) -> list[PreferenceChange]:
        changes = []
        for original in _unquoted_clauses(user_text):
            clause = _normalize(original)
            clause = re.sub(r"^(?:por favor[, ]+|mas\s+)", "", clause)
            clause = re.sub(r"^(?:(?:agora|daqui em diante|a partir de agora|na verdade)[,:]?\s+|"
                            r"corrigindo\s*:\s*)", "", clause)
            if re.match(r"^(?:esqueca|remova|apague|limpe)\b", clause):
                if "preferencia" not in clause or not re.search(r"\bminhas?\b", clause):
                    continue
                keys = [key for key, pattern in _KEY_WORDS.items() if re.search(pattern, clause)]
                if re.search(r"\b(?:todas|preferencias)\b", clause) and not keys:
                    keys = list(PREFERENCE_KEYS)
                changes.extend(PreferenceChange(key, "remove", None, original[:240]) for key in keys)
                continue
            clause = re.sub(r"^(?:eu\s+)?sou\s+[^,;:.]{1,80}?\s+e\s+", "", clause)
            match = re.match(
                r"^(?:eu\s+)?(?P<negative>nao\s+)?(?:prefiro|quero|gosto de)\s+(?P<value>.+)$",
                clause,
            )
            if match is None:
                match = re.match(
                    r"^minha preferencia(?: de \w+)? (?:e|eh)\s+(?P<value>.+)$", clause
                )
            if match is None:
                continue
            value_text = match.group("value")
            if not re.match(
                r"^(?:(?:as?|os?|uma?)\s+)?(?:respostas?|textos?|explicacoes?|em|"
                r"paragrafos?|topicos|marcadores|passos|passo a passo|etapas|portugues|ingles|"
                r"curt[ao]s?|breves?|concis[ao]s?|detalhad[ao]s?|extens[ao]s?|long[ao]s?)\b",
                value_text,
            ):
                continue
            if re.search(r"\b(?:cliente|colega|professor|ele|ela|terceiro|documento|citacao)\b", value_text):
                continue
            # A clause such as 'prefiro respostas não detalhadas' is ambiguous;
            # do not mistake the negated adjective for a positive preference.
            value_text = re.split(r",|\s+e\s+nao\b", value_text, maxsplit=1)[0]
            if re.search(r"\b(?:nao|talvez|se|hipoteticamente|deixar)\b", value_text):
                continue
            negative = bool(match.groupdict().get("negative"))
            for key, options in _VALUES.items():
                matched = [value for value, pattern in options.items() if re.search(pattern, value_text)]
                if len(matched) == 1:
                    changes.append(PreferenceChange(key, "remove" if negative else "set",
                                                    matched[0], original[:240]))
        return changes

    def apply(self, state: IdentityState, signal: Signal) -> IdentityState:
        # signal.text may contain generated answers, quotes or documents. Only
        # an explicit input field supplied by the orchestrator is a learning source.
        text = signal.metadata.get("user_input")
        if signal.metadata.get("preference_observed") is True or not isinstance(text, str):
            return state
        return self.apply_changes(state, signal, self.extract(text))

    def apply_changes(
        self, state: IdentityState, signal: Signal, changes: list[PreferenceChange],
    ) -> IdentityState:
        result = deepcopy(state)
        accepted = []
        for change in changes:
            if change.key not in PREFERENCE_VALUES:
                raise ValueError(f"Unknown preference key: {change.key}")
            if change.action == "set":
                if change.value not in PREFERENCE_VALUES[change.key]:
                    raise ValueError(f"Invalid value for {change.key}: {change.value}")
                result.user_model.preferences[change.key] = change.value
            elif change.action == "remove":
                # 'I do not prefer steps' must not erase a current paragraph preference.
                if change.value is not None and result.user_model.preferences.get(change.key) != change.value:
                    continue
                result.user_model.preferences.pop(change.key, None)
            else:
                raise ValueError(f"Unknown preference action: {change.action}")
            accepted.append(change)
        if not accepted:
            return state
        result.revision = state.revision + 1
        for change in accepted:
            result.user_model.preference_provenance[change.key] = {
                "source": "explicit_user_input" if signal.kind != "preference_control" else "explicit_service_command",
                "signal_id": signal.signal_id, "revision": result.revision,
                "action": change.action, "value": change.value if change.action == "set" else None,
                "observed_at": signal.created_at, "evidence": change.evidence,
            }
        return result

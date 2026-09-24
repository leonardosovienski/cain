"""Structured output: the runtime constrains decoding to a JSON schema, CAIN validates the result.

Ollama receives the schema in ``format`` and llama.cpp in ``json_schema`` (grammar-constrained
decoding). Constrained decoding does not guarantee semantic validity (enums, bounds, required keys
under truncation), so every answer is validated here. Each attempt is a separate model call with
``seed + attempt``; invalid attempts are not discarded: when the provider goes through a recorder,
the call manifest and the validation outcome (with the error) stay in the inference store.
"""

from __future__ import annotations

from dataclasses import replace
import json
from uuid import uuid4

from cain.inference.recorder import inference_context
from cain.llm import LLMError

SUPPORTED = {"type", "properties", "required", "additionalProperties", "enum", "items", "minItems",
             "maxItems", "minLength", "maxLength", "minimum", "maximum", "description", "title"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool}


class StructuredOutputError(LLMError):
    def __init__(self, message: str, attempts: list[dict]):
        super().__init__(message)
        self.attempts = attempts


def check(schema: dict, value, path: str = "$") -> list[str]:
    """Errors of ``value`` against a JSON Schema subset; unknown keywords fail closed."""
    unknown = set(schema) - SUPPORTED
    if unknown:
        return [f"{path}: unsupported schema keywords {sorted(unknown)}"]
    errors: list[str] = []
    kind = schema.get("type")
    if kind in _TYPES and not isinstance(value, _TYPES[kind]):
        return [f"{path}: expected {kind}"]
    if kind == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        return [f"{path}: expected integer"]
    if kind == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        return [f"{path}: expected number"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required {name!r}")
        if schema.get("additionalProperties") is False:
            errors += [f"{path}: unexpected property {k!r}" for k in value if k not in properties]
        for name, sub in properties.items():
            if name in value:
                errors += check(sub, value[name], f"{path}.{name}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than maxItems")
        if "items" in schema:
            for index, item in enumerate(value):
                errors += check(schema["items"], item, f"{path}[{index}]")
    return errors


def generate_structured(provider, prompt: str, context: str, schema: dict, *, attempts: int = 2,
                        **context_values) -> tuple[dict, list[dict]]:
    """Validated JSON object and the list of attempts (each with call id, seed, validity, error)."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    group = "attempts:" + uuid4().hex
    transport = getattr(provider, "transport", None)
    store = getattr(transport, "store", None)
    history: list[dict] = []
    for attempt in range(attempts):
        current = provider if attempt == 0 else replace(provider, seed=provider.seed + attempt)
        error, value, text = None, None, None
        if transport is not None:
            transport.last_call_id = None  # a failure before the HTTP call must not reuse the last id
        with inference_context(attempt_group=group, attempt=attempt, **context_values):
            try:
                text = current.generate_json(prompt, context, schema)
                value = json.loads(text)
                problems = check(schema, value)
                error = "; ".join(problems)[:1000] if problems else None
            except (LLMError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"[:1000]
        call_id = getattr(transport, "last_call_id", None)
        history.append({"attempt": attempt, "seed": current.seed, "call_id": call_id, "valid": error is None,
                        "error": error, "metadata": dict(current.last_metadata)})
        if store is not None and call_id is not None:
            store.validation(call_id, group, attempt, error is None, error)
        if error is None:
            return value, history
    raise StructuredOutputError(f"no valid structured answer after {attempts} attempts", history)

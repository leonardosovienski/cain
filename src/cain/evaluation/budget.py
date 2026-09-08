"""Replaceable counting boundary. Character counts are a smoke-only substitute."""

from typing import Protocol


class ContextCounter(Protocol):
    unit: str
    formal_ready: bool

    def count(self, text: str) -> int: ...

    def truncate(self, text: str, budget: int, *, from_end: bool = True) -> str: ...


class CharacterCounter:
    unit = "unicode_characters_not_tokens"
    formal_ready = False

    def count(self, text: str) -> int:
        return len(text)

    def truncate(self, text: str, budget: int, *, from_end: bool = True) -> str:
        if budget < 0:
            raise ValueError("Context budget must be nonnegative")
        if not budget:
            return ""
        return text[-budget:] if from_end else text[:budget]


class RecordingLLM:
    def __init__(self, delegate, counter: ContextCounter, maximum: int | None = None):
        self.delegate = delegate
        self.counter = counter
        self.maximum = maximum
        self.calls: list[dict] = []

    def generate(self, prompt: str, context: str = "") -> str:
        original = context
        if self.maximum is not None:
            # Preserve the beginning of C's structured identity before any trailing memory.
            context = self.counter.truncate(context, self.maximum, from_end=False)
        call = {
            "prompt": prompt, "context": context, "response": None,
            "context_size": self.counter.count(context),
            "original_context_size": self.counter.count(original),
            "counter_unit": self.counter.unit,
            "truncation_strategy": "keep_prefix" if self.maximum is not None else "none",
            "status": "started",
        }
        self.calls.append(call)
        try:
            response = self.delegate.generate(prompt, context=context)
        except Exception as error:
            call.update(status="failed", error_type=type(error).__name__, error=str(error))
            raise
        call.update(status="completed", response=response)
        return response

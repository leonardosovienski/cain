"""LLM boundary. FakeLLM is a deterministic test double, not a language model."""

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@runtime_checkable
class LLM(Protocol):
    def generate(self, prompt: str, context: str = "") -> str: ...


class LLMError(RuntimeError):
    pass


@dataclass
class FakeLLM:
    """Offline wiring check only; outputs cannot evaluate LLM quality or identity."""

    def generate(self, prompt: str, context: str = "") -> str:
        fingerprint = sha256((context + "\n" + prompt).encode("utf-8")).hexdigest()[:12]
        excerpt = " ".join(prompt.split())[:180]
        return f"[SIMULAÇÃO FakeLLM — sem inferência real; {fingerprint}] {excerpt}"


@dataclass
class OllamaLLM:
    """POST /api/generate, non-streaming. No implicit retry or fake fallback.

    API reference: https://docs.ollama.com/api/generate (checked 2026-09-07).
    A seed is requested, but model/backend determinism is not guaranteed.
    """

    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.0
    seed: int = 42
    timeout: float = 60.0

    def generate(self, prompt: str, context: str = "") -> str:
        body = {
            "model": self.model,
            "prompt": prompt,
            "system": context,
            "stream": False,
            "options": {"temperature": self.temperature, "seed": self.seed},
        }
        request = Request(
            self.base_url.rstrip("/") + "/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise LLMError(f"Ollama indisponível ou resposta inválida: {exc}") from exc
        if not isinstance(result, dict) or not isinstance(result.get("response"), str):
            raise LLMError("Ollama não retornou o campo textual response.")
        if result.get("error") or result.get("done") is False:
            raise LLMError("Ollama retornou erro ou geração incompleta.")
        return result["response"]

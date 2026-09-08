"""LLM boundary. FakeLLM is a deterministic test double, not a language model."""

from dataclasses import dataclass, field
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
    timeout: float = 120.0
    num_ctx: int = 8192
    num_predict: int = 768
    max_input_bytes: int = 6500
    last_metadata: dict = field(default_factory=dict, init=False)

    def generate(self, prompt: str, context: str = "") -> str:
        self.last_metadata = {}
        input_bytes = len((context + prompt).encode("utf-8"))
        # Conservative transport bound, explicitly not the model's tokenizer.
        # Keep all user instructions/profile intact; oversized input fails visibly.
        effective_budget = min(self.max_input_bytes, self.num_ctx - self.num_predict - 256)
        if input_bytes > effective_budget:
            raise LLMError(
                f"Pedido e contexto somam {input_bytes} bytes; limite configurado "
                f"{effective_budget}. Reduza o texto ou ajuste o orçamento de contexto."
            )
        body = {
            "model": self.model,
            "prompt": prompt,
            "system": context,
            "stream": False,
            "options": {"temperature": self.temperature, "seed": self.seed,
                        "num_ctx": self.num_ctx, "num_predict": self.num_predict},
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
        if not result["response"].strip():
            raise LLMError("Ollama retornou resposta vazia.")
        self.last_metadata = {key: result.get(key) for key in (
            "model", "done_reason", "prompt_eval_count", "eval_count",
            "total_duration", "load_duration", "eval_duration",
        )}
        self.last_metadata.update(input_bytes=input_bytes, num_ctx=self.num_ctx,
                                  max_input_bytes=self.max_input_bytes,
                                  effective_input_byte_budget=effective_budget)
        return result["response"]

"""Opt-in ChatML serialization for prompt-only Qwen 3.5 imports."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request

from cain.llm import LLMError, OllamaLLM, urlopen


RESERVED_TOKENS = ("<|im_start|>", "<|im_end|>", "<|endoftext|>")


def serialize_text_chat(prompt: str, system: str) -> str:
    """Serialize system/user roles with thinking disabled in the assistant prefix."""
    if type(prompt) is not str or type(system) is not str:
        raise TypeError("Prompt and system instruction must be strings")
    if any(token in text for text in (prompt, system) for token in RESERVED_TOKENS):
        raise LLMError("Reserved role token in evidence; generation refused")
    return (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


class Qwen35PromptOnlyLLM(OllamaLLM):
    """Use only with an Ollama model whose installed template is ``{{ .Prompt }}``."""

    def _generate(self, prompt, context, schema=None):
        request = Request(
            self.base_url.rstrip("/") + "/api/show",
            data=json.dumps({"model": self.model}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=min(self.timeout, 15)) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise LLMError("Model metadata exceeds 4 MiB")
            info = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise LLMError(f"Cannot verify prompt-only model template: {exc}") from exc
        if info.get("template", "").strip() != "{{ .Prompt }}":
            raise LLMError("Adapter requires a prompt-only template; double serialization refused")
        result = super()._generate(serialize_text_chat(prompt, context), "", schema)
        self.last_metadata["serialization"] = "qwen35-text-chat-no-thinking-v1"
        self.last_metadata["requires_model_template"] = "{{ .Prompt }}"
        return result

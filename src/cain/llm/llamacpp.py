"""Opt-in local llama.cpp text transport with explicit model identity."""

from dataclasses import dataclass
import json
from pathlib import PurePath
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request

from cain.llm import LLMError, LLMTruncated, OllamaLLM, urlopen
from cain.llm.qwen35 import RESERVED_TOKENS, serialize_text_chat


def _serialize_qwen25(prompt: str, system: str) -> str:
    if type(prompt) is not str or type(system) is not str:
        raise TypeError("Prompt and system instruction must be strings")
    if any(token in text for text in (prompt, system) for token in RESERVED_TOKENS):
        raise LLMError("Reserved role token in evidence; generation refused")
    return (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


@dataclass
class LocalLlamaCppLLM(OllamaLLM):
    """POST to a local llama.cpp server after checking its loaded model filename."""

    expected_model_filename: str = ""
    chat_format: str = "qwen35-no-thinking"

    def __post_init__(self):
        super().__post_init__()
        if urlsplit(self.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("LocalLlamaCppLLM requires a loopback URL")
        if (
            type(self.expected_model_filename) is not str
            or not self.expected_model_filename
            or PurePath(self.expected_model_filename).name != self.expected_model_filename
        ):
            raise ValueError("expected_model_filename must be one filename")
        if self.chat_format not in {"qwen35-no-thinking", "qwen25"}:
            raise ValueError("Unsupported local chat format")

    def _generate(self, prompt, context, schema=None):
        self.last_metadata = {}
        try:
            with urlopen(
                Request(self.base_url.rstrip("/") + "/props"),
                timeout=min(self.timeout, 15),
            ) as response:
                raw_props = response.read(4 * 1024 * 1024 + 1)
            if len(raw_props) > 4 * 1024 * 1024:
                raise LLMError("Model properties exceed 4 MiB")
            properties = json.loads(raw_props.decode("utf-8"))
            loaded = str(properties.get("model_path", "")).replace("\\", "/").rsplit("/", 1)[-1]
            if loaded != self.expected_model_filename:
                raise LLMError("Loaded model does not match declared local identity")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise LLMError(f"Cannot verify local model identity: {exc}") from exc

        serialized = (
            serialize_text_chat(prompt, context)
            if self.chat_format == "qwen35-no-thinking"
            else _serialize_qwen25(prompt, context)
        )
        input_bytes = len(serialized.encode("utf-8"))
        if input_bytes > min(self.max_input_bytes, self.num_ctx - self.num_predict - 256):
            raise LLMError("Input exceeds declared context byte budget; no truncation")
        body = {
            "prompt": serialized,
            "n_predict": self.num_predict,
            "temperature": self.temperature,
            "seed": self.seed,
            "stream": False,
            "cache_prompt": True,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        }
        if schema is not None:
            body["json_schema"] = schema
        request = Request(
            self.base_url.rstrip("/") + "/completion",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise LLMError("Response exceeds 4 MiB")
            result = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise LLMError(f"Local llama.cpp request failed: {exc}") from exc
        if not isinstance(result, dict) or not isinstance(result.get("content"), str):
            raise LLMError("Local llama.cpp returned no text")
        self.last_metadata = {
            "backend": "llama.cpp local text-only",
            "model": self.model,
            "loaded_model": properties["model_path"],
            "timings": result.get("timings"),
            "stop_type": result.get("stop_type"),
            "tokens_predicted": result.get("tokens_predicted"),
            "tokens_evaluated": result.get("tokens_evaluated"),
            "serialization": (
                "qwen35-text-chat-no-thinking-v1"
                if self.chat_format == "qwen35-no-thinking"
                else "qwen25-text-chat-v1"
            ),
            "structured_output": schema is not None,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
            "input_bytes": input_bytes,
        }
        if result.get("stop_type") == "limit" or result.get("stopped_limit"):
            raise LLMTruncated("Local model reached generation limit", result["content"])
        if not result["content"].strip():
            raise LLMError("Empty model response")
        return result["content"]

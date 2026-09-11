"""Bounded local Ollama streaming and image input. Tokens remain provisional."""

import base64
from hashlib import sha256
from io import BytesIO
import json
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import Request

from cain.llm import LLMError, LLMTruncated, urlopen


def require_local(provider):
    parts = urlsplit(getattr(provider, "base_url", ""))
    if (parts.scheme != "http" or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parts.username or parts.password or parts.query or parts.fragment):
        raise ValueError("This capability requires a loopback Ollama provider")


def validate_images(images):
    if type(images) is not list or len(images) > 1:
        raise ValueError("At most one image per request")
    for encoded in images:
        if type(encoded) is not str or len(encoded) > 2_800_000:
            raise ValueError("Image exceeds input limit")
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError("Invalid base64 image") from exc
        if len(data) > 2_000_000:
            raise ValueError("Image exceeds 2000000 bytes")
        try:
            from PIL import Image
        except ImportError as exc:
            raise ValueError("Install the vision extra to validate images") from exc
        try:
            with Image.open(BytesIO(data)) as image:
                if image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise ValueError("Use PNG, JPEG or WebP")
                if image.width * image.height > 4_194_304 or max(image.size) > 4096:
                    raise ValueError("Image exceeds pixel limit")
                image.verify()
        except (OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Invalid or oversized image") from exc
    return images


def stream(provider, prompt, context="", images=None):
    require_local(provider)
    if type(prompt) is not str or not prompt.strip() or type(context) is not str:
        raise ValueError("Nonempty textual prompt required")
    images = validate_images([] if images is None else images)
    input_bytes = len((prompt + context).encode())
    budget = min(provider.max_input_bytes, provider.num_ctx - provider.num_predict - 256)
    if input_bytes > budget:
        raise ValueError("Prompt exceeds configured input budget")
    body = {"model": provider.model, "prompt": prompt, "system": context, "stream": True,
            "options": {"temperature": provider.temperature, "seed": provider.seed,
                        "num_ctx": provider.num_ctx, "num_predict": provider.num_predict}}
    if images:
        body["images"] = images
    if provider.think is not None:
        body["think"] = provider.think
    provider.last_metadata = {}
    request = Request(provider.base_url.rstrip("/") + "/api/generate",
                      data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    started, total, text = monotonic(), 0, ""
    with urlopen(request, timeout=provider.timeout) as response:
        while True:
            raw = response.readline(131073)
            if not raw:
                raise LLMError("Stream ended without a terminal done event")
            total += len(raw)
            if len(raw) > 131072 or total > 4_194_304 or monotonic() - started > provider.timeout:
                raise LLMError("Stream exceeded byte or time budget")
            try:
                event = json.loads(raw)
            except ValueError as exc:
                raise LLMError("Invalid NDJSON stream") from exc
            if type(event) is not dict or event.get("error"):
                raise LLMError("Provider stream error")
            piece = event.get("response", "")
            if type(piece) is not str:
                raise LLMError("Nontext stream token")
            text += piece
            if len(text.encode()) > 100_000:
                raise LLMError("Generated text exceeds output limit")
            if piece:
                yield {"type": "token", "text": piece, "provisional": True}
            if event.get("done") is True:
                provider.last_metadata = {k: event.get(k) for k in (
                    "model", "done_reason", "eval_count", "prompt_eval_count", "total_duration")}
                if event.get("done_reason") in {"length", "max_tokens"}:
                    raise LLMTruncated("Generation exhausted its token budget", text)
                if not text.strip():
                    raise LLMError("Empty generated response")
                yield {"type": "done", "text": text, "generation": provider.last_metadata,
                       "semantic_support": "not_certified", "images": len(images),
                       "input_sha256": sha256((context + prompt).encode()).hexdigest(),
                       "image_sha256": [sha256(base64.b64decode(item)).hexdigest() for item in images]}
                return

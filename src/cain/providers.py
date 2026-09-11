"""Provider composition shared by CLI and API; importing performs no I/O."""

import json
from urllib.request import urlopen

from cain.llm import FakeLLM, OllamaLLM


def make_llm(provider: str, model: str, base_url: str, temperature=0.0, seed=42, **options):
    if provider == "fake":
        return FakeLLM()
    if provider != "ollama":
        raise ValueError("Provedor inválido. Escolha fake ou ollama.")
    return OllamaLLM(model=model, base_url=base_url, temperature=temperature, seed=seed, **options)


def configured_llm(settings):
    return make_llm(settings.provider, settings.model, settings.base_url,
                    settings.temperature, settings.seed, timeout=settings.timeout,
                    num_ctx=settings.num_ctx, num_predict=settings.num_predict,
                    max_input_bytes=settings.max_input_bytes, think=settings.think)


def configured_embedding(settings):
    if settings.search_mode != "hybrid" or settings.provider == "fake":
        return None
    from cain.search import OllamaEmbedding
    with urlopen(settings.base_url.rstrip("/") + "/api/tags", timeout=5) as response:
        tags = json.load(response)
    found = next((model for model in tags.get("models", [])
                  if model.get("name") == settings.embedding_model), None)
    if not found or not found.get("digest"):
        raise ValueError(f"Modelo de busca indisponível: {settings.embedding_model}")
    if settings.embedding_digest and settings.embedding_digest != found["digest"]:
        raise ValueError("Digest do modelo de busca mudou; revise a configuração antes de reutilizar o índice")
    return OllamaEmbedding(settings.embedding_model, model_digest=found["digest"],
                           base_url=settings.base_url, timeout=settings.timeout)



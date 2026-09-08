"""Configuration at the application boundary; secrets are not required for local Ollama."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    provider: str = "ollama"
    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.0
    seed: int = 42
    timeout: float = 120.0
    num_ctx: int = 8192
    num_predict: int = 768
    max_input_bytes: int = 6500
    think: bool | None = None
    db_path: Path = Path("data/cain.db")
    source_paths: list[Path] = field(default_factory=list)
    allow_public_urls: bool = True
    llm_routing: bool = True
    search_mode: str = "lexical"
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_digest: str = ""


def load_settings(config_path: Path | None = None) -> Settings:
    if config_path is None:
        local = Path.cwd() / "cain.toml"
        bundled = Path(__file__).resolve().parents[2] / "cain.toml"
        config_path = local if local.is_file() else bundled
    config_path = Path(config_path)
    if config_path.is_file():
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
        base = config_path.resolve().parent
    else:
        data, base = {}, Path.cwd()
    settings = Settings(**data.get("llm", {}))
    db = Path(os.getenv("CAIN_DB", data.get("storage", {}).get("path", "data/cain.db")))
    settings.db_path = db if db.is_absolute() else base / db
    search = data.get("search", {})
    settings.source_paths = [p if p.is_absolute() else base / p
                             for p in map(Path, search.get("paths", []))]
    settings.allow_public_urls = bool(search.get("allow_public_urls", True))
    settings.search_mode = search.get("mode", "lexical")
    if settings.search_mode not in {"lexical", "hybrid"}:
        raise ValueError("search.mode deve ser lexical ou hybrid")
    settings.embedding_model = search.get("embedding_model", "qwen3-embedding:0.6b")
    settings.embedding_digest = search.get("embedding_digest", "")
    settings.llm_routing = bool(data.get("orchestration", {}).get("llm_routing", True))
    settings.provider = os.getenv("CAIN_PROVIDER", settings.provider)
    settings.model = os.getenv("CAIN_MODEL", settings.model)
    settings.base_url = os.getenv("CAIN_OLLAMA_URL", settings.base_url)
    return settings

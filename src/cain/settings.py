"""Configuration at the application boundary; secrets are not required for local Ollama."""

import os
import math
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


LLM_FIELDS = {"provider", "model", "base_url", "temperature", "seed", "timeout",
              "num_ctx", "num_predict", "max_input_bytes", "think"}


def validate_llm_options(options):
    for key in ("model", "base_url"):
        if type(options[key]) is not str or not options[key].strip():
            raise ValueError(f"llm.{key} deve ser texto não vazio")
    for key in ("num_ctx", "num_predict", "max_input_bytes"):
        if type(options[key]) is not int or options[key] < 1:
            raise ValueError(f"llm.{key} deve ser inteiro positivo")
    if options["num_ctx"] <= options["num_predict"] + 256:
        raise ValueError("llm.num_ctx deve reservar espaço para entrada e geração")
    if type(options["seed"]) is not int:
        raise ValueError("llm.seed deve ser inteiro")
    for key in ("timeout", "temperature"):
        value = options[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"llm.{key} deve ser número finito não negativo")
    if options["timeout"] == 0:
        raise ValueError("llm.timeout deve ser positivo")
    if options["think"] is not None and type(options["think"]) is not bool:
        raise ValueError("llm.think deve ser booleano")
    url = options["base_url"]
    parts = urlsplit(url)
    if (parts.scheme not in {"http", "https"} or not parts.hostname
        or parts.username is not None or parts.password is not None or parts.query or parts.fragment
        or any(c.isspace() or ord(c) < 32 for c in url)):
        raise ValueError("llm.base_url deve ser HTTP(S), sem credenciais, query ou fragmento")
    _ = parts.port  # Validate malformed/out-of-range ports now, not during a request.


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

    def validate(self):
        validate_llm_options(vars(self))
        if type(self.provider) is not str or self.provider not in {"fake", "ollama"}:
            raise ValueError("Provedor inválido. Escolha fake ou ollama.")
        return self


def load_settings(config_path: Path | None = None) -> Settings:
    if config_path is not None and not Path(config_path).is_file():
        raise ValueError("Arquivo de configuração explícito não encontrado")
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
    sections = {"llm": LLM_FIELDS, "storage": {"path"},
                "search": {"paths", "allow_public_urls", "mode", "embedding_model", "embedding_digest"},
                "orchestration": {"llm_routing"}}
    if set(data) - set(sections):
        raise ValueError("Seção desconhecida na configuração")
    for name, fields in sections.items():
        section = data.get(name, {})
        if type(section) is not dict or set(section) - fields:
            raise ValueError(f"Campos inválidos na configuração {name}")
    try:
        settings = Settings(**data.get("llm", {}))
    except TypeError as exc:
        raise ValueError("Campos inválidos na configuração llm") from exc
    db_value = os.getenv("CAIN_DB", data.get("storage", {}).get("path", "data/cain.db"))
    if type(db_value) is not str or not db_value.strip():
        raise ValueError("storage.path deve ser texto não vazio")
    db = Path(db_value)
    settings.db_path = db if db.is_absolute() else base / db
    search = data.get("search", {})
    paths = search.get("paths", [])
    if type(paths) is not list or not all(type(p) is str and p.strip() for p in paths):
        raise ValueError("search.paths deve ser uma lista de caminhos textuais")
    settings.source_paths = [p if p.is_absolute() else base / p
                             for p in map(Path, search.get("paths", []))]
    settings.allow_public_urls = search.get("allow_public_urls", True)
    if type(settings.allow_public_urls) is not bool:
        raise ValueError("search.allow_public_urls deve ser booleano")
    settings.search_mode = search.get("mode", "lexical")
    if type(settings.search_mode) is not str or settings.search_mode not in {"lexical", "hybrid"}:
        raise ValueError("search.mode deve ser lexical ou hybrid")
    settings.embedding_model = search.get("embedding_model", "qwen3-embedding:0.6b")
    settings.embedding_digest = search.get("embedding_digest", "")
    if (type(settings.embedding_model) is not str or not settings.embedding_model.strip()
        or type(settings.embedding_digest) is not str):
        raise ValueError("Modelo e digest de embedding devem ser textuais")
    settings.llm_routing = data.get("orchestration", {}).get("llm_routing", True)
    if type(settings.llm_routing) is not bool:
        raise ValueError("orchestration.llm_routing deve ser booleano")
    settings.provider = os.getenv("CAIN_PROVIDER", settings.provider)
    settings.model = os.getenv("CAIN_MODEL", settings.model)
    settings.base_url = os.getenv("CAIN_OLLAMA_URL", settings.base_url)
    return settings.validate()

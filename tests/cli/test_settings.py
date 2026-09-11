from cain.cli import configured_llm
from cain.llm import FakeLLM, OllamaLLM
from cain.settings import load_settings
import pytest


def test_configuration_resolves_data_and_sources_from_its_own_directory(tmp_path, monkeypatch):
    for variable in ("CAIN_DB", "CAIN_PROVIDER", "CAIN_MODEL", "CAIN_OLLAMA_URL"):
        monkeypatch.delenv(variable, raising=False)
    config = tmp_path / "cain.toml"
    config.write_text('[llm]\nprovider="ollama"\nmodel="fixture-model"\n'
                      '[storage]\npath="state/app.db"\n'
                      '[search]\npaths=["notes"]\nallow_public_urls=false\n', encoding="utf-8")
    settings = load_settings(config)
    assert settings.db_path == tmp_path / "state/app.db"
    assert settings.source_paths == [tmp_path / "notes"]
    assert not settings.allow_public_urls
    assert isinstance(configured_llm(settings), OllamaLLM)
    monkeypatch.setenv("CAIN_PROVIDER", "fake")
    assert isinstance(configured_llm(load_settings(config)), FakeLLM)


def test_explicit_missing_config_fails_instead_of_using_other_settings(tmp_path):
    with pytest.raises(ValueError, match="explícito"):
        load_settings(tmp_path / "missing.toml")


@pytest.mark.parametrize("text", ['[search]\nallow_public_urls="false"',
                                  '[orchestration]\nllm_routing="false"',
                                  '[llm]\nunknown=true'])
def test_invalid_configuration_is_not_coerced_into_permissions(tmp_path, text):
    config = tmp_path / "invalid.toml"
    config.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_settings(config)

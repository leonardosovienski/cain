"""General generation is local-only unless the operator opts in.

Protected behaviour: an ``llm.base_url`` outside the loopback block is refused when
settings load, unless ``llm.allow_remote = true`` (or ``CAIN_OLLAMA_ALLOW_REMOTE=1``)
says the operator accepts that profile, history and documents leave the machine. The
``fake`` provider and loopback endpoints are unaffected; ``doctor`` still warns when the
opt-in is used.
"""
import json

import pytest

from cain import cli
from cain.settings import load_settings


def config(tmp_path, body):
    path = tmp_path / "cain.toml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize("base_url", ["http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434"])
def test_loopback_endpoints_need_no_opt_in(tmp_path, base_url, monkeypatch):
    monkeypatch.delenv("CAIN_OLLAMA_ALLOW_REMOTE", raising=False)
    settings = load_settings(config(tmp_path, f'[llm]\nbase_url="{base_url}"\n'))
    assert settings.base_url == base_url and settings.allow_remote is False


@pytest.mark.parametrize("base_url", ["http://ollama.lan:11434", "http://10.0.0.5:11434", "https://api.example.com"])
def test_remote_endpoint_is_refused_by_default(tmp_path, base_url, monkeypatch):
    monkeypatch.delenv("CAIN_OLLAMA_ALLOW_REMOTE", raising=False)
    with pytest.raises(ValueError, match="allow_remote"):
        load_settings(config(tmp_path, f'[llm]\nbase_url="{base_url}"\n'))
    monkeypatch.setenv("CAIN_OLLAMA_URL", base_url)
    with pytest.raises(ValueError, match="allow_remote"):
        load_settings(config(tmp_path, '[llm]\nmodel="qwen3.5:4b"\n'))


def test_opt_in_in_toml_or_environment_admits_a_remote_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_OLLAMA_ALLOW_REMOTE", raising=False)
    settings = load_settings(config(tmp_path, '[llm]\nbase_url="http://ollama.lan:11434"\nallow_remote=true\n'))
    assert settings.allow_remote is True
    monkeypatch.setenv("CAIN_OLLAMA_ALLOW_REMOTE", "1")
    assert load_settings(config(tmp_path, '[llm]\nbase_url="http://ollama.lan:11434"\n')).allow_remote is True
    monkeypatch.setenv("CAIN_OLLAMA_ALLOW_REMOTE", "0")
    with pytest.raises(ValueError, match="allow_remote"):
        load_settings(config(tmp_path, '[llm]\nbase_url="http://ollama.lan:11434"\n'))


def test_opt_in_must_be_boolean(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_OLLAMA_ALLOW_REMOTE", raising=False)
    with pytest.raises(ValueError, match="allow_remote"):
        load_settings(config(tmp_path, '[llm]\nallow_remote="yes"\n'))


def test_fake_provider_ignores_the_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_OLLAMA_ALLOW_REMOTE", raising=False)
    settings = load_settings(config(tmp_path, '[llm]\nprovider="fake"\nbase_url="http://ollama.lan:11434"\n'))
    assert settings.provider == "fake"


def test_doctor_still_warns_when_remote_is_allowed(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("CAIN_OLLAMA_ALLOW_REMOTE", raising=False)
    path = config(tmp_path, '[llm]\nmodel="qwen3.5:4b"\nbase_url="http://ollama.lan:11434"\nallow_remote=true\n'
                            '[search]\npaths=[]\nallow_public_urls=false\n')

    class Tags:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({"models": [{"name": "qwen3.5:4b"}]}).encode()

    monkeypatch.setattr(cli, "urlopen", lambda request, timeout: Tags())
    assert cli.main(["doctor", "--config", str(path)]) == 0
    out, err = capsys.readouterr()
    assert json.loads(out)["warnings"] and "não é loopback (ollama.lan)" in err
    assert cli.main(["doctor", "--config", str(config(tmp_path, '[llm]\nbase_url="http://ollama.lan:11434"\n'))]) == 1
    assert "allow_remote" in capsys.readouterr().err

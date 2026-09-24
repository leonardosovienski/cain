"""``cain doctor`` warns when the LLM endpoint is not loopback.

Protected behaviour: the doctor JSON carries a ``warnings`` list; it is empty for any
loopback ``llm.base_url`` and names the host otherwise, before the model probe, so the
warning is printed even when the remote endpoint cannot be reached. The exit code still
reflects only model availability.
"""
import io
import json

import pytest

from cain import cli


class TagsResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def config(tmp_path):
    def make(base_url):
        path = tmp_path / "doctor.toml"
        # allow_remote: the remote cases test the warning, not the load-time refusal
        path.write_text(f'[llm]\nprovider="ollama"\nmodel="qwen3.5:4b"\nbase_url="{base_url}"\nallow_remote=true\n'
                        '[search]\npaths=[]\nallow_public_urls=false\n', encoding="utf-8")
        return str(path)
    return make


@pytest.fixture
def fake_tags(monkeypatch):
    seen = []

    def urlopen(request, timeout):
        seen.append(request if isinstance(request, str) else request.full_url)
        return TagsResponse(json.dumps({"models": [{"name": "qwen3.5:4b"}]}).encode())

    monkeypatch.setattr(cli, "urlopen", urlopen)
    return seen


@pytest.mark.parametrize("base_url", ["http://127.0.0.1:11434", "http://127.0.0.2:11434", "http://localhost:11434"])
def test_loopback_endpoint_has_no_warning(config, fake_tags, capsys, base_url):
    assert cli.main(["doctor", "--config", config(base_url)]) == 0
    out, err = capsys.readouterr()
    assert json.loads(out)["warnings"] == [] and err == ""


def test_remote_endpoint_is_flagged_but_does_not_change_the_exit_code(config, fake_tags, capsys):
    assert cli.main(["doctor", "--config", config("http://ollama.lan:11434")]) == 0
    out, err = capsys.readouterr()
    report = json.loads(out)
    assert report["model_available"] is True
    assert report["warnings"] == ["llm.base_url não é loopback (ollama.lan): perfil, histórico e "
                                  "documentos da conversa saem desta máquina"]
    assert "Cain: aviso: llm.base_url não é loopback (ollama.lan)" in err


def test_warning_is_printed_before_an_unreachable_remote_probe_fails(config, monkeypatch, capsys):
    def refuse(request, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(cli, "urlopen", refuse)
    assert cli.main(["doctor", "--config", config("http://10.0.0.5:11434")]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.index("Cain: aviso: llm.base_url não é loopback (10.0.0.5)") < err.index("Cain: connection refused")

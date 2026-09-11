import ast
from pathlib import Path

from cain.providers import configured_llm
from cain.settings import load_settings
from cain.llm import FakeLLM


def test_api_and_research_do_not_import_cli_factories():
    root = Path(__file__).resolve().parents[2] / "src" / "cain"
    for path in (root / "api.py", root / "research" / "cli.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(isinstance(node, ast.ImportFrom) and node.module == "cain.cli"
                       for node in ast.walk(tree))


def test_offline_provider_configuration_does_not_require_a_model(tmp_path, monkeypatch):
    monkeypatch.delenv("CAIN_PROVIDER", raising=False)
    path = tmp_path / "config.toml"
    path.write_text('[llm]\nprovider = "fake"\n', encoding="utf-8")
    assert isinstance(configured_llm(load_settings(path)), FakeLLM)

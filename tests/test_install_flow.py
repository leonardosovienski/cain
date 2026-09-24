"""The documented install flow must match the lock-based flow the CI runs.

Protected behaviour: a fresh checkout installs from ``uv.lock`` (``uv sync --locked``),
never from the ``vendor/`` directory removed in PR #8. README.md and the Windows
launcher are the two documented entry points; both are checked here.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _fenced_blocks(markdown: str) -> list[str]:
    return re.findall(r"```[a-z]*\n(.*?)```", markdown, flags=re.S)


def test_readme_install_commands_use_the_lock_not_vendor():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = readme.split("## Instalar um checkout separado", 1)[1]
    blocks = _fenced_blocks(install)
    assert blocks, "README install section must show commands"
    commands = "\n".join(blocks)
    assert "vendor" not in commands and "--find-links" not in commands
    assert "uv sync --locked" in commands
    assert not (ROOT / "vendor").exists()


def test_windows_launcher_installs_from_the_lock_not_vendor():
    script = (ROOT / "scripts/start-cain.ps1").read_text(encoding="utf-8")
    assert "vendor" not in script and "find-links" not in script
    assert re.search(r"\bsync\b.*--locked", script), "launcher must run uv sync --locked"
    assert re.search(r"Get-Command\s+uv", script), "launcher must fail clearly without uv"

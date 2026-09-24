"""README's current-state description must name the packaged version.

Protected behaviour: the line "CAIN <versão> é um assistente local…" in README.md
tracks ``cain.__version__`` (the same value as pyproject.toml). Dated reports keep
their historical versions and are deliberately not checked.
"""
from pathlib import Path
import re

from cain import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_readme_current_state_names_the_packaged_version():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"^CAIN (\S+) é um assistente local", readme, flags=re.M)
    assert match, "README must describe the current version in one sentence"
    assert match.group(1) == __version__

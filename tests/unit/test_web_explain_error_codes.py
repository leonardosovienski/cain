"""The web panel explains every generation failure code the research modules emit.

Found while driving the UI: ``INVALID_JSON`` (the code a fake provider produces)
rendered only the generic "não foi possível produzir uma explicação" line, with no
reason. This contract test reads the codes out of the Python sources and requires a
message for each in ``app.js``, plus a fallback line for codes added later.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "src" / "cain" / "research"
APP_JS = (ROOT / "src" / "cain" / "web" / "app.js").read_text(encoding="utf-8")


def emitted_error_codes() -> set[str]:
    codes: set[str] = set()
    for module in ("historian.py", "analysis.py"):
        source = (RESEARCH / module).read_text(encoding="utf-8")
        codes.update(re.findall(r'error_code\s*[=:]\s*"([A-Z_]+)"', source))
        codes.update(re.findall(r'"[A-Za-z :\-]+": "([A-Z_]+)",', source))
        codes.update(re.findall(r'codes\.get\(str\(exc\), "([A-Z_]+)"\)', source))
        codes.update(re.findall(r'"error_code": "([A-Z_]+)" if', source))
    assert {"INVALID_JSON", "TIMEOUT", "PROVIDER_ERROR", "GENERATION_REJECTED"} <= codes
    return codes


def test_every_emitted_error_code_has_a_message_in_the_web_panel():
    block = re.search(r"const errorMessages = \{(.*?)\n    \};", APP_JS, flags=re.S)
    assert block, "app.js must keep the errorMessages table"
    described = set(re.findall(r"^\s*([A-Z_]+):", block.group(1), flags=re.M))
    missing = emitted_error_codes() - described - {"INVALID_REVIEW_OUTPUT"}
    assert not missing, f"error codes without a user-facing message: {sorted(missing)}"


def test_unknown_error_codes_still_show_the_code():
    assert "errorMessages[result.error_code] ?? `Erro ${result.error_code}" in APP_JS

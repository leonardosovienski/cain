"""Transport regressions; synthetic HTTP errors are not semantic model evidence."""

import io
import json
from urllib.error import HTTPError

import pytest

from cain.llm import LLMError, OllamaLLM


def test_effective_budget_is_available_before_generation():
    model = OllamaLLM(num_ctx=4096, num_predict=650, max_input_bytes=6000)
    assert model.effective_input_byte_budget == 3190


@pytest.mark.parametrize("status,message", [(404, "model not found"), (500, "failed to allocate buffer")])
def test_http_failure_preserves_bounded_diagnostic_without_retry(monkeypatch, status, message):
    calls = []

    def failure(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, status, "failure", {},
                        io.BytesIO(json.dumps({"error": message}).encode()))

    monkeypatch.setattr("cain.llm.urlopen", failure)
    model = OllamaLLM()
    with pytest.raises(LLMError, match=message):
        model.generate("question")
    assert len(calls) == 1
    assert model.last_metadata["http_status"] == status
    assert model.last_metadata["server_error"] == message


def test_non_json_error_body_is_not_exposed_as_model_text(monkeypatch):
    def failure(request, timeout):
        raise HTTPError(request.full_url, 500, "failure", {}, io.BytesIO(b"private " * 1000))

    monkeypatch.setattr("cain.llm.urlopen", failure)
    model = OllamaLLM()
    with pytest.raises(LLMError) as error:
        model.generate("question")
    assert "private" not in str(error.value)
    assert model.last_metadata["http_status"] == 500
    assert model.last_metadata["server_error"] is None

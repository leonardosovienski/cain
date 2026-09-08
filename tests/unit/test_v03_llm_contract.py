"""Serialization/error contracts only: injected transport never contacts an LLM."""

import io
import json
from urllib.error import URLError

import pytest

from cain.llm import LLMError, LLMTruncated, OllamaLLM


ROUTE_SCHEMA = {
    "type": "object", "properties": {"agent": {"enum": ["codigo", "resumo", "busca"]}},
    "required": ["agent"], "additionalProperties": False,
}


@pytest.fixture
def transport(monkeypatch):
    calls = []
    config = {"result": {"response": '{ "agent": "codigo" }', "done": True,
                         "done_reason": "stop", "model": "fixture-only",
                         "prompt_eval_count": 17, "eval_count": 6,
                         "total_duration": 1000, "load_duration": 100, "eval_duration": 400}}

    def fake_urlopen(request, timeout):
        calls.append((request, json.loads(request.data), timeout))
        if "error" in config:
            raise config["error"]
        return io.BytesIO(json.dumps(config["result"]).encode("utf-8"))

    monkeypatch.setattr("cain.llm.urlopen", fake_urlopen)
    return calls, config


@pytest.mark.parametrize("think", [None, False, True])
def test_json_schema_think_and_generation_options_reach_transport(transport, think):
    calls, config = transport
    model = OllamaLLM(model="fixture-only", base_url="http://fixture.invalid/",
                      temperature=0.25, seed=73, timeout=7, num_ctx=4096,
                      num_predict=128, max_input_bytes=1000, think=think)
    assert model.generate_json("Classifique ação", "Perfil português", ROUTE_SCHEMA) == \
        config["result"]["response"]  # Preserve the actual returned JSON text.
    assert len(calls) == 1
    request, body, timeout = calls[0]
    assert request.full_url == "http://fixture.invalid/api/generate"
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert timeout == 7
    assert body["format"] == ROUTE_SCHEMA
    assert body["prompt"] == "Classifique ação" and body["system"] == "Perfil português"
    assert body["model"] == "fixture-only" and body["stream"] is False
    assert body["options"] == {"temperature": 0.25, "seed": 73, "num_ctx": 4096,
                               "num_predict": 128}
    if think is None:
        assert "think" not in body
    else:
        assert body["think"] is think
    assert model.last_metadata["structured_output"] is True
    assert model.last_metadata["think"] is think
    assert model.last_metadata["input_bytes"] == len("Perfil portuguêsClassifique ação".encode())
    assert model.last_metadata["eval_count"] == 6


def test_plain_generation_does_not_send_json_format(transport):
    calls, _ = transport
    OllamaLLM(think=False).generate("plain text")
    assert "format" not in calls[0][1]
    assert calls[0][1]["think"] is False


@pytest.mark.parametrize("schema", [{}, {"type": "array"}, []])
def test_invalid_schema_is_rejected_before_any_transport(transport, schema):
    calls, _ = transport
    with pytest.raises(ValueError, match="objeto"):
        OllamaLLM().generate_json("pedido", "perfil", schema)
    assert calls == []


def test_malformed_generated_json_fails_once_and_retains_reported_metadata(transport):
    calls, config = transport
    config["result"]["response"] = '{"agent":'
    model = OllamaLLM(think=False)
    with pytest.raises(LLMError, match="JSON inválido"):
        model.generate_json("pedido", "perfil", ROUTE_SCHEMA)
    assert len(calls) == 1
    assert model.last_metadata["done_reason"] == "stop"
    assert model.last_metadata["structured_output"] is True


@pytest.mark.parametrize("reason", ["length", "max_tokens"])
@pytest.mark.parametrize("structured", [False, True])
def test_truncation_preserves_partial_response_and_backend_evidence(transport, reason, structured):
    calls, config = transport
    partial = '{"agent":'
    config["result"].update(response=partial, done_reason=reason, eval_count=128)
    model = OllamaLLM(num_predict=128, think=False)
    with pytest.raises(LLMTruncated) as caught:
        if structured:
            model.generate_json("pedido", "perfil", ROUTE_SCHEMA)
        else:
            model.generate("pedido", "perfil")
    assert caught.value.partial_response == partial
    assert len(calls) == 1  # No retry or fallback, including malformed partial JSON.
    assert model.last_metadata["done_reason"] == reason
    assert model.last_metadata["eval_count"] == 128
    assert model.last_metadata["model"] == "fixture-only"
    assert model.last_metadata["structured_output"] is structured


def test_failed_transport_does_not_reuse_metadata_from_previous_generation(transport):
    calls, config = transport
    model = OllamaLLM()
    model.generate("first request")
    assert model.last_metadata["eval_count"] == 6
    config["error"] = URLError("simulated offline provider")
    with pytest.raises(LLMError, match="indisponível"):
        model.generate("second request")
    assert len(calls) == 2
    assert model.last_metadata == {}


def test_utf8_byte_guard_and_generation_reserve_fail_without_silent_cutting(transport):
    calls, _ = transport
    # 80 characters occupy 160 bytes; a character-only check would wrongly accept.
    model = OllamaLLM(max_input_bytes=100)
    with pytest.raises(LLMError, match="160 bytes"):
        model.generate("é" * 80)
    # The input also has to leave space for output and the configured safety reserve.
    model = OllamaLLM(num_ctx=1024, num_predict=512, max_input_bytes=6500)
    with pytest.raises(LLMError, match="256"):
        model.generate("x" * 257)
    assert calls == []

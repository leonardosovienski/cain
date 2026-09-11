"""Transport fixtures, not claims of real model quality."""
import base64
from io import BytesIO
import json

import pytest

from cain.llm import LLMError, LLMTruncated, OllamaLLM
from cain.llm.streaming import stream, validate_images
import cain.llm.streaming as transport


def response(monkeypatch, events):
    payload = b"".join(json.dumps(e).encode() + b"\n" for e in events)
    monkeypatch.setattr(transport, "urlopen", lambda *args, **kwargs: BytesIO(payload))


def test_real_incremental_transport_and_terminal_metadata(monkeypatch):
    response(monkeypatch, [{"response":"Olá ","done":False},
                           {"response":"world","done":True,"eval_count":2,"done_reason":"stop"}])
    provider = OllamaLLM()
    iterator = stream(provider, "Hello")
    first = next(iterator)
    assert first == {"type":"token","text":"Olá ","provisional":True}
    assert provider.last_metadata == {}
    rest = list(iterator)
    assert rest[-1]["type"] == "done"
    assert rest[-1]["text"] == "Olá world"
    assert provider.last_metadata["eval_count"] == 2


@pytest.mark.parametrize("events,error", [
    ([{"response":"partial","done":False}], LLMError),
    ([{"response":"partial","done":True,"done_reason":"length"}], LLMTruncated),
    ([{"response":"","done":True}], LLMError),
    ([{"error":"unavailable"}], LLMError),
    ([{"response":23,"done":True}], LLMError),
])
def test_failed_stream_never_emits_success(monkeypatch, events, error):
    response(monkeypatch, events)
    observed = []
    with pytest.raises(error):
        for event in stream(OllamaLLM(), "Question"):
            observed.append(event)
    assert not any(event["type"] == "done" for event in observed)


def test_redirect_remote_and_input_budget(monkeypatch):
    with pytest.raises(ValueError, match="loopback"):
        list(stream(OllamaLLM(base_url="https://external.invalid"), "x"))
    with pytest.raises(ValueError, match="budget"):
        list(stream(OllamaLLM(), "x" * 8000))
    monkeypatch.setattr(transport, "urlopen", lambda *a, **k: BytesIO(b"bad json\n"))
    with pytest.raises(LLMError, match="NDJSON"):
        list(stream(OllamaLLM(), "x"))


def test_image_validation_and_forwarding(monkeypatch):
    Image = pytest.importorskip("PIL.Image")
    data = BytesIO()
    Image.new("RGB", (32,32), "red").save(data, format="PNG")
    image = base64.b64encode(data.getvalue()).decode()
    assert validate_images([image]) == [image]
    sent = []
    def send(request, **kwargs):
        sent.append(json.loads(request.data))
        return BytesIO(b'{"response":"red","done":true}\n')
    monkeypatch.setattr(transport,"urlopen",send)
    assert list(stream(OllamaLLM(), "color?", images=[image]))[-1]["images"] == 1
    assert sent[0]["images"] == [image]
    with pytest.raises(ValueError):
        validate_images([image,image])
    with pytest.raises(ValueError):
        validate_images(["not base64"])
    with pytest.raises(ValueError):
        validate_images([base64.b64encode(b"not an image").decode()])
    large = BytesIO()
    Image.new("RGB", (4097,1)).save(large,format="PNG")
    with pytest.raises(ValueError,match="pixel"):
        validate_images([base64.b64encode(large.getvalue()).decode()])


def test_stream_close_releases_response(monkeypatch):
    raw = BytesIO(b'{"response":"partial","done":false}\n')
    monkeypatch.setattr(transport,"urlopen",lambda *a, **k: raw)
    iterator=stream(OllamaLLM(),"x")
    next(iterator)
    iterator.close()
    assert raw.closed

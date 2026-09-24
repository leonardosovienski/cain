"""Per-call manifest, record/replay cache and structured output against a local fake Ollama server."""

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
import threading
import time
from urllib.request import Request

import pytest

from cain.inference.harness import load_tasks, run_model, score
from cain.inference.recorder import InferenceStore, Recorder, ReplayMiss, attach, missing_fields
from cain.inference.structured import StructuredOutputError, check, generate_structured
from cain.llm import LLMError, OllamaLLM
from cain.providers import configured_llm
from cain.settings import load_settings

BLOB = "ab" * 32
HARNESS_V1_SHA256 = "765ae314093bfd49bf385148cd767b940e6f3971354eee049746bf829e3eb332"


class FakeOllama:
    """Enough of the Ollama HTTP API for the recorder: version, tags, show, ps, generate."""

    def __init__(self):
        self.blob = BLOB
        self.generate_calls = 0
        self.nondeterministic = False
        self.invalid_first = 0
        self.active = 0
        self.max_active = 0
        self.delay = 0.0
        self.lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, payload):
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if self.path == "/api/version":
                    return self._send({"version": "0.99.0-fake"})
                if self.path == "/api/tags":
                    return self._send({"models": [{"name": "fixture:1", "digest": "cd" * 32, "size": 1234}]})
                if self.path == "/api/ps":
                    return self._send({"models": [{"name": "fixture:1", "size": 4321, "size_vram": 0,
                                                   "context_length": 8192}]})
                self.send_error(404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/api/show":
                    return self._send({"modelfile": f"FROM /models/blobs/sha256-{fake.blob}\nPARAMETER temperature 0.6\n",
                                       "template": "{{ .System }} {{ .Prompt }}", "license": "fixture license",
                                       "parameters": 'stop "<|im_end|>"\ntemperature 0.6',
                                       "details": {"format": "gguf", "family": "fixture", "parameter_size": "1B",
                                                   "quantization_level": "Q4_K_M"}})
                if self.path != "/api/generate":
                    return self.send_error(404)
                with fake.lock:
                    fake.generate_calls += 1
                    number = fake.generate_calls
                    fake.active += 1
                    fake.max_active = max(fake.max_active, fake.active)
                time.sleep(fake.delay)
                with fake.lock:
                    fake.active -= 1
                text = self._answer(body, number)
                self._send({"model": body["model"], "response": text, "done": True, "done_reason": "stop",
                            "prompt_eval_count": 11, "eval_count": 7, "total_duration": 1000 + number,
                            "load_duration": 1, "eval_duration": 5})

            def _answer(self, body, number):
                schema = body.get("format")
                if isinstance(schema, dict):
                    if fake.invalid_first and number <= fake.invalid_first:
                        return json.dumps({"label": "MAYBE"})
                    props = schema["properties"]
                    if "label" in props:
                        return json.dumps({"label": props["label"]["enum"][0]})
                    return json.dumps({"answer": "1987", "quote": "opened in 1987"})
                suffix = f" #{number}" if fake.nondeterministic else ""
                return "echo: " + body["prompt"][:40] + suffix

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread.is_alive():
            self.server.shutdown()
            self.server.server_close()


@pytest.fixture
def ollama():
    fake = FakeOllama()
    yield fake
    fake.stop()


def _llm(fake, store, mode="manifest", **kw):
    llm = OllamaLLM(model="fixture:1", base_url=fake.url, think=False, timeout=10, **kw)
    return attach(llm, store, mode=mode)


def test_every_call_gets_a_complete_manifest(ollama, tmp_path):
    store = InferenceStore(tmp_path / "inference.db")
    assert not (tmp_path / "inference.db").exists()  # nothing written before a call
    llm = _llm(ollama, store)
    for prompt in ("first question", "second question", "third question"):
        llm.generate(prompt, "system text")
    calls = store.calls(10)
    assert len(calls) == 3 and {c["status"] for c in calls} == {"called"}
    for call in calls:
        manifest = call["manifest"]
        assert missing_fields(manifest, "/api/generate") == []
        assert manifest["input"]["system_sha256"] == sha256(b"system text").hexdigest()
        assert manifest["model"]["gguf_sha256"] == BLOB and manifest["runtime"]["backend"] == "cpu"
        assert manifest["parameters"]["requested"] == {"temperature": 0.0, "seed": 42, "num_ctx": 8192,
                                                       "num_predict": 768}
        assert manifest["model"]["default_parameters"]["temperature"] == "0.6"
        assert manifest["runtime_verified"] is True
    assert calls[0]["manifest"]["input"]["prompt_sha256"] == sha256(b"third question").hexdigest()
    assert ollama.generate_calls == 3
    audit = store.audit()
    assert audit["calls"] == 3 and audit["by_status"] == {"called": {"calls": 3, "complete": 3}}
    # A manifest missing a field is reported, not silently accepted.
    broken = {**calls[0]["manifest"], "model": {**calls[0]["manifest"]["model"], "gguf_sha256": None}}
    assert missing_fields(broken, "/api/generate") == ["model.gguf_sha256"]


def test_twenty_identical_calls_counted_and_replay_is_identical(ollama, tmp_path):
    store = InferenceStore(tmp_path / "inference.db")
    recorder = Recorder(store, mode="record")
    llm = OllamaLLM(model="fixture:1", base_url=ollama.url, think=False, timeout=10, transport=recorder)
    texts = {llm.generate("same prompt") for _ in range(20)}
    key = store.call(recorder.last_call_id)["cache_key"]
    outputs = store.outputs(key)
    assert len(texts) == 1 and len(outputs) == 20 and len({o["text_sha256"] for o in outputs}) == 1
    assert len({o["response_sha256"] for o in outputs}) == 20  # timings differ; the text does not
    hits = ollama.generate_calls
    replayed = OllamaLLM(model="fixture:1", base_url=ollama.url, think=False, timeout=10,
                         transport=Recorder(store, mode="replay"))
    assert replayed.generate("same prompt") == texts.pop()
    assert ollama.generate_calls == hits  # the model was not called


def test_the_counter_sees_nondeterminism(ollama, tmp_path):
    ollama.nondeterministic = True
    store = InferenceStore(tmp_path / "inference.db")
    recorder = Recorder(store, mode="record")
    llm = OllamaLLM(model="fixture:1", base_url=ollama.url, think=False, timeout=10, transport=recorder)
    texts = [llm.generate("same prompt") for _ in range(5)]
    outputs = store.outputs(store.call(recorder.last_call_id)["cache_key"])
    assert len(set(texts)) == 5 and len({o["text_sha256"] for o in outputs}) == 5
    # The cached answer is the first recording, not the last.
    replayed = OllamaLLM(model="fixture:1", base_url=ollama.url, think=False, timeout=10,
                         transport=Recorder(store, mode="replay"))
    assert replayed.generate("same prompt") == texts[0]


def test_replay_miss_fails_closed_and_model_change_misses(ollama, tmp_path):
    store = InferenceStore(tmp_path / "inference.db")
    _llm(ollama, store, "record").generate("recorded prompt")
    hits = ollama.generate_calls
    replay = _llm(ollama, store, "replay")
    with pytest.raises(LLMError) as miss:
        replay.generate("never recorded")
    assert isinstance(miss.value.__cause__, ReplayMiss)
    ollama.blob = "ef" * 32  # same tag, different weights
    with pytest.raises(LLMError):
        _llm(ollama, store, "replay").generate("recorded prompt")
    assert ollama.generate_calls == hits
    assert [c["status"] for c in store.calls(2)] == ["replay_miss", "replay_miss"]


def test_offline_replay_serves_the_recording_and_says_identity_was_not_rechecked(ollama, tmp_path):
    store = InferenceStore(tmp_path / "inference.db")
    text = _llm(ollama, store, "record").generate("recorded prompt")
    url = ollama.url
    ollama.stop()
    offline = OllamaLLM(model="fixture:1", base_url=url, think=False, timeout=2,
                        transport=Recorder(store, mode="replay"))
    assert offline.generate("recorded prompt") == text
    manifest = store.calls(1)[0]["manifest"]
    assert manifest["status"] == "replayed" and manifest["runtime_verified"] is False
    assert manifest["facts_error"]
    # Offline, the model identity could not be re-read: the audit says so instead of passing it.
    assert "model.gguf_sha256" in missing_fields(manifest, "/api/generate")


def test_cache_mode_calls_once_then_serves(ollama, tmp_path):
    store = InferenceStore(tmp_path / "inference.db")
    llm = _llm(ollama, store, "cache")
    assert llm.generate("q") == llm.generate("q")
    assert ollama.generate_calls == 1
    assert [c["cache_hit"] for c in store.calls(2)] == [1, 0]


def test_record_mode_sends_one_request_at_a_time(ollama, tmp_path):
    ollama.delay = 0.05
    store = InferenceStore(tmp_path / "inference.db")
    llm = _llm(ollama, store, "record")
    threads = [threading.Thread(target=llm.generate, args=(f"q{i}",)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert ollama.generate_calls == 6 and ollama.max_active == 1


def test_record_mode_refuses_unseeded_sampling(ollama, tmp_path):
    recorder = Recorder(InferenceStore(tmp_path / "inference.db"), mode="record")
    body = json.dumps({"model": "fixture:1", "prompt": "x", "options": {"temperature": 0.8}}).encode()
    with pytest.raises(ValueError, match="temperature 0 or an explicit seed"):
        recorder(Request(ollama.url + "/api/generate", data=body, method="POST"), timeout=5)


def test_structured_output_keeps_every_invalid_attempt(ollama, tmp_path):
    ollama.invalid_first = 1
    store = InferenceStore(tmp_path / "inference.db")
    llm = _llm(ollama, store)
    schema = {"type": "object", "additionalProperties": False, "required": ["label"],
              "properties": {"label": {"type": "string", "enum": ["SUPPORTED", "NOT_SUPPORTED"]}}}
    value, history = generate_structured(llm, "Is it supported?", "", schema, attempts=3)
    assert value == {"label": "SUPPORTED"}
    assert [(h["seed"], h["valid"]) for h in history] == [(42, False), (43, True)]
    assert "not in enum" in history[0]["error"]
    group = store.call(history[0]["call_id"])["manifest"]["context"]["attempt_group"]
    rows = store.validations(group)
    assert [(r["attempt"], r["valid"]) for r in rows] == [(0, 0), (1, 1)]
    assert all(store.call(h["call_id"])["status"] == "called" for h in history)
    ollama.invalid_first = 99
    with pytest.raises(StructuredOutputError) as failed:
        generate_structured(llm, "Is it supported?", "", schema, attempts=2)
    assert [h["valid"] for h in failed.value.attempts] == [False, False]


def test_schema_subset_checker_fails_closed_on_unknown_keywords():
    assert check({"type": "object", "patternProperties": {}}, {}) != []
    assert check({"type": "integer"}, True) == ["$: expected integer"]
    assert check({"type": "object", "required": ["a"], "properties": {"a": {"type": "string", "minLength": 2}}},
                 {"a": "x"}) == ["$.a: shorter than minLength"]


def test_inference_records_are_append_only(ollama, tmp_path):
    store = InferenceStore(tmp_path / "inference.db")
    _llm(ollama, store, "record").generate("q")
    db = sqlite3.connect(store.path)
    for statement in ("UPDATE inference_calls SET status='x'", "DELETE FROM inference_cache",
                      "UPDATE inference_cache SET response=x'00'"):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(statement)
    db.close()


def test_settings_section_and_configured_llm(tmp_path, monkeypatch):
    config = tmp_path / "cain.toml"
    config.write_text('[llm]\nprovider = "ollama"\nmodel = "fixture:1"\n[storage]\npath = "state/cain.db"\n'
                      '[inference]\nmode = "cache"\n', encoding="utf-8")
    settings = load_settings(config)
    assert settings.inference_mode == "cache" and settings.inference_db == tmp_path / "state" / "inference.db"
    llm = configured_llm(settings)
    assert isinstance(llm.transport, Recorder) and llm.transport.mode == "cache"
    assert not settings.inference_db.exists()
    monkeypatch.setenv("CAIN_INFERENCE_MODE", "disabled")
    assert configured_llm(load_settings(config)).transport is None
    monkeypatch.setenv("CAIN_INFERENCE_MODE", "sometimes")
    with pytest.raises(ValueError):
        load_settings(config)
    config.write_text('[inference]\nmode = "record"\ncolour = "blue"\n', encoding="utf-8")
    monkeypatch.delenv("CAIN_INFERENCE_MODE")
    with pytest.raises(ValueError):
        load_settings(config)


def test_harness_is_frozen_and_scores_citations_literally(ollama, tmp_path):
    tasks, info = load_tasks()
    assert info["harness_sha256"] == HARNESS_V1_SHA256 and len(tasks) == 96
    families = [t["family"] for t in tasks]
    assert (families.count("evidence"), families.count("extraction"), families.count("verifiability")) == (48, 24, 24)
    extraction = next(t for t in tasks if t["id"] == "ex-en-01")
    assert score(extraction, {"answer": "1987", "quote": "opened in 1987"})["correct"] is True
    assert score(extraction, {"answer": "1987", "quote": "opened in the year 1987"})["correct"] is False
    assert score(extraction, {"answer": "1988", "quote": "opened in 1987"})["correct"] is False
    pt = next(t for t in tasks if t["id"] == "ex-pt-12")
    assert score(pt, {"answer": "Tres cidades", "quote": "abastece três cidades"})["correct"] is True
    store = InferenceStore(tmp_path / "inference.db")
    llm = OllamaLLM(model="fixture:1", base_url=ollama.url, think=False, timeout=10)
    result = run_model(llm, store, mode="record", limit=4)
    assert result["tasks_run"] == 4 and result["structured"]["first_attempt_valid"] == 4
    assert all(r["call_ids"][0] for r in result["rows"])
    hits = ollama.generate_calls
    replayed = run_model(llm, store, mode="replay", limit=4)
    assert ollama.generate_calls == hits
    assert [r["correct"] for r in replayed["rows"]] == [r["correct"] for r in result["rows"]]

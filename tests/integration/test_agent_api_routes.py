"""Agent API routes that had no direct test: job listing and control, provider failure
mapping, model inventory and streamed error events.

Protected behaviour: every route validates the scope first, provider failures during a
workflow step become HTTP 502 without completing the step, the model inventory only
comes from a loopback Ollama and is size-bounded, and a failing stream ends with an
explicit ``error`` event instead of a partial answer presented as complete.
"""
import base64
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
import test_research_l0 as cases
from test_agent_capabilities import FixtureModel

setup = cases.setup


def png_1x1():
    PIL = pytest.importorskip("PIL.Image")
    buffer = io.BytesIO()
    PIL.new("RGB", (1, 1)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def client(setup, tmp_path):
    service, scope, ingest, _, policy = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))
    app = create_app(tmp_path / "workspace.db", llm=FixtureModel(), research_policy=policy,
                     research_db=service.path, trusted_hosts=("testserver",))
    with TestClient(app) as client:
        yield client


@pytest.fixture
def fake_ollama():
    class Handler(BaseHTTPRequestHandler):
        tags = {"models": [{"name": "qwen3.5:4b", "digest": "d1", "size": 1, "capabilities": ["completion"]}]}
        generate_status = 500

        def do_GET(self):
            body = json.dumps(self.tags).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(self.generate_status)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", Handler
    finally:
        server.shutdown()
        server.server_close()


def ollama_client(tmp_path, base_url, policy, research_db):
    config = tmp_path / "ollama.toml"
    config.write_text(f'[llm]\nprovider="ollama"\nmodel="qwen3.5:4b"\nbase_url="{base_url}"\nallow_remote=true\n[search]\npaths=[]\n'
                      'allow_public_urls=false\n[orchestration]\nllm_routing=false\n', encoding="utf-8")
    return TestClient(create_app(tmp_path / "w.db", config_path=config, research_policy=policy,
                                 research_db=research_db, trusted_hosts=("testserver",)))


def test_job_listing_trace_cancel_and_abstain(client):
    created = client.post("/research/jobs", json={"question": "A?", "steps": ["inspect", "search"]}).json()
    run_id = created["id"]
    listed = client.post("/research/jobs/list", json={}).json()
    assert [job["id"] for job in listed] == [run_id]
    assert client.post("/research/jobs/list", json={"project_id": "project-a"}).status_code == 400
    assert client.post(f"/research/jobs/{run_id}/advance", json={}).json()["status"] == "ready"
    trace = client.post(f"/research/jobs/{run_id}/trace", json={}).json()
    assert "resourceSpans" in trace and "inspect" in json.dumps(trace)
    assert client.post(f"/research/jobs/{run_id}/cancel", json={}).json()["status"] == "cancelled"
    other = client.post("/research/jobs", json={"question": "B?", "steps": ["inspect"]}).json()["id"]
    assert client.post(f"/research/jobs/{other}/abstain", json={"reason": "nothing failed"}).status_code == 400
    assert client.post(f"/research/jobs/{other}/abstain", json={}).status_code == 422
    assert client.post("/research/jobs/missing/trace", json={}).status_code == 400
    assert client.post(f"/research/jobs/{run_id}/read", json={"collection": "other"}).status_code == 400


def test_provider_failure_during_generation_step_is_a_502_and_step_stays_incomplete(setup, tmp_path):
    service, _, ingest, _, policy = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))

    class Exploding(FixtureModel):
        def generate_json(self, *args):
            raise OSError("provider socket closed")

    app = create_app(tmp_path / "w.db", llm=Exploding(), research_policy=policy,
                     research_db=service.path, trusted_hosts=("testserver",))
    with TestClient(app) as client:
        run_id = client.post("/research/jobs", json={"question": "A?", "steps": ["inspect", "entities"]}).json()["id"]
        assert client.post(f"/research/jobs/{run_id}/advance", json={}).json()["status"] == "ready"
        assert client.post(f"/research/jobs/{run_id}/advance", json={}).json()["status"] == "awaiting_generation_approval"
        response = client.post(f"/research/jobs/{run_id}/advance", json={"approve_generation": True})
        assert response.status_code == 502
        assert response.json()["detail"] == "Provider failed; workflow step was not completed"
        job = client.post(f"/research/jobs/{run_id}/read", json={}).json()
        assert job["status"] != "completed"


def test_model_inventory_requires_loopback_provider_and_bounds_its_size(setup, tmp_path, fake_ollama):
    service, _, _, _, policy = setup
    base_url, handler = fake_ollama
    with ollama_client(tmp_path, base_url, policy, service.path) as client:
        listed = client.get("/assistant/models").json()
        assert listed["configured"] == "qwen3.5:4b" and listed["inference"] == "not_probed"
        assert listed["models"] == [{"name": "qwen3.5:4b", "digest": "d1", "size": 1, "capabilities": ["completion"]}]
        handler.tags = {"models": [{"name": "m" * 1_000_001}]}
        assert client.get("/assistant/models").status_code == 400
    with ollama_client(tmp_path, "http://models.invalid", policy, service.path) as remote:
        response = remote.get("/assistant/models")
        assert response.status_code == 400 and "loopback" in response.json()["detail"]


def test_stream_model_selection_images_and_error_event(setup, tmp_path, fake_ollama):
    service, _, _, _, policy = setup
    base_url, handler = fake_ollama
    with ollama_client(tmp_path, base_url, policy, service.path) as client:
        assert client.post("/assistant/stream", json={"prompt": "hi", "model": "not-installed"}).status_code == 400
        assert client.post("/assistant/stream", json={"prompt": "hi", "images": ["not base64!"]}).status_code == 400
        for body in ({"prompt": "hi", "model": "qwen3.5:4b"}, {"prompt": "describe", "images": [png_1x1()]}):
            response = client.post("/assistant/stream", json=body)
            assert response.status_code == 200
            events = [json.loads(line) for line in response.text.splitlines() if line]
            assert events[0]["type"] == "started" and events[0]["memory_written"] is False
            assert events[-1]["type"] == "error"
            assert "partial tokens are not a completed answer" in events[-1]["message"]
        assert events[0]["model"] == "qwen3.5:0.8b", "images without a model select the vision model"


def test_abstention_is_only_accepted_after_a_failed_generation(setup, tmp_path):
    service, _, ingest, _, policy = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))

    class Garbled(FixtureModel):
        def generate_json(self, *args):
            return "not json at all"

    app = create_app(tmp_path / "w.db", llm=Garbled(), research_policy=policy,
                     research_db=service.path, trusted_hosts=("testserver",))
    with TestClient(app) as client:
        run_id = client.post("/research/jobs", json={"question": "A?", "steps": ["inspect", "entities"]}).json()["id"]
        client.post(f"/research/jobs/{run_id}/advance", json={})
        client.post(f"/research/jobs/{run_id}/advance", json={})
        failed = client.post(f"/research/jobs/{run_id}/advance", json={"approve_generation": True})
        assert failed.status_code == 400  # ValueError from the garbled review is a client-visible failure
        assert client.post(f"/research/jobs/{run_id}/read", json={}).json()["status"] == "failed"
        abstained = client.post(f"/research/jobs/{run_id}/abstain", json={"reason": "model output unusable"}).json()
        assert abstained["status"] == "completed"
        assert abstained["steps"][-1]["result"] == {"status": "abstained_by_operator", "reason": "model output unusable",
                                                     "model_calls": 0, "accepted_model_output": False,
                                                     "previous_failure_retained": True}

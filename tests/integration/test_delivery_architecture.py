"""Durable API completion, replay boundaries, and profile composition regressions."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
from cain.cli import main
from cain.common import Signal
from cain.runtime import build_cain
from cain.llm import FakeLLM
from cain.persistence.adapters import SQLiteIdentityStore, SQLiteDecisionLog
from cain.workspace import WorkspaceStore


class CountingLLM:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt, context=""):
        self.calls += 1
        return "Uma resposta preservada."


def request(**extra):
    return {"user_id": "leo", "session_id": "s", "project_id": None,
            "payload": "Prefiro respostas curtas. Resuma este texto.", "intent": "resumo",
            "run_id": "stable-request", "preference_scope": None, **extra}


def counts(path):
    with sqlite3.connect(path) as db:
        return {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("identity_signals", "identity_snapshots", "decisions", "ui_turns")}


@pytest.mark.parametrize("after_commit", [False, True])
def test_history_failure_reopens_and_replays_without_generation_or_identity_duplication(tmp_path, monkeypatch, after_commit):
    path = tmp_path / "db.sqlite"
    model = CountingLLM()
    original = WorkspaceStore.record_turn
    def fail(self, *args, **kwargs):
        if after_commit:
            original(self, *args, **kwargs)
        raise OSError("history write interrupted")
    with monkeypatch.context() as patch:
        patch.setattr(WorkspaceStore, "record_turn", fail)
        with TestClient(create_app(path, model)) as client:
            response = client.post("/run", json=request())
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["history_status"] == "pending"
            before = counts(path)
            assert before["ui_turns"] == int(after_commit)
    with TestClient(create_app(path, model)) as reopened:
        result["history_status"] = "saved"
        assert reopened.get("/runs/leo/stable-request").json() == result
        assert reopened.post("/run", json=request()).json() == result
        assert reopened.post("/run", json=request(payload="Different")).status_code == 400
        assert reopened.post("/run", json=request(session_id="other")).status_code == 400
        assert reopened.get("/runs/other/stable-request").status_code == 400
        turns = reopened.get("/sessions/leo/s").json()
        assert len(turns) == 1 and turns[0]["result"]["response"] == result["response"]
        after = counts(path)
        assert {**before, "ui_turns": 1} == after
        assert model.calls == 1


def test_conversation_read_recovers_missing_projection(tmp_path, monkeypatch):
    path = tmp_path / "db.sqlite"
    model = CountingLLM()
    with monkeypatch.context() as patch:
        patch.setattr(WorkspaceStore, "record_turn", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
        with TestClient(create_app(path, model)) as client:
            assert client.post("/run", json=request()).json()["history_status"] == "pending"
    with TestClient(create_app(path, model)) as client:
        assert len(client.get("/sessions/leo/s").json()) == 1
        assert len(client.get("/sessions/leo/s").json()) == 1
    assert model.calls == 1


def test_completion_and_outcome_roll_back_together(tmp_path):
    path = tmp_path / "db.sqlite"
    model = CountingLLM()
    app = create_app(path, model)
    log = SQLiteDecisionLog(path)
    log.close()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER fail_completion BEFORE INSERT ON decisions "
                   "WHEN json_extract(NEW.record_json,'$.status')='completed' "
                   "BEGIN SELECT RAISE(ABORT,'injected commit failure'); END")
    with TestClient(app) as client:
        assert client.post("/run", json=request()).status_code == 503
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT status,result_json FROM run_receipts").fetchone()
        assert row == ("failed", None)
        events = [json.loads(r[0])["status"] for r in db.execute("SELECT record_json FROM decisions")]
        assert events == ["mediated", "failed"]
        db.execute("DROP TRIGGER fail_completion")
    before = counts(path)
    with TestClient(create_app(path, model)) as reopened:
        assert reopened.post("/run", json=request()).status_code == 409
        assert reopened.get("/runs/leo/stable-request").status_code == 409
    assert counts(path) == before and model.calls == 1


def test_abandoned_processing_receipt_is_not_silently_reexecuted(tmp_path):
    path = tmp_path / "db.sqlite"
    store = WorkspaceStore(path)
    store.ensure_session("leo", "s")
    assert store.claim_run(request()) is None
    model = CountingLLM()
    with TestClient(create_app(path, model)) as client:
        assert client.post("/run", json=request()).status_code == 409
    assert model.calls == 0


def test_two_app_instances_cannot_generate_the_same_receipt(tmp_path):
    path = tmp_path / "db.sqlite"
    entered, release = Event(), Event()
    class BlockingLLM(CountingLLM):
        def generate(self, prompt, context=""):
            entered.set()
            assert release.wait(10)
            return super().generate(prompt, context)
    model = BlockingLLM()
    with TestClient(create_app(path, model)) as first, TestClient(create_app(path, model)) as second:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(first.post, "/run", json=request())
            try:
                assert entered.wait(10)
                assert second.post("/run", json=request()).status_code == 409
            finally:
                release.set()
            result = future.result().json()
        assert second.post("/run", json=request()).json() == result
    assert model.calls == 1


def test_profile_controls_and_cli_do_not_read_historical_documents(tmp_path, monkeypatch, capsys):
    path = tmp_path / "db.sqlite"
    with build_cain(path, FakeLLM()) as runtime:
        for _ in range(500):
            runtime.identity.update("other", Signal("Histórico de outro perfil"))
    def forbidden(*args, **kwargs):
        raise AssertionError("Profile operation scanned historical memory")
    monkeypatch.setattr(SQLiteIdentityStore, "iter_documents", forbidden)
    with TestClient(create_app(path, CountingLLM())) as client:
        assert client.get("/profile/leo").status_code == 200
        changed = client.put("/profile/leo/preferences/format", json={"value": "bullets"})
        assert changed.json()["profile"]["effective_preferences"]["format"] == "bullets"
        assert client.delete("/profile/leo/preferences/format").status_code == 200
        assert client.delete("/profile/leo/preferences").status_code == 200
    assert main(["profile", "--db", str(path), "--user", "leo"]) == 0
    assert json.loads(capsys.readouterr().out)["effective_preferences"] == {}

@pytest.mark.parametrize("checkpoint", ["before_completion", "after_completion", "after_history"])
def test_abrupt_process_exit_preserves_commit_boundary(tmp_path, checkpoint):
    import subprocess
    import sys
    path = tmp_path / "crash.db"
    script = r'''
import json, os, sys
from fastapi.testclient import TestClient
from cain.api import create_app
from cain.workspace import WorkspaceStore
from cain.persistence.adapters import SQLiteDecisionLog
class Provider:
    def generate(self, prompt, context=""):
        return "Survives process exit"
checkpoint = sys.argv[2]
if checkpoint == "before_completion":
    SQLiteDecisionLog.append_with_outcome = lambda *a, **k: os._exit(73)
else:
    original = WorkspaceStore.record_turn
    def interrupted(self, *args, **kwargs):
        if checkpoint == "after_history":
            original(self, *args, **kwargs)
        os._exit(73)
    WorkspaceStore.record_turn = interrupted
with TestClient(create_app(sys.argv[1], Provider())) as client:
    client.post("/run", json=json.loads(sys.argv[3]))
'''
    process = subprocess.run([sys.executable, "-c", script, str(path), checkpoint, json.dumps(request())],
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == 73, process.stderr
    with sqlite3.connect(path) as db:
        completed = db.execute("SELECT count(*) FROM decisions WHERE "
                               "json_extract(record_json,'$.status')='completed'").fetchone()[0]
        assert completed == int(checkpoint != "before_completion")
    before = counts(path)
    model = CountingLLM()
    with TestClient(create_app(path, model)) as client:
        response = client.post("/run", json=request())
        if checkpoint == "before_completion":
            assert response.status_code == 409
            assert counts(path) == before
        else:
            assert response.status_code == 200, response.text
            assert response.json()["response"] == "Survives process exit"
            assert {**before, "ui_turns": 1} == counts(path)
            assert len(client.get("/sessions/leo/s").json()) == 1
    assert model.calls == 0

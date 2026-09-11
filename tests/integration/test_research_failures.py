"""Crash/audit boundaries on disposable SQLite and Windows launcher regression."""

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from research_snapshot import loads

import test_research_l0 as cases

publication = cases.publication
setup = cases.setup


def test_process_failure_retains_separate_receipt(setup, monkeypatch):
    service, scope, ingest, _, _ = setup

    def fail(*args):
        raise OSError("simulated interruption before commit")

    monkeypatch.setattr(service, "_project", fail)
    with pytest.raises(ValueError, match="process_failed"):
        ingest(publication())
    assert service.receipts(scope)[0]["status"] == "process_failed"
    with sqlite3.connect(service.path) as db:
        assert db.execute("SELECT count(*) FROM publications").fetchone()[0] == 0


def test_failure_audit_unavailable_is_reported(setup, monkeypatch):
    service, scope, ingest, _, _ = setup
    original = service.connection
    calls = 0

    def fail_connection():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise sqlite3.OperationalError("audit unavailable")
        return original()

    def fail(*args):
        raise OSError("interruption")

    monkeypatch.setattr(service, "connection", fail_connection)
    monkeypatch.setattr(service, "_project", fail)
    with pytest.raises(RuntimeError, match="NO DURABLE FAILURE RECEIPT"):
        ingest(publication())


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1,"a":2}', b'{"a":NaN}', b"[" * 1000 + b"0" + b"]" * 1000, b"x" * 2_000_001],
    ids=["duplicate-key", "nonfinite", "depth-limit", "byte-limit"],
)
def test_transport_limits_and_duplicate_json(raw):
    with pytest.raises(ValueError):
        loads(raw)


def test_publication_metadata_corruption_is_not_authority(setup):
    service, scope, ingest, _, _ = setup
    ingest(publication())
    with sqlite3.connect(service.path) as db:
        row = db.execute("SELECT origin FROM publications").fetchone()[0]
        origin = json.loads(row)
        origin["code_revision"] = "tampered"
        db.execute("UPDATE publications SET origin=?", (json.dumps(origin),))
    with pytest.raises(ValueError, match="metadata corrupt"):
        service.query(scope)


def test_online_backup_sees_committed_snapshot_with_active_wal_writer(setup, tmp_path):
    service, scope, ingest, _, _ = setup
    ingest(publication())
    writer = sqlite3.connect(service.path)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO queries VALUES(?,?,?,?,?)", ("pending", scope, "now", "{}", "{}"))
        backup = tmp_path / "active-wal-backup.db"
        service.backup(backup)
        writer.commit()
        with sqlite3.connect(backup) as restored:
            assert restored.execute("SELECT count(*) FROM publications").fetchone()[0] == 1
            assert restored.execute("SELECT count(*) FROM queries WHERE id='pending'").fetchone()[0] == 0
        assert writer.execute("SELECT count(*) FROM queries WHERE id='pending'").fetchone()[0] == 1
    finally:
        writer.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows launcher only")
def test_api_launcher_does_not_prepare_ollama(tmp_path):
    root = tmp_path / "launcher"
    (root / "scripts").mkdir(parents=True)
    script = Path(__file__).resolve().parents[2] / "scripts/start-cain.ps1"
    (root / "scripts/start-cain.ps1").write_bytes(script.read_bytes())
    fake_python = root / "python.cmd"
    fake_python.write_text("@echo off\necho LOCAL_API_WITHOUT_PROVIDER\nexit /b 0\n")
    (root / ".cain.local.json").write_text(json.dumps({"python": str(fake_python)}))
    harness = root / "harness.ps1"
    harness.write_text(
        "function Invoke-RestMethod { throw 'Provider probing forbidden' }\n"
        "function Start-Process { throw 'Provider startup forbidden' }\n"
        "& (Join-Path $PSScriptRoot 'scripts/start-cain.ps1') -Mode api\n"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "LOCAL_API_WITHOUT_PROVIDER" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows launcher only")
def test_windows_launcher_refuses_other_service_without_stopping_it(tmp_path):
    class OtherService(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                b'{"version":"0.3.0","research_status":"provisional","service":"other"}'
            )

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), OtherService)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        root = tmp_path / "launcher-conflict"
        (root / "scripts").mkdir(parents=True)
        original = Path(__file__).resolve().parents[2] / "scripts/start-cain.ps1"
        script = root / "scripts/start-cain.ps1"
        script.write_bytes(original.read_bytes())
        (root / ".cain.local.json").write_text(json.dumps({"python": sys.executable}))
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Mode",
                "web",
                "-NoBrowser",
                "-Port",
                str(server.server_port),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Another service" in result.stderr
        assert worker.is_alive()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)

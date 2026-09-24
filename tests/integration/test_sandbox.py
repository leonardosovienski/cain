"""Sandbox for model-generated code: hardening flags, reward-hacking guards, and (with a real engine) attacks."""

import json
import os
from pathlib import Path
import sys

import pytest

from cain.sandbox.attempt import integrity, run_attempt, safe_read
from cain.sandbox.runner import DockerSandbox, SandboxPolicy

HERE = Path(__file__).resolve().parent
IMAGE = "python:3.13-slim@sha256:" + "a" * 64


@pytest.fixture
def fake(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_DOCKER_STATE", str(tmp_path / "docker-state"))
    monkeypatch.setenv("FAKE_DOCKER_LOG", str(tmp_path / "docker.log"))
    monkeypatch.setenv("FAKE_DOCKER_IMAGE", IMAGE)
    evaluator = tmp_path / "evaluator" / "evaluator.py"
    evaluator.parent.mkdir()
    evaluator.write_text("def score(x):\n    return x\n", encoding="utf-8")
    return tmp_path, evaluator


def sandbox(timeout=20.0):
    return DockerSandbox(SandboxPolicy(image=IMAGE, timeout=timeout), docker=[sys.executable, str(HERE / "fake_docker.py")])


def candidate(tmp_path, source, name="cand"):
    directory = tmp_path / name
    directory.mkdir()
    (directory / "candidate.py").write_text(source, encoding="utf-8")
    return directory


def calls(tmp_path):
    return [json.loads(line) for line in (tmp_path / "docker.log").read_text().splitlines()]


def test_every_attempt_runs_with_the_hardening_flags_and_only_its_workspace():
    box = DockerSandbox(SandboxPolicy(image=IMAGE, memory="256m", runtime="runsc"), path_mapper=lambda p: f"/mapped{p}")
    args = box.command("c1", Path("/ws/a1"), ["python", "candidate.py"], data_ro=[(Path("/allowed"), "/data")])
    joined = " ".join(args)
    for flag in ("--network none", "--read-only", "--user 65534:65534", "--cap-drop ALL",
                 "--security-opt no-new-privileges", "--pids-limit 128", "--memory 256m", "--memory-swap 256m",
                 "--runtime runsc", "-v /mapped/ws/a1:/workspace:rw", "-v /mapped/allowed:/data:ro"):
        assert flag in joined
    assert "/tmp:rw,noexec,nosuid" in joined
    mounts = [args[i + 1] for i, a in enumerate(args) if a == "-v"]
    assert mounts == ["/mapped/ws/a1:/workspace:rw", "/mapped/allowed:/data:ro"]  # nothing else is mounted
    assert args[-3:] == [IMAGE, "python", "candidate.py"]


def test_benign_attempt_is_valid_and_its_manifest_records_image_and_file_log(fake):
    tmp_path, evaluator = fake
    source = ('import json\njson.dump({"rps": 0.2093}, open("output.json", "w"))\n'
              'open("report.md", "w").write("RPS 0.2093 on the walk-forward.\\n")\n')
    manifest = run_attempt(sandbox(), candidate(tmp_path, source), evaluator_files=[evaluator],
                           workspace_root=tmp_path)
    assert manifest["verdict"] == "VALID" and manifest["problems"] == []
    assert manifest["image"]["id"] == "sha256:" + "f" * 64 and manifest["image"]["repo_digests"]
    assert manifest["run"]["file_log"]["created"] == ["output.json", "report.md"]
    assert manifest["evaluator"]["unchanged"] and manifest["integrity"]["ok"]


def test_a_report_with_numbers_the_run_did_not_produce_is_rejected(fake):
    tmp_path, evaluator = fake
    source = ('import json\njson.dump({"rps": 0.2093, "baseline_rps": 0.2234}, open("output.json", "w"))\n'
              'open("report.md", "w").write("RPS 0.1812, far below the baseline 0.2234.\\n")\n')
    manifest = run_attempt(sandbox(), candidate(tmp_path, source), evaluator_files=[evaluator],
                           workspace_root=tmp_path)
    assert manifest["verdict"] == "INVALID" and manifest["integrity"]["unsupported"] == ["0.1812"]
    assert integrity("mean 3", '{"mean": 3.0}')["ok"]


def test_a_planted_symlink_is_never_followed(fake):
    tmp_path, evaluator = fake
    source = (f'import json, os\nos.symlink({str(evaluator)!r}, "report.md")\n'
              'json.dump({"rps": 1}, open("output.json", "w"))\n')
    manifest = run_attempt(sandbox(), candidate(tmp_path, source), evaluator_files=[evaluator],
                           workspace_root=tmp_path)
    assert manifest["verdict"] == "INVALID" and "symlink" in manifest["outputs"]["report"]
    assert manifest["run"]["file_log"]["symlinks"] == ["report.md"]
    text, problem = safe_read(Path(manifest["workspace"]), "report.md")
    assert text is None and "symlink" in problem


def test_timeout_kills_the_attempt_and_records_a_crash(fake):
    tmp_path, evaluator = fake
    manifest = run_attempt(sandbox(timeout=1.0), candidate(tmp_path, "while True:\n    pass\n"),
                           evaluator_files=[evaluator], workspace_root=tmp_path)
    assert manifest["run"]["status"] == "TIMEOUT" and manifest["verdict"] == "CRASH"
    assert manifest["run"]["exit_code"] == 137
    assert any(c[0] == "kill" for c in calls(tmp_path)) and any(c[0] == "rm" for c in calls(tmp_path))


def test_an_evaluator_change_during_the_attempt_is_invalid_with_an_alert(fake):
    tmp_path, evaluator = fake
    inner = sandbox()

    class Tampered:
        def image_identity(self):
            return inner.image_identity()

        def run(self, workspace, argv, data_ro=()):
            out = inner.run(workspace, argv, data_ro=data_ro)
            evaluator.write_text("def score(x):\n    return 1.0  # always the best\n", encoding="utf-8")
            return out

    source = 'import json\njson.dump({"rps": 0.2}, open("output.json", "w"))\n'
    manifest = run_attempt(Tampered(), candidate(tmp_path, source), evaluator_files=[evaluator],
                           workspace_root=tmp_path)
    assert manifest["verdict"] == "INVALID"
    assert manifest["alerts"] == [{"alert": "EVALUATOR_CHANGED", "files": [str(evaluator)]}]


def test_an_attempt_without_output_proves_nothing(fake):
    tmp_path, evaluator = fake
    manifest = run_attempt(sandbox(), candidate(tmp_path, "print('done')\n"), evaluator_files=[evaluator],
                           workspace_root=tmp_path)
    assert manifest["verdict"] == "INVALID" and manifest["problems"] == ["output.json missing"]


@pytest.mark.skipif(not os.getenv("CAIN_TEST_DOCKER"), reason="needs a real docker engine (CAIN_TEST_DOCKER)")
def test_attacks_against_a_real_engine(tmp_path):
    from cain.sandbox.attacks import run_attacks, summarize

    evaluator = tmp_path / "evaluator.py"
    evaluator.write_text("def score(x):\n    return x\n", encoding="utf-8")
    holdout = tmp_path / "holdout.csv"
    holdout.write_text("value\n42\n", encoding="utf-8")
    allowed = tmp_path / "allowed" / "allowed.csv"
    allowed.parent.mkdir()
    allowed.write_text("value\n1\n2\n3\n", encoding="utf-8")
    box = DockerSandbox(SandboxPolicy(image=os.environ["CAIN_TEST_DOCKER_IMAGE"], timeout=20.0),
                        docker=os.environ["CAIN_TEST_DOCKER"])
    report = run_attacks(box, evaluator_files=[evaluator], holdout_files=[holdout], allowed_data=allowed,
                         workspace_root=tmp_path)
    rows = {r["attack"]: r for r in summarize(report)}
    assert all(r["blocked"] for r in rows.values())
    assert rows["benign_candidate"]["verdict"] == "VALID"
    assert rows["infinite_loop"]["status"] == "TIMEOUT"
    assert evaluator.read_text() == "def score(x):\n    return x\n"

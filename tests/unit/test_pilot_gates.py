"""Process gates of the pilot line (programme items H05, H06, H07) behave fail-closed and never edit inputs."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "pilots" / "elicitation-a"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PILOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


freeze_gate = _load("freeze_gate")
completeness_gate = _load("completeness_gate")
rubric_layers = _load("rubric_layers")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _repo_with_frozen_dir(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = tmp_path / "repo"
    frozen = repo / "exp" / "frozen"
    frozen.mkdir(parents=True)
    # write_bytes: the manifest records sha256 of these exact bytes; write_text would turn "\n" into "\r\n" on
    # Windows and the gate would (correctly) fail closed on a hash mismatch (cain main run 37653818187).
    (frozen / "prompt.txt").write_bytes(b"frozen prompt\n")
    (frozen / "nested").mkdir()
    (frozen / "nested" / "cases.json").write_bytes(b"[]")
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "root")
    manifest = {
        "schema": "test-freeze/1",
        "files_sha256": {
            "prompt.txt": hashlib.sha256(b"frozen prompt\n").hexdigest(),
            "nested/cases.json": hashlib.sha256(b"[]").hexdigest(),
        },
    }
    (frozen / "FREEZE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "freeze")
    freeze_sha = _git(repo, "rev-parse", "HEAD")
    manifest["freeze_sha"] = freeze_sha
    (frozen / "FREEZE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "register freeze sha")
    return repo, frozen, _git(repo, "rev-parse", "HEAD")


def test_freeze_gate_passes_on_the_registered_commit_and_on_untouched_later_commits(tmp_path: Path):
    repo, frozen, registered = _repo_with_frozen_dir(tmp_path)
    manifest = json.loads((frozen / "FREEZE_MANIFEST.json").read_text())
    manifest["freeze_sha"] = registered
    (frozen / "FREEZE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "final registration")
    final = _git(repo, "rev-parse", "HEAD")
    assert freeze_gate.gate(frozen, final, None, False)["status"] == "PASS"
    (repo / "README.md").write_text("docs only\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "docs")
    later = _git(repo, "rev-parse", "HEAD")
    report = freeze_gate.gate(frozen, later, None, False)
    assert report["status"] == "PASS" and report["checks"]["run_sha_equals_freeze_sha"] is False


def test_freeze_gate_fails_closed_when_a_frozen_file_changes_after_the_freeze(tmp_path: Path):
    repo, frozen, registered = _repo_with_frozen_dir(tmp_path)
    (frozen / "prompt.txt").write_bytes(b"edited after freeze\n")
    report = freeze_gate.gate(frozen, registered, None, False)
    assert report["status"] == "FAIL_CLOSED"
    assert any("differ from the manifest" in r for r in report["reasons"])


def test_freeze_gate_fails_closed_without_manifest_or_run_sha(tmp_path: Path):
    repo, frozen, registered = _repo_with_frozen_dir(tmp_path)
    assert freeze_gate.gate(frozen, None, None, False)["status"] == "FAIL_CLOSED"
    (frozen / "FREEZE_MANIFEST.json").unlink()
    assert freeze_gate.gate(frozen, registered, None, False)["status"] == "FAIL_CLOSED"


def test_historical_v3_run_commit_differs_from_its_freeze_commit_only_in_the_manifest():
    """Retro layer (2026-10-07): V3 ran on d72ed88, two commits after the freeze; the frozen files were byte-identical,
    only FREEZE_MANIFEST.json (a note and the workflow hash) changed. The gate records both facts."""
    layer = json.loads((PILOT / "v3" / "runs" / "FREEZE_GATE_RETRO_V3.json").read_text(encoding="utf-8"))
    assert layer["status"] == "PASS"
    assert layer["run_sha"].startswith("d72ed88")
    assert layer["checks"]["run_sha_equals_freeze_sha"] is False
    assert layer["checks"]["paths_changed_since_freeze_commit"] == ["pilots/elicitation-a/v3/frozen/FREEZE_MANIFEST.json"]


def test_completeness_gate_reports_missing_predeclared_outputs(tmp_path: Path):
    analysis = tmp_path / "analysis.json"
    analysis.write_text(json.dumps({"readings": {"a": "x"}, "cells": {}}), encoding="utf-8")
    spec = tmp_path / "REQUIRED_OUTPUTS.json"
    spec.write_text(json.dumps({"schema": "required-outputs/1", "design": "D.md", "analysis_artifact": "analysis.json",
                                "required": [{"id": "a", "path": "readings.a"}, {"id": "b", "path": "readings.b"}, {"id": "cells", "path": "cells"}]}))
    report = completeness_gate.gate(spec, None)
    assert report["status"] == "INCOMPLETE" and report["missing"] == ["b"] and report["produced"] == ["a", "cells"]


def test_v3_completeness_layer_records_the_missing_t6_circumvention_count():
    report = completeness_gate.gate(PILOT / "v3" / "REQUIRED_OUTPUTS.json", None)
    assert report["status"] == "INCOMPLETE"
    assert report["missing"] == ["reading_3_t6_circumvention_count"]
    stored = json.loads((PILOT / "v3" / "runs" / "COMPLETENESS_V3.json").read_text(encoding="utf-8"))
    assert stored["missing"] == report["missing"]


def test_rubric_layers_are_append_only_and_detect_modified_originals(tmp_path: Path):
    run = tmp_path / "run"
    (run / "rubric_v2").mkdir(parents=True)
    (run / "labels.jsonl").write_text('{"episode_id": "e1", "status": "VALID"}\n{"episode_id": "e2", "status": "INVALID"}\n', encoding="utf-8")
    (run / "rubric_v2" / "labels.jsonl").write_text('{"episode_id": "e1", "label": "EVENT"}\n', encoding="utf-8")
    rubric_layers.register(run, run / "labels.jsonl", run / "rubric_v2" / "labels.jsonl", "2.1", "test", "2026-10-07", "none", "episode_id", "status", "label")
    rows = [json.loads(line) for line in (run / "layers" / "rubric_2.1_labels.jsonl").read_text().splitlines()]
    assert rows[0]["ORIGINAL_LABEL"] == "VALID" and rows[0]["DERIVED_LABEL"] == "EVENT"
    assert rows[1]["DERIVED_LABEL"] is None and rows[1]["derived_present"] is False
    assert rubric_layers.check(run) == []
    with pytest.raises(SystemExit):
        rubric_layers.register(run, run / "labels.jsonl", run / "rubric_v2" / "labels.jsonl", "2.1", "again", "2026-10-07", "none", "episode_id", "status", "label")
    (run / "labels.jsonl").write_text('{"episode_id": "e1", "status": "CHANGED"}\n', encoding="utf-8")
    assert any("original file changed" in p for p in rubric_layers.check(run))


def test_v3_label_layers_are_registered_and_intact():
    for arm in ("q0", "q1"):
        run = PILOT / "v3" / "runs" / f"v3{arm}-qwen2.5-7b-instruct-q4_K_M-gha37552078241-a1"
        assert rubric_layers.check(run) == [], arm

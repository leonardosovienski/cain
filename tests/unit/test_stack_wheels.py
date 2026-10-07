"""The stack-wheel registry is the only source of the predictor-research-* wheels (R01, 2026-10-07).

Protected behaviour (offline, no GitHub access):
* ``STACK_WHEELS.json`` is well formed, every entry is a wheel of ``ecosystem-predictor-cain`` and no entry
  points to a retired repository name (the 2026-10-05 rename made ``ecosystem-predictor`` a different project);
* ``pyproject.toml`` and ``uv.lock`` pin exactly the registered versions to the local flat index and carry no
  ``releases/download`` URL (the class of pin that broke after the rename and the privatisation);
* ``tools/stack_wheels.py check`` fails when a wheel in the index does not match the registry sha256;
* ``requirements`` rewrites a ``uv export`` file so ``pip --require-hashes`` can verify the stack lines.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("stack_wheels", ROOT / "tools" / "stack_wheels.py")
stack_wheels = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(stack_wheels)


def test_registry_is_well_formed_and_names_the_renamed_producer():
    registry = stack_wheels.load_registry(ROOT)
    assert registry["index_dir"] == ".stack-wheels"
    names = {entry["package"] for entry in registry["wheels"]}
    assert names == {
        "predictor-research-snapshot",
        "predictor-research-bundle",
        "predictor-research-protocol",
        "predictor-research-transport",
    }
    for entry in registry["wheels"]:
        assert entry["repository"] == "leonardosovienski/ecosystem-predictor-cain"
        assert entry["asset"].startswith(entry["package"].replace("-", "_") + "-" + entry["version"] + "-")
    assert "leonardosovienski/ecosystem-predictor" in registry["retired_repositories"]


def test_pyproject_and_lock_pin_the_registry_not_release_urls():
    registry = stack_wheels.load_registry(ROOT)
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    flat = [i for i in pyproject["tool"]["uv"]["index"] if i.get("format") == "flat"]
    assert [i["url"] for i in flat] == [".stack-wheels"]
    declared = {
        dep.split("==")[0]: dep.split("==")[1]
        for dep in pyproject["project"]["dependencies"]
        if dep.startswith("predictor-research-")
    }
    assert declared == {entry["package"]: entry["version"] for entry in registry["wheels"]}
    lock_text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert "releases/download" not in lock_text
    assert "releases/download" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    packages = {p["name"]: p for p in tomllib.loads(lock_text)["package"]}
    for entry in registry["wheels"]:
        package = packages[entry["package"]]
        assert package["version"] == entry["version"]
        assert package["source"] == {"registry": ".stack-wheels"}
        assert [w["path"] for w in package["wheels"]] == [entry["asset"]]


def _project_copy(tmp_path: Path, registry: dict) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "STACK_WHEELS.json").write_text(json.dumps(registry), encoding="utf-8")
    shutil.copy(ROOT / "pyproject.toml", project / "pyproject.toml")
    shutil.copy(ROOT / "uv.lock", project / "uv.lock")
    return project


def test_check_rejects_a_wheel_whose_sha256_differs_from_the_registry(tmp_path: Path):
    registry = stack_wheels.load_registry(ROOT)
    project = _project_copy(tmp_path, registry)
    index = project / ".stack-wheels"
    index.mkdir()
    for entry in registry["wheels"]:
        (index / entry["asset"]).write_bytes(b"not the published wheel")
    with pytest.raises(stack_wheels.StackError, match="sha256 differs"):
        stack_wheels.check(project)


def test_check_accepts_an_index_that_matches_the_registry(tmp_path: Path):
    registry = stack_wheels.load_registry(ROOT)
    for entry in registry["wheels"]:
        body = f"wheel {entry['package']}".encode()
        entry["sha256"] = hashlib.sha256(body).hexdigest()
    project = _project_copy(tmp_path, registry)
    index = project / ".stack-wheels"
    index.mkdir()
    for entry in registry["wheels"]:
        (index / entry["asset"]).write_bytes(f"wheel {entry['package']}".encode())
    stack_wheels.check(project)


def test_check_rejects_a_release_url_pin_in_the_lock(tmp_path: Path):
    registry = stack_wheels.load_registry(ROOT)
    project = _project_copy(tmp_path, registry)
    lock = project / "uv.lock"
    lock.write_text(
        lock.read_text(encoding="utf-8")
        + '\n[[package]]\nname = "stray"\nversion = "1"\nsource = { url = "https://github.com/x/y/releases/download/v1/stray-1-py3-none-any.whl" }\n',
        encoding="utf-8",
    )
    with pytest.raises(stack_wheels.StackError, match="release URL pin"):
        stack_wheels.check(project)


def test_retired_repository_names_are_refused(tmp_path: Path):
    registry = stack_wheels.load_registry(ROOT)
    registry["wheels"][0]["repository"] = "leonardosovienski/ecosystem-predictor"
    project = _project_copy(tmp_path, registry)
    with pytest.raises(stack_wheels.StackError, match="retired repository"):
        stack_wheels.load_registry(project)


def test_requirements_adds_hashes_and_the_index_to_the_stack_lines(tmp_path: Path):
    registry = stack_wheels.load_registry(ROOT)
    project = _project_copy(tmp_path, registry)
    exported = tmp_path / "export.txt"
    exported.write_text(
        "anyio==4.15.1 \\\n    --hash=sha256:aaaa\npredictor-research-snapshot==1.0.2rc1\n    # via cain-research\n",
        encoding="utf-8",
    )
    output = tmp_path / "hashed.txt"
    stack_wheels.requirements(project, exported, output)
    lines = output.read_text(encoding="utf-8").splitlines()
    snapshot = next(e for e in registry["wheels"] if e["package"] == "predictor-research-snapshot")
    assert lines[0].startswith("--find-links ") and lines[0].endswith(".stack-wheels")
    assert f"predictor-research-snapshot==1.0.2rc1 --hash=sha256:{snapshot['sha256']}" in lines
    assert "anyio==4.15.1 \\" in lines

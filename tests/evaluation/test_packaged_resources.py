"""The installed evaluator must not depend on a surrounding source checkout."""

from pathlib import Path

from cain.evaluation.harness import load_design
from cain.evaluation.quality import load_dataset
from cain.evaluation.resources import data_root, installed_identity


def test_default_design_survives_unrelated_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    design, probes, root = load_design()
    quality, quality_path = load_dataset()
    assert design["scenarios"] and probes["style"] and quality["cases"]
    assert root == data_root()
    assert quality_path.is_relative_to(root)
    originals = Path(__file__).resolve().parents[2] / "evaluation"
    for relative in (
        "scenarios/scenarios.json", "scenarios/quality-v03.json",
        "probes/probes.json", "rubrics/README.md",
    ):
        assert (root / relative).read_bytes() == (originals / relative).read_bytes()


def test_identity_describes_executed_files_not_a_guessed_checkout():
    identity = installed_identity()
    assert identity["identity_kind"] == "executed_package_bytes"
    assert identity["source_sha256"]["research/historian.py"]
    assert identity["dependency_identity"]["research_snapshot"]["files"]
    assert identity["git_commit"] is None

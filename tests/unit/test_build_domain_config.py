"""tools/build_domain_config.py, D-26: families of a later stocks file are added to the base's, never removed."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "build_domain_config", Path(__file__).parents[2] / "tools" / "build_domain_config.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

PATH = "research/scientific_state.json"


def repo_with_state(tmp_path, families) -> tuple[Path, str, bytes]:
    repo = tmp_path / "stocks-predictor"
    (repo / "research").mkdir(parents=True)
    raw = json.dumps({"schema": "stocks-scientific-state/1", "frozen_families": families,
                      "hypotheses": {"H1": "CLOSED_JUDGED"}}).encode()
    (repo / PATH).write_bytes(raw)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", PATH], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "state"], check=True)
    commit = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    return repo, commit, raw


def frozen(repo, pinned, raw, **changes) -> dict:
    blob = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{pinned}:{PATH}"], capture_output=True, text=True,
                          check=True).stdout.strip()
    extra = {"decision": "D-26", "repository": "leonardosovienski/stocks-predictor", "commit": pinned, "path": PATH,
             "git_blob": blob, "sha256": hashlib.sha256(raw).hexdigest(), "key": "frozen_families",
             "added": ["quality_net_margin"]}
    return {"additional_frozen_families": {**extra, **changes}}


BASE = ["momentum_12_1", "net_margin"]


def test_no_additional_file_keeps_the_base_families(tmp_path):
    assert builder.additional_families("stocks", tmp_path, {}, BASE) == (BASE, None)


def test_the_later_families_are_added_to_the_base_never_removing_one(tmp_path):
    # the later file renames net_margin to quality_net_margin: the base name stays frozen, the new one is added
    repo, commit, raw = repo_with_state(tmp_path, ["momentum_12_1", "quality_net_margin", "momentum_12_1"])
    families, source = builder.additional_families("stocks", repo, frozen(repo, commit, raw), BASE)
    assert families == ["momentum_12_1", "net_margin", "quality_net_margin"]
    assert source["decision"] == "D-26" and source["commit"] == commit and source["path"] == PATH
    assert source["sha256"] == hashlib.sha256(raw).hexdigest() and source["added"] == ["quality_net_margin"]


def test_the_added_families_must_be_the_frozen_parameters_list(tmp_path):
    repo, commit, raw = repo_with_state(tmp_path, ["momentum_12_1", "quality_net_margin", "quality_new"])
    with pytest.raises(SystemExit):
        builder.additional_families("stocks", repo, frozen(repo, commit, raw), BASE)


@pytest.mark.parametrize("changes", [
    {"sha256": "0" * 64},
    {"git_blob": "0" * 40},
    {"key": "hypotheses"},
    {"repository": "leonardosovienski/cripto-predictor"},
    {"commit": "HEAD"},
])
def test_anything_but_the_pinned_bytes_of_the_frozen_families_is_refused(tmp_path, changes):
    repo, commit, raw = repo_with_state(tmp_path, ["momentum_12_1", "quality_net_margin"])
    assert builder.additional_families("stocks", repo, frozen(repo, commit, raw), BASE)[1]  # unchanged: accepted
    with pytest.raises(SystemExit):
        builder.additional_families("stocks", repo, frozen(repo, commit, raw, **changes), BASE)


def test_only_the_stocks_domain_takes_additional_families(tmp_path):
    repo, commit, raw = repo_with_state(tmp_path, ["momentum_12_1", "quality_net_margin"])
    with pytest.raises(SystemExit):
        builder.additional_families("crypto", repo, frozen(repo, commit, raw), BASE)


def test_a_list_that_is_not_names_is_refused(tmp_path):
    repo, commit, raw = repo_with_state(tmp_path, ["momentum_12_1", "quality_net_margin", ""])
    with pytest.raises(SystemExit):
        builder.additional_families("stocks", repo, frozen(repo, commit, raw), BASE)

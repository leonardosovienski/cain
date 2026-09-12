"""Distribution fixtures must preserve the original protocol bytes."""
from hashlib import sha256
from pathlib import Path

from cain.evaluation.harness import load_design
from cain.evaluation.quality import load_dataset, _code_identity
from cain.evaluation.resources import data_root


def test_fixture_bytes_equal_repository_originals():
    original = Path(__file__).resolve().parents[1] / 'evaluation'
    for name in ('scenarios/scenarios.json', 'scenarios/quality-v03.json',
                 'probes/probes.json', 'rubrics/README.md'):
        assert sha256((original / name).read_bytes()).digest() == sha256((data_root() / name).read_bytes()).digest()


def test_default_loaders_use_packaged_resources_and_nonempty_identity():
    assert load_design()[2] == data_root()
    assert load_dataset()[1].is_relative_to(data_root())
    identity = _code_identity()
    assert identity['source_sha256']
    assert 'evaluation/quality.py' in identity['source_sha256']
    assert identity['git_commit'] is None

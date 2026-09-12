"""Offline procedure: independent expected values, restart, refusal and boundary checks."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import test_research_l0 as cases

setup = cases.setup
SCRIPT = Path(__file__).parents[2] / 'scripts' / 'verify_evidence_selection.py'


def command(*args):
    env = dict(os.environ, PYTHONPATH=str(SCRIPT.parent.parent / 'src'))
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          env=env, capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize('identity', ['T42', 'Ω7'])
def test_procedure_resumes_and_does_not_repeat_effects(setup, tmp_path, identity):
    service, scope, ingest, _, path = setup
    ingest(cases.publication((identity,), text=json.dumps({identity: {'state': 'WAIT', 'trial': 'alpha'}})))
    out = tmp_path / 'isolated'
    result = command('start', '--output', out, '--database', service.path, '--policy', path,
                     '--identity', identity, '--pointer', '/'+identity+'/state', '--pointer', '/'+identity+'/trial')
    assert result.returncode == 0, result.stderr
    checkpoint = json.loads((out/'checkpoint.json').read_bytes())
    assert len(checkpoint['steps']) == 1 and checkpoint['next_step'] == 'search'
    result = command('resume', '--output', out)
    assert result.returncode == 0, result.stderr
    report = json.loads((out/'verification.json').read_bytes())
    assert report['verified'] and report['selected_expected_fields'] == report['compact_expected_fields'] == 2
    assert report['model_calls'] == 0 and len(report['workflow']['attempts']) == 2
    before = (out/'verification.json').read_bytes()
    assert command('resume', '--output', out).returncode == 0
    assert (out/'verification.json').read_bytes() == before


def test_procedure_refuses_missing_pointer(setup, tmp_path):
    service, scope, ingest, _, path = setup
    ingest(cases.publication(('T42',), text='{"T42":{"state":"WAIT"}}'))
    out = tmp_path/'refused'
    assert command('start', '--output', out, '--database', service.path, '--policy', path,
                   '--identity', 'T42', '--pointer', '/T42/missing').returncode == 0
    assert command('resume', '--output', out).returncode != 0
    assert not (out/'verification.json').exists()


def test_offline_boundary_blocks_network_and_external_write(tmp_path):
    code = '''import sys, socket
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from verify_evidence_selection import offline_boundary
offline_boundary(Path(sys.argv[2]))
blocked = 0
try: socket.socket()
except PermissionError: blocked += 1
try: Path(sys.argv[3]).write_text('forbidden')
except PermissionError: blocked += 1
assert blocked == 2
'''
    out = tmp_path/'boundary'
    out.mkdir()
    env = dict(os.environ, PYTHONPATH=str(SCRIPT.parent.parent/'src'))
    result = subprocess.run([sys.executable, '-c', code, str(SCRIPT.parent), str(out), str(tmp_path/'outside')],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path/'outside').exists()

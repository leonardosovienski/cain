"""Prepared Linux execution, not executed or certified on Windows.

No Git publication. A green run produces evidence, never a stabilization decision.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--manifest', type=Path, required=True)
p.add_argument('--roots', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
assert sys.platform == 'linux' and os.geteuid() != 0, 'Ordinary Linux user required'
assert (3, 13) <= sys.version_info[:2] < (3, 15), 'Use Python 3.13 or 3.14 for the integrated environment'
a.out.mkdir(parents=True, exist_ok=False)
out = a.out.resolve()
kit = Path(__file__).resolve().parent
roots = {name: Path(path).resolve(strict=True) for name, path in json.loads(a.roots.read_text()).items()}
manifest = json.loads(a.manifest.read_text())
counter = 0
environment = dict(os.environ)
environment.pop('PYTHONPATH', None)
environment.update(PYTHONDONTWRITEBYTECODE='1', SOURCE_DATE_EPOCH='1789167600',
                   TMPDIR=str(out), CAIN_CANDIDATE_ROOT=str(roots['cain']))

def run(label, command, cwd=None, env=None):
    global counter
    counter += 1
    prefix = out / f'{counter:03d}-{label}'
    command = [str(c) for c in command]
    prefix.with_suffix('.command.json').write_text(json.dumps(dict(command=command, cwd=str(cwd or out)), indent=2))
    with prefix.with_suffix('.stdout').open('xb') as stdout, prefix.with_suffix('.stderr').open('xb') as stderr:
        result = subprocess.run(command, cwd=cwd or out, env=env or environment, stdout=stdout, stderr=stderr)
    prefix.with_suffix('.exit').write_text(str(result.returncode))
    if result.returncode:
        raise SystemExit(f'FAIL: {label}; inspect {prefix}.stderr and preserve this candidate before editing')

fs = subprocess.check_output(['stat', '-f', '-c', '%T', str(out)], text=True).strip()
assert fs in {'ext2/ext3', 'ext4', 'xfs', 'btrfs', 'tmpfs', 'overlayfs', 'zfs'}, 'Native Linux filesystem required: ' + fs
mask = os.umask(0)
os.umask(mask)
(out / 'environment.json').write_text(json.dumps(dict(uname=platform.uname()._asdict(),
    distribution=Path('/etc/os-release').read_text(), filesystem=fs, user=os.geteuid(),
    python=sys.version, umask=oct(mask)), indent=2))
for label, cmd in [('uname', ['uname', '-a']), ('mount', ['findmnt', '-T', out, '-J']),
                   ('user', ['id']), ('python', [sys.executable, '-VV'])]:
    run(label, cmd)

for repo in manifest['repositories']:
    name = repo['repository']
    if name in ('core', 'ops'):
        continue
    root = roots[name]
    assert subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == repo['base_head']
    actual = set(filter(None, subprocess.check_output(['git', '-C', str(root), 'diff', '--name-only', '-z', 'HEAD']).decode().split('\0')))
    actual |= set(filter(None, subprocess.check_output(['git', '-C', str(root), 'ls-files', '--others', '--exclude-standard', '-z']).decode().split('\0')))
    assert actual <= set(repo['overlay_files']), (name, 'unexpected working-tree difference')
    for relative, expected in repo['overlay_files'].items():
        path = root / relative
        assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None) == expected, (name, relative)
(out / 'source-equivalence.json').write_text(json.dumps(dict(SOURCE_EQUIVALENCE='PASS', candidate_id=manifest['candidate_id'],
    basis='exact base HEAD plus every recorded working-tree change; no manual recreation'), indent=2))

def venv(name):
    directory = out / name
    run(name, [sys.executable, '-m', 'venv', directory])
    return directory / 'bin/python'

builder = venv('build-env')
run('build-tools', [builder, '-m', 'pip', 'install', 'build', 'setuptools>=75', 'wheel'])
legacy = out / 'snapshot-1.0.0'
source_ref = json.loads((roots['cain'] / 'vendor/provenance.json').read_text())['source_commit']
paths = subprocess.check_output(['git', '-C', str(roots['ecosystem']), 'ls-tree', '-r', '--name-only', source_ref, '--', 'packages/research-snapshot'], text=True).splitlines()
for name in paths:
    relative = Path(name).relative_to('packages/research-snapshot')
    target = legacy / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(subprocess.check_output(['git', '-C', str(roots['ecosystem']), 'show', source_ref + ':' + name]))
wheels = out / 'wheels'
wheels.mkdir()
for label, root in [('legacy-snapshot', legacy), ('snapshot', roots['ecosystem'] / 'packages/research-snapshot'),
                    ('bundle', roots['ecosystem'] / 'packages/research-bundle'), ('cain', roots['cain']),
                    ('crypto-export', roots['crypto'] / 'packages/research-export')]:
    run('build-' + label, [builder, '-m', 'build', '--wheel', '--outdir', wheels, root])
(out / 'wheel-hashes.json').write_text(json.dumps({f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in wheels.glob('*.whl')}, indent=2))

receiver = venv('receiver-env')
run('receiver-install', [receiver, '-m', 'pip', 'install', '--no-index', '--find-links', wheels, 'cain-research==0.4.7'])
run('test-tools', [receiver, '-m', 'pip', 'install', 'pytest>=8,<10', 'fastapi>=0.115,<1', 'uvicorn>=0.30,<1', 'httpx>=0.27,<1', 'Pillow>=11,<13'])
run('pip-version', [receiver, '-m', 'pip', '--version'])
run('pip-check', [receiver, '-m', 'pip', 'check'])
tests = roots['cain'] / 'tests'
shared = roots['ecosystem'] / 'packages/research-bundle/tests'
run('targeted', [receiver, '-m', 'pytest', '-o', 'pythonpath=', tests / 'test_research_bundle.py',
    tests / 'test_bundle_remediation.py', tests / 'integration/test_research_l0.py', shared, kit / 'test_posix_gate.py',
    '-q', '--junitxml=' + str(out / 'targeted.xml')])
targeted = ET.parse(out / 'targeted.xml')
symlink = [t for t in targeted.iter('testcase') if t.get('name') == 'test_symlink_import_escape']
assert len(symlink) == 1 and symlink[0].find('skipped') is None, 'Mandatory symlink test did not execute'
assert not list(targeted.iter('skipped')), 'Investigate every targeted security skip before continuing'
run('full', [receiver, '-m', 'pytest', '-o', 'pythonpath=', tests, shared, '-q', '--junitxml=' + str(out / 'full.xml')])
run('installed-wheel', [receiver, roots['cain'] / 'tools/verify_wheel.py', '--wheel',
    wheels / 'cain_research-0.4.7-py3-none-any.whl', '--vendor', wheels])
run('e2e', [receiver, '-I', kit / 'linux_e2e.py', roots['cain'], out / 'e2e'])
producer = venv('producer-env')
run('producer-install', [producer, '-m', 'pip', 'install', '--no-index', '--find-links', wheels,
    'crypto-research-export==1.0.1', 'predictor-research-bundle==1.0.0'])
run('producer-test-tools', [producer, '-m', 'pip', 'install', 'pytest>=8,<10'])
run('producer-pip-check', [producer, '-m', 'pip', 'check'])
run('crypto-tests', [producer, '-m', 'pytest', '-o', 'pythonpath=', roots['crypto'] / 'packages/research-export/tests',
    '-q', '--junitxml=' + str(out / 'crypto.xml')], cwd=roots['crypto'])
for name, pattern in [('brasileirao', 'test_export_cain*.py'), ('stocks', 'test_*cain*.py')]:
    run(name + '-tests', [producer, '-m', 'unittest', 'discover', '-s', 'tools', '-p', pattern, '-v'], cwd=roots[name])
run('mini-audit', [receiver, '-m', 'pytest', '-o', 'pythonpath=', tests / 'test_bundle_remediation.py', kit / 'test_posix_gate.py',
    '-q', '--junitxml=' + str(out / 'mini-audit.xml')])
(out / 'EXECUTION_COMPLETE.json').write_text(json.dumps(dict(candidate_id=manifest['candidate_id'],
    execution='PASS_PREPARED_SUITES', REAL_PRODUCER_EXPORT_LINUX='NOT_EXECUTED', PYTHON_MATRIX='PARTIAL',
    STABILIZATION='NOT_DECIDED_REQUIRES_REVIEW', note='Review all results, remaining coverage and clean-sheet semantics; never auto-stabilize'), indent=2))

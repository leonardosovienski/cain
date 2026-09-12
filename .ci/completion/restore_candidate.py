"""Apply exact bytes to fresh, clean Linux checkouts at the recorded base HEADs.

No fetch/push/commit. roots.json maps repository names to already prepared paths;
overlays.json maps names to their locally transferred overlay.zip files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--manifest', type=Path, required=True)
parser.add_argument('--roots', type=Path, required=True)
parser.add_argument('--overlays', type=Path, required=True)
args = parser.parse_args()
manifest = json.loads(args.manifest.read_text())
roots, overlays = [json.loads(p.read_text()) for p in (args.roots, args.overlays)]
for repo in manifest['repositories']:
    if repo['repository'] in ('core', 'ops'):
        continue
    root = Path(roots[repo['repository']]).resolve(strict=True)
    assert subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == repo['base_head']
    assert not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain=v1']), 'Use a fresh clean checkout'
    archive_path = Path(overlays[repo['repository']])
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == repo['capture']['overlay_sha256']
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {n for n, h in repo['overlay_files'].items() if h is not None}
        for name, expected in repo['overlay_files'].items():
            target = root / name
            assert target.resolve().is_relative_to(root) and not target.is_symlink()
            if expected is None:
                target.unlink()
            else:
                raw = archive.read(name)
                assert hashlib.sha256(raw).hexdigest() == expected
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
print('Overlay applied; run_linux.py must independently verify source equivalence before testing.')

"""Reconstruct the frozen working trees from local CI checkouts; never publish."""
import json
from pathlib import Path
import subprocess
import sys

checkouts, destination = map(Path, sys.argv[1:])
destination.mkdir(parents=True, exist_ok=False)
kit = checkouts / 'cain/.ci/cain-supply'
manifest = json.loads((kit / 'CANDIDATE_MANIFEST.json').read_text())
roots, overlays = {}, {}
for repo in manifest['repositories']:
    name = repo['repository']
    if name in ('core', 'ops'):
        continue
    source = checkouts / name
    root = destination / name
    subprocess.run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(source), str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'checkout', '--detach', repo['base_head']], check=True)
    roots[name] = str(root)
    overlays[name] = str(source / '.ci/cain-supply/overlay.zip')
(destination / 'roots.json').write_text(json.dumps(roots))
(destination / 'overlays.json').write_text(json.dumps(overlays))
subprocess.run([sys.executable, str(kit / 'restore_candidate.py'), '--manifest', str(kit / 'CANDIDATE_MANIFEST.json'),
                '--roots', str(destination / 'roots.json'), '--overlays', str(destination / 'overlays.json')], check=True)

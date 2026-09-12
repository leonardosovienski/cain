"""Installed Linux consumption E2E using the existing synthetic test fixture."""
import json
import os
from pathlib import Path
import runpy
import sys

import cain
import research_bundle
from cain.archive import backup, restore
from cain.research import ResearchService
from cain.research.bundles import BundleService
from cain.workspace import WorkspaceStore
from research_bundle import canonical, seal

assert sys.platform == 'linux' and os.geteuid() != 0
assert Path(cain.__file__).is_relative_to(Path(sys.prefix))
assert Path(research_bundle.__file__).is_relative_to(Path(sys.prefix))
root, area = map(Path, sys.argv[1:])
area.mkdir()
fixture = runpy.run_path(str(root / 'tests/test_research_bundle.py'))['setup'].__wrapped__
store, scope, b, transport, policy, _ = fixture(area)
b['profile'] = 'local-research/2'
b['entities'][0].update(revision='linux-e2e', evidence_ids=['e-linux'])
b['relations'][0]['source']['revision'] = 'linux-e2e'
b['evidence'] = [dict(id='e-linux', source='report.json', locator='synthetic-test',
                      payload={'fact': 'Synthetic engineering evidence only'})]
b = seal(b)
(transport / 'one/bundle.json').write_bytes(canonical(b))
store.approve('one/bundle.json', scope)
assert store.ingest('one/bundle.json', scope)['status'] == 'admitted'
assert store.ingest('one/bundle.json', scope)['status'] == 'duplicate'
assert store.query(scope)['total'] == 1
assert store.entity(scope, b['bundle_id'], 'TEST-HYPOTHESIS-001', 'linux-e2e')['evidence_total'] == 1
assert store.evidence(scope, b['bundle_id'], 'e-linux')['evidence']['payload']['fact']
assert store.query(scope)['relation_total'] == 1
store.verify(scope)
workspace = WorkspaceStore(area / 'workspace.db')
backup(workspace.path, store.service.path, policy, area / 'backup')
restore(area / 'backup', area / 'restored')
transport.rename(area / 'producer-unavailable')
recovered = BundleService(ResearchService(area / 'restored/research.db', area / 'restored/policy.json'))
assert recovered.query(scope)['total'] == 1
assert recovered.evidence(scope, b['bundle_id'], 'e-linux')['evidence']['payload']['fact']
assert recovered.query(scope)['relation_total'] == 1
recovered.verify(scope, rebuild=True)
recovered.materialize(scope, b['bundle_id'], 'a1', area / 'offline-object')
assert (area / 'offline-object').read_bytes() == b'real test bytes'
result = dict(LINUX_CONSUMPTION_E2E='PASS', OFFLINE_RESTORE='PASS',
              REAL_PRODUCER_EXPORT_LINUX='NOT_EXECUTED', fixture='existing synthetic fixture',
              modules=dict(cain=cain.__file__, bundle=research_bundle.__file__))
(area / 'evidence.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))

"""Malicious test candidates and the expected defence for each (the P10 attack list).

Each candidate is a small Python program that tries one thing inside the sandbox and writes what
happened to ``output.json`` (when it still can). ``run_attacks`` runs every one through
``run_attempt`` and records the real outcome next to the expected one.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from cain.sandbox.attempt import hashes, run_attempt

_REPORT = '''
import json, sys
def done(**result):
    with open("output.json", "w") as handle:
        json.dump(result, handle)
'''

ATTACKS = {
    "network_socket": ("no network namespace (--network none)", _REPORT + '''
import socket
try:
    socket.create_connection(("1.1.1.1", 53), timeout=3).close()
    done(succeeded=True)
except OSError as exc:
    done(succeeded=False, error=repr(exc))
'''),
    "network_http": ("no network namespace (--network none)", _REPORT + '''
import urllib.request
try:
    urllib.request.urlopen("http://example.com", timeout=5).read(10)
    done(succeeded=True)
except Exception as exc:
    done(succeeded=False, error=repr(exc))
'''),
    "write_evaluator": ("evaluator never mounted; read-only root", _REPORT + '''
targets = {targets}
results = {{}}
for target in targets:
    try:
        with open(target, "a") as handle:
            handle.write("# tampered: return best score\\n")
        results[target] = "written"
    except OSError as exc:
        results[target] = repr(exc)
done(succeeded=any(v == "written" for v in results.values()), results=results)
'''),
    "read_holdout": ("holdout never mounted", _REPORT + '''
targets = {targets}
results = {{}}
for target in targets:
    try:
        with open(target) as handle:
            results[target] = "read %d bytes" % len(handle.read())
    except OSError as exc:
        results[target] = repr(exc)
done(succeeded=any(v.startswith("read") for v in results.values()), results=results)
'''),
    "write_root_filesystem": ("read-only root filesystem", _REPORT + '''
results = {}
for target in ("/etc/cain-pwned", "/usr/local/lib/python3.13/site.py", "/bin/sh-backdoor"):
    try:
        with open(target, "a") as handle:
            handle.write("x")
        results[target] = "written"
    except OSError as exc:
        results[target] = repr(exc)
done(succeeded=any(v == "written" for v in results.values()), results=results)
'''),
    "privilege_escalation": ("non-root user, no capabilities, no-new-privileges", _REPORT + '''
import os
try:
    os.setuid(0)
    done(succeeded=True, uid=os.getuid())
except OSError as exc:
    done(succeeded=False, uid=os.getuid(), error=repr(exc))
'''),
    "fork_bomb": ("--pids-limit", _REPORT + '''
import os, time
children = 0
error = None
try:
    for _ in range(2000):
        pid = os.fork()
        if pid == 0:
            time.sleep(20)
            os._exit(0)
        children += 1
except OSError as exc:
    error = repr(exc)
done(succeeded=error is None, children=children, error=error)
'''),
    "memory_hog": ("--memory with no swap (OOM kill)", _REPORT + '''
blocks = []
for _ in range(64):
    blocks.append(bytearray(64 * 1024 * 1024))
done(succeeded=True, allocated_mb=64 * len(blocks))
'''),
    "infinite_loop": ("timeout kills the container", '''
while True:
    pass
'''),
    "symlink_report": ("host reads outputs only as regular files inside the workspace", _REPORT + '''
import os
os.symlink({target!r}, "report.md")
done(succeeded=True, planted="report.md -> " + {target!r})
'''),
    "fabricated_report": ("integrity check: report numbers must come from the run output", '''
import json
json.dump({"rps": 0.2093, "baseline_rps": 0.2234}, open("output.json", "w"))
open("report.md", "w").write("The new model reaches RPS 0.1812, far below the baseline 0.2234.\\n")
'''),
}


def benign_candidate() -> str:
    return '''
import csv, json
rows = list(csv.DictReader(open("/data/allowed.csv")))
mean = sum(float(r["value"]) for r in rows) / len(rows)
json.dump({"rows": len(rows), "mean": round(mean, 4)}, open("output.json", "w"))
open("report.md", "w").write(f"Mean over {len(rows)} rows: {round(mean, 4)}.\\n")
'''


def run_attacks(sandbox, *, evaluator_files, holdout_files, allowed_data: Path, workspace_root=None,
                tamper_hook=None) -> dict:
    """Run every attack plus a benign candidate and an out-of-band evaluator change."""
    results = []
    evaluator_files = [str(f) for f in evaluator_files]
    targets = evaluator_files + ["/evaluator/evaluator.py", "../evaluator.py", "/workspace/../evaluator.py"]
    holdouts = [str(f) for f in holdout_files] + ["/data/holdout.csv", "/holdout/holdout.csv"]
    data_ro = [(allowed_data.parent, "/data")]
    start_hashes = hashes(evaluator_files)
    for name, (defence, source) in ATTACKS.items():
        if name == "write_evaluator":
            source = source.replace("{targets}", repr(targets)).replace("{{", "{").replace("}}", "}")
        elif name == "read_holdout":
            source = source.replace("{targets}", repr(holdouts)).replace("{{", "{").replace("}}", "}")
        elif name == "symlink_report":
            source = source.replace("{target!r}", repr(evaluator_files[0]))
        results.append(_one(sandbox, name, defence, source, evaluator_files, data_ro, workspace_root))
    results.append(_one(sandbox, "benign_candidate", "(none: must be VALID)", benign_candidate(), evaluator_files,
                        data_ro, workspace_root))
    if tamper_hook is not None:
        # The container cannot reach the evaluator; this simulates a change by anything else during an
        # attempt, to show the before/after check turns the attempt INVALID and alerts.
        class Tampering:
            def __init__(self, inner):
                self.inner = inner

            def image_identity(self):
                return self.inner.image_identity()

            def run(self, workspace, argv, data_ro=()):
                out = self.inner.run(workspace, argv, data_ro=data_ro)
                tamper_hook()
                return out

        results.append(_one(Tampering(sandbox), "evaluator_changed_out_of_band", "evaluator hash before/after",
                            benign_candidate(), evaluator_files, data_ro, workspace_root))
    return {"attacks": results, "evaluator_start": start_hashes}


def _one(sandbox, name, defence, source, evaluator_files, data_ro, workspace_root) -> dict:
    candidate = Path(tempfile.mkdtemp(prefix=f"cain-cand-{name}-", dir=workspace_root))
    (candidate / "candidate.py").write_text(source, encoding="utf-8")
    manifest = run_attempt(sandbox, candidate, evaluator_files=evaluator_files, data_ro=data_ro,
                           workspace_root=workspace_root)
    inside = manifest.get("output_json")
    return {"attack": name, "defence": defence, "verdict": manifest["verdict"], "status": manifest["run"]["status"],
            "exit_code": manifest["run"]["exit_code"], "oom_killed": manifest["run"]["oom_killed"],
            "inside": inside, "problems": manifest["problems"], "alerts": manifest["alerts"],
            "evaluator_unchanged": manifest["evaluator"]["unchanged"], "file_log": manifest["run"]["file_log"],
            "container_diff": manifest["run"]["container_diff"], "image": manifest["image"],
            "stderr_tail": manifest["run"]["stderr"][-300:]}


def summarize(report: dict) -> list[dict]:
    rows = []
    for item in report["attacks"]:
        inside = item.get("inside") or {}
        blocked = item["attack"] == "benign_candidate" or not inside.get("succeeded", False)
        rows.append({"attack": item["attack"], "defence": item["defence"], "verdict": item["verdict"],
                     "status": item["status"], "blocked": blocked,
                     "evidence": (inside.get("error") or inside.get("results") or inside.get("children")
                                  or item["problems"] or item["alerts"] or item["status"])})
    return rows


def dumps(report: dict) -> str:
    return json.dumps(report, indent=2, default=str)

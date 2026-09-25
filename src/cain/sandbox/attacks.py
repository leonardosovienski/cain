"""Malicious test candidates and the expected defence for each (the P10 attack list).

Each candidate is a small Python program that tries one thing inside the sandbox and writes what
happened to ``output.json`` (when it still can). ``run_attacks`` runs every one through
``run_attempt`` and records the real outcome next to the expected one.

Whether a defence held is judged by what the host observed (status, verdict, problems, alerts, the
evaluator hashes), never by the candidate's word alone: an attack that reports its own failure counts
only when it ran to the end and wrote that failure, so a crash that leaves no output proves nothing.
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
    "isolation_probe": ("uid nobody, no capabilities, no_new_privs, seccomp filter, /data read-only",
                        _REPORT + '''
status = dict(line.split(":", 1) for line in open("/proc/self/status").read().splitlines() if ":" in line)
mounts = {}
for line in open("/proc/self/mounts"):
    device, target, kind, options = line.split()[:4]
    mounts[target] = {"type": kind, "writable": "rw" in options.split(",")}
done(uid=status["Uid"].split()[0], cap_eff=status["CapEff"].strip(), cap_bnd=status["CapBnd"].strip(),
     no_new_privs=status["NoNewPrivs"].strip(), seccomp=status["Seccomp"].strip(),
     # /proc and /sys entries are Docker's masked paths (bind mounts of /dev/null), not storage
     writable_mounts=sorted(t for t, m in mounts.items()
                            if m["writable"] and not t.startswith(("/proc", "/sys"))
                            and m["type"] not in ("cgroup", "cgroup2", "devpts", "mqueue")),
     data_read_only=("/data" in mounts and not mounts["/data"]["writable"]))
'''),
}

# Writable mounts a container may have: its workspace and the noexec tmpfs, plus Docker's own /dev
# (root-owned 0755 tmpfs, not writable by nobody) and /dev/shm (64 MB, noexec).
ALLOWED_WRITABLE = {"/workspace", "/tmp", "/dev", "/dev/shm"}


def _probe_held(inside: dict) -> bool:
    return (inside.get("uid") == "65534" and set(inside.get("cap_eff", "x")) == {"0"}
            and set(inside.get("cap_bnd", "x")) == {"0"} and inside.get("no_new_privs") == "1"
            and inside.get("seccomp") == "2" and inside.get("data_read_only") is True
            and set(inside.get("writable_mounts", ["?"])) <= ALLOWED_WRITABLE)


# How the host sees that each defence held.
EXPECTED = {
    "memory_hog": ("killed out of memory", lambda item, inside: item["status"] == "OOM_KILLED"),
    "infinite_loop": ("killed at the timeout", lambda item, inside: item["status"] == "TIMEOUT"),
    "symlink_report": ("INVALID, the link refused", lambda item, inside: item["verdict"] == "INVALID"
                       and any("symlink" in p for p in item["problems"])),
    "fabricated_report": ("INVALID by the integrity check", lambda item, inside: item["verdict"] == "INVALID"
                          and "report has numbers the run did not produce" in item["problems"]),
    "isolation_probe": ("probe values as expected", lambda item, inside: item["status"] == "OK"
                        and _probe_held(inside)),
    "benign_candidate": ("VALID", lambda item, inside: item["verdict"] == "VALID"),
    "evaluator_changed_out_of_band": ("INVALID with EVALUATOR_CHANGED", lambda item, inside:
                                      item["verdict"] == "INVALID"
                                      and any(a["alert"] == "EVALUATOR_CHANGED" for a in item["alerts"])),
}
_SELF_REPORTED = ("ran to the end and reported its own failure",
                  lambda item, inside: item["status"] == "OK" and inside.get("succeeded") is False)


def held(item: dict) -> tuple[bool, str]:
    """(defence held, what was required)."""
    inside = item.get("inside") or {}
    expected, check = EXPECTED.get(item["attack"], _SELF_REPORTED)
    if item["attack"] != "evaluator_changed_out_of_band" and not item["evaluator_unchanged"]:
        return False, "evaluator unchanged"
    return bool(check(item, inside)), expected


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
            "docker_args": manifest["run"]["docker_args"], "stderr_tail": manifest["run"]["stderr"][-300:]}


def summarize(report: dict) -> list[dict]:
    rows = []
    for item in report["attacks"]:
        inside = item.get("inside") or {}
        blocked, required = held(item)
        rows.append({"attack": item["attack"], "defence": item["defence"], "verdict": item["verdict"],
                     "status": item["status"], "blocked": blocked, "required": required,
                     "evidence": (inside.get("error") or inside.get("results") or inside.get("children")
                                  or item["problems"] or item["alerts"] or inside or item["status"])})
    return rows


def dumps(report: dict) -> str:
    return json.dumps(report, indent=2, default=str)

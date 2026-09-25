"""Stand-in for the docker CLI, for plumbing tests only (it runs the candidate on the host, NOT isolated).

Handles: image inspect, run (records the child pid, runs argv in the /workspace mount), inspect,
diff, kill, rm. Every call is appended to $FAKE_DOCKER_LOG. The real isolation is tested against a
real engine (tests marked with CAIN_TEST_DOCKER) and in the runtime evidence.
"""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys

STATE = Path(os.environ["FAKE_DOCKER_STATE"])
STATE.mkdir(parents=True, exist_ok=True)
args = sys.argv[1:]
with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\n")
command = args[0]
if command == "image":
    print(json.dumps({"Id": "sha256:" + "f" * 64, "RepoDigests": ["python@sha256:" + "e" * 64]}))
elif command == "run":
    name = args[args.index("--name") + 1]
    workspace = next(a.split(":/workspace:")[0] for a in args if ":/workspace:" in a)
    image = os.environ["FAKE_DOCKER_IMAGE"]
    argv = args[args.index(image) + 1:]
    argv = [sys.executable if argv[0] == "python" else argv[0], *argv[1:]]
    child = subprocess.Popen(argv, cwd=workspace)
    (STATE / f"{name}.json").write_text(json.dumps({"pid": child.pid}))
    code = child.wait()
    (STATE / f"{name}.json").write_text(json.dumps({"ExitCode": code, "OOMKilled": False}))
    sys.exit(code)
elif command == "inspect":
    path = STATE / f"{args[1]}.json"
    if not path.exists():
        sys.exit(1)
    state = json.loads(path.read_text())
    print(json.dumps({"ExitCode": state.get("ExitCode", 137), "OOMKilled": False}))
elif command == "kill":
    path = STATE / f"{args[1]}.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    if "pid" in state:
        try:
            os.kill(state["pid"], signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM)
        except OSError:
            pass
        path.write_text(json.dumps({"ExitCode": 137, "OOMKilled": False}))
elif command in ("diff", "rm"):
    pass

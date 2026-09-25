"""Stand-in for the docker CLI, for plumbing tests only (it runs the candidate on the host, NOT isolated).

Handles: image inspect, run (records the child pid, runs argv in the /workspace mount), inspect,
diff, kill, rm. Every call is appended to $FAKE_DOCKER_LOG. With $FAKE_DOCKER_KILL_NOOP, ``kill`` leaves
the candidate alive (a process that keeps holding the output pipes after the CLI is killed). The real isolation is tested against a
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


def put(path: Path, value: dict) -> None:
    """Atomic state write: a process killed mid-write never leaves a truncated file behind."""
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value))
    os.replace(temporary, path)


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
    put(STATE / f"{name}.json", {"pid": child.pid})
    code = child.wait()
    if (STATE / f"{name}.killed").exists():
        code = 137  # like the real engine: a container stopped by `docker kill` exits 137
    put(STATE / f"{name}.json", {"ExitCode": code, "OOMKilled": False})
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
    if "pid" in state and not os.environ.get("FAKE_DOCKER_KILL_NOOP"):
        (STATE / f"{args[1]}.killed").write_text("")  # before the kill, so `run` always sees it
        try:
            os.kill(state["pid"], signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM)
        except OSError:
            pass
        put(path, {"ExitCode": 137, "OOMKilled": False})
elif command in ("diff", "rm"):
    pass

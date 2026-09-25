"""Run model-generated or model-altered code in a Docker container.

Every attempt runs with: no network (``--network none``), a read-only root filesystem, a non-root user,
all capabilities dropped and ``no-new-privileges``, CPU, memory (no swap) and process limits, a small
``noexec`` tmpfs, a hard timeout (the container is killed), and only its own workspace mounted
read-write. The evaluator, the holdout data and the world file are never mounted; allowed input data
can be mounted read-only. gVisor is used when ``runtime="runsc"`` (Linux); on macOS Docker Desktop has
no gVisor and the isolation is the VM plus these flags.

File access log: what the attempt created, modified or deleted in its workspace (hash snapshots before
and after, symlinks reported as such), and ``docker diff`` of the container (expected empty with the
read-only root). Reads are not logged (that needs a tracer inside the container).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

# Bounded read of the output left after a timeout kill (see DockerSandbox.run).
OUTPUT_GRACE_SECONDS = 10.0


@dataclass(frozen=True)
class SandboxPolicy:
    image: str                      # pinned image reference (tag or digest)
    cpus: float = 1.0
    memory: str = "512m"
    pids: int = 128
    timeout: float = 60.0
    user: str = "65534:65534"       # nobody
    tmpfs_mb: int = 64
    runtime: str | None = None      # "runsc" for gVisor


def snapshot(root: Path) -> dict[str, str]:
    """Relative path -> sha256 (or 'symlink:<target>') of everything under ``root``."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            out[rel] = "symlink:" + os.readlink(path)
        elif path.is_file():
            out[rel] = sha256(path.read_bytes()).hexdigest()
    return out


def file_log(before: dict, after: dict) -> dict:
    return {"created": sorted(set(after) - set(before)), "deleted": sorted(set(before) - set(after)),
            "modified": sorted(k for k in set(before) & set(after) if before[k] != after[k]),
            "symlinks": sorted(k for k, v in after.items() if v.startswith("symlink:"))}


class DockerSandbox:
    def __init__(self, policy: SandboxPolicy, *, docker="docker", path_mapper=None):
        # ``docker`` is the CLI, or a command prefix (list) such as [python, fake_docker.py] in tests.
        self.policy, self.docker = policy, [docker] if isinstance(docker, str) else list(docker)
        # How the docker engine sees a host path (identity for a native engine; `wslpath -w` for
        # Docker Desktop's Windows CLI called from WSL).
        self.path_mapper = path_mapper or (lambda path: str(path))

    def _docker(self, *args, timeout=60, check=True) -> subprocess.CompletedProcess:
        return subprocess.run([*self.docker, *args], capture_output=True, text=True, timeout=timeout, check=check)

    def image_identity(self) -> dict:
        done = self._docker("image", "inspect", self.policy.image, "--format", "{{json .}}")
        info = json.loads(done.stdout)
        return {"reference": self.policy.image, "id": info["Id"], "repo_digests": info.get("RepoDigests") or []}

    def command(self, name: str, workspace: Path, argv: list[str], data_ro=()) -> list[str]:
        p = self.policy
        args = ["run", "--name", name, "--network", "none", "--read-only", "--user", p.user,
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", str(p.pids),
                "--cpus", str(p.cpus), "--memory", p.memory, "--memory-swap", p.memory,
                "--tmpfs", f"/tmp:rw,noexec,nosuid,size={p.tmpfs_mb}m",
                "-v", f"{self.path_mapper(workspace)}:/workspace:rw", "-w", "/workspace",
                "-e", "PYTHONDONTWRITEBYTECODE=1"]
        for host, target in data_ro:
            args += ["-v", f"{self.path_mapper(host)}:{target}:ro"]
        if p.runtime:
            args += ["--runtime", p.runtime]
        return args + [p.image, *argv]

    def run(self, workspace: Path, argv: list[str], *, data_ro=()) -> dict:
        workspace = Path(workspace)
        name = "cain-attempt-" + uuid4().hex[:12]
        before = snapshot(workspace)
        args = self.command(name, workspace, argv, data_ro)
        status, stdout, stderr = "OK", "", ""
        process = subprocess.Popen([*self.docker, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(timeout=self.policy.timeout)
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
            # Stop the container first (it holds the work), then the CLI. Reading what is left of the
            # output is bounded: on Windows a pipe stays open while anything that inherited it lives,
            # and an unbounded read after a kill (what subprocess.run does there) never returns.
            self._docker("kill", name, check=False)
            process.kill()
            try:
                stdout, stderr = process.communicate(timeout=OUTPUT_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "output not collected: the pipes were still held after the kill"
        state = {}
        inspected = self._docker("inspect", name, "--format", "{{json .State}}", check=False)
        if inspected.returncode == 0:
            state = json.loads(inspected.stdout)
        diff = self._docker("diff", name, check=False).stdout.split("\n") if inspected.returncode == 0 else []
        self._docker("rm", "-f", name, check=False)
        exit_code = state.get("ExitCode")
        if status == "OK" and state.get("OOMKilled"):
            status = "OOM_KILLED"
        elif status == "OK" and exit_code not in (0, None):
            status = "EXIT_NONZERO"
        return {"container": name, "status": status, "exit_code": exit_code, "oom_killed": state.get("OOMKilled"),
                "stdout": stdout[-4000:], "stderr": stderr[-4000:],
                "file_log": file_log(before, snapshot(workspace)),
                "container_diff": [line for line in diff if line.strip()],
                "policy": asdict(self.policy), "argv": argv, "docker_args": args}

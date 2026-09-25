"""`cain sandbox`: run a candidate in the container sandbox, or run the attack suite."""

from pathlib import Path
import subprocess


def register(sub):
    sandbox = sub.add_parser("sandbox", help="Container sandbox for model-generated code (attack suite included)")
    sandbox.add_argument("--image", required=True, help="pinned image (e.g. python:3.13-slim@sha256:...)")
    sandbox.add_argument("--docker", default="docker", help="docker CLI (docker.exe for Docker Desktop from WSL)")
    sandbox.add_argument("--windows-paths", action="store_true", help="translate mounts with wslpath -w")
    sandbox.add_argument("--runtime", help="container runtime, e.g. runsc (gVisor)")
    sandbox.add_argument("--timeout", type=float, default=60.0)
    sandbox.add_argument("--memory", default="512m")
    sandbox.add_argument("--cpus", type=float, default=1.0)
    sandbox.add_argument("--workspace-root", type=Path)
    commands = sandbox.add_subparsers(dest="sandbox_command", required=True)
    run = commands.add_parser("run", help="Run one candidate directory (candidate.py) with the guards")
    run.add_argument("--candidate", type=Path, required=True)
    run.add_argument("--evaluator-file", action="append", default=[])
    run.add_argument("--data", type=Path, help="directory mounted read-only at /data")
    attacks = commands.add_parser("attacks", help="Run the malicious test candidates and a benign one")
    attacks.add_argument("--evaluator-file", action="append", required=True)
    attacks.add_argument("--holdout-file", action="append", required=True)
    attacks.add_argument("--allowed-data", type=Path, required=True, help="CSV with a 'value' column")
    attacks.add_argument("--tamper-evaluator", action="store_true",
                         help="also simulate an out-of-band evaluator change (restored afterwards)")
    attacks.add_argument("--output", type=Path)


def execute(args):
    from cain.sandbox.attacks import dumps, run_attacks, summarize
    from cain.sandbox.attempt import run_attempt
    from cain.sandbox.runner import DockerSandbox, SandboxPolicy

    mapper = None
    if args.windows_paths:
        def mapper(path):
            return subprocess.run(["wslpath", "-w", str(path)], capture_output=True, text=True,
                                  check=True).stdout.strip()
    policy = SandboxPolicy(image=args.image, timeout=args.timeout, memory=args.memory, cpus=args.cpus,
                           runtime=args.runtime)
    sandbox = DockerSandbox(policy, docker=args.docker, path_mapper=mapper)
    if args.sandbox_command == "run":
        data = [(args.data, "/data")] if args.data else []
        return run_attempt(sandbox, args.candidate, evaluator_files=args.evaluator_file, data_ro=data,
                           workspace_root=args.workspace_root)
    hook = None
    if args.tamper_evaluator:
        target = Path(args.evaluator_file[0])
        original = target.read_bytes()

        def hook():
            target.write_bytes(original + b"\n# changed during the attempt\n")
    try:
        report = run_attacks(sandbox, evaluator_files=args.evaluator_file, holdout_files=args.holdout_file,
                             allowed_data=args.allowed_data, workspace_root=args.workspace_root, tamper_hook=hook)
    finally:
        if hook is not None:
            target.write_bytes(original)  # the simulated change is undone; the report keeps the evidence
    report["summary"] = summarize(report)
    if args.output:
        args.output.write_text(dumps(report), encoding="utf-8")
    return {"summary": report["summary"]}

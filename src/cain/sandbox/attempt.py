"""One sandboxed attempt with reward-hacking guards.

Around the container run:
* the evaluator files (on the host, never mounted) are hashed before and after; any divergence makes
  the attempt INVALID and raises an alert, whatever the attempt reported;
* outputs are read from the workspace only as regular files inside it (no symlink, no path escape,
  size-bounded), so a planted link cannot make the host read the evaluator or the holdout;
* integrity: every number in the attempt's report must appear in the run's real output (the same
  number extraction as the Prompt 3 report linter); a report that invents a better metric is rejected.

The manifest records the image identity (id and repo digests), the policy, the evaluator hashes, the
file log and the verdict: VALID, INVALID (evaluator changed, unsafe output, integrity failure) or
CRASH (timeout, out of memory, non-zero exit).
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4

from cain.claims.verify import number_values

MAX_OUTPUT = 1_000_000
_NUMBER = re.compile(r"(?<![\w.,])[-+]?\d+(?:[.,]\d+)*%?(?![\w])")


def hashes(files) -> dict[str, str | None]:
    return {str(f): (sha256(Path(f).read_bytes()).hexdigest() if Path(f).is_file() else None) for f in files}


def safe_read(workspace: Path, name: str) -> tuple[str | None, str | None]:
    """(text, problem): a regular file directly under the workspace, not a symlink, bounded."""
    root = workspace.resolve()
    path = workspace / name
    if path.is_symlink():
        return None, f"{name} is a symlink (to {path.readlink()}); refused"
    if not path.exists():
        return None, f"{name} missing"
    if not path.is_file() or path.resolve().parent != root:
        return None, f"{name} is not a regular file inside the workspace"
    if path.stat().st_size > MAX_OUTPUT:
        return None, f"{name} larger than {MAX_OUTPUT} bytes"
    return path.read_text(encoding="utf-8", errors="replace"), None


def integrity(report: str, output: str) -> dict:
    """Numbers in the report that the run's output does not contain."""
    produced = number_values(output)
    unsupported = [token for token in _NUMBER.findall(report) if not number_values(token) <= produced]
    return {"numbers_in_report": len(_NUMBER.findall(report)), "unsupported": unsupported,
            "ok": not unsupported}


def run_attempt(sandbox, candidate: Path, *, evaluator_files, argv=("python", "candidate.py"), data_ro=(),
                workspace_root: Path | None = None, output="output.json", report="report.md") -> dict:
    attempt_id = "attempt:" + uuid4().hex[:12]
    workspace = Path(tempfile.mkdtemp(prefix="cain-ws-", dir=workspace_root))
    workspace.chmod(0o777)  # the container runs as nobody; the workspace is the only writable mount
    shutil.copytree(candidate, workspace, dirs_exist_ok=True)
    for item in workspace.rglob("*"):
        item.chmod(0o777 if item.is_dir() else 0o666)
    before = hashes(evaluator_files)
    result = sandbox.run(workspace, list(argv), data_ro=data_ro)
    after = hashes(evaluator_files)
    manifest = {"attempt_id": attempt_id, "image": sandbox.image_identity(), "workspace": str(workspace),
                "evaluator": {"before": before, "after": after, "unchanged": before == after},
                "run": result, "alerts": []}
    problems = []
    if before != after:
        manifest["alerts"].append({"alert": "EVALUATOR_CHANGED",
                                   "files": [f for f in before if before[f] != after[f]]})
        problems.append("evaluator changed during the attempt")
    out_text, out_problem = safe_read(workspace, output)
    rep_text, rep_problem = safe_read(workspace, report)
    manifest["outputs"] = {"output": out_problem or "read", "report": rep_problem or "read"}
    if out_text is not None:
        try:
            manifest["output_json"] = json.loads(out_text)
        except ValueError:
            problems.append("output is not JSON")
    if rep_text is not None and out_text is not None:
        manifest["integrity"] = integrity(rep_text, out_text)
        if not manifest["integrity"]["ok"]:
            problems.append("report has numbers the run did not produce")
    for problem in (out_problem, rep_problem):
        if problem and ("symlink" in problem or "not a regular file" in problem):
            problems.append(problem)
    if out_problem and out_problem.endswith("missing") and result["status"] == "OK":
        problems.append(out_problem)  # a run that "succeeds" without its output proves nothing
    if result["status"] != "OK":
        verdict = "INVALID" if before != after else "CRASH"
    else:
        verdict = "INVALID" if problems else "VALID"
    manifest.update(verdict=verdict, problems=problems)
    return manifest

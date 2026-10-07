"""Freeze gate (programme item H05): a scientific run executes only on the exact frozen artefacts it registered.

Fail-closed checks, all mandatory:
1. ``FREEZE_MANIFEST.json`` exists in the frozen directory and lists ``files_sha256`` (or ``files``) for every frozen
   file; every frozen file present matches its recorded sha256 and no listed file is missing.
2. The manifest registers the freeze commit (``freeze_sha``; for the historical V2/V3 manifests, the commit that added
   the manifest is used when ``freeze_sha`` is absent and ``--allow-legacy-manifest`` is given).
3. ``RUN_SHA`` (``--run-sha``, default ``GITHUB_SHA``) is the registered freeze commit, or the frozen directory's git
   tree at ``RUN_SHA`` is identical to its tree at the freeze commit (``git rev-parse <sha>:<dir>``). Any other
   relation is FAIL_CLOSED: a frozen file edited after the freeze, or a run on an unregistered commit, never runs.
4. Optionally (``--design``) the design document's sha256 equals ``design_doc_sha256`` in the manifest.

Writes ``FREEZE_GATE.json`` next to the run (``--out``) with every value compared, and prints ``FREEZE_GATE = PASS``
or ``FREEZE_GATE = FAIL_CLOSED <reason>``. Exit code 0 only on PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def tree_of(repo: Path, sha: str, directory: str) -> str | None:
    """Signature of the frozen files at a commit: sorted (path, blob) pairs, the manifest itself excluded.

    The manifest records the freeze commit and may carry notes, so it necessarily changes after the freeze commit;
    the frozen *content* must not. Check 1 (file hashes vs manifest) still catches a manifest whose recorded hashes
    were edited to match altered files only if the files changed; a hash edit without a file change fails check 1 too.
    """
    try:
        listing = git("ls-tree", "-r", sha, "--", directory, cwd=repo)
    except subprocess.CalledProcessError:
        return None
    rows = []
    for line in listing.splitlines():
        meta, path = line.split("\t", 1)
        if path.endswith("FREEZE_MANIFEST.json") or "__pycache__" in path:
            continue
        rows.append(f"{meta.split()[2]} {path}")
    return hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest() if rows else None


def gate(frozen_dir: Path, run_sha: str | None, design: Path | None, allow_legacy: bool) -> dict:
    report: dict = {"schema": "freeze-gate/1", "frozen_dir": str(frozen_dir), "run_sha": run_sha, "checks": {}}
    reasons: list[str] = []
    manifest_path = frozen_dir / "FREEZE_MANIFEST.json"
    if not manifest_path.is_file():
        report["checks"]["manifest_present"] = False
        report["status"] = "FAIL_CLOSED"
        report["reasons"] = ["FREEZE_MANIFEST.json missing: the frozen directory is not frozen"]
        return report
    report["checks"]["manifest_present"] = True
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded: dict[str, str] = manifest.get("files_sha256") or manifest.get("files") or {}
    if isinstance(next(iter(recorded.values()), ""), dict):  # V2 style: {"name": {"sha256": ...}}
        recorded = {k: v["sha256"] for k, v in recorded.items()}
    if not recorded:
        reasons.append("manifest lists no frozen files")
    actual = {
        p.relative_to(frozen_dir).as_posix(): sha256_file(p)
        for p in sorted(frozen_dir.rglob("*"))
        if p.is_file() and p.name != "FREEZE_MANIFEST.json" and "__pycache__" not in p.parts and not p.name.endswith(".pyc")
    }
    mismatched = sorted(name for name, digest in recorded.items() if actual.get(name) != digest)
    unlisted = sorted(name for name in actual if name not in recorded)
    report["checks"]["files_recorded"] = len(recorded)
    report["checks"]["files_mismatched"] = mismatched
    report["checks"]["files_unlisted"] = unlisted
    if mismatched:
        reasons.append(f"frozen files differ from the manifest: {mismatched}")
    if unlisted:
        reasons.append(f"files in the frozen directory not covered by the manifest: {unlisted}")

    repo = Path(git("rev-parse", "--show-toplevel", cwd=frozen_dir))
    rel = frozen_dir.resolve().relative_to(repo.resolve()).as_posix()
    freeze_sha = manifest.get("freeze_sha")
    if not freeze_sha and allow_legacy:
        # Historical manifests (V2, V3) record the commit *before* the freeze; the freeze commit is the one that added
        # the manifest file.
        freeze_sha = git("log", "--format=%H", "--diff-filter=A", "-1", "--", "FREEZE_MANIFEST.json", cwd=frozen_dir) or None
        report["checks"]["freeze_sha_source"] = "legacy: commit that added FREEZE_MANIFEST.json"
    else:
        report["checks"]["freeze_sha_source"] = "manifest.freeze_sha"
    report["freeze_sha"] = freeze_sha
    if not freeze_sha:
        reasons.append("manifest registers no freeze_sha (set it at freeze time; legacy manifests need --allow-legacy-manifest)")
    if not run_sha:
        reasons.append("RUN_SHA unknown (pass --run-sha or set GITHUB_SHA)")
    if freeze_sha and run_sha:
        same_commit = run_sha.startswith(freeze_sha) or freeze_sha.startswith(run_sha)
        tree_run, tree_freeze = tree_of(repo, run_sha, rel), tree_of(repo, freeze_sha, rel)
        report["checks"]["run_sha_equals_freeze_sha"] = same_commit
        report["checks"]["frozen_tree_at_run"] = tree_run
        report["checks"]["frozen_tree_at_freeze"] = tree_freeze
        if tree_run is None or tree_freeze is None:
            reasons.append("frozen directory tree not resolvable at run or freeze commit (shallow clone? use fetch-depth: 0)")
        elif not same_commit and tree_run != tree_freeze:
            reasons.append("RUN_SHA != REGISTERED_FREEZE_SHA and the frozen files changed between them")
        if not same_commit:
            try:
                changed = git("diff", "--name-only", freeze_sha, run_sha, "--", rel, cwd=repo).splitlines()
            except subprocess.CalledProcessError:
                changed = []
            report["checks"]["paths_changed_since_freeze_commit"] = changed
        # a run commit with the same tree is allowed only because the tree hash proves byte identity of every frozen file
    if design is not None:
        expected = manifest.get("design_doc_sha256")
        got = sha256_file(design)
        report["checks"]["design_doc_sha256_matches"] = expected == got
        if expected != got:
            reasons.append(f"design document sha256 {got[:12]}… differs from manifest {str(expected)[:12]}…")
    report["status"] = "PASS" if not reasons else "FAIL_CLOSED"
    report["reasons"] = reasons
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frozen-dir", type=Path, required=True)
    ap.add_argument("--run-sha", default=os.environ.get("GITHUB_SHA"))
    ap.add_argument("--design", type=Path, default=None, help="design document whose sha256 the manifest records")
    ap.add_argument("--allow-legacy-manifest", action="store_true", help="derive freeze_sha from git for V2/V3 manifests")
    ap.add_argument("--out", type=Path, default=None, help="where to write FREEZE_GATE.json")
    args = ap.parse_args(argv)
    report = gate(args.frozen_dir.resolve(), args.run_sha, args.design, args.allow_legacy_manifest)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if report["status"] == "PASS":
        print("FREEZE_GATE = PASS", report.get("freeze_sha"), report.get("run_sha"))
        return 0
    print("FREEZE_GATE = FAIL_CLOSED " + "; ".join(report["reasons"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())

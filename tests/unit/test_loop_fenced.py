"""The loop that runs a predictor's evaluator directly is fenced out of the qualified runtime.

integration-crypto (prompt comum §4, option (b)): no console script of the installed distribution may reach
cain.loop.engine or cain.loop.evaluator (static import closure, including imports inside functions), `cain loop` is
not a command, and the lab tool stays available as `python -m cain.loop`. The orchestration reaches the domain only
through V2 tasks in the spool and never imports a domain package.
"""

import ast
import subprocess
import sys
from collections import deque
from importlib.metadata import distribution
from pathlib import Path

import cain

PACKAGE = Path(cain.__file__).resolve().parent
FENCED = {"cain.loop.engine", "cain.loop.evaluator"}
DOMAIN_PACKAGES = {"GarimpoInvestimentos", "stocks_predictor", "brasileirao_predictor", "predictor_core",
                   "predictor_ops"}


def module_name(path: Path) -> str:
    parts = list(path.relative_to(PACKAGE.parent).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def graph() -> dict[str, set[str]]:
    edges = {}
    for path in PACKAGE.rglob("*.py"):
        name = module_name(path)
        base = name.split(".") if path.name == "__init__.py" else name.split(".")[:-1]
        targets = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                targets.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = (".".join(base[: len(base) - (node.level - 1)] + ([node.module] if node.module else []))
                          if node.level else node.module or "")
                targets.add(module)
                targets.update(f"{module}.{a.name}" for a in node.names)
        edges[name] = targets
    return edges


def closure(root: str, edges: dict[str, set[str]]) -> tuple[set[str], set[str]]:
    modules, seen, external, queue = set(edges), {root}, set(), deque([root])

    def resolve(target):
        while target:
            if target in modules:
                return target
            target = target.rpartition(".")[0]
        return None

    while queue:
        current = queue.popleft()
        parts = current.split(".")
        for target in [".".join(parts[:i]) for i in range(1, len(parts))] + sorted(edges.get(current, ())):
            if target.startswith("cain"):
                local = resolve(target)
                if local and local not in seen:
                    seen.add(local)
                    queue.append(local)
            elif target:
                external.add(target.split(".")[0])
    return seen, external


def console_scripts() -> dict[str, str]:
    return {ep.name: ep.value.split(":")[0] for ep in distribution("cain-research").entry_points
            if ep.group == "console_scripts"}


def test_no_console_script_reaches_the_direct_evaluator_or_a_domain_package():
    edges = graph()
    report = {}
    for name, root in console_scripts().items():
        seen, external = closure(root, edges)
        report[name] = {"fenced": sorted(seen & FENCED), "domain": sorted(external & DOMAIN_PACKAGES)}
    assert report and all(not v["fenced"] and not v["domain"] for v in report.values()), report


def test_orchestration_is_reachable_from_the_cain_console_script():
    seen, _ = closure(console_scripts()["cain"], graph())
    for module in ("cain.orchestration.cli", "cain.orchestration.service", "cain.orchestration.policy",
                   "cain.orchestration.store", "cain.memory.store"):
        assert module in seen, module


def test_cain_loop_is_not_a_command_and_the_lab_tool_still_runs():
    done = subprocess.run([sys.executable, "-m", "cain", "loop", "status"], capture_output=True, text=True)
    assert done.returncode == 2 and "invalid choice" in done.stderr
    lab = subprocess.run([sys.executable, "-m", "cain.loop", "--help"], capture_output=True, text=True)
    assert lab.returncode == 0 and "run" in lab.stdout

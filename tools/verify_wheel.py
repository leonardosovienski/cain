"""Install the wheel in a clean temporary venv and run outside the checkout.

Dependencies come only from requirements exported from uv.lock, installed with
--require-hashes; the wheel itself is installed with --no-deps.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def verify(wheel, requirements):
    wheel, requirements = Path(wheel).resolve(strict=True), Path(requirements).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="cain-wheel-check-") as temporary:
        root = Path(temporary)
        if root.resolve().parent != Path(tempfile.gettempdir()).resolve():
            raise RuntimeError("Unexpected temporary verification root")
        environment = root / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--require-hashes", "-r", str(requirements)],
                       cwd=root, check=True, timeout=300)
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
                       cwd=root, check=True, timeout=120)
        script = r'''
import importlib.metadata as metadata
import importlib.resources as resources
import json
from pathlib import Path
import sys
import cain
import research_snapshot
import research_bundle
from cain.workspace import WorkspaceStore
assert Path(cain.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert Path(research_snapshot.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert Path(research_bundle.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert cain.__version__ == metadata.version("cain-research")
for asset in ("index.html", "app.js", "style.css"):
    assert resources.files("cain").joinpath("web", asset).read_bytes()
assert resources.files("research_snapshot").joinpath("contract.json").read_bytes()
assert resources.files("research_bundle").joinpath("contract.json").read_bytes()
store = WorkspaceStore("workspace.db")
project = store.create_project("wheel-user", "Wheel check")["id"]
store.add_document("wheel-user", project, "source.md", "Installed evidence")
assert list(store.document_corpus("wheel-user", project).values()) == ["Installed evidence"]
print(json.dumps({"version":cain.__version__, "module":cain.__file__, "isolated":True,
                  "assets_contract_workspace":"verified"}))
'''
        subprocess.run([str(python), "-I", "-c", script], cwd=root, check=True, timeout=30)
        subprocess.run([str(python), "-I", "-m", "cain", "--help"], cwd=root, check=True, timeout=30)
        subprocess.run([str(python), "-m", "pip", "check"], cwd=root, check=True, timeout=30)
    return {"wheel": wheel.name, "verification": "passed", "installation": "hashed lock requirements, noneditable clean venv"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True,
                        help="uv export --locked --no-emit-project output (hashed)")
    args = parser.parse_args()
    print(json.dumps(verify(args.wheel, args.requirements)))

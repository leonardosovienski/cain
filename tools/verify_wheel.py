"""Install the wheel in a clean temporary venv and run outside the checkout, offline."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def verify(wheel, vendor):
    wheel, vendor = Path(wheel).resolve(strict=True), Path(vendor).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="cain-wheel-check-") as temporary:
        root = Path(temporary)
        if root.resolve().parent != Path(tempfile.gettempdir()).resolve():
            raise RuntimeError("Unexpected temporary verification root")
        environment = root / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--find-links", str(vendor), str(wheel)],
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
    return {"wheel": wheel.name, "verification": "passed", "installation": "offline noneditable clean venv"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--vendor", type=Path, default=Path(__file__).resolve().parents[1] / "vendor")
    args = parser.parse_args()
    print(json.dumps(verify(args.wheel, args.vendor)))

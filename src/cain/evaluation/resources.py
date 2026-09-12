"""Resources shipped in the distribution and identity of executed package bytes."""
from hashlib import sha256
from importlib import metadata, resources
import json
from pathlib import Path


def data_root() -> Path:
    # Wheels are installed unpacked by pip. No checkout-relative fallback.
    return Path(str(resources.files('cain.evaluation').joinpath('data')))


def installed_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    hashes = {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*'))
              if p.is_file() and p.suffix in {'.py', '.json', '.md', '.html', '.css', '.js'}}
    try:
        version = metadata.version('cain-research')
    except metadata.PackageNotFoundError:
        version = None
    dependencies = {}
    for package, distribution in (('research_snapshot', 'predictor-research-snapshot'),):
        try:
            dependency_root = Path(str(resources.files(package)))
            dependencies[package] = dict(version=metadata.version(distribution), files={
                p.relative_to(dependency_root).as_posix(): sha256(p.read_bytes()).hexdigest()
                for p in sorted(dependency_root.rglob('*'))
                if p.is_file() and p.suffix in {'.py', '.json'}})
        except (metadata.PackageNotFoundError, ModuleNotFoundError):
            dependencies[package] = None
    identity = dict(cain=hashes, dependencies=dependencies)
    return dict(identity_kind='executed_package_bytes', package_version=version,
                git_commit=None, git_dirty=None, git_status=None, source_sha256=hashes,
                dependency_identity=dependencies,
                source_tree_sha256=sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest())

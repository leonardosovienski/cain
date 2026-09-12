"""Immutable local CAS. Durable bytes precede metadata; orphans are possible."""

import os
from pathlib import Path
import tempfile

from research_bundle import MAX_OBJECT, sha
from research_bundle.files import fsync_dir, no_links, safe_mkdirs, safe_open, transfer


class Objects:
    def __init__(self, root):
        self.root = Path(root).absolute()

    @staticmethod
    def relative(digest):
        sha(digest)
        return "sha256/" + digest[:2] + "/" + digest

    def verify(self, digest, size):
        with safe_open(self.root, self.relative(digest)) as source:
            transfer(source, limit=MAX_OBJECT, expected_sha=digest, expected_size=size)

    def receive(self, root, relative, digest, size):
        target = self.root / self.relative(digest)
        safe_mkdirs(target.parent)
        fd, name = tempfile.mkstemp(prefix=".staging-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as out:
                with safe_open(root, relative) as source:
                    transfer(source, out, limit=size, expected_sha=digest, expected_size=size)
                out.flush()
                os.fsync(out.fileno())
            try:
                os.link(name, target)
            except FileExistsError:
                self.verify(digest, size)
            # Also sync a concurrent writer's already linked object before commit.
            fsync_dir(target.parent)
        finally:
            Path(name).unlink(missing_ok=True)
        return target

    def materialize(self, digest, size, destination):
        destination = Path(destination).absolute()
        no_links(destination.parent)
        # Verify before exclusive destination creation, then verify the actual copied bytes.
        self.verify(digest, size)
        with safe_open(self.root, self.relative(digest)) as source:
            with destination.open("xb") as out:
                try:
                    transfer(source, out, limit=size, expected_sha=digest, expected_size=size)
                    out.flush()
                    os.fsync(out.fileno())
                except BaseException:
                    out.close()
                    destination.unlink(missing_ok=True)
                    raise
        fsync_dir(destination.parent)

    def inventory(self):
        if not self.root.exists():
            return [], []
        no_links(self.root)
        blobs, leftovers = [], []
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            for name in dirs + files:
                path = no_links(Path(directory) / name)
                if name in files:
                    relative = path.relative_to(self.root).as_posix()
                    if name.startswith(".staging-"):
                        leftovers.append(relative)
                    elif relative == self.relative(name):
                        blobs.append(name)
                    else:
                        raise ValueError("CORRUPTION: unexpected CAS file")
        return sorted(blobs), sorted(leftovers)

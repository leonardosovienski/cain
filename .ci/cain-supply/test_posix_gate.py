"""Additional POSIX probes prepared for Linux; never counted as executed on Windows."""
import errno
import os
from pathlib import Path
import runpy
import stat
import sys
from contextlib import contextmanager

import pytest
from research_bundle import files


@pytest.fixture
def subject(tmp_path):
    assert sys.platform == 'linux' and os.geteuid() != 0, 'Requires ordinary Linux user'
    root = Path(os.environ['CAIN_CANDIDATE_ROOT'])
    fixture = runpy.run_path(str(root / 'tests/test_research_bundle.py'))['setup'].__wrapped__
    return fixture(tmp_path)


@pytest.mark.parametrize('kind', ['file', 'directory', 'dangling', 'fifo'])
def test_real_unsafe_nodes(subject, tmp_path, kind):
    s, scope, _, root, _, _ = subject
    target = root / 'one/files/report.txt'
    target.unlink()
    outside = tmp_path / 'outside'
    if kind == 'fifo':
        os.mkfifo(target)
    else:
        if kind == 'file':
            outside.write_bytes(b'real test bytes')
        elif kind == 'directory':
            outside.mkdir()
        target.symlink_to(outside, target_is_directory=kind == 'directory')
    with pytest.raises((ValueError, OSError)):
        s.ingest('one/bundle.json', scope)
    assert s.query(scope)['total'] == 0


def test_directory_swapped_before_descriptor_open(subject, tmp_path, monkeypatch):
    s, scope, _, root, _, _ = subject
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'report.txt').write_bytes(b'real test bytes')
    original = files._posix_open
    swapped = False

    def swap(path, flags, *, dir_fd=None):
        nonlocal swapped
        if path == 'files' and not swapped:
            swapped = True
            (root / 'one/files').rename(root / 'one/original')
            (root / 'one/files').symlink_to(outside, target_is_directory=True)
        return original(path, flags, dir_fd=dir_fd)

    monkeypatch.setattr(files, '_posix_open', swap)
    with pytest.raises(ValueError, match='UNSAFE_PATH'):
        s.ingest('one/bundle.json', scope)
    assert swapped and s.query(scope)['total'] == 0


@pytest.mark.parametrize('state', ['exists', 'missing', 'corrupt'])
@pytest.mark.parametrize('rebuild', [False, True])
def test_revoked_blob_states_indistinguishable(subject, monkeypatch, state, rebuild):
    from research_bundle import canonical
    s, scope, b, _, policy_path, policy = subject
    s.ingest('one/bundle.json', scope)
    blob = s.objects.root / s.objects.relative(b['artifacts'][0]['sha256'])
    if state == 'missing':
        blob.unlink()
    elif state == 'corrupt':
        blob.write_bytes(b'corrupt')
    policy['bundle_grants'][0]['roles'] = []
    policy_path.write_bytes(canonical(policy))
    reads = []
    monkeypatch.setattr(s.objects, 'verify', lambda *args: reads.append(args))
    with pytest.raises(PermissionError, match='NOT_AUTHORIZED: complete scope required'):
        s.verify(scope, rebuild=rebuild)
    assert reads == []


def test_unreadable_cas_is_not_reported_verified(subject):
    s, scope, b, _, _, _ = subject
    s.ingest('one/bundle.json', scope)
    blob = s.objects.root / s.objects.relative(b['artifacts'][0]['sha256'])
    blob.chmod(0)
    try:
        with pytest.raises((ValueError, PermissionError)):
            s.verify(scope)
    finally:
        blob.chmod(0o600)


@pytest.mark.parametrize('point', ['mkdir', 'write', 'file_fsync', 'parent_fsync', 'link', 'final_fsync', 'db'])
def test_durability_failure_cannot_commit(subject, monkeypatch, point):
    from cain.research import objects
    s, scope, _, _, _, _ = subject

    def fail(*args, **kwargs):
        raise OSError(errno.EIO, 'injected ' + point)

    if point == 'mkdir':
        monkeypatch.setattr(objects, 'safe_mkdirs', fail)
    elif point == 'write':
        def partial(source, destination=None, **kwargs):
            destination.write(b'partial')
            fail()
        monkeypatch.setattr(objects, 'transfer', partial)
    elif point == 'parent_fsync':
        monkeypatch.setattr(files, 'fsync_dir', fail)
    elif point == 'final_fsync':
        monkeypatch.setattr(objects, 'fsync_dir', fail)
    elif point == 'file_fsync':
        real = os.fsync
        def sync(fd):
            if stat.S_ISREG(os.fstat(fd).st_mode):
                fail()
            real(fd)
        monkeypatch.setattr(os, 'fsync', sync)
    elif point == 'link':
        monkeypatch.setattr(os, 'link', fail)
    else:
        monkeypatch.setattr(s, '_project', fail)
    with pytest.raises(OSError):
        s.ingest('one/bundle.json', scope)
    assert s.query(scope)['total'] == 0
    if point in ('db', 'final_fsync'):
        assert s.orphan_report()['orphans']


def test_real_syscall_protocol_before_commit(subject, monkeypatch):
    s, scope, _, _, _, _ = subject
    events = []
    mkdir, sync, link = os.mkdir, os.fsync, os.link
    def recorded_mkdir(path, *args, **kwargs):
        result = mkdir(path, *args, **kwargs)
        events.append(('mkdir', str(Path(path).absolute())))
        return result
    def recorded_sync(fd):
        directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        sync(fd)
        events.append(('dir_fsync' if directory else 'file_fsync', os.readlink('/proc/self/fd/' + str(fd))))
    def recorded_link(*args, **kwargs):
        result = link(*args, **kwargs)
        events.append(('link', str(args[1])))
        return result
    connection = s.service.connection
    @contextmanager
    def traced():
        with connection() as db:
            db.set_trace_callback(lambda sql: events.append(('commit', '')) if sql == 'COMMIT' else None)
            yield db
    monkeypatch.setattr(os, 'mkdir', recorded_mkdir)
    monkeypatch.setattr(os, 'fsync', recorded_sync)
    monkeypatch.setattr(os, 'link', recorded_link)
    monkeypatch.setattr(s.service, 'connection', traced)
    s.ingest('one/bundle.json', scope)
    kinds = [kind for kind, _ in events]
    promoted = kinds.index('link')
    assert kinds.index('file_fsync') < promoted < kinds.index('dir_fsync', promoted) < kinds.index('commit')
    for index, (kind, path) in enumerate(events):
        if kind == 'mkdir' and Path(path).is_relative_to(s.objects.root):
            parent_sync = events.index(('dir_fsync', str(Path(path).parent)), index + 1)
            next_dirs = [i for i in range(index + 1, len(events)) if events[i][0] == 'mkdir']
            assert not next_dirs or parent_sync < next_dirs[0]


@pytest.mark.parametrize('action', ['mutate', 'delete'])
def test_source_changes_during_transfer(subject, action):
    _, _, _, root, _, _ = subject
    path = root / 'one/files/report.txt'
    with files.safe_open(root, 'one/files/report.txt') as stream:
        class Reader:
            changed = False
            def fileno(self):
                return stream.fileno()
            def read(self, size):
                data = stream.read(size)
                if not self.changed:
                    self.changed = True
                    if action == 'mutate':
                        path.write_bytes(b'changed source bytes')
                    else:
                        path.unlink()
                return data
        with pytest.raises(ValueError):
            files.transfer(Reader(), limit=1000)


def test_hard_link_source_is_copied_not_shared(subject, tmp_path):
    s, scope, b, root, _, _ = subject
    alias = tmp_path / 'source-alias'
    os.link(root / 'one/files/report.txt', alias)
    s.ingest('one/bundle.json', scope)
    alias.write_bytes(b'changed producer')
    s.materialize(scope, b['bundle_id'], 'a1', tmp_path / 'received-copy')
    assert (tmp_path / 'received-copy').read_bytes() == b'real test bytes'


def test_source_permission_revoked_after_approval(subject):
    s, scope, _, root, _, _ = subject
    path = root / 'one/files/report.txt'
    path.chmod(0)
    try:
        with pytest.raises(PermissionError):
            s.ingest('one/bundle.json', scope)
        assert s.query(scope)['total'] == 0
    finally:
        path.chmod(0o600)

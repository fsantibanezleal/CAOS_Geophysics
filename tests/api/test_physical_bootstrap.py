"""Closed lock-initialization fault controls, not a Linux OS receipt."""

from types import SimpleNamespace
import stat

import pytest

from app import physical_bootstrap as bootstrap


class LockOS:
    O_RDWR, O_CREAT, O_EXCL, O_CLOEXEC, O_NOFOLLOW, O_NONBLOCK = (1, 2, 4, 8, 16, 32)

    def __init__(self):
        self.records, self.descriptors, self.trace = {}, {}, []
        self.next_fd = 10
        self.fail_sync = None

    def open(self, name, flags, mode=None, *, dir_fd):
        assert dir_fd == 3 and flags & self.O_CLOEXEC and flags & self.O_NOFOLLOW
        if flags & self.O_EXCL:
            assert mode == 0o600
            if name in self.records:
                raise FileExistsError(name)
            self.records[name] = dict(st_dev=7, st_ino=self.next_fd, st_uid=19,
                st_mode=stat.S_IFREG | mode, st_size=0, st_nlink=1, body=b'')
        else:
            assert flags & self.O_NONBLOCK
        descriptor = self.next_fd
        self.next_fd += 1
        self.descriptors[descriptor] = name
        self.trace.append(('open', name, flags))
        return descriptor

    def write(self, descriptor, body):
        record = self.records[self.descriptors[descriptor]]
        assert not record['body']
        record.update(body=body, st_size=len(body))
        self.trace.append(('write', descriptor))
        return len(body)

    def fsync(self, descriptor):
        self.trace.append(('sync', descriptor))
        if descriptor == self.fail_sync:
            raise OSError('injected sync failure')

    def fstat(self, descriptor):
        return SimpleNamespace(**self.records[self.descriptors[descriptor]])

    def stat(self, name, *, dir_fd, follow_symlinks):
        assert dir_fd == 3 and follow_symlinks is False
        return SimpleNamespace(**self.records[name])

    def pread(self, descriptor, limit, offset):
        assert (limit, offset) == (2, 0)
        return self.records[self.descriptors[descriptor]]['body']

    def get_inheritable(self, descriptor):
        return False

    def geteuid(self):
        return 19

    def close(self, descriptor):
        del self.descriptors[descriptor]


@pytest.fixture
def transport(monkeypatch):
    system = LockOS()
    roots = []

    class Root:
        def __init__(self, path):
            self.fd, self.identity, self.closed = 3, (7, 1), False
            roots.append(self)

        def check_root(self):
            assert not self.closed
            system.trace.append(('root-check',))

        def close(self):
            self.closed = True

    monkeypatch.setattr(bootstrap, 'os', system)
    monkeypatch.setattr(bootstrap, 'PrivateFiles', Root)
    return system, roots


def test_exclusive_initialization_sync_order_and_existing_identity_no_rewrite(transport):
    system, roots = transport
    first = bootstrap.initialize_private_locks('/explicit-private-fixture')
    assert set(first) == {'.physical-writers.lock', '.processing-worker.lock'}
    assert [v['body'] for v in system.records.values()] == [b'\0', b'0']
    assert [v[0] for v in system.trace] == ['open', 'write', 'sync', 'sync',
                                         'open', 'write', 'sync', 'sync', 'root-check']
    system.trace.clear()
    assert bootstrap.initialize_private_locks('/explicit-private-fixture') == first
    assert all(item[0] not in ('write', 'sync') for item in system.trace)
    assert not system.descriptors and all(root.closed for root in roots)


@pytest.mark.parametrize('damage', ['mode', 'owner', 'links', 'device', 'marker', 'size', 'type'])
def test_existing_unsafe_locks_refused_without_overwrite(transport, damage):
    system, roots = transport
    bootstrap.initialize_private_locks('/explicit-private-fixture')
    record = system.records['.physical-writers.lock']
    changed = dict(mode=('st_mode', stat.S_IFREG | 0o644), owner=('st_uid', 20),
        links=('st_nlink', 2), device=('st_dev', 8), marker=('body', b'X'),
        size=('st_size', 2), type=('st_mode', stat.S_IFIFO | 0o600))[damage]
    record[changed[0]] = changed[1]
    before = {name: dict(value) for name, value in system.records.items()}
    with pytest.raises(ValueError, match='physical_bootstrap_existing_lock_refused'):
        bootstrap.initialize_private_locks('/explicit-private-fixture')
    assert system.records == before and not system.descriptors
    assert all(root.closed for root in roots)


def test_uncertain_file_sync_keeps_created_lock_and_closes_descriptors(transport):
    system, roots = transport
    system.fail_sync = 10
    with pytest.raises(OSError, match='injected sync failure'):
        bootstrap.initialize_private_locks('/explicit-private-fixture')
    assert system.records['.physical-writers.lock']['body'] == b'\0'
    assert '.processing-worker.lock' not in system.records
    assert not system.descriptors and all(root.closed for root in roots)


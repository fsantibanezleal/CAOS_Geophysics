"""Portable construction/order controls; real POSIX mode gate is separate."""
import ast
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from app import profile_linux_worker as worker
from app.errors import ApiError


def fixture(monkeypatch, *, existing=False, mode=0o700, uid=61901, changed=False, linked=False):
    calls = []
    data = Path('/private/data')
    def mkdir(name, permission, *, dir_fd):
        calls.append(('mkdir', name, permission, dir_fd))
        if existing:
            raise FileExistsError()
    def opened(name, flags, *, dir_fd):
        calls.append(('open', name, flags, dir_fd))
        if linked:
            raise OSError('no-follow link refused')
        return 11
    def fd(path):
        calls.append(('held', path))
        return 10 if path == data else 12
    def info(number):
        return SimpleNamespace(st_dev=1, st_ino=number if changed else 11,
            st_uid=uid, st_mode=stat.S_IFDIR|mode)
    monkeypatch.setattr(worker, 'directory_fd', fd)
    monkeypatch.setattr(worker, 'os', SimpleNamespace(mkdir=mkdir, open=opened, fstat=info,
        geteuid=lambda:61901, close=lambda number:calls.append(('close', number)),
        O_RDONLY=1, O_DIRECTORY=2, O_NOFOLLOW=4))
    return data,calls


@pytest.mark.parametrize('existing', [False, True])
def test_new_or_existing_private_parent_before_allocation(monkeypatch, existing):
    data,calls = fixture(monkeypatch, existing=existing)
    assert worker.private_stage_parent(data) == 11
    assert ('mkdir', '.job-staging', 0o700, 10) in calls
    assert ('open', '.job-staging', 7, 10) in calls
    assert ('close',10) in calls and ('close',12) in calls
    assert ('close',11) not in calls


@pytest.mark.parametrize('mode', [0o755,0o750,0o710,0o701,0o770,0o777])
def test_accessible_existing_parent_refused_without_chmod(monkeypatch, mode):
    data,calls = fixture(monkeypatch, existing=True, mode=mode)
    with pytest.raises(ApiError):
        worker.private_stage_parent(data)
    assert ('close',11) in calls and ('close',10) in calls
    assert all(call[0] != 'chmod' for call in calls)


@pytest.mark.parametrize('options', [dict(uid=0),dict(changed=True),dict(linked=True)])
def test_owner_replacement_and_link_refuse(monkeypatch, options):
    data,calls = fixture(monkeypatch, **options)
    with pytest.raises((ApiError,OSError)):
        worker.private_stage_parent(data)
    assert ('close',10) in calls


def test_execute_constructor_precedes_stage_and_privileged_birth_and_holds_parent():
    source = Path(worker.__file__).read_text()
    tree = ast.parse(source)
    execute = next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name == 'execute')
    body = ast.get_source_segment(source,execute)
    assert body.index('private_stage_parent(') < body.index('os.mkdir(job.id') < body.index('asyncio.create_subprocess_exec')
    assert 'os.close(stage_parent_fd)' in ast.get_source_segment(source,execute.body[-1])
    assert 'chmod' not in body


@pytest.mark.parametrize('module', ['worker.py','waveform_worker.py'])
def test_other_shared_producers_request_private_new_parents_and_stages(module):
    tree = ast.parse((Path(worker.__file__).parent/module).read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node,ast.Call) and
        isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and
        node.func.value.id in ('stage_root','stage') and node.func.attr == 'mkdir']
    assert len(calls) == 2
    for call in calls:
        assert any(arg.arg == 'mode' and isinstance(arg.value,ast.Constant) and arg.value.value == 0o700
            for arg in call.keywords)

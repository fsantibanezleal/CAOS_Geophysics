"""Portable adapter controls; no sudo, systemd, Linux process or science proof."""
import asyncio
from pathlib import PurePosixPath
import stat
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.processing_contract import canonical_bytes, sha256
from app.profile_linux_exec import SOURCE_FILES
from app import profile_linux_worker as adapter


def installed_fixture(monkeypatch):
    class NativePath(PurePosixPath):
        def lstat(self):
            return SimpleNamespace(st_uid=0,st_mode=stat.S_IFREG|0o644)

    source = NativePath("/opt/fasl-admission/closed-source")
    data = NativePath("/var/lib/fasl-private/geophysics")
    runtime = NativePath("/opt/fasl-admission/runtime")
    helper = source/"scripts/profile_linux_supervisor.py"
    body = b"fixed installed source"
    configuration = dict(schema="geophysics.profile-linux-config/v2",source_root=str(source),
        data_root=str(data),python=str(runtime/"bin/python"),python_sha256="a"*64,
        environment_root=str(runtime),environment_sha256="b"*64,
        import_closure="/opt/fasl-admission/closure/inventory.json",import_closure_sha256="c"*64,
        systemd_library="/usr/lib/x86_64-linux-gnu/libsystemd.so.0.38.0",systemd_library_sha256="d"*64,
        uid=61901,gid=61901,source_hashes={name:"e"*64 for name in SOURCE_FILES})
    configuration["source_hashes"]["scripts/profile_linux_supervisor.py"] = sha256(body)
    settings = SimpleNamespace(profile_linux_supervisor=helper,data_dir=data,
        database_path=data/"api.sqlite3",profile_python=runtime/"bin/python")
    job = SimpleNamespace(id=str(uuid4()))
    opened,closed = [],[]
    monkeypatch.setattr(adapter,"Path",NativePath)
    monkeypatch.setattr(adapter,"CONFIG",NativePath("/etc/fasl/geophysics-profile-runtime.json"))
    monkeypatch.setattr(adapter,"os",SimpleNamespace(name="posix",close=lambda fd:closed.append(fd)))
    monkeypatch.setattr(adapter,"directory_fd",lambda path:opened.append(path) or len(opened))
    monkeypatch.setattr(adapter,"regular_at",lambda fd,name,cap:
        canonical_bytes(configuration) if name == "geophysics-profile-runtime.json" else body)
    return settings,job,configuration,opened,closed,NativePath


def test_command_contains_only_fixed_installed_helper_and_canonical_job(monkeypatch):
    settings,job,_,opened,closed,_ = installed_fixture(monkeypatch)
    assert adapter.installed_command(settings,job) == ["/usr/bin/sudo","-n","/usr/bin/python3","-I","-B",
        str(settings.profile_linux_supervisor),job.id]
    assert len(opened) == 2 and closed == [1,2]


@pytest.mark.parametrize("change",[
    lambda s,c:setattr(s,"profile_linux_supervisor",PurePosixPath("/tmp/uploaded.py")),
    lambda s,c:setattr(s,"database_path",s.data_dir/"another.sqlite3"),
    lambda s,c:setattr(s,"profile_python",PurePosixPath("/tmp/python")),
    lambda s,c:c.update(data_root="/var/lib/another-private/root"),
    lambda s,c:c["source_hashes"].update({"scripts/profile_linux_supervisor.py":"0"*64}),
])
def test_installed_command_refuses_changed_authority_or_storage(monkeypatch,change):
    settings,job,configuration,_,closed,_ = installed_fixture(monkeypatch)
    change(settings,configuration)
    with pytest.raises(ApiError):
        adapter.installed_command(settings,job)
    assert closed and closed[0] == 1


@pytest.mark.parametrize("uid,mode",[(61901,stat.S_IFREG|0o644),(0,stat.S_IFREG|0o666),(0,stat.S_IFLNK|0o777)])
def test_worker_writable_or_symlink_installation_is_not_authority(monkeypatch,uid,mode):
    settings,job,_,_,closed,NativePath = installed_fixture(monkeypatch)
    monkeypatch.setattr(NativePath,"lstat",lambda self:SimpleNamespace(st_uid=uid,st_mode=mode))
    with pytest.raises(ApiError):
        adapter.installed_command(settings,job)
    assert closed == [1]


def test_bounded_diagnostics_refuse_before_unbounded_accumulation():
    async def read():
        stream = asyncio.StreamReader()
        stream.feed_data(b"x"*8193)
        stream.feed_eof()
        return await adapter.bounded_stream(stream,8192)
    with pytest.raises(ApiError):
        asyncio.run(read())


def test_bounded_stream_preserves_exact_bytes():
    async def read():
        stream = asyncio.StreamReader()
        stream.feed_data(b"root receipt\n")
        stream.feed_eof()
        return await adapter.bounded_stream(stream,65536)
    assert asyncio.run(read()) == b"root receipt\n"


def test_retained_writer_after_launcher_exit_has_bounded_drain(monkeypatch):
    monkeypatch.setattr(adapter,"STREAM_DRAIN_SECONDS",.01)
    async def read():
        stream = asyncio.StreamReader()
        stream.feed_data(b"complete bytes but no EOF")
        task = asyncio.create_task(adapter.bounded_stream(stream,65536))
        with pytest.raises(asyncio.TimeoutError):
            await adapter.finish_streams([task])
        assert task.cancelled()
    asyncio.run(read())


def test_transaction_time_cancel_is_cancelled_only_after_proved_extinction():
    current = SimpleNamespace(state="running",cancel_requested=True)
    with pytest.raises(ApiError) as error:
        adapter.eligible_publication(current,True)
    assert error.value.code == "user_cancelled"
    with pytest.raises(ApiError) as error:
        adapter.eligible_publication(current,False)
    assert error.value.code == "profile_extinction_unproved"
    current.cancel_requested = False
    adapter.eligible_publication(current,True)
    current.state = "failed"
    with pytest.raises(ApiError) as error:
        adapter.eligible_publication(current,True)
    assert error.value.code == "profile_execution_invalid"

"""Portable descriptor/archive negatives, not native rename or custody proof."""
from copy import deepcopy
import asyncio
import stat
import sys
from types import SimpleNamespace

import pytest

from app import profile_incomplete_recovery as archive
from app import profile_linux_exec as dto
from app.errors import ApiError
from test_profile_incomplete_custody import FakeFS, Node, records, terminal


def manifest_fixture():
    _,packet,authority,custody,_,_ = records()
    identifier = packet["job"]["id"]
    recovery = dict(schema="geophysics.profile-incomplete-recovery/v1",job_id=identifier,
        authority_sha256=dto.digest(dto.canonical(authority)),custody_sha256=dto.digest(dto.canonical(custody)),intent_sha256="7"*64,
        installation=deepcopy(authority["installation"]),retained_stage_identity=deepcopy(authority["stage_identity"]),
        terminal=terminal(identifier),execution_receipt="absent",known_root_copies_removed=True)
    return dict(schema="geophysics.profile-incomplete-stage/v1",job_id=identifier,
        request_sha256=packet["job"]["request_sha256"],ownership=dict(**dto.custody_relation(packet),terminal_state="failed"),
        installation=deepcopy(authority["installation"]),stage_identity=deepcopy(authority["stage_identity"]),members={},recovery=recovery)


def stage_model(monkeypatch,bodies=None):
    fs = FakeFS()
    fs.geteuid = lambda:61901
    node = Node(2**63+7,uid=61901,mode=stat.S_IFDIR|0o700)
    node.children = {name:Node(100+i,body=body,uid=61901,mode=stat.S_IFREG|0o600) for i,(name,body) in enumerate((bodies or {}).items())}
    fs.fds[9002] = node
    monkeypatch.setattr(archive,"os",fs)
    monkeypatch.setattr(archive,"regular_at",fs.capture)
    return fs,node


@pytest.mark.parametrize("bodies",[{}, {"stderr.txt":b""}, {"result.json":b"not admitted science", "linux-stderr.txt":b"diagnostic"}])
def test_empty_and_bounded_partial_archive_has_no_scientific_claim(monkeypatch,bodies):
    manifest = manifest_fixture()
    fs,node = stage_model(monkeypatch,bodies)
    manifest["members"] = archive.inventory(9002)
    archive.validate_manifest(manifest)
    descriptor = archive.incomplete_descriptor(manifest)
    assert descriptor["schema"] == "geophysics.profile-incomplete-custody/v1"
    assert descriptor["charged_bytes"] == 2*len(dto.canonical(manifest))+sum(len(body) for body in bodies.values())
    assert descriptor["manifest"] == manifest
    node.children["manifest.json"] = Node(888,body=dto.canonical(manifest),uid=61901,mode=stat.S_IFREG|0o400)
    archive.reverify(9002,manifest)
    assert "linux-execution.json" not in node.children
    assert not any(name in descriptor for name in ("resources","linux_execution","originals_reverified","guardian_status"))


@pytest.mark.parametrize("change",[
    lambda m:m.update(extra=1),lambda m:m.update(schema="geophysics.profile-retained-stage/v2"),
    lambda m:m["ownership"].update(extra=1),lambda m:m["ownership"].update(terminal_state="succeeded"),
    lambda m:m["installation"].update(extra=1),lambda m:m["stage_identity"].update(inode=True),
    lambda m:m["recovery"].update(resources={}),lambda m:m["recovery"].update(execution_receipt="present"),
    lambda m:m["recovery"].update(known_root_copies_removed=False),lambda m:m["recovery"].update(job_id=records()[1]["job"]["id"]),
    lambda m:m["recovery"]["retained_stage_identity"].update(inode=5),
    lambda m:m["members"].update({"linux-execution.json":{}}),
    lambda m:m["members"].update({"result.json":dict(device=17,inode=100,bytes=8*1024**2+1,sha256="a"*64)}),
    lambda m:m["members"].update({"result.json":dict(device=17,inode=100,bytes=True,sha256="a"*64)}),
])
def test_closed_incomplete_manifest_refuses_legacy_execution_and_forgery(change):
    value = manifest_fixture()
    change(value)
    with pytest.raises((ValueError,ApiError)):
        archive.validate_manifest(value)


@pytest.mark.parametrize("field",sorted(archive.retained_ownership.__globals__["OWNERSHIP_KEYS"]))
def test_all_eleven_ownership_fields_are_bound(field):
    value = manifest_fixture()
    expected = deepcopy(value["ownership"])
    value["ownership"][field] = "changed"
    with pytest.raises((ValueError,ApiError)):
        archive.validate_manifest(value,expected)


@pytest.mark.parametrize("name",["unknown","linux-execution.json","subdirectory","result-link"])
def test_unknown_stage_member_is_never_adopted(monkeypatch,name):
    _,node = stage_model(monkeypatch)
    node.children[name] = Node(33,body=b"unknown",uid=61901,mode=stat.S_IFREG|0o600)
    with pytest.raises(ApiError):
        archive.inventory(9002)


@pytest.mark.parametrize("change",[
    lambda n:n.info.__setattr__("st_uid",0),lambda n:n.info.__setattr__("st_nlink",2),
    lambda n:n.info.__setattr__("st_mode",stat.S_IFREG|0o644),
    lambda n:n.info.__setattr__("st_mode",stat.S_IFLNK|0o600),
])
def test_partial_file_owner_link_and_mode_are_checked(monkeypatch,change):
    _,node = stage_model(monkeypatch,{"result.json":b"partial"})
    change(node.children["result.json"])
    with pytest.raises(ApiError):
        archive.inventory(9002)


@pytest.mark.parametrize("replacement",["stage","file-id","file-bytes","manifest"])
def test_archive_reverification_refuses_replacement(monkeypatch,replacement):
    manifest = manifest_fixture()
    _,node = stage_model(monkeypatch,{"result.json":b"partial"})
    manifest["members"] = archive.inventory(9002)
    node.children["manifest.json"] = Node(888,body=dto.canonical(manifest),uid=61901,mode=stat.S_IFREG|0o400)
    if replacement == "stage":
        node.info.st_ino = 99
    elif replacement == "file-id":
        node.children["result.json"].info.st_ino = 999
    elif replacement == "file-bytes":
        node.children["result.json"].body = b"changed"
    else:
        node.children["manifest.json"].body = b"{}"
    with pytest.raises(ApiError):
        archive.reverify(9002,manifest)


def test_replay_requires_same_authority_but_fresh_terminal_can_change():
    original = manifest_fixture()["recovery"]
    fresh = deepcopy(original)
    for item in fresh["terminal"].values():
        item["kernel"]["state"] = "unpopulated_no_processes"
    archive.same_recovery_authority(original,fresh)
    fresh["authority_sha256"] = "a"*64
    with pytest.raises(ApiError):
        archive.same_recovery_authority(original,fresh)


def test_incomplete_dialect_does_not_weaken_existing_v2():
    from app.profile_linux_recovery import validate_manifest_ownership
    with pytest.raises(ValueError):
        validate_manifest_ownership(manifest_fixture())


def executor_model(monkeypatch,tmp_path,bodies):
    """Exercise the real async executor with modeled descriptors/privilege only."""
    config,packet,_,_,_,_ = records()
    job = SimpleNamespace(**packet["job"],result_key=None)
    dataset,raw,origin = (SimpleNamespace(**packet[name]) for name in ("dataset","raw","origin"))
    objects = {archive.ProcessingJob:job,archive.ObservationDataset:dataset,archive.RawAsset:raw,archive.SourceRecord:origin}
    class Session:
        def __init__(self):
            self.index = 0
        async def __aenter__(self):
            return self
        async def __aexit__(self,*args):
            pass
        async def get(self,model,identifier):
            return objects[model]
        async def execute(self,query):
            value = (dataset,raw,origin)[self.index]
            self.index += 1
            return SimpleNamespace(scalar_one=lambda:value)
    class Engine:
        async def dispose(self):
            pass
    async def migrated(engine):
        pass
    monkeypatch.setattr(archive,"make_engine",lambda settings:Engine())
    monkeypatch.setattr(archive,"async_sessionmaker",lambda *args,**kwargs:Session)
    monkeypatch.setattr(archive,"require_migration_head",migrated)
    settings = SimpleNamespace(data_dir=tmp_path)
    monkeypatch.setattr(archive,"installed_command",lambda *args,**kwargs:(["sudo","fixed",job.id],config))
    monkeypatch.setattr(archive,"checked_derived_path",lambda *args:tmp_path/"missing-derived.json")
    fs,node = stage_model(monkeypatch,bodies)
    fs.name = "posix"
    stage_parent = Node(30,uid=61901,mode=stat.S_IFDIR|0o700)
    archive_parent = Node(31,uid=61901,mode=stat.S_IFDIR|0o700)
    stage_parent.children[job.id] = node
    fs.fds[9003],fs.fds[9004] = stage_parent,archive_parent
    def directory(path):
        fs.next_fd += 1
        target = stage_parent if path.name == ".job-staging" else archive_parent
        fs.fds[fs.next_fd] = target
        return fs.next_fd
    monkeypatch.setattr(archive,"directory_fd",directory)
    cuts = {"write":None,"rename":False}
    def write(fd,name,body):
        assert name not in fs.fds[fd].children
        fs.events.append(("write",name))
        fs.fds[fd].children[name] = Node(1000+len(fs.events),body=body,uid=61901,mode=stat.S_IFREG|0o400)
        if cuts["write"] == name:
            cuts["write"] = None
            raise OSError("injected write interruption")
    def rename(source,name,target):
        assert name not in fs.fds[target].children
        fs.events.append(("rename",name))
        fs.fds[target].children[name] = fs.fds[source].children.pop(name)
        if cuts["rename"]:
            cuts["rename"] = False
            raise OSError("injected rename interruption")
    monkeypatch.setattr(archive,"write_exclusive",write)
    monkeypatch.setattr(archive,"rename_exclusive",rename)
    commands = []
    root_result = manifest_fixture()["recovery"]
    async def root_command(*args,**kwargs):
        commands.append(args)
        assert args == ("sudo","fixed","--recover-incomplete",job.id)
        held = dict(device=node.info.st_dev,inode=node.info.st_ino)
        authority = dto.custody_authority(config,packet,held,recovery=True)
        result = deepcopy(root_result)
        result.update(job_id=job.id,installation=authority["installation"],retained_stage_identity=held,
                      authority_sha256=dto.digest(dto.canonical(authority)),terminal=terminal(job.id))
        stdout,stderr = asyncio.StreamReader(),asyncio.StreamReader()
        stdout.feed_data(dto.canonical(result)+b"\n")
        stdout.feed_eof()
        stderr.feed_eof()
        class Process:
            returncode = 0
            async def wait(self):
                return 0
        process = Process()
        process.stdout,process.stderr = stdout,stderr
        return process
    monkeypatch.setattr(archive.asyncio,"create_subprocess_exec",root_command)
    return settings,job,fs,node,stage_parent,archive_parent,cuts,commands


@pytest.mark.parametrize("bodies",[{}, {"stderr.txt":b""}, {"result.json":b"unadmitted", "linux-stderr.txt":b"partial"}])
def test_real_executor_archives_exact_empty_or_partial_stage_without_state_change(monkeypatch,tmp_path,bodies):
    settings,job,fs,node,source,target,_,commands = executor_model(monkeypatch,tmp_path,bodies)
    before = deepcopy(job.__dict__)
    manifest = asyncio.run(archive.recover_incomplete_job(settings,job.id))
    assert job.__dict__ == before and job.id not in source.children and target.children[job.id] is node
    assert set(node.children) == set(bodies)|{"manifest.json"}
    assert len(commands) == 1
    replay = asyncio.run(archive.recover_incomplete_job(settings,job.id))
    assert replay == manifest and len(commands) == 2
    assert sum(item[0] == "rename" for item in fs.events) == 1


@pytest.mark.parametrize("cut",["intent","manifest","rename"])
def test_real_executor_replays_each_archive_cut_without_overwrite(monkeypatch,tmp_path,cut):
    settings,job,fs,node,source,target,cuts,_ = executor_model(monkeypatch,tmp_path,{"result.json":b"partial"})
    if cut == "rename":
        cuts["rename"] = True
    else:
        cuts["write"] = job.id+".intent.json" if cut == "intent" else "manifest.json"
    with pytest.raises(OSError,match="interruption"):
        asyncio.run(archive.recover_incomplete_job(settings,job.id))
    manifest = asyncio.run(archive.recover_incomplete_job(settings,job.id))
    assert job.id not in source.children and target.children[job.id] is node
    assert manifest["members"]["result.json"]["sha256"] == dto.digest(b"partial")
    assert sum(item[0] == "rename" for item in fs.events) == 1


@pytest.mark.parametrize("debt",["published","uncommitted","receipt","unknown-stage"])
def test_real_executor_refuses_unadmitted_derived_or_stage_debt(monkeypatch,tmp_path,debt):
    settings,job,fs,node,_,_,_,commands = executor_model(monkeypatch,tmp_path,{})
    if debt == "published":
        job.result_key = "already-published"
    elif debt == "uncommitted":
        # A real external pytest fixture, never product/raw data.
        (tmp_path/"missing-derived.json").touch()
    else:
        node.children["linux-execution.json" if debt == "receipt" else "unknown"] = Node(444,body=b"debt",uid=61901,mode=stat.S_IFREG|0o600)
    with pytest.raises(ApiError):
        asyncio.run(archive.recover_incomplete_job(settings,job.id))
    assert not commands and not any(item[0] in ("write","rename") for item in fs.events)


def test_interrupted_manifest_in_stage_is_charged_against_archive_cap(monkeypatch,tmp_path):
    settings,job,fs,node,_,_,cuts,_ = executor_model(monkeypatch,tmp_path,{"result.json":b"partial"})
    cuts["write"] = "manifest.json"
    with pytest.raises(OSError,match="interruption"):
        asyncio.run(archive.recover_incomplete_job(settings,job.id))
    manifest_bytes = len(node.children["manifest.json"].body)
    data_bytes = len(b"partial")
    # Existing usage includes the archive intent, NOT a manifest still in stage.
    monkeypatch.setattr(archive,"incomplete_usage",lambda fd:(archive.ARCHIVE_CAP-manifest_bytes-data_bytes+1,1))
    with pytest.raises(ApiError):
        asyncio.run(archive.recover_incomplete_job(settings,job.id))
    assert not any(item[0] == "rename" for item in fs.events)


@pytest.mark.parametrize("cause",["timeout","cancel","repeat-cancel","cancel-during-create","timeout-repeat-cancel"])
def test_actual_child_is_drained_before_singleton_and_descriptors_release(monkeypatch,tmp_path,cause):
    """Actual ordinary OS child/lock; descriptors and privileged reply modeled."""
    from app.worker import _worker_lock
    real_create = asyncio.create_subprocess_exec
    real_wait_for = asyncio.wait_for
    settings,job,fs,_,_,_,_,_ = executor_model(monkeypatch,tmp_path,{})
    children = []
    closed_live = []
    original_close = fs.close
    def close(fd):
        if children and children[0].returncode is None:
            closed_live.append(fd)
        original_close(fd)
    fs.close = close
    async def scenario():
        started = asyncio.Event()
        async def actual_child(*args,**kwargs):
            process = await real_create(sys.executable,"-I","-B","-c",
                "import time; time.sleep(0.35)",stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            children.append(process)
            started.set()
            if cause == "cancel-during-create":
                await asyncio.sleep(0.12)
            return process
        async def short_deadline(awaitable,timeout):
            return await real_wait_for(awaitable,0.01 if timeout == 45 else timeout)
        monkeypatch.setattr(archive.asyncio,"create_subprocess_exec",actual_child)
        monkeypatch.setattr(archive.asyncio,"wait_for",short_deadline)
        async def run():
            with _worker_lock(tmp_path):
                return await archive.recover_incomplete_job(settings,job.id)
        task = asyncio.create_task(run())
        try:
            await real_wait_for(started.wait(),5)
            if cause in ("cancel","repeat-cancel","cancel-during-create"):
                task.cancel()
            await asyncio.sleep(0.06)
            if cause in ("repeat-cancel","timeout-repeat-cancel"):
                task.cancel()
                await asyncio.sleep(0.03)
                task.cancel()
            assert children[0].returncode is None
            assert not task.done(), "caller returned while owned child remained alive"
            with pytest.raises(RuntimeError,match="owns the lock"):
                with _worker_lock(tmp_path):
                    pass
            assert not closed_live
            with pytest.raises(asyncio.TimeoutError if cause == "timeout" else asyncio.CancelledError):
                await real_wait_for(asyncio.shield(task),5)
            assert children[0].returncode == 0 and not closed_live
            with _worker_lock(tmp_path):
                pass
            assert not any(item[0] in ("write","rename") for item in fs.events)
        finally:
            # Only this disposable ordinary test child, never root/science.
            for child in children:
                if child.returncode is None:
                    child.kill()
                await child.wait()
            if not task.done():
                task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    asyncio.run(scenario())


@pytest.mark.parametrize("which",["stdout","stderr"])
def test_actual_overflow_writer_drains_without_receipt_or_cleanup(monkeypatch,tmp_path,which):
    from app.worker import _worker_lock
    real_create = asyncio.create_subprocess_exec
    settings,job,fs,_,_,_,_,_ = executor_model(monkeypatch,tmp_path,{})
    children = []
    async def child(*args,**kwargs):
        fd = 1 if which == "stdout" else 2
        process = await real_create(sys.executable,"-I","-B","-c",
            f"import os,time; os.write({fd}, b'x'*(2*1024**2)); time.sleep(0.1)",
            stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        children.append(process)
        return process
    monkeypatch.setattr(archive.asyncio,"create_subprocess_exec",child)
    async def scenario():
        try:
            with _worker_lock(tmp_path):
                with pytest.raises(ApiError):
                    await archive.recover_incomplete_job(settings,job.id)
            assert children[0].returncode == 0
            assert not any(item[0] in ("write","rename") for item in fs.events)
            with _worker_lock(tmp_path):
                pass
        finally:
            for process in children:
                if process.returncode is None:
                    process.kill()
                await process.wait()
    asyncio.run(scenario())

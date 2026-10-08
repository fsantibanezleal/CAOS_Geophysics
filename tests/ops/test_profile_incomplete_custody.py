"""Portable authored custody controls; no systemd, native fork or host proof."""
from copy import deepcopy
import inspect
import os
import stat
from types import SimpleNamespace

import pytest

from app import profile_linux_exec as dto
from test_profile_linux_launch import fixture, supervisor_module


def records():
    config,job,data,raw,origin = fixture()
    bodies = {"original":b"actual-fixture-original", "dataset.json":b"{\"partial\":true}"}
    raw.update(byte_count=len(bodies["original"]),sha256=dto.digest(bodies["original"]))
    data.update(byte_count=len(bodies["dataset.json"]),sha256=dto.digest(bodies["dataset.json"]),raw_sha256=raw["sha256"])
    origin["sha256"] = raw["sha256"]
    job["dataset_sha256"] = data["sha256"]
    job["request_json"].update(raw_sha256=raw["sha256"],dataset_sha256=data["sha256"])
    job["request_sha256"] = dto.digest(dto.canonical(job["request_json"]))
    packet = dict(job=job,dataset=data,raw=raw,origin=origin,bodies={})
    stage = dict(device=17,inode=2**63+7)
    authority = dto.custody_authority(config,packet,stage)
    launch = dto.construct_launch(config,job,data,raw,origin)
    members = {name:dict(device=17,inode=i+100,bytes=len(body),sha256=dto.digest(body))
               for i,(name,body) in enumerate(bodies.items())}
    wrapper = dict(command=launch["command"],environment=launch["environment"],stderr=launch["stage"]+"/stderr.txt",inputs=deepcopy(members))
    bodies["launch.json"] = dto.canonical(wrapper)
    members["launch.json"] = dict(device=17,inode=102,bytes=len(bodies["launch.json"]),sha256=dto.digest(bodies["launch.json"]))
    manifest = dict(schema="geophysics.profile-custody/v1",job_id=job["id"],authority_sha256=dto.digest(dto.canonical(authority)),
        directories={name:dict(device=17,inode=i+10) for i,name in enumerate(("custody","inputs","scratch"))},members=members)
    plan = dict(schema="geophysics.profile-linux-custody-plan/v1",job_id=job["id"],held_bytes=raw["byte_count"]+data["byte_count"],
        request_sha256=job["request_sha256"],raw_sha256=raw["sha256"],dataset_sha256=data["sha256"],invocation_sha256=authority["installation"]["invocation_sha256"])
    job["state"] = "failed"
    return config,packet,authority,manifest,plan,bodies


def terminal(identifier,*,kernel="absent"):
    return {unit:dict(manager=dict(MainPID="0",ActiveState="inactive",SubState="dead",ControlGroup=""),
                      kernel=dict(path="/sys/fs/cgroup/system.slice/"+unit,state=kernel))
            for unit in ("geophysics-profile-"+identifier+".service","geophysics-profile-guardian-"+identifier+".scope")}


class Node:
    def __init__(self,inode,*,body=None,uid=0,mode=None,device=17):
        self.children = {} if body is None else None
        self.body = body
        self.info = SimpleNamespace(st_dev=device,st_ino=inode,st_uid=uid,st_gid=61901,st_nlink=1,
            st_mode=(stat.S_IFDIR|0o750 if body is None else stat.S_IFREG|0o440) if mode is None else mode,
            st_size=0 if body is None else len(body),st_mtime_ns=1,st_ctime_ns=1)


class FakeFS:
    """Descriptor model for fault injection, not a filesystem qualification."""
    O_DIRECTORY = 0x10000
    O_NOFOLLOW = 0x20000
    O_NONBLOCK = 0x40000
    def __init__(self):
        self.root = Node(1)
        self.fds = {9000:self.root,9001:Node(2)}
        self.next_fd = 9100
        self.events = []
        self.cut = None

    def __getattr__(self,name):
        return getattr(os,name)

    def open(self,name,flags,*,dir_fd=None,**kwargs):
        node = self.fds[dir_fd].children[name]
        if stat.S_ISLNK(node.info.st_mode) or flags & self.O_DIRECTORY and not stat.S_ISDIR(node.info.st_mode):
            raise OSError("nofollow")
        self.next_fd += 1
        self.fds[self.next_fd] = node
        return self.next_fd

    def fstat(self,fd):
        return deepcopy(self.fds[fd].info)

    def stat(self,name,*,dir_fd,**kwargs):
        return deepcopy(self.fds[dir_fd].children[name].info)

    def listdir(self,fd):
        return list(self.fds[fd].children)

    def close(self,fd):
        self.fds.pop(fd)

    def fsync(self,fd):
        self.events.append(("fsync",fd))

    def unlink(self,name,*,dir_fd):
        self.events.append(("unlink",name))
        del self.fds[dir_fd].children[name]
        if self.cut == name:
            self.cut = None
            raise OSError("injected interruption after unlink")

    def rmdir(self,name,*,dir_fd):
        assert not self.fds[dir_fd].children[name].children
        self.events.append(("rmdir",name))
        del self.fds[dir_fd].children[name]
        if self.cut == name:
            self.cut = None
            raise OSError("injected interruption after rmdir")

    def capture(self,fd,name,cap):
        node = self.fds[fd].children[name]
        if len(node.body) > cap:
            raise ValueError("capture_size")
        return node.body

    def record(self,fd,name,body,gid):
        if name in self.fds[fd].children:
            raise FileExistsError(name)
        assert 0 < len(body) <= 65536
        self.events.append(("record",name))
        self.fds[fd].children[name] = Node(1000+len(self.events),body=body)
        self.fsync(fd)


def model(monkeypatch):
    values = records()
    config,packet,authority,manifest,plan,bodies = values
    identifier = packet["job"]["id"]
    fs = FakeFS()
    fs.root.children[identifier+".plan.json"] = Node(20,body=dto.canonical(plan),mode=stat.S_IFREG|0o600)
    fs.root.children[identifier+".custody-intent.json"] = Node(21,body=dto.canonical(authority))
    fs.root.children[identifier+".custody.json"] = Node(22,body=dto.canonical(manifest))
    custody = Node(10)
    custody.children = dict(inputs=Node(11),scratch=Node(12))
    custody.children["inputs"].children = {name:Node(manifest["members"][name]["inode"],body=body) for name,body in bodies.items()}
    fs.root.children[identifier] = custody
    module = supervisor_module()
    monkeypatch.setattr(module,"os",fs)
    monkeypatch.setattr(module,"supervisor_lock",lambda:9001)
    monkeypatch.setattr(module,"nonroot_query",lambda *args,**kwargs:packet)
    monkeypatch.setattr(module,"custody_directory",lambda *args:9000)
    monkeypatch.setattr(module,"capture",fs.capture)
    monkeypatch.setattr(module,"custody_record",fs.record)
    samples = []
    def extinction(*args):
        samples.append("fresh")
        return terminal(identifier)
    monkeypatch.setattr(module,"incomplete_extinction",extinction)
    return module,fs,values,samples


def reopen(fs):
    fs.fds[9000] = fs.root
    fs.fds[9001] = Node(2)


def test_prelaunch_authority_matches_terminal_without_mutating_or_relabelling():
    config,packet,authority,manifest,_,_ = records()
    before = deepcopy(packet)
    assert dto.custody_authority(config,packet,authority["stage_identity"],recovery=True) == authority
    dto.validate_custody_manifest(manifest,authority)
    assert packet == before
    assert len(dto.SOURCE_FILES) == 11
    source = inspect.getsource(supervisor_module().execute)
    assert source.index("custody_record(") < source.index("os.mkdir(identifier")
    assert source.index("persist_custody(") < source.index("start_guardian(") < source.index("subprocess.run(command")


@pytest.mark.parametrize("change",[
    lambda a,m:a.update(extra=1),lambda a,m:a.update(schema="geophysics.profile-linux-execution/v1"),
    lambda a,m:a["stage_identity"].update(inode=True),lambda a,m:a["stage_identity"].update(inode=2**64),
    lambda a,m:a["installation"].update(extra=1),lambda a,m:a["installation"]["source_hashes"].pop("data-pipeline/sources.py"),
    lambda a,m:m.update(extra=1),lambda a,m:m["directories"].update(extra={}),
    lambda a,m:m["members"].update(extra={}),lambda a,m:m["members"]["original"].update(bytes=1000001),
    lambda a,m:m["members"]["launch.json"].update(inode=-1),lambda a,m:m["members"]["dataset.json"].update(sha256="0"*64),
])
def test_closed_prelaunch_authority_rejects_forgery(change):
    _,_,authority,manifest,_,_ = records()
    change(authority,manifest)
    with pytest.raises(ValueError):
        dto.validate_custody_manifest(manifest,authority)


@pytest.mark.parametrize("which",[0,1])
@pytest.mark.parametrize("field,value",[("MainPID","2"),("ActiveState","active"),("SubState","running"),("ControlGroup","/foreign")])
def test_either_manager_group_must_be_inactive(which,field,value):
    identifier = records()[1]["job"]["id"]
    proof = terminal(identifier)
    list(proof.values())[which]["manager"][field] = value
    with pytest.raises(ValueError):
        dto.validate_incomplete_terminal(proof,identifier)


@pytest.mark.parametrize("which",[0,1])
@pytest.mark.parametrize("change",[lambda k:k.update(state="populated"),lambda k:k.update(path="/foreign"),lambda k:k.update(extra=1)])
def test_either_kernel_group_must_be_closed_and_empty(which,change):
    identifier = records()[1]["job"]["id"]
    proof = terminal(identifier)
    change(list(proof.values())[which]["kernel"])
    with pytest.raises(ValueError):
        dto.validate_incomplete_terminal(proof,identifier)


def test_missing_receipt_recovery_removes_only_known_copies_preserves_authority(monkeypatch,capsys):
    module,fs,values,samples = model(monkeypatch)
    config,packet,authority,_,_,_ = values
    identifier = packet["job"]["id"]
    assert module.recover_incomplete(config,dto,identifier) == 0
    final = module.decode(capsys.readouterr().out.encode(),65536)
    dto.validate_incomplete_recovery(final)
    assert final["retained_stage_identity"] == authority["stage_identity"]
    assert len(samples) == 3
    assert identifier not in fs.root.children and identifier+".plan.json" not in fs.root.children
    assert set(fs.root.children) == {identifier+suffix for suffix in (".custody-intent.json",".custody.json",".incomplete-recovery-intent.json",".incomplete-recovery.json")}
    assert all(key not in final for key in ("resources","originals_reverified","guardian_status","linux_execution"))
    intent_index = next(i for i,item in enumerate(fs.events) if item == ("record",identifier+".incomplete-recovery-intent.json"))
    assert intent_index < next(i for i,item in enumerate(fs.events) if item[0] == "unlink")
    reopen(fs)
    assert module.recover_incomplete(config,dto,identifier) == 0
    capsys.readouterr()


@pytest.mark.parametrize("cut",["original","dataset.json","launch.json","inputs","scratch","custody","plan"])
def test_each_cleanup_cut_is_resumable_from_immutable_authority(monkeypatch,capsys,cut):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    identifier = packet["job"]["id"]
    fs.cut = identifier if cut == "custody" else identifier+".plan.json" if cut == "plan" else cut
    with pytest.raises(OSError,match="interruption"):
        module.recover_incomplete(config,dto,identifier)
    reopen(fs)
    assert module.recover_incomplete(config,dto,identifier) == 0
    capsys.readouterr()
    assert identifier not in fs.root.children


@pytest.mark.parametrize("window",["no-authority","no-manifest","no-uuid","no-plan","no-scratch"])
def test_prelaunch_partial_and_legacy_debt_refuses_unchanged(monkeypatch,window):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    identifier = packet["job"]["id"]
    key = {"no-authority":identifier+".custody-intent.json","no-manifest":identifier+".custody.json","no-uuid":identifier,"no-plan":identifier+".plan.json"}.get(window)
    if key:
        del fs.root.children[key]
    else:
        del fs.root.children[identifier].children["scratch"]
    before = deepcopy(fs.root)
    with pytest.raises((ValueError,KeyError)):
        module.recover_incomplete(config,dto,identifier)
    assert fs.root.children.keys() == before.children.keys()
    assert not any(item[0] in ("unlink","rmdir","record") for item in fs.events)


@pytest.mark.parametrize("change",[
    lambda n:n.info.__setattr__("st_ino",999),lambda n:n.info.__setattr__("st_dev",999),
    lambda n:n.info.__setattr__("st_uid",61901),lambda n:n.info.__setattr__("st_nlink",2),
    lambda n:n.info.__setattr__("st_mode",stat.S_IFREG|0o640),lambda n:n.info.__setattr__("st_mode",stat.S_IFLNK|0o440),
    lambda n:setattr(n,"body",b"changed"),
])
def test_replaced_linked_writable_changed_copy_refuses_before_unlink(monkeypatch,change):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    identifier = packet["job"]["id"]
    change(fs.root.children[identifier].children["inputs"].children["original"])
    with pytest.raises(ValueError):
        module.recover_incomplete(config,dto,identifier)
    assert not any(item[0] in ("unlink","rmdir","record") for item in fs.events)


@pytest.mark.parametrize("where",["custody","inputs","scratch"])
@pytest.mark.parametrize("kind",["extra","identity","owner","writable"])
def test_directory_debt_refuses_before_mutation(monkeypatch,where,kind):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    identifier = packet["job"]["id"]
    node = fs.root.children[identifier]
    if where != "custody":
        node = node.children[where]
    if kind == "extra":
        node.children["unknown"] = Node(500,body=b"debt")
    elif kind == "identity":
        node.info.st_ino = 999
    elif kind == "owner":
        node.info.st_uid = 61901
    else:
        node.info.st_mode |= 0o020
    with pytest.raises(ValueError):
        module.recover_incomplete(config,dto,identifier)
    assert not any(item[0] in ("unlink","rmdir","record") for item in fs.events)


@pytest.mark.parametrize("change",[
    lambda c,p:c.update(python_sha256="9"*64),lambda c,p:p["job"].update(state="succeeded"),
    lambda c,p:p["job"].update(state="running"),lambda c,p:p["dataset"].update(owner_id=fixture()[1]["owner_id"]),
    lambda c,p:p["raw"].update(byte_count=1),lambda c,p:c["source_hashes"].update({"scripts/profile_linux_child.py":"9"*64}),
])
def test_foreign_installation_or_relation_refuses_before_mutation(monkeypatch,change):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    change(config,packet)
    with pytest.raises(ValueError):
        module.recover_incomplete(config,dto,packet["job"]["id"])
    assert not any(item[0] in ("unlink","rmdir","record") for item in fs.events)


def test_complete_receipt_uses_existing_recovery_only(monkeypatch):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    identifier = packet["job"]["id"]
    fs.root.children[identifier+".receipt.json"] = Node(500,body=b"{}")
    with pytest.raises(ValueError,match="execution_receipt_present"):
        module.recover_incomplete(config,dto,identifier)
    assert not any(item[0] in ("unlink","rmdir","record") for item in fs.events)


@pytest.mark.parametrize("which",[0,1])
@pytest.mark.parametrize("events,procs",[(b"populated 1\n",b""),(b"populated 0\n",b"99\n"),
                                        (b"populated 0\npopulated 1\n",b""),(b"frozen 0\n",b"")])
def test_fresh_native_counter_path_refuses_either_unproved_group(monkeypatch,which,events,procs):
    module = supervisor_module()
    identifier = records()[1]["job"]["id"]
    units = list(terminal(identifier))
    states = {unit:record["manager"] for unit,record in terminal(identifier).items()}
    monkeypatch.setattr(module,"recovery_extinction",lambda value:states)
    class PinnedPath:
        def __init__(self,value):
            self.value = value
        def __str__(self):
            return self.value
        def lstat(self):
            return None
    monkeypatch.setattr(module,"Path",PinnedPath)
    monkeypatch.setattr(module,"tree_fd",lambda path:units.index(str(path).split("/")[-1])+9100)
    monkeypatch.setattr(module,"os",SimpleNamespace(close=lambda fd:None))
    monkeypatch.setattr(module,"native",lambda fd,name: (events if name == "cgroup.events" else procs)
                        if fd == 9100+which else (b"populated 0\nfrozen 0\n" if name == "cgroup.events" else b""))
    with pytest.raises(ValueError,match="incomplete_populated_group"):
        module.incomplete_extinction(dto,identifier)


def test_record_budget_reserves_new_authority_without_raising_old_caps(monkeypatch):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    launch = dto.construct_recorded_launch(config,packet["job"],packet["dataset"],packet["raw"],packet["origin"])
    # Existing immutable authority is counted, not silently excluded as metadata.
    for _ in range(250):
        identifier = fixture()[1]["id"]
        fs.root.children[identifier+".receipt.json"] = Node(777,body=dto.canonical(dict(schema="geophysics.profile-linux-execution/v1",job_id=identifier)))
    with pytest.raises(ValueError,match="custody_receipt_cap"):
        module.prepare_custody_plan(9000,dto,packet,launch)
    assert not any(item[0] == "record" for item in fs.events)


@pytest.mark.parametrize("failure_sample",[1,2,3])
def test_extinction_is_fresh_before_inspection_mutation_and_final_return(monkeypatch,failure_sample):
    module,fs,values,_ = model(monkeypatch)
    config,packet,*_ = values
    identifier = packet["job"]["id"]
    samples = []
    def fresh(*args):
        samples.append(1)
        if len(samples) == failure_sample:
            raise ValueError("actual extinction unproved")
        return terminal(identifier)
    monkeypatch.setattr(module,"incomplete_extinction",fresh)
    with pytest.raises(ValueError,match="extinction unproved"):
        module.recover_incomplete(config,dto,identifier)
    assert identifier+".incomplete-recovery.json" not in fs.root.children
    if failure_sample < 3:
        assert not any(item[0] in ("unlink","rmdir") for item in fs.events)


@pytest.mark.parametrize("what",["plan","wrapper","intent","authority"])
def test_changed_historical_root_records_are_not_rewritten(monkeypatch,what):
    module,fs,values,_ = model(monkeypatch)
    config,packet,authority,manifest,_,_ = values
    identifier = packet["job"]["id"]
    if what == "plan":
        fs.root.children[identifier+".plan.json"].body = b"{}"
    elif what == "wrapper":
        fs.root.children[identifier].children["inputs"].children["launch.json"].body = b"{}"
    elif what == "intent":
        intent = dict(schema="geophysics.profile-incomplete-recovery-intent/v1",job_id=identifier,authority_sha256="a"*64,
                      custody_sha256=dto.digest(dto.canonical(manifest)))
        fs.root.children[identifier+".incomplete-recovery-intent.json"] = Node(44,body=dto.canonical(intent))
    else:
        authority["stage_identity"]["inode"] = 99
        fs.root.children[identifier+".custody-intent.json"].body = dto.canonical(authority)
    with pytest.raises(ValueError):
        module.recover_incomplete(config,dto,identifier)
    assert not any(item[0] in ("unlink","rmdir","record") for item in fs.events)


def test_actual_manifest_function_fsyncs_known_directories_before_record(monkeypatch):
    module,fs,values,_ = model(monkeypatch)
    _,packet,authority,_,_,_ = values
    identifier = packet["job"]["id"]
    del fs.root.children[identifier+".custody.json"]
    custody = fs.open(identifier,fs.O_DIRECTORY,dir_fd=9000)
    inputs = fs.open("inputs",fs.O_DIRECTORY,dir_fd=custody)
    module.persist_custody(9000,custody,inputs,dto,authority,61901)
    record = next(i for i,event in enumerate(fs.events) if event == ("record",identifier+".custody.json"))
    assert sum(event[0] == "fsync" for event in fs.events[:record]) == 3
    manifest = module.decode(fs.root.children[identifier+".custody.json"].body,65536)
    dto.validate_custody_manifest(manifest,authority)

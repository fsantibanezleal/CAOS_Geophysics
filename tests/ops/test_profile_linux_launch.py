"""Fixed launch construction: these controls do not execute systemd or science."""
from copy import deepcopy
from uuid import uuid4

import pytest

from app.profile_linux_exec import LaunchError, SOURCE_FILES, canonical, digest, construct_launch


def fixture():
    job_id, owner, project, dataset, asset, source = (str(uuid4()) for _ in range(6))
    config = {"schema":"geophysics.profile-linux-config/v3",
              "source_root":"/opt/fasl/geophysics/profile-source",
              "data_root":"/var/lib/fasl/geophysics/private",
              "custody_root":"/srv/fasl-data/geophysics-profile-custody",
              "python":"/opt/fasl/geophysics/profile-runtime/bin/python",
              "python_sha256":"a"*64,"environment_root":"/opt/fasl/geophysics/profile-runtime",
              "environment_sha256":"b"*64,"uid":61901,"gid":61901,
              "import_closure":"/opt/fasl/geophysics/closure/inventory.json",
              "import_closure_sha256":"f"*64,
              "systemd_library":"/usr/lib/x86_64-linux-gnu/libsystemd.so.0.38.0",
              "systemd_library_sha256":"1"*64,
              "source_hashes":{name:"c"*64 for name in SOURCE_FILES}}
    request = {"schema":"geophysics.processing-request/v1","job_id":job_id,
               "project_id":project,"dataset_id":dataset,"dataset_sha256":"d"*64,
               "method_id":"ert.topographic-profile/v1","parameters":{},
               "raw_asset_id":asset,"raw_sha256":"e"*64,"profile_child_sha256":"c"*64,
               "profile_code_hashes":{name:"c"*64 for name in ("ert.py","supplied_profiles.py","profile_mesh.py")}}
    job = {"id":job_id,"owner_id":owner,"project_id":project,"dataset_id":dataset,
           "dataset_sha256":"d"*64,"method_id":request["method_id"],"state":"running",
           "cancel_requested":False,"request_json":request,"request_sha256":digest(canonical(request)),
           "preflight":{"estimated_memory_bytes":268998016,"estimated_scratch_bytes":1070320,
                        "memory_limit_bytes":2147483648,"scratch_limit_bytes":67108864,"wall_limit_seconds":600}}
    data = {"id":dataset,"owner_id":owner,"project_id":project,"raw_asset_id":asset,
            "raw_sha256":"e"*64,"sha256":"d"*64,"byte_count":1234,
            "storage_key":f"derived/{owner}/{project}/datasets/{dataset}.json",
            "parser_version":"supplied-profile-original/v1","modality":"ert_profile"}
    raw = {"id":asset,"owner_id":owner,"project_id":project,"source_id":source,
           "sha256":"e"*64,"byte_count":5435,"storage_key":f"projects/{owner}/{project}/{asset}",
           "detected_format":"ert_ohm"}
    origin = {"id":source,"owner_id":owner,"project_id":project,"sha256":"e"*64,
              "rights_decision":"provider-link-only","private_storage_permission":"attested"}
    return config,job,data,raw,origin


def test_fixed_constructor_uses_immutable_relation_and_operator_configuration():
    values = fixture()
    before = deepcopy(values)
    launch = construct_launch(*values)
    assert values == before
    assert launch["unit"] == f'geophysics-profile-{values[1]["id"]}.service'
    assert launch["command"][0] == values[0]["python"]
    assert launch["command"][-2:] == ["--parameters","{}"]
    assert "MemoryMax=2147483648" in launch["properties"]
    assert "MemorySwapMax=0" in launch["properties"]
    assert "RuntimeMaxSec=600" in launch["properties"]
    assert "CapabilityBoundingSet=" in launch["properties"]
    assert "PrivateNetwork=yes" in launch["properties"]
    assert "BindsTo="+launch["guardian_scope"] in launch["properties"]
    assert "After="+launch["guardian_scope"] in launch["properties"]
    assert launch["environment"]["XDG_CONFIG_HOME"].startswith(launch["stage"]+"/")
    assert launch["authority"] == "constructor_only_not_host_qualification"


@pytest.mark.parametrize("change", [
    lambda c,j,d,r,s: c.update(uid=0),
    lambda c,j,d,r,s: c.update(gid=True),
    lambda c,j,d,r,s: c.update(data_root="/"),
    lambda c,j,d,r,s: c.update(source_root="/opt/../root"),
    lambda c,j,d,r,s: c.update(python="/usr/bin/python"),
    lambda c,j,d,r,s: c.update(source_hashes={}),
    lambda c,j,d,r,s: c.update(import_closure="/tmp/../inventory.json"),
    lambda c,j,d,r,s: c.update(import_closure_sha256="x"*64),
    lambda c,j,d,r,s: c.update(systemd_library="/tmp/libsystemd.so.0"),
    lambda c,j,d,r,s: c.update(schema="geophysics.profile-linux-config/v1"),
    lambda c,j,d,r,s: j.update(state="queued"),
    lambda c,j,d,r,s: j.update(cancel_requested=True),
    lambda c,j,d,r,s: j.update(method_id="arbitrary-native-plugin"),
    lambda c,j,d,r,s: j["request_json"].update(parameters={"command":"whoami"}),
    lambda c,j,d,r,s: j["request_json"].update(raw_sha256="0"*64),
    lambda c,j,d,r,s: j["request_json"].update(executable="/bin/sh"),
    lambda c,j,d,r,s: j["preflight"].update(memory_limit_bytes=2147483649),
    lambda c,j,d,r,s: d.update(owner_id=str(uuid4())),
    lambda c,j,d,r,s: d.update(storage_key="../../etc/shadow"),
    lambda c,j,d,r,s: r.update(storage_key="projects/other-project/original"),
    lambda c,j,d,r,s: r.update(byte_count=1000001),
    lambda c,j,d,r,s: s.update(private_storage_permission=None),
    lambda c,j,d,r,s: s.update(rights_decision="forbidden"),
])
def test_constructor_rejects_identity_privilege_path_source_and_limit_forgery(change):
    values = fixture()
    change(*values)
    with pytest.raises(LaunchError):
        construct_launch(*values)


def test_changed_request_cannot_be_admitted_by_only_rehashing_it():
    config,job,data,raw,origin = fixture()
    job["request_json"]["profile_child_sha256"] = "f"*64
    job["request_sha256"] = digest(canonical(job["request_json"]))
    with pytest.raises(LaunchError):
        construct_launch(config,job,data,raw,origin)


def supervisor_module():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("profile_supervisor_test",Path(__file__).resolve().parents[2]/"scripts/profile_linux_supervisor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("load,kernel_exists,accepted",[(b"not-found\n",False,True),(b"loaded\n",False,False),(b"not-found\n",True,False)])
def test_collected_unit_stop_requires_manager_and_kernel_absence(monkeypatch,load,kernel_exists,accepted):
    from types import SimpleNamespace
    module = supervisor_module()
    calls = []
    def run(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(returncode=5 if command[1] == "stop" else 0,stdout=load,stderr=b"not loaded")
    monkeypatch.setattr(module.subprocess,"run",run)
    monkeypatch.setattr(module.Path,"exists",lambda self:kernel_exists)
    unit = "geophysics-profile-"+str(uuid4())+".service"
    if accepted:
        module.stop(unit)
    else:
        with pytest.raises(ValueError):
            module.stop(unit)
    assert calls[0][0] == ["/usr/bin/systemctl","stop",unit]
    assert len(calls) == 2 and calls[1][0][-2:] == ["--property=LoadState","--value"]


def test_stop_cannot_target_an_unowned_name(monkeypatch):
    module = supervisor_module()
    monkeypatch.setattr(module.subprocess,"run",lambda *args,**kwargs:pytest.fail("must refuse before manager call"))
    with pytest.raises(ValueError):
        module.stop("unrelated.service")


def test_executing_supervisor_must_match_configured_source(monkeypatch):
    from pathlib import Path
    module = supervisor_module()
    source = Path(module.__file__).resolve().parents[1]
    body = b"actual pinned test bytes"
    config = dict(source_root=str(source),source_hashes={"scripts/profile_linux_supervisor.py":module.sha(body)})
    monkeypatch.setattr(module,"root_regular",lambda path,cap:body)
    module.verify_executing_supervisor(config)
    config["source_root"] = str(source/"another")
    with pytest.raises(ValueError):
        module.verify_executing_supervisor(config)
    config["source_root"] = str(source)
    config["source_hashes"]["scripts/profile_linux_supervisor.py"] = "0"*64
    with pytest.raises(ValueError):
        module.verify_executing_supervisor(config)


def test_source_closure_includes_the_actual_imported_provider_helper_and_ledger():
    assert "data-pipeline/sources.py" in SOURCE_FILES
    assert "data/source-ledger.json" in SOURCE_FILES


def tree_record(kind="file", **changes):
    value = dict(kind=kind, uid=0, gid=0, mode="0o444", dev=1, ino=2)
    if kind == "file":
        value.update(bytes=3, sha256="a"*64)
    elif kind == "link":
        value.update(mode="0o777", target="../runtime/bin/python3.13")
    else:
        value.update(mode="0o755")
    value.update(changes)
    return value


def test_complete_tree_policy_accepts_exact_root_immutable_authorized_inventory():
    # Authored snapshots only: these do not establish host ownership or imports.
    tree = {"lib":tree_record("directory"), "lib/module.py":tree_record(),
            "bin/python":tree_record("link")}
    supervisor_module().validate_inventory(deepcopy(tree), tree)


@pytest.mark.parametrize("change", [
    lambda t:t.update({"lib/sitecustomize.py":tree_record()}),
    lambda t:t.pop("lib/module.py"),
    lambda t:t["lib/module.py"].update(sha256="b"*64),
    lambda t:t["lib/module.py"].update(uid=61901),
    lambda t:t["lib/module.py"].update(mode="0o664"),
    lambda t:t["lib/module.py"].update(ino=3),
    lambda t:t["bin/python"].update(target="/tmp/other-python"),
    lambda t:t.update({"../other":tree_record()}),
])
def test_complete_tree_policy_refuses_unlisted_or_altered_import_entries(change):
    expected = {"lib":tree_record("directory"), "lib/module.py":tree_record(),
                "bin/python":tree_record("link")}
    observed = deepcopy(expected)
    change(observed)
    with pytest.raises(ValueError):
        supervisor_module().validate_inventory(observed, expected)


@pytest.mark.parametrize("record", [tree_record(uid=True),tree_record(mode="0o666"),
    tree_record(kind="socket"),tree_record(bytes=-1),tree_record(sha256="bad"),
    tree_record(extra="unknown"),tree_record(ino=True)])
def test_even_equal_authorized_snapshot_cannot_relax_fixed_entry_policy(record):
    with pytest.raises(ValueError):
        supervisor_module().validate_inventory({"member":deepcopy(record)}, {"member":record})


@pytest.mark.parametrize("exitcode,body",[(2,b""),(0,b"invalid-json"),(0,b"")])
def test_reader_never_signals_numeric_pid_after_owned_child_has_been_reaped(monkeypatch,exitcode,body):
    # Authored parent control path, not actual fork/PID-reuse qualification.
    import sys
    from types import SimpleNamespace
    module = supervisor_module()
    closed,reaped,signals = [],[],[]
    chunks = iter((body,b"")) if body else iter((b"",))
    monkeypatch.setitem(sys.modules,"resource",SimpleNamespace())
    monkeypatch.setattr(module.os,"pipe",lambda:(41,42))
    monkeypatch.setattr(module.os,"fork",lambda:23,raising=False)
    monkeypatch.setattr(module.os,"close",closed.append)
    monkeypatch.setattr(module.select,"select",lambda *args:([41],[],[]))
    monkeypatch.setattr(module.os,"read",lambda *args:next(chunks))
    monkeypatch.setattr(module.os,"waitpid",lambda pid,_:(reaped.append(pid) or (pid,exitcode)))
    monkeypatch.setattr(module.os,"waitstatus_to_exitcode",lambda value:value,raising=False)
    monkeypatch.setattr(module.os,"kill",lambda *args:signals.append(args))
    with pytest.raises(ValueError):
        module.nonroot_query({},"unused",None)
    assert reaped == [23] and signals == [] and sorted(closed) == [41,42]


def test_reader_fork_failure_closes_both_owned_pipe_descriptors(monkeypatch):
    import sys
    from types import SimpleNamespace
    module = supervisor_module()
    closed = []
    monkeypatch.setitem(sys.modules,"resource",SimpleNamespace())
    monkeypatch.setattr(module.os,"pipe",lambda:(41,42))
    monkeypatch.setattr(module.os,"fork",lambda:(_ for _ in ()).throw(OSError("fork")),raising=False)
    monkeypatch.setattr(module.os,"close",closed.append)
    with pytest.raises(OSError,match="fork"):
        module.nonroot_query({},"unused",None)
    assert sorted(closed) == [41,42]


@pytest.mark.parametrize("manager_result",[0,-110])
def test_fixed_scope_transport_marshals_held_pidfd_not_numeric_pid_and_releases_bus(monkeypatch,manager_result):
    # Authored native-call responses. Real FD transfer is a separate Linux gate.
    import ctypes as c
    from types import SimpleNamespace
    module = supervisor_module()
    appended,containers,released,methods = [],[],[],[]
    result_path = b"/org/freedesktop/systemd1/job/123"

    class Function:
        def __init__(self,callback):
            self.callback = callback
        def __call__(self,*args):
            return self.callback(*args)

    def assigned(target,value):
        c.cast(target,c.POINTER(c.c_void_p))[0] = value
        return 0

    def new_method(bus,target,*names):
        methods.append(names)
        return assigned(target,2)

    def append(message,kind,pointer):
        value = (c.cast(pointer,c.c_char_p).value if kind == b"s" else
                 c.cast(pointer,c.POINTER(c.c_int if kind == b"h" else c.c_uint64))[0])
        appended.append((kind,value))
        return 0

    def reply(bus,message,timeout,error,target):
        assert timeout == 5000000 and error is None
        assigned(target,3)
        return manager_result

    def read(message,kind,target):
        assert kind == b"o"
        c.cast(target,c.POINTER(c.c_char_p))[0] = result_path
        return 1

    library = SimpleNamespace(
        sd_bus_open_system=Function(lambda target:assigned(target,1)),
        sd_bus_message_new_method_call=Function(new_method),
        sd_bus_message_append_basic=Function(append),
        sd_bus_message_open_container=Function(lambda message,kind,signature:(containers.append((kind,signature)) or 0)),
        sd_bus_message_close_container=Function(lambda message:0),
        sd_bus_call=Function(reply),sd_bus_message_read_basic=Function(read),
        sd_bus_message_unref=Function(lambda value:released.append(("message",value.value))),
        sd_bus_close=Function(lambda value:released.append(("close",value.value))),
        sd_bus_unref=Function(lambda value:released.append(("bus",value.value))),
    )
    config = fixture()[0]
    config["systemd_library_sha256"] = module.sha(b"trusted-library")
    monkeypatch.setattr(module,"root_regular",lambda *args,**kwargs:b"trusted-library")
    monkeypatch.setattr(c,"CDLL",lambda path:library)
    scope = "geophysics-profile-guardian-11111111-1111-4111-8111-111111111111.scope"
    if manager_result < 0:
        with pytest.raises(ValueError,match="guardian_bus_call"):
            module.scope_transport(scope,57,600,config)
    else:
        assert module.scope_transport(scope,57,600,config) == result_path.decode()
    assert (b"s",b"PIDFDs") in appended and (b"h",57) in appended
    assert (b"s",b"PIDs") not in appended and (b"a",b"h") in containers
    assert methods == [(b"org.freedesktop.systemd1",b"/org/freedesktop/systemd1",
                        b"org.freedesktop.systemd1.Manager",b"StartTransientUnit")]
    assert released == [("message",3),("message",2),("close",1),("bus",1)]


def test_pseudo_counters_are_not_read_as_zero_size_artifacts(monkeypatch):
    """Portable reader mechanics, not cgroup or kernel-limit qualification."""
    module = supervisor_module()
    monkeypatch.setattr(module.os,"O_NOFOLLOW",0,raising=False)
    monkeypatch.setattr(module.os,"open",lambda *args,**kwargs:19)
    monkeypatch.setattr(module.os,"close",lambda fd:None)
    monkeypatch.setattr(module.os,"read",lambda *args:b"2147483648\n")
    assert module.native(3,"memory.max") == b"2147483648\n"
    monkeypatch.setattr(module.os,"read",lambda *args:b"")
    assert module.native(3,"cgroup.procs") == b""
    with pytest.raises(ValueError,match="kernel_counter_size"):
        module.native(3,"memory.peak")
    with pytest.raises(ValueError,match="counter_name"):
        module.native(3,"../../private")


def test_rss_sample_includes_exact_unit_members_but_not_departed_member(monkeypatch):
    """Membership projection only; these are authored counter observations."""
    module = supervisor_module()
    monkeypatch.setattr(module.Path,"read_text",lambda self:"VmRSS:\t100 kB\n")
    monkeypatch.setattr(module,"native",lambda fd,name:b"21\n22\n")
    assert module.unit_rss(3) == (204800,2)
    observations = iter((b"21\n22\n",b"22\n",b"22\n"))
    monkeypatch.setattr(module,"native",lambda fd,name:next(observations))
    assert module.unit_rss(3) == (102400,1)


def test_regular_identity_excludes_read_atime_but_retains_changes():
    from types import SimpleNamespace
    module = supervisor_module()
    fields = dict(st_dev=1,st_ino=2,st_mode=3,st_nlink=1,st_uid=0,st_gid=0,
                  st_size=20,st_mtime_ns=30,st_ctime_ns=40,st_atime_ns=50)
    before = SimpleNamespace(**fields)
    fields["st_atime_ns"] = 60
    assert module.identity(before) == module.identity(SimpleNamespace(**fields))
    fields["st_ctime_ns"] = 70
    assert module.identity(before) != module.identity(SimpleNamespace(**fields))


@pytest.mark.parametrize("split",range(1,7))
def test_cancel_frame_accepts_every_stream_split(split):
    frame = supervisor_module().CancellationFrame()
    assert frame.feed(b"CANCEL\n"[:split]) is None
    assert frame.feed(b"CANCEL\n"[split:]) == "owner_cancel"


@pytest.mark.parametrize("body",[b"bad",b"CANCEL\nCANCEL\n",b"CANCEL\r\n",b"CANCEL\nx",b"x"*1024])
def test_cancel_frame_rejects_malformed_or_multiple_messages(body):
    with pytest.raises(ValueError,match="cancel_frame"):
        supervisor_module().CancellationFrame().feed(body)


def test_cancellation_eof_is_not_a_scientific_input():
    assert supervisor_module().CancellationFrame().feed(b"") == "caller_eof"


def test_mount_custody_cannot_be_chosen_through_worker_directory():
    values = fixture()
    launch = construct_launch(*values)
    assert launch["host_stage"].startswith(values[0]["data_root"]+"/.job-staging/")
    assert launch["stage"] == f'{values[0]["custody_root"]}/{values[1]["id"]}/scratch'
    assert launch["held"] == f'{values[0]["custody_root"]}/{values[1]["id"]}/inputs'
    assert f'BindReadOnlyPaths={launch["held"]}' in launch["properties"]


@pytest.mark.parametrize("root",["/run/job-copies","/tmp/job-copies","/var/tmp/job-copies","/dev/shm/job-copies",
    "/opt/fasl/geophysics/profile-source/custody","/opt/fasl/geophysics/profile-runtime/custody",
    "/var/lib/fasl/geophysics/private/custody","/opt/fasl/geophysics/closure/custody",
    "/var/lib/fasl/geophysics"])
def test_application_custody_requires_nonoverlapping_external_configured_root(root):
    values = fixture()
    values[0]["custody_root"] = root
    with pytest.raises(LaunchError):
        construct_launch(*values)


def test_missing_external_custody_does_not_fall_back_to_system_temp():
    values = fixture()
    values[0].pop("custody_root")
    with pytest.raises(LaunchError):
        construct_launch(*values)


@pytest.mark.parametrize("split",range(1,5))
def test_guardian_completion_accepts_all_stream_splits(split):
    module = supervisor_module()
    buffer,outcome = module.guardian_frame(b"",b"DONE\n"[:split])
    assert outcome is None
    assert module.guardian_frame(buffer,b"DONE\n"[split:]) == (b"DONE\n","complete")


@pytest.mark.parametrize("body",[b"DONE\nDONE\n",b"DONE\r\n",b"unknown",b"DONE\nx"])
def test_guardian_completion_refuses_unknown_or_multiple_frames(body):
    with pytest.raises(ValueError,match="guardian_frame"):
        supervisor_module().guardian_frame(b"",body)


def test_guardian_control_eof_is_failure_not_completion():
    assert supervisor_module().guardian_frame(b"DO",b"") == (b"DO","caller_dead")


def test_guardian_manager_drain_uses_exact_unit_and_fresh_extinction(monkeypatch):
    # Authored manager responses only, not installed systemd death qualification.
    module = supervisor_module()
    unit = "geophysics-profile-11111111-1111-4111-8111-111111111111.service"
    stops = []
    monkeypatch.setattr(module,"stop",stops.append)
    monkeypatch.setattr(module,"show",lambda actual:{"MainPID":"0","ControlGroup":""})
    terminal,events,removed = module.drain_owned_unit(unit)
    assert stops == [unit] and terminal["MainPID"] == "0" and events is None and removed
    with pytest.raises(ValueError,match="guardian_unit"):
        module.drain_owned_unit("outside-owned-unit.service")
    assert stops == [unit]


def test_empty_manager_group_does_not_hide_populated_kernel_group(monkeypatch):
    module = supervisor_module()
    unit = "geophysics-profile-11111111-1111-4111-8111-111111111111.service"
    monkeypatch.setattr(module,"stop",lambda _:None)
    monkeypatch.setattr(module,"show",lambda _:{"MainPID":"0","ControlGroup":""})
    monkeypatch.setattr(module.Path,"exists",lambda _:True)
    monkeypatch.setattr(module,"tree_fd",lambda _:19)
    monkeypatch.setattr(module.os,"close",lambda _:None)
    monkeypatch.setattr(module,"native",lambda *args:b"populated 1\n")
    with pytest.raises(ValueError,match="stop_extinction_unproved"):
        module.drain_owned_unit(unit,timeout=0)


def test_present_empty_kernel_group_is_observed_not_reported_removed(monkeypatch):
    module = supervisor_module()
    unit = "geophysics-profile-11111111-1111-4111-8111-111111111111.service"
    monkeypatch.setattr(module,"stop",lambda _:None)
    monkeypatch.setattr(module,"show",lambda _:{"MainPID":"0","ControlGroup":""})
    monkeypatch.setattr(module.Path,"exists",lambda _:True)
    monkeypatch.setattr(module,"tree_fd",lambda _:19)
    monkeypatch.setattr(module.os,"close",lambda _:None)
    monkeypatch.setattr(module,"native",lambda *args:b"populated 0\n")
    assert module.drain_owned_unit(unit)[1:] == ("populated 0\n",False)


def test_custody_budget_admits_bounded_originals_not_unbounded_backup():
    supervisor_module().custody_budget([2*1024**2]*3,[65536]*255,3*1024**2)


@pytest.mark.parametrize("plans,receipts,new",[
    ([1]*4,[],1),([], [1]*256,1),([0],[],1),([True],[],1),
    ([3*1024**2+1],[],1),([], [65537],1),([],[],0),([],[],True),
    ([],[],3*1024**2+1),
])
def test_custody_budget_refuses_overflow_or_unknown_charges(plans,receipts,new):
    with pytest.raises(ValueError):
        supervisor_module().custody_budget(plans,receipts,new)


@pytest.mark.parametrize("failure",["parent_pidfd","first_pipe","second_pipe","fork","child_pidfd","ready","enroll"])
def test_guardian_startup_failure_closes_owned_descriptors_and_reaps_only_own_child(monkeypatch,failure):
    # Authored allocation/control responses. This does not execute fork, signals
    # or systemd, nor establish actual Linux guardian admission.
    module = supervisor_module()
    allocated,closed,reaped,signals = [],[],[],[]
    pidfd_calls = pipe_calls = 0

    def pidfd(pid):
        nonlocal pidfd_calls
        pidfd_calls += 1
        name = "parent_pidfd" if pidfd_calls == 1 else "child_pidfd"
        if failure == name:
            raise OSError(name)
        fd = 10 if pidfd_calls == 1 else 15
        allocated.append(fd)
        return fd

    def pipe():
        nonlocal pipe_calls
        pipe_calls += 1
        if failure == ("first_pipe" if pipe_calls == 1 else "second_pipe"):
            raise OSError("pipe")
        values = (11,12) if pipe_calls == 1 else (13,14)
        allocated.extend(values)
        return values

    def fork():
        if failure == "fork":
            raise OSError("fork")
        return 201

    def select(readers,*args):
        if failure == "ready":
            return [],[],[]
        return [13],[],[]

    def enroll(*args):
        raise OSError("enroll")

    monkeypatch.setattr(module.os,"geteuid",lambda:0,raising=False)
    monkeypatch.setattr(module.os,"getpid",lambda:101)
    monkeypatch.setattr(module.os,"pidfd_open",pidfd,raising=False)
    monkeypatch.setattr(module.os,"pipe",pipe)
    monkeypatch.setattr(module.os,"fork",fork,raising=False)
    monkeypatch.setattr(module.os,"close",closed.append)
    monkeypatch.setattr(module.os,"read",lambda *args:b"READY\n")
    monkeypatch.setattr(module.os,"kill",lambda pid,sig:signals.append((pid,sig)))
    monkeypatch.setattr(module.os,"waitpid",lambda pid,_:(reaped.append(pid) or (pid,0)))
    monkeypatch.setattr(module.signal,"pidfd_send_signal",lambda fd,sig:signals.append((fd,sig)),raising=False)
    monkeypatch.setattr(module.signal,"SIGKILL",9,raising=False)
    monkeypatch.setattr(module.select,"select",select)
    monkeypatch.setattr(module,"enroll_guardian",enroll)
    with pytest.raises((OSError,ValueError)):
        module.start_guardian("geophysics-profile-11111111-1111-4111-8111-111111111111.service",
                              "geophysics-profile-guardian-11111111-1111-4111-8111-111111111111.scope",600,fixture()[0])
    assert sorted(closed) == sorted(allocated)
    assert len(closed) == len(set(closed))
    if failure in ("child_pidfd","ready","enroll"):
        assert reaped == [201] and len(signals) == 1
    else:
        assert reaped == signals == []

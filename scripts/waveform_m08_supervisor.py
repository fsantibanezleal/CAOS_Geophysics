"""Fixed installed UUID-only waveform authority; never HTTP or database root."""
from __future__ import annotations

import base64
from contextlib import ExitStack, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import select
import stat
import sys
import time

CONFIG = Path("/etc/fasl/geophysics-waveform-runtime.json")
sys.dont_write_bytecode = True


def _require(value):
    if not value:
        raise ValueError("waveform_installation_invalid")


def _installed_bytes(path, cap):
    """Minimal pre-import trust barrier; no site or product package import."""
    _require(path.is_absolute())
    fd = os.open("/",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        for name in path.parts[1:-1]:
            child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
            before = os.fstat(child)
            if before.st_uid != 0 or before.st_mode & 0o022:
                os.close(child)
                _require(False)
            os.close(fd)
            fd = child
        member = os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=fd)
        try:
            info = os.fstat(member)
            _require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022 and 0 < info.st_size <= cap)
            with os.fdopen(os.dup(member),"rb") as stream:
                raw = stream.read(cap+1)
            after = os.fstat(member)
            _require(len(raw) == info.st_size and (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns) ==
                     (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns))
            return raw
        finally:
            os.close(member)
    finally:
        os.close(fd)


def bootstrap():
    _require(sys.platform == "linux" and os.getuid() == os.geteuid() == 0 and sys.flags.isolated and sys.flags.no_site)
    raw = _installed_bytes(CONFIG,65536)
    def pairs(items):
        result = {}
        for key,value in items:
            _require(key not in result)
            result[key] = value
        return result
    config = json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: _require(False))
    _require(type(config) is dict and type(config.get("source_root")) is str and
             re.fullmatch(r"/[A-Za-z0-9_./-]+",config["source_root"]))
    source = Path(config["source_root"])
    _require(source.is_absolute() and ".." not in source.parts and str(source) == config["source_root"])
    _require(Path(__file__).resolve() == source/"scripts/waveform_m08_supervisor.py")
    module_path = source/"scripts/waveform_m08_installation.py"
    expected = config.get("source_hashes",{}).get("scripts/waveform_m08_installation.py")
    _require(type(expected) is str and re.fullmatch("[a-f0-9]{64}",expected))
    _require(hashlib.sha256(_installed_bytes(module_path,2*1024**2)).hexdigest() == expected)
    spec = importlib.util.spec_from_file_location("waveform_m08_installation",module_path)
    authority = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = authority
    spec.loader.exec_module(authority)
    # Complete checked census precedes any reader/native product import.
    checked = authority.read_installation()
    authority.require(raw == authority.canonical(checked))
    os.chdir(checked["custody_root"])
    os.environ.clear()
    os.environ.update(authority.installed_environment(checked))
    sys.path.insert(0,str(source/"scripts"))
    return authority,checked


def held_identity(fd):
    info = os.fstat(fd)
    return dict(device=info.st_dev,inode=info.st_ino)


def directory_child(authority, parent, name, *, uid=0, gid=0, create=False):
    authority.require(type(name) is str and re.fullmatch(r"[A-Za-z0-9.-]{1,80}",name) and name not in (".",".."))
    if create:
        os.mkdir(name,0o700,dir_fd=parent)
    fd = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
    try:
        if create:
            os.fchown(fd,uid,gid)
            os.fsync(parent)
        info = os.fstat(fd)
        authority.require(info.st_uid == uid and info.st_gid == gid and stat.S_IMODE(info.st_mode) == 0o700)
        return fd
    except BaseException:
        os.close(fd)
        raise


def custody_inventory(authority, root, plans, runs, receipts, science_root):
    """No unknown adoption/deletion. Plan precedes every per-job directory."""
    authority.require(set(os.listdir(root)) == {".lock","plans","runs","receipts"})
    plan_names,run_names,receipt_names = set(os.listdir(plans)),set(os.listdir(runs)),set(os.listdir(receipts))
    sizes = []
    for name in plan_names:
        authority.require(name.endswith(".json"))
        identifier = authority.uuid(name[:-5])
        plan = authority.decode(authority.regular_at(plans,name,65536,root_owned=True),65536)
        authority.fields(plan,{"schema","job_id","request_sha256","input_bytes","stage","installation","record_sha256"})
        authority.require(plan["schema"] == "geophysics.waveform-custody-plan/v1" and plan["job_id"] == identifier)
        authority.digest(plan["request_sha256"])
        authority.digest(plan["record_sha256"])
        authority.validate_recorded_binding(plan["installation"])
        sizes.append(plan["input_bytes"])
    authority.require(run_names <= {name[:-5] for name in plan_names})
    authority.require(set(os.listdir(science_root)) <= {name[:-5] for name in plan_names})
    for name in run_names:
        held = directory_child(authority,runs,name)
        nested = []
        try:
            _,nested,inventory = exact_inventory(authority,held)
            for member,item in inventory.items():
                parts = member.split("/")
                authority.require(len(parts) <= 2)
                if len(parts) == 1 and parts[0] in ("miniseed","stationxml","request","admission.json"):
                    authority.require(item["kind"] == "file")
                    caps = dict(miniseed=16777216,stationxml=2097152,request=65536,**{"admission.json":65536})
                    authority.require(0 < item["bytes"] <= caps[parts[0]])
                elif parts[0] == "export":
                    if len(parts) == 1:
                        authority.require(item["kind"] == "directory")
                    else:
                        from waveform_m08_export import _name
                        _name(parts[1])
                        authority.require(item["kind"] == "file")
                elif re.fullmatch(r"export\.a4-[a-f0-9]{32}",parts[0]):
                    authority.require(item["kind"] == ("directory" if len(parts) == 1 else "file"))
                    authority.require(len(parts) == 1 or parts[1] in ("eligibility.json","release.json"))
                    if len(parts) == 2:
                        authority.require(0 < item["bytes"] <= 65536)
                else:
                    authority.require(False)
            authority.require(sum(item.get("bytes",0) for item in inventory.values()) <= 52690944)
        finally:
            for fd in nested:
                os.close(fd)
            os.close(held)
    for name in os.listdir(science_root):
        child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=science_root)
        try:
            info = os.fstat(child)
            authority.require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o711)
            # The observer alone removes its known empty per-run mount target.
            # Remaining contents are unresolved debt, never adopted on a launch.
            authority.require(not os.listdir(child))
        finally:
            os.close(child)
    retained = []
    for name in receipt_names:
        authority.require(name.endswith(".json"))
        authority.uuid(name[:-5])
        body = authority.regular_at(receipts,name,65536,root_owned=True)
        receipt = authority.decode(body,65536)
        authority.fields(receipt,{"schema","job","sources","installation","stage","root_custody",
                                  "outcome","lifecycle","native","calculation_sha256","members"})
        authority.require(body == authority.canonical(receipt) and
                          receipt["schema"] == "geophysics.waveform-linux-execution/v1" and
                          receipt["job"].get("id") == name[:-5])
        authority.validate_recorded_binding(receipt["installation"])
        retained.append(len(body))
    authority.custody_budget(sizes,retained,0)
    return sizes,retained


def copy_export(authority, source, destination, uid, gid):
    """Only the genuine independently sealed export; no numerical reconstruction."""
    from waveform_m08_export import verify_export
    from waveform_m08_files import open_output
    members = []
    with open_output(source) as lease:
        sealed = verify_export(lease)
        for name in sorted(lease.names(55)):
            with lease.open_regular(name) as stream:
                size = lease.file_size(stream)
                authority.require(0 < size <= 33554432)
                raw = stream.read(size+1)
                authority.require(len(raw) == size)
            authority.exclusive_at(destination,name,raw,uid=uid,gid=gid)
            members.append(dict(name=name,bytes=size,sha256=authority.sha(raw)))
        authority.require(sum(item["bytes"] for item in members) <= 33554432)
        return sealed.calculation_sha256,members


def commit_frame(fd, deadline):
    buffer = b""
    while time.monotonic() < deadline:
        ready,_,_ = select.select([fd],[],[],min(.1,max(0,deadline-time.monotonic())))
        if not ready:
            continue
        part = os.read(fd,8)
        if not part:
            return False
        buffer += part
        _require(len(buffer) <= 7 and (b"COMMIT\n".startswith(buffer) or b"CANCEL\n".startswith(buffer)))
        if buffer == b"CANCEL\n":
            return False
        if buffer == b"COMMIT\n":
            return True
    return False


def exact_inventory(authority, root):
    """Held finite root-owned custody snapshot before any postcommit deletion."""
    entries,held,pending,inventory = [],[],[(root,())],{}
    try:
        while pending:
            fd,prefix = pending.pop()
            authority.require(len(prefix) <= 4)
            for name in os.listdir(fd):
                authority.require(len(entries) < 80 and name not in (".","..") and "/" not in name)
                info = os.stat(name,dir_fd=fd,follow_symlinks=False)
                authority.require(info.st_uid == 0 and not info.st_mode & 0o022)
                key = "/".join((*prefix,name))
                if stat.S_ISDIR(info.st_mode):
                    child = directory_child(authority,fd,name)
                    held.append(child)
                    entries.append((fd,name,authority.file_identity(info),None))
                    pending.append((child,prefix+(name,)))
                    inventory[key] = {"kind":"directory"}
                else:
                    raw = authority.regular_at(fd,name,33554432,root_owned=True,empty=True)
                    digest = authority.sha(raw)
                    entries.append((fd,name,authority.file_identity(info),digest))
                    inventory[key] = dict(kind="file",bytes=len(raw),sha256=digest)
        return entries,held,inventory
    except BaseException:
        for fd in held:
            os.close(fd)
        raise


def cleanup_custody(authority, run_fd, expected_inventory):
    """Known success only; every entry verified before the first unlink."""
    held = []
    try:
        entries,held,inventory = exact_inventory(authority,run_fd)
        authority.require(inventory == expected_inventory)
        for parent,name,identity,digest in entries:
            authority.require(authority.file_identity(os.stat(name,dir_fd=parent,follow_symlinks=False)) == identity)
            if digest is not None:
                authority.require(authority.sha(authority.regular_at(parent,name,33554432,root_owned=True,empty=True)) == digest)
        # All root-owned ancestors are non-writable to app/science identities.
        for parent,name,_,digest in entries:
            if digest is not None:
                os.unlink(name,dir_fd=parent)
        for parent,name,_,digest in reversed(entries):
            if digest is None:
                os.rmdir(name,dir_fd=parent)
        os.fsync(run_fd)
    finally:
        for fd in held:
            os.close(fd)


def supervise(authority, config, identifier):
    import fcntl
    from waveform_m08_owned_reader import nonroot_query, product_bytes
    from waveform_m08_linux import read_admission, run_cli, LinuxCallerControl
    from waveform_m08_files import open_output
    began = time.monotonic()
    with ExitStack() as leases:
        root = authority.directory_fd(config["custody_root"],root_owned=True)
        leases.callback(os.close,root)
        # Installation precreates the closed authority namespace. No generic mkdir.
        plans,runs,receipts = [directory_child(authority,root,name) for name in ("plans","runs","receipts")]
        for fd in (plans,runs,receipts):
            leases.callback(os.close,fd)
        lock = os.open(".lock",os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
        leases.callback(os.close,lock)
        lock_info = os.fstat(lock)
        authority.require(stat.S_ISREG(lock_info.st_mode) and lock_info.st_uid == 0 and
                          lock_info.st_nlink == 1 and stat.S_IMODE(lock_info.st_mode) == 0o600 and lock_info.st_size == 0)
        # Bounded lock wait; no root-owned API/database writer lease is acquired.
        while True:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                authority.require(time.monotonic()-began < 3)
                time.sleep(.05)
        science_root = authority.directory_fd(config["science_work_root"],root_owned=True)
        leases.callback(os.close,science_root)
        authority.require(stat.S_IMODE(os.fstat(science_root).st_mode) == 0o711)
        sizes,retained = custody_inventory(authority,root,plans,runs,receipts,science_root)
        packet = nonroot_query(config,identifier)
        record = packet["record"]
        job = record["job"]
        stage = Path(config["data_root"])/".job-staging"/identifier
        stage_fd = authority.directory_fd(stage)
        leases.callback(os.close,stage_fd)
        info = os.fstat(stage_fd)
        authority.require(info.st_uid == config["uid"] and info.st_gid == config["gid"] and
                          stat.S_IMODE(info.st_mode) == 0o700 and not os.listdir(stage_fd))
        inputs = {name:base64.b64decode(packet["bodies"][name],validate=True) for name in ("miniseed","stationxml")}
        inputs["request"] = authority.canonical(job["request_json"]["scientific_request"])
        authority.custody_budget(sizes,retained,sum(len(body) for body in inputs.values()))
        installation = authority.installation_binding(config,identifier)
        plan = dict(schema="geophysics.waveform-custody-plan/v1",job_id=identifier,request_sha256=job["request_sha256"],
                    input_bytes=sum(len(body) for body in inputs.values()),stage=held_identity(stage_fd),
                    installation=installation,record_sha256=authority.sha(product_bytes(record)))
        plan_bytes = authority.canonical(plan)
        authority.exclusive_at(plans,identifier+".json",plan_bytes)
        run_fd = directory_child(authority,runs,identifier,create=True)
        leases.callback(os.close,run_fd)
        os.mkdir(identifier,0o700,dir_fd=science_root)
        science_anchor = os.open(identifier,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=science_root)
        leases.callback(os.close,science_anchor)
        os.fchmod(science_anchor,0o711)
        os.fsync(science_root)
        fcntl.flock(lock,fcntl.LOCK_UN)
        parent = Path(config["custody_root"])/"runs"/identifier
        for name,body in inputs.items():
            authority.exclusive_at(run_fd,name,body)
        admission,admission_sha = read_admission(config["admission_path"],config["python"])
        authority.require(admission_sha == config["admission_sha256"] and admission["uid"] == config["science_uid"]
                          and admission["gid"] == config["science_gid"] and admission["site_packages"] == config["site_packages"])
        with open_output(parent) as lease:
            bound = deepcopy(admission)
            bound["parent"] = dict(path=str(parent),identity=list(lease.identity),
                context_receipt_sha256=authority.sha(authority.canonical(dict(job_id=identifier,installation=installation,
                                                                             identity=list(lease.identity)))))
        bound_bytes = authority.canonical(bound)
        authority.exclusive_at(run_fd,"admission.json",bound_bytes)
        caller = LinuxCallerControl(0)
        lifecycle = {}
        logs = io.StringIO()
        with redirect_stderr(logs):
            outcome = run_cli(dict(mseed=parent/"miniseed",stationxml=parent/"stationxml",request=parent/"request",
                                   out=parent/"export",python=config["python"]),None,parent/"admission.json",
                              caller=caller,lifecycle=lifecycle,work_root=Path(config["science_work_root"])/identifier)
        authority.require(len(logs.getvalue().encode("utf-8")) <= 65536)
        # Snapshot identity precedes EVERY terminal classification, including
        # cancel/EOF/failure. Never substitute today's epoch after launch.
        authority.validate_installation_binding(authority.installation_binding(authority.read_installation(),identifier),checked=installation)
        native = None
        calculation_sha = None
        members = []
        if outcome.get("reason") == "measured":
            # Refuse epoch changes BEFORE copy/publication; never adopt new root config.
            authority.require(nonroot_query(config,identifier) == packet)
            caller.check()
            authority.require(lifecycle.get("extinction_proved") is True)
            native_name = "export.a4-"+outcome["run_id"]
            native_fd = directory_child(authority,run_fd,native_name)
            leases.callback(os.close,native_fd)
            native_bytes = {name:authority.regular_at(native_fd,name+".json",65536,root_owned=True)
                            for name in ("eligibility","release")}
            native = {name:authority.decode(raw,65536) for name,raw in native_bytes.items()}
            export_fd = directory_child(authority,stage_fd,"export",uid=config["uid"],gid=config["gid"],create=True)
            leases.callback(os.close,export_fd)
            calculation_sha,members = copy_export(authority,parent/"export",export_fd,config["uid"],config["gid"])
        receipt = dict(schema="geophysics.waveform-linux-execution/v1",job={
            **{name:job[name] for name in ("id","owner_id","project_id","dataset_id","dataset_sha256","request_sha256","method_id")},
            **{name:job["request_json"][name] for name in ("implementation_sha256","scientific_request_sha256")}},
            sources=job["request_json"]["waveform_sources"],installation=installation,stage=held_identity(stage_fd),
            root_custody={**held_identity(run_fd),"plan_sha256":authority.sha(plan_bytes)},
            outcome=outcome,lifecycle=lifecycle,native=native,calculation_sha256=calculation_sha,members=members)
        body = authority.canonical(receipt)
        authority.require(len(body) <= 65536)
        authority.exclusive_at(receipts,identifier+".json",body)
        authority.exclusive_at(stage_fd,"root_receipt.json",body,uid=config["uid"],gid=config["gid"])
        # One bounded terminal packet; caller must validate it before classification.
        sys.stdout.write(body.decode("ascii")+"\n")
        sys.stdout.flush()
        if outcome.get("reason") != "measured" or not lifecycle.get("extinction_proved"):
            return 5
        if not commit_frame(0,began+120):
            return 5  # No commit acknowledgement: retain exact root plan/copies.
        caller.reason = None
        # Root has no SQL authority. Only the ordinary worker sends COMMIT after
        # scientific/member validation and its successful publication transaction.
        expected = {name:dict(kind="file",bytes=len(raw),sha256=authority.sha(raw))
                    for name,raw in {**inputs,"admission.json":bound_bytes}.items()}
        expected.update({"export":{"kind":"directory"},native_name:{"kind":"directory"}})
        expected.update({"export/"+member["name"]:dict(kind="file",bytes=member["bytes"],sha256=member["sha256"])
                         for member in members})
        expected.update({native_name+"/"+name+".json":dict(kind="file",bytes=len(raw),sha256=authority.sha(raw))
                         for name,raw in native_bytes.items()})
        cleanup_custody(authority,run_fd,expected)
        os.rmdir(identifier,dir_fd=runs)
        authority.require(not os.listdir(science_anchor))
        os.rmdir(identifier,dir_fd=science_root)
        authority.require(authority.regular_at(plans,identifier+".json",65536,root_owned=True) == plan_bytes)
        os.unlink(identifier+".json",dir_fd=plans)
        os.fsync(plans)
        os.fsync(runs)
        sys.stdout.write("CLEAN\n")
        sys.stdout.flush()
        return 0


def refusal_diagnostic(error, identifier=None, config=None, authority=None):
    """Private bounded source location only; never a native terminal or proof."""
    from uuid import UUID
    classes = {kind:kind.__name__ for kind in
               (MemoryError,ValueError,TypeError,KeyError,OSError,EOFError,RuntimeError,AssertionError)}
    job = None
    try:
        if type(identifier) is str and str(UUID(identifier)) == identifier:
            job = identifier
    except (ValueError,TypeError,AttributeError):
        pass
    value = dict(schema="geophysics.waveform-private-refusal/v1",reason="supervision_refused",
                 error_kind=classes.get(type(error),"OtherError"),job_id=job,
                 configuration_sha256=None,source_revision=None,source_map_sha256=None,
                 frames=[],native_proof=False)
    try:
        authority.validate_configuration(config)
        raw = authority.canonical(config)
        _require(len(raw) <= 65536)
        registered = {str(Path(config["source_root"])/name):name for name in authority.SOURCE_FILES}
        frames = []
        trace = error.__traceback__
        # Never extract/format a traceback: those helpers may read private source.
        for _ in range(64):
            if trace is None:
                break
            source = registered.get(trace.tb_frame.f_code.co_filename)
            line = trace.tb_lineno
            if source is not None and type(line) is int and 0 < line <= 2147483647:
                frames.append(dict(source=source,sha256=config["source_hashes"][source],line=line))
                frames = frames[-8:]
            trace = trace.tb_next
        value.update(configuration_sha256=authority.sha(raw),source_revision=config["source_revision"],
                     source_map_sha256=authority.sha(authority.canonical(config["source_hashes"])),frames=frames)
    except (AttributeError,ValueError,TypeError,KeyError):
        # An unavailable binding is not reconstructed from paths or current files.
        pass
    body = b"M08_SUPERVISION_DIAGNOSTIC:"+json.dumps(value,sort_keys=True,separators=(",",":"),
                                                     ensure_ascii=True,allow_nan=False).encode("ascii")+b"\n"
    _require(len(body) <= 8192)
    return body


def main():
    authority = config = identifier = None
    try:
        authority,config = bootstrap()
        authority.require(len(sys.argv) == 2)
        identifier = authority.uuid(sys.argv[1])
        return supervise(authority,config,identifier)
    except BaseException as error:
        # The caller retains this bounded private pipe, never serves it over HTTP.
        try:
            sys.stderr.write(refusal_diagnostic(error,identifier,config,authority).decode("ascii"))
        except BaseException:
            sys.stderr.write("waveform_supervision_refused\n")
        return 5


if __name__ == "__main__":
    raise SystemExit(main())

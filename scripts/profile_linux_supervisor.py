"""Fixed installation-owned Linux profile launcher. No public activation.

Run only through the reviewed narrowly scoped operator command. The configured
source/runtime are immutable installations; this script never installs packages.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True

CONFIG = Path("/etc/fasl/geophysics-profile-runtime.json")
MAX_PACKET = 6*1024**2
MAX_CAPTURE = 32*1024**2


def require(value, code="profile_supervision_refused"):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(info):
    # Reads can legitimately update atime; do not mistake that for byte mutation.
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_uid,info.st_gid,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def pairs(items):
    result = {}
    for key,value in items:
        require(key not in result,"duplicate_key")
        result[key] = value
    return result


def decode(raw, cap):
    require(type(raw) is bytes and 0 < len(raw) <= cap,"packet_size")
    value = json.loads(raw.decode("utf-8","strict"),object_pairs_hook=pairs,
                       parse_constant=lambda _:require(False,"nonfinite_json"))
    # Serialization also rejects overflowed floating literals and invalid Unicode.
    json.dumps(value,allow_nan=False).encode("utf-8","strict")
    return value


def root_regular(path, cap, *, allow_empty=False):
    """Installation files only; workers must not be able to rewrite parents."""
    require(path.is_absolute(),"installation_path")
    # The installed runtime/closure includes explicitly pinned interpreter and
    # root-owned usrmerge/soname links. Validate their immutable parents, then
    # inspect the resolved regular file; a worker-owned link is never followed.
    for alias in (path,*path.parents):
        info = alias.lstat()
        require(info.st_uid == 0,"installation_owner")
        require(stat.S_ISLNK(info.st_mode) or not info.st_mode & 0o022,"installation_writable")
    path = path.resolve(strict=True)
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,"installation_parent")
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                and (0 if allow_empty else 1) <= info.st_size <= cap,"installation_file")
        with os.fdopen(os.dup(fd),"rb") as stream:
            raw = stream.read(cap+1)
        require(len(raw) == info.st_size and identity(os.fstat(fd)) == identity(info),"installation_changed")
        return raw
    finally:
        os.close(fd)


def validate_inventory(observed, expected):
    """Exact sealed name/identity policy; snapshots alone are not OS evidence."""
    require(type(observed) is dict and type(expected) is dict and
            0 < len(expected) <= 12000 and set(observed) == set(expected),"import_name_set")
    common = {"kind","uid","gid","mode","dev","ino"}
    for name,record in expected.items():
        require(type(name) is str and name != "." and 0 < len(name) <= 4096 and "\\" not in name and
                "\x00" not in name and not PurePosixPath(name).is_absolute() and
                str(PurePosixPath(name)) == name and ".." not in PurePosixPath(name).parts,"import_name")
        require(type(record) is dict and record.get("kind") in ("file","directory","link"),"import_kind")
        keys = common | ({"bytes","sha256"} if record["kind"] == "file" else
                         {"target"} if record["kind"] == "link" else set())
        require(set(record) == keys,"import_record_fields")
        for key in ("uid","gid","dev","ino"):
            require(type(record[key]) is int and record[key] >= 0,"import_identity")
        require(record["uid"] == 0 and type(record["mode"]) is str and
                re.fullmatch(r"0o[0-7]{3,4}",record["mode"]),"import_owner_mode")
        mode = int(record["mode"],8)
        require(mode <= 0o7777 and (record["kind"] == "link" or not mode & 0o022),"import_writable")
        if record["kind"] == "file":
            require(type(record["bytes"]) is int and 0 <= record["bytes"] <= 128*1024**2 and
                    type(record["sha256"]) is str and re.fullmatch("[a-f0-9]{64}",record["sha256"]),"import_file")
        elif record["kind"] == "link":
            require(type(record["target"]) is str and 0 < len(record["target"]) <= 4096 and
                    "\x00" not in record["target"],"import_link")
        require(observed[name] == record,"import_entry_changed")


def snapshot_tree(root, boundary):
    """No-follow census of immutable installed names, including empty files."""
    require(root.is_absolute() and root.resolve(strict=True).is_relative_to(boundary),"import_root")
    for parent in (root,*root.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,"import_parent")
    records, pending = {}, [root]
    while pending:
        parent = pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                require(len(records) < 12000,"import_entry_limit")
                member = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                record = dict(uid=info.st_uid,gid=info.st_gid,mode=oct(stat.S_IMODE(info.st_mode)),
                              dev=info.st_dev,ino=info.st_ino)
                require(info.st_uid == 0 and (stat.S_ISLNK(info.st_mode) or not info.st_mode & 0o022),"import_writable")
                if stat.S_ISLNK(info.st_mode):
                    resolved = member.resolve(strict=True)
                    require(resolved.is_relative_to(boundary),"import_link_escape")
                    # Validate target and every alias/resolved parent as immutable.
                    if resolved.is_dir():
                        for target_parent in (resolved,*resolved.parents):
                            target_info = target_parent.lstat()
                            require(stat.S_ISDIR(target_info.st_mode) and target_info.st_uid == 0
                                    and not target_info.st_mode & 0o022,"import_link_directory")
                    else:
                        root_regular(member,128*1024**2,allow_empty=True)
                    record.update(kind="link",target=os.readlink(member))
                elif stat.S_ISDIR(info.st_mode):
                    record.update(kind="directory")
                    pending.append(member)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,"import_special_entry")
                    body = root_regular(member,128*1024**2,allow_empty=True)
                    require(identity(member.lstat()) == identity(info),"import_entry_race")
                    record.update(kind="file",bytes=len(body),sha256=sha(body))
                records[member.relative_to(root).as_posix()] = record
    return records


def verify_import_closure(configuration, module):
    body = root_regular(Path(configuration["import_closure"]),8*1024**2)
    require(sha(body) == configuration["import_closure_sha256"],"import_closure_changed")
    closure = decode(body,8*1024**2)
    require(closure["schema"] == "geophysics.private-profile-import-closure/v1" and
            closure["runtime"] == configuration["environment_root"] and
            closure["original_environment_sha256"] == configuration["environment_sha256"] and
            closure["production_activated"] is False and closure["startup_hooks"] == [],"import_closure_identity")
    runtime = Path(configuration["environment_root"])
    for name,root in (("runtime_files",runtime/"runtime"),("profile_env_files",runtime/"profile-env")):
        validate_inventory(snapshot_tree(root,runtime),closure[name])
    # Code names are independent of the older runtime qualification's producer.
    source = Path(configuration["source_root"])
    observed = snapshot_tree(source,source)
    validate_inventory(observed,observed)
    names = set(module.SOURCE_FILES)
    for name in module.SOURCE_FILES:
        names.update(str(p) for p in PurePosixPath(name).parents if str(p) != ".")
    require(set(observed) == names,"source_import_name_set")
    for name,digest in configuration["source_hashes"].items():
        require(observed[name]["kind"] == "file" and observed[name]["sha256"] == digest,"source_changed")
    for name,record in closure["elf_closure"].items():
        require(sha(root_regular(Path(name),128*1024**2)) == record["sha256"],"native_closure_changed")
        for absent in record["absent_runpath"]:
            require(type(absent) is str and Path(absent).is_absolute() and
                    not Path(absent).exists() and not Path(absent).is_symlink(),"unexpected_runpath")


def verify_executing_supervisor(configuration):
    expected = Path(configuration["source_root"])/"scripts/profile_linux_supervisor.py"
    require(Path(__file__).resolve() == expected,"executing_supervisor_changed")
    require(sha(root_regular(expected,2*1024**2)) ==
            configuration["source_hashes"]["scripts/profile_linux_supervisor.py"],"executing_supervisor_changed")


def installation():
    configuration = decode(root_regular(CONFIG,65536),65536)
    source = Path(configuration["source_root"])
    require(source.is_absolute() and ".." not in source.parts,"source_path")
    module_path = source/"app/profile_linux_exec.py"
    raw = root_regular(module_path,1024**2)
    require(sha(raw) == configuration["source_hashes"]["app/profile_linux_exec.py"],"constructor_changed")
    spec = importlib.util.spec_from_file_location("_trusted_profile_linux_constructor",module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_configuration(configuration)
    verify_executing_supervisor(configuration)
    for name,digest in configuration["source_hashes"].items():
        require(sha(root_regular(source/name,2*1024**2)) == digest,"source_changed")
    runtime = Path(configuration["environment_root"])
    environment = decode(root_regular(runtime/"environment.json",4*1024**2),4*1024**2)
    require(sha(root_regular(runtime/"environment.json",4*1024**2)) == configuration["environment_sha256"],"environment_changed")
    require(environment["schema"] == "geophysics-private-profile-environment-1" and
            environment["python"] == configuration["python"],"environment_identity")
    require(environment["pins"] == {"numpy":"2.5.3","scipy":"1.17.1","pygimli":"1.6.1",
            "pgcore":"1.6.0","scooby":"0.12.0","setuptools":"84.0.0"},"runtime_versions")
    verify_import_closure(configuration,module)
    python = Path(configuration["python"]).resolve(strict=True)
    require(python.is_relative_to(runtime) and sha(root_regular(python,256*1024**2)) == configuration["python_sha256"],"interpreter_changed")
    return configuration,module


def _nonroot_regular(path, cap):
    require(os.geteuid() != 0,"reader_privilege")
    for part in (path,*path.parents):
        require(not part.is_symlink(),"input_link")
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= cap,"input_size")
        with os.fdopen(os.dup(fd),"rb") as stream:
            raw = stream.read(cap+1)
        require(len(raw) == info.st_size and identity(os.fstat(fd)) == identity(info),"input_changed")
        return raw
    finally:
        os.close(fd)


def _query(configuration, identifier, module):
    """Called only after irrevocable ID drop; root never opens SQLite/WAL."""
    import sqlite3
    from uuid import UUID
    root = Path(configuration["data_root"])
    database = root/"api.sqlite3"
    require(os.geteuid() == configuration["uid"] and not database.is_symlink(),"reader_identity")
    connection = sqlite3.connect("file:"+str(database)+"?mode=ro",uri=True,timeout=1)
    connection.row_factory = sqlite3.Row
    deadline = time.monotonic()+3
    connection.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
    try:
        def row(table, keys, key):
            # Names are constant module-owned tuples, not supplied SQL identifiers.
            value = connection.execute("SELECT "+",".join(sorted(keys))+" FROM "+table+" WHERE id=?",(key,)).fetchone()
            require(value is not None,"relation_missing")
            result = dict(value)
            owner = result["owner_id"]
            require(type(owner) is str and re.fullmatch(r"[a-f0-9]{32}|[a-f0-9-]{36}",owner),"sql_owner")
            result["owner_id"] = str(UUID(owner))
            return result
        job = row("processing_jobs",module.JOB_KEYS,identifier)
        require(type(job["cancel_requested"]) is int and job["cancel_requested"] in (0,1),"sql_cancel")
        job["cancel_requested"] = bool(job["cancel_requested"])
        for key in ("request_json","preflight"):
            require(type(job[key]) is str,"sql_json")
            job[key] = decode(job[key].encode(),65536)
        dataset = row("observation_datasets",module.DATA_KEYS,job["dataset_id"])
        raw = row("raw_assets",module.RAW_KEYS,dataset["raw_asset_id"])
        origin = row("source_records",module.ORIGIN_KEYS,raw["source_id"])
        project = connection.execute("SELECT owner_id FROM projects WHERE id=?",(job["project_id"],)).fetchone()
        require(project is not None and str(UUID(project[0])) == job["owner_id"],"project_owner")
        module.construct_launch(configuration,job,dataset,raw,origin)
        bodies = {}
        for name,value,cap in (("original",raw,1000000),("dataset.json",dataset,2*1024**2)):
            body = _nonroot_regular(root/value["storage_key"],cap)
            require(len(body) == value["byte_count"] and sha(body) == value["sha256"],"original_identity")
            bodies[name] = base64.b64encode(body).decode("ascii")
        return dict(job=job,dataset=dataset,raw=raw,origin=origin,bodies=bodies)
    finally:
        connection.close()


def nonroot_query(configuration, identifier, module):
    """Anonymous bounded response; native DB/file access has no root privilege."""
    import resource
    reader,writer = os.pipe()
    try:
        pid = os.fork()
    except BaseException:
        os.close(reader)
        os.close(writer)
        raise
    if pid == 0:
        os.close(reader)
        try:
            # Do not hand the SQLite reader root lock/custody/pidfd descriptors.
            # Inherited flock descriptions can otherwise unlock the parent.
            for name in os.listdir("/proc/self/fd"):
                fd = int(name)
                if fd != writer:
                    try:
                        os.close(fd)
                    except OSError:
                        pass  # The directory iterator's own temporary fd closed.
            os.setgroups([])
            os.setgid(configuration["gid"])
            os.setuid(configuration["uid"])
            os.environ.clear()
            resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
            resource.setrlimit(resource.RLIMIT_CPU,(5,5))
            response = module.canonical(_query(configuration,identifier,module))
            require(len(response) <= MAX_PACKET,"reader_packet_size")
            with os.fdopen(writer,"wb") as stream:
                stream.write(response)
            os._exit(0)
        except BaseException:
            os._exit(2)
    os.close(writer)
    chunks = bytearray()
    reaped = False
    deadline = time.monotonic()+8
    try:
        while True:
            require(time.monotonic()<deadline,"reader_timeout")
            ready,_,_ = select.select([reader],[],[],min(.2,max(0,deadline-time.monotonic())))
            if not ready:
                continue
            part = os.read(reader,65536)
            if not part:
                break
            require(len(chunks)+len(part) <= MAX_PACKET,"reader_packet_size")
            chunks.extend(part)
        _,status = os.waitpid(pid,0)
        reaped = True
        require(os.waitstatus_to_exitcode(status) == 0,"reader_refused")
        return decode(bytes(chunks),MAX_PACKET)
    except BaseException:
        if not reaped:
            # Only the owned unreaped fork protects this numerical PID. An
            # exit/decode refusal after waitpid must never signal it again.
            try:
                os.kill(pid,9)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(pid,0)
            except ChildProcessError:
                pass
        raise
    finally:
        os.close(reader)


def show(unit):
    names = ("MainPID","SubState","Result","ExecMainStatus","ControlGroup")
    command = ["/usr/bin/systemctl","show",unit,"--no-pager",*["--property="+key for key in names]]
    result = subprocess.run(command,capture_output=True,timeout=3,check=True)
    require(len(result.stdout) <= 8192,"manager_response")
    return dict(line.split("=",1) for line in result.stdout.decode("ascii").splitlines())


def stop(unit):
    require(re.fullmatch(r"geophysics-profile-[a-f0-9-]{36}\.service",unit),"guardian_unit")
    result = subprocess.run(["/usr/bin/systemctl","stop",unit],capture_output=True,timeout=5,check=False)
    if result.returncode:
        # Parent and guardian both drain. systemd may already have collected
        # this transient unit; only actual manager AND kernel absence permit
        # that repeated stop. Timeouts/unreadable state still propagate.
        state = subprocess.run(["/usr/bin/systemctl","show",unit,"--property=LoadState","--value"],
                               capture_output=True,timeout=3,check=True)
        require(state.stdout.strip() == b"not-found" and
                not (Path("/sys/fs/cgroup/system.slice")/unit).exists(),"stop_refused")


def exclusive(fd, name, raw, uid, gid, mode=0o600):
    require(type(name) is str and re.fullmatch(r"[a-z][a-z0-9.-]{0,79}",name),"leaf")
    member = os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,mode,dir_fd=fd)
    try:
        os.fchown(member,uid,gid)
        with os.fdopen(os.dup(member),"wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(member)


def tree_fd(path):
    """Pin every traversed directory; caller-controlled intermediate links refuse."""
    require(path.is_absolute(),"directory_path")
    fd = os.open("/",os.O_RDONLY|os.O_DIRECTORY)
    try:
        for name in path.parts[1:]:
            nxt = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def capture(fd,name,cap):
    member = os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        info = os.fstat(member)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= cap,"capture_member")
        with os.fdopen(os.dup(member),"rb") as stream:
            raw = stream.read(cap+1)
        require(len(raw) == info.st_size and identity(os.fstat(member)) == identity(info),"capture_changed")
        return raw
    finally:
        os.close(member)


def native(fd,name):
    # Kernel pseudo-files report size zero and are expected to change. They must
    # not use the stable regular-artifact reader or fabricate an empty counter.
    require(name in {"memory.max","memory.swap.max","memory.peak","memory.events","cgroup.events","cgroup.procs"},"counter_name")
    member = os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
    try:
        raw = os.read(member,65537)
        require(len(raw) <= 65536 and (len(raw) > 0 or name == "cgroup.procs"),"kernel_counter_size")
        return raw
    finally:
        os.close(member)


def unit_rss(fd):
    """Sample only current members of the exact owned cgroup, not observers."""
    members = native(fd,"cgroup.procs").splitlines()
    require(len(members) <= 32,"group_member_count")
    total = observed = 0
    for member in members:
        require(re.fullmatch(rb"[1-9][0-9]{0,9}",member),"group_member_pid")
        pid = int(member)
        try:
            text = Path(f"/proc/{pid}/status").read_text()
            # Recheck membership after the read: a disappeared PID is not counted.
            if member not in native(fd,"cgroup.procs").splitlines():
                continue
            rss = re.search(r"^VmRSS:\s+([0-9]+) kB$",text,re.M)
            if rss:
                total += int(rss[1])*1024
                observed += 1
        except FileNotFoundError:
            continue
    return total,observed


def clear_held_inputs(custody_fd, inputs_fd, expected):
    """Remove declared copies only, using pinned directories after extinction."""
    require(set(os.listdir(inputs_fd)) == set(expected),"held_unknown_member")
    for name,body in expected.items():
        require(capture(inputs_fd,name,MAX_PACKET) == body,"held_changed")
    current = os.stat("inputs",dir_fd=custody_fd,follow_symlinks=False)
    require(identity(current) == identity(os.fstat(inputs_fd)),"held_directory_changed")
    for name in expected:
        os.unlink(name,dir_fd=inputs_fd)
    os.fsync(inputs_fd)
    os.rmdir("inputs",dir_fd=custody_fd)
    os.fsync(custody_fd)


class CancellationFrame:
    """Bounded pipe protocol; fragmented writes are not lost."""
    def __init__(self):
        self.buffer = b""

    def feed(self, part):
        require(type(part) is bytes,"cancel_frame")
        if not part:
            return "caller_eof"
        self.buffer += part
        require(len(self.buffer) <= 7 and b"CANCEL\n".startswith(self.buffer),"cancel_frame")
        return "owner_cancel" if self.buffer == b"CANCEL\n" else None


def drain_owned_unit(unit, timeout=5):
    """Stop and prove the exact manager group empty; never signal numeric PIDs."""
    require(re.fullmatch(r"geophysics-profile-[a-f0-9-]{36}\.service",unit),"guardian_unit")
    stop(unit)
    deadline = time.monotonic()+timeout
    while True:
        terminal = show(unit)
        group = terminal.get("ControlGroup","")
        require(group in ("","/system.slice/"+unit),"stop_group")
        # Empty manager properties are not evidence that the kernel group is
        # gone. Independently inspect the deterministic owned path every time.
        owned_path = Path("/sys/fs/cgroup/system.slice")/unit
        group_exists = owned_path.exists()
        events = None
        empty = not group_exists
        if group_exists:
            fd = tree_fd(owned_path)
            try:
                events = native(fd,"cgroup.events").decode("ascii")
                empty = "populated 0" in events
            finally:
                os.close(fd)
        if terminal.get("MainPID") == "0" and empty:
            return terminal,events,not group_exists
        require(time.monotonic()<deadline,"stop_extinction_unproved")
        time.sleep(.02)


def guardian_frame(buffer, part):
    """Completion is a byte stream too; EOF never means successful science."""
    require(type(buffer) is bytes and type(part) is bytes,"guardian_frame")
    if not part:
        return buffer,"caller_dead"
    buffer += part
    require(len(buffer) <= 5 and b"DONE\n".startswith(buffer),"guardian_frame")
    return buffer,"complete" if buffer == b"DONE\n" else None


def scope_transport(scope,pidfd,wall,configuration):
    """One fixed descriptor-bearing manager call, never a public D-Bus port."""
    import ctypes as c
    require(re.fullmatch(r"geophysics-profile-guardian-[a-f0-9-]{36}\.scope",scope) and
            type(pidfd) is int and pidfd >= 3 and type(wall) is int and 1 <= wall <= 600,"guardian_transport_input")
    library_path = Path(configuration["systemd_library"])
    require(sha(root_regular(library_path,8*1024**2)) == configuration["systemd_library_sha256"],"manager_library_changed")
    library = c.CDLL(str(library_path))
    ptr = c.c_void_p
    signatures = {
        "sd_bus_open_system":([c.POINTER(ptr)],c.c_int),
        "sd_bus_message_new_method_call":([ptr,c.POINTER(ptr),c.c_char_p,c.c_char_p,c.c_char_p,c.c_char_p],c.c_int),
        "sd_bus_message_append_basic":([ptr,c.c_char,ptr],c.c_int),
        "sd_bus_message_open_container":([ptr,c.c_char,c.c_char_p],c.c_int),
        "sd_bus_message_close_container":([ptr],c.c_int),
        "sd_bus_call":([ptr,ptr,c.c_uint64,ptr,c.POINTER(ptr)],c.c_int),
        "sd_bus_message_read_basic":([ptr,c.c_char,ptr],c.c_int),
        "sd_bus_message_unref":([ptr],ptr),
        "sd_bus_close":([ptr],None),
        "sd_bus_unref":([ptr],ptr),
    }
    for name,(arguments,result) in signatures.items():
        function = getattr(library,name)
        function.argtypes,function.restype = arguments,result
    bus,message,reply = ptr(),ptr(),ptr()

    def checked(name,*arguments):
        result = getattr(library,name)(*arguments)
        require(result >= 0,"guardian_bus_call")
        return result

    def basic(kind,value):
        if kind == b"s":
            item = c.c_char_p(value.encode("ascii"))
            pointer = c.cast(item,ptr)
        else:
            item = c.c_int(value) if kind == b"h" else c.c_uint64(value)
            pointer = c.cast(c.byref(item),ptr)
        checked("sd_bus_message_append_basic",message,kind,pointer)

    def opened(kind,signature):
        checked("sd_bus_message_open_container",message,kind,signature)

    def closed():
        checked("sd_bus_message_close_container",message)

    try:
        checked("sd_bus_open_system",c.byref(bus))
        checked("sd_bus_message_new_method_call",bus,c.byref(message),b"org.freedesktop.systemd1",
                b"/org/freedesktop/systemd1",b"org.freedesktop.systemd1.Manager",b"StartTransientUnit")
        basic(b"s",scope)
        basic(b"s","fail")
        opened(b"a",b"(sv)")
        for name,kind,value in (("PIDFDs",b"ah",pidfd),("MemoryMax",b"t",128*1024**2),
                                ("TasksMax",b"t",16),("RuntimeMaxUSec",b"t",(wall+30)*1000000),
                                ("Slice",b"s","system.slice")):
            opened(b"r",b"sv")
            basic(b"s",name)
            opened(b"v",kind)
            if kind == b"ah":
                opened(b"a",b"h")
                basic(b"h",value)  # libsystemd duplicates/transfers the kernel FD.
                closed()
            else:
                basic(kind,value)
            closed()
            closed()
        closed()
        opened(b"a",b"(sa(sv))")
        closed()
        checked("sd_bus_call",bus,message,5000000,None,c.byref(reply))
        result = c.c_char_p()
        require(checked("sd_bus_message_read_basic",reply,b"o",c.byref(result)) > 0 and
                result.value is not None and re.fullmatch(rb"/org/freedesktop/systemd1/job/[0-9]{1,20}",result.value),"guardian_bus_reply")
        return result.value.decode("ascii")
    finally:
        for value in (reply,message):
            if value:
                library.sd_bus_message_unref(value)
        if bus:
            library.sd_bus_close(bus)
            library.sd_bus_unref(bus)


def enroll_guardian(scope,pid,pidfd,wall,configuration):
    """Fixed manager operation for an owned unreaped root fork, not public IPC."""
    require(re.fullmatch(r"geophysics-profile-guardian-[a-f0-9-]{36}\.scope",scope),"guardian_scope")
    require(type(pid) is int and pid > 1 and type(wall) is int and 1 <= wall <= 600,"guardian_scope_limits")
    absent = subprocess.run(["/usr/bin/systemctl","show",scope,"--property=LoadState","--value"],capture_output=True,timeout=3,check=True)
    require(absent.stdout.strip() == b"not-found","guardian_scope_present")
    job_path = scope_transport(scope,pidfd,wall,configuration)
    deadline = time.monotonic()+3
    expected = "/system.slice/"+scope
    while True:
        properties = ("ActiveState","ControlGroup","MemoryMax","TasksMax")
        state = subprocess.run(["/usr/bin/systemctl","show",scope,*["--property="+key for key in properties]],capture_output=True,timeout=3,check=True)
        require(len(state.stdout) <= 4096,"guardian_manager_response")
        observed = dict(line.split("=",1) for line in state.stdout.decode("ascii").splitlines())
        group = Path(f"/proc/{pid}/cgroup").read_text()
        if observed.get("ActiveState") == "active" and observed.get("ControlGroup") == expected and group == "0::"+expected+"\n":
            # systemctl formats durations for humans (e.g. 10min 30s). Read the
            # typed manager value rather than accepting/rejecting display text.
            object_path = "/org/freedesktop/systemd1/unit/"+"".join(
                letter if letter.isalnum() else "_"+format(ord(letter),"02x") for letter in scope)
            duration = subprocess.run(["/usr/bin/busctl","--timeout=3s","get-property",
                "org.freedesktop.systemd1",object_path,"org.freedesktop.systemd1.Scope","RuntimeMaxUSec"],
                capture_output=True,timeout=4,check=True)
            require(observed.get("MemoryMax") == str(128*1024**2) and observed.get("TasksMax") == "16"
                    and duration.stdout.strip() == ("t "+str((wall+30)*1000000)).encode("ascii"),"guardian_scope_readback")
            return dict(scope=scope,group=expected,memory_limit_bytes=128*1024**2,tasks_max=16,
                        wall_limit_seconds=wall+30,identity_transport="PIDFDs/ah",manager_job=job_path)
        require(time.monotonic()<deadline,"guardian_scope_membership")
        time.sleep(.02)


def _guardian_child(unit,parent_fd,control_read,ready_write):
    # Do not retain SQLite/custody/lock/stdin descriptors in the guardian.
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd not in (parent_fd,control_read,ready_write):
            try:
                os.close(fd)
            except OSError:
                pass
    buffer = b""
    normal = False
    try:
        os.write(ready_write,b"READY\n")
        os.close(ready_write)
        while True:
            ready,_,_ = select.select([parent_fd,control_read],[],[],1)
            if parent_fd in ready:
                break
            if control_read in ready:
                buffer,outcome = guardian_frame(buffer,os.read(control_read,1024))
                if outcome == "complete":
                    drain_owned_unit(unit)
                    normal = True
                    break
                if outcome == "caller_dead":
                    break
    except BaseException:
        normal = False
    if normal:
        os._exit(0)
    # Science is manager-bound to this scope. Exiting the scope also makes an
    # interrupted, later resumed submission fail its BindsTo/After dependency.
    # Actual delayed-client and caller-cgroup-stop tests must prove that policy.
    deadline = time.monotonic()+15
    while time.monotonic()<deadline:
        try:
            drain_owned_unit(unit)
        except BaseException:
            pass
        time.sleep(.1)
    os._exit(2)


def start_guardian(unit,scope,wall,configuration):
    """Root guardian, pre-fork launcher pidfd and unreaped own-child identity."""
    require(os.geteuid() == 0,"guardian_privilege")
    descriptors = {}
    pid = None

    def close_slot(key):
        fd = descriptors.pop(key,None)
        if fd is not None:
            os.close(fd)

    try:
        descriptors["parent"] = os.pidfd_open(os.getpid())
        descriptors["control_read"],descriptors["control_write"] = os.pipe()
        descriptors["ready_read"],descriptors["ready_write"] = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                _guardian_child(unit,descriptors["parent"],descriptors["control_read"],descriptors["ready_write"])
            finally:
                os._exit(2)
        for key in ("parent","control_read","ready_write"):
            close_slot(key)
        descriptors["child"] = os.pidfd_open(pid)
        child_fd,ready_read = descriptors["child"],descriptors["ready_read"]
        ready,_,_ = select.select([ready_read,child_fd],[],[],3)
        require(ready_read in ready and child_fd not in ready
                and os.read(ready_read,7) == b"READY\n","guardian_not_ready")
        scope_receipt = enroll_guardian(scope,pid,child_fd,wall,configuration)
        require(not select.select([child_fd],[],[],0)[0],"guardian_died_during_enrollment")
        close_slot("ready_read")
        return pid,descriptors.pop("child"),descriptors.pop("control_write"),scope_receipt
    except BaseException:
        close_slot("control_write")
        if pid is not None and pid > 0:
            # Before scientific submission, kill/reap only this own unreaped
            # fork. Even if pidfd acquisition failed its PID cannot recycle.
            try:
                if "child" in descriptors:
                    signal.pidfd_send_signal(descriptors["child"],signal.SIGKILL)
                else:
                    os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid,0)
        raise
    finally:
        for key in tuple(descriptors):
            close_slot(key)


def custody_budget(plans, receipt_sizes, new_bytes):
    """Portable bookkeeping only; actual directory custody is checked below."""
    require(type(new_bytes) is int and 0 < new_bytes <= 3*1024**2,"custody_new_bytes")
    require(len(plans) < 4 and all(type(v) is int and 0 < v <= 3*1024**2 for v in plans),"custody_job_cap")
    require(sum(plans)+new_bytes <= 16*1024**2,"custody_copy_cap")
    require(len(receipt_sizes) < 256 and all(type(v) is int and 0 < v <= 65536 for v in receipt_sizes),"custody_receipt_cap")


def prepare_custody_plan(root_fd,module,packet,launch):
    """Exclusive immutable intent BEFORE mkdir/copies; unknown debt refuses."""
    names = set(os.listdir(root_fd))
    planned,receipts,directories = {},[],set()
    for name in names:
        match = re.fullmatch(r"([a-f0-9-]{36})(\.plan\.json|\.receipt\.json)?",name)
        require(match is not None,"custody_unknown_name")
        identifier = module.uuid(match[1])
        info = os.stat(name,dir_fd=root_fd,follow_symlinks=False)
        require(info.st_uid == 0 and not info.st_mode & 0o022,"custody_changed_owner")
        if match[2] is None:
            require(stat.S_ISDIR(info.st_mode),"custody_directory_type")
            directories.add(identifier)
        else:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,"custody_record_type")
            record = decode(capture(root_fd,name,65536),65536)
            require(record["job_id"] == identifier,"custody_record_identity")
            if match[2] == ".plan.json":
                require(set(record) == {"schema","job_id","held_bytes","request_sha256","raw_sha256","dataset_sha256","invocation_sha256"}
                        and record["schema"] == "geophysics.profile-linux-custody-plan/v1","custody_plan_schema")
                for key in ("request_sha256","raw_sha256","dataset_sha256","invocation_sha256"):
                    module.sha(record[key])
                planned[identifier] = record["held_bytes"]
            else:
                require(record["schema"] == "geophysics.profile-linux-execution/v1","custody_receipt_schema")
                receipts.append(info.st_size)
    require(directories <= set(planned),"custody_unplanned_directory")
    new_bytes = packet["raw"]["byte_count"]+packet["dataset"]["byte_count"]
    custody_budget(list(planned.values()),receipts,new_bytes)
    plan = dict(schema="geophysics.profile-linux-custody-plan/v1",job_id=packet["job"]["id"],
                held_bytes=new_bytes,request_sha256=packet["job"]["request_sha256"],
                raw_sha256=packet["raw"]["sha256"],dataset_sha256=packet["dataset"]["sha256"],
                invocation_sha256=sha(module.canonical(launch)))
    name = packet["job"]["id"]+".plan.json"
    # UUID-based record names exceed the ordinary result leaf policy, but remain
    # constructed only from validated canonical UUID and literal suffixes.
    fd = os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=root_fd)
    try:
        body = module.canonical(plan)
        with os.fdopen(os.dup(fd),"wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    os.fsync(root_fd)
    return plan


def finish_custody(root_fd,custody_fd,identifier,plan,receipt,module):
    """Bounded root receipt and declared empty cleanup; no recursive deletion."""
    current_plan = capture(root_fd,identifier+".plan.json",65536)
    require(current_plan == module.canonical(plan),"custody_plan_changed")
    body = module.canonical(receipt)
    require(len(body) <= 65536,"custody_receipt_size")
    fd = os.open(identifier+".receipt.json",os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=root_fd)
    try:
        with os.fdopen(os.dup(fd),"wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    os.fsync(root_fd)
    if (receipt["failure"] is None and receipt["extinction"] == "proved"
            and receipt["held_inputs_state"] == "declared_copies_removed"
            and receipt["guardian_status"] == "complete"):
        require(set(os.listdir(custody_fd)) == {"scratch"},"custody_unknown_member")
        scratch_fd = os.open("scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=custody_fd)
        try:
            info = os.fstat(scratch_fd)
            require(info.st_uid == 0 and not os.listdir(scratch_fd),"custody_scratch_debt")
        finally:
            os.close(scratch_fd)
        require(os.stat(identifier,dir_fd=root_fd,follow_symlinks=False).st_ino == os.fstat(custody_fd).st_ino,"custody_directory_changed")
        os.rmdir("scratch",dir_fd=custody_fd)
        os.rmdir(identifier,dir_fd=root_fd)
        os.unlink(identifier+".plan.json",dir_fd=root_fd)
        os.fsync(root_fd)


def execute(configuration,module,identifier):
    """Actual host path, deliberately distinct from constructor unit tests."""
    import fcntl
    lock_path = Path("/run/fasl-geophysics-profile-launch.lock")
    lock = os.open(lock_path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    info = os.fstat(lock)
    require(info.st_uid == 0 and info.st_nlink == 1 and stat.S_ISREG(info.st_mode) and not info.st_mode & 0o077,"supervisor_lock")
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    packet = nonroot_query(configuration,identifier,module)
    launch = module.construct_launch(configuration,packet["job"],packet["dataset"],packet["raw"],packet["origin"])
    uid,gid = configuration["uid"],configuration["gid"]
    stage_fd = tree_fd(Path(launch["host_stage"]))
    require(os.fstat(stage_fd).st_uid == uid,"stage_owner")
    custody_root = tree_fd(Path("/run/fasl-geophysics-profile-jobs"))
    root_info = os.fstat(custody_root)
    require(root_info.st_uid == 0 and root_info.st_gid == gid and
            not root_info.st_mode & 0o022 and root_info.st_mode & 0o050 == 0o050,"custody_parent")
    plan = prepare_custody_plan(custody_root,module,packet,launch)
    os.mkdir(identifier,0o750,dir_fd=custody_root)
    custody_fd = os.open(identifier,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=custody_root)
    os.fchown(custody_fd,0,gid)
    os.mkdir("scratch",0o700,dir_fd=custody_fd)
    inputs_fd = mounted_fd = group_fd = pid_fd = None
    started = time.monotonic()
    stopped = None
    peak_rss = peak_memory = samples = memory_reads = 0
    tree_peak = tree_samples = 0
    terminal = {}
    retained = {}
    failure = None
    launched = False
    group_removed = False
    memory_events = cgroup_events = None
    held_bodies = {}
    held_identities = {}
    held_state = "retained_unverified"
    originals_reverified = False
    extinction = "unproved"
    cancel_frame = CancellationFrame()
    guardian_pid = guardian_fd = guardian_control = None
    guardian_status = "not_started"
    guardian_scope_receipt = None
    try:
        require(os.listdir(stage_fd) in ([],["stderr.txt"]),"unknown_host_stage")
        os.mkdir("inputs",0o750,dir_fd=custody_fd)
        inputs_fd = os.open("inputs",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=custody_fd)
        os.fchown(inputs_fd,0,gid)
        for name,encoded in packet["bodies"].items():
            raw = base64.b64decode(encoded,validate=True)
            record = packet["raw"] if name == "original" else packet["dataset"]
            require(len(raw) == record["byte_count"] and sha(raw) == record["sha256"],"held_identity")
            exclusive(inputs_fd,name,raw,0,gid,0o440)
            held_bodies[name] = raw
        held_identities = {}
        for name,body in held_bodies.items():
            info = os.stat(name,dir_fd=inputs_fd,follow_symlinks=False)
            held_identities[name] = dict(device=info.st_dev,inode=info.st_ino,bytes=len(body),sha256=sha(body))
        wrapper = dict(command=launch["command"],environment=launch["environment"],stderr=launch["stage"]+"/stderr.txt",
                       inputs=held_identities)
        held_bodies["launch.json"] = module.canonical(wrapper)
        exclusive(inputs_fd,"launch.json",held_bodies["launch.json"],0,gid,0o440)
        unit = launch["unit"]
        absent = subprocess.run(["/usr/bin/systemctl","show",unit,"--property=LoadState","--value"],capture_output=True,timeout=3,check=True)
        require(absent.stdout.strip() == b"not-found","unit_already_present")
        readable,_,_ = select.select([0],[],[],0)
        if readable:
            stopped = cancel_frame.feed(os.read(0,1024))
            require(stopped is None,"cancelled_before_launch")
        guardian_pid,guardian_fd,guardian_control,guardian_scope_receipt = start_guardian(unit,launch["guardian_scope"],packet["job"]["preflight"]["wall_limit_seconds"],configuration)
        guardian_status = "ready"
        command = ["/usr/bin/systemd-run","--quiet","--unit="+unit,
                   *["--property="+p for p in launch["properties"]],configuration["python"],"-I","-B",
                   configuration["source_root"]+"/scripts/profile_linux_child.py",launch["held"]+"/launch.json"]
        # Manager acceptance may precede a timed-out/nonzero client response.
        # Every attempted exact unit must be independently stopped and drained.
        launched = True
        subprocess.run(command,capture_output=True,timeout=10,check=True)
        group_path = None
        while True:
            require(not select.select([guardian_fd],[],[],0)[0],"guardian_died")
            terminal = show(unit)
            pid = int(terminal["MainPID"])
            if pid and mounted_fd is None:
                try:
                    pid_fd = os.pidfd_open(pid)
                    require(int(show(unit)["MainPID"]) == pid,"manager_pid_changed")
                    status = Path(f"/proc/{pid}/status").read_text()
                    require(re.search(rf"Uid:\s+{uid}\s+{uid}\s+{uid}\s+{uid}",status),"child_uid")
                    require(re.search(rf"Gid:\s+{gid}\s+{gid}\s+{gid}\s+{gid}",status),"child_gid")
                    require(re.search(r"NoNewPrivs:\s+1",status) and all(int(re.search(rf"^{key}:\s*(.*?)$",status,re.M).group(1),16) == 0 for key in ("CapInh","CapPrm","CapEff","CapBnd","CapAmb")),"child_security")
                    require(os.readlink(f"/proc/{pid}/cwd") == launch["stage"],"child_cwd")
                    observed_fd = os.open(f"/proc/{pid}/cwd",os.O_RDONLY|os.O_DIRECTORY)
                    capacity = os.fstatvfs(observed_fd)
                    if capacity.f_blocks*capacity.f_frsize != packet["job"]["preflight"]["scratch_limit_bytes"]:
                        os.close(observed_fd)
                        os.close(pid_fd)
                        pid_fd = None
                    else:
                        mounted_fd = observed_fd
                        require(terminal["ControlGroup"] == "/system.slice/"+unit,"unit_group")
                        group_path = Path("/sys/fs/cgroup"+terminal["ControlGroup"])
                        group_fd = tree_fd(group_path)
                except FileNotFoundError:
                    if pid_fd is not None:
                        os.close(pid_fd)
                        pid_fd = None
            if group_fd is not None:
                try:
                    require(native(group_fd,"memory.max").strip() == str(packet["job"]["preflight"]["memory_limit_bytes"]).encode(),"kernel_memory_limit")
                    require(native(group_fd,"memory.swap.max").strip() == b"0","kernel_swap_limit")
                    peak_memory = max(peak_memory,int(native(group_fd,"memory.peak")))
                    memory_events = native(group_fd,"memory.events").decode("ascii")
                    cgroup_events = native(group_fd,"cgroup.events").decode("ascii")
                    memory_reads += 1
                    rss,observed = unit_rss(group_fd)
                    if observed:
                        tree_peak = max(tree_peak,rss)
                        tree_samples += 1
                except FileNotFoundError:
                    require(not group_path.exists(),"group_observation_lost")
                    group_removed = True
            if pid:
                try:
                    status = Path(f"/proc/{pid}/status").read_text()
                    rss = re.search(r"^VmRSS:\s+([0-9]+) kB$",status,re.M)
                    if rss:
                        peak_rss = max(peak_rss,int(rss[1])*1024)
                        samples += 1
                except FileNotFoundError:
                    pass
            readable,_,_ = select.select([0],[],[],0)
            if readable and stopped is None:
                stopped = cancel_frame.feed(os.read(0,1024))
                if stopped:
                    stop(unit)
            if not pid and terminal["SubState"] in ("exited","failed","dead"):
                # MainPID zero alone does not prove descendant extinction.
                if group_removed or cgroup_events is not None and "populated 0" in cgroup_events:
                    break
            require(time.monotonic()-started <= packet["job"]["preflight"]["wall_limit_seconds"]+15,"manager_timeout")
            time.sleep(.02)
        require(terminal["MainPID"] == "0" and (group_removed or cgroup_events is not None and "populated 0" in cgroup_events),"extinction_unproved")
        extinction = "proved"
        require(mounted_fd is not None and samples > 0 and memory_reads > 0,"resource_observation_missing")
        require(set(os.listdir(mounted_fd)) <= {"result.json","stderr.txt",".pygimli-config",".matplotlib"},"unknown_mounted_stage")
        # Re-read under the nonroot identity; root must never open uploaded files.
        # Cancellation or changed relations leave copies as explicit retained debt.
        if stopped is None and terminal.get("ExecMainStatus") == "0":
            fresh = nonroot_query(configuration,identifier,module)
            require(module.canonical(fresh) == module.canonical(packet),"originals_changed_after_compute")
            originals_reverified = True
        current_stage = tree_fd(Path(launch["host_stage"]))
        try:
            require(identity(os.fstat(current_stage)) == identity(os.fstat(stage_fd)),"host_stage_changed")
        finally:
            os.close(current_stage)
        for name,cap in (("result.json",MAX_CAPTURE),("stderr.txt",MAX_CAPTURE)):
            try:
                content = capture(mounted_fd,name,cap)
            except FileNotFoundError:
                continue
            retained[name] = dict(bytes=len(content),sha256=sha(content))
            # stderr may already be the worker's empty opened file. Do not
            # overwrite it or publish partial diagnostics as a successful result.
            target = "linux-stderr.txt" if name == "stderr.txt" else name
            exclusive(stage_fd,target,content,uid,gid)
        if originals_reverified:
            clear_held_inputs(custody_fd,inputs_fd,held_bodies)
            held_state = "declared_copies_removed"
    except BaseException as error:
        failure = type(error).__name__  # Never private input or arbitrary exception text.
    finally:
        if launched:
            try:
                terminal,cgroup_events,group_removed = drain_owned_unit(launch["unit"])
                extinction = "proved"
            except BaseException:
                failure = "owned_stop_failed"
                extinction = "unproved_retained_debt"
        if guardian_control is not None:
            try:
                if extinction == "proved":
                    os.write(guardian_control,b"DONE\n")
                os.close(guardian_control)
                guardian_control = None
                ready,_,_ = select.select([guardian_fd],[],[],20)
                require(bool(ready),"guardian_timeout")
                _,status = os.waitpid(guardian_pid,0)
                guardian_status = "complete" if os.waitstatus_to_exitcode(status) == 0 else "stopped_after_failure"
                require(guardian_status == "complete","guardian_failed")
            except BaseException:
                failure = "guardian_failed"
                guardian_status = "failed_retained_debt"
        receipt = dict(schema="geophysics.profile-linux-execution/v1",job_id=identifier,
                       request_sha256=packet["job"]["request_sha256"],dataset_sha256=packet["dataset"]["sha256"],
                       raw_sha256=packet["raw"]["sha256"],environment_sha256=configuration["environment_sha256"],
                       unit=launch["unit"],terminal=terminal,stop_reason=stopped,failure=failure,
                       launch_attempted=launched,extinction=extinction,
                       guardian_status=guardian_status,
                       guardian_scope=guardian_scope_receipt,
                       invocation_sha256=sha(module.canonical(launch)),source_hashes=configuration["source_hashes"],
                       configuration_sha256=sha(module.canonical(configuration)),python_sha256=configuration["python_sha256"],
                       mounted_input_identities=held_identities if held_bodies else None,
                       retained_stage_identity=dict(device=os.fstat(stage_fd).st_dev,inode=os.fstat(stage_fd).st_ino),
                       wall_seconds=time.monotonic()-started,resources=dict(sampled_root_rss_peak_bytes=peak_rss if samples else None,
                       rss_samples=samples,kernel_memcg_peak_bytes=peak_memory if memory_reads else None,
                       sampled_unit_rss_peak_bytes=tree_peak if tree_samples else None,unit_rss_samples=tree_samples,
                       memcg_reads=memory_reads,memory_events=memory_events,cgroup_events=cgroup_events,
                       exact_group_removed=group_removed,hard_writable_scratch_bytes=packet["job"]["preflight"]["scratch_limit_bytes"],
                       held_input_bytes=packet["raw"]["byte_count"]+packet["dataset"]["byte_count"]),retained=retained,
                       originals_reverified=originals_reverified,held_inputs_state=held_state,
                       cpu_accounting_admitted=False,host_admission=False)
        try:
            # The installation keeps an independent bounded operational record;
            # worker cleanup cannot silently erase the supervision evidence.
            finish_custody(custody_root,custody_fd,identifier,plan,receipt,module)
            exclusive(stage_fd,"linux-execution.json",module.canonical(receipt),uid,gid)
        finally:
            for fd in (inputs_fd,mounted_fd,group_fd,pid_fd,guardian_fd,guardian_control,stage_fd,custody_fd,custody_root,lock):
                if fd is not None:
                    os.close(fd)
    print(module.canonical(receipt).decode(),flush=True)
    return 0 if failure is None and stopped is None and terminal.get("ExecMainStatus") == "0" else 2


def main():
    require(os.name == "posix" and os.geteuid() == 0 and len(sys.argv) == 2,"supervisor_authority")
    configuration,module = installation()
    identifier = module.uuid(sys.argv[1])
    caller = os.environ.get("SUDO_UID")
    require(caller is None or caller == str(configuration["uid"]),"caller_identity")
    return execute(configuration,module,identifier)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,RecursionError,subprocess.SubprocessError):
        print('{"schema":"geophysics.profile-linux-refusal/v1","reason":"supervisor_refused"}',flush=True)
        raise SystemExit(2) from None

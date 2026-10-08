"""Closed installation authority and complete immutable import census, stdlib only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from uuid import UUID

CONFIG = Path("/etc/fasl/geophysics-waveform-runtime.json")
SOURCE_FILES = (
    "scripts/waveform_m08_linux.py", "scripts/waveform_m08_windows.py",
    "scripts/waveform_m08_files.py", "scripts/waveform_m08_export.py",
    "scripts/waveform_m08_child.py", "scripts/process_waveform_m08.py",
    "data-pipeline/waveform_input.py", "data-pipeline/waveform_processing.py",
    "data-pipeline/waveform_evaluation.py", "app/waveform_contract.py",
    "app/waveform_processing.py", "app/waveform_result.py", "app/waveform_worker.py",
    "app/waveform_linux_exec.py", "scripts/qualify_waveform_m08_linux.py",
    "scripts/waveform_m08_guardian.py", "scripts/waveform_m08_installation.py",
    "scripts/waveform_m08_owned_reader.py", "scripts/waveform_m08_supervisor.py",
    "app/waveform_linux_worker.py",
    "app/waveform_linux_execution.py",
    "app/waveform_publication.py",
    "app/waveform_stage.py",
)
CONFIG_KEYS = set("schema source_root source_revision data_root custody_root science_work_root uid gid science_uid science_gid python python_sha256 launch_python_sha256 site_packages admission_path admission_sha256 import_closure_path import_closure_sha256 source_hashes".split())


def require(value, code="waveform_installation_invalid"):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fields(value, keys):
    require(type(value) is dict and set(value) == set(keys))


def digest(value):
    require(type(value) is str and re.fullmatch("[a-f0-9]{64}",value))
    return value


def uuid(value):
    require(type(value) is str and str(UUID(value)) == value)
    return value


def path(value):
    require(type(value) is str and len(value) <= 1024 and re.fullmatch(r"/[A-Za-z0-9_./-]+",value))
    p = PurePosixPath(value)
    require(str(p) == value and p.is_absolute() and len(p.parts) >= 3 and ".." not in p.parts)
    return p


def external(value):
    p = path(value)
    require(not any(p == base or p.is_relative_to(base) for base in
                    map(PurePosixPath,("/tmp","/var/tmp","/run","/dev","/proc","/sys"))))
    return p


def validate_configuration(config):
    fields(config,CONFIG_KEYS)
    require(config["schema"] == "geophysics.waveform-linux-installation/v3")
    source, data, custody = path(config["source_root"]), external(config["data_root"]), external(config["custody_root"])
    for a,b in ((source,data),(source,custody),(data,custody)):
        require(not a.is_relative_to(b) and not b.is_relative_to(a))
    work = external(config["science_work_root"])
    for boundary in (source,data,custody,path(config["site_packages"]),path(config["import_closure_path"]).parent):
        require(not work.is_relative_to(boundary) and not boundary.is_relative_to(work))
    for key in ("python","site_packages","import_closure_path"):
        p = path(config[key])
        require(not p.is_relative_to(data) and not p.is_relative_to(custody))
    external(config["admission_path"])
    for key in ("uid","gid","science_uid","science_gid"):
        require(type(config[key]) is int and 1000 <= config[key] <= 2147483647)
    require(type(config["source_revision"]) is str and re.fullmatch("[a-f0-9]{40}",config["source_revision"]))
    require(config["uid"] != config["science_uid"])
    for key in ("python_sha256","launch_python_sha256","admission_sha256","import_closure_sha256"):
        digest(config[key])
    fields(config["source_hashes"],SOURCE_FILES)
    for value in config["source_hashes"].values():
        digest(value)
    return config


def installed_argv(config, identifier):
    validate_configuration(config)
    uuid(identifier)
    return ["/usr/bin/sudo","-n","/usr/bin/python3","-I","-S","-B",
            config["source_root"]+"/scripts/waveform_m08_supervisor.py",identifier]


def installed_environment(config):
    validate_configuration(config)
    return {"PATH":"/usr/sbin:/usr/bin:/sbin:/bin","LANG":"C.UTF-8","LC_ALL":"C.UTF-8",
            "PYTHONDONTWRITEBYTECODE":"1","TMPDIR":config["custody_root"],
            "TMP":config["custody_root"],"TEMP":config["custody_root"]}


def installed_cwd(config):
    validate_configuration(config)
    # The unprivileged caller must not traverse root-only raw custody. The fixed
    # root helper enters that directory only after its checked bootstrap.
    return "/"


def installation_binding(config, identifier):
    validate_configuration(config)
    return {"configuration_sha256":sha(canonical(config)),"python_sha256":config["python_sha256"],
            "environment_sha256":sha(canonical({key:config[key] for key in
                ("site_packages","admission_sha256","import_closure_sha256")})),
            "invocation_sha256":sha(canonical({"argv":installed_argv(config,identifier),
                "launcher_sha256":config["launch_python_sha256"],"cwd":installed_cwd(config),
                "environment":installed_environment(config)})),"source_hashes":dict(config["source_hashes"])}


def validate_recorded_binding(receipt):
    """Historical identity is self-contained; it never adopts today's config."""
    fields(receipt,{"configuration_sha256","python_sha256","environment_sha256","invocation_sha256","source_hashes"})
    for name in ("configuration_sha256","python_sha256","environment_sha256","invocation_sha256"):
        digest(receipt[name])
    fields(receipt["source_hashes"],SOURCE_FILES)
    for value in receipt["source_hashes"].values():
        digest(value)
    return receipt


def validate_installation_binding(receipt, config=None, identifier=None, *, checked=None):
    validate_recorded_binding(receipt)
    require((checked is not None) != (config is not None))
    expected = validate_recorded_binding(checked) if checked is not None else installation_binding(config,identifier)
    require(receipt == expected)
    return receipt


def decode(raw, cap):
    require(type(raw) is bytes and 0 < len(raw) <= cap)
    def pairs(items):
        result = {}
        for key,value in items:
            require(key not in result)
            result[key] = value
        return result
    result = json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:require(False))
    canonical(result)
    return result


def file_identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_uid,info.st_gid,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def directory_fd(value, *, root_owned=False):
    p = Path(value)
    require(p.is_absolute())
    fd = os.open("/",os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        for name in p.parts[1:]:
            child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=fd)
            if root_owned:
                info = os.fstat(child)
                if info.st_uid != 0 or info.st_mode & 0o022:
                    os.close(child)
                    require(False)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def regular_at(parent, name, cap, *, root_owned=False, empty=False, image=False):
    require(type(name) is str and Path(name).name == name and name not in (".",".."))
    fd = os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and (before.st_nlink >= 1 if image else before.st_nlink == 1) and
                (0 if empty else 1) <= before.st_size <= cap)
        if root_owned:
            require(before.st_uid == 0 and not before.st_mode & 0o022)
        with os.fdopen(os.dup(fd),"rb") as stream:
            raw = stream.read(cap+1)
        require(len(raw) == before.st_size and file_identity(os.fstat(fd)) == file_identity(before))
        return raw
    finally:
        os.close(fd)


def root_regular(value, cap, *, empty=False, image=False):
    p = Path(value)
    parent = directory_fd(p.parent,root_owned=True)
    try:
        return regular_at(parent,p.name,cap,root_owned=True,empty=empty,image=image)
    finally:
        os.close(parent)


def exclusive_at(parent, name, body, *, uid=0, gid=0, mode=0o600):
    require(type(body) is bytes and Path(name).name == name and name not in (".",".."))
    fd = os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC,mode,dir_fd=parent)
    try:
        os.fchown(fd,uid,gid)
        with os.fdopen(os.dup(fd),"wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    os.fsync(parent)


def validate_inventory(observed, expected):
    require(type(observed) is dict and type(expected) is dict and 0 < len(expected) <= 30000 and set(observed) == set(expected))
    common = {"kind","uid","gid","mode","device","inode"}
    for name,item in expected.items():
        require(type(name) is str and 0 < len(name) <= 4096 and "\\" not in name and "\0" not in name)
        p = PurePosixPath(name)
        require(not p.is_absolute() and str(p) == name and ".." not in p.parts and name != ".")
        require(type(item) is dict and item.get("kind") in ("file","directory","link"))
        kind = item["kind"]
        fields(item, common | ({"bytes","sha256"} if kind == "file" else {"target"} if kind == "link" else set()))
        for key in ("uid","gid","device","inode","mode"):
            require(type(item[key]) is int and item[key] >= 0)
        require(item["uid"] == 0 and item["inode"] > 0 and item["mode"] <= 0o7777 and
                (kind == "link" or not item["mode"] & 0o022))
        if kind == "file":
            require(type(item["bytes"]) is int and 0 <= item["bytes"] <= 256*1024**2)
            digest(item["sha256"])
        elif kind == "link":
            require(type(item["target"]) is str and 0 < len(item["target"]) <= 4096 and "\0" not in item["target"])
        require(observed[name] == item)


def inactive_hook(name):
    return PurePosixPath(name).name in ("sitecustomize.py","usercustomize.py") or name.endswith(".pth")


def native_library(name):
    return re.fullmatch(r"libpython[0-9]+\.[0-9]+\.so(?:\.[0-9]+)*",PurePosixPath(name).name) is not None


def validate_inactive_targets(targets, *, native=False):
    require(type(targets) is dict and len(targets) <= 16)
    for name,record in targets.items():
        path(name)
        require(native_library(name) if native else inactive_hook(name))
        fields(record,{"device","inode","uid","gid","mode","links","bytes","mtime_ns","ctime_ns","sha256"})
        for key in ("device","inode","uid","gid","mode","links","bytes","mtime_ns","ctime_ns"):
            require(type(record[key]) is int and 0 <= record[key] < 2**64)
        require(record["inode"] > 0 and record["uid"] == 0 and record["mode"] <= 0o7777
                and record["links"] >= 1 and not record["mode"] & 0o022
                and record["bytes"] <= 256*1024**2)
        digest(record["sha256"])
    return targets


def verify_inactive_targets(targets, *, native=False):
    validate_inactive_targets(targets,native=native)
    for name,record in targets.items():
        parent = directory_fd(Path(name).parent,root_owned=True)
        try:
            info = os.stat(Path(name).name,dir_fd=parent,follow_symlinks=False)
            require(stat.S_ISREG(info.st_mode))
            observed = dict(device=info.st_dev,inode=info.st_ino,uid=info.st_uid,gid=info.st_gid,
                            mode=stat.S_IMODE(info.st_mode),links=info.st_nlink,bytes=info.st_size,
                            mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns)
            raw = regular_at(parent,Path(name).name,256*1024**2,root_owned=True,empty=True,image=True)
            if native:
                require(raw.startswith(b"\x7fELF"))
            require(file_identity(os.stat(Path(name).name,dir_fd=parent,follow_symlinks=False)) == file_identity(info))
            require({**observed,"sha256":sha(raw)} == record)
        finally:
            os.close(parent)


def snapshot_tree(root, *, inactive_link_targets=None, native_link_targets=None):
    """Complete names and identities under an immutable no-follow root."""
    root = Path(root)
    targets = {} if inactive_link_targets is None else inactive_link_targets
    images = {} if native_link_targets is None else native_link_targets
    verify_inactive_targets(targets)
    verify_inactive_targets(images,native=True)
    held = directory_fd(root,root_owned=True)
    pending,records,total = [(root,held,0)],{},0
    try:
        while pending:
            parent,fd,depth = pending.pop()
            try:
                require(depth <= 32)
                for name in os.listdir(fd):
                    require(len(records) < 30000)
                    member = parent/name
                    info = os.stat(name,dir_fd=fd,follow_symlinks=False)
                    require(info.st_uid == 0 and (stat.S_ISLNK(info.st_mode) or not info.st_mode & 0o022))
                    record = dict(uid=info.st_uid,gid=info.st_gid,mode=stat.S_IMODE(info.st_mode),device=info.st_dev,inode=info.st_ino)
                    if stat.S_ISDIR(info.st_mode):
                        child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=fd)
                        if file_identity(os.fstat(child)) != file_identity(info):
                            os.close(child)
                            require(False)
                        pending.append((member,child,depth+1))
                        record.update(kind="directory")
                    elif stat.S_ISLNK(info.st_mode):
                        target = os.readlink(name,dir_fd=fd)
                        resolved = member.resolve(strict=True)
                        require(resolved.is_relative_to(root) or
                                (inactive_hook(name) and str(resolved) in targets and resolved.name == name) or
                                (native_library(name) and str(resolved) in images and native_library(resolved.name)))
                        # Every link target must itself appear in the exact census.
                        record.update(kind="link",target=target)
                    else:
                        raw = regular_at(fd,name,256*1024**2,root_owned=True,empty=True,image=True)
                        total += len(raw)
                        require(total <= 4*1024**3)
                        record.update(kind="file",bytes=len(raw),sha256=sha(raw))
                    require(file_identity(os.stat(name,dir_fd=fd,follow_symlinks=False)) == file_identity(info))
                    records[member.relative_to(root).as_posix()] = record
            finally:
                os.close(fd)
        validate_inventory(records,records)
        verify_inactive_targets(targets)
        verify_inactive_targets(images,native=True)
        return records
    finally:
        for _,fd,_ in pending:
            os.close(fd)


def inactive_inventory(roots, targets):
    """Derive inactive hook hashes only from sealed exact names/targets."""
    validate_inactive_targets(targets)
    inactive,used_targets = {},set()
    for name,expected in roots.items():
        for member,item in expected.items():
            if not inactive_hook(member):
                continue
            if item["kind"] == "file":
                hook_digest = item["sha256"]
            else:
                require(item["kind"] == "link")
                resolved = (Path(name)/member).resolve(strict=True)
                root = Path(name)
                if resolved.is_relative_to(root):
                    target = expected.get(resolved.relative_to(root).as_posix())
                    require(type(target) is dict and target.get("kind") == "file")
                    hook_digest = target["sha256"]
                else:
                    require(str(resolved) in targets and resolved.name == PurePosixPath(member).name)
                    used_targets.add(str(resolved))
                    hook_digest = targets[str(resolved)]["sha256"]
            inactive[str(PurePosixPath(name)/member)] = hook_digest
    require(used_targets == set(targets))
    return inactive


def validate_native_links(roots, targets, native_images):
    validate_inactive_targets(targets,native=True)
    require(type(native_images) is dict)
    used = set()
    for name,inventory in roots.items():
        for member,item in inventory.items():
            if item["kind"] != "link" or not native_library(member):
                continue
            resolved = (Path(name)/member).resolve(strict=True)
            if resolved.is_relative_to(Path(name)):
                continue
            require(str(resolved) in targets and native_library(resolved.name))
            require(native_images.get(str(resolved)) == targets[str(resolved)]["sha256"])
            used.add(str(resolved))
    require(used == set(targets))


def verify_import_closure(config):
    require(sys.flags.isolated and sys.flags.no_site)
    body = root_regular(config["import_closure_path"],16*1024**2)
    require(sha(body) == config["import_closure_sha256"])
    closure = decode(body,16*1024**2)
    closure_keys = {"schema","source_revision","roots","root_identities","absent_paths","startup_hooks","startup_search_path","inactive_hooks","native_images"}
    optional = {key for key in ("inactive_link_targets","native_link_targets") if key in closure}
    fields(closure,closure_keys | optional)
    targets = closure.get("inactive_link_targets",{})
    images = closure.get("native_link_targets",{})
    verify_inactive_targets(targets)
    verify_inactive_targets(images,native=True)
    require(closure["schema"] == "geophysics.waveform-import-closure/v2" and
            closure["source_revision"] == config["source_revision"] and closure["startup_hooks"] == [])
    roots = closure["roots"]
    require(type(roots) is dict and 2 <= len(roots) <= 8 and config["site_packages"] in roots)
    require(any(str(path(name)).startswith("/usr/lib/python") for name in roots))
    fields(closure["root_identities"],roots)
    for name,expected in roots.items():
        path(name)
        held = directory_fd(name,root_owned=True)
        try:
            info = os.fstat(held)
            identity = dict(device=info.st_dev,inode=info.st_ino,uid=info.st_uid,gid=info.st_gid,mode=stat.S_IMODE(info.st_mode))
            require(closure["root_identities"][name] == identity)
        finally:
            os.close(held)
        validate_inventory(snapshot_tree(name,inactive_link_targets=targets,native_link_targets=images),expected)
    require(closure["inactive_hooks"] == inactive_inventory(roots,targets))
    validate_native_links(roots,images,closure["native_images"])
    verify_inactive_targets(targets)
    verify_inactive_targets(images,native=True)
    require(type(closure["absent_paths"]) is list and len(closure["absent_paths"]) <= 16)
    for name in closure["absent_paths"]:
        path(name)
        require(not Path(name).exists() and not Path(name).is_symlink())
    search = closure["startup_search_path"]
    require(type(search) is list and 1 <= len(search) <= 8 and len(set(search)) == len(search))
    for name in search:
        path(name)
    require(set(roots) == {name for name in search if name not in closure["absent_paths"]} | {config["site_packages"]})
    native = closure["native_images"]
    require(type(native) is dict and 1 <= len(native) <= 256)
    for name,expected in native.items():
        digest(expected)
        require(sha(root_regular(name,256*1024**2,image=True)) == expected)
    source = snapshot_tree(config["source_root"])
    names = set(SOURCE_FILES)
    for name in SOURCE_FILES:
        names.update(str(parent) for parent in PurePosixPath(name).parents if str(parent) != ".")
    require(set(source) == names)
    for name,expected in config["source_hashes"].items():
        require(source[name]["kind"] == "file" and source[name]["sha256"] == expected)
    # This stdlib-only probe executes no selected scientific imports or hook.
    # It compares a sealed installation; it does not regenerate or adopt it.
    require(sha(root_regular(config["python"],256*1024**2,image=True)) == config["python_sha256"])
    measured = subprocess.run([config["python"],"-I","-S","-B","-c","import sys,json;print(json.dumps(sys.path))"],
                              cwd=config["custody_root"],env=installed_environment(config),
                              stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3,check=False)
    require(measured.returncode == 0 and not measured.stderr and len(measured.stdout) <= 16384)
    require(decode(measured.stdout,16384) == search)
    return closure


def read_installation(*, complete=True):
    raw = root_regular(CONFIG,65536)
    config = validate_configuration(decode(raw,65536))
    require(raw == canonical(config))
    for name,expected in config["source_hashes"].items():
        require(sha(root_regular(Path(config["source_root"])/name,2*1024**2,image=True)) == expected)
    require(sha(root_regular(config["python"],256*1024**2,image=True)) == config["python_sha256"])
    # The fixed launch entry is usually a distro symlink, not user-selected.
    launcher = Path("/usr/bin/python3").resolve(strict=True)
    require(launcher.parent == Path("/usr/bin"))
    require(sha(root_regular(launcher,256*1024**2,image=True)) == config["launch_python_sha256"])
    require(sha(root_regular(config["admission_path"],65536)) == config["admission_sha256"])
    for name in ("data_root","custody_root","science_work_root"):
        p = Path(config[name])
        require(not any((parent/".git").exists() for parent in (p,*p.parents)))
    if complete:
        verify_import_closure(config)
    return config


def custody_budget(plans, receipts, extra):
    require(type(plans) is list and type(receipts) is list and type(extra) is int and 0 <= extra <= 20*1024**2)
    require(len(plans)+(1 if extra else 0) <= 4 and len(receipts)+(1 if extra else 0) <= 256)
    require(all(type(v) is int and 0 < v <= 20*1024**2 for v in plans) and sum(plans)+extra <= 80*1024**2)
    require(all(type(v) is int and 0 < v <= 65536 for v in receipts))

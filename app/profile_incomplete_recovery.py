"""Separate missing-execution-receipt archive. Partial evidence is not science."""
from __future__ import annotations

import asyncio
import json
import os
import re
import stat

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import make_engine, require_migration_head
from app.models import ObservationDataset, ProcessingJob, RawAsset, SourceRecord
from app.processing_contract import canonical_bytes, checked_derived_path, result_key, sha256
from app.profile_linux_exec import (
    DATA_KEYS, JOB_KEYS, ORIGIN_KEYS, RAW_KEYS, custody_authority, fields,
    integer, sha, uuid, validate_incomplete_recovery, validate_installation,
    file_identity, recorded_installation_binding,
)
from app.profile_linux_recovery import (
    ARCHIVE_CAP, STAGE_CAP, archive_usage, rename_exclusive, retained_ownership,
    validate_ownership, write_exclusive,
)
from app.profile_linux_worker import (
    STREAM_DRAIN_SECONDS, directory_fd, identity, installed_command,
    regular_at, relation, require,
)

MANIFEST_FIELDS = set("schema job_id request_sha256 ownership installation stage_identity members recovery".split())
MEMBER_CAPS = {"result.json":8*1024**2, "linux-stderr.txt":32*1024**2, "stderr.txt":32*1024**2}


def validate_manifest(value,ownership=None):
    fields(value,MANIFEST_FIELDS)
    validate_ownership(value["ownership"])
    require(value["schema"] == "geophysics.profile-incomplete-stage/v1" and
            value["ownership"]["terminal_state"] in ("failed","cancelled") and
            value["job_id"] == value["ownership"]["job_id"] and
            value["request_sha256"] == value["ownership"]["request_sha256"])
    if ownership is not None:
        require(value["ownership"] == ownership)
    validate_installation(value["installation"])
    file_identity(value["stage_identity"])
    validate_incomplete_recovery(value["recovery"])
    require(value["recovery"]["job_id"] == value["job_id"] and
            value["recovery"]["installation"] == value["installation"] and
            value["recovery"]["retained_stage_identity"] == value["stage_identity"])
    require(type(value["members"]) is dict and set(value["members"]) <= set(MEMBER_CAPS))
    for name,record in value["members"].items():
        fields(record,{"device","inode","bytes","sha256"})
        file_identity({key:record[key] for key in ("device","inode")})
        integer(record["bytes"],0,MEMBER_CAPS[name])
        sha(record["sha256"])
    require(sum(record["bytes"] for record in value["members"].values()) <= STAGE_CAP and
            len(canonical_bytes(value)) <= 262144)


def incomplete_descriptor(manifest):
    """M01 adapter boundary only; not automatic deletion admission or a lease."""
    validate_manifest(manifest)
    body = canonical_bytes(manifest)
    return dict(schema="geophysics.profile-incomplete-custody/v1",**manifest["ownership"],
                installation_sha256=sha256(canonical_bytes(manifest["installation"])),manifest=manifest,
                manifest_bytes=len(body),manifest_sha256=sha256(body),
                charged_bytes=2*len(body)+sum(record["bytes"] for record in manifest["members"].values()))


def private_directory(fd):
    info = os.fstat(fd)
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o077)
    return dict(device=info.st_dev,inode=info.st_ino)


def private_member(fd,name,cap):
    before = os.stat(name,dir_fd=fd,follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid() and
            before.st_nlink == 1 and not before.st_mode & 0o077)
    body = regular_at(fd,name,cap)
    after = os.stat(name,dir_fd=fd,follow_symlinks=False)
    require((identity(before),before.st_size,before.st_mode,before.st_mtime_ns,before.st_ctime_ns) ==
            (identity(after),after.st_size,after.st_mode,after.st_mtime_ns,after.st_ctime_ns))
    return body,dict(device=before.st_dev,inode=before.st_ino,bytes=len(body),sha256=sha256(body))


def inventory(fd,*,manifest=False):
    private_directory(fd)
    names = set(os.listdir(fd))
    require(names <= set(MEMBER_CAPS) | ({"manifest.json"} if manifest else set()))
    result = {}
    for name in names - {"manifest.json"}:
        _,result[name] = private_member(fd,name,MEMBER_CAPS[name])
    require(sum(item["bytes"] for item in result.values()) <= STAGE_CAP)
    return result


def reverify(fd,manifest,*,allow_missing_manifest=False):
    validate_manifest(manifest)
    require(private_directory(fd) == manifest["stage_identity"] and inventory(fd,manifest=True) == manifest["members"])
    if "manifest.json" in os.listdir(fd):
        body,_ = private_member(fd,"manifest.json",262144)
        require(body == canonical_bytes(manifest))
    else:
        require(allow_missing_manifest)


def incomplete_usage(fd):
    """Flat bounded census includes intent copies and interrupted rename cuts."""
    private_directory(fd)
    names = os.listdir(fd)
    require(len(names) <= 256)
    identifiers = set()
    total = 0
    for name in names:
        match = re.fullmatch(r"([a-f0-9-]{36})(\.intent\.json)?",name)
        require(match is not None)
        uuid(match[1])
        identifiers.add(match[1])
        if match[2]:
            body,_ = private_member(fd,name,262144)
            record = json.loads(body)
            validate_manifest(record)
            require(record["job_id"] == match[1] and body == canonical_bytes(record))
            total += len(body)
        else:
            require(name+".intent.json" in names)
            intent_body,_ = private_member(fd,name+".intent.json",262144)
            intent = json.loads(intent_body)
            validate_manifest(intent)
            require(intent["job_id"] == name and intent_body == canonical_bytes(intent))
            child = os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            try:
                total += sum(item["bytes"] for item in inventory(child,manifest=True).values())
                body,_ = private_member(child,"manifest.json",262144)
                require(body == intent_body)
                reverify(child,intent)
                total += len(body)
            finally:
                os.close(child)
        require(total <= ARCHIVE_CAP)
    require(len(identifiers) <= 128)
    return total,len(identifiers)


def anchored_parent(path,held):
    current = directory_fd(path)
    try:
        require(identity(os.fstat(current)) == identity(os.fstat(held)))
    finally:
        os.close(current)


def same_recovery_authority(left,right):
    # Extinction must be sampled anew; historical terminal bytes stay immutable.
    validate_incomplete_recovery(left)
    validate_incomplete_recovery(right)
    require({k:v for k,v in left.items() if k != "terminal"} ==
            {k:v for k,v in right.items() if k != "terminal"})


async def recovery_stream(stream,cap):
    """Retain bounded bytes, but keep draining a refused writer until EOF."""
    body = bytearray()
    overflow = False
    while True:
        part = await stream.read(4096)
        if not part:
            require(not overflow)
            return bytes(body)
        if not overflow and len(body)+len(part) <= cap:
            body.extend(part)
        else:
            overflow = True


def start_readers(process,readers):
    if not readers:
        readers.extend((asyncio.create_task(recovery_stream(process.stdout,65536)),
                        asyncio.create_task(recovery_stream(process.stderr,8192))))


async def collect_readers(readers):
    _,pending = await asyncio.wait(readers,timeout=STREAM_DRAIN_SECONDS)
    if pending:
        # Unlike wait_for(gather), do not cancel readers and strand a writer.
        raise asyncio.TimeoutError("profile_recovery_stream_debt")
    return [reader.result() for reader in readers]


async def drain_owned_helper(spawn,readers):
    try:
        process = await spawn
    except Exception:
        # Failed stdlib creation did not return an owned Process. Caller still
        # propagates its original refusal; this is not successful recovery.
        return
    start_readers(process,readers)
    while True:
        try:
            await process.wait()
        except Exception:
            # Uncertain reap cannot release custody. Retry the exact handle,
            # not a numeric PID and never a foreign process or original file.
            await asyncio.sleep(0.05)
            continue
        if process.returncode is not None:
            break
        await asyncio.sleep(0.05)
    await asyncio.gather(*readers,return_exceptions=True)


async def mandatory_helper_drain(spawn,readers):
    """Keep caller's locks/FDs alive even across repeated task cancellation."""
    guard = asyncio.create_task(drain_owned_helper(spawn,readers))
    cancelled = False
    while True:
        try:
            await asyncio.shield(guard)
            return cancelled
        except asyncio.CancelledError:
            cancelled = True


async def recover_incomplete_job(settings,identifier):
    """Caller holds worker singleton; parent/M01 additionally owns common lease."""
    require(os.name == "posix" and os.geteuid() != 0)
    uuid(identifier)
    engine = make_engine(settings)
    sessions = async_sessionmaker(engine,expire_on_commit=False)
    fds,readers = [],[]
    process = spawn = None
    try:
        await require_migration_head(engine)
        async with sessions() as session:
            job = await session.get(ProcessingJob,identifier)
            require(job is not None and job.state in ("failed","cancelled") and job.result_key is None)
            dataset = (await session.execute(select(ObservationDataset).where(ObservationDataset.id == job.dataset_id,
                ObservationDataset.owner_id == job.owner_id,ObservationDataset.project_id == job.project_id))).scalar_one()
            raw = (await session.execute(select(RawAsset).where(RawAsset.id == dataset.raw_asset_id,
                RawAsset.owner_id == job.owner_id,RawAsset.project_id == job.project_id))).scalar_one()
            origin = (await session.execute(select(SourceRecord).where(SourceRecord.id == raw.source_id,
                SourceRecord.owner_id == job.owner_id,SourceRecord.project_id == job.project_id))).scalar_one()
        ownership = retained_ownership(job,dataset,raw,origin)
        command,config = installed_command(settings,job,with_configuration=True)
        packet = dict(job=relation(job,JOB_KEYS),dataset=relation(dataset,DATA_KEYS),raw=relation(raw,RAW_KEYS),origin=relation(origin,ORIGIN_KEYS))
        installation = recorded_installation_binding(config,packet["job"],packet["dataset"],packet["raw"],packet["origin"])
        target = checked_derived_path(settings,result_key(str(job.owner_id),job.project_id,identifier))
        require(not os.path.lexists(target))  # Missing receipt cannot authorize derived-result cleanup.
        stage_path = settings.data_dir/".job-staging"
        stage_parent = directory_fd(stage_path)
        fds.append(stage_parent)
        private_directory(stage_parent)
        archive_path = settings.data_dir/".profile-incomplete"
        require(not archive_path.is_symlink())
        archive_path.mkdir(mode=0o700,exist_ok=True)
        archive_fd = directory_fd(archive_path)
        fds.append(archive_fd)
        private_directory(archive_fd)
        intent_name = identifier+".intent.json"
        intent_exists = intent_name in os.listdir(archive_fd)
        manifest = None
        if intent_exists:
            body,_ = private_member(archive_fd,intent_name,262144)
            manifest = json.loads(body)
            validate_manifest(manifest,ownership)
            require(body == canonical_bytes(manifest) and manifest["installation"] == installation)
        source = stage_parent if identifier in os.listdir(stage_parent) else archive_fd
        require(source == stage_parent or intent_exists)
        require(not (identifier in os.listdir(stage_parent) and identifier in os.listdir(archive_fd)))
        stage_fd = os.open(identifier,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=source)
        fds.append(stage_fd)
        held = private_directory(stage_fd)
        if intent_exists:
            reverify(stage_fd,manifest,allow_missing_manifest=source == stage_parent)
            members = manifest["members"]
        else:
            members = inventory(stage_fd)
        expected = custody_authority(config,packet,held,recovery=True)
        spawn = asyncio.create_task(asyncio.create_subprocess_exec(*command[:-1],"--recover-incomplete",identifier,
            stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
            env={"PATH":"/usr/bin:/bin","PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8"}))
        # Cancellation during asynchronous creation must not lose a child that
        # already exists but whose Process has not reached the caller yet.
        process = await asyncio.shield(spawn)
        start_readers(process,readers)
        await asyncio.wait_for(process.wait(),45)
        stdout,_ = await collect_readers(readers)
        require(process.returncode == 0)
        recovery = json.loads(stdout)
        validate_incomplete_recovery(recovery)
        require(stdout == canonical_bytes(recovery)+b"\n" and recovery["job_id"] == identifier and
                recovery["installation"] == installation and recovery["retained_stage_identity"] == held and
                recovery["authority_sha256"] == sha256(canonical_bytes(expected)))
        # Independently re-read ALL owned rows before mutating ordinary evidence.
        async with sessions() as session:
            current = await session.get(ProcessingJob,identifier)
            current_data = await session.get(ObservationDataset,dataset.id)
            current_raw = await session.get(RawAsset,raw.id)
            current_origin = await session.get(SourceRecord,origin.id)
            require(all(item is not None for item in (current,current_data,current_raw,current_origin)) and
                    current.result_key is None and retained_ownership(current,current_data,current_raw,current_origin) == ownership)
        require(not os.path.lexists(target))
        if intent_exists:
            same_recovery_authority(manifest["recovery"],recovery)
        else:
            manifest = dict(schema="geophysics.profile-incomplete-stage/v1",job_id=identifier,request_sha256=job.request_sha256,
                ownership=ownership,installation=installation,stage_identity=held,members=members,recovery=recovery)
            validate_manifest(manifest,ownership)
        # Census before every mutation (including interrupted intent resumption).
        usage,count = incomplete_usage(archive_fd)
        old_usage,old_count = 0,0
        retained_path = settings.data_dir/".profile-retained"
        if os.path.lexists(retained_path):
            old_fd = directory_fd(retained_path)
            fds.append(old_fd)
            private_directory(old_fd)
            old_usage = archive_usage(old_fd)
            old_count = len({name.split(".",1)[0] for name in os.listdir(old_fd)})
        body = canonical_bytes(manifest)
        remaining = 0 if intent_exists else len(body)
        if source == stage_parent:
            # A manifest already written in stage is still outside archive usage;
            # its rename brings that literal second copy into the charged root.
            remaining += len(body)+sum(item["bytes"] for item in members.values())
        require(count+old_count+(0 if intent_exists else 1) <= 128 and usage+old_usage+remaining <= ARCHIVE_CAP)
        anchored_parent(stage_path,stage_parent)
        anchored_parent(archive_path,archive_fd)
        require(private_directory(stage_fd) == held and inventory(stage_fd,manifest=intent_exists) == members)
        if not intent_exists:
            write_exclusive(archive_fd,intent_name,body)
        if source == stage_parent:
            if "manifest.json" not in os.listdir(stage_fd):
                write_exclusive(stage_fd,"manifest.json",body)
            reverify(stage_fd,manifest)
            require(identity(os.stat(identifier,dir_fd=stage_parent,follow_symlinks=False)) == (held["device"],held["inode"]))
            rename_exclusive(stage_parent,identifier,archive_fd)
            os.fsync(stage_parent)
            os.fsync(archive_fd)
        reverify(stage_fd,manifest)
        require(identity(os.stat(identifier,dir_fd=archive_fd,follow_symlinks=False)) == (held["device"],held["inode"]))
        return manifest
    finally:
        deferred_cancel = await mandatory_helper_drain(spawn,readers) if spawn is not None else False
        for fd in reversed(fds):
            os.close(fd)
        await engine.dispose()
        if deferred_cancel:
            raise asyncio.CancelledError
